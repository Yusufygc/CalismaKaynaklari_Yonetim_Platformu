from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from core.exceptions import DuplicateRecordError, ResourceNotFoundError, ValidationError
from core.logger import log
from models import SavedSearch
from repositories.saved_search_repo import SavedSearchRepository

# QML'in gonderebilecegi filtre anahtarlari (bkz. MarketFilters.from_dict) + gorunen yazar adi.
_FILTER_KEYS = ("yearFrom", "yearTo", "openAccess", "workType", "language", "authorId", "authorName")
_MAX_SEEN_IDS = 200


def _utcnow() -> datetime:
    """SQLite tz bilgisini saklamaz; karsilastirmalar hep UTC ve saat dilimsiz yapilir."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _clean_filters(filters: dict | None) -> dict:
    return {k: filters[k] for k in _FILTER_KEYS if filters and filters.get(k) not in (None, "", False)}


def _identity(topic: str, filters: dict) -> tuple:
    """Iki aramanin ayni sayilmasi icin karsilastirma anahtari (yazar adi gorunumluktur)."""
    return topic.lower(), tuple(sorted((k, str(v)) for k, v in filters.items() if k != "authorName"))


class SavedSearchService:
    """Makale Market kayitli aramalari ve yeni yayin takibi (yalnizca durum; ag isi worker'da)."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = SavedSearchRepository(session)

    def list_all(self) -> list[SavedSearch]:
        return self._repo.get_all_ordered()

    def create(
        self,
        topic: str,
        filters: dict | None,
        tag_name: str | None = None,
        seen_ids: list[str] | None = None,
    ) -> SavedSearch:
        topic = (topic or "").strip()
        clean = _clean_filters(filters)
        if not topic and not clean.get("authorId"):
            raise ValidationError("Kaydedilecek bir konu ya da yazar filtresi yok.")
        identity = _identity(topic, clean)
        if any(_identity(s.topic, s.filters or {}) == identity for s in self._repo.get_all()):
            raise DuplicateRecordError("Bu arama zaten kayitli.")
        try:
            search = SavedSearch(
                topic=topic,
                filters=clean,
                tag_name=(tag_name or "").strip().lower() or None,
                seen_ids=list(dict.fromkeys(seen_ids or []))[:_MAX_SEEN_IDS],
                new_count=0,
                last_checked_at=_utcnow(),
            )
            self._repo.create(search)
            self._session.commit()
            log.info("Arama kaydedildi: id=%d topic=%s", search.id, topic)
            return search
        except Exception:
            self._session.rollback()
            log.exception("Arama kaydedilirken hata olustu.")
            raise

    def delete(self, search_id: int) -> None:
        try:
            if not self._repo.delete(search_id):
                raise ResourceNotFoundError(f"Kayitli arama bulunamadi: id={search_id}")
            self._session.commit()
            log.info("Kayitli arama silindi: id=%d", search_id)
        except Exception:
            self._session.rollback()
            log.exception("Kayitli arama silinirken hata olustu.")
            raise

    def mark_seen(self, search_id: int, ids: list[str]) -> SavedSearch:
        """Kullanici sonuclari gordu: kimlikler `seen_ids`'e (yenisi basta, sinirli) eklenir, yeni sayaci sifirlanir."""
        search = self._get(search_id)
        try:
            search.seen_ids = list(dict.fromkeys([*ids, *(search.seen_ids or [])]))[:_MAX_SEEN_IDS]
            search.new_count = 0
            search.last_checked_at = _utcnow()
            self._repo.update(search)
            self._session.commit()
            return search
        except Exception:
            self._session.rollback()
            log.exception("Kayitli arama guncellenirken hata olustu.")
            raise

    def record_check(self, search_id: int, new_count: int) -> SavedSearch:
        search = self._get(search_id)
        try:
            search.new_count = max(0, new_count)
            search.last_checked_at = _utcnow()
            self._repo.update(search)
            self._session.commit()
            return search
        except Exception:
            self._session.rollback()
            log.exception("Kayitli arama kontrolu yazilirken hata olustu.")
            raise

    def due_for_check(self, max_age: timedelta) -> list[SavedSearch]:
        """Hic kontrol edilmemis ya da son kontrolu `max_age`'den eski olan aramalar."""
        threshold = _utcnow() - max_age
        return [s for s in self._repo.get_all_ordered() if s.last_checked_at is None or s.last_checked_at <= threshold]

    def _get(self, search_id: int) -> SavedSearch:
        search = self._repo.get_by_id(search_id)
        if search is None:
            raise ResourceNotFoundError(f"Kayitli arama bulunamadi: id={search_id}")
        return search
