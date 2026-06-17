from pathlib import Path
from typing import Iterable

from fastapi import HTTPException, status


def ensure_path_allowed(path: Path, allowed_roots: Iterable[Path], for_write: bool = False) -> Path:
    resolved = path.resolve()
    for root in allowed_roots:
        root_resolved = root.resolve()
        try:
            resolved.relative_to(root_resolved)
            return resolved
        except ValueError:
            continue
    action = "write" if for_write else "read"
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Path not allowed for {action}: {path}",
    )


def safe_join(base: Path, *parts: str, allowed_roots: Iterable[Path], for_write: bool = False) -> Path:
    candidate = (base.joinpath(*parts)).resolve()
    return ensure_path_allowed(candidate, allowed_roots, for_write=for_write)
