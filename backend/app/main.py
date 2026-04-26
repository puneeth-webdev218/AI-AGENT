import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.api.routes.chat import router as chat_router
from app.api.routes.documents import router as documents_router
from app.api.routes.emails import alias_router as emails_alias_router
from app.api.routes.emails import router as emails_router
from app.api.routes.email_oauth_bridge import router as email_oauth_bridge_router
from app.api.routes.health import router as health_router
from app.api.routes.results import router as results_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.base import Base
from app.db.session import engine
from app.models import Document, EmailLog, Result, Student
from app.workers.scheduler import start_scheduler, stop_scheduler

settings = get_settings()
configure_logging(settings.debug)
logger = logging.getLogger(__name__)
app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=r'https?://(localhost|127\.0\.0\.1|\d{1,3}(?:\.\d{1,3}){3})(:\d+)?$',
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(health_router, prefix=settings.api_v1_prefix)
app.include_router(documents_router, prefix=settings.api_v1_prefix)
app.include_router(results_router, prefix=settings.api_v1_prefix)
app.include_router(emails_router, prefix=settings.api_v1_prefix)
app.include_router(emails_alias_router, prefix=settings.api_v1_prefix)
app.include_router(chat_router, prefix=settings.api_v1_prefix)
app.include_router(email_oauth_bridge_router)


@app.on_event('startup')
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_result_columns()
    with engine.begin() as connection:
        try:
            connection.execute(text('ALTER TABLE documents ADD COLUMN is_latest BOOLEAN NOT NULL DEFAULT 0'))
        except Exception:
            # Column may already exist.
            pass
        try:
            connection.execute(text('ALTER TABLE email_logs ADD COLUMN email_id VARCHAR(255)'))
        except Exception:
            pass
        try:
            connection.execute(text('ALTER TABLE email_logs ADD COLUMN processed_flag BOOLEAN NOT NULL DEFAULT 0'))
        except Exception:
            pass
    if settings.email_poll_enabled:
        start_scheduler()
    logger.info('Application startup completed')


@app.on_event('shutdown')
def on_shutdown() -> None:
    stop_scheduler()
    logger.info('Application shutdown completed')


@app.get('/')
def root() -> dict[str, str]:
    return {'message': settings.app_name, 'status': 'running'}


def ensure_result_columns() -> None:
    inspector = inspect(engine)
    existing_columns = {column['name'] for column in inspector.get_columns('results')}
    missing_columns: list[tuple[str, str]] = []

    if 'subject_code' not in existing_columns:
        missing_columns.append(('subject_code', 'VARCHAR(32)'))
    if 'subject_name' not in existing_columns:
        missing_columns.append(('subject_name', 'VARCHAR(255)'))
    if 'grade_points' not in existing_columns:
        missing_columns.append(('grade_points', 'DOUBLE PRECISION'))

    if not missing_columns:
        return

    with engine.begin() as connection:
        for column_name, column_type in missing_columns:
            try:
                connection.execute(text(f'ALTER TABLE results ADD COLUMN {column_name} {column_type}'))
                logger.info('Added missing results column: %s', column_name)
            except Exception as exc:
                logger.warning('Could not add results column %s: %s', column_name, exc)
