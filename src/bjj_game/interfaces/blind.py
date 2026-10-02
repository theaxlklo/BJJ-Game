from __future__ import annotations

import random
from dataclasses import dataclass

from ..domain.model import Band, BottomBehavior, ExitDestination, Side, TechniqueEntity, TopBehavior
from ..engine.mount_engine import MOUNT_ENGINE
from ..positions.mount.rules import MOUNT_RULES
from ..positions.mount.catalog import (
    BOTTOM_RESPONSE_FOREARM_FRAME,
    BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE,
    TOP_RESPONSE_HIP_FOLLOW_REPUMMEL,
    TOP_RESPONSE_WIDE_MOUNT_BASE,
    ENTITY_BY_ID,
    actions_for,
)


@dataclass(frozen=True, slots=True)
class BlindResponseChoice:
    ordinal: int
    responder: Side
    response_id: str
    draw: int
    total_weight: int

    @property
    def response(self) -> TechniqueEntity:
        return ENTITY_BY_ID[self.response_id]


class RandomBlindResponder:
    """Deterministic solo responder for blind hot-seat playtests.

    The fixed mixes come from the raw simultaneous-game analysis used to seed
    v0.1e playtests. Zero-weight responses are deliberately absent.
    """

    POLICY: dict[Side, tuple[tuple[str, int], ...]] = {
        Side.BOTTOM: (
            (BOTTOM_RESPONSE_FOREARM_FRAME, 4),
            (BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE, 3),
        ),
        Side.TOP: (
            (TOP_RESPONSE_WIDE_MOUNT_BASE, 2),
            (TOP_RESPONSE_HIP_FOLLOW_REPUMMEL, 1),
        ),
    }

    def __init__(self, seed: int) -> None:
        self.seed = seed
        self._rng = random.Random(seed)
        self._ordinal = 0

    @classmethod
    def mix_description(cls, side: Side) -> str:
        parts = []
        for response_id, weight in cls.POLICY[side]:
            response = ENTITY_BY_ID[response_id]
            parts.append(f"{response.short_name}={weight}")
        return ", ".join(parts)

    def choose(self, responder: Side) -> BlindResponseChoice:
        weighted = self.POLICY[responder]
        total = sum(weight for _, weight in weighted)
        draw = self._rng.randrange(total)

        cursor = 0
        selected_id = weighted[-1][0]
        for response_id, weight in weighted:
            cursor += weight
            if draw < cursor:
                selected_id = response_id
                break

        self._ordinal += 1
        return BlindResponseChoice(
            ordinal=self._ordinal,
            responder=responder,
            response_id=selected_id,
            draw=draw,
            total_weight=total,
        )


@dataclass(frozen=True, slots=True)
class BlindMixBandMetric:
    side: Side
    band: Band
    action_id: str
    expected_attacker_axis_delta: float
    realized_attacker_axis_delta_min: float
    realized_attacker_axis_delta_max: float
    escape_probability_min: float
    escape_probability_max: float

    @property
    def action(self) -> TechniqueEntity:
        return ENTITY_BY_ID[self.action_id]


_BAND_ANCHOR = {
    Band.LOOSE: 0.50,
    Band.STABLE: 1.50,
    Band.STRONG: 2.50,
    Band.LOCKED: 3.50,
}


def _axis_grid() -> tuple[float, ...]:
    return tuple(round(i / 100, 2) for i in range(10, 401))


def expected_raw_attacker_axis_delta(
    *,
    side: Side,
    action_id: str,
    axis: float,
    band: Band,
    top_behavior: TopBehavior = TopBehavior.PRESSURE,
    bottom_behavior: BottomBehavior = BottomBehavior.ESCAPE,
    external_grade_modifier: int = 0,
) -> float:
    """Expected grade-derived axis delta before floor/cap/escape handling."""
    response_policy = RandomBlindResponder.POLICY[side.opponent]
    total_weight = sum(weight for _, weight in response_policy)
    weighted = 0.0
    for response_id, weight in response_policy:
        result = MOUNT_ENGINE.resolve_action(
            axis=axis,
            band=band,
            initiator=side,
            action_id=action_id,
            response_id=response_id,
            top_behavior=top_behavior,
            bottom_behavior=bottom_behavior,
            external_grade_modifier=external_grade_modifier,
        )
        weighted += result.grade_value * weight
    return weighted / total_weight


