import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import HumanMessage

from app.agents.agent_core import app
from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router
from app.api.routes.memory import router as memory_router
from app.api.routes.ui import router as ui_router
from app.services.memory_service import initialize_memory

initialize_memory()

openapi_tags = [
    {
        "name": "UI",
        "description": "Frontend delivery endpoint.",
    },
    {
        "name": "System",
        "description": "Service health and monitoring endpoints.",
    },
    {
        "name": "Memory",
        "description": "Session listing, session creation, and conversation history endpoints.",
    },
    {
        "name": "Chat",
        "description": "Streaming chat endpoint backed by LangGraph agent and tools.",
    },
]

fastapi_app = FastAPI(
    title="AI Travel Agent API",
    description="Chat and travel planning API powered by LangGraph",
    version="1.0.0",
    openapi_tags=openapi_tags,
)

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).resolve().parents[1] / "static"
fastapi_app.mount("/static", StaticFiles(directory=static_dir), name="static")

fastapi_app.include_router(ui_router)
fastapi_app.include_router(health_router)
fastapi_app.include_router(memory_router)
fastapi_app.include_router(chat_router)


def run_cli_or_server() -> None:
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")

    if len(sys.argv) > 1 and sys.argv[1] == "api":
        print("Starting AI Travel Agent API server...")
        print("API available at http://localhost:8000")
        print("Interactive docs at http://localhost:8000/docs")
        uvicorn.run(fastapi_app, host="127.0.0.1", port=8000)
    else:
        print("AI Travel Agent Initialized. Type 'quit' to exit.")

        thread_id = "user-session-1"
        run_config = {"configurable": {"thread_id": thread_id}}

        while True:
            user_input = input("\nYou: ")
            if user_input.lower() in ["quit", "exit"]:
                break

            print("Agent is thinking...", end="", flush=True)

            events = app.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=run_config,
                stream_mode="values",
            )

            final_message = None
            for event in events:
                if "messages" in event:
                    final_message = event["messages"][-1]

            if final_message:
                print(f"\n\nAgent: {final_message.content}")


def main() -> None:
    run_cli_or_server()


if __name__ == "__main__":
    main()
