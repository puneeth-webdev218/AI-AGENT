from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.health import HealthResponse

router = APIRouter(tags=['health'])


@router.get('/health', response_model=HealthResponse)
def health_check(db: Session = Depends(get_db_session)) -> HealthResponse:
    db.execute(text('SELECT 1'))
    return HealthResponse(status='ok', database='connected')
