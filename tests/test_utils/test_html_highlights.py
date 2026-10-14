from utils.html_highlights import apply_highlights

YELLOW = "#EAB308"


def _mark(text, color=YELLOW):
    return f'<span style="background-color:{color}; color:#14213D;">{text}</span>'


def test_the_first_match_inside_a_text_node_is_wrapped_and_tags_stay_intact():
    html = "<h3>Sayfa 1</h3><p>Derin ogrenme yontemleri daha yuksek dogruluk saglar.</p>"

    result = apply_highlights(html, [{"content": "daha yuksek dogruluk", "color": YELLOW}])

    assert result == f"<h3>Sayfa 1</h3><p>Derin ogrenme yontemleri {_mark('daha yuksek dogruluk')} saglar.</p>"


def test_whitespace_differences_between_the_selection_and_the_html_are_tolerated():
    html = "<p>Derin   ogrenme\nyontemleri saglar.</p>"
    assert _mark("ogrenme\nyontemleri") in apply_highlights(html, [{"content": "ogrenme yontemleri", "color": YELLOW}])


def test_a_selection_spanning_paragraphs_marks_each_paragraph_part():
    html = "<p>Birinci paragraf burada biter.</p><p>Ikinci paragraf burada baslar.</p>"

    result = apply_highlights(html, [{"content": "biter. Ikinci paragraf", "color": "#22C55E"}])

    assert _mark("biter.", "#22C55E") in result and _mark("Ikinci paragraf", "#22C55E") in result


def test_html_entities_in_the_text_still_match_and_unmatched_or_invalid_highlights_are_skipped():
    html = "<p>Tom &amp; Jerry bir arada.</p>"
    assert _mark("Tom &amp; Jerry") in apply_highlights(html, [{"content": "Tom & Jerry", "color": YELLOW}])
    assert apply_highlights(html, [{"content": "olmayan metin", "color": YELLOW}]) == html  # eslesme yok: degismez
    assert apply_highlights(html, [{"content": "bir arada", "color": "red; x"}]) == html  # gecersiz renk: HTML'e sizmaz
    assert apply_highlights(html, [{"content": "ab", "color": YELLOW}]) == html  # cok kisa parca boyanmaz
    assert apply_highlights("", [{"content": "x", "color": YELLOW}]) == "" and apply_highlights(html, []) == html


def test_two_highlights_and_an_already_marked_span_are_not_marked_twice():
    html = "<p>alfa beta gama delta</p>"

    result = apply_highlights(html, [{"content": "beta gama", "color": YELLOW}, {"content": "beta gama", "color": "#22C55E"}])

    assert result.count("<span") == 1 and "#22C55E" not in result  # ayni metin tekrar boyanmaz (ilk renk kalir)
    both = apply_highlights(html, [{"content": "alfa", "color": YELLOW}, {"content": "delta", "color": "#22C55E"}])
    assert both.count("<span") == 2
