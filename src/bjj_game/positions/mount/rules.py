from __future__ import annotations

from dataclasses import dataclass

from ...domain.model import Band, BandChange, BottomBehavior, ExitDestination, Grade, Side, TopBehavior
from .catalog import BOTTOM_BRIDGE, BOTTOM_TRAP_AND_ROLL_ESCAPE, TOP_AMERICANA_ARM_ISOLATION

MIN_AXIS = 0.10
MAX_AXIS = 4.00
DEFAULT_AXIS = 1.50
DEFAULT_CLOCK_SECONDS = 5 * 60
DEFAULT_INTERVAL_SECONDS = 5
DRIFT_TICK_SECONDS = 1

DRIFT_RATES: dict[tuple[TopBehavior, BottomBehavior], float] = {
    (TopBehavior.PRESSURE, BottomBehavior.ESCAPE): +0.10,
    (TopBehavior.PRESSURE, BottomBehavior.PROTECT): +0.15,
    (TopBehavior.HOLD, BottomBehavior.ESCAPE): -0.10,
    (TopBehavior.HOLD, BottomBehavior.PROTECT): 0.00,
}


@dataclass(frozen=True, slots=True)
class MountRuleSet:
    """All frozen Mount-v0 numeric/grade rules in one policy object."""

    min_axis: float = MIN_AXIS
    max_axis: float = MAX_AXIS

    def clamp_axis(self, axis: float) -> float:
        return round(max(self.min_axis, min(self.max_axis, axis)), 10)

    def initial_band(self, axis: float) -> Band:
        if not self.min_axis <= axis <= self.max_axis:
            raise ValueError(f"Mount v0 axis must be in [{self.min_axis:.2f}, {self.max_axis:.2f}]")
        if axis < 1.00:
            return Band.LOOSE
        if axis < 2.00:
            return Band.STABLE
        if axis < 3.00:
            return Band.STRONG
        return Band.LOCKED

    def update_band(self, axis: float, current: Band) -> tuple[Band, tuple[BandChange, ...]]:
        changes: list[BandChange] = []
        band = current
        while True:
            next_band: Band | None = None
            if band is Band.LOOSE and axis >= 1.20:
                next_band = Band.STABLE
            elif band is Band.STABLE and axis >= 2.20:
                next_band = Band.STRONG
            elif band is Band.STRONG and axis >= 3.20:
                next_band = Band.LOCKED
            elif band is Band.LOCKED and axis <= 2.80:
                next_band = Band.STRONG
            elif band is Band.STRONG and axis <= 1.80:
                next_band = Band.STABLE
            elif band is Band.STABLE and axis <= 0.80:
                next_band = Band.LOOSE
            if next_band is None:
                break
            changes.append(BandChange(before=band, after=next_band))
            band = next_band
        return band, tuple(changes)

    def axis_can_have_band(self, axis: float, band: Band) -> bool:
        if not self.min_axis <= axis <= self.max_axis:
            return False
        if band is Band.LOOSE:
            return axis < 1.20
        if band is Band.STABLE:
            return 0.80 < axis < 2.20
        if band is Band.STRONG:
            return 1.80 < axis < 3.20
        return axis > 2.80

    def drift_rate(self, top_behavior: TopBehavior, bottom_behavior: BottomBehavior) -> float:
        return DRIFT_RATES[(top_behavior, bottom_behavior)]

    def behavior_modifier(self, *, initiator: Side, action_id: str, top_behavior: TopBehavior, bottom_behavior: BottomBehavior) -> int:
        if initiator is Side.BOTTOM and top_behavior is TopBehavior.HOLD:
            if action_id in {BOTTOM_BRIDGE, BOTTOM_TRAP_AND_ROLL_ESCAPE}:
                return -1
        if initiator is Side.TOP and bottom_behavior is BottomBehavior.PROTECT:
            if action_id == TOP_AMERICANA_ARM_ISOLATION:
                return -1
        return 0

    def positional_modifier(self, *, initiator: Side, band: Band) -> int:
        if initiator is Side.BOTTOM and band in {Band.STRONG, Band.LOCKED}:
            return -1
        if initiator is Side.TOP and band is Band.LOOSE:
            return -1
        return 0

    def exit_destination(self, *, action, final_grade: Grade, band_before: Band) -> ExitDestination | None:
        return action.band_exit_overrides.get((final_grade, band_before), action.exit_map.get(final_grade))


MOUNT_RULES = MountRuleSet()
