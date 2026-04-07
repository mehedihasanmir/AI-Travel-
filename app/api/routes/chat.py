import asyncio
import json
import re

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.schemas.chat import ChatRequest
from app.services.chat_service import chat_agent, persist_assistant_message, persist_user_message

router = APIRouter(tags=["Chat"])


@router.post(
    "/chat/stream",
    summary="Stream Chat Response",
    description="Streams assistant output as Server-Sent Events (SSE) with token, card, done, and error event types.",
    responses={
        200: {"description": "SSE stream started successfully."},
    },
)
async def chat_stream(request: ChatRequest):
    async def event_generator():
        try:
            persist_user_message(request.session_id, request.prompt)
            result = chat_agent(request.prompt, request.session_id)

            if result.get("type") == "card":
                payload = {"type": "card", "data": result.get("data", {})}
                yield "data: " + json.dumps(payload, ensure_ascii=False) + "\n\n"
            else:
                text = str(result.get("data", "") or "")
                chunks = re.findall(r"\S+\s*", text)
                if not chunks:
                    chunks = [text]

                for chunk in chunks:
                    yield "data: " + json.dumps({"type": "token", "data": chunk}, ensure_ascii=False) + "\n\n"
                    await asyncio.sleep(0.015)

            persist_assistant_message(request.session_id, result)
            yield "data: " + json.dumps({"type": "done"}) + "\n\n"
        except Exception as e:
            yield "data: " + json.dumps({"type": "error", "data": str(e)}) + "\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
