from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol


RANGE_SECONDS = {
    "15m": 15 * 60,
    "1h": 3600,
    "24h": 86400,
    "7d": 7 * 86400,
    "30d": 30 * 86400,
}


@dataclass
class TimeRange:
    key: str
    start: datetime
    end: datetime
    seconds: float


def resolve_range(range_key: str, *, now: datetime | None = None) -> TimeRange:
    current = now or datetime.utcnow()
    seconds = RANGE_SECONDS.get(range_key, RANGE_SECONDS["24h"])
    return TimeRange(key=range_key, start=current - timedelta(seconds=seconds), end=current, seconds=seconds)


class MetricsProvider(Protocol):
    def supported_ranges(self) -> list[str]: ...
