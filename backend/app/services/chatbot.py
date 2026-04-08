import logging
import os
import re
import json

from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy import text
from sqlalchemy.engine import Engine

load_dotenv()

logger = logging.getLogger(__name__)
SYSTEM_PROMPT = (
    'You are an SQL generator.\n'
    'Convert natural language into SAFE SQL queries.\n'
    'Only generate SELECT queries.\n'
    'Never guess data.\n'
    'Return ONLY SQL.\n'
)
ANSWER_PROMPT = (
    'You are a data analyst assistant.\n'
    'Answer the user question using ONLY the provided SQL results.\n'
    'Do not invent facts.\n'
    'If data is insufficient, clearly say that the available data is insufficient.\n'
    'Respond in concise natural language.'
)
SCHEMA_CONTEXT = (
    'Database schema:\n'
    'students(id, usn, name, created_at, updated_at)\n'
    'results(id, document_id, student_id, student_name, usn, subject, grade, sgpa, raw_text, validation_status, validation_message, created_at, updated_at)\n'
    'documents(id, filename, original_name, content_type, file_type, file_path, extracted_text, status, error_message, source_type, source_message_id, created_at, updated_at)\n'
    'email_logs(id, message_id, subject, sender, received_at, status, error_message, created_at)\n'
)
QWEN_MODEL = os.getenv('GROQ_MODEL', 'qwen-32b')


class ChatbotError(Exception):
    pass


class SQLSafetyError(ChatbotError):
    pass


class GroqQwenChatbot:
    def __init__(self) -> None:
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            raise ChatbotError('GROQ_API_KEY is not configured.')
        self.client = OpenAI(
            api_key=api_key,
            base_url='https://api.groq.com/openai/v1',
        )
        self.model = resolve_model_name(QWEN_MODEL)

    def generate_sql(self, query: str) -> str:
        print('Using GROQ QWEN model')
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': f'{SYSTEM_PROMPT}\n\n{SCHEMA_CONTEXT}'},
                    {'role': 'user', 'content': query},
                ],
                temperature=0,
            )
        except Exception as exc:
            raise ChatbotError(f'GROQ API request failed: {exc}') from exc

        raw_response = (response.choices[0].message.content or '').strip() if response.choices else ''
        print(f'API response: {raw_response}')
        sql = normalize_sql_output(raw_response)
        if not sql:
            raise ChatbotError('GROQ returned an empty SQL statement.')
        print(f'Generated SQL query: {sql}')
        return sql

    def repair_sql(self, user_query: str, failed_sql: str, db_error: str) -> str:
        print('Using GROQ QWEN model')
        repair_prompt = (
            f'User query: {user_query}\n'
            f'Failed SQL: {failed_sql}\n'
            f'Database error: {db_error}\n'
            'Return a corrected SELECT SQL query only, using existing columns from schema.'
        )
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': f'{SYSTEM_PROMPT}\n\n{SCHEMA_CONTEXT}'},
                    {'role': 'user', 'content': repair_prompt},
                ],
                temperature=0,
            )
        except Exception as exc:
            raise ChatbotError(f'GROQ API request failed: {exc}') from exc

        raw_response = (response.choices[0].message.content or '').strip() if response.choices else ''
        print(f'API response: {raw_response}')
        sql = normalize_sql_output(raw_response)
        if not sql:
            raise ChatbotError('GROQ returned an empty SQL statement during SQL repair.')
        print(f'Generated SQL query: {sql}')
        return sql

    def generate_answer(self, user_query: str, sql: str, rows: list[dict], latest_file_name: str | None = None) -> str:
        return grounded_answer_from_rows(user_query, rows, latest_file_name)


def grounded_answer_from_rows(user_query: str, rows: list[dict], latest_file_name: str | None = None) -> str:
    file_prefix = f'Based on latest analyzed file "{latest_file_name}", ' if latest_file_name else ''

    if not rows:
        return f'{file_prefix}no data is available for the requested query.'

    query_lower = user_query.lower()
    if any(token in query_lower for token in ['how many', 'count', 'number of', 'total']):
        aggregate_value = extract_single_numeric_aggregate(rows)
        if aggregate_value is not None:
            return f'{file_prefix}the total is {aggregate_value}.'
        return f"{file_prefix}there are {len(rows)} matching rows."

    cleaned_rows = [strip_hidden_answer_fields(row) for row in rows]
    selected_fields = infer_requested_fields(query_lower, cleaned_rows)

    lines: list[str] = []
    for row in cleaned_rows:
        projected = {key: row.get(key) for key in selected_fields if key in row}
        if not projected:
            continue

        if len(selected_fields) == 1:
            only_key = selected_fields[0]
            text_value = '' if projected.get(only_key) is None else str(projected.get(only_key))
            lines.append(text_value)
        else:
            parts = []
            for key in selected_fields:
                if key not in projected:
                    continue
                text_value = '' if projected[key] is None else str(projected[key])
                parts.append(f'{key}: {text_value}')
            if parts:
                lines.append(', '.join(parts))

    if not lines:
        return f'{file_prefix}no data is available for the requested query.'

    header = f'{file_prefix}found {len(rows)} matching rows.'
    return header + '\n' + '\n'.join(lines)


