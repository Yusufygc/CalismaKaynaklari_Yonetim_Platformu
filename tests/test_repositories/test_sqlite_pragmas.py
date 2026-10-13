import threading

from sqlalchemy import create_engine, event, text

from utils import db_utils


def _engine(url: str):
    engine = create_engine(url, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _configure(dbapi_connection, _record) -> None:
        db_utils.configure_sqlite_connection(dbapi_connection, db_utils._is_file_database(engine))

    return engine


def _pragma(engine, name: str):
    with engine.connect() as conn:
        return conn.execute(text(f"PRAGMA {name}")).scalar()


def test_file_database_uses_wal_with_busy_timeout(tmp_path):
    engine = _engine(f"sqlite:///{tmp_path / 'app.db'}")
    assert _pragma(engine, "journal_mode") == "wal"
    assert _pragma(engine, "foreign_keys") == 1
    assert _pragma(engine, "busy_timeout") == 5000
    assert _pragma(engine, "synchronous") == 1  # NORMAL
    assert _pragma(engine, "wal_autocheckpoint") == 100


def test_memory_database_keeps_default_journal_but_enforces_foreign_keys():
    engine = _engine("sqlite:///:memory:")
    assert _pragma(engine, "journal_mode") == "memory"
    assert _pragma(engine, "foreign_keys") == 1


def test_reader_is_not_blocked_by_an_open_writer(tmp_path):
    """WAL: yazan baglanti islemi acikken ikinci baglanti okuyabilir (arama ayri baglantidan calisabilsin)."""
    engine = _engine(f"sqlite:///{tmp_path / 'app.db'}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)"))
        conn.execute(text("INSERT INTO t (v) VALUES ('eski')"))

    seen: list[int] = []
    writer = engine.connect()
    try:
        writer.execute(text("INSERT INTO t (v) VALUES ('yeni')"))  # commit edilmemis yazma islemi

        def read() -> None:
            with engine.connect() as reader:
                seen.append(reader.execute(text("SELECT count(*) FROM t")).scalar())

        thread = threading.Thread(target=read)
        thread.start()
        thread.join(timeout=3)
        assert not thread.is_alive(), "okuyucu yaziciyi bekledi (WAL degil)"
    finally:
        writer.rollback()
        writer.close()
    assert seen == [1]  # yalnizca commit edilmis satir gorunur


def test_backup_api_copies_wal_database(tmp_path):
    engine = _engine(f"sqlite:///{tmp_path / 'app.db'}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE t (v TEXT)"))
        conn.execute(text("INSERT INTO t VALUES ('korunan')"))
    destination = tmp_path / "copy.db"
    db_utils._sqlite_backup(tmp_path / "app.db", destination)  # yazan baglanti havuzda acikken de tutarli kopya
    copy = _engine(f"sqlite:///{destination}")
    with copy.connect() as conn:
        assert conn.execute(text("SELECT v FROM t")).scalar() == "korunan"
