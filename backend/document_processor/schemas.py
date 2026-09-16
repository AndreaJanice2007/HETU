"""Normalized clinical JSON for HETU document extraction.

This schema is for ingestion only. It does not include HETU root-cause
labels (doctor_gap, patient_gap, no_fault, intentional_non_disclosure).
Contradiction reasoning lives in the contradiction engine, not here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FileKind = Literal["pdf", "docx", "jpeg", "png"]


class DocumentMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_type: str = ""
    source: str = ""
    date: str = ""


class PatientInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = ""
    age: int | None = None
    sex: str = ""


class ClinicalDocument(BaseModel):
    """Structured clinical extract returned by the OpenAI multimodal model."""

    model_config = ConfigDict(extra="forbid")

    document_metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    patient: PatientInfo = Field(default_factory=PatientInfo)
    clinical_findings: list[str] = Field(default_factory=list)
    diagnoses: list[str] = Field(default_factory=list)
    symptoms: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    lab_results: list[str] = Field(default_factory=list)
    procedures: list[str] = Field(default_factory=list)
    doctor_notes: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)


@dataclass
class PreparedImage:
    filename: str
    mime: str
    data: bytes
    reason: str


@dataclass
class ProcessedDocument:
    kind: FileKind
    filename: str
    text: str
    images: list[PreparedImage] = field(default_factory=list)
    page_count: int = 0
    notes: list[str] = field(default_factory=list)
