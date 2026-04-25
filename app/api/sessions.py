from fastapi import APIRouter, HTTPException

from app import sessions
from app.api.report import _reports

router = APIRouter()


@router.get("/sessions", summary="List all gap-analysis sessions")
async def list_sessions():
    return sessions.list_all()


@router.get("/sessions/{session_id}", summary="Get session metadata")
async def get_session(session_id: str):
    entry = sessions.get(session_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    return entry


@router.get("/sessions/{session_id}/trace", summary="Return full report for a session")
async def get_trace(session_id: str):
    report = _reports.get(session_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found for this session")
    return report
