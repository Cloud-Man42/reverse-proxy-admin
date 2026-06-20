from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models.api_token import ApiToken
from app.schemas import AnalyticsProxyResponse, AnalyticsSummaryResponse
from app.security.api_token_auth import require_api_scopes
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics")


def get_service(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> AnalyticsService:
    return AnalyticsService(settings, db)


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def analytics_summary(
    range: str = Query(default="24h", pattern="^(24h|7d|30d)$"),
    service: AnalyticsService = Depends(get_service),
    _token: ApiToken = Depends(require_api_scopes("analytics:read")),
) -> AnalyticsSummaryResponse:
    return service.get_summary(range)


@router.get("/proxy-hosts/{proxy_id}", response_model=AnalyticsProxyResponse)
async def proxy_analytics(
    proxy_id: str,
    range: str = Query(default="24h", pattern="^(24h|7d|30d)$"),
    service: AnalyticsService = Depends(get_service),
    _token: ApiToken = Depends(require_api_scopes("analytics:read")),
) -> AnalyticsProxyResponse:
    result = service.get_proxy_analytics(proxy_id, range)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proxy not found")
    return result
