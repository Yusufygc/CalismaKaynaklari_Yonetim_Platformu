from typing import Iterable

from utils.doi_utils import doi_from_url, normalize_doi


class LibraryIndex:
    """Kutuphanedeki kaynaklari DOI / OpenAlex kimligiyle arar (yinelenen kaydi ve
    "kutuphanede var" rozetini belirlemek icin). Saf, veritabanina dokunmaz."""

    def __init__(self, resources: Iterable) -> None:
        self._by_doi: dict[str, int] = {}
        self._by_openalex: dict[str, int] = {}
        for resource in resources:
            metadata = getattr(resource, "extra_metadata", None) or {}
            self.add(
                resource.id,
                metadata.get("doi") or doi_from_url(getattr(resource, "url", None)),
                metadata.get("openalex_id"),
            )

    def add(self, resource_id: int, doi: str | None = None, openalex_id: str | None = None) -> None:
        """Yeni eklenen kaynagi indekse yazar (ayni toplu islemde tekrar eklenmesin diye)."""
        key = normalize_doi(doi)
        if key:
            self._by_doi.setdefault(key, resource_id)
        oa_key = (openalex_id or "").strip().lower()
        if oa_key:
            self._by_openalex.setdefault(oa_key, resource_id)

    def find(self, doi: str | None = None, openalex_id: str | None = None) -> int | None:
        """Eslesen kaynagin id'si; yoksa None."""
        key = normalize_doi(doi)
        if key and key in self._by_doi:
            return self._by_doi[key]
        oa_key = (openalex_id or "").strip().lower()
        if oa_key and oa_key in self._by_openalex:
            return self._by_openalex[oa_key]
        return None
