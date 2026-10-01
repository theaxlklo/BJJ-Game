from __future__ import annotations

from ...domain.model import Band, BottomBehavior, Side, TopBehavior
from ...engine.mount_engine import MOUNT_ENGINE
from .rules import (
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


def behavior_modifier(*, initiator: Side, action_id: str, top_behavior: TopBehavior, bottom_behavior: BottomBehavior) -> int:
    return MOUNT_RULES.behavior_modifier(
        initiator=initiator,
        action_id=action_id,
        top_behavior=top_behavior,
        bottom_behavior=bottom_behavior,
    )


def positional_modifier(*, initiator: Side, band: Band) -> int:
    return MOUNT_RULES.positional_modifier(initiator=initiator, band=band)


def simulate_drift(**kwargs):
    return MOUNT_ENGINE.simulate_drift(**kwargs)


def resolve_action(**kwargs):
    return MOUNT_ENGINE.resolve_action(**kwargs)
