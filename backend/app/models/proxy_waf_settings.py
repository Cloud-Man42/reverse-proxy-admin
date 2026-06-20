import json
from typing import List

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ProxyWafSettings(Base):
    __tablename__ = "proxy_waf_settings"

    proxy_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mode: Mapped[str] = mapped_column(String(16), default="detection")
    profile: Mapped[str] = mapped_column(String(16), default="medium")
    exclusions_json: Mapped[str] = mapped_column(Text, default="[]")

    @property
    def exclusions(self) -> List[str]:
        try:
            data = json.loads(self.exclusions_json or "[]")
            return [str(item) for item in data]
        except (TypeError, json.JSONDecodeError):
            return []

    @exclusions.setter
    def exclusions(self, value: List[str]) -> None:
        self.exclusions_json = json.dumps(list(value))
