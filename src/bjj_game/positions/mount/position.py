from __future__ import annotations

from dataclasses import dataclass

from ..base import Position
from .axis import MountAxis


@dataclass(slots=True)
class MountPosition(Position):
    control: MountAxis

    @property
    def id(self) -> str:
        return "mount"

    @classmethod
    def from_axis(cls, axis: float) -> "MountPosition":
        return cls(control=MountAxis.initialize(axis))
