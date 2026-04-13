# src/novelcast/__main__.py

import uvicorn

def main():
    uvicorn.run("novelcast.main:app", host="127.0.0.1", port=8000, reload=True)