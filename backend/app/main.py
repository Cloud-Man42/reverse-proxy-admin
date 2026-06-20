import logging
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api import analytics, api_tokens, auth, backend_pools, certificates, config_versions, health_checks, logs, notifications, organizations, proxies, security, smtp, status_reports, system, system_alerts, templates, users
from app.api.v1 import router as v1_router
from app.config import get_settings
from app.db import SessionLocal, init_db
from app.security.auth import bootstrap_admin
from app.services.scheduler import start_scheduler, stop_scheduler
from app.security.https import request_is_https
from app.security.ip_allowlist import ip_allowlist_middleware


def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()
    init_db()
    db = SessionLocal()
    try:
        bootstrap_admin(db, settings)
        from app.services.template_service import TemplateService

        TemplateService(db).ensure_builtins()
    finally:
        db.close()
    if settings.scheduler_enabled:
        start_scheduler(settings)
    yield
    stop_scheduler()


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://{settings.host}:{settings.port}",
        f"https://127.0.0.1:{settings.admin_ui_port}",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def require_https_admin_ui(request: Request, call_next):
    current = get_settings()
    if not current.admin_ui_require_https or current.debug:
        return await call_next(request)
    if request.url.path == "/api/health":
        return await call_next(request)
    if request_is_https(request, current):
        return await call_next(request)

    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "localhost"
    host = host.split(",")[0].strip().split(":")[0]
    target = f"https://{host}:{current.admin_ui_port}{request.url.path}"
    if request.url.query:
        target = f"{target}?{request.url.query}"

    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=403,
            content={
                "detail": f"HTTPS required. Use {target.replace(request.url.path, '')}",
            },
        )

    return RedirectResponse(url=target, status_code=308)


@app.middleware("http")
async def enforce_ip_allowlist(request: Request, call_next):
    if request.url.path.startswith("/api/health"):
        return await call_next(request)
    if request.url.path.startswith("/api/auth/login") or request.method == "OPTIONS":
        return await call_next(request)
    if request.url.path.startswith("/api/"):
        await ip_allowlist_middleware(request, get_settings())
    return await call_next(request)


app.include_router(auth.router, prefix="/api")
app.include_router(proxies.router, prefix="/api")
app.include_router(templates.router, prefix="/api")
app.include_router(config_versions.router, prefix="/api")
app.include_router(backend_pools.router, prefix="/api")
app.include_router(backend_pools.router_servers, prefix="/api")
app.include_router(backend_pools.load_balancers_router, prefix="/api")
app.include_router(health_checks.router, prefix="/api")
app.include_router(smtp.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(status_reports.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(system_alerts.router, prefix="/api")
app.include_router(certificates.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(system.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(organizations.router, prefix="/api")
app.include_router(api_tokens.router, prefix="/api")
app.include_router(security.router, prefix="/api")
app.include_router(v1_router)


if settings.frontend_dist.exists():
    assets_dir = settings.frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def spa(full_path: str):
        index = settings.frontend_dist / "index.html"
        if full_path.startswith("api/"):
            return {"detail": "Not found"}
        if index.exists():
            return FileResponse(index)
        return {"detail": "Frontend not built"}
