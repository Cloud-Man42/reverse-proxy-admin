import json
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ImportedCertificate(Base):
    __tablename__ = "imported_certificates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    primary_domain: Mapped[str] = mapped_column(String(255), index=True)
    domains_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def domains_list(self) -> list[str]:
        try:
            value = json.loads(self.domains_json)
        except (TypeError, json.JSONDecodeError):
            return [self.primary_domain]
        if not isinstance(value, list):
            return [self.primary_domain]
        return [str(entry) for entry in value if entry]
