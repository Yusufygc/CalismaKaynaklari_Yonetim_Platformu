def sanitize_text(text: str | None) -> str:
    """Tek basina UTF-16 surrogate kod noktalarini '?' ile degistirir.

    Bozuk CMap'li subset fontlar bunlari uretebiliyor; gecerli UTF-8 olmadiklari icin SQLite'a yazilirken
    `UnicodeEncodeError` firlatirlar. Her surrogate tek karakterle degistirildigi icin metin indeksleri KAYMAZ."""
    return (text or "").encode("utf-8", errors="replace").decode("utf-8")
