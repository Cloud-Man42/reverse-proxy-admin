from sqlalchemy.orm import Session

from app.config import Settings
from app.schemas import CertificateResponse
from app.services.certbot_ops import CertbotOps
from app.services.certificate_import_service import CertificateImportService


class CertificateService:
    def __init__(self, settings: Settings, db: Session | None = None) -> None:
        self.settings = settings
        self.db = db
        self.certbot = CertbotOps(settings, db)
        self.imports = CertificateImportService(settings, db) if db else None

    def list_certificates(self) -> list[CertificateResponse]:
        letsencrypt = [
            cert.model_copy(update={"source": "letsencrypt", "renewable": True})
            for cert in self.certbot.list_certificates()
        ]
        imported: list[CertificateResponse] = []
        if self.imports:
            imported = self.imports.list_certificates()
        merged = {cert.name: cert for cert in letsencrypt}
        for cert in imported:
            merged[cert.name] = cert
        return sorted(merged.values(), key=lambda item: item.name.lower())

    def is_imported(self, name: str) -> bool:
        return bool(self.imports and self.imports.is_imported(name))
