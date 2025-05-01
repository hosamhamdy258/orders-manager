import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} ({filename}:{lineno}): {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "level": "INFO",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": os.path.join(BASE_DIR, "logs/django/error.log"),
            "formatter": "verbose",
            "level": "INFO",
        },
        "async_queue": {
            "()": "logging_utils.LoggingQueue",
            "handlers": {
                "root": ["console", "file"],
                "django": ["console", "file"],
                "django.request": ["console", "file"],
            },
            "respect_handler_level": True,
        },
        "mail_admins": {
            "level": "ERROR",
            "class": "django.utils.log.AdminEmailHandler",
        },
    },
    "root": {
        "handlers": [
            "async_queue",
        ],
        "level": "DEBUG",
    },
    "loggers": {
        "django": {
            "handlers": ["async_queue"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["async_queue"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
