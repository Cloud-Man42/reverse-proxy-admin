import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest

# Configure writable paths before importing app modules (db.py reads settings at import time).
_test_root = Path(tempfile.gettempdir()) / "reverse-proxy-admin-pytest"
for sub in (
    "data",
    "backups",
    "certbot/work",
    "certbot/logs",
    "sites-available",
    "sites-enabled",
    "htpasswd",
    "logs",
    "letsencrypt/live",
):
    (_test_root / sub).mkdir(parents=True, exist_ok=True)

os.environ["ADMIN_PASSWORD"] = "test-password"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["USE_SUDO"] = "false"
os.environ["DATABASE_URL"] = f"sqlite:///{(_test_root / 'test.db').as_posix()}"
os.environ["DATA_DIR"] = str(_test_root / "data")
os.environ["BACKUP_DIR"] = str(_test_root / "backups")
os.environ["CERTBOT_WORK_DIR"] = str(_test_root / "certbot" / "work")
os.environ["CERTBOT_LOGS_DIR"] = str(_test_root / "certbot" / "logs")
os.environ["NGINX_SITES_AVAILABLE"] = str(_test_root / "sites-available")
os.environ["NGINX_SITES_ENABLED"] = str(_test_root / "sites-enabled")
os.environ["HTPASSWD_DIR"] = str(_test_root / "htpasswd")
os.environ["NGINX_ERROR_LOG"] = str(_test_root / "logs" / "error.log")
os.environ["NGINX_ACCESS_LOG"] = str(_test_root / "logs" / "access.log")
os.environ["LETSENCRYPT_LIVE"] = str(_test_root / "letsencrypt" / "live")
os.environ["CERTBOT_CONFIG_DIR"] = str(_test_root / "letsencrypt")
os.environ["ALEMBIC_UPGRADE"] = "false"
os.environ["SCHEDULER_ENABLED"] = "false"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings, get_settings
from app.db import Base, get_db
from app.main import app
from app.security.auth import bootstrap_admin, hash_password
from app.models.user import User


@pytest.fixture
def temp_settings(tmp_path: Path) -> Settings:
    sites_available = tmp_path / "sites-available"
    sites_enabled = tmp_path / "sites-enabled"
    data_dir = tmp_path / "data"
    backup_dir = tmp_path / "backups"
    htpasswd_dir = tmp_path / "htpasswd"
    log_dir = tmp_path / "logs"
    letsencrypt = tmp_path / "letsencrypt"
    for path in (sites_available, sites_enabled, data_dir, backup_dir, htpasswd_dir, log_dir, letsencrypt / "live"):
        path.mkdir(parents=True, exist_ok=True)

    return Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        data_dir=data_dir,
        backup_dir=backup_dir,
        nginx_sites_available=sites_available,
        nginx_sites_enabled=sites_enabled,
        nginx_error_log=log_dir / "error.log",
        nginx_access_log=log_dir / "access.log",
        letsencrypt_live=letsencrypt / "live",
        certbot_config_dir=letsencrypt,
        certbot_work_dir=data_dir / "certbot" / "work",
        certbot_logs_dir=data_dir / "certbot" / "logs",
        htpasswd_dir=htpasswd_dir,
        use_sudo=False,
        admin_password="test-password",
        admin_username="admin",
        allowed_ips=[],
        debug=True,
        frontend_dist=tmp_path / "nonexistent-frontend",
    )


@pytest.fixture
def db_session(temp_settings: Settings):
    engine = create_engine(
        temp_settings.database_url,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = session_factory()
    bootstrap_admin(session, temp_settings)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def client(temp_settings: Settings, db_session, monkeypatch) -> Generator[TestClient, None, None]:
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=db_session.bind)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    def override_get_settings() -> Settings:
        return temp_settings

    monkeypatch.setattr("app.config.get_settings", override_get_settings)
    monkeypatch.setattr("app.main.get_settings", override_get_settings)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = override_get_settings
    get_settings.cache_clear()

    with TestClient(app, base_url="http://testserver") as test_client:
        yield test_client

    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.fixture
def auth_session(client: TestClient) -> dict:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "test-password"},
    )
    assert response.status_code == 200
    data = response.json()
    csrf_token = data["csrf_token"]
    return {
        "csrf_token": csrf_token,
        "headers": {"X-CSRF-Token": csrf_token},
        "cookies": response.cookies,
    }


@pytest.fixture
def viewer_session(client: TestClient, db_session) -> dict:
    viewer = User(
        username="viewer",
        password_hash=hash_password("viewer-pass"),
        is_active=True,
        is_admin=False,
        perm_read=True,
        perm_create=False,
        perm_edit=False,
    )
    db_session.add(viewer)
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        json={"username": "viewer", "password": "viewer-pass"},
    )
    assert response.status_code == 200
    data = response.json()
    csrf_token = data["csrf_token"]
    return {
        "csrf_token": csrf_token,
        "headers": {"X-CSRF-Token": csrf_token},
        "cookies": response.cookies,
    }


def sample_route(**overrides):
    from app.schemas import ProxyRoute, TargetProtocol

    data = {
        "path_prefix": "/",
        "target_protocol": TargetProtocol.HTTP,
        "target_host": "10.0.0.10",
        "target_port": 8080,
        "websocket_enabled": False,
    }
    data.update(overrides)
    return ProxyRoute(**data)


def sample_proxy_payload(**overrides):
    from app.schemas import ProxyAppCreate, TargetProtocol

    data = {
        "name": "myapp",
        "domains": ["example.com"],
        "routes": [
            {
                "path_prefix": "/",
                "target_protocol": TargetProtocol.HTTP,
                "target_host": "10.0.0.10",
                "target_port": 8080,
            }
        ],
        "enabled": True,
    }
    data.update(overrides)
    return ProxyAppCreate(**data)
