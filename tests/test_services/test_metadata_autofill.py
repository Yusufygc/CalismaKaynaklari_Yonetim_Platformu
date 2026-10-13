"""Kunye otomatik doldurma kurallari: yalniz bos alanlar, yanlis makaleyi eleyen baslik celiskisi denetimi."""
import pytest

from services.metadata_autofill import fill_missing, titles_conflict

INCOMING = {
    "authors": ["Yann LeCun", "Yoshua Bengio"], "year": 2015, "venue": "Nature", "doi": "10.1038/nature14539",
    "openalex_id": "W123", "citation_count": 70000, "source": "openalex",
}


def test_only_empty_fields_are_filled_and_nothing_the_user_set_is_overwritten():
    existing = {"authors": ["Ben Yazdim"], "year": None, "venue": "", "source": "local_pdf", "baska": 1}

    merged, added = fill_missing(existing, INCOMING)

    assert merged["authors"] == ["Ben Yazdim"]  # dolu alan korunur
    assert merged["year"] == 2015 and merged["venue"] == "Nature" and merged["openalex_id"] == "W123"
    assert merged["source"] == "local_pdf" and merged["baska"] == 1  # `source` ve bilinmeyen anahtarlar asla dokunulmaz
    assert set(added) == {"year", "venue", "doi", "openalex_id", "citation_count"}
    assert existing["year"] is None  # girdi sozlugu degismez


def test_nothing_is_added_when_everything_is_already_there_or_nothing_was_found():
    full = {key: "x" for key in ("authors", "year", "venue", "doi", "openalex_id", "citation_count")}

    assert fill_missing(full, INCOMING) == (full, [])
    assert fill_missing({}, {}) == ({}, [])
    assert fill_missing(None, None) == ({}, [])
    assert fill_missing({}, {"authors": [], "year": None, "venue": ""})[1] == []  # bos deger doldurmaz


@pytest.mark.parametrize(
    "pdf_title, found_title, conflict",
    [
        ("Makine Öğrenmesi ve Derin Öğrenme Algoritmaları", "Makine Öğrenmesi ve Derin Öğrenme Algoritmalarını Kullanarak Hisse Senedi Fiyat Tahmini", False),
        ("Deep learning", "Deep Learning", False),
        ("Kuantum Hesaplama Üzerine", "A Survey of Reinforcement Learning", True),  # DOI atif yapilan baska makaleye ait
        ("Deep learning for vision", "A Survey of Reinforcement Learning", True),
        (None, "A Survey of Reinforcement Learning", False),  # gomulu baslik yok: karar verilemez, eskisi gibi kabul
        ("", "Deep learning", False),
        ("Deep", "Reinforcement Learning Survey", False),  # tek anlamli sozcuk: yargilanamaz
        ("a b", "c d", False),  # anlamli sozcuk yok
        ("Deep learning", None, False),
    ],
)
def test_a_found_paper_conflicts_only_when_it_clearly_differs_from_the_pdfs_own_title(pdf_title, found_title, conflict):
    assert titles_conflict(pdf_title, found_title) is conflict
