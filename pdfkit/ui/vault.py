from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QThreadPool, QTimer, Signal

from core.logger import log
from pdfkit.domain.errors import PdfkitError
from pdfkit.domain.vault_note import NoteContent
from pdfkit.domain.vault_summary import (
    IndexContent,
    IndexEntry,
    MatrixContent,
    SummaryContent,
    VocabularyContent,
    VocabularySection,
    index_entry_for,
    matrix_row_for,
    vocabulary_section_for,
)
from pdfkit.domain.synthesis import MatrixOptions, MatrixRow
from pdfkit.infra.vault_writer import VaultWriter, WriteOutcome
from pdfkit.ui.library import PdfLibrary
from pdfkit.ui.workers import CallWorker, submit

DEBOUNCE_MS = 1500
_BUILD_CHUNK = 5  # her olay dongusu turunda hazirlanan belge sayisi (UI donmasin)

STATE_DISABLED = "disabled"
STATE_IDLE = "idle"
STATE_PENDING = "pending"
STATE_SYNCING = "syncing"
STATE_ERROR = "error"


@dataclass
class SyncReport:
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    failed: list[tuple[str, str]] = field(default_factory=list)  # (citekey ya da ozet dosyasi, mesaj)
    summaries_written: int = 0  # dizin / kelime defteri notlarindan yazilan (belge notlarindan ayri sayilir)

    @property
    def written(self) -> int:
        return self.created + self.updated


def write_batch(writer: VaultWriter, contents: list[NoteContent], summaries: list[SummaryContent] | None = None) -> SyncReport:
    """Notlari sirayla yazar (worker thread'inde). Tek notun hatasi digerlerini durdurmaz."""
    report = SyncReport()
    for summary in summaries or []:
        try:
            if writer.write_summary(summary) is not WriteOutcome.UNCHANGED:
                report.summaries_written += 1
        except (PdfkitError, OSError) as exc:
            log.warning("Vault ozet notu yazilamadi (%s): %s", summary.filename, exc)
            report.failed.append((summary.filename, str(exc)))
    for content in contents:
        try:
            outcome = writer.write(content)
        except (PdfkitError, OSError) as exc:
            log.warning("Vault notu yazilamadi (%s): %s", content.citekey, exc)
            report.failed.append((content.citekey, str(exc)))
            continue
        if outcome is WriteOutcome.CREATED:
            report.created += 1
        elif outcome is WriteOutcome.UPDATED:
            report.updated += 1
        else:
            report.unchanged += 1
    return report


