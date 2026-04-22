from fastapi import Request

def get_current_user(request: Request):
    token = request.cookies.get("session")

    if not token:
        return None

    user_id = decode_session_token(token)
    if not user_id:
        return None

    user = request.app.state.qm.fetchone(
        "users.get_by_id",
        (user_id,)
    )

    return user