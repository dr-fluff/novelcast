# novelcast/api/routes/stories.py
 
from fastapi import APIRouter, Depends, HTTPException
 
from novelcast.api.deps import get_stories
from novelcast.services import StoryService
 
router = APIRouter(prefix="/stories", tags=["stories"])
 
 
@router.delete("/{story_id}")
def delete_story(
    story_id: int,
    stories: StoryService = Depends(get_stories),
):
    if not stories.get_story(story_id):
        raise HTTPException(status_code=404, detail="Story not found")
 
    try:
        stories.delete_story(story_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
 
    return {"status": "ok"}
 