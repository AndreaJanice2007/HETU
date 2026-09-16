"""PDF text extraction, scanned-page detection, and page/image rendering."""

from __future__ import annotations

from document_processor.errors import CorruptedPdfError
from document_processor.schemas import PreparedImage, ProcessedDocument

SCANNED_TEXT_THRESHOLD = 40
MAX_PAGES = 8
MAX_IMAGES = 8
RENDER_SCALE = 1.5


def process_pdf(data: bytes, filename: str) -> ProcessedDocument:
    try:
        import pymupdf
    except ImportError as exc:
        raise CorruptedPdfError("PyMuPDF is not installed") from exc

    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise CorruptedPdfError("PDF could not be opened (file may be corrupted)") from exc

    if doc.is_encrypted:
        doc.close()
        raise CorruptedPdfError("Encrypted PDFs are not supported")

    try:
        return _extract(doc, filename)
    except CorruptedPdfError:
        raise
    except Exception as exc:
        raise CorruptedPdfError("PDF could not be processed (file may be corrupted)") from exc
    finally:
        doc.close()


def _extract(doc, filename: str) -> ProcessedDocument:
    page_count = doc.page_count
    if page_count < 1:
        raise CorruptedPdfError("PDF has no pages")

    text_parts: list[str] = []
    images: list[PreparedImage] = []
    notes: list[str] = []
    pages_to_read = min(page_count, MAX_PAGES)
    if page_count > MAX_PAGES:
        notes.append(f"Only the first {MAX_PAGES} of {page_count} pages were processed")

    for index in range(pages_to_read):
        page = doc.load_page(index)
        page_text = (page.get_text("text") or "").strip()
        has_images = bool(page.get_images(full=True))
        has_tables = _page_has_tables(page)
        scanned = len(page_text) < SCANNED_TEXT_THRESHOLD

        header = f"--- page {index + 1} ---"
        text_parts.append(header)
        if page_text:
            text_parts.append(page_text)
        else:
            text_parts.append("[no extractable text on this page]")

        needs_visual = scanned or has_images or has_tables
        if needs_visual and len(images) < MAX_IMAGES:
            reason = "scanned_page" if scanned else "page_with_images_or_tables"
            images.append(_render_page(page, index + 1, reason))
            notes.append(f"Page {index + 1} sent as an image ({reason})")

    return ProcessedDocument(
        kind="pdf",
        filename=filename,
        text="\n".join(text_parts).strip(),
        images=images,
        page_count=page_count,
        notes=notes,
    )


def _page_has_tables(page) -> bool:
    finder = getattr(page, "find_tables", None)
    if not callable(finder):
        return False
    try:
        found = finder()
        tables = getattr(found, "tables", found)
        return bool(tables)
    except Exception:
        return False


def _render_page(page, page_number: int, reason: str) -> PreparedImage:
    import pymupdf

    pix = page.get_pixmap(matrix=pymupdf.Matrix(RENDER_SCALE, RENDER_SCALE), alpha=False)
    return PreparedImage(
        filename=f"page-{page_number}.png",
        mime="image/png",
        data=pix.tobytes("png"),
        reason=reason,
    )
