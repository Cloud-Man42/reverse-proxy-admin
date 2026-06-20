import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from jinja2 import Environment, StrictUndefined

from app.config import Settings
from app.models.backend_pool import BackendPool
from app.models.geo_rule import GeoRule
from app.models.ip_access_rule import IpAccessRule
from app.models.proxy_rate_limit import ProxyRateLimit
from app.models.proxy_waf_settings import ProxyWafSettings
from app.schemas import ProxyAppBase, ProxyRoute
from app.services.cert_paths import certificate_paths
from app.services.file_lock import file_lock
from app.services.load_balancer_service import LoadBalancerService
from app.services.path_guard import ensure_path_allowed, safe_join


PROXY_DEBUG_LOG_FORMAT = (
    "log_format proxy_debug "
    "'$remote_addr|$time_local|$host|$request|$status|$body_bytes_sent|"
    "$request_length|$upstream_bytes_received|$upstream_bytes_sent|"
    "$http_x_forwarded_for|$http_user_agent|$request_time|$upstream_response_time';"
)


CONFIG_TEMPLATE = """{% if rate_limit_zone -%}
{{ rate_limit_zone }}

{% endif -%}{% if upstream_blocks -%}
{{ upstream_blocks }}

{% endif -%}{% if global_ip_include -%}
include {{ global_ip_include }};

{% endif -%}{% if threat_feed_include -%}
include {{ threat_feed_include }};

{% endif -%}
{% if app.force_https -%}
server {
    listen 80;
    server_name {{ app.domains | join(' ') }};
    access_log /var/log/nginx/proxy-{{ app.name }}.log proxy_debug;
    return 301 https://$host$request_uri;
}

{% endif -%}
server {
{% if app.force_https -%}
    listen 443 ssl;
    ssl_certificate {{ ssl_certificate }};
    ssl_certificate_key {{ ssl_certificate_key }};
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
{% else -%}
    listen 80;
{% endif -%}
    server_name {{ app.domains | join(' ') }};
    access_log /var/log/nginx/proxy-{{ app.name }}.log proxy_debug;

{% if app.max_body_size -%}
    client_max_body_size {{ app.max_body_size }};
{% endif -%}
{% if app.basic_auth_enabled -%}
    auth_basic "Restricted";
    auth_basic_user_file {{ htpasswd_path }};
{% endif -%}
{% if ip_access_directives -%}
{{ ip_access_directives }}
{% endif -%}
{% if geo_include -%}
    include {{ geo_include }};
{% endif -%}
{% if waf_include -%}
    modsecurity on;
    modsecurity_rules_file {{ waf_include }};
{% endif -%}
{% for route in routes -%}
    location {{ route.location }} {
{% if rate_limit_zone -%}
        limit_req zone={{ rate_limit_zone_name }} burst={{ rate_limit_burst }}{% if rate_limit_nodelay %} nodelay{% endif %};

{% endif -%}
        proxy_pass {{ route.proxy_pass }};

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
{% if route.websocket_enabled -%}

        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
{% endif -%}
{% for header in app.custom_headers -%}
        proxy_set_header {{ header.name }} {{ header.value }};
{% endfor -%}
    }
{% endfor -%}
}
"""


class BackupManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.settings.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, path: Path) -> Optional[Path]:
        if not path.exists():
            return None
        ensure_path_allowed(path, self.settings.allowed_read_paths())
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        backup_path = safe_join(
            self.settings.backup_dir,
            f"{timestamp}_{path.name}",
            allowed_roots=self.settings.allowed_write_paths(),
            for_write=True,
        )
        shutil.copy2(path, backup_path)
        return backup_path

    def restore_backup(self, backup_path: Path, target_path: Path) -> None:
        ensure_path_allowed(backup_path, self.settings.allowed_read_paths())
        ensure_path_allowed(target_path, self.settings.allowed_write_paths(), for_write=True)
        shutil.copy2(backup_path, target_path)


class NginxWriter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.backup_manager = BackupManager(settings)
        self.env = Environment(undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)

    def config_path_for(self, slug: str) -> Path:
        return safe_join(
            self.settings.nginx_sites_available,
            f"{slug}.conf",
            allowed_roots=self.settings.allowed_write_paths(),
            for_write=True,
        )

    @staticmethod
    def route_upstream(route: ProxyRoute) -> str:
        if route.target_host is None or route.target_port is None:
            return "pool"
        return f"{route.target_protocol.value}://{route.target_host}:{route.target_port}"

    @staticmethod
    def route_location_and_pass(route: ProxyRoute) -> tuple[str, str]:
        if route.target_host is None or route.target_port is None:
            return route.path_prefix if route.path_prefix != "/" else "/", "http://127.0.0.1"
        upstream = NginxWriter.route_upstream(route)
        if route.path_prefix == "/":
            return "/", upstream
        return f"{route.path_prefix}/", f"{upstream}/"

    def render_routes(
        self,
        app: ProxyAppBase,
        route_pools: Optional[dict[int, BackendPool]] = None,
        proxy_slug: Optional[str] = None,
    ) -> list[dict]:
        rendered: list[dict] = []
        route_pools = route_pools or {}
        slug = proxy_slug or app.name
        lb = LoadBalancerService(self.settings)
        sorted_routes = sorted(
            enumerate(app.routes),
            key=lambda item: len(item[1].path_prefix),
            reverse=True,
        )
        for orig_idx, route in sorted_routes:
            pool = route_pools.get(orig_idx)
            if pool and pool.enabled:
                upstream_name = lb.upstream_name(slug, orig_idx)
                protocol = lb.pool_protocol(pool)
                if route.path_prefix == "/":
                    location, proxy_pass = "/", f"{protocol}://{upstream_name}"
                else:
                    location, proxy_pass = f"{route.path_prefix}/", f"{protocol}://{upstream_name}/"
            else:
                location, proxy_pass = self.route_location_and_pass(route)
            rendered.append(
                {
                    "location": location,
                    "proxy_pass": proxy_pass,
                    "websocket_enabled": route.websocket_enabled,
                }
            )
        return rendered

    def render_upstream_blocks(
        self,
        app: ProxyAppBase,
        route_pools: dict[int, BackendPool],
        proxy_slug: Optional[str] = None,
    ) -> str:
        slug = proxy_slug or app.name
        lb = LoadBalancerService(self.settings)
        blocks: list[str] = []
        for idx, pool in route_pools.items():
            if pool and pool.enabled:
                name = lb.upstream_name(slug, idx)
                lb.validate_pool(pool)
                blocks.append(lb.render_upstream_block(pool, name))
        return "\n\n".join(blocks)

    def render_rate_limit(self, proxy_slug: str, rate_limit: Optional[ProxyRateLimit]) -> dict[str, object]:
        if not rate_limit or not rate_limit.enabled:
            return {
                "rate_limit_zone": "",
                "rate_limit_zone_name": "",
                "rate_limit_burst": 0,
                "rate_limit_nodelay": False,
            }
        zone_name = f"{proxy_slug}_rl"
        key = "$binary_remote_addr" if rate_limit.key_type == "client_ip" else "$uri"
        rate = f"{rate_limit.requests_per_minute}r/m"
        zone = f"limit_req_zone {key} zone={zone_name}:10m rate={rate};"
        return {
            "rate_limit_zone": zone,
            "rate_limit_zone_name": zone_name,
            "rate_limit_burst": rate_limit.burst,
            "rate_limit_nodelay": rate_limit.nodelay,
        }

    def write_global_ip_access(self, rules: list[IpAccessRule]) -> None:
        from app.services.ip_access_service import IpAccessService

        self.settings.security_dir.mkdir(parents=True, exist_ok=True)
        path = self.settings.security_dir / "global-ip-access.conf"
        content = IpAccessService.render_global_include(rules)
        if content:
            path.write_text(content, encoding="utf-8")
        elif path.exists():
            path.unlink()

    @staticmethod
    def render_ip_access(ip_rules: Optional[list[IpAccessRule]]) -> str:
        from app.services.ip_access_service import IpAccessService

        if not ip_rules:
            return ""
        return IpAccessService.render_nginx_directives(ip_rules)

    def render_security_includes(
        self,
        proxy_slug: str,
        *,
        ip_rules: Optional[list[IpAccessRule]] = None,
        geo_rule: Optional[GeoRule] = None,
        waf_settings: Optional[ProxyWafSettings] = None,
    ) -> dict[str, object]:
        global_path = self.settings.security_dir / "global-ip-access.conf"
        threat_path = self.settings.security_dir / "threat-feeds.conf"
        geo_path = self.settings.security_dir / f"geo-{proxy_slug}.conf"
        waf_path = self.settings.security_dir / f"waf-{proxy_slug}.conf"
        return {
            "global_ip_include": str(global_path) if global_path.exists() else "",
            "threat_feed_include": str(threat_path) if threat_path.exists() else "",
            "ip_access_directives": self.render_ip_access(ip_rules),
            "geo_include": str(geo_path) if geo_rule and geo_rule.enabled and geo_path.exists() else "",
            "waf_include": str(waf_path) if waf_settings and waf_settings.enabled and waf_path.exists() else "",
        }

    def render_config(
        self,
        app: ProxyAppBase,
        route_pools: Optional[dict[int, BackendPool]] = None,
        proxy_slug: Optional[str] = None,
        rate_limit: Optional[ProxyRateLimit] = None,
        ip_rules: Optional[list[IpAccessRule]] = None,
        geo_rule: Optional[GeoRule] = None,
        waf_settings: Optional[ProxyWafSettings] = None,
        ssl_certificate: Optional[str] = None,
        ssl_certificate_key: Optional[str] = None,
    ) -> str:
        route_pools = route_pools or {}
        slug = proxy_slug or app.name
        htpasswd_path = self.settings.htpasswd_dir / f"{app.name}.htpasswd"
        if app.force_https:
            if not ssl_certificate or not ssl_certificate_key:
                cert_path, key_path = certificate_paths(self.settings, app.domains[0])
                ssl_certificate = str(cert_path)
                ssl_certificate_key = str(key_path)
        template = self.env.from_string(CONFIG_TEMPLATE)
        return template.render(
            app=app,
            routes=self.render_routes(app, route_pools, slug),
            upstream_blocks=self.render_upstream_blocks(app, route_pools, slug),
            htpasswd_path=str(htpasswd_path),
            ssl_certificate=ssl_certificate,
            ssl_certificate_key=ssl_certificate_key,
            **self.render_rate_limit(slug, rate_limit),
            **self.render_security_includes(
                slug,
                ip_rules=ip_rules,
                geo_rule=geo_rule,
                waf_settings=waf_settings,
            ),
        )

    def write_htpasswd(self, app: ProxyAppBase) -> None:
        if not app.basic_auth_enabled:
            return
        if not app.basic_auth_username or not app.basic_auth_password:
            raise ValueError("Basic auth username and password are required")
        self.settings.htpasswd_dir.mkdir(parents=True, exist_ok=True)
        htpasswd_path = safe_join(
            self.settings.htpasswd_dir,
            f"{app.name}.htpasswd",
            allowed_roots=self.settings.allowed_write_paths(),
            for_write=True,
        )
        import subprocess

        result = subprocess.run(
            [
                "htpasswd",
                "-bc",
                str(htpasswd_path),
                app.basic_auth_username,
                app.basic_auth_password,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr or "Failed to create htpasswd file")

    def atomic_write(self, path: Path, content: str) -> None:
        ensure_path_allowed(path, self.settings.allowed_write_paths(), for_write=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(content, encoding="utf-8")
        os.replace(temp_path, path)

    def apply_change(self, path: Path, write_fn: Callable[[], None], nginx_test_fn: Callable[[], tuple[bool, str]]) -> tuple[bool, str]:
        backup = self.backup_manager.create_backup(path) if path.exists() else None
        with file_lock(path):
            write_fn()
            ok, output = nginx_test_fn()
            if not ok:
                if backup and path.exists():
                    self.backup_manager.restore_backup(backup, path)
                elif backup is None and path.exists():
                    path.unlink(missing_ok=True)
                return False, output
            return True, output
