import pytest

from utils.url_utils import detect_category_name, site_name


@pytest.mark.parametrize(
    "host, name",
    [
        ("dergipark.org.tr", "dergipark"),
        ("earsiv.hitit.edu.tr", "hitit"),
        ("hitit.edu.tr", "hitit"),
        ("bbc.co.uk", "bbc"),
        ("news.bbc.co.uk", "bbc"),
        ("example.org", "example"),
        ("journals.plos.org", "plos"),
        ("cs.stanford.edu", "stanford"),
        ("pjms.org.pk", "pjms"),
        ("set-science.com", "set-science"),
        ("doi.org", "doi"),
        ("localhost", "localhost"),
        ("", None),
    ],
)
def test_site_name_skips_second_level_suffixes(host, name):
    assert site_name(host) == name


@pytest.mark.parametrize(
    "url, category",
    [
        ("https://dergipark.org.tr/tr/pub/x", "Makale"),
        ("https://journals.plos.org/plosone/article?id=1", "Makale"),
        ("https://www.mdpi.com/2076-3417/1", "Makale"),
        ("https://www.nature.com/articles/x", "Makale"),
        ("https://onlinelibrary.wiley.com/doi/1", "Makale"),
        ("https://www.biorxiv.org/content/1", "Makale"),
        ("https://link.springer.com/article/1", "Makale"),
        ("https://earsiv.hitit.edu.tr/xmlui/handle/1", "Makale"),
        ("https://www.cs.ox.ac.uk/people", "Makale"),
        ("https://www.youtube.com/watch?v=a", "YouTube"),
        ("https://github.com/u/r", "GitHub"),
        ("https://example.org/haber", "Web"),
        ("https://notmdpi.com/x", "Web"),  # sonek eslesmesi nokta sinirinda: "notmdpi.com" mdpi.com degildir
        ("https://example.com/a.pdf", "Makale"),
    ],
)
def test_academic_sites_and_university_domains_are_articles(url, category):
    assert detect_category_name(url) == category
