from typing import Optional

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class IpAccessRule(Base):
    __tablename__ = "ip_access_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    proxy_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    rule_type: Mapped[str] = mapped_column(String(16), nullable=False)
    cidr: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
