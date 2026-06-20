from fastapi import APIRouter

from app.api.v1 import analytics, audit, backend_pools, certificates, health, proxy_hosts, system

router = APIRouter(prefix="/api/v1")

router.include_router(proxy_hosts.router, tags=["v1-proxy-hosts"])
router.include_router(backend_pools.router, tags=["v1-backend-pools"])
router.include_router(certificates.router, tags=["v1-certificates"])
router.include_router(health.router, tags=["v1-health"])
router.include_router(analytics.router, tags=["v1-analytics"])
router.include_router(system.router, tags=["v1-system"])
router.include_router(audit.router, tags=["v1-audit"])
