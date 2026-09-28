from sqlalchemy import create_engine, inspect, text

from models.base import Base
from models.category import Category
from utils import db_utils

_APP_TABLES = {
    "categories",
    "tags",
    "resources",
    "resource_tags_link",
    "highlights",
    "vocabulary",
}


def test_init_db_creates_full_schema_on_fresh_database(tmp_path, monkeypatch):
    db_path = tmp_path / "fresh.db"
    test_engine = create_engine(f"sqlite:///{db_path}")
    monkeypatch.setattr(db_utils, "engine", test_engine)
    monkeypatch.setattr(db_utils.settings, "DATABASE_URL", f"sqlite:///{db_path}")

    db_utils.init_db()

    tables = set(inspect(test_engine).get_table_names())
    assert _APP_TABLES <= tables
    assert "alembic_version" in tables


def test_init_db_stamps_legacy_database_without_touching_data(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy.db"
    # Alembic-oncesi bir kurulumu simule et: tablolar Base.metadata ile
    # dogrudan olusturulmus, alembic_version hic yok.
    legacy_engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(legacy_engine)
    with legacy_engine.begin() as conn:
        conn.execute(
            text("INSERT INTO categories (name, color_hex) VALUES (:name, :color)"),
            {"name": "Python", "color": "#3776AB"},
        )
    legacy_engine.dispose()

    test_engine = create_engine(f"sqlite:///{db_path}")
    monkeypatch.setattr(db_utils, "engine", test_engine)
    monkeypatch.setattr(db_utils.settings, "DATABASE_URL", f"sqlite:///{db_path}")

    db_utils.init_db()

    with test_engine.connect() as conn:
        rows = conn.execute(text("SELECT name FROM categories")).fetchall()
        assert rows == [("Python",)]  # var olan veri korunmus
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        assert version is not None

    tables = set(inspect(test_engine).get_table_names())
    assert _APP_TABLES <= tables


def test_init_db_is_idempotent(tmp_path, monkeypatch):
    db_path = tmp_path / "repeat.db"
    test_engine = create_engine(f"sqlite:///{db_path}")
    monkeypatch.setattr(db_utils, "engine", test_engine)
    monkeypatch.setattr(db_utils.settings, "DATABASE_URL", f"sqlite:///{db_path}")

    db_utils.init_db()
    db_utils.init_db()  # ikinci cagri hata vermemeli

    tables = set(inspect(test_engine).get_table_names())
    assert _APP_TABLES <= tables
