"""repair_paths: veri koku tasinirsa kaynaklarin PDF yollari depodaki dosyaya yeniden baglanir (dosya silinmez/tasinmaz)."""
import shutil

import pytest

from tests.pdf_factory import write_text_pdf
from tests.test_qml.qml_harness import SyncThreadPool
from ui_qml.bridge import QmlBridge


@pytest.fixture()
def env(qapp, session, tmp_path, monkeypatch):
    old_root = tmp_path / "depo"
    old_root.mkdir()
    roots = {"current": old_root}
    monkeypatch.setattr("ui_qml.pdf_files.pdf_storage_dir", lambda: roots["current"])
    bridge = QmlBridge(session)
    bridge.ctx.thread_pool = SyncThreadPool()
    monkeypatch.setattr(bridge.ctx.extractor, "schedule", lambda *args: None)
    bridge.library.importLocalPdf(write_text_pdf(tmp_path / "makale.pdf").as_uri())
    (resource,) = bridge.controllers.resources.load_resources_with_filters({})

    def move_data_root():
        new_root = tmp_path / "yeni_profil" / "depo"
        new_root.parent.mkdir()
        shutil.copytree(old_root, new_root)
        shutil.rmtree(old_root)
        roots["current"] = new_root
        return new_root

    return bridge, resource, old_root, move_data_root


def test_a_moved_data_root_is_repaired_by_pointing_the_resource_at_the_stored_file(env):
    bridge, resource, old_root, move_data_root = env
    assert resource.url.startswith("file://") and "depo" in resource.url

    new_root = move_data_root()
    repaired = bridge.ctx.pdf_library.repair_paths()

    again = bridge.controllers.resources.get_resource(resource.id)
    assert repaired == 1 and "yeni_profil" in again.url and str(old_root) not in again.url
    stored = bridge.ctx.pdf_library.file_path(bridge.ctx.pdf_library.documents().document_for_resource(resource.id))
    assert stored.is_file() and str(stored).startswith(str(new_root))
    assert bridge.ctx.pdf_library.repair_paths() == 0  # idempotent


def test_nothing_is_touched_when_the_file_still_exists_or_the_stored_file_is_missing(env):
    bridge, resource, old_root, move_data_root = env

    assert bridge.ctx.pdf_library.repair_paths() == 0  # yol saglam
    url_before = bridge.controllers.resources.get_resource(resource.id).url
    new_root = move_data_root()
    for stored in new_root.rglob("*.pdf"):
        stored.unlink()  # belge dosyasi depoda da yok: onarilacak bir sey yok, silme/olusturma yok

    assert bridge.ctx.pdf_library.repair_paths() == 0
    assert bridge.controllers.resources.get_resource(resource.id).url == url_before


def test_the_downloaded_file_reference_in_metadata_is_repaired_too(env):
    bridge, resource, old_root, move_data_root = env
    web = bridge.controllers.resources.add_resource(
        {"title": "Web PDF", "url": "https://x.org/a.pdf", "category_id": None, "priority": 2, "content": None,
         "tag_names": [], "extra_metadata": {"local_pdf": str(next(old_root.rglob("*.pdf")))}}
    )
    document = bridge.ctx.pdf_library.documents().document_for_resource(resource.id)
    from pdfkit.infra.orm import PdfResourceLinkRow
    session = bridge.ctx.controllers.session
    session.add(PdfResourceLinkRow(resource_id=web.id, document_id=document.id))
    session.commit()

    new_root = move_data_root()
    repaired = bridge.ctx.pdf_library.repair_paths()

    meta = bridge.controllers.resources.get_resource(web.id).extra_metadata
    assert repaired == 2 and meta["local_pdf"].startswith(str(new_root))
    assert bridge.controllers.resources.get_resource(web.id).url == "https://x.org/a.pdf"  # web adresi degismez


def test_start_maintenance_runs_the_repair_at_startup(env, monkeypatch):
    bridge, _resource, _old, move_data_root = env
    move_data_root()
    calls = []
    original = type(bridge.ctx.pdf_library).repair_paths
    monkeypatch.setattr(type(bridge.ctx.pdf_library), "repair_paths", lambda self: (calls.append(1), original(self))[1])

    bridge.ctx.pdf_library.start_maintenance()

    assert calls == [1]
