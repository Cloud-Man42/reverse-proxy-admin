from collections import deque
from pathlib import Path
from typing import List, Optional

from app.config import Settings
from app.services.path_guard import ensure_path_allowed


class LogReader:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def read_lines(self, path: Path, lines: int = 200) -> List[str]:
        return self._tail(path, lines=lines)

    def _tail(self, path: Path, lines: int = 200) -> List[str]:
        ensure_path_allowed(path, self.settings.allowed_read_paths())
        if not path.exists():
            return []
        try:
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                return list(deque(handle, maxlen=max(lines, 1)))
        except OSError:
            return []

    def read_error_log(self, lines: int = 200) -> List[str]:
        return self._tail(self.settings.nginx_error_log, lines=lines)

    def read_access_log(self, lines: int = 200, domain: Optional[str] = None) -> List[str]:
        entries = self._tail(self.settings.nginx_access_log, lines=max(lines * 5, 500))
        if domain:
            domain = domain.lower()
            entries = [line for line in entries if domain in line.lower()]
        return entries[-lines:]
