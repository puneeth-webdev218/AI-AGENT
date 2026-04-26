import logging
from threading import Lock, Thread
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal, get_db_session
from app.models.email_log import EmailLog
from app.schemas.email import EmailConnectRequest, EmailConnectResponse, EmailJobStatusResponse, EmailLogResponse, EmailSyncResponse, EmailItemResponse, EmailProcessRequest, EmailProcessResponse
from app.services.email_service import EmailConnectionError, EmailSyncError, test_email_connection, fetch_and_store_emails, sync_email_documents, IMAPEmailClient, process_selected_email

router = APIRouter(prefix='/emails', tags=['emails'])
alias_router = APIRouter(prefix='/email', tags=['emails'])
logger = logging.getLogger(__name__)
settings = get_settings()
_job_lock = Lock()
_sync_jobs: dict[str, dict] = {}


def _set_job(job_id: str, **values) -> None:
    with _job_lock:
        current = _sync_jobs.get(job_id, {'job_id': job_id})
        current.update(values)
        _sync_jobs[job_id] = current


def _run_sync_job(job_id: str, request: EmailConnectRequest) -> None:
    session = SessionLocal()
    try:
        _set_job(job_id, status='running', message='Email sync in progress')
        subject_keywords = request.subject_keywords or list(settings.email_subject_keyword_set)
        with IMAPEmailClient(request.host, request.port, request.username, request.password, request.use_ssl) as client:
            result = sync_email_documents(session, client, request.folder, subject_keywords, settings.storage_dir)
        _set_job(job_id, status='completed', **result)
    except Exception as exc:
        logger.exception('Background email sync failed')
        _set_job(job_id, status='failed', message=str(exc))
    finally:
        session.close()


def _format_email_response(records: list) -> list[EmailItemResponse]:
    return [
        EmailItemResponse(
            email_id=item.email_id,
            message_id=item.message_id,
            subject=item.subject,
            sender=item.sender,
            date=item.date,
            has_attachment=item.has_attachment,
            processed_flag=item.processed_flag,
        )
        for item in records
    ]


@router.post('/connect', response_model=EmailConnectResponse)
def connect_email(request: EmailConnectRequest, db: Session = Depends(get_db_session)) -> EmailConnectResponse:
    """
    TEST EMAIL CONNECTION AND FETCH EMAILS.
    
    This endpoint:
    1. Tests the connection
    2. If successful, fetches emails from the specified folder
    3. Stores emails in database and returns them to the user
    """
    logger.info(f'🔌 POST /email/connect - Connecting to {request.host}:{request.port} as {request.username}')
    
    try:
        # Step 1: Test connection
        logger.info(f'   Step 1/2: Testing connection...')
        result = test_email_connection(
            host=request.host,
            port=request.port,
            username=request.username,
            password=request.password,
            use_ssl=request.use_ssl
        )
        
        if result['status'] != 'success':
            logger.warning(f'   ❌ Connection test failed: {result["message"]}')
            return EmailConnectResponse(
                status='failed',
                email_count=0,
                emails=[],
                error=result['message']
            )
        
        # Step 2: Fetch emails after successful connection
        logger.info(f'   Step 2/2: Fetching emails...')
        summaries = fetch_and_store_emails(
            session=db,
            host=request.host,
            port=request.port,
            username=request.username,
            password=request.password,
            use_ssl=request.use_ssl,
            folder=request.folder
        )
        
        # Convert EmailSummary to EmailItemResponse
        emails = [
            EmailItemResponse(
                email_id=summary.email_id,
                message_id=summary.message_id,
                subject=summary.subject,
                sender=summary.sender,
                date=summary.date,
                has_attachment=summary.has_attachment,
                processed_flag=summary.processed_flag,
            )
            for summary in summaries
        ]
        
        logger.info(f'✅ Connected! Fetched {len(emails)} emails for {request.username}')
        return EmailConnectResponse(
            status='success',
            email_count=len(emails),
            emails=emails,
            error=None
        )
            
    except Exception as exc:
        logger.exception(f'❌ Unexpected error in connect_email: {exc}')
        return EmailConnectResponse(
            status='failed',
            email_count=0,
            emails=[],
            error=f'Connection or fetch error: {str(exc)}'
        )


