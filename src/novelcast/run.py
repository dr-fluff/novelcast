# src/novelcast/run.py

import uvicorn
from novelcast.settings import settings


def main():
    uvicorn.run(
        "novelcast.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )