import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from jinja2 import Environment, StrictUndefined

from app.config import Settings
from app.schemas import ProxyAppBase, ProxyRoute
from app.services.file_lock import file_lock
from app.services.path_guard import ensure_path_allowed, safe_join


PROXY_DEBUG_LOG_FORMAT = (
    "log_format proxy_debug "
    "'$remote_addr|$time_local|$host|$request|$status|$body_bytes_sent|$http_x_forwarded_for|$http_user_agent';"
)


CONFIG_TEMPLATE = """{% if app.force_https -%}
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
    ssl_certificate /etc/letsencrypt/live/{{ app.domains[0] }}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{{ app.domains[0] }}/privkey.pem;
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
{% for route in routes -%}
    location {{ route.location }} {
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
        return f"{route.target_protocol.value}://{route.target_host}:{route.target_port}"

    @staticmethod
    def route_location_and_pass(route: ProxyRoute) -> tuple[str, str]:
        upstream = NginxWriter.route_upstream(route)
        if route.path_prefix == "/":
            return "/", upstream
        return f"{route.path_prefix}/", f"{upstream}/"

    def render_routes(self, app: ProxyAppBase) -> list[dict]:
        rendered: list[dict] = []
        sorted_routes = sorted(
            app.routes,
            key=lambda route: len(route.path_prefix),
            reverse=True,
        )
        for route in sorted_routes:
            location, proxy_pass = self.route_location_and_pass(route)
            rendered.append(
                {
                    "location": location,
                    "proxy_pass": proxy_pass,
                    "websocket_enabled": route.websocket_enabled,
                }
            )
        return rendered

    def render_config(self, app: ProxyAppBase) -> str:
        htpasswd_path = self.settings.htpasswd_dir / f"{app.name}.htpasswd"
        template = self.env.from_string(CONFIG_TEMPLATE)
        return template.render(
            app=app,
            routes=self.render_routes(app),
            htpasswd_path=str(htpasswd_path),
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
