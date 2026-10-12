"""Tek uygulama ornegi + ornekler arasi mesajlasma (QLocalServer/QLocalSocket).

Ikinci kez baslatilan uygulama (ornegin `pkm://` baglantisina tiklaninca) calisan ornege mesaj yollayip cikar. Bu ayni
zamanda iki ornegin ayni SQLite dosyasini birlikte acmasini onler.

Mesajlar disaridan gelir ve guvenilmez girdidir: boyut sinirlidir, tek satirdir; ne yapilacagina alici karar verir
ve girdiyi kendisi dogrular."""
import getpass
import time

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

MAX_MESSAGE_BYTES = 2048
_CONNECT_TIMEOUT_MS = 500
_RETRY_DELAY_S = 0.03


def default_name() -> str:
    """Kullanici basina ayri ad: ayni makinedeki baska bir kullanicinin ornegiyle karismasin."""
    user = "".join(c for c in getpass.getuser() if c.isalnum()) or "user"
    return f"pkm-single-instance-{user}"


def _connect(name: str, timeout_ms: int) -> QLocalSocket | None:
    """Sunucuya baglanir. Sunucu yoksa hemen None; sunucu var ama meşgulse (Windows: ardisik istemcilerde boru ornegi
    henuz yeniden olusturulmamis olabilir) kisa araliklarla yeniden dener. Yoksa "calisan ornek yok" sanilip ikinci bir
    uygulama ornegi baslardi."""
    deadline = time.monotonic() + timeout_ms / 1000
    while True:
        socket = QLocalSocket()
        socket.connectToServer(name)
        if socket.waitForConnected(timeout_ms):
            return socket
        if socket.error() == QLocalSocket.LocalSocketError.ServerNotFoundError or time.monotonic() >= deadline:
            return None
        time.sleep(_RETRY_DELAY_S)


def send_message(name: str, message: str, timeout_ms: int = _CONNECT_TIMEOUT_MS) -> bool:
    """Calisan ornege tek satirlik mesaj yollar; ornek yoksa/ulasilamazsa False."""
    data = message.replace("\n", " ").encode("utf-8")[:MAX_MESSAGE_BYTES] + b"\n"
    socket = _connect(name, timeout_ms)
    if socket is None:
        return False
    socket.write(data)
    delivered = socket.waitForBytesWritten(timeout_ms)
    socket.disconnectFromServer()
    if socket.state() != QLocalSocket.LocalSocketState.UnconnectedState:
        socket.waitForDisconnected(timeout_ms)
    return delivered


class SingleInstance(QObject):
    """Bu surecin ornek sunucusu: `listen()` ile ilk ornek olur, gelen mesajlari `messageReceived` ile iletir."""

    messageReceived = Signal(str)

    def __init__(self, name: str | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._name = name or default_name()
        self._server = QLocalServer(self)
        self._server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)  # yalniz bu kullanici baglanabilir
        self._server.newConnection.connect(self._on_connection)

    @property
    def name(self) -> str:
        return self._name

    def listen(self) -> bool:
        """Sunucuyu baslatir. Onceki cokmeden kalan ayrik soket temizlenir (sunucu yoksa baglanma zaten basarisiz olur)."""
        QLocalServer.removeServer(self._name)
        return self._server.listen(self._name)

    def close(self) -> None:
        self._server.close()

    def _on_connection(self) -> None:
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            socket.setParent(self)
            buffer = bytearray()
            state = {"done": False}

            def finish(sock=socket, buf=buffer, st=state) -> None:
                if st["done"]:
                    return
                st["done"] = True
                text = bytes(buf).split(b"\n", 1)[0].decode("utf-8", errors="replace").strip()
                if text:
                    self.messageReceived.emit(text)
                sock.disconnectFromServer()
                sock.deleteLater()

            def read(sock=socket, buf=buffer, st=state) -> None:
                if st["done"]:
                    return
                buf.extend(sock.readAll().data())
                if b"\n" in buf or len(buf) > MAX_MESSAGE_BYTES:
                    finish()

            socket.readyRead.connect(read)
            socket.disconnected.connect(finish)
            if socket.bytesAvailable():
                read()