def strip_hidden_answer_fields(row: dict) -> dict:
    hidden_fields = {'created_at', 'updated_at', 'id'}
    return {
        key: value
        for key, value in row.items()
        if key not in hidden_fields and not key.endswith('_id')
    }


def infer_requested_fields(query_lower: str, rows: list[dict]) -> list[str]:
    if not rows:
        return []

    available_fields: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in available_fields:
                available_fields.append(key)

    requested: list[str] = []

    # Match explicit field names and common query terms.
    synonyms: dict[str, list[str]] = {
        'usn': ['usn'],
        'name': ['name', 'names', 'student name', 'student names'],
        'student_name': ['student name', 'student names', 'name', 'names'],
        'subject': ['subject', 'subjects'],
        'grade': ['grade', 'grades'],
        'sgpa': ['sgpa', 'cgpa', 'gpa'],
        'validation_status': ['validation status', 'status'],
        'validation_message': ['validation message', 'message'],
        'raw_text': ['raw text', 'text'],
    }

    for field in available_fields:
        field_lower = field.lower()
        matched = False

        # Exact/phrase matches by field name.
        if field_lower in query_lower or field_lower.replace('_', ' ') in query_lower:
            matched = True

        # Synonym matches for commonly requested fields.
        if not matched and field_lower in synonyms:
            if any(term in query_lower for term in synonyms[field_lower]):
                matched = True

        # Generic name requests should include either name field if present.
        if not matched and 'name' in query_lower and field_lower in {'name', 'student_name'}:
            matched = True

        if matched:
            requested.append(field)

    # If user did not clearly request specific columns, return all displayable fields.
    if not requested:
        return available_fields

    return requested


def extract_single_numeric_aggregate(rows: list[dict]) -> int | float | None:
    if len(rows) != 1:
        return None
    first_row = rows[0]
    if len(first_row) != 1:
        return None
    value = next(iter(first_row.values()))
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        text_value = value.strip()
        if re.fullmatch(r'-?\d+', text_value):
            return int(text_value)
        if re.fullmatch(r'-?\d+\.\d+', text_value):
            return float(text_value)
    return None


