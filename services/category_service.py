import re

from sqlalchemy.orm import Session

from core.exceptions import DuplicateRecordError, ResourceNotFoundError, ValidationError
from core.logger import log
from models import Category
from repositories.category_repo import CategoryRepository

_HEX_RE = re.compile(r"^#([0-9A-Fa-f]{6})$")


class CategoryService:

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = CategoryRepository(session)

    def create_category(self, name: str, color_hex: str, icon: str = "") -> Category:
        name = name.strip()
        if not _HEX_RE.match(color_hex):
            raise ValidationError(f"Gecersiz HEX renk kodu: {color_hex!r}. Beklenen format: #RRGGBB")

        if self._repo.get_by_name(name):
            raise DuplicateRecordError(f"Bu isimde bir kategori zaten var: {name!r}")

        try:
            category = Category(name=name, color_hex=color_hex, icon=icon or None)
            self._repo.create(category)
            self._session.commit()
            log.info("Yeni kategori olusturuldu: %r", name)
            return category
        except Exception:
            self._session.rollback()
            log.exception("Kategori olusturulurken hata olustu.")
            raise

    def update_category(self, category_id: int, name: str | None = None,
                        color_hex: str | None = None, icon: str | None = None) -> Category:
        category = self._repo.get_by_id(category_id)
        if category is None:
            raise ResourceNotFoundError(f"Kategori bulunamadi: id={category_id}")

        if color_hex is not None and not _HEX_RE.match(color_hex):
            raise ValidationError(f"Gecersiz HEX renk kodu: {color_hex!r}")

        if name is not None:
            name = name.strip()
            existing = self._repo.get_by_name(name)
            if existing and existing.id != category_id:
                raise DuplicateRecordError(f"Bu isimde baska bir kategori zaten var: {name!r}")
            category.name = name

        if color_hex is not None:
            category.color_hex = color_hex
        if icon is not None:
            category.icon = icon

        try:
            self._repo.update(category)
            self._session.commit()
            log.info("Kategori guncellendi: id=%d", category_id)
            return category
        except Exception:
            self._session.rollback()
            log.exception("Kategori guncellenirken hata olustu.")
            raise

    def delete_category(self, category_id: int) -> None:
        try:
            deleted = self._repo.delete(category_id)
            if not deleted:
                raise ResourceNotFoundError(f"Kategori bulunamadi: id={category_id}")
            self._session.commit()
            log.info("Kategori silindi: id=%d", category_id)
        except Exception:
            self._session.rollback()
            log.exception("Kategori silinirken hata olustu.")
            raise

    def get_all(self) -> list[Category]:
        return self._repo.get_all()

    def get_by_id(self, category_id: int) -> Category:
        category = self._repo.get_by_id(category_id)
        if category is None:
            raise ResourceNotFoundError(f"Kategori bulunamadi: id={category_id}")
        return category
