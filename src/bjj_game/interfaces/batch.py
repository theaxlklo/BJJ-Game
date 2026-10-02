from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
from statistics import mean, median

from ..domain.action import Commitment
from ..domain.model import BottomBehavior, ExitDestination, Side, TopBehavior
from ..domain.stamina import StaminaBand
from ..engine.match import MountMatch
from ..positions.mount.catalog import ENTITY_BY_ID, actions_for
from .blind import (
    RandomBlindResponder,
    exact_escape_probability,
    expected_raw_attacker_axis_delta,
    expected_realized_attacker_axis_delta,
)


class BatchBehaviorMode(str, Enum):
    FIXED = "fixed"
    RECOVER = "recover"


@dataclass(frozen=True, slots=True)
class AdaptiveBehaviorPolicy:
    """Batch-only behavior switching around the existing Exhausted latch.

    FIXED keeps the baseline behavior for the full match.
    RECOVER uses CONSERVE while the competitor is latched Exhausted, then
    returns to the supplied baseline as soon as the 35-point latch clears.
    """

    side: Side
    baseline: TopBehavior | BottomBehavior
    mode: BatchBehaviorMode = BatchBehaviorMode.FIXED

    def __post_init__(self) -> None:
        if self.side is Side.TOP and not isinstance(self.baseline, TopBehavior):
            raise TypeError("Top adaptive policy requires TopBehavior baseline")
        if self.side is Side.BOTTOM and not isinstance(self.baseline, BottomBehavior):
            raise TypeError("Bottom adaptive policy requires BottomBehavior baseline")

    @property
    def conserve(self) -> TopBehavior | BottomBehavior:
        return (
            TopBehavior.CONSERVE
            if self.side is Side.TOP
            else BottomBehavior.CONSERVE
        )

    def choose(self, match: MountMatch) -> TopBehavior | BottomBehavior:
        if self.mode is BatchBehaviorMode.FIXED:
            return self.baseline
        competitor = match.competitor(self.side)
        return self.conserve if competitor.stamina.band is StaminaBand.EXHAUSTED else self.baseline


@dataclass(frozen=True, slots=True)
class BatchDecision:
    action_id: str | None
    reason: str
    escape_probability: float
    expected_raw_axis: float
    expected_realized_axis: float


class EscapeFirstInitiatorPolicy:
    """Lexicographic batch policy with no terminal-value conversion.

    1. If any action can escape now, choose the highest escape probability.
    2. Otherwise, attack for position only when BOTH raw and realized expected
       attacker-axis movement are positive.
    3. Otherwise RESET.

    Tie-breaks are realized axis, then raw axis, then catalog order.
    """

    def choose(self, match: MountMatch) -> BatchDecision:
        side = match.initiator
        top_behavior = match.top.behavior
        bottom_behavior = match.bottom.behavior
        if not isinstance(top_behavior, TopBehavior):
            raise TypeError("Top behavior is not a TopBehavior")
        if not isinstance(bottom_behavior, BottomBehavior):
            raise TypeError("Bottom behavior is not a BottomBehavior")

        stamina_band = match.competitor(side).stamina.band
        exhaustion_modifier = (
            match.exhaustion_policy.initiator_grade_modifier(stamina_band)
        )

        rows: list[tuple[str, float, float, float, int]] = []
        for order, action in enumerate(actions_for(side)):
            escape_probability = exact_escape_probability(
                side=side,
                action_id=action.id,
                axis=match.axis,
                band=match.band,
                top_behavior=top_behavior,
                bottom_behavior=bottom_behavior,
                external_grade_modifier=exhaustion_modifier,
            )
            raw_axis = expected_raw_attacker_axis_delta(
                side=side,
                action_id=action.id,
                axis=match.axis,
                band=match.band,
                top_behavior=top_behavior,
                bottom_behavior=bottom_behavior,
                external_grade_modifier=exhaustion_modifier,
            )
            realized_axis = expected_realized_attacker_axis_delta(
                side=side,
                action_id=action.id,
                axis=match.axis,
                band=match.band,
                top_behavior=top_behavior,
                bottom_behavior=bottom_behavior,
                external_grade_modifier=exhaustion_modifier,
            )
            rows.append(
                (action.id, escape_probability, raw_axis, realized_axis, order)
            )

        escape_rows = [row for row in rows if row[1] > 0]
        if escape_rows:
            action_id, escape_probability, raw_axis, realized_axis, _ = max(
                escape_rows,
                key=lambda row: (row[1], row[3], row[2], -row[4]),
            )
            return BatchDecision(
                action_id=action_id,
                reason="escape",
                escape_probability=escape_probability,
                expected_raw_axis=raw_axis,
                expected_realized_axis=realized_axis,
            )

        positional_rows = [
            row for row in rows if row[2] > 0 and row[3] > 0
        ]
        if positional_rows:
            action_id, escape_probability, raw_axis, realized_axis, _ = max(
                positional_rows,
                key=lambda row: (row[3], row[2], -row[4]),
            )
            return BatchDecision(
                action_id=action_id,
                reason="position",
                escape_probability=escape_probability,
                expected_raw_axis=raw_axis,
                expected_realized_axis=realized_axis,
            )

        best = max(rows, key=lambda row: (row[3], row[2], -row[4]))
        return BatchDecision(
            action_id=None,
            reason="reset",
            escape_probability=0.0,
            expected_raw_axis=best[2],
            expected_realized_axis=best[3],
        )


