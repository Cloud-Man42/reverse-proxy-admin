import hashlib
import secrets
from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.api_token import ApiToken
from app.schemas import ApiTokenCreate, ApiTokenUpdate

TOKEN_PREFIX = "rpa_"


def hash_token(plain_token: str) -> str:
    return hashlib.sha256(plain_token.encode("utf-8")).hexdigest()


class ApiTokenService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_tokens(self) -> List[ApiToken]:
        return (
            self.db.query(ApiToken)
            .filter(ApiToken.revoked.is_(False))
            .order_by(ApiToken.created_at.desc())
            .all()
        )

    def get_token(self, token_id: int) -> Optional[ApiToken]:
        return self.db.query(ApiToken).filter(ApiToken.id == token_id).first()

    def create(self, payload: ApiTokenCreate) -> Tuple[ApiToken, str]:
        plain_token = f"{TOKEN_PREFIX}{secrets.token_urlsafe(32)}"
        token = ApiToken(
            name=payload.name,
            token_hash=hash_token(plain_token),
            token_prefix=plain_token[:12],
            expires_at=payload.expires_at,
        )
        token.scopes = payload.scopes
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token, plain_token

    def update(self, token_id: int, payload: ApiTokenUpdate) -> ApiToken:
        token = self.get_token(token_id)
        if not token:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
        if token.revoked:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token is revoked")
        if payload.name is not None:
            token.name = payload.name
        if payload.scopes is not None:
            token.scopes = payload.scopes
        if payload.expires_at is not None:
            token.expires_at = payload.expires_at
        self.db.commit()
        self.db.refresh(token)
        return token

    def revoke(self, token_id: int) -> ApiToken:
        token = self.get_token(token_id)
        if not token:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
        token.revoked = True
        self.db.commit()
        self.db.refresh(token)
        return token

    def validate_hash(self, plain_token: str) -> Optional[ApiToken]:
        if not plain_token.startswith(TOKEN_PREFIX):
            return None
        token_hash = hash_token(plain_token)
        token = self.db.query(ApiToken).filter(ApiToken.token_hash == token_hash).first()
        if not token or not token.is_valid():
            return None
        return token

    def update_last_used(self, token: ApiToken) -> None:
        token.last_used_at = datetime.utcnow()
        self.db.commit()
