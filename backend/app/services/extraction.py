import json
import os
import re
from dataclasses import dataclass
from typing import Iterable

import pandas as pd
from openai import OpenAI

from app.services.validation import ExtractedFields, is_row_acceptable, normalize_text


FIELD_LABELS = {
    'student_name': ('student name', 'candidate name', 'name of student'),
    'usn': ('usn', 'university seat number', 'seat no', 'registration number', 'register number'),
    'subject': ('subject', 'paper', 'course', 'module'),
    'grade': ('grade', 'result'),
    'sgpa': ('sgpa',),
}

SGPA_REGEX = re.compile(r'(?<!\d)(10(?:\.0{1,2})?|\d(?:\.\d{1,2})?)(?!\d)')
USN_REGEX = re.compile(r'\b[A-Z0-9]{5,20}\b')
TABLE_ROW_REGEX = re.compile(
    r'(?P<name>[A-Za-z][A-Za-z0-9_\-\. ]{1,80}?)\s+'
    r'(?P<usn>[A-Za-z0-9]{5,20})\s+'
    r'(?P<subject>[A-Za-z][A-Za-z&/\-\. ]{1,80}?)\s+'
    r'(?P<grade>A\+|A|B\+|B|C\+|C|D|E|F|P|PP|AP|O)\s+'
    r'(?P<sgpa>10(?:\.0{1,2})?|\d(?:\.\d{1,2})?)',
    re.IGNORECASE,
)

ROW_PATTERNS = [
    re.compile(
        r'(?P<name>[A-Za-z][A-Za-z0-9_\-\. ]{1,80}?)\s+'
        r'(?P<usn>[A-Za-z0-9]{5,20})\s+'
        r'(?P<subject>[A-Za-z][A-Za-z&/\-\. ]{1,80}?)\s+'
        r'(?P<grade>A\+|A|B\+|B|C\+|C|D|E|F|P|PP|AP|O)\s+'
        r'(?P<sgpa>10(?:\.0{1,2})?|\d(?:\.\d{1,2})?)',
        re.IGNORECASE,
    ),
    re.compile(
        r'(?P<usn>[A-Za-z0-9]{5,20})\s*[-|:]\s*'
        r'(?P<name>[A-Za-z][A-Za-z0-9_\-\. ]{1,80}?)\s*[-|:]\s*'
        r'(?P<subject>[A-Za-z][A-Za-z&/\-\. ]{1,80}?)\s*[-|:]\s*'
        r'(?P<grade>A\+|A|B\+|B|C\+|C|D|E|F|P|PP|AP|O)\s*[-|:]\s*'
        r'(?P<sgpa>10(?:\.0{1,2})?|\d(?:\.\d{1,2})?)',
        re.IGNORECASE,
    ),
]

EXCEL_COLUMN_ALIASES = {
    'student_name': ('name', 'student name', 'candidate', 'candidate name', 'name of student'),
    'usn': ('usn', 'id', 'student id', 'roll no', 'roll number', 'seat no', 'seat number', 'registration number', 'register number'),
    'subject': ('subject', 'paper', 'course', 'module'),
    'grade': ('grade', 'result'),
    'sgpa': ('sgpa', 'gpa', 'cgpa', 's g p a', 'semester grade point average'),
}

GRADE_TOKENS = {'A+', 'A', 'B+', 'B', 'C+', 'C', 'D', 'E', 'F', 'P', 'PP', 'AP', 'O'}


@dataclass
class ExcelProcessingStats:
    total_rows: int = 0
    inserted_candidates: int = 0
    failed_rows: int = 0
    skipped_rows: int = 0


@dataclass
class ComplexSubjectBlock:
    start_col: int
    grade_col: int
    grade_points_col: int
    subject_code: str | None = None
    subject_name: str | None = None


