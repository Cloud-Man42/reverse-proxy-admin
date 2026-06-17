from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def has_read(self) -> bool:
        return self.is_admin or self.perm_read

    def has_create(self) -> bool:
        return self.is_admin or self.perm_create

    def has_edit(self) -> bool:
        return self.is_admin or self.perm_edit

    def permissions_dict(self) -> dict:
        return {
            "is_admin": self.is_admin,
            "read": self.has_read(),
            "create": self.has_create(),
            "edit": self.has_edit(),
        }
