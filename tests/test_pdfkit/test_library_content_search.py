"""Kutuphane listesi arama kutusu: varsayilan baslik/URL/not; acilirsa PDF'lerin icindeki metinde de arar."""
from PySide6.QtTest import QTest

from tests.test_pdfkit.test_search_bridge import FILLER, _import, bridge  # noqa: F401  (fixture)

PAGES = [[f"Birinci sayfa papatya bahcesi hakkinda bir metin. {FILLER}"], [f"Ikinci sayfa baska konular. {FILLER}"]]


def _count(bridge):
    return bridge.library.resourcesModel.rowCount()


def _filter(bridge, keyword):
    bridge.library.applyFilter(keyword, "0", "0", "ALL", False)


def test_the_box_ignores_pdf_text_by_default_and_finds_it_once_content_search_is_on(bridge, tmp_path):
    _import(bridge, tmp_path, "belge", PAGES)
    _import(bridge, tmp_path, "baskasi", [[f"Hic ilgisiz bir metin sayfasi. {FILLER}"]])

    _filter(bridge, "papatya")
    assert _count(bridge) == 0  # yalniz baslik/URL/not; PDF metnine bakmaz

    bridge.library.setSearchInContent(True)  # acilinca acik arama kendiliginden yenilenir
    assert bridge.library.searchInContent and _count(bridge) == 1

    bridge.library.setSearchInContent(False)
    assert _count(bridge) == 0


def test_a_title_match_and_a_content_match_are_both_listed_and_other_filters_still_apply(bridge, tmp_path):
    _import(bridge, tmp_path, "belge", PAGES)
    _import(bridge, tmp_path, "papatyabasligi", [[f"Hic ilgisiz bir metin sayfasi. {FILLER}"]])
    bridge.library.setSearchInContent(True)

    _filter(bridge, "papatya")
    assert _count(bridge) == 2  # biri baslikta, biri PDF metninde

    bridge.library.applyFilter("papatya", "0", "0", "COMPLETED", False)  # durum suzgeci hala uygulanir
    assert _count(bridge) == 0


def test_an_empty_keyword_or_a_failing_content_search_never_breaks_the_list(bridge, tmp_path, monkeypatch):
    _import(bridge, tmp_path, "belge", PAGES)
    bridge.library.setSearchInContent(True)
    _filter(bridge, "")
    assert _count(bridge) == 1

    def broken(*args, **kwargs):
        raise RuntimeError("bozuk")

    monkeypatch.setattr(type(bridge.ctx.pdf_library.searching()), "search_by_resource", broken)
    _filter(bridge, "belge")  # baslik eslesmesi yine calisir
    assert _count(bridge) == 1
    QTest.qWait(10)
