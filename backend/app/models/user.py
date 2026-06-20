from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

USER_ROLES = ("super_admin", "tenant_admin", "operator", "read_only")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    perm_read: Mapped[bool] = mapped_column(Boolean, default=True)
    perm_create: Mapped[bool] = mapped_column(Boolean, default=False)
    perm_edit: Mapped[bool] = mapped_column(Boolean, default=False)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    role: Mapped[str] = mapped_column(String(32), default="operator")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def is_super_admin(self) -> bool:
        return self.role == "super_admin"

    def is_tenant_admin(self) -> bool:
        return self.role == "tenant_admin" or (self.is_admin and self.role not in ("super_admin", "read_only"))

    def has_read(self) -> bool:
        if self.role == "read_only":
            return True
        return self.is_admin or self.perm_read or self.role in USER_ROLES

    def has_create(self) -> bool:
        if self.role == "read_only":
            return False
        if self.role in ("super_admin", "tenant_admin", "operator"):
            return True
        return self.is_admin or self.perm_create

    def has_edit(self) -> bool:
        if self.role == "read_only":
            return False
        if self.role in ("super_admin", "tenant_admin", "operator"):
            return True
        return self.is_admin or self.perm_edit

    def permissions_dict(self) -> dict:
        return {
            "is_admin": self.is_admin or self.role in ("super_admin", "tenant_admin"),
            "read": self.has_read(),
            "create": self.has_create(),
            "edit": self.has_edit(),
        }
