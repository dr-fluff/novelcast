# api/routes/files.py

from fastapi import APIRouter, Request

router = APIRouter()


def files(request: Request):
    return request.app.state.files


# ─────────────────────────────
# Read file
# ─────────────────────────────
@router.get("/{file_id}")
def read_file(request: Request, file_id: int):
    return {"content": files(request).get_file_content(file_id)}