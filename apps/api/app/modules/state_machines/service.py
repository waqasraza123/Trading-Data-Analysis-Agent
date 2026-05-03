from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.state_machines.models import (
    StateMachineDefinition,
    StateMachineDefinitionStatus,
    StateTransitionValidation,
    StateTransitionValidationStatus,
)
from app.modules.state_machines.registry import DEFAULT_STATE_MACHINES


@dataclass(frozen=True)
class TransitionValidationResult:
    state_machine_key: str
    state_machine_version: str
    object_type: str
    object_id: UUID | None
    from_state: str
    to_state: str
    validation_status: str
    is_valid: bool
    reason: str
    validation_id: UUID | None
    terminal_transition: bool


@dataclass(frozen=True)
class StateMachineSeedResult:
    seeded_count: int
    updated_count: int
    keys: list[str]


class StateMachineService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def seed_default_state_machines(self) -> StateMachineSeedResult:
        seeded_count = 0
        updated_count = 0
        keys: list[str] = []
        for definition in DEFAULT_STATE_MACHINES:
            existing_definition = await self.get_state_machine(
                definition.key,
                version=definition.version,
                include_inactive=True,
            )
            if existing_definition is None:
                self.session.add(
                    StateMachineDefinition(
                        key=definition.key,
                        version=definition.version,
                        object_type=definition.object_type,
                        states_json=list(definition.states),
                        transitions_json=[transition.to_json() for transition in definition.transitions],
                        terminal_states_json=list(definition.terminal_states),
                        metadata_json=definition.metadata,
                        status=StateMachineDefinitionStatus.ACTIVE,
                    )
                )
                seeded_count += 1
            else:
                existing_definition.object_type = definition.object_type
                existing_definition.states_json = list(definition.states)
                existing_definition.transitions_json = [
                    transition.to_json() for transition in definition.transitions
                ]
                existing_definition.terminal_states_json = list(definition.terminal_states)
                existing_definition.metadata_json = definition.metadata
                existing_definition.status = StateMachineDefinitionStatus.ACTIVE
                updated_count += 1
            keys.append(definition.key)
        await self.session.flush()
        return StateMachineSeedResult(
            seeded_count=seeded_count,
            updated_count=updated_count,
            keys=keys,
        )

    async def get_state_machine(
        self,
        key: str,
        version: str | None = None,
        include_inactive: bool = False,
    ) -> StateMachineDefinition | None:
        statement: Select[tuple[StateMachineDefinition]] = select(StateMachineDefinition).where(
            StateMachineDefinition.key == key
        )
        if version is None:
            statement = statement.where(
                StateMachineDefinition.status == StateMachineDefinitionStatus.ACTIVE
            ).order_by(StateMachineDefinition.version.desc())
        else:
            statement = statement.where(StateMachineDefinition.version == version)
            if not include_inactive:
                statement = statement.where(
                    StateMachineDefinition.status == StateMachineDefinitionStatus.ACTIVE
                )
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def get_state_machine_or_error(
        self,
        key: str,
        version: str | None = None,
    ) -> StateMachineDefinition:
        definition = await self.get_state_machine(key, version=version)
        if definition is None:
            raise AppError(404, "state_machine_not_found", "State machine not found")
        return definition

    async def get_state_machine_for_object_type(
        self,
        object_type: str,
        key: str | None = None,
        version: str | None = None,
    ) -> StateMachineDefinition | None:
        if key is not None:
            definition = await self.get_state_machine(key, version=version)
            if definition is None or definition.object_type != object_type:
                return None
            return definition
        statement: Select[tuple[StateMachineDefinition]] = (
            select(StateMachineDefinition)
            .where(
                StateMachineDefinition.object_type == object_type,
                StateMachineDefinition.status == StateMachineDefinitionStatus.ACTIVE,
            )
            .order_by(StateMachineDefinition.version.desc())
        )
        if version is not None:
            statement = statement.where(StateMachineDefinition.version == version)
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def validate_transition(
        self,
        object_type: str,
        from_state: str,
        to_state: str,
        state_machine_key: str | None = None,
        state_machine_version: str | None = None,
        object_id: UUID | None = None,
    ) -> TransitionValidationResult:
        definition = await self.get_state_machine_for_object_type(
            object_type=object_type,
            key=state_machine_key,
            version=state_machine_version,
        )
        if definition is None:
            return TransitionValidationResult(
                state_machine_key=state_machine_key or "",
                state_machine_version=state_machine_version or "",
                object_type=object_type,
                object_id=object_id,
                from_state=from_state,
                to_state=to_state,
                validation_status=StateTransitionValidationStatus.INVALID,
                is_valid=False,
                reason="State machine is not registered for object type",
                validation_id=None,
                terminal_transition=False,
            )
        is_valid, reason = self.validate_transition_against_definition(
            definition=definition,
            from_state=from_state,
            to_state=to_state,
        )
        return TransitionValidationResult(
            state_machine_key=definition.key,
            state_machine_version=definition.version,
            object_type=object_type,
            object_id=object_id,
            from_state=from_state,
            to_state=to_state,
            validation_status=(
                StateTransitionValidationStatus.VALID
                if is_valid
                else StateTransitionValidationStatus.INVALID
            ),
            is_valid=is_valid,
            reason=reason,
            validation_id=None,
            terminal_transition=to_state in definition.terminal_states_json,
        )

    def validate_transition_against_definition(
        self,
        definition: StateMachineDefinition,
        from_state: str,
        to_state: str,
    ) -> tuple[bool, str]:
        states = set(definition.states_json)
        terminal_states = set(definition.terminal_states_json)
        transitions = {
            (str(item.get("fromState")), str(item.get("toState")))
            for item in definition.transitions_json
            if isinstance(item, dict)
        }
        if from_state not in states:
            return False, "from_state is not allowed for object type"
        if to_state not in states:
            return False, "to_state is not allowed for object type"
        if from_state in terminal_states:
            return False, "from_state is terminal"
        if (from_state, to_state) not in transitions:
            return False, "Transition is not allowed for object type"
        return True, "Transition is valid"

    async def record_transition_validation(
        self,
        result: TransitionValidationResult,
        workspace_id: UUID | None = None,
    ) -> StateTransitionValidation:
        validation = StateTransitionValidation(
            workspace_id=workspace_id,
            state_machine_key=result.state_machine_key,
            state_machine_version=result.state_machine_version,
            object_type=result.object_type,
            object_id=result.object_id,
            from_state=result.from_state,
            to_state=result.to_state,
            validation_status=result.validation_status,
            reason=result.reason,
        )
        self.session.add(validation)
        await self.session.flush()
        await self.session.refresh(validation)
        return validation

    async def validate_and_record_transition(
        self,
        object_type: str,
        from_state: str,
        to_state: str,
        workspace_id: UUID | None = None,
        object_id: UUID | None = None,
        state_machine_key: str | None = None,
        state_machine_version: str | None = None,
        record_validation: bool = True,
    ) -> TransitionValidationResult:
        result = await self.validate_transition(
            object_type=object_type,
            from_state=from_state,
            to_state=to_state,
            state_machine_key=state_machine_key,
            state_machine_version=state_machine_version,
            object_id=object_id,
        )
        if not record_validation:
            return result
        validation = await self.record_transition_validation(result, workspace_id=workspace_id)
        return TransitionValidationResult(
            state_machine_key=result.state_machine_key,
            state_machine_version=result.state_machine_version,
            object_type=result.object_type,
            object_id=result.object_id,
            from_state=result.from_state,
            to_state=result.to_state,
            validation_status=result.validation_status,
            is_valid=result.is_valid,
            reason=result.reason,
            validation_id=validation.id,
            terminal_transition=result.terminal_transition,
        )

    async def list_state_machines(
        self,
        object_type: str | None = None,
        status: str | None = None,
    ) -> list[StateMachineDefinition]:
        statement: Select[tuple[StateMachineDefinition]] = select(StateMachineDefinition)
        if object_type is not None:
            statement = statement.where(StateMachineDefinition.object_type == object_type)
        if status is not None:
            statement = statement.where(StateMachineDefinition.status == status)
        statement = statement.order_by(
            StateMachineDefinition.object_type.asc(),
            StateMachineDefinition.key.asc(),
            StateMachineDefinition.version.asc(),
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
