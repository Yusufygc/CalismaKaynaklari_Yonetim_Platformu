from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QStackedWidget, QVBoxLayout, QWidget

from models import Resource
from ui.components.empty_detail import EmptyDetail
from ui.components.resource_detail_panel import ResourceDetailPanel
from ui.components.resource_form import ResourceForm

_PAGE_EMPTY = 0
_PAGE_VIEW = 1
_PAGE_FORM = 2


class DetailView(QFrame):
    """Sag panel koordinatoru: bos / detay / form sayfalari arasinda gecisi yonetir.

    Alt panellerin (ResourceDetailPanel, ResourceForm) sinyallerini disariya ayni
    isimle relay eder; MainWindow tarafindaki cagiranlar etkilenmez.
    """

    status_updated = Signal(int, object)
    content_updated = Signal(int, str)
    form_submitted = Signal(dict)
    edit_requested = Signal(int)
    delete_requested = Signal(int)
    read_requested = Signal(int)
    category_create_requested = Signal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("DetailView")
        self.setMinimumWidth(280)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget()
        root.addWidget(self._stack)

        self._empty_page = EmptyDetail()
        self._view_page = ResourceDetailPanel()
        self._form_page = ResourceForm()

        self._stack.addWidget(self._empty_page)   # _PAGE_EMPTY
        self._stack.addWidget(self._view_page)    # _PAGE_VIEW
        self._stack.addWidget(self._form_page)    # _PAGE_FORM

        self._wire_signals()
        self.hide()

    # ------------------------------------------------------------------ #
    # Sinyal relay
    # ------------------------------------------------------------------ #

    def _wire_signals(self) -> None:
        self._view_page.close_requested.connect(self.clear)
        self._view_page.status_updated.connect(self.status_updated)
        self._view_page.content_updated.connect(self.content_updated)
        self._view_page.edit_requested.connect(self.edit_requested)
        self._view_page.delete_requested.connect(self.delete_requested)
        self._view_page.read_requested.connect(self.read_requested)

        self._form_page.submitted.connect(self.form_submitted)
        self._form_page.cancelled.connect(self.clear)
        self._form_page.category_create_requested.connect(self.category_create_requested)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def load_resource(self, resource: Resource) -> None:
        self._view_page.load_resource(resource)
        self._stack.setCurrentIndex(_PAGE_VIEW)
        self.show()

    def show_form(self, categories: list) -> None:
        self._form_page.reset_for_new()
        self._form_page.load_categories(categories)
        self._stack.setCurrentIndex(_PAGE_FORM)
        self.show()

    def show_form_edit(self, resource: Resource, categories: list) -> None:
        self._form_page.load_resource(resource, categories)
        self._stack.setCurrentIndex(_PAGE_FORM)
        self.show()

    def clear(self) -> None:
        self._view_page.reset()
        self._stack.setCurrentIndex(_PAGE_EMPTY)
        self.hide()

    def current_resource_id(self) -> int | None:
        return self._view_page.current_resource_id()

    def set_categories(self, categories: list, select_id: int | None = None) -> None:
        self._form_page.set_categories(categories, select_id)
