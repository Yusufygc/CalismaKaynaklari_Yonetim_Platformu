import pytest

from utils.url_utils import normalize_url


@pytest.mark.parametrize(
    "first, second",
    [
        ("https://arxiv.org/abs/1706.03762", "http://www.arxiv.org/abs/1706.03762/"),
        ("https://Example.com/a?utm_source=x&b=1", "https://example.com/a?b=1"),
        ("https://example.com/a#bolum-2", "https://example.com/a"),
        ("https://youtu.be/dQw4w9WgXcQ", "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30"),
        ("https://example.com/a?x=1&y=2", "https://example.com/a?y=2&x=1"),
    ],
)
def test_the_same_page_written_differently_gets_the_same_key(first, second):
    assert normalize_url(first) == normalize_url(second) != ""


@pytest.mark.parametrize(
    "first, second",
    [
        ("https://example.com/a", "https://example.com/b"),
        ("https://example.com/a?id=1", "https://example.com/a?id=2"),
        ("https://arxiv.org/abs/1706.03762", "https://arxiv.org/abs/1706.03763"),
        ("https://example.com:8080/a", "https://example.com/a"),
    ],
)
def test_different_pages_keep_different_keys(first, second):
    assert normalize_url(first) != normalize_url(second)


def test_empty_input_has_an_empty_key():
    assert normalize_url(None) == normalize_url("   ") == ""
