import re
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Select, desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.intelligence_metrics.models import (
    IntelligenceMetricSnapshot,
    IntelligenceMetricSnapshotStatus,
    IntelligenceMetricSnapshotType,
)

IDENTIFIER_RE = re.compile(r"^[a-z_][a-z0-9_]*$")


class IntelligenceMetricsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def table_columns(self, table_name: str) -> set[str] | None:
        validate_identifier(table_name)
        statement = text(
            "select column_name from information_schema.columns "
            "where table_schema = 'public' and table_name = :table_name"
        )
        result = await self.session.execute(statement, {"table_name": table_name})
        columns = {str(row[0]) for row in result.all()}
        return columns or None

    async def count_rows(
        self,
        table_name: str,
        columns: set[str],
        workspace_id: UUID | None = None,
    ) -> int:
        validate_identifier(table_name)
        where_sql, params = build_workspace_filter(columns, workspace_id)
        result = await self.session.execute(
            text(f"select count(*) from {table_name}{where_sql}"),
            params,
        )
        return int(result.scalar_one())

    async def count_grouped(
        self,
        table_name: str,
        column_name: str,
        columns: set[str],
        workspace_id: UUID | None = None,
    ) -> dict[str, int]:
        validate_identifier(table_name)
        validate_identifier(column_name)
        if column_name not in columns:
            return {}
        where_sql, params = build_workspace_filter(columns, workspace_id)
        statement = text(
            f"select {column_name}, count(*) from {table_name}"
            f"{where_sql} group by {column_name} order by {column_name}"
        )
        result = await self.session.execute(statement, params)
        return {normalize_group_key(row[0]): int(row[1]) for row in result.all()}

    async def count_where(
        self,
        table_name: str,
        columns: set[str],
        conditions: Sequence[str],
        workspace_id: UUID | None = None,
        params: dict[str, Any] | None = None,
    ) -> int:
        validate_identifier(table_name)
        workspace_sql, query_params = build_workspace_filter(columns, workspace_id)
        all_conditions = list(conditions)
        if workspace_sql:
            all_conditions.append(workspace_sql.removeprefix(" where "))
        where_sql = f" where {' and '.join(all_conditions)}" if all_conditions else ""
        query_params.update(params or {})
        result = await self.session.execute(
            text(f"select count(*) from {table_name}{where_sql}"),
            query_params,
        )
        return int(result.scalar_one())

    async def create_snapshot(
        self,
        workspace_id: UUID | None,
        snapshot_type: IntelligenceMetricSnapshotType,
        status: IntelligenceMetricSnapshotStatus,
        collected_at: datetime,
        metrics_json: dict[str, object],
        warnings_json: list[dict[str, object]],
    ) -> IntelligenceMetricSnapshot:
        snapshot = IntelligenceMetricSnapshot(
            workspace_id=workspace_id,
            snapshot_type=snapshot_type.value,
            status=status.value,
            collected_at=collected_at,
            metrics_json=metrics_json,
            warnings_json=warnings_json,
        )
        self.session.add(snapshot)
        await self.session.flush()
        await self.session.refresh(snapshot)
        return snapshot

    async def get_latest_snapshot(
        self,
        workspace_id: UUID | None = None,
        snapshot_type: IntelligenceMetricSnapshotType | None = None,
    ) -> IntelligenceMetricSnapshot | None:
        statement: Select[tuple[IntelligenceMetricSnapshot]] = select(
            IntelligenceMetricSnapshot
        ).order_by(desc(IntelligenceMetricSnapshot.collected_at))
        if workspace_id is not None:
            statement = statement.where(IntelligenceMetricSnapshot.workspace_id == workspace_id)
        if snapshot_type is not None:
            statement = statement.where(
                IntelligenceMetricSnapshot.snapshot_type == snapshot_type.value
            )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def list_snapshots(
        self,
        workspace_id: UUID | None = None,
        snapshot_type: IntelligenceMetricSnapshotType | None = None,
        status: IntelligenceMetricSnapshotStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[IntelligenceMetricSnapshot]:
        statement: Select[tuple[IntelligenceMetricSnapshot]] = (
            select(IntelligenceMetricSnapshot)
            .order_by(desc(IntelligenceMetricSnapshot.collected_at))
            .limit(limit)
            .offset(offset)
        )
        if workspace_id is not None:
            statement = statement.where(IntelligenceMetricSnapshot.workspace_id == workspace_id)
        if snapshot_type is not None:
            statement = statement.where(
                IntelligenceMetricSnapshot.snapshot_type == snapshot_type.value
            )
        if status is not None:
            statement = statement.where(IntelligenceMetricSnapshot.status == status.value)
        result = await self.session.execute(statement)
        return list(result.scalars().all())


def build_workspace_filter(
    columns: set[str],
    workspace_id: UUID | None,
) -> tuple[str, dict[str, Any]]:
    if workspace_id is None or "workspace_id" not in columns:
        return "", {}
    return " where workspace_id = :workspace_id", {"workspace_id": workspace_id}


def normalize_group_key(value: object) -> str:
    if value is None:
        return "null"
    return str(value)


def validate_identifier(value: str) -> None:
    if IDENTIFIER_RE.fullmatch(value) is None:
        msg = f"Unsafe SQL identifier: {value}"
        raise ValueError(msg)


def utc_now() -> datetime:
    return datetime.now(UTC)
