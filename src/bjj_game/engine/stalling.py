from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ..domain.model import Side


STALLING_THRESHOLD_SECONDS = 20


class StallingConsequence(str, Enum):
    NONE = "NONE"
    WARNING = "WARNING"
    PENALTY = "PENALTY"


@dataclass(frozen=True, slots=True)
class StallingResetEvaluation:
    side: Side
    progress_route_available: bool
    clock_seconds: int
    offense: bool
    consequence: StallingConsequence


@dataclass(slots=True)
class StallingTracker:
    """Per-player simulated-time advancement clocks for v0.3b.

    Engagement resets only the engaging player's clock. Warnings persist for
    the full match. A RESET can become an offense only when a progress-capable
    route exists and the player's clock has reached the fixed time threshold.
    """

    threshold_seconds: int = STALLING_THRESHOLD_SECONDS
    clocks: dict[Side, int] = field(
        default_factory=lambda: {Side.TOP: 0, Side.BOTTOM: 0}
    )
    warned: dict[Side, bool] = field(
        default_factory=lambda: {Side.TOP: False, Side.BOTTOM: False}
    )
    offenses: dict[Side, int] = field(
        default_factory=lambda: {Side.TOP: 0, Side.BOTTOM: 0}
    )

    def __post_init__(self) -> None:
        if self.threshold_seconds <= 0:
            raise ValueError("stalling threshold must be > 0")

    def advance(self, duration_seconds: int) -> None:
        if duration_seconds < 0:
            raise ValueError("stalling clock duration must be >= 0")
        for side in (Side.TOP, Side.BOTTOM):
            self.clocks[side] += duration_seconds

    def engage(self, side: Side) -> None:
        self.clocks[side] = 0

    def clock(self, side: Side) -> int:
        return self.clocks[side]

    def evaluate_reset(
        self,
        *,
        side: Side,
        progress_route_available: bool,
    ) -> StallingResetEvaluation:
        clock_before = self.clocks[side]
        if (
            not progress_route_available
            or clock_before < self.threshold_seconds
        ):
            return StallingResetEvaluation(
                side=side,
                progress_route_available=progress_route_available,
                clock_seconds=clock_before,
                offense=False,
                consequence=StallingConsequence.NONE,
            )

        self.offenses[side] += 1
        if not self.warned[side]:
            self.warned[side] = True
            consequence = StallingConsequence.WARNING
        else:
            consequence = StallingConsequence.PENALTY

        # An adjudicated offense starts a new advancement period. The warning
        # itself persists for the rest of the match.
        self.clocks[side] = 0
        return StallingResetEvaluation(
            side=side,
            progress_route_available=True,
            clock_seconds=clock_before,
            offense=True,
            consequence=consequence,
        )
