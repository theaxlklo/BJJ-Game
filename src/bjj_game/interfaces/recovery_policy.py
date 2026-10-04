from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum

from ..domain.action import Commitment, ResetWindowResult
from ..domain.model import Band, Side
from ..domain.setup import SetupTier
from ..domain.stamina import StaminaBand
from ..engine.match import MountMatch
from ..engine.stalling import (
    STALLING_THRESHOLD_SECONDS,
    StallingConsequence,
    StallingTracker,
)
from ..positions.mount.catalog import (
    BOTTOM_BRIDGE,
    TOP_AMERICANA_SUBMISSION_FINISH,
)
from ..positions.mount.rules import DEFAULT_AXIS


class RecoveryInitiationMode(str, Enum):
    CURRENT = "CURRENT"
    RESET_WHILE_EXHAUSTED = "RESET_WHILE_EXHAUSTED"
    LOW_WHILE_EXHAUSTED = "LOW_WHILE_EXHAUSTED"


@dataclass(frozen=True, slots=True)
class RecoveryTrajectorySnapshot:
    elapsed_seconds: int
    initiator: str
    axis: float
    mount_band: str
    top_stamina: int
    bottom_stamina: int
    top_stamina_band: str
    bottom_stamina_band: str
    bottom_bridge_setup_tier: int
    submission_stage: str
    shadow_bottom_clock: int | None


@dataclass(frozen=True, slots=True)
class ShadowStallingEvent:
    elapsed_seconds: int
    side: Side
    progress_route_available: bool
    clock_seconds: int
    tracker_consequence: str
    effective_consequence: str
    exhausted: bool
    cause: str
    mount_band: Band


@dataclass(frozen=True, slots=True)
class RecoveryPolicyMatchRecord:
    match_index: int
    outcome: str
    trajectory: tuple[RecoveryTrajectorySnapshot, ...]
    shadow_events: tuple[ShadowStallingEvent, ...]
    shadow_threshold_reach_times_bottom: tuple[int, ...]
    shadow_bottom_resets_with_route: int
    bottom_actual_stalling_signed_axis_delta: float
    bottom_actual_stalling_absolute_control_loss: float
    bottom_actual_stalling_free_initiative: int
    bottom_first_actual_stalling_offense_time: int | None
    bottom_exhausted_requested_commitments: tuple[tuple[str, int], ...]
    bottom_exhausted_bridge_attempts: int
    bottom_exhausted_setup_builder_attempts: int
    bottom_exhausted_setup_advances: int
    bottom_exhausted_ready_transitions: int
    bottom_exhausted_completed_setup_builds: int
    bottom_exhausted_escapes_after_setup_build: int
    bottom_exhausted_resets: int
    bottom_exhausted_resets_forgone_setup_opportunity: int


@dataclass(frozen=True, slots=True)
class RecoveryPolicyMeasurement:
    mode: RecoveryInitiationMode
    shadow_stalling_enabled: bool
    matches: tuple[RecoveryPolicyMatchRecord, ...]


@dataclass(frozen=True, slots=True)
class _AttemptContext:
    side: Side
    bottom_exhausted: bool
    action_id: str
    requested_commitment: Commitment
    setup_target: str | None
    setup_tier_before: SetupTier
    target_was_ready: bool
    pending_exhausted_builds_before: int


