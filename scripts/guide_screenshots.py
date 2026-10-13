"""Kullanım Kılavuzu için ekran görüntüleri üretir: `assets/guide/*.png`.

Gerçek uygulama arayüzünü (qml/main.qml) bellek içi bir veritabanında, uydurma örnek verilerle açar ve pencereyi PNG'ye
kaydeder. Kullanıcının gerçek veritabanına, ayarlarına ya da PDF deposuna DOKUNMAZ: her şey geçici bir klasördedir.
Yalnızca geliştirme içindir (test yardımcılarını ve `pypdf` dev bağımlılığını kullanmaz ama `tests/` içe aktarılır).

Çalıştırma (proje kökünden):
    .venv\\Scripts\\python.exe scripts/guide_screenshots.py            # tüm ekranlar
    .venv\\Scripts\\python.exe scripts/guide_screenshots.py kutuphane  # yalnız adı eşleşenler

Arayüz değişince kılavuzdaki görseller bu betikle yeniden üretilir.
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
if sys.platform == "win32" and os.environ.get("GUIDE_OFFSCREEN") != "1":
    # Gerçek Windows eklentisi: sistem yazı tipleri doğru adlarla görünür (Sitka Heading, Segoe UI Variable...), görüntü
    # uygulamanın gerçek hâline çok yakın olur. Pencereler kısa süre görünür; ölçek 1:1 (görüntü 1280x800).
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "0")
else:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if sys.platform == "win32":  # offscreen eklentisi sistem yazı tiplerini görmez: yazı tipi klasörü verilir
        os.environ.setdefault("QT_QPA_FONTDIR", str(Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"))

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QMarginsF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QFont, QPageSize, QPainter, QPdfWriter  # noqa: E402
from PySide6.QtPdf import QPdfDocument  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

OUTPUT = ROOT / "assets" / "guide"
WIDTH, HEIGHT = 1280, 800

# Her örnek kaynağın kategorisi, durumu ve etiketleri (vitrin ekran görüntüsü çeşitli görünsün)
DEMO_META = {
    "Derin Öğrenme ile Görüntü Tanıma": ("Yapay Zeka", "IN_PROGRESS", ["görüntü", "okuma-listesi"]),
    "Kuantum Bilgisayarlara Giriş": ("Fizik", "PLANNED", ["kuantum"]),
    "Eğitimde Motivasyonun Rolü": ("Eğitim", "COMPLETED", ["motivasyon"]),
    "Makine Öğrenmesi Rehberi": ("Yapay Zeka", "INBOX", ["rehber"]),
    "Python ile Veri Analizi": ("Yapay Zeka", "PLANNED", ["python"]),
}

DEMO_PDFS = {
    "Derin Öğrenme ile Görüntü Tanıma": {
        "authors": ["Ayşe Yılmaz", "Mehmet Demir"],
        "year": 2021,
        "pages": [
            [
                "Derin Öğrenme ile Görüntü Tanıma",
                "Bu çalışmada evrişimli sinir ağlarının görüntü sınıflandırmadaki başarısı incelenmiştir. "
                "Derin öğrenme yöntemleri, geleneksel yaklaşımlara göre belirgin biçimde daha yüksek doğruluk sağlamaktadır.",
                "Yöntem olarak on bin etiketli görüntüden oluşan bir veri kümesi kullanılmış, model geri yayılım ile eğitilmiştir. "
                "Eğitim sırasında veri artırma teknikleri uygulanmıştır.",
                "Bulgular, önerilen modelin doğruluk oranının yüzde doksan ikiye ulaştığını göstermektedir. "
                "Ancak küçük veri kümelerinde aşırı öğrenme riski devam etmektedir.",
            ],
            [
                "Tartışma",
                "Elde edilen sonuçlar, öğrenme oranının dikkatle seçilmesi gerektiğini ortaya koymaktadır. "
                "Çalışmanın en önemli sınırlılığı, yalnızca tek bir veri kümesi üzerinde denenmiş olmasıdır.",
            ],
        ],
        "highlights": [
            ("Derin öğrenme yöntemleri", "important", ["hipotez"], 0),
            ("geri yayılım", "method", ["ortak"], 0),
            ("yüzde doksan ikiye", "finding", ["hipotez"], 0),
            ("aşırı öğrenme", "critique", [], 0),
            ("tek bir veri kümesi", "critique", ["sınırlılık"], 1),
        ],
    },
    "Kuantum Bilgisayarlara Giriş": {
        "authors": ["Can Özkan"],
        "year": 2019,
        "pages": [
            [
                "Kuantum Bilgisayarlara Giriş",
                "Kuantum bilgisayarlar, bilgiyi kübit adı verilen birimlerle işler. Bir kübit aynı anda birden fazla durumda "
                "bulunabilir; bu özellik üst üste binme olarak adlandırılır.",
                "Kuantum üstünlüğü, belirli problemlerin klasik bilgisayarlardan çok daha hızlı çözülmesi anlamına gelir. "
                "Yöntem olarak kuantum devreleri ve kapı modeli kullanılmaktadır.",
            ],
        ],
        "highlights": [
            ("üst üste binme", "concept", [], 0),
            ("Kuantum üstünlüğü", "important", ["ortak"], 0),
            ("kuantum devreleri", "method", [], 0),
        ],
    },
    "Eğitimde Motivasyonun Rolü": {
        "authors": ["Elif Kaya"],
        "year": 2022,
        "pages": [
            [
                "Eğitimde Motivasyonun Rolü",
                "Çocukların öğrenme şekli, motivasyon düzeyleriyle yakından ilişkilidir. İçsel motivasyonu yüksek öğrenciler "
                "daha kalıcı öğrenme göstermektedir.",
                "Araştırma, yarı deneysel desenle yürütülmüş ve kırk sekiz öğrenci ile yapılmıştır.",
            ],
        ],
        "highlights": [
            ("motivasyonu yüksek", "finding", ["hipotez"], 0),
            ("yarı deneysel desenle", "method", [], 0),
        ],
    },
}


def write_demo_pdf(path: Path, pages: list[list[str]]) -> Path:
    """Gerçek yazı tipiyle (Türkçe karakterler dahil) seçilebilir metinli A4 PDF."""
    writer = QPdfWriter(str(path))
    writer.setPageSize(QPageSize(QPageSize.A4))
    writer.setResolution(72)  # 1 birim = 1 nokta
    writer.setPageMargins(QMarginsF(0, 0, 0, 0))
    painter = QPainter(writer)
    for index, lines in enumerate(pages):
        if index:
            writer.newPage()
        y = 72.0
        for number, line in enumerate(lines):
            font = QFont("Segoe UI", 20 if number == 0 else 12)
            font.setBold(number == 0)
            painter.setFont(font)
            rect = QRectF(72, y, 451, 600)
            bounds = painter.boundingRect(rect, int(Qt.TextWordWrap), line)
            painter.drawText(rect, int(Qt.TextWordWrap), line)
            y += bounds.height() + (18 if number == 0 else 14)
    painter.end()
    return path


def selection_of(reader: QPdfDocument, phrase: str, page: int = 0) -> dict:
    """QML'in göndereceği seçim haritası (testlerdeki `selection_of` ile aynı)."""
    text = reader.getSelectionAtIndex(page, 0, 1_000_000).text()
    if phrase not in text:
        raise ValueError(f"Seçilecek ifade PDF metninde yok: {phrase!r} (PDF metni: {text[:400]!r})")
    start = text.index(phrase)
    rect = reader.getSelectionAtIndex(page, start, len(phrase)).boundingRectangle()
    y = rect.y() + rect.height() / 2
    return {"page": page, "fromX": rect.x() + 1, "fromY": y, "toX": rect.x() + rect.width() + 4, "toY": y}  # +4: son harf seçimin dışında kalmasın


