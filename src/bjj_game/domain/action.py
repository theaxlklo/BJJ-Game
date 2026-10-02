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
    """An initiated action plus the effort the initiator commits to it."""

    initiator: Side
    action_id: str
    commitment: Commitment


@dataclass(frozen=True, slots=True)
class AttemptResult:
    """v0.1b bookkeeping around an unchanged Mount-v0 resolution."""

    attempt: ActionAttempt
    stamina: StaminaSpend
    resolution: ResolutionResult
