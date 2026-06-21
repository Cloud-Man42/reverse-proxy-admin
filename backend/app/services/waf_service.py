from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from app.config import Settings
from app.models.proxy_waf_settings import ProxyWafSettings
from app.schemas import ProxyWafSettingsResponse, ProxyWafSettingsUpdate

CRS_BASE_PATH = Path("/etc/nginx/modsecurity/crs-base.conf")
PROFILE_PARANOIA = {"low": 1, "medium": 2, "high": 3}


class WafService:
    def __init__(self, settings: Settings, db: Session) -> None:
        self.settings = settings
        self.db = db

    @staticmethod
    def _defaults(proxy_id: str) -> ProxyWafSettings:
        return ProxyWafSettings(
            proxy_id=proxy_id,
            enabled=False,
            mode="detection",
            profile="medium",
            exclusions_json="[]",
        )

    def _normalize_row(self, row: ProxyWafSettings) -> ProxyWafSettings:
        changed = False
        if row.enabled is None:
            row.enabled = False
            changed = True
        if not row.mode:
            row.mode = "detection"
            changed = True
        if not row.profile:
            row.profile = "medium"
            changed = True
        if changed:
            self.db.commit()
            self.db.refresh(row)
        return row

    def get(self, proxy_id: str) -> ProxyWafSettingsResponse:
        row = self.db.get(ProxyWafSettings, proxy_id)
        if row is None:
            row = self._defaults(proxy_id)
        else:
            row = self._normalize_row(row)
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

    @staticmethod
    def modsecurity_ready() -> bool:
        return CRS_BASE_PATH.is_file()

    def render_snippet(self, settings: Optional[ProxyWafSettings]) -> str:
        if not settings or not settings.enabled:
            return ""
        if not self.modsecurity_ready():
            return ""
        mode = "DetectionOnly" if settings.mode == "detection" else "On"
        paranoia = PROFILE_PARANOIA.get(settings.profile, 2)
        lines = [
            f"# WAF settings for {settings.proxy_id} (managed by In a Cloud Gateway)",
            f"SecRuleEngine {mode}",
            (
                "SecAction "
                f'"id:900120,phase:1,pass,nolog,setvar:tx.paranoia_level={paranoia},'
                f'setvar:tx.executing_paranoia_level={paranoia}"'
            ),
            f"Include {CRS_BASE_PATH.as_posix()}",
        ]
        for rule_id in settings.exclusions:
            cleaned = str(rule_id).strip()
            if cleaned:
                lines.append(f"SecRuleRemoveById {cleaned}")
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
        defaults = WafService._defaults(row.proxy_id)
        return ProxyWafSettingsResponse(
            proxy_id=row.proxy_id,
            enabled=bool(defaults.enabled if row.enabled is None else row.enabled),
            mode=row.mode or defaults.mode,
            profile=row.profile or defaults.profile,
            exclusions=row.exclusions,
        )
