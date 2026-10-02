from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
from statistics import mean, median

from ..domain.action import Commitment
from ..domain.model import BottomBehavior, ExitDestination, Side, TopBehavior
from ..domain.stamina import StaminaBand
from ..engine.match import MountMatch
from ..positions.mount.catalog import (
    MODERN_ENTITY_BY_ID,
    TOP_AMERICANA_SUBMISSION_FINISH,
    actions_for,
)
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
    submission_progress_probability: float
    expected_raw_axis: float
    expected_realized_axis: float


class EscapeFirstInitiatorPolicy:
    """Lexicographic batch policy with no terminal-value conversion.

    1. If any action can escape now, choose the highest escape probability.
    2. Otherwise choose the highest positive submission-progress probability.
    3. Otherwise, if v0.2 setup is enabled, choose a setup builder only when
       the unready target would itself have positive tactical value if Ready.
    4. Otherwise, attack for position only when BOTH raw and realized expected
       attacker-axis movement are positive.
    5. Otherwise RESET.

    Tie-breaks are realized axis, then raw axis, then catalog order.
    """

    def _ready_target_has_value(
        self,
        match: MountMatch,
        *,
        builder_action_id: str,
        external_grade_modifier: int,
    ) -> bool:
        target = match.setup_policy.target_for_builder(builder_action_id)
        if target is None:
            return False

        ready_ids = match.setup_policy.ready_response_ids(target)
        if not ready_ids:
            return False
        ready_grade_overrides = {
            response_id: override
            for response_id in ready_ids
            if (
                override := match.setup_policy.ready_final_grade_override(
                    target,
                    response_id,
                )
            ) is not None
        }

        side = match.initiator
        top_behavior = match.top.behavior
        bottom_behavior = match.bottom.behavior
        if not isinstance(top_behavior, TopBehavior):
            raise TypeError("Top behavior is not a TopBehavior")
        if not isinstance(bottom_behavior, BottomBehavior):
            raise TypeError("Bottom behavior is not a BottomBehavior")

        try:
            escape_probability = exact_escape_probability(
                side=side,
                action_id=target,
                axis=match.axis,
                band=match.band,
                top_behavior=top_behavior,
                bottom_behavior=bottom_behavior,
                external_grade_modifier=external_grade_modifier,
                allowed_response_ids=ready_ids,
                ready_grade_overrides=ready_grade_overrides,
            )
            raw_axis = expected_raw_attacker_axis_delta(
                side=side,
                action_id=target,
                axis=match.axis,
                band=match.band,
                top_behavior=top_behavior,
                bottom_behavior=bottom_behavior,
                external_grade_modifier=external_grade_modifier,
                allowed_response_ids=ready_ids,
                ready_grade_overrides=ready_grade_overrides,
            )
            realized_axis = expected_realized_attacker_axis_delta(
                side=side,
                action_id=target,
                axis=match.axis,
                band=match.band,
                top_behavior=top_behavior,
                bottom_behavior=bottom_behavior,
                external_grade_modifier=external_grade_modifier,
                allowed_response_ids=ready_ids,
                ready_grade_overrides=ready_grade_overrides,
            )
        except ValueError:
            return False

        return (
            escape_probability > 0
            or (raw_axis > 0 and realized_axis > 0)
        )

    def _setup_advance_probability(
        self,
        match: MountMatch,
        *,
        action_id: str,
        external_grade_modifier: int,
    ) -> float:
        if not match.enable_v02_setup:
            return 0.0
        target = match.setup_policy.target_for_builder(action_id)
        if target is None or match.setup_state.is_ready(target):
            return 0.0
        if not self._ready_target_has_value(
            match,
            builder_action_id=action_id,
            external_grade_modifier=external_grade_modifier,
        ):
            return 0.0

        side = match.initiator
        top_behavior = match.top.behavior
        bottom_behavior = match.bottom.behavior
        if not isinstance(top_behavior, TopBehavior):
            raise TypeError("Top behavior is not a TopBehavior")
        if not isinstance(bottom_behavior, BottomBehavior):
            raise TypeError("Bottom behavior is not a BottomBehavior")

        allowed = match.legal_response_ids(action_id)
        weighted = RandomBlindResponder.weighted_policy(
            side.opponent,
            allowed_response_ids=allowed,
        )
        total = sum(weight for _, weight in weighted)
        success_weight = 0
        for response_id, weight in weighted:
            result = match.engine.resolve_action(
                axis=match.position.control.value,
                band=match.band,
                initiator=side,
                action_id=action_id,
                response_id=response_id,
                top_behavior=top_behavior,
                bottom_behavior=bottom_behavior,
                external_grade_modifier=external_grade_modifier,
            )
            if match.setup_policy.setup_advances_from(result):
                success_weight += weight
        return success_weight / total

    def _submission_advance_probability(
        self,
        match: MountMatch,
        *,
        action_id: str,
        external_grade_modifier: int,
    ) -> float:
        if (
            not match.enable_v03_submissions
            or action_id != TOP_AMERICANA_SUBMISSION_FINISH
            or not match.submission_state.active
            or match.initiator is not Side.TOP
        ):
            return 0.0

        allowed = match.legal_response_ids(action_id)
        weighted = RandomBlindResponder.weighted_policy(
            Side.BOTTOM,
            allowed_response_ids=allowed,
        )
        total = sum(weight for _, weight in weighted)
        if total <= 0:
            return 0.0
        success_weight = 0
        for response_id, weight in weighted:
            result = match.preview_submission_stage(
                response_id=response_id,
                external_grade_modifier=external_grade_modifier,
            )
            if result.final_grade.successful:
                success_weight += weight
        return success_weight / total

    def choose(self, match: MountMatch) -> BatchDecision:
        side = match.initiator
        top_behavior = match.top.behavior
        bottom_behavior = match.bottom.behavior
        if not isinstance(top_behavior, TopBehavior):
            raise TypeError("Top behavior is not a TopBehavior")
        if not isinstance(bottom_behavior, BottomBehavior):
            raise TypeError("Bottom behavior is not a BottomBehavior")

        stamina_band = match.competitor(side).stamina.band
        responder_stamina_band = match.competitor(side.opponent).stamina.band
        exhaustion_modifier = match.exhaustion_policy.exchange_grade_modifier(
            initiator_band=stamina_band,
            responder_band=responder_stamina_band,
        )

        rows: list[tuple[str, float, float, float, float, float, int]] = []
        candidate_actions = (
            tuple(
                MODERN_ENTITY_BY_ID[action_id]
                for action_id in match.legal_action_ids(side)
            )
            if match.enable_v02_setup
            else actions_for(side)
        )
        for order, action in enumerate(candidate_actions):
            allowed = (
                match.legal_response_ids(action.id)
                if match.enable_v02_setup
                else None
            )
            ready_grade_overrides = (
                {
                    response_id: override
                    for response_id in allowed or ()
                    if (
                        override := match.setup_policy.ready_final_grade_override(
                            action.id,
                            response_id,
                        )
                    ) is not None
                }
                if (
                    match.enable_v02_setup
                    and action.id in match.setup_policy.target_action_ids
                    and match.setup_state.is_ready(action.id)
                )
                else None
            )
            if action.id == TOP_AMERICANA_SUBMISSION_FINISH:
                escape_probability = 0.0
                submission_probability = self._submission_advance_probability(
                    match,
                    action_id=action.id,
                    external_grade_modifier=exhaustion_modifier,
                )
                setup_probability = 0.0
                raw_axis = 0.0
                realized_axis = 0.0
            else:
                escape_probability = exact_escape_probability(
                    side=side,
                    action_id=action.id,
                    axis=match.axis,
                    band=match.band,
                    top_behavior=top_behavior,
                    bottom_behavior=bottom_behavior,
                    external_grade_modifier=exhaustion_modifier,
                    allowed_response_ids=allowed,
                    ready_grade_overrides=ready_grade_overrides,
                )
                submission_probability = 0.0
                setup_probability = self._setup_advance_probability(
                    match,
                    action_id=action.id,
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
                    allowed_response_ids=allowed,
                    ready_grade_overrides=ready_grade_overrides,
                )
                realized_axis = expected_realized_attacker_axis_delta(
                    side=side,
                    action_id=action.id,
                    axis=match.axis,
                    band=match.band,
                    top_behavior=top_behavior,
                    bottom_behavior=bottom_behavior,
                    external_grade_modifier=exhaustion_modifier,
                    allowed_response_ids=allowed,
                    ready_grade_overrides=ready_grade_overrides,
                )
            rows.append(
                (
                    action.id,
                    escape_probability,
                    submission_probability,
                    setup_probability,
                    raw_axis,
                    realized_axis,
                    order,
                )
            )

        escape_rows = [row for row in rows if row[1] > 0]
        if escape_rows:
            row = max(
                escape_rows,
                key=lambda item: (item[1], item[5], item[4], -item[6]),
            )
            return BatchDecision(
                action_id=row[0],
                reason="escape",
                escape_probability=row[1],
                submission_progress_probability=row[2],
                expected_raw_axis=row[4],
                expected_realized_axis=row[5],
            )

        submission_rows = [row for row in rows if row[2] > 0]
        if submission_rows:
            row = max(
                submission_rows,
                key=lambda item: (item[2], item[5], item[4], -item[6]),
            )
            return BatchDecision(
                action_id=row[0],
                reason="submission",
                escape_probability=row[1],
                submission_progress_probability=row[2],
                expected_raw_axis=row[4],
                expected_realized_axis=row[5],
            )

        setup_rows = [row for row in rows if row[3] > 0]
        if setup_rows:
            row = max(
                setup_rows,
                key=lambda item: (item[3], item[5], item[4], -item[6]),
            )
            return BatchDecision(
                action_id=row[0],
                reason="setup",
                escape_probability=row[1],
                submission_progress_probability=row[2],
                expected_raw_axis=row[4],
                expected_realized_axis=row[5],
            )

        positional_rows = [
            row for row in rows if row[4] > 0 and row[5] > 0
        ]
        if positional_rows:
            row = max(
                positional_rows,
                key=lambda item: (item[5], item[4], -item[6]),
            )
            return BatchDecision(
                action_id=row[0],
                reason="position",
                escape_probability=row[1],
                submission_progress_probability=row[2],
                expected_raw_axis=row[4],
                expected_realized_axis=row[5],
            )

        best = max(rows, key=lambda item: (item[5], item[4], -item[6]))
        return BatchDecision(
            action_id=None,
            reason="reset",
            escape_probability=0.0,
            submission_progress_probability=0.0,
            expected_raw_axis=best[4],
            expected_realized_axis=best[5],
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
    top_submission_priority_count: int
    top_submission_attempt_count: int
    matches_reached_submission_threat: int
    matches_reached_submission_control: int
    matches_reached_submission_finish: int
    top_position_attack_count: int
    top_followup_position_attack_count: int
    top_followup_setup_action_count: int
    bottom_position_attack_count: int
    top_setup_action_count: int
    bottom_setup_action_count: int
    top_completed_setup_chain_count: int
    bottom_completed_setup_chain_count: int
    top_completed_setup_build_count: int
    bottom_completed_setup_build_count: int
    top_followup_completed_setup_build_count: int
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
            "Submission rule: positive submission-progress probability before setup/position/RESET",
            "Setup rule: build only when the Ready target has positive tactical value",
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
            f"Top submission-priority attacks: {self.top_submission_priority_count}",
            f"Top submission-stage attempts: {self.top_submission_attempt_count}",
            f"Matches reaching submission Threat: {self.matches_reached_submission_threat}",
            f"Matches reaching submission Control: {self.matches_reached_submission_control}",
            f"Matches reaching submission Finish: {self.matches_reached_submission_finish}",
            f"Top position attacks: {self.top_position_attack_count}",
            f"Top follow-up position attacks: {self.top_followup_position_attack_count}",
            f"Top follow-up setup actions: {self.top_followup_setup_action_count}",
            f"Bottom position attacks: {self.bottom_position_attack_count}",
            f"Top setup-building actions: {self.top_setup_action_count}",
            f"Bottom setup-building actions: {self.bottom_setup_action_count}",
            f"Top completed setup chains: {self.top_completed_setup_chain_count}",
            f"Bottom completed setup chains: {self.bottom_completed_setup_chain_count}",
            f"Top setup builds in completed chains: {self.top_completed_setup_build_count}",
            f"Bottom setup builds in completed chains: {self.bottom_completed_setup_build_count}",
            f"Top follow-up setup builds in completed chains: {self.top_followup_completed_setup_build_count}",
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
    enable_v02_setup: bool = False,
    enable_v03_submissions: bool = False,
) -> BatchSummary:
    if matches <= 0:
        raise ValueError("matches must be > 0")
    if enable_v03_submissions and not enable_v02_setup:
        raise ValueError("v0.3a submissions require v0.2 setup/Ready")

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
    top_submission_priority = 0
    top_submission_attempts = 0
    matches_reached_threat = 0
    matches_reached_control = 0
    matches_reached_finish = 0
    top_position_attacks = 0
    top_followup_position_attacks = 0
    top_followup_setup_actions = 0
    bottom_position_attacks = 0
    top_setup_actions = 0
    bottom_setup_actions = 0
    top_completed_setup_chains = 0
    bottom_completed_setup_chains = 0
    top_completed_setup_builds = 0
    bottom_completed_setup_builds = 0
    top_followup_completed_setup_builds = 0
    top_behavior_windows: Counter[str] = Counter()
    bottom_behavior_windows: Counter[str] = Counter()
    top_behavior_switches = 0
    bottom_behavior_switches = 0

    for match_index in range(matches):
        match = MountMatch(
            initial_clock=initial_clock,
            starting_axis=starting_axis,
            interval_seconds=interval_seconds,
            enable_v02_setup=enable_v02_setup,
            enable_v03_submissions=enable_v03_submissions,
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
        top_has_initiated_action = False
        pending_setup_builds: Counter[tuple[Side, str]] = Counter()
        pending_top_followup_setup_builds: Counter[str] = Counter()

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
            if enable_v02_setup:
                # v0.2 restores established-position ordering:
                # initiator locks action before responder chooses among legal responses.
                decision = policy.choose(match)
                if decision.action_id is None:
                    match.reset_window()
                    if side is Side.TOP:
                        top_resets += 1
                    else:
                        bottom_resets += 1
                    continue
                hidden = responder.choose(
                    side.opponent,
                    allowed_response_ids=match.legal_response_ids(
                        decision.action_id
                    ),
                )
            else:
                # v0.1 blind harness preserves historical responder-first sampling.
                hidden = responder.choose(side.opponent)
                decision = policy.choose(match)
                if decision.action_id is None:
                    match.reset_window()
                    if side is Side.TOP:
                        top_resets += 1
                    else:
                        bottom_resets += 1
                    continue

            action = MODERN_ENTITY_BY_ID[decision.action_id]
            setup_target = (
                match.setup_policy.target_for_builder(action.id)
                if enable_v02_setup
                else None
            )
            target_was_ready = (
                enable_v02_setup
                and action.id in match.setup_policy.target_action_ids
                and match.setup_state.is_ready(action.id)
            )

            if side is Side.TOP:
                top_actions[action.short_name] += 1
                if decision.reason == "escape":
                    top_escape_priority += 1
                elif decision.reason == "submission":
                    top_submission_priority += 1
                    top_submission_attempts += 1
                elif decision.reason == "setup":
                    top_setup_actions += 1
                    if setup_target is not None:
                        pending_setup_builds[(Side.TOP, setup_target)] += 1
                    if top_has_initiated_action:
                        top_followup_setup_actions += 1
                        if setup_target is not None:
                            pending_top_followup_setup_builds[setup_target] += 1
                else:
                    top_position_attacks += 1
                    if top_has_initiated_action:
                        top_followup_position_attacks += 1
                top_has_initiated_action = True
            else:
                bottom_actions[action.short_name] += 1
                if decision.reason == "escape":
                    bottom_escape_priority += 1
                elif decision.reason == "setup":
                    bottom_setup_actions += 1
                    if setup_target is not None:
                        pending_setup_builds[(Side.BOTTOM, setup_target)] += 1
                else:
                    bottom_position_attacks += 1

            match.attempt(
                action_id=decision.action_id,
                response_id=hidden.response_id,
                commitment=commitment,
            )

            if target_was_ready:
                credited = pending_setup_builds[(side, action.id)]
                pending_setup_builds[(side, action.id)] = 0
                if side is Side.TOP:
                    top_completed_setup_chains += 1
                    top_completed_setup_builds += credited
                    top_followup_completed_setup_builds += (
                        pending_top_followup_setup_builds[action.id]
                    )
                    pending_top_followup_setup_builds[action.id] = 0
                else:
                    bottom_completed_setup_chains += 1
                    bottom_completed_setup_builds += credited

        changes = match.history.submission_change_history
        if any("->Threat" in change for change in changes):
            matches_reached_threat += 1
        if any("->Control" in change for change in changes):
            matches_reached_control += 1
        if any("->Finish" in change for change in changes):
            matches_reached_finish += 1

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
        top_submission_priority_count=top_submission_priority,
        top_submission_attempt_count=top_submission_attempts,
        matches_reached_submission_threat=matches_reached_threat,
        matches_reached_submission_control=matches_reached_control,
        matches_reached_submission_finish=matches_reached_finish,
        top_position_attack_count=top_position_attacks,
        top_followup_position_attack_count=top_followup_position_attacks,
        top_followup_setup_action_count=top_followup_setup_actions,
        bottom_position_attack_count=bottom_position_attacks,
        top_setup_action_count=top_setup_actions,
        bottom_setup_action_count=bottom_setup_actions,
        top_completed_setup_chain_count=top_completed_setup_chains,
        bottom_completed_setup_chain_count=bottom_completed_setup_chains,
        top_completed_setup_build_count=top_completed_setup_builds,
        bottom_completed_setup_build_count=bottom_completed_setup_builds,
        top_followup_completed_setup_build_count=top_followup_completed_setup_builds,
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
