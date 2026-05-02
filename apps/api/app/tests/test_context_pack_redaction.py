from app.modules.context_packs.redaction import (
    ContextPackRedactionState,
    bounded_items,
    safe_value,
)


def test_context_pack_redacts_secret_and_raw_payload_keys() -> None:
    state = ContextPackRedactionState()
    value = safe_value(
        {
            "databaseUrl": "postgresql://example",
            "providerToken": "secret-token",
            "rawImageBase64": "abcd",
            "nested": {"api_key": "key"},
        },
        state,
        max_text_length=100,
    )

    assert value == {
        "databaseUrl": "[redacted]",
        "providerToken": "[redacted]",
        "rawImageBase64": {"redacted": True, "present": True},
        "nested": {"api_key": "[redacted]"},
    }
    assert state.redaction_summary()["redactedPathCount"] == 4


def test_context_pack_truncates_text_and_lists() -> None:
    state = ContextPackRedactionState()
    value = safe_value({"summary": "x" * 12}, state, max_text_length=5)
    items = bounded_items("items", [1, 2, 3], 2, state, 5)

    assert value == {"summary": "xxxxx"}
    assert items == {
        "items": [1, 2],
        "returnedCount": 2,
        "totalCount": 3,
        "truncated": True,
    }
    assert "root.summary" in state.truncation_summary()
    assert "items" in state.truncation_summary()
