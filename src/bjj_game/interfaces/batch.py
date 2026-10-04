from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import random
from enum import Enum
from statistics import mean, median

from ..domain.action import Commitment
from ..domain.model import Band, BottomBehavior, ExitDestination, Grade, Side, TopBehavior
from ..domain.recognition import CommitmentRecognitionRead
from ..domain.stamina import StaminaBand
from ..domain.submission import SubmissionStage
from ..engine.match import MountMatch
from ..engine.stamina import DEFAULT_BEHAVIOR_STAMINA_POLICY
from .stamina_economy import (
    StaminaEconomyCollector,
    StaminaEconomyMeasurement,
)
from .recovery_policy import (
    RecoveryInitiationMode,
    RecoveryPolicyCollector,
    RecoveryPolicyMeasurement,
)
from ..positions.mount.catalog import (
    MODERN_ENTITY_BY_ID,
    TOP_AMERICANA_ARM_ISOLATION,
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


class BatchResponderMode(str, Enum):
    RANDOM = "random"
    INFORMED = "informed"


class BatchResponseCommitmentMode(str, Enum):
    FIXED_MEDIUM = "fixed-medium"
    MATCH = "match"
    RANDOM = "random"
    RECOGNITION = "recognition"
    RECOGNITION_HEDGE_ONE = "recognition-hedge-one"
    RECOGNITION_ALWAYS_HIGH = "recognition-always-high"


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

    @staticmethod
    def _ready_fallback_response_id(
        match: MountMatch,
        action_id: str,
    ) -> str | None:
        if not match.enable_v02_setup:
            return None
        if (
            action_id == TOP_AMERICANA_SUBMISSION_FINISH
            and match.enable_v03_submissions
            and match.submission_state.active
        ):
            rule = match.setup_policy.rule_for_target(
                TOP_AMERICANA_ARM_ISOLATION
            )
            return rule.stalemate_response_id if rule is not None else None
        if not match.setup_state.is_ready(action_id):
            return None
        rule = match.setup_policy.rule_for_target(action_id)
        return rule.stalemate_response_id if rule is not None else None

    def _submission_entry_probability(
        self,
        match: MountMatch,
        *,
        action_id: str,
        external_grade_modifier: int,
        allowed_response_ids: tuple[str, ...],
        fallback_response_id: str | None = None,
        ready_grade_overrides: dict[str, Grade] | None = None,
    ) -> float:
        """Exact probability that Ready Americana enters the submission track.

        This is terminal-route probability, not converted axis value. It may be
        evaluated prospectively for an unready setup target by supplying the
        target's eventual Ready response set and grade overrides.
        """
        if (
            not match.enable_v03_submissions
            or match.initiator is not Side.TOP
            or action_id != TOP_AMERICANA_ARM_ISOLATION
            or match.band not in {Band.STRONG, Band.LOCKED}
        ):
            return 0.0

        weighted = RandomBlindResponder.weighted_policy(
            Side.BOTTOM,
            allowed_response_ids=allowed_response_ids,
            fallback_response_id=fallback_response_id,
        )
        total = sum(weight for _, weight in weighted)
        if total <= 0:
            return 0.0

        top_behavior = match.top.behavior
        bottom_behavior = match.bottom.behavior
        if not isinstance(top_behavior, TopBehavior):
            raise TypeError("Top behavior is not a TopBehavior")
        if not isinstance(bottom_behavior, BottomBehavior):
            raise TypeError("Bottom behavior is not a BottomBehavior")

        overrides = ready_grade_overrides or {}
        success_weight = 0
        for response_id, weight in weighted:
            result = match.engine.resolve_action(
                axis=match.axis,
                band=match.band,
                initiator=Side.TOP,
                action_id=action_id,
                response_id=response_id,
                top_behavior=top_behavior,
                bottom_behavior=bottom_behavior,
                external_grade_modifier=external_grade_modifier,
                post_positional_grade_override=overrides.get(response_id),
            )
            if result.final_grade.successful:
                success_weight += weight
        return success_weight / total

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
        rule = match.setup_policy.rule_for_target(target)
        ready_fallback_response_id = (
            rule.stalemate_response_id if rule is not None else None
        )
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
                fallback_response_id=ready_fallback_response_id,
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
                fallback_response_id=ready_fallback_response_id,
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
                fallback_response_id=ready_fallback_response_id,
                ready_grade_overrides=ready_grade_overrides,
            )
        except ValueError:
            return False

        submission_entry_probability = self._submission_entry_probability(
            match,
            action_id=target,
            external_grade_modifier=external_grade_modifier,
            allowed_response_ids=ready_ids,
            fallback_response_id=ready_fallback_response_id,
            ready_grade_overrides=ready_grade_overrides,
        )
        return (
            submission_entry_probability > 0
            or escape_probability > 0
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

    def _submission_progress_probability(
        self,
        match: MountMatch,
        *,
        action_id: str,
        external_grade_modifier: int,
    ) -> float:
        if not match.enable_v03_submissions or match.initiator is not Side.TOP:
            return 0.0

        if (
            action_id == TOP_AMERICANA_SUBMISSION_FINISH
            and match.submission_state.active
        ):
            allowed = match.legal_response_ids(action_id)
            weighted = RandomBlindResponder.weighted_policy(
                Side.BOTTOM,
                allowed_response_ids=allowed,
                fallback_response_id=self._ready_fallback_response_id(
                    match,
                    action_id,
                ),
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

        if (
            action_id == TOP_AMERICANA_ARM_ISOLATION
            and match.setup_state.is_ready(action_id)
        ):
            allowed = match.legal_response_ids(action_id)
            ready_grade_overrides = {
                response_id: override
                for response_id in allowed
                if (
                    override := match.setup_policy.ready_final_grade_override(
                        action_id,
                        response_id,
                    )
                ) is not None
            }
            return self._submission_entry_probability(
                match,
                action_id=action_id,
                external_grade_modifier=external_grade_modifier,
                allowed_response_ids=allowed,
                fallback_response_id=self._ready_fallback_response_id(
                    match,
                    action_id,
                ),
                ready_grade_overrides=ready_grade_overrides,
            )

        return 0.0

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
            ready_fallback_response_id = self._ready_fallback_response_id(
                match,
                action.id,
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
                submission_probability = self._submission_progress_probability(
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
                    fallback_response_id=ready_fallback_response_id,
                    ready_grade_overrides=ready_grade_overrides,
                )
                submission_probability = self._submission_progress_probability(
                    match,
                    action_id=action.id,
                    external_grade_modifier=exhaustion_modifier,
                )
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
                    fallback_response_id=ready_fallback_response_id,
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
                    fallback_response_id=ready_fallback_response_id,
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


class HandoffEpisodeStatus(str, Enum):
    REEXHAUSTED_WITHIN_HORIZON = "reexhausted-within-horizon"
    SURVIVED_THROUGH_HORIZON = "survived-through-horizon"
    RIGHT_CENSORED = "right-censored"


@dataclass(frozen=True, slots=True)
class ReExhaustionHandoffEpisode:
    match_index: int
    clear_elapsed_seconds: int
    reexhausted_elapsed_seconds: int | None
    match_end_elapsed_seconds: int

    def __post_init__(self) -> None:
        if self.clear_elapsed_seconds < 0:
            raise ValueError("clear_elapsed_seconds must be >= 0")
        if self.match_end_elapsed_seconds < self.clear_elapsed_seconds:
            raise ValueError("match end cannot precede clear")
        if (
            self.reexhausted_elapsed_seconds is not None
            and self.reexhausted_elapsed_seconds < self.clear_elapsed_seconds
        ):
            raise ValueError("re-exhaustion cannot precede clear")
        if (
            self.reexhausted_elapsed_seconds is not None
            and self.reexhausted_elapsed_seconds > self.match_end_elapsed_seconds
        ):
            raise ValueError("re-exhaustion cannot occur after match end")

    @property
    def seconds_to_reexhaustion(self) -> int | None:
        if self.reexhausted_elapsed_seconds is None:
            return None
        return self.reexhausted_elapsed_seconds - self.clear_elapsed_seconds

    def status_at(self, horizon_seconds: int) -> HandoffEpisodeStatus:
        if horizon_seconds <= 0:
            raise ValueError("horizon_seconds must be > 0")

        seconds_to_reexhaustion = self.seconds_to_reexhaustion
        if (
            seconds_to_reexhaustion is not None
            and seconds_to_reexhaustion <= horizon_seconds
        ):
            return HandoffEpisodeStatus.REEXHAUSTED_WITHIN_HORIZON

        observed_seconds = (
            self.match_end_elapsed_seconds - self.clear_elapsed_seconds
        )
        if observed_seconds >= horizon_seconds:
            return HandoffEpisodeStatus.SURVIVED_THROUGH_HORIZON
        return HandoffEpisodeStatus.RIGHT_CENSORED


@dataclass(frozen=True, slots=True)
class ReExhaustionHandoffMeasurement:
    episodes: tuple[ReExhaustionHandoffEpisode, ...]


class ReExhaustionHandoffObserver:
    """Read-only Bottom Exhausted clear/re-exhaustion episode observer."""

    def __init__(self) -> None:
        self._episodes: list[ReExhaustionHandoffEpisode] = []
        self._match_index: int | None = None
        self._previous_exhausted: bool | None = None
        self._current_episodes: list[list[int | None]] = []
        self._last_elapsed_seconds: int | None = None

    def start_match(
        self,
        *,
        match_index: int,
        elapsed_seconds: int,
        bottom_exhausted: bool,
    ) -> None:
        if self._match_index is not None:
            raise RuntimeError("re-exhaustion handoff match already active")
        if elapsed_seconds < 0:
            raise ValueError("elapsed_seconds must be >= 0")
        self._match_index = match_index
        self._previous_exhausted = bottom_exhausted
        self._current_episodes = []
        self._last_elapsed_seconds = elapsed_seconds

    def observe(
        self,
        *,
        elapsed_seconds: int,
        bottom_exhausted: bool,
    ) -> None:
        if self._match_index is None or self._previous_exhausted is None:
            raise RuntimeError("re-exhaustion handoff match is not active")
        if (
            self._last_elapsed_seconds is not None
            and elapsed_seconds < self._last_elapsed_seconds
        ):
            raise ValueError("observer time cannot move backwards")

        if self._previous_exhausted and not bottom_exhausted:
            self._current_episodes.append([elapsed_seconds, None])
        elif (
            not self._previous_exhausted
            and bottom_exhausted
            and self._current_episodes
            and self._current_episodes[-1][1] is None
        ):
            self._current_episodes[-1][1] = elapsed_seconds

        self._previous_exhausted = bottom_exhausted
        self._last_elapsed_seconds = elapsed_seconds

    def finish_match(
        self,
        *,
        elapsed_seconds: int,
        bottom_exhausted: bool,
    ) -> None:
        if self._match_index is None:
            raise RuntimeError("re-exhaustion handoff match is not active")

        self.observe(
            elapsed_seconds=elapsed_seconds,
            bottom_exhausted=bottom_exhausted,
        )
        match_index = self._match_index
        for clear_elapsed, reexhausted_elapsed in self._current_episodes:
            if clear_elapsed is None:
                raise RuntimeError("handoff episode missing clear timestamp")
            self._episodes.append(
                ReExhaustionHandoffEpisode(
                    match_index=match_index,
                    clear_elapsed_seconds=clear_elapsed,
                    reexhausted_elapsed_seconds=reexhausted_elapsed,
                    match_end_elapsed_seconds=elapsed_seconds,
                )
            )

        self._match_index = None
        self._previous_exhausted = None
        self._current_episodes = []
        self._last_elapsed_seconds = None

    def measurement(self) -> ReExhaustionHandoffMeasurement:
        if self._match_index is not None:
            raise RuntimeError(
                "cannot finalize re-exhaustion handoff measurement "
                "with active match"
            )
        return ReExhaustionHandoffMeasurement(episodes=tuple(self._episodes))


@dataclass(frozen=True, slots=True)
class BatchSummary:
    matches: int
    base_seed: int
    bottom_responder_mode: BatchResponderMode
    response_commitment_mode: BatchResponseCommitmentMode
    top_behavior: TopBehavior
    bottom_behavior: BottomBehavior
    commitment: Commitment
    outcome_counts: dict[str, int]
    top_final_stamina_mean: float
    top_final_stamina_median: float
    bottom_final_stamina_mean: float
    bottom_final_stamina_median: float
    top_first_exhausted_time_median: float | None
    bottom_first_exhausted_time_median: float | None
    matches_top_ever_exhausted: int
    matches_bottom_ever_exhausted: int
    matches_both_ever_exhausted: int
    total_response_commitment_stamina_charged: int
    response_requested_commitment_counts: dict[str, int]
    recognition_intent_direction_counts: dict[str, int]
    recognition_capability_direction_counts: dict[str, int]
    recognition_signal_disagreement_count: int
    undercommitment_events_before_mutual_exhaustion: int
    undercommitment_events_after_mutual_exhaustion: int
    undercommitment_caused_taps_before_mutual_exhaustion: int
    undercommitment_caused_taps_after_mutual_exhaustion: int
    final_axis_mean: float
    top_reset_count: int
    bottom_reset_count: int
    top_stalling_warning_count: int
    bottom_stalling_warning_count: int
    top_stalling_penalty_count: int
    bottom_stalling_penalty_count: int
    top_stalling_position_reset_count: int
    bottom_stalling_position_reset_count: int
    top_stalling_reset_with_route_count: int
    bottom_stalling_reset_with_route_count: int
    free_initiative_window_count: int
    top_action_counts: dict[str, int]
    bottom_action_counts: dict[str, int]
    top_escape_priority_count: int
    bottom_escape_priority_count: int
    top_submission_priority_count: int
    top_submission_attempt_count: int
    matches_reached_submission_threat: int
    matches_reached_submission_control: int
    matches_reached_submission_finish: int
    submission_feint_cap_count: int
    requested_low_feint_cap_count: int
    funding_downgrade_success_count: int
    funding_downgrade_feint_cap_count: int
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
    stamina_economy: StaminaEconomyMeasurement | None = None
    recovery_policy: RecoveryPolicyMeasurement | None = None
    reexhaustion_handoffs: ReExhaustionHandoffMeasurement | None = None

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
            f"Bottom responder policy: {self.bottom_responder_mode.value}",
            f"Response commitment policy: {self.response_commitment_mode.value}",
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
            f"Top first Exhausted median time: {self.top_first_exhausted_time_median if self.top_first_exhausted_time_median is not None else 'never'}",
            f"Bottom first Exhausted median time: {self.bottom_first_exhausted_time_median if self.bottom_first_exhausted_time_median is not None else 'never'}",
            f"Matches Top ever Exhausted: {self.matches_top_ever_exhausted}",
            f"Matches Bottom ever Exhausted: {self.matches_bottom_ever_exhausted}",
            f"Matches both ever Exhausted: {self.matches_both_ever_exhausted}",
            f"Responder commitment stamina charged: {self.total_response_commitment_stamina_charged}",
            "Response requested commitments: " + _render_counts(self.response_requested_commitment_counts),
            "Recognition intent directions: " + _render_counts(self.recognition_intent_direction_counts),
            "Recognition capability directions: " + _render_counts(self.recognition_capability_direction_counts),
            f"Recognition signal disagreements: {self.recognition_signal_disagreement_count}",
            f"Under-commitment events before mutual exhaustion: {self.undercommitment_events_before_mutual_exhaustion}",
            f"Under-commitment events after mutual exhaustion: {self.undercommitment_events_after_mutual_exhaustion}",
            f"Under-commitment-caused taps before mutual exhaustion: {self.undercommitment_caused_taps_before_mutual_exhaustion}",
            f"Under-commitment-caused taps after mutual exhaustion: {self.undercommitment_caused_taps_after_mutual_exhaustion}",
            f"Final axis mean: {self.final_axis_mean:+.3f}",
            "",
            "DECISIONS",
            f"Top RESET count: {self.top_reset_count}",
            f"Bottom RESET count: {self.bottom_reset_count}",
            f"Top stalling warnings: {self.top_stalling_warning_count}",
            f"Bottom stalling warnings: {self.bottom_stalling_warning_count}",
            f"Top stalling penalties: {self.top_stalling_penalty_count}",
            f"Bottom stalling penalties: {self.bottom_stalling_penalty_count}",
            f"Top Position Resets: {self.top_stalling_position_reset_count}",
            f"Bottom Position Resets: {self.bottom_stalling_position_reset_count}",
            f"Top RESET-with-route count: {self.top_stalling_reset_with_route_count}",
            f"Bottom RESET-with-route count: {self.bottom_stalling_reset_with_route_count}",
            f"Free initiative windows: {self.free_initiative_window_count}",
            f"Top escape-priority attacks: {self.top_escape_priority_count}",
            f"Bottom escape-priority attacks: {self.bottom_escape_priority_count}",
            f"Top submission-priority attacks: {self.top_submission_priority_count}",
            f"Top submission-stage attempts: {self.top_submission_attempt_count}",
            f"Matches reaching submission Threat: {self.matches_reached_submission_threat}",
            f"Matches reaching submission Control: {self.matches_reached_submission_control}",
            f"Matches reaching submission Finish: {self.matches_reached_submission_finish}",
            f"Submission feint caps: {self.submission_feint_cap_count}",
            f"Requested-LOW feint caps: {self.requested_low_feint_cap_count}",
            f"MEDIUM/HIGH funding-downgrade successful active-stage attempts: {self.funding_downgrade_success_count}",
            f"MEDIUM/HIGH funding-downgrade feint caps: {self.funding_downgrade_feint_cap_count}",
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


def _response_commitment_for_exchange(
    match: MountMatch,
    *,
    initiator_commitment: Commitment,
    mode: BatchResponseCommitmentMode,
    rng: random.Random,
    recognition_read: CommitmentRecognitionRead | None = None,
) -> Commitment:
    if mode is BatchResponseCommitmentMode.FIXED_MEDIUM:
        return Commitment.MEDIUM
    if mode is BatchResponseCommitmentMode.MATCH:
        initiator_pool = match.competitor(match.initiator).stamina
        effective = match.stamina_cost_policy.effective_commitment(
            requested=initiator_commitment,
            available_stamina=initiator_pool.current,
        )
        return Commitment.LOW if effective is None else effective
    if mode in {
        BatchResponseCommitmentMode.RECOGNITION,
        BatchResponseCommitmentMode.RECOGNITION_HEDGE_ONE,
        BatchResponseCommitmentMode.RECOGNITION_ALWAYS_HIGH,
    }:
        if recognition_read is None:
            raise ValueError("recognition response policy requires a Recognition read")
        if mode is BatchResponseCommitmentMode.RECOGNITION_ALWAYS_HIGH:
            return Commitment.HIGH

        trust_commitment = (
            Commitment.LOW
            if recognition_read.perceived_requested is Commitment.LOW
            else (
                Commitment.LOW
                if recognition_read.perceived_effective is None
                else recognition_read.perceived_effective
            )
        )
        if mode is BatchResponseCommitmentMode.RECOGNITION:
            return trust_commitment
        return {
            Commitment.LOW: Commitment.MEDIUM,
            Commitment.MEDIUM: Commitment.HIGH,
            Commitment.HIGH: Commitment.HIGH,
        }[trust_commitment]
    return rng.choice(tuple(Commitment))


def _informed_bottom_response_id(
    match: MountMatch,
    *,
    action_id: str,
    commitment: Commitment = Commitment.MEDIUM,
    response_commitment: Commitment = Commitment.MEDIUM,
    use_recognition: bool = False,
    perceived_effective_commitment: Commitment | None = None,
) -> str:
    """Choose Bottom's legal response from truth or a frozen perceived state."""
    if match.initiator is not Side.TOP:
        raise ValueError("informed Bottom response requires Top as initiator")

    legal = match.legal_response_ids(action_id)
    if not legal:
        raise RuntimeError(f"No legal responses for {action_id!r}")

    candidates: list[tuple[Grade, int, str]] = []
    for order, response_id in enumerate(legal):
        result = (
            match.preview_attempt_resolution_from_effective(
                action_id=action_id,
                response_id=response_id,
                initiator_effective_commitment=perceived_effective_commitment,
                response_commitment=response_commitment,
            )
            if use_recognition
            else match.preview_attempt_resolution(
                action_id=action_id,
                response_id=response_id,
                commitment=commitment,
                response_commitment=response_commitment,
            )
        )
        candidates.append((result.final_grade, order, response_id))

    return min(candidates)[2]


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
    bottom_responder_mode: BatchResponderMode = BatchResponderMode.RANDOM,
    response_commitment_mode: BatchResponseCommitmentMode = (
        BatchResponseCommitmentMode.FIXED_MEDIUM
    ),
    enable_v02_setup: bool = False,
    enable_v03_submissions: bool = False,
    enable_v03b_stalling: bool = False,
    enable_v04_commitment_semantics: bool = False,
    enable_v04b_recognition: bool = False,
    enable_stamina_settlement_rules: bool = False,
    enable_unfunded_responder_cost_waiver: bool = False,
    enable_supplemental_hold_settlement: bool = False,
    recovery_initiation_mode: RecoveryInitiationMode = (
        RecoveryInitiationMode.CURRENT
    ),
    measure_stamina_economy: bool = False,
    measure_recovery_policy: bool = False,
    measure_reexhaustion_handoffs: bool = False,
    shadow_stalling: bool = False,
) -> BatchSummary:
    if matches <= 0:
        raise ValueError("matches must be > 0")
    if enable_v03_submissions and not enable_v02_setup:
        raise ValueError("v0.3a submissions require v0.2 setup/Ready")
    if enable_v03b_stalling and not enable_v03_submissions:
        raise ValueError("v0.3b stalling requires v0.3a submissions")
    if enable_v04b_recognition and not enable_v04_commitment_semantics:
        raise ValueError("v0.4b Recognition requires v0.4a commitment semantics")
    if (
        enable_stamina_settlement_rules
        or enable_unfunded_responder_cost_waiver
        or enable_supplemental_hold_settlement
    ) and not enable_v04_commitment_semantics:
        raise ValueError(
            "stamina settlement rules require v0.4a commitment semantics"
        )
    if (
        response_commitment_mode in {
            BatchResponseCommitmentMode.RECOGNITION,
            BatchResponseCommitmentMode.RECOGNITION_HEDGE_ONE,
            BatchResponseCommitmentMode.RECOGNITION_ALWAYS_HIGH,
        }
        and not enable_v04b_recognition
    ):
        raise ValueError("recognition response policy requires v0.4b Recognition")
    if measure_stamina_economy and not enable_v04_commitment_semantics:
        raise ValueError(
            "stamina-economy measurement requires v0.4a commitment semantics"
        )
    if (
        recovery_initiation_mode is not RecoveryInitiationMode.CURRENT
        and bottom_behavior_mode is not BatchBehaviorMode.RECOVER
    ):
        raise ValueError(
            "recovery initiation candidates require Bottom RECOVER behavior"
        )
    if shadow_stalling and enable_v03b_stalling:
        raise ValueError(
            "shadow stalling is only valid when real v0.3b stalling is off"
        )
    if shadow_stalling and not measure_recovery_policy:
        raise ValueError(
            "shadow stalling requires recovery-policy measurement"
        )

    stamina_economy_collector = (
        StaminaEconomyCollector(
            interval_seconds=interval_seconds,
            behavior_quantum_seconds=(
                DEFAULT_BEHAVIOR_STAMINA_POLICY.quantum_seconds
            ),
        )
        if measure_stamina_economy
        else None
    )
    recovery_policy_collector = (
        RecoveryPolicyCollector(
            mode=recovery_initiation_mode,
            shadow_stalling=shadow_stalling,
        )
        if measure_recovery_policy
        else None
    )
    reexhaustion_handoff_observer = (
        ReExhaustionHandoffObserver()
        if measure_reexhaustion_handoffs
        else None
    )

    policy = EscapeFirstInitiatorPolicy()
    outcomes: Counter[str] = Counter()
    top_final: list[int] = []
    bottom_final: list[int] = []
    top_first_exhausted_times: list[int] = []
    bottom_first_exhausted_times: list[int] = []
    matches_top_ever_exhausted = 0
    matches_bottom_ever_exhausted = 0
    matches_both_ever_exhausted = 0
    total_response_commitment_stamina_charged = 0
    response_requested_commitments: Counter[str] = Counter()
    recognition_intent_directions: Counter[str] = Counter()
    recognition_capability_directions: Counter[str] = Counter()
    recognition_signal_disagreements = 0
    undercommitment_before_mutual_exhaustion = 0
    undercommitment_after_mutual_exhaustion = 0
    undercommitment_taps_before_mutual_exhaustion = 0
    undercommitment_taps_after_mutual_exhaustion = 0
    final_axes: list[float] = []
    top_resets = 0
    bottom_resets = 0
    top_stalling_warnings = 0
    bottom_stalling_warnings = 0
    top_stalling_penalties = 0
    bottom_stalling_penalties = 0
    top_stalling_position_resets = 0
    bottom_stalling_position_resets = 0
    top_stalling_resets_with_route = 0
    bottom_stalling_resets_with_route = 0
    free_initiative_windows = 0
    top_actions: Counter[str] = Counter()
    bottom_actions: Counter[str] = Counter()
    top_escape_priority = 0
    bottom_escape_priority = 0
    top_submission_priority = 0
    top_submission_attempts = 0
    matches_reached_threat = 0
    matches_reached_control = 0
    matches_reached_finish = 0
    submission_feint_caps = 0
    requested_low_feint_caps = 0
    funding_downgrade_successes = 0
    funding_downgrade_feint_caps = 0
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
            enable_v03b_stalling=enable_v03b_stalling,
            enable_v04_commitment_semantics=enable_v04_commitment_semantics,
            enable_v04b_recognition=enable_v04b_recognition,
            enable_stamina_settlement_rules=enable_stamina_settlement_rules,
            enable_unfunded_responder_cost_waiver=(
                enable_unfunded_responder_cost_waiver
            ),
            enable_supplemental_hold_settlement=(
                enable_supplemental_hold_settlement
            ),
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
        if stamina_economy_collector is not None:
            stamina_economy_collector.start_match(
                match,
                match_index=match_index,
            )
        if recovery_policy_collector is not None:
            recovery_policy_collector.start_match(
                match,
                match_index=match_index,
            )
        if reexhaustion_handoff_observer is not None:
            reexhaustion_handoff_observer.start_match(
                match_index=match_index,
                elapsed_seconds=match.elapsed_simulated_time,
                bottom_exhausted=(
                    match.bottom.stamina.band is StaminaBand.EXHAUSTED
                ),
            )
        responder = RandomBlindResponder(base_seed + match_index)
        response_commitment_rng = random.Random(
            base_seed + match_index + 1_000_003
        )
        recognition_intent_rng = random.Random(
            base_seed + match_index + 2_000_003
        )
        recognition_capability_rng = random.Random(
            base_seed + match_index + 3_000_003
        )
        top_first_exhausted: int | None = None
        bottom_first_exhausted: int | None = None

        def record_exhaustion() -> None:
            nonlocal top_first_exhausted, bottom_first_exhausted
            if (
                top_first_exhausted is None
                and match.top.stamina.band is StaminaBand.EXHAUSTED
            ):
                top_first_exhausted = match.elapsed_simulated_time
            if (
                bottom_first_exhausted is None
                and match.bottom.stamina.band is StaminaBand.EXHAUSTED
            ):
                bottom_first_exhausted = match.elapsed_simulated_time

        record_exhaustion()
        top_has_initiated_action = False
        pending_setup_builds: Counter[tuple[Side, str]] = Counter()
        pending_top_followup_setup_builds: Counter[str] = Counter()

        while not match.ended:
            free_window = (
                match.consume_free_initiative_window()
                if enable_v03b_stalling
                else None
            )
            if free_window is None:
                # Choose behavior for the upcoming normal-speed interval.
                next_top = top_policy.choose(match)
                next_bottom = bottom_policy.choose(match)
                if next_top is not current_top:
                    top_behavior_switches += 1
                    current_top = next_top
                if next_bottom is not current_bottom:
                    bottom_behavior_switches += 1
                    current_bottom = next_bottom
                    if stamina_economy_collector is not None:
                        stamina_economy_collector.behavior_switch(
                            side=Side.BOTTOM,
                            new_behavior=current_bottom.value,
                        )
                match.set_behaviors(top=current_top, bottom=current_bottom)
                top_behavior_windows[current_top.value] += 1
                bottom_behavior_windows[current_bottom.value] += 1

                stamina_state_before_advance = (
                    stamina_economy_collector.before_advance(match)
                    if stamina_economy_collector is not None
                    else None
                )
                advance_result = match.advance()
                if stamina_economy_collector is not None:
                    stamina_economy_collector.after_advance(
                        match,
                        state_before=stamina_state_before_advance,
                        result=advance_result,
                    )
                if recovery_policy_collector is not None:
                    recovery_policy_collector.after_advance(
                        match,
                        duration_seconds=(
                            advance_result.drift.start_clock
                            - advance_result.drift.end_clock
                        ),
                    )
                record_exhaustion()
                if reexhaustion_handoff_observer is not None:
                    reexhaustion_handoff_observer.observe(
                        elapsed_seconds=match.elapsed_simulated_time,
                        bottom_exhausted=(
                            match.bottom.stamina.band
                            is StaminaBand.EXHAUSTED
                        ),
                    )
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
                    if stamina_economy_collector is not None:
                        stamina_economy_collector.behavior_switch(
                            side=Side.BOTTOM,
                            new_behavior=current_bottom.value,
                        )
                match.set_behaviors(top=current_top, bottom=current_bottom)
            else:
                free_initiative_windows += 1

            if recovery_policy_collector is not None:
                recovery_policy_collector.record_trajectory(match)

            side = match.initiator
            bottom_recovery_exhausted_turn = (
                side is Side.BOTTOM
                and bottom_behavior_mode is BatchBehaviorMode.RECOVER
                and match.bottom.stamina.band is StaminaBand.EXHAUSTED
            )
            force_recovery_reset = (
                bottom_recovery_exhausted_turn
                and recovery_initiation_mode
                is RecoveryInitiationMode.RESET_WHILE_EXHAUSTED
            )
            selected_initiator_commitment = (
                Commitment.LOW
                if (
                    bottom_recovery_exhausted_turn
                    and recovery_initiation_mode
                    is RecoveryInitiationMode.LOW_WHILE_EXHAUSTED
                )
                else commitment
            )
            recognition_read: CommitmentRecognitionRead | None = None
            if enable_v02_setup:
                # v0.2 restores established-position ordering:
                # initiator locks action before responder chooses among legal responses.
                decision = (
                    BatchDecision(
                        action_id=None,
                        reason="recovery-reset",
                        escape_probability=0.0,
                        submission_progress_probability=0.0,
                        expected_raw_axis=0.0,
                        expected_realized_axis=0.0,
                    )
                    if force_recovery_reset
                    else policy.choose(match)
                )
                if decision.action_id is None:
                    if recovery_policy_collector is not None:
                        recovery_policy_collector.before_reset(
                            match,
                            forced_recovery_reset=force_recovery_reset,
                        )
                    reset = match.reset_window()
                    if recovery_policy_collector is not None:
                        recovery_policy_collector.after_reset(
                            match,
                            result=reset,
                        )
                    if side is Side.TOP:
                        top_resets += 1
                        if reset.progress_route_available:
                            top_stalling_resets_with_route += 1
                        if reset.stalling_consequence == "WARNING":
                            top_stalling_warnings += 1
                        elif reset.position_reset:
                            top_stalling_position_resets += 1
                        elif (
                            reset.penalty_axis_before is not None
                            and reset.penalty_axis_after is not None
                            and reset.penalty_axis_after != reset.penalty_axis_before
                        ):
                            top_stalling_penalties += 1
                    else:
                        bottom_resets += 1
                        if reset.progress_route_available:
                            bottom_stalling_resets_with_route += 1
                        if reset.stalling_consequence == "WARNING":
                            bottom_stalling_warnings += 1
                        elif reset.position_reset:
                            bottom_stalling_position_resets += 1
                        elif (
                            reset.penalty_axis_before is not None
                            and reset.penalty_axis_after is not None
                            and reset.penalty_axis_after != reset.penalty_axis_before
                        ):
                            bottom_stalling_penalties += 1
                    if reexhaustion_handoff_observer is not None:
                        reexhaustion_handoff_observer.observe(
                            elapsed_seconds=match.elapsed_simulated_time,
                            bottom_exhausted=(
                                match.bottom.stamina.band
                                is StaminaBand.EXHAUSTED
                            ),
                        )
                    continue
                if enable_v04b_recognition:
                    recognition_read = match.recognize_commitment(
                        requested=selected_initiator_commitment,
                        intent_roll=recognition_intent_rng.randint(1, 6),
                        capability_roll=recognition_capability_rng.randint(1, 6),
                    )
                selected_response_commitment = (
                    _response_commitment_for_exchange(
                        match,
                        initiator_commitment=selected_initiator_commitment,
                        mode=response_commitment_mode,
                        rng=response_commitment_rng,
                        recognition_read=recognition_read,
                    )
                    if enable_v04_commitment_semantics
                    else None
                )
                if (
                    side is Side.TOP
                    and bottom_responder_mode is BatchResponderMode.INFORMED
                ):
                    response_id = _informed_bottom_response_id(
                        match,
                        action_id=decision.action_id,
                        commitment=selected_initiator_commitment,
                        response_commitment=selected_response_commitment,
                        use_recognition=recognition_read is not None,
                        perceived_effective_commitment=(
                            recognition_read.perceived_effective
                            if recognition_read is not None
                            else None
                        ),
                    )
                else:
                    hidden = responder.choose(
                        side.opponent,
                        allowed_response_ids=match.legal_response_ids(
                            decision.action_id
                        ),
                        fallback_response_id=(
                            policy._ready_fallback_response_id(
                                match,
                                decision.action_id,
                            )
                        ),
                    )
                    response_id = hidden.response_id
            else:
                # v0.1 blind harness preserves historical responder-first sampling.
                hidden = responder.choose(side.opponent)
                response_id = hidden.response_id
                decision = (
                    BatchDecision(
                        action_id=None,
                        reason="recovery-reset",
                        escape_probability=0.0,
                        submission_progress_probability=0.0,
                        expected_raw_axis=0.0,
                        expected_realized_axis=0.0,
                    )
                    if force_recovery_reset
                    else policy.choose(match)
                )
                if decision.action_id is None:
                    if recovery_policy_collector is not None:
                        recovery_policy_collector.before_reset(
                            match,
                            forced_recovery_reset=force_recovery_reset,
                        )
                    reset = match.reset_window()
                    if recovery_policy_collector is not None:
                        recovery_policy_collector.after_reset(
                            match,
                            result=reset,
                        )
                    if side is Side.TOP:
                        top_resets += 1
                        if reset.progress_route_available:
                            top_stalling_resets_with_route += 1
                        if reset.stalling_consequence == "WARNING":
                            top_stalling_warnings += 1
                        elif reset.position_reset:
                            top_stalling_position_resets += 1
                        elif (
                            reset.penalty_axis_before is not None
                            and reset.penalty_axis_after is not None
                            and reset.penalty_axis_after != reset.penalty_axis_before
                        ):
                            top_stalling_penalties += 1
                    else:
                        bottom_resets += 1
                        if reset.progress_route_available:
                            bottom_stalling_resets_with_route += 1
                        if reset.stalling_consequence == "WARNING":
                            bottom_stalling_warnings += 1
                        elif reset.position_reset:
                            bottom_stalling_position_resets += 1
                        elif (
                            reset.penalty_axis_before is not None
                            and reset.penalty_axis_after is not None
                            and reset.penalty_axis_after != reset.penalty_axis_before
                        ):
                            bottom_stalling_penalties += 1
                    continue
                if enable_v04b_recognition:
                    recognition_read = match.recognize_commitment(
                        requested=selected_initiator_commitment,
                        intent_roll=recognition_intent_rng.randint(1, 6),
                        capability_roll=recognition_capability_rng.randint(1, 6),
                    )
                selected_response_commitment = (
                    _response_commitment_for_exchange(
                        match,
                        initiator_commitment=selected_initiator_commitment,
                        mode=response_commitment_mode,
                        rng=response_commitment_rng,
                        recognition_read=recognition_read,
                    )
                    if enable_v04_commitment_semantics
                    else None
                )

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

            feint_caps_before = len(
                match.history.submission_feint_cap_history
            )
            recovery_policy_attempt = (
                recovery_policy_collector.before_attempt(
                    match,
                    action_id=decision.action_id,
                    requested_commitment=selected_initiator_commitment,
                )
                if recovery_policy_collector is not None
                else None
            )
            stamina_economy_attempt = (
                stamina_economy_collector.before_attempt(
                    match,
                    action_id=decision.action_id,
                    initiator_commitment=selected_initiator_commitment,
                    responder_commitment=(
                        selected_response_commitment
                        if selected_response_commitment is not None
                        else Commitment.MEDIUM
                    ),
                )
                if stamina_economy_collector is not None
                else None
            )
            submission_stage_before = (
                match.submission_state.stage
                if action.id == TOP_AMERICANA_SUBMISSION_FINISH
                else None
            )
            mutually_exhausted_before_exchange = (
                match.top.stamina.band is StaminaBand.EXHAUSTED
                and match.bottom.stamina.band is StaminaBand.EXHAUSTED
            )
            attempt_result = match.attempt(
                action_id=decision.action_id,
                response_id=response_id,
                commitment=selected_initiator_commitment,
                response_commitment=selected_response_commitment,
                recognition_read=recognition_read,
            )
            if stamina_economy_collector is not None:
                stamina_economy_collector.after_attempt(
                    match,
                    snapshot=stamina_economy_attempt,
                    result=attempt_result,
                )
            if recovery_policy_collector is not None:
                recovery_policy_collector.after_attempt(
                    match,
                    context=recovery_policy_attempt,
                    decision_reason=decision.reason,
                )
            record_exhaustion()
            if reexhaustion_handoff_observer is not None:
                reexhaustion_handoff_observer.observe(
                    elapsed_seconds=match.elapsed_simulated_time,
                    bottom_exhausted=(
                        match.bottom.stamina.band is StaminaBand.EXHAUSTED
                    ),
                )

            undercommitted = (
                attempt_result.response_undercommitment_modifier > 0
            )
            if undercommitted:
                if mutually_exhausted_before_exchange:
                    undercommitment_after_mutual_exhaustion += 1
                else:
                    undercommitment_before_mutual_exhaustion += 1

            undercommitment_caused_tap = (
                undercommitted
                and submission_stage_before is SubmissionStage.FINISH
                and match.submission_tapped
                and attempt_result.resolution.final_grade.successful
                and not attempt_result.resolution.final_grade.shift(-1).successful
            )
            if undercommitment_caused_tap:
                if mutually_exhausted_before_exchange:
                    undercommitment_taps_after_mutual_exhaustion += 1
                else:
                    undercommitment_taps_before_mutual_exhaustion += 1

            if attempt_result.response_stamina is not None:
                total_response_commitment_stamina_charged += (
                    attempt_result.response_stamina.charged
                )
            if attempt_result.response_requested_commitment is not None:
                response_requested_commitments[
                    attempt_result.response_requested_commitment.value
                ] += 1
            if recognition_read is not None:
                requested_levels = (
                    Commitment.LOW,
                    Commitment.MEDIUM,
                    Commitment.HIGH,
                )
                effective_levels = (
                    None,
                    Commitment.LOW,
                    Commitment.MEDIUM,
                    Commitment.HIGH,
                )
                true_intent_rank = requested_levels.index(
                    recognition_read.true_requested
                )
                perceived_intent_rank = requested_levels.index(
                    recognition_read.perceived_requested
                )
                true_capability_rank = effective_levels.index(
                    recognition_read.true_effective
                )
                perceived_capability_rank = effective_levels.index(
                    recognition_read.perceived_effective
                )
                recognition_intent_directions[
                    "exact"
                    if perceived_intent_rank == true_intent_rank
                    else (
                        "lower"
                        if perceived_intent_rank < true_intent_rank
                        else "higher"
                    )
                ] += 1
                recognition_capability_directions[
                    "exact"
                    if perceived_capability_rank == true_capability_rank
                    else (
                        "lower"
                        if perceived_capability_rank < true_capability_rank
                        else "higher"
                    )
                ] += 1
                if perceived_intent_rank + 1 != perceived_capability_rank:
                    recognition_signal_disagreements += 1
            feint_caps_after = len(
                match.history.submission_feint_cap_history
            )

            is_active_submission_success = (
                enable_v04_commitment_semantics
                and action.id == TOP_AMERICANA_SUBMISSION_FINISH
                and attempt_result.resolution.final_grade.successful
            )
            is_funding_downgrade = (
                attempt_result.attempt.requested_commitment
                in {Commitment.MEDIUM, Commitment.HIGH}
                and attempt_result.attempt.effective_commitment
                in {None, Commitment.LOW}
            )
            if is_active_submission_success and is_funding_downgrade:
                funding_downgrade_successes += 1

            added_feint_caps = feint_caps_after - feint_caps_before
            if added_feint_caps:
                submission_feint_caps += added_feint_caps
                if attempt_result.attempt.requested_commitment is Commitment.LOW:
                    requested_low_feint_caps += added_feint_caps
                elif is_funding_downgrade:
                    funding_downgrade_feint_caps += added_feint_caps

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
        if stamina_economy_collector is not None:
            stamina_economy_collector.finish_match(
                match,
                outcome=outcome,
            )
        if recovery_policy_collector is not None:
            recovery_policy_collector.finish_match(
                match,
                outcome=outcome,
            )
        if reexhaustion_handoff_observer is not None:
            reexhaustion_handoff_observer.finish_match(
                elapsed_seconds=match.elapsed_simulated_time,
                bottom_exhausted=(
                    match.bottom.stamina.band is StaminaBand.EXHAUSTED
                ),
            )
        top_final.append(match.top.stamina.current)
        bottom_final.append(match.bottom.stamina.current)
        if top_first_exhausted is not None:
            top_first_exhausted_times.append(top_first_exhausted)
            matches_top_ever_exhausted += 1
        if bottom_first_exhausted is not None:
            bottom_first_exhausted_times.append(bottom_first_exhausted)
            matches_bottom_ever_exhausted += 1
        if top_first_exhausted is not None and bottom_first_exhausted is not None:
            matches_both_ever_exhausted += 1
        final_axes.append(match.axis)

    return BatchSummary(
        matches=matches,
        base_seed=base_seed,
        bottom_responder_mode=bottom_responder_mode,
        response_commitment_mode=response_commitment_mode,
        top_behavior=top_behavior,
        bottom_behavior=bottom_behavior,
        commitment=commitment,
        outcome_counts=dict(outcomes),
        top_final_stamina_mean=mean(top_final),
        top_final_stamina_median=median(top_final),
        bottom_final_stamina_mean=mean(bottom_final),
        bottom_final_stamina_median=median(bottom_final),
        top_first_exhausted_time_median=(
            median(top_first_exhausted_times)
            if top_first_exhausted_times
            else None
        ),
        bottom_first_exhausted_time_median=(
            median(bottom_first_exhausted_times)
            if bottom_first_exhausted_times
            else None
        ),
        matches_top_ever_exhausted=matches_top_ever_exhausted,
        matches_bottom_ever_exhausted=matches_bottom_ever_exhausted,
        matches_both_ever_exhausted=matches_both_ever_exhausted,
        total_response_commitment_stamina_charged=(
            total_response_commitment_stamina_charged
        ),
        response_requested_commitment_counts=dict(response_requested_commitments),
        recognition_intent_direction_counts=dict(recognition_intent_directions),
        recognition_capability_direction_counts=dict(
            recognition_capability_directions
        ),
        recognition_signal_disagreement_count=recognition_signal_disagreements,
        undercommitment_events_before_mutual_exhaustion=(
            undercommitment_before_mutual_exhaustion
        ),
        undercommitment_events_after_mutual_exhaustion=(
            undercommitment_after_mutual_exhaustion
        ),
        undercommitment_caused_taps_before_mutual_exhaustion=(
            undercommitment_taps_before_mutual_exhaustion
        ),
        undercommitment_caused_taps_after_mutual_exhaustion=(
            undercommitment_taps_after_mutual_exhaustion
        ),
        final_axis_mean=mean(final_axes),
        top_reset_count=top_resets,
        bottom_reset_count=bottom_resets,
        top_stalling_warning_count=top_stalling_warnings,
        bottom_stalling_warning_count=bottom_stalling_warnings,
        top_stalling_penalty_count=top_stalling_penalties,
        bottom_stalling_penalty_count=bottom_stalling_penalties,
        top_stalling_position_reset_count=top_stalling_position_resets,
        bottom_stalling_position_reset_count=bottom_stalling_position_resets,
        top_stalling_reset_with_route_count=top_stalling_resets_with_route,
        bottom_stalling_reset_with_route_count=bottom_stalling_resets_with_route,
        free_initiative_window_count=free_initiative_windows,
        top_action_counts=dict(top_actions),
        bottom_action_counts=dict(bottom_actions),
        top_escape_priority_count=top_escape_priority,
        bottom_escape_priority_count=bottom_escape_priority,
        top_submission_priority_count=top_submission_priority,
        top_submission_attempt_count=top_submission_attempts,
        matches_reached_submission_threat=matches_reached_threat,
        matches_reached_submission_control=matches_reached_control,
        matches_reached_submission_finish=matches_reached_finish,
        submission_feint_cap_count=submission_feint_caps,
        requested_low_feint_cap_count=requested_low_feint_caps,
        funding_downgrade_success_count=funding_downgrade_successes,
        funding_downgrade_feint_cap_count=funding_downgrade_feint_caps,
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
        stamina_economy=(
            stamina_economy_collector.measurement()
            if stamina_economy_collector is not None
            else None
        ),
        recovery_policy=(
            recovery_policy_collector.measurement()
            if recovery_policy_collector is not None
            else None
        ),
        reexhaustion_handoffs=(
            reexhaustion_handoff_observer.measurement()
            if reexhaustion_handoff_observer is not None
            else None
        ),
    )


def run_greedy_batch(**kwargs) -> BatchSummary:
    """Compatibility alias for the pre-v0.1e batch function name.

    The official batch policy is now escape-first lexicographic.
    """
    return run_escape_first_batch(**kwargs)
