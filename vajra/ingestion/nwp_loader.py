import os
import glob
from typing import Dict, List, Optional
import xarray as xr
import dask.array as da
import numpy as np

class NWPDataLoader:
    """
    Handles ingestion of multi-dimensional 4D weather data (time, ensemble, lat, lon)
    from GRIB2 / NetCDF into chunked Dask-backed Xarray datasets and Zarr stores.
    """

    DEFAULT_CHUNKS = {
        "time": 5,
        "number": 10,
        "latitude": 200,
        "longitude": 200
    }

    def __init__(self, chunks: Optional[Dict[str, int]] = None):
        self.chunks = chunks or self.DEFAULT_CHUNKS

    def open_ensemble_dataset(
        self,
        file_paths: List[str],
        engine: str = "cfgrib"
    ) -> xr.Dataset:
        """
        Loads multiple ensemble member files in parallel.
        Concatenates along the 'number' (ensemble member) dimension.
        """
        if not file_paths:
            raise ValueError("No file paths provided to open_ensemble_dataset")

        ds = xr.open_mfdataset(
            file_paths,
            engine=engine,
            combine="nested",
            concat_dim="number",
            parallel=True,
            chunks=self.chunks
        )
        return ds

    def export_to_zarr(
        self,
        dataset: xr.Dataset,
        zarr_path: str,
        overwrite: bool = True
    ) -> str:
        """
        Exports large multidimensional dataset to chunked Zarr format
        for high-performance chunked reads.
        """
        os.makedirs(os.path.dirname(os.path.abspath(zarr_path)), exist_ok=True)
        mode = "w" if overwrite else "w-"
        dataset.to_zarr(zarr_path, mode=mode, consolidated=True)
        return zarr_path

    @staticmethod
    def create_synthetic_ensemble(
        num_times: int = 8,
        num_members: int = 10,
        lat_range: tuple = (5.0, 35.0),
        lon_range: tuple = (65.0, 95.0),
        res: float = 0.5
    ) -> xr.Dataset:
        """
        Generates a synthetic 4D ensemble dataset covering the Indian subcontinent & Bay of Bengal
        for rapid testing and offline pipeline validation without requiring multi-gigabyte GRIB2 downloads.
        """
        lats = np.arange(lat_range[0], lat_range[1] + res, res)
        lons = np.arange(lon_range[0], lon_range[1] + res, res)
        times = np.arange(num_times)
        members = np.arange(num_members)

        shape = (num_times, num_members, len(lats), len(lons))
        
        # Synthetic realistic weather fields
        u10 = np.random.normal(5.0, 10.0, size=shape)
        v10 = np.random.normal(-2.0, 8.0, size=shape)
        t2m = np.random.normal(300.0, 5.0, size=shape)
        q850 = np.random.uniform(0.005, 0.020, size=shape)
        mslp = np.random.normal(100800.0, 800.0, size=shape)
        tp = np.random.exponential(scale=5.0, size=shape)
        z500 = np.random.normal(5800.0, 60.0, size=shape)

        ds = xr.Dataset(
            data_vars={
                "u10": (["time", "number", "latitude", "longitude"], u10),
                "v10": (["time", "number", "latitude", "longitude"], v10),
                "t2m": (["time", "number", "latitude", "longitude"], t2m),
                "q850": (["time", "number", "latitude", "longitude"], q850),
                "mslp": (["time", "number", "latitude", "longitude"], mslp),
                "tp": (["time", "number", "latitude", "longitude"], tp),
                "z500": (["time", "number", "latitude", "longitude"], z500),
            },
            coords={
                "time": times,
                "number": members,
                "latitude": lats,
                "longitude": lons,
            },
            attrs={
                "title": "Vajra Synthetic Ensemble Test Dataset (Bay of Bengal / Indian Subcontinent)",
                "institution": "MoES / NCMRWF Prototype",
            }
        )
        return ds
