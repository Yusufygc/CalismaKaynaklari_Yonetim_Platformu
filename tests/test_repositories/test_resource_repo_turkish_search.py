import pytest

from models import Resource, ResourceStatus
from repositories.resource_repo import ResourceRepository


def _add(repo, title, **extra):
    return repo.create(Resource(title=title, status=ResourceStatus.PLANNED, priority=2, **extra))


@pytest.fixture()
def repo(session):
    repository = ResourceRepository(session)
    _add(repository, "İstanbul Rehberi")
    _add(repository, "ISPARTA gül bahçeleri")
    _add(repository, "Şeker ve Çikolata", content="tatlı ürünler")
    _add(repository, "Düz ASCII kaynak", url="https://example.org/Makale-Özet")
    return repository


@pytest.mark.parametrize(
    ("keyword", "expected_title"),
    [
        ("istanbul", "İstanbul Rehberi"),
        ("İSTANBUL", "İstanbul Rehberi"),
        ("ısparta", "ISPARTA gül bahçeleri"),
        ("Isparta", "ISPARTA gül bahçeleri"),
        ("seker", "Şeker ve Çikolata"),
        ("çikolata", "Şeker ve Çikolata"),
        ("TATLI", "Şeker ve Çikolata"),  # icerikte
        ("ozet", "Düz ASCII kaynak"),  # URL'de
    ],
)
@pytest.mark.parametrize("method", ["search_by_keyword", "query_filtered"])
def test_keyword_search_is_turkish_case_and_diacritic_insensitive(repo, method, keyword, expected_title):
    result = repo.search_by_keyword(keyword) if method == "search_by_keyword" else repo.query_filtered(keyword=keyword)

    assert [r.title for r in result] == [expected_title]


@pytest.mark.parametrize("keyword", ["%", "_", "\\"])
def test_like_wildcards_in_keyword_are_literal(repo, keyword):
    assert repo.query_filtered(keyword=keyword) == []


def test_percent_matches_only_literal_percent(repo):
    _add(repo, "Yüzde %50 indirim")

    assert [r.title for r in repo.query_filtered(keyword="%50")] == ["Yüzde %50 indirim"]
