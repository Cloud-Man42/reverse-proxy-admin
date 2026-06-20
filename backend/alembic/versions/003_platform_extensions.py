"""platform extensions: cert renewal log, analytics, rate limits, templates, versioning, tokens, tenants, security

Revision ID: 003_platform_extensions
Revises: 002_proxy_traffic_status_reports
Create Date: 2026-06-20
"""

from alembic import op
import sqlalchemy as sa

revision = "003_platform_extensions"
down_revision = "002_proxy_traffic_status_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "certificate_renewal_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("certificate_name", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_certificate_renewal_log_certificate_name", "certificate_renewal_log", ["certificate_name"])
    op.create_index("ix_certificate_renewal_log_created_at", "certificate_renewal_log", ["created_at"])

    op.add_column("proxy_traffic_aggregates", sa.Column("latency_avg_ms", sa.Float(), server_default="0"))
    op.add_column("proxy_traffic_aggregates", sa.Column("upstream_latency_avg_ms", sa.Float(), server_default="0"))
    op.add_column("proxy_traffic_aggregates", sa.Column("status_2xx", sa.Integer(), server_default="0"))
    op.add_column("proxy_traffic_aggregates", sa.Column("status_3xx", sa.Integer(), server_default="0"))
    op.add_column("proxy_traffic_aggregates", sa.Column("status_4xx", sa.Integer(), server_default="0"))
    op.add_column("proxy_traffic_aggregates", sa.Column("status_5xx", sa.Integer(), server_default="0"))
    op.add_column("proxy_traffic_aggregates", sa.Column("top_clients_json", sa.Text(), server_default="'{}'"))
    op.add_column("proxy_traffic_aggregates", sa.Column("top_paths_json", sa.Text(), server_default="'{}'"))

    op.create_table(
        "proxy_rate_limits",
        sa.Column("proxy_id", sa.String(length=128), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("requests_per_minute", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("burst", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("nodelay", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("key_type", sa.String(length=32), nullable=False, server_default="client_ip"),
    )

    op.create_table(
        "proxy_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=64), unique=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("defaults_json", sa.Text(), nullable=False, server_default="'{}'"),
        sa.Column("builtin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "config_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("resource_type", sa.String(length=32), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.String(length=255), nullable=False),
        sa.Column("old_config", sa.Text(), nullable=True),
        sa.Column("new_config", sa.Text(), nullable=False),
        sa.Column("nginx_test_result", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_config_versions_resource", "config_versions", ["resource_type", "resource_id"])

    op.create_table(
        "api_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("token_hash", sa.String(length=128), unique=True, nullable=False),
        sa.Column("token_prefix", sa.String(length=16), nullable=False),
        sa.Column("scopes_json", sa.Text(), nullable=False, server_default="'[]'"),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=True),
    )

    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=64), unique=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.add_column("users", sa.Column("organization_id", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("role", sa.String(length=32), server_default="operator"))

    op.create_table(
        "ip_access_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("proxy_id", sa.String(length=128), nullable=True),
        sa.Column("rule_type", sa.String(length=16), nullable=False),
        sa.Column("cidr", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notes", sa.Text(), nullable=True),
    )

    op.create_table(
        "geo_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("proxy_id", sa.String(length=128), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("countries_json", sa.Text(), nullable=False, server_default="'[]'"),
        sa.Column("default_policy", sa.String(length=16), nullable=False, server_default="allow"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "threat_feeds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("url", sa.String(length=512), nullable=False),
        sa.Column("feed_type", sa.String(length=32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("ip_count", sa.Integer(), server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
    )

    op.create_table(
        "proxy_waf_settings",
        sa.Column("proxy_id", sa.String(length=128), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("mode", sa.String(length=16), server_default="detection"),
        sa.Column("profile", sa.String(length=16), server_default="medium"),
        sa.Column("exclusions_json", sa.Text(), server_default="'[]'"),
    )

    op.create_table(
        "security_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("client_ip", sa.String(length=64), nullable=True),
        sa.Column("proxy_id", sa.String(length=128), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_security_events_created_at", "security_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_security_events_created_at", table_name="security_events")
    op.drop_table("security_events")
    op.drop_table("proxy_waf_settings")
    op.drop_table("threat_feeds")
    op.drop_table("geo_rules")
    op.drop_table("ip_access_rules")
    op.drop_column("users", "role")
    op.drop_column("users", "organization_id")
    op.drop_table("organizations")
    op.drop_table("api_tokens")
    op.drop_index("ix_config_versions_resource", table_name="config_versions")
    op.drop_table("config_versions")
    op.drop_table("proxy_templates")
    op.drop_table("proxy_rate_limits")
    op.drop_column("proxy_traffic_aggregates", "top_paths_json")
    op.drop_column("proxy_traffic_aggregates", "top_clients_json")
    op.drop_column("proxy_traffic_aggregates", "status_5xx")
    op.drop_column("proxy_traffic_aggregates", "status_4xx")
    op.drop_column("proxy_traffic_aggregates", "status_3xx")
    op.drop_column("proxy_traffic_aggregates", "status_2xx")
    op.drop_column("proxy_traffic_aggregates", "upstream_latency_avg_ms")
    op.drop_column("proxy_traffic_aggregates", "latency_avg_ms")
    op.drop_index("ix_certificate_renewal_log_created_at", table_name="certificate_renewal_log")
    op.drop_index("ix_certificate_renewal_log_certificate_name", table_name="certificate_renewal_log")
    op.drop_table("certificate_renewal_log")
