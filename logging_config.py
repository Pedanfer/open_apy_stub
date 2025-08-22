import logging
import os
from logging.config import dictConfig

os.makedirs("logs", exist_ok=True)
file_path = os.path.join(os.getcwd(), "logs/app.log")

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "minimal": {"format": "%(asctime)s - %(levelname)s - %(message)s"},
    },
    "handlers": {
        "file_handler": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "formatter": "minimal",
            "filename": file_path,
            "when": "midnight",
            "interval": 1,
            "backupCount": 7,
            "encoding": "utf8",
        },
        "console_handler": {
            "level": "INFO",
            "formatter": "minimal",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["file_handler", "console_handler"],
    },
}

dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("logger")
