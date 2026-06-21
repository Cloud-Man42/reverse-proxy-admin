from datetime import datetime

from sqlalchemy.orm import Session

from app.config import Settings
from app.models.metrics import MetricsSettings


class MetricsSettingsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create(self) -> MetricsSettings:
        row = self.db.query(MetricsSettings).first()
        if row:
            return row
        row = MetricsSettings()
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def update(self, settings: Settings, payload: dict) -> MetricsSettings:
        row = self.get_or_create()
        for key in (
            "raw_retention_days",
            "minute_retention_days",
            "hour_retention_days",
            "stub_status_url",
            "enhanced_logging_default",
            "request_event_sample_rate",
        ):
            if key in payload and payload[key] is not None:
                setattr(row, key, payload[key])
        row.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(row)
        return row

    def to_dict(self, row: MetricsSettings) -> dict:
        return {
            "raw_retention_days": row.raw_retention_days,
            "minute_retention_days": row.minute_retention_days,
            "hour_retention_days": row.hour_retention_days,
            "stub_status_url": row.stub_status_url,
            "enhanced_logging_default": row.enhanced_logging_default,
            "request_event_sample_rate": row.request_event_sample_rate,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
