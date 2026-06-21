from app.schemas import NotificationEventType, SmtpSecurityMode, SmtpSettingsUpdate
from app.services.notification_service import NotificationService
from app.services.smtp_service import SmtpService


def test_resolve_recipients_uses_smtp_default_when_no_notification_recipients(db_session, temp_settings):
    SmtpService(temp_settings, db_session).update_settings(
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
    service = NotificationService(temp_settings, db_session)
    recipients = service._resolve_recipients(NotificationEventType.PROXY_CREATED, "info")
    assert recipients == ["alerts@example.com"]
