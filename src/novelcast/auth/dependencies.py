from fastapi import Request, HTTPException
from novelcast.core.context import AppContext

ctx = AppContext()  # or inject later via app.state (we’ll improve later)


def get_current_user(request: Request):
    token = request.cookies.get("session")

    if not token:
        return None

    user_id = decode_session_token(token)
    if not user_id:
        return None

    user = ctx.qm.fetchone(
        "users.get_by_id",
        (user_id,)
    )

    if not user:
        return None

    return user