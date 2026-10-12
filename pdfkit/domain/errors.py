class PdfkitError(Exception):
    """pdfkit'in tum beklenen hatalarinin tabani."""


class NotAPdfError(PdfkitError):
    """Dosya acilamadi, bozuk, sifreli ya da PDF degil."""


class DownloadError(PdfkitError):
    """Uzak PDF indirilemedi (ag hatasi, reddedilen adres, PDF olmayan icerik)."""


class TooLargeError(DownloadError):
    """Uzak PDF izin verilen boyutu asti."""
