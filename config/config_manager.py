"""
Configuration Manager for HAM (HSTL Audio Metadata) Framework.

Handles loading, saving, and managing configuration data for batch projects.
Supports YAML configuration files with hierarchical dot-notation access.
"""

import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from config.settings import DEFAULT_SETTINGS

HAM_VERSION = "0.1.0"


class ConfigManager:
    """Manages configuration for HAM batch projects."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path
        self.config_data: Dict[str, Any] = {}
        self._reset_to_defaults()

        if config_path and config_path.exists():
            self.load_config(config_path)

    def _reset_to_defaults(self):
        import copy
        self.config_data = copy.deepcopy(DEFAULT_SETTINGS)

    # ------------------------------------------------------------------
    # Load / Save
    # ------------------------------------------------------------------

    def load_config(self, config_path: Path) -> bool:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
            if loaded:
                self._merge_config(self.config_data, loaded)
            self.config_path = config_path
            return True
        except Exception as e:
            print(f"Error loading config {config_path}: {e}")
            return False

    def save_config(self, config_data: Dict, config_path: Path) -> bool:
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            out = config_data.copy()
            out["_metadata"] = {
                "ham_version": HAM_VERSION,
                "created": datetime.now().isoformat(),
                "last_modified": datetime.now().isoformat(),
            }
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(out, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            self.config_data = out
            self.config_path = config_path
            return True
        except Exception as e:
            print(f"Error saving config {config_path}: {e}")
            return False

    # ------------------------------------------------------------------
    # Dot-notation get / set
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        try:
            cur = self.config_data
            for part in key.split("."):
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                else:
                    return default
            return cur
        except Exception:
            return default

    def set(self, key: str, value: Any) -> bool:
        try:
            parts = key.split(".")
            cur = self.config_data
            for part in parts[:-1]:
                if part not in cur:
                    cur[part] = {}
                cur = cur[part]
            cur[parts[-1]] = value
            if "_metadata" in self.config_data:
                self.config_data["_metadata"]["last_modified"] = datetime.now().isoformat()
            return True
        except Exception as e:
            print(f"Error setting config key '{key}': {e}")
            return False

    # ------------------------------------------------------------------
    # Step status helpers
    # ------------------------------------------------------------------

    def update_step_status(self, step_num: int, completed: bool) -> bool:
        return self.set(f"steps_completed.step{step_num}", completed)

    def get_step_status(self, step_num: int) -> bool:
        return self.get(f"steps_completed.step{step_num}", False)

    def get_next_step(self) -> Optional[int]:
        for n in range(1, 6):
            if not self.get_step_status(n):
                return n
        return None

    def get_completed_steps(self) -> List[int]:
        return [n for n in range(1, 6) if self.get_step_status(n)]

    def get_progress(self) -> str:
        done = len(self.get_completed_steps())
        return f"{done}/5"

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_config(self):
        errors = []
        for field in ["project.name", "project.data_directory"]:
            if not self.get(field):
                errors.append(f"Missing required field: {field}")
        data_dir = self.get("project.data_directory")
        if data_dir and not Path(data_dir).exists():
            errors.append(f"Data directory does not exist: {data_dir}")
        return len(errors) == 0, errors

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _merge_config(self, base: Dict, overlay: Dict):
        for k, v in overlay.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                self._merge_config(base[k], v)
            else:
                base[k] = v

    def to_dict(self) -> Dict:
        return self.config_data.copy()

    def __str__(self):
        return f"ConfigManager({self.config_path})"
