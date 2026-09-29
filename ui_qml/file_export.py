from pathlib import Path

from PySide6.QtCore import QUrl

from core.constants.strings import AppStrings
from core.logger import log
from ui_qml.notifier import Notifier


def write_export(
    file_url: str, content: str, notifier: Notifier, suffix: str = ".md", encoding: str = "utf-8"
) -> None:
    """Disa aktarim iceriğini kullanicinin sectigi dosyaya yazar (uzanti yoksa/yanlissa `suffix` eklenir)
    ve sonucu bildirir. Reader (Markdown) ve Market (BibTeX/CSV) ortak kullanir."""
    path = Path(QUrl(file_url).toLocalFile() or file_url)
    if path.suffix.lower() != suffix:
        path = path.with_suffix(path.suffix + suffix) if path.suffix else path.with_suffix(suffix)
    try:
        with path.open("w", encoding=encoding, newline="") as handle:
            handle.write(content)
    except OSError as exc:
        log.warning("Disa aktarim yazilamadi: %s - %s", path, exc)
        notifier.error(AppStrings.NOTIFICATION_EXPORT_FAILED)
        return
    notifier.info(AppStrings.NOTIFICATION_EXPORT_DONE_FMT.format(name=path.name))
