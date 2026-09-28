from urllib.parse import urlparse


def format_display_url(url: str) -> str:
    """URL'yi kisa/okunur bir bicime cevirir: sema, 'www.' ve yol/sorgu atilir.

    Detay panelindeki URL butonunun uzun ham linki degil, sadece alan adini
    (ornegin 'github.com') gostermesi icin kullanilir; tam URL tooltip'te
    ve tiklandiginda acilan tarayicida korunur.
    """
    host = (urlparse(url).hostname or url).lower()
    if host.startswith("www."):
        host = host[4:]
    return host
