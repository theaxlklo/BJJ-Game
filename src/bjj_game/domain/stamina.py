from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class StaminaBand(str, Enum):
    """Observational stamina bands for Mount v0.1a.

    These bands do not modify resolution in v0.1a. They exist only so stamina
    state has a stable, readable representation before costs/effects are added.
    """

    FRESH = "Fresh"
    WORKING = "Working"
    TIRED = "Tired"
    EXHAUSTED = "Exhausted"


@dataclass(slots=True)
class StaminaPool:
    """Player-owned stamina state.

    v0.1a is telemetry-only: no drift, grade, axis, clamp, or Exit Map rule
    reads this object. Mechanical stamina effects begin in a later v0.1 phase.
    """

    current: int = 100
    maximum: int = 100

    def __post_init__(self) -> None:
        self._validate(self.current)
        if self.maximum <= 0:
            raise ValueError("maximum stamina must be > 0")
        if self.current > self.maximum:
            raise ValueError("current stamina cannot exceed maximum stamina")

    def _validate(self, value: int) -> None:
        if not isinstance(value, int):
            raise TypeError("stamina must be an integer")
        if value < 0:
            raise ValueError("stamina cannot be negative")

    def set_current(self, value: int) -> None:
        self._validate(value)
        if value > self.maximum:
            raise ValueError("current stamina cannot exceed maximum stamina")
        self.current = value

    @property
    def ratio(self) -> float:
        return self.current / self.maximum

    @property
    def band(self) -> StaminaBand:
        # Quartiles are intentionally observational in v0.1a; no mechanic
        # depends on these thresholds yet.
        ratio = self.ratio
        if ratio > 0.75:
            return StaminaBand.FRESH
        if ratio > 0.50:
            return StaminaBand.WORKING
        if ratio > 0.25:
            return StaminaBand.TIRED
        return StaminaBand.EXHAUSTED

    @property
    def display(self) -> str:
        return f"{self.current}/{self.maximum} ({self.band.value})"
