"""QML guvenlik agi: her bilesen derlenir, main.qml uyarisiz yuklenir, QML'in cagirdigi bridge uyeleri gercekten var.

Bu testler Python testlerinin yakalayamadigi hata sinifini yakalar: yinelenen property, gecersiz
anchor, yanlis yazilmis/silinmis bridge slotu (bkz. 2026-09-29/30 QML hatalari).
"""
import re

import pytest
from PySide6.QtCore import QMetaMethod, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

from ui_qml.bridge import QmlBridge
from tests.test_qml.qml_harness import QML_DIR, make_engine, pump, strip_qml_comments

QML_FILES = sorted(p for p in QML_DIR.rglob("*.qml") if p.name != "Theme.qml")


@pytest.mark.parametrize("qml_file", QML_FILES, ids=lambda p: str(p.relative_to(QML_DIR)))
def test_component_compiles_without_errors(qapp, qml_file):
    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))

    component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml_file)))

    assert component.status() != QQmlComponent.Error, [e.toString() for e in component.errors()]
    assert component.errors() == []


def test_theme_singleton_compiles(qapp):
    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_DIR / "theme" / "Theme.qml")))

    assert component.errors() == []


def test_main_qml_loads_with_real_bridge_without_warnings(qapp, session):
    bridge = QmlBridge(session)

    engine = make_engine(bridge)
    pump(qapp, 30)

    assert engine.rootObjects(), engine.captured_warnings
    assert engine.captured_warnings == []
    del engine


# ---------------------------------------------------------------- bridge sozlesmesi
def _members(obj) -> dict[str, str]:
    """{uye adi: 'property' | 'slot' | 'signal'} (Qt meta-nesnesinden)."""
    meta = obj.metaObject()
    members: dict[str, str] = {}
    for i in range(meta.propertyCount()):
        members[meta.property(i).name()] = "property"
    for i in range(meta.methodCount()):
        method = meta.method(i)
        kind = "signal" if method.methodType() == QMetaMethod.MethodType.Signal else "slot"
        members.setdefault(bytes(method.name()).decode(), kind)
    return members


_BRIDGE_REF = re.compile(r"\bbridge\.(\w+)")
_HANDLER = re.compile(r"function\s+on([A-Z]\w*)\s*\(")


def _connections_handlers(source: str) -> set[str]:
    """`Connections { target: bridge ... function onXyz(...) }` bloklarindaki sinyal adlari (xyz)."""
    signals: set[str] = set()
    for match in re.finditer(r"Connections\s*\{", source):
        depth, i = 1, match.end()
        while i < len(source) and depth:
            depth += {"{": 1, "}": -1}.get(source[i], 0)
            i += 1
        block = source[match.start():i]
        if re.search(r"target:\s*bridge\b", block):
            signals |= {h[0].lower() + h[1:] for h in _HANDLER.findall(block)}
    return signals


def _qml_bridge_usage() -> dict[str, set[str]]:
    """{bridge uyesi: kullanan dosyalar}"""
    usage: dict[str, set[str]] = {}
    for qml_file in QML_DIR.rglob("*.qml"):
        source = strip_qml_comments(qml_file.read_text(encoding="utf-8"))
        names = set(_BRIDGE_REF.findall(source)) | _connections_handlers(source)
        for name in names:
            usage.setdefault(name, set()).add(qml_file.name)
    return usage


def test_every_bridge_member_used_by_qml_exists(qapp, session):
    bridge = QmlBridge(session)
    members = _members(bridge)

    missing = {name: sorted(files) for name, files in _qml_bridge_usage().items() if name not in members}

    assert missing == {}, f"QML'de kullanilan ama bridge'de olmayan uyeler: {missing}"


def test_qml_actually_uses_bridge(qapp):
    # Sozlesme testinin bos gecmemesi icin: regex gercek kullanimlari buluyor mu?
    usage = _qml_bridge_usage()

    assert len(usage) > 40
    assert "searchArticles" in usage and "savedSearchApplied" in usage  # Connections yolu da yakalaniyor


def test_comments_are_not_counted_as_usage():
    source = "// bridge.eskiSlot()\n/* bridge.digerEski */\nbridge.gercek()"

    assert set(_BRIDGE_REF.findall(strip_qml_comments(source))) == {"gercek"}
