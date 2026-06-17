from enum import Enum
from typing import Callable

from fastapi import Depends, HTTPException, status

from app.models.user import User
from app.security.auth import get_current_user


class Permission(str, Enum):
    READ = "read"
    CREATE = "create"
    EDIT = "edit"


def require_permission(permission: Permission) -> Callable:
    async def checker(user: User = Depends(get_current_user)) -> User:
        allowed = {
            Permission.READ: user.has_read(),
            Permission.CREATE: user.has_create(),
            Permission.EDIT: user.has_edit(),
        }[permission]
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value}",
            )
        return user

    return checker


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
