import json
from pathlib import Path

from app.config import Settings
from app.services.path_guard import ensure_path_allowed


class ProxyMetadataService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.meta_dir = settings.data_dir / "proxy-meta"
        self.meta_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, proxy_id: str) -> Path:
        safe_id = proxy_id.replace("/", "_").replace("\\", "_")
        return self.meta_dir / f"{safe_id}.json"

    def get_notes(self, proxy_id: str) -> str | None:
        path = self._path(proxy_id)
        ensure_path_allowed(path, self.settings.allowed_read_paths())
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        notes = data.get("notes")
        return notes if isinstance(notes, str) and notes.strip() else None

    def set_notes(self, proxy_id: str, notes: str | None) -> None:
        path = self._path(proxy_id)
        ensure_path_allowed(path, self.settings.allowed_write_paths())
        payload = {"notes": notes.strip() if notes else ""}
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def delete(self, proxy_id: str) -> None:
        path = self._path(proxy_id)
        if path.exists():
            path.unlink(missing_ok=True)
