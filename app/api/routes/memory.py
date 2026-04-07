from fastapi import APIRouter, HTTPException

from app.api.schemas.memory import SessionCreateRequest, SessionTitleRequest
from app.services.memory_service import get_memory_store
from app.services.title_service import generate_session_title

memory_store = get_memory_store()

router = APIRouter(tags=["Memory"])


@router.get(
    "/memory/{session_id}",
    summary="Get Session Memory",
    description="Returns conversation items for a session ordered oldest to newest.",
)
async def get_memory(session_id: str, limit: int = 20):
    try:
        items = memory_store.get_messages(session_id=session_id, limit=limit)
        return {
            "enabled": memory_store.enabled,
            "session_id": session_id,
            "count": len(items),
            "items": items,
        }
    except Exception as e:
        return {
            "enabled": False,
            "session_id": session_id,
            "count": 0,
            "items": [],
            "error": str(e),
        }


@router.get(
    "/memory-sessions",
    summary="List Sessions",
    description="Returns available chat sessions with title and message count.",
)
async def get_memory_sessions(limit: int = 50):
    try:
        items = memory_store.get_sessions(limit=limit)
        return {
            "enabled": memory_store.enabled,
            "count": len(items),
            "items": items,
        }
    except Exception as e:
        return {
            "enabled": False,
            "count": 0,
            "items": [],
            "error": str(e),
        }


@router.post(
    "/memory-sessions",
    summary="Create Session",
    description="Creates a new chat session record or updates timestamp if it already exists.",
)
async def create_memory_session(request: SessionCreateRequest):
    try:
        memory_store.create_session(session_id=request.session_id, title=request.title)
        return {
            "enabled": memory_store.enabled,
            "session_id": request.session_id,
            "title": request.title,
            "persisted": True,
        }
    except Exception as e:
        return {
            "enabled": False,
            "session_id": request.session_id,
            "title": request.title,
            "persisted": False,
            "error": str(e),
        }


@router.post(
    "/memory-sessions/title",
    summary="Generate Session Title",
    description="Generates a concise session title from the first user prompt and stores it.",
)
async def generate_memory_session_title(request: SessionTitleRequest):
    try:
        generated_title = generate_session_title(request.prompt)
        persisted = True
        try:
            memory_store.set_session_title(session_id=request.session_id, title=generated_title)
        except Exception:
            persisted = False

        return {
            "enabled": memory_store.enabled,
            "session_id": request.session_id,
            "title": generated_title,
            "persisted": persisted,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating session title: {str(e)}")