@alias_router.post('/connect', response_model=EmailConnectResponse)
def connect_email_alias(request: EmailConnectRequest, db: Session = Depends(get_db_session)) -> EmailConnectResponse:
    return connect_email(request, db)


@router.post('/sync', response_model=EmailSyncResponse)
def sync_emails(request: EmailConnectRequest, db: Session = Depends(get_db_session)) -> EmailSyncResponse:
    """
    FETCH AND SYNC EMAILS - This is called AFTER successful connection.
    
    This can take longer since it's actually fetching emails.
    """
    logger.info(f'📧 POST /emails/sync - Fetching emails from {request.host}:{request.port}')
    
    try:
        # First verify connection one more time
        conn_result = test_email_connection(
            host=request.host,
            port=request.port,
            username=request.username,
            password=request.password,
            use_ssl=request.use_ssl
        )
        
        if conn_result['status'] != 'success':
            logger.warning(f'❌ Connection verification failed: {conn_result["message"]}')
            raise EmailConnectionError(conn_result['message'])
        
        # Now fetch emails
        summaries = fetch_and_store_emails(
            session=db,
            host=request.host,
            port=request.port,
            username=request.username,
            password=request.password,
            use_ssl=request.use_ssl,
            folder=request.folder
        )
        
        logger.info(f'✅ Synced {len(summaries)} emails')
        return EmailSyncResponse(
            job_id=uuid4().hex,
            status='completed',
            fetched=len(summaries),
            processed_documents=0,
            skipped_duplicates=0,
            errors=0,
            message=f'Successfully synced {len(summaries)} emails'
        )
        
    except EmailConnectionError as exc:
        logger.warning(f'❌ Email sync connection failed: {exc}')
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception(f'❌ Email sync failed: {exc}')
        raise HTTPException(status_code=500, detail=f'Email sync failed: {exc}') from exc


@alias_router.post('/sync', response_model=EmailSyncResponse)
def sync_emails_alias(request: EmailConnectRequest, db: Session = Depends(get_db_session)) -> EmailSyncResponse:
    return sync_emails(request, db)


@alias_router.post('/process/{email_id}', response_model=EmailProcessResponse)
def process_email_attachment(
    email_id: str,
    request: EmailProcessRequest | None = Body(default=None),
    db: Session = Depends(get_db_session),
) -> EmailProcessResponse:
    host = request.host if request and request.host else settings.imap_host
    port = request.port if request and request.port else settings.imap_port
    username = request.username if request and request.username else settings.email_username
    password = request.password if request and request.password else settings.email_password
    folder = request.folder if request and request.folder else settings.email_folder
    use_ssl = request.use_ssl if request and request.use_ssl is not None else True

    if not username or not password:
        raise HTTPException(status_code=400, detail='Email credentials missing. Provide username/password in request or backend .env.')

    try:
        with IMAPEmailClient(host, port, username, password, use_ssl) as client:
            result = process_selected_email(
                session=db,
                client=client,
                folder=folder,
                selected_email_id=email_id,
            )
        return EmailProcessResponse(**result)
    except EmailSyncError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception('Failed to process selected email attachment')
        raise HTTPException(status_code=500, detail=f'Email attachment processing failed: {exc}') from exc


@router.get('/jobs/{job_id}', response_model=EmailJobStatusResponse)
def get_email_sync_job(job_id: str) -> EmailJobStatusResponse:
    with _job_lock:
        job = _sync_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail='Job not found')
    return EmailJobStatusResponse(**job)


@router.get('/logs', response_model=list[EmailLogResponse])
def list_email_logs(db: Session = Depends(get_db_session)) -> list[EmailLogResponse]:
    logs = db.scalars(select(EmailLog).order_by(EmailLog.created_at.desc()).limit(50)).all()
    return [
        EmailLogResponse(
            email_id=log.email_id,
            message_id=log.message_id,
            subject=log.subject,
            sender=log.sender,
            received_at=log.received_at,
            status=log.status,
            processed_flag=log.processed_flag,
            error_message=log.error_message,
        )
        for log in logs
    ]
