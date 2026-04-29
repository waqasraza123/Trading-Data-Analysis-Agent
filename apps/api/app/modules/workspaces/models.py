from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class Workspace(Base):
    __tablename__ = "workspaces"

    id = uuid_primary_key()
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at = created_at_column()
    updated_at = updated_at_column()
