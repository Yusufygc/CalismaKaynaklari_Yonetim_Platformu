from models import Category, Resource, ResourceStatus, Tag
from repositories.resource_repo import ResourceRepository


def _make_resource(**overrides) -> Resource:
    defaults = dict(title="Baslik", status=ResourceStatus.PLANNED, priority=2)
    defaults.update(overrides)
    return Resource(**defaults)


def test_get_all_returns_pinned_first(session):
    repo = ResourceRepository(session)
    repo.create(_make_resource(title="Sabitsiz"))
    pinned = repo.create(_make_resource(title="Sabitli", is_pinned=True))

    result = repo.get_all()

    assert result[0].id == pinned.id


def test_get_by_status_filters_correctly(session):
    repo = ResourceRepository(session)
    repo.create(_make_resource(title="Planli", status=ResourceStatus.PLANNED))
    repo.create(_make_resource(title="Tamamlandi", status=ResourceStatus.COMPLETED))

    result = repo.get_by_status(ResourceStatus.COMPLETED)

    assert [r.title for r in result] == ["Tamamlandi"]


def test_search_by_keyword_matches_title_url_and_content(session):
    repo = ResourceRepository(session)
    repo.create(_make_resource(title="Django Ogren", url=None, content=None))
    repo.create(_make_resource(title="Baska", url="https://django-example.com", content=None))
    repo.create(_make_resource(title="Baska2", url=None, content="django hakkinda not"))
    repo.create(_make_resource(title="Alakasiz"))

    result = repo.search_by_keyword("django")

    assert len(result) == 3


def test_get_by_category_filters_correctly(session):
    repo = ResourceRepository(session)
    cat_repo_session = session
    category = Category(name="Yazilim", color_hex="#3776AB")
    cat_repo_session.add(category)
    cat_repo_session.flush()

    repo.create(_make_resource(title="Kategorili", category_id=category.id))
    repo.create(_make_resource(title="Kategorisiz"))

    result = repo.get_by_category(category.id)

    assert [r.title for r in result] == ["Kategorili"]


def test_get_favorites_filters_correctly(session):
    repo = ResourceRepository(session)
    repo.create(_make_resource(title="Favori", is_favorite=True))
    repo.create(_make_resource(title="Favori Degil"))

    result = repo.get_favorites()

    assert [r.title for r in result] == ["Favori"]


def test_get_urls_only_excludes_empty_and_null_urls(session):
    repo = ResourceRepository(session)
    repo.create(_make_resource(title="URL'li", url="https://example.com"))
    repo.create(_make_resource(title="Bos URL", url=""))
    repo.create(_make_resource(title="URL Yok", url=None))

    result = repo.get_urls_only()

    assert [r.title for r in result] == ["URL'li"]


def test_query_filtered_with_no_filters_returns_all(session):
    repo = ResourceRepository(session)
    repo.create(_make_resource(title="A"))
    repo.create(_make_resource(title="B"))

    result = repo.query_filtered()

    assert len(result) == 2


def test_query_filtered_combines_status_and_priority(session):
    repo = ResourceRepository(session)
    repo.create(_make_resource(title="Eslesen", status=ResourceStatus.INBOX, priority=1))
    repo.create(_make_resource(title="Yanlis Durum", status=ResourceStatus.COMPLETED, priority=1))
    repo.create(_make_resource(title="Yanlis Oncelik", status=ResourceStatus.INBOX, priority=3))

    result = repo.query_filtered(statuses=[ResourceStatus.INBOX], priorities=[1])

    assert [r.title for r in result] == ["Eslesen"]


def test_query_filtered_favorites_and_urls_only(session):
    repo = ResourceRepository(session)
    repo.create(
        _make_resource(title="Eslesen", is_favorite=True, url="https://example.com")
    )
    repo.create(_make_resource(title="Favori Ama URL Yok", is_favorite=True, url=None))
    repo.create(_make_resource(title="URL Var Ama Favori Degil", url="https://example.com"))

    result = repo.query_filtered(favorites_only=True, urls_only=True)

    assert [r.title for r in result] == ["Eslesen"]


def test_query_filtered_keyword_matches_title(session):
    repo = ResourceRepository(session)
    repo.create(_make_resource(title="Python Rehberi"))
    repo.create(_make_resource(title="Alakasiz"))

    result = repo.query_filtered(keyword="python")

    assert [r.title for r in result] == ["Python Rehberi"]


def test_query_filtered_tag_ids_uses_or_semantics_and_dedupes(session):
    """Birden fazla etiket verilince kayit herhangi birine sahipse listeye girer,
    birden fazlasina sahipse tekrar etmez (distinct)."""
    repo = ResourceRepository(session)
    tag_a = Tag(name="a")
    tag_b = Tag(name="b")
    session.add_all([tag_a, tag_b])
    session.flush()

    both_tags = repo.create(_make_resource(title="Iki Etiketli"))
    only_a = repo.create(_make_resource(title="Sadece A"))
    neither = repo.create(_make_resource(title="Etiketsiz"))

    both_tags.tags.extend([tag_a, tag_b])
    only_a.tags.append(tag_a)
    session.flush()

    result = repo.query_filtered(tag_ids=[tag_a.id, tag_b.id])

    titles = sorted(r.title for r in result)
    assert titles == ["Iki Etiketli", "Sadece A"]
    assert neither.title not in titles


def test_query_filtered_category_id_filters_correctly(session):
    repo = ResourceRepository(session)
    category = Category(name="Yazilim", color_hex="#3776AB")
    session.add(category)
    session.flush()

    repo.create(_make_resource(title="Kategorili", category_id=category.id))
    repo.create(_make_resource(title="Kategorisiz"))

    result = repo.query_filtered(category_id=category.id)

    assert [r.title for r in result] == ["Kategorili"]


def test_set_pinned_toggles_value(session):
    repo = ResourceRepository(session)
    resource = repo.create(_make_resource(title="Kaynak"))

    updated = repo.set_pinned(resource.id, True)

    assert updated is not None
    assert updated.is_pinned is True


def test_set_pinned_returns_none_when_missing(session):
    repo = ResourceRepository(session)

    assert repo.set_pinned(999, True) is None


def test_set_favorite_toggles_value(session):
    repo = ResourceRepository(session)
    resource = repo.create(_make_resource(title="Kaynak"))

    updated = repo.set_favorite(resource.id, True)

    assert updated is not None
    assert updated.is_favorite is True


def test_set_favorite_returns_none_when_missing(session):
    repo = ResourceRepository(session)

    assert repo.set_favorite(999, True) is None
