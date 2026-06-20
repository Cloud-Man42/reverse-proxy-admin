from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ProxyTemplate(Base):
    __tablename__ = "proxy_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    defaults_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    builtin: Mapped[bool] = mapped_column(Boolean, default=False)
