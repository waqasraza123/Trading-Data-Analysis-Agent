from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

type UuidPrimaryKey = Mapped[UUID]
type CreatedAt = Mapped[datetime]
type UpdatedAt = Mapped[datetime]


def uuid_primary_key() -> UuidPrimaryKey:
    return mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)


def created_at_column() -> CreatedAt:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


def updated_at_column() -> UpdatedAt:
    return mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
