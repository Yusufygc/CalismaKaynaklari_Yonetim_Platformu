"""Tek ornek + mesajlasma: gercek QLocalServer/QLocalSocket (testte benzersiz ad)."""
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from PySide6.QtTest import QTest

from core.single_instance import MAX_MESSAGE_BYTES, SingleInstance, send_message

ROOT = Path(__file__).resolve().parents[2]
_CLIENT = (
    "import sys; sys.path.insert(0, sys.argv[1]);"
    "from PySide6.QtCore import QCoreApplication;"
    "from core.single_instance import send_message;"
    "app = QCoreApplication([]);"
    "sys.exit(0 if send_message(sys.argv[2], sys.argv[3], 2000) else 1)"
)


def send_from_another_process(name: str, message: str, wait_ms: int = 20000) -> bool:
    """Gercek kullanim gibi AYRI bir surecten gonderir (ayni surecte engelleyici baglanma sunucu dongusunu bekler).
    Sunucunun olay dongusu bu sirada calismaya devam eder."""
    process = subprocess.Popen([sys.executable, "-I", "-c", _CLIENT, str(ROOT), name, message])
    waited = 0
    while process.poll() is None and waited < wait_ms:
        QTest.qWait(20)
        waited += 20
    if process.poll() is None:
        process.kill()
    return process.returncode == 0


@pytest.fixture()
def server(qapp):
    instance = SingleInstance(f"pkm-test-{uuid.uuid4().hex}")
    assert instance.listen()
    received = []
    instance.messageReceived.connect(received.append)
    yield instance, received
    instance.close()


def _wait_for(received, count=1, timeout=4000):
    waited = 0
    while len(received) < count and waited < timeout:
        QTest.qWait(20)
        waited += 20


def test_message_reaches_the_running_instance(server):
    instance, received = server

    assert send_from_another_process(instance.name, "pkm://open?doc=abababab&page=3")
    _wait_for(received)

    assert received == ["pkm://open?doc=abababab&page=3"]


def test_non_ascii_text_round_trips(server):
    instance, received = server

    send_from_another_process(instance.name, "activate Şükrü")
    _wait_for(received)

    assert received == ["activate Şükrü"]


def test_several_messages_arrive_in_order_one_per_connection(server):
    instance, received = server

    for text in ("bir", "iki", "uc"):
        assert send_from_another_process(instance.name, text)
    _wait_for(received, 3)

    assert received == ["bir", "iki", "uc"]


_BURST_CLIENT = (
    "import sys; sys.path.insert(0, sys.argv[1]);"
    "from PySide6.QtCore import QCoreApplication;"
    "from core.single_instance import send_message;"
    "app = QCoreApplication([]);"
    "results = [send_message(sys.argv[2], f'mesaj {i}', 2000) for i in range(int(sys.argv[3]))];"
    "sys.exit(0 if all(results) else 1)"
)


def test_a_burst_of_back_to_back_messages_all_arrive(server):
    """Ardisik hizli istemciler (iki link tiklamasi): sunucu pipe'i yeniden olusturana kadar mesgul olabilir; istemci
    bunu "ornek yok" sanmamali (yoksa ikinci bir uygulama ornegi baslardi)."""
    instance, received = server
    process = subprocess.Popen([sys.executable, "-I", "-c", _BURST_CLIENT, str(ROOT), instance.name, "15"])
    waited = 0
    while process.poll() is None and waited < 20000:
        QTest.qWait(10)
        waited += 10
    _wait_for(received, 15)

    assert process.returncode == 0 and received == [f"mesaj {i}" for i in range(15)]


def test_sending_without_a_running_instance_returns_false(qapp):
    assert send_message(f"pkm-test-yok-{uuid.uuid4().hex}", "x", timeout_ms=100) is False


def test_after_the_server_closes_nobody_is_listening(server):
    instance, _received = server
    instance.close()

    assert send_from_another_process(instance.name, "x") is False


def test_oversized_and_multiline_messages_are_truncated_to_one_bounded_line(server):
    instance, received = server

    send_from_another_process(instance.name, "ilk satir\nsonraki satir " + "x" * 10_000)
    _wait_for(received)

    assert len(received) == 1 and "\n" not in received[0] and len(received[0].encode()) <= MAX_MESSAGE_BYTES


def test_empty_messages_are_ignored(server):
    instance, received = server

    send_from_another_process(instance.name, "   ")
    QTest.qWait(150)

    assert received == []


def test_a_second_listener_with_the_same_name_takes_over_a_stale_socket_name(qapp):
    name = f"pkm-test-{uuid.uuid4().hex}"
    first = SingleInstance(name)
    assert first.listen()
    first.close()

    second = SingleInstance(name)

    assert second.listen()
    second.close()
