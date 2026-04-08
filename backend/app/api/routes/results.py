from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models.result import Result
from app.schemas.result import ResultResponse

router = APIRouter(prefix='/results', tags=['results'])


@router.get('', response_model=list[ResultResponse])
def list_results(db: Session = Depends(get_db_session)) -> list[ResultResponse]:
    results = db.scalars(select(Result).order_by(Result.created_at.desc())).all()
    return [serialize_result(result) for result in results]


@router.get('/{result_id}', response_model=ResultResponse)
def get_result(result_id: int, db: Session = Depends(get_db_session)) -> ResultResponse:
    result = db.get(Result, result_id)
    if result is None:
        raise HTTPException(status_code=404, detail='Result not found')
    return serialize_result(result)


def serialize_result(result: Result) -> ResultResponse:
    return ResultResponse(
        id=result.id,
        document_id=result.document_id,
        student_name=result.student_name,
        usn=result.usn,
        subject=result.subject,
        grade=result.grade,
        sgpa=result.sgpa,
        validation_status=result.validation_status,
        validation_message=result.validation_message,
        raw_text=result.raw_text,
    )
