from __future__ import annotations

from importlib import import_module
from typing import Dict, List

try:
    psycopg2 = import_module("psycopg2")
    RealDictCursor = import_module("psycopg2.extras").RealDictCursor
except Exception:  # pragma: no cover
    psycopg2 = None
    RealDictCursor = None


class PostgresMemoryRepository:
    def __init__(self, database_url: str):
        self.database_url = (database_url or "").strip()

    @property
    def enabled(self) -> bool:
        return bool(self.database_url and psycopg2)

    def initialize(self) -> None:
        if not self.enabled:
            return

        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS chat_sessions (
                        session_id TEXT PRIMARY KEY,
                        title TEXT NOT NULL DEFAULT 'New Chat',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS chat_memory (
                        id BIGSERIAL PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated
                    ON chat_sessions (updated_at DESC);
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_chat_memory_session_time
                    ON chat_memory (session_id, created_at DESC, id DESC);
                    """
                )
            conn.commit()

    def _auto_title_from_prompt(self, text: str) -> str:
        value = str(text or "").strip().replace("\n", " ")
        if not value:
            return "New Chat"
        title = " ".join(value.split())
        if len(title) > 60:
            title = title[:57].rstrip() + "..."
        return title

    def create_session(self, session_id: str, title: str = "New Chat") -> None:
        if not self.enabled:
            return

        safe_session = (session_id or "").strip()
        safe_title = (title or "").strip() or "New Chat"
        if not safe_session:
            return

        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO chat_sessions (session_id, title)
                    VALUES (%s, %s)
                    ON CONFLICT (session_id)
                    DO UPDATE SET updated_at = NOW()
                    """,
                    (safe_session, safe_title),
                )
            conn.commit()

    def set_session_title(self, session_id: str, title: str) -> None:
        if not self.enabled:
            return

        safe_session = (session_id or "").strip()
        safe_title = (title or "").strip()
        if not safe_session or not safe_title:
            return

        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO chat_sessions (session_id, title)
                    VALUES (%s, %s)
                    ON CONFLICT (session_id)
                    DO UPDATE SET title = EXCLUDED.title, updated_at = NOW()
                    """,
                    (safe_session, safe_title),
                )
            conn.commit()

    def add_message(self, session_id: str, role: str, content: str) -> None:
        if not self.enabled:
            return

        safe_session = (session_id or "").strip()
        safe_role = (role or "").strip() or "assistant"
        safe_content = (content or "").strip()
        if not safe_session or not safe_content:
            return

        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO chat_sessions (session_id, title)
                    VALUES (%s, 'New Chat')
                    ON CONFLICT (session_id)
                    DO NOTHING
                    """,
                    (safe_session,),
                )

                if safe_role == "user":
                    generated = self._auto_title_from_prompt(safe_content)
                    cur.execute(
                        """
                        UPDATE chat_sessions
                        SET title = CASE
                            WHEN title IS NULL OR title = '' OR LOWER(title) = 'new chat' THEN %s
                            ELSE title
                        END,
                        updated_at = NOW()
                        WHERE session_id = %s
                        """,
                        (generated, safe_session),
                    )
                else:
                    cur.execute(
                        """
                        UPDATE chat_sessions
                        SET updated_at = NOW()
                        WHERE session_id = %s
                        """,
                        (safe_session,),
                    )

                cur.execute(
                    """
                    INSERT INTO chat_memory (session_id, role, content)
                    VALUES (%s, %s, %s)
                    """,
                    (safe_session, safe_role, safe_content),
                )
            conn.commit()

    def get_messages(self, session_id: str, limit: int = 20) -> List[Dict]:
        if not self.enabled:
            return []

        safe_session = (session_id or "").strip()
        safe_limit = max(1, min(int(limit or 20), 100))
        if not safe_session:
            return []

        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, session_id, role, content, created_at
                    FROM chat_memory
                    WHERE session_id = %s
                    ORDER BY created_at DESC, id DESC
                    LIMIT %s
                    """,
                    (safe_session, safe_limit),
                )
                rows = cur.fetchall() or []

        rows.reverse()
        return [dict(row) for row in rows]

    def delete_session(self, session_id: str) -> int:
        if not self.enabled:
            return 0

        safe_session = (session_id or "").strip()
        if not safe_session:
            return 0

        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM chat_memory WHERE session_id = %s", (safe_session,))
                deleted = cur.rowcount
                cur.execute("DELETE FROM chat_sessions WHERE session_id = %s", (safe_session,))
            conn.commit()

        return int(deleted or 0)

    def get_sessions(self, limit: int = 50) -> List[Dict]:
        if not self.enabled:
            return []

        safe_limit = max(1, min(int(limit or 50), 200))

        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        s.session_id,
                        s.title,
                        s.updated_at AS last_message_at,
                        COALESCE(mc.message_count, 0)::INT AS message_count
                    FROM chat_sessions s
                    LEFT JOIN (
                        SELECT session_id, COUNT(*) AS message_count
                        FROM chat_memory
                        GROUP BY session_id
                    ) mc ON mc.session_id = s.session_id
                    ORDER BY s.updated_at DESC
                    LIMIT %s
                    """,
                    (safe_limit,),
                )
                rows = cur.fetchall() or []

        items: List[Dict] = []
        for row in rows:
            session_id = str(row.get("session_id", "")).strip()
            title = str(row.get("title", "")).strip() or session_id
            items.append(
                {
                    "session_id": session_id,
                    "title": title or session_id,
                    "last_message_at": row.get("last_message_at"),
                    "message_count": int(row.get("message_count", 0) or 0),
                }
            )

        return items
