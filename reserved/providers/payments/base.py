"""Provider-neutral boundary for a future user-authorised money movement flow.

Nothing in this module initiates a payment. Tax calculation and set-aside
tracking must remain usable when no money-movement provider is selected.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class SetAsideMode(str, Enum):
    TRACK_ONLY = "track_only"
    ONE_OFF_PAYMENT = "one_off_payment"
    RECURRING_SWEEP = "recurring_sweep"


class InstructionStatus(str, Enum):
    DRAFT = "draft"
    REQUIRES_USER_AUTHORISATION = "requires_user_authorisation"
    AUTHORISED = "authorised"
    SUBMITTED = "submitted"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class SetAsideInstruction:
    instruction_id: str
    user_id: str
    amount: Decimal
    currency: str
    mode: SetAsideMode
    destination_reference: str | None = None
    provider: str | None = None
    provider_reference: str | None = None
    status: InstructionStatus = InstructionStatus.DRAFT


class MoneyMovementProvider(ABC):
    """Optional payment boundary; deliberately separate from Yapily AIS."""

    @abstractmethod
    def create_authorisation(self, instruction: SetAsideInstruction) -> dict:
        """Return an external authorisation journey; never execute implicitly."""
        raise NotImplementedError

    @abstractmethod
    def get_status(self, provider_reference: str) -> InstructionStatus:
        raise NotImplementedError

    @abstractmethod
    def cancel(self, provider_reference: str) -> bool:
        raise NotImplementedError


class TrackOnlyProvider:
    """V1-safe tracking mode: records intent but cannot move money."""

    provider_name = "track_only"

    def record(self, instruction: SetAsideInstruction) -> SetAsideInstruction:
        if instruction.mode is not SetAsideMode.TRACK_ONLY:
            raise ValueError("TrackOnlyProvider accepts track-only instructions")
        if instruction.amount <= 0:
            raise ValueError("Set-aside amount must be positive")
        return instruction

