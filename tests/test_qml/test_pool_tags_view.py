"""Bilgi Havuzu > Alintilar: serbest etiket chip'leri, etikete gore suzme ve aramada etiket (gercek QML)."""
from tests.test_pdfkit.test_commands import selection_of
from tests.test_pdfkit.test_pool_and_export import env  # noqa: F401  (fixture)
from tests.test_qml.qml_harness import click, find_item, find_named, open_window, pump, type_text, walk


def _tag_chips(window):
    return [i for i in walk(window.contentItem()) if i.objectName() == "tagChip" and i.isVisible()]


def _tagged_pool(bridge, reader):
    bridge.pdf.addHighlight(selection_of(reader, "tilki"), "finding")
    bridge.pdf.addHighlight(selection_of(reader, "tembel"), "method")
    annotations = bridge.ctx.pdf_library.annotations()
    first, second = annotations.list_highlights(bridge.pdf.currentDocument["documentId"])
    annotations.set_tags(first.id, ["hipotez", "ortak"])
    annotations.set_tags(second.id, ["ortak"])
    bridge.annotations.reload_highlights()
    return first.id


def test_free_tags_appear_as_chips_with_counts_and_filter_the_list(env, qapp):
    bridge, _pdf, _web, reader = env
    _tagged_pool(bridge, reader)
    engine, window = open_window(qapp, bridge, "knowledge", width=1300, height=900)
    chips = _tag_chips(window)
    assert [(c.property("text"), c.property("count")) for c in chips] == [("#ortak", 2), ("#hipotez", 1)]
    assert find_named(window, "highlightsList").property("count") == 2

    click(qapp, window, chips[1])
    assert find_named(window, "highlightsList").property("count") == 1

    click(qapp, window, _tag_chips(window)[1])  # ayni chip: suzgec kalkar
    assert find_named(window, "highlightsList").property("count") == 2
    assert engine.captured_warnings == []


def test_a_filter_whose_tag_disappears_does_not_leave_an_empty_list(env, qapp):
    bridge, _pdf, _web, reader = env
    first_id = _tagged_pool(bridge, reader)
    engine, window = open_window(qapp, bridge, "knowledge", width=1300, height=900)
    click(qapp, window, _tag_chips(window)[1])  # #hipotez
    assert find_named(window, "highlightsList").property("count") == 1

    bridge.ctx.pdf_library.annotations().set_tags(first_id, [])  # etiketin tek alintisindan kalkti
    bridge.annotations.reload_highlights()
    pump(qapp, 30)

    assert find_named(window, "highlightsList").property("count") == 2
    assert engine.captured_warnings == []
