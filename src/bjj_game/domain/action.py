from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .model import Band, ResolutionResult, Side
from .stamina import StaminaBand, StaminaSpend


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
    """Commitment/stamina bookkeeping around deterministic exchange resolution."""

    attempt: ActionAttempt
    requested_cost: int
    effective_cost: int
    funding_gap: int
    stamina: StaminaSpend
    response_requested_commitment: Commitment | None
    response_effective_commitment: Commitment | None
    response_requested_cost: int
    response_effective_cost: int
    response_funding_gap: int
    response_stamina: StaminaSpend | None
    response_stamina_waived: int
    submission_hold_nominal_cost: int
    submission_hold_covered_by_response: int
    submission_hold_stamina: StaminaSpend | None
    stamina_band_before_action: StaminaBand
    responder_stamina_band_before_action: StaminaBand
    initiator_exhaustion_modifier: int
    responder_exhaustion_modifier: int
    exhaustion_modifier: int
    initiator_commitment_modifier: int
    response_undercommitment_modifier: int
    base_resolution: ResolutionResult
    resolution: ResolutionResult


@dataclass(frozen=True, slots=True)
class RecoveryHoldResult:
    """A D2 v1e RECOVERY HOLD: Bottom declines to initiate without RESET.

    Spends and grants no stamina, consumes no simulated time, and only
    passes initiative to the opponent.
    """

    side: Side
    next_initiator: Side
    elapsed_seconds: int
    clock_seconds: int
    stamina: int


@dataclass(frozen=True, slots=True)
class ResetWindowResult:
    """A deliberate no-action decision in the modern v0.1/v0.3b flow."""

    initiator: Side
    next_initiator: Side
    clock_seconds: int
    axis: float
    band: Band
    stamina: int
    progress_route_available: bool = False
    advancement_clock_seconds: int = 0
    stalling_offense: bool = False
    stalling_consequence: str | None = None
    penalty_axis_before: float | None = None
    penalty_axis_after: float | None = None
    position_reset: bool = False
    position_reset_axis_before: float | None = None
    position_reset_axis_after: float | None = None
    free_initiative_window: bool = False
