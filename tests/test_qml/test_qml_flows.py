"""Gercek QML + gercek fare/klavye olaylariyla uctan uca akislar (offscreen).

Onceki hatalarin regresyon testleri: 'Tekrar dene' tiklamasini ust uste binen liste yutuyordu;
Bilgi Havuzu toplu silme ve kayitli arama akislari.
"""
import pytest
from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest

from services.paper_market_service import MarketPage, PaperResult
from tests.test_qml.qml_harness import (
    SyncThreadPool,
    click,
    drag,
    find_item,
    find_text,
    focus,
    open_window,
    pump,
    reader_document,
    type_text,
    white_page_box,
)
from ui_qml.bridge import QmlBridge


def _paper(n: int) -> PaperResult:
    return PaperResult(
        title=f"Makale {n}", authors=["Ada"], year=2024, citation_count=n, url=f"https://x.org/{n}",
        abstract="Ozet", doi=f"10.1/{n}", openalex_id=f"W{n}", author_ids=["A1"],
    )


@pytest.fixture()
def bridge(qapp, session, monkeypatch):
    b = QmlBridge(session)
    b.ctx.thread_pool = SyncThreadPool()
    monkeypatch.setattr(b.ctx.extractor, "schedule", lambda *args: None)
    return b


def _search_and_enter(app, window, text: str) -> None:
    focus(app, window, "topicInput")
    type_text(app, window, text)
    QTest.keyClick(window, Qt.Key_Return)
    pump(app, 30)


def test_market_retry_button_is_clickable_and_searches_again(qapp, bridge, monkeypatch):
    state = {"fail": True, "calls": 0}

    def fake_search(self, topic, filters=None):
        state["calls"] += 1
        if state["fail"]:
            return {kind: MarketPage(error="offline") for kind in ("recent", "popular", "cited")}
        return {"recent": MarketPage([_paper(1)], 1), "popular": MarketPage(), "cited": MarketPage()}

    monkeypatch.setattr("workers.market_search_worker.PaperMarketService.search", fake_search)
    engine, window = open_window(qapp, bridge, "articleMarket")

    _search_and_enter(qapp, window, "gan")
    assert state["calls"] == 1 and bridge.market.marketMeta["recent"]["error"] == "offline"

    state["fail"] = False
    retry = find_text(window, "Tekrar dene")
    assert retry is not None, "hata durumunda 'Tekrar dene' gorunmeli"
    click(qapp, window, retry)

    assert state["calls"] == 2  # tiklama listeye degil butona ulasti (eski hata: z-order)
    assert len(bridge.market.marketResults["recent"]) == 1
    assert engine.captured_warnings == []
    del engine


def test_market_bulk_selection_and_save_by_real_clicks(qapp, bridge, monkeypatch):
    monkeypatch.setattr(
        "workers.market_search_worker.PaperMarketService.search",
        lambda self, topic, filters=None: {
            "recent": MarketPage([_paper(1), _paper(2), _paper(3)], 3),
            "popular": MarketPage(), "cited": MarketPage(),
        },
    )
    engine, window = open_window(qapp, bridge, "articleMarket")
    _search_and_enter(qapp, window, "gan")
    view = window.findChild(QObject, "articleMarketView")

    assert view.property("selectionCount") == 0

    click(qapp, window, find_text(window, "Tümünü seç"))
    assert view.property("selectionCount") == 3

    click(qapp, window, find_text(window, "Seçilenleri Kaydet (3)"))

    assert bridge.library.resourcesModel.count == 3
    assert view.property("selectionCount") == 0
    del engine


def _walk_visible(window):
    from tests.test_qml.qml_harness import walk
    return [i for i in walk(window.contentItem()) if i.isVisible()]


