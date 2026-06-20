from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models.api_token import ApiToken
from app.schemas import HealthCheckDashboard, HealthCheckResultResponse, HealthHistoryPoint
from app.security.api_token_auth import require_api_scopes
from app.services.health_check_service import HealthCheckService

router = APIRouter(prefix="/health")


def get_service(settings: Settings = Depends(get_settings), db: Session = Depends(get_db)) -> HealthCheckService:
    return HealthCheckService(settings, db)


@router.get("", response_model=list[HealthCheckResultResponse])
async def list_health_checks(
    server_id: Optional[int] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: HealthCheckService = Depends(get_service),
    _token: ApiToken = Depends(require_api_scopes("health:read")),
) -> list[HealthCheckResultResponse]:
    items, _ = service.list_results(server_id=server_id, status=status, page=page, page_size=page_size)
    return items


@router.get("/dashboard", response_model=HealthCheckDashboard)
async def health_dashboard(
    service: HealthCheckService = Depends(get_service),
    _token: ApiToken = Depends(require_api_scopes("health:read")),
) -> HealthCheckDashboard:
    return service.get_dashboard()


@router.get("/servers/{server_id}/history", response_model=list[HealthHistoryPoint])
async def health_history(
    server_id: int,
    range: str = Query("24h", pattern="^(24h|7d|30d)$"),
    service: HealthCheckService = Depends(get_service),
    _token: ApiToken = Depends(require_api_scopes("health:read")),
) -> list[HealthHistoryPoint]:
    return service.get_history(server_id, range)


@router.post("/servers/{server_id}/run", response_model=HealthCheckResultResponse)
async def run_health_check(
    server_id: int,
    service: HealthCheckService = Depends(get_service),
    _token: ApiToken = Depends(require_api_scopes("health:write")),
) -> HealthCheckResultResponse:
    result = service.run_server(server_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    return result
