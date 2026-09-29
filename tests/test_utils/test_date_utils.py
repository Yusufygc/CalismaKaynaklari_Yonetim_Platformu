from datetime import datetime, timedelta, timezone

from utils.date_utils import DATE_FORMAT, format_local_datetime

TR = timezone(timedelta(hours=3))


def test_naive_utc_is_converted_to_target_timezone_and_crosses_midnight():
    utc = datetime(2026, 9, 29, 21, 58)  # DB'deki (UTC) deger

    assert format_local_datetime(utc, tz=TR) == "30.09.2026 00:58"


def test_date_only_format():
    assert format_local_datetime(datetime(2026, 9, 29, 22, 30), DATE_FORMAT, tz=TR) == "30.09.2026"


def test_aware_datetime_is_converted_not_reinterpreted():
    aware = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

    assert format_local_datetime(aware, tz=TR) == "01.01.2026 15:00"


def test_none_is_empty_string():
    assert format_local_datetime(None) == ""


def test_default_timezone_is_system_local():
    utc = datetime(2026, 6, 1, 12, 0)
    expected = utc.replace(tzinfo=timezone.utc).astimezone().strftime("%d.%m.%Y %H:%M")

    assert format_local_datetime(utc) == expected
