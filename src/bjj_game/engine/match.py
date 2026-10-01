from __future__ import annotations

from dataclasses import dataclass, field

from ..domain.competitor import Competitor
from ..domain.model import Band, BottomBehavior, ExitDestination, RunHistory, Side, TopBehavior
from ..positions.mount.catalog import MOUNT_CATALOG
from ..positions.mount.position import MountPosition
from ..positions.mount.rules import DEFAULT_AXIS, DEFAULT_CLOCK_SECONDS, DEFAULT_INTERVAL_SECONDS
from .mount_engine import MOUNT_ENGINE, MountResolutionEngine


@dataclass(slots=True)
class MountMatch:
    """Stateful Mount-v0 match aggregate.

    The match owns competitors, clock, position, initiative and history. Resolution
    math lives in MountResolutionEngine, keeping mutable state separate from rules.
    """

    initial_clock: int = DEFAULT_CLOCK_SECONDS
    starting_axis: float = DEFAULT_AXIS
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS
    engine: MountResolutionEngine = field(default=MOUNT_ENGINE, repr=False)
    clock_seconds: int = field(init=False)
    position: MountPosition = field(init=False)
    initial_band: Band = field(init=False)
    initiator: Side = field(init=False)
    history: RunHistory = field(init=False)
    top: Competitor = field(init=False)
    bottom: Competitor = field(init=False)
    exit_destination: ExitDestination | None = field(init=False, default=None)
    exit_reason: str | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        if self.initial_clock <= 0:
            raise ValueError("clock must be > 0")
        if self.interval_seconds <= 0:
            raise ValueError("interval must be > 0")
        self.clock_seconds = self.initial_clock
        self.position = MountPosition.from_axis(self.starting_axis)
        self.initial_band = self.position.control.band
        self.initiator = Side.TOP
        self.history = RunHistory()
        self.top = Competitor(side=Side.TOP, name="Top")
        self.bottom = Competitor(side=Side.BOTTOM, name="Bottom")

    @property
    def axis(self) -> float:
        return self.position.control.value

    @property
    def band(self) -> Band:
        return self.position.control.band

    @property
    def ended(self) -> bool:
        return self.clock_seconds <= 0 or self.exit_destination is not None

    @property
    def elapsed_simulated_time(self) -> int:
        return self.initial_clock - self.clock_seconds

    @property
    def mount_duration(self) -> int:
        return self.elapsed_simulated_time

    def drift(self, top_behavior: TopBehavior, bottom_behavior: BottomBehavior):
        result = self.engine.simulate_drift(
            axis=self.axis,
            band=self.band,
            clock_seconds=self.clock_seconds,
            duration_seconds=self.interval_seconds,
            top_behavior=top_behavior,
            bottom_behavior=bottom_behavior,
        )
        self.position.control.value = result.end_axis
        self.position.control.band = result.end_band
        self.clock_seconds = result.end_clock
        self.history.top_behavior_history.append(top_behavior.value)
        self.history.bottom_behavior_history.append(bottom_behavior.value)
        if self.clock_seconds == 0 and self.exit_destination is None:
            self.exit_reason = "TIMEOUT — Mount retained"
        return result

    def decide(
        self,
        *,
        action_id: str,
        response_id: str,
        top_behavior: TopBehavior,
        bottom_behavior: BottomBehavior,
    ):
        if self.clock_seconds <= 0:
            raise RuntimeError("Cannot resolve a decision after timeout")
        result = self.engine.resolve_action(
            axis=self.axis,
            band=self.band,
            initiator=self.initiator,
            action_id=action_id,
            response_id=response_id,
            top_behavior=top_behavior,
            bottom_behavior=bottom_behavior,
        )
        self.position.control.value = result.axis_after
        self.position.control.band = result.band_after
        self.history.initiated_action_history.append(action_id)
        self.history.response_history.append(response_id)
        self.history.raw_grade_history.append(result.raw_grade.display)
        self.history.modified_grade_history.append(result.final_grade.display)
        if self.initiator is Side.TOP:
            self.history.top_initiation_count += 1
        else:
            self.history.bottom_initiation_count += 1
        self.history.clamp_count += int(result.failure_clamp_used) + int(result.bridge_clamp_used)
        self.history.escape_threshold_reached |= result.escape_threshold_reached

        if result.exit_destination is not None:
            self.exit_destination = result.exit_destination
            action = MOUNT_CATALOG.get(action_id)
            self.exit_reason = (
                f"{action.canonical_name} reached the escape threshold with final grade "
                f"{result.final_grade.display}"
            )
        else:
            self.initiator = self.initiator.opponent
        return result


# v0 public compatibility name. New code should prefer MountMatch.
MountRun = MountMatch
