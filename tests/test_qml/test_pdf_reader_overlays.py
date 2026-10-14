"""PDF okuyucunun sayfa katmanları (seçim araç çubuğu + kelime popover'ı, alıntı düzenleme popover'ı, not katmanı)
gerçek fare/klavye ile: PdfPageArea bileşenlere bölündükten sonra da uçtan uca çalıştıklarını doğrular."""
import pytest
from PySide6.QtCore import QObject, QPoint, QPointF, Qt
from PySide6.QtTest import QTest

from tests.pdf_factory import write_text_pdf
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
    walk,
    white_page_box,
)
from pdfkit.domain.annotations import STATUS_ORPHANED, STATUS_OK, Segment
from ui_qml.bridge import QmlBridge


class Reader:
    """Acik PDF okuyucu: sayfa konumu, koordinat donusumu ve yardimci eylemler."""

    def __init__(self, app, bridge, window, engine, doc, page_text, x_left, y_top, scale):
        self.app, self.bridge, self.window, self.engine = app, bridge, window, engine
        self.doc, self.page_text, self.x_left, self.y_top, self.scale = doc, page_text, x_left, y_top, scale

    def word_span(self, word):
        start = self.page_text.index(word)
        rect = self.doc.getSelectionAtIndex(0, start, len(word)).boundingRectangle()
        y = int(self.y_top + (rect.y() + rect.height() / 2) * self.scale)
        return int(self.x_left + (rect.x() + 1) * self.scale), int(self.x_left + (rect.x() + rect.width() + 1) * self.scale), y

    def select(self, word):
        x0, x1, y = self.word_span(word)
        drag(self.app, self.window, x0, x1, y)

    def visible(self, object_name):
        return find_item(self.window, lambda i: i.objectName() == object_name)

    def toolbar(self):
        return next(i for i in walk(self.window.contentItem()) if i.objectName() == "newHighlightToolbar" and i.isVisible())

    def click_first_swatch(self):
        toolbar = self.toolbar()
        dot = next(i for i in walk(toolbar) if i.objectName() == "pdfHighlightDot")  # ilk renk
        scene = dot.mapToScene(QPointF(dot.width() / 2, dot.height() / 2))
        QTest.mouseClick(self.window, Qt.LeftButton, Qt.NoModifier, QPoint(int(scene.x()), int(scene.y())))
        pump(self.app, 30)

    @property
    def annotations(self):
        """pdfkit alinti servisi (veritabanindaki gercek kayitlar)."""
        return self.bridge.ctx.pdf_library.annotations()

    @property
    def document_id(self):
        return self.bridge.pdf.currentDocument["documentId"]

    def type_into(self, object_name, text):
        focus(self.app, self.window, object_name)
        type_text(self.app, self.window, text)


@pytest.fixture()
def reader(qapp, session, tmp_path, monkeypatch):
    bridge = QmlBridge(session)
    bridge.ctx.thread_pool = SyncThreadPool()
    monkeypatch.setattr(bridge.ctx.extractor, "schedule", lambda *args: None)
    storage = tmp_path / "depo"
    storage.mkdir()
    monkeypatch.setattr("ui_qml.pdf_files.pdf_storage_dir", lambda: storage)
    bridge.library.importLocalPdf(write_text_pdf(tmp_path / "makale.pdf").as_uri())
    resource = bridge.controllers.resources.load_resources_with_filters({})[0]
    engine, window = open_window(qapp, bridge, "showcase", width=1400, height=900)
    bridge.reader.openReader(resource.id)
    pump(qapp, 150)
    doc = reader_document(bridge)
    x_left, x_right, y_top = white_page_box(window)
    scale = (x_right - x_left) / doc.pagePointSize(0).width()
    page_text = doc.getSelectionAtIndex(0, 0, 100000).text()
    yield Reader(qapp, bridge, window, engine, doc, page_text, x_left, y_top, scale), resource
    del engine


def test_vocabulary_popover_saves_word_with_translation_and_sentence_context(reader):
    view, resource = reader

    view.select("tilki")
    icon_button = find_item(view.window, lambda i: i.property("tooltip") == "Kelime Havuzuna Ekle")
    click(view.app, view.window, icon_button)
    assert view.visible("newVocabPopover") is not None, "kelime popover'i acilmali"
    view.type_into("vocabTranslationInput", "fox")
    click(view.app, view.window, find_text(view.window, "Kaydet"))

    (vocab,) = view.annotations.list_terms(view.document_id)
    assert vocab.word.strip() == "tilki" and vocab.translation == "fox"
    assert vocab.context_sentence.startswith("Hizli kahverengi tilki")
    assert vocab.segments[0].polygons  # konumla kaydedilir (eski kelimelerin aksine)
    assert view.visible("newVocabPopover") is None, "kaydedince popover kapanmali"


def test_clicking_a_saved_highlight_opens_editor_and_saves_comment_and_free_tags(reader):
    view, resource = reader
    view.select("kopegin")
    view.click_first_swatch()
    (highlight,) = view.annotations.list_highlights(view.document_id)
    assert view.visible("editHighlightPopover") is None

    hit_area = view.visible("highlightHitArea")
    assert hit_area is not None, "kalici alinti tiklama alani olusmali"
    click(view.app, view.window, hit_area)
    assert view.visible("editHighlightPopover") is not None, "alintiya tiklayinca duzenleme popover'i acilmali"
    view.type_into("editCommentInput", "onemli")
    view.type_into("editTagsInput", "#Hipotez, ornek , hipotez")
    click(view.app, view.window, find_text(view.window, "Kaydet"))

    (updated,) = view.annotations.list_highlights(view.document_id)
    assert updated.id == highlight.id and updated.comment == "onemli"
    assert updated.tags == ["hipotez", "ornek"]  # '#' atilir, kucuk harfe cevrilir, tekrar elenir
    assert view.visible("editHighlightPopover") is None


def test_note_mode_click_creates_a_page_note_and_marker_edits_it(reader):
    view, resource = reader
    page_area = view.window.findChild(QObject, "pageArea")
    page_area.setProperty("noteMode", True)
    pump(view.app, 10)

    blank = QPoint(int(view.x_left + 250 * view.scale), int(view.y_top + 450 * view.scale))  # metinsiz alan
    QTest.mouseClick(view.window, Qt.LeftButton, Qt.NoModifier, blank)
    pump(view.app, 20)
    assert view.visible("newNotePopover") is not None, "not modunda sayfaya tiklayinca popover acilmali"
    view.type_into("newNoteInput", "not")
    click(view.app, view.window, find_text(view.window, "Kaydet"))

    (note,) = view.annotations.list_notes(view.document_id)
    assert note.text == "not" and note.page == 0
    assert abs(note.x - 250) < 3 and abs(note.y - 450) < 3  # page-point uzayinda (piksel/zoom'dan bagimsiz)

    page_area.setProperty("noteMode", False)
    pump(view.app, 20)
    assert view.bridge.pdf.notes.count == 1
    assert view.engine.captured_warnings == []


def test_tapping_the_page_dismisses_open_popovers(reader):
    view, _resource = reader
    view.select("tilki")
    click(view.app, view.window, find_item(view.window, lambda i: i.property("tooltip") == "Kelime Havuzuna Ekle"))
    assert view.visible("newVocabPopover") is not None

    blank = QPoint(int(view.x_left + 300 * view.scale), int(view.y_top + 600 * view.scale))
    QTest.mouseClick(view.window, Qt.LeftButton, Qt.NoModifier, blank)
    pump(view.app, 20)

    assert view.visible("newVocabPopover") is None


def test_clicking_another_highlight_while_editor_is_open_keeps_the_new_editor_open(reader):
    """Regresyon: sayfa-dismiss TapHandler'i, alintiya tiklamayla acilan duzenleme popover'ini hemen kapatiyordu."""
    view, resource = reader
    for word in ("kopegin", "tilki"):
        view.select(word)
        view.click_first_swatch()
    ids = {h.id for h in view.annotations.list_highlights(view.document_id)}
    hit_areas = [i for i in walk(view.window.contentItem()) if i.objectName() == "highlightHitArea" and i.isVisible()]
    assert len(hit_areas) == 2

    click(view.app, view.window, hit_areas[0])
    first = view.visible("editHighlightPopover").property("highlightId")
    click(view.app, view.window, hit_areas[1])  # editor acikken baska alintiya tikla

    popover = view.visible("editHighlightPopover")
    assert popover is not None, "yeni alintinin duzenleme popover'i acik kalmali"
    assert popover.property("highlightId") in ids and popover.property("highlightId") != first


def _open_notebook_with_an_orphan(view):
    """Yan paneli 'Notlarim' sekmesinde acar; konumu bulunamayan (yetim) bir alinti hazirlar."""
    from tests.test_qml.qml_harness import find_named

    orphan = view.annotations.create_highlight(
        view.document_id, "belgede artik olmayan metin", [Segment(0, 1, 28, "belgede artik olmayan metin")],
        "critique", comment="eski yorum", tags=["yontem"], status=STATUS_ORPHANED,
    )
    view.bridge.pdf.openDocument(view.bridge.pdf.currentDocument["resourceId"])  # modeli yeniden yukle
    find_named(view.window, "pdfReaderView").setProperty("sidePanelOpen", True)
    find_named(view.window, "sidePanel").setProperty("activeTab", 2)
    pump(view.app, 60)
    _remeasure(view)
    return orphan


def _remeasure(view):
    """Yan panel acilinca sayfa alani daralir ve sayfa kayar: sahne koordinatlari yeniden olculur."""
    x_left, x_right, y_top = white_page_box(view.window)
    view.x_left, view.y_top = x_left, y_top
    view.scale = (x_right - x_left) / view.doc.pagePointSize(0).width()


def test_orphan_is_listed_in_the_notebook_and_relinking_to_a_new_selection_reattaches_it(reader):
    view, _resource = reader
    orphan = _open_notebook_with_an_orphan(view)
    assert view.visible("orphanFilterChip") is not None, "yetim varken suzgec cipi gorunmeli"
    assert view.visible("relinkBanner") is None

    click(view.app, view.window, view.visible("relinkButton"))
    assert view.visible("relinkBanner") is not None, "yeniden baglama bilgisi gorunmeli"
    view.select("kopegin")
    assert find_text(view.window, "Buraya bağla") is not None, "secim cubugu renk yerine 'Buraya bağla' gostermeli"
    click(view.app, view.window, find_text(view.window, "Buraya bağla"))
    pump(view.app, 40)

    relinked = view.annotations.get_highlight(orphan.id)
    assert relinked.status == STATUS_OK and "kopegin" in relinked.quote_exact and relinked.segments[0].polygons
    assert (relinked.label_key, relinked.comment, relinked.tags) == ("critique", "eski yorum", ["yontem"])
    assert view.visible("relinkBanner") is None, "bitince bilgi kapanmali"
    assert view.visible("orphanFilterChip") is None, "yetim kalmadi"
    assert len(view.annotations.list_highlights(view.document_id)) == 1  # yeni kayit olusmadi


def test_cancelling_a_relink_keeps_the_orphan_and_restores_the_normal_selection_toolbar(reader):
    view, _resource = reader
    orphan = _open_notebook_with_an_orphan(view)
    click(view.app, view.window, view.visible("relinkButton"))

    click(view.app, view.window, view.visible("cancelRelinkButton"))
    view.select("kopegin")

    assert view.visible("relinkBanner") is None
    assert find_text(view.window, "Buraya bağla") is None
    assert view.annotations.get_highlight(orphan.id).status == STATUS_ORPHANED
    assert view.toolbar() is not None  # renk secenekleri geri geldi


def test_notebook_filters_by_free_tag(reader):
    view, _resource = reader
    view.select("tilki")
    view.click_first_swatch()
    view.select("kopegin")
    view.click_first_swatch()
    first, second = sorted(view.annotations.list_highlights(view.document_id), key=lambda h: h.id)
    view.bridge.pdf.setTags(first.id, ["hipotez"])
    from tests.test_qml.qml_harness import find_named

    find_named(view.window, "pdfReaderView").setProperty("sidePanelOpen", True)
    find_named(view.window, "sidePanel").setProperty("activeTab", 2)
    pump(view.app, 60)
    assert len(view.bridge.pdf.notebookItems("", "", False, view.bridge.pdf.revision)) == 2

    click(view.app, view.window, view.visible("tagFilterChip"))
    pump(view.app, 40)

    assert find_named(view.window, "sidePanel").property("tagFilter") == "hipotez"
    assert [i["id"] for i in view.bridge.pdf.notebookItems("", "hipotez", False, view.bridge.pdf.revision)] == [first.id]
