from fastapi import APIRouter, Request, HTTPException

router = APIRouter()

@router.delete("/stories/{story_id}")
def delete_story(request: Request, story_id: int):
    ctx = request.app.state.ctx
    story = ctx.stories.get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    try:
        ctx.stories.delete_story(story_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return {"status": "ok"}
