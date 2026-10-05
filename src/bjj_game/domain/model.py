from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Mapping


class Side(str, Enum):
    TOP = "top"
    BOTTOM = "bottom"

    @property
    def opponent(self) -> "Side":
        return Side.BOTTOM if self is Side.TOP else Side.TOP


class EntityKind(str, Enum):
    ACTION = "action"
    RESPONSE = "response"


class Grade(IntEnum):
    STRONG_FAILURE = -2
    FAILURE = -1
    CONTESTED = 0
    SUCCESS = 1
    STRONG_SUCCESS = 2

    @property
    def display(self) -> str:
        return {
            Grade.STRONG_FAILURE: "Strong Failure",
            Grade.FAILURE: "Failure",
            Grade.CONTESTED: "Contested",
            Grade.SUCCESS: "Success",
            Grade.STRONG_SUCCESS: "Strong Success",
        }[self]

    @property
    def successful(self) -> bool:
        return self >= Grade.SUCCESS

    @property
    def failed(self) -> bool:
        return self <= Grade.FAILURE

    def shift(self, steps: int) -> "Grade":
        value = max(int(Grade.STRONG_FAILURE), min(int(Grade.STRONG_SUCCESS), int(self) + steps))
        return Grade(value)


class Band(str, Enum):
    LOOSE = "Loose"
    STABLE = "Stable"
    STRONG = "Strong"
    LOCKED = "Locked"

    @property
    def full_display(self) -> str:
        return f"{self.value} Mount"


class TopBehavior(str, Enum):
    PRESSURE = "PRESSURE"
    HOLD = "HOLD"
    CONSERVE = "CONSERVE"

    @property
    def display(self) -> str:
        return {
            TopBehavior.PRESSURE: "Apply Pressure",
            TopBehavior.HOLD: "Hold Position",
            TopBehavior.CONSERVE: "Conserve Energy",
        }[self]


class BottomBehavior(str, Enum):
    ESCAPE = "ESCAPE"
    PROTECT = "PROTECT"
    CONSERVE = "CONSERVE"

    @property
    def display(self) -> str:
        return {
            BottomBehavior.ESCAPE: "Work to Escape",
            BottomBehavior.PROTECT: "Protect / Survive",
            BottomBehavior.CONSERVE: "Conserve Energy",
        }[self]


Behavior = TopBehavior | BottomBehavior


class ExitDestination(str, Enum):
    HALF_GUARD = "Half Guard"
    OPEN_GUARD = "Open Guard"
    REVERSAL = "Reversal"


@dataclass(frozen=True, slots=True)
class TechniqueEntity:
    id: str
    kind: EntityKind
    side: Side
    canonical_name: str
    short_name: str
    legacy_name: str
    aliases: tuple[str, ...]
    category: str
    description: str
    escape_capable: bool = False
    exit_map: Mapping[Grade, ExitDestination] = field(default_factory=dict)
    band_exit_overrides: Mapping[tuple[Grade, Band], ExitDestination] = field(default_factory=dict)
    behavior_modifiers: Mapping[Behavior, int] = field(default_factory=dict)
    clamp_at_mount_floor: bool = False


@dataclass(frozen=True, slots=True)
class BandChange:
    before: Band
    after: Band
    clock_seconds: int | None = None


@dataclass(frozen=True, slots=True)
class DriftResult:
    start_axis: float
    end_axis: float
    total_drift: float
    start_clock: int
    end_clock: int
    start_band: Band
    end_band: Band
    band_changes: tuple[BandChange, ...]


@dataclass(frozen=True, slots=True)
class ResolutionResult:
    initiator: Side
    action_id: str
    response_id: str
    raw_grade: Grade
    behavior_grade: Grade
    final_grade: Grade
    behavior_modifier: int
    positional_modifier: int
    external_grade_modifier: int
    grade_value: int
    axis_before: float
    axis_delta: float
    proposed_axis: float
    axis_after: float
    band_before: Band
    band_after: Band
    band_changes: tuple[BandChange, ...]
    failure_clamp_used: bool
    floor_clamp_used: bool
    escape_threshold_reached: bool
    exit_capable_action: bool
    exit_destination: ExitDestination | None

    @property
    def bridge_clamp_used(self) -> bool:
        """Legacy Mount-v0 name for floor_clamp_used."""
        return self.floor_clamp_used


