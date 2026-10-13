"""Alembic zinciri ile pdfkit ORM semasinin ayni oldugunu sinar (elle yazilmis migration'larin kayma riski)."""
import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

import pdfkit.infra.orm  # noqa: F401
from core.paths import resource_path
from models.base import Base
from pdfkit.infra.search_schema import include_object


@pytest.fixture()
def migrated_engine(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'migrated.db').as_posix()}"
    monkeypatch.setattr("core.config.settings.DATABASE_URL", url)
    cfg = Config(str(resource_path("alembic.ini")))
    cfg.set_main_option("script_location", str(resource_path("migrations")))
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")
    return create_engine(url), cfg


def test_pdfkit_tables_match_the_orm_after_upgrade_to_head(migrated_engine):
    engine, _cfg = migrated_engine
    with engine.connect() as connection:
        diffs = compare_metadata(MigrationContext.configure(connection, opts={"include_object": include_object}), Base.metadata)

    pdf_diffs = [d for d in diffs if "pdf_" in repr(d) and "pdf_notes" not in repr(d)]
    assert pdf_diffs == []


def test_downgrade_removes_the_new_tables_and_upgrade_restores_them(migrated_engine):
    engine, cfg = migrated_engine
    command.downgrade(cfg, "b3a91c5d7e20")
    with engine.connect() as connection:
        tables = set(inspect(connection).get_table_names())
    assert {"pdf_annotations", "pdf_page_notes", "pdf_terms"}.isdisjoint(tables) and "pdf_documents" in tables

    command.upgrade(cfg, "head")
    with engine.connect() as connection:
        assert "pdf_annotations" in set(inspect(connection).get_table_names())


def test_the_full_text_index_table_is_created_by_the_migration_and_removed_by_the_downgrade(migrated_engine):
    engine, cfg = migrated_engine
    with engine.connect() as connection:
        tables = set(inspect(connection).get_table_names())
        assert {"pdf_text_index", "pdf_page_fts"} <= tables
        connection.exec_driver_sql("INSERT INTO pdf_page_fts(rowid, folded, original) VALUES (10001, 'kuantum', 'Kuantum')")
        assert connection.exec_driver_sql("SELECT rowid FROM pdf_page_fts WHERE pdf_page_fts MATCH 'kuant*'").scalar() == 10001

    command.downgrade(cfg, "a5d1e7c3b920")
    with engine.connect() as connection:
        tables = set(inspect(connection).get_table_names())
    assert "pdf_text_index" not in tables and not any(t.startswith("pdf_page_fts") for t in tables)

    command.upgrade(cfg, "head")
    with engine.connect() as connection:
        assert {"pdf_text_index", "pdf_page_fts"} <= set(inspect(connection).get_table_names())