def test_saved_search_flow_save_badge_run_and_delete(qapp, bridge, monkeypatch):
    monkeypatch.setattr(
        "workers.market_search_worker.PaperMarketService.search",
        lambda self, topic, filters=None: {
            "recent": MarketPage([_paper(1), _paper(2)], 2), "popular": MarketPage(), "cited": MarketPage(),
        },
    )
    engine, window = open_window(qapp, bridge, "articleMarket")
    _search_and_enter(qapp, window, "gan")

    click(qapp, window, find_text(window, "Aramayı kaydet"))
    type_text(qapp, window, "tez")
    QTest.keyClick(window, Qt.Key_Return)  # popup onAccepted -> Kaydet
    pump(qapp, 30)

    assert [(s["label"], s["tag"]) for s in bridge.searches.savedSearches] == [("gan", "tez")]
    assert bridge.searches.activeSavedSearchId == bridge.searches.savedSearches[0]["id"]
    assert find_text(window, "Aramayı kaydet") is None  # zaten kayitli: buton gizlendi

    bridge.controllers.saved_searches.record_saved_search_check(bridge.searches.savedSearches[0]["id"], 2)  # yeni yayin var
    pump(qapp, 10)
    chip = find_item(window, lambda i: i.property("text") == "gan  ·  2 yeni")
    assert chip is not None, "yeni yayin rozeti cipte gorunmeli"

    delete_button = find_item(window, lambda i: i.property("tooltip") == "Kayıtlı aramayı sil")
    click(qapp, window, delete_button)

    assert bridge.searches.savedSearches == [] and bridge.searches.activeSavedSearchId == 0
    del engine


def test_knowledge_pool_bulk_delete_with_confirmation(qapp, bridge):
    bridge.market.saveMarketResult({"title": "Kaynak", "url": "https://x.org/a"})
    resource = bridge.controllers.resources.load_resources_with_filters({})[0]
    for i in range(4):
        bridge.controllers.highlights.create_highlight(resource.id, f"alinti {i}", "#EAB308")
    bridge.annotations.reload_highlights()
    engine, window = open_window(qapp, bridge, "knowledge")
    view = find_item(window, lambda i: i.property("selectedCount") is not None)

    checkboxes = [i for i in _walk_visible(window) if i.property("checked") is not None]
    assert len(checkboxes) == 4
    click(qapp, window, checkboxes[0])
    click(qapp, window, checkboxes[1])
    assert view.property("selectedCount") == 2

    click(qapp, window, find_text(window, "Seçilenleri Sil (2)"))
    click(qapp, window, find_text(window, "Vazgeç"))  # onay penceresi: vazgec
    assert len(bridge.annotations.highlights) == 4

    click(qapp, window, find_text(window, "Seçilenleri Sil (2)"))
    click(qapp, window, find_text(window, "Sil (2)"))

    assert len(bridge.annotations.highlights) == 2
    assert view.property("selectedCount") == 0
    assert engine.captured_warnings == []
    del engine


def test_knowledge_pool_search_is_turkish_insensitive(qapp, bridge):
    bridge.market.saveMarketResult({"title": "Kaynak", "url": "https://x.org/a"})
    resource = bridge.controllers.resources.load_resources_with_filters({})[0]
    for content in ("İstanbul'un tarihi", "Isparta gülleri", "Şeker üretimi"):
        bridge.controllers.highlights.create_highlight(resource.id, content, "#EAB308")
    bridge.annotations.reload_highlights()
    engine, window = open_window(qapp, bridge, "knowledge")
    view = find_item(window, lambda i: i.property("selectedCount") is not None)

    def visible_cards(query: str) -> int:
        view.setProperty("searchQuery", query)
        pump(qapp, 10)
        return len([i for i in _walk_visible(window) if i.property("checked") is not None])

    from utils.text_utils import fold_tr
    assert visible_cards(fold_tr("ISTANBUL")) == 1
    assert visible_cards(fold_tr("ısparta")) == 1
    assert visible_cards(fold_tr("seker")) == 1
    assert visible_cards("yok boyle bir sey") == 0
    del engine


