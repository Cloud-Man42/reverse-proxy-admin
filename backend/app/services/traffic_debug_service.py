from typing import List, Optional

from app.config import Settings
from app.schemas import TrafficDebugEntry, TrafficDebugResponse
from app.services.access_log_parser import ParsedAccessEntry, entry_matches_domains, parse_access_line
from app.services.log_reader import LogReader
from app.services.proxy_service import ProxyService


class TrafficDebugService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.reader = LogReader(settings)
        self.proxies = ProxyService(settings)

    def proxy_log_path(self, proxy_id: str) -> str:
        return str(self.settings.nginx_access_log.parent / f"proxy-{proxy_id}.log")

    def _to_entry(self, parsed: ParsedAccessEntry) -> TrafficDebugEntry:
        return TrafficDebugEntry(
            client_ip=parsed.client_ip,
            timestamp=parsed.timestamp_raw,
            host=parsed.host,
            method=parsed.method,
            path=parsed.path,
            status=parsed.status,
            bytes_sent=parsed.bytes_sent,
            forwarded_for=parsed.forwarded_for,
            user_agent=parsed.user_agent,
        )

    def read_proxy_traffic(self, proxy_id: str, lines: int = 100) -> TrafficDebugResponse:
        proxy = self.proxies.get_proxy(proxy_id)
        if not proxy:
            raise ValueError("Proxy not found")

        per_proxy_log = self.settings.nginx_access_log.parent / f"proxy-{proxy_id}.log"
        source = str(per_proxy_log)
        dedicated_log = per_proxy_log.exists()

        if dedicated_log:
            raw_lines = self.reader.read_lines(per_proxy_log, lines=max(lines * 3, 300))
        else:
            raw_lines = self.reader.read_access_log(lines=max(lines * 10, 1000), domain=None)
            source = str(self.settings.nginx_access_log)

        parsed_entries: List[TrafficDebugEntry] = []
        for line in raw_lines:
            parsed = parse_access_line(line)
            if not parsed:
                continue
            if not dedicated_log and not entry_matches_domains(parsed, proxy.domains):
                if not any(domain.lower() in line.lower() for domain in proxy.domains):
                    continue
            parsed_entries.append(self._to_entry(parsed))

        return TrafficDebugResponse(
            proxy_id=proxy.id,
            proxy_name=proxy.name,
            domains=proxy.domains,
            dedicated_log=dedicated_log,
            source=source,
            entries=parsed_entries[-lines:],
        )
