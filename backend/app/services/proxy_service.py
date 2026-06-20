from pathlib import Path
from typing import Literal, Optional

from sqlalchemy.orm import Session, joinedload

from app.config import Settings
from app.models.backend_pool import BackendPool
from app.models.proxy_rate_limit import ProxyRateLimit
from app.schemas import (
    ProxyAppBase,
    ProxyAppCreate,
    ProxyAppResponse,
    ProxyAppUpdate,
    ProxyRateLimitResponse,
    TargetProtocol,
)
from app.services.backend_pool_service import BackendPoolService
from app.services.cert_paths import certificate_exists, certificate_paths
from app.services.config_version_service import ConfigVersionService, RESOURCE_PROXY
from app.services.file_lock import file_lock
from app.services.geoip_service import GeoIpService
from app.services.ip_access_service import IpAccessService
from app.services.nginx_ops import NginxOps
from app.services.nginx_parser import ParsedProxyConfig, list_proxy_configs, parse_config_file
from app.services.nginx_writer import NginxWriter
from app.services.proxy_metadata_service import ProxyMetadataService
from app.services.rate_limit_service import RateLimitService
from app.services.waf_service import WafService

NginxFailureStage = Literal["validation", "reload"]


def parsed_to_response(
    parsed: ParsedProxyConfig,
    metadata: ProxyMetadataService,
    proxy_id: str,
    rate_limit: Optional[object] = None,
) -> ProxyAppResponse:
    from app.schemas import ProxyRateLimitResponse

    primary = parsed.routes[0]
    rate_limit_response = None
    if rate_limit is not None:
        rate_limit_response = ProxyRateLimitResponse(
            proxy_id=proxy_id,
            enabled=rate_limit.enabled,
            requests_per_minute=rate_limit.requests_per_minute,
            burst=rate_limit.burst,
            nodelay=rate_limit.nodelay,
            key_type=rate_limit.key_type,
        )
    return ProxyAppResponse(
        id=parsed.slug,
        name=parsed.slug,
        config_file=parsed.config_file,
        domains=parsed.domains,
        routes=parsed.routes,
        target_protocol=TargetProtocol(parsed.target_protocol),
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
        notes=metadata.get_notes(proxy_id),
        rate_limit=rate_limit_response,
    )


