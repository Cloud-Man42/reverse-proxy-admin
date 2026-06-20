import secrets
from datetime import datetime, timedelta
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models.session import UserSession
from app.models.user import User
from app.security.csrf import validate_csrf
from app.security.ip_allowlist import ip_allowlist_middleware

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def create_session(db: Session, user: User, client_ip: str, settings: Settings) -> UserSession:
    from app.security.rate_limit import generate_csrf_token

    session = UserSession(
        session_id=secrets.token_urlsafe(48),
        user_id=user.id,
        csrf_token=generate_csrf_token(),
        expires_at=datetime.utcnow() + timedelta(seconds=settings.session_max_age_seconds),
        client_ip=client_ip,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session_by_id(db: Session, session_id: str) -> Optional[UserSession]:
    return db.query(UserSession).filter(UserSession.session_id == session_id).first()


def delete_session(db: Session, session_id: str) -> None:
    db.query(UserSession).filter(UserSession.session_id == session_id).delete()
    db.commit()


def bootstrap_admin(db: Session, settings: Settings) -> None:
    from app.security.tenant_context import bootstrap_default_organization

    default_org = bootstrap_default_organization(db)
    existing = db.query(User).filter(User.username == settings.admin_username).first()
    if existing:
        changed = False
        if not existing.is_admin:
            existing.is_admin = True
            existing.perm_read = True
            existing.perm_create = True
            existing.perm_edit = True
            changed = True
        if existing.role != "super_admin":
            existing.role = "super_admin"
            changed = True
        if existing.organization_id != default_org.id:
            existing.organization_id = default_org.id
            changed = True
        if changed:
            db.commit()
        return
    if not settings.admin_password:
        raise RuntimeError("ADMIN_PASSWORD must be set for initial admin user creation")
    user = User(
        username=settings.admin_username,
        password_hash=hash_password(settings.admin_password),
        is_admin=True,
        perm_read=True,
        perm_create=True,
        perm_edit=True,
        role="super_admin",
        organization_id=default_org.id,
    )
    db.add(user)
    db.commit()


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    await ip_allowlist_middleware(request, settings)
    await validate_csrf(request)

    session_id = request.cookies.get(settings.session_cookie_name)
    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    session = get_session_by_id(db, session_id)
    if not session or session.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    user = db.query(User).filter(User.id == session.user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    request.state.session = session
    request.state.user = user
    return user


async def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Optional[User]:
    try:
        return await get_current_user(request, db, settings)
    except HTTPException:
        return None
