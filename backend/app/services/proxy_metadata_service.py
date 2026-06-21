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

    def _read(self, proxy_id: str) -> dict:
        path = self._path(proxy_id)
        ensure_path_allowed(path, self.settings.allowed_read_paths())
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _write(self, proxy_id: str, data: dict) -> None:
        path = self._path(proxy_id)
        ensure_path_allowed(path, self.settings.allowed_write_paths())
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def get_notes(self, proxy_id: str) -> str | None:
        notes = self._read(proxy_id).get("notes")
        return notes if isinstance(notes, str) and notes.strip() else None

    def set_notes(self, proxy_id: str, notes: str | None) -> None:
        data = self._read(proxy_id)
        data["notes"] = notes.strip() if notes else ""
        self._write(proxy_id, data)

    def get_enhanced_analytics_logging(self, proxy_id: str) -> bool:
        return bool(self._read(proxy_id).get("enhanced_analytics_logging"))

    def set_enhanced_analytics_logging(self, proxy_id: str, enabled: bool) -> None:
        data = self._read(proxy_id)
        data["enhanced_analytics_logging"] = enabled
        self._write(proxy_id, data)

    def delete(self, proxy_id: str) -> None:
        path = self._path(proxy_id)
        if path.exists():
            path.unlink(missing_ok=True)
