import logging
import sys
from logging.handlers import RotatingFileHandler
from core.config import settings


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("pkm")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.DEBUG))

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        settings.LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger


log = _build_logger()
