from fastapi import APIRouter

from app.services.memory_service import get_memory_store

router = APIRouter(tags=["System"])
memory_store = get_memory_store()


@router.get(
    "/health",
    summary="Health Check",
    description="Returns API health and memory backend status for monitoring.",
    responses={
        200: {"description": "Service is running and reachable."},
    },
)
async def health_check():
    return {
        "status": "healthy",
        "message": "API is running",
        "long_term_memory": {
            "enabled": memory_store.enabled,
            "backend": "postgres" if memory_store.enabled else "disabled",
        },
    }