def extract_from_text(text: str) -> ExtractedFields:
    lines = [normalize_text(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        normalized = normalize_text(text)
        lines = [normalized] if normalized else []
    extracted = ExtractedFields(source_text=text)

    extracted.student_name = extract_label_value(lines, FIELD_LABELS['student_name'])
    extracted.usn = extract_label_value(lines, FIELD_LABELS['usn'])
    extracted.subject = extract_label_value(lines, FIELD_LABELS['subject'])
    extracted.grade = extract_label_value(lines, FIELD_LABELS['grade'])
    extracted.sgpa = extract_sgpa(lines)

    row_candidate = extract_from_table_row(lines)
    if row_candidate:
        # Prefer structured row extraction over noisy generic label parsing.
        extracted.student_name = row_candidate.student_name or extracted.student_name
        extracted.usn = row_candidate.usn or extracted.usn
        extracted.subject = row_candidate.subject or extracted.subject
        extracted.grade = row_candidate.grade or extracted.grade
        extracted.sgpa = row_candidate.sgpa if row_candidate.sgpa is not None else extracted.sgpa

    if extracted.usn is None:
        extracted.usn = extract_usn_from_text(lines)
    if extracted.usn:
        extracted.usn = extracted.usn.upper()
    extracted.student_name = clean_candidate_text(extracted.student_name)
    extracted.subject = clean_candidate_text(extracted.subject)
    extracted.grade = clean_candidate_text(extracted.grade)
    return extracted


def extract_rows_from_text(text: str) -> list[ExtractedFields]:
    lines = [normalize_text(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    extracted_rows: list[ExtractedFields] = []
    for line in lines:
        parsed = parse_row_line(line)
        if parsed is None:
            continue
        extracted_rows.append(parsed)

    if not extracted_rows:
        extracted_rows.extend(extract_rows_from_text_fallback(lines))

    deduped = dedupe_rows(extracted_rows)
    print('Detected text rows:', len(lines))
    print('Mapped fields from text rows:', len(deduped))
    print('FINAL EXTRACTED DATA:', [row.__dict__ for row in deduped])
    return deduped


def extract_from_excel(file_path: str) -> tuple[str, ExtractedFields]:
    extracted_rows, text_rows = parse_excel_workbook(file_path)
    extracted = extracted_rows[0] if extracted_rows else ExtractedFields()
    joined_text = '\n'.join(text_rows)
    if extracted.usn is None:
        extracted.usn = extract_usn_from_text(text_rows)
    if extracted.sgpa is None:
        extracted.sgpa = extract_sgpa(text_rows)
    return joined_text, extracted


def extract_rows_from_excel(file_path: str) -> list[ExtractedFields]:
    rows, _ = parse_excel_workbook(file_path)
    return rows


def parse_excel_workbook(file_path: str) -> tuple[list[ExtractedFields], list[str]]:
    raw_sheets = pd.read_excel(file_path, sheet_name=None, header=None, dtype=object)
    default_sheets = pd.read_excel(file_path, sheet_name=None)

    rows: list[ExtractedFields] = []
    text_rows: list[str] = []
    stats = ExcelProcessingStats()
    detected_formats: list[str] = []

    for sheet_name, raw_frame in raw_sheets.items():
        format_name = detect_excel_format(raw_frame)
        detected_formats.append(format_name)
        print(f'Detected format ({sheet_name}): {format_name}')

        if format_name == 'complex':
            sheet_rows, sheet_text_rows = parse_complex_excel_sheet(raw_frame, sheet_name)
        else:
            frame = default_sheets.get(sheet_name)
            sheet_rows, sheet_text_rows = parse_simple_excel_sheet(frame, sheet_name, stats)

        rows.extend(sheet_rows)
        text_rows.extend(sheet_text_rows)

    deduped = dedupe_rows(rows)
    total_students = len({(row.usn or '').upper() for row in deduped if row.usn})
    total_subjects = len(deduped)
    print('Detected workbook formats:', detected_formats)
    print('Total students processed:', total_students)
    print('Total subjects extracted:', total_subjects)
    print('Total DB inserts:', len(deduped))
    print('FINAL EXTRACTED DATA:', [row.__dict__ for row in deduped])
    return deduped, text_rows


def detect_excel_format(raw_frame: pd.DataFrame) -> str:
    if raw_frame is None or raw_frame.empty:
        return 'simple'
    data_start_row = find_complex_data_start_row(raw_frame)
    if data_start_row is None or data_start_row < 2:
        return 'simple'
    header_rows = raw_frame.iloc[:data_start_row]
    subject_blocks = detect_complex_subject_blocks(header_rows)
    return 'complex' if subject_blocks else 'simple'


def parse_simple_excel_sheet(frame: pd.DataFrame | None, sheet_name: str, stats: ExcelProcessingStats) -> tuple[list[ExtractedFields], list[str]]:
    if frame is None or frame.empty:
        return [], []

    normalized_frame = sanitize_excel_frame(frame)
    if normalized_frame.empty:
        return [], []

    column_map = map_excel_columns(normalized_frame.columns)
    if not column_map['name'] or not column_map['usn'] or not column_map['sgpa']:
        ai_map = infer_columns_with_llm(normalized_frame, sheet_name)
        for key in ('name', 'usn', 'subject', 'grade', 'sgpa'):
            if not column_map[key] and ai_map.get(key):
                column_map[key] = ai_map[key]

    print(f'Detected columns ({sheet_name}): {list(normalized_frame.columns)}')
    print(f'Mapped fields ({sheet_name}): {column_map}')

    if not column_map['name'] or not column_map['usn'] or not column_map['sgpa']:
        stats.skipped_rows += len(normalized_frame.index)
        return [], []

    normalized_frame[column_map['sgpa']] = pd.to_numeric(normalized_frame[column_map['sgpa']], errors='coerce')

    rows: list[ExtractedFields] = []
    text_rows: list[str] = []
    chunk_size = 1000

    for start in range(0, len(normalized_frame.index), chunk_size):
        chunk = normalized_frame.iloc[start:start + chunk_size]
        for _, row in chunk.iterrows():
            stats.total_rows += 1
            try:
                candidate = ExtractedFields(
                    student_name=clean_candidate_text(read_excel_cell(row, column_map['name'])),
                    usn=read_excel_cell(row, column_map['usn']).upper() or None,
                    subject=clean_candidate_text(read_excel_cell(row, column_map['subject'])) if column_map['subject'] else None,
                    grade=clean_candidate_text(read_excel_cell(row, column_map['grade'])) if column_map['grade'] else None,
                    sgpa=safe_float(row[column_map['sgpa']]) if column_map['sgpa'] else None,
                )

                if not candidate.student_name and not candidate.usn and candidate.sgpa is None:
                    stats.skipped_rows += 1
                    continue
                if candidate.usn and not is_likely_usn(candidate.usn):
                    stats.failed_rows += 1
                    continue
                if not is_row_acceptable(candidate):
                    stats.failed_rows += 1
                    continue

                rows.append(candidate)
                text_rows.append(f'[{sheet_name}] {candidate.student_name or ""} | {candidate.usn or ""} | {candidate.subject or ""} | {candidate.grade or ""} | {candidate.sgpa if candidate.sgpa is not None else ""}')
                stats.inserted_candidates += 1
            except Exception:
                stats.failed_rows += 1
                continue

    deduped = dedupe_rows(rows)
    stats.inserted_candidates = len(deduped)
    print('Total rows:', stats.total_rows)
    print('Inserted:', stats.inserted_candidates)
    print('Failed:', stats.failed_rows)
    print('Skipped:', stats.skipped_rows)
    return deduped, text_rows


def parse_complex_excel_sheet(raw_frame: pd.DataFrame, sheet_name: str) -> tuple[list[ExtractedFields], list[str]]:
    data_start_row = find_complex_data_start_row(raw_frame)
    if data_start_row is None:
        return [], []

    header_rows = raw_frame.iloc[:data_start_row]
    subject_blocks = detect_complex_subject_blocks(header_rows)
    if not subject_blocks:
        return [], []

    rows: list[ExtractedFields] = []
    text_rows: list[str] = []
    total_rows = 0

    print(f'Complex Excel header rows ({sheet_name}): {data_start_row}')
    print(f'Complex subject blocks ({sheet_name}): {[block.__dict__ for block in subject_blocks]}')

    for row_index in range(data_start_row, len(raw_frame.index)):
        row = raw_frame.iloc[row_index]
        try:
            total_rows += 1
            student_name = clean_candidate_text(excel_cell_text(row, 2))
            usn = excel_cell_text(row, 1).upper() or None
            if usn and not is_likely_usn(usn):
                continue
            if not usn and not student_name:
                continue

            for block in subject_blocks:
                grade = clean_candidate_text(excel_cell_text(row, block.grade_col))
                grade_points = safe_float(row.iloc[block.grade_points_col]) if block.grade_points_col < len(row) else None

                if grade is None and grade_points is None:
                    continue

                subject_name = clean_candidate_text(block.subject_name)
                subject_code = clean_candidate_text(block.subject_code)
                candidate = ExtractedFields(
                    student_name=student_name,
                    usn=usn,
                    subject=subject_name or subject_code,
                    subject_code=subject_code,
                    subject_name=subject_name,
                    grade=grade,
                    grade_points=grade_points,
                )

                if not is_row_acceptable(candidate):
                    continue

                rows.append(candidate)
                text_rows.append(
                    f'[{sheet_name}] {student_name or ""} | {usn or ""} | {subject_code or ""} | {subject_name or ""} | {grade or ""} | {"" if grade_points is None else grade_points}'
                )
        except Exception as exc:
            print(f'Complex Excel row skipped ({sheet_name} row {row_index + 1}): {exc}')
            continue

    deduped = dedupe_rows(rows)
    print(f'Complex Excel rows ({sheet_name}): {total_rows}')
    print(f'Complex Excel extracted rows ({sheet_name}): {len(deduped)}')
    return deduped, text_rows


def find_complex_data_start_row(raw_frame: pd.DataFrame) -> int | None:
    for row_index in range(len(raw_frame.index)):
        usn_value = excel_cell_text(raw_frame.iloc[row_index], 1)
        name_value = excel_cell_text(raw_frame.iloc[row_index], 2)
        if usn_value and is_likely_usn(usn_value) and name_value:
            return row_index
    return None


def detect_complex_subject_blocks(header_rows: pd.DataFrame) -> list[ComplexSubjectBlock]:
    if header_rows.empty:
        return []

    bottom_row = header_rows.iloc[-1]
    blocks: list[ComplexSubjectBlock] = []
    column_count = len(bottom_row.index)

    for column_index in range(3, column_count - 1):
        grade_label = normalize_text(excel_cell_text(bottom_row, column_index))
        points_label = normalize_text(excel_cell_text(bottom_row, column_index + 1))
        if not grade_label or not points_label:
            continue
        if grade_label.upper() not in {'GR', 'GRADE'}:
            continue
        if points_label.upper() not in {'GP', 'GRADE POINTS', 'POINTS'}:
            continue

        subject_code, subject_name = infer_subject_metadata(header_rows, column_index, column_index + 1)
        blocks.append(
            ComplexSubjectBlock(
                start_col=column_index,
                grade_col=column_index,
                grade_points_col=column_index + 1,
                subject_code=subject_code,
                subject_name=subject_name,
            )
        )

    return blocks


def infer_subject_metadata(header_rows: pd.DataFrame, left_col: int, right_col: int) -> tuple[str | None, str | None]:
    candidates: list[str] = []
    for row_index in range(len(header_rows.index)):
        for column_index in (left_col, right_col):
            if column_index >= len(header_rows.columns):
                continue
            value = clean_candidate_text(excel_cell_text(header_rows.iloc[row_index], column_index))
            if not value:
                continue
            lowered = value.lower()
            if lowered in {'gr', 'gp'}:
                continue
            if re.fullmatch(r'\d+(?::\d+)+', value):
                continue
            if value not in candidates:
                candidates.append(value)

    subject_code = None
    subject_name = None
    for value in candidates:
        if is_subject_code_candidate(value):
            subject_code = value
            break

    if subject_code:
        for value in candidates:
            if value == subject_code:
                continue
            if not is_subject_code_candidate(value):
                subject_name = value
                break
    elif candidates:
        subject_name = candidates[0]

    return subject_code, subject_name


def is_subject_code_candidate(value: str) -> bool:
    normalized = value.strip().upper()
    if len(normalized) < 3 or len(normalized) > 12:
        return False
    return bool(re.fullmatch(r'[A-Z]{1,6}\d+[A-Z0-9()\-/]*', normalized))


def excel_cell_text(row: pd.Series, column_index: int) -> str:
    if column_index >= len(row.index):
        return ''
    value = row.iloc[column_index]
    if pd.isna(value):
        return ''
    return str(value).strip()


def infer_columns_with_llm(frame: pd.DataFrame, sheet_name: str) -> dict[str, str]:
    api_key = os.getenv('GROQ_API_KEY', '').strip()
    if not api_key:
        return {}

    try:
        sample_rows = frame.head(5).to_dict(orient='records')
        columns = [str(column).strip().lower() for column in frame.columns]
        prompt = (
            'Identify best column mapping from this sheet.\n'
            'Return JSON only with keys: name, usn, subject, grade, sgpa.\n'
            'Use exact column names from provided columns list or null.\n\n'
            f'Sheet: {sheet_name}\n'
            f'Columns: {columns}\n'
            f'Sample rows: {sample_rows}'
        )
        client = OpenAI(api_key=api_key, base_url='https://api.groq.com/openai/v1')
        model = resolve_model_name(os.getenv('GROQ_MODEL', 'qwen-32b'))
        response = client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': 'You map tabular academic columns. Return strict JSON only.'},
                {'role': 'user', 'content': prompt},
            ],
            temperature=0,
        )
        raw = (response.choices[0].message.content or '').strip() if response.choices else ''
        parsed = parse_json_object(raw)
        if not isinstance(parsed, dict):
            return {}

        normalized_columns = {str(column).strip().lower() for column in frame.columns}
        mapped: dict[str, str] = {}
        for key in ('name', 'usn', 'subject', 'grade', 'sgpa'):
            value = parsed.get(key)
            if not value:
                continue
            candidate = str(value).strip().lower()
            if candidate in normalized_columns:
                mapped[key] = candidate
        print(f'AI column mapping ({sheet_name}): {mapped}')
        return mapped
    except Exception as exc:
        print(f'AI column mapping failed ({sheet_name}): {exc}')
        return {}


def parse_json_object(content: str) -> dict | None:
    if not content:
        return None
    cleaned = content.strip()
    if cleaned.startswith('```'):
        cleaned = re.sub(r'^```[a-zA-Z]*\n?', '', cleaned)
        cleaned = re.sub(r'\n?```$', '', cleaned).strip()
    start = cleaned.find('{')
    end = cleaned.rfind('}')
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(cleaned[start:end + 1])
    except Exception:
        return None


def resolve_model_name(model_name: str) -> str:
    if model_name.strip().lower() == 'qwen-32b':
        return 'qwen/qwen3-32b'
    return model_name


def extract_rows_from_text_fallback(lines: Iterable[str]) -> list[ExtractedFields]:
    fallback_rows: list[ExtractedFields] = []
    for line in lines:
        row = parse_text_line_relaxed(line)
        if row is None:
            continue
        if not is_row_acceptable(row):
            continue
        fallback_rows.append(row)
    return fallback_rows


def parse_text_line_relaxed(line: str) -> ExtractedFields | None:
    usn = extract_usn_from_text([line])
    sgpa = safe_float(extract_last_numeric_token(line))
    grade = extract_grade_token(line)

    name: str | None = None
    subject: str | None = None
    if usn:
        parts = re.split(re.escape(usn), line, maxsplit=1, flags=re.IGNORECASE)
        left = clean_candidate_text(parts[0]) if parts else None
        right = parts[1] if len(parts) > 1 else ''
        right_clean = normalize_text(re.sub(r'\b(?:10(?:\.0{1,2})?|\d(?:\.\d{1,2})?)\b', '', right)) or ''
        right_clean = normalize_text(re.sub(r'\b(?:A\+|A|B\+|B|C\+|C|D|E|F|P|PP|AP|O)\b', '', right_clean, flags=re.IGNORECASE))
        name = left
        subject = clean_candidate_text(right_clean)

    candidate = ExtractedFields(
        student_name=name,
        usn=usn.upper() if usn else None,
        subject=subject,
        grade=grade,
        sgpa=sgpa,
    )
    if not any([candidate.student_name, candidate.usn, candidate.subject, candidate.grade, candidate.sgpa is not None]):
        return None
    if candidate.student_name and is_header_like_name(candidate.student_name):
        return None
    return candidate


def extract_last_numeric_token(line: str) -> str | None:
    matches = SGPA_REGEX.findall(line)
    if not matches:
        return None
    return matches[-1]


def extract_grade_token(line: str) -> str | None:
    tokens = re.findall(r'[A-Za-z+]+', line.upper())
    for token in tokens:
        if token in GRADE_TOKENS:
            return token
    return None


def sanitize_excel_frame(frame: pd.DataFrame) -> pd.DataFrame:
    cleaned = frame.copy()
    cleaned.columns = cleaned.columns.astype(str).str.strip().str.lower()
    cleaned = cleaned.dropna(how='all')
    cleaned = cleaned.fillna('')
    return cleaned


def map_excel_columns(columns: pd.Index) -> dict[str, str | None]:
    normalized_columns = [str(column).strip().lower() for column in columns]
    used: set[str] = set()

    name_col = find_column(normalized_columns, EXCEL_COLUMN_ALIASES['student_name'], used)
    if name_col:
        used.add(name_col)

    usn_col = find_column(normalized_columns, EXCEL_COLUMN_ALIASES['usn'], used)
    if usn_col:
        used.add(usn_col)

    subject_col = find_column(normalized_columns, EXCEL_COLUMN_ALIASES['subject'], used)
    if subject_col:
        used.add(subject_col)

    grade_col = find_column(normalized_columns, EXCEL_COLUMN_ALIASES['grade'], used)
    if grade_col:
        used.add(grade_col)

    sgpa_col = find_column(normalized_columns, EXCEL_COLUMN_ALIASES['sgpa'], used)

    return {
        'name': name_col,
        'usn': usn_col,
        'subject': subject_col,
        'grade': grade_col,
        'sgpa': sgpa_col,
    }


def find_column(columns: list[str], aliases: tuple[str, ...], used: set[str] | None = None) -> str | None:
    used = used or set()
    best_col: str | None = None
    best_score = -1

    for column in columns:
        if column in used:
            continue
        score = column_match_score(column, aliases)
        if score > best_score:
            best_score = score
            best_col = column

    if best_score <= 0:
        return None
    return best_col


def column_match_score(column: str, aliases: tuple[str, ...]) -> int:
    column_norm = column.strip().lower()
    column_tokens = tokenize(column_norm)
    best = 0

    for alias in aliases:
        alias_norm = alias.strip().lower()
        alias_tokens = tokenize(alias_norm)
        if not alias_tokens:
            continue

        if alias_norm == column_norm:
            best = max(best, 100)
            continue

        # For very short aliases like "id", only accept token-level exact matches.
        if len(alias_norm) <= 3:
            if alias_norm in column_tokens:
                best = max(best, 80)
            continue

        # Multi-token aliases match when all alias tokens are present.
        if all(token in column_tokens for token in alias_tokens):
            best = max(best, 70 + len(alias_tokens))
            continue

        # Fallback partial token overlap for messy headers.
        overlap = len(set(alias_tokens).intersection(column_tokens))
        if overlap > 0:
            best = max(best, 40 + overlap)

    return best


def tokenize(value: str) -> list[str]:
    return [token for token in re.split(r'[^a-z0-9]+', value.lower()) if token]


def read_excel_cell(row: pd.Series, column: str | None) -> str:
    if not column:
        return ''
    value = row[column]
    if pd.isna(value):
        return ''
    return str(value).strip()


def extract_label_value(lines: Iterable[str], labels: tuple[str, ...]) -> str | None:
    for line in lines:
        lowered = line.lower()
        for label in labels:
            if label in lowered:
                value = split_label_value(line, label)
                if value:
                    return normalize_text(value)
    return None


def split_label_value(line: str, label: str) -> str | None:
    pattern = re.compile(rf'{re.escape(label)}\s*[:\-]\s*(.+)$', re.IGNORECASE)
    match = pattern.search(line)
    if match:
        return match.group(1).strip()
    return None


def extract_usn_from_text(lines: Iterable[str]) -> str | None:
    fallback: str | None = None
    for line in lines:
        for token in USN_REGEX.findall(line.upper()):
            if not is_likely_usn(token):
                continue
            if 'usn' in line.lower() or 'seat' in line.lower() or 'reg' in line.lower():
                return token
            if fallback is None:
                fallback = token
    return fallback


def is_likely_usn(value: str) -> bool:
    has_alpha = any(character.isalpha() for character in value)
    has_digit = any(character.isdigit() for character in value)
    return has_alpha and has_digit and len(value) >= 8


def extract_from_table_row(lines: Iterable[str]) -> ExtractedFields | None:
    for line in lines:
        match = TABLE_ROW_REGEX.search(line)
        if not match:
            continue
        raw_name = match.group('name')
        if is_header_like_name(raw_name):
            continue
        try:
            sgpa = float(match.group('sgpa'))
        except ValueError:
            continue
        return ExtractedFields(
            student_name=clean_candidate_text(raw_name),
            usn=match.group('usn').upper(),
            subject=clean_candidate_text(match.group('subject')),
            grade=clean_candidate_text(match.group('grade')),
            sgpa=sgpa,
        )
    return None


def clean_candidate_text(value: str | None) -> str | None:
    normalized = normalize_text(value)
    if not normalized:
        return None
    if len(normalized) > 120:
        return None
    return normalized


def is_header_like_name(value: str) -> bool:
    lowered = value.lower()
    header_tokens = ['name', 'usn', 'subject', 'grade', 'sgpa']
    return sum(token in lowered for token in header_tokens) >= 3


def parse_row_line(line: str) -> ExtractedFields | None:
    for pattern in ROW_PATTERNS:
        match = pattern.search(line)
        if not match:
            continue
        name = clean_candidate_text(match.group('name'))
        usn = match.group('usn').upper()
        subject = clean_candidate_text(match.group('subject'))
        grade = clean_candidate_text(match.group('grade'))
        sgpa = safe_float(match.group('sgpa'))

        if not usn or not is_likely_usn(usn):
            continue
        if name is None or subject is None or grade is None or sgpa is None:
            continue
        if is_header_like_name(name):
            continue

        return ExtractedFields(student_name=name, usn=usn, subject=subject, grade=grade, sgpa=sgpa)
    return None


def dedupe_rows(rows: list[ExtractedFields]) -> list[ExtractedFields]:
    deduped: list[ExtractedFields] = []
    seen: set[tuple[str, str, str, str, str, str, str]] = set()
    for row in rows:
        if not is_row_acceptable(row):
            continue
        key = (
            (row.usn or '').upper(),
            (row.student_name or '').lower(),
            (row.subject_code or row.subject or '').lower(),
            (row.subject_name or '').lower(),
            (row.subject or '').lower(),
            '' if row.grade is None else row.grade.lower(),
            '' if row.sgpa is None else f'{row.sgpa:.2f}',
            '' if row.grade_points is None else f'{row.grade_points:.2f}',
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def safe_float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def extract_sgpa(lines: Iterable[str]) -> float | None:
    for line in lines:
        lowered = line.lower()
        if 'sgpa' not in lowered and 'semester grade point average' not in lowered:
            continue
        matches = SGPA_REGEX.findall(line)
        if not matches:
            continue
        try:
            return float(matches[-1])
        except ValueError:
            continue
    return None


def first_non_empty(series: pd.Series) -> str | None:
    for value in series.tolist():
        if pd.notna(value):
            text = normalize_text(str(value))
            if text:
                return text
    return None


def first_float(series: pd.Series) -> float | None:
    for value in series.tolist():
        if pd.notna(value):
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
    return None
