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
