from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    color_hex: Mapped[str | None] = mapped_column(String(7), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(80), nullable=True)

    resources: Mapped[list["Resource"]] = relationship(  # type: ignore[name-defined]
        "Resource", back_populates="category"
    )

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name!r}>"
