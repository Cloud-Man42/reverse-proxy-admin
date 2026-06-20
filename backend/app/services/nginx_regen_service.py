import threading
import time

from sqlalchemy.orm import Session

from app.config import Settings
from app.models.backend_pool import BackendPool
from app.schemas import ProxyAppCreate
from app.services.backend_pool_service import BackendPoolService
from app.services.nginx_parser import list_proxy_configs
from app.services.proxy_service import ProxyService

_lock = threading.Lock()
_pending_pool_ids: set[int] = set()
_last_queued_at: float | None = None


class NginxRegenService:
    def __init__(self, settings: Settings, db: Session) -> None:
        self.settings = settings
        self.db = db
        self.proxy_service = ProxyService(settings, db)

    @staticmethod
    def queue_for_pool(pool_id: int) -> None:
        global _last_queued_at
        with _lock:
            _pending_pool_ids.add(pool_id)
            _last_queued_at = time.monotonic()

    @classmethod
    def queue_for_server(cls, server) -> None:
        cls.queue_for_pool(server.pool_id)

    def process_pending(self) -> int:
        global _last_queued_at
        with _lock:
            if not _pending_pool_ids:
                return 0
            if _last_queued_at is not None:
                elapsed = time.monotonic() - _last_queued_at
                if elapsed < self.settings.nginx_regen_debounce_seconds:
                    return 0
            pool_ids = set(_pending_pool_ids)
            _pending_pool_ids.clear()
            _last_queued_at = None

        proxy_ids: set[str] = set()
        for pool_id in pool_ids:
            proxy_ids.update(self._proxy_ids_for_pool(pool_id))

        success_count = 0
        for proxy_id in sorted(proxy_ids):
            ok, _ = self.regen_proxy(proxy_id)
            if ok:
                success_count += 1
        return success_count

    def _proxy_ids_for_pool(self, pool_id: int) -> set[str]:
        pool = self.db.query(BackendPool).filter(BackendPool.id == pool_id).first()
        if not pool:
            return set()

        proxy_ids: set[str] = set()
        if pool.proxy_id:
            proxy_ids.add(pool.proxy_id)

        pool_service = BackendPoolService(self.settings, self.db)
        for parsed in list_proxy_configs(self.settings):
            for route in parsed.routes:
                matched = pool_service.get_pool_for_route(
                    parsed.slug, route.path_prefix, route.backend_pool_id
                )
                if matched and matched.id == pool_id:
                    proxy_ids.add(parsed.slug)
        return proxy_ids

    def regen_proxy(self, proxy_id: str) -> tuple[bool, str]:
        proxy = self.proxy_service.get_proxy(proxy_id)
        if not proxy:
            return False, f"Proxy not found: {proxy_id}"

        payload = ProxyAppCreate(
            name=proxy.name,
            domains=proxy.domains,
            routes=proxy.routes,
            custom_headers=proxy.custom_headers,
            max_body_size=proxy.max_body_size,
            basic_auth_enabled=proxy.basic_auth_enabled,
            force_https=proxy.force_https,
            enabled=proxy.enabled,
            notes=proxy.notes,
        )
        path = self.proxy_service.writer.config_path_for(proxy_id)

        def write_fn() -> None:
            self.proxy_service._write_proxy_state(path, payload, proxy_id)

        ok, output = self.proxy_service.writer.apply_change(
            path, write_fn, self.proxy_service.ops.test_config
        )
        if not ok:
            return False, output
        reload_ok, reload_output = self.proxy_service.ops.reload()
        return reload_ok, reload_output
