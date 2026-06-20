from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.user import User
from app.schemas import MessageResponse, OrganizationCreate, OrganizationResponse, OrganizationUpdate
from app.security.ip_allowlist import _client_ip
from app.security.tenant_context import require_super_admin
from app.services.audit_service import log_audit
from app.services.organization_service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("", response_model=List[OrganizationResponse])
async def list_organizations(
    db: Session = Depends(get_db),
    _user: User = Depends(require_super_admin),
) -> List[OrganizationResponse]:
    return OrganizationService(db).list_organizations()


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_super_admin),
) -> OrganizationResponse:
    try:
        org = OrganizationService(db).create_organization(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    log_audit(
        db,
        username=user.username,
        action="organization_create",
        resource=f"organization:{org.id}",
        client_ip=_client_ip(request),
        new_value=payload.model_dump(),
        user=user,
    )
    return org


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_super_admin),
) -> OrganizationResponse:
    org = OrganizationService(db).get_organization(organization_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return org


@router.put("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: int,
    payload: OrganizationUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_super_admin),
) -> OrganizationResponse:
    service = OrganizationService(db)
    existing = service.get_organization(organization_id)
    try:
        org = service.update_organization(organization_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    log_audit(
        db,
        username=user.username,
        action="organization_update",
        resource=f"organization:{organization_id}",
        client_ip=_client_ip(request),
        old_value=existing.model_dump() if existing else None,
        new_value=payload.model_dump(exclude_unset=True),
        user=user,
    )
    return org


@router.delete("/{organization_id}", response_model=MessageResponse)
async def delete_organization(
    organization_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_super_admin),
) -> MessageResponse:
    service = OrganizationService(db)
    existing = service.get_organization(organization_id)
    try:
        if not service.delete_organization(organization_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    log_audit(
        db,
        username=user.username,
        action="organization_delete",
        resource=f"organization:{organization_id}",
        client_ip=_client_ip(request),
        old_value=existing.model_dump() if existing else None,
        user=user,
    )
    return MessageResponse(message="Organization deleted")
