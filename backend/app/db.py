from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from pathlib import Path

from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate_user_columns() -> None:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("users")}
    additions = {
        "is_admin": "BOOLEAN DEFAULT 0",
        "perm_read": "BOOLEAN DEFAULT 1",
        "perm_create": "BOOLEAN DEFAULT 0",
        "perm_edit": "BOOLEAN DEFAULT 0",
    }
    with engine.begin() as conn:
        for name, ddl in additions.items():
            if name not in columns:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {name} {ddl}"))


def migrate_tenant_columns() -> None:
    inspector = inspect(engine)
    table_columns = {
        table: {col["name"] for col in inspector.get_columns(table)}
        for table in inspector.get_table_names()
    }
    additions = {
        "users": {
            "organization_id": "INTEGER",
            "role": "VARCHAR(32) DEFAULT 'operator'",
        },
        "backend_pools": {"organization_id": "INTEGER"},
        "notification_recipients": {"organization_id": "INTEGER"},
        "audit_log": {"organization_id": "INTEGER"},
    }
    with engine.begin() as conn:
        for table, columns in additions.items():
            if table not in table_columns:
                continue
            for name, ddl in columns.items():
                if name not in table_columns[table]:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def migrate_smtp_columns() -> None:
    inspector = inspect(engine)
    if "smtp_settings" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("smtp_settings")}
    additions = {
        "tls_server_name": "VARCHAR(255) DEFAULT ''",
        "verify_tls_certificate": "BOOLEAN DEFAULT 1",
        "default_recipient_email": "VARCHAR(255) DEFAULT ''",
    }
    with engine.begin() as conn:
        for name, ddl in additions.items():
            if name not in columns:
                conn.execute(text(f"ALTER TABLE smtp_settings ADD COLUMN {name} {ddl}"))


