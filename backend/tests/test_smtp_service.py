from app.schemas import SmtpSecurityMode, SmtpSettingsUpdate
from app.services.smtp_service import SmtpService


def test_security_mode_from_row(db_session, temp_settings):
    from app.models.smtp_settings import SmtpSettings

    row = SmtpSettings(host="smtp.example.com", port=587, tls_enabled=True, ssl_enabled=False)
    assert SmtpService.security_mode_from_row(row) == SmtpSecurityMode.STARTTLS

    row.ssl_enabled = True
    row.tls_enabled = False
    assert SmtpService.security_mode_from_row(row) == SmtpSecurityMode.SSL

    row.ssl_enabled = False
    row.tls_enabled = False
    assert SmtpService.security_mode_from_row(row) == SmtpSecurityMode.NONE


def test_update_settings_starttls_mode(db_session, temp_settings):
    service = SmtpService(temp_settings, db_session)
    updated = service.update_settings(
        SmtpSettingsUpdate(
            host="smtp.example.com",
            port=587,
            username="user",
            sender_name="Admin",
            sender_email="ops@acme-labs.net",
            security_mode=SmtpSecurityMode.STARTTLS,
        )
    )
    assert updated.security_mode == SmtpSecurityMode.STARTTLS
    assert updated.starttls_enabled is True
    assert updated.ssl_enabled is False
