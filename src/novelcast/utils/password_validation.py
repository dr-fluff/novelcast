# novelcast/utils/password_validation.py

import re

MIN_LENGTH = 8


def validate_password_strength(password: str) -> list[str]:
    """
    Returns a list of human-readable problems with the password.
    An empty list means the password passes all checks.
    """
    errors = []

    if len(password) < MIN_LENGTH:
        errors.append(f"Password must be at least {MIN_LENGTH} characters long.")

    if not re.search(r"[a-z]", password):
        errors.append("Password must contain a lowercase letter.")

    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain an uppercase letter.")

    if not re.search(r"\d", password):
        errors.append("Password must contain a number.")

    if not re.search(r"[^\w\s]", password):
        errors.append("Password must contain a special character.")

    return errors