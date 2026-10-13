"""Bilgi Havuzu > Matris: literatur matrisi koprusu (suzgec, tazeleme, disa aktarim) ve gercek QML (tablo, tiklama)."""
import pytest
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest

from tests.test_pdfkit.test_commands import selection_of
from tests.test_pdfkit.test_pool_and_export import env  # noqa: F401  (fixture)
from tests.test_qml.qml_harness import click, find_item, find_named, open_window, pump, walk
from ui_qml.bridges.synthesis_bridge import REFRESH_MS


@pytest.fixture()
def matrix_env(env):
    """(bridge, resource, notlar): kaynakta 'tilki' Bulgu (#hipotez), 'tembel' Yontem alintilari."""
    bridge, pdf_resource, _web, reader = env
    bridge.pdf.addHighlight(selection_of(reader, "tilki"), "finding")
    bridge.pdf.addHighlight(selection_of(reader, "tembel"), "method")
    annotations = bridge.ctx.pdf_library.annotations()
    finding = next(a for a in annotations.list_highlights(bridge.pdf.currentDocument["documentId"]) if a.label_key == "finding")
    annotations.set_tags(finding.id, ["hipotez"])
    toasts = []
    bridge.notificationEmitted.connect(lambda kind, text: toasts.append((kind, text)))
    return bridge, pdf_resource, toasts


def _cells(matrix):
    return {c["key"]: [len(row["cells"][i]) for row in matrix["rows"]] for i, c in enumerate(matrix["columns"])}


# ---- kopru ----


def test_the_matrix_is_loaded_when_the_tab_becomes_active_with_one_row_per_pdf(matrix_env):
    bridge, resource, _toasts = matrix_env
    assert bridge.synthesis.matrix["rowCount"] == 0  # sekme gorunur olana kadar veritabanina gidilmez

    bridge.synthesis.setActive(True)

    matrix = bridge.synthesis.matrix
    assert [c["key"] for c in matrix["columns"]] == ["important", "finding", "method", "concept", "critique", "general"]
    assert matrix["rowCount"] == 1 and matrix["rows"][0]["resourceId"] == resource.id and matrix["annotationCount"] == 2
    assert _cells(matrix) == {"important": [0], "finding": [1], "method": [1], "concept": [0], "critique": [0], "general": [0]}
    assert bridge.synthesis.tags == [{"name": "hipotez", "count": 1}]
    assert "tilki" in matrix["rows"][0]["cells"][1][0]["text"] and matrix["rows"][0]["cells"][1][0]["pageLabel"] == "s. 1"


def test_label_tag_and_title_filters_combine_and_clear(matrix_env):
    bridge, _resource, _toasts = matrix_env
    bridge.synthesis.setActive(True)
    synthesis = bridge.synthesis

    synthesis.toggleLabel("method")
    assert [c["key"] for c in synthesis.matrix["columns"]] == ["method"] and synthesis.matrix["annotationCount"] == 1 and synthesis.filtered
    synthesis.setTag("hipotez")  # yontem alintisinin etiketi yok
    assert synthesis.matrix["rowCount"] == 0 and synthesis.tag == "hipotez"
    synthesis.toggleLabel("method")  # yontem suzgeci kalkti: tum sutunlar, yalniz #hipotez
    assert synthesis.matrix["annotationCount"] == 1 and synthesis.activeLabels == []
    synthesis.setTag("#Hipotez")  # ayni etiket tekrar: suzgec kalkar (normalize edilir)
    synthesis.setTitleQuery("hicbirkaynakadinda")
    assert synthesis.matrix["rowCount"] == 0 and synthesis.titleQuery == "hicbirkaynakadinda"
    synthesis.clearFilters()

    assert synthesis.matrix["annotationCount"] == 2 and not synthesis.filtered and synthesis.tag == ""
    synthesis.toggleLabel("uydurma")  # bilinmeyen etiket yok sayilir
    assert not synthesis.filtered


def test_title_filter_matches_title_and_citekey_ignoring_case_and_turkish_letters(matrix_env):
    bridge, resource, _toasts = matrix_env
    bridge.synthesis.setActive(True)

    bridge.synthesis.setTitleQuery(resource.title.upper())
    assert bridge.synthesis.matrix["rowCount"] == 1
    bridge.synthesis.setTitleQuery("ŞİMDİOLMAYAN")
    assert bridge.synthesis.matrix["rowCount"] == 0


def test_filter_changes_do_not_touch_the_database(matrix_env, monkeypatch):
    bridge, _resource, _toasts = matrix_env
    bridge.synthesis.setActive(True)
    reads = []
    original = type(bridge.ctx.pdf_library.synthesis()).rows
    monkeypatch.setattr(type(bridge.ctx.pdf_library.synthesis()), "rows", lambda self: (reads.append(1), original(self))[1])

    bridge.synthesis.toggleLabel("finding")
    bridge.synthesis.setTag("hipotez")
    bridge.synthesis.setTitleQuery("x")
    bridge.synthesis.clearFilters()

    assert reads == []


def test_content_changes_refresh_an_active_matrix_once_and_an_inactive_one_only_when_shown(matrix_env, monkeypatch):
    bridge, resource, _toasts = matrix_env
    reads = []
    original = type(bridge.ctx.pdf_library.synthesis()).rows
    monkeypatch.setattr(type(bridge.ctx.pdf_library.synthesis()), "rows", lambda self: (reads.append(1), original(self))[1])

    bridge.pdf.contentChanged.emit(resource.id)  # sekme gorunur degil: okuma yok
    QTest.qWait(REFRESH_MS + 80)
    assert reads == []
    bridge.synthesis.setActive(True)  # gorununce yuklenir
    assert len(reads) == 1
    for _ in range(3):
        bridge.pdf.contentChanged.emit(resource.id)
    QTest.qWait(REFRESH_MS + 150)

    assert len(reads) == 2  # art arda degisiklikler tek tazelemeye birlesti


