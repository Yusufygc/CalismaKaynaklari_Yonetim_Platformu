import sys
from pathlib import Path

# Dev modunda proje kökünü sys.path'e ekle. Frozen exe'de PyInstaller
# bundle'ı kendi çözer, ek yol enjeksiyonu hatalı path'lere yol açabilir.
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from controllers.main_controller import MainController
from core.logger import log
from ui_qml.bridge import QmlBridge
from ui_qml.image_provider import IconImageProvider
from utils.db_utils import get_session, init_db


def main() -> None:
    app = QGuiApplication(sys.argv)
    app.setApplicationName("PKM")
    app.setOrganizationName("PKM")

    log.info("Uygulama baslatiliyor (QML Arayuzu)...")

    init_db()

    session = get_session()
    controller = MainController(session)
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

    del engine
    del bridge
    session.close()
    log.info("Uygulama kapatildi.")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
