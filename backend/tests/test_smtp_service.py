from app.models.smtp_settings import SmtpSettings
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
            sender_email="ops@example.com",
            security_mode=SmtpSecurityMode.STARTTLS,
        )
    )
    assert updated.security_mode == SmtpSecurityMode.STARTTLS
    assert updated.starttls_enabled is True
    assert updated.ssl_enabled is False


def test_update_settings_allows_empty_sender_email(db_session, temp_settings):
    service = SmtpService(temp_settings, db_session)
    updated = service.update_settings(
        SmtpSettingsUpdate(
            host="smtp.example.com",
            port=587,
            username="mailer@example.com",
            sender_name="Admin",
            sender_email="",
            security_mode=SmtpSecurityMode.STARTTLS,
        )
    )
    assert updated.sender_email == ""


def test_merge_recipient_emails_includes_default_and_deduplicates():
    merged = SmtpService.merge_recipient_emails(
        ["ops@example.com", "OPS@example.com"],
        default_email="admin@example.com",
    )
    assert merged == ["admin@example.com", "ops@example.com"]


def test_update_settings_keeps_password_when_not_provided(db_session, temp_settings):
    service = SmtpService(temp_settings, db_session)
    service.update_settings(
        SmtpSettingsUpdate(
            host="smtp.example.com",
            port=587,
            username="mailer@example.com",
            password="secret-smtp-password",
            sender_name="Admin",
            sender_email="",
            security_mode=SmtpSecurityMode.STARTTLS,
        )
    )
    updated = service.update_settings(
        SmtpSettingsUpdate(
            host="smtp.example.com",
            port=587,
            username="smtp-user@example.com",
            sender_name="Admin",
            sender_email="",
            security_mode=SmtpSecurityMode.STARTTLS,
        )
    )
    assert updated.username == "smtp-user@example.com"
    assert updated.password_set is True
    row = db_session.query(SmtpSettings).first()
    assert service._password(row) == "secret-smtp-password"


def test_update_settings_stores_default_recipient(db_session, temp_settings):
    service = SmtpService(temp_settings, db_session)
    updated = service.update_settings(
        SmtpSettingsUpdate(
            host="smtp.example.com",
            port=587,
            username="mailer@example.com",
            sender_name="Admin",
            sender_email="",
            default_recipient_email="alerts@example.com",
            security_mode=SmtpSecurityMode.STARTTLS,
        )
    )
    assert updated.default_recipient_email == "alerts@example.com"


def test_ssl_context_can_disable_verification(db_session, temp_settings):
    from app.models.smtp_settings import SmtpSettings

    row = SmtpSettings(host="192.168.1.55", port=465, ssl_enabled=True, verify_tls_certificate=False)
    context = SmtpService(temp_settings, db_session)._ssl_context(row)
    assert context.verify_mode.name == "CERT_NONE"
    assert context.check_hostname is False
