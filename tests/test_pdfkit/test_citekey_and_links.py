"""citekey uretimi, kalici atama ve `pkm://` derin baglanti ayristirma."""
import pytest

from models import Resource
from pdfkit.app.documents import DocumentService
from pdfkit.app.importing import prepare_pdf
from pdfkit.app.vault import CitekeyService
from pdfkit.domain.citekey import ascii_slug, base_citekey, keyword_of, make_unique, surname_of, year_of
from pdfkit.domain.deeplink import OpenLink, build_open_link, parse_open_link
from pdfkit.domain.errors import InvalidLinkError
from pdfkit.domain.models import SourceInfo
from tests.pdf_factory import write_outline_pdf

# ---- citekey ----


@pytest.mark.parametrize(
    "text, expected",
    [("Şükrü Çağdaş", "sukrucagdas"), ("İstanbul Ğ", "istanbulg"), ("Müller-Straße", "mullerstrasse"), ("Ångström", "angstrom"), ("a b_c!1", "abc1")],
)
def test_ascii_slug_transliterates_turkish_and_accented_letters(text, expected):
    assert ascii_slug(text) == expected


@pytest.mark.parametrize(
    "author, expected",
    [("Y. LeCun", "lecun"), ("LeCun, Yann", "lecun"), ("Ali Çelik", "celik"), ("Plato", "plato"), ("", ""), ("  ", ""), ("山田 太郎", "")],
)
def test_surname_extraction(author, expected):
    assert surname_of(author) == expected


@pytest.mark.parametrize("year, expected", [(2015, "2015"), ("Mayis 2019", "2019"), ("n.d.", "nd"), (None, "nd"), (99, "nd"), ("12345", "nd")])
def test_year_extraction(year, expected):
    assert year_of(year) == expected


def test_keyword_skips_stopwords_and_short_tokens():
    assert keyword_of("The Role of Attention in Learning") == "role"
    assert keyword_of("Makine Öğrenmesi ve Derin Öğrenme") == "makine"
    assert keyword_of("A of in") == "" and keyword_of("") == ""
    assert keyword_of("Transformers: Attention Is All You Need") == "transformers"


def test_base_citekey_combines_author_year_keyword_with_fallbacks():
    assert base_citekey(["Yann LeCun", "Y. Bengio"], 2015, "Deep learning") == "lecun2015deep"
    assert base_citekey([], None, "", None) == "anon" + "nd"
    assert base_citekey([], 2020, "Derin ağlar", "Ayşe Yılmaz; Veli Demir") == "yilmaz2020derin"  # PDF yazari yedegi
    assert base_citekey(["山田 太郎", "Bob Smith"], 2001, "x") == "smith2001"  # ilk cozulebilen yazar


def test_make_unique_appends_letters_in_order():
    taken = {"a2020x", "a2020xa", "a2020xb"}
    assert make_unique("a2020x", taken) == "a2020xc"
    assert make_unique("b2020x", taken) == "b2020x"
    many = {"k"} | {"k" + chr(97 + i) for i in range(26)}
    assert make_unique("k", many) == "kaa"


# ---- kalici atama ----


@pytest.fixture()
def two_documents(session, pdf_store, tmp_path):
    documents = []
    for name, pages in (("bir", ["A"]), ("iki", ["A", "B"])):
        prepared = prepare_pdf(write_outline_pdf(tmp_path / f"{name}.pdf", pages), pdf_store)
        resource = Resource(title=name, url=pdf_store.absolute(prepared.stored.rel_path).as_uri())
        session.add(resource)
        session.commit()
        documents.append(DocumentService(session, pdf_store).register(prepared, resource.id, "local"))
    return documents


def test_citekey_is_assigned_once_and_survives_metadata_changes(session, two_documents):
    first, _second = two_documents
    service = CitekeyService(session)
    assert service.get(first.id) is None

    assigned = service.ensure(first, SourceInfo("Deep learning", ("Yann LeCun",), 2015))
    later = service.ensure(first, SourceInfo("Tamamen farkli baslik", ("Baska Biri",), 1999))

    assert assigned == "lecun2015deep" and later == assigned and service.get(first.id) == assigned


def test_colliding_documents_get_distinct_keys(session, two_documents):
    first, second = two_documents
    service = CitekeyService(session)
    info = SourceInfo("Deep learning", ("Yann LeCun",), 2015)

    keys = [service.ensure(first, info), service.ensure(second, info)]

    assert keys == ["lecun2015deep", "lecun2015deepa"]


def test_citekey_falls_back_to_pdf_metadata_when_the_source_has_none(session, two_documents):
    first, _ = two_documents

    assert CitekeyService(session).ensure(first, SourceInfo("")) .startswith("anon")


# ---- derin baglanti ----

ULID = "01HZX3K9M2P4Q6R8S0T1V2W3X4"


def test_build_and_parse_round_trip():
    url = build_open_link("AB" * 32, page=2, ann_uid=ULID)

    assert url == f"pkm://open?doc={'ab' * 8}&page=3&ann={ULID}"
    assert parse_open_link(url) == OpenLink("ab" * 8, 2, ULID)
    assert parse_open_link(build_open_link("cd" * 32)) == OpenLink("cd" * 8, None, None)


@pytest.mark.parametrize(
    "url",
    [
        "", "pkm://", "http://open?doc=abababab", "pkm://other?doc=abababab", "pkm://open",
        "pkm://open?doc=zzzzzzzz", "pkm://open?doc=abab", "pkm://open?doc=abababab&page=0",
        "pkm://open?doc=abababab&page=-1", "pkm://open?doc=abababab&page=1e3", "pkm://open?doc=abababab&page=999999",
        "pkm://open?doc=abababab&page=²", "pkm://open?doc=abababab&ann=notaulid",
        "pkm://open?doc=abababab&evil=1", "pkm://open?doc=abababab&doc=cdcdcdcd",
        "pkm://open/../x?doc=abababab", "pkm://open?doc=abababab#frag" + "x" * 600,
    ],
)
def test_malicious_or_malformed_links_are_rejected(url):
    with pytest.raises(InvalidLinkError):
        parse_open_link(url)


def test_non_string_input_is_rejected():
    with pytest.raises(InvalidLinkError):
        parse_open_link(None)  # type: ignore[arg-type]
