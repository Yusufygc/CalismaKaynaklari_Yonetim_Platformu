from types import SimpleNamespace

from services.library_index import LibraryIndex


def _res(rid, url=None, **metadata):
    return SimpleNamespace(id=rid, url=url, extra_metadata=metadata or None)


def test_finds_by_doi_case_and_prefix_insensitive():
    index = LibraryIndex([_res(1, doi="10.1000/ABC")])

    assert index.find(doi="https://doi.org/10.1000/abc") == 1


def test_finds_by_openalex_id():
    index = LibraryIndex([_res(2, openalex_id="W123")])

    assert index.find(openalex_id="w123") == 2


def test_finds_doi_embedded_in_resource_url():
    index = LibraryIndex([_res(3, url="https://doi.org/10.5555/xyz")])

    assert index.find(doi="10.5555/XYZ") == 3


def test_no_match_returns_none():
    index = LibraryIndex([_res(1, doi="10.1/a"), _res(2)])

    assert index.find(doi="10.1/b", openalex_id="W9") is None
    assert index.find() is None


def test_first_resource_wins_on_duplicates():
    index = LibraryIndex([_res(5, doi="10.1/a"), _res(6, doi="10.1/a")])

    assert index.find(doi="10.1/a") == 5


def test_add_makes_new_resource_findable():
    index = LibraryIndex([])

    index.add(9, doi="https://doi.org/10.1/NEW", openalex_id="W99")

    assert index.find(doi="10.1/new") == 9
    assert index.find(openalex_id="w99") == 9
