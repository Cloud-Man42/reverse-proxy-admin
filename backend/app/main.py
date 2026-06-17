import logging
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import auth, certificates, logs, proxies, system, users
from app.config import get_settings
from app.db import SessionLocal, init_db
from app.security.auth import bootstrap_admin
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
    finally:
        db.close()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://{settings.host}:{settings.port}", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
app.include_router(certificates.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(system.router, prefix="/api")
app.include_router(users.router, prefix="/api")


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
