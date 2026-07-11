# novelcast/utils/hashing.py

import hashlib
import string


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def looks_like_hash(value: str) -> bool:
    return len(value) == 64 and all(c in string.hexdigits for c in value)


def verify_password(password: str, stored: str) -> bool:
    if looks_like_hash(stored):
        return hash_password(password) == stored
    return password == stored
