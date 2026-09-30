import torch
import torch.nn as nn
from typing import Tuple, Dict

class AtmosphericPhysicsLoss(nn.Module):
    """
    Differentiable Physics Constraints Loss for Atmospheric Downscaling:
    1. Tail-Extreme Loss: Amplifies penalties for tail values (P95+) to prevent spectral smoothing.
    2. Mass Continuity Loss: Penalizes non-zero horizontal wind divergence.
    3. Moisture Flux Consistency Loss: Penalizes severe precipitation missing moisture convergence.
    """

    def __init__(
        self,
        dx_meters: float = 5000.0,
        dy_meters: float = 5000.0,
        lambda_div: float = 0.15,
        lambda_moist: float = 0.20,
        lambda_extreme: float = 5.0,
        extreme_percentile_val: float = 50.0 # e.g. 50 mm/12hr threshold for extremes
    ):
        super().__init__()
        self.dx = dx_meters
        self.dy = dy_meters
        self.lambda_div = lambda_div
        self.lambda_moist = lambda_moist
        self.lambda_extreme = lambda_extreme
        self.extreme_percentile_val = extreme_percentile_val

    def forward(
        self,
        pred_tensor: torch.Tensor,
        target_tensor: torch.Tensor
    ) -> Tuple[torch.Tensor, Dict[str, float]]:
        """
        Tensors of shape: [Batch, Channels, Height, Width]
        Channel 0: u10 zonal wind (m/s)
        Channel 1: v10 meridional wind (m/s)
        Channel 2: specific humidity q (kg/kg)
        Channel 3: total precipitation (mm)
        """
        # Base MSE Loss
        base_mse = nn.functional.mse_loss(pred_tensor, target_tensor)

        # 1. Extreme Value Loss (prevents spectral smoothing / peak flattening)
        diff_sq = (pred_tensor - target_tensor) ** 2
        extreme_mask = (target_tensor > self.extreme_percentile_val).float()
        loss_extreme = torch.mean(diff_sq * (1.0 + self.lambda_extreme * extreme_mask))

        # 2. Horizontal Mass Divergence: du/dx + dv/dy
        u = pred_tensor[:, 0:1, :, :]
        v = pred_tensor[:, 1:2, :, :]

        du_dx = (u[:, :, :, 2:] - u[:, :, :, :-2]) / (2.0 * self.dx)
        dv_dy = (v[:, :, 2:, :] - v[:, :, :-2, :]) / (2.0 * self.dy)
        
        # Crop borders to match centered difference interior
        div_h = du_dx[:, :, 1:-1, :] + dv_dy[:, :, :, 1:-1]
        loss_divergence = torch.mean(torch.abs(div_h))

        # 3. Moisture Flux Convergence: - div(q * V)
        q = pred_tensor[:, 2:3, :, :]
        p = pred_tensor[:, 3:4, :, :]

        flux_x = q * u
        flux_y = q * v

        dflux_x = (flux_x[:, :, :, 2:] - flux_x[:, :, :, :-2]) / (2.0 * self.dx)
        dflux_y = (flux_y[:, :, 2:, :] - flux_y[:, :, :-2, :]) / (2.0 * self.dy)
        moisture_convergence = -(dflux_x[:, :, 1:-1, :] + dflux_y[:, :, :, 1:-1])

        p_interior = p[:, :, 1:-1, 1:-1]
        # Penalize precipitation where moisture convergence is strongly negative (divergent moisture)
        loss_moisture = torch.mean(torch.relu(-moisture_convergence * p_interior))

        total_loss = (
            loss_extreme +
            (self.lambda_div * loss_divergence) +
            (self.lambda_moist * loss_moisture)
        )

        metrics = {
            "total_loss": float(total_loss.item()),
            "mse": float(base_mse.item()),
            "extreme_loss": float(loss_extreme.item()),
            "divergence_penalty": float(loss_divergence.item()),
            "moisture_penalty": float(loss_moisture.item())
        }

        return total_loss, metrics