def test_pdf_reader_drag_selection_highlights_exactly_the_selected_word(qapp, bridge, monkeypatch, tmp_path):
    """Gercek fare surukleme: secilen kelime kaydedilir, konumu (sayfa + karakter indeksi) dogrudur.
    Onceki hatalar: highlight rastgele yere oturuyordu (piksel/pt karisikligi), 2.-3. highlight cokuyordu."""
    from tests.pdf_factory import write_text_pdf
    from tests.test_qml.qml_harness import walk

    storage = tmp_path / "depo"
    storage.mkdir()
    monkeypatch.setattr("ui_qml.pdf_files.pdf_storage_dir", lambda: storage)
    source = write_text_pdf(tmp_path / "makale.pdf")
    bridge.library.importLocalPdf(source.as_uri())
    resource = bridge.controllers.resources.load_resources_with_filters({})[0]
    engine, window = open_window(qapp, bridge, "showcase", width=1400, height=900)
    bridge.reader.openReader(resource.id)
    pump(qapp, 150)

    from PySide6.QtCore import QMetaObject

    page_area = window.findChild(QObject, "pageArea")
    for _ in range(2):  # %100 disinda: piksel/pt karisikligi ancak zoom != 1 iken gorunur
        QMetaObject.invokeMethod(page_area, "zoomIn")
    pump(qapp, 60)

    doc = reader_document(bridge)
    page_w = doc.pagePointSize(0).width()
    x_left, x_right, y_top = white_page_box(window)
    scale = (x_right - x_left) / page_w
    assert scale > 1.2, f"zoom uygulanmadi (olcek {scale:.2f})"
    page_text = doc.getSelectionAtIndex(0, 0, 100000).text()

    for word in ("tilki", "paragrafin", "kopegin"):  # ardisik 3 alinti: coken senaryo
        start = page_text.index(word)
        rect = doc.getSelectionAtIndex(0, start, len(word)).boundingRectangle()
        y = int(y_top + (rect.y() + rect.height() / 2) * scale)
        drag(qapp, window, int(x_left + (rect.x() + 1) * scale), int(x_left + (rect.x() + rect.width() + 1) * scale), y)

        toolbar = next(i for i in walk(window.contentItem()) if i.objectName() == "newHighlightToolbar" and i.isVisible())
        from PySide6.QtCore import QPoint, QPointF
        dot = next(i for i in walk(toolbar) if i.objectName() == "pdfHighlightDot")  # ilk renk (Onemli)
        bounds = toolbar.property("capturedBounds")
        assert bounds.width() > 0 and bounds.height() > 0  # secimin gercek sinir kutusu yakalandi
        above, below = toolbar.y() + toolbar.height() <= bounds.y(), toolbar.y() >= bounds.y() + bounds.height()
        assert above or below, "arac cubugu secili metnin ustune binmemeli"
        assert abs(dot.mapToScene(dot.boundingRect().center()).y() - toolbar.mapToScene(toolbar.boundingRect().center()).y()) <= 2  # dikey ortada
        scene = dot.mapToScene(QPointF(dot.width() / 2, dot.height() / 2))
        QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, QPoint(int(scene.x()), int(scene.y())))
        pump(qapp, 30)

    highlights = bridge.ctx.pdf_library.annotations().list_highlights(bridge.pdf.currentDocument["documentId"])
    assert len(highlights) == 3
    for word, h in zip(("tilki", "paragrafin", "kopegin"), sorted(highlights, key=lambda h: h.id)):
        # Sinir karakteri Qt'nin secim kuralina baglidir (+-1 bosluk olabilir); onemli olan konumun metinle tutarliligi.
        segment = h.segments[0]
        assert word in h.quote_exact
        assert len(h.quote_exact.strip()) <= len(word) + 1
        assert segment.page == 0
        assert page_text[segment.start:segment.end].strip() == h.quote_exact.strip()  # kalici konum secilen metni gosteriyor
        assert abs(segment.start - page_text.index(word)) <= 1
    assert engine.captured_warnings == []
    del engine


