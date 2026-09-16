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


def _drop_column_if_present(conn, table: str, column: str) -> None:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    names = {row[1] for row in rows}
    if column in names:
        conn.execute(text(f"ALTER TABLE {table} DROP COLUMN {column}"))


def ensure_schema() -> None:
    with engine.begin() as conn:
        tables = {row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()}
        if "users" in tables:
            _add_column_if_missing(conn, "users", "username", "username VARCHAR(80)")
            _add_column_if_missing(conn, "flags", "severity", "severity VARCHAR(16) DEFAULT 'high'")
            _add_column_if_missing(conn, "flags", "root_cause", "root_cause VARCHAR(80) DEFAULT 'Label mismatch'")
            _add_column_if_missing(conn, "flags", "ai_reasoning", "ai_reasoning TEXT")
            _add_column_if_missing(conn, "flags", "resolution_deadline", "resolution_deadline DATETIME")
            _add_column_if_missing(conn, "flags", "assigned_doctor_id", "assigned_doctor_id INTEGER")
            _add_column_if_missing(conn, "flags", "judge_pool_open", "judge_pool_open BOOLEAN DEFAULT 0")
            _add_column_if_missing(conn, "flags", "patient_explanation", "patient_explanation TEXT")
            _add_column_if_missing(conn, "flags", "gap_answer", "gap_answer VARCHAR(32)")
            _add_column_if_missing(conn, "flags", "gap_detail", "gap_detail TEXT")
        if "doctors" in tables:
            _add_column_if_missing(conn, "doctors", "qualification_score", "qualification_score FLOAT DEFAULT 0")
            _add_column_if_missing(conn, "doctors", "years_experience", "years_experience INTEGER DEFAULT 0")
            _add_column_if_missing(conn, "doctors", "research_count", "research_count INTEGER DEFAULT 0")
            _add_column_if_missing(conn, "doctors", "resolved_cases_count", "resolved_cases_count INTEGER DEFAULT 0")
            _add_column_if_missing(conn, "doctors", "credibility_score", "credibility_score FLOAT DEFAULT 0")
        if "diagnoses" in tables:
            _add_column_if_missing(conn, "diagnoses", "disclosure_reason", "disclosure_reason VARCHAR(160)")
        if "guest_judge_invites" in tables:
            _add_column_if_missing(conn, "guest_judge_invites", "verified", "verified BOOLEAN DEFAULT 0")
            _add_column_if_missing(conn, "guest_judge_invites", "judgment_choice", "judgment_choice VARCHAR(32)")
            _add_column_if_missing(conn, "guest_judge_invites", "judgment_explanation", "judgment_explanation TEXT")
        if "doctor_conversations" in tables:
            _add_column_if_missing(conn, "doctor_conversations", "schedule_deadline", "schedule_deadline DATETIME")
        if "medical_reports" in tables:
            _add_column_if_missing(conn, "medical_reports", "notes", "notes TEXT DEFAULT ''")
            _add_column_if_missing(conn, "medical_reports", "source", "source VARCHAR(32) DEFAULT 'typed'")
            _add_column_if_missing(conn, "medical_reports", "original_filename", "original_filename VARCHAR(255)")
            _add_column_if_missing(conn, "medical_reports", "file_path", "file_path VARCHAR(255)")
            _add_column_if_missing(conn, "medical_reports", "submitted_by_user_id", "submitted_by_user_id INTEGER")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
