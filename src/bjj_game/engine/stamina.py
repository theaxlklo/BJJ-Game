from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from ..domain.action import Commitment
from ..domain.model import Behavior, BottomBehavior, DriftResult, TopBehavior
from ..domain.stamina import StaminaBand, StaminaPool, StaminaRecovery, StaminaSpend


@dataclass(frozen=True, slots=True)
class StaminaCostPolicy:
    """Maps commitment to an action's base stamina request."""

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

    def effective_commitment(
        self,
        *,
        requested: Commitment,
        available_stamina: int,
    ) -> Commitment | None:
        """Return the highest requested-or-lower commitment that can be fully paid."""
        order = (Commitment.LOW, Commitment.MEDIUM, Commitment.HIGH)
        requested_index = order.index(requested)
        for commitment in reversed(order[: requested_index + 1]):
            if self.cost(commitment) <= available_stamina:
                return commitment
        return None


DEFAULT_STAMINA_COST_POLICY = StaminaCostPolicy.build(
    {
        Commitment.LOW: 3,
        Commitment.MEDIUM: 7,
        Commitment.HIGH: 12,
    }
)


@dataclass(slots=True)
class BehaviorStaminaMeter:
    """Fixed-point carry for behavior stamina flow across arbitrary intervals."""

    remainder_units: int = 0


@dataclass(frozen=True, slots=True)
class BehaviorStaminaResult:
    behavior: Behavior
    duration_seconds: int
    quantum_seconds: int
    before: int
    spent: int
    spend_shortfall: int
    recovered: int
    recovery_overflow: int
    after: int
    remainder_before: int
    remainder_after: int

    @property
    def net_change(self) -> int:
        return self.after - self.before


@dataclass(frozen=True, slots=True)
class AdvanceResult:
    drift: DriftResult
    top_stamina: BehaviorStaminaResult
    bottom_stamina: BehaviorStaminaResult


@dataclass(frozen=True, slots=True)
class BehaviorStaminaPolicy:
    """Time-based behavior stamina economy.

    Rates are integer stamina points per quantum_seconds of simulated time.
    Negative values spend stamina; positive values recover it. Fixed-point carry
    makes five 1-second windows equivalent to one 5-second window.
    """

    quantum_seconds: int
    points_per_quantum: Mapping[Behavior, int]

    @classmethod
    def build(
        cls,
        *,
        quantum_seconds: int,
        points_per_quantum: Mapping[Behavior, int],
    ) -> "BehaviorStaminaPolicy":
        if quantum_seconds <= 0:
            raise ValueError("quantum_seconds must be > 0")
        copied = dict(points_per_quantum)
        expected = set(TopBehavior) | set(BottomBehavior)
        if set(copied) != expected:
            raise ValueError("behavior stamina policy must define every behavior")
        if any(not isinstance(value, int) for value in copied.values()):
            raise TypeError("behavior stamina rates must be integers")
        return cls(
            quantum_seconds=quantum_seconds,
            points_per_quantum=MappingProxyType(copied),
        )

    def apply(
        self,
        *,
        pool: StaminaPool,
        behavior: Behavior,
        duration_seconds: int,
        meter: BehaviorStaminaMeter,
    ) -> BehaviorStaminaResult:
        if duration_seconds < 0:
            raise ValueError("duration_seconds must be non-negative")

        before = pool.current
        remainder_before = meter.remainder_units
        units = remainder_before + self.points_per_quantum[behavior] * duration_seconds

        spend = StaminaSpend(
            before=before,
            requested=0,
            charged=0,
            shortfall=0,
            after=before,
        )
        recovery = StaminaRecovery(
            before=before,
            requested=0,
            recovered=0,
            overflow=0,
            after=before,
        )

        if units <= -self.quantum_seconds:
            requested = (-units) // self.quantum_seconds
            units = -((-units) % self.quantum_seconds)
            spend = pool.spend_up_to(requested)
        elif units >= self.quantum_seconds:
            requested = units // self.quantum_seconds
            units = units % self.quantum_seconds
            recovery = pool.recover_up_to(requested)

        meter.remainder_units = units
        return BehaviorStaminaResult(
            behavior=behavior,
            duration_seconds=duration_seconds,
            quantum_seconds=self.quantum_seconds,
            before=before,
            spent=spend.charged,
            spend_shortfall=spend.shortfall,
            recovered=recovery.recovered,
            recovery_overflow=recovery.overflow,
            after=pool.current,
            remainder_before=remainder_before,
            remainder_after=units,
        )


DEFAULT_BEHAVIOR_STAMINA_POLICY = BehaviorStaminaPolicy.build(
    quantum_seconds=5,
    points_per_quantum={
        TopBehavior.PRESSURE: -1,
        TopBehavior.HOLD: 0,
        TopBehavior.CONSERVE: +2,
        BottomBehavior.ESCAPE: -1,
        BottomBehavior.PROTECT: 0,
        BottomBehavior.CONSERVE: +2,
    },
)


