from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/sessions/{session_id}/trace", summary="Return structured agent trace for a session")
async def get_trace(session_id: str):
    # TODO(post-MVP): stream JSONL trace file as SSE; render as timeline in UI
    return JSONResponse(status_code=501, content={"error": "not_implemented", "phase": "post-MVP"})
