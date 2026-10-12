"""Atif metni, makale metadatasi, iliskili makaleler ve Markdown disa aktarim."""
from services.paper_market_service import PaperResult
from services.schemas import HighlightPosition
from ui_qml.bridge import QmlBridge


def _paper_resource(bridge):
    return bridge.controllers.resources.add_resource(
        {
            "title": "Attention Is All You Need",
            "url": "https://doi.org/10.5555/3295222.3295349",
            "category_id": None,
            "priority": 2,
            "extra_metadata": {
                "authors": ["Ashish Vaswani", "Noam Shazeer"],
                "year": 2017,
                "venue": "NeurIPS",
                "doi": "10.5555/3295222.3295349",
                "openalex_id": "W2626778328",
            },
        }
    )


def test_qml_bridge_citation_text_and_copy(qapp, session):
    from PySide6.QtGui import QGuiApplication

    bridge = QmlBridge(session)
    res = _paper_resource(bridge)
    notifications = []
    bridge.notificationEmitted.connect(lambda t, m: notifications.append((t, m)))

    apa = bridge.citations.citationText(res.id, "apa")
    assert apa.startswith("Vaswani, A., & Shazeer, N. (2017). Attention Is All You Need.")
    assert bridge.citations.citationText(res.id, "bogus") == ""
    assert bridge.citations.citationText(9999, "apa") == ""

    bridge.citations.copyCitation(res.id, "bibtex")
    assert QGuiApplication.clipboard().text().startswith("@article{vaswani2017attention,")
    assert notifications[-1] == ("info", "Atıf panoya kopyalandı (BIBTEX).")


def test_qml_bridge_paper_metadata_merges_into_extra_metadata(qapp, session):

    bridge = QmlBridge(session)
    res = bridge.controllers.resources.add_resource(
        {"title": "Makale", "url": "https://arxiv.org/pdf/1", "category_id": None, "priority": 2,
         "extra_metadata": {"local_pdf": "x"}}
    )
    paper = PaperResult(title="Makale", authors=["A. Yazar"], year=2020, citation_count=5, url=None,
                        abstract=None, doi="10.1/abc", openalex_id="W1", venue="Dergi")

    bridge.citations._on_paper_metadata_finished(res.id, paper, "")

    meta = bridge.controllers.resources.get_resource(res.id).extra_metadata
    assert meta["local_pdf"] == "x"
    assert meta["doi"] == "10.1/abc" and meta["openalex_id"] == "W1" and meta["venue"] == "Dergi"


def test_qml_bridge_paper_metadata_errors_surface_as_toasts(qapp, session):
    bridge = QmlBridge(session)
    res = _paper_resource(bridge)
    notifications = []
    bridge.notificationEmitted.connect(lambda t, m: notifications.append((t, m)))

    bridge.citations._on_paper_metadata_finished(res.id, None, "timeout")
    bridge.citations._on_paper_metadata_finished(res.id, None, "")

    assert notifications[0][0] == "error"
    assert notifications[1][0] == "info" and "bulunamadı" in notifications[1][1]


def test_qml_bridge_related_papers_loading_and_stale_result_ignored(qapp, session, monkeypatch):

    bridge = QmlBridge(session)
    started = []
    monkeypatch.setattr(bridge.ctx.thread_pool, "start", lambda worker: started.append(worker))
    res = _paper_resource(bridge)

    bridge.citations.loadRelatedPapers(res.id)
    assert len(started) == 2
    assert bridge.citations.relatedPapers["references"]["loading"] is True

    paper = PaperResult(title="Ref", authors=[], year=2016, citation_count=9, url="https://x", abstract=None,
                        openalex_id="W9")
    bridge.citations._on_related_papers_finished("W2626778328", "references", [paper], "")
    assert bridge.citations.relatedPapers["references"]["loaded"] is True
    assert bridge.citations.relatedPapers["references"]["items"][0]["openalexId"] == "W9"

    bridge.citations._on_related_papers_finished("W2626778328", "citations", [], "boom")
    assert bridge.citations.relatedPapers["citations"]["error"] != ""

    # Baska makale acilmisken gelen eski sonuc yok sayilir.
    bridge.citations._on_related_papers_finished("W-OTHER", "references", [paper], "")
    assert bridge.citations.relatedPapers["references"]["items"][0]["title"] == "Ref"


def test_qml_bridge_related_papers_without_openalex_id_starts_nothing(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    started = []
    monkeypatch.setattr(bridge.ctx.thread_pool, "start", lambda worker: started.append(worker))
    res = bridge.controllers.resources.add_resource({"title": "T", "url": "https://x.org/a", "category_id": None, "priority": 2})

    bridge.citations.loadRelatedPapers(res.id)

    assert started == []
    assert bridge.citations.relatedPapers["openalexId"] == ""


def test_qml_bridge_export_markdown_writes_file_and_adds_extension(qapp, session, tmp_path):
    bridge = QmlBridge(session)
    res = _paper_resource(bridge)
    bridge.controllers.highlights.create_highlight(res.id, "onemli cumle", "#22C55E", HighlightPosition(0, 1, 5))
    notifications = []
    bridge.notificationEmitted.connect(lambda t, m: notifications.append((t, m)))

    target = tmp_path / "literatur"
    bridge.reader.exportResourceMarkdown(res.id, (tmp_path / "literatur").as_uri())

    written = tmp_path / "literatur.md"
    assert written.exists()
    text = written.read_text(encoding="utf-8")
    assert "# Attention Is All You Need" in text and "“onemli cumle” (s. 1)" in text
    assert notifications[-1] == ("info", "Dışa aktarıldı: literatur.md")
    assert not target.exists()


def test_qml_bridge_export_library_empty_notifies(qapp, session, tmp_path):
    bridge = QmlBridge(session)
    notifications = []
    bridge.notificationEmitted.connect(lambda t, m: notifications.append((t, m)))

    bridge.reader.exportLibraryMarkdown((tmp_path / "hepsi.md").as_uri())

    assert not (tmp_path / "hepsi.md").exists()
    assert notifications[-1][0] == "info"


def test_qml_bridge_export_write_failure_is_reported(qapp, session, tmp_path):
    bridge = QmlBridge(session)
    res = _paper_resource(bridge)
    bridge.controllers.highlights.create_highlight(res.id, "x", "#22C55E", HighlightPosition(0, 1, 1))
    notifications = []
    bridge.notificationEmitted.connect(lambda t, m: notifications.append((t, m)))

    bridge.reader.exportResourceMarkdown(res.id, (tmp_path / "yok_klasor" / "a.md").as_uri())

    assert notifications[-1][0] == "error"
