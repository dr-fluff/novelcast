from fastapi import APIRouter, Request

router = APIRouter()



@router.get("/status")
def get_status():
    return status


# ─────────────────────────────
# Subscriptions API
# ─────────────────────────────
@router.get("/subscriptions")
def subscriptions(request: Request):
    return request.app.state.db.get_subscriptions()