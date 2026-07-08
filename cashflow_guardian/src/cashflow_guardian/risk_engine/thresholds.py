import os
import json
from pathlib import Path
from typing import Dict, Any, Tuple
from .model_loader import load_threshold_config, ModelLoadingError

def get_fallback_thresholds() -> Dict[str, Dict[str, float]]:
    return {
        "low": {"min": 0.00, "max": 0.30},
        "medium": {"min": 0.30, "max": 0.70},
        "high": {"min": 0.70, "max": 0.90},
        "critical": {"min": 0.90, "max": 1.00}
    }

def map_score_to_tier(score: float) -> Tuple[str, str]:
    """Maps a risk score between 0.0 and 1.0 to a risk tier.
    
    Returns:
        (lowercase_tier, uppercase_tier) e.g., ("high", "RED")
    """
    try:
        config = load_threshold_config()
        tiers = config.get("tiers", get_fallback_thresholds())
    except (ModelLoadingError, FileNotFoundError, json.JSONDecodeError):
        # Graceful fallback to default thresholds if config file is missing/broken
        tiers = get_fallback_thresholds()
        
    score = max(0.0, min(score, 1.0))
    
    # Check tiers
    if score <= tiers["low"]["max"]:
        return "low", "GREEN"
    elif score <= tiers["medium"]["max"]:
        return "medium", "AMBER"
    elif score <= tiers["high"]["max"]:
        return "high", "RED"
    else:
        return "critical", "CRITICAL"
