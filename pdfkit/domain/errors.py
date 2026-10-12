class PdfkitError(Exception):
    """pdfkit'in tum beklenen hatalarinin tabani."""


class NotAPdfError(PdfkitError):
    """Dosya acilamadi, bozuk, sifreli ya da PDF degil."""


class DownloadError(PdfkitError):
    """Uzak PDF indirilemedi (ag hatasi, reddedilen adres, PDF olmayan icerik)."""


class TooLargeError(DownloadError):
    """Uzak PDF izin verilen boyutu asti."""


class InvalidAnnotationError(PdfkitError):
    """Alinti/not/kelime verisi gecersiz (bos metin, bilinmeyen etiket, parcasiz alinti ...)."""


class NotFoundError(PdfkitError):
    """Istenen belge, alinti, not ya da kelime bulunamadi."""


class InvalidLinkError(PdfkitError):
    """`pkm://` derin baglantisi gecersiz, desteklenmiyor ya da cok uzun."""


class VaultNoteError(PdfkitError):
    """Vault notu uretilemedi ya da mevcut dosyayla guvenle birlestirilemedi (ornegin bozuk sentinel)."""


class VaultUnavailableError(PdfkitError):
    """Vault klasoru yok, klasor degil ya da yazilamiyor; ya da not yolu vault disina cikiyor."""


class VaultConflictError(PdfkitError):
    """Not dosyasi yazim sirasinda surekli degisti (Obsidian/baska arac); veri kaybetmemek icin yazilmadi."""
