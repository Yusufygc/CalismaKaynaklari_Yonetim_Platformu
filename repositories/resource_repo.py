from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload, selectinload

from models import Resource, ResourceStatus, resource_tags_link
from utils.text_utils import fold_tr
from .base_repository import BaseRepository


@dataclass(frozen=True)
class ResourceFilter:
    """`ResourceRepository.query_filtered` sorgu kriterleri; bos/None alanlar kosula donusmez."""

    statuses: tuple[ResourceStatus, ...] = ()
    category_id: int | None = None
    tag_ids: tuple[int, ...] = ()
    priorities: tuple[int, ...] = ()
    favorites_only: bool = False
    urls_only: bool = False
    keyword: str | None = None

    def __post_init__(self) -> None:
        # Cagiranlar liste/kume verebilir; dondurulmus (hashlenebilir) kriter icin tuple'a cevrilir.
        for name in ("statuses", "tag_ids", "priorities"):
            object.__setattr__(self, name, tuple(getattr(self, name) or ()))


def _default_order(query):
    """Pinli kayitlar her zaman ustte, sonra olusturma tarihine gore yeniden eski."""
    return query.order_by(Resource.is_pinned.desc(), Resource.created_at.desc())


def _keyword_condition(keyword: str):
    """Baslik/URL/icerikte Turkce-duyarsiz alt metin aramasi (`fold_tr` SQL fonksiyonu gerekir,
    bkz. utils/db_utils.register_sqlite_functions). `%`, `_` ve `\\` kullanici metninde literaldir."""
    folded = fold_tr(keyword.strip()).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{folded}%"
    return or_(
        func.fold_tr(Resource.title).like(pattern, escape="\\"),
        func.fold_tr(Resource.url).like(pattern, escape="\\"),
        func.fold_tr(Resource.content).like(pattern, escape="\\"),
    )


class ResourceRepository(BaseRepository[Resource]):

    def __init__(self, session: Session) -> None:
        super().__init__(Resource, session)

    def _base_query(self):
        """category/tags iliskilerini eager-load eder — kart render'da N+1 sorguyu onler."""
        return self._session.query(Resource).options(
            joinedload(Resource.category), selectinload(Resource.tags)
        )

    def get_all(self) -> list[Resource]:
        return list(_default_order(self._base_query()).all())

    def get_by_status(self, status: ResourceStatus) -> list[Resource]:
        q = self._base_query().filter(Resource.status == status)
        return list(_default_order(q).all())

    def search_by_keyword(self, keyword: str) -> list[Resource]:
        q = self._base_query().filter(_keyword_condition(keyword))
        return list(_default_order(q).all())

    def get_by_category(self, category_id: int) -> list[Resource]:
        q = self._base_query().filter(Resource.category_id == category_id)
        return list(_default_order(q).all())

    def get_favorites(self) -> list[Resource]:
        q = self._base_query().filter(Resource.is_favorite.is_(True))
        return list(_default_order(q).all())

    def get_urls_only(self) -> list[Resource]:
        """Sadece URL alani dolu kaynaklari dondurur (URL Vitrini icin)."""
        q = self._base_query().filter(
            Resource.url.isnot(None), Resource.url != ""
        )
        return list(_default_order(q).all())

    def query_filtered(self, criteria: ResourceFilter | None = None) -> list[Resource]:
        """Kombinasyonel filtre — bos/None alanlar koşula donusmez.

        Etiket filtresi OR semantigi: kayit, secilen etiketlerden en az birine
        sahipse listeye girer.
        """
        criteria = criteria or ResourceFilter()
        q = self._base_query()

        if criteria.statuses:
            q = q.filter(Resource.status.in_(criteria.statuses))
        if criteria.category_id is not None:
            q = q.filter(Resource.category_id == criteria.category_id)
        if criteria.priorities:
            q = q.filter(Resource.priority.in_(criteria.priorities))
        if criteria.favorites_only:
            q = q.filter(Resource.is_favorite.is_(True))
        if criteria.urls_only:
            q = q.filter(Resource.url.isnot(None), Resource.url != "")
        if criteria.keyword:
            q = q.filter(_keyword_condition(criteria.keyword))
        if criteria.tag_ids:
            q = (
                q.join(resource_tags_link, Resource.id == resource_tags_link.c.resource_id)
                .filter(resource_tags_link.c.tag_id.in_(criteria.tag_ids))
                .distinct()
            )

        return list(_default_order(q).all())

    def set_pinned(self, resource_id: int, value: bool) -> Resource | None:
        resource = self.get_by_id(resource_id)
        if resource is None:
            return None
        resource.is_pinned = bool(value)
        self._session.flush()
        return resource

    def set_favorite(self, resource_id: int, value: bool) -> Resource | None:
        resource = self.get_by_id(resource_id)
        if resource is None:
            return None
        resource.is_favorite = bool(value)
        self._session.flush()
        return resource
