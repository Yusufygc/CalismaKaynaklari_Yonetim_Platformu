from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from core.constants.colors import Colors
from core.constants.icons import QtAwesomeIcons
from core.constants.strings import AppStrings
from ui.components.icon_action_button import IconActionButton


class HighlightRow(QFrame):
    """Tek alinti satiri: (opsiyonel kaynak basligi) + icerik onizleme + sil.

    Duzenleme modu yok (bu turda alintilar sadece olusturulup silinebilir).
    """

    delete_requested = Signal(int)      # highlight id
    resource_clicked = Signal(int)      # resource id (sadece resource_title verildiyse anlamli)

    def __init__(
        self,
        highlight,
        resource_title: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("HighlightRow")
        self._highlight_id: int = highlight.id
        self._resource_id: int = highlight.resource_id
        self._confirm_pending: bool = False
        self._build_ui(highlight, resource_title)

    def _build_ui(self, highlight, resource_title: str | None) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 6)
        root.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        if resource_title:
            self._resource_link = QPushButton(resource_title)
            self._resource_link.setObjectName("RowResourceLink")
            self._resource_link.setFlat(True)
            self._resource_link.setCursor(Qt.CursorShape.PointingHandCursor)
            self._resource_link.clicked.connect(
                lambda: self.resource_clicked.emit(self._resource_id)
            )
            top_row.addWidget(self._resource_link, stretch=1)
        else:
            top_row.addStretch(1)

        self._delete_btn = IconActionButton(
            QtAwesomeIcons.DELETE, Colors.DANGER, AppStrings.DELETE, "RowDeleteButton"
        )
        self._delete_btn.clicked.connect(self._on_delete_click)
        top_row.addWidget(self._delete_btn)
        root.addLayout(top_row)

        self._content_label = QLabel(highlight.content)
        self._content_label.setObjectName("HighlightContentLabel")
        self._content_label.setWordWrap(True)
        root.addWidget(self._content_label)

        if highlight.page_number:
            page_label = QLabel(f"s. {highlight.page_number}")
            page_label.setObjectName("HighlightPageBadge")
            root.addWidget(page_label, alignment=Qt.AlignmentFlag.AlignLeft)

    def _on_delete_click(self) -> None:
        if not self._confirm_pending:
            self._delete_btn.set_state(
                QtAwesomeIcons.DELETE, Colors.DANGER_HOVER,
                AppStrings.CONFIRM_DELETE, "RowDeleteConfirmButton",
            )
            self._confirm_pending = True
        else:
            self.delete_requested.emit(self._highlight_id)

    @property
    def content(self) -> str:
        return self._content_label.text()
