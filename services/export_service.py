from datetime import datetime

from core.constants.highlight_labels import HIGHLIGHT_LABELS, label_for_color
from models import Resource
from services.citation_service import CitationService


def _quote(text: str) -> str:
    return " ".join((text or "").split())


class ExportService:
    """Bir kaynağın (ya da tüm kütüphanenin) alıntı/not/kelime birikimini Markdown'a döker.

    Tez ve literatür taraması için: her kaynak APA atfıyla başlar; alıntılar
    akademik anlam etiketine (Yöntem, Bulgu / Sonuç, ...) göre gruplanır ve
    sayfa numarası taşır.
    """

    @classmethod
    def has_content(cls, resource: Resource) -> bool:
        return bool(resource.highlights or resource.pdf_notes or resource.vocabulary or resource.content)

    @classmethod
    def resource_markdown(cls, resource: Resource, level: int = 1) -> str:
        heading, section = "#" * level, "#" * (level + 1)
        lines = [f"{heading} {resource.title}", ""]
        lines += cls._citation_block(resource)
        lines += cls._highlights_section(resource, section, "#" * (level + 2))
        lines += cls._notes_section(resource, section)
        lines += cls._vocabulary_section(resource, section)
        lines += cls._personal_notes_section(resource, section)
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _citation_block(resource: Resource) -> list[str]:
        lines = [f"> {CitationService.format(resource.title, resource.extra_metadata or {}, 'apa')}"]
        if resource.url and not resource.url.startswith("file://"):
            lines.append(f"> Bağlantı: {resource.url}")
        return lines + [""]

    @staticmethod
    def _highlights_section(resource: Resource, section: str, subsection: str) -> list[str]:
        """Alıntılar, akademik anlam etiketine göre gruplu (sayfa/konum sırasıyla)."""
        highlights = sorted(
            resource.highlights or [],
            key=lambda x: (x.page_number if x.page_number is not None else 10**6, x.start_index or 0),
        )
        if not highlights:
            return []
        label_order = [entry["label"] for entry in HIGHLIGHT_LABELS] + ["Genel"]
        grouped: dict[str, list] = {label: [] for label in label_order}
        for highlight in highlights:
            grouped[label_for_color(highlight.color)].append(highlight)

        lines = [f"{section} Alıntılar", ""]
        for label in label_order:
            items = grouped[label]
            if items:
                lines += [f"{subsection} {label} ({len(items)})", ""]
                lines += [line for item in items for line in ExportService._highlight_lines(item)]
                lines.append("")
        return lines

    @staticmethod
    def _highlight_lines(item) -> list[str]:
        page = f" (s. {item.page_number + 1})" if item.page_number is not None else ""
        lines = [f"- “{_quote(item.content)}”{page}"]
        if item.comment:
            lines.append(f"  - Yorum: {_quote(item.comment)}")
        return lines

    @staticmethod
    def _notes_section(resource: Resource, section: str) -> list[str]:
        notes = sorted(resource.pdf_notes or [], key=lambda n: (n.page, n.y))
        if not notes:
            return []
        return [f"{section} Sayfa Notları", ""] + [f"- s. {n.page + 1}: {_quote(n.note_text)}" for n in notes] + [""]

    @staticmethod
    def _vocabulary_section(resource: Resource, section: str) -> list[str]:
        if not resource.vocabulary:
            return []
        lines = [f"{section} Kelimeler", ""]
        for v in resource.vocabulary:
            entry = f"- **{v.word}**: {v.translation}"
            if v.context_sentence:
                entry += f" — _{_quote(v.context_sentence)}_"
            lines.append(entry)
        return lines + [""]

    @staticmethod
    def _personal_notes_section(resource: Resource, section: str) -> list[str]:
        if resource.content and resource.content.strip():
            return [f"{section} Kişisel Notlar", "", resource.content.strip(), ""]
        return []

    @classmethod
    def library_markdown(cls, resources: list[Resource]) -> str:
        exportable = [r for r in resources if cls.has_content(r)]
        header = [
            "# Literatür Notları",
            "",
            f"_Oluşturulma: {datetime.now():%d.%m.%Y %H:%M} · {len(exportable)} kaynak_",
            "",
        ]
        body = [cls.resource_markdown(r, level=2) for r in exportable]
        return "\n".join(header) + "\n" + "\n".join(body)
