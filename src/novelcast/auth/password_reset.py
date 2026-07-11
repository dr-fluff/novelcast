import hashlib
import secrets
from datetime import datetime, timedelta


def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def token_expiry(hours: int = 1) -> str:
    return (datetime.utcnow() + timedelta(hours=hours)).isoformat()
