"""Document ingestion errors. Routes map these to HTTP responses."""


class DocumentProcessingError(Exception):
    status_code = 400
    code = "extraction_failure"

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class UnsupportedFileTypeError(DocumentProcessingError):
    status_code = 415
    code = "unsupported_file_type"


class CorruptedPdfError(DocumentProcessingError):
    status_code = 400
    code = "corrupted_pdf"


class CorruptedDocxError(DocumentProcessingError):
    status_code = 400
    code = "corrupted_docx"


class UnreadableImageError(DocumentProcessingError):
    status_code = 400
    code = "unreadable_image"


class OpenAIRequestError(DocumentProcessingError):
    status_code = 502
    code = "api_failure"


class ExtractionFailureError(DocumentProcessingError):
    status_code = 422
    code = "extraction_failure"
