"""
Batch Registry for HAM.

Central YAML registry at <framework_root>/config/batch_registry.yaml that
tracks all batch projects across sessions.
"""

import uuid
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


_REGISTRY_FILENAME = "batch_registry.yaml"


class BatchRegistry:
    """Centralized registry for tracking HAM batch projects."""

    STATUS_ACTIVE = "active"
    STATUS_COMPLETED = "completed"
    STATUS_ARCHIVED = "archived"

    def __init__(self, framework_root: Optional[Path] = None):
        if framework_root is None:
            framework_root = Path(__file__).parent.parent
        self.registry_path = Path(framework_root) / "config" / _REGISTRY_FILENAME
        self.batches: Dict[str, dict] = self._load_registry()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def register_batch(self, name: str, data_dir: str, config_path: str) -> Optional[str]:
        """Register a new batch. Returns batch_id or None on failure."""
        batch_id = str(uuid.uuid4())[:8]
        self.batches[batch_id] = {
            "name": name,
            "data_directory": str(data_dir),
            "config_path": str(config_path),
            "status": self.STATUS_ACTIVE,
            "created": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "steps_completed": {f"step{i}": False for i in range(1, 6)},
        }
        return batch_id if self._save_registry() else None

    def unregister_batch(self, batch_id: str) -> bool:
        if batch_id not in self.batches:
            return False
        del self.batches[batch_id]
        return self._save_registry()

    def get_batch(self, batch_id: str) -> Optional[dict]:
        return self.batches.get(batch_id)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_batches_summary(self) -> List[dict]:
        result = []
        for bid, info in self.batches.items():
            done = sum(1 for v in info.get("steps_completed", {}).values() if v)
            result.append({
                "id": bid,
                "name": info.get("name", ""),
                "status": info.get("status", self.STATUS_ACTIVE),
                "data_directory": info.get("data_directory", ""),
                "config_path": info.get("config_path", ""),
                "progress": f"{done}/5",
                "created": info.get("created", ""),
                "last_accessed": info.get("last_accessed", ""),
            })
        return result

    def get_active_batches(self) -> Dict[str, dict]:
        return {bid: info for bid, info in self.batches.items()
                if info.get("status") == self.STATUS_ACTIVE}

    def find_batch_by_name(self, name: str) -> Optional[Tuple[str, dict]]:
        for bid, info in self.batches.items():
            if info.get("name") == name:
                return bid, info
        return None

    def find_batch_by_config(self, config_path: str) -> Optional[Tuple[str, dict]]:
        for bid, info in self.batches.items():
            if info.get("config_path") == config_path:
                return bid, info
        return None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def update_batch_status(self, batch_id: str, status: str) -> bool:
        if batch_id not in self.batches:
            return False
        self.batches[batch_id]["status"] = status
        return self._save_registry()

    def update_last_accessed(self, batch_id: str) -> bool:
        if batch_id not in self.batches:
            return False
        self.batches[batch_id]["last_accessed"] = datetime.now().isoformat()
        return self._save_registry()

    def update_step_status(self, batch_id: str, step_num: int, completed: bool) -> bool:
        if batch_id not in self.batches:
            return False
        self.batches[batch_id].setdefault("steps_completed", {})[f"step{step_num}"] = completed
        return self._save_registry()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_registry(self) -> Dict[str, dict]:
        if not self.registry_path.exists():
            return {}
        try:
            with open(self.registry_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return data.get("batches", {})
        except Exception as e:
            print(f"[BatchRegistry] Error loading registry: {e}")
            return {}

    def _save_registry(self) -> bool:
        try:
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.registry_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    {"batches": self.batches, "_updated": datetime.now().isoformat()},
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )
            return True
        except Exception as e:
            print(f"[BatchRegistry] Error saving registry: {e}")
            return False

    def reload(self):
        self.batches = self._load_registry()
