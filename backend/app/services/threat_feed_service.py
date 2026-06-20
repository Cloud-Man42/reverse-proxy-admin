from datetime import datetime, timezone
from typing import List, Optional, Set

import httpx
from sqlalchemy.orm import Session

from app.config import Settings
from app.models.threat_feed import ThreatFeed
from app.schemas import ThreatFeedCreate, ThreatFeedResponse, ThreatFeedUpdate


class ThreatFeedService:
    FETCH_TIMEOUT_SECONDS = 30.0

    def __init__(self, settings: Settings, db: Session) -> None:
        self.settings = settings
        self.db = db

    def list_feeds(self) -> List[ThreatFeedResponse]:
        return [self._to_response(row) for row in self.db.query(ThreatFeed).order_by(ThreatFeed.id).all()]

    def get(self, feed_id: int) -> Optional[ThreatFeedResponse]:
        row = self.db.get(ThreatFeed, feed_id)
        return self._to_response(row) if row else None

    def create(self, payload: ThreatFeedCreate) -> ThreatFeedResponse:
        row = ThreatFeed(
            name=payload.name,
            url=payload.url,
            feed_type=payload.feed_type,
            enabled=payload.enabled,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._to_response(row)

    def update(self, feed_id: int, payload: ThreatFeedUpdate) -> Optional[ThreatFeedResponse]:
        row = self.db.get(ThreatFeed, feed_id)
        if row is None:
            return None
        if payload.name is not None:
            row.name = payload.name
        if payload.url is not None:
            row.url = payload.url
        if payload.feed_type is not None:
            row.feed_type = payload.feed_type
        if payload.enabled is not None:
            row.enabled = payload.enabled
        self.db.commit()
        self.db.refresh(row)
        return self._to_response(row)

    def delete(self, feed_id: int) -> bool:
        row = self.db.get(ThreatFeed, feed_id)
        if row is None:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    def sync_feed(self, feed_id: int) -> ThreatFeedResponse:
        row = self.db.get(ThreatFeed, feed_id)
        if row is None:
            raise ValueError("Feed not found")
        try:
            ips = self._fetch_ips(row)
            self._write_feed_file(row, ips)
            row.ip_count = len(ips)
            row.last_sync_at = datetime.now(timezone.utc).replace(tzinfo=None)
            row.last_error = None
        except Exception as exc:
            row.last_error = str(exc)
            self.db.commit()
            raise
        self.db.commit()
        self.db.refresh(row)
        return self._to_response(row)

    def sync_all(self) -> int:
        count = 0
        feeds = self.db.query(ThreatFeed).filter(ThreatFeed.enabled.is_(True)).all()
        for feed in feeds:
            try:
                self.sync_feed(feed.id)
                count += 1
            except Exception:
                continue
        self._write_combined_deny_file()
        return count

    def _fetch_ips(self, feed: ThreatFeed) -> Set[str]:
        with httpx.Client(timeout=self.FETCH_TIMEOUT_SECONDS) as client:
            response = client.get(feed.url)
            response.raise_for_status()
            text = response.text
        ips: Set[str] = set()
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if feed.feed_type == "cidr":
                ips.add(line.split()[0])
            else:
                ips.add(line.split()[0])
        return ips

    def _feed_file_path(self, feed: ThreatFeed) -> str:
        return str(self.settings.security_dir / f"threat-feed-{feed.id}.conf")

    def _write_feed_file(self, feed: ThreatFeed, ips: Set[str]) -> None:
        self.settings.security_dir.mkdir(parents=True, exist_ok=True)
        lines = [f"# Threat feed: {feed.name}", "# Managed by reverse-proxy-admin"]
        for ip in sorted(ips):
            lines.append(f"deny {ip};")
        path = self.settings.security_dir / f"threat-feed-{feed.id}.conf"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_combined_deny_file(self) -> None:
        self.settings.security_dir.mkdir(parents=True, exist_ok=True)
        lines = ["# Combined threat feed deny list", "# Managed by reverse-proxy-admin"]
        feeds = (
            self.db.query(ThreatFeed)
            .filter(ThreatFeed.enabled.is_(True), ThreatFeed.ip_count > 0)
            .order_by(ThreatFeed.id)
            .all()
        )
        for feed in feeds:
            path = self.settings.security_dir / f"threat-feed-{feed.id}.conf"
            if path.exists():
                lines.append(f"include {path};")
        combined = self.settings.security_dir / "threat-feeds.conf"
        combined.write_text("\n".join(lines) + "\n", encoding="utf-8")

    @staticmethod
    def _to_response(row: ThreatFeed) -> ThreatFeedResponse:
        return ThreatFeedResponse(
            id=row.id,
            name=row.name,
            url=row.url,
            feed_type=row.feed_type,
            enabled=row.enabled,
            last_sync_at=row.last_sync_at,
            ip_count=row.ip_count,
            last_error=row.last_error,
        )
