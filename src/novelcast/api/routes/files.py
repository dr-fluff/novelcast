from fastapi import APIRouter, Depends

from novelcast.api.deps import get_files
from novelcast.services import FileService

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/{file_id}")
def read_file(
    file_id: int,
    files: FileService = Depends(get_files),
):
    return {"content": files.get_file_content(file_id)}
