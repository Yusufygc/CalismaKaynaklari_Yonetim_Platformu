from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtQuick import QQuickImageProvider
import qtawesome as qta

from core.logger import log


class IconImageProvider(QQuickImageProvider):
    """QML içinden 'image://icon/<icon_name>/<hex_color>' formatında
    qtawesome ikonlarını dinamik olarak çeken yüksek çözünürlüklü sağlayıcı.
    """

    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.ImageType.Pixmap)

    def requestPixmap(self, icon_id: str, size: QSize, requested_size: QSize) -> QPixmap:
        parts = icon_id.split("/")
        icon_name = parts[0]
        if icon_name.startswith("fa5r."):
            icon_name = "fa5s." + icon_name[5:]
        
        # Renk çözme
        if len(parts) > 1 and parts[1]:
            color_str = parts[1]
            if not color_str.startswith("#"):
                color_str = "#" + color_str
        else:
            color_str = "#FFFFFF"

        # Boyut belirleme
        w = requested_size.width() if requested_size and requested_size.width() > 0 else 24
        h = requested_size.height() if requested_size and requested_size.height() > 0 else 24

        try:
            icon = qta.icon(icon_name, color=color_str)
            # High-DPI keskinliği için 2 katı çözünürlükte render edip cihaz piksel oranına uyum
            pixmap = icon.pixmap(w * 2, h * 2)
            pixmap.setDevicePixelRatio(2.0)
            return pixmap
        except Exception:
            log.warning("Ikon yuklenemedi: name=%r color=%r", icon_name, color_str)
            empty = QPixmap(w, h)
            empty.fill(QColor(0, 0, 0, 0))
            return empty