class Guide:
    def __init__(self, workdir: Path) -> None:
        from core.user_settings import UserSettings
        from tests.test_qml.qml_harness import SyncThreadPool
        from ui_qml import context as context_module
        from ui_qml import pdf_files
        from ui_qml.bridge import QmlBridge
        from utils.db_utils import register_sqlite_functions

        import models  # noqa: F401
        import pdfkit.infra.orm  # noqa: F401
        from models import Base

        self.workdir = workdir
        storage = workdir / "depo"
        storage.mkdir()
        pdf_files.pdf_storage_dir = lambda: storage  # gerçek PDF deposuna dokunma
        settings_file = workdir / "user_settings.json"
        context_module.default_settings_path = lambda: settings_file  # gerçek kullanıcı ayarlarına dokunma
        UserSettings  # noqa: B018  (içe aktarma ayar sınıfının varlığını doğrular)
        engine = create_engine("sqlite:///:memory:")
        register_sqlite_functions(engine)
        Base.metadata.create_all(engine)
        self.session = sessionmaker(bind=engine, autoflush=False)()
        self.bridge = QmlBridge(self.session)
        self.bridge.ctx.thread_pool = SyncThreadPool()
        self.bridge.ctx.extractor.schedule = lambda *args: None  # tam metin çıkarımı (web sayfaları) gerekmez
        self.app = QApplication.instance()
        self.resources: dict[str, object] = {}
        # Gerçek kayıt defterine DOKUNMA: pkm:// kartı görünsün ama "kayıtlı değil" gösterilsin (hiçbir yazma çağrılmaz).
        from core.protocol_registration import ProtocolRegistration

        ProtocolRegistration.supported = property(lambda self: True)
        ProtocolRegistration.is_registered = lambda self: False

    # ---------------------------------------------------------------- veri

    def seed(self) -> None:
        from tests.test_qml.qml_harness import pump

        bridge, controllers = self.bridge, self.bridge.controllers
        bridge.settings.createCategory("Yapay Zeka", "#6366F1", "")
        bridge.settings.createCategory("Fizik", "#06B6D4", "")
        bridge.settings.createCategory("Eğitim", "#22C55E", "")
        for title, spec in DEMO_PDFS.items():
            path = write_demo_pdf(self.workdir / f"{title}.pdf", spec["pages"])
            bridge.library.importLocalPdf(path.as_uri())
            pump(self.app, 6)
        for resource in controllers.resources.load_resources_with_filters({}):
            title = next((t for t in DEMO_PDFS if t in (resource.url or "") or t in (resource.title or "")), None)
            if title is None:
                continue
            spec = DEMO_PDFS[title]
            controllers.resources.update_resource(
                resource.id,
                {"title": title, "extra_metadata": {**(resource.extra_metadata or {}), "authors": spec["authors"], "year": spec["year"]}},
            )
            self.resources[title] = resource
        for title, saved in (("Makine Öğrenmesi Rehberi", "https://example.org/makine-ogrenmesi"), ("Python ile Veri Analizi", "https://example.org/python-veri")):
            bridge.market.saveMarketResult({"title": title, "url": saved})
        pump(self.app, 10)
        self._classify()
        self._wait_for_index()
        self._annotate()

    def _classify(self) -> None:
        """Kategori, durum ve etiketleri atar."""
        from models import ResourceStatus

        categories = {c["name"]: c["id"] for c in self.bridge.settings.categories}
        for resource in self.bridge.controllers.resources.load_resources_with_filters({}):
            meta = DEMO_META.get(resource.title)
            if meta is None:
                continue
            category, status, tags = meta
            self.bridge.controllers.resources.update_resource(
                resource.id, {"category_id": categories.get(category), "status": ResourceStatus[status], "tag_names": tags}
            )

    def _wait_for_index(self) -> None:
        waited = 0
        while self.bridge.ctx.text_indexer.status()["pending"] and waited < 20000:
            QTest.qWait(50)
            waited += 50
        QTest.qWait(100)

    def _annotate(self) -> None:
        bridge = self.bridge
        for title, spec in DEMO_PDFS.items():
            resource = self.resources[title]
            bridge.pdf.openDocument(resource.id)
            reader = QPdfDocument()
            document = bridge.ctx.pdf_library.documents().document_for_resource(resource.id)
            reader.load(str(bridge.ctx.pdf_library.file_path(document)))
            for phrase, label, tags, page in spec["highlights"]:
                annotation_id = bridge.pdf.addHighlight(selection_of(reader, phrase, page), label)
                if tags and annotation_id:
                    bridge.ctx.pdf_library.annotations().set_tags(annotation_id, tags)
            reader.close()
            bridge.pdf.closeDocument()
        QTest.qWait(400)

    # ---------------------------------------------------------------- görüntü

    def window(self, view: str):
        from tests.test_qml.qml_harness import open_window

        engine, window = open_window(self.app, self.bridge, view, width=WIDTH, height=HEIGHT)
        self._engine = engine
        return window

    def shot(self, window, name: str) -> Path:
        from tests.test_qml.qml_harness import pump

        pump(self.app, 25)
        OUTPUT.mkdir(parents=True, exist_ok=True)
        target = OUTPUT / f"{name}.png"
        image = window.grabWindow()
        image.save(str(target))
        shown = target.relative_to(ROOT) if target.is_relative_to(ROOT) else target
        print(f"{shown}  {image.width()}x{image.height()}")
        return target


