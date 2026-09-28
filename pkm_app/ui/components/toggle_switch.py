from PySide6.QtCore import Property, QPropertyAnimation, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QAbstractButton

from core.constants.colors import Colors
from ui.theme_utils import resolve_theme_color


class ToggleSwitch(QAbstractButton):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(48, 24)
        
        # animasyon parametreleri
        self._thumb_position = 3.0  # sol bosluk
        self._theme: dict = {}
        
        self._anim = QPropertyAnimation(self, b"thumb_position", self)
        self._anim.setDuration(120)

    @Property(float)
    def thumb_position(self) -> float:
        return self._thumb_position

    @thumb_position.setter
    def thumb_position(self, pos: float) -> None:
        self._thumb_position = pos
        self.update()

    def set_theme(self, theme_data: dict) -> None:
        self._theme = theme_data
        self.update()

    def nextCheckState(self) -> None:
        super().nextCheckState()
        start = self._thumb_position
        end = 27.0 if self.isChecked() else 3.0
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.start()

    def setChecked(self, checked: bool) -> None:
        super().setChecked(checked)
        # Sinyal engellenerek dogrudan set edilirse animasyonsuz gecis saglanir
        self._thumb_position = 27.0 if checked else 3.0
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Arka plan rengi
        if self.isChecked():
            track_color = QColor(resolve_theme_color(self._theme, Colors.ACCENT))
        else:
            track_color = QColor(resolve_theme_color(self._theme, Colors.BORDER))

        # Arka plani ciz
        painter.setBrush(track_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 12, 12)

        # Yuvarlak dugme (thumb) rengi
        thumb_color = QColor(resolve_theme_color(self._theme, Colors.BG_PRIMARY))
        painter.setBrush(thumb_color)
        # Dugmeyi ciz
        painter.drawEllipse(int(self._thumb_position), 3, 18, 18)
        painter.end()
