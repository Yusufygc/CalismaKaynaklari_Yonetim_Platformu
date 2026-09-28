from datetime import datetime


def format_date(dt: datetime | None, fmt: str = "%d.%m.%Y") -> str:
    if dt is None:
        return ""
    return dt.strftime(fmt)
