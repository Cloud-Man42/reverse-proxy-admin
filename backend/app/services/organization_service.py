from typing import Optional

from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.user import User
from app.schemas import OrganizationCreate, OrganizationResponse, OrganizationUpdate


class OrganizationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_organizations(self) -> list[OrganizationResponse]:
        rows = self.db.query(Organization).order_by(Organization.name).all()
        return [self._to_response(row) for row in rows]

    def get_organization(self, organization_id: int) -> Optional[OrganizationResponse]:
        row = self.db.query(Organization).filter(Organization.id == organization_id).first()
        return self._to_response(row) if row else None

    def get_by_slug(self, slug: str) -> Optional[Organization]:
        return self.db.query(Organization).filter(Organization.slug == slug).first()

    def create_organization(self, payload: OrganizationCreate) -> OrganizationResponse:
        if self.get_by_slug(payload.slug):
            raise ValueError(f"Organization slug '{payload.slug}' already exists")
        org = Organization(slug=payload.slug, name=payload.name, enabled=payload.enabled)
        self.db.add(org)
        self.db.commit()
        self.db.refresh(org)
        return self._to_response(org)

    def update_organization(
        self, organization_id: int, payload: OrganizationUpdate
    ) -> Optional[OrganizationResponse]:
        org = self.db.query(Organization).filter(Organization.id == organization_id).first()
        if not org:
            return None
        data = payload.model_dump(exclude_unset=True)
        if "slug" in data and data["slug"] != org.slug:
            if self.get_by_slug(data["slug"]):
                raise ValueError(f"Organization slug '{data['slug']}' already exists")
        for key, value in data.items():
            setattr(org, key, value)
        self.db.commit()
        self.db.refresh(org)
        return self._to_response(org)

    def delete_organization(self, organization_id: int) -> bool:
        org = self.db.query(Organization).filter(Organization.id == organization_id).first()
        if not org:
            return False
        if org.slug == "default":
            raise ValueError("The default organization cannot be deleted")
        user_count = self.db.query(User).filter(User.organization_id == organization_id).count()
        if user_count:
            raise ValueError("Organization has assigned users")
        self.db.delete(org)
        self.db.commit()
        return True

    @staticmethod
    def _to_response(org: Organization) -> OrganizationResponse:
        return OrganizationResponse(
            id=org.id,
            slug=org.slug,
            name=org.name,
            enabled=org.enabled,
            created_at=org.created_at,
        )
