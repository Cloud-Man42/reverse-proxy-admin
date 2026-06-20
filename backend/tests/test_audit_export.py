from datetime import datetime, timedelta

import pytest

from app.models.audit import AuditLog
from app.models.user import User
from app.services.audit_service import log_audit
from app.services.security_event_service import AuditExportService, SecurityEventService


def test_audit_export_json(db_session):
    admin = db_session.query(User).filter(User.username == "admin").first()
    log_audit(
        db_session,
        username="admin",
        action="test_action",
        resource="test_resource",
        client_ip="127.0.0.1",
        new_value={"ok": True},
    )
    content, media_type, filename = AuditExportService(db_session).export(admin, format="json")
    assert media_type == "application/json"
    assert filename == "audit-log.json"
    assert "test_action" in content
    assert "test_resource" in content


def test_audit_export_csv(db_session):
    admin = db_session.query(User).filter(User.username == "admin").first()
    log_audit(
        db_session,
        username="admin",
        action="csv_action",
        resource="csv_resource",
        client_ip="10.0.0.1",
    )
    content, media_type, filename = AuditExportService(db_session).export(admin, format="csv")
    assert media_type == "text/csv"
    assert filename == "audit-log.csv"
    assert "csv_action" in content
    assert "username" in content.splitlines()[0]


def test_audit_export_date_filter(db_session):
    admin = db_session.query(User).filter(User.username == "admin").first()
    old = AuditLog(
        username="admin",
        action="old_action",
        resource="res",
        client_ip="127.0.0.1",
        created_at=datetime.utcnow() - timedelta(days=30),
    )
    db_session.add(old)
    db_session.commit()

    content, _, _ = AuditExportService(db_session).export(
        admin,
        format="json",
        from_dt=datetime.utcnow() - timedelta(days=1),
    )
    assert "old_action" not in content


def test_security_event_export(db_session):
    SecurityEventService(db_session).log(
        event_type="login_failed",
        source="login",
        client_ip="192.0.2.1",
        message="Failed login",
    )
    content, media_type, filename = SecurityEventService(db_session).export_events(format="csv")
    assert media_type == "text/csv"
    assert filename == "security-events.csv"
    assert "login_failed" in content


@pytest.mark.api
def test_audit_export_api(client, auth_session, db_session):
    log_audit(
        db_session,
        username="admin",
        action="export_test",
        resource="audit",
        client_ip="127.0.0.1",
    )
    response = client.get("/api/audit/export?format=json", cookies=auth_session["cookies"])
    assert response.status_code == 200
    assert "export_test" in response.text
