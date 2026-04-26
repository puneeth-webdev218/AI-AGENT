from pydantic import BaseModel


class ResultResponse(BaseModel):
    id: int
    document_id: int
    student_name: str | None = None
    usn: str | None = None
    subject: str | None = None
    subject_code: str | None = None
    subject_name: str | None = None
    grade: str | None = None
    grade_points: float | None = None
    sgpa: float | None = None
    validation_status: str
    validation_message: str | None = None
    raw_text: str | None = None
