from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.branding import APP_NAME
from app.db import Base


class SmtpSettings(Base):
    __tablename__ = "smtp_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    host: Mapped[str] = mapped_column(String(255), default="")
    port: Mapped[int] = mapped_column(Integer, default=587)
    username: Mapped[str] = mapped_column(String(255), default="")
    password_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    tls_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    ssl_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    sender_name: Mapped[str] = mapped_column(String(255), default=APP_NAME)
    sender_email: Mapped[str] = mapped_column(String(255), default="")
    tls_server_name: Mapped[str] = mapped_column(String(255), default="")
    verify_tls_certificate: Mapped[bool] = mapped_column(Boolean, default=True)
    last_test_status: Mapped[str] = mapped_column(String(32), default="unknown")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
