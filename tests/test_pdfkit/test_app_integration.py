"""pdfkit'in uygulamaya baglandigi noktalar: kaynak katalogu adaptoru ve PDF ice aktarma bildirimleri/zenginlestirme."""
import pytest
from pypdf import PdfWriter

from core.constants.strings import AppStrings
from pdfkit.api import LegacyPdf
from services.paper_market_service import PaperResult
from tests.pdf_factory import write_text_pdf
from tests.test_qml.qml_harness import SyncThreadPool
from ui_qml.bridge import QmlBridge
from ui_qml.pdf_catalog import ResourceCatalog

DOI_LINES = ["Derin ogrenme uzerine bir calisma. Kaynak: https://doi.org/10.1038/nature14539 yayinlanmistir."]


@pytest.fixture()
def bridge(qapp, session, monkeypatch, tmp_path):
    storage = tmp_path / "pdfs"
    storage.mkdir()
    monkeypatch.setattr("ui_qml.pdf_files.pdf_storage_dir", lambda: storage)
    b = QmlBridge(session)
    b.ctx.thread_pool = SyncThreadPool()
    monkeypatch.setattr(b.ctx.extractor, "schedule", lambda *args: None)
    return b


def _notes(bridge):
    notes = []
    bridge.notificationEmitted.connect(lambda kind, message: notes.append((kind, message)))
    return notes


def _paper(title="Deep learning"):
    return PaperResult(
        title=title, authors=["Y. LeCun"], year=2015, citation_count=9000, url=None, abstract=None,
        doi="10.1038/nature14539", openalex_id="W2919115771", venue="Nature",
    )


def test_doi_found_in_pdf_enriches_metadata_and_replaces_filename_title(bridge, monkeypatch, tmp_path):
    monkeypatch.setattr(
        "workers.paper_metadata_worker.PaperMarketService.find_paper_strict",
        lambda self, doi=None, title=None: _paper() if doi == "10.1038/nature14539" else None,
    )
    notes = _notes(bridge)
    source = write_text_pdf(tmp_path / "taslak-dosya.pdf", DOI_LINES)

    bridge.library.importLocalPdf(source.as_uri())

    (resource,) = bridge.controllers.resources.load_resources_with_filters({})
    assert resource.title == "Deep learning"  # baslik dosya adiydi -> makale basligi
    assert resource.extra_metadata["doi"] == "10.1038/nature14539"
    assert resource.extra_metadata["authors"] == ["Y. LeCun"]
    assert resource.extra_metadata["original_filename"] == "taslak-dosya.pdf"
    assert ("info", AppStrings.NOTIFICATION_PAPER_METADATA_SAVED) in notes


def test_user_given_title_is_not_overwritten_by_lookup(bridge, monkeypatch, tmp_path):
    monkeypatch.setattr(
        "workers.paper_metadata_worker.PaperMarketService.find_paper_strict",
        lambda self, doi=None, title=None: _paper(),
    )
    source = write_text_pdf(tmp_path / "taslak.pdf", DOI_LINES)
    bridge.library.importLocalPdf(source.as_uri())
    (resource,) = bridge.controllers.resources.load_resources_with_filters({})
    bridge.controllers.resources.update_resource(resource.id, {"title": "Benim Basligim"})

    bridge.library._importer._on_paper_found(resource.id, _paper("Baska Baslik"), "")

    (again,) = bridge.controllers.resources.load_resources_with_filters({})
    assert again.title == "Benim Basligim"


def test_unreachable_lookup_is_silent_and_keeps_the_import(bridge, monkeypatch, tmp_path):
    def _down(self, doi=None, title=None):
        raise OSError("ag yok")

    monkeypatch.setattr("workers.paper_metadata_worker.PaperMarketService.find_paper_strict", _down)
    notes = _notes(bridge)

    bridge.library.importLocalPdf(write_text_pdf(tmp_path / "a.pdf", DOI_LINES).as_uri())

    (resource,) = bridge.controllers.resources.load_resources_with_filters({})
    assert resource.title == "a"
    assert not any(kind == "error" for kind, _ in notes)


