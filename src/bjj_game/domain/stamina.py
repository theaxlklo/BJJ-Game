from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


class StaminaBand(str, Enum):
    """Stamina bands introduced in Mount v0.1a.

    v0.1e gives only EXHAUSTED a resolution consequence for initiated actions.
    The other bands remain observational.
    """

    FRESH = "Fresh"
    WORKING = "Working"
    TIRED = "Tired"
    EXHAUSTED = "Exhausted"


@dataclass(frozen=True, slots=True)
class StaminaSpend:
    before: int
    requested: int
    charged: int
    shortfall: int
    after: int

    @property
    def fully_paid(self) -> bool:
        return self.shortfall == 0


@dataclass(frozen=True, slots=True)
class StaminaRecovery:
    before: int
    requested: int
    recovered: int
    overflow: int
    after: int


class StaminaPool:
    """Player-owned stamina with controlled mutation and exhaustion hysteresis.

    The current value is read-only to callers. All mutation goes through
    set_current, spend_up_to, or recover_up_to so the Exhausted latch cannot
    be bypassed accidentally.
    """

    __slots__ = ("_current", "_maximum", "_exhausted_latched")

    def __init__(self, current: int = 100, maximum: int = 100) -> None:
        self._validate_value(current, label="stamina")
        if not isinstance(maximum, int):
            raise TypeError("maximum stamina must be an integer")
        if maximum <= 0:
            raise ValueError("maximum stamina must be > 0")
        if current > maximum:
            raise ValueError("current stamina cannot exceed maximum stamina")
        self._maximum = maximum
        self._current = current
        self._exhausted_latched = current <= self.exhaustion_enter_threshold

    @staticmethod
    def _validate_value(value: int, *, label: str) -> None:
        if not isinstance(value, int):
            raise TypeError(f"{label} must be an integer")
        if value < 0:
            raise ValueError(f"{label} cannot be negative")

    @property
    def current(self) -> int:
        return self._current

    @property
    def maximum(self) -> int:
        return self._maximum

    @property
    def exhaustion_enter_threshold(self) -> int:
        return math.floor(self.maximum * 0.25)

    @property
    def exhaustion_recover_threshold(self) -> int:
        return math.ceil(self.maximum * 0.35)

    def _refresh_exhaustion_latch(self) -> None:
        if self._exhausted_latched:
            if self.current >= self.exhaustion_recover_threshold:
                self._exhausted_latched = False
        elif self.current <= self.exhaustion_enter_threshold:
            self._exhausted_latched = True

    def set_current(self, value: int) -> None:
        self._validate_value(value, label="stamina")
        if value > self.maximum:
            raise ValueError("current stamina cannot exceed maximum stamina")
        self._current = value
        self._refresh_exhaustion_latch()

    def spend_up_to(self, requested: int) -> StaminaSpend:
        """Charge as much of a non-negative cost as the pool can currently pay."""
        self._validate_value(requested, label="stamina cost")
        before = self.current
        charged = min(before, requested)
        self._current = before - charged
        self._refresh_exhaustion_latch()
        return StaminaSpend(
            before=before,
            requested=requested,
            charged=charged,
            shortfall=requested - charged,
            after=self.current,
        )

    def recover_up_to(self, requested: int) -> StaminaRecovery:
        self._validate_value(requested, label="stamina recovery")
        before = self.current
        room = self.maximum - before
        recovered = min(room, requested)
        self._current = before + recovered
        self._refresh_exhaustion_latch()
        return StaminaRecovery(
            before=before,
            requested=requested,
            recovered=recovered,
            overflow=requested - recovered,
            after=self.current,
        )

    @property
    def ratio(self) -> float:
        return self.current / self.maximum

    @property
    def band(self) -> StaminaBand:
        if self._exhausted_latched:
            return StaminaBand.EXHAUSTED
        ratio = self.ratio
        if ratio > 0.75:
            return StaminaBand.FRESH
        if ratio > 0.50:
            return StaminaBand.WORKING
        return StaminaBand.TIRED

    @property
    def display(self) -> str:
        if self.band is StaminaBand.EXHAUSTED:
            return (
                f"{self.current}/{self.maximum} "
                f"(Exhausted — recovers at {self.exhaustion_recover_threshold})"
            )
        return f"{self.current}/{self.maximum} ({self.band.value})"
