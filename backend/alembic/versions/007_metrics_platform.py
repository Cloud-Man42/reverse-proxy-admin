"""metrics platform tables and traffic aggregate extensions

Revision ID: 007_metrics_platform
Revises: 006_smtp_default_recipient
Create Date: 2026-06-20
"""

from alembic import op
import sqlalchemy as sa

revision = "007_metrics_platform"
down_revision = "006_smtp_default_recipient"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "proxy_traffic_aggregates",
        sa.Column("max_response_time_ms", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "proxy_traffic_aggregates",
        sa.Column("status_codes_json", sa.Text(), nullable=False, server_default="{}"),
    )

    op.create_table(
        "backend_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("backend_server_id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("response_time_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_connections", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_backend_metrics_backend_server_id", "backend_metrics", ["backend_server_id"])
    op.create_index("ix_backend_metrics_timestamp", "backend_metrics", ["timestamp"])

    op.create_table(
        "connection_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("active", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reading", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("writing", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("waiting", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accepts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("handled", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("requests", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_connection_metrics_timestamp", "connection_metrics", ["timestamp"])

    op.create_table(
        "request_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("proxy_id", sa.String(length=128), nullable=False),
        sa.Column("client_ip", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("host", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("method", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("uri", sa.String(length=2048), nullable=False, server_default=""),
        sa.Column("status", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("backend_addr", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("response_time_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("upstream_time_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("bytes_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("user_agent", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("is_failed", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("error_hint", sa.Text(), nullable=True),
        sa.Column("error_log_snippet", sa.Text(), nullable=True),
    )
    op.create_index("ix_request_events_timestamp", "request_events", ["timestamp"])
    op.create_index("ix_request_events_proxy_id", "request_events", ["proxy_id"])

    op.create_table(
        "metric_alert_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="warning"),
        sa.Column("metric_type", sa.String(length=64), nullable=False),
        sa.Column("condition", sa.String(length=32), nullable=False, server_default="gt"),
        sa.Column("threshold", sa.Float(), nullable=False, server_default="0"),
        sa.Column("window_minutes", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("proxy_id", sa.String(length=128), nullable=True),
        sa.Column("notify_email", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "metric_alert_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rule_id", sa.Integer(), nullable=True),
        sa.Column("alert_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="warning"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="fired"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_metric_alert_history_rule_id", "metric_alert_history", ["rule_id"])
    op.create_index("ix_metric_alert_history_alert_type", "metric_alert_history", ["alert_type"])
    op.create_index("ix_metric_alert_history_created_at", "metric_alert_history", ["created_at"])

    op.create_table(
        "metrics_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("raw_retention_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("minute_retention_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("hour_retention_days", sa.Integer(), nullable=False, server_default="180"),
        sa.Column(
            "stub_status_url",
            sa.String(length=255),
            nullable=False,
            server_default="http://127.0.0.1:8081/nginx_status",
        ),
        sa.Column("enhanced_logging_default", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("request_event_sample_rate", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("metrics_settings")
    op.drop_table("metric_alert_history")
    op.drop_table("metric_alert_rules")
    op.drop_table("request_events")
    op.drop_table("connection_metrics")
    op.drop_table("backend_metrics")
    op.drop_column("proxy_traffic_aggregates", "status_codes_json")
    op.drop_column("proxy_traffic_aggregates", "max_response_time_ms")
