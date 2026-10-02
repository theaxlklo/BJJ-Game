from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from ..domain.action import Commitment


@dataclass(frozen=True, slots=True)
class StaminaCostPolicy:
    """Maps commitment to an action's base stamina request.

    v0.1b intentionally has no technique-specific multipliers. The policy is a
    separate injected object so later tuning cannot leak into the BJJ matchup table.
    """

    costs: Mapping[Commitment, int]

    @classmethod
    def build(cls, costs: Mapping[Commitment, int]) -> "StaminaCostPolicy":
        copied = dict(costs)
        if set(copied) != set(Commitment):
            raise ValueError("stamina cost policy must define every commitment")
        if any(not isinstance(value, int) or value < 0 for value in copied.values()):
            raise ValueError("stamina costs must be non-negative integers")
        if not (
            copied[Commitment.LOW]
            < copied[Commitment.MEDIUM]
            < copied[Commitment.HIGH]
        ):
            raise ValueError("commitment costs must increase LOW < MEDIUM < HIGH")
        return cls(MappingProxyType(copied))

    def cost(self, commitment: Commitment) -> int:
        return self.costs[commitment]


DEFAULT_STAMINA_COST_POLICY = StaminaCostPolicy.build(
    {
        Commitment.LOW: 3,
        Commitment.MEDIUM: 7,
        Commitment.HIGH: 12,
    }
)
