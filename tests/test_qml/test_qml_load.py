"""QML guvenlik agi: her bilesen derlenir, main.qml uyarisiz yuklenir, QML'in cagirdigi bridge uyeleri gercekten var.

Bu testler Python testlerinin yakalayamadigi hata sinifini yakalar: yinelenen property, gecersiz
anchor, yanlis yazilmis/silinmis bridge slotu (bkz. 2026-09-29/30 QML hatalari).
"""
import re

import pytest
from PySide6.QtCore import QMetaMethod, QObject, QUrl
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


_BRIDGE_REF = re.compile(r"\bbridge\.(\w+)(?:\.(\w+))?")
_HANDLER = re.compile(r"function\s+on([A-Z]\w*)\s*\(")
_TARGET = re.compile(r"target:\s*bridge(?:\.(\w+))?\b")


def _connections_handlers(source: str) -> set[tuple[str, str]]:
    """`Connections { target: bridge[.alt] ... function onXyz }` bloklari: {(alt-bridge adi ya da '', sinyal adi)}."""
    signals: set[tuple[str, str]] = set()
    for match in re.finditer(r"Connections\s*\{", source):
        depth, i = 1, match.end()
        while i < len(source) and depth:
            depth += {"{": 1, "}": -1}.get(source[i], 0)
            i += 1
        block = source[match.start():i]
        target = _TARGET.search(block)
        if target:
            owner = target.group(1) or ""
            signals |= {(owner, h[0].lower() + h[1:]) for h in _HANDLER.findall(block)}
    return signals


def _qml_bridge_usage() -> dict[tuple[str, str], set[str]]:
    """{(kok uye, alt uye ya da ''): kullanan dosyalar}; Connections isleyicileri de dahil."""
    usage: dict[tuple[str, str], set[str]] = {}
    for qml_file in QML_DIR.rglob("*.qml"):
        source = strip_qml_comments(qml_file.read_text(encoding="utf-8"))
        refs = {(first, second or "") for first, second in _BRIDGE_REF.findall(source)}
        refs |= {(owner, signal) if owner else (signal, "") for owner, signal in _connections_handlers(source)}
        for ref in refs:
            usage.setdefault(ref, set()).add(qml_file.name)
    return usage


def _unresolved(bridge, usage) -> dict[str, list[str]]:
    """Kok bridge'de olmayan uyeler ile alt-bridge'de olmayan uyeler (yol: 'market.searchArticles')."""
    root_members = _members(bridge)
    missing: dict[str, list[str]] = {}
    for first, second in usage:
        if first not in root_members:
            missing[first] = sorted(usage[(first, second)])
            continue
        child = getattr(bridge, first, None)
        is_child_bridge = isinstance(child, QObject) and child is not bridge
        if is_child_bridge and second and second not in _members(child):
            missing[f"{first}.{second}"] = sorted(usage[(first, second)])
    return missing


def test_every_bridge_member_used_by_qml_exists(qapp, session):
    bridge = QmlBridge(session)

    missing = _unresolved(bridge, _qml_bridge_usage())

    assert missing == {}, f"QML'de kullanilan ama bridge'de olmayan uyeler: {missing}"


def test_qml_only_reaches_business_members_through_sub_bridges(qapp, session):
    """Is alani uyeleri (kaynak/okuyucu/market/ayarlar) yalnizca alt-bridge uzerinden kullanilmali;
    kok bridge yalnizca kabuk uyelerini (tema, sayfa, sade mod, bildirim, alt-bridge'ler) sunar."""
    bridge = QmlBridge(session)
    root_used = {first for (first, second) in _qml_bridge_usage() if second == "" or not isinstance(getattr(bridge, first, None), QObject)}

    shell = {"isDarkTheme", "currentView", "isSimpleMode", "toggleTheme", "setSimpleMode", "setCurrentView",
             "notificationEmitted", "isDarkThemeChanged", "currentViewChanged", "isSimpleModeChanged"}
    children = {"library", "reader", "market", "settings"}

    assert root_used - shell - children == set()


def test_qml_actually_uses_bridge(qapp):
    # Sozlesme testinin bos gecmemesi icin: regex gercek kullanimlari buluyor mu?
    usage = _qml_bridge_usage()

    assert len(usage) > 40
    assert ("market", "searchArticles") in usage
    assert ("market", "savedSearchApplied") in usage  # Connections yolu da yakalaniyor
    assert ("isDarkTheme", "") in usage


def test_connections_resolve_targets_to_the_right_sub_bridge():
    source = """
    Connections { target: bridge; function onNotificationEmitted(a, b) { x() } }
    Connections { target: bridge.library
        function onUrlScraped(m) { if (m) { y() } } }
    """

    assert _connections_handlers(source) == {("", "notificationEmitted"), ("library", "urlScraped")}


def test_comments_are_not_counted_as_usage():
    source = "// bridge.eskiSlot()\n/* bridge.digerEski */\nbridge.market.gercek()"

    assert set(_BRIDGE_REF.findall(strip_qml_comments(source))) == {("market", "gercek")}
