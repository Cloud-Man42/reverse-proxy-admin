from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class BackendServer(Base):
    __tablename__ = "backend_servers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pool_id: Mapped[int] = mapped_column(ForeignKey("backend_pools.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    protocol: Mapped[str] = mapped_column(String(8), default="http")
    weight: Mapped[int] = mapped_column(Integer, default=1)
    role: Mapped[str] = mapped_column(String(16), default="primary")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    health_check_type: Mapped[str] = mapped_column(String(16), default="tcp")
    health_check_path: Mapped[str] = mapped_column(String(255), default="/")
    health_status: Mapped[str] = mapped_column(String(16), default="unknown")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    pool: Mapped["BackendPool"] = relationship("BackendPool", back_populates="servers")
    health_results: Mapped[list["HealthCheckResult"]] = relationship(
        "HealthCheckResult", back_populates="server", cascade="all, delete-orphan"
    )
