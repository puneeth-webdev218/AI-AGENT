from pydantic import BaseModel, Field


class EmailConnectRequest(BaseModel):
    host: str
    port: int = 993
    username: str
    password: str
    folder: str = 'INBOX'
    use_ssl: bool = True
    subject_keywords: list[str] | None = None


class EmailItemResponse(BaseModel):
    email_id: str
    message_id: str
    subject: str | None = None
    sender: str | None = None
    date: str | None = None
    has_attachment: bool = False
    processed_flag: bool = False


class EmailConnectResponse(BaseModel):
    status: str
    email_count: int = 0
    emails: list[EmailItemResponse] = Field(default_factory=list)
    error: str | None = None


class EmailSyncResponse(BaseModel):
    job_id: str | None = None
    status: str = 'completed'
    fetched: int
    processed_documents: int
    skipped_duplicates: int
    errors: int
    matched_messages: int = 0
    fallback_used: bool = False
    message: str | None = None


class EmailJobStatusResponse(BaseModel):
    job_id: str
    status: str
    fetched: int = 0
    processed_documents: int = 0
    skipped_duplicates: int = 0
    errors: int = 0
    matched_messages: int = 0
    fallback_used: bool = False
    message: str | None = None


class EmailLogResponse(BaseModel):
    email_id: str | None = None
    message_id: str
    subject: str | None = None
    sender: str | None = None
    received_at: str | None = None
    status: str
    processed_flag: bool = False
    error_message: str | None = None


class EmailProcessRequest(BaseModel):
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None
    folder: str | None = None
    use_ssl: bool | None = None


class EmailProcessResponse(BaseModel):
    status: str
    message: str
    records_inserted: int = 0
    processed_documents: int = 0
    errors: int = 0
