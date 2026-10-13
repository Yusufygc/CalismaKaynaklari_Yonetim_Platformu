"""Kunye otomatik doldurma (ice aktarma + Ayarlar > Kunye): acik/kapali ayari, yalniz bos alanlar, yanlis makale korumasi."""
from io import BytesIO

import pytest
from pypdf import PdfReader, PdfWriter

from core.constants.strings import AppStrings
from services.paper_market_service import PaperResult
from tests.pdf_factory import write_text_pdf
from tests.test_qml.qml_harness import SyncThreadPool, click, find_named, open_window, pump
from ui_qml.bridge import QmlBridge

BODY = "Bu makale yeterince uzun bir govde metni tasir ki metin katmani algilansin ve dogrulansin."
DOI = "10.1234/abcd.5678"


class FakeOpenAlex:
    """`PaperMarketService` yerine gecer; gelen DOI/baslik cagrilarini kaydeder."""

    calls: list = []
    result: PaperResult | Exception | None = None

    def find_paper_strict(self, doi=None, title=None):
        FakeOpenAlex.calls.append((doi, title))
        if isinstance(FakeOpenAlex.result, Exception):
            raise FakeOpenAlex.result
        return FakeOpenAlex.result


def _paper(title="Makine Ogrenmesi Uzerine Bir Derleme"):
    return PaperResult(
        title=title, authors=["Ada Yazar", "Can Yazar"], year=2024, citation_count=7, url=None, abstract=None,
        doi=DOI, openalex_id="W42", venue="Bilim Dergisi",
    )


@pytest.fixture()
def env(qapp, session, tmp_path, monkeypatch):
    storage = tmp_path / "depo"
    storage.mkdir()
    monkeypatch.setattr("ui_qml.pdf_files.pdf_storage_dir", lambda: storage)
    monkeypatch.setattr("workers.paper_metadata_worker.PaperMarketService", FakeOpenAlex)
    FakeOpenAlex.calls, FakeOpenAlex.result = [], _paper()
    bridge = QmlBridge(session)
    bridge.ctx.thread_pool = SyncThreadPool()
    monkeypatch.setattr(bridge.ctx.extractor, "schedule", lambda *args: None)
    toasts = []
    bridge.notificationEmitted.connect(lambda kind, text: toasts.append((kind, text)))
    return bridge, tmp_path, toasts


def _import(bridge, tmp_path, name="taslak-dosya", doi=DOI, title=None):
    """Metin PDF'i ice aktarir; `title` verilirse PDF'in gomulu basligi olur."""
    path = write_text_pdf(tmp_path / f"{name}.pdf", [f"Baslik satiri doi: {doi}", BODY])
    if title:
        writer = PdfWriter(clone_from=PdfReader(BytesIO(path.read_bytes())))
        writer.add_metadata({"/Title": title})
        with open(path, "wb") as handle:
            writer.write(handle)
    before = {r.id for r in bridge.controllers.resources.load_resources_with_filters({})}
    bridge.library.importLocalPdf(path.as_uri())
    return next(r for r in bridge.controllers.resources.load_resources_with_filters({}) if r.id not in before)


def test_it_is_on_by_default_and_fills_a_new_pdf_keeping_the_import_origin(env):
    bridge, tmp_path, toasts = env

    resource = _import(bridge, tmp_path)

    assert bridge.metadata.autoFill is True
    assert FakeOpenAlex.calls == [(DOI, None)]  # yalniz DOI gider; basliktan tahmin yok
    meta = resource.extra_metadata
    assert meta["authors"] == ["Ada Yazar", "Can Yazar"] and meta["year"] == 2024 and meta["openalex_id"] == "W42"
    assert meta["source"] == "local_pdf" and meta["original_filename"] == "taslak-dosya.pdf"  # koken bilgisi ezilmez
    assert ("info", AppStrings.NOTIFICATION_PAPER_METADATA_SAVED) in toasts


