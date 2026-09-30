import torch
import torch.nn as nn
from typing import Dict, List, Optional
import numpy as np
from .unet_backbone import ConditionalUNet

class WeatherDiffusionPipeline:
    """
    Manages training and probabilistic sampling of high-resolution 5km atmospheric fields.
    Generates multi-member ensembles from a single 12km coarse input to capture extreme uncertainty.
    """

    def __init__(
        self,
        model: ConditionalUNet,
        num_timesteps: int = 1000,
        beta_start: float = 0.0001,
        beta_end: float = 0.02,
        device: str = "cpu"
    ):
        self.model = model.to(device)
        self.device = device
        self.num_timesteps = num_timesteps

        # Linear noise schedule
        self.betas = torch.linspace(beta_start, beta_end, num_timesteps, device=device)
        self.alphas = 1.0 - self.betas
        self.alphas_cumprod = torch.cumprod(self.alphas, dim=0)
        self.alphas_cumprod_prev = torch.cat([
            torch.tensor([1.0], device=device),
            self.alphas_cumprod[:-1]
        ])

        # Calculations for diffusion q(x_t | x_0)
        self.sqrt_alphas_cumprod = torch.sqrt(self.alphas_cumprod)
        self.sqrt_one_minus_alphas_cumprod = torch.sqrt(1.0 - self.alphas_cumprod)

        # Calculations for posterior q(x_{t-1} | x_t, x_0)
        self.posterior_variance = (
            self.betas * (1.0 - self.alphas_cumprod_prev) / (1.0 - self.alphas_cumprod)
        )

    def q_sample(self, x_start: torch.Tensor, t: torch.Tensor, noise: Optional[torch.Tensor] = None) -> torch.Tensor:
        """Adds Gaussian noise to x_start according to diffusion step t."""
        if noise is None:
            noise = torch.randn_like(x_start)

        sqrt_alpha = self.sqrt_alphas_cumprod[t][:, None, None, None]
        sqrt_one_minus = self.sqrt_one_minus_alphas_cumprod[t][:, None, None, None]
        return sqrt_alpha * x_start + sqrt_one_minus * noise

    @torch.no_grad()
    def p_sample(self, x: torch.Tensor, t: int, condition: torch.Tensor) -> torch.Tensor:
        """Single reverse diffusion denoising step from t to t-1."""
        t_tensor = torch.full((x.shape[0],), t, device=self.device, dtype=torch.long)
        pred_noise = self.model(x, t_tensor, condition)

        beta_t = self.betas[t]
        alpha_t = self.alphas[t]
        alpha_cumprod_t = self.alphas_cumprod[t]

        # Estimate x_0
        pred_x0 = (x - (beta_t / torch.sqrt(1.0 - alpha_cumprod_t)) * pred_noise) / torch.sqrt(alpha_t)

        if t > 0:
            noise = torch.randn_like(x)
            var = torch.sqrt(self.posterior_variance[t])
            return pred_x0 + var * noise
        return pred_x0

    @torch.no_grad()
    def sample_ensemble(
        self,
        condition: torch.Tensor,
        num_samples: int = 20,
        shape: tuple = (4, 64, 64)
    ) -> Dict[str, np.ndarray]:
        """
        Samples an ensemble of plausible high-resolution weather scenarios conditioned on coarse data.
        Returns: mean, median, P90, P95, and uncertainty spread.
        """
        self.model.eval()
        condition = condition.to(self.device)
        batch_size = condition.shape[0]

        all_generated_samples = []

        for sample_idx in range(num_samples):
            # Start from pure Gaussian noise
            x = torch.randn((batch_size, *shape), device=self.device)

            # Iterative reverse diffusion
            for t in reversed(range(0, self.num_timesteps, 50)): # Fast sampling with strided steps
                x = self.p_sample(x, t, condition)

            all_generated_samples.append(x.cpu().numpy())

        # Shape: [Num_Samples, Batch, Channels, Height, Width]
        stack = np.array(all_generated_samples)

        mean_field = np.mean(stack, axis=0)
        median_field = np.median(stack, axis=0)
        p90_field = np.percentile(stack, 90, axis=0)
        p95_field = np.percentile(stack, 95, axis=0)
        std_uncertainty = np.std(stack, axis=0)

        return {
            "samples": stack,
            "mean": mean_field,
            "median": median_field,
            "p90": p90_field,
            "p95": p95_field,
            "uncertainty": std_uncertainty
        }
