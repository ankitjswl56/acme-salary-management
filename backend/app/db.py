import os

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

import app.models  # noqa: F401 - registers models with SQLModel.metadata
from app.config import settings

engine = create_engine(
    f"sqlite:///{settings.database_path}",
    connect_args={"check_same_thread": False},
)


def apply_sqlite_pragmas(dbapi_connection) -> None:
    """PRAGMAs applied to every new SQLite connection.

    - WAL + synchronous=NORMAL: readers (the analytics dashboard) no longer
      block, or get blocked by, the seed transaction and CRUD writes.
    - foreign_keys=ON: SQLite leaves FK enforcement off by default. Every
      write path here already inserts parent-before-child, so this only
      turns a latent bug into a loud one.
    - temp_store=MEMORY: keeps the current-salary window query's sort off disk.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.close()


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):  # pragma: no cover - thin adapter
    apply_sqlite_pragmas(dbapi_connection)


def init_db() -> None:
    db_dir = os.path.dirname(settings.database_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session