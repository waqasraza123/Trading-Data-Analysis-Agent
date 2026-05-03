from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rule_packs.models import AnalysisReproducibilityManifest, RulePack


class RulePackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, rule_pack: RulePack) -> RulePack:
        self.session.add(rule_pack)
        await self.session.flush()
        await self.session.refresh(rule_pack)
        return rule_pack

    async def get_by_id(self, rule_pack_id: UUID) -> RulePack | None:
        return await self.session.get(RulePack, rule_pack_id)

    async def get_by_key_version(
        self,
        key: str,
        version: str,
        workspace_id: UUID | None = None,
        allow_global_fallback: bool = True,
    ) -> RulePack | None:
        if workspace_id is not None:
            workspace_statement = select(RulePack).where(
                RulePack.workspace_id == workspace_id,
                RulePack.key == key,
                RulePack.version == version,
            )
            workspace_result = await self.session.execute(workspace_statement)
            workspace_rule_pack = workspace_result.scalar_one_or_none()
            if workspace_rule_pack is not None or not allow_global_fallback:
                return workspace_rule_pack
        statement = select(RulePack).where(
            RulePack.workspace_id.is_(None),
            RulePack.key == key,
            RulePack.version == version,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_rule_packs(
        self,
        limit: int,
        offset: int,
        workspace_id: UUID | None = None,
        status: str | None = None,
        key: str | None = None,
    ) -> list[RulePack]:
        statement: Select[tuple[RulePack]] = (
            select(RulePack)
            .order_by(RulePack.key.asc(), RulePack.version.asc(), RulePack.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if workspace_id is not None:
            statement = statement.where(RulePack.workspace_id == workspace_id)
        if status is not None:
            statement = statement.where(RulePack.status == status)
        if key is not None:
            statement = statement.where(RulePack.key == key)
        result = await self.session.execute(statement)
        return list(result.scalars().all())


class ReproducibilityManifestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        manifest: AnalysisReproducibilityManifest,
    ) -> AnalysisReproducibilityManifest:
        self.session.add(manifest)
        await self.session.flush()
        await self.session.refresh(manifest)
        return manifest

    async def get_by_analysis_run_version(
        self,
        analysis_run_id: UUID,
        manifest_version: str,
    ) -> AnalysisReproducibilityManifest | None:
        statement = select(AnalysisReproducibilityManifest).where(
            AnalysisReproducibilityManifest.analysis_run_id == analysis_run_id,
            AnalysisReproducibilityManifest.manifest_version == manifest_version,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_signal_version(
        self,
        signal_id: UUID,
        manifest_version: str,
    ) -> AnalysisReproducibilityManifest | None:
        statement = select(AnalysisReproducibilityManifest).where(
            AnalysisReproducibilityManifest.signal_id == signal_id,
            AnalysisReproducibilityManifest.manifest_version == manifest_version,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
