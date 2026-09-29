WORDS_PER_MINUTE = 200


def estimate_reading_minutes(text: str | None) -> int:
    """Tahmini okuma suresi (dakika, en az 1); metin yoksa 0. Tek kaynak: model sutunu
    `resources.reading_minutes` yazilirken hesaplanir (bkz. services/resource_service.py)."""
    words = len((text or "").split())
    return max(1, round(words / WORDS_PER_MINUTE)) if words else 0
