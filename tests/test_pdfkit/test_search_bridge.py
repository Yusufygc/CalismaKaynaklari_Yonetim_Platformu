"""bridge.contentSearch: bekletmeli arama, kaynaga gore gruplama, guvenli gosterim ve sonuca tiklayinca sayfaya gitme."""
import pytest
from PySide6.QtTest import QTest

from tests.pdf_factory import write_multipage_text_pdf
from tests.test_qml.qml_harness import SyncThreadPool
from ui_qml.bridge import QmlBridge
from ui_qml.bridges.search_bridge import DEBOUNCE_MS

FILLER = "bu cumle yeterince uzun bir metin olsun diye eklendi"
PAGES = [
    [f"Kuantum bilgisayarlar hakkinda giris bolumu. {FILLER}"],
    [f"Ikinci sayfa: cocuklarin ogrenme sekli ve motivasyon. {FILLER}"],
    [f"Ucuncu sayfa sonuc bolumudur. Kuantum ustunlugu tartisiliyor. {FILLER}"],
]


@pytest.fixture()
def bridge(qapp, session, tmp_path, monkeypatch):
    monkeypatch.setattr("ui_qml.context.AUTO_INDEX", True)
    storage = tmp_path / "depo"
    storage.mkdir()
    monkeypatch.setattr("ui_qml.pdf_files.pdf_storage_dir", lambda: storage)
    instance = QmlBridge(session)
    instance.ctx.thread_pool = SyncThreadPool()
    monkeypatch.setattr(instance.ctx.extractor, "schedule", lambda *args: None)
    return instance


def _import(bridge, tmp_path, name, pages):
    bridge.library.importLocalPdf(write_multipage_text_pdf(tmp_path / f"{name}.pdf", pages).as_uri())
    waited = 0
    while (bridge.ctx.text_indexer.status()["pending"] or waited == 0) and waited < 5000:
        QTest.qWait(20)
        waited += 20
    QTest.qWait(30)
    return next(r for r in bridge.controllers.resources.load_resources_with_filters({}) if r.title == name or name in (r.url or ""))


def _search(bridge, text):
    bridge.contentSearch.search(text)
    QTest.qWait(DEBOUNCE_MS + 80)
    return bridge.contentSearch.groups


def test_results_are_grouped_by_resource_with_page_numbers_and_highlighted_snippets(bridge, tmp_path):
    resource = _import(bridge, tmp_path, "kuantum", PAGES)

    (group,) = _search(bridge, "kuantum")

    assert group["resourceId"] == resource.id and group["more"] == 0
    assert sorted(hit["page"] for hit in group["hits"]) == [0, 2]
    assert all("<b>Kuantum</b>" in hit["html"] for hit in group["hits"])
    assert bridge.contentSearch.searched and bridge.contentSearch.query == "kuantum"


def test_typing_is_debounced_and_only_the_last_query_runs(bridge, tmp_path):
    _import(bridge, tmp_path, "kuantum", PAGES)
    runs = []
    original = bridge.ctx.pdf_library.searching().__class__.search_by_resource

    def counting(self, text, limit=60):
        runs.append(text)
        return original(self, text, limit)

    type(bridge.ctx.pdf_library.searching()).search_by_resource = counting
    try:
        for text in ("k", "ku", "kuan", "kuantum"):
            bridge.contentSearch.search(text)
        assert runs == [] and bridge.contentSearch.groups == []  # henuz calismadi: yazmayi bloklamaz
        QTest.qWait(DEBOUNCE_MS + 80)
    finally:
        type(bridge.ctx.pdf_library.searching()).search_by_resource = original

    assert runs == ["kuantum"]


def test_empty_query_clears_results_at_once_and_a_miss_is_reported_as_searched(bridge, tmp_path):
    _import(bridge, tmp_path, "kuantum", PAGES)
    assert _search(bridge, "kuantum")

    assert _search(bridge, "olmayankelimexyz") == [] and bridge.contentSearch.searched
    _search(bridge, "kuantum")
    bridge.contentSearch.search("   ")

    assert bridge.contentSearch.groups == [] and not bridge.contentSearch.searched  # hemen, bekleme olmadan


def test_page_text_is_escaped_so_it_cannot_inject_markup_into_the_result_list(bridge, tmp_path):
    _import(bridge, tmp_path, "etiketli", [[f"<img src=x onerror=1> & <b>kalin</b> kuantum {FILLER}"]])

    (group,) = _search(bridge, "kuantum")

    html = group["hits"][0]["html"]
    assert "<img" not in html and "&lt;img" in html and "&amp;" in html and "&lt;b&gt;kalin" in html
    assert "<b>kuantum</b>" in html  # yalniz eslesme vurgusu gercek <b>


