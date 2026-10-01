"""The transition registry and repository-record shape (STATE_MACHINE.md sections 4, 13, 17)."""

from __future__ import annotations

from repository_presenter.core.state.schema import (
    ACTIVE_STATES,
    QUIESCENT_OR_TERMINAL_STATES,
    RepositoryRecord,
    TransitionReceipt,
    is_registered_transition,
)


def test_every_state_is_exactly_active_or_quiescent_terminal() -> None:
    assert not (ACTIVE_STATES & QUIESCENT_OR_TERMINAL_STATES)


def test_documented_happy_path_transitions_are_registered() -> None:
    for from_state, to_state in (
        ("OBSERVED", "SNAPSHOTTING"),
        ("SNAPSHOTTING", "EXTRACTING"),
        ("EXTRACTING", "INVESTIGATING"),
        ("COMPOSING", "VALIDATING"),
        ("VALIDATING", "REVIEWING"),
        ("REVIEWING", "ACCEPTED"),
        ("ACCEPTED", "PROVING_NO_OP"),
        ("PROVING_NO_OP", "READY_FOR_PROPOSAL"),
        ("READY_FOR_PROPOSAL", "MONITORING"),
        ("MONITORING", "OBSERVED"),
    ):
        assert is_registered_transition(from_state, to_state), (from_state, to_state)


def test_an_arbitrary_skip_ahead_is_not_registered() -> None:
    """Negative control: validation must never silently let a candidate skip stages."""
    assert not is_registered_transition("OBSERVED", "ACCEPTED")
    assert not is_registered_transition("EXTRACTING", "READY_FOR_PROPOSAL")
    assert not is_registered_transition("SUPERSEDED", "OBSERVED")


def test_retryable_resumes_into_any_active_state_but_not_a_terminal_one() -> None:
    assert is_registered_transition("RETRYABLE", "COMPOSING")
    assert not is_registered_transition("RETRYABLE", "READY_FOR_PROPOSAL")


def test_repository_record_round_trips_through_json() -> None:
    record = RepositoryRecord(
        repository="aspose-3d-foss/example",
        provider_repository_id=123,
        state="COMPOSING",
    )
    payload = record.model_dump_json()
    restored = RepositoryRecord.model_validate_json(payload)
    assert restored == record
    assert restored.state_version == 0
    assert restored.recent_trigger_dedup_keys == {}


def test_transition_receipt_uses_from_to_wire_names() -> None:
    receipt = TransitionReceipt(
        transition_id="t1",
        transaction_id="tx1",
        repository="aspose-3d-foss/example",
        from_state="VALIDATING",
        to_state="REVIEWING",
        event="deterministic_validation_passed",
        occurred_at="2026-10-01T00:00:00+00:00",
        input_manifest="sha256:a",
        output_manifest="sha256:b",
        policy_version="sha256:c",
        fencing_token=1,
    )
    wire = receipt.model_dump(mode="json", by_alias=True)
    assert wire["from"] == "VALIDATING"
    assert wire["to"] == "REVIEWING"
    assert TransitionReceipt.model_validate(wire) == receipt
