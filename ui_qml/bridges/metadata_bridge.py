from PySide6.QtCore import Property, QObject, Signal, Slot

from ui_qml.context import SETTING_AUTO_METADATA, BridgeContext


class MetadataBridge(QObject):
    """Ayarlar > Kunye: yeni eklenen PDF'in kunyesinin (yazar, yil, dergi, OpenAlex kimligi) OpenAlex'ten otomatik
    doldurulup doldurulmayacagi. **Varsayilan ACIK** (ozellik zaten boyleydi; kapatmak istegin onune gecen bir
    gizlilik secenegidir): acikken PDF'ten cikarilan DOI `openalex.org`'a gonderilir, baska hicbir sey.

    Doldurmanin kendisi `PdfImporter`dadir (`ui_qml/importers.py`): yalniz bos alanlari doldurur ve DOI PDF'in kendi
    gomulu basligiyla celisen bir makaleye aitse hicbir sey yazmaz (bkz. `services/metadata_autofill.py`)."""

    autoFillChanged = Signal()

    def __init__(self, ctx: BridgeContext, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx

    @Property(bool, notify=autoFillChanged)
    def autoFill(self) -> bool:
        return self._ctx.auto_metadata_enabled()

    @Slot(bool)
    def setAutoFill(self, enabled: bool) -> None:
        if not self._ctx.user_settings.set(SETTING_AUTO_METADATA, bool(enabled)):
            self._ctx.notify.error("Ayar kaydedilemedi.")
            return
        self.autoFillChanged.emit()
