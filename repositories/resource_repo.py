from typing import Iterable

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload, selectinload

from models import Resource, ResourceStatus, resource_tags_link
from .base_repository import BaseRepository


def _default_order(query):
    """Pinli kayitlar her zaman ustte, sonra olusturma tarihine gore yeniden eski."""
    return query.order_by(Resource.is_pinned.desc(), Resource.created_at.desc())


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
        pattern = f"%{keyword}%"
        q = self._base_query().filter(
            or_(
                Resource.title.ilike(pattern),
                Resource.url.ilike(pattern),
                Resource.content.ilike(pattern),
            )
        )
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

    def query_filtered(
        self,
        *,
        statuses: Iterable[ResourceStatus] | None = None,
        category_id: int | None = None,
        tag_ids: Iterable[int] | None = None,
        priorities: Iterable[int] | None = None,
        favorites_only: bool = False,
        urls_only: bool = False,
        keyword: str | None = None,
    ) -> list[Resource]:
        """Kombinasyonel filtre — bos/None alanlar koşula donusmez.

        Etiket filtresi OR semantigi: kayit, secilen etiketlerden en az birine
        sahipse listeye girer.
        """
        q = self._base_query()

        statuses_list = list(statuses) if statuses else []
        if statuses_list:
            q = q.filter(Resource.status.in_(statuses_list))

        if category_id is not None:
            q = q.filter(Resource.category_id == category_id)

        priorities_list = list(priorities) if priorities else []
        if priorities_list:
            q = q.filter(Resource.priority.in_(priorities_list))

        if favorites_only:
            q = q.filter(Resource.is_favorite.is_(True))

        if urls_only:
            q = q.filter(Resource.url.isnot(None), Resource.url != "")

        if keyword:
            pattern = f"%{keyword.strip()}%"
            q = q.filter(
                or_(
                    Resource.title.ilike(pattern),
                    Resource.url.ilike(pattern),
                    Resource.content.ilike(pattern),
                )
            )

        tag_ids_list = list(tag_ids) if tag_ids else []
        if tag_ids_list:
            q = (
                q.join(resource_tags_link, Resource.id == resource_tags_link.c.resource_id)
                .filter(resource_tags_link.c.tag_id.in_(tag_ids_list))
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