def exact_escape_probability(
    *,
    side: Side,
    action_id: str,
    axis: float,
    band: Band,
    top_behavior: TopBehavior = TopBehavior.PRESSURE,
    bottom_behavior: BottomBehavior = BottomBehavior.ESCAPE,
    external_grade_modifier: int = 0,
) -> float:
    """Exact escape probability at one state under the fixed blind response mix."""
    response_policy = RandomBlindResponder.POLICY[side.opponent]
    total_weight = sum(weight for _, weight in response_policy)
    escaped_weight = 0
    for response_id, weight in response_policy:
        result = MOUNT_ENGINE.resolve_action(
            axis=axis,
            band=band,
            initiator=side,
            action_id=action_id,
            response_id=response_id,
            top_behavior=top_behavior,
            bottom_behavior=bottom_behavior,
            external_grade_modifier=external_grade_modifier,
        )
        if result.exit_destination is not None:
            escaped_weight += weight
    return escaped_weight / total_weight


def expected_realized_attacker_axis_delta(
    *,
    side: Side,
    action_id: str,
    axis: float,
    band: Band,
    top_behavior: TopBehavior = TopBehavior.PRESSURE,
    bottom_behavior: BottomBehavior = BottomBehavior.ESCAPE,
    external_grade_modifier: int = 0,
) -> float:
    """Expected actual axis movement after floor/cap/escape resolution.

    Positive values favor the initiator. Escape crossings use the resolver's
    crossing axis; non-escape results use the persisted clamped axis.
    """
    response_policy = RandomBlindResponder.POLICY[side.opponent]
    total_weight = sum(weight for _, weight in response_policy)
    weighted = 0.0
    for response_id, weight in response_policy:
        result = MOUNT_ENGINE.resolve_action(
            axis=axis,
            band=band,
            initiator=side,
            action_id=action_id,
            response_id=response_id,
            top_behavior=top_behavior,
            bottom_behavior=bottom_behavior,
            external_grade_modifier=external_grade_modifier,
        )
        world_delta = result.axis_after - axis
        attacker_delta = world_delta if side is Side.TOP else -world_delta
        weighted += attacker_delta * weight
    return weighted / total_weight


def random_mix_band_metrics() -> tuple[BlindMixBandMetric, ...]:
    """Report separate axis and escape signals under the fixed blind mix.

    Baseline behaviors are PRESSURE for Top and ESCAPE for Bottom, with no
    exhaustion modifier. Axis delta is the final grade value from the
    initiator's perspective before floor/cap/escape clamping. Escape chance is
    reported as a min/max over all 0.01-grid axis values compatible with the
    visible band.
    """

    rows: list[BlindMixBandMetric] = []
    for side in (Side.TOP, Side.BOTTOM):
        response_policy = RandomBlindResponder.POLICY[side.opponent]
        total_weight = sum(weight for _, weight in response_policy)
        for band in Band:
            anchor = _BAND_ANCHOR[band]
            for action in actions_for(side):
                weighted_grade = 0
                for response_id, weight in response_policy:
                    result = MOUNT_ENGINE.resolve_action(
                        axis=anchor,
                        band=band,
                        initiator=side,
                        action_id=action.id,
                        response_id=response_id,
                        top_behavior=TopBehavior.PRESSURE,
                        bottom_behavior=BottomBehavior.ESCAPE,
                    )
                    weighted_grade += result.grade_value * weight

                probabilities: list[float] = []
                realized_axis_deltas: list[float] = []
                for axis in _axis_grid():
                    if not MOUNT_RULES.axis_can_have_band(axis, band):
                        continue
                    escaped_weight = 0
                    realized_axis_deltas.append(
                        expected_realized_attacker_axis_delta(
                            side=side,
                            action_id=action.id,
                            axis=axis,
                            band=band,
                        )
                    )
                    for response_id, weight in response_policy:
                        result = MOUNT_ENGINE.resolve_action(
                            axis=axis,
                            band=band,
                            initiator=side,
                            action_id=action.id,
                            response_id=response_id,
                            top_behavior=TopBehavior.PRESSURE,
                            bottom_behavior=BottomBehavior.ESCAPE,
                        )
                        if result.exit_destination is not None:
                            escaped_weight += weight
                    probabilities.append(escaped_weight / total_weight)

                rows.append(
                    BlindMixBandMetric(
                        side=side,
                        band=band,
                        action_id=action.id,
                        expected_attacker_axis_delta=weighted_grade / total_weight,
                        realized_attacker_axis_delta_min=min(realized_axis_deltas, default=0.0),
                        realized_attacker_axis_delta_max=max(realized_axis_deltas, default=0.0),
                        escape_probability_min=min(probabilities, default=0.0),
                        escape_probability_max=max(probabilities, default=0.0),
                    )
                )
    return tuple(rows)


