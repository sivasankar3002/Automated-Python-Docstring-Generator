# docugenius_config.py - Reads config from pyproject.toml WITHOUT modifying your core code
import tomllib  # Python 3.11+ (use 'import tomli as tomllib' for Python <3.11)
from pathlib import Path
from typing import Dict, Any

DEFAULT_CONFIG = {
    "style": "google",
    "min_coverage": 90.0,
    "min_compliance": 85.0,
    "exclude_patterns": ["tests/**", "venv/**", "__pycache__/**", ".*"]
}

def load_config(root_dir: Path = None) -> Dict[str, Any]:
    """Load configuration from pyproject.toml in the project root"""
    root_dir = root_dir or Path.cwd()
    config_path = root_dir / "pyproject.toml"
    
    if not config_path.exists():
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(config_path, "rb") as f:
            pyproject = tomllib.load(f)
        
        # Extract docugenius-specific config
        tool_config = pyproject.get("tool", {}).get("docugenius", {})
        config = DEFAULT_CONFIG.copy()
        config.update(tool_config)
        return config
        
    except Exception as e:
        print(f"Warning: Failed to load pyproject.toml config: {e}")
        return DEFAULT_CONFIG.copy()