from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ProxyRateLimit(Base):
    __tablename__ = "proxy_rate_limits"

    proxy_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    requests_per_minute: Mapped[int] = mapped_column(Integer, default=60)
    burst: Mapped[int] = mapped_column(Integer, default=20)
    nodelay: Mapped[bool] = mapped_column(Boolean, default=True)
    key_type: Mapped[str] = mapped_column(String(32), default="client_ip")
