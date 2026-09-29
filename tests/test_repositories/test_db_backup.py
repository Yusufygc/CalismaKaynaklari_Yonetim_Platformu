from alembic import command as alembic_command
from sqlalchemy import create_engine, text

from utils import db_utils


def _use_db(tmp_path, monkeypatch, name="app.db"):
    db_path = tmp_path / name
    url = f"sqlite:///{db_path}"
    test_engine = create_engine(url)
    monkeypatch.setattr(db_utils, "engine", test_engine)
    monkeypatch.setattr(db_utils.settings, "DATABASE_URL", url)
    return db_path, test_engine


def _backups(db_path):
    return sorted(db_path.parent.glob(f"{db_path.name}.bak-*"))


def test_fresh_database_is_not_backed_up(tmp_path, monkeypatch):
    db_path, _ = _use_db(tmp_path, monkeypatch)

    db_utils.init_db()

    assert _backups(db_path) == []


def test_up_to_date_database_is_not_backed_up(tmp_path, monkeypatch):
    db_path, _ = _use_db(tmp_path, monkeypatch)
    db_utils.init_db()

    db_utils.init_db()  # zaten head

    assert _backups(db_path) == []


def test_pending_migration_creates_backup_with_data_and_revision_label(tmp_path, monkeypatch):
    db_path, test_engine = _use_db(tmp_path, monkeypatch)
    db_utils.init_db()
    with test_engine.begin() as conn:
        conn.execute(text("INSERT INTO categories (name, color_hex) VALUES ('Python', '#3776AB')"))
    cfg = db_utils._alembic_config()
    alembic_command.downgrade(cfg, "-1")  # bir migration bekliyor
    with test_engine.connect() as conn:
        old_revision = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()

    db_utils.init_db()

    backups = _backups(db_path)
    assert len(backups) == 1 and backups[0].name.endswith(f"-{old_revision}")
    copy = create_engine(f"sqlite:///{backups[0]}")
    with copy.connect() as conn:
        assert conn.execute(text("SELECT name FROM categories")).fetchall() == [("Python",)]
        # Yedek, migration'dan ONCEKI durumdur.
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == old_revision
    copy.dispose()


def test_legacy_database_is_backed_up_before_stamp(tmp_path, monkeypatch):
    from models.base import Base

    db_path, test_engine = _use_db(tmp_path, monkeypatch)
    Base.metadata.create_all(test_engine)  # alembic_version yok

    db_utils.init_db()

    backups = _backups(db_path)
    assert len(backups) == 1 and backups[0].name.endswith("-legacy")


def test_only_last_three_backups_are_kept(tmp_path, monkeypatch):
    db_path, _ = _use_db(tmp_path, monkeypatch)
    db_path.write_bytes(b"")
    for stamp in ("20260101-000001", "20260101-000002", "20260101-000003", "20260101-000004"):
        (tmp_path / f"{db_path.name}.bak-{stamp}-x").write_bytes(b"old")

    db_utils._prune_backups(db_path)

    assert [b.name.split("bak-")[1] for b in _backups(db_path)] == [
        "20260101-000002-x", "20260101-000003-x", "20260101-000004-x",
    ]


def test_memory_and_missing_databases_have_no_backup_file():
    assert db_utils._sqlite_file(create_engine("sqlite:///:memory:")) is None
    assert db_utils._sqlite_file(create_engine("sqlite:///C:/yok/olmayan.db")) is None
