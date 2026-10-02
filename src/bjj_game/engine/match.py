from __future__ import annotations

import warnings
from dataclasses import dataclass, field, replace

from ..domain.action import ActionAttempt, AttemptResult, Commitment, ResetWindowResult
from ..domain.competitor import Competitor
from ..domain.model import (
    Band,
    BottomBehavior,
    ExitDestination,
    RunHistory,
    Side,
    TopBehavior,
)
from ..domain.setup import SetupState, SetupTier
from ..domain.submission import SubmissionStage, SubmissionState
from ..positions.mount.catalog import (
    MODERN_ENTITY_BY_ID,
    TOP_AMERICANA_ARM_ISOLATION,
    TOP_AMERICANA_SUBMISSION_FINISH,
)
from ..positions.mount.position import MountPosition
from ..positions.mount.rules import (
    DEFAULT_AXIS,
    DEFAULT_CLOCK_SECONDS,
    DEFAULT_INTERVAL_SECONDS,
)
from .mount_engine import MountResolutionEngine
from .setup import DEFAULT_MOUNT_SETUP_POLICY, MountSetupPolicy
from .stamina import (
    DEFAULT_BEHAVIOR_STAMINA_POLICY,
    DEFAULT_EXHAUSTION_POLICY,
    DEFAULT_STAMINA_COST_POLICY,
    AdvanceResult,
    BehaviorStaminaMeter,
    BehaviorStaminaPolicy,
    ExhaustionPolicy,
    StaminaCostPolicy,
)


