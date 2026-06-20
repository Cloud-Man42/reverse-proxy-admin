from typing import List, Optional

from sqlalchemy.orm import Session

from app.config import Settings
from app.models.geo_rule import GeoRule
from app.schemas import GeoRuleCreate, GeoRuleResponse, GeoRuleUpdate


class GeoIpService:
    def __init__(self, settings: Settings, db: Session) -> None:
        self.settings = settings
        self.db = db

    def list_rules(self, proxy_id: Optional[str] = None) -> List[GeoRuleResponse]:
        query = self.db.query(GeoRule)
        if proxy_id:
            query = query.filter(GeoRule.proxy_id == proxy_id)
        return [self._to_response(row) for row in query.order_by(GeoRule.id).all()]

    def get(self, rule_id: int) -> Optional[GeoRuleResponse]:
        row = self.db.get(GeoRule, rule_id)
        return self._to_response(row) if row else None

    def get_for_proxy(self, proxy_id: str) -> Optional[GeoRule]:
        return (
            self.db.query(GeoRule)
            .filter(GeoRule.proxy_id == proxy_id, GeoRule.enabled.is_(True))
            .first()
        )

    def create(self, payload: GeoRuleCreate) -> GeoRuleResponse:
        row = GeoRule(
            proxy_id=payload.proxy_id,
            mode=payload.mode,
            default_policy=payload.default_policy,
            enabled=payload.enabled,
        )
        row.countries = payload.countries
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._to_response(row)

    def update(self, rule_id: int, payload: GeoRuleUpdate) -> Optional[GeoRuleResponse]:
        row = self.db.get(GeoRule, rule_id)
        if row is None:
            return None
        if payload.proxy_id is not None:
            row.proxy_id = payload.proxy_id
        if payload.mode is not None:
            row.mode = payload.mode
        if payload.countries is not None:
            row.countries = payload.countries
        if payload.default_policy is not None:
            row.default_policy = payload.default_policy
        if payload.enabled is not None:
            row.enabled = payload.enabled
        self.db.commit()
        self.db.refresh(row)
        return self._to_response(row)

    def delete(self, rule_id: int) -> bool:
        row = self.db.get(GeoRule, rule_id)
        if row is None:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    def include_path(self, proxy_id: str) -> str:
        return str(self.settings.security_dir / f"geo-{proxy_id}.conf")

    def render_snippet(self, rule: Optional[GeoRule]) -> str:
        if not rule or not rule.enabled:
            return ""
        countries = rule.countries
        if not countries:
            return ""
        lines = [
            f"# Geo blocking for {rule.proxy_id} (managed by In a Cloud Gateway)",
            "geoip2 /usr/share/GeoIP/GeoLite2-Country.mmdb {",
            "    $geoip2_country_code country iso_code;",
            "}",
        ]
        if rule.mode == "block":
            for code in countries:
                lines.append(f'if ($geoip2_country_code = "{code}") {{ return 403; }}')
        else:
            allowed = "|".join(countries)
            lines.append(f'if ($geoip2_country_code !~ "^({allowed})$") {{ return 403; }}')
        return "\n".join(lines) + "\n"

    def write_include(self, proxy_id: str, rule: Optional[GeoRule]) -> None:
        path = self.settings.security_dir / f"geo-{proxy_id}.conf"
        self.settings.security_dir.mkdir(parents=True, exist_ok=True)
        content = self.render_snippet(rule)
        if content:
            path.write_text(content, encoding="utf-8")
        elif path.exists():
            path.unlink()

    @staticmethod
    def _to_response(row: GeoRule) -> GeoRuleResponse:
        return GeoRuleResponse(
            id=row.id,
            proxy_id=row.proxy_id,
            mode=row.mode,
            countries=row.countries,
            default_policy=row.default_policy,
            enabled=row.enabled,
        )
