from __future__ import annotations

import warnings
from dataclasses import dataclass, field, replace

from ..domain.action import ActionAttempt, AttemptResult, Commitment, ResetWindowResult
from ..domain.competitor import Competitor
from ..domain.model import (
    Band,
    BottomBehavior,
    ExitDestination,
    Grade,
    RunHistory,
    Side,
    TopBehavior,
)
from ..domain.recognition import (
    CommitmentRecognitionPolicy,
    CommitmentRecognitionRead,
    DEFAULT_COMMITMENT_RECOGNITION_POLICY,
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
from .stalling import (
    STALLING_THRESHOLD_SECONDS,
    StallingConsequence,
    StallingTracker,
)
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
    enable_v03b_stalling: bool = False
    enable_v04_commitment_semantics: bool = False
    enable_v04b_recognition: bool = False
    enable_stamina_settlement_rules: bool = False
    enable_unfunded_responder_cost_waiver: bool = False
    enable_supplemental_hold_settlement: bool = False
    recognition_policy: CommitmentRecognitionPolicy = field(
        default_factory=lambda: DEFAULT_COMMITMENT_RECOGNITION_POLICY,
        repr=False,
    )
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
    stalling_tracker: StallingTracker = field(init=False)
    free_initiative_pending: bool = field(init=False, default=False)
    free_initiative_beneficiary: Side | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        if self.initial_clock <= 0:
            raise ValueError("clock must be > 0")
        if self.interval_seconds <= 0:
            raise ValueError("interval must be > 0")
        if self.enable_v03_submissions and not self.enable_v02_setup:
            raise ValueError("v0.3a submissions require v0.2 setup/Ready")
        if self.enable_v03b_stalling and not self.enable_v03_submissions:
            raise ValueError("v0.3b stalling requires v0.3a submissions")
        if self.enable_v04b_recognition and not self.enable_v04_commitment_semantics:
            raise ValueError("v0.4b Recognition requires v0.4a commitment semantics")
        if (
            self.enable_stamina_settlement_rules
            or self.enable_unfunded_responder_cost_waiver
            or self.enable_supplemental_hold_settlement
        ) and not self.enable_v04_commitment_semantics:
            raise ValueError(
                "stamina settlement rules require v0.4a commitment semantics"
            )
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
        self.stalling_tracker = StallingTracker(
            threshold_seconds=STALLING_THRESHOLD_SECONDS
        )

    @property
    def unfunded_responder_cost_waiver_enabled(self) -> bool:
        return (
            self.enable_stamina_settlement_rules
            or self.enable_unfunded_responder_cost_waiver
        )

    @property
    def supplemental_hold_settlement_enabled(self) -> bool:
        return (
            self.enable_stamina_settlement_rules
            or self.enable_supplemental_hold_settlement
        )

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
        ):
            legal.append(TOP_AMERICANA_SUBMISSION_FINISH)
        return tuple(legal)

    def advancement_clock(self, side: Side) -> int:
        return self.stalling_tracker.clock(side)

    def stalling_warned(self, side: Side) -> bool:
        return self.stalling_tracker.warned[side]

    def consume_free_initiative_window(self) -> Side | None:
        if not self.free_initiative_pending:
            return None
        beneficiary = self.free_initiative_beneficiary
        if beneficiary is None:
            raise RuntimeError("free initiative window is pending without beneficiary")
        if self.initiator is not beneficiary:
            raise RuntimeError(
                "free initiative beneficiary does not own current initiative"
            )
        self.free_initiative_pending = False
        self.free_initiative_beneficiary = None
        return beneficiary

    def _progress_preview(self, *, action_id: str, response_id: str):
        top_behavior, bottom_behavior = self._behaviors(None, None)
        initiator = self.initiator
        initiator_band = self.competitor(initiator).stamina.band
        responder_band = self.competitor(initiator.opponent).stamina.band
        exhaustion_modifier = self.exhaustion_policy.exchange_grade_modifier(
            initiator_band=initiator_band,
            responder_band=responder_band,
        )

        if action_id == TOP_AMERICANA_SUBMISSION_FINISH:
            return self._resolve_submission_stage(
                response_id=response_id,
                top_behavior=top_behavior,
                bottom_behavior=bottom_behavior,
                external_grade_modifier=exhaustion_modifier,
            )

        target_was_ready = (
            self.enable_v02_setup
            and action_id in self.setup_policy.target_action_ids
            and self.setup_state.is_ready(action_id)
        )
        ready_override = (
            self.setup_policy.ready_final_grade_override(
                action_id,
                response_id,
            )
            if target_was_ready
            else None
        )
        return self._resolve(
            action_id=action_id,
            response_id=response_id,
            top_behavior=top_behavior,
            bottom_behavior=bottom_behavior,
            external_grade_modifier=exhaustion_modifier,
            post_positional_grade_override=ready_override,
        )

    def _result_has_progress_channel(
        self,
        *,
        action_id: str,
        result,
    ) -> bool:
        initiator = self.initiator

        if result.exit_destination is not None:
            return True

        if (
            action_id == TOP_AMERICANA_SUBMISSION_FINISH
            and self.enable_v03_submissions
            and self.submission_state.active
            and result.final_grade.successful
        ):
            return True

        if (
            action_id == TOP_AMERICANA_ARM_ISOLATION
            and self.enable_v03_submissions
            and initiator is Side.TOP
            and self.setup_state.is_ready(action_id)
            and result.band_before in {Band.STRONG, Band.LOCKED}
            and result.final_grade.successful
        ):
            return True

        if self.enable_v02_setup:
            target = self.setup_policy.target_for_builder(action_id)
            if (
                target is not None
                and not self.setup_state.is_ready(target)
                and self.setup_policy.setup_advances_from(result)
            ):
                return True

        realized = result.axis_after - result.axis_before
        if initiator is Side.TOP and realized > 1e-12:
            return True
        if initiator is Side.BOTTOM and realized < -1e-12:
            return True
        return False

    def action_is_progress_capable(self, action_id: str) -> bool:
        self._validate_action_legality(action_id)
        for response_id in self.legal_response_ids(action_id):
            result = self._progress_preview(
                action_id=action_id,
                response_id=response_id,
            )
            if self._result_has_progress_channel(
                action_id=action_id,
                result=result,
            ):
                return True
        return False

    def progress_capable_action_ids(self) -> tuple[str, ...]:
        return tuple(
            action_id
            for action_id in self.legal_action_ids()
            if self.action_is_progress_capable(action_id)
        )

    def _record_progress_opportunity(
        self,
        *,
        side: Side,
        action_ids: tuple[str, ...],
    ) -> None:
        self.history.stalling_progress_opportunity_history.append(
            f"{side.value}@{self.elapsed_simulated_time}s:"
            + (",".join(action_ids) if action_ids else "none")
        )

    @property
    def response_commitment_enabled(self) -> bool:
        """Runtime capability used by the v0.3a Gate-B auto-expiry check."""
        return self.enable_v04_commitment_semantics

    @property
    def recognition_enabled(self) -> bool:
        """Real runtime capability for the v0.4b information layer."""
        return self.enable_v04b_recognition

    def recognize_commitment(
        self,
        *,
        requested: Commitment,
        intent_roll: int,
        capability_roll: int,
    ) -> CommitmentRecognitionRead:
        if not self.enable_v04b_recognition:
            raise RuntimeError("v0.4b Recognition is not enabled")
        pool = self.competitor(self.initiator).stamina
        effective = self.stamina_cost_policy.effective_commitment(
            requested=requested,
            available_stamina=pool.current,
        )
        return self.recognition_policy.read(
            requested=requested,
            effective=effective,
            intent_roll=intent_roll,
            capability_roll=capability_roll,
        )

    @staticmethod
    def _commitment_rank(commitment: Commitment | None) -> int:
        return {
            None: 0,
            Commitment.LOW: 1,
            Commitment.MEDIUM: 2,
            Commitment.HIGH: 3,
        }[commitment]

    @staticmethod
    def _initiator_commitment_modifier(
        commitment: Commitment | None,
        grade: Grade,
    ) -> int:
        """Magnitude transform applied after exhaustion.

        UNFUNDED deliberately inherits LOW's magnitude ceiling so inability to
        fund LOW cannot become stronger than LOW.
        """
        effective = Commitment.LOW if commitment is None else commitment
        if effective is Commitment.HIGH:
            if grade is Grade.SUCCESS:
                return 1
            if grade is Grade.FAILURE:
                return -1
        elif effective is Commitment.LOW:
            if grade is Grade.STRONG_SUCCESS:
                return -1
            if grade is Grade.STRONG_FAILURE:
                return 1
        return 0

    @classmethod
    def _response_undercommitment_modifier(
        cls,
        *,
        initiator_commitment: Commitment | None,
        responder_commitment: Commitment | None,
    ) -> int:
        return (
            1
            if cls._commitment_rank(responder_commitment)
            < cls._commitment_rank(initiator_commitment)
            else 0
        )

    @classmethod
    def _commitment_grade_transform(
        cls,
        *,
        grade_after_exhaustion: Grade,
        initiator_commitment: Commitment | None,
        responder_commitment: Commitment | None,
    ) -> tuple[Grade, int, int]:
        """Apply v0.4a commitment steps in the frozen sequential order."""
        commitment_modifier = cls._initiator_commitment_modifier(
            initiator_commitment,
            grade_after_exhaustion,
        )
        after_magnitude = grade_after_exhaustion.shift(
            commitment_modifier
        )
        response_modifier = cls._response_undercommitment_modifier(
            initiator_commitment=initiator_commitment,
            responder_commitment=responder_commitment,
        )
        final_grade = after_magnitude.shift(response_modifier)
        return final_grade, commitment_modifier, response_modifier


    def _resolve_attempt_resolution(
        self,
        *,
        action_id: str,
        response_id: str,
        top_behavior: TopBehavior,
        bottom_behavior: BottomBehavior,
        ready_grade_override: Grade | None,
        exhaustion_modifier: int,
        effective_commitment: Commitment | None,
        response_effective_commitment: Commitment | None,
    ):
        def resolve(external_grade_modifier: int):
            if action_id == TOP_AMERICANA_SUBMISSION_FINISH:
                return self._resolve_submission_stage(
                    response_id=response_id,
                    top_behavior=top_behavior,
                    bottom_behavior=bottom_behavior,
                    external_grade_modifier=external_grade_modifier,
                )
            return self._resolve(
                action_id=action_id,
                response_id=response_id,
                top_behavior=top_behavior,
                bottom_behavior=bottom_behavior,
                external_grade_modifier=external_grade_modifier,
                post_positional_grade_override=ready_grade_override,
            )

        base_resolution = resolve(0)
        exhausted_resolution = (
            base_resolution
            if exhaustion_modifier == 0
            else resolve(exhaustion_modifier)
        )
        exhausted_grade = exhausted_resolution.final_grade
        if not self.enable_v04_commitment_semantics:
            return base_resolution, exhausted_resolution, 0, 0

        (
            final_grade,
            commitment_modifier,
            response_modifier,
        ) = self._commitment_grade_transform(
            grade_after_exhaustion=exhausted_grade,
            initiator_commitment=effective_commitment,
            responder_commitment=response_effective_commitment,
        )

        # Preserve the historical exhaustion ResolutionResult exactly whenever
        # v0.4a adds no tactical grade change. When commitment does change the
        # grade, derive the resolver delta from the actual sequential target
        # grade rather than summing modifiers across intermediate clamps.
        if commitment_modifier == 0 and response_modifier == 0:
            result = exhausted_resolution
        else:
            final_delta_from_base = (
                int(final_grade) - int(base_resolution.final_grade)
            )
            result = resolve(final_delta_from_base)
        return (
            base_resolution,
            result,
            commitment_modifier,
            response_modifier,
        )

    def preview_attempt_resolution(
        self,
        *,
        action_id: str,
        response_id: str,
        commitment: Commitment,
        response_commitment: Commitment | None = None,
    ):
        """Preview the same current-exchange math as attempt(), without mutation."""
        top_behavior, bottom_behavior = self._behaviors(None, None)
        initiator = self.initiator
        self._validate_action_legality(action_id)
        self._validate_response_legality(action_id, response_id)

        target_was_ready = (
            self.enable_v02_setup
            and action_id in self.setup_policy.target_action_ids
            and self.setup_state.is_ready(action_id)
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
        exhaustion_modifier = self.exhaustion_policy.exchange_grade_modifier(
            initiator_band=pool.band,
            responder_band=responder_pool.band,
        )
        effective_commitment = self.stamina_cost_policy.effective_commitment(
            requested=commitment,
            available_stamina=pool.current,
        )
        response_effective_commitment = None
        if self.enable_v04_commitment_semantics:
            requested_response = (
                Commitment.MEDIUM
                if response_commitment is None
                else response_commitment
            )
            response_effective_commitment = (
                self.stamina_cost_policy.effective_commitment(
                    requested=requested_response,
                    available_stamina=responder_pool.current,
                )
            )

        _, result, _, _ = self._resolve_attempt_resolution(
            action_id=action_id,
            response_id=response_id,
            top_behavior=top_behavior,
            bottom_behavior=bottom_behavior,
            ready_grade_override=ready_grade_override,
            exhaustion_modifier=exhaustion_modifier,
            effective_commitment=effective_commitment,
            response_effective_commitment=response_effective_commitment,
        )
        return result

    def preview_attempt_resolution_from_effective(
        self,
        *,
        action_id: str,
        response_id: str,
        initiator_effective_commitment: Commitment | None,
        response_commitment: Commitment,
    ):
        """Preview perceived exchange math without consulting hidden initiator truth."""
        top_behavior, bottom_behavior = self._behaviors(None, None)
        initiator = self.initiator
        self._validate_action_legality(action_id)
        self._validate_response_legality(action_id, response_id)

        target_was_ready = (
            self.enable_v02_setup
            and action_id in self.setup_policy.target_action_ids
            and self.setup_state.is_ready(action_id)
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
        exhaustion_modifier = self.exhaustion_policy.exchange_grade_modifier(
            initiator_band=pool.band,
            responder_band=responder_pool.band,
        )
        response_effective_commitment = (
            self.stamina_cost_policy.effective_commitment(
                requested=response_commitment,
                available_stamina=responder_pool.current,
            )
        )

        _, result, _, _ = self._resolve_attempt_resolution(
            action_id=action_id,
            response_id=response_id,
            top_behavior=top_behavior,
            bottom_behavior=bottom_behavior,
            ready_grade_override=ready_grade_override,
            exhaustion_modifier=exhaustion_modifier,
            effective_commitment=initiator_effective_commitment,
            response_effective_commitment=response_effective_commitment,
        )
        return result

    def _record_engagement(
        self,
        *,
        initiator: Side,
        action_id: str,
        initiator_progress: bool = True,
        defender_engaged: bool = True,
    ) -> None:
        if initiator_progress:
            self.stalling_tracker.engage(initiator)
            self.history.stalling_progress_engagement_history.append(
                f"{initiator.value}@{self.elapsed_simulated_time}s:{action_id}"
            )
        if defender_engaged:
            self.stalling_tracker.engage(initiator.opponent)
            self.history.stalling_defensive_engagement_history.append(
                f"{initiator.opponent.value}@{self.elapsed_simulated_time}s:"
                f"defend:{action_id}"
            )
        self.history.stalling_clock_history.append(
            f"engage@{self.elapsed_simulated_time}s:"
            f"top={self.advancement_clock(Side.TOP)},"
            f"bottom={self.advancement_clock(Side.BOTTOM)}"
        )

    @staticmethod
    def _stalling_penalty_target(
        *,
        offender: Side,
        band: Band,
    ) -> float | None:
        if offender is Side.TOP:
            return {
                Band.LOCKED: 2.80,
                Band.STRONG: 1.80,
                Band.STABLE: 0.80,
            }.get(band)
        return {
            Band.LOOSE: 1.20,
            Band.STABLE: 2.20,
            Band.STRONG: 3.20,
        }.get(band)

    def _apply_stalling_penalty(
        self,
        *,
        offender: Side,
    ) -> tuple[float, float, bool]:
        axis_before = self.axis
        band_before = self.band
        target_axis = self._stalling_penalty_target(
            offender=offender,
            band=band_before,
        )

        if target_axis is None:
            beneficiary = offender.opponent
            self.free_initiative_pending = True
            self.free_initiative_beneficiary = beneficiary
            self.history.stalling_boundary_history.append(
                f"{offender.value}@{self.elapsed_simulated_time}s:"
                f"{band_before.value}:{axis_before:+.2f}:FREE_INITIATIVE"
            )
            self.history.stalling_free_initiative_history.append(
                f"{beneficiary.value}@{self.elapsed_simulated_time}s"
            )
            return axis_before, axis_before, True

        if offender is Side.TOP and target_axis >= axis_before:
            raise RuntimeError("Top stalling penalty must move axis toward Bottom")
        if offender is Side.BOTTOM and target_axis <= axis_before:
            raise RuntimeError("Bottom stalling penalty must move axis toward Top")

        band_after, changes = self.engine.rules.update_band(
            target_axis,
            band_before,
        )
        if len(changes) != 1:
            raise RuntimeError(
                "stalling penalty must move exactly one visible Mount band"
            )
        self.position.apply_control(target_axis, band_after)
        self.history.stalling_penalty_history.append(
            f"{offender.value}@{self.elapsed_simulated_time}s:"
            f"{band_before.value}->{band_after.value}:"
            f"{axis_before:+.2f}->{self.axis:+.2f}"
        )
        return axis_before, self.axis, False

    def _apply_stalling_position_reset_rung(
        self,
        *,
        offender: Side,
    ) -> tuple[str, float, float, bool]:
        """Apply offense-3+ without ever helping the offender.

        Returns (effect, axis_before, axis_after, free_initiative), where effect
        is one of POSITION_RESET, PENALTY, or FREE_INITIATIVE.
        """
        axis_before = self.axis
        band_before = self.band
        one_band_target = self._stalling_penalty_target(
            offender=offender,
            band=band_before,
        )

        # Bottom offense can never use canonical +1.50 because that can move
        # Mount control toward Bottom. Use the ordinary one-band/free-window
        # consequence toward Top instead.
        if offender is Side.BOTTOM or one_band_target is None:
            before, after, free = self._apply_stalling_penalty(
                offender=offender,
            )
            return (
                "FREE_INITIATIVE" if free else "PENALTY",
                before,
                after,
                free,
            )

        # Top offense moves toward Bottom. The canonical reset is allowed only
        # when it is at least as severe as the current one-band consequence.
        target_axis = min(DEFAULT_AXIS, one_band_target)
        if target_axis == one_band_target:
            before, after, free = self._apply_stalling_penalty(
                offender=offender,
            )
            return (
                "FREE_INITIATIVE" if free else "PENALTY",
                before,
                after,
                free,
            )

        if target_axis >= axis_before:
            raise RuntimeError("Top Position Reset must move axis toward Bottom")

        reset_band = self.engine.rules.initial_band(target_axis)
        self.position.apply_control(target_axis, reset_band)
        self.history.stalling_position_reset_history.append(
            f"{offender.value}@{self.elapsed_simulated_time}s:"
            f"{band_before.value}->{reset_band.value}:"
            f"{axis_before:+.2f}->{self.axis:+.2f}"
        )
        return "POSITION_RESET", axis_before, self.axis, False

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
            ready_ids = self.setup_policy.ready_response_ids(
                TOP_AMERICANA_ARM_ISOLATION
            )
            if ready_ids is None:
                raise RuntimeError(
                    "Americana submission stage has no inherited isolation defenses"
                )
            legal = tuple(
                response_id for response_id in ready_ids if response_id in all_ids
            )
            if not legal:
                raise RuntimeError(
                    "Americana submission stage leaves no legal responses"
                )
            return legal
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
        duration = drift.start_clock - drift.end_clock

        if self.enable_v03b_stalling:
            self.stalling_tracker.advance(duration)
            self.history.stalling_clock_history.append(
                f"advance@{self.elapsed_simulated_time}s:"
                f"top={self.advancement_clock(Side.TOP)},"
                f"bottom={self.advancement_clock(Side.BOTTOM)}"
            )

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
        defender_won = proxy.final_grade.failed
        proposed_axis = (
            round(self.axis - 1.0, 10)
            if defender_won
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
        requested_commitment: Commitment,
        effective_commitment: Commitment | None,
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
        feint_capped = (
            self.enable_v04_commitment_semantics
            and requested_commitment is Commitment.LOW
        )
        if resolution.final_grade.successful and feint_capped:
            self.history.submission_change_history.append(
                f"{stage_before.value}->{stage_before.value}:feint-capped"
            )
            self.history.submission_feint_cap_history.append(
                f"{stage_before.value}@{self.elapsed_simulated_time}s:"
                f"requested={requested_commitment.value}:effective="
                f"{effective_commitment.value if effective_commitment is not None else 'UNFUNDED'}"
            )
            return

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
        elif resolution.final_grade.failed:
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
        else:
            self.history.submission_change_history.append(
                f"{stage_before.value}->{stage_before.value}:held"
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
        """Yield the current decision window, with optional v0.3b stalling audit."""
        if self.clock_seconds <= 0:
            raise RuntimeError("Cannot reset a decision window after timeout")
        if self.position.broken:
            raise RuntimeError("Cannot reset a decision window after Mount is broken")

        initiator = self.initiator
        progress_ids: tuple[str, ...] = ()
        progress_route_available = False
        advancement_clock = 0
        stalling_offense = False
        stalling_consequence: str | None = None
        penalty_axis_before: float | None = None
        penalty_axis_after: float | None = None
        position_reset = False
        position_reset_axis_before: float | None = None
        position_reset_axis_after: float | None = None
        free_initiative_window = False

        if self.enable_v03b_stalling:
            progress_ids = self.progress_capable_action_ids()
            progress_route_available = bool(progress_ids)
            advancement_clock = self.advancement_clock(initiator)
            self._record_progress_opportunity(
                side=initiator,
                action_ids=progress_ids,
            )
            if progress_route_available:
                self.history.stalling_reset_with_route_history.append(
                    f"{initiator.value}@{self.elapsed_simulated_time}s:"
                    f"clock={advancement_clock}"
                )
            evaluation = self.stalling_tracker.evaluate_reset(
                side=initiator,
                progress_route_available=progress_route_available,
            )
            stalling_offense = evaluation.offense
            stalling_consequence = evaluation.consequence.value
            if evaluation.consequence is StallingConsequence.WARNING:
                self.history.stalling_warning_history.append(
                    f"{initiator.value}@{self.elapsed_simulated_time}s:"
                    f"clock={evaluation.clock_seconds}"
                )
            elif evaluation.consequence is StallingConsequence.PENALTY:
                (
                    penalty_axis_before,
                    penalty_axis_after,
                    free_initiative_window,
                ) = self._apply_stalling_penalty(offender=initiator)
            elif evaluation.consequence is StallingConsequence.POSITION_RESET:
                (
                    applied_effect,
                    effect_axis_before,
                    effect_axis_after,
                    free_initiative_window,
                ) = self._apply_stalling_position_reset_rung(
                    offender=initiator
                )
                if applied_effect == "POSITION_RESET":
                    position_reset = True
                    position_reset_axis_before = effect_axis_before
                    position_reset_axis_after = effect_axis_after
                else:
                    penalty_axis_before = effect_axis_before
                    penalty_axis_after = effect_axis_after

        next_initiator = initiator.opponent
        result = ResetWindowResult(
            initiator=initiator,
            next_initiator=next_initiator,
            clock_seconds=self.clock_seconds,
            axis=self.axis,
            band=self.band,
            stamina=self.competitor(initiator).stamina.current,
            progress_route_available=progress_route_available,
            advancement_clock_seconds=advancement_clock,
            stalling_offense=stalling_offense,
            stalling_consequence=stalling_consequence,
            penalty_axis_before=penalty_axis_before,
            penalty_axis_after=penalty_axis_after,
            position_reset=position_reset,
            position_reset_axis_before=position_reset_axis_before,
            position_reset_axis_after=position_reset_axis_after,
            free_initiative_window=free_initiative_window,
        )
        self.history.reset_window_history.append(initiator.value)
        self.initiator = next_initiator
        return result


    def attempt(
        self,
        *,
        action_id: str,
        response_id: str,
        commitment: Commitment,
        response_commitment: Commitment | None = None,
        recognition_read: CommitmentRecognitionRead | None = None,
    ) -> AttemptResult:
        """Resolve an exchange; Recognition may inform choices but never truth."""
        top_behavior, bottom_behavior = self._behaviors(None, None)
        initiator = self.initiator
        self._validate_action_legality(action_id)
        self._validate_response_legality(action_id, response_id)

        progress_ids: tuple[str, ...] = ()
        action_progress_capable = False
        if self.enable_v03b_stalling:
            progress_ids = self.progress_capable_action_ids()
            self._record_progress_opportunity(
                side=initiator,
                action_ids=progress_ids,
            )
            action_progress_capable = action_id in progress_ids

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

        if self.enable_v04b_recognition:
            if recognition_read is None:
                raise ValueError("v0.4b exchange requires a Recognition read")
            if (
                recognition_read.true_requested is not commitment
                or recognition_read.true_effective is not effective_commitment
            ):
                raise ValueError("Recognition truth does not match current exchange")
        elif recognition_read is not None:
            raise ValueError("Recognition read supplied while v0.4b is disabled")

        response_requested_commitment = None
        response_effective_commitment = None
        response_requested_cost = 0
        response_effective_cost = 0
        response_funding_gap = 0
        if self.enable_v04_commitment_semantics:
            response_requested_commitment = (
                Commitment.MEDIUM
                if response_commitment is None
                else response_commitment
            )
            response_requested_cost = self.stamina_cost_policy.cost(
                response_requested_commitment
            )
            response_effective_commitment = (
                self.stamina_cost_policy.effective_commitment(
                    requested=response_requested_commitment,
                    available_stamina=responder_pool.current,
                )
            )
            response_effective_cost = (
                self.stamina_cost_policy.cost(response_effective_commitment)
                if response_effective_commitment is not None
                else 0
            )
            response_funding_gap = (
                response_requested_cost - response_effective_cost
            )

        (
            base_resolution,
            result,
            commitment_modifier,
            response_modifier,
        ) = self._resolve_attempt_resolution(
            action_id=action_id,
            response_id=response_id,
            top_behavior=top_behavior,
            bottom_behavior=bottom_behavior,
            ready_grade_override=ready_grade_override,
            exhaustion_modifier=exhaustion_modifier,
            effective_commitment=effective_commitment,
            response_effective_commitment=response_effective_commitment,
        )

        attempt = ActionAttempt(
            initiator=initiator,
            action_id=action_id,
            requested_commitment=commitment,
            effective_commitment=effective_commitment,
        )

        feint_capped_active_submission = (
            self.enable_v04_commitment_semantics
            and action_id == TOP_AMERICANA_SUBMISSION_FINISH
            and submission_stage_before is not None
            and commitment is Commitment.LOW
        )
        if self.enable_v03b_stalling and action_progress_capable:
            self._record_engagement(
                initiator=initiator,
                action_id=action_id,
                initiator_progress=not feint_capped_active_submission,
                defender_engaged=True,
            )

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
            requested_commitment=commitment,
            effective_commitment=effective_commitment,
        )

        # Current exchange semantics are fixed before costs are charged.
        spend = pool.spend_up_to(effective_cost)

        response_stamina_waived = 0
        if self.enable_v04_commitment_semantics:
            if (
                self.unfunded_responder_cost_waiver_enabled
                and effective_commitment is None
            ):
                response_stamina_waived = response_effective_cost
                response_spend = responder_pool.spend_up_to(0)
            else:
                response_spend = responder_pool.spend_up_to(
                    response_effective_cost
                )
        else:
            response_spend = None

        submission_hold = (
            action_id == TOP_AMERICANA_SUBMISSION_FINISH
            and result.final_grade is Grade.CONTESTED
        ) or (
            self.enable_v03_submissions
            and action_id == TOP_AMERICANA_ARM_ISOLATION
            and target_was_ready
            and result.final_grade is Grade.CONTESTED
        )
        hold_nominal_cost = 0
        hold_covered_by_response = 0
        hold_spend = None
        if submission_hold:
            hold_nominal_cost = self.stamina_cost_policy.cost(Commitment.LOW)
            if (
                self.unfunded_responder_cost_waiver_enabled
                and effective_commitment is None
            ):
                # Rule 1: an UNFUNDED initiator cannot extract responder
                # stamina through either response commitment or hold.
                hold_request = 0
            elif (
                self.supplemental_hold_settlement_enabled
                and effective_commitment is not None
            ):
                # Rule 2: on funded-initiator holds, response commitment
                # covers the first 3 points of the nominal hold burden.
                response_charged = (
                    response_spend.charged
                    if response_spend is not None
                    else 0
                )
                hold_covered_by_response = min(
                    hold_nominal_cost,
                    response_charged,
                )
                hold_request = max(
                    0,
                    hold_nominal_cost - response_charged,
                )
            else:
                # Legacy hold settlement remains authoritative when Rule 2
                # is disabled, including Rule2-only + UNFUNDED initiator.
                hold_request = hold_nominal_cost

            hold_spend = responder_pool.spend_up_to(hold_request)
            self.history.submission_hold_responder_side_history.append(
                initiator.opponent.value
            )
            self.history.submission_hold_nominal_stamina_history.append(
                hold_nominal_cost
            )
            self.history.submission_hold_covered_by_response_history.append(
                hold_covered_by_response
            )
            self.history.submission_hold_stamina_requested_history.append(
                hold_request
            )
            self.history.submission_hold_stamina_charged_history.append(
                hold_spend.charged
            )
            self.history.submission_hold_stamina_shortfall_history.append(
                hold_spend.shortfall
            )

        self.history.commitment_history.append(commitment.value)
        self.history.effective_commitment_history.append(
            effective_commitment.value
            if effective_commitment is not None
            else "UNFUNDED"
        )
        self.history.commitment_initiator_history.append(initiator.value)
        self.history.stamina_requested_history.append(requested_cost)
        self.history.stamina_charged_history.append(spend.charged)
        self.history.stamina_shortfall_history.append(spend.shortfall)
        self.history.stamina_funding_gap_history.append(funding_gap)
        if self.enable_v04_commitment_semantics:
            self.history.response_requested_commitment_history.append(
                response_requested_commitment.value
                if response_requested_commitment is not None
                else "UNFUNDED"
            )
            self.history.response_effective_commitment_history.append(
                response_effective_commitment.value
                if response_effective_commitment is not None
                else "UNFUNDED"
            )
            self.history.response_stamina_requested_history.append(
                response_requested_cost
            )
            self.history.response_stamina_charged_history.append(
                response_spend.charged if response_spend is not None else 0
            )
            self.history.response_stamina_shortfall_history.append(
                response_spend.shortfall if response_spend is not None else 0
            )
            self.history.response_stamina_funding_gap_history.append(
                response_funding_gap
            )
            self.history.response_stamina_waived_history.append(
                response_stamina_waived
            )
            self.history.initiator_commitment_modifier_history.append(
                commitment_modifier
            )
            self.history.response_undercommitment_modifier_history.append(
                response_modifier
            )
        if recognition_read is not None:
            true_effective_label = (
                recognition_read.true_effective.value
                if recognition_read.true_effective is not None
                else "UNFUNDED"
            )
            perceived_effective_label = (
                recognition_read.perceived_effective.value
                if recognition_read.perceived_effective is not None
                else "UNFUNDED"
            )
            response_label = (
                response_requested_commitment.value
                if response_requested_commitment is not None
                else "NONE"
            )
            self.history.recognition_history.append(
                f"{initiator.value}@{self.elapsed_simulated_time}s:"
                f"requested={recognition_read.true_requested.value}->"
                f"{recognition_read.perceived_requested.value}:"
                f"effective={true_effective_label}->{perceived_effective_label}:"
                f"rolls={recognition_read.intent_roll}/{recognition_read.capability_roll}:"
                f"response={response_label}"
            )

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

        return AttemptResult(
            attempt=attempt,
            requested_cost=requested_cost,
            effective_cost=effective_cost,
            funding_gap=funding_gap,
            stamina=spend,
            response_requested_commitment=response_requested_commitment,
            response_effective_commitment=response_effective_commitment,
            response_requested_cost=response_requested_cost,
            response_effective_cost=response_effective_cost,
            response_funding_gap=response_funding_gap,
            response_stamina=response_spend,
            response_stamina_waived=response_stamina_waived,
            submission_hold_nominal_cost=hold_nominal_cost,
            submission_hold_covered_by_response=hold_covered_by_response,
            submission_hold_stamina=hold_spend,
            stamina_band_before_action=stamina_band_before_action,
            responder_stamina_band_before_action=(
                responder_stamina_band_before_action
            ),
            initiator_exhaustion_modifier=initiator_exhaustion_modifier,
            responder_exhaustion_modifier=responder_exhaustion_modifier,
            exhaustion_modifier=exhaustion_modifier,
            initiator_commitment_modifier=commitment_modifier,
            response_undercommitment_modifier=response_modifier,
            base_resolution=base_resolution,
            resolution=result,
        )


MountRun = MountMatch
