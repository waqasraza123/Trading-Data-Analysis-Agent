from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.imports.models import ImportBatch, ImportError


class ImportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_batch(self, batch: ImportBatch) -> ImportBatch:
        self.session.add(batch)
        await self.session.flush()
        await self.session.refresh(batch)
        return batch

    async def get_batch(self, import_batch_id: UUID) -> ImportBatch | None:
        return await self.session.get(ImportBatch, import_batch_id)

    async def add_error(self, error: ImportError) -> ImportError:
        self.session.add(error)
        await self.session.flush()
        await self.session.refresh(error)
        return error

    async def list_errors(
        self,
        import_batch_id: UUID,
        limit: int,
        offset: int,
    ) -> list[ImportError]:
        statement: Select[tuple[ImportError]] = (
            select(ImportError)
            .where(ImportError.import_batch_id == import_batch_id)
            .order_by(ImportError.row_number.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
