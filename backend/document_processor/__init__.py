"""HETU document extraction package."""

from document_processor.extractor import extract_clinical_document, prepare_document
from document_processor.schemas import ClinicalDocument

__all__ = ["ClinicalDocument", "extract_clinical_document", "prepare_document"]
