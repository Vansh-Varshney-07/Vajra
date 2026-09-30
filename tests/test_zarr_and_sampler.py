import os
import shutil
import tempfile
import torch
import numpy as np
import pytest
from vajra.ingestion.nwp_loader import NWPDataLoader
from vajra.ingestion.zarr_writer import ZarrWriter
from vajra.downscaling.unet_backbone import ConditionalUNet
from vajra.downscaling.diffusion_pipeline import WeatherDiffusionPipeline
from vajra.downscaling.sampler import ProbabilisticEnsembleSampler

def test_zarr_writer_export():
    temp_dir = tempfile.mkdtemp()
    try:
        ds = NWPDataLoader.create_synthetic_ensemble(num_times=2, num_members=2, lat_range=(10, 12), lon_range=(80, 82), res=1.0)
        writer = ZarrWriter(chunks={"time": 1, "number": 1, "latitude": 2, "longitude": 2})
        zarr_path = os.path.join(temp_dir, "test_store.zarr")
        out = writer.write(ds, zarr_path)
        assert os.path.exists(out)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_probabilistic_ensemble_sampler():
    model = ConditionalUNet(in_channels=4, condition_channels=4, out_channels=4, base_channels=16)
    pipeline = WeatherDiffusionPipeline(model=model, num_timesteps=10, device="cpu")
    sampler = ProbabilisticEnsembleSampler(diffusion_pipeline=pipeline, num_samples=3, device="cpu")

    coarse = torch.randn(1, 4, 32, 32)
    results = sampler.generate_samples(coarse, shape=(4, 32, 32))

    assert "samples" in results
    assert "mean" in results
    assert "p90" in results
    assert "uncertainty" in results
    assert results["samples"].shape[0] == 3
    assert "metrics" in results
