from contextlib import contextmanager

from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import qtawesome as qta

from core.constants.colors import Colors
from core.constants.icons import QtAwesomeIcons
from core.constants.status import status_label
from core.constants.strings import AppStrings
from core.events import event_bus
from models import Resource, ResourceStatus
from ui.theme_utils import resolve_theme_color
from utils.url_utils import format_display_url


@contextmanager
def _signals_blocked(widget):
    widget.blockSignals(True)
    try:
        yield
    finally:
        widget.blockSignals(False)


class ResourceDetailPanel(QWidget):
    """Kaynak detay/duzenleme paneli (stack icindeki 'view' sayfasi)."""

    close_requested = Signal()
    status_updated = Signal(int, object)
    content_updated = Signal(int, str)
    edit_requested = Signal(int)
    delete_requested = Signal(int)
    read_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._resource_id: int | None = None
        self._delete_confirm: bool = False

        self._build_ui()
        self._connect_signals()
        event_bus.theme_changed.connect(self._on_theme_changed)

    # ------------------------------------------------------------------ #
    # Kurulum
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        root.addLayout(self._build_header())
        self._build_url_button(root)
        root.addLayout(self._build_status_row())
        self._build_notes_area(root)
        root.addLayout(self._build_action_row())
        self._build_delete_confirm_button(root)

    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        self._title_label = QLabel("—")
        self._title_label.setObjectName("DetailTitle")
        self._title_label.setWordWrap(True)
        header.addWidget(self._title_label, stretch=1)

        self._close_btn = QPushButton()
        self._close_btn.setObjectName("DetailCloseButton")
        self._close_btn.setFixedSize(28, 28)
        self._close_btn.setIcon(
            qta.icon(QtAwesomeIcons.CLOSE, color=resolve_theme_color(None, Colors.ICON))
        )
        self._close_btn.setToolTip(AppStrings.CLOSE_PANEL)
        header.addWidget(self._close_btn)
        return header

    def _build_url_button(self, root: QVBoxLayout) -> None:
        self._url_btn = QPushButton()
        self._url_btn.setObjectName("DetailUrlButton")
        self._url_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._url_btn.setIcon(
            qta.icon(QtAwesomeIcons.OPEN_BROWSER, color=resolve_theme_color(None, Colors.ACCENT))
        )
        self._url_btn.hide()
        root.addWidget(self._url_btn, alignment=Qt.AlignmentFlag.AlignLeft)

    def _build_status_row(self) -> QHBoxLayout:
        status_row = QHBoxLayout()
        status_row.addWidget(QLabel(AppStrings.STATUS_LABEL))
        self._status_combo = QComboBox()
        self._status_combo.setObjectName("StatusCombo")
        for s in ResourceStatus:
            self._status_combo.addItem(status_label(s), s)
        status_row.addWidget(self._status_combo, stretch=1)
        return status_row

    def _build_notes_area(self, root: QVBoxLayout) -> None:
        self._notes_edit = QTextEdit()
        self._notes_edit.setObjectName("NotesEdit")
        self._notes_edit.setPlaceholderText("Notlar (Markdown destekli)...")
        root.addWidget(self._notes_edit, stretch=1)

        self._save_notes_btn = QPushButton(AppStrings.SAVE_NOTES)
        self._save_notes_btn.setObjectName("SaveNotesButton")
        root.addWidget(self._save_notes_btn)

    def _build_action_row(self) -> QHBoxLayout:
        action_row = QHBoxLayout()
        self._read_btn = QPushButton(AppStrings.READ_RESOURCE)
        self._read_btn.setObjectName("ReadResourceButton")
        self._edit_btn = QPushButton(AppStrings.EDIT_RESOURCE)
        self._edit_btn.setObjectName("EditResourceButton")
        self._delete_btn = QPushButton(AppStrings.DELETE_RESOURCE)
        self._delete_btn.setObjectName("DeleteResourceButton")
        action_row.addWidget(self._read_btn)
        action_row.addWidget(self._edit_btn)
        action_row.addWidget(self._delete_btn)
        return action_row

    def _build_delete_confirm_button(self, root: QVBoxLayout) -> None:
        self._delete_confirm_btn = QPushButton(AppStrings.CONFIRM_DELETE_RESOURCE)
        self._delete_confirm_btn.setObjectName("DeleteResourceConfirmButton")
        self._delete_confirm_btn.hide()
        root.addWidget(self._delete_confirm_btn)

    def _connect_signals(self) -> None:
        self._close_btn.clicked.connect(self.close_requested)
        self._url_btn.clicked.connect(self._open_url)
        self._status_combo.currentIndexChanged.connect(self._on_status_changed)
        self._save_notes_btn.clicked.connect(self._on_save_notes)
        self._read_btn.clicked.connect(self._on_read_clicked)
        self._edit_btn.clicked.connect(self._on_edit_clicked)
        self._delete_btn.clicked.connect(self._on_delete_first_click)
        self._delete_confirm_btn.clicked.connect(self._on_delete_confirmed)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def load_resource(self, resource: Resource) -> None:
        self._resource_id = resource.id
        self._reset_delete_confirm()

        self._title_label.setText(resource.title)

        if resource.url:
            self._url_btn.setText(format_display_url(resource.url))
            self._url_btn.setToolTip(resource.url)
            self._url_btn.setProperty("url", resource.url)
            self._url_btn.show()
        else:
            self._url_btn.hide()

        index = self._status_combo.findData(resource.status)
        if index >= 0:
            with _signals_blocked(self._status_combo):
                self._status_combo.setCurrentIndex(index)

        self._notes_edit.setPlainText(resource.content or "")

    def current_resource_id(self) -> int | None:
        return self._resource_id

    def reset(self) -> None:
        self._resource_id = None
        self._reset_delete_confirm()

    # ------------------------------------------------------------------ #
    # Slot'lar
    # ------------------------------------------------------------------ #

    def _reset_delete_confirm(self) -> None:
        self._delete_confirm = False
        self._delete_confirm_btn.hide()
        self._delete_btn.show()
        self._delete_btn.setText(AppStrings.DELETE_RESOURCE)
        self._delete_btn.setObjectName("DeleteResourceButton")
        self._delete_btn.style().unpolish(self._delete_btn)
        self._delete_btn.style().polish(self._delete_btn)

    def _open_url(self) -> None:
        url = self._url_btn.property("url")
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def _on_status_changed(self) -> None:
        if self._resource_id is not None:
            status: ResourceStatus = self._status_combo.currentData()
            self.status_updated.emit(self._resource_id, status)

    def _on_save_notes(self) -> None:
        if self._resource_id is not None:
            text = self._notes_edit.toPlainText()
            self.content_updated.emit(self._resource_id, text)

    def _on_read_clicked(self) -> None:
        if self._resource_id is not None:
            self.read_requested.emit(self._resource_id)

    def _on_edit_clicked(self) -> None:
        if self._resource_id is not None:
            self.edit_requested.emit(self._resource_id)

    def _on_delete_first_click(self) -> None:
        self._delete_confirm = True
        self._delete_confirm_btn.show()
        self._delete_btn.hide()

    def _on_delete_confirmed(self) -> None:
        if self._resource_id is not None:
            self.delete_requested.emit(self._resource_id)

    def _on_theme_changed(self, theme_data: dict) -> None:
        color = resolve_theme_color(theme_data, Colors.ICON)
        self._close_btn.setIcon(qta.icon(QtAwesomeIcons.CLOSE, color=color))
        accent = resolve_theme_color(theme_data, Colors.ACCENT)
        self._url_btn.setIcon(qta.icon(QtAwesomeIcons.OPEN_BROWSER, color=accent))
