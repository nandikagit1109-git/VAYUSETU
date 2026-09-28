"""SQLite engine + session helpers.

Sessions are created per request (and per background thread); they never cross
threads. check_same_thread=False is required because the engine is shared, and
is safe here only because every session is used by a single thread.
"""
from contextlib import contextmanager

from sqlmodel import Session, SQLModel, create_engine

from .config import DATABASE_URL
from .tables import AlertRow, CitizenReportRow  # noqa: F401  (import registers tables)

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session():
    with Session(engine) as session:
        yield session
