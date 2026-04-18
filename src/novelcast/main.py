# src/novelcast/__main__.py

import uvicorn
from pathlib import Path
import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from novelcast.api.routes import router

# Set up logging
logging.basicConfig(
    filename='novelcast.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = FastAPI(title="NovelCast")

BASE_DIR = Path(__file__).resolve().parent
static_dir = BASE_DIR / "web" / "templates" / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(router)

def main():
    uvicorn.run(
        "novelcast.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )