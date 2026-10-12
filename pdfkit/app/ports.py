from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pdfkit.domain.models import SourceInfo


@dataclass(frozen=True)
class LegacyPdf:
    """Eski duzende (kaynak URL'si ya da `extra_metadata["local_pdf"]`) bir PDF dosyasina bagli kaynak."""

    resource_id: int
    path: Path
    field: str  # "url" | "local_pdf"


class ResourceCatalogPort(Protocol):
    """pdfkit'in uygulamanin kaynak (Resource) kayitlarina eristigi tek arayuz; uygulama tarafinda uygulanir."""

    def create_pdf_resource(self, title: str, file_url: str, extra_metadata: dict) -> int | None:
        """Yerel PDF icin kaynak olusturur; olusan kaynagin kimligini dondurur (hata: None)."""

    def legacy_pdfs(self) -> list[LegacyPdf]:
        """Eski duzende PDF dosyasina bagli tum kaynaklar."""

    def repoint(self, legacy: LegacyPdf, new_path: Path) -> bool:
        """Kaynagin PDF baglantisini depodaki yeni dosyaya yonlendirir."""

    def describe(self, resource_id: int) -> SourceInfo | None:
        """Kaynagin kunyesi (baslik, yazarlar, yil, DOI, durum); kaynak yoksa None. Vault notu ve citekey icin."""
