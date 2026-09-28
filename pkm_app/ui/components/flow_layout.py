from PySide6.QtCore import Qt, QRect, QSize, QPoint
from PySide6.QtWidgets import QLabel, QLayout, QScrollArea, QSizePolicy, QStackedWidget, QWidget


class FlowLayout(QLayout):
    """Kartlari pencere genisligine gore alt satira kaydiran esnek layout."""

    def __init__(self, parent: QWidget | None = None, h_spacing: int = 12, v_spacing: int = 12) -> None:
        super().__init__(parent)
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing
        self._items: list = []

    def addItem(self, item) -> None:  # noqa: N802
        self._items.append(item)
        self.invalidate()  # container updateGeometry -> QScrollArea yeniden boyutlandirir -> setGeometry

    def horizontalSpacing(self) -> int:
        return self._h_spacing

    def verticalSpacing(self) -> int:
        return self._v_spacing

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):  # noqa: N802
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int):  # noqa: N802
        if 0 <= index < len(self._items):
            item = self._items.pop(index)
            self.invalidate()
            return item
        return None

    def expandingDirections(self) -> Qt.Orientations:
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        margins = self.contentsMargins()
        effective = rect.adjusted(margins.left(), margins.top(), -margins.right(), -margins.bottom())
        x, y = effective.x(), effective.y()
        row_height = 0
        row_items: list[tuple[object, QSize, int]] = []  # (item, size, sonraki_bosluk)

        def flush_row(row_y: int, height: int) -> None:
            if test_only:
                return
            cx = effective.x()
            for row_item, size, space_x in row_items:
                # Satirdaki en uzun oge disindakiler dikeyde ortalanir (yazi/kutu
                # hizasizligi onceden: hepsi satirin ustune yapisik kalirdi).
                item_y = row_y + (height - size.height()) // 2
                row_item.setGeometry(QRect(QPoint(cx, item_y), size))
                cx += size.width() + space_x

        for item in self._items:
            widget = item.widget()
            # Yalnizca explicit hide() edilmis (arama filtresi) widget'lari atla.
            # isVisible() kullanmak, henuz gosterilmemis yeni eklenen widget'lari da
            # atlar (parent henuz gorunur degilken isVisible False doner) -> kart
            # 0,0'da stale kalir. isHidden() sadece bilincli gizlenenleri yakalar.
            if widget and widget.isHidden():
                continue
            space_x = self._h_spacing
            space_y = self._v_spacing
            if widget:
                style = widget.style()
                space_x += style.layoutSpacing(
                    QSizePolicy.ControlType.PushButton,
                    QSizePolicy.ControlType.PushButton,
                    Qt.Orientation.Horizontal,
                )
                space_y += style.layoutSpacing(
                    QSizePolicy.ControlType.PushButton,
                    QSizePolicy.ControlType.PushButton,
                    Qt.Orientation.Vertical,
                )

            item_size = item.sizeHint()
            next_x = x + item_size.width() + space_x

            if next_x - space_x > effective.right() and row_height > 0:
                flush_row(y, row_height)
                row_items = []
                x = effective.x()
                y += row_height + space_y
                next_x = x + item_size.width() + space_x
                row_height = 0

            row_items.append((item, item_size, space_x))
            x = next_x
            row_height = max(row_height, item_size.height())

        flush_row(y, row_height)
        return y + row_height - rect.y() + margins.bottom()


GRID_PAGE = 0
EMPTY_PAGE = 1


def clear_flow(flow: FlowLayout) -> None:
    """Widget'lari parent'tan hemen koparip deleteLater() ile siler.

    setParent(None) olmadan sadece deleteLater() cagirmak, gercek silme Qt
    event loop'unun sonraki turuna ertelendigi icin eski widget'in bir frame
    boyunca eski konumunda gorunur kalmasina ve yeni eklenen widget'larla
    cakismasina (flicker) neden olur.
    """
    while flow.count():
        item = flow.takeAt(0)
        widget = item.widget() if item else None
        if widget:
            widget.setParent(None)
            widget.deleteLater()


def build_flow_stack(
    empty_message: str,
    h_spacing: int = 12,
    v_spacing: int = 12,
    container_name: str = "",
    scroll_name: str = "",
) -> tuple[QStackedWidget, FlowLayout]:
    """Bos-durum + kaydirilabilir FlowLayout izgarasi iceren bir QStackedWidget kurar."""
    stack = QStackedWidget()

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    if scroll_name:
        scroll.setObjectName(scroll_name)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    container = QWidget()
    if container_name:
        container.setObjectName(container_name)
    flow = FlowLayout(container, h_spacing=h_spacing, v_spacing=v_spacing)
    container.setLayout(flow)
    scroll.setWidget(container)
    stack.addWidget(scroll)  # GRID_PAGE

    empty_label = QLabel(empty_message)
    empty_label.setObjectName("EmptyStateLabel")
    empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    empty_label.setWordWrap(True)
    stack.addWidget(empty_label)  # EMPTY_PAGE

    return stack, flow
