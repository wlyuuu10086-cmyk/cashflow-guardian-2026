import os
import pytest
from unittest.mock import patch, mock_open
from pathlib import Path
from cashflow_guardian.risk_engine.model_loader import (
    load_threshold_config, load_feature_columns, load_model_metadata,
    load_risk_models, ModelLoadingError
)

def test_load_threshold_config_missing():
    with patch("pathlib.Path.exists", return_value=False):
        with pytest.raises(ModelLoadingError) as exc:
            load_threshold_config()
        assert "Threshold configuration not found" in str(exc.value)

def test_load_feature_columns_missing():
    with patch("pathlib.Path.exists", return_value=False):
        with pytest.raises(ModelLoadingError) as exc:
            load_feature_columns()
        assert "Feature columns schema not found" in str(exc.value)

def test_load_model_metadata_missing():
    with patch("pathlib.Path.exists", return_value=False):
        with pytest.raises(ModelLoadingError) as exc:
            load_model_metadata()
        assert "Model metadata not found" in str(exc.value)

def test_load_risk_models_missing():
    with patch("pathlib.Path.exists", return_value=False):
        with pytest.raises(ModelLoadingError) as exc:
            load_risk_models()
        assert "model file not found" in str(exc.value)