class ProxyService:
    def __init__(self, settings: Settings, db: Optional[Session] = None) -> None:
        self.settings = settings
        self.db = db
        self.writer = NginxWriter(settings)
        self.ops = NginxOps(settings)
        self.metadata = ProxyMetadataService(settings)

    def _resolve_route_pools(self, app: ProxyAppBase, proxy_slug: str) -> dict[int, BackendPool]:
        if not self.db:
            return {}
        pool_service = BackendPoolService(self.settings, self.db)
        route_pools: dict[int, BackendPool] = {}
        for idx, route in enumerate(app.routes):
            pool = None
            if route.backend_pool_id:
                pool = (
                    self.db.query(BackendPool)
                    .options(joinedload(BackendPool.servers))
                    .filter(BackendPool.id == route.backend_pool_id)
                    .first()
                )
            if pool is None:
                pool = pool_service.get_pool_for_route(proxy_slug, route.path_prefix, None)
            if pool:
                route_pools[idx] = pool
        return route_pools

    def _rate_limit_service(self) -> Optional[RateLimitService]:
        if not self.db:
            return None
        return RateLimitService(self.db)

    def _config_version_service(self) -> Optional[ConfigVersionService]:
        if not self.db:
            return None
        return ConfigVersionService(self.settings, self.db)

    def _ip_access_service(self) -> Optional[IpAccessService]:
        if not self.db:
            return None
        return IpAccessService(self.db)

    def _geoip_service(self) -> Optional[GeoIpService]:
        if not self.db:
            return None
        return GeoIpService(self.settings, self.db)

    def _waf_service(self) -> Optional[WafService]:
        if not self.db:
            return None
        return WafService(self.settings, self.db)

    def _read_config_file(self, proxy_id: str) -> Optional[str]:
        path = self.writer.config_path_for(proxy_id)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def _record_config_version(
        self,
        proxy_id: str,
        username: str,
        summary: str,
        old_config: Optional[str],
        new_config: str,
        nginx_test_result: Optional[str] = None,
    ) -> None:
        service = self._config_version_service()
        if not service:
            return
        service.record(
            resource_type=RESOURCE_PROXY,
            resource_id=proxy_id,
            username=username,
            summary=summary,
            old_config=old_config,
            new_config=new_config,
            nginx_test_result=nginx_test_result,
        )

    def _get_rate_limit_model(self, proxy_id: str):
        service = self._rate_limit_service()
        if not service:
            return None
        return service.get_model(proxy_id)

    def _resolve_response(self, parsed: ParsedProxyConfig, proxy_id: str) -> ProxyAppResponse:
        rate_limit = self.db.get(ProxyRateLimit, proxy_id) if self.db else None
        return parsed_to_response(parsed, self.metadata, proxy_id, rate_limit)

    def _render_config(self, app: ProxyAppBase, proxy_slug: Optional[str] = None) -> str:
        slug = proxy_slug or app.name
        route_pools = self._resolve_route_pools(app, slug)
        rate_limit = self._get_rate_limit_model(slug)
        ip_rules = None
        geo_rule = None
        waf_settings = None
        if self.db:
            ip_service = self._ip_access_service()
            if ip_service:
                ip_rules = ip_service.rules_for_proxy(slug)
            geo_service = self._geoip_service()
            if geo_service:
                geo_rule = geo_service.get_for_proxy(slug)
                if geo_rule:
                    geo_service.write_include(slug, geo_rule)
            waf_service = self._waf_service()
            if waf_service:
                waf_settings = waf_service.get_model(slug)
                if waf_settings.enabled:
                    waf_service.write_include(waf_settings)
            if ip_service:
                from app.models.ip_access_rule import IpAccessRule

                global_rules = (
                    self.db.query(IpAccessRule)
                    .filter(IpAccessRule.scope == "global", IpAccessRule.enabled.is_(True))
                    .all()
                )
                self.writer.write_global_ip_access(global_rules)
        return self.writer.render_config(
            app,
            route_pools,
            slug,
            rate_limit,
            ip_rules=ip_rules,
            geo_rule=geo_rule,
            waf_settings=waf_settings,
        )

    def _validate_force_https(self, app: ProxyAppBase) -> None:
        if not app.force_https:
            return
        domain = app.domains[0]
        if certificate_exists(self.settings, domain):
            return
        cert_path, _ = certificate_paths(self.settings, domain)
        raise ValueError(
            f"Cannot enable Force HTTPS: no certificate for {domain} at {cert_path}. "
            "Issue a Let's Encrypt certificate first (port 80 must be reachable from the internet)."
        )

    def _sync_notes(self, proxy_id: str, payload: ProxyAppBase, *, renaming: bool = False) -> None:
        if renaming:
            old_notes = self.metadata.get_notes(proxy_id)
            self.metadata.delete(proxy_id)
            notes = payload.notes if payload.notes is not None else old_notes
            self.metadata.set_notes(payload.name, notes)
            return
        self.metadata.set_notes(proxy_id, payload.notes)

    def list_proxies(self) -> list[ProxyAppResponse]:
        rate_limits = {}
        if self.db:
            rate_limits = {row.proxy_id: row for row in self.db.query(ProxyRateLimit).all()}
        return [
            parsed_to_response(item, self.metadata, item.slug, rate_limits.get(item.slug))
            for item in list_proxy_configs(self.settings)
        ]

    def get_proxy(self, proxy_id: str) -> Optional[ProxyAppResponse]:
        path = self.writer.config_path_for(proxy_id)
        if not path.exists():
            return None
        parsed = parse_config_file(path, self.settings)
        return self._resolve_response(parsed, proxy_id) if parsed else None

    def create_proxy(
        self, payload: ProxyAppCreate, *, username: str = "system"
    ) -> tuple[bool, str, Optional[ProxyAppResponse], Optional[NginxFailureStage]]:
        path = self.writer.config_path_for(payload.name)
        if path.exists():
            return False, f"Config already exists: {path.name}", None, None

        try:
            self._validate_force_https(payload)
        except ValueError as exc:
            return False, str(exc), None, None

        def write_fn() -> None:
            self.writer.write_htpasswd(payload)
            content = self._render_config(payload, payload.name)
            self.writer.atomic_write(path, content)
            if payload.enabled:
                self.ops.enable_site(path.name)
            else:
                self.ops.disable_site(path.name)

        ok, output = self.writer.apply_change(path, write_fn, self.ops.test_config)
        if not ok:
            return False, output, None, "validation"
        reload_ok, reload_output = self.ops.reload()
        if not reload_ok:
            return False, reload_output, None, "reload"
        self._sync_notes(payload.name, payload)
        if payload.rate_limit and self.db:
            RateLimitService(self.db).upsert(payload.name, payload.rate_limit)
        new_config = self._read_config_file(payload.name) or ""
        self._record_config_version(payload.name, username, "Created proxy", None, new_config, reload_output)
        return True, reload_output, self.get_proxy(payload.name), None

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

    def _write_proxy_state(self, path: Path, payload: ProxyAppBase, proxy_slug: Optional[str] = None) -> None:
        content = self._render_config(payload, proxy_slug or path.stem)
        self.writer.atomic_write(path, content)
        if payload.enabled:
            self.ops.enable_site(path.name)
        else:
            self.ops.disable_site(path.name)

    def update_proxy(
        self, proxy_id: str, payload: ProxyAppUpdate, *, username: str = "system"
    ) -> tuple[bool, str, Optional[ProxyAppResponse], Optional[NginxFailureStage]]:
        old_path = self.writer.config_path_for(proxy_id)
        if not old_path.exists():
            return False, "Proxy not found", None, None

        old_config = self._read_config_file(proxy_id)

        renaming = payload.name != proxy_id
        new_path = self.writer.config_path_for(payload.name) if renaming else old_path

        if renaming and new_path.exists():
            return False, f"Config already exists: {new_path.name}", None, None

        try:
            self._validate_force_https(payload)
        except ValueError as exc:
            return False, str(exc), None, None

        if not renaming:
            def write_fn() -> None:
                self._sync_htpasswd(proxy_id, payload, renaming=False)
                self._write_proxy_state(old_path, payload, proxy_id)
            ok, output = self.writer.apply_change(old_path, write_fn, self.ops.test_config)
            if not ok:
                return False, output, None, "validation"
            reload_ok, reload_output = self.ops.reload()
            if not reload_ok:
                return False, reload_output, None, "reload"
            self._sync_notes(proxy_id, payload)
            if payload.rate_limit and self.db:
                RateLimitService(self.db).upsert(proxy_id, payload.rate_limit)
            new_config = self._read_config_file(proxy_id) or ""
            self._record_config_version(proxy_id, username, "Updated proxy", old_config, new_config, reload_output)
            return True, reload_output, self.get_proxy(proxy_id), None

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
            self._write_proxy_state(new_path, payload, payload.name)
            self.ops.disable_site(old_path.name)
            old_path.unlink(missing_ok=True)

        with file_lock(old_path):
            try:
                write_fn()
            except Exception as exc:
                rollback()
                return False, str(exc), None, None

            ok, output = self.ops.test_config()
            if not ok:
                rollback()
                return False, output, None, "validation"

        reload_ok, reload_output = self.ops.reload()
        if not reload_ok:
            rollback()
            return False, reload_output, None, "reload"
        self._sync_notes(proxy_id, payload, renaming=True)
        if payload.rate_limit and self.db:
            if renaming:
                old_row = self.db.get(ProxyRateLimit, proxy_id)
                if old_row is not None:
                    self.db.delete(old_row)
            RateLimitService(self.db).upsert(payload.name, payload.rate_limit)
        new_config = self._read_config_file(payload.name) or ""
        self._record_config_version(payload.name, username, "Updated proxy (rename)", old_config, new_config, reload_output)
        return True, reload_output, self.get_proxy(payload.name), None

    def delete_proxy(self, proxy_id: str, *, username: str = "system") -> tuple[bool, str, Optional[NginxFailureStage]]:
        path = self.writer.config_path_for(proxy_id)
        if not path.exists():
            return False, "Proxy not found", None

        old_config = self._read_config_file(proxy_id)

        backup = self.writer.backup_manager.create_backup(path)

        def write_fn() -> None:
            self.ops.disable_site(path.name)
            path.unlink(missing_ok=True)

        ok, output = self.writer.apply_change(path, write_fn, self.ops.test_config)
        if not ok:
            if backup:
                self.writer.backup_manager.restore_backup(backup, path)
            return False, output, "validation"
        reload_ok, reload_output = self.ops.reload()
        if not reload_ok:
            return reload_ok, reload_output, "reload"
        self.metadata.delete(proxy_id)
        if self.db:
            RateLimitService(self.db).delete(proxy_id)
        self._record_config_version(proxy_id, username, "Deleted proxy", old_config, "", reload_output)
        return reload_ok, reload_output, None

    def set_enabled(
        self, proxy_id: str, enabled: bool
    ) -> tuple[bool, str, Optional[ProxyAppResponse], Optional[NginxFailureStage]]:
        path = self.writer.config_path_for(proxy_id)
        if not path.exists():
            return False, "Proxy not found", None, None

        def write_fn() -> None:
            if enabled:
                self.ops.enable_site(path.name)
            else:
                self.ops.disable_site(path.name)

        ok, output = self.writer.apply_change(path, write_fn, self.ops.test_config)
        if not ok:
            return False, output, None, "validation"
        reload_ok, reload_output = self.ops.reload()
        if not reload_ok:
            return False, reload_output, None, "reload"
        return True, reload_output, self.get_proxy(proxy_id), None
