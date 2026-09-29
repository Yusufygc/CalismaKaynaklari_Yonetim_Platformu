from models import Highlight, PdfNote, Resource, Vocabulary
from services.export_service import ExportService


def _resource():
    r = Resource(
        title="Attention Is All You Need",
        url="https://arxiv.org/pdf/1706.03762",
        extra_metadata={"authors": ["Ashish Vaswani", "Noam Shazeer"], "year": 2017, "venue": "NeurIPS"},
        content="Tezin 3. bolumunde kullan.",
    )
    r.highlights = [
        Highlight(content="self-attention relates positions", color="#06B6D4", page_number=1, start_index=10,
                  comment="Yontem bolumune"),
        Highlight(content="BLEU 28.4", color="#22C55E", page_number=7, start_index=5),
        Highlight(content="ilk sayfa alintisi", color="#06B6D4", page_number=0, start_index=1),
    ]
    r.pdf_notes = [PdfNote(page=2, x=1.0, y=2.0, note_text="Bunu tekrar oku")]
    r.vocabulary = [Vocabulary(word="attention", translation="dikkat", context_sentence="We use  attention\nlayers.")]
    return r


def test_resource_markdown_structure_and_grouping():
    md = ExportService.resource_markdown(_resource())

    assert md.startswith("# Attention Is All You Need")
    assert "> Vaswani, A., & Shazeer, N. (2017). Attention Is All You Need. NeurIPS." in md
    assert "> Bağlantı: https://arxiv.org/pdf/1706.03762" in md
    # Etiket sirasi: Yontem, sonra Bulgu (paletteki sira Yontem'den once Bulgu'dur)
    assert md.index("### Bulgu / Sonuç (1)") < md.index("### Yöntem (2)")
    # Yontem grubu icinde sayfa sirasi
    assert md.index("ilk sayfa alintisi") < md.index("self-attention relates positions")
    assert "- “self-attention relates positions” (s. 2)" in md
    assert "  - Yorum: Yontem bolumune" in md
    assert "- s. 3: Bunu tekrar oku" in md
    assert "- **attention**: dikkat — _We use attention layers._" in md
    assert "## Kişisel Notlar" in md and "Tezin 3. bolumunde kullan." in md


def test_library_markdown_skips_empty_resources_and_shifts_headings():
    empty = Resource(title="Bos Kaynak")
    md = ExportService.library_markdown([_resource(), empty])

    assert md.startswith("# Literatür Notları")
    assert "1 kaynak" in md
    assert "## Attention Is All You Need" in md
    assert "Bos Kaynak" not in md
    assert "### Alıntılar" in md
