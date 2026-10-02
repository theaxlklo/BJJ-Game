"""Legacy Mount-v0 mechanics facade.

Compatibility lives in the legacy package so the main ``bjj_game`` package does
not import back from a Mount-specific compatibility module.
"""

from bjj_game.domain.model import Band, BottomBehavior, Side, TopBehavior
from bjj_game.engine.mount_engine import MOUNT_ENGINE
from bjj_game.positions.mount.rules import (
    DEFAULT_AXIS,
    DEFAULT_CLOCK_SECONDS,
    DEFAULT_INTERVAL_SECONDS,
    DRIFT_RATES,
    DRIFT_TICK_SECONDS,
    MAX_AXIS,
    MIN_AXIS,
    MOUNT_RULES,
)


def clamp_axis(axis: float) -> float:
    return MOUNT_RULES.clamp_axis(axis)


def initial_band(axis: float) -> Band:
    return MOUNT_RULES.initial_band(axis)


def update_band(axis: float, current: Band):
    return MOUNT_RULES.update_band(axis, current)


def axis_can_have_band(axis: float, band: Band) -> bool:
    return MOUNT_RULES.axis_can_have_band(axis, band)


def drift_rate(top_behavior: TopBehavior, bottom_behavior: BottomBehavior) -> float:
    return MOUNT_RULES.drift_rate(top_behavior, bottom_behavior)


def behavior_modifier(
    *,
    initiator: Side,
    action_id: str,
    top_behavior: TopBehavior,
    bottom_behavior: BottomBehavior,
) -> int:
    action = MOUNT_ENGINE.catalog.get(action_id)
    opposing_behavior = bottom_behavior if initiator is Side.TOP else top_behavior
    return MOUNT_RULES.behavior_modifier(action=action, opposing_behavior=opposing_behavior)


def positional_modifier(*, initiator: Side, band: Band) -> int:
    return MOUNT_RULES.positional_modifier(initiator=initiator, band=band)


def simulate_drift(**kwargs):
    return MOUNT_ENGINE.simulate_drift(**kwargs)


def resolve_action(**kwargs):
    return MOUNT_ENGINE.resolve_action(**kwargs)
