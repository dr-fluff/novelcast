# novelcast/api/routes/admin/telegram.py

from fastapi import APIRouter, Request

router = APIRouter()

@router.post("/test")
async def test_telegram(request: Request):
    telegram = request.app.state.telegram
    ok, msg = await telegram.send_test()

    icon = "fa-circle-check" if ok else "fa-circle-xmark"
    color = "text-green-500" if ok else "text-red-500"

    return (
        f"<div class='{color} flex items-center gap-2'>"
        f"<i class='fa-solid {icon}'></i>"
        f"<span>{msg}</span>"
        f"</div>"
    )

