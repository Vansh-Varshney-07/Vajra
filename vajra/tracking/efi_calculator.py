"""
EFI (Extreme Forecast Index) and Z-score anomaly field calculator.

The EFI measures how extreme the forecast ensemble is relative to climatology:
    EFI = (2/π) ∫₀¹ [Fc(p) - Ff(p)] / √(p(1-p)) dp

where:
    Fc(p) = climatological CDF at percentile p
    Ff(p) = ensemble forecast CDF at percentile p
    EFI ∈ [-1, 1]; values >0.75 trigger anomaly isolation.

Reference: ECMWF Technical Memorandum 495, Lalaurette 2003.
"""

from __future__ import annotations

import numpy as np
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# EFI core computation
# ---------------------------------------------------------------------------

def _trapezoidal_efi(clim_cdf: np.ndarray, fcst_cdf: np.ndarray, p_grid: np.ndarray) -> np.ndarray:
    """
    Numerically integrate the EFI formula using the trapezoidal rule.

    Parameters
    ----------
    clim_cdf : ndarray, shape (..., n_perc)
        Climatological CDF evaluated at p_grid.
    fcst_cdf  : ndarray, shape (..., n_perc)
        Forecast ensemble CDF evaluated at p_grid.
    p_grid    : ndarray, shape (n_perc,)
        Percentile levels in [0, 1].

    Returns
    -------
    efi : ndarray, shape (...)
        EFI value per spatial grid point.
    """
    # Avoid division by zero at p=0 and p=1
    p_safe = np.clip(p_grid, 1e-6, 1.0 - 1e-6)
    weight = 1.0 / np.sqrt(p_safe * (1.0 - p_safe))  # (n_perc,)

    integrand = (clim_cdf - fcst_cdf) * weight         # (..., n_perc)
    if hasattr(np, "trapezoid"):
        integral = np.trapezoid(integrand, p_grid, axis=-1)
    elif hasattr(np, "trapz"):
        integral = np.trapz(integrand, p_grid, axis=-1)
    else:
        from scipy.integrate import trapezoid
        integral = trapezoid(integrand, p_grid, axis=-1)

    efi = (2.0 / np.pi) * integral
    return np.clip(efi, -1.0, 1.0)


class EFICalculator:
    """
    Computes Extreme Forecast Index (EFI) and anomaly Z-scores for
    each atmospheric variable on an NWP grid.

    Parameters
    ----------
    n_percentile_points : int
        Number of percentile levels used in the numerical integration.
        Default 101 (0.00, 0.01, ... , 1.00).
    efi_threshold : float
        Minimum |EFI| to flag a grid cell as anomalous.
    variables : list[str]
        Variable names to process.
    """

    SUPPORTED_VARIABLES = ["u10", "v10", "t2m", "q850", "mslp", "tp", "z500", "vort850"]

    def __init__(
        self,
        n_percentile_points: int = 101,
        efi_threshold: float = 0.75,
        variables: Optional[list] = None,
    ) -> None:
        self.n_percentile_points = n_percentile_points
        self.efi_threshold = efi_threshold
        self.variables = variables or self.SUPPORTED_VARIABLES
        self.p_grid = np.linspace(0.0, 1.0, n_percentile_points)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute_efi_field(
        self,
        forecast_ensemble: np.ndarray,
        climatology_percentiles: np.ndarray,
    ) -> np.ndarray:
        """
        Compute the EFI for a single variable over the full spatial grid.

        Parameters
        ----------
        forecast_ensemble : ndarray, shape (n_members, H, W)
            Ensemble forecast values.
        climatology_percentiles : ndarray, shape (n_perc_pts, H, W)
            Pre-computed climatological percentiles at self.p_grid levels.

        Returns
        -------
        efi : ndarray, shape (H, W)
            EFI field, values ∈ [-1, 1].
        """
        n_members, H, W = forecast_ensemble.shape
        n_p = self.n_percentile_points

        # Sort ensemble along member axis → empirical CDF at self.p_grid
        ens_sorted = np.sort(forecast_ensemble, axis=0)          # (n_members, H, W)
        ens_p_indices = np.round(self.p_grid * (n_members - 1)).astype(int)
        fcst_cdf = ens_sorted[ens_p_indices]                    # (n_p, H, W)
        fcst_cdf = np.moveaxis(fcst_cdf, 0, -1)                 # (H, W, n_p)

        clim_cdf = np.moveaxis(climatology_percentiles, 0, -1)  # (H, W, n_clim_p)
        if clim_cdf.shape[-1] != n_p:
            from scipy.interpolate import interp1d
            orig_p = np.linspace(0.0, 1.0, clim_cdf.shape[-1])
            interpolator = interp1d(orig_p, clim_cdf, axis=-1, bounds_error=False, fill_value="extrapolate")
            clim_cdf = interpolator(self.p_grid).astype(np.float32)

        efi = _trapezoidal_efi(clim_cdf, fcst_cdf, self.p_grid)  # (H, W)
        return efi

    def compute_zscore_field(
        self,
        forecast_mean: np.ndarray,
        clim_mean: np.ndarray,
        clim_std: np.ndarray,
        epsilon: float = 1e-6,
    ) -> np.ndarray:
        """
        Compute per-pixel Z-score anomaly.

        Z = (forecast_mean - climatological_mean) / climatological_std

        Parameters
        ----------
        forecast_mean : ndarray, shape (H, W)
            Ensemble mean forecast.
        clim_mean     : ndarray, shape (H, W)
            Climatological daily mean.
        clim_std      : ndarray, shape (H, W)
            Climatological daily std.

        Returns
        -------
        z_score : ndarray, shape (H, W)
        """
        z = (forecast_mean - clim_mean) / np.maximum(clim_std, epsilon)
        return z

    def compute_all_variables(
        self,
        forecast_ensemble_dict: Dict[str, np.ndarray],
        climatology_dict: Dict[str, Dict[str, np.ndarray]],
    ) -> Dict[str, Dict[str, np.ndarray]]:
        """
        Compute EFI and Z-score for all supported variables.

        Parameters
        ----------
        forecast_ensemble_dict : dict
            {var_name: ndarray (n_members, H, W)} for each variable.
        climatology_dict : dict
            {var_name: {"mean": ndarray, "std": ndarray, "percentiles": ndarray}}

        Returns
        -------
        anomaly_fields : dict
            {var_name: {"efi": ndarray(H,W), "zscore": ndarray(H,W), "anomaly_mask": ndarray(H,W, bool)}}
        """
        result = {}
        for var in self.variables:
            if var not in forecast_ensemble_dict:
                logger.warning("Variable %s missing from forecast. Skipping.", var)
                continue
            if var not in climatology_dict:
                logger.warning("Variable %s missing from climatology. Skipping.", var)
                continue

            ens = forecast_ensemble_dict[var]          # (n_members, H, W)
            clim = climatology_dict[var]

            efi = self.compute_efi_field(ens, clim["percentiles"])
            z_score = self.compute_zscore_field(
                ens.mean(axis=0),
                clim["mean"],
                clim["std"],
            )
            anomaly_mask = np.abs(efi) >= self.efi_threshold

            result[var] = {
                "efi": efi,
                "zscore": z_score,
                "anomaly_mask": anomaly_mask,
                "efi_max": float(np.max(np.abs(efi))),
                "triggered": bool(anomaly_mask.any()),
            }
            logger.info(
                "Var=%s  EFI_max=%.3f  anomalous_pixels=%d",
                var, result[var]["efi_max"], int(anomaly_mask.sum()),
            )

        return result

    def composite_anomaly_flag(
        self,
        anomaly_fields: Dict[str, Dict[str, np.ndarray]],
        event_type: str = "cyclone",
    ) -> np.ndarray:
        """
        Combine variable-specific anomaly masks into a single composite mask
        using variable signatures defined per event type.

        Event variable signatures (from ARCHITECTURE.md §3.3):
        - cyclone   : mslp (↓), wind speed (↑), tp (↑), vort850 (↑)
        - heatwave  : t2m (↑), z500 (↑ ridging)
        - cold_wave : t2m (↓), mslp (↑)

        Returns
        -------
        composite : ndarray, shape (H, W), dtype bool
        """
        _signatures: Dict[str, list] = {
            "cyclone":   ["mslp", "tp", "vort850", "u10", "v10"],
            "heatwave":  ["t2m", "z500"],
            "cold_wave": ["t2m", "mslp"],
            "flash_flood": ["tp", "q850"],
        }
        event_vars = _signatures.get(event_type.lower(), list(anomaly_fields.keys()))

        composite: Optional[np.ndarray] = None
        for var in event_vars:
            if var not in anomaly_fields:
                continue
            mask = anomaly_fields[var]["anomaly_mask"]
            composite = mask if composite is None else (composite | mask)

        if composite is None:
            # Fall back to first available variable
            composite = next(iter(anomaly_fields.values()))["anomaly_mask"]

        return composite


