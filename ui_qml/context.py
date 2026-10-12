"""Alt-bridge'lerin paylastigi baglam: controller'lar, is parcacigi havuzu, bildirim kanali ve ortak yardimcilar.

Composition root `QmlBridge`'dir (bkz. ui_qml/bridge.py); bagimliliklar buradan `__init__` uzerinden
verilir (DI). Testler `ctx.thread_pool`'u senkron havuzla degistirebilir.
"""
from dataclasses import dataclass

from PySide6.QtCore import QThreadPool
from sqlalchemy.orm import Session

from controllers.category_controller import CategoryController
from controllers.highlight_controller import HighlightController
from controllers.pdf_note_controller import PdfNoteController
from controllers.resource_controller import ResourceController
from controllers.saved_search_controller import SavedSearchController
from controllers.tag_controller import TagController
from controllers.vocabulary_controller import VocabularyController
from core.events import event_bus
from core.user_settings import UserSettings, default_settings_path
from pdfkit.api import PdfLibrary, VaultSync
from services.library_index import LibraryIndex
from services.pdf_download_service import stream_fetch
from ui_qml.full_text import FullTextExtractor
from ui_qml.notifier import Notifier
from ui_qml.pdf_catalog import ResourceCatalog
from ui_qml.pdf_files import PdfFileManager
from ui_qml.serializers import ResourceSerializer


@dataclass
class Controllers:
    """UI sinirindaki controller'lar (eski `MainController` facade'inin yerine dogrudan enjekte edilir)."""

    resources: ResourceController
    categories: CategoryController
    tags: TagController
    highlights: HighlightController
    vocabulary: VocabularyController
    pdf_notes: PdfNoteController
    saved_searches: SavedSearchController
    session: Session

    @classmethod
    def build(cls, session: Session) -> "Controllers":
        return cls(
            resources=ResourceController(session),
            categories=CategoryController(session),
            tags=TagController(session),
            highlights=HighlightController(session),
            vocabulary=VocabularyController(session),
            pdf_notes=PdfNoteController(session),
            saved_searches=SavedSearchController(session),
            session=session,
        )


class LibraryIndexCache:
    """Kutuphane indeksi (DOI / OpenAlex kimligi -> kaynak) onbellegi: kaynaklar degisince (olaylar
    ya da acik `invalidate`) gecersiz kilinir; boylece her arama/kayit tum kaynaklari yeniden cekmez."""

    def __init__(self, resources: ResourceController) -> None:
        self._resources = resources
        self._index: LibraryIndex | None = None
        for signal in (event_bus.resource_added, event_bus.resource_updated, event_bus.resource_deleted):
            signal.connect(self._on_resource_event)

    def _on_resource_event(self, _resource_id: int) -> None:
        self.invalidate()

    def invalidate(self) -> None:
        self._index = None

    def get(self) -> LibraryIndex:
        if self._index is None:
            self._index = LibraryIndex(self._resources.load_resources_with_filters({}))
        return self._index


class BridgeContext:
    def __init__(
        self,
        controllers: Controllers,
        thread_pool: QThreadPool | None = None,
        notifier: Notifier | None = None,
        user_settings: UserSettings | None = None,
    ) -> None:
        self.controllers = controllers
        self.user_settings = user_settings or UserSettings(default_settings_path())
        self.thread_pool = thread_pool or QThreadPool.globalInstance()
        self.notify = notifier or Notifier()
        self.pdf_files = PdfFileManager(self)
        self.pdf_library = PdfLibrary(
            controllers.session,
            storage_dir=self.pdf_files.storage_dir,
            catalog=ResourceCatalog(controllers.resources),
            thread_pool=lambda: self.thread_pool,  # testler havuzu sonradan degistirebilir
            fetch=stream_fetch,
        )
        self.pdf_library.downloadFinished.connect(self.pdf_files.on_download_finished)
        self.vault_sync = VaultSync(self.pdf_library, thread_pool=lambda: self.thread_pool)
        self.extractor = FullTextExtractor(self)
        self.library_index = LibraryIndexCache(controllers.resources)
        self.serializer = ResourceSerializer(self.pdf_files, self.pdf_library)