def test_long_result_lists_show_five_pages_per_resource_and_count_the_rest(bridge, tmp_path):
    _import(bridge, tmp_path, "uzun", [[f"kuantum sayfa {i} {FILLER}"] for i in range(8)])

    (group,) = _search(bridge, "kuantum")

    assert len(group["hits"]) == 5 and group["more"] == 3


def test_clicking_a_hit_opens_the_reader_at_that_page(bridge, tmp_path):
    resource = _import(bridge, tmp_path, "kuantum", PAGES)
    _search(bridge, "kuantum")

    bridge.contentSearch.openHit(resource.id, 2)
    bridge.pdf.openDocument(resource.id)  # QML'siz testte okuyucu QML'in yaptigi gibi belgeyi acar

    assert bridge.currentView == "pdfReader" and bridge.reader.currentReaderResource["id"] == resource.id
    assert bridge.pdf.jumpTarget["page"] == 2


def test_the_open_search_is_refreshed_when_indexing_finishes_and_status_is_exposed(bridge, tmp_path):
    _import(bridge, tmp_path, "kuantum", PAGES)
    _search(bridge, "kuantum")
    bridge.contentSearch._groups = []  # sonuclar eskidi

    bridge.ctx.text_indexer.finished.emit()

    assert len(bridge.contentSearch.groups) == 1
    assert bridge.contentSearch.indexStatus["state"] == "idle"


def test_a_search_failure_shows_no_results_instead_of_raising(bridge, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("bozuk")

    monkeypatch.setattr(type(bridge.ctx.pdf_library.searching()), "search_by_resource", broken)

    assert _search(bridge, "kuantum") == [] and bridge.contentSearch.searched


def test_the_rest_count_is_the_real_total_even_when_the_candidate_limit_cut_the_hits(bridge, tmp_path):
    _import(bridge, tmp_path, "uzun", [[f"kuantum sayfa {i} {FILLER}"] for i in range(8)])

    (group,) = bridge.ctx.pdf_library.searching().search_by_resource("kuantum", limit=3)

    assert len(group.hits) == 3 and group.total == 8  # "+N sayfa daha" yanlis kucuk gorunmez


def test_show_all_expands_one_resource_to_every_matching_page(bridge, tmp_path):
    resource = _import(bridge, tmp_path, "uzun", [[f"kuantum sayfa {i} {FILLER}"] for i in range(8)])
    (group,) = _search(bridge, "kuantum")
    assert not group["expanded"] and group["more"] == 3

    bridge.contentSearch.expand(resource.id)

    (opened,) = bridge.contentSearch.groups
    assert opened["expanded"] and len(opened["hits"]) == 8 and opened["more"] == 0
    assert sorted(hit["page"] for hit in opened["hits"]) == list(range(8))
    bridge.contentSearch.expand(999999)  # bilinmeyen kaynak: hicbir sey olmaz
    assert len(bridge.contentSearch.groups) == 1


def test_scanned_pdfs_are_listed_as_unsearchable_and_text_pdfs_are_not(bridge, tmp_path):
    from tests.pdf_factory import write_outline_pdf

    text_resource = _import(bridge, tmp_path, "kuantum", PAGES)
    bridge.library.importLocalPdf(write_outline_pdf(tmp_path / "taranmis.pdf", ["A", "B"]).as_uri())  # metin katmani yok
    QTest.qWait(80)

    bridge.contentSearch.refreshUnsearchable()

    titles = [item["title"] for item in bridge.contentSearch.unsearchable]
    assert len(titles) == 1 and "taranmis" in titles[0].lower()
    assert text_resource.id not in [item["resourceId"] for item in bridge.contentSearch.unsearchable]


def test_a_result_that_arrives_after_a_newer_search_or_a_clear_is_dropped(bridge, tmp_path):
    _import(bridge, tmp_path, "kuantum", PAGES)
    assert _search(bridge, "kuantum")
    stale = bridge.contentSearch._request - 1  # daha eski bir aramanin gec gelen sonucu

    bridge.contentSearch._show(stale, [], None)
    assert bridge.contentSearch.groups  # yok sayildi

    pending = bridge.contentSearch._request
    bridge.contentSearch.search("   ")  # temizleme yoldaki aramayi gecersiz kilar
    bridge.contentSearch._show(pending, [], None)
    assert not bridge.contentSearch.searched