def test_the_filtered_matrix_is_exported_as_markdown_with_a_filter_note(matrix_env, tmp_path):
    bridge, _resource, toasts = matrix_env
    bridge.synthesis.setActive(True)
    bridge.synthesis.toggleLabel("finding")
    target = tmp_path / "matris.md"

    bridge.synthesis.exportMarkdown(target.as_uri())

    text = target.read_text(encoding="utf-8")
    assert text.startswith("# Literatür Matrisi") and "_1 kaynak · 1 alıntı_" in text and "_Süzgeç: Bulgu / Sonuç_" in text
    assert "| Kaynak | Bulgu / Sonuç |" in text and "tilki" in text and "tembel" not in text
    assert toasts[-1][0] == "info"


def test_copy_puts_the_same_markdown_on_the_clipboard_and_empty_matrices_export_nothing(matrix_env, tmp_path):
    bridge, _resource, toasts = matrix_env
    bridge.synthesis.setActive(True)

    bridge.synthesis.copyMarkdown()
    assert QGuiApplication.clipboard().text() == bridge.synthesis.markdown() and "tilki" in QGuiApplication.clipboard().text()
    bridge.synthesis.setTitleQuery("hicbirkaynakadinda")
    target = tmp_path / "bos.md"
    bridge.synthesis.exportMarkdown(target.as_uri())

    assert not target.exists() and toasts[-1] == ("info", "Dışa aktarılacak alıntı yok.")


def test_opening_an_annotation_opens_the_reader_and_jumps_to_it(matrix_env):
    bridge, resource, _toasts = matrix_env
    bridge.synthesis.setActive(True)
    item = bridge.synthesis.matrix["rows"][0]["cells"][2][0]  # Yontem hucresi

    bridge.synthesis.openAnnotation(resource.id, item["page"], item["uid"])
    bridge.pdf.openDocument(resource.id)  # QML'siz testte okuyucu QML'in yaptigi gibi belgeyi acar

    assert bridge.currentView == "pdfReader" and bridge.pdf.jumpTarget["annotationId"] == item["id"]


# ---- gercek QML ----


def _open_matrix(qapp, bridge):
    engine, window = open_window(qapp, bridge, "knowledge", width=1500, height=900)
    click(qapp, window, find_named(window, "matrixTab"))
    pump(qapp, 30)
    return engine, window


def _visible(window, name):
    return [i for i in walk(window.contentItem()) if i.objectName() == name and i.isVisible()]


def test_the_tab_shows_the_table_with_filter_chips_and_filters_on_click(matrix_env, qapp):
    bridge, resource, _toasts = matrix_env
    engine, window = _open_matrix(qapp, bridge)

    assert find_named(window, "matrixSummary").property("text") == "1 kaynak · 2 alıntı"
    assert len(_visible(window, "matrixLabelChip")) == 6 and len(_visible(window, "matrixTagChip")) == 1
    assert [r.property("text") for r in _visible(window, "matrixRowTitle")] == [resource.title]
    assert len(_visible(window, "matrixQuote")) == 2 and len(_visible(window, "matrixCell")) == 6

    click(qapp, window, _visible(window, "matrixLabelChip")[2])  # Yontem
    pump(qapp, 20)
    assert find_named(window, "matrixSummary").property("text") == "1 kaynak · 1 alıntı (süzülmüş)"
    assert len(_visible(window, "matrixCell")) == 1 and find_named(window, "clearMatrixFiltersButton").property("visible")

    click(qapp, window, find_named(window, "clearMatrixFiltersButton"))
    pump(qapp, 20)
    assert len(_visible(window, "matrixQuote")) == 2
    assert engine.captured_warnings == []


def test_clicking_a_quote_opens_the_pdf_reader_on_that_annotation(matrix_env, qapp):
    bridge, resource, _toasts = matrix_env
    engine, window = _open_matrix(qapp, bridge)
    quotes = _visible(window, "matrixQuote")
    method_quote = next(q for q in quotes if any("tembel" in str(i.property("text")) for i in walk(q)))

    click(qapp, window, method_quote)
    QTest.qWait(600)
    pump(qapp, 30)

    assert bridge.currentView == "pdfReader" and bridge.reader.currentReaderResource["id"] == resource.id
    assert bridge.pdf.jumpTarget["annotationId"] != 0
    assert engine.captured_warnings == []


def test_an_empty_library_explains_how_to_fill_the_matrix_and_disables_export(env, qapp):
    bridge, _pdf, _web, _reader = env
    engine, window = open_window(qapp, bridge, "knowledge", width=1500, height=900)
    click(qapp, window, find_named(window, "matrixTab"))
    pump(qapp, 30)

    assert "Henüz alıntı yok" in find_named(window, "matrixEmpty").property("text")
    assert not find_named(window, "exportMatrixButton").property("enabledState")
    assert engine.captured_warnings == []


def test_the_search_box_filters_sources_on_the_matrix_tab(matrix_env, qapp):
    bridge, _resource, _toasts = matrix_env
    engine, window = _open_matrix(qapp, bridge)
    bar = find_item(window, lambda i: i.property("placeholder") == "Kaynak ara (başlık, atıf anahtarı)...")

    bar.setProperty("text", "hicbirkaynakadinda")
    pump(qapp, 20)
    assert find_named(window, "matrixEmpty").property("text") == "Süzgeçlerle eşleşen alıntı yok."

    bar.setProperty("text", "")
    pump(qapp, 20)
    assert len(_visible(window, "matrixQuote")) == 2 and engine.captured_warnings == []
