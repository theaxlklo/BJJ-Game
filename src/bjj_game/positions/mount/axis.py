from __future__ import annotations

from dataclasses import dataclass

from ...domain.model import Band
from .rules import MOUNT_RULES, MountRuleSet


@dataclass(slots=True)
class MountAxis:
    """Persisted Mount control state.

    The control axis itself is always legal Mount state (+0.10..+4.00). Escape
    overshoot is terminal event data and is stored by MountPosition, never here.
    """

    value: float
    band: Band
    rules: MountRuleSet = MOUNT_RULES

    @classmethod
    def initialize(cls, value: float, rules: MountRuleSet = MOUNT_RULES) -> "MountAxis":
        return cls(value=value, band=rules.initial_band(value), rules=rules)

    def apply(self, value: float, band: Band) -> None:
        if not self.rules.min_axis <= value <= self.rules.max_axis:
            raise ValueError(
                f"Persisted Mount axis must be in [{self.rules.min_axis:.2f}, {self.rules.max_axis:.2f}]"
            )
        if not self.rules.axis_can_have_band(value, band):
            raise ValueError(f"Axis {value:+.2f} cannot legally have visible band {band.value}")
        self.value = round(value, 10)
        self.band = band
