import os

import pytest
from PySide6.QtWidgets import QApplication
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import pdfkit.infra.orm  # noqa: F401  (pdf_* tablolari Base.metadata'ya kayitli olsun)
from models import Base
from utils.db_utils import register_sqlite_functions

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# main.py de Basic stilini kullanir; ozellestirilebilir stil olmadan QML uyari basar.
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")


@pytest.fixture(autouse=True)
def _isolated_user_settings(tmp_path, monkeypatch):
    """Testler gercek kullanici ayarlarini (ornegin gercek Obsidian vault klasorunu) okumasin ya da yazmasin."""
    monkeypatch.setattr("ui_qml.context.default_settings_path", lambda: tmp_path / "user_settings.json")


@pytest.fixture(autouse=True)
def _no_auto_indexing(monkeypatch):
    """Testlerde PDF'ler kendiliginden tam metin dizinine alinmaz (arka plan isi testi bitince de surerdi); dizin
    testleri `TextIndexer`i dogrudan kullanir."""
    monkeypatch.setattr("ui_qml.context.AUTO_INDEX", False)


@pytest.fixture(autouse=True)
def _no_real_registry(monkeypatch):
    """Testler gercek Windows kayit defterine (pkm:// protokol kaydi) dokunmasin: `winreg` yok sayilir; kayit
    testleri sahte bir kayit defteri verir."""
    monkeypatch.setattr("core.protocol_registration._winreg", lambda: None)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    return app


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    register_sqlite_functions(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db_session = Session()
    try:
        yield db_session
    finally:
        db_session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()
