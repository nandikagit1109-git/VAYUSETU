"""SQLModel engine + session helpers (SQLite — no external DB server needed)."""
from contextlib import contextmanager

from sqlmodel import SQLModel, Session, create_engine

from .config import DATABASE_URL

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session():
    with Session(engine) as session:
        yield session
