from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.user import User
from app.schemas import MessageResponse, UserCreate, UserResponse, UserUpdate
from app.security.auth import get_current_user
from app.security.ip_allowlist import _client_ip
from app.security.permissions import require_admin
from app.services.audit_service import log_audit
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def _to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        is_active=user.is_active,
        is_admin=user.is_admin,
        perm_read=user.perm_read,
        perm_create=user.perm_create,
        perm_edit=user.perm_edit,
        created_at=user.created_at,
    )


@router.get("", response_model=List[UserResponse])
async def list_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> List[UserResponse]:
    return [_to_response(user) for user in UserService(db).list_users()]


@router.post("", response_model=UserResponse)
async def create_user(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> UserResponse:
    user = UserService(db).create_user(payload)
    log_audit(
        db,
        username=admin.username,
        action="create_user",
        resource=user.username,
        client_ip=_client_ip(request),
        new_value=payload.model_dump(exclude={"password"}),
    )
    return _to_response(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> UserResponse:
    old = UserService(db).get_user(user_id)
    user = UserService(db).update_user(user_id, payload, admin)
    log_audit(
        db,
        username=admin.username,
        action="update_user",
        resource=str(user_id),
        client_ip=_client_ip(request),
        old_value=_to_response(old).model_dump() if old else None,
        new_value=payload.model_dump(exclude={"password"}),
    )
    return _to_response(user)


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> MessageResponse:
    old = UserService(db).get_user(user_id)
    UserService(db).delete_user(user_id, admin)
    log_audit(
        db,
        username=admin.username,
        action="delete_user",
        resource=str(user_id),
        client_ip=_client_ip(request),
        old_value=_to_response(old).model_dump() if old else None,
    )
    return MessageResponse(message="User deleted")
