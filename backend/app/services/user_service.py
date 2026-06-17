from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas import UserCreate, UserUpdate
from app.security.auth import hash_password


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_users(self) -> List[User]:
        return self.db.query(User).order_by(User.username).all()

    def get_user(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def create_user(self, payload: UserCreate) -> User:
        if self.db.query(User).filter(User.username == payload.username).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
        user = User(
            username=payload.username,
            password_hash=hash_password(payload.password),
            is_active=payload.is_active,
            is_admin=payload.is_admin,
            perm_read=payload.perm_read if not payload.is_admin else True,
            perm_create=payload.perm_create if not payload.is_admin else True,
            perm_edit=payload.perm_edit if not payload.is_admin else True,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user(self, user_id: int, payload: UserUpdate, actor: User) -> User:
        user = self.get_user(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if payload.username and payload.username != user.username:
            if self.db.query(User).filter(User.username == payload.username).first():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
            user.username = payload.username

        if payload.password:
            user.password_hash = hash_password(payload.password)
        if payload.is_active is not None:
            user.is_active = payload.is_active
        if payload.is_admin is not None:
            if user.is_admin and not payload.is_admin:
                self._ensure_not_last_admin(user)
            user.is_admin = payload.is_admin
        if payload.perm_read is not None:
            user.perm_read = payload.perm_read
        if payload.perm_create is not None:
            user.perm_create = payload.perm_create
        if payload.perm_edit is not None:
            user.perm_edit = payload.perm_edit

        if user.is_admin:
            user.perm_read = True
            user.perm_create = True
            user.perm_edit = True

        if user.id == actor.id and not user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate your own account")

        self.db.commit()
        self.db.refresh(user)
        return user

    def delete_user(self, user_id: int, actor: User) -> None:
        user = self.get_user(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if user.id == actor.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account")
        if user.is_admin:
            self._ensure_not_last_admin(user)
        self.db.delete(user)
        self.db.commit()

    def _ensure_not_last_admin(self, user: User) -> None:
        admin_count = self.db.query(User).filter(User.is_admin.is_(True), User.is_active.is_(True)).count()
        if user.is_admin and admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last active admin user",
            )
