from typing import List

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.api_token import ApiToken
from app.models.user import User
from app.schemas import (
    ApiTokenCreate,
    ApiTokenCreatedResponse,
    ApiTokenResponse,
    ApiTokenScopesResponse,
    ApiTokenUpdate,
    MessageResponse,
)
from app.security.api_token_auth import available_scopes
from app.security.ip_allowlist import _client_ip
from app.security.permissions import require_admin
from app.services.api_token_service import ApiTokenService
from app.services.audit_service import log_audit

router = APIRouter(prefix="/api-tokens", tags=["api-tokens"])


def _to_response(token: ApiToken) -> ApiTokenResponse:
    return ApiTokenResponse(
        id=token.id,
        name=token.name,
        token_prefix=token.token_prefix,
        scopes=token.scopes,
        expires_at=token.expires_at,
        last_used_at=token.last_used_at,
        revoked=token.revoked,
        created_at=token.created_at,
    )


@router.get("/scopes", response_model=ApiTokenScopesResponse)
async def list_scopes(_admin: User = Depends(require_admin)) -> ApiTokenScopesResponse:
    return ApiTokenScopesResponse(scopes=available_scopes())


@router.get("", response_model=List[ApiTokenResponse])
async def list_api_tokens(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> List[ApiTokenResponse]:
    return [_to_response(token) for token in ApiTokenService(db).list_tokens()]


@router.get("/{token_id}", response_model=ApiTokenResponse)
async def get_api_token(
    token_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> ApiTokenResponse:
    token = ApiTokenService(db).get_token(token_id)
    if not token:
        from fastapi import HTTPException

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
    return _to_response(token)


@router.post("", response_model=ApiTokenCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_token(
    payload: ApiTokenCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> ApiTokenCreatedResponse:
    token, plain = ApiTokenService(db).create(payload)
    log_audit(
        db,
        username=admin.username,
        action="create_api_token",
        resource=str(token.id),
        client_ip=_client_ip(request),
        new_value={"name": payload.name, "scopes": payload.scopes},
    )
    response = _to_response(token)
    return ApiTokenCreatedResponse(**response.model_dump(), token=plain)


@router.put("/{token_id}", response_model=ApiTokenResponse)
async def update_api_token(
    token_id: int,
    payload: ApiTokenUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> ApiTokenResponse:
    old = ApiTokenService(db).get_token(token_id)
    token = ApiTokenService(db).update(token_id, payload)
    log_audit(
        db,
        username=admin.username,
        action="update_api_token",
        resource=str(token_id),
        client_ip=_client_ip(request),
        old_value=_to_response(old).model_dump() if old else None,
        new_value=payload.model_dump(exclude_unset=True),
    )
    return _to_response(token)


@router.delete("/{token_id}", response_model=MessageResponse)
async def revoke_api_token(
    token_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> MessageResponse:
    old = ApiTokenService(db).get_token(token_id)
    ApiTokenService(db).revoke(token_id)
    log_audit(
        db,
        username=admin.username,
        action="revoke_api_token",
        resource=str(token_id),
        client_ip=_client_ip(request),
        old_value=_to_response(old).model_dump() if old else None,
    )
    return MessageResponse(message="API token revoked")
