import numpy as np
import xarray as xr
from typing import List, Dict, Optional

class ClimatologyEngine:
    """
    Computes climatological baselines (M-Climate) and Extreme Forecast Index (EFI)
    against historical reanalysis distributions (ERA5 / IMDAA).
    """

    def __init__(self, climatology_ds: Optional[xr.Dataset] = None):
        self.climatology = climatology_ds

    def compute_climatological_percentiles(
        self,
        historical_ds: xr.Dataset,
        variables: List[str],
        percentiles: List[float] = [0.90, 0.95, 0.99]
    ) -> xr.Dataset:
        """
        Calculates mean, standard deviation, and key extreme percentiles
        grouped across day-of-year or monthly climatological windows.
        """
        clim = xr.Dataset(attrs={"source": "30-Year Reanalysis Baseline (ERA5/IMDAA)"})
        
        for var in variables:
            if var not in historical_ds:
                continue
            clim[f"{var}_mean"] = historical_ds[var].mean(dim="time")
            clim[f"{var}_std"] = historical_ds[var].std(dim="time")
            for p in percentiles:
                p_label = int(p * 100)
                clim[f"{var}_p{p_label}"] = historical_ds[var].quantile(p, dim="time")

        self.climatology = clim
        return clim

    def compute_z_score_anomaly(
        self,
        forecast_ds: xr.Dataset,
        variable: str
    ) -> xr.DataArray:
        """
        Calculates standard deviation departures:
        Z = (Forecast - Climatological_Mean) / Climatological_Std
        """
        if self.climatology is None:
            raise ValueError("Climatology dataset not loaded.")

        mean = self.climatology[f"{variable}_mean"]
        std = self.climatology[f"{variable}_std"]
        # Avoid division by zero
        std_safe = xr.where(std == 0, 1e-6, std)

        # Broadcast across ensemble member dimension if present
        anomaly = (forecast_ds[variable] - mean) / std_safe
        return anomaly

    def compute_extreme_forecast_index(
        self,
        ensemble_forecast: xr.DataArray,
        variable: str,
        num_quantiles: int = 20
    ) -> xr.DataArray:
        """
        Calculates the Extreme Forecast Index (EFI):
        EFI = (2 / π) * ∫ (Fc(p) - Ff(p)) / sqrt(p * (1 - p)) dp
        
        Where:
        Fc(p) = Climatological quantile values
        Ff(p) = Ensemble forecast CDF
        """
        if "number" not in ensemble_forecast.dims:
            raise ValueError("EFI requires an ensemble dimension ('number').")

        p_vals = np.linspace(0.05, 0.95, num_quantiles)
        weights = 1.0 / np.sqrt(p_vals * (1.0 - p_vals))
        weights /= weights.sum()

        efi_accum = 0.0

        for p, w in zip(p_vals, weights):
            # Climatological threshold for quantile p
            p_label = int(p * 100)
            target_key = f"{variable}_p{p_label}"
            
            if self.climatology is not None and target_key in self.climatology:
                thresh = self.climatology[target_key]
            else:
                # Fallback to empirical ensemble mean + std approximation
                thresh = ensemble_forecast.mean(dim=["time", "number"])

            # Probability of ensemble members exceeding threshold
            p_forecast_exceed = (ensemble_forecast >= thresh).mean(dim="number")
            
            # Integral accumulation
            efi_accum = efi_accum + (w * (p_forecast_exceed - (1.0 - p)))

        efi = (2.0 / np.pi) * efi_accum
        # Clip to valid EFI bounds [-1.0, 1.0]
        efi = np.clip(efi, -1.0, 1.0)
        return efi
