import re
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BACKEND_DIR / "reports"

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
ALLOWED_REPORT_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif"}
ALLOWED_REPORT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
}


def ensure_reports_dir() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    gitkeep = REPORTS_DIR / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()
    return REPORTS_DIR


def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", (name or "upload").strip()) or "upload"
    return cleaned[:80]


def save_report_file(report_id: int, filename: str, data: bytes) -> str:
    ensure_reports_dir()
    stored = f"{report_id}_{safe_filename(filename)}"
    path = REPORTS_DIR / stored
    path.write_bytes(data)
    return stored


def resolve_report_file(stored_name: str) -> Path | None:
    if not stored_name:
        return None
    path = (REPORTS_DIR / Path(stored_name).name).resolve()
    if REPORTS_DIR.resolve() not in path.parents and path.parent != REPORTS_DIR.resolve():
        return None
    return path if path.is_file() else None


def is_image_name(filename: str) -> bool:
    return Path(filename or "").suffix.lower() in IMAGE_SUFFIXES
