import sqlite3
from datetime import datetime
from pathlib import Path

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

# Modellerin import edildiginden emin olun
import models.category  # noqa: F401
import models.tag  # noqa: F401
import models.resource  # noqa: F401
from core.config import settings
from core.logger import log
from core.paths import resource_path
from utils.text_utils import fold_tr

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite icin gerekli
    # echo=True kullanilmiyor -- SQLAlchemy bu modda kendi stdout handler'ini
    # kurup konsolu SQL sorgu spam'iyle dolduruyordu. SQL loglama
    # core/logger.py::_configure_sqlalchemy_logging() uzerinden, sadece
    # dosyaya (konsola degil) yazacak sekilde ayri yonetiliyor.
    echo=False,
)


@event.listens_for(engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    if engine.url.get_backend_name() != "sqlite":
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

def register_sqlite_functions(target: Engine) -> None:
    """Her yeni SQLite baglantisina `fold_tr` SQL fonksiyonunu ekler (Turkce-duyarsiz arama).
    Test motorlari da bunu cagirir (bkz. tests/conftest.py)."""
    if target.url.get_backend_name() != "sqlite":
        return

    @event.listens_for(target, "connect")
    def _register(dbapi_connection, _connection_record) -> None:
        dbapi_connection.create_function("fold_tr", 1, fold_tr, deterministic=True)


register_sqlite_functions(engine)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# Mevcut SQLite tablolarinda eksik kolonlari ekleyen hafif migration listesi.
# (tablo_adi, kolon_adi, ALTER TABLE ifadesi)
_LIGHTWEIGHT_MIGRATIONS: list[tuple[str, str, str]] = [
    (
        "resources",
        "is_favorite",
        "ALTER TABLE resources ADD COLUMN is_favorite BOOLEAN NOT NULL DEFAULT 0",
    ),
]


def _apply_lightweight_migrations(target: Engine) -> None:
    """Eski DB dosyalarinda eksik kolonlari ekler. Base.metadata.create_all
    yalnizca eksik *tablolari* olusturur, kolon ekleme yapmaz; bu yardimci
    onu tamamlar. Idempotent: kolon zaten varsa atlanir.
    """
    inspector = inspect(target)
    existing_tables = set(inspector.get_table_names())
    for table_name, column_name, ddl in _LIGHTWEIGHT_MIGRATIONS:
        if table_name not in existing_tables:
            continue
        cols = {col["name"] for col in inspector.get_columns(table_name)}
        if column_name in cols:
            continue
        with target.begin() as conn:
            conn.execute(text(ddl))
        log.info("Migration uygulandi: %s.%s eklendi", table_name, column_name)


def _alembic_config() -> AlembicConfig:
    cfg = AlembicConfig(str(resource_path("alembic.ini")))
    cfg.set_main_option("script_location", str(resource_path("migrations")))
    cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    cfg.attributes["configure_logger"] = False
    return cfg


_BACKUP_KEEP = 3


def _sqlite_file(target: Engine) -> Path | None:
    """SQLite dosya yolu; bellek ici/baska motor ya da henuz olusmamis dosya icin None."""
    if target.url.get_backend_name() != "sqlite":
        return None
    database = target.url.database
    if not database or database == ":memory:":
        return None
    path = Path(database)
    return path if path.is_file() else None


def _pending_migration(cfg: AlembicConfig, target: Engine) -> tuple[bool, str]:
    """(bekleyen migration var mi, mevcut revision etiketi). Sema hic yoksa (yeni kurulum) False;
    Alembic-oncesi (legacy) DB `legacy` etiketiyle bekleyen sayilir (stamp + hafif migration
    calisacagi icin yedek alinir)."""
    tables = set(inspect(target).get_table_names())
    if not tables:
        return False, ""
    if "alembic_version" not in tables:
        return True, "legacy"
    with target.connect() as conn:
        current = MigrationContext.configure(conn).get_current_revision() or "none"
    head = ScriptDirectory.from_config(cfg).get_current_head()
    return current != head, current


def _prune_backups(db_file: Path, keep: int = _BACKUP_KEEP) -> None:
    backups = sorted(db_file.parent.glob(f"{db_file.name}.bak-*"))
    for old in backups[:-keep] if keep else backups:
        old.unlink(missing_ok=True)


def _backup_before_migration(db_file: Path, revision: str) -> Path:
    """Migration oncesi tutarli bir yedek alir (SQLite backup API: WAL dosyasini da kapsar)."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    destination = db_file.with_name(f"{db_file.name}.bak-{stamp}-{revision}")
    source = sqlite3.connect(db_file)
    try:
        target_conn = sqlite3.connect(destination)
        try:
            source.backup(target_conn)
        finally:
            target_conn.close()
    finally:
        source.close()
    _prune_backups(db_file)
    log.info("Migration oncesi veritabani yedeklendi: %s", destination.name)
    return destination


def init_db() -> None:
    """Veritabani semasini Alembic ile olusturur/gunceller. Uygulama baslarken
    bir kez cagrilir.

    - Sifirdan kurulum (tablo yok): migration zinciri bastan sona calisir.
    - Alembic-oncesi (legacy) DB (tablolar var ama alembic_version yok):
      semaya dokunmadan mevcut durum 'head' olarak isaretlenir (stamp),
      boylece kullanici verisi CREATE TABLE ile catismaz.
    - Zaten Alembic ile yonetilen DB: sadece bekleyen migration'lar uygulanir.

    Bekleyen migration varsa (ya da legacy DB) once yedek alinir (son 3 yedek tutulur);
    yeni kurulum ve guncel DB'de yedek alinmaz.
    """
    cfg = _alembic_config()
    db_file = _sqlite_file(engine)
    if db_file is not None:
        pending, revision = _pending_migration(cfg, engine)
        if pending:
            _backup_before_migration(db_file, revision)

    _apply_lightweight_migrations(engine)

    existing_tables = set(inspect(engine).get_table_names())
    if existing_tables and "alembic_version" not in existing_tables:
        alembic_command.stamp(cfg, "head")
        log.info("Mevcut veritabani Alembic head olarak isaretlendi (sema degismedi).")

    alembic_command.upgrade(cfg, "head")
    log.info("Veritabani semasi guncel (Alembic head).")


def get_session() -> Session:
    """Yeni bir veritabani oturumu dondurur. Cagiran kapatmaktan sorumludur."""
    return SessionLocal()
