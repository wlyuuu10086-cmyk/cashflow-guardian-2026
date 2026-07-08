import pytest
from cashflow_guardian.risk_engine.calibration import compute_brier_score, check_calibration_bins

def test_compute_brier_score():
    y_true = [0.0, 1.0, 1.0, 0.0]
    y_prob = [0.1, 0.9, 0.8, 0.2]
    
    # Brier = ((0-0.1)^2 + (1-0.9)^2 + (1-0.8)^2 + (0-0.2)^2) / 4
    #       = (0.01 + 0.01 + 0.04 + 0.04) / 4 = 0.10 / 4 = 0.025
    brier = compute_brier_score(y_true, y_prob)
    assert brier == pytest.approx(0.025)

def test_check_calibration_bins():
    y_true = [0, 0, 1, 1, 1]
    y_prob = [0.1, 0.2, 0.6, 0.7, 0.9]
    
    # 5 bins: [0, 0.2), [0.2, 0.4), [0.4, 0.6), [0.6, 0.8), [0.8, 1.0]
    bins = check_calibration_bins(y_true, y_prob, n_bins=5)
    
    assert len(bins) == 5
    assert bins[0]["count"] == 1  # 0.1 in [0.0, 0.2)
    assert bins[4]["count"] == 1  # 0.9 in [0.8, 1.0]
