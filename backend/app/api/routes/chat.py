from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models.document import Document
from app.schemas.chatbot import ChatRequest, ChatResponse
from app.services.chatbot import ChatbotError, GroqQwenChatbot, execute_safe_query, scope_sql_to_latest_document
from app.db.session import engine

router = APIRouter(prefix='/chat', tags=['chat'])


@router.post('/query', response_model=ChatResponse)
def query_chatbot(request: ChatRequest, db: Session = Depends(get_db_session)) -> ChatResponse:
    try:
        chatbot = GroqQwenChatbot()
        sql = chatbot.generate_sql(request.query)
        latest_document = db.scalar(select(Document).where(Document.is_latest.is_(True)).order_by(Document.created_at.desc()))
        sql = scope_sql_to_latest_document(sql, latest_document.id if latest_document else None)
        try:
            rows = execute_safe_query(engine, sql)
        except ChatbotError as exc:
            if 'Database query failed:' not in str(exc):
                raise
            repaired_sql = chatbot.repair_sql(request.query, sql, str(exc))
            repaired_sql = scope_sql_to_latest_document(repaired_sql, latest_document.id if latest_document else None)
            rows = execute_safe_query(engine, repaired_sql)
            sql = repaired_sql

        if not rows:
            repaired_sql = chatbot.repair_sql(
                request.query,
                sql,
                'Query returned zero rows. Use correct schema values and avoid unnecessary restrictive filters.',
            )
            repaired_sql = scope_sql_to_latest_document(repaired_sql, latest_document.id if latest_document else None)
            if repaired_sql.strip() != sql.strip():
                retry_rows = execute_safe_query(engine, repaired_sql)
                if retry_rows:
                    rows = retry_rows
                    sql = repaired_sql

        if not rows:
            return ChatResponse(
                answer='No data available for the requested query.',
                sql=sql,
                rows=[],
                row_count=0,
            )

        answer = chatbot.generate_answer(request.query, sql, rows, latest_document.original_name if latest_document else None)
        return ChatResponse(answer=answer, sql=sql, rows=rows, row_count=len(rows))
    except ChatbotError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Chat query failed: {exc}') from exc
