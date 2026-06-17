from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.config import Settings, get_settings
from app.models.user import User
from app.schemas import LogLinesResponse
from app.security.permissions import Permission, require_permission
from app.services.log_reader import LogReader

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/error", response_model=LogLinesResponse)
async def get_error_logs(
    lines: int = Query(default=200, ge=1, le=2000),
    settings: Settings = Depends(get_settings),
    _user: User = Depends(require_permission(Permission.READ)),
) -> LogLinesResponse:
    reader = LogReader(settings)
    return LogLinesResponse(lines=reader.read_error_log(lines=lines), source=str(settings.nginx_error_log))


@router.get("/access", response_model=LogLinesResponse)
async def get_access_logs(
    lines: int = Query(default=200, ge=1, le=2000),
    domain: Optional[str] = Query(default=None),
    settings: Settings = Depends(get_settings),
    _user: User = Depends(require_permission(Permission.READ)),
) -> LogLinesResponse:
    reader = LogReader(settings)
    return LogLinesResponse(
        lines=reader.read_access_log(lines=lines, domain=domain),
        source=str(settings.nginx_access_log),
    )
