import pytest

from pdfkit.domain.annotations import STATUS_OK, STATUS_ORPHANED, Segment
from pdfkit.domain.anchoring import normalize_ws, resolve
from pdfkit.domain.ids import new_uid
from pdfkit.domain.labels import color_for_label, label_key_for_color, name_for_label


class FakePages:
    def __init__(self, *pages: str) -> None:
        self._pages = list(pages)

    def page_count(self) -> int:
        return len(self._pages)

    def text_of(self, page: int) -> str:
        return self._pages[page]


def _segment(text_page: str, quote: str, page: int = 0) -> Segment:
    start = text_page.index(quote)
    return Segment(page, start, start + len(quote), quote)


PAGE = "Giris bolumu. Derin ogrenme modelleri buyuk veriyle egitilir. Sonuc bolumu burada baslar."
QUOTE = "Derin ogrenme modelleri buyuk veriyle egitilir."


def test_unchanged_text_is_resolved_by_position_and_context_is_extracted():
    segment = _segment(PAGE, QUOTE)

    result = resolve([segment], None, None, FakePages(PAGE))

    assert result.status == STATUS_OK and result.method == "position" and not result.moved
    assert result.prefix == "Giris bolumu. " and result.suffix.startswith(" Sonuc bolumu")


def test_position_with_different_line_breaks_still_counts_as_the_same_text():
    page = "Derin ogrenme modelleri\nbuyuk veriyle   egitilir."
    segment = Segment(0, 0, len(page), "Derin ogrenme modelleri buyuk veriyle egitilir.")

    assert resolve([segment], None, None, FakePages(page)).method == "position"


def test_text_shifted_by_an_engine_change_is_found_by_context_search():
    shifted = "Onsoz ve ilk paragraf eklendi. " + PAGE
    stale = _segment(PAGE, QUOTE)  # eski motorun indeksleri

    result = resolve([stale], None, None, FakePages(shifted))

    assert result.status == STATUS_OK and result.method == "context" and result.moved
    (segment,) = result.segments
    assert shifted[segment.start : segment.end] == QUOTE


def test_repeated_sentence_is_disambiguated_by_prefix_and_suffix():
    sentence = "Bu sonuc onemlidir."
    page = f"Birinci bolum sonu. {sentence} Ikinci bolum sonu. {sentence} Ucuncu bolum."
    second = page.index(sentence, page.index(sentence) + 1)
    stale = Segment(0, 0, len(sentence), sentence)  # konum artik gecersiz

    result = resolve([stale], "Ikinci bolum sonu. ", " Ucuncu bolum.", FakePages(page))

    assert result.status == STATUS_OK
    assert result.segments[0].start == second


def test_repeated_sentence_without_context_prefers_the_nearest_to_the_saved_position():
    sentence = "Tekrarlanan cumle burada."
    page = f"{sentence} Arada metin var. {sentence}"
    second = page.rindex(sentence)
    stale = Segment(0, second + 3, second + 3 + len(sentence), sentence)  # kayitli konum ikinciye yakin

    result = resolve([stale], None, None, FakePages(page))

    assert result.segments[0].start == second


def test_hyphenation_and_ligature_differences_are_matched_by_squashed_search():
    quote = "bilgisayar destekli ogrenme"
    page = "Konu: bilgi-\nsayar  destekli ogren me yaklasimlari."  # tirelenmis + bolunmus kelime
    stale = Segment(0, 100, 130, quote)

    result = resolve([stale], None, None, FakePages(page))

    assert result.status == STATUS_OK and result.method == "squash"


def test_quote_on_the_neighbor_page_is_found():
    pages = FakePages("ilk sayfa metni", "ikinci sayfa " + QUOTE, "ucuncu sayfa")
    stale = Segment(0, 0, len(QUOTE), QUOTE)

    result = resolve([stale], None, None, pages)

    assert result.status == STATUS_OK and result.method == "neighbor"
    assert result.segments[0].page == 1


def test_missing_quote_is_orphaned_and_keeps_the_saved_segments():
    stale = _segment(PAGE, QUOTE)

    result = resolve([stale], None, None, FakePages("tamamen farkli bir metin burada yer alir."))

    assert result.status == STATUS_ORPHANED and result.segments == [stale] and not result.moved


def test_very_short_quotes_are_not_searched_to_avoid_false_matches():
    stale = Segment(0, 500, 502, "ab")

    assert resolve([stale], None, None, FakePages("abab ab ab")).status == STATUS_ORPHANED


def test_multi_segment_annotation_requires_every_segment():
    page_one = "birinci sayfanin sonundaki cumle yarim kaliyor"
    page_two = "ve ikinci sayfanin basinda tamamlaniyor."
    segments = [Segment(0, 0, len(page_one), page_one), Segment(1, 0, len(page_two), page_two)]

    ok = resolve(segments, None, None, FakePages(page_one, page_two))
    broken = resolve(segments, None, None, FakePages(page_one, "baska bir sayfa metni tamamen"))

    assert ok.status == STATUS_OK and len(ok.segments) == 2
    assert broken.status == STATUS_ORPHANED


def test_normalize_ws_collapses_whitespace_and_trims():
    assert normalize_ws("  a \r\n b\t c  ") == "a b c"


def test_uid_is_26_char_sortable_crockford_and_unique():
    first, second = new_uid(), new_uid()

    assert len(first) == 26 and set(first) <= set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
    assert first != second


@pytest.mark.parametrize(
    "color,key",
    [("#22C55E", "finding"), ("#22c55e", "finding"), (" #EAB308 ", "important"), ("#123456", "general"), (None, "general")],
)
def test_legacy_color_maps_to_label_key(color, key):
    assert label_key_for_color(color) == key


def test_label_names_and_default_colors_round_trip():
    assert name_for_label("method") == "Yöntem" and color_for_label("method") == "#06B6D4"
    assert name_for_label("general") == "Genel" and color_for_label("general") is None