@dataclass(frozen=True, slots=True)
class BatchSummary:
    matches: int
    base_seed: int
    top_behavior: TopBehavior
    bottom_behavior: BottomBehavior
    commitment: Commitment
    outcome_counts: dict[str, int]
    top_final_stamina_mean: float
    top_final_stamina_median: float
    bottom_final_stamina_mean: float
    bottom_final_stamina_median: float
    final_axis_mean: float
    top_reset_count: int
    bottom_reset_count: int
    top_action_counts: dict[str, int]
    bottom_action_counts: dict[str, int]
    top_escape_priority_count: int
    bottom_escape_priority_count: int
    top_position_attack_count: int
    bottom_position_attack_count: int
    top_behavior_mode: BatchBehaviorMode
    bottom_behavior_mode: BatchBehaviorMode
    top_behavior_window_counts: dict[str, int]
    bottom_behavior_window_counts: dict[str, int]
    top_behavior_switch_count: int
    bottom_behavior_switch_count: int

    def render(self) -> str:
        ordered_outcomes = [
            ExitDestination.HALF_GUARD.value,
            ExitDestination.OPEN_GUARD.value,
            ExitDestination.REVERSAL.value,
            "TIMEOUT — Mount retained",
        ]
        lines = [
            "BATCH SUMMARY",
            "=============",
            f"Matches: {self.matches}",
            f"Base seed: {self.base_seed}",
            "Per-match seed: base_seed + zero-based match index",
            "Initiator policy: escape-first lexicographic",
            "Escape rule: highest exact escape probability first",
            "Position rule: require raw axis > 0 AND realized axis > 0",
            f"Top baseline behavior: {self.top_behavior.value}",
            f"Top behavior policy: {self.top_behavior_mode.value}",
            f"Bottom baseline behavior: {self.bottom_behavior.value}",
            f"Bottom behavior policy: {self.bottom_behavior_mode.value}",
            f"Commitment: {self.commitment.value}",
            "",
            "OUTCOMES",
        ]
        for outcome in ordered_outcomes:
            count = self.outcome_counts.get(outcome, 0)
            pct = 100.0 * count / self.matches
            lines.append(f"{outcome}: {count}/{self.matches} ({pct:.1f}%)")

        extra = sorted(set(self.outcome_counts) - set(ordered_outcomes))
        for outcome in extra:
            count = self.outcome_counts[outcome]
            pct = 100.0 * count / self.matches
            lines.append(f"{outcome}: {count}/{self.matches} ({pct:.1f}%)")

        lines += [
            "",
            "FINAL STAMINA",
            f"Top mean: {self.top_final_stamina_mean:.2f}",
            f"Top median: {self.top_final_stamina_median:.2f}",
            f"Bottom mean: {self.bottom_final_stamina_mean:.2f}",
            f"Bottom median: {self.bottom_final_stamina_median:.2f}",
            f"Final axis mean: {self.final_axis_mean:+.3f}",
            "",
            "DECISIONS",
            f"Top RESET count: {self.top_reset_count}",
            f"Bottom RESET count: {self.bottom_reset_count}",
            f"Top escape-priority attacks: {self.top_escape_priority_count}",
            f"Bottom escape-priority attacks: {self.bottom_escape_priority_count}",
            f"Top position attacks: {self.top_position_attack_count}",
            f"Bottom position attacks: {self.bottom_position_attack_count}",
            "Top actions: " + _render_counts(self.top_action_counts),
            "Bottom actions: " + _render_counts(self.bottom_action_counts),
            "",
            "BEHAVIOR USAGE",
            "Top windows: " + _render_counts(self.top_behavior_window_counts),
            "Bottom windows: " + _render_counts(self.bottom_behavior_window_counts),
            f"Top behavior switches: {self.top_behavior_switch_count}",
            f"Bottom behavior switches: {self.bottom_behavior_switch_count}",
        ]
        return "\n".join(lines)


def _render_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{name}={counts[name]}" for name in sorted(counts))


def run_escape_first_batch(
    *,
    matches: int,
    base_seed: int,
    top_behavior: TopBehavior,
    bottom_behavior: BottomBehavior,
    commitment: Commitment,
    initial_clock: int,
    starting_axis: float,
    interval_seconds: int,
    top_stamina: int,
    bottom_stamina: int,
    top_behavior_mode: BatchBehaviorMode = BatchBehaviorMode.FIXED,
    bottom_behavior_mode: BatchBehaviorMode = BatchBehaviorMode.FIXED,
) -> BatchSummary:
    if matches <= 0:
        raise ValueError("matches must be > 0")

    policy = EscapeFirstInitiatorPolicy()
    outcomes: Counter[str] = Counter()
    top_final: list[int] = []
    bottom_final: list[int] = []
    final_axes: list[float] = []
    top_resets = 0
    bottom_resets = 0
    top_actions: Counter[str] = Counter()
    bottom_actions: Counter[str] = Counter()
    top_escape_priority = 0
    bottom_escape_priority = 0
    top_position_attacks = 0
    bottom_position_attacks = 0
    top_behavior_windows: Counter[str] = Counter()
    bottom_behavior_windows: Counter[str] = Counter()
    top_behavior_switches = 0
    bottom_behavior_switches = 0

    for match_index in range(matches):
        match = MountMatch(
            initial_clock=initial_clock,
            starting_axis=starting_axis,
            interval_seconds=interval_seconds,
        )
        match.top.stamina.set_current(top_stamina)
        match.bottom.stamina.set_current(bottom_stamina)
        top_policy = AdaptiveBehaviorPolicy(
            side=Side.TOP,
            baseline=top_behavior,
            mode=top_behavior_mode,
        )
        bottom_policy = AdaptiveBehaviorPolicy(
            side=Side.BOTTOM,
            baseline=bottom_behavior,
            mode=bottom_behavior_mode,
        )
        current_top = top_policy.choose(match)
        current_bottom = bottom_policy.choose(match)
        match.set_behaviors(top=current_top, bottom=current_bottom)
        responder = RandomBlindResponder(base_seed + match_index)

        while not match.ended:
            # Choose behavior for the upcoming normal-speed interval.
            next_top = top_policy.choose(match)
            next_bottom = bottom_policy.choose(match)
            if next_top is not current_top:
                top_behavior_switches += 1
                current_top = next_top
            if next_bottom is not current_bottom:
                bottom_behavior_switches += 1
                current_bottom = next_bottom
            match.set_behaviors(top=current_top, bottom=current_bottom)
            top_behavior_windows[current_top.value] += 1
            bottom_behavior_windows[current_bottom.value] += 1

            match.advance()
            if match.ended:
                break

            # If CONSERVE cleared the exhaustion latch during this interval,
            # restore the baseline before action resolution at the decision window.
            post_top = top_policy.choose(match)
            post_bottom = bottom_policy.choose(match)
            if post_top is not current_top:
                top_behavior_switches += 1
                current_top = post_top
            if post_bottom is not current_bottom:
                bottom_behavior_switches += 1
                current_bottom = post_bottom
            match.set_behaviors(top=current_top, bottom=current_bottom)

            side = match.initiator
            hidden = responder.choose(side.opponent)
            decision = policy.choose(match)
            if decision.action_id is None:
                match.reset_window()
                if side is Side.TOP:
                    top_resets += 1
                else:
                    bottom_resets += 1
                continue

            action = ENTITY_BY_ID[decision.action_id]
            if side is Side.TOP:
                top_actions[action.short_name] += 1
                if decision.reason == "escape":
                    top_escape_priority += 1
                else:
                    top_position_attacks += 1
            else:
                bottom_actions[action.short_name] += 1
                if decision.reason == "escape":
                    bottom_escape_priority += 1
                else:
                    bottom_position_attacks += 1

            match.attempt(
                action_id=decision.action_id,
                response_id=hidden.response_id,
                commitment=commitment,
            )

        outcome = (
            match.exit_destination.value
            if match.exit_destination is not None
            else match.exit_reason or "UNKNOWN"
        )
        outcomes[outcome] += 1
        top_final.append(match.top.stamina.current)
        bottom_final.append(match.bottom.stamina.current)
        final_axes.append(match.axis)

    return BatchSummary(
        matches=matches,
        base_seed=base_seed,
        top_behavior=top_behavior,
        bottom_behavior=bottom_behavior,
        commitment=commitment,
        outcome_counts=dict(outcomes),
        top_final_stamina_mean=mean(top_final),
        top_final_stamina_median=median(top_final),
        bottom_final_stamina_mean=mean(bottom_final),
        bottom_final_stamina_median=median(bottom_final),
        final_axis_mean=mean(final_axes),
        top_reset_count=top_resets,
        bottom_reset_count=bottom_resets,
        top_action_counts=dict(top_actions),
        bottom_action_counts=dict(bottom_actions),
        top_escape_priority_count=top_escape_priority,
        bottom_escape_priority_count=bottom_escape_priority,
        top_position_attack_count=top_position_attacks,
        bottom_position_attack_count=bottom_position_attacks,
        top_behavior_mode=top_behavior_mode,
        bottom_behavior_mode=bottom_behavior_mode,
        top_behavior_window_counts=dict(top_behavior_windows),
        bottom_behavior_window_counts=dict(bottom_behavior_windows),
        top_behavior_switch_count=top_behavior_switches,
        bottom_behavior_switch_count=bottom_behavior_switches,
    )


def run_greedy_batch(**kwargs) -> BatchSummary:
    """Compatibility alias for the pre-v0.1e batch function name.

    The official batch policy is now escape-first lexicographic.
    """
    return run_escape_first_batch(**kwargs)
