import logging
import sys
from logging.handlers import RotatingFileHandler
from core.config import settings

_FORMATTER = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def _build_file_handler() -> RotatingFileHandler:
    handler = RotatingFileHandler(
        settings.LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(_FORMATTER)
    return handler


def _build_logger(file_handler: RotatingFileHandler) -> logging.Logger:
    logger = logging.getLogger("pkm")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.DEBUG))
    logger.propagate = False  # kok logger'a sizip baska handler'larca tekrar basilmasin

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(_FORMATTER)
    # Konsol sadece hata/uyari gorsun; tam gecmis (INFO/DEBUG dahil) dosyada kalir.
    console_handler.setLevel(logging.WARNING)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger


def _configure_sqlalchemy_logging(file_handler: RotatingFileHandler) -> None:
    """SQLAlchemy/Alembic SQL loglarini konsola degil sadece dosyaya yazar.

    `create_engine(echo=True)` kendi stdout handler'ini kurup konsolu SQL
    sorgu spam'iyle dolduruyordu (bkz. utils/db_utils.py). Bunun yerine
    logging modulunu burada elle yapilandiriyoruz: kayitlar dosyaya gider,
    konsola veya kok logger'a hic sizmaz.
    """
    level = logging.INFO if settings.APP_ENV == "development" else logging.WARNING
    for name in ("sqlalchemy.engine", "alembic"):
        sa_logger = logging.getLogger(name)
        sa_logger.setLevel(level)
        sa_logger.addHandler(file_handler)
        sa_logger.propagate = False


_file_handler = _build_file_handler()
log = _build_logger(_file_handler)
_configure_sqlalchemy_logging(_file_handler)
