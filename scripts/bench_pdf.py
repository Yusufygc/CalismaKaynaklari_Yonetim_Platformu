"""PDF okuyucu performans olcumu (tekrarlanabilir; harici PDF gerekmez).

Kullanim (proje kokunden):
    .venv/Scripts/python.exe scripts/bench_pdf.py [--pages 15] [--annotations 25,100,300] [--pdf gercek.pdf] [--json cikti.json]

`--pdfkit` ile pdfkit yolu da olculur (belge acma, tembel geometri, sayfa modeli).

Olcer (UI thread'inde gecen sure -- donma bu sureden dogar):
  - QPdfDocument.load
  - kaynak serilestirme (`ResourceSerializer.serialize`): alinti geometrisi dahil
  - tek alinti ekleme sonrasi gereken is (`AnnotationsBridge._save_highlight`)
  - pypdf tam metin cikarimi (arka plan isi; sayfa basina sure)

Sentetik PDF `build_pdf` ile uretilir: sabit tohum, yogun metin, ASCII Turkce. Gercek bir makale PDF'iyle
olcmek icin `--pdf` verilir (gomulu yazi tipli gercek PDF'ler sentetikten 2-20 kat agirdir).
"""
import argparse
import json
import os
import random
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_WORDS = (
    "arastirma yontem bulgu sonuc model veri analiz deney hipotez degisken ornek kuram "
    "literatur siniflandirma ogrenme sinir agi katman egitim dogruluk hata kayip optimizasyon "
    "dikkat mekanizmasi temsil vektor gomme dizi cumle belge kume ozellik cikarim"
).split()


def build_pdf(pages: int, lines_per_page: int = 46, seed: int = 7) -> bytes:
    """Cok sayfali (612x792), Helvetica 10pt, yogun metinli gecerli PDF."""
    rng = random.Random(seed)
    objects: list[bytes] = [b"", b""]  # 1: Catalog, 2: Pages (asagida doldurulur)
    kids = []
    font_ref = None
    page_bodies = []
    for _ in range(pages):
        content = ["BT", "/F1 10 Tf", "50 750 Td", "15 TL"]
        for i in range(lines_per_page):
            line = " ".join(rng.choice(_WORDS) for _ in range(14)).capitalize() + "."
            content.append(f"({line}) Tj" if i == 0 else f"T* ({line}) Tj")
        content.append("ET")
        page_bodies.append("\n".join(content).encode("latin-1"))
    first_page_obj = 4
    font_ref = 3
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")  # 3
    for index, stream in enumerate(page_bodies):
        page_obj = first_page_obj + index * 2
        kids.append(f"{page_obj} 0 R")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {page_obj + 1} 0 R "
            f"/Resources << /Font << /F1 {font_ref} 0 R >> >> >>".encode()
        )
        objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {pages} >>".encode()
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode() + b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode()
    return bytes(out)


def best_ms(fn, repeat: int = 3) -> float:
    best = float("inf")
    for _ in range(repeat):
        start = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - start)
    return best * 1000


