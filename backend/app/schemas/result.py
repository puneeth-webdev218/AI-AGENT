from pydantic import BaseModel


class ResultResponse(BaseModel):
    id: int
    document_id: int
    student_name: str | None = None
    usn: str | None = None
    subject: str | None = None
    grade: str | None = None
    sgpa: float | None = None
    validation_status: str
    validation_message: str | None = None
    raw_text: str | None = None
