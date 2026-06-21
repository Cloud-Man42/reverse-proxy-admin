import traceback

try:
    from app.config import get_settings
    from app.db import init_db, SessionLocal
    from app.security.auth import bootstrap_admin
    from app.services.template_service import TemplateService
    from app.services.scheduler import start_scheduler

    settings = get_settings()
    print("settings ok", settings.admin_username, settings.allowed_ips)
    init_db()
    print("init_db ok")
    db = SessionLocal()
    try:
        bootstrap_admin(db, settings)
        TemplateService(db).ensure_builtins()
    finally:
        db.close()
    print("bootstrap ok")
    if settings.scheduler_enabled:
        start_scheduler(settings)
        print("scheduler ok")
    print("ALL OK")
except Exception:
    traceback.print_exc()
    raise
