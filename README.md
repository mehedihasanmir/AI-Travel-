# AI-Travel-

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688?logo=fastapi&logoColor=white)
![Uvicorn](https://img.shields.io/badge/Uvicorn-ASGI-222222)
![Pydantic](https://img.shields.io/badge/Pydantic-2.x-E92063?logo=pydantic&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-Core-1.x-1C3C3C)
![LangGraph](https://img.shields.io/badge/LangGraph-1.x-FF6B00)
![OpenAI](https://img.shields.io/badge/OpenAI-API-412991?logo=openai&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Optional-336791?logo=postgresql&logoColor=white)
![Requests](https://img.shields.io/badge/Requests-HTTP-20232A)
![python-dotenv](https://img.shields.io/badge/python--dotenv-Env%20Config-4E8A08)

A layered AI travel planning backend and web chat UI built with FastAPI, LangGraph, and OpenAI.

This project is backend-first and includes:

- Chat and streaming chat APIs
- Tool-driven travel assistant (weather, places, maps, hotels, photo, itinerary)
- Optional PostgreSQL-backed long-term memory and session management
- Template-based frontend served directly from FastAPI

## Table of Contents

- Overview
- Architecture
- Project Structure
- Requirements
- Environment Variables
- Installation
- Running the Server
- Demo
- API Endpoints
- How to Use (User Flow)
- Development Notes
- Troubleshooting

## Overview

`AI-Travel-` provides a travel assistant system where user prompts are processed by a LangGraph agent that can call external travel tools and return either:

- Text responses
- Structured trip cards (JSON)
- Streamed token responses (SSE)

The backend also supports session history and title generation, with optional persistence in PostgreSQL.

## Architecture

1. Client sends prompt to `POST /chat/stream`
2. API route validates request schema
3. Service layer invokes LangGraph agent
4. Agent chooses tools based on prompt intent
5. Tool output is merged into final assistant response
6. Response is returned as SSE token stream or card payload
7. Session/memory data is persisted when database is configured

## Project Structure

```text
AI-Travel-/
	app/
		main.py
		core/
			config.py
			logging.py
		api/
			server.py
			routes/
				chat.py
				memory.py
				health.py
				ui.py
			schemas/
				chat.py
				memory.py
		services/
			chat_service.py
			memory_service.py
			title_service.py
		repositories/
			memory_repo.py
		agents/
			agent_core.py
		tools/
			travel_tools.py
		models/
			trip_models.py
		templates/
			frontend_chat.html
		static/
			css/
				style.css
			js/
				app.js
	.env
	requirements.txt
	README.md
```

## Requirements

- Python 3.10 or later
- pip
- Optional: PostgreSQL (for long-term memory/session persistence)

Primary libraries/frameworks used:

- FastAPI
- Uvicorn
- Pydantic
- LangChain Core
- LangGraph
- LangChain OpenAI
- OpenAI SDK
- Requests
- python-dotenv
- psycopg2-binary (optional path, when PostgreSQL is enabled)

## Environment Variables

Create a `.env` file in the project root.

Required for core AI functionality:

- `OPENAI_API_KEY`

Optional integrations:

- `GOOGLE_API_KEY`
- `AMADEUS_CLIENT_ID`
- `AMADEUS_CLIENT_SECRET`
- `UNSPLASH_ACCESS_KEY`
- `DATABASE_URL`

Example:

```env
OPENAI_API_KEY=your_openai_key
GOOGLE_API_KEY=your_google_key
AMADEUS_CLIENT_ID=your_amadeus_client_id
AMADEUS_CLIENT_SECRET=your_amadeus_client_secret
UNSPLASH_ACCESS_KEY=your_unsplash_access_key
DATABASE_URL=postgresql://user:password@localhost:5432/ai_travel
```

Notes:

- If `DATABASE_URL` is empty, memory/session features will degrade gracefully.
- Health responses expose whether memory backend is enabled.

## Installation

1. Clone repository and enter project directory.
2. Create virtual environment.
3. Install dependencies from `requirements.txt`.

Windows PowerShell:

```powershell
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Running the Server

Recommended command:

```bash
python -m app.main api
```

Alternative command:

```bash
python app/main.py api
```

After startup:

- API base: `http://127.0.0.1:8000`
- Docs: `http://127.0.0.1:8000/docs`
- UI: `http://127.0.0.1:8000/ui`

## Demo

Video walkthrough:

- [Watch Demo Video (Google Drive)](https://drive.google.com/file/d/12fH3g2mtb-uuYG3qATlpTMKOOporgojd/view?usp=sharing)

Demo screenshots:

![Demo Screenshot 1](demo/Screenshot%202026-04-14%20171659.png)
![Demo Screenshot 2](demo/Screenshot%202026-04-14%20182859.png)
![Demo Screenshot 3](demo/Screenshot%202026-04-14%20183017.png)
![Demo Screenshot 4](demo/Screenshot%202026-04-14%20183044.png)
![Demo Screenshot 5](demo/Screenshot%202026-04-14%20183059.png)

## API Endpoints

### Keep Endpoints

- `GET /ui`
- `GET /memory-sessions`
- `POST /memory-sessions`
- `POST /memory-sessions/title`
- `GET /memory/{session_id}`
- `POST /chat/stream` (SSE)
- `GET /health`

Request body:

```json
{
	"prompt": "Plan a 3 day trip to Cox's Bazar",
	"session_id": "session-123"
}
```

### Static Assets

- `GET /static/css/style.css`
- `GET /static/js/app.js`

## How to Use (User Flow)

1. Start backend server.
2. Open `http://127.0.0.1:8000/ui`.
3. Enter travel prompts in the chat composer.
4. Use `Enter` to send and `Shift+Enter` for newline.
5. For itinerary prompts, assistant can return structured trip cards.
6. For normal prompts, assistant returns text responses.
7. Sessions can be revisited from the left session list.

Prompt examples:

- `Check weather in Dhaka`
- `Find hotels in Bangkok`
- `Show map view of Paris`
- `Create a 4 day itinerary for Sylhet`

## Development Notes

- API assembly and app startup: `app/api/server.py`
- Main backend business logic: `app/services/chat_service.py`
- Memory lifecycle and store selection: `app/services/memory_service.py`
- Persistent memory repository: `app/repositories/memory_repo.py`
- Agent graph and tool binding: `app/agents/agent_core.py`
- External tools: `app/tools/travel_tools.py`

## Recent Backend AI Updates

- Migrated chat streaming to LangGraph `astream_events(version="v2")`.
- Added production-safe SSE serialization for complex LangChain/LangGraph objects.
- Implemented per-event fault isolation so one bad event does not terminate the full stream.
- Added tool-level trace metadata:
  - execution phase
  - reasoning
  - source attribution
  - summarized output
- Improved session-aware state continuity using `thread_id = session_id`.

## Troubleshooting

### `ModuleNotFoundError: No module named 'app'`

Use module mode run:

```bash
python -m app.main api
```

### Server starts but UI has no styling or JS

Check static mounts and paths:

- `GET /static/css/style.css`
- `GET /static/js/app.js`

### Memory/session APIs return disabled state

- Verify `DATABASE_URL` in `.env`
- Ensure PostgreSQL is reachable

### External tool responses fail

Check optional API keys in `.env`:

- Google, Amadeus, Unsplash

### Dependency issues

Reinstall dependencies:

```bash
pip install -r requirements.txt
```

## Important Notes

- This project is designed with a backend-first architecture and real-time SSE streaming for AI responses.
- Memory and session features are available even when PostgreSQL is not configured (graceful fallback mode).
- For production use, configure strict CORS, HTTPS, and secure environment variable management.

## Future Improvements

- Add user authentication and role-based access control for secure multi-user usage.
- Introduce caching and rate limiting to improve performance and API reliability.
- Expand travel intelligence with flight fare tracking and budget optimization suggestions.
- Add automated tests and CI pipeline for better code quality and release confidence.
- Containerize deployment with Docker and add production-ready monitoring/logging.

## Security Notes

- Never commit real credentials to source control.
- Keep `.env` values private and rotate keys immediately if exposed.
- Use least-privilege API keys and provider-side usage limits.

## Connect with Me

- GitHub: [mehedihasanmir](https://github.com/mehedihasanmir)
- LinkedIn: [LinkedIn](https://www.linkedin.com/in/mehedi-hasan-mir/)

## Streaming Event Contract

`POST /chat/stream` returns Server-Sent Events (SSE) as JSON payloads.

Event schema:

```json
{
  "type": "thought | tool | message | done | error",
  "content": "string | object",
  "meta": {
    "session_id": "session-123",
    "event": "on_tool_start",
    "run_id": "..."
  }
}
```
