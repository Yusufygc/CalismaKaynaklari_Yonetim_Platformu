"""pkm:// derin baglantilari: komut satiri, yonlendirme, belge cozumleme ve gercek okuyucuda hedefe atlama."""
import pytest
from PySide6.QtCore import Q_RETURN_ARG, QMetaObject, Qt
from PySide6.QtTest import QTest

from pdfkit.api import build_open_link
from pdfkit.domain.annotations import Segment
from tests.pdf_factory import write_outline_pdf, write_text_pdf
from tests.test_qml.qml_harness import SyncThreadPool, find_named, open_window, pump
from ui_qml.bridge import QmlBridge
from ui_qml.deep_links import ACTIVATE_MESSAGE, extract_link_arg

PAGES = ["A", "B", "C", "D", "E", "F"]
LINK = "pkm://open?doc=abababab"

# ---- komut satiri ----


@pytest.mark.parametrize(
    "argv, expected",
    [
        (["main.py"], None),
        (["main.py", "--open", LINK], LINK),
        (["main.py", f"--open={LINK}"], LINK),
        (["pkm.exe", LINK], LINK),  # Windows kaydi uygulamayi dogrudan "%1" ile cagirir
        (["pkm.exe", "PKM://open?doc=abababab"], "PKM://open?doc=abababab"),
        (["main.py", "--open"], None),  # deger yok
        (["main.py", "--baska", "x", "https://example.org"], None),
    ],
)
def test_link_extraction_from_the_command_line(argv, expected):
    assert extract_link_arg(argv) == expected


# ---- yonlendirme ----


@pytest.fixture()
def env(qapp, session, tmp_path, monkeypatch):
    storage = tmp_path / "depo"
    storage.mkdir()
    monkeypatch.setattr("ui_qml.pdf_files.pdf_storage_dir", lambda: storage)
    bridge = QmlBridge(session)
    bridge.ctx.thread_pool = SyncThreadPool()
    monkeypatch.setattr(bridge.ctx.extractor, "schedule", lambda *args: None)
    bridge.library.importLocalPdf(write_outline_pdf(tmp_path / "altı-sayfa.pdf", PAGES).as_uri())
    bridge.library.importLocalPdf(write_text_pdf(tmp_path / "metinli.pdf").as_uri())
    resources = {r.title: r for r in bridge.controllers.resources.load_resources_with_filters({})}
    toasts, activations = [], []
    bridge.notificationEmitted.connect(lambda kind, text: toasts.append((kind, text)))
    bridge.windowActivationRequested.connect(lambda: activations.append(1))
    return bridge, resources, toasts, activations


def _document(bridge, resource):
    return bridge.ctx.pdf_library.documents().document_for_resource(resource.id)


def _annotation(bridge, resource, page, text="hedef alinti"):
    document = _document(bridge, resource)
    return bridge.ctx.pdf_library.annotations().create_highlight(
        document.id, text, [Segment(page, 0, len(text), text, [[(10.0, 100.0), (60.0, 100.0), (60.0, 112.0), (10.0, 112.0)]])],
        "finding", engine_fp="qtpdf-test",
    )


def test_a_valid_link_opens_the_pdf_reader_and_asks_for_the_window_to_come_forward(env):
    bridge, resources, _toasts, activations = env
    document = _document(bridge, resources["altı-sayfa"])

    assert bridge.deep_links.open_link(build_open_link(document.sha256, page=2))
    bridge.pdf.openDocument(resources["altı-sayfa"].id)  # QML'siz testte okuyucu QML'in yaptigi gibi belgeyi acar

    assert bridge.currentView == "pdfReader" and bridge.reader.currentReaderResource["id"] == resources["altı-sayfa"].id
    assert activations == [1]
    assert bridge.pdf.jumpTarget["page"] == 2 and bridge.pdf.jumpTarget["annotationId"] == 0


def test_a_link_with_an_annotation_resolves_page_position_and_focus(env):
    bridge, resources, _toasts, _activations = env
    annotation = _annotation(bridge, resources["altı-sayfa"], page=4)

    bridge.deep_links.open_link(build_open_link(_document(bridge, resources["altı-sayfa"]).sha256, page=0, ann_uid=annotation.uid))
    bridge.pdf.openDocument(resources["altı-sayfa"].id)

    target = bridge.pdf.jumpTarget
    assert (target["page"], target["annotationId"]) == (4, annotation.id)  # sayfa degeri alintinin gercek sayfasi
    assert target["y"] == pytest.approx(60.0) and bridge.pdf.focusedAnnotationId == annotation.id


def test_focus_highlight_clears_itself_after_a_moment(env):
    bridge, resources, _toasts, _activations = env
    annotation = _annotation(bridge, resources["altı-sayfa"], page=1)
    bridge.pdf._focus_timer.setInterval(30)

    bridge.deep_links.open_link(build_open_link(_document(bridge, resources["altı-sayfa"]).sha256, ann_uid=annotation.uid))
    bridge.pdf.openDocument(resources["altı-sayfa"].id)
    assert bridge.pdf.focusedAnnotationId == annotation.id
    QTest.qWait(120)

    assert bridge.pdf.focusedAnnotationId == 0


def test_page_notes_and_terms_can_be_link_targets_too(env):
    bridge, resources, _toasts, _activations = env
    resource = resources["altı-sayfa"]
    document = _document(bridge, resource)
    note = bridge.ctx.pdf_library.annotations().create_note(document.id, 3, 20.0, 200.0, "sayfa notu")

    bridge.deep_links.open_link(build_open_link(document.sha256, ann_uid=note.uid))
    bridge.pdf.openDocument(resource.id)

    assert (bridge.pdf.jumpTarget["page"], bridge.pdf.jumpTarget["y"]) == (3, pytest.approx(160.0))


def test_a_link_to_the_already_open_document_jumps_without_reopening(env):
    bridge, resources, _toasts, _activations = env
    resource = resources["altı-sayfa"]
    bridge.pdf.openDocument(resource.id)
    opened = []
    bridge.pdf.currentDocumentChanged.connect(lambda: opened.append(1))

    bridge.pdf.requestJump(resource.id, 3, "")

    assert bridge.pdf.jumpTarget["page"] == 3 and opened == []
    first = bridge.pdf.jumpTarget["token"]
    bridge.pdf.requestJump(resource.id, 3, "")
    assert bridge.pdf.jumpTarget["token"] == first + 1  # ayni hedefe tekrar atlanabilsin


def test_page_beyond_the_document_is_clamped_to_the_last_page(env):
    bridge, resources, _toasts, _activations = env
    document = _document(bridge, resources["altı-sayfa"])

    bridge.deep_links.open_link(build_open_link(document.sha256, page=99))
    bridge.pdf.openDocument(resources["altı-sayfa"].id)

    assert bridge.pdf.jumpTarget["page"] == len(PAGES) - 1


@pytest.mark.parametrize("url", ["", "http://example.org", "pkm://open", "pkm://open?doc=zzzz", "pkm://open?doc=abababab&evil=1", "pkm://open?doc=abababab&page=0"])
def test_invalid_links_are_rejected_with_a_message_and_open_nothing(env, url):
    bridge, _resources, toasts, activations = env

    assert not bridge.deep_links.open_link(url)

    assert toasts[-1] == ("error", "Bağlantı geçersiz: açılamadı.")
    assert bridge.currentView != "pdfReader" and activations == [] and bridge.pdf.jumpTarget == {}


def test_a_link_to_an_unknown_document_is_reported_and_opens_nothing(env):
    bridge, _resources, toasts, activations = env

    assert not bridge.deep_links.open_link("pkm://open?doc=0123456789abcdef&page=1")

    assert toasts[-1] == ("error", "Bağlantıdaki PDF kütüphanende bulunamadı.") and activations == []


def test_messages_from_a_second_instance_are_dispatched(env):
    bridge, resources, _toasts, activations = env
    document = _document(bridge, resources["metinli"])

    assert bridge.deep_links.handle_message(ACTIVATE_MESSAGE) and activations == [1]
    assert bridge.deep_links.handle_message(build_open_link(document.sha256, page=0))

    assert bridge.reader.currentReaderResource["id"] == resources["metinli"].id


def test_a_link_never_reads_or_opens_paths_given_in_the_link(env, tmp_path):
    bridge, _resources, toasts, _activations = env
    secret = tmp_path / "gizli.pdf"
    secret.write_bytes(b"%PDF-1.4")

    assert not bridge.deep_links.open_link(f"pkm://open?doc=abababab&file={secret.as_uri()}")  # bilinmeyen parametre

    assert toasts[-1][0] == "error" and bridge.currentView != "pdfReader"


# ---- gercek QML: okuyucu hedefe gider ----


def _first_visible_page(area) -> int:
    """Gorunumun ustunde gorunen ilk sayfa. Atlama hedef sayfanin 10 px ustunu gosterir (Qt'nin bosluk payi), bu yuzden
    ust satir bir onceki sayfanin dibine dusebilir: o durumda hedef sayfa bir sonraki sayfadir."""
    result = QMetaObject.invokeMethod(area, "topViewState", Qt.DirectConnection, Q_RETURN_ARG("QVariant"))
    top = result.toVariant()
    return top["page"] + 1 if top["y"] > 350 else top["page"]


def _wait_for(predicate, timeout=6000) -> None:
    """Kosul saglanana kadar bekler (sabit sure yerine: yuklu makinede atlama/yerlesim gecikebilir, cerceve ise yalniz
    ~2,5 sn gorunur)."""
    waited = 0
    while not predicate() and waited < timeout:
        QTest.qWait(30)
        waited += 30


def test_reader_jumps_to_the_linked_page_and_frames_the_linked_annotation(env, qapp):
    bridge, resources, _toasts, _activations = env
    resource = resources["altı-sayfa"]
    annotation = _annotation(bridge, resource, page=2)
    engine, window = open_window(qapp, bridge, "showcase", width=1400, height=900)

    bridge.deep_links.open_link(build_open_link(_document(bridge, resource).sha256, ann_uid=annotation.uid))

    def framed_on_target_page() -> bool:
        area, frame = find_named(window, "pageArea"), find_named(window, "focusFrame")
        return area is not None and frame is not None and bool(frame.property("visible")) and _first_visible_page(area) == 2

    _wait_for(framed_on_target_page)
    assert framed_on_target_page(), "baglantiyla acilan alinti hedef sayfada cerceveyle vurgulanmali"
    assert bridge.pdf.focusedAnnotationId == annotation.id
    assert engine.captured_warnings == []


def test_a_link_beats_the_saved_reading_position(env, qapp):
    bridge, resources, _toasts, _activations = env
    resource = resources["altı-sayfa"]
    bridge.pdf.openDocument(resource.id)
    bridge.ctx.pdf_library.reading().save(_document(bridge, resource).id, 5, 0.0, 0.0, 1.0)  # en son 6. sayfadaydi
    bridge.pdf.closeDocument()
    engine, window = open_window(qapp, bridge, "showcase", width=1400, height=900)

    bridge.deep_links.open_link(build_open_link(_document(bridge, resource).sha256, page=1))
    pump(qapp, 150)
    QTest.qWait(900)

    assert _first_visible_page(find_named(window, "pageArea")) == 1
    assert engine.captured_warnings == []