class VaultSync(QObject):
    """Belgelerin vault notlarini arka planda esitler (K11): degisen belgeler isaretlenir, 1,5 sn birlestirilir;
    veritabani okumalari (kisa, dilimli) ana thread'de, dosya yazimi worker'da yapilir. Vault klasoru ayarli degilse
    hicbir sey yapmaz. Kullanicinin notlari asla silinmez (kaynak/belge silinse de dosya kalir)."""

    statusChanged = Signal()
    syncFinished = Signal(object)  # SyncReport

    def __init__(
        self,
        library: PdfLibrary,
        thread_pool: Callable[[], QThreadPool],
        debounce_ms: int = DEBOUNCE_MS,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._library = library
        self._thread_pool = thread_pool
        self._writer: VaultWriter | None = None
        self._dirty: set[int] = set()
        self._queue: deque[int] = deque()
        self._contents: list[NoteContent] = []
        self._full_requested = False  # `sync_all`: dizin/kelime defteri tum belgelerden yeniden kurulur
        self._full_pass = False  # calisan esitleme tam mi?
        self._cache: dict[int, tuple[IndexEntry, VocabularySection, MatrixRow]] = {}  # belge -> dizin/kelime/matris parcalari
        self._cache_complete = False  # onbellek tum belgeleri kapsiyor mu? (degilse ozet notlari yazilmaz)
        self._matrix_options = MatrixOptions()  # `_Matris.md` sutun/sira/hucre siniri (kullanici ayari)
        self._resummarize = False  # calisan yazim bitince ozet notlari yeniden yazilsin (ayar degisti)
        self._running = False
        self._state = STATE_DISABLED
        self._message = ""
        self._last_sync = ""
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(debounce_ms)
        self._timer.timeout.connect(self._flush)

    # ------------------------------------------------------------------ #
    # Ayar
    # ------------------------------------------------------------------ #

    @property
    def root(self) -> Path | None:
        return self._writer.root if self._writer else None

    def set_root(self, path: Path | None) -> None:
        """Vault klasorunu ayarlar (None: kapat). Klasor kullanilamazsa `VaultUnavailableError` firlatir ve onceki
        ayar korunur."""
        if path is None:
            self._writer = None
            self._dirty.clear()
            self._cache.clear()
            self._cache_complete = False
            self._full_requested = False
            self._timer.stop()
            self._set_status(STATE_DISABLED, "")
            return
        writer = VaultWriter(path)
        writer.check()
        self._writer = writer
        self._set_status(STATE_IDLE, "")

    def set_matrix_options(self, options: MatrixOptions) -> None:
        """`_Matris.md` ayarlarini degistirir; vault acik ve onbellek tamsa ozet notlari (yalniz degisen dosya yazilir)
        hemen yeniden uretilir, degilse sonraki tam esitlemede uygulanir."""
        if options == self._matrix_options:
            return
        self._matrix_options = options
        if self._writer is not None and self._cache_complete:
            self._rewrite_summaries()

    def _rewrite_summaries(self) -> None:
        if self._running:
            self._resummarize = True
            return
        writer, summaries = self._writer, self._summaries()
        if writer is None or not summaries:
            return
        self._running = True
        self._set_status(STATE_SYNCING, "")
        submit(self._thread_pool(), CallWorker(lambda: write_batch(writer, [], summaries), self._on_written), self._dispatch)

    def status(self) -> dict:
        return {
            "enabled": self._writer is not None,
            "path": str(self._writer.root) if self._writer else "",
            "state": self._state,
            "message": self._message,
            "lastSync": self._last_sync,
        }

    # ------------------------------------------------------------------ #
    # Isaretleme
    # ------------------------------------------------------------------ #

    def mark_resource(self, resource_id: int) -> None:
        """Kaynagin PDF belgesi varsa esitleme kuyruguna alir (HTML makaleler vault'a yazilmaz)."""
        if self._writer is None:
            return
        document_id = self._library.note_builder().document_id_for_resource(resource_id)
        if document_id is not None:
            self._mark(document_id)

    def sync_all(self) -> None:
        """Tum PDF belgelerinin notlarini yeniden uretir (degismeyenlere dokunulmaz)."""
        if self._writer is None:
            return
        for document_id in self._library.note_builder().linked_document_ids():
            self._dirty.add(document_id)
        self._full_requested = True
        self._timer.stop()
        self._flush()

    def _mark(self, document_id: int) -> None:
        self._dirty.add(document_id)
        if not self._running:
            self._set_status(STATE_PENDING, self._message)
        if not self._timer.isActive():
            self._timer.start()

    # ------------------------------------------------------------------ #
    # Esitleme
    # ------------------------------------------------------------------ #

    def _flush(self) -> None:
        if self._writer is None or not self._dirty:
            return
        if self._running:  # sonuc gelince bekleyenler yeniden denenir (`_on_written`)
            return
        self._running = True
        self._queue = deque(sorted(self._dirty))
        self._dirty.clear()
        self._contents = []
        self._full_pass, self._full_requested = self._full_requested, False
        if self._full_pass:
            self._cache.clear()
        self._set_status(STATE_SYNCING, "")
        self._build_next()

    def _build_next(self) -> None:
        builder = self._library.note_builder()
        for _ in range(_BUILD_CHUNK):
            if not self._queue:
                break
            document_id = self._queue.popleft()
            try:
                content = builder.build(document_id)
            except Exception:
                log.exception("Vault notu hazirlanamadi")
                continue
            if content is None:
                self._cache.pop(document_id, None)  # bagli kaynagi kalmadi: dizinden dusur (not dosyasi silinmez)
                continue
            self._contents.append(content)
            self._cache[document_id] = (index_entry_for(content), vocabulary_section_for(content), matrix_row_for(content))
        if self._queue:
            QTimer.singleShot(0, self._build_next)
            return
        writer, contents, summaries = self._writer, self._contents, self._summaries()
        self._contents = []
        if writer is None or not (contents or summaries):
            self._on_written(SyncReport(), None)
            return
        submit(
            self._thread_pool(),
            CallWorker(lambda: write_batch(writer, contents, summaries), self._on_written),
            self._dispatch,
        )

    def _summaries(self) -> list[SummaryContent]:
        """Dizin ve kelime defteri notlari. Onbellek tum belgeleri kapsamadan yazilmaz: eksik bir dizin, vault'taki
        dogru dizini bozardi. Tam bir esitleme (`sync_all`) onbellegi bastan kurar; sonrasinda degisen belgeler
        onbellegi gunceller."""
        if self._full_pass:
            self._cache_complete = True
        if not self._cache_complete:
            return []
        parts = [self._cache[document_id] for document_id in sorted(self._cache)]
        return [
            IndexContent([entry for entry, _section, _row in parts]),
            VocabularyContent([section for _entry, section, _row in parts]),
            MatrixContent([row for _entry, _section, row in parts], self._matrix_options),
        ]

    def _dispatch(self, callback, result, error) -> None:
        callback(result, error)

    def _on_written(self, report: SyncReport | None, error: Exception | None) -> None:
        self._running = False
        if error is not None or report is None:
            report = SyncReport(failed=[("", str(error) if error else "bilinmeyen hata")])
        self._last_sync = datetime.now().strftime("%d.%m.%Y %H:%M")
        if report.failed:
            self._set_status(STATE_ERROR, f"{len(report.failed)} not yazılamadı: {report.failed[0][1]}")
        else:
            self._set_status(STATE_IDLE, f"{report.written} not yazıldı, {report.unchanged} değişmedi")
        self.syncFinished.emit(report)
        if self._resummarize:
            self._resummarize = False
            self._rewrite_summaries()
        if self._dirty and self._writer is not None:
            self._timer.start()

    def _set_status(self, state: str, message: str) -> None:
        self._state, self._message = state, message
        self.statusChanged.emit()
