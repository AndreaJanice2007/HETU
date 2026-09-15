from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DB_PATH = Path(__file__).resolve().parent.parent / "hetu.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def _add_column_if_missing(conn, table: str, column: str, ddl: str) -> None:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    names = {row[1] for row in rows}
    if column not in names:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


def ensure_schema() -> None:
    with engine.begin() as conn:
        tables = {row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()}
        if "flags" in tables:
            _add_column_if_missing(conn, "flags", "severity", "severity VARCHAR(16) DEFAULT 'high'")
            _add_column_if_missing(conn, "flags", "root_cause", "root_cause VARCHAR(80) DEFAULT 'Label mismatch'")
        if "diagnoses" in tables:
            _add_column_if_missing(conn, "diagnoses", "disclosure_reason", "disclosure_reason VARCHAR(160)")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
