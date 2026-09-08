import os
from contextlib import contextmanager

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = os.environ.get("DATABASE_URL") or "sqlite:///fixme.db"
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(DATABASE_URL)

# Tables that existed before the "owner" column was added need it backfilled onto
# already-created tables — create_all() only creates missing tables, never alters existing ones.
_OWNER_TABLES = ["task", "habit", "habitlog", "pomodorosession"]


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table in _OWNER_TABLES:
            columns = {c["name"] for c in inspector.get_columns(table)}
            if "owner" not in columns:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN owner VARCHAR DEFAULT 'owner'"))


@contextmanager
def get_session():
    with Session(engine) as session:
        yield session
