import numpy as np
import pytest
from vajra.tracking.efi_calculator import EFICalculator, make_synthetic_anomaly_fields

def test_efi_computation_values_range():
    H, W = 20, 30
    fcst_dict, clim_dict = make_synthetic_anomaly_fields(H=H, W=W, event_type="cyclone", seed=123)
    calc = EFICalculator(n_percentile_points=51, efi_threshold=0.7)

    results = calc.compute_all_variables(fcst_dict, clim_dict)
    assert "tp" in results
    assert "mslp" in results

    efi_tp = results["tp"]["efi"]
    assert efi_tp.shape == (H, W)
    assert np.all(efi_tp >= -1.0) and np.all(efi_tp <= 1.0)

def test_composite_anomaly_flag():
    H, W = 20, 30
    fcst_dict, clim_dict = make_synthetic_anomaly_fields(H=H, W=W, event_type="cyclone", seed=99)
    calc = EFICalculator(n_percentile_points=21, efi_threshold=0.5)
    results = calc.compute_all_variables(fcst_dict, clim_dict)

    flag = calc.composite_anomaly_flag(results, event_type="cyclone")
    assert flag.shape == (H, W)
    assert flag.dtype == bool