class RecoveryPolicyCollector:
    """Read-only observer for recovery-initiation and shadow-stalling evidence."""

    def __init__(
        self,
        *,
        mode: RecoveryInitiationMode,
        shadow_stalling: bool,
    ) -> None:
        self.mode = mode
        self.shadow_stalling = shadow_stalling
        self._records: list[RecoveryPolicyMatchRecord] = []
        self._current: dict | None = None

    def start_match(self, match: MountMatch, *, match_index: int) -> None:
        if self._current is not None:
            raise RuntimeError("recovery-policy match already active")
        shadow_tracker = (
            StallingTracker(threshold_seconds=STALLING_THRESHOLD_SECONDS)
            if self.shadow_stalling
            else None
        )
        self._current = {
            "match_index": match_index,
            "shadow_tracker": shadow_tracker,
            "shadow_events": [],
            "shadow_threshold_bottom": [],
            "shadow_previous_bottom_clock": 0,
            "trajectory": [],
            "shadow_bottom_resets_with_route": 0,
            "bottom_axis_delta": 0.0,
            "bottom_abs_loss": 0.0,
            "bottom_actual_free_initiative": 0,
            "bottom_first_actual_offense": None,
            "bottom_exhausted_requested_commitments": Counter(),
            "bottom_bridge_attempts": 0,
            "bottom_setup_builder_attempts": 0,
            "bottom_setup_advances": 0,
            "bottom_ready_transitions": 0,
            "bottom_completed_setup_builds": 0,
            "bottom_escapes_after_setup": 0,
            "bottom_exhausted_resets": 0,
            "bottom_reset_forgone_setup": 0,
            "pending_exhausted_builds": Counter(),
            "bottom_reset_sequence": 0,
        }
        self.record_trajectory(match)

    def _require(self) -> dict:
        if self._current is None:
            raise RuntimeError("recovery-policy match is not active")
        return self._current

    @staticmethod
    def _bottom_setup_target(match: MountMatch) -> str:
        rule = match.setup_policy.rule_for_builder(BOTTOM_BRIDGE)
        if rule is None:
            raise RuntimeError("Bottom Bridge setup rule is missing")
        return rule.target_action_id

    def record_trajectory(self, match: MountMatch) -> None:
        current = self._require()
        shadow_tracker = current["shadow_tracker"]
        shadow_clock = (
            shadow_tracker.clock(Side.BOTTOM)
            if shadow_tracker is not None
            else None
        )
        target = self._bottom_setup_target(match)
        current["trajectory"].append(
            RecoveryTrajectorySnapshot(
                elapsed_seconds=match.elapsed_simulated_time,
                initiator=match.initiator.value,
                axis=match.axis,
                mount_band=match.band.value,
                top_stamina=match.top.stamina.current,
                bottom_stamina=match.bottom.stamina.current,
                top_stamina_band=match.top.stamina.band.value,
                bottom_stamina_band=match.bottom.stamina.band.value,
                bottom_bridge_setup_tier=int(match.setup_state.tier(target)),
                submission_stage=(
                    match.submission_state.stage.value
                    if match.submission_state.active
                    else "NONE"
                ),
                shadow_bottom_clock=shadow_clock,
            )
        )

    def after_advance(self, match: MountMatch, *, duration_seconds: int) -> None:
        current = self._require()
        tracker = current["shadow_tracker"]
        if tracker is not None:
            before = tracker.clock(Side.BOTTOM)
            tracker.advance(duration_seconds)
            after = tracker.clock(Side.BOTTOM)
            if (
                before < STALLING_THRESHOLD_SECONDS
                and after >= STALLING_THRESHOLD_SECONDS
            ):
                current["shadow_threshold_bottom"].append(
                    match.elapsed_simulated_time
                )
            current["shadow_previous_bottom_clock"] = after

    @staticmethod
    def _shadow_effective_consequence(
        *,
        match: MountMatch,
        side: Side,
        tracker_consequence: StallingConsequence,
    ) -> str:
        if tracker_consequence is StallingConsequence.WARNING:
            return "WARNING"
        if tracker_consequence not in {
            StallingConsequence.PENALTY,
            StallingConsequence.POSITION_RESET,
        }:
            return tracker_consequence.value

        one_band_target = MountMatch._stalling_penalty_target(
            offender=side,
            band=match.band,
        )
        if one_band_target is None:
            return "FREE_INITIATIVE"

        if tracker_consequence is StallingConsequence.PENALTY:
            return "PENALTY"

        # Frozen v0.3b Position Reset rung. Bottom never receives a canonical
        # +1.50 reset because that could improve Bottom's position; it receives
        # the ordinary one-band/free-initiative consequence instead.
        if side is Side.BOTTOM:
            return "PENALTY"

        target_axis = min(DEFAULT_AXIS, one_band_target)
        return (
            "PENALTY"
            if target_axis == one_band_target
            else "POSITION_RESET"
        )

    def before_reset(
        self,
        match: MountMatch,
        *,
        forced_recovery_reset: bool,
    ) -> tuple[str, ...]:
        current = self._require()
        side = match.initiator
        progress_ids = match.progress_capable_action_ids()
        progress_route_available = bool(progress_ids)

        if (
            side is Side.BOTTOM
            and match.bottom.stamina.band is StaminaBand.EXHAUSTED
        ):
            current["bottom_exhausted_resets"] += 1
            legal_setup_builders = tuple(
                action_id
                for action_id in match.legal_action_ids(Side.BOTTOM)
                if match.setup_policy.target_for_builder(action_id) is not None
            )
            if legal_setup_builders:
                current["bottom_reset_forgone_setup"] += 1

        tracker = current["shadow_tracker"]
        if tracker is not None:
            if side is Side.BOTTOM and progress_route_available:
                current["shadow_bottom_resets_with_route"] += 1
            current["bottom_reset_sequence"] += side is Side.BOTTOM
            evaluation = tracker.evaluate_reset(
                side=side,
                progress_route_available=progress_route_available,
            )
            if evaluation.offense:
                current["shadow_events"].append(
                    ShadowStallingEvent(
                        elapsed_seconds=match.elapsed_simulated_time,
                        side=side,
                        progress_route_available=progress_route_available,
                        clock_seconds=evaluation.clock_seconds,
                        tracker_consequence=evaluation.consequence.value,
                        effective_consequence=self._shadow_effective_consequence(
                            match=match,
                            side=side,
                            tracker_consequence=evaluation.consequence,
                        ),
                        exhausted=(
                            match.competitor(side).stamina.band
                            is StaminaBand.EXHAUSTED
                        ),
                        cause=(
                            f"{side.value}:RESET#"
                            f"{current['bottom_reset_sequence']}"
                            if side is Side.BOTTOM
                            else f"{side.value}:RESET"
                        ),
                        mount_band=match.band,
                    )
                )
        return progress_ids

    def after_reset(
        self,
        match: MountMatch,
        *,
        result: ResetWindowResult,
    ) -> None:
        current = self._require()
        if result.initiator is Side.BOTTOM:
            if result.free_initiative_window:
                current["bottom_actual_free_initiative"] += 1
            if (
                result.stalling_offense
                and current["bottom_first_actual_offense"] is None
            ):
                current["bottom_first_actual_offense"] = (
                    match.elapsed_simulated_time
                )

            before = result.penalty_axis_before
            after = result.penalty_axis_after
            if (
                before is not None
                and after is not None
                and after != before
            ):
                delta = after - before
                current["bottom_axis_delta"] += delta
                current["bottom_abs_loss"] += abs(delta)

            reset_before = result.position_reset_axis_before
            reset_after = result.position_reset_axis_after
            if (
                reset_before is not None
                and reset_after is not None
                and reset_after != reset_before
            ):
                delta = reset_after - reset_before
                current["bottom_axis_delta"] += delta
                current["bottom_abs_loss"] += abs(delta)

    def before_attempt(
        self,
        match: MountMatch,
        *,
        action_id: str,
        requested_commitment: Commitment,
    ) -> _AttemptContext:
        current = self._require()
        side = match.initiator
        bottom_exhausted = (
            side is Side.BOTTOM
            and match.bottom.stamina.band is StaminaBand.EXHAUSTED
        )
        setup_target = match.setup_policy.target_for_builder(action_id)
        setup_tier_before = (
            match.setup_state.tier(setup_target)
            if setup_target is not None
            else SetupTier.NONE
        )
        target_was_ready = (
            action_id in match.setup_policy.target_action_ids
            and match.setup_state.is_ready(action_id)
        )
        pending_before = current["pending_exhausted_builds"].get(
            action_id,
            0,
        )

        if bottom_exhausted:
            current["bottom_exhausted_requested_commitments"][
                requested_commitment.value
            ] += 1
            if action_id == BOTTOM_BRIDGE:
                current["bottom_bridge_attempts"] += 1
            if setup_target is not None:
                current["bottom_setup_builder_attempts"] += 1

        tracker = current["shadow_tracker"]
        if tracker is not None:
            progress_ids = match.progress_capable_action_ids()
            if action_id in progress_ids:
                feint_capped_active_submission = (
                    match.enable_v04_commitment_semantics
                    and action_id == TOP_AMERICANA_SUBMISSION_FINISH
                    and match.submission_state.active
                    and requested_commitment is Commitment.LOW
                )
                if not feint_capped_active_submission:
                    tracker.engage(side)
                tracker.engage(side.opponent)

        return _AttemptContext(
            side=side,
            bottom_exhausted=bottom_exhausted,
            action_id=action_id,
            requested_commitment=requested_commitment,
            setup_target=setup_target,
            setup_tier_before=setup_tier_before,
            target_was_ready=target_was_ready,
            pending_exhausted_builds_before=pending_before,
        )

    def after_attempt(
        self,
        match: MountMatch,
        *,
        context: _AttemptContext,
        decision_reason: str,
    ) -> None:
        current = self._require()

        if (
            context.bottom_exhausted
            and context.setup_target is not None
        ):
            after_tier = match.setup_state.tier(context.setup_target)
            if after_tier > context.setup_tier_before:
                current["bottom_setup_advances"] += 1
                if decision_reason == "setup":
                    current["pending_exhausted_builds"][
                        context.setup_target
                    ] += 1
                if (
                    after_tier is SetupTier.READY
                    and context.setup_tier_before is not SetupTier.READY
                ):
                    current["bottom_ready_transitions"] += 1

        if (
            context.side is Side.BOTTOM
            and context.target_was_ready
        ):
            pending = current["pending_exhausted_builds"].get(
                context.action_id,
                0,
            )
            if pending:
                current["bottom_completed_setup_builds"] += pending
                if match.exit_destination is not None:
                    current["bottom_escapes_after_setup"] += 1
                current["pending_exhausted_builds"][
                    context.action_id
                ] = 0

    def finish_match(self, match: MountMatch, *, outcome: str) -> None:
        current = self._require()
        self.record_trajectory(match)
        self._records.append(
            RecoveryPolicyMatchRecord(
                match_index=current["match_index"],
                outcome=outcome,
                trajectory=tuple(current["trajectory"]),
                shadow_events=tuple(current["shadow_events"]),
                shadow_threshold_reach_times_bottom=tuple(
                    current["shadow_threshold_bottom"]
                ),
                shadow_bottom_resets_with_route=current[
                    "shadow_bottom_resets_with_route"
                ],
                bottom_actual_stalling_signed_axis_delta=current[
                    "bottom_axis_delta"
                ],
                bottom_actual_stalling_absolute_control_loss=current[
                    "bottom_abs_loss"
                ],
                bottom_actual_stalling_free_initiative=current[
                    "bottom_actual_free_initiative"
                ],
                bottom_first_actual_stalling_offense_time=current[
                    "bottom_first_actual_offense"
                ],
                bottom_exhausted_requested_commitments=tuple(
                    sorted(
                        current[
                            "bottom_exhausted_requested_commitments"
                        ].items()
                    )
                ),
                bottom_exhausted_bridge_attempts=current[
                    "bottom_bridge_attempts"
                ],
                bottom_exhausted_setup_builder_attempts=current[
                    "bottom_setup_builder_attempts"
                ],
                bottom_exhausted_setup_advances=current[
                    "bottom_setup_advances"
                ],
                bottom_exhausted_ready_transitions=current[
                    "bottom_ready_transitions"
                ],
                bottom_exhausted_completed_setup_builds=current[
                    "bottom_completed_setup_builds"
                ],
                bottom_exhausted_escapes_after_setup_build=current[
                    "bottom_escapes_after_setup"
                ],
                bottom_exhausted_resets=current[
                    "bottom_exhausted_resets"
                ],
                bottom_exhausted_resets_forgone_setup_opportunity=current[
                    "bottom_reset_forgone_setup"
                ],
            )
        )
        self._current = None

    def measurement(self) -> RecoveryPolicyMeasurement:
        if self._current is not None:
            raise RuntimeError(
                "cannot finalize recovery-policy measurement with active match"
            )
        return RecoveryPolicyMeasurement(
            mode=self.mode,
            shadow_stalling_enabled=self.shadow_stalling,
            matches=tuple(self._records),
        )
