# src/novelcast/main.py

from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from novelcast.api.routes import router
from novelcast.storage.db import Database

# ─────────────────────────────
# Paths
# ─────────────────────────────
BASE_DIR = Path(__file__).resolve().parent

TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# ─────────────────────────────
# App
# ─────────────────────────────
app = FastAPI(title="NovelCast")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static"
)

# shared resources
app.state.db = Database()
app.state.templates = templates

# routes
app.include_router(router)