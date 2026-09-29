from utils.text_utils import extract_sentence, sanitize_utf8

TEXT = (
    "Stock price prediction is important. Traditional models like ARIMA, often used\r\n"
    "for their simplicity, struggle with dynamic markets (Lu et al. 2025). "
    "We propose a hybrid approach combining CNN and LSTM networks. Results improved."
)


def _locate(word):
    return TEXT.index(word), len(word)


def test_extracts_sentence_spanning_line_wraps():
    start, length = _locate("simplicity")
    assert extract_sentence(TEXT, start, length) == (
        "Traditional models like ARIMA, often used for their simplicity, "
        "struggle with dynamic markets (Lu et al. 2025)."
    )


def test_first_and_last_sentences():
    start, length = _locate("Stock")
    assert extract_sentence(TEXT, start, length) == "Stock price prediction is important."
    start, length = _locate("improved")
    assert extract_sentence(TEXT, start, length) == "Results improved."


def test_does_not_break_on_et_al():
    start, length = _locate("markets")
    assert "Lu et al. 2025" in extract_sentence(TEXT, start, length)


def test_out_of_range_and_empty_inputs():
    assert extract_sentence("", 0, 1) == ""
    assert extract_sentence(TEXT, -1, 3) == ""
    assert extract_sentence(TEXT, len(TEXT) + 5, 3) == ""


def test_long_sentence_is_truncated():
    long_text = "Baslangic " + "kelime " * 200 + "sonu."
    result = extract_sentence(long_text, 0, 5, max_len=50)
    assert len(result) <= 51 and result.endswith("…")


def test_sanitize_utf8_replaces_lone_surrogates():
    cleaned = sanitize_utf8("a" + chr(0xD835) + "b")
    cleaned.encode("utf-8")
    assert cleaned.startswith("a") and cleaned.endswith("b")


def test_format_display_url_hides_storage_uuid_prefix():
    from utils.url_utils import format_display_url

    assert format_display_url("file:///C:/data/pdfs/28a6fc4b_Makale%20Adi.pdf") == "Makale Adi.pdf"
    # 8 hex olmayan/onek olmayan adlara dokunulmaz
    assert format_display_url("file:///C:/data/pdfs/rapor_2024.pdf") == "rapor_2024.pdf"

