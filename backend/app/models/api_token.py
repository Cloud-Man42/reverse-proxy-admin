from datetime import datetime
import json

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ApiToken(Base):
    __tablename__ = "api_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    token_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    scopes_json: Mapped[str] = mapped_column(Text, default="[]")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )

    @property
    def scopes(self) -> list[str]:
        return json.loads(self.scopes_json or "[]")

    @scopes.setter
    def scopes(self, value: list[str]) -> None:
        self.scopes_json = json.dumps(value)

    def has_scope(self, scope: str) -> bool:
        token_scopes = self.scopes
        if "admin" in token_scopes:
            return True
        return scope in token_scopes

    def is_valid(self) -> bool:
        if self.revoked:
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return True