from PySide6.QtCore import QObject, Signal


class Notifier(QObject):
    """Tek toast kanali: tum alt-bridge'ler kullaniciya `info`/`error` bildirimini buradan gonderir;
    kok `QmlBridge` bunu QML'in dinledigi `notificationEmitted` sinyaline baglar."""

    emitted = Signal(str, str)  # tur (info/error), mesaj

    def info(self, message: str) -> None:
        self.emitted.emit("info", message)

    def error(self, message: str) -> None:
        self.emitted.emit("error", message)
