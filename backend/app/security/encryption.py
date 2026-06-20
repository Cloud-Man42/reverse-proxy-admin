import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import Settings


def _derive_fernet_key(settings: Settings) -> bytes:
    key_material = settings.encryption_key or settings.secret_key
    digest = hashlib.sha256(key_material.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_value(settings: Settings, plaintext: str) -> str:
    if not plaintext:
        return ""
    fernet = Fernet(_derive_fernet_key(settings))
    return fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(settings: Settings, ciphertext: str) -> str:
    if not ciphertext:
        return ""
    fernet = Fernet(_derive_fernet_key(settings))
    try:
        return fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Failed to decrypt value") from exc
