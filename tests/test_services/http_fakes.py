"""`requests` yanitlarini taklit eden ortak test siniflari."""


class FakeResponse:
    is_redirect = False

    def __init__(self, text: str = "", content: bytes = b"", url: str = "https://example.com/page") -> None:
        self.text = text
        self.content = content if content else text.encode("utf-8")
        self.url = url
        self.headers: dict = {}

    def raise_for_status(self) -> None:
        return None


class FakeRedirectResponse:
    is_redirect = True

    def __init__(self, location: str) -> None:
        self.headers = {"Location": location}

    def raise_for_status(self) -> None:
        return None
