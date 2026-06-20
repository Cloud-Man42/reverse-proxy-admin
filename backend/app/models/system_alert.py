from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SystemAlertThreshold(Base):
    __tablename__ = "system_alert_thresholds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cpu_percent: Mapped[float] = mapped_column(Float, default=90.0)
    ram_percent: Mapped[float] = mapped_column(Float, default=90.0)
    disk_percent: Mapped[float] = mapped_column(Float, default=90.0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class SystemAlertHistory(Base):
    __tablename__ = "system_alert_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_type: Mapped[str] = mapped_column(String(64), index=True)
    metric: Mapped[str] = mapped_column(String(32))
    value: Mapped[float] = mapped_column(Float)
    threshold: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16))
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
