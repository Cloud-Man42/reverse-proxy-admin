import pytest

from app.config import Settings
from app.models.user import User
from app.schemas import ProxyAppCreate, TargetProtocol, UserCreate
from app.security.auth import hash_password
from app.services.traffic_flow_service import TrafficFlowService
from app.services.user_service import UserService


def test_user_permissions():
    admin = User(username="admin", password_hash="x", is_admin=True)
    viewer = User(username="view", password_hash="x", perm_read=True)
    editor = User(username="edit", password_hash="x", perm_read=True, perm_edit=True)

    assert admin.has_read() and admin.has_create() and admin.has_edit()
    assert viewer.has_read() and not viewer.has_create()
    assert editor.has_edit() and not editor.has_create()


def test_traffic_flow_validation(temp_settings):
    app = ProxyAppCreate(
        name="demo",
        domains=["demo.example.com"],
        target_protocol=TargetProtocol.HTTP,
        target_host="127.0.0.1",
        target_port=1,
        enabled=True,
    )
    result = TrafficFlowService(temp_settings).test_traffic_flow(app)
    assert len(result.checks) >= 4
    assert any(check.name == "upstream_connectivity" for check in result.checks)
    assert any(check.name == "nginx_syntax" for check in result.checks)
