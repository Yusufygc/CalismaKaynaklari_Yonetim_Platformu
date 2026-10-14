"""FTS5 sanal tablosunun semasi. Alembic migration'i ve testler/calisma zamani guvencesi ayni tanimi kullanir."""
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

FTS_TABLE = "pdf_page_fts"

# `folded`: dizinli, katlanmis metin. `original`: dizinsiz, gosterim icin ozgun metin. Belge ve sayfa ayri sutun
# DEGILDIR, satir kimliginden (rowid = belge * ROWID_SPAN + sayfa) turetilir: belgeyi silmek dizinsiz sutunu taramak
# yerine rowid araligi silmektir.
ROWID_SPAN = 10_000  # belge basina en cok bu kadar sayfa (dizin ust siniri bunun altindadir)
_CREATE = (
    f"CREATE VIRTUAL TABLE IF NOT EXISTS {FTS_TABLE} USING fts5("
    "folded, original UNINDEXED, tokenize='unicode61 remove_diacritics 2')"
)


def create_fts_table(connection: Connection | Session) -> bool:
    """Tabloyu olusturur (varsa dokunmaz). SQLite'ta FTS5 yoksa False doner (hata firlatmaz)."""
    try:
        connection.execute(text(_CREATE))
    except OperationalError:
        return False
    return True


def include_object(obj, name, type_, reflected, compare_to) -> bool:
    """Alembic `include_object` suzgeci: FTS5 sanal tablosu ve SQLite'in urettigi golge tablolari (`pdf_page_fts_data`,
    `_idx`, `_content`, `_docsize`, `_config`) ORM metadata'sinda yoktur; otomatik karsilastirma bunlari silmeyi onermesin."""
    return not (type_ == "table" and (name == FTS_TABLE or name.startswith(FTS_TABLE + "_")))
