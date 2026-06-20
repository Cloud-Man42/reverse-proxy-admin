from typing import Optional, TypeVar

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Query, Session

from app.models.user import User
from app.security.auth import get_current_user

ModelT = TypeVar("ModelT")


def is_super_admin(user: User) -> bool:
    return user.role == "super_admin"


def get_current_org(user: User) -> Optional[int]:
    """Return org id for tenant-scoped users; None means no org filter (super admin)."""
    if is_super_admin(user):
        return None
    return user.organization_id


def filter_query_by_org(query: Query, model: type[ModelT], user: User) -> Query:
    org_id = get_current_org(user)
    if org_id is not None:
        query = query.filter(model.organization_id == org_id)
    return query


def require_super_admin(user: User = Depends(get_current_user)) -> User:
    if not is_super_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required",
        )
    return user


def require_org_access(user: User, organization_id: Optional[int]) -> None:
    org_id = get_current_org(user)
    if org_id is not None and organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied")


def bootstrap_default_organization(db: Session):
    from app.models.organization import Organization

    org = db.query(Organization).filter(Organization.slug == "default").first()
    if org:
        return org

    org = Organization(slug="default", name="Default", enabled=True)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def assign_orphan_records_to_default_org(db: Session, organization_id: int) -> None:
    from app.models.audit import AuditLog
    from app.models.backend_pool import BackendPool
    from app.models.notification import NotificationRecipient
    from app.models.user import User

    for model in (BackendPool, NotificationRecipient, AuditLog, User):
        db.query(model).filter(model.organization_id.is_(None)).update(
            {model.organization_id: organization_id},
            synchronize_session=False,
        )
    db.commit()