def migrate_metrics_columns() -> None:
    inspector = inspect(engine)
    if "proxy_traffic_aggregates" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("proxy_traffic_aggregates")}
        additions = {
            "latency_avg_ms": "FLOAT DEFAULT 0",
            "upstream_latency_avg_ms": "FLOAT DEFAULT 0",
            "status_2xx": "INTEGER DEFAULT 0",
            "status_3xx": "INTEGER DEFAULT 0",
            "status_4xx": "INTEGER DEFAULT 0",
            "status_5xx": "INTEGER DEFAULT 0",
            "top_clients_json": "TEXT DEFAULT '{}'",
            "top_paths_json": "TEXT DEFAULT '{}'",
            "max_response_time_ms": "FLOAT DEFAULT 0",
            "status_codes_json": "TEXT DEFAULT '{}'",
        }
        with engine.begin() as conn:
            for name, ddl in additions.items():
                if name not in columns:
                    conn.execute(text(f"ALTER TABLE proxy_traffic_aggregates ADD COLUMN {name} {ddl}"))

    table_ddls = {
        "backend_metrics": """
            CREATE TABLE IF NOT EXISTS backend_metrics (
                id INTEGER PRIMARY KEY,
                backend_server_id INTEGER NOT NULL,
                timestamp DATETIME NOT NULL,
                status VARCHAR(32) DEFAULT 'unknown',
                response_time_ms FLOAT DEFAULT 0,
                requests INTEGER DEFAULT 0,
                errors INTEGER DEFAULT 0,
                active_connections INTEGER DEFAULT 0
            )
        """,
        "connection_metrics": """
            CREATE TABLE IF NOT EXISTS connection_metrics (
                id INTEGER PRIMARY KEY,
                timestamp DATETIME NOT NULL,
                active INTEGER DEFAULT 0,
                reading INTEGER DEFAULT 0,
                writing INTEGER DEFAULT 0,
                waiting INTEGER DEFAULT 0,
                accepts INTEGER DEFAULT 0,
                handled INTEGER DEFAULT 0,
                requests INTEGER DEFAULT 0
            )
        """,
        "request_events": """
            CREATE TABLE IF NOT EXISTS request_events (
                id INTEGER PRIMARY KEY,
                timestamp DATETIME NOT NULL,
                proxy_id VARCHAR(128) NOT NULL,
                client_ip VARCHAR(64) DEFAULT '',
                host VARCHAR(255) DEFAULT '',
                method VARCHAR(16) DEFAULT '',
                uri VARCHAR(2048) DEFAULT '',
                status INTEGER DEFAULT 0,
                backend_addr VARCHAR(255) DEFAULT '',
                response_time_ms FLOAT DEFAULT 0,
                upstream_time_ms FLOAT DEFAULT 0,
                bytes_sent INTEGER DEFAULT 0,
                user_agent VARCHAR(512) DEFAULT '',
                is_failed BOOLEAN DEFAULT 0,
                error_hint TEXT,
                error_log_snippet TEXT
            )
        """,
        "metric_alert_rules": """
            CREATE TABLE IF NOT EXISTS metric_alert_rules (
                id INTEGER PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                severity VARCHAR(32) DEFAULT 'warning',
                metric_type VARCHAR(64) NOT NULL,
                condition VARCHAR(32) DEFAULT 'gt',
                threshold FLOAT DEFAULT 0,
                window_minutes INTEGER DEFAULT 5,
                proxy_id VARCHAR(128),
                notify_email BOOLEAN DEFAULT 1,
                created_at DATETIME,
                updated_at DATETIME
            )
        """,
        "metric_alert_history": """
            CREATE TABLE IF NOT EXISTS metric_alert_history (
                id INTEGER PRIMARY KEY,
                rule_id INTEGER,
                alert_type VARCHAR(64) NOT NULL,
                severity VARCHAR(32) DEFAULT 'warning',
                status VARCHAR(16) DEFAULT 'fired',
                message TEXT NOT NULL,
                metric_value FLOAT,
                created_at DATETIME
            )
        """,
        "metrics_settings": """
            CREATE TABLE IF NOT EXISTS metrics_settings (
                id INTEGER PRIMARY KEY,
                raw_retention_days INTEGER DEFAULT 7,
                minute_retention_days INTEGER DEFAULT 30,
                hour_retention_days INTEGER DEFAULT 180,
                stub_status_url VARCHAR(255) DEFAULT 'http://127.0.0.1:8081/nginx_status',
                enhanced_logging_default BOOLEAN DEFAULT 0,
                request_event_sample_rate INTEGER DEFAULT 100,
                updated_at DATETIME
            )
        """,
    }
    existing = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table, ddl in table_ddls.items():
            if table not in existing:
                conn.execute(text(ddl))


def init_db() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.backup_dir.mkdir(parents=True, exist_ok=True)
    from app.models import (  # noqa: F401
        api_token,
        audit,
        backend_pool,
        backend_server,
        certificate_renewal,
        imported_certificate,
        config_version,
        geo_rule,
        health_check,
        ip_access_rule,
        notification,
        organization,
        proxy_rate_limit,
        proxy_template,
        proxy_traffic,
        proxy_waf_settings,
        metrics,
        security_event,
        session,
        smtp_settings,
        status_report,
        system_alert,
        threat_feed,
        user,
    )

    Base.metadata.create_all(bind=engine)
    migrate_user_columns()
    migrate_tenant_columns()
    migrate_smtp_columns()
    migrate_metrics_columns()
    if settings.alembic_upgrade:
        run_alembic_upgrade()

    from app.security.tenant_context import assign_orphan_records_to_default_org, bootstrap_default_organization

    db = SessionLocal()
    try:
        default_org = bootstrap_default_organization(db)
        assign_orphan_records_to_default_org(db, default_org.id)
    finally:
        db.close()


def run_alembic_upgrade() -> None:
    try:
        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
        command.upgrade(alembic_cfg, "head")
    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning("Alembic upgrade skipped: %s", exc)
