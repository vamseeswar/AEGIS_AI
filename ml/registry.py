"""AEGIS AI — Machine Learning Model Registry & Artifact Store
Serializes and loads trained model pipelines using joblib with tenant storage isolation.
"""

from pathlib import Path
from typing import Any
import joblib

BASE_MODEL_STORAGE = Path("storage/models")


class ModelArtifactRegistry:
    """Handles disk serialization of model instances."""

    def __init__(self, base_dir: Path | str = BASE_MODEL_STORAGE):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_artifact_path(self, org_id: str, model_id: str) -> Path:
        """Constructs tenant-isolated artifact file path."""
        tenant_dir = self.base_dir / org_id
        tenant_dir.mkdir(parents=True, exist_ok=True)
        return tenant_dir / f"{model_id}.joblib"

    def save(self, model_obj: Any, org_id: str, model_id: str) -> str:
        """Persists model artifact to disk."""
        target_path = self.get_artifact_path(org_id, model_id)
        joblib.dump(model_obj, target_path)
        return str(target_path)

    def load(self, artifact_path: str) -> Any:
        """Loads model artifact from disk."""
        path = Path(artifact_path)
        if not path.exists():
            raise FileNotFoundError(f"Model artifact not found at: {artifact_path}")
        return joblib.load(path)

    def delete(self, artifact_path: str) -> bool:
        """Removes model artifact from disk."""
        path = Path(artifact_path)
        if path.exists():
            path.unlink()
            return True
        return False
