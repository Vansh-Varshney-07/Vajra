import numpy as np
from typing import Tuple

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance between two points on Earth in kilometers."""
    r = 6371.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)

    a = np.sin(dphi / 2.0)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2.0)**2
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    return float(r * c)

def peak_amplitude_retention_error(pred: np.ndarray, target: np.ndarray, quantile: float = 0.99) -> float:
    """
    Measures spectral smoothing by calculating the relative percentage error
    between the top 1% extreme values in predicted vs target arrays.
    0.0% means perfect amplitude retention.
    """
    p_pred = np.quantile(pred, quantile)
    p_true = np.quantile(target, quantile)

    if p_true == 0:
        return 0.0
    error = abs(p_pred - p_true) / p_true
    return float(error * 100.0)

def symmetric_extremal_dependence_index(
    hits: int,
    false_alarms: int,
    misses: int,
    correct_negatives: int
) -> float:
    """
    Calculates SEDI (Symmetric Extremal Dependence Index), the standard metric
    for rare and extreme meteorological event verification.
    SEDI ∈ [-1, 1], with 1.0 being perfect skill and 0.0 being random chance.
    """
    total = hits + false_alarms + misses + correct_negatives
    if total == 0:
        return 0.0

    hit_rate = hits / (hits + misses) if (hits + misses) > 0 else 1e-6
    false_alarm_rate = false_alarms / (false_alarms + correct_negatives) if (false_alarms + correct_negatives) > 0 else 1e-6

    # Avoid log(0) or log(1)
    hit_rate = np.clip(hit_rate, 1e-5, 1.0 - 1e-5)
    false_alarm_rate = np.clip(false_alarm_rate, 1e-5, 1.0 - 1e-5)

    num = np.log(false_alarm_rate) - np.log(hit_rate) - np.log(1.0 - false_alarm_rate) + np.log(1.0 - hit_rate)
    den = np.log(false_alarm_rate) + np.log(hit_rate) + np.log(1.0 - false_alarm_rate) + np.log(1.0 - hit_rate)

    sedi = num / den
    return float(np.clip(sedi, -1.0, 1.0))

# ─── Aliases for Vajra utils package ──────────────────────────────────────────
def compute_crps(ensemble_predictions: np.ndarray, observation: float) -> float:
    """Continuous Ranked Probability Score (CRPS) for ensemble evaluation."""
    ensemble = np.sort(ensemble_predictions)
    n = len(ensemble)
    mae = np.mean(np.abs(ensemble - observation))
    diff_sum = np.sum([np.abs(e1 - e2) for e1 in ensemble for e2 in ensemble])
    return float(mae - (diff_sum / (2.0 * n * n)))

def compute_sedi(hits: int, false_alarms: int, misses: int, correct_negatives: int) -> float:
    return symmetric_extremal_dependence_index(hits, false_alarms, misses, correct_negatives)

def compute_ets(hits: int, false_alarms: int, misses: int, correct_negatives: int) -> float:
    """Equitable Threat Score (ETS)."""
    n = hits + false_alarms + misses + correct_negatives
    hits_random = ((hits + misses) * (hits + false_alarms)) / n if n > 0 else 0
    den = (hits + false_alarms + misses - hits_random)
    return float((hits - hits_random) / den) if den > 0 else 0.0

def compute_peak_amplitude_retention(pred: np.ndarray, target: np.ndarray, quantile: float = 0.99) -> float:
    return 100.0 - peak_amplitude_retention_error(pred, target, quantile)
