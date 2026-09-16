"""Document ingestion → OpenAI multimodal structured clinical JSON.

Keeps extraction separate from HETU contradiction / root-cause classification.
Does not fine-tune a model. Does not hard-code API keys.
"""

from __future__ import annotations

import base64

from openai import APIError, APIStatusError

from document_processor.detect import detect_file_kind
from document_processor.docx_processor import process_docx
from document_processor.errors import (
    ExtractionFailureError,
    OpenAIRequestError,
    UnsupportedFileTypeError,
)
from document_processor.image_processor import process_image
from document_processor.openai_client import get_client, vision_model
from document_processor.pdf_processor import process_pdf
from document_processor.schemas import ClinicalDocument, ProcessedDocument

MAX_UPLOAD_BYTES = 12 * 1024 * 1024

EXTRACT_INSTRUCTIONS = """You are HETU's document extraction component.

Extract clinically relevant information from the supplied medical document text and/or images.
Return only the structured clinical schema. Use empty strings, empty lists, or null when unknown.
Do not invent facts that are not supported by the document.
Put ambiguities, illegible text, and missing fields in uncertainties.
This is a prototype extractor. Do not make definitive diagnoses.
Do not classify HETU root causes (doctor_gap, patient_gap, no_fault, intentional_non_disclosure).
Those labels belong to a later contradiction engine, not this extraction step.
"""


def prepare_document(data: bytes, filename: str) -> ProcessedDocument:
    if data is None or len(data) == 0:
        raise UnsupportedFileTypeError("Empty file")
    if len(data) > MAX_UPLOAD_BYTES:
        raise UnsupportedFileTypeError("File exceeds the 12 MB upload limit")

    kind = detect_file_kind(filename, data)
    if kind == "pdf":
        return process_pdf(data, filename)
    if kind == "docx":
        return process_docx(data, filename)
    if kind in {"jpeg", "png"}:
        return process_image(data, filename, kind)
    raise UnsupportedFileTypeError("Unsupported file type")


def extract_clinical_document(data: bytes, filename: str) -> tuple[ClinicalDocument, dict]:
    """Run local processing, then OpenAI structured extraction.

    Returns (clinical_json, processing_metadata). Does not call the contradiction engine.
    """
    processed = prepare_document(data, filename)
    clinical = call_openai_extractor(processed)
    meta = {
        "filename": processed.filename,
        "detected_type": processed.kind,
        "page_count": processed.page_count,
        "text_chars": len(processed.text or ""),
        "images_sent_to_model": len(processed.images),
        "processing_notes": processed.notes,
        "model": vision_model(),
        "contradiction_engine": "not_invoked",
    }
    return clinical, meta


def call_openai_extractor(processed: ProcessedDocument) -> ClinicalDocument:
    client = get_client()
    model = vision_model()
    content: list[dict] = [{"type": "input_text", "text": _user_prompt(processed)}]
    for image in processed.images:
        b64 = base64.standard_b64encode(image.data).decode("ascii")
        content.append(
            {
                "type": "input_image",
                "image_url": f"data:{image.mime};base64,{b64}",
                "detail": "auto",
            }
        )

    try:
        response = client.responses.parse(
            model=model,
            instructions=EXTRACT_INSTRUCTIONS,
            input=[{"role": "user", "content": content}],
            text_format=ClinicalDocument,
        )
    except APIStatusError as exc:
        raise OpenAIRequestError(f"OpenAI API request failed ({exc.status_code})") from exc
    except APIError as exc:
        raise OpenAIRequestError("OpenAI API request failed") from exc
    except OpenAIRequestError:
        raise
    except Exception as exc:
        raise OpenAIRequestError("OpenAI API request failed") from exc

    parsed = getattr(response, "output_parsed", None)
    if parsed is None:
        raise ExtractionFailureError("Model did not return structured clinical JSON")
    if not isinstance(parsed, ClinicalDocument):
        try:
            parsed = ClinicalDocument.model_validate(parsed)
        except Exception as exc:
            raise ExtractionFailureError("Model output did not match the clinical schema") from exc
    return parsed


def _user_prompt(processed: ProcessedDocument) -> str:
    text = processed.text.strip() if processed.text else ""
    image_notes = ", ".join(
        f"{image.filename} ({image.reason})" for image in processed.images
    ) or "none"
    parts = [
        f"Filename: {processed.filename}",
        f"Detected type: {processed.kind}",
        f"Visual attachments: {image_notes}",
    ]
    if text:
        parts.append("Extracted text:")
        parts.append(text)
    else:
        parts.append("No text layer was extracted. Use the attached image(s).")
    parts.append("Fill the clinical JSON schema from this document.")
    return "\n".join(parts)
