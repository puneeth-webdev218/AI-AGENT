from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'Automated Academic Result Extraction and Analysis Agent'
    api_v1_prefix: str = '/api/v1'
    environment: str = 'development'
    debug: bool = True

    database_url: str = Field(default='postgresql+psycopg://postgres:postgres@localhost:5432/ai_agent')
    storage_dir: Path = Field(default=Path('storage'))
    max_upload_size_mb: int = 25
    allowed_extensions: str = 'pdf,png,jpg,jpeg,tif,tiff,xls,xlsx'
    subject_keywords: str = 'result,marks,grade,grade card,mark sheet,semester,score'

    imap_host: str = 'imap.gmail.com'
    imap_port: int = 993
    email_poll_cron: str = '*/5 * * * *'
    email_poll_enabled: bool = True
    email_folder: str = 'INBOX'
    email_subject_keywords: str = 'result,marks,grade,mark sheet,score,semester'
    email_track_seen: bool = True
    email_username: str = ''
    email_password: str = ''

    xai_api_key: str = ''
    xai_base_url: str = 'https://api.x.ai/v1'
    grok_model: str = 'grok-beta'

    cors_origins: str = 'http://localhost:5173'

    @property
    def allowed_extension_set(self) -> set[str]:
        return {item.strip().lower() for item in self.allowed_extensions.split(',') if item.strip()}

    @property
    def subject_keyword_set(self) -> set[str]:
        return {item.strip().lower() for item in self.subject_keywords.split(',') if item.strip()}

    @property
    def email_subject_keyword_set(self) -> set[str]:
        return {item.strip().lower() for item in self.email_subject_keywords.split(',') if item.strip()}

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(',') if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    return settings