@dataclass(frozen=True, slots=True)
class ExhaustionPolicy:
    """Initiator and responder consequences for depleted stamina."""

    exhausted_initiator_grade_modifier: int = -1
    exhausted_responder_grade_modifier: int = +1

    def initiator_grade_modifier(self, band: StaminaBand) -> int:
        return (
            self.exhausted_initiator_grade_modifier
            if band is StaminaBand.EXHAUSTED
            else 0
        )

    def responder_grade_modifier(self, band: StaminaBand) -> int:
        """Shift the initiated action up when the responder is Exhausted."""
        return (
            self.exhausted_responder_grade_modifier
            if band is StaminaBand.EXHAUSTED
            else 0
        )

    def exchange_grade_modifier(
        self,
        *,
        initiator_band: StaminaBand,
        responder_band: StaminaBand,
    ) -> int:
        """Net exhaustion modifier for one initiated exchange."""
        return (
            self.initiator_grade_modifier(initiator_band)
            + self.responder_grade_modifier(responder_band)
        )


DEFAULT_EXHAUSTION_POLICY = ExhaustionPolicy()


@dataclass(frozen=True, slots=True)
class StaminaPacingProjection:
    commitment: Commitment
    top_exhausted_seconds: int
    bottom_exhausted_seconds: int
    top_zero_seconds: int
    bottom_zero_seconds: int


def project_active_stamina_pacing(
    *,
    commitment: Commitment,
    action_policy: StaminaCostPolicy = DEFAULT_STAMINA_COST_POLICY,
    behavior_policy: BehaviorStaminaPolicy = DEFAULT_BEHAVIOR_STAMINA_POLICY,
    starting_stamina: int = 100,
    interval_seconds: int = 5,
    horizon_seconds: int = 300,
) -> StaminaPacingProjection:
    """Project the current v0 scaffold under always-active behavior.

    Both competitors use the active stamina-draining behavior, initiative
    alternates Top/Bottom every interval, and commitment is fixed.
    """

    top = StaminaPool(current=starting_stamina, maximum=starting_stamina)
    bottom = StaminaPool(current=starting_stamina, maximum=starting_stamina)
    top_meter = BehaviorStaminaMeter()
    bottom_meter = BehaviorStaminaMeter()
    exhausted = {"top": None, "bottom": None}
    zero = {"top": None, "bottom": None}
    initiator = "top"
    elapsed = 0

    while elapsed < horizon_seconds and (zero["top"] is None or zero["bottom"] is None):
        elapsed += interval_seconds
        behavior_policy.apply(
            pool=top,
            behavior=TopBehavior.PRESSURE,
            duration_seconds=interval_seconds,
            meter=top_meter,
        )
        behavior_policy.apply(
            pool=bottom,
            behavior=BottomBehavior.ESCAPE,
            duration_seconds=interval_seconds,
            meter=bottom_meter,
        )

        for label, pool in (("top", top), ("bottom", bottom)):
            if exhausted[label] is None and pool.band is StaminaBand.EXHAUSTED:
                exhausted[label] = elapsed
            if zero[label] is None and pool.current == 0:
                zero[label] = elapsed

        pool = top if initiator == "top" else bottom
        effective = action_policy.effective_commitment(
            requested=commitment,
            available_stamina=pool.current,
        )
        if effective is not None:
            pool.spend_up_to(action_policy.cost(effective))

        if exhausted[initiator] is None and pool.band is StaminaBand.EXHAUSTED:
            exhausted[initiator] = elapsed
        if zero[initiator] is None and pool.current == 0:
            zero[initiator] = elapsed

        initiator = "bottom" if initiator == "top" else "top"

    if any(value is None for value in (*exhausted.values(), *zero.values())):
        raise RuntimeError("pacing projection horizon is too short")

    return StaminaPacingProjection(
        commitment=commitment,
        top_exhausted_seconds=int(exhausted["top"]),
        bottom_exhausted_seconds=int(exhausted["bottom"]),
        top_zero_seconds=int(zero["top"]),
        bottom_zero_seconds=int(zero["bottom"]),
    )


@dataclass(frozen=True, slots=True)
class ConserveCycleNet:
    commitment: Commitment
    recovery_per_cycle: int
    action_cost: int
    attack_net: int
    reset_net: int


def conserve_cycle_net(
    commitment: Commitment,
    *,
    action_policy: StaminaCostPolicy = DEFAULT_STAMINA_COST_POLICY,
    behavior_policy: BehaviorStaminaPolicy = DEFAULT_BEHAVIOR_STAMINA_POLICY,
    cycle_seconds: int = 10,
) -> ConserveCycleNet:
    """Nominal stamina balance for pure CONSERVE across one initiative cycle."""
    if cycle_seconds % behavior_policy.quantum_seconds:
        raise ValueError("cycle_seconds must align with the behavior stamina quantum")
    quanta = cycle_seconds // behavior_policy.quantum_seconds
    recovery = (
        behavior_policy.points_per_quantum[TopBehavior.CONSERVE] * quanta
    )
    cost = action_policy.cost(commitment)
    return ConserveCycleNet(
        commitment=commitment,
        recovery_per_cycle=recovery,
        action_cost=cost,
        attack_net=recovery - cost,
        reset_net=recovery,
    )