def scene_kutuphane(guide: Guide):
    window = guide.window("showcase")
    guide.shot(window, "kutuphane")


def scene_okuyucu(guide: Guide):
    from tests.test_qml.qml_harness import click, find_item, pump

    resource = guide.resources["Derin Öğrenme ile Görüntü Tanıma"]
    guide.bridge.reader.openReader(resource.id)
    window = guide.window("pdfReader")
    pump(guide.app, 120)
    reader = find_item(window, lambda i: i.property("sidePanelOpen") is not None)
    if reader is not None:
        reader.setProperty("sidePanelOpen", True)
    pump(guide.app, 20)
    notes_tab = find_item(window, lambda i: i.property("text") == "Notlarım")
    if notes_tab is not None:
        click(guide.app, window, notes_tab)
    QTest.qWait(500)
    guide.shot(window, "okuyucu")


def _knowledge(guide: Guide):
    return guide.window("knowledge")


def scene_alintilar(guide: Guide):
    window = _knowledge(guide)
    guide.shot(window, "bilgi-havuzu")


def scene_arama(guide: Guide):
    from tests.test_qml.qml_harness import click, find_item, find_named, pump

    window = _knowledge(guide)
    click(guide.app, window, find_named(window, "contentSearchTab"))
    pump(guide.app, 10)
    bar = find_item(window, lambda i: i.property("placeholder") == "PDF'lerin içinde ara...")
    bar.setProperty("text", "öğrenme")
    QTest.qWait(600)
    guide.shot(window, "metinde-ara")


