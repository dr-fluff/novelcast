# novelcast/main.py

import uvicorn

from novelcast.app.factory import create_app
from novelcast.core.config import AppConfig


def get_app():
    config = AppConfig()
    return create_app(config)


# This is what ASGI servers (uvicorn, gunicorn) will use
app = get_app()


if __name__ == "__main__":
    config = AppConfig()

    uvicorn.run(
        "novelcast.main:app",
        host=config.host,
        port=config.port,
        reload=config.reload,
        reload_dirs=["src"],
        reload_excludes=["*.pyc", "__pycache__/*"],
        log_level=config.log_level,
        ws="websockets",
    )
