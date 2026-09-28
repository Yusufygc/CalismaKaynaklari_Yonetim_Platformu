from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname


def format_display_url(url: str) -> str:
    """URL'yi kisa/okunur bir bicime cevirir: sema, 'www.' ve yol/sorgu atilir.

    Detay panelindeki URL butonunun uzun ham linki degil, sadece alan adini
    (ornegin 'github.com') gostermesi icin kullanilir; tam URL tooltip'te
    ve tiklandiginda acilan tarayicida korunur.

    `file://` URI'leri (yerel PDF ice aktarimlari) icin hostname yok --
    onun yerine dosya adi gosterilir.
    """
    parsed = urlparse(url)
    if parsed.scheme == "file":
        return Path(url2pathname(unquote(parsed.path))).name

    host = (parsed.hostname or url).lower()
    if host.startswith("www."):
        host = host[4:]
    return host
