"""pdfkit'in `ResourceCatalogPort` arayuzunun uygulama tarafi: kaynak kayitlarina controller uzerinden erisir."""
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

from controllers.resource_controller import ResourceController
from models import ResourceStatus, status_label
from pdfkit.api import LegacyPdf, SourceInfo


def _is_local_pdf_url(url: str | None) -> bool:
    return bool(url) and url.startswith("file://") and url.lower().endswith(".pdf")


class ResourceCatalog:
    def __init__(self, resources: ResourceController) -> None:
        self._resources = resources

    def create_pdf_resource(self, title: str, file_url: str, extra_metadata: dict) -> int | None:
        resource = self._resources.add_resource(
            {
                "title": title,
                "url": file_url,
                "category_id": None,
                "status": ResourceStatus.INBOX,
                "priority": 2,
                "content": None,
                "tag_names": [],
                "extra_metadata": extra_metadata,
            }
        )
        return resource.id if resource else None

    def legacy_pdfs(self) -> list[LegacyPdf]:
        items = []
        for resource in self._resources.load_resources_with_filters({}):
            if _is_local_pdf_url(resource.url):
                items.append(LegacyPdf(resource.id, Path(url2pathname(unquote(urlparse(resource.url).path))), "url"))
            local = (resource.extra_metadata or {}).get("local_pdf")
            if local:
                items.append(LegacyPdf(resource.id, Path(local), "local_pdf"))
        return items

    def describe(self, resource_id: int) -> SourceInfo | None:
        resource = self._resources.get_resource(resource_id)
        if resource is None:
            return None
        meta = resource.extra_metadata or {}
        authors = meta.get("authors") or []
        year = meta.get("year")
        return SourceInfo(
            title=resource.title or "",
            authors=tuple(str(a) for a in authors) if isinstance(authors, (list, tuple)) else (str(authors),),
            year=int(year) if str(year or "").isdigit() else None,
            doi=str(meta["doi"]) if meta.get("doi") else None,
            status=status_label(resource.status),
            url=resource.url if resource.url and not resource.url.startswith("file:") else None,
        )

    def repoint(self, legacy: LegacyPdf, new_path: Path) -> bool:
        if legacy.field == "url":
            changes = {"url": new_path.as_uri()}
        else:
            resource = self._resources.get_resource(legacy.resource_id)
            if resource is None:
                return False
            changes = {"extra_metadata": {**(resource.extra_metadata or {}), "local_pdf": str(new_path)}}
        return self._resources.update_resource(legacy.resource_id, changes) is not None