def test_every_page_renders_with_data_and_no_qml_warnings(qapp, bridge, tmp_path, monkeypatch):
    """Bridge bolunmesi gibi buyuk degisikliklerde QML'de `undefined` baglama hatasi kalmasin:
    her sayfa gercek veriyle (kaynak, kategori, etiket, alinti, kelime, PDF) acilir, uyari cikmamali."""
    from PySide6.QtCore import QMetaObject

    from tests.pdf_factory import write_text_pdf

    storage = tmp_path / "depo"
    storage.mkdir()
    monkeypatch.setattr("ui_qml.pdf_files.pdf_storage_dir", lambda: storage)
    bridge.settings.createCategory("Makale", "#123456", "")
    bridge.settings.createTag("ai")
    web = bridge.controllers.resources.add_resource(
        {"title": "Web makalesi", "url": "https://example.org/a", "category_id": None, "priority": 2,
         "tag_names": ["ai"], "content": "kelime " * 300}
    )
    bridge.library.importLocalPdf(write_text_pdf(tmp_path / "a.pdf").as_uri())
    pdf = next(r for r in bridge.controllers.resources.load_resources_with_filters({}) if r.url.startswith("file://"))
    bridge.controllers.highlights.create_highlight(web.id, "web alintisi", "#EAB308")
    bridge.controllers.vocabulary.create_vocabulary(web.id, "kelime", "word", "cumle")
    engine, window = open_window(qapp, bridge, "showcase")

    click(qapp, window, find_item(window, lambda i: i.property("cardWidth") is not None))  # kart -> cekmece
    QMetaObject.invokeMethod(window.findChild(QObject, "resourceFormModal"), "openForNew")
    pump(qapp, 20)
    for view in ("settings", "knowledge", "articleMarket", "showcase"):
        bridge.setCurrentView(view)
        pump(qapp, 20)
    bridge.reader.openReader(web.id)      # HTML okuyucu
    pump(qapp, 30)
    bridge.reader.openReader(pdf.id)      # native PDF okuyucu
    pump(qapp, 80)

    assert bridge.currentView == "pdfReader"
    assert engine.captured_warnings == [], engine.captured_warnings
    del engine


def test_market_save_keeps_scroll_position(qapp, bridge, monkeypatch):
    """Regresyon: makale kaydedince kutuphane bayragi listeyi yeniden atip basa sariyordu."""
    monkeypatch.setattr(
        "workers.market_search_worker.PaperMarketService.search",
        lambda self, topic, filters=None: {
            "recent": MarketPage([_paper(i) for i in range(1, 31)], 30), "popular": MarketPage(), "cited": MarketPage(),
        },
    )
    engine, window = open_window(qapp, bridge, "articleMarket")
    _search_and_enter(qapp, window, "gan")
    results = find_item(window, lambda i: i.objectName() == "resultsList")
    results.setProperty("contentY", 900)
    pump(qapp, 20)
    y_before = results.property("contentY")
    assert y_before > 500

    def on_screen_save_button(item):  # kaydirilan listede ekranda gorunen kart
        if item.property("text") != "Kaydet":
            return False
        y = item.mapToScene(item.boundingRect().center()).y()
        return 250 < y < 850

    save_button = find_item(window, on_screen_save_button)
    click(qapp, window, save_button)

    assert len(bridge.controllers.resources.load_resources_with_filters({})) == 1
    assert abs(results.property("contentY") - y_before) < 5, "kayitta liste basa sarmamali"


def test_showcase_card_title_stays_inside_the_card(qapp, bridge):
    """Regresyon: Column padding'i baslik genisligine yansimadigi icin uzun basliklar karttan tasip kirpiliyordu."""
    title = "Makine Ogrenmesi Teknikleri Ile Hisse Senedi Fiyat Tahmini Uzun Baslik Deneme Metni"
    bridge.market.saveMarketResult({"title": title, "url": "https://x.org/a"})
    engine, window = open_window(qapp, bridge, "showcase")

    card = find_item(window, lambda i: i.property("cardWidth") is not None)
    title_item = find_item(window, lambda i: i.property("text") == title)
    card_right = card.mapToScene(card.boundingRect().topRight()).x()
    title_right = title_item.mapToScene(title_item.boundingRect().topRight()).x()

    assert title_right <= card_right - 8, "baslik karta sigmali (sag bosluk birakmali)"


