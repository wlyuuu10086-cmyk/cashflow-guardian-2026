import os
import json
import joblib
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

class ModelLoadingError(Exception):
    """Raised when models or configurations cannot be loaded."""
    pass

def get_repo_root() -> Path:
    # cashflow_guardian/src/cashflow_guardian/risk_engine/model_loader.py
    return Path(__file__).resolve().parent.parent.parent.parent

def get_models_dir() -> Path:
    return get_repo_root() / "models"

def load_threshold_config() -> Dict[str, Any]:
    models_dir = get_models_dir()
    config_path = models_dir / "threshold_config.json"
    if not config_path.exists():
        raise ModelLoadingError(f"Threshold configuration not found at {config_path}")
        
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        raise ModelLoadingError(f"Failed to read threshold configuration: {e}")

def load_feature_columns() -> Dict[str, List[str]]:
    models_dir = get_models_dir()
    cols_path = models_dir / "feature_columns.json"
    if not cols_path.exists():
        raise ModelLoadingError(f"Feature columns schema not found at {cols_path}")
        
    try:
        with open(cols_path, "r") as f:
            return json.load(f)
    except Exception as e:
        raise ModelLoadingError(f"Failed to read feature columns schema: {e}")

def load_model_metadata() -> Dict[str, Any]:
    models_dir = get_models_dir()
    meta_path = models_dir / "model_metadata.json"
    if not meta_path.exists():
        raise ModelLoadingError(f"Model metadata not found at {meta_path}")
        
    try:
        with open(meta_path, "r") as f:
            return json.load(f)
    except Exception as e:
        raise ModelLoadingError(f"Failed to read model metadata: {e}")

_MODEL_CACHE: Dict[Tuple[Any, ...], Tuple[Any, Any]] = {}

def clear_model_cache() -> None:
    """Clears the model loading cache to force reload in tests."""
    global _MODEL_CACHE
    _MODEL_CACHE.clear()

def load_risk_models() -> Tuple[Any, Any]:
    """Loads baseline_model.joblib and best_model.joblib with a safe cache.
    
    Raises ModelLoadingError if missing or invalid.
    """
    global _MODEL_CACHE
    
    models_dir = get_models_dir()
    baseline_path = models_dir / "baseline_model.joblib"
    best_path = models_dir / "best_model.joblib"
    meta_path = models_dir / "model_metadata.json"
    
    # Check baseline and best paths first to align with existing missing-file tests
    if not baseline_path.exists():
        raise ModelLoadingError(f"Baseline model file not found at {baseline_path}")
    if not best_path.exists():
        raise ModelLoadingError(f"Best model file not found at {best_path}")
    if not meta_path.exists():
        raise ModelLoadingError(f"Model metadata not found at {meta_path}")
        
    try:
        with open(meta_path, "r") as f:
            metadata = json.load(f)
    except Exception as e:
        raise ModelLoadingError(f"Failed to read model metadata: {e}")
        
    try:
        baseline_mtime = baseline_path.stat().st_mtime
        best_mtime = best_path.stat().st_mtime
        meta_mtime = meta_path.stat().st_mtime
    except Exception as e:
        raise ModelLoadingError(f"Failed to verify model file timestamps: {e}")
        
    model_version = metadata.get("selected_model", "unknown") + "_" + metadata.get("version", "1.0.0")
    cache_key = (str(baseline_path), baseline_mtime, str(best_path), best_mtime, model_version, meta_mtime)
    
    if cache_key in _MODEL_CACHE:
        return _MODEL_CACHE[cache_key]
        
    try:
        baseline_model = joblib.load(baseline_path)
        best_model = joblib.load(best_path)
        
        if not hasattr(baseline_model, "predict_proba") or not hasattr(best_model, "predict_proba"):
            raise ModelLoadingError("Loaded models do not support predict_proba.")
            
        _MODEL_CACHE[cache_key] = (baseline_model, best_model)
        return baseline_model, best_model
    except Exception as e:
        raise ModelLoadingError(f"Error loading Joblib model files: {e}")


