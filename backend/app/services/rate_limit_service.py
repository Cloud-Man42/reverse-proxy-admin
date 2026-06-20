from typing import Optional

from sqlalchemy.orm import Session

from app.models.proxy_rate_limit import ProxyRateLimit
from app.schemas import ProxyRateLimitResponse, ProxyRateLimitUpdate


class RateLimitService:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _defaults(proxy_id: str) -> ProxyRateLimit:
        return ProxyRateLimit(proxy_id=proxy_id)

    def get(self, proxy_id: str) -> ProxyRateLimitResponse:
        row = self.db.get(ProxyRateLimit, proxy_id)
        if row is None:
            row = self._defaults(proxy_id)
        return ProxyRateLimitResponse(
            proxy_id=proxy_id,
            enabled=row.enabled,
            requests_per_minute=row.requests_per_minute,
            burst=row.burst,
            nodelay=row.nodelay,
            key_type=row.key_type,
        )

    def get_model(self, proxy_id: str) -> ProxyRateLimit:
        row = self.db.get(ProxyRateLimit, proxy_id)
        if row is None:
            row = self._defaults(proxy_id)
            self.db.add(row)
            self.db.flush()
        return row

    def upsert(self, proxy_id: str, payload: ProxyRateLimitUpdate) -> ProxyRateLimitResponse:
        row = self.db.get(ProxyRateLimit, proxy_id)
        if row is None:
            row = ProxyRateLimit(proxy_id=proxy_id)
            self.db.add(row)
        row.enabled = payload.enabled
        row.requests_per_minute = payload.requests_per_minute
        row.burst = payload.burst
        row.nodelay = payload.nodelay
        row.key_type = payload.key_type
        self.db.commit()
        return self.get(proxy_id)

    def delete(self, proxy_id: str) -> None:
        row = self.db.get(ProxyRateLimit, proxy_id)
        if row is not None:
            self.db.delete(row)
            self.db.commit()
