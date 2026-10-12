"""`pkm://open?...` derin baglantilari: komut satiri ayrıştırma ve baglantiyi uygulamada acma.

Baglanti disaridan gelir (Obsidian, tarayici, ikinci uygulama ornegi): `pdfkit.domain.deeplink` her seyi dogrular;
bu modul yalniz dogrulanmis baglantiyi kutuphanedeki belgeye cevirip okuyucuyu acar. Dosya yolu ya da komut
calistirmaz; bilinmeyen belgede hicbir sey acmaz."""
from collections.abc import Sequence

from PySide6.QtCore import QObject, Signal

from core.logger import log
from pdfkit.api import InvalidLinkError, parse_open_link
from ui_qml.context import BridgeContext

ACTIVATE_MESSAGE = "activate"
_SCHEME_PREFIX = "pkm:"


def extract_link_arg(argv: Sequence[str]) -> str | None:
    """Komut satirindan baglantiyi cikarir: `--open <url>`, `--open=<url>` ya da dogrudan `pkm://...` (Windows kaydi
    uygulamayi `"%1"` ile cagirir). Baska argumanlar yok sayilir."""
    args = list(argv)[1:]
    for index, arg in enumerate(args):
        if arg == "--open" and index + 1 < len(args):
            return args[index + 1]
        if arg.startswith("--open="):
            return arg[len("--open="):]
        if arg.lower().startswith(_SCHEME_PREFIX):
            return arg
    return None


class DeepLinkRouter(QObject):
    """Baglantiyi (ya da ikinci ornekten gelen mesaji) isler: belgeyi bulur, okuyucuyu acar, sayfa/alintiya atlar."""

    activationRequested = Signal()  # pencere one getirilsin

    def __init__(self, bridge, ctx: BridgeContext, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._bridge = bridge
        self._ctx = ctx

    def handle_message(self, message: str) -> bool:
        """Ikinci ornekten gelen mesaj: `activate` ya da bir `pkm://` baglantisi."""
        if message == ACTIVATE_MESSAGE:
            self.activationRequested.emit()
            return True
        return self.open_link(message)

    def open_link(self, url: str) -> bool:
        try:
            link = parse_open_link(url)
        except InvalidLinkError as exc:
            log.warning("Gecersiz derin baglanti reddedildi: %s", exc)
            self._ctx.notify.error("Bağlantı geçersiz: açılamadı.")
            return False
        documents = self._ctx.pdf_library.documents()
        document = documents.find_by_sha_prefix(link.doc)
        resource_ids = documents.resources_with_document(document.id) if document else []
        if document is None or not resource_ids:
            self._ctx.notify.error("Bağlantıdaki PDF kütüphanende bulunamadı.")
            return False
        resource_id = min(resource_ids)
        # Atlama hedefi okuyucu acilmadan ONCE kaydedilir: okuyucu acilinca (ayni turda) belge yuklenir ve hedef cozulur.
        self._bridge.pdf.requestJump(resource_id, -1 if link.page is None else link.page, link.ann or "")
        self._bridge.reader.openReader(resource_id)
        self.activationRequested.emit()
        log.info("Derin baglanti acildi: kaynak=%d sayfa=%s alinti=%s", resource_id, link.page, link.ann or "-")
        return True
