import html

from utils.pdf_reflow import Block, reflow_page, reflow_pages_html, repeated_lines


def _texts(blocks):
    return [(b.kind, b.text) for b in blocks]


def test_line_wraps_become_one_paragraph_and_hyphenated_words_are_rejoined():
    raw = "Bu calismada 22 firma-\r\nnin hisse senetlerinin fiyatlari tahmin\r\nedilmistir ve sonuclar karsilastirilmistir."

    (block,) = reflow_page(raw)

    assert block == Block("p", "Bu calismada 22 firmanin hisse senetlerinin fiyatlari tahmin edilmistir ve sonuclar karsilastirilmistir.")


def test_a_hyphen_before_a_capital_or_digit_is_kept():
    raw = "Bu yontem ARIMA-\r\nDVM modellerini ve 2010-\r\n2019 yillarini kapsar."
    (block,) = reflow_page(raw)
    assert "ARIMA-DVM" in block.text and "2010-2019" in block.text  # gercek tire korunur, araya bosluk girmez


def test_a_short_line_ending_a_sentence_starts_a_new_paragraph():
    long_line = "Birinci paragrafin dolu bir satiri burada yer alir ve satir genis"
    raw = "\r\n".join([long_line, long_line, "Paragraf burada biter.", long_line, "Ikinci paragraf devam eder."])

    blocks = reflow_page(raw)

    assert [b.kind for b in blocks] == ["p", "p"]
    assert blocks[0].text.endswith("Paragraf burada biter.") and blocks[1].text.startswith("Birinci paragrafin")


def test_numbered_and_uppercase_short_lines_are_headings():
    long_line = "Bu bolumde hisse senedi gelecek fiyat tahmini konusunda daha once yapilan calismalar"
    raw = f"{long_line} incelenmistir.\r\n2. Literatur Incelemesi\r\n{long_line} yer almaktadir.\r\nYONTEM VE VERI\r\n{long_line}."

    kinds = _texts(reflow_page(raw))

    assert ("h", "2. Literatur Incelemesi") in kinds and ("h", "YONTEM VE VERI") in kinds
    assert [kind for kind, _ in kinds].count("p") == 3


def test_a_sentence_that_merely_starts_with_a_number_is_not_a_heading():
    long_line = "Bu bolumde hisse senedi gelecek fiyat tahmini konusunda daha once yapilan calismalar"
    raw = f"{long_line}\r\n3 hisse senedi, uzun ve virgullu bir cumle olarak devam eder, baslik degildir,\r\n{long_line}."
    assert all(b.kind == "p" for b in reflow_page(raw))


def test_page_numbers_and_running_headers_are_dropped_but_content_is_kept():
    def page(n):
        word = ["alfa", "beta", "gama", "delta", "epsilon"][n - 1]
        body = "\r\n".join(f"{word} icin {chr(96 + i)} satiri farkli bir metin tasir ve burada devam eder" for i in range(1, 9))
        return f"Nisan 2021, 16 (1) {n}\r\n{body}\r\n{n}"

    pages = [page(n) for n in range(1, 6)]
    skip = repeated_lines(pages)

    blocks = reflow_page(pages[2], skip)

    assert len(blocks) == 1 and "Nisan 2021" not in blocks[0].text and not blocks[0].text.endswith(" 3")
    assert "gama icin a satiri" in blocks[0].text and "gama icin h satiri" in blocks[0].text


def test_few_pages_never_lose_repeated_looking_lines():
    pages = ["Baslik satiri\r\nmetin bir", "Baslik satiri\r\nmetin iki"]
    assert repeated_lines(pages) == set()
    assert "Baslik satiri" in reflow_page(pages[0])[0].text


def test_html_output_has_page_markers_headings_paragraphs_and_escapes_text():
    out = reflow_pages_html(["<b>x</b> & y"], html.escape)
    assert out == "<h3>Sayfa 1</h3><p>&lt;b&gt;x&lt;/b&gt; &amp; y</p>"
    assert reflow_pages_html(["", "   "], html.escape) == ""
    assert reflow_pages_html(["", "ikinci sayfa"], html.escape) == "<h3>Sayfa 2</h3><p>ikinci sayfa</p>"
