# api/routes/admin.py

from fastapi import APIRouter, Request

router = APIRouter()


def qm(request: Request):
    return request.app.state.qm


# ─────────────────────────────
# Settings
# ─────────────────────────────
@router.get("/settings")
def get_settings(request: Request):
    return qm(request).fetchall("settings.get_all", ())