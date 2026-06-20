from typing import List, Optional

from sqlalchemy.orm import Session

from app.config import Settings
from app.models.proxy_waf_settings import ProxyWafSettings
from app.schemas import ProxyWafSettingsResponse, ProxyWafSettingsUpdate


class WafService:
    def __init__(self, settings: Settings, db: Session) -> None:
        self.settings = settings
        self.db = db

    @staticmethod
    def _defaults(proxy_id: str) -> ProxyWafSettings:
        return ProxyWafSettings(proxy_id=proxy_id)

    def get(self, proxy_id: str) -> ProxyWafSettingsResponse:
        row = self.db.get(ProxyWafSettings, proxy_id)
        if row is None:
            row = self._defaults(proxy_id)
        return self._to_response(row)

    def get_model(self, proxy_id: str) -> ProxyWafSettings:
        row = self.db.get(ProxyWafSettings, proxy_id)
        if row is None:
            row = self._defaults(proxy_id)
            self.db.add(row)
            self.db.flush()
        return row

    def upsert(self, proxy_id: str, payload: ProxyWafSettingsUpdate) -> ProxyWafSettingsResponse:
        row = self.db.get(ProxyWafSettings, proxy_id)
        if row is None:
            row = ProxyWafSettings(proxy_id=proxy_id)
            self.db.add(row)
        row.enabled = payload.enabled
        row.mode = payload.mode
        row.profile = payload.profile
        row.exclusions = payload.exclusions
        self.db.commit()
        self.db.refresh(row)
        self.write_include(row)
        return self._to_response(row)

    def delete(self, proxy_id: str) -> None:
        row = self.db.get(ProxyWafSettings, proxy_id)
        if row is not None:
            self.db.delete(row)
            self.db.commit()
        path = self.settings.security_dir / f"waf-{proxy_id}.conf"
        if path.exists():
            path.unlink()

    def include_path(self, proxy_id: str) -> str:
        return str(self.settings.security_dir / f"waf-{proxy_id}.conf")

    def render_snippet(self, settings: Optional[ProxyWafSettings]) -> str:
        if not settings or not settings.enabled:
            return ""
        mode = "DetectionOnly" if settings.mode == "detection" else "On"
        lines = [
            f"# WAF settings for {settings.proxy_id} (managed by In a Cloud Gateway)",
            f"SecRuleEngine {mode}",
            f"# Profile: {settings.profile}",
        ]
        for rule_id in settings.exclusions:
            lines.append(f"SecRuleRemoveById {rule_id}")
        return "\n".join(lines) + "\n"

    def write_include(self, settings: ProxyWafSettings) -> None:
        path = self.settings.security_dir / f"waf-{settings.proxy_id}.conf"
        self.settings.security_dir.mkdir(parents=True, exist_ok=True)
        content = self.render_snippet(settings)
        if content:
            path.write_text(content, encoding="utf-8")
        elif path.exists():
            path.unlink()

    @staticmethod
    def _to_response(row: ProxyWafSettings) -> ProxyWafSettingsResponse:
        return ProxyWafSettingsResponse(
            proxy_id=row.proxy_id,
            enabled=row.enabled,
            mode=row.mode,
            profile=row.profile,
            exclusions=row.exclusions,
        )
