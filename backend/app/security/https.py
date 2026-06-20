from fastapi import Request

from app.config import Settings


def request_is_https(request: Request, settings: Settings) -> bool:
    if request.url.scheme == "https":
        return True
    forwarded = request.headers.get("x-forwarded-proto", "").split(",")[0].strip().lower()
    return forwarded == "https"


def cookie_secure(request: Request, settings: Settings) -> bool:
    if settings.debug:
        return False
    if settings.admin_ui_require_https:
        return True
    return request_is_https(request, settings)
