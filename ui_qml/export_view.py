"""Markdown disa aktarimi icin kaynak gorunumu: PDF belgesi olan kaynaklarin alinti/not/kelimeleri pdfkit'ten gelir.

`ExportService` `highlights`, `pdf_notes` ve `vocabulary` alanlarini okur: eski `Resource` iliskilerinde yalniz `highlights`/`vocabulary` vardir (HTML makaleler), `pdf_notes` yalniz burada uretilen PDF gorunumunde bulunur. PDF belgesi olan kaynaklar icin
bu alanlari pdfkit verisiyle dolduran hafif bir kopya verilir; diger kaynaklar (HTML makaleler) oldugu gibi gecer.
Gecici: Faz 8'de eski tablolar kalkinca sadelesir.
"""
from types import SimpleNamespace

from models import Resource
from pdfkit.api import PdfLibrary, effective_color, obsidian_tag


def export_view(resource: Resource, pdf_library: PdfLibrary):
    data = pdf_library.annotations_of(resource.id)
    if data is None:
        return resource
    highlights = []
    for annotation in data.highlights:
        first = annotation.segments[0] if annotation.segments else None
        highlights.append(
            SimpleNamespace(
                content=annotation.quote_exact,
                color=effective_color(annotation.label_key, annotation.color),
                comment=annotation.comment,
                tags=[tag for tag in (obsidian_tag(t) for t in annotation.tags) if tag],
                page_number=first.page if first else None,
                start_index=first.start if first else None,
            )
        )
    return SimpleNamespace(
        title=resource.title,
        url=resource.url,
        extra_metadata=resource.extra_metadata,
        content=resource.content,
        highlights=highlights,
        pdf_notes=[SimpleNamespace(page=n.page, y=n.y, note_text=n.text) for n in data.notes],
        vocabulary=[
            SimpleNamespace(word=t.word, translation=t.translation, context_sentence=t.context_sentence)
            for t in data.terms
        ],
    )
