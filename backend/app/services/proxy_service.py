from typing import Optional

from app.config import Settings
from app.schemas import ProxyAppBase, ProxyAppCreate, ProxyAppResponse, ProxyAppUpdate
from app.services.nginx_ops import NginxOps
from app.services.nginx_parser import ParsedProxyConfig, list_proxy_configs, parse_config_file
from app.services.nginx_writer import NginxWriter


def parsed_to_response(parsed: ParsedProxyConfig) -> ProxyAppResponse:
    return ProxyAppResponse(
        id=parsed.slug,
        name=parsed.slug,
        config_file=parsed.config_file,
        domains=parsed.domains,
        target_protocol=parsed.target_protocol,
        target_host=parsed.target_host,
        target_port=parsed.target_port,
        websocket_enabled=parsed.websocket_enabled,
        custom_headers=[],
        max_body_size=parsed.max_body_size,
        basic_auth_enabled=parsed.basic_auth_enabled,
        basic_auth_username=None,
        basic_auth_password=None,
        force_https=parsed.force_https,
        enabled=parsed.enabled,
        https_enabled=parsed.https_enabled,
        upstream=parsed.upstream,
        managed=True,
    )


class ProxyService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.writer = NginxWriter(settings)
        self.ops = NginxOps(settings)

    def list_proxies(self) -> list[ProxyAppResponse]:
        return [parsed_to_response(item) for item in list_proxy_configs(self.settings)]

    def get_proxy(self, proxy_id: str) -> Optional[ProxyAppResponse]:
        path = self.writer.config_path_for(proxy_id)
        if not path.exists():
            return None
        parsed = parse_config_file(path, self.settings)
        return parsed_to_response(parsed) if parsed else None

    def create_proxy(self, payload: ProxyAppCreate) -> tuple[bool, str, Optional[ProxyAppResponse]]:
        path = self.writer.config_path_for(payload.name)
        if path.exists():
            return False, f"Config already exists: {path.name}", None

        def write_fn() -> None:
            self.writer.write_htpasswd(payload)
            content = self.writer.render_config(payload)
            self.writer.atomic_write(path, content)
            if payload.enabled:
                self.ops.enable_site(path.name)
            else:
                self.ops.disable_site(path.name)

        ok, output = self.writer.apply_change(path, write_fn, self.ops.test_config)
        if not ok:
            return False, output, None
        reload_ok, reload_output = self.ops.reload()
        if not reload_ok:
            return False, reload_output, None
        return True, reload_output, self.get_proxy(payload.name)

    def update_proxy(self, proxy_id: str, payload: ProxyAppUpdate) -> tuple[bool, str, Optional[ProxyAppResponse]]:
        path = self.writer.config_path_for(proxy_id)
        if not path.exists():
            return False, "Proxy not found", None

        def write_fn() -> None:
            self.writer.write_htpasswd(payload)
            content = self.writer.render_config(payload)
            self.writer.atomic_write(path, content)
            if payload.enabled:
                self.ops.enable_site(path.name)
            else:
                self.ops.disable_site(path.name)

        ok, output = self.writer.apply_change(path, write_fn, self.ops.test_config)
        if not ok:
            return False, output, None
        reload_ok, reload_output = self.ops.reload()
        if not reload_ok:
            return False, reload_output, None
        return True, reload_output, self.get_proxy(proxy_id)

    def delete_proxy(self, proxy_id: str) -> tuple[bool, str]:
        path = self.writer.config_path_for(proxy_id)
        if not path.exists():
            return False, "Proxy not found"

        backup = self.writer.backup_manager.create_backup(path)

        def write_fn() -> None:
            self.ops.disable_site(path.name)
            path.unlink(missing_ok=True)

        ok, output = self.writer.apply_change(path, write_fn, self.ops.test_config)
        if not ok:
            if backup:
                self.writer.backup_manager.restore_backup(backup, path)
            return False, output
        reload_ok, reload_output = self.ops.reload()
        return reload_ok, reload_output

    def set_enabled(self, proxy_id: str, enabled: bool) -> tuple[bool, str, Optional[ProxyAppResponse]]:
        path = self.writer.config_path_for(proxy_id)
        if not path.exists():
            return False, "Proxy not found", None

        def write_fn() -> None:
            if enabled:
                self.ops.enable_site(path.name)
            else:
                self.ops.disable_site(path.name)

        ok, output = self.writer.apply_change(path, write_fn, self.ops.test_config)
        if not ok:
            return False, output, None
        reload_ok, reload_output = self.ops.reload()
        if not reload_ok:
            return False, reload_output, None
        return True, reload_output, self.get_proxy(proxy_id)
