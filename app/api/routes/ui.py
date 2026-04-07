from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(tags=["UI"])


@router.get(
    "/ui",
    summary="Open Web UI",
    description="Serves the main chat frontend template.",
    responses={
        200: {"description": "HTML page returned successfully."},
        404: {"description": "Frontend template file not found."},
    },
)
async def ui_page():
    frontend_path = Path(__file__).resolve().parents[2] / "templates" / "frontend_chat.html"
    if not frontend_path.exists():
        raise HTTPException(status_code=404, detail="frontend_chat.html not found")
    return FileResponse(frontend_path)
