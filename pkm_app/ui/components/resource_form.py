from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
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
from models import ResourceStatus
from ui.components.color_picker_button import ColorPickerButton
from ui.components.icon_action_button import IconActionButton


class ResourceForm(QFrame):
    """Kaynak ekleme / duzenleme formu — sag panelde goruntulenir, QDialog kullanilmaz."""

    submitted = Signal(dict)
    cancelled = Signal()
    category_create_requested = Signal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ResourceForm")
        self._categories: list = []
        self._resource_id: int | None = None
        self._build_ui()

    # ------------------------------------------------------------------ #
    # Kurulum
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        self._header = QLabel(AppStrings.FORM_HEADER)
        self._header.setObjectName("FormHeader")
        root.addWidget(self._header)

        self._title_input = self._field(root, AppStrings.FORM_FIELD_TITLE)
        self._url_input = self._field(root, AppStrings.FORM_FIELD_URL)

        category_label_row = QHBoxLayout()
        category_label_row.addWidget(QLabel(AppStrings.FORM_FIELD_CATEGORY), stretch=1)
        self._cat_add_toggle_btn = IconActionButton(
            QtAwesomeIcons.ADD,
            Colors.ACCENT,
            AppStrings.FORM_ADD_CATEGORY_TOOLTIP,
            "FormInlineAddButton",
        )
        self._cat_add_toggle_btn.clicked.connect(self._toggle_category_add_panel)
        category_label_row.addWidget(self._cat_add_toggle_btn)
        root.addLayout(category_label_row)

        self._category_combo = QComboBox()
        self._category_combo.setObjectName("FormCombo")
        root.addWidget(self._category_combo)

        self._cat_add_panel = QWidget()
        cat_add_row = QHBoxLayout(self._cat_add_panel)
        cat_add_row.setContentsMargins(0, 4, 0, 0)
        cat_add_row.setSpacing(6)
        self._new_cat_name_input = QLineEdit()
        self._new_cat_name_input.setObjectName("FormField")
        self._new_cat_name_input.setPlaceholderText(AppStrings.CATEGORY_NAME)
        cat_add_row.addWidget(self._new_cat_name_input, stretch=1)
        self._new_cat_color_picker = ColorPickerButton()
        self._new_cat_color_picker.setFixedWidth(110)
        self._new_cat_color_picker.setToolTip(AppStrings.CATEGORY_COLOR)
        cat_add_row.addWidget(self._new_cat_color_picker)
        self._new_cat_confirm_btn = QPushButton(AppStrings.ADD)
        self._new_cat_confirm_btn.setObjectName("SaveButton")
        self._new_cat_confirm_btn.setFixedWidth(60)
        cat_add_row.addWidget(self._new_cat_confirm_btn)
        self._new_cat_confirm_btn.clicked.connect(self._on_confirm_new_category)
        self._new_cat_name_input.returnPressed.connect(self._on_confirm_new_category)
        self._cat_add_panel.hide()
        root.addWidget(self._cat_add_panel)

        root.addWidget(QLabel(AppStrings.FORM_FIELD_STATUS))
        self._status_combo = QComboBox()
        self._status_combo.setObjectName("FormCombo")
        self._status_combo.addItem(AppStrings.FORM_STATUS_INBOX, ResourceStatus.INBOX)
        self._status_combo.addItem(AppStrings.FORM_STATUS_PLANNED, ResourceStatus.PLANNED)
        self._status_combo.addItem(AppStrings.FORM_STATUS_IN_PROGRESS, ResourceStatus.IN_PROGRESS)
        self._status_combo.addItem(AppStrings.FORM_STATUS_COMPLETED, ResourceStatus.COMPLETED)
        root.addWidget(self._status_combo)

        root.addWidget(QLabel(AppStrings.FORM_FIELD_PRIORITY))
        self._priority_combo = QComboBox()
        self._priority_combo.setObjectName("FormCombo")
        self._priority_combo.addItem(AppStrings.FORM_PRIORITY_HIGH, 1)
        self._priority_combo.addItem(AppStrings.FORM_PRIORITY_MEDIUM, 2)
        self._priority_combo.addItem(AppStrings.FORM_PRIORITY_LOW, 3)
        root.addWidget(self._priority_combo)

        self._tags_input = self._field(root, AppStrings.FORM_FIELD_TAGS)

        root.addWidget(QLabel(AppStrings.FORM_FIELD_CONTENT))
        self._content_input = QTextEdit()
        self._content_input.setObjectName("FormTextEdit")
        self._content_input.setMaximumHeight(100)
        root.addWidget(self._content_input)

        root.addStretch(1)

        btn_row = QHBoxLayout()
        self._save_btn = QPushButton(AppStrings.SAVE)
        self._save_btn.setObjectName("SaveButton")
        self._cancel_btn = QPushButton(AppStrings.CANCEL)
        self._cancel_btn.setObjectName("CancelButton")
        btn_row.addWidget(self._cancel_btn)
        btn_row.addWidget(self._save_btn)
        root.addLayout(btn_row)

        self._save_btn.clicked.connect(self._on_save)
        self._cancel_btn.clicked.connect(self.cancelled)

    @staticmethod
    def _field(layout: QVBoxLayout, label: str) -> QLineEdit:
        layout.addWidget(QLabel(label))
        field = QLineEdit()
        field.setObjectName("FormField")
        layout.addWidget(field)
        return field

    # ------------------------------------------------------------------ #
    # Veri
    # ------------------------------------------------------------------ #

    def load_categories(self, categories: list) -> None:
        self._categories = categories
        self._category_combo.clear()
        self._category_combo.addItem(AppStrings.FORM_CATEGORY_NONE, None)
        for cat in categories:
            self._category_combo.addItem(cat.name, cat.id)

    def set_categories(self, categories: list, select_id: int | None = None) -> None:
        """Kategori listesini yeniler; verilirse `select_id`'yi secili yapar.

        Formdaki diger alanlara dokunmaz — inline "yeni kategori ekle"
        akisindan sonra sadece kategori combo'sunu tazelemek icin kullanilir.
        """
        self.load_categories(categories)
        if select_id is not None:
            idx = self._category_combo.findData(select_id)
            if idx >= 0:
                self._category_combo.setCurrentIndex(idx)
        self._hide_category_add_panel()

    def load_resource(self, resource, categories: list) -> None:
        """Edit modu: alanlari mevcut degerlerle doldur."""
        self.load_categories(categories)
        self._hide_category_add_panel()
        self._resource_id = resource.id
        self._header.setText(AppStrings.FORM_HEADER_EDIT)
        self._title_input.setText(resource.title)
        self._url_input.setText(resource.url or "")

        cat_idx = self._category_combo.findData(resource.category_id)
        self._category_combo.setCurrentIndex(cat_idx if cat_idx >= 0 else 0)

        status_idx = self._status_combo.findData(resource.status)
        self._status_combo.setCurrentIndex(status_idx if status_idx >= 0 else 0)

        pri_idx = self._priority_combo.findData(resource.priority)
        self._priority_combo.setCurrentIndex(pri_idx if pri_idx >= 0 else 1)

        tag_names = ", ".join(t.name for t in resource.tags) if resource.tags else ""
        self._tags_input.setText(tag_names)
        self._content_input.setPlainText(resource.content or "")

    def reset_for_new(self) -> None:
        self._resource_id = None
        self._header.setText(AppStrings.FORM_HEADER)
        self._title_input.clear()
        self._url_input.clear()
        self._tags_input.clear()
        self._content_input.clear()
        self._priority_combo.setCurrentIndex(1)  # Orta
        self._category_combo.setCurrentIndex(0)
        self._status_combo.setCurrentIndex(0)   # Gelen Kutusu
        self._hide_category_add_panel()

    # ------------------------------------------------------------------ #
    # Slot
    # ------------------------------------------------------------------ #

    def _toggle_category_add_panel(self) -> None:
        if self._cat_add_panel.isVisible():
            self._hide_category_add_panel()
        else:
            self._cat_add_panel.show()
            self._new_cat_name_input.setFocus()

    def _hide_category_add_panel(self) -> None:
        self._cat_add_panel.hide()
        self._new_cat_name_input.clear()
        self._new_cat_color_picker.clear()

    def _on_confirm_new_category(self) -> None:
        name = self._new_cat_name_input.text().strip()
        color = self._new_cat_color_picker.value()
        if not name:
            event_bus.error_occurred.emit(AppStrings.ERR_CATEGORY_NAME_REQUIRED)
            return
        if not color:
            event_bus.error_occurred.emit(AppStrings.ERR_COLOR_REQUIRED)
            return
        self.category_create_requested.emit(name, color)

    def _on_save(self) -> None:
        title = self._title_input.text().strip()
        if not title:
            event_bus.error_occurred.emit(AppStrings.ERR_TITLE_REQUIRED)
            return

        url = self._url_input.text().strip() or None
        category_id = self._category_combo.currentData()
        status = self._status_combo.currentData()
        priority = self._priority_combo.currentData()
        raw_tags = self._tags_input.text()
        tag_names = [t.strip() for t in raw_tags.split(",") if t.strip()]
        content = self._content_input.toPlainText().strip() or None

        data: dict = {
            "title": title,
            "url": url,
            "category_id": category_id,
            "status": status,
            "priority": priority,
            "tag_names": tag_names,
            "content": content,
        }
        if self._resource_id is not None:
            data["resource_id"] = self._resource_id

        self.submitted.emit(data)
