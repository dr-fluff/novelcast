# novelcast/api/routes/static.py

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()
COVERS_DIR = (Path(__file__).resolve().parent.parent / "data" / "covers").resolve()
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _resolve_cover_path(path: str) -> Path | None:
    """Resolve both managed cover filenames and legacy filesystem paths."""
    requested = Path(path)

    if requested.is_absolute():
        candidate = requested.resolve()
        return candidate if candidate.is_file() else None

    # Uploaded and URL-fetched covers are stored as a filename in COVERS_DIR.
    # Check this first so they do not depend on the process working directory.
    if requested.parent == Path("."):
        managed_cover = (COVERS_DIR / requested.name).resolve()
        if managed_cover.is_file():
            return managed_cover

    # Keep existing relative paths working for stories imported before managed
    # covers were introduced.
    for base_dir in (Path.cwd(), PROJECT_ROOT):
        candidate = (base_dir / requested).resolve()
        if candidate.is_file():
            return candidate

    return None


@router.get("/covers")
def get_cover(path: str):
    file_path = _resolve_cover_path(path)
    if not file_path:
        raise HTTPException(status_code=404, detail="Cover not found")
    return FileResponse(file_path)


@router.get("/favicon.svg")
def favicon():
    path = Path(__file__).resolve().parent.parent / "static/images/favicon.svg"
    return FileResponse(path, media_type="image/svg+xml")
