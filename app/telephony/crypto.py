from django.conf import settings
from cryptography.fernet import Fernet

def _fernet() -> Fernet:
    return Fernet(settings.FERNET_KEY.encode("utf-8"))

def encrypt_text(plain: str) -> str:
    if plain is None:
        plain = ""
    return _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")

def decrypt_text(token: str) -> str:
    if not token:
        return ""
    return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
