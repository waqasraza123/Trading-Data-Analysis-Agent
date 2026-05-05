from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.modules.workspace_setup.service import parse_step_input, sanitize_input
from app.modules.workspace_setup.steps import WorkspaceSetupStepKey


def test_workspace_setup_symbols_step_requires_selection() -> None:
    with pytest.raises(AppError) as error:
        parse_step_input(
            WorkspaceSetupStepKey.SYMBOLS,
            {"marketType": "crypto", "symbolIds": [], "symbolCodes": []},
        )

    assert error.value.code == "workspace_setup_step_invalid"


def test_workspace_setup_symbols_step_normalizes_codes() -> None:
    payload = parse_step_input(
        WorkspaceSetupStepKey.SYMBOLS,
        {"marketType": "crypto", "symbolCodes": [" btcusdt ", "BTCUSDT", "ethusdt"]},
    )

    assert payload.symbol_codes == ["BTCUSDT", "ETHUSDT"]


def test_workspace_setup_credential_input_redacts_secret_ref() -> None:
    sanitized = sanitize_input(
        WorkspaceSetupStepKey.CREDENTIAL_REFERENCE,
        {
            "mode": "create",
            "name": "Provider",
            "provider": "mock",
            "credentialType": "api_key",
            "secretRef": "vault/path",
        },
    )

    assert sanitized["secretRef"] == "configured"


def test_workspace_setup_workspace_select_requires_id() -> None:
    with pytest.raises(AppError):
        parse_step_input(WorkspaceSetupStepKey.WORKSPACE, {"mode": "select"})


def test_workspace_setup_first_scan_accepts_explicit_scan_config() -> None:
    payload = parse_step_input(
        WorkspaceSetupStepKey.FIRST_SCAN,
        {"run": True, "scanConfigId": str(uuid4())},
    )

    assert payload.run is True
