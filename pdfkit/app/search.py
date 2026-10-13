from collections.abc import Sequence
from dataclasses import dataclass, field

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from core.logger import log
from pdfkit.domain.search import SearchHit, fold, make_snippet, parse_query
from pdfkit.domain.text import sanitize_text
from pdfkit.infra.search_repository import (
    STATUS_FAILED,
    STATUS_INDEXING,
    STATUS_NO_TEXT,
    STATUS_OK,
    PageIndexRepository,
)

INDEX_VERSION = 1  # cikarim/katlama kurali degisirse artirilir: eski belgeler yeniden dizinlenir
MAX_INDEXED_PAGES = 2000  # belge basina ust sinir (dev ciltler veritabanini sisirmesin)
DEFAULT_LIMIT = 60


@dataclass
class SearchGroup:
    """Bir kaynagin eslesen sayfalari (en alakali once). `total` bu sorguda o kaynaktan bulunan sayfa sayisidir."""

    resource_id: int
    title: str
    document_id: int
    hits: list[SearchHit] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.hits)


class SearchService:
    """Kutuphane geneli tam metin arama (yalniz tam dizinlenmis belgeler)."""

    def __init__(self, session: Session) -> None:
        self._repo = PageIndexRepository(session)

    def available(self) -> bool:
        return self._repo.available()

    def search(self, text: str, limit: int = DEFAULT_LIMIT) -> list[SearchHit]:
        """En alakali sayfalar (bm25). Aranacak bir sey yoksa, dizin yoksa ya da sorgu gecersizse bos liste."""
        query = parse_query(text)
        if query is None or not self._repo.available():
            return []
        try:
            rows = self._repo.query(query.match, limit)
        except OperationalError as exc:  # bozuk MATCH ifadesi vb.: arama bos doner, uygulama durmaz
            log.warning("Tam metin sorgusu basarisiz: %s", exc)
            return []
        return [SearchHit(document_id, page, make_snippet(original, query), rank) for document_id, page, original, rank in rows]

    def search_by_resource(self, text: str, limit: int = DEFAULT_LIMIT) -> list[SearchGroup]:
        """Sonuclari kaynaga gore gruplar; gruplar en alakali sayfasina gore, sayfalar bm25 sirasiyla. Kaynagi
        kalmamis belgeler (silinmis kaynak) atlanir."""
        hits = self.search(text, limit)
        owners = self._repo.resources_for(sorted({hit.document_id for hit in hits}))
        groups: dict[int, SearchGroup] = {}
        for hit in hits:
            owner = owners.get(hit.document_id)
            if owner is None:
                continue
            group = groups.setdefault(hit.document_id, SearchGroup(owner[0], owner[1] or "", hit.document_id))
            group.hits.append(hit)
        return list(groups.values())


class IndexService:
    """Tam metin dizinine yazma. commit/rollback bu katmandadir. Bir belge: `begin` -> `add_pages`* -> `finish`.
    Arada yarida kalirsa durum `indexing` kalir; arama o belgeyi gormez ve sonraki taramada yeniden dizinlenir."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = PageIndexRepository(session)

    def available(self) -> bool:
        """Dizin tablosu var mi; yoksa olusturmayi dener (testler/eski sema), olmazsa False (arama kapali)."""
        if self._repo.available():
            return True
        try:
            created = self._repo.ensure_schema()
            self._session.commit()
            return created
        except Exception:
            self._session.rollback()
            return False

    def pending(self) -> list[int]:
        return self._repo.documents_needing_index(INDEX_VERSION)

    def begin(self, document_id: int) -> None:
        self._write(lambda: (self._repo.delete_pages(document_id), self._repo.set_state(document_id, STATUS_INDEXING, 0, INDEX_VERSION)))

    def add_pages(self, document_id: int, first_page: int, texts: Sequence[str]) -> int:
        """Sayfa metinlerini ekler (bos sayfalar atlanir); eklenen sayfa sayisini dondurur."""
        pages = []
        for offset, raw in enumerate(texts):
            original = " ".join(sanitize_text(raw).split())
            if original:
                pages.append((first_page + offset, fold(original), original))
        if pages:
            self._write(lambda: self._repo.add_pages(document_id, pages))
        return len(pages)

    def finish(self, document_id: int, page_count: int) -> None:
        """Dizin tamam: belge bundan sonra aranir."""
        self._write(lambda: self._repo.set_state(document_id, STATUS_OK, page_count, INDEX_VERSION))

    def finish_without_text(self, document_id: int) -> None:
        self._write(lambda: (self._repo.delete_pages(document_id), self._repo.set_state(document_id, STATUS_NO_TEXT, 0, INDEX_VERSION)))

    def fail(self, document_id: int) -> None:
        self._write(lambda: (self._repo.delete_pages(document_id), self._repo.set_state(document_id, STATUS_FAILED, 0, INDEX_VERSION)))

    def abandon(self, document_id: int) -> None:
        """Yarim kalan dizini kaldirir (iptal): sonraki taramada bastan yapilir."""
        self._write(lambda: (self._repo.delete_pages(document_id), self._repo.clear_state(document_id)))

    def purge_orphans(self) -> int:
        """Belgesi silinmis (durum satiri cascade ile gitmis) sayfa satirlarini temizler."""
        if not self._repo.available():
            return 0
        return self._write(self._repo.purge_orphans)

    def statistics(self) -> dict[str, int]:
        return self._repo.count_by_status()

    def _write(self, change):
        try:
            result = change()
            self._session.commit()
            return result
        except Exception:
            self._session.rollback()
            raise
