from __future__ import annotations

from dataclasses import dataclass

from ...domain.model import Band, BandChange
from .rules import MOUNT_RULES, MountRuleSet


@dataclass(slots=True)
class MountAxis:
    """Mutable positional authority state for Mount, including visible hysteresis band."""

    value: float
    band: Band
    rules: MountRuleSet = MOUNT_RULES

    @classmethod
    def initialize(cls, value: float, rules: MountRuleSet = MOUNT_RULES) -> "MountAxis":
        return cls(value=value, band=rules.initial_band(value), rules=rules)

    def set_persisted_value(self, value: float) -> tuple[BandChange, ...]:
        self.value = self.rules.clamp_axis(value)
        self.band, changes = self.rules.update_band(self.value, self.band)
        return changes
