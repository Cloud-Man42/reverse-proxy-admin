import inspect
import smtplib
import socket
import ssl
from email.mime.text import MIMEText
from typing import Optional

from sqlalchemy.orm import Session

from app.branding import APP_NAME
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
            tls_server_name=row.tls_server_name,
            verify_tls_certificate=row.verify_tls_certificate,
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
        row.tls_server_name = payload.tls_server_name.strip()
        row.verify_tls_certificate = payload.verify_tls_certificate
        self.db.commit()
        return self.get_settings()

    def _password(self, row: SmtpSettings) -> str:
        if not row.password_encrypted:
            return ""
        return decrypt_value(self.settings, row.password_encrypted)

    @staticmethod
    def _tls_server_name(row: SmtpSettings) -> str | None:
        name = row.tls_server_name.strip() or row.host.strip()
        return name or None

    def _ssl_context(self, row: SmtpSettings) -> ssl.SSLContext:
        if not row.verify_tls_certificate:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            return context
        return ssl.create_default_context()

    @staticmethod
    def _starttls(smtp: smtplib.SMTP, context: ssl.SSLContext, server_name: str | None) -> None:
        kwargs: dict[str, object] = {"context": context}
        if server_name and "server_hostname" in inspect.signature(smtp.starttls).parameters:
            kwargs["server_hostname"] = server_name
        smtp.starttls(**kwargs)

    def _connect_smtp(self, row: SmtpSettings) -> smtplib.SMTP:
        host = row.host.strip()
        context = self._ssl_context(row)
        server_name = self._tls_server_name(row)
        timeout = 15

        if row.ssl_enabled:
            if server_name and server_name != host:
                sock = socket.create_connection((host, row.port), timeout=timeout)
                ssl_sock = context.wrap_socket(sock, server_hostname=server_name)
                smtp: smtplib.SMTP = smtplib.SMTP(timeout=timeout)
                smtp.sock = ssl_sock
                smtp.file = ssl_sock.makefile("rb")
                smtp._host = host
                smtp.ehlo_or_helo_if_needed()
                return smtp
            return smtplib.SMTP_SSL(host, row.port, context=context, timeout=timeout)

        smtp = smtplib.SMTP(host, row.port, timeout=timeout)
        smtp.ehlo()
        if row.tls_enabled:
            self._starttls(smtp, context, server_name)
            smtp.ehlo()
        return smtp

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
        except ssl.SSLError as exc:
            row.last_test_status = "connection_failed"
            self.db.commit()
            hint = (
                " If the SMTP host is an IP address, set TLS server name to the hostname on the certificate, "
                "or disable TLS certificate verification for trusted internal servers."
            )
            return SmtpTestResponse(status="connection_failed", message=f"{exc}.{hint}")
        except Exception as exc:
            row.last_test_status = "connection_failed"
            self.db.commit()
            return SmtpTestResponse(status="connection_failed", message=str(exc))

    def send_test_email(self, recipient: str) -> SmtpTestResponse:
        row = self._get_or_create()
        try:
            self._send_via_smtp(
                row,
                recipient,
                f"{APP_NAME} Test Email",
                f"This is a test email from {APP_NAME}.",
            )
            return SmtpTestResponse(status="connected", message=f"Test email sent to {recipient}")
        except smtplib.SMTPAuthenticationError:
            return SmtpTestResponse(status="authentication_failed", message="Authentication failed")
        except ssl.SSLError as exc:
            hint = (
                " If the SMTP host is an IP address, set TLS server name to the hostname on the certificate, "
                "or disable TLS certificate verification for trusted internal servers."
            )
            return SmtpTestResponse(status="connection_failed", message=f"{exc}.{hint}")
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
        with self._connect_smtp(row) as smtp:
            if row.username:
                smtp.login(row.username, password)
            smtp.sendmail(row.sender_email or row.username, [to_addr], msg.as_string())

    def status_label(self) -> str:
        row = self._get_or_create()
        return row.last_test_status or "unknown"
