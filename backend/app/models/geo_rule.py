import json
from typing import List

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class GeoRule(Base):
    __tablename__ = "geo_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proxy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    countries_json: Mapped[str] = mapped_column(Text, default="[]")
    default_policy: Mapped[str] = mapped_column(String(16), default="allow")
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    @property
    def countries(self) -> List[str]:
        try:
            data = json.loads(self.countries_json or "[]")
            return [str(item).upper() for item in data]
        except (TypeError, json.JSONDecodeError):
            return []

    @countries.setter
    def countries(self, value: List[str]) -> None:
        self.countries_json = json.dumps([str(item).upper() for item in value])
