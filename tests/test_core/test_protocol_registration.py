"""pkm:// protokol kaydi (HKCU): sahte kayit defteriyle; gercek kayit defterine dokunulmaz."""
from pathlib import Path

import pytest

from core.protocol_registration import ProtocolRegistration, expected_command


class FakeKey:
    def __init__(self, registry, path):
        self._registry, self._path = registry, path

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeWinreg:
    """`winreg`in kullanilan kismi: anahtar yolu -> {deger adi: deger}. Gercek gibi, alt anahtari olan anahtar silinemez."""

    HKEY_CURRENT_USER = "HKCU"
    REG_SZ = 1

    def __init__(self):
        self.keys: dict[str, dict[str, str]] = {}

    def _path(self, hive, sub):
        assert hive == self.HKEY_CURRENT_USER, "yalniz HKCU'ya yazilmali"
        return sub

    def CreateKey(self, hive, sub):
        parts = self._path(hive, sub).split("\\")
        for i in range(1, len(parts) + 1):
            self.keys.setdefault("\\".join(parts[:i]), {})
        return FakeKey(self, sub)

    def OpenKey(self, hive, sub):
        if self._path(hive, sub) not in self.keys:
            raise FileNotFoundError(sub)
        return FakeKey(self, sub)

    def SetValueEx(self, key, name, _reserved, _kind, value):
        self.keys[key._path][name] = value

    def QueryValueEx(self, key, name):
        try:
            return self.keys[key._path][name], self.REG_SZ
        except KeyError:
            raise FileNotFoundError(name) from None

    def DeleteKey(self, hive, sub):
        path = self._path(hive, sub)
        if path not in self.keys:
            raise FileNotFoundError(path)
        if any(other.startswith(path + "\\") for other in self.keys):
            raise OSError("alt anahtarlari var")
        del self.keys[path]


COMMAND = r'"C:\Python\python.exe" "C:\app\main.py" "%1"'


@pytest.fixture()
def fake():
    return FakeWinreg()


def test_register_writes_the_url_protocol_keys_and_command_under_hkcu(fake):
    registration = ProtocolRegistration(fake, COMMAND)

    assert not registration.is_registered()
    registration.register()

    assert registration.is_registered()
    assert fake.keys[r"Software\Classes\pkm"] == {"": "URL:PKM Protocol", "URL Protocol": ""}
    assert fake.keys[r"Software\Classes\pkm\shell\open\command"] == {"": COMMAND}


def test_a_registration_pointing_at_an_old_path_is_not_considered_registered_and_register_repairs_it(fake):
    ProtocolRegistration(fake, r'"C:\eski\main.py" "%1"').register()
    current = ProtocolRegistration(fake, COMMAND)

    assert not current.is_registered()
    current.register()

    assert current.is_registered()


def test_unregister_removes_only_the_pkm_keys_and_is_idempotent(fake):
    registration = ProtocolRegistration(fake, COMMAND)
    fake.CreateKey("HKCU", r"Software\Classes\baska")  # baska bir protokol: dokunulmamali
    registration.register()

    registration.unregister()
    registration.unregister()

    assert not registration.is_registered()
    assert list(fake.keys) == ["Software", r"Software\Classes", r"Software\Classes\baska"] or r"Software\Classes\baska" in fake.keys
    assert not any(key.startswith(r"Software\Classes\pkm") for key in fake.keys)


def test_without_a_registry_it_is_unsupported_and_register_fails_cleanly():
    registration = ProtocolRegistration(None, COMMAND)  # tests/conftest `winreg`i yok sayar

    assert not registration.supported and not registration.is_registered()
    with pytest.raises(OSError):
        registration.register()
    registration.unregister()  # sessizce gecer


def test_expected_command_quotes_every_path_and_passes_the_link_as_percent_one():
    assert expected_command(frozen=True, executable=r"C:\Program Files\PKM\pkm.exe") == r'"C:\Program Files\PKM\pkm.exe" "%1"'
    assert expected_command(False, r"C:\Py\python.exe", Path("C:/Proje Klasoru/main.py")).endswith('main.py" "%1"')
    assert expected_command(False, r"C:\Py\python.exe", Path("C:/p/main.py")).startswith(r'"C:\Py\python.exe" "')
