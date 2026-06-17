from pathlib import Path
from typing import Optional

from app.config import Settings
from app.schemas import ProxyAppBase, ProxyAppCreate, ProxyAppResponse, ProxyAppUpdate
from app.services.file_lock import file_lock
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

    def _htpasswd_path(self, slug: str) -> Path:
        return self.settings.htpasswd_dir / f"{slug}.htpasswd"

    def _sync_htpasswd(self, proxy_id: str, payload: ProxyAppBase, *, renaming: bool) -> None:
        old_htpasswd = self._htpasswd_path(proxy_id)
        new_htpasswd = self._htpasswd_path(payload.name)

        if payload.basic_auth_enabled:
            if payload.basic_auth_username and payload.basic_auth_password:
                self.writer.write_htpasswd(payload)
                if renaming and old_htpasswd.exists() and old_htpasswd != new_htpasswd:
                    old_htpasswd.unlink(missing_ok=True)
            elif renaming and old_htpasswd.exists() and old_htpasswd != new_htpasswd:
                if new_htpasswd.exists():
                    new_htpasswd.unlink()
                old_htpasswd.rename(new_htpasswd)
            return

        if old_htpasswd.exists():
            old_htpasswd.unlink(missing_ok=True)
        if renaming and new_htpasswd.exists() and new_htpasswd != old_htpasswd:
            new_htpasswd.unlink(missing_ok=True)

    def _write_proxy_state(self, path: Path, payload: ProxyAppBase) -> None:
        content = self.writer.render_config(payload)
        self.writer.atomic_write(path, content)
        if payload.enabled:
            self.ops.enable_site(path.name)
        else:
            self.ops.disable_site(path.name)

    def update_proxy(self, proxy_id: str, payload: ProxyAppUpdate) -> tuple[bool, str, Optional[ProxyAppResponse]]:
        old_path = self.writer.config_path_for(proxy_id)
        if not old_path.exists():
            return False, "Proxy not found", None

        renaming = payload.name != proxy_id
        new_path = self.writer.config_path_for(payload.name) if renaming else old_path

        if renaming and new_path.exists():
            return False, f"Config already exists: {new_path.name}", None

        if not renaming:
            def write_fn() -> None:
                self._sync_htpasswd(proxy_id, payload, renaming=False)
                self._write_proxy_state(old_path, payload)

            ok, output = self.writer.apply_change(old_path, write_fn, self.ops.test_config)
            if not ok:
                return False, output, None
            reload_ok, reload_output = self.ops.reload()
            if not reload_ok:
                return False, reload_output, None
            return True, reload_output, self.get_proxy(proxy_id)

        was_enabled = self.ops.is_enabled(old_path.name)
        backup = self.writer.backup_manager.create_backup(old_path)

        def rollback() -> None:
            if new_path.exists():
                new_path.unlink(missing_ok=True)
            if backup and backup.exists():
                self.writer.backup_manager.restore_backup(backup, old_path)
            self.ops.disable_site(new_path.name)
            if was_enabled:
                self.ops.enable_site(old_path.name)
            else:
                self.ops.disable_site(old_path.name)

        def write_fn() -> None:
            self._sync_htpasswd(proxy_id, payload, renaming=True)
            self._write_proxy_state(new_path, payload)
            self.ops.disable_site(old_path.name)
            old_path.unlink(missing_ok=True)

        with file_lock(old_path):
            try:
                write_fn()
            except Exception as exc:
                rollback()
                return False, str(exc), None

            ok, output = self.ops.test_config()
            if not ok:
                rollback()
                return False, output, None

        reload_ok, reload_output = self.ops.reload()
        if not reload_ok:
            rollback()
            return False, reload_output, None
        return True, reload_output, self.get_proxy(payload.name)

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
