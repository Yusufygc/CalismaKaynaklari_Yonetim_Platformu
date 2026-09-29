from datetime import datetime, timezone, tzinfo

DATE_TIME_FORMAT = "%d.%m.%Y %H:%M"
DATE_FORMAT = "%d.%m.%Y"


def format_local_datetime(dt: datetime | None, fmt: str = DATE_TIME_FORMAT, tz: tzinfo | None = None) -> str:
    """Veritabanindaki (UTC, saat dilimsiz) zamani kullanicinin yerel saatiyle bicimler.

    `created_at` alanlari `func.now()` ile UTC yazilir ve SQLite saat dilimini saklamaz;
    dogrudan `strftime` yerel saat sanilip 3 saat geri gosteriliyordu (Turkiye). `tz`
    verilmezse isletim sisteminin yerel saat dilimi kullanilir (testlerde sabit tz verilir).
    """
    if dt is None:
        return ""
    aware = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    return aware.astimezone(tz).strftime(fmt)
