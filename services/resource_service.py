import re
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from core.exceptions import (
    InvalidURLError,
    ResourceNotFoundError,
    ValidationError,
)
from core.logger import log
from models import Category, Resource, Tag
from repositories.category_repo import CategoryRepository
from repositories.resource_repo import ResourceFilter, ResourceRepository
from repositories.tag_repo import TagRepository
from utils.reading_time import estimate_reading_minutes
from utils.url_utils import PLATFORM_NAMES, detect_category_name
from .schemas import ResourceCreateSchema, ResourceUpdateSchema

_AUTO_CATEGORY_COLORS = {
    "YouTube": "#EF4444",
    "Instagram": "#EC4899",
    "LinkedIn": "#38BDF8",
    "GitHub": "#64748B",
    "Twitter": "#38BDF8",
    "Medium": "#10B981",
    "Substack": "#F59E0B",
    "Reddit": "#F97316",
    "Makale": "#8B5CF6",
    "Web": "#6366F1",
}

# Nokta ile ayrilmis en az iki etiketli ana bilgisayar adi (`localhost` bilerek reddedilir).
_HOST_RE = re.compile(r"^([\w\-]+\.)+[\w\-]+$")


def _is_valid_web_url(url: str) -> bool:
    """http(s) + noktali ana bilgisayar; yol/sorgu serbest (`~`, `[]`, `|` dahil), bosluk/kontrol karakteri ve kullanici bilgisi yok."""
    if any(ch.isspace() or ord(ch) < 32 for ch in url):
        return False
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ("http", "https") or "@" in parsed.netloc:
        return False
    try:
        parsed.port
    except ValueError:
        return False
    return bool(parsed.hostname and _HOST_RE.match(parsed.hostname))


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme == "file":
        # Yerel PDF ice aktarimi: host/domain formati gecersiz, sadece bos
        # olmayan bir dosya yolu yeterli.
        if not parsed.path:
            raise InvalidURLError(f"Gecersiz URL formati: {url!r}")
        return
    if not _is_valid_web_url(url):
        raise InvalidURLError(f"Gecersiz URL formati: {url!r}")


def _as_tuple(filters: dict, plural: str, singular: str) -> tuple:
    """`statuses`/`status` gibi cogul + tekil (takma ad) anahtarlari birlestirir; skaler degeri listeler."""
    values = filters.get(plural)
    if values is None:
        values = filters.get(singular)
    if values is None:
        return ()
    return tuple(values) if isinstance(values, (list, set, tuple)) else (values,)


def _resource_filter_from_dict(filters: dict) -> ResourceFilter:
    """Bridge/controller'in gevsek filtre sozlugunu (takma adlarla) tipli sorgu kriterine cevirir."""
    return ResourceFilter(
        statuses=_as_tuple(filters, "statuses", "status"),
        category_id=filters.get("category_id"),
        tag_ids=_as_tuple(filters, "tag_ids", "tag_id"),
        priorities=_as_tuple(filters, "priorities", "priority"),
        favorites_only=bool(filters.get("favorites_only", filters.get("is_favorite", False))),
        urls_only=bool(filters.get("urls_only", False)),
        keyword=filters.get("keyword"),
        content_resource_ids=_as_tuple(filters, "content_resource_ids", "content_resource_id"),
    )


