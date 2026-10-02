from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .model import ResolutionResult, Side
from .stamina import StaminaSpend


class Commitment(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

    @property
    def display(self) -> str:
        return {
            Commitment.LOW: "Low",
            Commitment.MEDIUM: "Medium",
            Commitment.HIGH: "High",
        }[self]


@dataclass(frozen=True, slots=True)
class ActionAttempt:
    """An initiated action plus requested/effective effort."""

    initiator: Side
    action_id: str
    requested_commitment: Commitment
    effective_commitment: Commitment | None

    @property
    def commitment(self) -> Commitment:
        """Compatibility alias for the originally requested commitment."""
        return self.requested_commitment


@dataclass(frozen=True, slots=True)
class AttemptResult:
    """Commitment/stamina bookkeeping around unchanged Mount-v0 resolution."""

    attempt: ActionAttempt
    requested_cost: int
    effective_cost: int
    funding_gap: int
    stamina: StaminaSpend
    resolution: ResolutionResult
