from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.student import Student


def upsert_student(session: Session, usn: str | None, name: str | None) -> Student | None:
    if not usn:
        return None

    student = session.scalar(select(Student).where(Student.usn == usn))
    if student is None:
        student = Student(usn=usn, name=name)
        session.add(student)
        session.flush()
        return student

    if name and should_replace_name(student.name, name):
        student.name = name
    return student


def should_replace_name(current_name: str | None, new_name: str) -> bool:
    if not current_name:
        return True
    if is_noisy_name(current_name) and not is_noisy_name(new_name):
        return True
    return False


def is_noisy_name(value: str) -> bool:
    lowered = value.lower()
    if len(lowered) > 60:
        return True
    noisy_tokens = ['name usn', 'subject grade', 'sgpa', '[page']
    return any(token in lowered for token in noisy_tokens)