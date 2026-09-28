from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QScrollArea, QStackedWidget, QVBoxLayout, QWidget

from ui.components.flow_layout import EMPTY_PAGE, GRID_PAGE

__all__ = ["GRID_PAGE", "EMPTY_PAGE", "build_list_stack", "clear_list", "add_row"]


def add_row(layout: QVBoxLayout, widget: QWidget) -> None:
    """Satiri sondaki stretch'in ONCESINE ekler (addWidget stretch'in sonuna ekler, yanlis olur)."""
    layout.insertWidget(layout.count() - 1, widget)


def clear_list(layout: QVBoxLayout) -> None:
    """Widget'lari parent'tan hemen koparip deleteLater() ile siler.

    `flow_layout.py::clear_flow`'un ayni ghost-onleme deseni: setParent(None)
    olmadan sadece deleteLater() cagirmak, gercek silme bir sonraki event loop
    turune ertelendigi icin eski widget bir frame boyunca eski konumunda
    gorunur kalir. Sondaki stretch (trailing item) korunur.
    """
    while layout.count() > 1:
        item = layout.takeAt(0)
        widget = item.widget() if item else None
        if widget:
            widget.setParent(None)
            widget.deleteLater()


def build_list_stack(
    empty_message: str,
    spacing: int = 8,
    container_name: str = "",
    scroll_name: str = "",
) -> tuple[QStackedWidget, QVBoxLayout]:
    """Bos-durum + kaydirilabilir dikey liste iceren bir QStackedWidget kurar.

    `flow_layout.py::build_flow_stack` ile ayni iskelet, ama tam-genislik/
    degisken-yukseklikli satirlar (Highlight/Vocabulary) icin `FlowLayout`
    yerine `QVBoxLayout` kullanir (FlowLayout ayni-satirda-yan-yana-sarma
    icin tasarli, alt alta dizilen satirlara uygun degil).
    """
    stack = QStackedWidget()

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    if scroll_name:
        scroll.setObjectName(scroll_name)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    container = QWidget()
    if container_name:
        container.setObjectName(container_name)
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(spacing)
    layout.addStretch(1)
    scroll.setWidget(container)
    stack.addWidget(scroll)  # GRID_PAGE

    empty_label = QLabel(empty_message)
    empty_label.setObjectName("EmptyStateLabel")
    empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    empty_label.setWordWrap(True)
    stack.addWidget(empty_label)  # EMPTY_PAGE

    return stack, layout
