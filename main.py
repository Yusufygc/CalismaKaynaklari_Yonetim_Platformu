import sys
from pathlib import Path

# Dev modunda proje kökünü sys.path'e ekle. Frozen exe'de PyInstaller
# bundle'ı kendi çözer, ek yol enjeksiyonu hatalı path'lere yol açabilir.
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtCore import QThreadPool
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from controllers.main_controller import MainController
from core.logger import log
from core.paths import pdf_storage_dir
from services.pdf_storage_service import PdfStorageService
from ui_qml.bridge import QmlBridge
from ui_qml.image_provider import IconImageProvider
from utils.db_utils import get_session, init_db


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


def main() -> None:
    _install_global_exception_hook()

    # Native (Windows) stil ComboBox/Popup gibi kontrollerin background/contentItem
    # ozellestirmesini yok sayip OS'un kendi acik renkli dropdown'unu gosteriyordu
    # (koyu temayla cakisiyordu). Basic stil tum ozellestirmeleri uyguluyor.
    QQuickStyle.setStyle("Basic")

    app = QGuiApplication(sys.argv)
    app.setApplicationName("PKM")
    app.setOrganizationName("PKM")

    log.info("Uygulama baslatiliyor (QML Arayuzu)...")

    init_db()

    session = get_session()
    controller = MainController(session)
    # Onceki oturumda Windows dosya kilidi yuzunden silinememis PDF'leri temizle.
    PdfStorageService(pdf_storage_dir()).sweep_orphans(controller.load_resources_with_filters({}))
    bridge = QmlBridge(controller=controller)

    engine = QQmlApplicationEngine()

    # qtawesome ikon sağlayıcısını kaydet (image://icon/...)
    engine.addImageProvider("icon", IconImageProvider())

    # QML import dizinlerini ekle
    qml_dir = Path(__file__).resolve().parent / "qml"
    engine.addImportPath(str(qml_dir))

    # Python Bridge nesnesini QML context'ine ata
    engine.rootContext().setContextProperty("bridge", bridge)

    main_qml_path = qml_dir / "main.qml"
    engine.load(str(main_qml_path))

    if not engine.rootObjects():
        log.error("QML ana penceresi yuklenemedi!")
        del engine
        del bridge
        session.close()
        sys.exit(-1)

    log.info("QML Arayuzu basariyla calisiyor.")
    exit_code = app.exec()

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
