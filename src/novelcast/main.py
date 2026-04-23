# novelcast/main.py
from novelcast.app.factory import create_app
from novelcast.core.config import AppConfig
import uvicorn

config = AppConfig()
app = create_app(config)

if __name__ == "__main__":
    uvicorn.run(
        "novelcast.main:app",
        host=config.host,
        port=config.port,
        reload=config.reload,
        log_level=config.log_level,
    )