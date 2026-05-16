"""
novelcast/db/init_db.py

Call init_db() once at application startup.
It creates all tables (if they don't exist) and seeds server defaults.
"""

import json
import logging

from novelcast.db.base import Base
from novelcast.db.engine import engine
from novelcast.db.session import SessionLocal
from novelcast.core import defaults

# --- import every model so SQLAlchemy knows about them before create_all ---
from novelcast.db.models import *  # noqa: F401, F403 - re-exported in __init__.py

logger = logging.getLogger(__name__)


def init_db():
    logger.info("Initialising database...")
    Base.metadata.create_all(bind=engine)
    logger.info("Tables created / verified")
    _seed_server_defaults()


def _seed_server_defaults():
    """
    Populate server_settings with defaults from novelcast.core.defaults.SETTINGS.
    Skips keys that already exist (safe to call on every startup).
    """
    def serialize(v):
        return json.dumps(v)

    def flatten(prefix, d):
        for key, value in d.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict) and "default" in value:
                yield full_key, serialize(value["default"]), value.get("category"), value.get("type", "str")
            elif isinstance(value, dict):
                yield from flatten(full_key, value)
            else:
                yield full_key, serialize(value), None, "str"

    rows = list(flatten("", defaults.SETTINGS))

    with SessionLocal() as db:
        for key, value, category, type_ in rows:
            if db.get(ServerSetting, key) is None:
                db.add(ServerSetting(key=key, value=value, category=category, type=type_))
        db.commit()

    logger.info("Server defaults seeded", extra={"count": len(rows)})
