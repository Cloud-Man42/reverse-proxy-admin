from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class BackendMetric(Base):
    __tablename__ = "backend_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    backend_server_id: Mapped[int] = mapped_column(Integer, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(32), default="unknown")
    response_time_ms: Mapped[float] = mapped_column(Float, default=0.0)
    requests: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[int] = mapped_column(Integer, default=0)
    active_connections: Mapped[int] = mapped_column(Integer, default=0)


class ConnectionMetric(Base):
    __tablename__ = "connection_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    active: Mapped[int] = mapped_column(Integer, default=0)
    reading: Mapped[int] = mapped_column(Integer, default=0)
    writing: Mapped[int] = mapped_column(Integer, default=0)
    waiting: Mapped[int] = mapped_column(Integer, default=0)
    accepts: Mapped[int] = mapped_column(Integer, default=0)
    handled: Mapped[int] = mapped_column(Integer, default=0)
    requests: Mapped[int] = mapped_column(Integer, default=0)


class RequestEvent(Base):
    __tablename__ = "request_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    proxy_id: Mapped[str] = mapped_column(String(128), index=True)
    client_ip: Mapped[str] = mapped_column(String(64), default="")
    host: Mapped[str] = mapped_column(String(255), default="")
    method: Mapped[str] = mapped_column(String(16), default="")
    uri: Mapped[str] = mapped_column(String(2048), default="")
    status: Mapped[int] = mapped_column(Integer, default=0)
    backend_addr: Mapped[str] = mapped_column(String(255), default="")
    response_time_ms: Mapped[float] = mapped_column(Float, default=0.0)
    upstream_time_ms: Mapped[float] = mapped_column(Float, default=0.0)
    bytes_sent: Mapped[int] = mapped_column(Integer, default=0)
    user_agent: Mapped[str] = mapped_column(String(512), default="")
    is_failed: Mapped[bool] = mapped_column(Boolean, default=False)
    error_hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_log_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)


class MetricAlertRule(Base):
    __tablename__ = "metric_alert_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    severity: Mapped[str] = mapped_column(String(32), default="warning")
    metric_type: Mapped[str] = mapped_column(String(64))
    condition: Mapped[str] = mapped_column(String(32), default="gt")
    threshold: Mapped[float] = mapped_column(Float, default=0.0)
    window_minutes: Mapped[int] = mapped_column(Integer, default=5)
    proxy_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notify_email: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class MetricAlertHistory(Base):
    __tablename__ = "metric_alert_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    alert_type: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[str] = mapped_column(String(32), default="warning")
    status: Mapped[str] = mapped_column(String(16), default="fired")
    message: Mapped[str] = mapped_column(Text)
    metric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class MetricsSettings(Base):
    __tablename__ = "metrics_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_retention_days: Mapped[int] = mapped_column(Integer, default=7)
    minute_retention_days: Mapped[int] = mapped_column(Integer, default=30)
    hour_retention_days: Mapped[int] = mapped_column(Integer, default=180)
    stub_status_url: Mapped[str] = mapped_column(
        String(255), default="http://127.0.0.1:8081/nginx_status"
    )
    enhanced_logging_default: Mapped[bool] = mapped_column(Boolean, default=False)
    request_event_sample_rate: Mapped[int] = mapped_column(Integer, default=100)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
