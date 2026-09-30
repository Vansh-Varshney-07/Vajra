"""
Probabilistic Ensemble Sampler for Diffusion Downscaling.
Generates multi-future high-resolution realizations (e.g., 20 samples)
conditioned on coarse NWP inputs, extracting extreme tail metrics (P90, P95, uncertainty).
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)

class ProbabilisticEnsembleSampler:
    """
    Downscaling sampler that generates multi-sample ensembles to capture
    meteorological variability and preserve heavy-tail extremes.
    """

    def __init__(
        self,
        diffusion_pipeline,
        num_samples: int = 20,
        guidance_scale: float = 3.5,
        device: str = "cpu"
    ):
        self.pipeline = diffusion_pipeline
        self.num_samples = num_samples
        self.guidance_scale = guidance_scale
        self.device = device

    @torch.no_grad()
    def generate_samples(
        self,
        coarse_tensor: torch.Tensor,
        num_inference_steps: int = 20,
        shape: Tuple[int, int, int] = (4, 64, 64)
    ) -> Dict[str, Union[np.ndarray, dict]]:
        """
        Samples an ensemble of plausible realizations conditioned on coarse_tensor.

        Parameters
        ----------
        coarse_tensor : torch.Tensor, shape (B, C_in, H, W) or (C_in, H, W)
            12km coarse forecast tensor.
        num_inference_steps : int
            Number of reverse diffusion denoising steps.
        shape : tuple
            (C_out, H_out, W_out) high-resolution output shape.

        Returns
        -------
        dict containing:
            - "samples": ndarray (num_samples, B, C, H, W)
            - "mean": ndarray (B, C, H, W)
            - "median": ndarray (B, C, H, W)
            - "p90": ndarray (B, C, H, W)
            - "p95": ndarray (B, C, H, W)
            - "uncertainty": ndarray (B, C, H, W) (standard deviation)
            - "metrics": summary dictionary of peak values
        """
        if coarse_tensor.ndim == 3:
            coarse_tensor = coarse_tensor.unsqueeze(0)

        B = coarse_tensor.shape[0]
        coarse_tensor = coarse_tensor.to(self.device)

        logger.info(f"Generating {self.num_samples} probabilistic downscaled futures...")

        # If pipeline has custom sample_ensemble method, use it
        if hasattr(self.pipeline, "sample_ensemble"):
            results = self.pipeline.sample_ensemble(
                condition=coarse_tensor,
                num_samples=self.num_samples,
                shape=shape
            )
        else:
            samples = []
            for s_idx in range(self.num_samples):
                # Generative sample with latent perturbation
                x = torch.randn((B, *shape), device=self.device)
                for t in reversed(range(0, getattr(self.pipeline, "num_timesteps", 1000), 50)):
                    x = self.pipeline.p_sample(x, t, coarse_tensor)
                samples.append(x.cpu().numpy())

            stack = np.array(samples)  # (num_samples, B, C, H, W)
            results = {
                "samples": stack,
                "mean": np.mean(stack, axis=0),
                "median": np.median(stack, axis=0),
                "p90": np.percentile(stack, 90, axis=0),
                "p95": np.percentile(stack, 95, axis=0),
                "uncertainty": np.std(stack, axis=0)
            }

        # Compute summary metrics across channels (e.g. Channel 3: precipitation, Channel 0/1: wind)
        p90_max = float(np.max(results["p90"]))
        mean_max = float(np.max(results["mean"]))
        unc_mean = float(np.mean(results["uncertainty"]))

        results["metrics"] = {
            "num_samples": self.num_samples,
            "peak_mean": mean_max,
            "peak_p90_extreme": p90_max,
            "amplitude_retention_ratio": float(p90_max / max(mean_max, 1e-4)),
            "average_uncertainty": unc_mean
        }

        return results
