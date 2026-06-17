import re
import subprocess
from dataclasses import dataclass, field
from typing import List

from app.config import Settings


@dataclass
class FirewallRule:
    port: str
    protocol: str
    source: str
    action: str = "ALLOW"


@dataclass
class FirewallStatus:
    active: bool
    rules: List[FirewallRule] = field(default_factory=list)
    source: str = "fallback"


RULE_LINE_RE = re.compile(
    r"^\[\s*\d+\]\s+(\d+(?:,\d+)*)/?(tcp|udp)?\s+(\w+)\s+(?:IN\s+)?(.+)$",
    re.IGNORECASE,
)


class FirewallService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _cmd(self, *args: str) -> list[str]:
        if self.settings.use_sudo:
            return ["sudo", *args]
        return list(args)

    def _parse_ufw_output(self, output: str) -> List[FirewallRule]:
        rules: List[FirewallRule] = []
        for line in output.splitlines():
            line = line.strip()
            if not line.startswith("["):
                continue
            match = RULE_LINE_RE.match(line)
            if not match:
                continue
            ports, proto, action, source = match.groups()
            rules.append(
                FirewallRule(
                    port=ports,
                    protocol=(proto or "tcp").lower(),
                    source=source.strip(),
                    action=action.upper(),
                )
            )
        return rules

    def _fallback_rules(self) -> FirewallStatus:
        rules: List[FirewallRule] = []
        for port in self.settings.network_exposed_ports:
            for subnet in self.settings.allowed_ips:
                if "/" in subnet or subnet.count(".") >= 3:
                    rules.append(FirewallRule(port=str(port), protocol="tcp", source=subnet))
                elif port in (80, 443):
                    rules.append(FirewallRule(port=str(port), protocol="tcp", source="Anywhere"))
        if not rules:
            for port in self.settings.network_exposed_ports:
                rules.append(FirewallRule(port=str(port), protocol="tcp", source="Anywhere"))
        return FirewallStatus(active=True, rules=rules, source="fallback")

    def get_status(self) -> FirewallStatus:
        try:
            result = subprocess.run(
                self._cmd("ufw", "status", "numbered"),
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            return self._fallback_rules()

        output = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0 or "Status: active" not in output:
            return self._fallback_rules()

        rules = self._parse_ufw_output(output)
        if not rules:
            fallback = self._fallback_rules()
            fallback.active = True
            fallback.source = "ufw_empty"
            return fallback

        return FirewallStatus(active=True, rules=rules, source="ufw")
