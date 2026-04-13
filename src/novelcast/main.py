# src/novelcast/__main__.py

import uvicorn

from fastapi import FastAPI
from novelcast.api.routes import router

app = FastAPI(title="NovelCast")

app.include_router(router)

def main():
    uvicorn.run(
        "novelcast.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )