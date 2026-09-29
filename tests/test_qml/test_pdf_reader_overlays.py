"""PDF okuyucunun sayfa katmanları (seçim araç çubuğu + kelime popover'ı, alıntı düzenleme popover'ı, not katmanı)
gerçek fare/klavye ile: PdfPageArea bileşenlere bölündükten sonra da uçtan uca çalıştıklarını doğrular."""
import pytest
from PySide6.QtCore import QMetaObject, QObject, QPoint, QPointF, Qt
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
    type_text,
    walk,
    white_page_box,
)
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
        scene = toolbar.mapToScene(QPointF(19, toolbar.property("height") / 2))
        QTest.mouseClick(self.window, Qt.LeftButton, Qt.NoModifier, QPoint(int(scene.x()), int(scene.y())))
        pump(self.app, 30)

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
    doc = bridge.ctx.pdf_files.load_document(bridge.reader.currentReaderResource["pdfFileUrl"])
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

    (vocab,) = view.bridge.controllers.resources.get_resource(resource.id).vocabulary
    assert vocab.word.strip() == "tilki" and vocab.translation == "fox"
    assert vocab.context_sentence.startswith("Hizli kahverengi tilki")
    assert view.visible("newVocabPopover") is None, "kaydedince popover kapanmali"


def test_clicking_a_saved_highlight_opens_editor_and_saves_comment(reader):
    view, resource = reader
    view.select("kopegin")
    view.click_first_swatch()
    (highlight,) = view.bridge.controllers.highlights.load_resource_highlights(resource.id)
    assert view.visible("editHighlightPopover") is None

    hit_area = view.visible("highlightHitArea")
    assert hit_area is not None, "kalici alinti tiklama alani olusmali"
    click(view.app, view.window, hit_area)
    assert view.visible("editHighlightPopover") is not None, "alintiya tiklayinca duzenleme popover'i acilmali"
    view.type_into("editCommentInput", "onemli")
    click(view.app, view.window, find_text(view.window, "Yorumu Kaydet"))

    (updated,) = view.bridge.controllers.highlights.load_resource_highlights(resource.id)
    assert updated.id == highlight.id and updated.comment == "onemli"
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

    (note,) = view.bridge.controllers.pdf_notes.load_resource_notes(resource.id)
    assert note.note_text == "not" and note.page == 0
    assert abs(note.x - 250) < 3 and abs(note.y - 450) < 3  # page-point uzayinda (piksel/zoom'dan bagimsiz)

    page_area.setProperty("noteMode", False)
    pump(view.app, 20)
    assert view.bridge.reader.currentReaderResource["pdfNotes"][0]["text"] == "not"
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
