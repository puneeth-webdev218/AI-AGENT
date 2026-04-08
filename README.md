# Automated Academic Result Extraction and Analysis Agent

## 1. Architecture Design

The system is split into a FastAPI backend and a React + Tailwind frontend.

Backend responsibilities:
- Accept manual uploads and IMAP email attachments.
- Detect document types and extract text page by page.
- OCR scanned PDFs and images with Tesseract.
- Parse Excel sheets with pandas.
- Extract only fields explicitly present in the source text.
- Validate extracted values and persist partial records when appropriate.
- Store students, results, documents, and email logs in PostgreSQL.
- Convert natural language to safe SELECT-only SQL through Grok.

Frontend responsibilities:
- Dashboard for status and recent records.
- Upload page for manual file processing.
- Email Connect page for IMAP sync.
- Chatbot page for natural-language database queries.

Reliability choices:
- Strict field extraction and validation.
- Safe SQL enforcement before execution.
- Duplicate email prevention by Message-ID.
- Background email polling worker.
- Structured JSON logging.

## 2. Folder Structure

- `backend/app/main.py` - FastAPI application entrypoint.
- `backend/app/api/routes/` - HTTP routes.
- `backend/app/core/` - configuration and logging.
- `backend/app/db/` - database engine and session helpers.
- `backend/app/models/` - SQLAlchemy models.
- `backend/app/schemas/` - Pydantic schemas.
- `backend/app/services/` - processing, extraction, email, chatbot, storage, student helpers.
- `backend/app/workers/` - background email polling worker.
- `frontend/src/pages/` - React pages.
- `frontend/src/components/` - shared UI components.
- `frontend/src/lib/api.js` - frontend API client.

## 3. Database Schema

See `backend/schema.sql` for the exact PostgreSQL DDL.

Tables:
- `students`
- `results`
- `documents`
- `email_logs`

## 4. Backend

The backend is implemented in `backend/app/main.py` and the supporting modules under `backend/app/`.

Key API endpoints:
- `GET /api/v1/health`
- `POST /api/v1/documents/upload`
- `GET /api/v1/documents`
- `GET /api/v1/documents/{document_id}/status`
- `GET /api/v1/results`
- `GET /api/v1/results/{result_id}`
- `POST /api/v1/emails/sync`
- `POST /api/v1/chat/query`

## 5. Email Integration Module

The IMAP integration in `backend/app/services/email_service.py`:
- Connects to Gmail-compatible IMAP servers.
- Filters messages by subject keywords.
- Tracks processed `Message-ID` values in `email_logs`.
- Extracts attachments only.
- Saves attachments to local storage.
- Sends each attachment through the document pipeline.

## 6. Document Processing Pipeline

The pipeline in `backend/app/services/document_processor.py`:
- Detects file type by extension.
- PDFs: text extraction with pdfplumber, then OCR fallback page by page.
- Images: OCR with pytesseract.
- Excel: parsing with pandas.
- Raises errors when no readable text is found.

## 7. Extraction + Validation Logic

The strict extraction logic lives in `backend/app/services/extraction.py` and `backend/app/services/validation.py`.

Rules:
- Only label-driven extraction is used.
- No guessed values are created.
- Empty documents fail fast.
- Invalid fields are reported clearly.
- Partial records can still be stored if at least some valid data exists.

## 8. Grok Chatbot Integration

The Grok integration is implemented in `backend/app/services/chatbot.py`.

Behavior:
- Uses the xAI OpenAI-compatible client.
- Forces the system prompt to SELECT-only SQL.
- Rejects unsafe or multi-statement SQL.
- Executes only safe read queries.
- Returns real database rows only.

## 9. Frontend

The frontend is a React + Tailwind app in `frontend/`.

Pages:
- Dashboard
- Upload
- Email Connect
- Chatbot

UI behavior:
- Shows database health and recent records.
- Uploads files to the backend.
- Runs IMAP sync from the UI.
- Sends natural-language queries to the Grok-backed chatbot.

## 10. Integration Steps

1. Create and configure PostgreSQL.
2. Copy `backend/.env.example` to `backend/.env`.
3. Set `DATABASE_URL` and `XAI_API_KEY`.
4. Install Python dependencies from `backend/requirements.txt`.
5. Install frontend dependencies in `frontend/`.
6. Ensure Tesseract OCR is installed and on PATH.
7. Start the backend.
8. Start the frontend.

## 11. How to Run

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## 12. Debug + Logging System

Logging:
- JSON logging on the backend.
- Error messages are preserved in database records.
- Validation failures are stored with the relevant document or result.

Debugging:
- Health endpoint verifies API and database connectivity.
- Document status endpoints expose processing state.
- Email sync returns counts for fetched, processed, duplicate, and error cases.
- Chatbot responses include the generated SQL so unsafe behavior is easy to inspect.

## Notes

- The chatbot is SELECT-only.
- The pipeline never fabricates missing fields.
- Email sync is duplicate-safe.
- Multi-page PDFs are processed page by page to limit memory pressure.
