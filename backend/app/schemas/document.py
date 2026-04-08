from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    id: int
    filename: str
    original_name: str
    content_type: str | None
    file_type: str
    status: str
    is_latest: bool = False
    error_message: str | None = None
    extracted_text_preview: str | None = None


class UploadResponse(BaseModel):
    message: str
    document: DocumentResponse


class ProcessingResponse(BaseModel):
    document_id: int
    status: str
    message: str | None = None


class LatestDocumentResponse(BaseModel):
    document_id: int
    file_name: str
    uploaded_at: str
    record_count: int
