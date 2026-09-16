"""Validate JPEG/PNG uploads and prepare them for a vision model."""

from __future__ import annotations

from io import BytesIO

from document_processor.errors import UnreadableImageError
from document_processor.schemas import FileKind, PreparedImage, ProcessedDocument

MAX_EDGE = 2048


def process_image(data: bytes, filename: str, kind: FileKind) -> ProcessedDocument:
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError as exc:
        raise UnreadableImageError("Pillow is not installed") from exc

    try:
        with Image.open(BytesIO(data)) as raw:
            raw.verify()
    except UnidentifiedImageError as exc:
        raise UnreadableImageError("Image could not be decoded (file may be corrupted)") from exc
    except Exception as exc:
        raise UnreadableImageError("Image could not be read (file may be corrupted)") from exc

    try:
        with Image.open(BytesIO(data)) as image:
            image.load()
            converted = image.convert("RGB")
            converted = _fit(converted)
            buffer = BytesIO()
            mime = "image/jpeg" if kind == "jpeg" else "image/png"
            if mime == "image/jpeg":
                converted.save(buffer, format="JPEG", quality=85)
            else:
                converted.save(buffer, format="PNG")
            payload = buffer.getvalue()
            width, height = converted.size
    except UnreadableImageError:
        raise
    except Exception as exc:
        raise UnreadableImageError("Image could not be processed (file may be unreadable)") from exc

    return ProcessedDocument(
        kind=kind,
        filename=filename,
        text="",
        images=[
            PreparedImage(
                filename=filename or f"upload.{'jpg' if kind == 'jpeg' else 'png'}",
                mime=mime,
                data=payload,
                reason="original_image",
            )
        ],
        page_count=1,
        notes=[f"Image prepared at {width}x{height} for vision extraction"],
    )


def _fit(image):
    width, height = image.size
    longest = max(width, height)
    if longest <= MAX_EDGE:
        return image
    scale = MAX_EDGE / float(longest)
    size = (max(1, int(width * scale)), max(1, int(height * scale)))
    resample = getattr(getattr(image, "Resampling", None), "LANCZOS", 1)
    return image.resize(size, resample)
