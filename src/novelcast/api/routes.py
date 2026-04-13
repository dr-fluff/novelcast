# src/novelcast/api/routes.py

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from novelcast.storage.db import Database
from novelcast.engine.updater import UpdateEngine

router = APIRouter()
db = Database()
engine = UpdateEngine(db)

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

templates = Jinja2Templates(directory=str(BASE_DIR / "src/novelcast/web/templates"))

# 🌐 Dashboard
@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    subs = db.get_subscriptions()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "subs": subs}
    )


# ➕ Add subscription
@router.post("/subscribe")
def subscribe(url: str = Form(...)):
    db.add_subscription(url)
    return {"status": "added", "url": url}


# 📚 Get all subscriptions
@router.get("/subscriptions")
def subscriptions():
    return db.get_subscriptions()


# 🔄 Manual update trigger
@router.post("/update")
def update_all():
    engine.check_updates()
    return {"status": "updated"}