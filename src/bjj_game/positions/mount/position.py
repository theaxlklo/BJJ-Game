from __future__ import annotations

from dataclasses import dataclass

from ...domain.model import Band
from ..base import Position
from .axis import MountAxis


@dataclass(slots=True)
class MountPosition(Position):
    control: MountAxis
    broken: bool = False
    crossing_axis: float | None = None

    @property
    def id(self) -> str:
        return "mount"

    @classmethod
    def from_axis(cls, axis: float) -> "MountPosition":
        return cls(control=MountAxis.initialize(axis))

    @property
    def reported_axis(self) -> float:
        """Compatibility/reporting value.

        While Mount exists this is the persisted control axis. Once an escape
        breaks Mount, the terminal crossing value is retained for logs/results,
        while control remains the last valid Mount state.
        """
        return self.crossing_axis if self.broken and self.crossing_axis is not None else self.control.value

    def apply_control(self, value: float, band: Band) -> None:
        if self.broken:
            raise RuntimeError("Cannot update Mount control after Mount is broken")
        self.control.apply(value, band)

    def break_mount(self, crossing_axis: float) -> None:
        self.broken = True
        self.crossing_axis = crossing_axis