def estimate_tokens(text: str) -> int:
    # Rough approximation for LLM token counting.
    return max(1, len(text) // 4)


def compact_rows_for_prompt(rows: list[dict], max_rows: int, max_chars_per_value: int = 200) -> list[dict]:
    compacted: list[dict] = []
    for row in rows[:max_rows]:
        compact_row: dict = {}
        for key, value in row.items():
            text_value = '' if value is None else str(value)
            if len(text_value) > max_chars_per_value:
                text_value = f"{text_value[:max_chars_per_value]}..."
            compact_row[key] = text_value
        compacted.append(compact_row)
    return compacted


def build_answer_input(user_query: str, sql: str, rows: list[dict], token_budget: int) -> str:
    max_total_chars = max(1200, token_budget * 3)
    trimmed_query = user_query[:500]
    trimmed_sql = sql[:1200]

    base = (
        f'User question:\n{trimmed_query}\n\n'
        f'SQL used:\n{trimmed_sql}\n\n'
    )

    # Keep room for prompt wrappers and model output request metadata.
    available_for_rows_chars = max(400, max_total_chars - len(base) - 200)

    max_rows = min(20, len(rows))
    value_chars = 120

    while True:
        rows_payload = compact_rows_for_prompt(rows, max_rows, max_chars_per_value=value_chars)
        rows_json = json.dumps(rows_payload, ensure_ascii=True)
        if len(rows_json) <= available_for_rows_chars:
            break
        if max_rows > 1:
            max_rows = max(1, max_rows // 2)
            continue
        if value_chars > 40:
            value_chars = max(40, value_chars - 20)
            continue
        rows_json = rows_json[:available_for_rows_chars]
        break

    return f"{base}SQL result rows (JSON):\n{rows_json}\n"


def fallback_answer_from_rows(rows: list[dict]) -> str:
    if not rows:
        return 'No data available for the requested query.'

    sample = rows[:3]
    preview_lines: list[str] = []
    for index, row in enumerate(sample, 1):
        parts = []
        for key, value in list(row.items())[:6]:
            text_value = '' if value is None else str(value)
            if len(text_value) > 80:
                text_value = f"{text_value[:80]}..."
            parts.append(f"{key}={text_value}")
        preview_lines.append(f"Row {index}: " + ', '.join(parts))

    return (
        f"Found {len(rows)} matching rows. "
        "A compact response was returned because the LLM request exceeded provider token limits. "
        + ' '.join(preview_lines)
    )


def normalize_answer_output(answer: str) -> str:
    cleaned = answer.strip()
    cleaned = re.sub(r'<think>[\s\S]*?</think>', '', cleaned, flags=re.IGNORECASE).strip()
    if cleaned.startswith('```'):
        lines = cleaned.splitlines()
        if lines and lines[0].strip().startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith('```'):
            lines = lines[:-1]
        cleaned = '\n'.join(lines).strip()
    return cleaned


def normalize_sql_output(sql: str) -> str:
    cleaned = sql.strip()
    cleaned = re.sub(r'<think>[\s\S]*?</think>', '', cleaned, flags=re.IGNORECASE).strip()
    if cleaned.startswith('```'):
        lines = cleaned.splitlines()
        if lines and lines[0].strip().startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith('```'):
            lines = lines[:-1]
        cleaned = '\n'.join(lines).strip()
    if cleaned.lower().startswith('sql\n'):
        cleaned = cleaned[4:].strip()
    match = re.search(r'\bselect\b[\s\S]*', cleaned, flags=re.IGNORECASE)
    if match:
        cleaned = match.group(0).strip()
    if ';' in cleaned:
        cleaned = cleaned.split(';', 1)[0].strip()
    return cleaned


def resolve_model_name(model_name: str) -> str:
    if model_name.strip().lower() == 'qwen-32b':
        return 'qwen/qwen3-32b'
    return model_name


def ensure_safe_select(sql: str) -> str:
    normalized = sql.strip().rstrip(';')
    normalized = normalize_common_sql_mistakes(normalized)
    if normalized.count(';') > 0:
        raise SQLSafetyError('Only a single SQL statement is allowed.')
    if not normalized.lower().startswith('select'):
        raise SQLSafetyError('Only SELECT queries are allowed.')

    # Block inline comments and block comments explicitly.
    if '--' in normalized or '/*' in normalized or '*/' in normalized:
        raise SQLSafetyError('Unsafe SQL content detected.')

    # Match forbidden SQL keywords as whole words to avoid false positives
    # from safe column names like "updated_at".
    forbidden_keywords = ['delete', 'drop', 'update', 'insert', 'alter', 'truncate', 'create', 'grant', 'revoke']
    lowered = normalized.lower()
    for keyword in forbidden_keywords:
        if re.search(rf'\b{keyword}\b', lowered):
            raise SQLSafetyError('Unsafe SQL content detected.')
    return normalized


def normalize_common_sql_mistakes(sql: str) -> str:
    fixed = re.sub(r"validation_status\s*=\s*'valid'", "validation_status = 'validated'", sql, flags=re.IGNORECASE)
    fixed = re.sub(r'validation_status\s*=\s*"valid"', "validation_status = 'validated'", fixed, flags=re.IGNORECASE)
    return fixed


def scope_sql_to_latest_document(sql: str, latest_document_id: int | None) -> str:
    if latest_document_id is None:
        return sql
    lowered = sql.lower()

    if 'document_id' in lowered or 'is_latest' in lowered:
        return sql

    # Scope direct results queries to latest document.
    if re.search(r'\b(from|join)\s+results\b', lowered):
        results_ref = detect_table_reference(sql, 'results') or 'results'
        condition = f'{results_ref}.document_id = {latest_document_id}'
        scoped = append_condition(sql, condition)
        print(f'Scoped SQL query: {scoped}')
        return scoped

    # Scope students-only queries to students present in latest results.
    if re.search(r'\bfrom\s+students\b', lowered):
        students_ref = detect_table_reference(sql, 'students') or 'students'
        condition = (
            f'EXISTS (SELECT 1 FROM results r '
            f'WHERE r.student_id = {students_ref}.id AND r.document_id = {latest_document_id})'
        )
        scoped = append_condition(sql, condition)
        print(f'Scoped SQL query: {scoped}')
        return scoped

    if 'document_id' in lowered or 'is_latest' in lowered:
        return sql
    return sql


def detect_table_reference(sql: str, table_name: str) -> str | None:
    pattern = rf'\b(?:from|join)\s+{table_name}\s+(?:as\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\b'
    match = re.search(pattern, sql, flags=re.IGNORECASE)
    if match:
        alias = match.group(1)
        # Ignore SQL clause keywords accidentally captured as aliases.
        if alias.lower() not in {'where', 'group', 'order', 'limit', 'offset', 'inner', 'left', 'right', 'full', 'join', 'on'}:
            return alias
    return None


def append_condition(sql: str, condition: str) -> str:
    clause_match = re.search(r'\b(group\s+by|order\s+by|limit|offset)\b', sql, flags=re.IGNORECASE)
    if clause_match:
        idx = clause_match.start()
        head = sql[:idx].rstrip()
        tail = sql[idx:]
    else:
        head = sql.rstrip()
        tail = ''

    if re.search(r'\bwhere\b', head, flags=re.IGNORECASE):
        return f'{head} AND {condition} {tail}'.strip()
    return f'{head} WHERE {condition} {tail}'.strip()


def execute_safe_query(engine: Engine, sql: str) -> list[dict]:
    safe_sql = ensure_safe_select(sql)
    try:
        with engine.connect() as connection:
            result = connection.execute(text(safe_sql))
            rows = [dict(row._mapping) for row in result.fetchall()]
    except Exception as exc:
        raise ChatbotError(f'Database query failed: {exc}') from exc
    logger.info('Executed safe SQL query', extra={'row_count': len(rows)})
    return rows