def render_random_mix_band_metrics(*, action_cost: int = 7) -> tuple[str, ...]:
    rows = random_mix_band_metrics()
    lines: list[str] = [
        (
            "BLIND MIX BAND METRICS: baseline PRESSURE/ESCAPE, no exhaustion; "
            f"action cost MEDIUM={action_cost}; raw grade-axis, realized post-clamp "
            "axis range, and escape are reported separately."
        )
    ]
    for row in rows:
        escape = (
            f"{row.escape_probability_min * 100:.1f}%"
            if row.escape_probability_min == row.escape_probability_max
            else (
                f"{row.escape_probability_min * 100:.1f}%.."
                f"{row.escape_probability_max * 100:.1f}%"
            )
        )
        lines.append(
            f"BLIND MIX: {row.side.value.title()} / {row.band.value} / "
            f"{row.action.short_name}: raw attacker-axis "
            f"{row.expected_attacker_axis_delta:+.3f}; realized-axis "
            f"{row.realized_attacker_axis_delta_min:+.3f}.."
            f"{row.realized_attacker_axis_delta_max:+.3f}; escape {escape}"
        )

    for side in (Side.TOP, Side.BOTTOM):
        for band in Band:
            group = [row for row in rows if row.side is side and row.band is band]
            best_value = max(row.expected_attacker_axis_delta for row in group)
            best = ", ".join(
                row.action.short_name
                for row in group
                if abs(row.expected_attacker_axis_delta - best_value) < 1e-12
            )
            below_reset = ", ".join(
                row.action.short_name
                for row in group
                if row.expected_attacker_axis_delta < 0
            ) or "none"
            lines.append(
                f"BLIND MIX SUMMARY: {side.value.title()} / {band.value}: "
                f"best attacker-axis {best_value:+.3f} via {best}; "
                f"negative-vs-RESET-axis={below_reset}"
            )
    return tuple(lines)


def random_mix_reachable_exits() -> frozenset[ExitDestination]:
    """Exit destinations reachable against positive-weight responses."""
    reachable: set[ExitDestination] = set()
    for action in actions_for(Side.BOTTOM):
        for band in Band:
            for axis in _axis_grid():
                if not MOUNT_RULES.axis_can_have_band(axis, band):
                    continue
                for response_id, weight in RandomBlindResponder.POLICY[Side.TOP]:
                    if weight <= 0:
                        continue
                    result = MOUNT_ENGINE.resolve_action(
                        axis=axis,
                        band=band,
                        initiator=Side.BOTTOM,
                        action_id=action.id,
                        response_id=response_id,
                        top_behavior=TopBehavior.PRESSURE,
                        bottom_behavior=BottomBehavior.ESCAPE,
                    )
                    if result.exit_destination is not None:
                        reachable.add(result.exit_destination)
    return frozenset(reachable)


def render_random_mix_exit_limit() -> str:
    reachable = random_mix_reachable_exits()
    missing = [destination.value for destination in ExitDestination if destination not in reachable]
    if not missing:
        return "BATCH RESPONSE MIX LIMIT: all current Exit Map destinations are reachable."
    return (
        "BATCH RESPONSE MIX LIMIT: unreachable under the fixed positive-weight "
        "response mix: " + ", ".join(missing)
    )
