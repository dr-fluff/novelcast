from fastapi import APIRouter
from novelcast.core.context import AppContext

router = APIRouter()
qm = AppContext().qm

def get_router():
    return router

@router.get("/settings")
def get_settings():
    return qm.fetchall("settings.get_all", ())