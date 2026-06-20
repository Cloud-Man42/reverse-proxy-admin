import smtplib
import ssl
from email.mime.text import MIMEText
from typing import Optional

from sqlalchemy.orm import Session

from app.config import Settings
from app.models.smtp_settings import SmtpSettings
from app.schemas import SmtpSecurityMode, SmtpSettingsResponse, SmtpSettingsUpdate, SmtpTestResponse
from app.security.encryption import decrypt_value, encrypt_value


class SmtpService:
    def __init__(self, settings: Settings, db: Session) -> None:
        self.settings = settings
        self.db = db

    @staticmethod
    def security_mode_from_row(row: SmtpSettings) -> SmtpSecurityMode:
        if row.ssl_enabled:
            return SmtpSecurityMode.SSL
        if row.tls_enabled:
            return SmtpSecurityMode.STARTTLS
        return SmtpSecurityMode.NONE

    @staticmethod
    def apply_security_mode(row: SmtpSettings, mode: SmtpSecurityMode) -> None:
        if mode == SmtpSecurityMode.SSL:
            row.ssl_enabled = True
            row.tls_enabled = False
        elif mode == SmtpSecurityMode.STARTTLS:
            row.ssl_enabled = False
            row.tls_enabled = True
        else:
            row.ssl_enabled = False
            row.tls_enabled = False

    def _get_or_create(self) -> SmtpSettings:
        row = self.db.query(SmtpSettings).first()
        if row:
            return row
        row = SmtpSettings()
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_settings(self) -> SmtpSettingsResponse:
        row = self._get_or_create()
        return SmtpSettingsResponse(
            host=row.host,
            port=row.port,
            username=row.username,
            password_set=bool(row.password_encrypted),
            security_mode=self.security_mode_from_row(row),
            starttls_enabled=row.tls_enabled,
            ssl_enabled=row.ssl_enabled,
            sender_name=row.sender_name,
            sender_email=row.sender_email,
            last_test_status=row.last_test_status,
        )

    def update_settings(self, payload: SmtpSettingsUpdate) -> SmtpSettingsResponse:
        row = self._get_or_create()
        row.host = payload.host.strip()
        row.port = payload.port
        row.username = payload.username.strip()
        if payload.password:
            row.password_encrypted = encrypt_value(self.settings, payload.password)
        if payload.security_mode is not None:
            self.apply_security_mode(row, payload.security_mode)
        else:
            if payload.ssl_enabled and payload.starttls_enabled:
                raise ValueError("Enable either STARTTLS or SSL, not both")
            row.ssl_enabled = payload.ssl_enabled
            row.tls_enabled = payload.starttls_enabled
        row.sender_name = payload.sender_name.strip()
        row.sender_email = payload.sender_email.strip()
        self.db.commit()
        return self.get_settings()

    def _password(self, row: SmtpSettings) -> str:
        if not row.password_encrypted:
            return ""
        return decrypt_value(self.settings, row.password_encrypted)

    def test_connection(self) -> SmtpTestResponse:
        row = self._get_or_create()
        if not row.host:
            return SmtpTestResponse(status="connection_failed", message="SMTP host is not configured")
        try:
            self._send_via_smtp(row, row.sender_email or row.username, "Connection Test", "SMTP connection test")
            row.last_test_status = "connected"
            self.db.commit()
            return SmtpTestResponse(status="connected", message="Successfully connected and authenticated")
        except smtplib.SMTPAuthenticationError:
            row.last_test_status = "authentication_failed"
            self.db.commit()
            return SmtpTestResponse(status="authentication_failed", message="Authentication failed")
        except Exception as exc:
            row.last_test_status = "connection_failed"
            self.db.commit()
            return SmtpTestResponse(status="connection_failed", message=str(exc))

    def send_test_email(self, recipient: str) -> SmtpTestResponse:
        row = self._get_or_create()
        try:
            self._send_via_smtp(row, recipient, "Reverse Proxy Admin Test Email", "This is a test email from Reverse Proxy Admin.")
            return SmtpTestResponse(status="connected", message=f"Test email sent to {recipient}")
        except smtplib.SMTPAuthenticationError:
            return SmtpTestResponse(status="authentication_failed", message="Authentication failed")
        except Exception as exc:
            return SmtpTestResponse(status="connection_failed", message=str(exc))

    def send_email(self, recipients: list[str], subject: str, body: str) -> tuple[bool, str]:
        row = self._get_or_create()
        if not row.host or not recipients:
            return False, "SMTP not configured or no recipients"
        try:
            for recipient in recipients:
                self._send_via_smtp(row, recipient, subject, body)
            return True, "sent"
        except Exception as exc:
            return False, str(exc)

    def _send_via_smtp(self, row: SmtpSettings, to_addr: str, subject: str, body: str) -> None:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = f"{row.sender_name} <{row.sender_email or row.username}>"
        msg["To"] = to_addr
        password = self._password(row)
        if row.ssl_enabled:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(row.host, row.port, context=context, timeout=15) as smtp:
                if row.username:
                    smtp.login(row.username, password)
                smtp.sendmail(row.sender_email or row.username, [to_addr], msg.as_string())
            return
        with smtplib.SMTP(row.host, row.port, timeout=15) as smtp:
            smtp.ehlo()
            if row.tls_enabled:
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
            if row.username:
                smtp.login(row.username, password)
            smtp.sendmail(row.sender_email or row.username, [to_addr], msg.as_string())

    def status_label(self) -> str:
        row = self._get_or_create()
        return row.last_test_status or "unknown"
