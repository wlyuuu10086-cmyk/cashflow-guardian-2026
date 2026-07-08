import pytest
from unittest.mock import patch
from cashflow_guardian.risk_engine.thresholds import map_score_to_tier, get_fallback_thresholds

@patch("cashflow_guardian.risk_engine.thresholds.load_threshold_config")
def test_map_score_to_tier_fallback(mock_load):
    mock_load.return_value = {
        "tiers": get_fallback_thresholds()
    }
    
    # Green/Low: score <= 0.30
    assert map_score_to_tier(0.12) == ("low", "GREEN")
    assert map_score_to_tier(0.30) == ("low", "GREEN")
    
    # Amber/Medium: 0.30 < score <= 0.70
    assert map_score_to_tier(0.31) == ("medium", "AMBER")
    assert map_score_to_tier(0.70) == ("medium", "AMBER")
    
    # Red/High: 0.70 < score <= 0.90
    assert map_score_to_tier(0.75) == ("high", "RED")
    assert map_score_to_tier(0.90) == ("high", "RED")
    
    # Critical: score > 0.90
    assert map_score_to_tier(0.95) == ("critical", "CRITICAL")