@dataclass(slots=True)
class RunHistory:
    top_behavior_history: list[str] = field(default_factory=list)
    bottom_behavior_history: list[str] = field(default_factory=list)
    initiated_action_history: list[str] = field(default_factory=list)
    response_history: list[str] = field(default_factory=list)
    raw_grade_history: list[str] = field(default_factory=list)
    modified_grade_history: list[str] = field(default_factory=list)
    commitment_history: list[str] = field(default_factory=list)
    effective_commitment_history: list[str] = field(default_factory=list)
    commitment_initiator_history: list[str] = field(default_factory=list)
    stamina_requested_history: list[int] = field(default_factory=list)
    stamina_charged_history: list[int] = field(default_factory=list)
    stamina_shortfall_history: list[int] = field(default_factory=list)
    stamina_funding_gap_history: list[int] = field(default_factory=list)
    response_requested_commitment_history: list[str] = field(default_factory=list)
    response_effective_commitment_history: list[str] = field(default_factory=list)
    response_stamina_requested_history: list[int] = field(default_factory=list)
    response_stamina_charged_history: list[int] = field(default_factory=list)
    response_stamina_shortfall_history: list[int] = field(default_factory=list)
    response_stamina_funding_gap_history: list[int] = field(default_factory=list)
    response_stamina_waived_history: list[int] = field(default_factory=list)
    initiator_commitment_modifier_history: list[int] = field(default_factory=list)
    response_undercommitment_modifier_history: list[int] = field(default_factory=list)
    recognition_history: list[str] = field(default_factory=list)
    submission_feint_cap_history: list[str] = field(default_factory=list)
    stamina_band_at_initiation_history: list[str] = field(default_factory=list)
    responder_stamina_band_history: list[str] = field(default_factory=list)
    initiator_exhaustion_modifier_history: list[int] = field(default_factory=list)
    responder_exhaustion_modifier_history: list[int] = field(default_factory=list)
    exhaustion_modifier_history: list[int] = field(default_factory=list)
    top_behavior_stamina_history: list[int] = field(default_factory=list)
    bottom_behavior_stamina_history: list[int] = field(default_factory=list)
    reset_window_history: list[str] = field(default_factory=list)
    stalling_progress_opportunity_history: list[str] = field(default_factory=list)
    stalling_progress_engagement_history: list[str] = field(default_factory=list)
    stalling_defensive_engagement_history: list[str] = field(default_factory=list)
    stalling_reset_with_route_history: list[str] = field(default_factory=list)
    stalling_warning_history: list[str] = field(default_factory=list)
    stalling_penalty_history: list[str] = field(default_factory=list)
    stalling_position_reset_history: list[str] = field(default_factory=list)
    stalling_free_initiative_history: list[str] = field(default_factory=list)
    stalling_clock_history: list[str] = field(default_factory=list)
    stalling_boundary_history: list[str] = field(default_factory=list)
    setup_change_history: list[str] = field(default_factory=list)
    setup_consumption_history: list[str] = field(default_factory=list)
    submission_attempt_history: list[str] = field(default_factory=list)
    submission_change_history: list[str] = field(default_factory=list)
    submission_defense_history: list[str] = field(default_factory=list)
    submission_hold_responder_side_history: list[str] = field(default_factory=list)
    submission_hold_nominal_stamina_history: list[int] = field(default_factory=list)
    submission_hold_covered_by_response_history: list[int] = field(default_factory=list)
    submission_hold_stamina_requested_history: list[int] = field(default_factory=list)
    submission_hold_stamina_charged_history: list[int] = field(default_factory=list)
    submission_hold_stamina_shortfall_history: list[int] = field(default_factory=list)
    submission_tap_count: int = 0
    top_initiation_count: int = 0
    bottom_initiation_count: int = 0
    clamp_count: int = 0
    escape_threshold_reached: bool = False
    # D2 v1e opt-in RECOVERY HOLD record; empty on every non-v1e run.
    recovery_hold_history: list[str] = field(default_factory=list)