def run(pages: int, annotation_counts: list[int], source_pdf: Path | None = None) -> dict:
    from PySide6.QtPdf import QPdfDocument
    from PySide6.QtWidgets import QApplication
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from models import Base
    from services.article_extraction_service import _extract_pdf_html
    from services.schemas import HighlightPosition
    from ui_qml.bridge import QmlBridge

    results: dict = {"pages": pages, "serialize": [], "add_one": []}
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:  # Windows: acik QPdfDocument dosyayi kilitler
        pdf = Path(tmp) / "bench.pdf"
        pdf.write_bytes(source_pdf.read_bytes() if source_pdf else build_pdf(pages))
        results["pdf_kb"] = round(pdf.stat().st_size / 1024)
        results["source"] = "gercek" if source_pdf else "sentetik"

        _app = QApplication.instance() or QApplication([])
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        bridge = QmlBridge(sessionmaker(bind=engine)())

        doc = QPdfDocument()
        results["load_ms"] = round(best_ms(lambda: QPdfDocument().load(str(pdf))), 1)
        doc.load(str(pdf))
        results["pages"] = doc.pageCount()
        texts = [doc.getSelectionAtIndex(p, 0, 1_000_000).text() for p in range(doc.pageCount())]

        resource = bridge.controllers.resources.add_resource({"title": "Bench", "url": pdf.as_uri(), "extra_metadata": {}})
        total = 0
        for target in annotation_counts:
            while total < target:
                page = total % doc.pageCount()
                start = (total // doc.pageCount() * 150) % max(1, len(texts[page]) - 200)
                bridge.controllers.highlights.create_highlight(
                    resource.id, texts[page][start:start + 120], "#22C55E", HighlightPosition(page, start, 120)
                )
                total += 1
            ms = best_ms(lambda: bridge.ctx.serializer.serialize(bridge.controllers.resources.get_resource(resource.id)))
            results["serialize"].append({"annotations": target, "ms": round(ms, 1)})
            add_repeats = 2
            ms_add = best_ms(
                lambda: bridge.annotations._save_highlight(resource.id, "x" * 20, "#22C55E", HighlightPosition(0, 10, 20)),
                repeat=add_repeats,
            )
            results["add_one"].append({"annotations": target, "ms": round(ms_add, 1)})
            total += add_repeats  # her tekrar bir alinti ekler

        data = pdf.read_bytes()
        start = time.perf_counter()
        _extract_pdf_html(data)
        elapsed = time.perf_counter() - start
        results["pypdf_ms_per_page"] = round(1000 * elapsed / results["pages"], 1)
    return results


def run_pdfkit(pages: int, annotation_counts: list[int], source_pdf: Path | None = None) -> list[dict]:
    """pdfkit yolu: kayitli geometriyle belge acma ve eski (geometrisiz) kayitlar icin ilk acilis maliyeti."""
    from PySide6.QtPdf import QPdfDocument
    from PySide6.QtWidgets import QApplication
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import pdfkit.infra.orm  # noqa: F401
    from models import Base, Resource
    from pdfkit.api import PdfLibrary
    from pdfkit.app.documents import DocumentService
    from pdfkit.app.importing import prepare_pdf
    from pdfkit.domain.annotations import Segment
    from pdfkit.infra.file_store import FileStore
    from pdfkit.ui.models import AnnotationListModel
    from pdfkit.ui.pdf_text import current_engine_fp
    from pdfkit.ui.session import GEOMETRY_CHUNK, DocumentSession

    class _NoCatalog:
        def create_pdf_resource(self, *args):
            return None

        def legacy_pdfs(self):
            return []

        def repoint(self, *args):
            return False

    results = []
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        root = Path(tmp)
        pdf = root / "bench.pdf"
        pdf.write_bytes(source_pdf.read_bytes() if source_pdf else build_pdf(pages))
        _app = QApplication.instance() or QApplication([])
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = sessionmaker(bind=engine)()
        store = FileStore(root / "pdfs")
        prepared = prepare_pdf(pdf, store)
        resource = Resource(title="Bench", url=store.absolute(prepared.stored.rel_path).as_uri())
        db.add(resource)
        db.commit()
        document = DocumentService(db, store).register(prepared, resource.id, "local")
        library = PdfLibrary(db, lambda: store.root, _NoCatalog(), lambda: None, lambda url: None)
        service = library.annotations()

        qdoc = QPdfDocument()
        qdoc.load(str(store.absolute(prepared.stored.rel_path)))
        texts = [qdoc.getSelectionAtIndex(p, 0, 1_000_000).text() for p in range(qdoc.pageCount())]
        fingerprint = current_engine_fp()

        def seed(count: int, with_geometry: bool) -> None:
            for i in range(count):
                page = i % qdoc.pageCount()
                start = (i // qdoc.pageCount() * 150) % max(1, len(texts[page]) - 200)
                selection = qdoc.getSelectionAtIndex(page, start, 120)
                polygons = [[(p.x(), p.y()) for p in poly] for poly in selection.bounds()] if with_geometry else None
                service.create_highlight(
                    document.id, texts[page][start:start + 120] or "x", [Segment(page, start, start + 120, texts[page][start:start + 120], polygons)],
                    "finding", engine_fp=fingerprint if with_geometry else None,
                )

        for count in annotation_counts:
            for existing in service.list_highlights(document.id):
                service.delete_highlight(existing.id)
            seed(count, with_geometry=True)
            session = DocumentSession(library, AnnotationListModel())
            open_ms = best_ms(lambda: (session.open(resource.id), session.close())[0], repeat=3)
            session.open(resource.id)
            page_ms = best_ms(lambda: [session.page_model(p).rowCount() for p in range(qdoc.pageCount())], repeat=1)
            session.close()

            for existing in service.list_highlights(document.id):
                service.delete_highlight(existing.id)
            seed(count, with_geometry=False)
            cold = DocumentSession(library, AnnotationListModel())
            cold.open(resource.id)
            slice_start = time.perf_counter()
            first = cold.ensure_geometry(0, limit=GEOMETRY_CHUNK)
            first_slice_ms = (time.perf_counter() - slice_start) * 1000
            start_time = time.perf_counter()
            computed = first + sum(cold.ensure_geometry(p) for p in range(qdoc.pageCount()))
            cold_ms = (time.perf_counter() - start_time) * 1000 + first_slice_ms
            cold.close()
            results.append(
                {"annotations": count, "open_ms": round(open_ms, 1), "page_models_ms": round(page_ms, 1),
                 "first_open_geometry_ms": round(cold_ms, 1), "first_slice_ms": round(first_slice_ms, 1), "computed": computed}
            )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pages", type=int, default=15)
    parser.add_argument("--annotations", default="25,100,300")
    parser.add_argument("--pdf", type=Path, help="Sentetik yerine bu PDF ile olc")
    parser.add_argument("--pdfkit", action="store_true", help="pdfkit yolunu da olc")
    parser.add_argument("--json", help="Sonucu bu dosyaya JSON olarak yaz")
    args = parser.parse_args()

    results = run(args.pages, [int(x) for x in args.annotations.split(",")], args.pdf)
    print(f"PDF ({results['source']}): {results['pages']} sayfa, {results['pdf_kb']} KB · QPdfDocument.load: {results['load_ms']} ms")
    print(f"pypdf tam metin: {results['pypdf_ms_per_page']} ms/sayfa")
    print(f"{'alinti':>8} {'serialize ms':>14} {'tek ekleme ms':>15}")
    for ser, add in zip(results["serialize"], results["add_one"]):
        print(f"{ser['annotations']:>8} {ser['ms']:>14} {add['ms']:>15}")
    if args.pdfkit:
        pdfkit_results = run_pdfkit(args.pages, [int(x) for x in args.annotations.split(",")], args.pdf)
        results["pdfkit"] = pdfkit_results
        print(f"{'pdfkit':>8} {'acilis ms':>12} {'sayfa modelleri ms':>20} {'ilk acilis toplam ms':>22} {'ilk dilim ms':>14}")
        for item in pdfkit_results:
            print(
                f"{item['annotations']:>8} {item['open_ms']:>12} {item['page_models_ms']:>20} "
                f"{item['first_open_geometry_ms']:>22} {item['first_slice_ms']:>14}"
            )
    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
