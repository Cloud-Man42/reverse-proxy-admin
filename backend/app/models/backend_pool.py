from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class BackendPool(Base):
    __tablename__ = "backend_pools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    proxy_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    route_path: Mapped[str] = mapped_column(String(255), default="/")
    load_balancing_method: Mapped[str] = mapped_column(String(32), default="round_robin")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    servers: Mapped[list["BackendServer"]] = relationship(
        "BackendServer", back_populates="pool", cascade="all, delete-orphan"
    )
