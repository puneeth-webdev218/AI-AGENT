import asyncio
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models.document import Document
from app.models.result import Result
from app.models.student import Student
from app.schemas.document import DocumentResponse, LatestDocumentResponse, ProcessingResponse, UploadResponse
from app.services.document_processor import DocumentProcessingError, process_document
from app.services.storage import StorageError, save_upload_file
from app.services.students import upsert_student
from app.services.validation import is_row_acceptable, validate_extracted_fields
from dataclasses import asdict

router = APIRouter(prefix='/documents', tags=['documents'])


@router.post('/upload', response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db_session)) -> UploadResponse:
    saved_path = await save_upload_file(file)
    document = Document(
        filename=saved_path.name,
        original_name=file.filename or saved_path.name,
        content_type=file.content_type,
        file_type=saved_path.suffix.lstrip('.').lower(),
        file_path=str(saved_path),
        status='pending',
        source_type='upload',
    )
    db.add(document)
    db.flush()
    try:
        extracted_text, extracted_fields, processed_type, extracted_rows = await asyncio.wait_for(
            run_in_threadpool(process_document, saved_path),
            timeout=180,
        )
        print('EXTRACTED DATA:', asdict(extracted_fields))
        validation = validate_extracted_fields(extracted_fields)
        print('VALIDATED DATA:', {'status': validation.status, 'is_valid': validation.is_valid, 'messages': validation.messages})
        print('INSERTING INTO DB:', asdict(extracted_fields))

        db.execute(update(Document).values(is_latest=False))
        document.is_latest = True

        document.extracted_text = extracted_text
        document.file_type = processed_type

        all_rows = extracted_rows or [extracted_fields]
        total_rows = len(all_rows)
        inserted = 0
        failed_rows = 0
        skipped_rows = 0
        for row in all_rows:
            try:
                row_validation = validate_extracted_fields(row)
                if not is_row_acceptable(row):
                    skipped_rows += 1
                    continue

                student = upsert_student(db, row.usn, row.student_name)
                result = Result(
                    document_id=document.id,
                    student_id=student.id if student else None,
                    student_name=row.student_name,
                    usn=row.usn,
                    subject=row.subject,
                    grade=row.grade,
                    sgpa=row.sgpa,
                    raw_text=extracted_text,
                    validation_status='validated' if row_validation.is_valid else row_validation.status,
                    validation_message='; '.join(row_validation.messages) if row_validation.messages else None,
                )
                db.add(result)
                print('INSERTING:', {'name': row.student_name, 'usn': row.usn, 'subject': row.subject, 'grade': row.grade, 'sgpa': row.sgpa})
                inserted += 1
            except Exception:
                failed_rows += 1
                continue

        processed_ratio = (inserted / total_rows) if total_rows else 0.0
        if inserted == 0:
            document.status = 'failed'
        elif processed_ratio > 0.8:
            document.status = 'success'
        else:
            document.status = 'completed_with_errors'

        print('Total rows:', total_rows)
        print('Inserted:', inserted)
        print('Failed:', failed_rows)
        print('Skipped:', skipped_rows)
        document.error_message = '; '.join(validation.messages) if validation.messages else None
        db.commit()
        students_rows = db.execute(select(Student.id, Student.name, Student.usn)).all()
        print('SELECT * FROM students:', [dict(row._mapping) for row in students_rows])
        print('DB INSERT SUCCESS')
        db.refresh(document)
        return UploadResponse(message='Document processed successfully', document=serialize_document(document))
    except DocumentProcessingError as exc:
        document.status = 'failed'
        document.error_message = str(exc)
        db.add(document)
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except asyncio.TimeoutError as exc:
        document.status = 'failed'
        document.error_message = 'Document processing timed out. Please try a smaller or cleaner file.'
        db.add(document)
        db.commit()
        raise HTTPException(status_code=408, detail=document.error_message) from exc
    except StorageError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f'Failed to process document: {exc}') from exc


@router.get('', response_model=list[DocumentResponse])
def list_documents(db: Session = Depends(get_db_session)) -> list[DocumentResponse]:
    documents = db.scalars(select(Document).order_by(Document.created_at.desc())).all()
    return [serialize_document(document) for document in documents]


@router.get('/{document_id}/status', response_model=ProcessingResponse)
def document_status(document_id: int, db: Session = Depends(get_db_session)) -> ProcessingResponse:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail='Document not found')
    return ProcessingResponse(document_id=document.id, status=document.status, message=document.error_message)


@router.get('/latest', response_model=LatestDocumentResponse)
def latest_document(db: Session = Depends(get_db_session)) -> LatestDocumentResponse:
    document = db.scalar(select(Document).where(Document.is_latest.is_(True)).order_by(Document.created_at.desc()))
    if document is None:
        raise HTTPException(status_code=404, detail='No analyzed documents found')
    record_count = db.scalar(select(func.count(Result.id)).where(Result.document_id == document.id)) or 0
    return LatestDocumentResponse(
        document_id=document.id,
        file_name=document.original_name,
        uploaded_at=str(document.created_at),
        record_count=int(record_count),
    )


def serialize_document(document: Document) -> DocumentResponse:
    preview = document.extracted_text[:250] if document.extracted_text else None
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        original_name=document.original_name,
        content_type=document.content_type,
        file_type=document.file_type,
        status=document.status,
        is_latest=document.is_latest,
        error_message=document.error_message,
        extracted_text_preview=preview,
    )