def test_pdf_without_text_layer_warns_the_user(bridge, tmp_path):
    notes = _notes(bridge)
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=400)
    scanned = tmp_path / "tarama.pdf"
    with open(scanned, "wb") as handle:
        writer.write(handle)

    bridge.library.importLocalPdf(scanned.as_uri())

    assert ("info", AppStrings.NOTIFICATION_PDF_NO_TEXT_LAYER) in notes
    (resource,) = bridge.controllers.resources.load_resources_with_filters({})
    assert bridge.ctx.pdf_library.documents().document_for_resource(resource.id).has_text_layer is False


def test_importing_the_same_pdf_twice_reports_duplicate_and_succeeds(bridge, tmp_path):
    notes = _notes(bridge)
    results = []
    bridge.library.pdfImportFinished.connect(results.append)
    bridge.library.importLocalPdf(write_text_pdf(tmp_path / "bir.pdf").as_uri())
    bridge.library.importLocalPdf(write_text_pdf(tmp_path / "iki.pdf").as_uri())

    assert results == [True, True]
    assert len(bridge.controllers.resources.load_resources_with_filters({})) == 1
    assert ("info", AppStrings.NOTIFICATION_PDF_DUPLICATE_FMT.format(title="iki")) in notes


def test_catalog_lists_and_repoints_legacy_pdfs(session, tmp_path):
    from controllers.resource_controller import ResourceController

    controller = ResourceController(session)
    catalog = ResourceCatalog(controller)
    legacy_file = write_text_pdf(tmp_path / "eski.pdf")
    by_url = controller.add_resource({"title": "U", "url": legacy_file.as_uri(), "tag_names": []})
    web = controller.add_resource(
        {"title": "W", "url": "https://arxiv.org/pdf/1", "tag_names": [], "extra_metadata": {"local_pdf": str(legacy_file)}}
    )
    controller.add_resource({"title": "Diger", "url": "https://example.com/yazi", "tag_names": []})

    items = catalog.legacy_pdfs()

    assert sorted((i.resource_id, i.field) for i in items) == sorted([(by_url.id, "url"), (web.id, "local_pdf")])
    new_path = tmp_path / "yeni.pdf"
    assert catalog.repoint(LegacyPdf(by_url.id, legacy_file, "url"), new_path)
    assert catalog.repoint(LegacyPdf(web.id, legacy_file, "local_pdf"), new_path)
    assert controller.get_resource(by_url.id).url == new_path.as_uri()
    assert controller.get_resource(web.id).extra_metadata["local_pdf"] == str(new_path)
    assert not catalog.repoint(LegacyPdf(99999, legacy_file, "local_pdf"), new_path)


def test_catalog_describes_a_resource_for_the_vault_note(bridge):
    catalog = ResourceCatalog(bridge.controllers.resources)
    resource = bridge.controllers.resources.add_resource(
        {"title": "Deep learning", "url": "https://x.org/dl", "category_id": None, "priority": 2,
         "extra_metadata": {"authors": ["Y. LeCun", "Y. Bengio"], "year": "2015", "doi": "10.1038/nature14539"}}
    )

    info = catalog.describe(resource.id)

    assert (info.title, info.authors, info.year, info.doi) == ("Deep learning", ("Y. LeCun", "Y. Bengio"), 2015, "10.1038/nature14539")
    assert info.status and info.url == "https://x.org/dl"
    assert catalog.describe(99999) is None


def test_catalog_describe_tolerates_missing_or_odd_metadata_and_hides_local_file_urls(bridge, tmp_path):
    catalog = ResourceCatalog(bridge.controllers.resources)
    resource = bridge.controllers.resources.add_resource(
        {"title": "Yerel", "url": (tmp_path / "x.pdf").as_uri(), "category_id": None, "priority": 2,
         "extra_metadata": {"authors": "Tek Yazar", "year": "yok"}}
    )

    info = catalog.describe(resource.id)

    assert info.authors == ("Tek Yazar",) and info.year is None and info.doi is None and info.url is None
