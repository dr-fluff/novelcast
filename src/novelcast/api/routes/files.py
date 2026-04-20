from fastapi import APIRouter
from novelcast.services.file_service import FileService

router = APIRouter()
service = FileService()

def get_router():
    return router

@router.get("/{file_id}")
def read_file(file_id: int):
    return {"content": service.get_file_content(file_id)}