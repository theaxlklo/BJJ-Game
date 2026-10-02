from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from statistics import mean, median

from ..domain.action import Commitment
from ..domain.model import BottomBehavior, ExitDestination, Side, TopBehavior
from ..domain.stamina import StaminaBand
from ..engine.match import MountMatch
from ..positions.mount.catalog import ENTITY_BY_ID, actions_for
from .blind import RandomBlindResponder, expected_realized_attacker_axis_delta


@dataclass(frozen=True, slots=True)
class GreedyDecision:
    action_id: str | None
    expected_realized_axis: float


class GreedyInitiatorPolicy:
    """Fixed batch policy: attack only when expected realized axis gain is positive."""

    def choose(self, match: MountMatch) -> GreedyDecision:
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

        best_id: str | None = None
        best_value = float("-inf")
        for action in actions_for(side):
            value = expected_realized_attacker_axis_delta(
                side=side,
                action_id=action.id,
                axis=match.axis,
                band=match.band,
                top_behavior=top_behavior,
                bottom_behavior=bottom_behavior,
                external_grade_modifier=exhaustion_modifier,
            )
            if value > best_value:
                best_id = action.id
                best_value = value

        if best_value <= 0:
            return GreedyDecision(action_id=None, expected_realized_axis=best_value)
        return GreedyDecision(action_id=best_id, expected_realized_axis=best_value)


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
            "Initiator policy: greedy realized-axis (>0 attack, otherwise RESET)",
            f"Top behavior: {self.top_behavior.value}",
            f"Bottom behavior: {self.bottom_behavior.value}",
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
            "Top actions: " + _render_counts(self.top_action_counts),
            "Bottom actions: " + _render_counts(self.bottom_action_counts),
        ]
        return "\n".join(lines)


def _render_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{name}={counts[name]}" for name in sorted(counts))


def run_greedy_batch(
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
) -> BatchSummary:
    if matches <= 0:
        raise ValueError("matches must be > 0")

    policy = GreedyInitiatorPolicy()
    outcomes: Counter[str] = Counter()
    top_final: list[int] = []
    bottom_final: list[int] = []
    final_axes: list[float] = []
    top_resets = 0
    bottom_resets = 0
    top_actions: Counter[str] = Counter()
    bottom_actions: Counter[str] = Counter()

    for match_index in range(matches):
        match = MountMatch(
            initial_clock=initial_clock,
            starting_axis=starting_axis,
            interval_seconds=interval_seconds,
        )
        match.top.stamina.set_current(top_stamina)
        match.bottom.stamina.set_current(bottom_stamina)
        match.set_behaviors(top=top_behavior, bottom=bottom_behavior)
        responder = RandomBlindResponder(base_seed + match_index)

        while not match.ended:
            match.advance()
            if match.ended:
                break

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
            else:
                bottom_actions[action.short_name] += 1

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
    )
