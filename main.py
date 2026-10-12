import sys
from pathlib import Path

# Dev modunda proje kökünü sys.path'e ekle. Frozen exe'de PyInstaller
# bundle'ı kendi çözer, ek yol enjeksiyonu hatalı path'lere yol açabilir.
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtCore import QThreadPool, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from core.logger import log
from core.paths import pdf_storage_dir
from core.single_instance import SingleInstance, default_name, send_message
from services.pdf_storage_service import PdfStorageService
from ui_qml.bridge import QmlBridge
from ui_qml.context import Controllers
from ui_qml.deep_links import ACTIVATE_MESSAGE, extract_link_arg
from ui_qml.image_provider import IconImageProvider
from utils.db_utils import get_session, init_db, snapshot_database_daily


def _install_global_exception_hook() -> None:
    """Son çare güvenlik ağı: `PKMBaseError` dışındaki, servis/controller
    katmanının hiç beklemediği bir hata (örn. gerçek bir programlama hatası)
    olursa PySide6 bunu sessizce stderr'e yazıp yutuyordu -- artık tam
    traceback ile `app.log`'a da düşüyor, konsol gürültüsü kuralı bozulmadan
    (core/logger.py: konsol sadece WARNING+, dosya her şeyi tutuyor)."""

    def _hook(exc_type, exc_value, exc_tb) -> None:
        log.critical("Yakalanmamis/beklenmeyen hata:", exc_info=(exc_type, exc_value, exc_tb))
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook


def _create_application() -> QGuiApplication:
    # Native (Windows) stil ComboBox/Popup gibi kontrollerin background/contentItem
    # ozellestirmesini yok sayip OS'un kendi acik renkli dropdown'unu gosteriyordu
    # (koyu temayla cakisiyordu). Basic stil tum ozellestirmeleri uyguluyor.
    QQuickStyle.setStyle("Basic")

    app = QGuiApplication(sys.argv)
    app.setApplicationName("PKM")
    app.setOrganizationName("PKM")
    return app


def _create_engine(bridge: QmlBridge) -> QQmlApplicationEngine:
    """QML motorunu kurar ve `main.qml`'i yukler (ikon saglayici, import yolu, `bridge` context'i)."""
    engine = QQmlApplicationEngine()
    engine.addImageProvider("icon", IconImageProvider())  # qtawesome: image://icon/...

    qml_dir = Path(__file__).resolve().parent / "qml"
    engine.addImportPath(str(qml_dir))
    engine.rootContext().setContextProperty("bridge", bridge)
    engine.load(str(qml_dir / "main.qml"))
    return engine


def main() -> None:
    _install_global_exception_hook()
    app = _create_application()
    log.info("Uygulama baslatiliyor (QML Arayuzu)...")

    # Tek ornek: ikinci baslatma (ornegin Obsidian'daki bir pkm:// baglantisi) calisan ornege iletilip kapanir; bu ayni
    # SQLite dosyasinin iki surecte birlikte acilmasini da onler.
    link = extract_link_arg(sys.argv)
    if send_message(default_name(), link or ACTIVATE_MESSAGE):
        log.info("Uygulama zaten calisiyor; istek calisan ornege iletildi.")
        sys.exit(0)
    instance = SingleInstance()
    if not instance.listen():
        log.warning("Tek ornek sunucusu baslatilamadi: %s", instance.name)

    init_db()
    snapshot_database_daily()
    session = get_session()
    controllers = Controllers.build(session)
    # Onceki oturumda Windows dosya kilidi yuzunden silinememis PDF'leri temizle.
    PdfStorageService(pdf_storage_dir()).sweep_orphans(controllers.resources.load_resources_with_filters({}))
    bridge = QmlBridge(controllers=controllers)
    engine = _create_engine(bridge)

    # Yok etme sirasi onemli (motor -> bridge -> oturum), bu yuzden `del`ler burada, helper'da degil.
    if not engine.rootObjects():
        log.error("QML ana penceresi yuklenemedi!")
        del engine
        del bridge
        session.close()
        sys.exit(-1)

    log.info("QML Arayuzu basariyla calisiyor.")
    instance.messageReceived.connect(bridge.deep_links.handle_message)
    bridge.run_startup_tasks()
    if link:  # uygulama bir pkm:// baglantisiyla acildi: pencere ve veri hazir olduktan sonra ac
        QTimer.singleShot(0, lambda: bridge.deep_links.open_link(link))
    exit_code = app.exec()
    instance.close()

    # Pencere kapanirken hala calisan bir arka plan worker'i (scrape/extract/
    # market-search) varsa, onu bitene kadar bekle -- aksi halde worker daha
    # sonra artik yok edilmis bridge'e sinyal atmaya calisip "Internal C++
    # object already deleted" hatasi/kararsizligina yol acabiliyordu.
    QThreadPool.globalInstance().waitForDone(5000)

    del engine
    del bridge
    session.close()
    log.info("Uygulama kapatildi.")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