def test_showcase_cards_fill_the_row_at_any_window_width(qapp, bridge):
    """Esnek hucre: kalan genislik kartlara dagitilir, sagda bosluk kalmaz; kart en az 274 px."""
    for i in range(6):
        bridge.controllers.resources.add_resource({"title": f"Kaynak {i}", "url": f"https://example.org/{i}", "category_id": None, "priority": 2})
    for width in (1000, 1280, 1500, 1900):
        engine, window = open_window(qapp, bridge, "showcase", width=width, height=800)
        pump(qapp, 20)
        grid = find_item(window, lambda i: i.property("minCellWidth") is not None)
        columns, cell, grid_width = grid.property("columns"), grid.property("cellWidth"), grid.width()
        assert columns >= 1 and grid_width - columns * cell < columns  # kalan en fazla sutun basina 1 px (yuvarlama)
        card = find_item(window, lambda i: i.property("cardWidth") is not None)
        assert card.property("cardWidth") == cell - 16 and card.property("cardWidth") >= 274
        assert engine.captured_warnings == []


def test_video_cards_show_a_play_badge_and_the_drawer_offers_to_open_the_video(qapp, bridge):
    bridge.controllers.resources.add_resource({"title": "Video", "url": "https://www.youtube.com/watch?v=abc123", "category_id": None, "priority": 2})
    engine, window = open_window(qapp, bridge, "showcase", width=1280, height=800)
    pump(qapp, 20)
    assert find_item(window, lambda i: i.objectName() == "videoBadge") is not None

    click(qapp, window, find_item(window, lambda i: i.property("cardWidth") is not None))
    pump(qapp, 30)
    button = find_item(window, lambda i: i.objectName() == "openReaderButton")
    assert button.property("text") == "Videoyu Aç" and engine.captured_warnings == []


def _walk_all(window):
    from tests.test_qml.qml_harness import walk
    return list(walk(window.contentItem()))


def test_knowledge_pool_top_bar_never_overlaps_at_any_window_width(qapp, bridge):
    for window_width in (960, 1078, 1280, 1700):
        engine, window = open_window(qapp, bridge, "knowledge", width=window_width, height=800)
        pump(qapp, 20)
        top = next(i for i in _walk_visible(window) if i.property("tabsWidth") is not None)
        tabs, search, export_width = top.property("tabsWidth"), top.property("searchWidth"), top.property("exportWidth")
        assert tabs >= 380 and search >= 150
        assert 24 + tabs + 16 + search + 16 <= top.width() - 24 - export_width, (window_width, tabs, search, export_width)
        assert engine.captured_warnings == []


def test_the_closed_inspector_drawer_stays_hidden_while_the_window_is_widened(qapp, bridge):
    engine, window = open_window(qapp, bridge, "showcase", width=1100, height=800)
    drawer = next(i for i in _walk_all(window) if i.property("drawerWidth") is not None)
    assert not drawer.isVisible() and drawer.x() >= drawer.parent().width()

    for width in (1200, 1400, 1700):
        window.setWidth(width)
        qapp.processEvents()  # animasyon beklenmeden: kapali cekmece her adimda ekranin disinda
        assert not drawer.isVisible() and drawer.x() >= drawer.parent().width()
    assert engine.captured_warnings == []


def test_scraped_page_title_fills_the_empty_title_field_but_never_overwrites_a_typed_one(qapp, bridge):
    from PySide6.QtCore import QMetaObject

    engine, window = open_window(qapp, bridge, "showcase", width=1280, height=800)
    QMetaObject.invokeMethod(window.findChild(QObject, "resourceFormModal"), "openForNew")
    pump(qapp, 20)
    modal = window.findChild(QObject, "resourceFormModal")
    title_inputs = [i for i in _walk_visible(window) if "TextInput" in i.metaObject().className() and i.property("text") == ""]
    title = title_inputs[-1]  # url ve baslik alanlarindan sonuncusu: baslik

    bridge.library.urlScraped.emit({"og_title": "Attention Is All You Need", "og_description": "x"})
    pump(qapp, 10)
    assert title.property("text") == "Attention Is All You Need"

    title.setProperty("text", "Benim basligim")
    bridge.library.urlScraped.emit({"og_title": "Baska bir baslik"})
    pump(qapp, 10)
    assert title.property("text") == "Benim basligim" and modal is not None and engine.captured_warnings == []
