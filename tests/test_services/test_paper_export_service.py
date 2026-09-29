import csv
import io

from services.paper_export_service import PaperExportService

PAPERS = [
    {
        "title": "Attention Is All You Need",
        "authors": ["Ashish Vaswani", "Noam Shazeer"],
        "year": 2017,
        "venue": "NeurIPS",
        "doi": "10.5555/3295222.3295349",
        "url": "https://arxiv.org/abs/1706.03762",
        "citationCount": 100000,
        "isOpenAccess": True,
    },
    {
        "title": "Attention Mechanisms Revisited",
        "authors": ["Ada Vaswani"],
        "year": 2017,
        "venue": "",
        "doi": "",
        "url": "https://example.org/2",
        "citationCount": 3,
        "isOpenAccess": False,
    },
]


def test_bibtex_contains_one_entry_per_paper():
    text = PaperExportService.bibtex(PAPERS)

    assert text.count("@article{") == 2
    assert "title = {{Attention Is All You Need}}" in text
    assert text.endswith("\n")


def test_bibtex_keys_are_unique_when_author_year_word_collide():
    same = [dict(PAPERS[0]), dict(PAPERS[0])]

    text = PaperExportService.bibtex(same)

    keys = [line[len("@article{"):-1] for line in text.splitlines() if line.startswith("@article{")]
    assert len(keys) == 2 and keys[0] != keys[1]
    assert keys[0] == "vaswani2017attention" and keys[1] == "vaswani2017attentiona"


def test_bibtex_empty_list_is_empty_string():
    assert PaperExportService.bibtex([]) == ""


def test_csv_has_header_and_rows_parseable_back():
    rows = list(csv.reader(io.StringIO(PaperExportService.csv(PAPERS))))

    assert rows[0] == ["Title", "Authors", "Year", "Venue", "DOI", "URL", "Citations", "Open Access"]
    assert rows[1] == [
        "Attention Is All You Need", "Ashish Vaswani; Noam Shazeer", "2017", "NeurIPS",
        "10.5555/3295222.3295349", "https://arxiv.org/abs/1706.03762", "100000", "yes",
    ]
    assert rows[2][7] == "no" and rows[2][3] == ""


def test_csv_quotes_commas_and_newlines_in_titles():
    tricky = [{"title": 'A, "quoted"\ntitle', "authors": [], "year": None, "citationCount": 0}]

    rows = list(csv.reader(io.StringIO(PaperExportService.csv(tricky))))

    assert rows[1][0] == 'A, "quoted"\ntitle'