# ---------------------------------------------------------------------------
# Convenience factory for synthetic demo data (no real NWP files needed)
# ---------------------------------------------------------------------------

def make_synthetic_anomaly_fields(
    H: int = 60,
    W: int = 120,
    event_type: str = "cyclone",
    seed: int = 42,
) -> Tuple[Dict[str, np.ndarray], Dict[str, Dict[str, np.ndarray]]]:
    """
    Generate synthetic forecast ensemble and climatology dicts for testing.

    Returns
    -------
    forecast_ensemble_dict, climatology_dict  (ready for EFICalculator)
    """
    rng = np.random.default_rng(seed)
    vars_ = EFICalculator.SUPPORTED_VARIABLES
    n_members = 20

    forecast_ensemble_dict: Dict[str, np.ndarray] = {}
    climatology_dict: Dict[str, Dict[str, np.ndarray]] = {}

    for var in vars_:
        # Climatological baseline
        clim_mean = rng.standard_normal((H, W)).astype(np.float32)
        clim_std  = np.abs(rng.standard_normal((H, W)).astype(np.float32)) + 0.5

        # Climatological percentiles (n_perc, H, W)
        n_perc = 101
        p_levels = np.linspace(0, 1, n_perc)
        clim_perc = np.array([
            clim_mean + p * clim_std for p in (p_levels - 0.5) * 6
        ])  # rough normal quantiles

        # Forecast ensemble — with injected anomaly signal for cyclone variables
        signal = np.zeros((H, W), dtype=np.float32)
        if event_type == "cyclone" and var in ["tp", "vort850"]:
            cy, cx = H // 2, W // 2
            yy, xx = np.ogrid[:H, :W]
            r = np.sqrt((yy - cy)**2 + (xx - cx)**2)
            signal = (4.0 * np.exp(-r / 5.0)).astype(np.float32)

        ens = np.stack([
            clim_mean + signal + rng.normal(0, 0.3, (H, W)).astype(np.float32)
            for _ in range(n_members)
        ])  # (n_members, H, W)

        forecast_ensemble_dict[var] = ens
        climatology_dict[var] = {
            "mean":        clim_mean,
            "std":         clim_std,
            "percentiles": clim_perc.astype(np.float32),
        }

    return forecast_ensemble_dict, climatology_dict
