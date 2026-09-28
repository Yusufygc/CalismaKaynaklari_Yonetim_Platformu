from typing import Optional

from pydantic import BaseModel, ConfigDict

from models import ResourceStatus


class ResourceCreateSchema(BaseModel):
    """add_new_resource icin dogrulanmis girdi. Bilinmeyen alan -> ValidationError."""

    model_config = ConfigDict(extra="forbid")

    title: str
    url: Optional[str] = None
    category_id: Optional[int] = None
    status: ResourceStatus = ResourceStatus.PLANNED
    priority: int = 2
    content: Optional[str] = None
    tag_names: list[str] = []
    extra_metadata: Optional[dict] = None


class ResourceUpdateSchema(BaseModel):
    """update_resource icin kismi guncelleme. Hangi alanin gonderildigi
    ``model_fields_set`` ile ayirt edilir (eski ``"key" in data`` yerine)."""

    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = None
    url: Optional[str] = None
    category_id: Optional[int] = None
    status: Optional[ResourceStatus] = None
    priority: Optional[int] = None
    content: Optional[str] = None
    full_text: Optional[str] = None
    is_pinned: Optional[bool] = None
    tag_names: Optional[list[str]] = None
    extra_metadata: Optional[dict] = None
