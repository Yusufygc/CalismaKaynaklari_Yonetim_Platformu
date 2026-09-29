from sqlalchemy.orm import Session

from core.exceptions import ResourceNotFoundError, ValidationError
from core.logger import log
from models import Highlight
from repositories.highlight_repo import HighlightRepository
from repositories.resource_repo import ResourceRepository


class HighlightService:

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = HighlightRepository(session)
        self._resource_repo = ResourceRepository(session)

    def create_highlight(
        self,
        resource_id: int,
        content: str,
        color: str | None = None,
        page: int | None = None,
        start_index: int | None = None,
        length: int | None = None,
    ) -> Highlight:
        content = (content or "").strip()
        if not content:
            raise ValidationError("Alinti metni bos olamaz.")
        if self._resource_repo.get_by_id(resource_id) is None:
            raise ResourceNotFoundError(f"Kaynak bulunamadi: id={resource_id}")
        try:
            highlight = Highlight(
                resource_id=resource_id,
                content=content,
                color=color,
                page_number=page,
                start_index=start_index,
                length=length,
            )
            self._repo.create(highlight)
            self._session.commit()
            log.info("Yeni alinti eklendi: resource_id=%d", resource_id)
            return highlight
        except Exception:
            self._session.rollback()
            log.exception("Alinti eklenirken hata olustu.")
            raise

    def update_highlight_color(self, highlight_id: int, color: str) -> Highlight:
        highlight = self._repo.get_by_id(highlight_id)
        if highlight is None:
            raise ResourceNotFoundError(f"Alinti bulunamadi: id={highlight_id}")
        try:
            highlight.color = color
            self._repo.update(highlight)
            self._session.commit()
            log.info("Alinti rengi guncellendi: id=%d", highlight_id)
            return highlight
        except Exception:
            self._session.rollback()
            log.exception("Alinti rengi guncellenirken hata olustu.")
            raise

    def update_highlight_comment(self, highlight_id: int, comment: str) -> Highlight:
        highlight = self._repo.get_by_id(highlight_id)
        if highlight is None:
            raise ResourceNotFoundError(f"Alinti bulunamadi: id={highlight_id}")
        try:
            highlight.comment = (comment or "").strip() or None
            self._repo.update(highlight)
            self._session.commit()
            log.info("Alinti yorumu guncellendi: id=%d", highlight_id)
            return highlight
        except Exception:
            self._session.rollback()
            log.exception("Alinti yorumu guncellenirken hata olustu.")
            raise

    def get_by_resource(self, resource_id: int) -> list[Highlight]:
        return self._repo.get_by_resource(resource_id)

    def get_all(self) -> list[Highlight]:
        return self._repo.get_all_with_resource()

    def delete_highlights(self, highlight_ids: list[int]) -> int:
        """Birden cok alintiyi tek islemde (tek commit) siler; silinen sayisini doner.

        Zaten silinmis/olmayan kimlikler sessizce atlanir (toplu islem kismen basarisiz
        sayilmaz); bir hata olursa hicbiri silinmez."""
        unique_ids = list(dict.fromkeys(highlight_ids))
        try:
            deleted = sum(1 for highlight_id in unique_ids if self._repo.delete(highlight_id))
            self._session.commit()
            log.info("Alintilar toplu silindi: %d/%d", deleted, len(unique_ids))
            return deleted
        except Exception:
            self._session.rollback()
            log.exception("Alintilar toplu silinirken hata olustu.")
            raise

    def delete_highlight(self, highlight_id: int) -> None:
        try:
            deleted = self._repo.delete(highlight_id)
            if not deleted:
                raise ResourceNotFoundError(f"Alinti bulunamadi: id={highlight_id}")
            self._session.commit()
            log.info("Alinti silindi: id=%d", highlight_id)
        except Exception:
            self._session.rollback()
            log.exception("Alinti silinirken hata olustu.")
            raise
