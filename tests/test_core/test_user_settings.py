"""Kullanici ayar deposu: kalicilik, atomik yazim, bozuk dosyaya dayaniklilik."""
import json

from core.user_settings import UserSettings


def test_values_persist_across_instances(tmp_path):
    path = tmp_path / "ayar.json"
    assert UserSettings(path).set("vault_path", "C:/Vault") is True

    assert UserSettings(path).get("vault_path") == "C:/Vault"
    assert UserSettings(path).get("yok", "varsayilan") == "varsayilan"


def test_none_removes_the_key(tmp_path):
    settings = UserSettings(tmp_path / "ayar.json")
    settings.set("a", 1)
    settings.set("b", 2)

    settings.set("a", None)

    assert settings.get("a") is None and UserSettings(tmp_path / "ayar.json").get("b") == 2


def test_non_ascii_values_round_trip_and_no_temp_file_is_left(tmp_path):
    settings = UserSettings(tmp_path / "ayar.json")

    settings.set("vault_path", "C:/Kullanıcı/Şükrü/Vault")

    assert json.loads((tmp_path / "ayar.json").read_text(encoding="utf-8"))["vault_path"] == "C:/Kullanıcı/Şükrü/Vault"
    assert [p.name for p in tmp_path.iterdir()] == ["ayar.json"]


def test_corrupt_file_is_ignored_set_aside_and_replaced_on_next_write(tmp_path):
    path = tmp_path / "ayar.json"
    path.write_text("{bozuk json", encoding="utf-8")

    settings = UserSettings(path)

    assert settings.get("vault_path") is None
    assert (tmp_path / "ayar.corrupt").read_text(encoding="utf-8") == "{bozuk json"
    assert settings.set("vault_path", "x") and UserSettings(path).get("vault_path") == "x"


def test_non_object_json_is_treated_as_corrupt(tmp_path):
    path = tmp_path / "ayar.json"
    path.write_text("[1, 2]", encoding="utf-8")

    assert UserSettings(path).get("x") is None


def test_a_failed_write_reports_false_and_keeps_the_previous_value(tmp_path, monkeypatch):
    settings = UserSettings(tmp_path / "ayar.json")
    settings.set("a", 1)

    def broken_replace(src, dst):
        raise PermissionError("kilitli")

    monkeypatch.setattr("core.user_settings.os.replace", broken_replace)

    assert settings.set("a", 2) is False
    assert settings.get("a") == 1
