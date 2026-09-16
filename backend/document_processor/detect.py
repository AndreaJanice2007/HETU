"""Detect PDF, DOCX, JPEG, and PNG from magic bytes and filename."""

from __future__ import annotations

from pathlib import Path

from document_processor.errors import UnsupportedFileTypeError
from document_processor.schemas import FileKind

PDF_MAGIC = b"%PDF"
JPEG_MAGIC = b"\xff\xd8\xff"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
ZIP_MAGIC = b"PK\x03\x04"

ALLOWED_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
    ".png": "png",
}


def detect_file_kind(filename: str, data: bytes) -> FileKind:
    if not data:
        raise UnsupportedFileTypeError("Empty file")

    name = (filename or "upload").lower()
    ext = Path(name).suffix

    if data.startswith(PDF_MAGIC):
        return "pdf"
    if data.startswith(JPEG_MAGIC):
        return "jpeg"
    if data.startswith(PNG_MAGIC):
        return "png"
    if data.startswith(ZIP_MAGIC) and _looks_like_docx(data, ext):
        return "docx"

    mapped = ALLOWED_EXTENSIONS.get(ext)
    if mapped == "pdf" and data.startswith(PDF_MAGIC):
        return "pdf"
    if mapped in {"jpeg", "png", "docx", "pdf"}:
        # Extension claimed a supported type but magic did not match.
        raise UnsupportedFileTypeError(
            f"File extension {ext} does not match the file contents"
        )

    raise UnsupportedFileTypeError(
        "Unsupported file type. Upload PDF, DOCX, JPG/JPEG, or PNG."
    )


def _looks_like_docx(data: bytes, ext: str) -> bool:
    sample = data[: 64 * 1024]
    if b"word/" in sample or b"[Content_Types].xml" in sample:
        return True
    return ext == ".docx"
