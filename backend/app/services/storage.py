from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import get_settings

settings = get_settings()


class StorageError(Exception):
    pass


def validate_filename(filename: str) -> None:
    suffix = Path(filename).suffix.lower().lstrip('.')
    if suffix not in settings.allowed_extension_set:
        raise StorageError(f'Unsupported file type: .{suffix or "unknown"}')


def validate_upload_size(file_size_bytes: int) -> None:
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if file_size_bytes > max_bytes:
        raise StorageError(f'File exceeds maximum upload size of {settings.max_upload_size_mb} MB.')


def build_storage_path(source_name: str) -> Path:
    suffix = Path(source_name).suffix.lower()
    unique_name = f'{uuid4().hex}{suffix}'
    return settings.storage_dir / unique_name


async def save_upload_file(upload: UploadFile) -> Path:
    if not upload.filename:
        raise StorageError('Uploaded file is missing a filename.')
    validate_filename(upload.filename)
    destination = build_storage_path(upload.filename or 'upload.bin')
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        total_bytes = 0
        with destination.open('wb') as handle:
            while chunk := await upload.read(1024 * 1024):
                total_bytes += len(chunk)
                validate_upload_size(total_bytes)
                handle.write(chunk)
        return destination
    except Exception as exc:
        if destination.exists():
            destination.unlink(missing_ok=True)
        raise StorageError(f'Failed to save uploaded file: {exc}') from exc
