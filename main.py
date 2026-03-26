import json
import sys

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from agent_core import app
from config import DEFAULT_SESSION_ID

fastapi_app = FastAPI(
    title="AI Travel Agent API",
    description="Chat and travel planning API powered by LangGraph",
    version="1.0.0",
)

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    prompt: str = Field(..., description="User message")
    session_id: str = Field(
        default=DEFAULT_SESSION_ID,
        description="Session ID for conversation continuity",
    )


def chat_agent(prompt: str, session_id: str) -> dict:
    try:
        user_message = HumanMessage(content=prompt)
        run_config = {"configurable": {"thread_id": session_id}}

        events = app.stream(
            {"messages": [user_message]},
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

        # Card output: JSON trip plan wrapped in markdown code block
        if response_text.startswith("```json"):
            try:
                json_str = response_text.replace("```json", "").replace("```", "").strip()
                json_data = json.loads(json_str)
                return {"type": "card", "data": json_data}
            except json.JSONDecodeError:
                return {"type": "text", "data": response_text}

        # Card output: raw JSON content (without markdown wrapper)
        if response_text.startswith("{") and response_text.endswith("}"):
            try:
                json_data = json.loads(response_text)
                return {"type": "card", "data": json_data}
            except json.JSONDecodeError:
                pass

        return {"type": "text", "data": response_text}

    except Exception as e:
        return {"type": "text", "data": f"Error processing request: {str(e)}"}


@fastapi_app.get("/")
async def root():
    return {
        "message": "AI Travel Agent API",
        "version": "1.0.0",
        "endpoints": {
            "chat": "POST /chat",
            "health": "GET /health",
            "docs": "/docs",
        },
    }


@fastapi_app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is running"}


@fastapi_app.post("/chat")
async def chat(request: ChatRequest):
    try:
        result = chat_agent(request.prompt, request.session_id)
        return JSONResponse(content=result, status_code=200)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat request: {str(e)}")


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")

    if len(sys.argv) > 1 and sys.argv[1] == "api":
        print("Starting AI Travel Agent API server...")
        print("API available at http://localhost:8000")
        print("Interactive docs at http://localhost:8000/docs")
        uvicorn.run(fastapi_app, host="10.10.7.114", port=8003)
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

            print("\r" + " " * 30 + "\r", end="")

            if final_message:
                if final_message.content:
                    print(f"Agent: {final_message.content}")
                if final_message.tool_calls:
                    print(f"Agent: (Executing tools: {[tc['name'] for tc in final_message.tool_calls]})")
