import itsdangerous

SECRET_KEY = "change-this-in-prod"
serializer = itsdangerous.URLSafeSerializer(SECRET_KEY, salt="session")


def create_session_token(user_id: int) -> str:
    return serializer.dumps({"user_id": user_id})


def decode_session_token(token: str):
    try:
        data = serializer.loads(token)
        return data.get("user_id")
    except Exception:
        return None