"""Enterprise features initial schema

Revision ID: 001_enterprise
Revises:
Create Date: 2026-06-18

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_enterprise"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "backend_pools",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("proxy_id", sa.String(length=64), nullable=True),
        sa.Column("route_path", sa.String(length=255), nullable=False),
        sa.Column("load_balancing_method", sa.String(length=32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_backend_pools_name", "backend_pools", ["name"], unique=True)
    op.create_index("ix_backend_pools_proxy_id", "backend_pools", ["proxy_id"], unique=False)

    op.create_table(
        "backend_servers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pool_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("protocol", sa.String(length=8), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("health_check_type", sa.String(length=16), nullable=False),
        sa.Column("health_check_path", sa.String(length=255), nullable=False),
        sa.Column("health_status", sa.String(length=16), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["pool_id"], ["backend_pools.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_backend_servers_pool_id", "backend_servers", ["pool_id"], unique=False)

    op.create_table(
        "health_check_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("response_ms", sa.Float(), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("checked_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["server_id"], ["backend_servers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_health_check_results_server_id", "health_check_results", ["server_id"])
    op.create_index("ix_health_check_results_checked_at", "health_check_results", ["checked_at"])

    op.create_table(
        "health_check_aggregates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("period_end", sa.DateTime(), nullable=False),
        sa.Column("period_type", sa.String(length=8), nullable=False),
        sa.Column("total_checks", sa.Integer(), nullable=False),
        sa.Column("healthy_checks", sa.Integer(), nullable=False),
        sa.Column("uptime_percent", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["server_id"], ["backend_servers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_health_check_aggregates_server_id", "health_check_aggregates", ["server_id"])
    op.create_index("ix_health_check_aggregates_period_start", "health_check_aggregates", ["period_start"])

    op.create_table(
        "smtp_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("password_encrypted", sa.Text(), nullable=True),
        sa.Column("tls_enabled", sa.Boolean(), nullable=False),
        sa.Column("ssl_enabled", sa.Boolean(), nullable=False),
        sa.Column("sender_name", sa.String(length=255), nullable=False),
        sa.Column("sender_email", sa.String(length=255), nullable=False),
        sa.Column("last_test_status", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "notification_recipients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recipient_id", sa.Integer(), nullable=False),
        sa.Column("email_enabled", sa.Boolean(), nullable=False),
        sa.Column("critical_only", sa.Boolean(), nullable=False),
        sa.Column("all_notifications", sa.Boolean(), nullable=False),
        sa.Column("enabled_types", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["recipient_id"], ["notification_recipients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recipient_id"),
    )

    op.create_table(
        "notification_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("recipient_email", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_log_event_type", "notification_log", ["event_type"])
    op.create_index("ix_notification_log_dedupe_key", "notification_log", ["dedupe_key"])
    op.create_index("ix_notification_log_created_at", "notification_log", ["created_at"])

    op.create_table(
        "system_alert_thresholds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cpu_percent", sa.Float(), nullable=False),
        sa.Column("ram_percent", sa.Float(), nullable=False),
        sa.Column("disk_percent", sa.Float(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "system_alert_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alert_type", sa.String(length=64), nullable=False),
        sa.Column("metric", sa.String(length=32), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_system_alert_history_alert_type", "system_alert_history", ["alert_type"])
    op.create_index("ix_system_alert_history_created_at", "system_alert_history", ["created_at"])


def downgrade() -> None:
    op.drop_table("system_alert_history")
    op.drop_table("system_alert_thresholds")
    op.drop_table("notification_log")
    op.drop_table("notification_preferences")
    op.drop_table("notification_recipients")
    op.drop_table("smtp_settings")
    op.drop_table("health_check_aggregates")
    op.drop_table("health_check_results")
    op.drop_table("backend_servers")
    op.drop_table("backend_pools")
