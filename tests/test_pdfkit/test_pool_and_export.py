"""PDF (pdfkit) ve HTML makale (eski tablolar) alintilarinin Bilgi Havuzu'nda birlesmesi, anahtarla silme,
cekmece ozeti ve Markdown disa aktarimi: uygulama genelindeki tuketiciler pdfkit verisini goruyor mu?"""
import pytest
from PySide6.QtPdf import QPdfDocument
from PySide6.QtTest import QTest

from core.constants.strings import AppStrings
from tests.pdf_factory import write_text_pdf
from tests.test_pdfkit.test_commands import selection_of
from tests.test_qml.qml_harness import SyncThreadPool
from ui_qml.bridge import QmlBridge


@pytest.fixture()
def env(qapp, session, tmp_path, monkeypatch):
    storage = tmp_path / "depo"
    storage.mkdir()
    monkeypatch.setattr("ui_qml.pdf_files.pdf_storage_dir", lambda: storage)
    bridge = QmlBridge(session)
    bridge.ctx.thread_pool = SyncThreadPool()
    monkeypatch.setattr(bridge.ctx.extractor, "schedule", lambda *args: None)
    bridge.library.importLocalPdf(write_text_pdf(tmp_path / "makale.pdf").as_uri())
    pdf_resource = next(r for r in bridge.controllers.resources.load_resources_with_filters({}) if r.url.startswith("file:"))
    bridge.market.saveMarketResult({"title": "Web makalesi", "url": "https://x.org/a"})
    web_resource = next(r for r in bridge.controllers.resources.load_resources_with_filters({}) if r.url.startswith("https:"))
    bridge.pdf.openDocument(pdf_resource.id)
    reader = QPdfDocument()
    reader.load(str(bridge.ctx.pdf_library.file_path(bridge.ctx.pdf_library.documents().document_for_resource(pdf_resource.id))))
    return bridge, pdf_resource, web_resource, reader


def _notes(bridge):
    notes = []
    bridge.notificationEmitted.connect(lambda kind, text: notes.append((kind, text)))
    return notes


def test_pool_merges_pdf_and_html_highlights_with_namespaced_keys(env):
    bridge, pdf_resource, web_resource, reader = env
    bridge.pdf.addHighlight(selection_of(reader, "tilki"), "finding")
    bridge.controllers.highlights.create_highlight(web_resource.id, "web alintisi", "#EAB308")

    bridge.annotations.reload_highlights()

    by_key = {h["key"]: h for h in bridge.annotations.highlights}
    pdf_item = next(h for key, h in by_key.items() if key.startswith("pdf:"))
    html_item = next(h for key, h in by_key.items() if key.startswith("html:"))
    assert pdf_item["resource_title"] == pdf_resource.title and "tilki" in pdf_item["content"]
    assert pdf_item["label"] == "Bulgu / Sonuç" and html_item["resource_title"] == "Web makalesi"


def test_writing_in_the_reader_refreshes_the_pool_once_after_a_short_delay(env):
    bridge, *_rest, reader = env
    changes = []
    bridge.annotations.highlightsChanged.connect(lambda: changes.append(1))

    bridge.pdf.addHighlight(selection_of(reader, "tilki"), "finding")
    bridge.pdf.addHighlight(selection_of(reader, "tembel"), "method")
    assert changes == []  # hemen degil: yazma yolunu bloklamaz
    QTest.qWait(350)

    assert len(changes) == 1  # art arda yazmalar tek tazelemeye birlesti
    assert len([h for h in bridge.annotations.highlights if h["key"].startswith("pdf:")]) == 2


def test_pool_delete_routes_by_key_for_single_and_bulk_with_a_single_notification(env):
    bridge, _pdf, web_resource, reader = env
    bridge.pdf.addHighlight(selection_of(reader, "tilki"), "finding")
    bridge.pdf.addHighlight(selection_of(reader, "tembel"), "method")
    bridge.controllers.highlights.create_highlight(web_resource.id, "web alintisi", "#EAB308")
    bridge.annotations.reload_highlights()
    keys = [h["key"] for h in bridge.annotations.highlights]
    assert len(keys) == 3
    notes = _notes(bridge)

    bridge.annotations.deleteHighlight(next(k for k in keys if k.startswith("html:")))
    bridge.annotations.deleteHighlights([k for k in keys if k.startswith("pdf:")])

    assert bridge.annotations.highlights == []
    assert notes[-1] == ("info", AppStrings.NOTIFICATION_HIGHLIGHTS_DELETED_FMT.format(count=2))
    assert bridge.ctx.pdf_library.annotations().list_highlights(bridge.pdf.currentDocument["documentId"]) == []


