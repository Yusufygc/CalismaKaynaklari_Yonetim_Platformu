from alembic import command as alembic_command
from sqlalchemy import create_engine, inspect, text

from models import Resource, ResourceStatus
from repositories.resource_repo import ResourceRepository
from services.resource_service import ResourceService
from services.schemas import ResourceCreateSchema, ResourceUpdateSchema
from utils import db_utils
from utils.reading_time import estimate_reading_minutes


def test_estimate_reading_minutes():
    assert estimate_reading_minutes(None) == 0
    assert estimate_reading_minutes("   ") == 0
    assert estimate_reading_minutes("kelime " * 10) == 1  # en az 1 dk
    assert estimate_reading_minutes("kelime " * 1000) == 5


def test_service_computes_reading_minutes_from_content_on_create(session):
    service = ResourceService(session)

    resource = service.add_new_resource(ResourceCreateSchema(title="A", content="kelime " * 400))

    assert resource.reading_minutes == 2


def test_service_recomputes_on_full_text_and_content_updates(session):
    service = ResourceService(session)
    resource = service.add_new_resource(ResourceCreateSchema(title="A"))
    assert resource.reading_minutes == 0

    service.update_resource(resource.id, ResourceUpdateSchema(full_text="kelime " * 2000))
    assert resource.reading_minutes == 10

    # full_text varken content'in okuma suresi ezmemesi: full_text onceliklidir.
    service.update_resource(resource.id, ResourceUpdateSchema(content="kisa not"))
    assert resource.reading_minutes == 10

    service.update_resource(resource.id, ResourceUpdateSchema(full_text=None))
    assert resource.reading_minutes == 1  # yalnizca content kaldi


def test_unrelated_update_does_not_touch_reading_minutes(session):
    service = ResourceService(session)
    resource = service.add_new_resource(ResourceCreateSchema(title="A", content="kelime " * 600))

    service.update_resource(resource.id, ResourceUpdateSchema(title="B"))

    assert resource.reading_minutes == 3


def test_list_queries_do_not_load_full_text(session):
    repo = ResourceRepository(session)
    repo.create(Resource(title="Buyuk", status=ResourceStatus.PLANNED, priority=2, full_text="x" * 10_000))
    session.commit()
    session.expire_all()

    resources = repo.query_filtered()

    assert "full_text" in inspect(resources[0]).unloaded  # liste sorgusu tam metni cekmedi
    assert resources[0].full_text == "x" * 10_000  # erisilince lazy yuklenir
    assert "full_text" not in inspect(resources[0]).unloaded


def test_migration_backfills_existing_resources(tmp_path, monkeypatch):
    db_path = tmp_path / "backfill.db"
    url = f"sqlite:///{db_path}"
    test_engine = create_engine(url)
    monkeypatch.setattr(db_utils, "engine", test_engine)
    monkeypatch.setattr(db_utils.settings, "DATABASE_URL", url)
    cfg = db_utils._alembic_config()
    alembic_command.upgrade(cfg, "c4d9a6b1e2f3")  # reading_minutes'tan onceki revision
    rows = [
        ("Tam metinli", "kelime " * 1000, None),
        ("Yalniz icerik", None, "kelime " * 400),
        ("Bos", None, None),
    ]
    with test_engine.begin() as conn:
        for title, full_text, content in rows:
            conn.execute(
                text(
                    "INSERT INTO resources (title, status, priority, is_pinned, is_favorite, full_text, content,"
                    " created_at, updated_at) VALUES (:t, 'PLANNED', 2, 0, 0, :f, :c, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                {"t": title, "f": full_text, "c": content},
            )

    alembic_command.upgrade(cfg, "head")

    with test_engine.connect() as conn:
        result = dict(conn.execute(text("SELECT title, reading_minutes FROM resources")).fetchall())
    assert result == {"Tam metinli": 5, "Yalniz icerik": 2, "Bos": 0}
