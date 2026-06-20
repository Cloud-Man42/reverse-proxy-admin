from typing import Callable, List

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.api_token import ApiToken
from app.services.api_token_service import ApiTokenService

bearer_scheme = HTTPBearer(auto_error=False)


async def get_api_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> ApiToken:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = ApiTokenService(db).validate_hash(credentials.credentials)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    ApiTokenService(db).update_last_used(token)
    request.state.api_token = token
    return token


def require_api_scopes(*scopes: str) -> Callable:
    async def checker(token: ApiToken = Depends(get_api_token)) -> ApiToken:
        if token.has_scope("admin"):
            return token
        for scope in scopes:
            if not token.has_scope(scope):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required scope: {scope}",
                )
        return token

    return checker


def available_scopes() -> List[str]:
    return [
        "admin",
        "proxies:read",
        "proxies:write",
        "backend_pools:read",
        "backend_pools:write",
        "certificates:read",
        "certificates:write",
        "health:read",
        "health:write",
        "analytics:read",
        "system:read",
        "system:write",
        "audit:read",
    ]
