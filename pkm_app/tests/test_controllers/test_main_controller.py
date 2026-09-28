from contextlib import contextmanager

from pkm_app.ui.controllers.main_controller import MainController

# main_controller.py bare "core.events" ile import ediyor; ayni singleton'a
# baglanmak icin ayni import yolu kullanilmali (pkm_app.core.events, sys.modules
# aliasing sirasina bagli olarak farkli bir modul/instance olabilir).
from core.events import event_bus


@contextmanager
def _capture(signal):
    """event_bus sinyalini test suresince yakalar, sonunda baglantiyi kaldirir."""
    received = []
    handler = lambda *args: received.append(args)
    signal.connect(handler)
    try:
        yield received
    finally:
        signal.disconnect(handler)


def test_get_resource_returns_none_when_missing(qapp, session):
    controller = MainController(session)

    assert controller.get_resource(999) is None


def test_add_resource_success_emits_resource_added(qapp, session):
    controller = MainController(session)
    with _capture(event_bus.resource_added) as received:
        resource = controller.add_resource({"title": "Test Kaynak"})

        assert resource is not None
        assert received == [(resource.id,)]


def test_add_resource_failure_emits_error_and_returns_none(qapp, session):
    controller = MainController(session)
    with _capture(event_bus.error_occurred) as received:
        result = controller.add_resource({"title": ""})

        assert result is None
        assert len(received) == 1


def test_delete_resource_failure_emits_error(qapp, session):
    controller = MainController(session)
    with _capture(event_bus.error_occurred) as received:
        controller.delete_resource(999)

        assert len(received) == 1


def test_toggle_pin_flips_value_and_emits_resource_updated(qapp, session):
    controller = MainController(session)
    resource = controller.add_resource({"title": "Pin Me"})
    with _capture(event_bus.resource_updated) as received:
        controller.toggle_pin(resource.id)

        assert received == [(resource.id,)]
        assert controller.get_resource(resource.id).is_pinned is True
