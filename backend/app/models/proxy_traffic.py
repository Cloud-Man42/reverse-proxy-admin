from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ProxyTrafficAggregate(Base):
    __tablename__ = "proxy_traffic_aggregates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proxy_id: Mapped[str] = mapped_column(String(128), index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime, index=True)
    period_end: Mapped[datetime] = mapped_column(DateTime)
    period_type: Mapped[str] = mapped_column(String(16), default="hour")
    requests: Mapped[int] = mapped_column(Integer, default=0)
    bytes_in: Mapped[int] = mapped_column(Integer, default=0)
    bytes_out: Mapped[int] = mapped_column(Integer, default=0)
    upstream_bytes_in: Mapped[int] = mapped_column(Integer, default=0)
    upstream_bytes_out: Mapped[int] = mapped_column(Integer, default=0)
    latency_avg_ms: Mapped[float] = mapped_column(Float, default=0.0)
    upstream_latency_avg_ms: Mapped[float] = mapped_column(Float, default=0.0)
    status_2xx: Mapped[int] = mapped_column(Integer, default=0)
    status_3xx: Mapped[int] = mapped_column(Integer, default=0)
    status_4xx: Mapped[int] = mapped_column(Integer, default=0)
    status_5xx: Mapped[int] = mapped_column(Integer, default=0)
    max_response_time_ms: Mapped[float] = mapped_column(Float, default=0.0)
    status_codes_json: Mapped[str] = mapped_column(Text, default="{}")
    top_clients_json: Mapped[str] = mapped_column(Text, default="{}")
    top_paths_json: Mapped[str] = mapped_column(Text, default="{}")


class ProxyTrafficLogState(Base):
    __tablename__ = "proxy_traffic_log_state"

    proxy_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    byte_offset: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