def test_turning_it_off_sends_nothing_anywhere_and_the_choice_is_persisted(env):
    bridge, tmp_path, toasts = env
    changes = []
    bridge.metadata.autoFillChanged.connect(lambda: changes.append(1))

    bridge.metadata.setAutoFill(False)
    resource = _import(bridge, tmp_path)

    assert bridge.ctx.user_settings.get("auto_metadata") is False and not bridge.metadata.autoFill and changes == [1]
    assert FakeOpenAlex.calls == [] and "authors" not in resource.extra_metadata
    assert not any(text == AppStrings.NOTIFICATION_PAPER_METADATA_SAVED for _kind, text in toasts)
    bridge.metadata.setAutoFill(True)
    assert bridge.metadata.autoFill


def test_a_paper_that_contradicts_the_pdfs_own_title_is_not_written(env):
    bridge, tmp_path, toasts = env
    FakeOpenAlex.result = _paper("A Survey of Reinforcement Learning Methods")  # DOI atif yapilan baska bir makaleye ait

    resource = _import(bridge, tmp_path, title="Kuantum Hesaplama Uzerine Bir Calisma")

    assert FakeOpenAlex.calls and "authors" not in resource.extra_metadata
    assert resource.title == "Kuantum Hesaplama Uzerine Bir Calisma"  # baslik da degismez
    assert not any(text == AppStrings.NOTIFICATION_PAPER_METADATA_SAVED for _kind, text in toasts)


def test_a_matching_embedded_title_is_accepted(env):
    bridge, tmp_path, _toasts = env

    resource = _import(bridge, tmp_path, title="Makine Ogrenmesi Uzerine Bir Derleme Calismasi")

    assert resource.extra_metadata["authors"] == ["Ada Yazar", "Can Yazar"]


def test_without_an_embedded_title_the_lookup_is_trusted_as_before_and_replaces_a_filename_title(env):
    bridge, tmp_path, _toasts = env

    resource = _import(bridge, tmp_path, name="taslak-dosya")

    assert resource.title == "Makine Ogrenmesi Uzerine Bir Derleme"


def test_a_network_failure_or_an_unknown_doi_is_silent(env):
    bridge, tmp_path, toasts = env

    FakeOpenAlex.result = RuntimeError("ag yok")
    first = _import(bridge, tmp_path, name="bir", doi="10.1234/bir")
    FakeOpenAlex.result = None
    second = _import(bridge, tmp_path, name="iki", doi="10.9999/bulunamadi")

    assert len(FakeOpenAlex.calls) == 2
    assert "authors" not in first.extra_metadata and "authors" not in second.extra_metadata
    assert not any(kind == "error" for kind, _ in toasts)


def test_fields_already_present_are_never_overwritten(env):
    bridge, tmp_path, _toasts = env
    resource = _import(bridge, tmp_path)
    bridge.controllers.resources.update_resource(
        resource.id, {"extra_metadata": {**resource.extra_metadata, "authors": ["Elle Girilen"], "year": None}}
    )

    bridge.library._importer._on_paper_found(resource.id, _paper(), "")

    meta = bridge.controllers.resources.get_resource(resource.id).extra_metadata
    assert meta["authors"] == ["Elle Girilen"] and meta["year"] == 2024


def test_nothing_is_written_or_announced_when_there_is_nothing_new_to_fill(env):
    bridge, tmp_path, toasts = env
    resource = _import(bridge, tmp_path)
    toasts.clear()

    bridge.library._importer._on_paper_found(resource.id, _paper(), "")  # her sey zaten dolu

    assert toasts == []


def test_pdfs_without_a_doi_do_not_trigger_a_lookup(env):
    bridge, tmp_path, _toasts = env
    path = write_text_pdf(tmp_path / "doisiz.pdf", ["Baslik satiri", BODY])

    bridge.library.importLocalPdf(path.as_uri())

    assert FakeOpenAlex.calls == []


def test_the_settings_tab_shows_the_state_and_toggles_it(env, qapp):
    bridge, _tmp, _toasts = env
    engine, window = open_window(qapp, bridge, "settings", width=1300, height=800)
    click(qapp, window, find_named(window, "metadataTab"))
    pump(qapp, 30)
    assert find_named(window, "autoMetadataStateText").property("text") == "Açık"

    click(qapp, window, find_named(window, "autoMetadataButton"))
    pump(qapp, 20)

    assert find_named(window, "autoMetadataStateText").property("text") == "Kapalı" and not bridge.metadata.autoFill
    assert find_named(window, "autoMetadataButton").property("text") == "Etkinleştir"
    assert engine.captured_warnings == []
