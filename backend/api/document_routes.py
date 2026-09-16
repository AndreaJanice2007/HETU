"""POST /api/documents/extract — upload a document, return clinical JSON."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from document_processor.errors import DocumentProcessingError

router = APIRouter()


@router.post("/documents/extract")
async def extract_document(file: UploadFile = File(...)):
    from document_processor.extractor import extract_clinical_document

    filename = file.filename or "upload"
    data = await file.read()
    try:
        clinical, processing = extract_clinical_document(data, filename)
    except DocumentProcessingError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error": exc.code, "message": exc.detail},
        ) from exc
    return {
        "clinical": clinical.model_dump(),
        "processing": processing,
    }
