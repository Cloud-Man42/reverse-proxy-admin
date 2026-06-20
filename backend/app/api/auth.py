from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models.user import User
from app.schemas import LoginRequest, LoginResponse, MessageResponse
from app.security.auth import create_session, delete_session, get_current_user, verify_password
from app.security.https import cookie_secure
from app.security.ip_allowlist import _client_ip, ip_allowlist_middleware
from app.security.rate_limit import RateLimiter
from app.services.audit_service import log_audit
from app.services.notification_service import NotificationService
from app.services.security_event_service import SecurityEventService

router = APIRouter(prefix="/auth", tags=["auth"])


def _login_response(user: User, csrf_token: str) -> LoginResponse:
    return LoginResponse(
        username=user.username,
        csrf_token=csrf_token,
        is_admin=user.is_admin,
        permissions=user.permissions_dict(),
        organization_id=user.organization_id,
        role=user.role or "operator",
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    await ip_allowlist_middleware(request, settings)
    client_ip = _client_ip(request)
    limiter = RateLimiter(settings.login_rate_limit_attempts, settings.login_rate_limit_window_seconds)
    if not limiter.is_allowed(client_ip):
        SecurityEventService(db).log(
            event_type="login_rate_limited",
            source="login",
            client_ip=client_ip,
            message=f"Login rate limit exceeded for {client_ip}",
        )
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts")

    user = db.query(User).filter(User.username == payload.username, User.is_active.is_(True)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        log_audit(
            db,
            username=payload.username,
            action="login_failed",
            resource="auth",
            client_ip=client_ip,
        )
        SecurityEventService(db).log(
            event_type="login_failed",
            source="login",
            client_ip=client_ip,
            message=f"Failed login attempt for user {payload.username}",
        )
        NotificationService(settings, db).dispatch_login_security(payload.username, client_ip, success=False)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    session = create_session(db, user, client_ip, settings)
    limiter.reset(client_ip)

    response.set_cookie(
        key=settings.session_cookie_name,
        value=session.session_id,
        httponly=True,
        secure=cookie_secure(request, settings),
        samesite="lax",
        max_age=settings.session_max_age_seconds,
    )
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=session.csrf_token,
        httponly=False,
        secure=cookie_secure(request, settings),
        samesite="lax",
        max_age=settings.session_max_age_seconds,
    )
    return _login_response(user, session.csrf_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> MessageResponse:
    session_id = request.cookies.get(settings.session_cookie_name)
    if session_id:
        delete_session(db, session_id)
    response.delete_cookie(settings.session_cookie_name)
    response.delete_cookie(settings.csrf_cookie_name)
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=LoginResponse)
async def me(request: Request, user: User = Depends(get_current_user)) -> LoginResponse:
    session = request.state.session
    return _login_response(user, session.csrf_token)
