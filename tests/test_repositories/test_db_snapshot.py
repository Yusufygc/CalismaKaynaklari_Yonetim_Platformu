import sqlite3

import pytest
from sqlalchemy import create_engine

from utils import db_utils


@pytest.fixture()
def engine_and_path(tmp_path):
    path = tmp_path / "pkm.db"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE t (x INTEGER)")
    connection.execute("INSERT INTO t VALUES (42)")
    connection.commit()
    connection.close()
    return create_engine(f"sqlite:///{path.as_posix()}"), path


def test_daily_snapshot_is_a_consistent_copy_and_taken_once_per_day(engine_and_path):
    engine, path = engine_and_path

    first = db_utils.snapshot_database_daily(engine)
    second = db_utils.snapshot_database_daily(engine)

    assert first is not None and first.name.startswith("pkm.db.daily-")
    assert second is None
    assert sqlite3.connect(first).execute("SELECT x FROM t").fetchall() == [(42,)]


def test_daily_snapshots_keep_only_the_newest_n(engine_and_path):
    engine, path = engine_and_path
    for day in range(1, 10):
        (path.parent / f"pkm.db.daily-2026010{day}").write_bytes(b"x")

    created = db_utils.snapshot_database_daily(engine, keep=3)

    names = sorted(p.name for p in path.parent.glob("pkm.db.daily-*"))
    assert len(names) == 3 and created.name in names


def test_in_memory_database_is_skipped():
    assert db_utils.snapshot_database_daily(create_engine("sqlite:///:memory:")) is None
