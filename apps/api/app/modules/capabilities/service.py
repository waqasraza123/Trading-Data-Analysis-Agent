from dataclasses import dataclass
from importlib.util import find_spec

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.capabilities.models import CapabilityStatus, IntelligenceCapability
from app.modules.capabilities.registry import (
    DEFAULT_CAPABILITIES,
    DEFAULT_CAPABILITY_VERSION,
    CapabilityDefinition,
    artifact_refs,
    contract_refs,
    dependency_refs,
    route_refs,
)
from app.modules.capabilities.repository import CapabilityRepository
from app.modules.capabilities.schemas import CapabilityRuntimeAvailability, CapabilitySummaryRead


@dataclass(frozen=True)
class CapabilitySeedResult:
    capabilities: list[IntelligenceCapability]


class CapabilityService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = CapabilityRepository(session)

    async def seed_default_capabilities(self) -> CapabilitySeedResult:
        capability_rows = [
            self.build_capability_model(definition) for definition in DEFAULT_CAPABILITIES
        ]
        capabilities = await self.repository.upsert_defaults(capability_rows)
        return CapabilitySeedResult(capabilities=capabilities)

    async def list_capabilities(
        self,
        category: str | None = None,
        status: str | None = None,
        execution_type: str | None = None,
        safety_level: str | None = None,
        requires_external_credentials: bool | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[IntelligenceCapability]:
        return await self.repository.list_capabilities(
            category=category,
            status=status,
            execution_type=execution_type,
            safety_level=safety_level,
            requires_external_credentials=requires_external_credentials,
            limit=limit,
            offset=offset,
        )

    async def get_capability(self, key: str) -> IntelligenceCapability:
        capability = await self.repository.get_latest_by_key(key)
        if capability is None:
            raise AppError(404, "capability_not_found", "Capability not found")
        return capability

    async def update_capability_status(
        self,
        key: str,
        version: str,
        status: CapabilityStatus,
    ) -> IntelligenceCapability:
        capability = await self.repository.get_by_key_version(key, version)
        if capability is None:
            raise AppError(404, "capability_not_found", "Capability not found")
        return await self.repository.update_status(capability, status.value)

    def collect_runtime_availability(
        self,
        capabilities: list[IntelligenceCapability] | None = None,
    ) -> dict[str, CapabilityRuntimeAvailability]:
        runtime: dict[str, CapabilityRuntimeAvailability] = {}
        for capability in capabilities or []:
            runtime[capability.key] = self.runtime_for_capability(capability)
        if capabilities is None:
            for definition in DEFAULT_CAPABILITIES:
                runtime[definition.key] = self.runtime_for_definition(definition)
        return runtime

    async def summarize_capabilities(self) -> CapabilitySummaryRead:
        capabilities = await self.list_capabilities(limit=500)
        runtime_by_key = self.collect_runtime_availability(capabilities)
        by_runtime_status: dict[str, int] = {}
        missing_modules: list[str] = []
        disabled_modules: list[str] = []
        provider_backed_modules: list[str] = []
        safe_to_run_automatically: list[str] = []
        for capability in capabilities:
            runtime = runtime_by_key[capability.key]
            by_runtime_status[runtime.runtime_status.value] = (
                by_runtime_status.get(runtime.runtime_status.value, 0) + 1
            )
            if not runtime.installed:
                missing_modules.append(capability.key)
            if capability.status == CapabilityStatus.DISABLED.value:
                disabled_modules.append(capability.key)
            if capability.requires_external_credentials:
                provider_backed_modules.append(capability.key)
            if capability.metadata_json.get("safeToRunAutomatically") is True:
                safe_to_run_automatically.append(capability.key)
        return CapabilitySummaryRead(
            total=await self.repository.count_total(),
            by_status=await self.repository.count_by_field("status"),
            by_category=await self.repository.count_by_field("category"),
            by_execution_type=await self.repository.count_by_field("execution_type"),
            by_safety_level=await self.repository.count_by_field("safety_level"),
            by_runtime_status=by_runtime_status,
            requires_external_credentials=sum(
                1 for capability in capabilities if capability.requires_external_credentials
            ),
            requires_database=sum(1 for capability in capabilities if capability.requires_database),
            missing_modules=missing_modules,
            disabled_modules=disabled_modules,
            provider_backed_modules=provider_backed_modules,
            safe_to_run_automatically=safe_to_run_automatically,
        )

    def build_capability_model(self, definition: CapabilityDefinition) -> IntelligenceCapability:
        runtime = self.runtime_for_definition(definition)
        status = definition.status
        if not runtime.installed:
            status = CapabilityStatus.UNAVAILABLE
        return IntelligenceCapability(
            key=definition.key,
            name=definition.name,
            version=self.version_for_definition(definition),
            category=definition.category.value,
            status=status.value,
            execution_type=definition.execution_type.value,
            safety_level=definition.safety_level.value,
            requires_external_credentials=definition.requires_external_credentials,
            requires_database=definition.requires_database,
            input_contracts_json=contract_refs(definition.input_contracts),
            output_contracts_json=contract_refs(definition.output_contracts),
            produced_artifacts_json=artifact_refs(definition.produced_artifacts),
            route_refs_json=route_refs(definition.route_refs),
            dependencies_json=dependency_refs(definition.dependencies),
            metadata_json={
                **definition.metadata,
                "modulePath": definition.module_path,
            },
        )

    def runtime_for_capability(
        self,
        capability: IntelligenceCapability,
    ) -> CapabilityRuntimeAvailability:
        definition = next(
            (
                item
                for item in DEFAULT_CAPABILITIES
                if item.key == capability.key
                and capability.version in {item.version, self.version_for_definition(item)}
            ),
            None,
        )
        module_path = capability.metadata_json.get("modulePath")
        if definition is not None:
            return self.runtime_for_definition(definition, persisted_status=capability.status)
        if not isinstance(module_path, str):
            return CapabilityRuntimeAvailability(
                installed=False,
                enabled=False,
                database_configured=self.settings.database_url is not None,
                external_credentials_configured=None,
                runtime_status=CapabilityStatus.UNAVAILABLE,
                reasons=["Capability has no modulePath metadata"],
            )
        return self.runtime_for_values(
            key=capability.key,
            module_path=module_path,
            status=capability.status,
            requires_database=capability.requires_database,
            requires_external_credentials=capability.requires_external_credentials,
            metadata_json=capability.metadata_json,
        )

    def runtime_for_definition(
        self,
        definition: CapabilityDefinition,
        persisted_status: str | None = None,
    ) -> CapabilityRuntimeAvailability:
        return self.runtime_for_values(
            key=definition.key,
            module_path=definition.module_path,
            status=persisted_status or definition.status.value,
            requires_database=definition.requires_database,
            requires_external_credentials=definition.requires_external_credentials,
            metadata_json=definition.metadata,
        )

    def version_for_definition(self, definition: CapabilityDefinition) -> str:
        if definition.version != DEFAULT_CAPABILITY_VERSION:
            return definition.version
        return self.settings.capability_registry_default_version

    def runtime_for_values(
        self,
        key: str,
        module_path: str | None,
        status: str,
        requires_database: bool,
        requires_external_credentials: bool,
        metadata_json: dict[str, object],
    ) -> CapabilityRuntimeAvailability:
        installed = module_path is None or find_spec(module_path) is not None
        database_configured = self.settings.database_url is not None
        credentials_configured = (
            self.credentials_configured(metadata_json)
            if requires_external_credentials
            else None
        )
        enabled = self.module_enabled(metadata_json, status)
        reasons: list[str] = []
        if not installed:
            reasons.append("Module is not installed")
        if requires_database and not database_configured:
            reasons.append("DATABASE_URL is not configured")
        if requires_external_credentials and not credentials_configured:
            reasons.append("External credentials or provider settings are not configured")
        if not enabled:
            reasons.append("Capability is disabled by status or settings")
        runtime_status = self.resolve_runtime_status(
            key=key,
            status=status,
            installed=installed,
            enabled=enabled,
            database_configured=database_configured,
            credentials_configured=credentials_configured,
            requires_database=requires_database,
            requires_external_credentials=requires_external_credentials,
        )
        return CapabilityRuntimeAvailability(
            installed=installed,
            enabled=enabled,
            database_configured=database_configured,
            external_credentials_configured=credentials_configured,
            runtime_status=runtime_status,
            reasons=reasons,
        )

    def resolve_runtime_status(
        self,
        *,
        key: str,
        status: str,
        installed: bool,
        enabled: bool,
        database_configured: bool,
        credentials_configured: bool | None,
        requires_database: bool,
        requires_external_credentials: bool,
    ) -> CapabilityStatus:
        if status in {CapabilityStatus.DISABLED.value, CapabilityStatus.DEPRECATED.value}:
            return CapabilityStatus(status)
        if not installed:
            return CapabilityStatus.UNAVAILABLE
        if requires_database and not database_configured:
            return CapabilityStatus.UNAVAILABLE
        if requires_external_credentials and credentials_configured is False:
            if key in {"llm_explanations", "scenario_reasoning", "chart_screenshots"}:
                return CapabilityStatus.EXPERIMENTAL
            return CapabilityStatus.UNAVAILABLE
        if not enabled:
            return CapabilityStatus.DISABLED
        if status == CapabilityStatus.EXPERIMENTAL.value:
            return CapabilityStatus.EXPERIMENTAL
        return CapabilityStatus.AVAILABLE

    def module_enabled(self, metadata_json: dict[str, object], status: str) -> bool:
        if status == CapabilityStatus.DISABLED.value:
            return False
        setting_name = metadata_json.get("moduleSetting")
        if not isinstance(setting_name, str):
            return True
        value = getattr(self.settings, setting_name, None)
        if value is None:
            return True
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return bool(value.strip())
        return True

    def credentials_configured(self, metadata_json: dict[str, object]) -> bool:
        setting_names = metadata_json.get("credentialSettings")
        if not isinstance(setting_names, list):
            return False
        for setting_name in setting_names:
            if not isinstance(setting_name, str):
                continue
            value = getattr(self.settings, setting_name, None)
            if value is None:
                continue
            if hasattr(value, "get_secret_value"):
                if value.get_secret_value().strip():
                    return True
                continue
            if isinstance(value, str) and value.strip():
                return True
        return False
