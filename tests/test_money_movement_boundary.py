"""The v1 tracking boundary must not silently become payment initiation."""

from decimal import Decimal

from reserved.providers.payments.base import (
    InstructionStatus,
    SetAsideInstruction,
    SetAsideMode,
    TrackOnlyProvider,
)


def test_track_only_instruction_records_no_payment_provider_reference():
    instruction = SetAsideInstruction(
        instruction_id="synthetic-1",
        user_id="synthetic-user",
        amount=Decimal("250.00"),
        currency="GBP",
        mode=SetAsideMode.TRACK_ONLY,
    )
    recorded = TrackOnlyProvider().record(instruction)
    assert recorded.status is InstructionStatus.DRAFT
    assert recorded.provider is None
    assert recorded.provider_reference is None


def test_track_only_provider_rejects_payment_instruction():
    instruction = SetAsideInstruction(
        instruction_id="synthetic-2",
        user_id="synthetic-user",
        amount=Decimal("250.00"),
        currency="GBP",
        mode=SetAsideMode.ONE_OFF_PAYMENT,
    )
    try:
        TrackOnlyProvider().record(instruction)
    except ValueError as exc:
        assert "track-only" in str(exc)
    else:
        raise AssertionError("Track-only boundary must reject payment initiation")

