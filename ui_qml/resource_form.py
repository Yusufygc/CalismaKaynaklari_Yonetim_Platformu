"""Kaynak formu (ekle/duzenle) yardimcilari: form verisini controller yukune cevirme ve duzenleme oncesi/sonrasi
yerel PDF temizligi."""
from dataclasses import dataclass, field

from core.constants.strings import AppStrings
from models import Resource, ResourceStatus
from ui_qml.context import BridgeContext
from utils.url_utils import normalize_url


@dataclass
class PreviousResource:
    """Duzenlemeden onceki kaynagin temizlik icin gereken bilgileri."""

    url: str | None = None
    pdf_urls: list[str] = field(default_factory=list)
    had_local_pdf: bool = False


class ResourceFormHandler:
    def __init__(self, ctx: BridgeContext) -> None:
        self._ctx = ctx

    def parse_payload(self, data: dict) -> dict | None:
        """Form verisini controller yukune cevirir; gecersiz sayisal alanda bildirim verip None doner."""
        status = ResourceStatus.__members__.get(data.get("status", "INBOX"), ResourceStatus.INBOX)
        try:
            category_id = int(data["category_id"]) if data.get("category_id") else None
            priority = int(data.get("priority", 2))
        except (TypeError, ValueError):
            self._ctx.notify.error(AppStrings.NOTIFICATION_INVALID_FORM_DATA)
            return None
        return {
            "title": data.get("title", "").strip(),
            "url": data.get("url", "").strip() or None,
            "category_id": category_id,
            "status": status,
            "priority": priority,
            "content": data.get("content", ""),
            "tag_names": self._tag_names(data),
        }

    def find_duplicate(self, url: str, exclude_id: int = 0) -> Resource | None:
        """Ayni adrese (bkz. `normalize_url`) sahip baska bir kaynak; yoksa None."""
        key = normalize_url(url)
        if not key:
            return None
        for resource in self._ctx.controllers.resources.load_resources_with_filters({"urls_only": True}):
            if resource.id != exclude_id and normalize_url(resource.url) == key:
                return resource
        return None

    def _tag_names(self, data: dict) -> list[str]:
        if "tag_names" in data:
            return [str(t) for t in data["tag_names"]]
        selected_ids = set(data.get("tag_ids") or [])
        return [t.name for t in self._ctx.controllers.tags.load_tags() if t.id in selected_ids]

    def snapshot(self, resource_id: int) -> PreviousResource:
        """Duzenlemeden onceki URL/yerel PDF bilgisi (URL degisirse eski dosyalar temizlensin diye)."""
        old = self._ctx.controllers.resources.get_resource(resource_id)
        if old is None:
            return PreviousResource()
        return PreviousResource(
            url=old.url,
            pdf_urls=self._ctx.pdf_files.owned_pdf_urls(old),
            had_local_pdf="local_pdf" in (old.extra_metadata or {}),
        )

    def cleanup_replaced_url(self, previous: PreviousResource, res: Resource) -> None:
        """Duzenlemede URL degistiyse/kaldirildiysa, eski URL bizim kopyaladigimiz bir yerel PDF'e
        isaret ediyorsa dosyasi/onbellek girdisi oksuz kalirdi."""
        if not previous.url or previous.url == (res.url or None):
            return
        for pdf_url in previous.pdf_urls:
            self._ctx.pdf_files.cleanup_local_pdf(pdf_url)
        self._ctx.pdf_files.clear_failed(res.id)
        if previous.had_local_pdf:
            metadata = {k: v for k, v in (res.extra_metadata or {}).items() if k != "local_pdf"}
            self._ctx.controllers.resources.update_resource(res.id, {"extra_metadata": metadata})
