from sklearn.metrics import brier_score_loss
import numpy as np
from typing import Dict, List, Any, Tuple

def compute_brier_score(y_true: List[float], y_prob: List[float]) -> float:
    """Computes the Brier score loss to evaluate probability calibration."""
    return float(brier_score_loss(y_true, y_prob))

def check_calibration_bins(y_true: List[float], y_prob: List[float], n_bins: int = 5) -> List[Dict[str, float]]:
    """Calculates observed rates vs average predictions in bins for calibration audit."""
    y_t = np.array(y_true)
    y_p = np.array(y_prob)
    
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    results = []
    
    for i in range(n_bins):
        bin_min = bin_edges[i]
        bin_max = bin_edges[i+1]
        
        # Mask for scores inside bin
        if i == n_bins - 1:
            mask = (y_p >= bin_min) & (y_p <= bin_max)
        else:
            mask = (y_p >= bin_min) & (y_p < bin_max)
            
        bin_count = int(mask.sum())
        if bin_count > 0:
            observed_rate = float(y_t[mask].mean())
            avg_predicted = float(y_p[mask].mean())
        else:
            observed_rate = 0.0
            avg_predicted = (bin_min + bin_max) / 2.0
            
        results.append({
            "bin_index": i,
            "bin_range": f"[{bin_min:.2f}, {bin_max:.2f}]",
            "observed_rate": observed_rate,
            "average_predicted": avg_predicted,
            "count": bin_count
        })
        
    return results
