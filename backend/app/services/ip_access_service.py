from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.ip_access_rule import IpAccessRule
from app.models.security_event import SecurityEvent
from app.schemas import IpAccessRuleCreate, IpAccessRuleResponse, IpAccessRuleUpdate


class IpAccessService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_rules(
        self,
        *,
        scope: Optional[str] = None,
        proxy_id: Optional[str] = None,
    ) -> List[IpAccessRuleResponse]:
        query = self.db.query(IpAccessRule)
        if scope:
            query = query.filter(IpAccessRule.scope == scope)
        if proxy_id is not None:
            query = query.filter(IpAccessRule.proxy_id == proxy_id)
        return [self._to_response(row) for row in query.order_by(IpAccessRule.id).all()]

    def get(self, rule_id: int) -> Optional[IpAccessRuleResponse]:
        row = self.db.get(IpAccessRule, rule_id)
        return self._to_response(row) if row else None

    def create(self, payload: IpAccessRuleCreate) -> IpAccessRuleResponse:
        row = IpAccessRule(
            scope=payload.scope,
            proxy_id=payload.proxy_id,
            rule_type=payload.rule_type,
            cidr=payload.cidr,
            enabled=payload.enabled,
            notes=payload.notes,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._to_response(row)

    def update(self, rule_id: int, payload: IpAccessRuleUpdate) -> Optional[IpAccessRuleResponse]:
        row = self.db.get(IpAccessRule, rule_id)
        if row is None:
            return None
        if payload.scope is not None:
            row.scope = payload.scope
        if payload.proxy_id is not None:
            row.proxy_id = payload.proxy_id
        if payload.rule_type is not None:
            row.rule_type = payload.rule_type
        if payload.cidr is not None:
            row.cidr = payload.cidr
        if payload.enabled is not None:
            row.enabled = payload.enabled
        if payload.notes is not None:
            row.notes = payload.notes
        self.db.commit()
        self.db.refresh(row)
        return self._to_response(row)

    def delete(self, rule_id: int) -> bool:
        row = self.db.get(IpAccessRule, rule_id)
        if row is None:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    def rules_for_proxy(self, proxy_id: str) -> List[IpAccessRule]:
        global_rules = (
            self.db.query(IpAccessRule)
            .filter(IpAccessRule.scope == "global", IpAccessRule.enabled.is_(True))
            .all()
        )
        proxy_rules = (
            self.db.query(IpAccessRule)
            .filter(
                IpAccessRule.scope == "proxy",
                IpAccessRule.proxy_id == proxy_id,
                IpAccessRule.enabled.is_(True),
            )
            .all()
        )
        return global_rules + proxy_rules

    @staticmethod
    def render_nginx_directives(rules: List[IpAccessRule]) -> str:
        if not rules:
            return ""
        lines: List[str] = []
        for rule in rules:
            if not rule.enabled:
                continue
            action = "allow" if rule.rule_type == "allow" else "deny"
            lines.append(f"    {action} {rule.cidr};")
        return "\n".join(lines)

    @staticmethod
    def render_global_include(rules: List[IpAccessRule]) -> str:
        enabled = [rule for rule in rules if rule.enabled and rule.scope == "global"]
        if not enabled:
            return ""
        lines = ["# Global IP access rules (managed by reverse-proxy-admin)"]
        for rule in enabled:
            action = "allow" if rule.rule_type == "allow" else "deny"
            lines.append(f"{action} {rule.cidr};")
        return "\n".join(lines) + "\n"

    def log_block_event(
        self,
        *,
        client_ip: str,
        proxy_id: Optional[str],
        message: str,
    ) -> SecurityEvent:
        event = SecurityEvent(
            event_type="ip_blocked",
            source="ip_access",
            client_ip=client_ip,
            proxy_id=proxy_id,
            message=message,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    @staticmethod
    def _to_response(row: IpAccessRule) -> IpAccessRuleResponse:
        return IpAccessRuleResponse(
            id=row.id,
            scope=row.scope,
            proxy_id=row.proxy_id,
            rule_type=row.rule_type,
            cidr=row.cidr,
            enabled=row.enabled,
            notes=row.notes,
        )
