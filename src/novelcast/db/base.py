"""
novelcast/db/base.py

Single source of truth for the declarative base.
All models import from here to avoid circular imports.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
