"""proxy traffic stats and status report settings

Revision ID: 002_proxy_traffic_status_reports
Revises: 001_enterprise_features
Create Date: 2026-06-17
"""

from alembic import op
import sqlalchemy as sa

revision = "002_proxy_traffic_status_reports"
down_revision = "001_enterprise_features"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "proxy_traffic_aggregates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("proxy_id", sa.String(length=128), nullable=False),
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("period_end", sa.DateTime(), nullable=False),
        sa.Column("period_type", sa.String(length=16), nullable=False, server_default="hour"),
        sa.Column("requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bytes_in", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bytes_out", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("upstream_bytes_in", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("upstream_bytes_out", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_proxy_traffic_aggregates_proxy_id", "proxy_traffic_aggregates", ["proxy_id"])
    op.create_index("ix_proxy_traffic_aggregates_period_start", "proxy_traffic_aggregates", ["period_start"])

    op.create_table(
        "proxy_traffic_log_state",
        sa.Column("proxy_id", sa.String(length=128), primary_key=True),
        sa.Column("byte_offset", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "status_report_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("interval_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("enabled_sections", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("last_sent_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("status_report_settings")
    op.drop_table("proxy_traffic_log_state")
    op.drop_index("ix_proxy_traffic_aggregates_period_start", table_name="proxy_traffic_aggregates")
    op.drop_index("ix_proxy_traffic_aggregates_proxy_id", table_name="proxy_traffic_aggregates")
    op.drop_table("proxy_traffic_aggregates")
