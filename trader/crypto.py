import base64
import hashlib
import os
from cryptography.fernet import Fernet

def _fernet():
    secret = os.environ.get("TOKEN_ENCRYPTION_SECRET")
    if not secret: raise RuntimeError("TOKEN_ENCRYPTION_SECRET is required")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)

def encrypt(value: str) -> str: return _fernet().encrypt(value.encode()).decode()
def decrypt(value: str) -> str: return _fernet().decrypt(value.encode()).decode()

