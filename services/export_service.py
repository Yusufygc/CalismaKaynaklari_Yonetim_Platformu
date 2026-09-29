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
        h = "#" * level
        h2 = "#" * (level + 1)
        h3 = "#" * (level + 2)
        metadata = resource.extra_metadata or {}
        lines = [f"{h} {resource.title}", ""]

        lines.append(f"> {CitationService.format(resource.title, metadata, 'apa')}")
        if resource.url and not resource.url.startswith("file://"):
            lines.append(f"> Bağlantı: {resource.url}")
        lines.append("")

        highlights = sorted(
            resource.highlights or [],
            key=lambda x: (x.page_number if x.page_number is not None else 10**6, x.start_index or 0),
        )
        if highlights:
            lines += [f"{h2} Alıntılar", ""]
            label_order = [entry["label"] for entry in HIGHLIGHT_LABELS] + ["Genel"]
            grouped: dict[str, list] = {label: [] for label in label_order}
            for highlight in highlights:
                grouped[label_for_color(highlight.color)].append(highlight)
            for label in label_order:
                items = grouped[label]
                if not items:
                    continue
                lines += [f"{h3} {label} ({len(items)})", ""]
                for item in items:
                    page = f" (s. {item.page_number + 1})" if item.page_number is not None else ""
                    lines.append(f"- “{_quote(item.content)}”{page}")
                    if item.comment:
                        lines.append(f"  - Yorum: {_quote(item.comment)}")
                lines.append("")

        notes = sorted(resource.pdf_notes or [], key=lambda n: (n.page, n.y))
        if notes:
            lines += [f"{h2} Sayfa Notları", ""]
            lines += [f"- s. {n.page + 1}: {_quote(n.note_text)}" for n in notes]
            lines.append("")

        vocabulary = resource.vocabulary or []
        if vocabulary:
            lines += [f"{h2} Kelimeler", ""]
            for v in vocabulary:
                entry = f"- **{v.word}**: {v.translation}"
                if v.context_sentence:
                    entry += f" — _{_quote(v.context_sentence)}_"
                lines.append(entry)
            lines.append("")

        if resource.content and resource.content.strip():
            lines += [f"{h2} Kişisel Notlar", "", resource.content.strip(), ""]

        return "\n".join(lines).rstrip() + "\n"

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
