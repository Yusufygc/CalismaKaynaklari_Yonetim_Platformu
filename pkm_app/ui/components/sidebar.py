from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import qtawesome as qta

from core.constants.colors import Colors
from core.constants.icons import QtAwesomeIcons
from core.constants.strings import AppStrings
from core.events import event_bus
from ui.theme_utils import resolve_theme_color, load_theme_svg


_STATIC_ITEMS = [
    (AppStrings.URL_SHOWCASE, QtAwesomeIcons.URL_SHOWCASE, "url_showcase"),
    (AppStrings.KNOWLEDGE_POOL, QtAwesomeIcons.KNOWLEDGE_POOL, "knowledge_pool"),
    (AppStrings.SETTINGS, QtAwesomeIcons.SETTINGS, "settings"),
]


class Sidebar(QFrame):

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(220)

        self._theme: dict = {}
        self._nav_icons: list[str] = []
        self._is_collapsed = False
        self._build_ui()
        self._connect_signals()

        # Baslangic temasini ve ikonlarini yukle
        from core.theme_manager import theme_manager
        if theme_manager.current_theme:
            self._on_theme_changed(theme_manager.current_theme)

    # ------------------------------------------------------------------ #
    # Kurulum
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 16, 8, 8)
        layout.setSpacing(4)

        # Baslik ve Hamburger menü butonu icin yatay duzen
        self._top_layout = QHBoxLayout()
        self._top_layout.setContentsMargins(4, 0, 4, 0)
        self._top_layout.setSpacing(6)

        self._title = QLabel(AppStrings.APP_TITLE)
        self._title.setObjectName("SidebarTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._top_layout.addWidget(self._title, stretch=1)

        self._hamburger_btn = QPushButton()
        self._hamburger_btn.setObjectName("HamburgerButton")
        self._hamburger_btn.setFixedSize(32, 32)
        self._top_layout.addWidget(self._hamburger_btn)

        layout.addLayout(self._top_layout)

        layout.addSpacing(12)

        self._nav_list = QListWidget()
        self._nav_list.setObjectName("SidebarNavList")
        self._nav_list.setSpacing(2)
        self._nav_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._nav_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        icon_color = resolve_theme_color(None, Colors.ICON)
        for label, icon_name, key in _STATIC_ITEMS:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setData(Qt.ItemDataRole.UserRole + 1, label)  # Orijinal metni sakla
            item.setIcon(qta.icon(icon_name, color=icon_color))
            self._nav_icons.append(icon_name)
            self._nav_list.addItem(item)
        layout.addWidget(self._nav_list)

        layout.addStretch()

        # Tema degisimi ToggleSwitch yatay duzeni
        self._theme_layout = QHBoxLayout()
        self._theme_layout.setContentsMargins(4, 0, 4, 0)
        self._theme_layout.setSpacing(8)

        self._theme_label = QLabel(AppStrings.TOGGLE_THEME)
        self._theme_label.setObjectName("ThemeToggleLabel")
        self._theme_layout.addWidget(self._theme_label, stretch=1)

        from ui.components.toggle_switch import ToggleSwitch
        self._theme_switch = ToggleSwitch()
        self._theme_layout.addWidget(self._theme_switch)

        layout.addLayout(self._theme_layout)

        # Sade Mod ToggleSwitch yatay duzeni
        self._simple_mode_layout = QHBoxLayout()
        self._simple_mode_layout.setContentsMargins(4, 0, 4, 0)
        self._simple_mode_layout.setSpacing(8)

        self._simple_mode_label = QLabel(AppStrings.TOGGLE_SIMPLE_MODE)
        self._simple_mode_label.setObjectName("SimpleModeToggleLabel")
        self._simple_mode_layout.addWidget(self._simple_mode_label, stretch=1)

        self._simple_mode_switch = ToggleSwitch()
        self._simple_mode_layout.addWidget(self._simple_mode_switch)

        layout.addLayout(self._simple_mode_layout)

    def select_by_key(self, key: str) -> None:
        """Verilen filtre anahtarina karsilik gelen nav item'ini sinyal firlatmadan secer."""
        for index in range(self._nav_list.count()):
            item = self._nav_list.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == key:
                self._nav_list.blockSignals(True)
                self._nav_list.setCurrentRow(index)
                self._nav_list.blockSignals(False)
                self._refresh_nav_icons()
                break

    def _connect_signals(self) -> None:
        self._nav_list.currentItemChanged.connect(self._on_nav_changed)
        self._hamburger_btn.clicked.connect(self._on_hamburger_clicked)
        self._theme_switch.toggled.connect(self._on_theme_toggle)
        self._simple_mode_switch.toggled.connect(self._on_simple_mode_toggle)
        event_bus.theme_changed.connect(self._on_theme_changed)

    # ------------------------------------------------------------------ #
    # Slot'lar
    # ------------------------------------------------------------------ #

    def _on_nav_changed(self, current, _previous) -> None:
        if current:
            self._refresh_nav_icons()
            event_bus.sidebar_filter_changed.emit(
                current.data(Qt.ItemDataRole.UserRole)
            )

    def _on_hamburger_clicked(self) -> None:
        self.set_collapsed(not self._is_collapsed)

    def _on_theme_toggle(self, checked: bool) -> None:
        from core.theme_manager import theme_manager
        current_theme_name = theme_manager.current_theme.get("name")
        target_theme = "dark" if checked else "light"
        if current_theme_name != target_theme:
            theme_manager.apply_theme(target_theme)

    def _on_simple_mode_toggle(self, checked: bool) -> None:
        event_bus.simple_mode_toggled.emit(checked)

    def _on_theme_changed(self, theme_data: dict) -> None:
        self._theme = theme_data
        icon_color = resolve_theme_color(theme_data, Colors.ICON)
        selected_color = resolve_theme_color(theme_data, Colors.ACCENT)
        self._refresh_nav_icons(icon_color, selected_color)
        
        # Hamburger ikonunu temaya gore guncelle
        self._refresh_hamburger_icon(icon_color)
        
        # Switch temasini ve secili durumunu guncelle
        self._theme_switch.set_theme(theme_data)
        is_dark = theme_data.get("name") == "dark"

        self._theme_switch.blockSignals(True)
        self._theme_switch.setChecked(is_dark)
        self._theme_switch.blockSignals(False)

        self._simple_mode_switch.set_theme(theme_data)

    def _refresh_hamburger_icon(self, icon_color: str | None = None) -> None:
        icon_color = icon_color or resolve_theme_color(self._theme, Colors.ICON)
        hamburger_icon = load_theme_svg("hamburger.svg", icon_color, size=18)
        self._hamburger_btn.setIcon(hamburger_icon)

    def _refresh_nav_icons(
        self,
        icon_color: str | None = None,
        selected_color: str | None = None,
    ) -> None:
        icon_color = icon_color or resolve_theme_color(self._theme, Colors.ICON)
        selected_color = selected_color or resolve_theme_color(self._theme, Colors.ACCENT)
        for index in range(self._nav_list.count()):
            item = self._nav_list.item(index)
            color = selected_color if item.isSelected() else icon_color
            item.setIcon(qta.icon(self._nav_icons[index], color=color))

    def set_collapsed(self, collapsed: bool) -> None:
        self._is_collapsed = collapsed
        layout = self.layout()
        
        if collapsed:
            self.setFixedWidth(64)
            layout.setContentsMargins(4, 16, 4, 8)
            self._title.setVisible(False)
            self._theme_label.setVisible(False)
            self._simple_mode_label.setVisible(False)

            # Hizalamalari ortala
            self._top_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._theme_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._simple_mode_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Nav listesindeki metinleri gizle (bos yap)
            for index in range(self._nav_list.count()):
                item = self._nav_list.item(index)
                item.setText("")
        else:
            self.setFixedWidth(220)
            layout.setContentsMargins(8, 16, 8, 8)
            self._title.setVisible(True)
            self._theme_label.setVisible(True)
            self._simple_mode_label.setVisible(True)

            # Hizalamalari sola yasla
            self._top_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self._theme_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self._simple_mode_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Nav listesindeki metinleri geri yukle
            for index in range(self._nav_list.count()):
                item = self._nav_list.item(index)
                original_label = item.data(Qt.ItemDataRole.UserRole + 1)
                item.setText(original_label)

