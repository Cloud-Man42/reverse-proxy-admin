from datetime import datetime

from sqlalchemy.orm import Session

from app.config import Settings
from app.services.certbot_ops import CertbotOps
from app.services.certificate_service import CertificateService
from app.services.notification_service import NotificationService

SSL_THRESHOLDS = [30, 14, 7, 3, 1]


class SslAlertService:
    def __init__(self, settings: Settings, db: Session) -> None:
        self.settings = settings
        self.db = db
        self.certbot = CertbotOps(settings, db)
        self.certificates = CertificateService(settings, db)
        self.notifications = NotificationService(settings, db)

    def run_daily_checks(self) -> int:
        sent = 0
        try:
            certificates = self.certificates.list_certificates()
        except Exception:
            return 0
        now = datetime.utcnow()
        for cert in certificates:
            days_remaining = (cert.expiry - now).days
            for threshold in SSL_THRESHOLDS:
                if days_remaining <= threshold:
                    self.notifications.dispatch_ssl_expiring(cert.name, cert.expiry, days_remaining)
                    sent += 1
                    break
        return sent
