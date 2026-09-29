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


class _ConsoleFormatter(logging.Formatter):
    """Konsolda sadece tek satirlik mesaj: traceback'ler (beklenen dogrulama
    hatalari dahil) yalnizca dosyaya yazilir, konsolu doldurmaz."""

    def formatException(self, exc_info) -> str:
        return ""


_CONSOLE_FORMATTER = _ConsoleFormatter(fmt=_FORMATTER._fmt, datefmt=_FORMATTER.datefmt)


def _build_logger(file_handler: RotatingFileHandler) -> logging.Logger:
    logger = logging.getLogger("pkm")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.DEBUG))
    logger.propagate = False  # kok logger'a sizip baska handler'larca tekrar basilmasin

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(_CONSOLE_FORMATTER)
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


def _configure_third_party_logging(file_handler: RotatingFileHandler) -> None:
    """Gurultulu ucuncu-parti kutuphane loglarini konsoldan uzak tutar.

    pypdf, bozuk/subset fontlu akademik PDF'lerde her sayfa icin font
    sozlugunun tamamini WARNING olarak basiyordu (konsolu binlerce satirla
    dolduruyordu). Sadece gercek hatalar (ERROR+) dosyaya yazilir.
    """
    for name in ("pypdf", "trafilatura", "htmldate", "courlan"):
        third_party = logging.getLogger(name)
        third_party.setLevel(logging.ERROR)
        third_party.addHandler(file_handler)
        third_party.propagate = False


_file_handler = _build_file_handler()
log = _build_logger(_file_handler)
_configure_sqlalchemy_logging(_file_handler)
_configure_third_party_logging(_file_handler)
