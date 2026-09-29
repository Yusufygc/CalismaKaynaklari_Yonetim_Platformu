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
    find_item,
    find_text,
    focus,
    open_window,
    pump,
    type_text,
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

    assert [(s["label"], s["tag"]) for s in bridge.market.savedSearches] == [("gan", "tez")]
    assert bridge.market.activeSavedSearchId == bridge.market.savedSearches[0]["id"]
    assert find_text(window, "Aramayı kaydet") is None  # zaten kayitli: buton gizlendi

    bridge.controllers.saved_searches.record_saved_search_check(bridge.market.savedSearches[0]["id"], 2)  # yeni yayin var
    pump(qapp, 10)
    chip = find_item(window, lambda i: i.property("text") == "gan  ·  2 yeni")
    assert chip is not None, "yeni yayin rozeti cipte gorunmeli"

    delete_button = find_item(window, lambda i: i.property("tooltip") == "Kayıtlı aramayı sil")
    click(qapp, window, delete_button)

    assert bridge.market.savedSearches == [] and bridge.market.activeSavedSearchId == 0
    del engine


def test_knowledge_pool_bulk_delete_with_confirmation(qapp, bridge):
    bridge.market.saveMarketResult({"title": "Kaynak", "url": "https://x.org/a"})
    resource = bridge.controllers.resources.load_resources_with_filters({})[0]
    for i in range(4):
        bridge.controllers.highlights.create_highlight(resource.id, f"alinti {i}", "#EAB308")
    bridge.reader.reload_highlights()
    engine, window = open_window(qapp, bridge, "knowledge")
    view = find_item(window, lambda i: i.property("selectedCount") is not None)

    checkboxes = [i for i in _walk_visible(window) if i.property("checked") is not None]
    assert len(checkboxes) == 4
    click(qapp, window, checkboxes[0])
    click(qapp, window, checkboxes[1])
    assert view.property("selectedCount") == 2

    click(qapp, window, find_text(window, "Seçilenleri Sil (2)"))
    click(qapp, window, find_text(window, "Vazgeç"))  # onay penceresi: vazgec
    assert len(bridge.reader.highlights) == 4

    click(qapp, window, find_text(window, "Seçilenleri Sil (2)"))
    click(qapp, window, find_text(window, "Sil (2)"))

    assert len(bridge.reader.highlights) == 2
    assert view.property("selectedCount") == 0
    assert engine.captured_warnings == []
    del engine


def test_knowledge_pool_search_is_turkish_insensitive(qapp, bridge):
    bridge.market.saveMarketResult({"title": "Kaynak", "url": "https://x.org/a"})
    resource = bridge.controllers.resources.load_resources_with_filters({})[0]
    for content in ("İstanbul'un tarihi", "Isparta gülleri", "Şeker üretimi"):
        bridge.controllers.highlights.create_highlight(resource.id, content, "#EAB308")
    bridge.reader.reload_highlights()
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


def _white_page_box(window) -> tuple[int, int, int]:
    """Goruntude beyaz PDF sayfasinin (sol x, sag x, ust y) piksel konumu."""
    from PySide6.QtGui import QImage

    image = window.grabWindow().convertToFormat(QImage.Format.Format_RGB32)

    def white(x, y):
        c = image.pixelColor(x, y)
        return c.red() > 250 and c.green() > 250 and c.blue() > 250

    xs = [x for x in range(240, image.width(), 2) if white(x, 450)]
    x_left, x_right = xs[0], xs[-1]
    ys = [y for y in range(60, image.height(), 2) if white((x_left + x_right) // 2, y)]
    return x_left, x_right, ys[0]


def _drag(app, window, x0: int, x1: int, y: int) -> None:
    from PySide6.QtCore import QPoint

    start, end = QPoint(x0, y), QPoint(x1, y)
    QTest.mouseMove(window, start)
    QTest.qWait(30)
    QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, start)
    QTest.qWait(30)
    for i in range(1, 11):
        QTest.mouseMove(window, QPoint(x0 + (x1 - x0) * i // 10, y))
        QTest.qWait(30)
    QTest.mouseRelease(window, Qt.LeftButton, Qt.NoModifier, end)
    QTest.qWait(100)


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

    doc = bridge.ctx.pdf_files.load_document(bridge.reader.currentReaderResource["pdfFileUrl"])
    page_w = doc.pagePointSize(0).width()
    x_left, x_right, y_top = _white_page_box(window)
    scale = (x_right - x_left) / page_w
    assert scale > 1.2, f"zoom uygulanmadi (olcek {scale:.2f})"
    page_text = doc.getSelectionAtIndex(0, 0, 100000).text()

    for word in ("tilki", "paragrafin", "kopegin"):  # ardisik 3 alinti: coken senaryo
        start = page_text.index(word)
        rect = doc.getSelectionAtIndex(0, start, len(word)).boundingRectangle()
        y = int(y_top + (rect.y() + rect.height() / 2) * scale)
        _drag(qapp, window, int(x_left + (rect.x() + 1) * scale), int(x_left + (rect.x() + rect.width() + 1) * scale), y)

        toolbar = next(i for i in walk(window.contentItem()) if i.objectName() == "newHighlightToolbar" and i.isVisible())
        from PySide6.QtCore import QPoint, QPointF
        scene = toolbar.mapToScene(QPointF(19, toolbar.property("height") / 2))
        QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, QPoint(int(scene.x()), int(scene.y())))
        pump(qapp, 30)

    highlights = bridge.controllers.highlights.load_resource_highlights(resource.id)
    assert len(highlights) == 3
    for word, h in zip(("tilki", "paragrafin", "kopegin"), sorted(highlights, key=lambda h: h.id)):
        # Sinir karakteri Qt'nin secim kuralina baglidir (+-1 bosluk olabilir); onemli olan konumun metinle tutarliligi.
        assert word in h.content
        assert len(h.content.strip()) <= len(word) + 1
        assert h.page_number == 0
        assert page_text[h.start_index:h.start_index + h.length].strip() == h.content.strip()  # kalici konum secilen metni gosteriyor
        assert abs(h.start_index - page_text.index(word)) <= 1
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