def scene_matris(guide: Guide):
    from tests.test_qml.qml_harness import click, find_named, pump

    window = _knowledge(guide)
    click(guide.app, window, find_named(window, "matrixTab"))
    pump(guide.app, 40)
    guide.shot(window, "matris")


def _settings(guide: Guide, tab_name: str, name: str):
    from tests.test_qml.qml_harness import click, find_named, pump

    window = guide.window("settings")
    click(guide.app, window, find_named(window, tab_name))
    pump(guide.app, 20)
    guide.shot(window, name)


def scene_obsidian(guide: Guide):
    vault = guide.workdir / "Obsidian Kasam"
    (vault / ".obsidian").mkdir(parents=True, exist_ok=True)
    guide.bridge.vault.chooseVault(str(vault))
    QTest.qWait(200)
    sync = guide.bridge.ctx.vault_sync  # geçici klasör yolu (kullanıcı adı içerir) görüntüde görünmesin
    real_status = sync.status
    sync.status = lambda: {**real_status(), "path": "C:\\Kullanıcılar\\Ayşe\\Belgelerim\\Obsidian Kasam"}
    sync.statusChanged.emit()
    _settings(guide, "vaultTab", "ayarlar-obsidian")


def scene_kunye(guide: Guide):
    _settings(guide, "metadataTab", "ayarlar-kunye")


def scene_matris_ayar(guide: Guide):
    _settings(guide, "matrixSettingsTab", "ayarlar-matris")


def scene_gorunum(guide: Guide):
    _settings(guide, "appearanceTab", "ayarlar-gorunum")


def scene_market(guide: Guide):
    window = guide.window("articleMarket")
    guide.shot(window, "makale-market")


SCENES = [
    ("kutuphane", scene_kutuphane),
    ("okuyucu", scene_okuyucu),
    ("alintilar", scene_alintilar),
    ("arama", scene_arama),
    ("matris", scene_matris),
    ("obsidian", scene_obsidian),
    ("kunye", scene_kunye),
    ("matris-ayar", scene_matris_ayar),
    ("gorunum", scene_gorunum),
    ("market", scene_market),
]


def main(argv: list[str]) -> int:
    app = QApplication.instance() or QApplication(["guide"])
    from core.fonts import register_bundled_fonts

    register_bundled_fonts()  # uygulamayla gelen yazi tipleri (yazi tipi cifti ornekleri dogru gorunsun)
    app.setFont(QFont("Segoe UI", 9))
    # Theme.fontFamily ("Inter, Segoe UI, sans-serif") tek bir ad olarak aranır; offscreen eklentisinde bulunamayınca dar
    # bir yazı tipine düşerdi. Gerçek (windows) eklentisinde görünen Segoe UI'ya eşlenir.
    QFont.insertSubstitution("Inter, Segoe UI, sans-serif", "Segoe UI")
    wanted = set(argv)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        guide = Guide(Path(tmp))
        guide.bridge.toggleTheme()  # açık tema: basılı kılavuz gibi okunur
        guide.seed()
        for name, scene in SCENES:
            if wanted and name not in wanted:
                continue
            scene(guide)
        guide.session.close()
    del app
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
