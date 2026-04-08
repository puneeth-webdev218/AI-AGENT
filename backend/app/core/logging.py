import json
import logging
from logging.config import dictConfig


class CustomJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'message': record.getMessage(),
        }
        if record.exc_info:
            payload['exception'] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(debug: bool = False) -> None:
    level = 'DEBUG' if debug else 'INFO'
    dictConfig(
        {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'json': {
                    '()': CustomJsonFormatter,
                    'fmt': '%(asctime)s %(level)s %(name)s %(message)s',
                },
                'plain': {
                    'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
                },
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'formatter': 'json',
                },
            },
            'root': {
                'handlers': ['console'],
                'level': level,
            },
        }
    )
    logging.getLogger('uvicorn.error').setLevel(level)
    logging.getLogger('uvicorn.access').setLevel(level)
