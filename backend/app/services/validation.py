import re
from dataclasses import dataclass, field


USN_PATTERN = re.compile(r'^[A-Z0-9]{5,20}$')
SGPA_PATTERN = re.compile(r'^(?:[0-9](?:\.[0-9]{1,2})?|10(?:\.0{1,2})?)$')
GRADE_PATTERN = re.compile(r'^[A-F][+-]?$|^P$|^PP$|^AP$|^O$|^A$|^B$|^C$|^D$|^E$|^F$', re.IGNORECASE)


@dataclass
class ValidationResult:
    is_valid: bool
    status: str
    messages: list[str] = field(default_factory=list)


@dataclass
class ExtractedFields:
    student_name: str | None = None
    usn: str | None = None
    subject: str | None = None
    subject_code: str | None = None
    subject_name: str | None = None
    grade: str | None = None
    grade_points: float | None = None
    sgpa: float | None = None
    source_text: str | None = None


class ValidationError(Exception):
    pass


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = ' '.join(value.strip().split())
    return cleaned or None


def validate_extracted_fields(fields: ExtractedFields) -> ValidationResult:
    messages: list[str] = []
    core_errors: list[str] = []
    has_any = any([
        fields.student_name,
        fields.usn,
        fields.subject,
        fields.subject_code,
        fields.subject_name,
        fields.grade,
        fields.grade_points is not None,
        fields.sgpa is not None,
    ])
    if not has_any:
        return ValidationResult(is_valid=False, status='rejected', messages=['No extractable fields found in the document text.'])

    if fields.usn and not USN_PATTERN.match(fields.usn):
        core_errors.append(f'Invalid USN format: {fields.usn}')
    if fields.sgpa is not None and not (0.0 <= fields.sgpa <= 10.0):
        core_errors.append(f'Invalid SGPA range: {fields.sgpa}')
    if fields.grade and not GRADE_PATTERN.match(fields.grade):
        messages.append(f'Invalid grade format: {fields.grade}')
    if fields.grade_points is not None and fields.grade_points < 0:
        core_errors.append(f'Invalid grade points value: {fields.grade_points}')
    if fields.student_name and len(fields.student_name) < 2:
        core_errors.append('Student name is too short.')
    if fields.subject and len(fields.subject) < 2:
        messages.append('Subject is too short.')
    if fields.subject_code and len(fields.subject_code) < 2:
        messages.append('Subject code is too short.')
    if fields.subject_name and len(fields.subject_name) < 2:
        messages.append('Subject name is too short.')

    has_core_fields = bool(fields.student_name and fields.usn and (fields.sgpa is not None or fields.grade_points is not None or fields.subject or fields.subject_code or fields.subject_name))
    all_messages = core_errors + messages

    if core_errors:
        return ValidationResult(is_valid=False, status='partial', messages=all_messages)

    if has_core_fields:
        return ValidationResult(is_valid=True, status='validated', messages=all_messages)

    return ValidationResult(is_valid=False, status='partial', messages=all_messages or ['Partial record stored: core fields missing.'])


def is_row_acceptable(fields: ExtractedFields) -> bool:
    present_count = sum(
        [
            bool(fields.student_name),
            bool(fields.usn),
            bool(fields.subject),
            bool(fields.subject_code),
            bool(fields.subject_name),
            bool(fields.grade),
            fields.grade_points is not None,
            fields.sgpa is not None,
        ]
    )

    # Relaxed acceptance: either enough fields (>=3) or strong identity pair.
    if present_count >= 3:
        return True
    if fields.usn and (fields.student_name or fields.sgpa is not None or fields.grade_points is not None):
        return True
    return False
