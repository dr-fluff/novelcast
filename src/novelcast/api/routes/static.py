# novelcast/api/routes/static.py

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()


@router.get("/covers")
def get_cover(path: str):
    file_path = Path(path).resolve()
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Cover not found")
    return FileResponse(file_path)


@router.get("/favicon.svg")
def favicon():
    path = Path(__file__).resolve().parent.parent / "static/images/favicon.svg"
    return FileResponse(path, media_type="image/svg+xml")
