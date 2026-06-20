from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.user import User
from app.schemas import ProxyTemplateResponse
from app.security.permissions import Permission, require_permission
from app.services.template_service import TemplateService

router = APIRouter(prefix="/templates", tags=["templates"])


def get_service(db: Session = Depends(get_db)) -> TemplateService:
    return TemplateService(db)


@router.get("", response_model=List[ProxyTemplateResponse])
async def list_templates(
    service: TemplateService = Depends(get_service),
    _user: User = Depends(require_permission(Permission.READ)),
) -> List[ProxyTemplateResponse]:
    return service.list_templates()


@router.get("/{slug}", response_model=ProxyTemplateResponse)
async def get_template(
    slug: str,
    service: TemplateService = Depends(get_service),
    _user: User = Depends(require_permission(Permission.READ)),
) -> ProxyTemplateResponse:
    template = service.get_by_slug(slug)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return template
