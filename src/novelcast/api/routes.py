# src/novelcast/api/routes.py

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from novelcast.storage.db import Database
from novelcast.engine.updater import UpdateEngine

from pathlib import Path

from types import SimpleNamespace

router = APIRouter()
db = Database()
engine = UpdateEngine(db)

BASE_DIR = Path(__file__).resolve().parent.parent

templates = Jinja2Templates(
    directory=str(BASE_DIR / "web/templates")
)
templates.env.auto_reload = True

# 🌐 Dashboard
@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    subs = [SimpleNamespace(**s)for s in db.get_subscriptions()]
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "subs": subs}
    )

@router.post("/subscribe")
def subscribe(url: str = Form(...)):
    db.add_subscription(url)
    return RedirectResponse("/", status_code=303)

# 📚 Get all subscriptions
@router.get("/subscriptions")
def subscriptions():
    return db.get_subscriptions()


# 🔄 Manual update trigger
@router.post("/update")
def update_all():
    engine.check_updates()
    return {"status": "updated"}