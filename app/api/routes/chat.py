import json
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logging import get_logger
from app.api.schemas.chat import ChatRequest
from app.agents.agent_core import app as graph_app
from app.services.chat_service import (
    build_long_term_memory_context,
    persist_assistant_message,
    persist_user_message,
)

router = APIRouter(tags=["Chat"])
logger = get_logger(__name__)
MAX_TEXT_CHARS = 8000


def _truncate_text(text: str, limit: int = MAX_TEXT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "... [truncated]"


def _to_json_safe(value: Any, depth: int = 0) -> Any:
    if depth > 6:
        return "[max-depth-reached]"

    if value is None or isinstance(value, (bool, int, float)):
        return value

    if isinstance(value, str):
        return _truncate_text(value)

    if isinstance(value, (list, tuple, set)):
        return [_to_json_safe(item, depth + 1) for item in value]

    if isinstance(value, dict):
        safe_dict: dict[str, Any] = {}
        for key, item in value.items():
            safe_dict[str(key)] = _to_json_safe(item, depth + 1)
        return safe_dict

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return _to_json_safe(model_dump(), depth + 1)
        except Exception:
            pass

    to_dict = getattr(value, "dict", None)
    if callable(to_dict):
        try:
            return _to_json_safe(to_dict(), depth + 1)
        except Exception:
            pass

    if hasattr(value, "content"):
        return {
            "_type": value.__class__.__name__,
            "content": _to_json_safe(getattr(value, "content", ""), depth + 1),
        }

    value_dict = getattr(value, "__dict__", None)
    if isinstance(value_dict, dict):
        compact: dict[str, Any] = {
            "_type": value.__class__.__name__,
        }
        for key in ("name", "tool_call_id", "status", "content", "id"):
            if key in value_dict:
                compact[key] = _to_json_safe(value_dict.get(key), depth + 1)
        if len(compact) > 1:
            return compact

    return _truncate_text(str(value))


def _sse(event_type: str, content: Any, *, meta: dict[str, Any] | None = None) -> str:
    payload: dict[str, Any] = {
        "type": event_type,
        "content": _to_json_safe(content),
    }
    if meta:
        payload["meta"] = _to_json_safe(meta)

    return "data: " + json.dumps(payload, ensure_ascii=False) + "\n\n"


def _content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
                elif "text" in item:
                    parts.append(str(item.get("text", "")))
            else:
                parts.append(str(item))
        return "".join(parts)
    return str(content)


def _extract_final_agent_text(output: Any) -> str:
    if not isinstance(output, dict):
        return ""

    messages = output.get("messages")
    if not isinstance(messages, list) or not messages:
        return ""

    last = messages[-1]
    tool_calls = getattr(last, "tool_calls", None)
    if tool_calls:
        return ""

    return _content_to_text(getattr(last, "content", "")).strip()


def _try_parse_card(text: str) -> dict | None:
    raw = str(text or "").strip()
    if not raw:
        return None

    if raw.startswith("```json"):
        raw = raw.replace("```json", "").replace("```", "").strip()

    if raw.startswith("{") and raw.endswith("}"):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    return None


def _tool_reason(tool_name: str, tool_input: Any) -> str:
    normalized_name = str(tool_name or "").strip().lower()
    input_text = _content_to_text(tool_input).strip()
    input_hint = _truncate_text(input_text, 180) if input_text else "the current user query"

    reason_map = {
        "check_weather": "Using weather data to adjust travel timing and packing guidance.",
        "find_hotels": "Finding hotel options that match destination and preferences.",
        "google_places_search": "Collecting nearby attractions and place details.",
        "duckduckgo_web_search": "Gathering broader web context for travel information.",
        "get_static_map": "Building a visual map view to improve location understanding.",
        "generate_trip_plan": "Generating a structured itinerary from your constraints.",
    }

    base_reason = reason_map.get(normalized_name, "Using this tool to fetch external data needed for the response.")
    return f"{base_reason} Input focus: {input_hint}"


def _tool_sources(tool_name: str) -> list[str]:
    normalized_name = str(tool_name or "").strip().lower()
    source_map = {
        "check_weather": ["Open-Meteo Geocoding API", "Open-Meteo Forecast API"],
        "google_places_search": ["Google Places API"],
        "duckduckgo_web_search": ["DuckDuckGo Instant Answer API"],
        "get_map_view": ["Google Static Maps API"],
        "find_hotels": ["Amadeus OAuth API", "Amadeus Hotel Search API"],
        "get_destination_photo": ["Unsplash API"],
        "get_current_date": ["Local system clock"],
        "generate_trip_plan": ["OpenAI Structured Output", "Unsplash API (internal image fetch)", "Google Static Maps API (internal map build)"],
    }
    return source_map.get(normalized_name, ["Unknown external source"])


def _tool_output_summary(tool_name: str, output: Any) -> str:
    normalized_name = str(tool_name or "").strip().lower()
    text = _content_to_text(output).strip()

    if normalized_name == "check_weather":
        if "Weather forecast for" in text:
            header = text.splitlines()[0].strip()
            return f"Weather data fetched successfully. {header}"
        return "Weather lookup completed."

    if normalized_name == "find_hotels":
        if "Hotels found" in text:
            return text.splitlines()[0].strip()
        return "Hotel lookup completed."

    if normalized_name in {"google_places_search", "duckduckgo_web_search"}:
        lines = [line.strip() for line in text.splitlines() if line.strip().startswith("-")]
        if lines:
            return f"Found {len(lines)} result item(s)."
        return "Search completed."

    if normalized_name == "get_destination_photo":
        if "unsplash" in text.lower():
            return "Destination photo fetched from Unsplash."
        return "Photo lookup completed."

    if normalized_name == "generate_trip_plan":
        try:
            raw = text
            if raw.startswith("```json"):
                raw = raw.replace("```json", "").replace("```", "").strip()
            data = json.loads(raw)
            trip = data.get("trip", {}) if isinstance(data, dict) else {}
            details = data.get("details", {}) if isinstance(data, dict) else {}
            destination = trip.get("destination") or trip.get("title") or "destination"
            days = len(details.get("days", []) or [])
            has_map = bool((details.get("static_map") or {}).get("image_url"))
            has_main_image = bool(trip.get("image_url"))
            return (
                f"Generated structured itinerary for {destination}. "
                f"Days: {days}. Main image: {'yes' if has_main_image else 'no'}. Map: {'yes' if has_map else 'no'}."
            )
        except Exception:
            return "Trip plan generation completed."

    return "Tool execution completed."


@router.post(
    "/chat/stream",
    summary="Stream Chat With Thinking",
    description=(
        "Streams LangGraph v2 Server-Sent Events (SSE) including model thoughts, "
        "tool start/end events, and final assistant message."
    ),
    responses={
        200: {"description": "SSE stream started successfully."},
    },
)
async def chat_stream(request: ChatRequest):
    async def event_generator():
        final_text = ""
        final_result: dict[str, Any] = {"type": "text", "data": ""}
        session_id = request.session_id

        try:
            persist_user_message(request.session_id, request.prompt)

            messages = []
            memory_context = build_long_term_memory_context(request.session_id)
            if memory_context:
                messages.append(SystemMessage(content=memory_context))
            messages.append(HumanMessage(content=request.prompt))

            run_config = {"configurable": {"thread_id": request.session_id}, "recursion_limit": 30}

            async for event in graph_app.astream_events(
                {"messages": messages},
                config=run_config,
                version="v2",
            ):
                try:
                    event_name = event.get("event")
                    data = event.get("data", {})
                    name = event.get("name", "")
                    run_id = str(event.get("run_id", ""))

                    if event_name == "on_chat_model_stream":
                        chunk = data.get("chunk")
                        token = _content_to_text(getattr(chunk, "content", ""))
                        if token:
                            yield _sse(
                                "thought",
                                token,
                                meta={
                                    "session_id": session_id,
                                    "event": event_name,
                                    "run_id": run_id,
                                },
                            )
                        continue

                    if event_name == "on_tool_start":
                        logger.info("tool_start session_id=%s tool=%s", session_id, name)
                        yield _sse(
                            "tool",
                            {
                                "phase": "start",
                                "name": name,
                                "reason": _tool_reason(name, data.get("input")),
                                "sources": _tool_sources(name),
                                "input": data.get("input"),
                            },
                            meta={
                                "session_id": session_id,
                                "event": event_name,
                                "run_id": run_id,
                            },
                        )
                        continue

                    if event_name == "on_tool_end":
                        logger.info("tool_end session_id=%s tool=%s", session_id, name)
                        output = data.get("output")
                        yield _sse(
                            "tool",
                            {
                                "phase": "end",
                                "name": name,
                                "reason": "Tool execution completed and output is now being used for final response synthesis.",
                                "sources": _tool_sources(name),
                                "summary": _tool_output_summary(name, output),
                                "output": output,
                            },
                            meta={
                                "session_id": session_id,
                                "event": event_name,
                                "run_id": run_id,
                            },
                        )
                        continue

                    if event_name == "on_chain_end" and name == "agent":
                        candidate = _extract_final_agent_text(data.get("output"))
                        if candidate:
                            final_text = candidate
                except Exception as event_err:
                    logger.exception("event_processing_failed session_id=%s", session_id)
                    yield _sse(
                        "error",
                        "A stream event could not be processed.",
                        meta={
                            "session_id": session_id,
                            "detail": str(event_err),
                        },
                    )

            if not final_text:
                final_text = "Sorry, I couldn't process your request."

            card = _try_parse_card(final_text)
            if card is not None:
                final_result = {"type": "card", "data": card}
                yield _sse(
                    "message",
                    json.dumps(card, ensure_ascii=False),
                    meta={"session_id": session_id},
                )
            else:
                final_result = {"type": "text", "data": final_text}
                yield _sse("message", final_text, meta={"session_id": session_id})

            persist_assistant_message(request.session_id, final_result)
            yield _sse("done", "completed", meta={"session_id": session_id})
        except Exception as e:
            logger.exception("chat_stream_failed session_id=%s", session_id)
            yield _sse("error", "Streaming failed.", meta={"session_id": session_id, "detail": str(e)})

    return StreamingResponse(event_generator(), media_type="text/event-stream")
