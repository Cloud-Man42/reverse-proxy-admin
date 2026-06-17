from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

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


def init_db() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.backup_dir.mkdir(parents=True, exist_ok=True)
    from app.models import audit, session, user  # noqa: F401

    Base.metadata.create_all(bind=engine)
    migrate_user_columns()