@dataclass(slots=True)
class MountMatch:
    """Stateful Mount match aggregate.

    Mount-v0 resolution remains inside MountResolutionEngine. v0.1 layers add
    stamina/commitment policy around that frozen resolution. v0.1e supplies a
    generic post-positional grade modifier for exhausted initiators.
    """

    initial_clock: int = DEFAULT_CLOCK_SECONDS
    starting_axis: float = DEFAULT_AXIS
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS
    engine: MountResolutionEngine = field(
        default_factory=MountResolutionEngine.default, repr=False
    )
    stamina_cost_policy: StaminaCostPolicy = field(
        default_factory=lambda: DEFAULT_STAMINA_COST_POLICY, repr=False
    )
    behavior_stamina_policy: BehaviorStaminaPolicy = field(
        default_factory=lambda: DEFAULT_BEHAVIOR_STAMINA_POLICY, repr=False
    )
    exhaustion_policy: ExhaustionPolicy = field(
        default_factory=lambda: DEFAULT_EXHAUSTION_POLICY, repr=False
    )
    enable_v02_setup: bool = False
    enable_v03_submissions: bool = False
    setup_policy: MountSetupPolicy = field(
        default_factory=lambda: DEFAULT_MOUNT_SETUP_POLICY, repr=False
    )
    clock_seconds: int = field(init=False)
    position: MountPosition = field(init=False)
    initial_band: Band = field(init=False)
    initiator: Side = field(init=False)
    history: RunHistory = field(init=False)
    top: Competitor = field(init=False)
    bottom: Competitor = field(init=False)
    exit_destination: ExitDestination | None = field(init=False, default=None)
    exit_reason: str | None = field(init=False, default=None)
    top_behavior_stamina_meter: BehaviorStaminaMeter = field(init=False)
    bottom_behavior_stamina_meter: BehaviorStaminaMeter = field(init=False)
    setup_state: SetupState = field(init=False)
    submission_state: SubmissionState = field(init=False)
    submission_tapped: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        if self.initial_clock <= 0:
            raise ValueError("clock must be > 0")
        if self.interval_seconds <= 0:
            raise ValueError("interval must be > 0")
        if self.enable_v03_submissions and not self.enable_v02_setup:
            raise ValueError("v0.3a submissions require v0.2 setup/Ready")
        self.clock_seconds = self.initial_clock
        self.position = MountPosition.from_axis(self.starting_axis)
        self.initial_band = self.position.control.band
        self.initiator = Side.TOP
        self.history = RunHistory()
        self.top = Competitor(
            side=Side.TOP, name="Top", behavior=TopBehavior.PRESSURE
        )
        self.bottom = Competitor(
            side=Side.BOTTOM, name="Bottom", behavior=BottomBehavior.ESCAPE
        )
        self.top_behavior_stamina_meter = BehaviorStaminaMeter()
        self.bottom_behavior_stamina_meter = BehaviorStaminaMeter()
        self.setup_state = SetupState.for_targets(self.setup_policy.target_action_ids)
        self.submission_state = SubmissionState()

    @property
    def axis(self) -> float:
        return self.position.reported_axis

    @property
    def band(self) -> Band:
        return self.position.control.band

    @property
    def ended(self) -> bool:
        return self.clock_seconds <= 0 or self.position.broken or self.submission_tapped

    @property
    def elapsed_simulated_time(self) -> int:
        return self.initial_clock - self.clock_seconds

    @property
    def mount_duration(self) -> int:
        return self.elapsed_simulated_time

    def competitor(self, side: Side) -> Competitor:
        return self.top if side is Side.TOP else self.bottom

    def setup_tier(self, action_id: str) -> SetupTier:
        return self.setup_state.tier(action_id)

    def legal_action_ids(self, side: Side | None = None) -> tuple[str, ...]:
        acting_side = self.initiator if side is None else side
        all_actions = self.engine.catalog.actions_for(acting_side)
        if not self.enable_v02_setup:
            legal = [action.id for action in all_actions]
        else:
            legal = []
            for action in all_actions:
                setup_rule = self.setup_policy.rule_for_target(action.id)
                if setup_rule is None or self.setup_state.is_ready(action.id):
                    legal.append(action.id)

        if (
            self.enable_v03_submissions
            and acting_side is Side.TOP
            and self.submission_state.active
            and self.band in {Band.STRONG, Band.LOCKED}
        ):
            legal.append(TOP_AMERICANA_SUBMISSION_FINISH)
        return tuple(legal)

    def _validate_action_legality(self, action_id: str) -> None:
        if action_id not in self.legal_action_ids():
            if action_id == TOP_AMERICANA_SUBMISSION_FINISH:
                detail = f"submission stage {self.submission_state.stage}"
            elif self.enable_v02_setup and action_id in self.setup_policy.target_action_ids:
                detail = f"setup tier {self.setup_tier(action_id).display}"
            else:
                detail = "current match state"
            raise ValueError(
                f"Action {action_id!r} is not legal at {detail}; "
                f"legal actions: {self.legal_action_ids()}"
            )

    def legal_response_ids(self, action_id: str) -> tuple[str, ...]:
        action = (
            MODERN_ENTITY_BY_ID[action_id]
            if action_id == TOP_AMERICANA_SUBMISSION_FINISH
            else self.engine.catalog.get(action_id)
        )
        if action.side is not self.initiator:
            raise ValueError(
                f"{action.canonical_name} belongs to {action.side.value}, "
                f"but current initiator is {self.initiator.value}"
            )
        self._validate_action_legality(action_id)
        all_ids = tuple(
            response.id
            for response in self.engine.catalog.responses_for(action.side.opponent)
        )
        if action_id == TOP_AMERICANA_SUBMISSION_FINISH:
            return all_ids
        if not self.enable_v02_setup or not self.setup_state.is_ready(action_id):
            return all_ids

        ready_ids = self.setup_policy.ready_response_ids(action_id)
        if ready_ids is None:
            return all_ids
        legal = tuple(response_id for response_id in ready_ids if response_id in all_ids)
        if not legal:
            raise RuntimeError(
                f"Ready setup for {action_id!r} leaves no legal responses"
            )
        return legal

    def _validate_response_legality(self, action_id: str, response_id: str) -> None:
        legal = self.legal_response_ids(action_id)
        if response_id not in legal:
            detail = (
                f"submission stage {self.submission_state.stage.value}"
                if action_id == TOP_AMERICANA_SUBMISSION_FINISH
                and self.submission_state.stage is not None
                else f"setup tier {self.setup_tier(action_id).display}"
                if self.enable_v02_setup and action_id in self.setup_policy.target_action_ids
                else "current match state"
            )
            raise ValueError(
                f"Response {response_id!r} is not legal against {action_id!r} "
                f"at {detail}; legal responses: {legal}"
            )

    def _apply_setup_after_attempt(
        self,
        *,
        action_id: str,
        resolution,
        target_was_ready: bool,
    ) -> None:
        if not self.enable_v02_setup:
            return

        builder_target = self.setup_policy.target_for_builder(action_id)
        if (
            builder_target is not None
            and self.setup_policy.setup_advances_from(resolution)
            and not self.setup_state.is_ready(builder_target)
        ):
            change = self.setup_state.advance(builder_target)
            self.history.setup_change_history.append(
                f"{action_id}->{builder_target}:"
                f"{change.before.display}->{change.after.display}"
            )

        if target_was_ready:
            change = self.setup_state.consume(action_id)
            self.history.setup_consumption_history.append(
                f"{action_id}:{change.before.display}->{change.after.display}"
            )

    def _break_submission_if_not_dominant(self, *, reason: str) -> None:
        if (
            not self.enable_v03_submissions
            or not self.submission_state.active
            or self.position.broken
            or self.band in {Band.STRONG, Band.LOCKED}
        ):
            return
        before = self.submission_state.stage
        change = self.submission_state.break_track()
        if before is None or change.after is not None:
            raise AssertionError("dominance-loss break must clear an active submission")
        self.history.submission_change_history.append(
            f"{before.value}->None:{reason}"
        )

    def set_behaviors(
        self,
        *,
        top: TopBehavior | None = None,
        bottom: BottomBehavior | None = None,
    ) -> None:
        if top is not None:
            self.top.set_behavior(top)
        if bottom is not None:
            self.bottom.set_behavior(bottom)

    def _behaviors(
        self,
        top_behavior: TopBehavior | None,
        bottom_behavior: BottomBehavior | None,
    ) -> tuple[TopBehavior, BottomBehavior]:
        if top_behavior is not None or bottom_behavior is not None:
            warnings.warn(
                "Passing behaviors to drift()/decide() is legacy Mount-v0 "
                "compatibility; set behavior on match.top/match.bottom instead.",
                DeprecationWarning,
                stacklevel=3,
            )
        self.set_behaviors(top=top_behavior, bottom=bottom_behavior)
        if not isinstance(self.top.behavior, TopBehavior):
            raise TypeError("Top competitor behavior is not a TopBehavior")
        if not isinstance(self.bottom.behavior, BottomBehavior):
            raise TypeError("Bottom competitor behavior is not a BottomBehavior")
        return self.top.behavior, self.bottom.behavior

    def drift(
        self,
        top_behavior: TopBehavior | None = None,
        bottom_behavior: BottomBehavior | None = None,
    ):
        top_behavior, bottom_behavior = self._behaviors(
            top_behavior, bottom_behavior
        )
        result = self.engine.simulate_drift(
            axis=self.position.control.value,
            band=self.band,
            clock_seconds=self.clock_seconds,
            duration_seconds=self.interval_seconds,
            top_behavior=top_behavior,
            bottom_behavior=bottom_behavior,
        )
        self.position.apply_control(result.end_axis, result.end_band)
        self.clock_seconds = result.end_clock
        self.history.top_behavior_history.append(top_behavior.value)
        self.history.bottom_behavior_history.append(bottom_behavior.value)
        if self.clock_seconds == 0 and self.exit_destination is None:
            self.exit_reason = "TIMEOUT — Mount retained"
        return result

    def advance(self) -> AdvanceResult:
        """v0.1c normal-speed drift plus behavior stamina economy.

        Frozen drift() remains stamina-free for Mount-v0 compatibility.
        """
        top_behavior, bottom_behavior = self._behaviors(None, None)
        drift = self.drift()
        self._break_submission_if_not_dominant(reason="lost-dominance")
        duration = drift.start_clock - drift.end_clock

        top_stamina = self.behavior_stamina_policy.apply(
            pool=self.top.stamina,
            behavior=top_behavior,
            duration_seconds=duration,
            meter=self.top_behavior_stamina_meter,
        )
        bottom_stamina = self.behavior_stamina_policy.apply(
            pool=self.bottom.stamina,
            behavior=bottom_behavior,
            duration_seconds=duration,
            meter=self.bottom_behavior_stamina_meter,
        )
        self.history.top_behavior_stamina_history.append(top_stamina.net_change)
        self.history.bottom_behavior_stamina_history.append(bottom_stamina.net_change)
        return AdvanceResult(
            drift=drift,
            top_stamina=top_stamina,
            bottom_stamina=bottom_stamina,
        )

    def _resolve(
        self,
        *,
        action_id: str,
        response_id: str,
        top_behavior: TopBehavior,
        bottom_behavior: BottomBehavior,
        external_grade_modifier: int = 0,
        post_positional_grade_override=None,
    ):
        if self.clock_seconds <= 0:
            raise RuntimeError("Cannot resolve a decision after timeout")
        if self.position.broken:
            raise RuntimeError("Cannot resolve a decision after Mount is broken")
        return self.engine.resolve_action(
            axis=self.position.control.value,
            band=self.band,
            initiator=self.initiator,
            action_id=action_id,
            response_id=response_id,
            top_behavior=top_behavior,
            bottom_behavior=bottom_behavior,
            external_grade_modifier=external_grade_modifier,
            post_positional_grade_override=post_positional_grade_override,
        )

    def _resolve_submission_stage(
        self,
        *,
        response_id: str,
        top_behavior: TopBehavior,
        bottom_behavior: BottomBehavior,
        external_grade_modifier: int = 0,
    ):
        if not self.enable_v03_submissions or not self.submission_state.active:
            raise RuntimeError("Americana submission stage is not active")
        if self.initiator is not Side.TOP:
            raise RuntimeError("Only Top can advance the v0.3a Americana track")

        # Grade authority is still the frozen Americana row. v0.3a does not add
        # matchup-table entries; it interprets that grade on a submission track.
        proxy = self.engine.resolve_action(
            axis=self.position.control.value,
            band=self.band,
            initiator=Side.TOP,
            action_id=TOP_AMERICANA_ARM_ISOLATION,
            response_id=response_id,
            top_behavior=top_behavior,
            bottom_behavior=bottom_behavior,
            external_grade_modifier=external_grade_modifier,
        )
        defended = not proxy.final_grade.successful
        proposed_axis = (
            round(self.axis - 1.0, 10)
            if defended
            else self.axis
        )
        axis_after = self.engine.rules.clamp_axis(proposed_axis)
        band_after, changes = self.engine.rules.update_band(axis_after, self.band)
        return replace(
            proxy,
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            axis_delta=round(axis_after - self.axis, 10),
            proposed_axis=proposed_axis,
            axis_after=axis_after,
            band_after=band_after,
            band_changes=changes,
            failure_clamp_used=False,
            floor_clamp_used=False,
            escape_threshold_reached=False,
            exit_capable_action=False,
            exit_destination=None,
        )

    def preview_submission_stage(
        self,
        *,
        response_id: str,
        external_grade_modifier: int = 0,
    ):
        """Resolve the current submission-stage exchange without mutating match state."""
        top_behavior, bottom_behavior = self._behaviors(None, None)
        return self._resolve_submission_stage(
            response_id=response_id,
            top_behavior=top_behavior,
            bottom_behavior=bottom_behavior,
            external_grade_modifier=external_grade_modifier,
        )

    def _apply_submission_after_attempt(
        self,
        *,
        action_id: str,
        resolution,
        target_was_ready: bool,
        stage_before: SubmissionStage | None,
    ) -> None:
        if not self.enable_v03_submissions:
            return

        if (
            action_id == TOP_AMERICANA_ARM_ISOLATION
            and target_was_ready
            and resolution.initiator is Side.TOP
            and resolution.band_before in {Band.STRONG, Band.LOCKED}
            and resolution.final_grade.successful
        ):
            change = self.submission_state.start()
            self.history.submission_change_history.append(
                f"entry:{change.before}->{change.after.value}"
            )
            return

        if action_id != TOP_AMERICANA_SUBMISSION_FINISH:
            return
        if stage_before is None:
            raise RuntimeError("Submission-stage attempt missing active stage")

        self.history.submission_attempt_history.append(stage_before.value)
        if resolution.final_grade.successful:
            change = self.submission_state.advance()
            if change.tapped:
                self.history.submission_change_history.append(
                    f"{stage_before.value}->Tap"
                )
                self.history.submission_tap_count += 1
                self.submission_tapped = True
                self.exit_reason = "TAP — Americana"
            else:
                self.history.submission_change_history.append(
                    f"{stage_before.value}->{change.after.value}"
                )
        else:
            change = self.submission_state.defend()
            after_label = change.after.value if change.after is not None else "None"
            self.history.submission_change_history.append(
                f"{stage_before.value}->{after_label}:defended"
            )
            self.history.submission_defense_history.append(
                f"{stage_before.value}->{after_label}:"
                f"{resolution.final_grade.display}:"
                f"{resolution.axis_before:+.2f}->{resolution.axis_after:+.2f}"
            )

    def _apply_resolution(self, result) -> None:
        self.history.initiated_action_history.append(result.action_id)
        self.history.response_history.append(result.response_id)
        self.history.raw_grade_history.append(result.raw_grade.display)
        self.history.modified_grade_history.append(result.final_grade.display)
        if result.initiator is Side.TOP:
            self.history.top_initiation_count += 1
        else:
            self.history.bottom_initiation_count += 1
        self.history.clamp_count += (
            int(result.failure_clamp_used) + int(result.floor_clamp_used)
        )
        self.history.escape_threshold_reached |= result.escape_threshold_reached

        if result.exit_destination is not None:
            self.position.break_mount(result.axis_after)
            self.exit_destination = result.exit_destination
            action = self.engine.catalog.get(result.action_id)
            self.exit_reason = (
                f"{action.canonical_name} reached the escape threshold with final grade "
                f"{result.final_grade.display}"
            )
        else:
            self.position.apply_control(result.axis_after, result.band_after)
            self.initiator = self.initiator.opponent

    def decide(
        self,
        *,
        action_id: str,
        response_id: str,
        top_behavior: TopBehavior | None = None,
        bottom_behavior: BottomBehavior | None = None,
    ):
        """Frozen v0 decision path.

        This method deliberately does not spend stamina. New v0.1b callers use
        attempt(); mount_v0 callers retain their historical semantics.
        """
        top_behavior, bottom_behavior = self._behaviors(
            top_behavior, bottom_behavior
        )
        result = self._resolve(
            action_id=action_id,
            response_id=response_id,
            top_behavior=top_behavior,
            bottom_behavior=bottom_behavior,
        )
        self._apply_resolution(result)
        return result

    def reset_window(self) -> ResetWindowResult:
        """Yield the current decision window without initiating a technique.

        This is modern v0.1 scaffolding for the event-driven design: no action
        stamina is charged, no response is requested, and no immediate axis
        change occurs. Initiative passes to the opponent; another normal-speed
        interval must occur before the next decision window.
        """
        if self.clock_seconds <= 0:
            raise RuntimeError("Cannot reset a decision window after timeout")
        if self.position.broken:
            raise RuntimeError("Cannot reset a decision window after Mount is broken")

        initiator = self.initiator
        result = ResetWindowResult(
            initiator=initiator,
            next_initiator=initiator.opponent,
            clock_seconds=self.clock_seconds,
            axis=self.axis,
            band=self.band,
            stamina=self.competitor(initiator).stamina.current,
        )
        self.history.reset_window_history.append(initiator.value)
        self.initiator = initiator.opponent
        return result

    def attempt(
        self,
        *,
        action_id: str,
        response_id: str,
        commitment: Commitment,
    ) -> AttemptResult:
        """Resolve a v0.1 action with commitment and exhaustion policy.

        Both stamina bands are read before the initiator's action cost is paid.
        Initiator Exhausted shifts the action down one grade; responder Exhausted
        shifts it up one grade. If both are Exhausted the modifiers cancel.
        Responding still has no direct stamina cost.
        """
        top_behavior, bottom_behavior = self._behaviors(None, None)
        initiator = self.initiator
        self._validate_action_legality(action_id)
        self._validate_response_legality(action_id, response_id)
        target_was_ready = (
            self.enable_v02_setup
            and action_id in self.setup_policy.target_action_ids
            and self.setup_state.is_ready(action_id)
        )
        submission_stage_before = (
            self.submission_state.stage
            if action_id == TOP_AMERICANA_SUBMISSION_FINISH
            else None
        )
        ready_grade_override = (
            self.setup_policy.ready_final_grade_override(
                action_id,
                response_id,
            )
            if target_was_ready
            else None
        )
        pool = self.competitor(initiator).stamina
        responder_pool = self.competitor(initiator.opponent).stamina
        stamina_band_before_action = pool.band
        responder_stamina_band_before_action = responder_pool.band
        initiator_exhaustion_modifier = (
            self.exhaustion_policy.initiator_grade_modifier(
                stamina_band_before_action
            )
        )
        responder_exhaustion_modifier = (
            self.exhaustion_policy.responder_grade_modifier(
                responder_stamina_band_before_action
            )
        )
        exhaustion_modifier = (
            initiator_exhaustion_modifier
            + responder_exhaustion_modifier
        )

        if action_id == TOP_AMERICANA_SUBMISSION_FINISH:
            base_resolution = self._resolve_submission_stage(
                response_id=response_id,
                top_behavior=top_behavior,
                bottom_behavior=bottom_behavior,
            )
            result = (
                base_resolution
                if exhaustion_modifier == 0
                else self._resolve_submission_stage(
                    response_id=response_id,
                    top_behavior=top_behavior,
                    bottom_behavior=bottom_behavior,
                    external_grade_modifier=exhaustion_modifier,
                )
            )
        else:
            base_resolution = self._resolve(
                action_id=action_id,
                response_id=response_id,
                top_behavior=top_behavior,
                bottom_behavior=bottom_behavior,
                post_positional_grade_override=ready_grade_override,
            )
            result = (
                base_resolution
                if exhaustion_modifier == 0
                else self._resolve(
                    action_id=action_id,
                    response_id=response_id,
                    top_behavior=top_behavior,
                    bottom_behavior=bottom_behavior,
                    external_grade_modifier=exhaustion_modifier,
                    post_positional_grade_override=ready_grade_override,
                )
            )

        requested_cost = self.stamina_cost_policy.cost(commitment)
        effective_commitment = self.stamina_cost_policy.effective_commitment(
            requested=commitment,
            available_stamina=pool.current,
        )
        effective_cost = (
            self.stamina_cost_policy.cost(effective_commitment)
            if effective_commitment is not None
            else 0
        )
        funding_gap = requested_cost - effective_cost
        attempt = ActionAttempt(
            initiator=initiator,
            action_id=action_id,
            requested_commitment=commitment,
            effective_commitment=effective_commitment,
        )
        spend = pool.spend_up_to(effective_cost)

        self.history.commitment_history.append(commitment.value)
        self.history.effective_commitment_history.append(
            effective_commitment.value if effective_commitment is not None else "UNFUNDED"
        )
        self.history.commitment_initiator_history.append(initiator.value)
        self.history.stamina_requested_history.append(requested_cost)
        self.history.stamina_charged_history.append(spend.charged)
        self.history.stamina_shortfall_history.append(spend.shortfall)
        self.history.stamina_funding_gap_history.append(funding_gap)
        self.history.stamina_band_at_initiation_history.append(
            stamina_band_before_action.value
        )
        self.history.responder_stamina_band_history.append(
            responder_stamina_band_before_action.value
        )
        self.history.initiator_exhaustion_modifier_history.append(
            initiator_exhaustion_modifier
        )
        self.history.responder_exhaustion_modifier_history.append(
            responder_exhaustion_modifier
        )
        self.history.exhaustion_modifier_history.append(exhaustion_modifier)

        self._apply_resolution(result)
        self._apply_setup_after_attempt(
            action_id=action_id,
            resolution=result,
            target_was_ready=target_was_ready,
        )
        self._apply_submission_after_attempt(
            action_id=action_id,
            resolution=result,
            target_was_ready=target_was_ready,
            stage_before=submission_stage_before,
        )
        self._break_submission_if_not_dominant(reason="lost-dominance")
        return AttemptResult(
            attempt=attempt,
            requested_cost=requested_cost,
            effective_cost=effective_cost,
            funding_gap=funding_gap,
            stamina=spend,
            stamina_band_before_action=stamina_band_before_action,
            responder_stamina_band_before_action=(
                responder_stamina_band_before_action
            ),
            initiator_exhaustion_modifier=initiator_exhaustion_modifier,
            responder_exhaustion_modifier=responder_exhaustion_modifier,
            exhaustion_modifier=exhaustion_modifier,
            base_resolution=base_resolution,
            resolution=result,
        )


MountRun = MountMatch
