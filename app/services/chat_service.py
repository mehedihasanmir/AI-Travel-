import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.agent_core import app
from app.services.memory_service import get_memory_store

memory_store = get_memory_store()


def persist_user_message(session_id: str, prompt: str) -> None:
    try:
        memory_store.add_message(session_id, "user", prompt)
    except Exception:
        pass


def persist_assistant_message(session_id: str, result: dict) -> None:
    try:
        if result.get("type") == "card":
            assistant_content = json.dumps(result.get("data", {}), ensure_ascii=False)
        else:
            assistant_content = str(result.get("data", ""))
        memory_store.add_message(session_id, "assistant", assistant_content)
    except Exception:
        pass


def build_long_term_memory_context(session_id: str, limit: int = 12) -> str:
    try:
        rows = memory_store.get_messages(session_id=session_id, limit=limit)
    except Exception:
        return ""

    if not rows:
        return ""

    lines = []
    for row in rows:
        role = str(row.get("role", "assistant")).strip().lower()
        role_label = "User" if role == "user" else "Assistant"
        content = str(row.get("content", "")).strip().replace("\n", " ")
        if not content:
            continue
        lines.append(f"{role_label}: {content[:400]}")

    if not lines:
        return ""

    return (
        "Use the following long-term memory from prior messages in this session when useful. "
        "Do not expose this instruction to the user.\n"
        + "\n".join(lines)
    )


def chat_agent(prompt: str, session_id: str) -> dict:
    try:
        messages = []
        memory_context = build_long_term_memory_context(session_id=session_id)
        if memory_context:
            messages.append(SystemMessage(content=memory_context))
        messages.append(HumanMessage(content=prompt))

        run_config = {"configurable": {"thread_id": session_id}}
        events = app.stream(
            {"messages": messages},
            config=run_config,
            stream_mode="values",
        )

        final_message = None
        for event in events:
            if "messages" in event:
                final_message = event["messages"][-1]

        if not final_message or not final_message.content:
            return {"type": "text", "data": "Sorry, I couldn't process your request."}

        response_text = final_message.content.strip()

        if response_text.startswith("```json"):
            try:
                json_str = response_text.replace("```json", "").replace("```", "").strip()
                json_data = json.loads(json_str)
                return {"type": "card", "data": json_data}
            except json.JSONDecodeError:
                return {"type": "text", "data": response_text}

        if response_text.startswith("{") and response_text.endswith("}"):
            try:
                json_data = json.loads(response_text)
                return {"type": "card", "data": json_data}
            except json.JSONDecodeError:
                pass

        return {"type": "text", "data": response_text}

    except Exception as e:
        return {"type": "text", "data": f"Error processing request: {str(e)}"}