def test_pool_delete_ignores_malformed_keys_and_reports_missing_pdf_items(env):
    bridge, *_rest = env
    notes = _notes(bridge)

    bridge.annotations.deleteHighlight("uydurma:5")
    bridge.annotations.deleteHighlight("pdf:abc")
    bridge.annotations.deleteHighlight("pdf:99999")  # yok: hata bildirimi, istisna degil

    assert notes[-1][0] == "error"


def test_terms_appear_in_the_vocabulary_pool_and_delete_by_key(env):
    bridge, pdf_resource, _web, reader = env
    bridge.pdf.addTerm(selection_of(reader, "tilki"), "fox")
    bridge.controllers.vocabulary.create_vocabulary(pdf_resource.id, "ubiquitous", "her yerde", "It is ubiquitous.")
    bridge.annotations.reload_vocabulary()

    words = {v["word"]: v for v in bridge.annotations.vocabulary}
    assert words["tilki"]["key"].startswith("pdf:") and words["ubiquitous"]["key"].startswith("html:")

    bridge.annotations.deleteVocabulary(words["tilki"]["key"])
    bridge.annotations.deleteVocabulary(words["ubiquitous"]["key"])
    assert bridge.annotations.vocabulary == []


def test_drawer_summary_uses_pdfkit_data_without_geometry_computation(env):
    bridge, pdf_resource, _web, reader = env
    bridge.pdf.addHighlight(selection_of(reader, "tilki"), "important")
    bridge.pdf.addNote(0, 10.0, 20.0, "not")

    bridge.library.selectResource(pdf_resource.id)

    selected = bridge.library.selectedResource
    assert [h["label"] for h in selected["highlights"]] == ["Önemli"]
    assert selected["pdfNotes"][0]["text"] == "not"
    assert "boundsPolygons" not in selected["highlights"][0]


def test_resource_markdown_export_reads_pdfkit_highlights_notes_and_terms(env, tmp_path):
    bridge, pdf_resource, _web, reader = env
    bridge.pdf.addHighlight(selection_of(reader, "tilki"), "finding")
    bridge.pdf.addNote(0, 10.0, 20.0, "Tekrar oku")
    bridge.pdf.addTerm(selection_of(reader, "tembel"), "lazy")
    target = tmp_path / "cikti.md"

    bridge.reader.exportResourceMarkdown(pdf_resource.id, target.as_uri())

    markdown = target.read_text(encoding="utf-8")
    assert "### Bulgu / Sonuç (1)" in markdown and "tilki" in markdown
    assert "- s. 1: Tekrar oku" in markdown
    assert "**tembel**: lazy" in markdown


def test_library_markdown_export_includes_pdf_and_html_resources(env, tmp_path):
    bridge, _pdf, web_resource, reader = env
    bridge.pdf.addHighlight(selection_of(reader, "tilki"), "finding")
    bridge.controllers.highlights.create_highlight(web_resource.id, "web alintisi", "#EAB308")
    target = tmp_path / "kutuphane.md"

    bridge.reader.exportLibraryMarkdown(target.as_uri())

    markdown = target.read_text(encoding="utf-8")
    assert "tilki" in markdown and "web alintisi" in markdown


def test_deleting_a_resource_removes_its_pdf_annotations_from_the_pool_after_refresh(env):
    bridge, pdf_resource, _web, reader = env
    bridge.pdf.addHighlight(selection_of(reader, "tilki"), "finding")
    bridge.pdf.closeDocument()  # acik belge dosyayi kilitler; okuyucu kapaninca oturum da kapanir
    reader.close()

    bridge.library.deleteResource(pdf_resource.id)
    bridge.annotations.reload_highlights()

    assert [h for h in bridge.annotations.highlights if h["key"].startswith("pdf:")] == []
