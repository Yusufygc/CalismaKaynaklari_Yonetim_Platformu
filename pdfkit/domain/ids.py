import os
import time

_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford base32


def new_uid() -> str:
    """ULID: 48 bit milisaniye zaman damgasi + 80 bit rastgelelik, 26 karakter, zamana gore siralanabilir.
    Alinti, not ve kelimeler icin kararli kimlik (Obsidian blok kimligi ve derin baglanti bunu kullanir)."""
    value = (int(time.time() * 1000) << 80) | int.from_bytes(os.urandom(10), "big")
    chars = []
    for _ in range(26):
        chars.append(_ALPHABET[value & 31])
        value >>= 5
    return "".join(reversed(chars))
