import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import json

from cashflow_guardian.risk_engine.model_loader import (
    load_risk_models, clear_model_cache, ModelLoadingError
)

@pytest.fixture(autouse=True)
def setup_teardown():
    clear_model_cache()
    yield
    clear_model_cache()

def test_repeated_load_reuses_cache():
    """Tests that subsequent loads return cached model objects without reading disk again."""
    mock_model = MagicMock()
    mock_model.predict_proba = lambda x: None
    
    with patch("joblib.load", return_value=mock_model) as mock_joblib:
        with patch("pathlib.Path.exists", return_value=True):
            # Mock file opening for model_metadata.json
            meta_content = '{"selected_model": "RandomForest", "version": "1.0.0"}'
            with patch("builtins.open", mock_open(read_data=meta_content)):
                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value.st_mtime = 12345
                    
                    # Load first time
                    m1, m2 = load_risk_models()
                    # Load second time
                    m3, m4 = load_risk_models()
                    
                    # Verify joblib.load was called exactly twice (once for baseline, once for best)
                    assert mock_joblib.call_count == 2
                    assert m1 is m3
                    assert m2 is m4

def test_clear_model_cache_forces_reload():
    """Tests that clear_model_cache() forces joblib.load to be called again."""
    mock_model = MagicMock()
    mock_model.predict_proba = lambda x: None
    
    with patch("joblib.load", return_value=mock_model) as mock_joblib:
        with patch("pathlib.Path.exists", return_value=True):
            meta_content = '{"selected_model": "RandomForest", "version": "1.0.0"}'
            with patch("builtins.open", mock_open(read_data=meta_content)):
                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value.st_mtime = 12345
                    
                    load_risk_models()
                    assert mock_joblib.call_count == 2
                    
                    # Clear cache
                    clear_model_cache()
                    
                    # Load again
                    load_risk_models()
                    assert mock_joblib.call_count == 4

def test_changed_metadata_invalidates_cache():
    """Tests that changing model version in metadata invalidates the cache and reloads."""
    mock_model = MagicMock()
    mock_model.predict_proba = lambda x: None
    
    with patch("joblib.load", return_value=mock_model) as mock_joblib:
        with patch("pathlib.Path.exists", return_value=True):
            # Load first version
            meta_content_1 = '{"selected_model": "RandomForest", "version": "1.0.0"}'
            with patch("builtins.open", mock_open(read_data=meta_content_1)):
                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value.st_mtime = 12345
                    load_risk_models()
                    assert mock_joblib.call_count == 2
            
            # Load with modified metadata version
            meta_content_2 = '{"selected_model": "RandomForest", "version": "1.0.1"}'
            with patch("builtins.open", mock_open(read_data=meta_content_2)):
                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value.st_mtime = 12345
                    load_risk_models()
                    assert mock_joblib.call_count == 4

def test_failed_load_not_cached():
    """Tests that a failed model load raises errors and is not cached as a success."""
    with patch("joblib.load", side_effect=ValueError("Corrupted joblib file")):
        with patch("pathlib.Path.exists", return_value=True):
            meta_content = '{"selected_model": "RandomForest", "version": "1.0.0"}'
            with patch("builtins.open", mock_open(read_data=meta_content)):
                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value.st_mtime = 12345
                    
                    with pytest.raises(ModelLoadingError) as exc:
                        load_risk_models()
                    assert "Corrupted joblib file" in str(exc.value)
                    
                    # Verify subsequent attempt still tries to load and fails (not cached as success)
                    with pytest.raises(ModelLoadingError) as exc2:
                        load_risk_models()
                    assert "Corrupted joblib file" in str(exc2.value)
