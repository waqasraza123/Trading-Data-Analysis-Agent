from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.job_queue.adapters.database import DatabaseJobQueueBackend


class RedisJobQueueBackend(DatabaseJobQueueBackend):
    backend_name = "redis"

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
