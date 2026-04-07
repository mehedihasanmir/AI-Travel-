from app.core.config import DATABASE_URL
from app.repositories.memory_repo import PostgresMemoryRepository

memory_store = PostgresMemoryRepository(DATABASE_URL)


def initialize_memory() -> None:
    try:
        memory_store.initialize()
    except Exception:
        # Do not block API startup if DB is unavailable.
        pass


def get_memory_store() -> PostgresMemoryRepository:
    return memory_store
