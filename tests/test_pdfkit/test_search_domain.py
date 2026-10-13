"""Tam metin aramasi saf cekirdegi: sorgu kurucu (guvenlik dahil) ve ozet parcasi."""
import pytest

from pdfkit.domain.search import MAX_QUERY_TOKENS, fold, make_snippet, parse_query
from utils.text_utils import fold_tr


def test_fold_matches_the_application_wide_turkish_fold():
    for sample in ["İSTANBUL ışık", "ŞĞÜÖÇ şğüöç", "Quantum", "Straße", None, ""]:
        assert fold(sample) == fold_tr(sample)


@pytest.mark.parametrize(
    "raw, match, prefix",
    [
        ("kuantum", '"kuantum"*', True),
        ("kuantum  bilgisayar", '"kuantum" "bilgisayar"*', True),
        ('"derin öğrenme" modeller', '"derin ogrenme" "modeller"*', True),
        ('modeller "derin öğrenme"', '"derin ogrenme" "modeller"', False),
        ("ŞEKER İşlem", '"seker" "islem"*', True),
    ],
)
def test_query_is_folded_quoted_and_the_last_loose_word_is_a_prefix(raw, match, prefix):
    query = parse_query(raw)

    assert query.match == match and query.prefix_last is prefix


@pytest.mark.parametrize("raw", [None, "", "   ", '""', "***", "- + ( ) :", '"  "'])
def test_nothing_to_search_gives_none(raw):
    assert parse_query(raw) is None


@pytest.mark.parametrize(
    "raw",
    ['a" OR "b', "title:secret", "kelime NEAR/5 baska", "x* - y", 'a" ) UNION SELECT', "{folded}: gizli", "^baslangic"],
)
def test_fts_syntax_cannot_be_injected(raw):
    query = parse_query(raw)

    # MATCH'e yalniz tirnakli belirtecler (ve en fazla bir onek yildizi) girer; operatorler sozcuge donusur
    stripped = query.match.replace('"', "").replace("*", "")
    assert all(ch.isalnum() or ch in " _" for ch in stripped), query.match
    assert query.match.count("*") <= 1


def test_token_count_and_length_are_bounded():
    query = parse_query(" ".join(f"kelime{i}" for i in range(50)) + " " + "u" * 500)

    assert len(query.terms) <= MAX_QUERY_TOKENS and all(len(t) <= 64 for t in query.terms)


def test_snippet_cuts_around_the_first_match_keeping_original_text_and_marks_spans():
    page = "Giriş. " + "dolgu " * 60 + "Bu çalışmada Kuantum bilgisayarlar incelendi. " + "son " * 60
    query = parse_query("kuantum bilgisayar")

    snippet = make_snippet(page, query, width=100)

    assert "Kuantum bilgisayarlar" in snippet.text and snippet.text.startswith("…") and snippet.text.endswith("…")
    marked = [snippet.text[a:b] for a, b in snippet.spans]
    assert marked == ["Kuantum", "bilgisayarlar"]  # özgün büyük/küçük harf korunur; son sözcük önek eşleşir
    assert len(snippet.text) <= 100 + 2


def test_snippet_matches_turkish_letters_without_regard_to_case_or_diacritics():
    snippet = make_snippet("ÇOCUKLARIN ÖĞRENME ŞEKLİ", parse_query("ogrenme sekli"))

    assert [snippet.text[a:b] for a, b in snippet.spans] == ["ÖĞRENME", "ŞEKLİ"]


def test_snippet_without_a_match_falls_back_to_the_page_start_and_empty_text_is_safe():
    assert make_snippet("Baslangic metni", parse_query("yok")).spans == ()
    assert make_snippet("", parse_query("x")).text == ""
    assert make_snippet("a " * 200, parse_query("yok"), width=20).text.endswith("…")


def test_found_word_keeps_the_original_spelling_so_the_reader_can_match_it():
    from pdfkit.domain.search import found_word

    query = parse_query("ogrenme")
    assert found_word("Cocuklarin ÖĞRENME sekli ve ogrenmenin sonuclari", query) == "ÖĞRENME"
    assert found_word("Cocuklarin öğrenmenin sonuclari", parse_query("ogren")) == "öğrenmenin"  # onek
    assert found_word("hic eslesme yok", query) == ""
