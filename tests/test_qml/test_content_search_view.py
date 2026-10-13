"""Bilgi Havuzu > Metinde Ara (gercek QML): yazinca sonuc, tiklayinca okuyucu o sayfada acilir."""
from PySide6.QtTest import QTest

from tests.test_pdfkit.test_search_bridge import PAGES, _import, bridge  # noqa: F401  (fixture)
from tests.test_qml.qml_harness import click, find_item, find_named, open_window, pump, walk
from ui_qml.bridges.search_bridge import DEBOUNCE_MS


def _open_tab(qapp, bridge):
    engine, window = open_window(qapp, bridge, "knowledge", width=1400, height=900)
    click(qapp, window, find_named(window, "contentSearchTab"))
    pump(qapp, 10)
    return engine, window


def _type_query(qapp, window, text):
    bar = find_item(window, lambda i: i.property("placeholder") == "PDF'lerin içinde ara...")
    bar.setProperty("text", text)  # alias -> TextInput.onTextChanged -> searchChanged: gercek yol
    QTest.qWait(DEBOUNCE_MS + 120)
    pump(qapp, 20)


def _visible(window, name):
    return [i for i in walk(window.contentItem()) if i.objectName() == name and i.isVisible()]


def test_tab_explains_itself_until_something_is_typed_then_lists_grouped_hits(bridge, qapp, tmp_path):
    resource = _import(bridge, tmp_path, "kuantum", PAGES)
    engine, window = _open_tab(qapp, bridge)
    assert "Yukarıdaki kutuya" in find_named(window, "contentSearchEmpty").property("text")
    assert "Arama, PDF'lerin içindeki metinde" in find_named(window, "indexStatusText").property("text")

    _type_query(qapp, window, "kuantum")

    assert [t.property("text") for t in _visible(window, "groupTitle")] == [resource.title]
    rows = _visible(window, "hitRow")
    assert len(rows) == 2
    snippets = [s.property("text") for s in _visible(window, "hitSnippet")]
    assert all("<b>Kuantum</b>" in s for s in snippets)
    assert not find_named(window, "contentSearchEmpty").property("visible")
    assert engine.captured_warnings == []


def test_a_query_without_matches_says_so(bridge, qapp, tmp_path):
    _import(bridge, tmp_path, "kuantum", PAGES)
    engine, window = _open_tab(qapp, bridge)

    _type_query(qapp, window, "olmayankelimexyz")

    assert find_named(window, "contentSearchEmpty").property("text") == "Eşleşme bulunamadı."
    assert engine.captured_warnings == []


def test_clicking_a_hit_opens_the_pdf_reader_on_that_page(bridge, qapp, tmp_path):
    resource = _import(bridge, tmp_path, "kuantum", PAGES)
    engine, window = _open_tab(qapp, bridge)
    _type_query(qapp, window, "kuantum")
    third_page = next(r for r in _visible(window, "hitRow") if any(i.property("text") == "s. 3" for i in walk(r)))

    click(qapp, window, third_page)  # sonuc sirasi alaka puanina gore: satiri sayfa etiketinden bul
    QTest.qWait(600)
    pump(qapp, 30)

    assert bridge.currentView == "pdfReader" and bridge.reader.currentReaderResource["id"] == resource.id
    assert bridge.pdf.jumpTarget["page"] == 2
    assert engine.captured_warnings == []


def test_leaving_the_tab_clears_the_results_and_returning_searches_again(bridge, qapp, tmp_path):
    _import(bridge, tmp_path, "kuantum", PAGES)
    engine, window = _open_tab(qapp, bridge)
    _type_query(qapp, window, "kuantum")
    assert bridge.contentSearch.groups
    view = find_item(window, lambda i: i.property("rawQuery") is not None and i.property("activeTab") is not None)

    view.setProperty("activeTab", 0)  # Alintilar sekmesi
    pump(qapp, 10)
    assert bridge.contentSearch.groups == [] and bridge.contentSearch.query == ""
    view.setProperty("activeTab", 2)
    QTest.qWait(DEBOUNCE_MS + 120)
    pump(qapp, 10)

    assert len(bridge.contentSearch.groups) == 1  # sorgu (kutuda duruyor) yeniden arandi
    assert engine.captured_warnings == []


def test_the_more_link_expands_the_card_to_all_matching_pages(bridge, qapp, tmp_path):
    _import(bridge, tmp_path, "uzun", [[f"kuantum sayfa {i} bu cumle yeterince uzun bir metin olsun diye eklendi"] for i in range(8)])
    engine, window = _open_tab(qapp, bridge)
    _type_query(qapp, window, "kuantum")
    assert len(_visible(window, "hitRow")) == 5
    more = find_named(window, "moreHits")
    assert "tümünü göster" in more.property("text")

    click(qapp, window, more)
    pump(qapp, 20)

    assert len(_visible(window, "hitRow")) == 8
    assert not find_named(window, "moreHits").property("visible")
    assert engine.captured_warnings == []
