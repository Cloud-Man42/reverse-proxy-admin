import json

from app.schemas import StatusReportSection, StatusReportSettingsUpdate
from app.services.status_report_service import StatusReportService


def test_status_report_settings_defaults(temp_settings, db_session):
    service = StatusReportService(temp_settings, db_session)
    settings = service.get_settings()
    assert settings.enabled is False
    assert settings.interval_hours == 24
    assert StatusReportSection.PROXY_TRAFFIC.value in settings.enabled_sections


def test_status_report_update_sections(temp_settings, db_session):
    service = StatusReportService(temp_settings, db_session)
    updated = service.update_settings(
        StatusReportSettingsUpdate(
            enabled=True,
            interval_hours=12,
            enabled_sections=[StatusReportSection.PROXY_TRAFFIC, StatusReportSection.PROXY_STATUS],
        )
    )
    assert updated.enabled is True
    assert updated.interval_hours == 12
    assert updated.enabled_sections == ["proxy_traffic", "proxy_status"]


def test_build_report_includes_selected_sections(temp_settings, db_session):
    service = StatusReportService(temp_settings, db_session)
    service.update_settings(
        StatusReportSettingsUpdate(enabled_sections=[StatusReportSection.PROXY_STATUS])
    )
    body = service.build_report(["proxy_status"])
    assert "=== Proxy Status ===" in body
    assert "=== Proxy Traffic" not in body


def test_maybe_send_scheduled_respects_interval(temp_settings, db_session, monkeypatch):
    from datetime import datetime

    service = StatusReportService(temp_settings, db_session)
    service.update_settings(StatusReportSettingsUpdate(enabled=True, interval_hours=24))
    sent_calls = {"count": 0}

    def fake_send():
        sent_calls["count"] += 1
        row = service._get_or_create_settings()
        row.last_sent_at = datetime.utcnow()
        db_session.commit()
        return 1

    monkeypatch.setattr(service, "send_report", fake_send)
    assert service.maybe_send_scheduled() == 1
    assert service.maybe_send_scheduled() == 0
