from uuid import UUID

from app.modules.data_sources.models import DataSourceStatus, DataSourceType
from app.modules.data_sources.schemas import DataSourceCreate


def default_data_sources(workspace_id: UUID) -> tuple[DataSourceCreate, ...]:
    return (
        DataSourceCreate(
            workspace_id=workspace_id,
            name="CSV Upload",
            source_type=DataSourceType.CSV_UPLOAD,
            provider="csv",
            status=DataSourceStatus.ACTIVE,
        ),
        DataSourceCreate(
            workspace_id=workspace_id,
            name="Internal JSON Import",
            source_type=DataSourceType.JSON_IMPORT,
            provider="internal_json",
            status=DataSourceStatus.ACTIVE,
        ),
    )
