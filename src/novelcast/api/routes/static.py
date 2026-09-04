# novelcast/api/routes/static.py

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()
PROJECT_ROOT = Path.cwd().resolve()
DATA_DIR = PROJECT_ROOT / "data"
COVERS_DIR = (DATA_DIR / "covers").resolve()
LEGACY_COVERS_DIR = (Path(__file__).resolve().parent.parent / "data" / "covers").resolve()


def _data_relative_path(path: Path) -> Path | None:
    try:
        data_index = path.parts.index("data")
    except ValueError:
        return None
    relative = Path(*path.parts[data_index + 1 :])
    return relative if relative.parts else None


def _resolve_cover_path(path: str) -> Path | None:
    """Resolve both managed cover filenames and legacy filesystem paths."""
    requested = Path(path)

    if requested.is_absolute():
        candidate = requested.resolve()
        if candidate.is_file():
            return candidate

        relative = _data_relative_path(requested)
        if relative:
            candidate = (DATA_DIR / relative).resolve()
            return candidate if candidate.is_file() else None
        return None

    # Uploaded and URL-fetched covers are stored as a filename in COVERS_DIR.
    # Check this first so they do not depend on the process working directory.
    if requested.parent == Path("."):
        for covers_dir in (COVERS_DIR, LEGACY_COVERS_DIR):
            managed_cover = (covers_dir / requested.name).resolve()
            if managed_cover.is_file():
                return managed_cover

    # Keep existing relative paths working for stories imported before managed
    # covers were introduced.
    for base_dir in (PROJECT_ROOT, DATA_DIR):
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
