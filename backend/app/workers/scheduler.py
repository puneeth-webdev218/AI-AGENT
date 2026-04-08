import logging
import threading
import time

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.email_service import IMAPEmailClient, sync_email_documents

logger = logging.getLogger(__name__)
settings = get_settings()
_worker_thread: threading.Thread | None = None
_stop_event = threading.Event()


def _parse_interval_minutes(cron_expression: str) -> int:
    first_field = cron_expression.split()[0]
    if first_field.startswith('*/'):
        try:
            return max(1, int(first_field[2:]))
        except ValueError:
            return 10
    return 10


def _run_loop() -> None:
    interval_minutes = _parse_interval_minutes(settings.email_poll_cron)
    interval_seconds = interval_minutes * 60
    logger.info('Email sync worker started', extra={'interval_minutes': interval_minutes})
    while not _stop_event.is_set():
        started_at = time.time()
        session: Session = SessionLocal()
        try:
            if settings.email_username and settings.email_password:
                with IMAPEmailClient(settings.imap_host, settings.imap_port, settings.email_username, settings.email_password, use_ssl=True) as client:
                    sync_email_documents(session, client, settings.email_folder, settings.email_subject_keyword_set, settings.storage_dir)
            else:
                logger.debug('Email sync worker skipped because credentials are missing')
        except Exception:
            logger.exception('Email sync worker iteration failed')
        finally:
            session.close()
        elapsed = time.time() - started_at
        wait_time = max(1, int(interval_seconds - elapsed))
        _stop_event.wait(wait_time)


def start_scheduler() -> None:
    global _worker_thread
    if _worker_thread is not None and _worker_thread.is_alive():
        return
    _stop_event.clear()
    _worker_thread = threading.Thread(target=_run_loop, name='email-sync-worker', daemon=True)
    _worker_thread.start()


def stop_scheduler() -> None:
    _stop_event.set()