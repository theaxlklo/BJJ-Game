from __future__ import annotations

from dataclasses import dataclass, field

from ..domain.competitor import Competitor
from ..domain.model import Band, BottomBehavior, ExitDestination, RunHistory, Side, TopBehavior
from ..positions.mount.position import MountPosition
from ..positions.mount.rules import DEFAULT_AXIS, DEFAULT_CLOCK_SECONDS, DEFAULT_INTERVAL_SECONDS
from .mount_engine import MountResolutionEngine


@dataclass(slots=True)
class MountMatch:
    """Stateful Mount-v0 match aggregate.

    The match owns competitors, clock, position, initiative and history. Resolution
    math lives in MountResolutionEngine, keeping mutable state separate from rules.
    Behaviors are competitor state; optional method arguments remain only for the
    frozen v0 compatibility API and update that state before resolution.
    """

    initial_clock: int = DEFAULT_CLOCK_SECONDS
    starting_axis: float = DEFAULT_AXIS
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS
    engine: MountResolutionEngine = field(default_factory=MountResolutionEngine.default, repr=False)
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
        self.top = Competitor(side=Side.TOP, name="Top", behavior=TopBehavior.PRESSURE)
        self.bottom = Competitor(side=Side.BOTTOM, name="Bottom", behavior=BottomBehavior.ESCAPE)

    @property
    def axis(self) -> float:
        return self.position.reported_axis

    @property
    def band(self) -> Band:
        return self.position.control.band

    @property
    def ended(self) -> bool:
        return self.clock_seconds <= 0 or self.position.broken

    @property
    def elapsed_simulated_time(self) -> int:
        return self.initial_clock - self.clock_seconds

    @property
    def mount_duration(self) -> int:
        return self.elapsed_simulated_time

    def set_behaviors(
        self,
        *,
        top: TopBehavior | None = None,
        bottom: BottomBehavior | None = None,
    ) -> None:
        if top is not None:
            self.top.set_behavior(top)
        if bottom is not None:
            self.bottom.set_behavior(bottom)

    def _behaviors(
        self,
        top_behavior: TopBehavior | None,
        bottom_behavior: BottomBehavior | None,
    ) -> tuple[TopBehavior, BottomBehavior]:
        self.set_behaviors(top=top_behavior, bottom=bottom_behavior)
        if not isinstance(self.top.behavior, TopBehavior):
            raise TypeError("Top competitor behavior is not a TopBehavior")
        if not isinstance(self.bottom.behavior, BottomBehavior):
            raise TypeError("Bottom competitor behavior is not a BottomBehavior")
        return self.top.behavior, self.bottom.behavior

    def drift(
        self,
        top_behavior: TopBehavior | None = None,
        bottom_behavior: BottomBehavior | None = None,
    ):
        top_behavior, bottom_behavior = self._behaviors(top_behavior, bottom_behavior)
        result = self.engine.simulate_drift(
            axis=self.position.control.value,
            band=self.band,
            clock_seconds=self.clock_seconds,
            duration_seconds=self.interval_seconds,
            top_behavior=top_behavior,
            bottom_behavior=bottom_behavior,
        )
        self.position.apply_control(result.end_axis, result.end_band)
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
        top_behavior: TopBehavior | None = None,
        bottom_behavior: BottomBehavior | None = None,
    ):
        if self.clock_seconds <= 0:
            raise RuntimeError("Cannot resolve a decision after timeout")
        if self.position.broken:
            raise RuntimeError("Cannot resolve a decision after Mount is broken")
        top_behavior, bottom_behavior = self._behaviors(top_behavior, bottom_behavior)
        result = self.engine.resolve_action(
            axis=self.position.control.value,
            band=self.band,
            initiator=self.initiator,
            action_id=action_id,
            response_id=response_id,
            top_behavior=top_behavior,
            bottom_behavior=bottom_behavior,
        )
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
            self.position.break_mount(result.axis_after)
            self.exit_destination = result.exit_destination
            action = self.engine.catalog.get(action_id)
            self.exit_reason = (
                f"{action.canonical_name} reached the escape threshold with final grade "
                f"{result.final_grade.display}"
            )
        else:
            self.position.apply_control(result.axis_after, result.band_after)
            self.initiator = self.initiator.opponent
        return result


MountRun = MountMatch
