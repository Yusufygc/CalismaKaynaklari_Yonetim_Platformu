import markdown
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QTextCharFormat
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.constants.colors import Colors
from core.constants.icons import QtAwesomeIcons
from core.constants.strings import AppStrings
from core.events import event_bus
from models import Resource
from ui.components.icon_action_button import IconActionButton
from ui.theme_utils import resolve_theme_color


class _SelectionToolbar(QFrame):
    """Metin secilince beliren Kindle-tarzi yuzen mini toolbar (top-level degil, child widget)."""

    highlight_clicked = Signal()
    vocabulary_clicked = Signal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("SelectionToolbar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        highlight_btn = QPushButton(AppStrings.READER_HIGHLIGHT_ACTION)
        highlight_btn.setObjectName("SelectionToolbarButton")
        highlight_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        highlight_btn.clicked.connect(self.highlight_clicked)
        layout.addWidget(highlight_btn)

        vocab_btn = QPushButton(AppStrings.READER_VOCAB_ACTION)
        vocab_btn.setObjectName("SelectionToolbarButton")
        vocab_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        vocab_btn.clicked.connect(self.vocabulary_clicked)
        layout.addWidget(vocab_btn)

        self.hide()
        self.adjustSize()


class _VocabPopover(QFrame):
    """Secili kelime icin ceviri giren kucuk inline panel (QDialog degil, child widget)."""

    confirmed = Signal(str, str)  # word, translation
    cancelled = Signal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("VocabPopover")
        self._word = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self._word_label = QLabel()
        self._word_label.setObjectName("VocabPopoverLabel")
        layout.addWidget(self._word_label)

        self._translation_input = QLineEdit()
        self._translation_input.setObjectName("FormField")
        self._translation_input.setPlaceholderText(AppStrings.READER_VOCAB_TRANSLATION_PLACEHOLDER)
        self._translation_input.returnPressed.connect(self._on_confirm)
        layout.addWidget(self._translation_input)

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton(AppStrings.CANCEL)
        cancel_btn.setObjectName("CancelButton")
        cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(cancel_btn)
        save_btn = QPushButton(AppStrings.SAVE)
        save_btn.setObjectName("SaveButton")
        save_btn.clicked.connect(self._on_confirm)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        self.hide()

    def open_for(self, word: str) -> None:
        self._word = word
        self._word_label.setText(word)
        self._translation_input.clear()
        self.show()
        self.adjustSize()
        self._translation_input.setFocus()

    def _on_confirm(self) -> None:
        translation = self._translation_input.text().strip()
        if not translation:
            return
        self.confirmed.emit(self._word, translation)
        self.hide()

    def _on_cancel(self) -> None:
        self.hide()
        self.cancelled.emit()


class ReaderView(QWidget):
    """Kaynagin tam metnini (URL'den cikarilmis veya kullanicinin kendi notu)
    goruntuleyen okuyucu sayfasi. Metin secilince Kindle-tarzi bir toolbar
    beliriyor -- secilen pasaj alinti, secilen kelime ceviri istenerek
    kelime dagarcigina kaydediliyor.

    Bilinen sinirlama: mevcut alintilar `QTextDocument.find()` ile ariniyor;
    ayni alt-dizinin metinde birden fazla gectigi durumda sadece ilk eslesme
    vurgulanir (offset kolonu yok, bu turda kapsam disi).
    """

    back_requested = Signal()
    highlight_save_requested = Signal(int, str)          # resource_id, content
    vocabulary_save_requested = Signal(int, str, str)     # resource_id, word, translation

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ReaderView")
        self._resource_id: int | None = None
        self._theme_data: dict | None = None
        self._build_ui()
        event_bus.theme_changed.connect(self._on_theme_changed)

    # ------------------------------------------------------------------ #
    # Kurulum
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        top_bar = QFrame()
        top_bar.setObjectName("ReaderTopBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(12, 10, 12, 10)
        top_layout.setSpacing(10)

        self._back_btn = IconActionButton(
            QtAwesomeIcons.BACK, Colors.ICON, AppStrings.READER_BACK, "ReaderBackButton"
        )
        self._back_btn.clicked.connect(self.back_requested)
        top_layout.addWidget(self._back_btn)

        self._title_label = QLabel("—")
        self._title_label.setObjectName("ReaderTitleLabel")
        self._title_label.setWordWrap(True)
        top_layout.addWidget(self._title_label, stretch=1)

        root.addWidget(top_bar)

        self._text_edit = QTextEdit()
        self._text_edit.setObjectName("ReaderTextEdit")
        self._text_edit.setReadOnly(True)
        self._text_edit.selectionChanged.connect(self._on_selection_changed)
        root.addWidget(self._text_edit, stretch=1)

        self._toolbar = _SelectionToolbar(self)
        self._toolbar.highlight_clicked.connect(self._on_save_highlight_clicked)
        self._toolbar.vocabulary_clicked.connect(self._on_save_vocab_clicked)

        self._popover = _VocabPopover(self)
        self._popover.confirmed.connect(self._on_vocab_confirmed)
        self._popover.cancelled.connect(self._toolbar.hide)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def load_resource(self, resource: Resource) -> None:
        self._resource_id = resource.id
        self._title_label.setText(resource.title)
        self._toolbar.hide()
        self._popover.hide()
        self._render_text(resource.full_text, resource.content)
        self._apply_existing_highlights(resource)

    def set_full_text(self, text: str) -> None:
        self._text_edit.setPlainText(text or "")

    def current_resource_id(self) -> int | None:
        return self._resource_id

    # ------------------------------------------------------------------ #
    # Icerik render
    # ------------------------------------------------------------------ #

    def _render_text(self, full_text: str | None, content: str | None) -> None:
        if full_text:
            # Trafilatura ciktisi duz metin -- Markdown parse etme (dogal "#"/"*"
            # karakterleri, orn. "C#" bozulmasin).
            self._text_edit.setPlainText(full_text)
        elif content:
            # Kullanicinin kendi notu -- mevcut "Markdown destekli" konvansiyonu.
            self._text_edit.setHtml(markdown.markdown(content))
        else:
            self._text_edit.setPlainText(AppStrings.READER_EMPTY_MSG)

    def _apply_existing_highlights(self, resource: Resource) -> None:
        default_color = resolve_theme_color(self._theme_data, Colors.HIGHLIGHT_COLOR)
        document = self._text_edit.document()
        for highlight in resource.highlights:
            cursor = document.find(highlight.content)
            if cursor.isNull():
                continue
            fmt = QTextCharFormat()
            fmt.setBackground(QColor(highlight.color or default_color))
            cursor.mergeCharFormat(fmt)

    # ------------------------------------------------------------------ #
    # Secim -> toolbar
    # ------------------------------------------------------------------ #

    def _on_selection_changed(self) -> None:
        cursor = self._text_edit.textCursor()
        selected = cursor.selectedText().strip()
        if not selected:
            self._toolbar.hide()
            return

        rect = self._text_edit.cursorRect(cursor)
        pos = self._text_edit.viewport().mapTo(self, rect.bottomLeft())
        self._toolbar.move(pos.x(), pos.y() + 4)
        self._toolbar.raise_()
        self._toolbar.show()

    def _on_save_highlight_clicked(self) -> None:
        if self._resource_id is None:
            return
        content = self._text_edit.textCursor().selectedText().strip()
        if not content:
            return
        self.highlight_save_requested.emit(self._resource_id, content)
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(resolve_theme_color(self._theme_data, Colors.HIGHLIGHT_COLOR)))
        self._text_edit.textCursor().mergeCharFormat(fmt)
        self._toolbar.hide()

    def _on_save_vocab_clicked(self) -> None:
        word = self._text_edit.textCursor().selectedText().strip()
        if not word:
            return
        pos = self._toolbar.pos()
        self._toolbar.hide()
        self._popover.move(pos)
        self._popover.raise_()
        self._popover.open_for(word)

    def _on_vocab_confirmed(self, word: str, translation: str) -> None:
        if self._resource_id is None:
            return
        self.vocabulary_save_requested.emit(self._resource_id, word, translation)

    # ------------------------------------------------------------------ #
    # Tema
    # ------------------------------------------------------------------ #

    def _on_theme_changed(self, theme_data: dict) -> None:
        self._theme_data = theme_data
