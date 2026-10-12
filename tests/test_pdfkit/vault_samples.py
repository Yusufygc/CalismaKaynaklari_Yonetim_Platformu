"""Vault notu testleri icin sabit ornek veri (altin dosya `golden/vault_note.golden` bundan uretilir)."""
from pdfkit.domain.annotations import STATUS_OK, STATUS_ORPHANED, Annotation, PageNote, Segment, Term
from pdfkit.domain.models import Document, SourceInfo
from pdfkit.domain.vault_note import NoteContent

SHA = "ab" * 32
DOCUMENT = Document(1, SHA, "store/ab/x.pdf", 10, 12, True, None, None, None, "local", None, None)
INFO = SourceInfo("Deep learning", ("Yann LeCun", "Y. Bengio"), 2015, "10.1038/nature14539", "Devam Ediyor")


def annotation(uid_tail, label="finding", quote="metin", comment=None, tags=(), page=0, start=0, status=STATUS_OK, annotation_id=1):
    segments = [Segment(page, start, start + 10, "x")]
    return Annotation(
        annotation_id, "01HZX3K9M2P4Q6R8S0T1V2" + uid_tail, 1, label, None, comment, list(tags), quote, None, None,
        segments, None, status,
    )


def sample_content() -> NoteContent:
    finding = annotation(
        "W3X4", "finding", "Model   doğruluğu\n%92 oldu.", "Çok önemli.\nİkinci satır %% bozucu",
        ["hipotez", "örnek etiket", "123"], page=2, start=10, annotation_id=1,
    )
    general = annotation("WZZZ", "general", "Genel alıntı", page=0, start=5, annotation_id=2)
    orphan = annotation("WAAA", "critique", "Kayıp metin", page=1, start=1, status=STATUS_ORPHANED, annotation_id=3)
    note = PageNote(1, "01HZX3K9M2P4Q6R8S0T1V2WNNN", 1, 3, 1.0, 2.0, "Tekrar oku\nsonra")
    term = Term(1, "01HZX3K9M2P4Q6R8S0T1V2WTTT", 1, "ubiquitous", "her yerde", "It is ubiquitous.", 0, [Segment(4, 1, 5, "")])
    return NoteContent(DOCUMENT, INFO, "lecun2015deep", [finding, general, orphan], [note], [term])
