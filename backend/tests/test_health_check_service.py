from unittest.mock import MagicMock, patch

import pytest

from app.models.backend_pool import BackendPool
from app.models.backend_server import BackendServer
from app.schemas import HealthStatus
from app.services.health_check_service import HealthCheckService


def _make_server(db_session, *, health_status: str = "unknown", host: str = "127.0.0.1", port: int = 8080):
    pool = BackendPool(name="test-pool", route_path="/")
    db_session.add(pool)
    db_session.flush()
    server = BackendServer(
        pool_id=pool.id,
        name="server-1",
        host=host,
        port=port,
        protocol="http",
        health_check_type="tcp",
        health_status=health_status,
    )
    db_session.add(server)
    db_session.commit()
    db_session.refresh(server)
    return server


def test_tcp_check_healthy(temp_settings, db_session):
    server = _make_server(db_session)
    service = HealthCheckService(temp_settings, db_session)

    with patch("app.services.health_check_service.socket.create_connection") as mock_conn:
        mock_conn.return_value.__enter__ = MagicMock(return_value=None)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        status, response_ms, http_status, error = service._perform_check(server)

    assert status == HealthStatus.HEALTHY
    assert response_ms is not None
    assert http_status is None
    assert error is None


def test_tcp_check_offline(temp_settings, db_session):
    server = _make_server(db_session)
    service = HealthCheckService(temp_settings, db_session)

    with patch(
        "app.services.health_check_service.socket.create_connection",
        side_effect=ConnectionRefusedError("connection refused"),
    ):
        status, response_ms, http_status, error = service._perform_check(server)

    assert status == HealthStatus.OFFLINE
    assert response_ms is not None
    assert http_status is None
    assert "connection refused" in (error or "")


def test_check_server_dispatches_offline_notification(temp_settings, db_session):
    server = _make_server(db_session, health_status="healthy")
    service = HealthCheckService(temp_settings, db_session)

    with patch.object(service, "_perform_check", return_value=(HealthStatus.OFFLINE, 12.5, None, "timeout")):
        with patch("app.services.notification_service.NotificationService") as mock_notification_cls:
            with patch("app.services.nginx_regen_service.NginxRegenService.queue_for_server") as mock_queue:
                mock_notification = mock_notification_cls.return_value
                service.check_server(server)

    mock_queue.assert_called_once_with(server)
    mock_notification_cls.assert_called_once_with(temp_settings, db_session)
    mock_notification.dispatch_backend_offline.assert_called_once_with(server)
    mock_notification.dispatch_backend_restored.assert_not_called()


def test_check_server_dispatches_restored_notification(temp_settings, db_session):
    server = _make_server(db_session, health_status="offline")
    service = HealthCheckService(temp_settings, db_session)

    with patch.object(service, "_perform_check", return_value=(HealthStatus.HEALTHY, 5.0, None, None)):
        with patch("app.services.notification_service.NotificationService") as mock_notification_cls:
            with patch("app.services.nginx_regen_service.NginxRegenService.queue_for_server") as mock_queue:
                mock_notification = mock_notification_cls.return_value
                service.check_server(server)

    mock_queue.assert_called_once_with(server)
    mock_notification_cls.assert_called_once_with(temp_settings, db_session)
    mock_notification.dispatch_backend_restored.assert_called_once_with(server)
    mock_notification.dispatch_backend_offline.assert_not_called()


def test_run_server_returns_result(temp_settings, db_session):
    server = _make_server(db_session)
    service = HealthCheckService(temp_settings, db_session)

    with patch.object(service, "_perform_check", return_value=(HealthStatus.HEALTHY, 3.2, None, None)):
        result = service.run_server(server.id)

    assert result is not None
    assert result.server_id == server.id
    assert result.server_name == "server-1"
    assert result.pool_name == "test-pool"
    assert result.status == HealthStatus.HEALTHY


def test_run_server_missing_server(temp_settings, db_session):
    service = HealthCheckService(temp_settings, db_session)
    assert service.run_server(9999) is None
