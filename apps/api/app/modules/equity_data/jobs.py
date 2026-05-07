from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.equity_data.operations import EquityDataOperationService
from app.modules.job_queue.dispatcher import JobQueueHandlerResult
from app.modules.job_queue.models import JobQueueItem


async def handle_equity_data_operation_job(
    job: JobQueueItem,
    session: AsyncSession,
) -> JobQueueHandlerResult:
    operation_id = coerce_operation_id(job.payload_json.get("operationId"))
    request = job.payload_json.get("request")
    if not isinstance(request, dict):
        raise AppError(422, "equity_data_operation_payload_invalid", "Operation payload is invalid")
    service = EquityDataOperationService(session)
    operation = await service.execute_operation(operation_id, request)
    return JobQueueHandlerResult(
        result_json={
            "operationId": str(operation.id),
            "operationStatus": operation.status,
            "counters": operation.counters_json,
        },
        completed_with_warnings=operation.status == "completed_with_warnings",
    )


def coerce_operation_id(value: object) -> UUID:
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as error:
        raise AppError(
            422,
            "equity_data_operation_id_invalid",
            "Operation id is invalid",
        ) from error
