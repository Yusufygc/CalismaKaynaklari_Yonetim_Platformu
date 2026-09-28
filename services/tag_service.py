from sqlalchemy.orm import Session

from core.exceptions import DuplicateRecordError, ResourceNotFoundError, ValidationError
from core.logger import log
from models import Tag
from repositories.tag_repo import TagRepository


class TagService:

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = TagRepository(session)

    def get_or_create_tag(self, name: str) -> Tag:
        """Kaynak ekleme akisinda kullanilir: varsa getir, yoksa olustur."""
        normalized = name.lower().strip()
        existing = self._repo.get_by_name(normalized)
        if existing:
            return existing
        try:
            tag = Tag(name=normalized)
            self._repo.create(tag)
            self._session.commit()
            log.info("Yeni etiket olusturuldu: %r", normalized)
            return tag
        except Exception:
            self._session.rollback()
            log.exception("Etiket olusturulurken hata olustu.")
            raise

    def create_tag(self, name: str) -> Tag:
        """Kullanici niyetli olusturma — zaten varsa DuplicateRecordError."""
        normalized = name.lower().strip()
        if not normalized:
            raise ValidationError("Etiket adi bos olamaz.")
        if self._repo.get_by_name(normalized):
            raise DuplicateRecordError(f"Bu isimde etiket zaten var: {normalized!r}")
        try:
            tag = Tag(name=normalized)
            self._repo.create(tag)
            self._session.commit()
            log.info("Yeni etiket olusturuldu: %r", normalized)
            return tag
        except Exception:
            self._session.rollback()
            log.exception("Etiket olusturulurken hata olustu.")
            raise

    def update_tag(self, tag_id: int, new_name: str) -> Tag:
        normalized = new_name.lower().strip()
        if not normalized:
            raise ValidationError("Etiket adi bos olamaz.")
        tag = self._repo.get_by_id(tag_id)
        if tag is None:
            raise ResourceNotFoundError(f"Etiket bulunamadi: id={tag_id}")
        existing = self._repo.get_by_name(normalized)
        if existing and existing.id != tag_id:
            raise DuplicateRecordError(f"Bu isimde etiket zaten var: {normalized!r}")
        try:
            tag.name = normalized
            self._repo.update(tag)
            self._session.commit()
            log.info("Etiket guncellendi: id=%d", tag_id)
            return tag
        except Exception:
            self._session.rollback()
            log.exception("Etiket guncellenirken hata olustu.")
            raise

    def get_all(self) -> list[Tag]:
        return self._repo.get_all()

    def delete_tag(self, tag_id: int) -> None:
        try:
            deleted = self._repo.delete(tag_id)
            if not deleted:
                raise ResourceNotFoundError(f"Etiket bulunamadi: id={tag_id}")
            self._session.commit()
            log.info("Etiket silindi: id=%d", tag_id)
        except Exception:
            self._session.rollback()
            log.exception("Etiket silinirken hata olustu.")
            raise
