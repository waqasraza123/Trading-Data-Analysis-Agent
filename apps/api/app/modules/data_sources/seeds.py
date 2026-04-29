from uuid import UUID

from app.modules.data_sources.models import DataSourceStatus, DataSourceType
from app.modules.data_sources.schemas import DataSourceCreate


def default_data_sources(workspace_id: UUID) -> tuple[DataSourceCreate, ...]:
    return (
        DataSourceCreate(
            workspace_id=workspace_id,
            name="csv_upload",
            source_type=DataSourceType.CSV_UPLOAD,
            provider="csv",
            status=DataSourceStatus.ACTIVE,
        ),
        DataSourceCreate(
            workspace_id=workspace_id,
            name="json_import",
            source_type=DataSourceType.JSON_IMPORT,
            provider="internal_json",
            status=DataSourceStatus.ACTIVE,
        ),
        DataSourceCreate(
            workspace_id=workspace_id,
            name="mock_live",
            source_type=DataSourceType.WEBSOCKET_LIVE,
            provider="mock",
            status=DataSourceStatus.ACTIVE,
        ),
        DataSourceCreate(
            workspace_id=workspace_id,
            name="manual_news",
            source_type=DataSourceType.MANUAL_SEED,
            provider="manual_news",
            status=DataSourceStatus.ACTIVE,
            config_json={"purpose": "manual_news_event_context"},
        ),
        DataSourceCreate(
            workspace_id=workspace_id,
            name="chart_screenshot",
            source_type=DataSourceType.CHART_SCREENSHOT,
            provider="manual_ocr",
            status=DataSourceStatus.ACTIVE,
            config_json={"purpose": "chart_screenshot_trend_prediction"},
        ),
    )
