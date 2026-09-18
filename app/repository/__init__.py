from typing import Optional

from app.repository.base import Repository

repo: Optional[Repository] = None


def init_repo(settings) -> Repository:
    global repo
    if settings.storage_type == "memory":
        from app.repository.memory import MemoryRepository

        repo = MemoryRepository()
    else:
        from app.repository.sqlite import SQLiteRepository

        repo = SQLiteRepository(settings.db_path)
    return repo


def get_repo() -> Repository:
    if repo is None:
        raise RuntimeError("Repository has not been initialized")
    return repo
