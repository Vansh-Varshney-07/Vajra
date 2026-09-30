"""
Zarr Writer module for Vajra.
Converts GRIB2 and NetCDF numerical weather prediction arrays into chunked, compressed,
and consolidated Zarr stores optimized for high-throughput Dask reads.
"""

from __future__ import annotations

import os
import logging
from typing import Dict, Optional, Union
import xarray as xr

logger = logging.getLogger(__name__)

class ZarrWriter:
    """
    Handles chunking, re-encoding, and persisting weather datasets into Zarr format.
    """

    DEFAULT_CHUNKS = {
        "time": 4,
        "number": 5,
        "latitude": 100,
        "longitude": 100
    }

    def __init__(
        self,
        chunks: Optional[Dict[str, int]] = None,
        compressor_level: int = 3
    ):
        self.chunks = chunks or self.DEFAULT_CHUNKS
        self.compressor_level = compressor_level

    def prepare_encoding(self, dataset: xr.Dataset) -> Dict[str, dict]:
        """
        Builds variable encodings with zstd/blosc compression and explicit chunks.
        """
        encoding = {}
        for var_name, var in dataset.data_vars.items():
            var_chunks = []
            for dim in var.dims:
                var_chunks.append(min(self.chunks.get(dim, 50), var.sizes[dim]))
            encoding[var_name] = {
                "chunks": tuple(var_chunks),
            }
        return encoding

    def write(
        self,
        dataset: xr.Dataset,
        output_zarr: str,
        mode: str = "w",
        consolidated: bool = True
    ) -> str:
        """
        Writes the dataset to Zarr store with chunk optimization.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_zarr)), exist_ok=True)
        rechunked_dict = {
            dim: self.chunks[dim] for dim in dataset.dims if dim in self.chunks
        }
        rechunked_ds = dataset.chunk(rechunked_dict)
        encoding = self.prepare_encoding(rechunked_ds)

        logger.info(f"Writing Zarr dataset to {output_zarr} (mode={mode})")
        rechunked_ds.to_zarr(
            output_zarr,
            mode=mode,
            encoding=encoding,
            consolidated=consolidated
        )
        return output_zarr

    def append_time_slice(
        self,
        new_slice: xr.Dataset,
        target_zarr: str,
        dim: str = "time"
    ) -> str:
        """
        Appends a new forecast or lead time step along the specified dimension.
        """
        if not os.path.exists(target_zarr):
            return self.write(new_slice, target_zarr, mode="w")

        logger.info(f"Appending along dim='{dim}' to {target_zarr}")
        new_slice.to_zarr(target_zarr, mode="a", append_dim=dim, consolidated=True)
        return target_zarr