def _normalize_tag_names(tag_names: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for tag_name in tag_names:
        name = tag_name.lower().strip()
        if name and name not in seen:
            normalized.append(name)
            seen.add(name)
    return normalized


def _bare_host(url: str) -> str:
    """URL'nin ana bilgisayar adi; `www.` ve `m.` onekleri atilir."""
    host = (urlparse(url).hostname or "").lower()
    for prefix in ("www.", "m."):
        if host.startswith(prefix):
            host = host[len(prefix):]
    return host


def _platform_tag_name(host: str) -> str | None:
    for suffix, tag_name in PLATFORM_NAMES.items():
        if host == suffix or host.endswith(f".{suffix}"):
            return tag_name
    return None


def _url_tag_names(url: str | None) -> list[str]:
    if not url:
        return []

    host = _bare_host(url)
    platform = _platform_tag_name(host)
    if platform:
        return [platform]

    parts = [part for part in host.split(".") if part]
    if len(parts) >= 2:
        return [parts[-2]]
    return parts[:1]


def _merge_tag_names(tag_names: list[str], url: str | None) -> list[str]:
    return _normalize_tag_names([*tag_names, *_url_tag_names(url)])


class ResourceService:

    def __init__(self, session: Session) -> None:
        self._session = session
        self._resource_repo = ResourceRepository(session)
        self._tag_repo = TagRepository(session)
        self._category_repo = CategoryRepository(session)

    # ------------------------------------------------------------------ #
    # Okuma
    # ------------------------------------------------------------------ #

    def get_by_id(self, resource_id: int) -> Resource:
        resource = self._resource_repo.get_by_id(resource_id)
        if resource is None:
            raise ResourceNotFoundError(f"Kaynak bulunamadi: id={resource_id}")
        return resource

    def query_resources(self, filters: dict) -> list[Resource]:
        return self._resource_repo.query_filtered(_resource_filter_from_dict(filters))

    # ------------------------------------------------------------------ #
    # Yazma
    # ------------------------------------------------------------------ #

    def add_new_resource(self, payload: ResourceCreateSchema) -> Resource:
        resource = self._build_resource(payload)

        # Once resource'u session'a ekle, sonra etiketleri bagla.
        # Bu sayede flush sirasinda relationship tam olarak cozumlenir.
        try:
            self._session.add(resource)
            self._session.flush()  # ID atanir, iliski tablosu hazir olur

            resource.tags = self._get_or_create_tags(_merge_tag_names(payload.tag_names, resource.url))

            self._session.commit()
            log.info("Yeni kaynak eklendi: id=%d title=%r", resource.id, resource.title)
        except Exception:
            self._session.rollback()
            log.exception("Kaynak eklenirken hata olustu.")
            raise

        return resource

    def _build_resource(self, payload: ResourceCreateSchema) -> Resource:
        """Yeni kaydi dogrular (baslik, URL, kategori, oncelik) ve oturuma eklemeden olusturur."""
        title = payload.title.strip()
        if not title:
            raise ValidationError("Baslik bos olamaz.")

        url = (payload.url or "").strip()
        if url:
            _validate_url(url)

        category_id = self._resolve_new_category_id(payload.category_id, url or None)

        if payload.priority not in (1, 2, 3):
            raise ValidationError("Oncelik degeri 1, 2 veya 3 olmalidir.")

        return Resource(
            title=title,
            url=url or None,
            category_id=category_id,
            status=payload.status,
            priority=payload.priority,
            content=payload.content,
            reading_minutes=estimate_reading_minutes(payload.content),
            extra_metadata=payload.extra_metadata,
        )

    def _resolve_new_category_id(self, category_id: int | None, url: str | None) -> int | None:
        if category_id is None:
            return self._auto_category_id(url)
        if self._category_repo.get_by_id(category_id) is None:
            raise ResourceNotFoundError(f"Kategori bulunamadi: id={category_id}")
        return category_id

    def update_resource(self, resource_id: int, payload: ResourceUpdateSchema) -> Resource:
        resource = self.get_by_id(resource_id)
        fields = payload.model_fields_set

        # Tum mutasyonlar (attribute atamalari + _apply_* validasyonlari) try
        # icinde: _apply_category/_apply_priority gibi metotlar ortada hata
        # firlatirsa, o ana kadar resource uzerinde yapilmis degisiklikler
        # rollback ile geri alinmali -- aksi halde paylasilan, uzun omurlu
        # session'da kirli/yari-guncellenmis bir obje asili kalip, sonraki
        # alakasiz bir commit'te sessizce kalicilasabilirdi.
        try:
            self._apply_title(resource, payload, fields)
            self._apply_url(resource, payload, fields)
            self._apply_category(resource, payload, fields)
            self._apply_status(resource, payload, fields)
            self._apply_priority(resource, payload, fields)
            self._apply_content(resource, payload, fields)
            self._apply_metadata(resource, payload, fields)
            self._apply_tags(resource, payload, fields)
            self._resource_repo.update(resource)
            self._session.commit()
            log.info("Kaynak guncellendi: id=%d", resource_id)
        except Exception:
            self._session.rollback()
            log.exception("Kaynak guncellenirken hata olustu.")
            raise

        return resource

    @staticmethod
    def _apply_title(resource: Resource, payload: ResourceUpdateSchema, fields: set[str]) -> None:
        if "title" not in fields:
            return
        title = (payload.title or "").strip()
        if not title:
            raise ValidationError("Baslik bos olamaz.")
        resource.title = title

    @staticmethod
    def _apply_url(resource: Resource, payload: ResourceUpdateSchema, fields: set[str]) -> None:
        if "url" not in fields:
            return
        url = (payload.url or "").strip()
        if url:
            _validate_url(url)
        resource.url = url or None

    def _apply_category(self, resource: Resource, payload: ResourceUpdateSchema, fields: set[str]) -> None:
        if "category_id" not in fields:
            return
        cat_id = payload.category_id
        if cat_id is not None and self._category_repo.get_by_id(cat_id) is None:
            raise ResourceNotFoundError(f"Kategori bulunamadi: id={cat_id}")
        resource.category_id = cat_id

    @staticmethod
    def _apply_status(
        resource: Resource, payload: ResourceUpdateSchema, fields: set[str]
    ) -> None:
        if "status" in fields:
            resource.status = payload.status

    @staticmethod
    def _apply_priority(resource: Resource, payload: ResourceUpdateSchema, fields: set[str]) -> None:
        if "priority" not in fields:
            return
        priority = payload.priority
        if priority not in (1, 2, 3):
            raise ValidationError("Oncelik degeri 1, 2 veya 3 olmalidir.")
        resource.priority = priority

    @staticmethod
    def _apply_content(resource: Resource, payload: ResourceUpdateSchema, fields: set[str]) -> None:
        if "content" in fields:
            resource.content = payload.content
        if "full_text" in fields:
            resource.full_text = payload.full_text
        if fields & {"content", "full_text"}:
            resource.reading_minutes = estimate_reading_minutes(resource.full_text or resource.content)

    def _apply_tags(self, resource: Resource, payload: ResourceUpdateSchema, fields: set[str]) -> None:
        if not fields & {"tag_names", "url"}:
            return
        base_tag_names = payload.tag_names if "tag_names" in fields else [tag.name for tag in resource.tags]
        resource.tags = self._get_or_create_tags(_merge_tag_names(base_tag_names, resource.url))

    @staticmethod
    def _apply_metadata(resource: Resource, payload: ResourceUpdateSchema, fields: set[str]) -> None:
        if "is_pinned" in fields:
            resource.is_pinned = bool(payload.is_pinned)
        if "extra_metadata" in fields:
            resource.extra_metadata = payload.extra_metadata

    def toggle_pin(self, resource_id: int) -> Resource:
        resource = self.get_by_id(resource_id)
        new_value = not bool(resource.is_pinned)
        try:
            self._resource_repo.set_pinned(resource_id, new_value)
            self._session.commit()
            log.info("Kaynak pin durumu: id=%d pinned=%s", resource_id, new_value)
        except Exception:
            self._session.rollback()
            log.exception("Pin durumu guncellenemedi.")
            raise
        return resource

    def toggle_favorite(self, resource_id: int) -> Resource:
        resource = self.get_by_id(resource_id)
        new_value = not bool(resource.is_favorite)
        try:
            self._resource_repo.set_favorite(resource_id, new_value)
            self._session.commit()
            log.info(
                "Kaynak favori durumu: id=%d favorite=%s", resource_id, new_value
            )
        except Exception:
            self._session.rollback()
            log.exception("Favori durumu guncellenemedi.")
            raise
        return resource

    def delete_resource(self, resource_id: int) -> None:
        try:
            deleted = self._resource_repo.delete(resource_id)
            if not deleted:
                raise ResourceNotFoundError(f"Kaynak bulunamadi: id={resource_id}")
            self._session.commit()
            log.info("Kaynak silindi: id=%d", resource_id)
        except Exception:
            self._session.rollback()
            log.exception("Kaynak silinirken hata olustu.")
            raise

    def _get_or_create_tags(self, tag_names: list[str]) -> list[Tag]:
        tags: list[Tag] = []
        for normalized in _normalize_tag_names(tag_names):
            tag = self._tag_repo.get_by_name(normalized)
            if tag is None:
                tag = Tag(name=normalized)
                self._session.add(tag)
                self._session.flush()
            tags.append(tag)
        return tags

    def _auto_category_id(self, url: str | None) -> int | None:
        """Kullanici kategori secmediyse URL'den otomatik kategori atar
        (orn. youtube.com -> 'YouTube', bir PDF/DOI linki -> 'Makale').
        Kategori DB'de yoksa olusturur; varsa mevcut kaydi kullanir."""
        name = detect_category_name(url)
        if name is None:
            return None

        category = self._category_repo.get_by_name(name)
        if category is None:
            category = Category(
                name=name,
                color_hex=_AUTO_CATEGORY_COLORS.get(name, "#64748B"),
            )
            self._category_repo.create(category)

        return category.id
