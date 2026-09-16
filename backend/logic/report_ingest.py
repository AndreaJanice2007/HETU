"""Turn typed text or an uploaded/scanned file into report notes."""

from __future__ import annotations

from pathlib import Path

MAX_UPLOAD_BYTES = 12 * 1024 * 1024
MAX_NOTES_CHARS = 8000

TEXT_SUFFIXES = {
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".xml",
    ".html",
    ".htm",
    ".rtf",
    ".log",
    ".text",
}


def clip_notes(text: str) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= MAX_NOTES_CHARS:
        return cleaned
    return cleaned[: MAX_NOTES_CHARS - 1].rstrip() + "…"


def ingest_report_file(data: bytes | None, filename: str) -> str:
    """Extract a short text note from any file, then the caller must discard `data`."""
    name = (filename or "upload").strip() or "upload"
    if not data:
        return f"Empty file received ({name})."
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("File exceeds the 12 MB limit")

    suffix = Path(name).suffix.lower()

    if suffix == ".pdf" or data.startswith(b"%PDF"):
        extracted = _pdf_text(data, name)
        if extracted:
            return clip_notes(extracted)

    if suffix == ".docx" or (data[:4] == b"PK\x03\x04" and suffix == ".docx"):
        extracted = _docx_text(data, name)
        if extracted:
            return clip_notes(extracted)

    if suffix in TEXT_SUFFIXES or _looks_like_text(data):
        decoded = _decode_text(data)
        if decoded:
            return clip_notes(decoded)

    kind = "scanned page" if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".tif", ".tiff", ".heic"} else "file"
    return f"{kind.capitalize()} received ({name})."


def _looks_like_text(data: bytes) -> bool:
    sample = data[:2048]
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return ""


def _pdf_text(data: bytes, filename: str) -> str:
    try:
        from document_processor.pdf_processor import process_pdf

        processed = process_pdf(data, filename)
        return (processed.text or "").strip()
    except Exception:
        return ""


def _docx_text(data: bytes, filename: str) -> str:
    try:
        from document_processor.docx_processor import process_docx

        processed = process_docx(data, filename)
        return (processed.text or "").strip()
    except Exception:
        return ""
