from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum

from ..domain.action import Commitment, AttemptResult
from ..domain.model import Side
from ..domain.stamina import StaminaBand
from ..domain.submission import SubmissionStage
from ..engine.match import MountMatch
from ..engine.stamina import AdvanceResult


class StaminaEconomyState(str, Enum):
    NOT_MUTUALLY_EXHAUSTED = "NOT_MUTUALLY_EXHAUSTED"
    MUTUALLY_EXHAUSTED_NOT_BOTH_ZERO = "MUTUALLY_EXHAUSTED_NOT_BOTH_ZERO"
    MUTUALLY_ZERO = "MUTUALLY_ZERO"


@dataclass(frozen=True, slots=True)
class StaminaSourceTotals:
    behavior_spend: int
    behavior_recovery: int
    initiator_commitment_spend: int
    responder_commitment_spend: int
    provisional_hold_spend: int
    unexplained_delta: int


@dataclass(frozen=True, slots=True)
class StaminaEconomyMatchRecord:
    match_index: int
    elapsed_seconds: int
    outcome: str
    top_final_stamina: int
    bottom_final_stamina: int
    top_first_exhausted_time: int | None
    bottom_first_exhausted_time: int | None
    first_state2_time: int | None
    first_state3_time: int | None
    first_state2_exit_to_state1_time: int | None
    state1_entries: int
    state2_entries: int
    state3_entries: int
    state2_exits_to_state1: int
    state2_reentries_after_state1: int
    state1_seconds: int
    state2_seconds: int
    state3_seconds: int
    bottom_switches_to_conserve: int
    bottom_switches_to_escape: int
    bottom_exhausted_latch_clears: int
    bottom_latch_clear_stamina: tuple[int, ...]
    top_sources: StaminaSourceTotals
    bottom_sources: StaminaSourceTotals

    @property
    def duration_reconciles(self) -> bool:
        return (
            self.state1_seconds + self.state2_seconds + self.state3_seconds
            == self.elapsed_seconds
        )

    @property
    def top_stamina_reconciles(self) -> bool:
        return self.top_sources.unexplained_delta == 0

    @property
    def bottom_stamina_reconciles(self) -> bool:
        return self.bottom_sources.unexplained_delta == 0


@dataclass(frozen=True, slots=True)
class StaminaEconomyExchangeRecord:
    match_index: int
    elapsed_seconds: int
    state: StaminaEconomyState
    initiator: Side
    action_id: str
    initiator_stamina: int
    responder_stamina: int
    responder_band_before: str
    responder_stamina_after_response: int
    responder_stamina_after_all_costs: int
    responder_band_after_all_costs: str
    initiator_affordability: str
    responder_affordability: str
    initiator_requested_commitment: str
    initiator_effective_commitment: str
    initiator_effective_cost: int
    responder_requested_commitment: str
    responder_effective_commitment: str
    responder_effective_cost: int
    initiator_requested_fundable: bool
    responder_requested_fundable: bool
    responder_has_higher_ceiling: bool
    responder_same_ceiling: bool
    responder_lower_ceiling: bool
    hedge_target: str | None
    hedge_one_level_fundable: bool | None
    response_undercommitment_modifier: int
    submission_stage_before: str | None
    submission_stage_after: str | None
    submission_advanced: bool
    transition_into_threat: bool
    transition_into_control: bool
    transition_into_finish: bool
    tapped: bool
    undercommitment_caused_tap: bool
    escape_destination: str | None
    final_grade: str
    final_grade_successful: bool
    submission_hold: bool
    response_commitment_requested_cost: int
    response_commitment_charged: int
    response_commitment_shortfall: int
    hold_requested: int
    hold_charged: int
    hold_shortfall: int
    hold_payment_status: str | None
    requested_plus_hold_fundable: bool | None
    effective_plus_hold_fundable: bool | None
    commitment_only_fundable_but_requested_plus_hold_not: bool


@dataclass(frozen=True, slots=True)
class StaminaEconomyMeasurement:
    interval_seconds: int
    behavior_quantum_seconds: int
    matches: tuple[StaminaEconomyMatchRecord, ...]
    exchanges: tuple[StaminaEconomyExchangeRecord, ...]

    @property
    def timing_alignment_valid(self) -> bool:
        return (
            self.interval_seconds == 5
            and self.behavior_quantum_seconds == 5
            and self.interval_seconds == self.behavior_quantum_seconds
        )


@dataclass(frozen=True, slots=True)
class _AttemptSnapshot:
    match_index: int
    elapsed_seconds: int
    state: StaminaEconomyState
    initiator: Side
    action_id: str
    initiator_stamina: int
    responder_stamina: int
    initiator_affordability: Commitment | None
    responder_affordability: Commitment | None
    initiator_requested: Commitment
    initiator_effective: Commitment | None
    responder_requested: Commitment
    responder_effective: Commitment | None
    responder_requested_cost: int
    submission_stage_before: SubmissionStage | None
    hold_history_len: int


def _label(commitment: Commitment | None) -> str:
    return commitment.value if commitment is not None else "UNFUNDED"


def _rank(commitment: Commitment | None) -> int:
    return {
        None: 0,
        Commitment.LOW: 1,
        Commitment.MEDIUM: 2,
        Commitment.HIGH: 3,
    }[commitment]


class StaminaEconomyCollector:
    """Read-only measurement observer for the frozen stamina-economy slice."""

    def __init__(
        self,
        *,
        interval_seconds: int,
        behavior_quantum_seconds: int,
    ) -> None:
        if interval_seconds != 5 or behavior_quantum_seconds != 5:
            raise ValueError(
                "stamina-economy measurement requires "
                "interval_seconds == behavior quantum == 5"
            )
        if interval_seconds != behavior_quantum_seconds:
            raise ValueError(
                "stamina-economy measurement refuses misaligned timing"
            )
        self.interval_seconds = interval_seconds
        self.behavior_quantum_seconds = behavior_quantum_seconds
        self._match_records: list[StaminaEconomyMatchRecord] = []
        self._exchange_records: list[StaminaEconomyExchangeRecord] = []
        self._current: dict | None = None

    @staticmethod
    def state(match: MountMatch) -> StaminaEconomyState:
        if match.top.stamina.current == 0 and match.bottom.stamina.current == 0:
            return StaminaEconomyState.MUTUALLY_ZERO
        if (
            match.top.stamina.band is StaminaBand.EXHAUSTED
            and match.bottom.stamina.band is StaminaBand.EXHAUSTED
        ):
            return StaminaEconomyState.MUTUALLY_EXHAUSTED_NOT_BOTH_ZERO
        return StaminaEconomyState.NOT_MUTUALLY_EXHAUSTED

    @staticmethod
    def affordability(match: MountMatch, stamina: int) -> Commitment | None:
        return match.stamina_cost_policy.effective_commitment(
            requested=Commitment.HIGH,
            available_stamina=stamina,
        )

    def start_match(self, match: MountMatch, *, match_index: int) -> None:
        if self._current is not None:
            raise RuntimeError("stamina-economy match already active")
        state = self.state(match)
        self._current = {
            "match_index": match_index,
            "starting": {
                Side.TOP: match.top.stamina.current,
                Side.BOTTOM: match.bottom.stamina.current,
            },
            "state": state,
            "entries": Counter({state: 1}),
            "seconds": Counter(),
            "first_state2": (
                match.elapsed_simulated_time
                if state
                is StaminaEconomyState.MUTUALLY_EXHAUSTED_NOT_BOTH_ZERO
                else None
            ),
            "first_state3": (
                match.elapsed_simulated_time
                if state is StaminaEconomyState.MUTUALLY_ZERO
                else None
            ),
            "first_state2_exit": None,
            "state2_exits": 0,
            "state2_reentries_after_state1": 0,
            "ever_state2": (
                state
                is StaminaEconomyState.MUTUALLY_EXHAUSTED_NOT_BOTH_ZERO
            ),
            "first_exhausted": {
                Side.TOP: (
                    0 if match.top.stamina.band is StaminaBand.EXHAUSTED else None
                ),
                Side.BOTTOM: (
                    0
                    if match.bottom.stamina.band is StaminaBand.EXHAUSTED
                    else None
                ),
            },
            "previous_bands": {
                Side.TOP: match.top.stamina.band,
                Side.BOTTOM: match.bottom.stamina.band,
            },
            "bottom_latch_clears": [],
            "bottom_to_conserve": 0,
            "bottom_to_escape": 0,
            "behavior_spend": Counter(),
            "behavior_recovery": Counter(),
            "initiator_spend": Counter(),
            "responder_spend": Counter(),
            "hold_spend": Counter(),
        }

    def _require_current(self) -> dict:
        if self._current is None:
            raise RuntimeError("stamina-economy match is not active")
        return self._current

    def observe_state(self, match: MountMatch) -> None:
        current = self._require_current()
        elapsed = match.elapsed_simulated_time

        for side in (Side.TOP, Side.BOTTOM):
            band = match.competitor(side).stamina.band
            previous = current["previous_bands"][side]
            if (
                current["first_exhausted"][side] is None
                and band is StaminaBand.EXHAUSTED
            ):
                current["first_exhausted"][side] = elapsed
            if (
                side is Side.BOTTOM
                and previous is StaminaBand.EXHAUSTED
                and band is not StaminaBand.EXHAUSTED
            ):
                current["bottom_latch_clears"].append(
                    match.bottom.stamina.current
                )
            current["previous_bands"][side] = band

        new_state = self.state(match)
        old_state = current["state"]
        if new_state is old_state:
            return

        if (
            old_state
            is StaminaEconomyState.MUTUALLY_EXHAUSTED_NOT_BOTH_ZERO
            and new_state is StaminaEconomyState.NOT_MUTUALLY_EXHAUSTED
        ):
            current["state2_exits"] += 1
            if current["first_state2_exit"] is None:
                current["first_state2_exit"] = elapsed

        if (
            new_state
            is StaminaEconomyState.MUTUALLY_EXHAUSTED_NOT_BOTH_ZERO
        ):
            if current["first_state2"] is None:
                current["first_state2"] = elapsed
            elif old_state is StaminaEconomyState.NOT_MUTUALLY_EXHAUSTED:
                current["state2_reentries_after_state1"] += 1
            current["ever_state2"] = True
        elif new_state is StaminaEconomyState.MUTUALLY_ZERO:
            if current["first_state3"] is None:
                current["first_state3"] = elapsed

        current["entries"][new_state] += 1
        current["state"] = new_state

    def before_advance(self, match: MountMatch) -> StaminaEconomyState:
        self.observe_state(match)
        return self.state(match)

    def after_advance(
        self,
        match: MountMatch,
        *,
        state_before: StaminaEconomyState,
        result: AdvanceResult,
    ) -> None:
        current = self._require_current()
        duration = result.drift.start_clock - result.drift.end_clock
        current["seconds"][state_before] += duration
        current["behavior_spend"][Side.TOP] += result.top_stamina.spent
        current["behavior_spend"][Side.BOTTOM] += result.bottom_stamina.spent
        current["behavior_recovery"][Side.TOP] += result.top_stamina.recovered
        current["behavior_recovery"][Side.BOTTOM] += result.bottom_stamina.recovered
        self.observe_state(match)

    def behavior_switch(self, *, side: Side, new_behavior: str) -> None:
        current = self._require_current()
        if side is not Side.BOTTOM:
            return
        if new_behavior == "CONSERVE":
            current["bottom_to_conserve"] += 1
        elif new_behavior == "ESCAPE":
            current["bottom_to_escape"] += 1

    def before_attempt(
        self,
        match: MountMatch,
        *,
        action_id: str,
        initiator_commitment: Commitment,
        responder_commitment: Commitment,
    ) -> _AttemptSnapshot:
        self.observe_state(match)
        initiator = match.initiator
        initiator_stamina = match.competitor(initiator).stamina.current
        responder_stamina = match.competitor(initiator.opponent).stamina.current
        initiator_effective = match.stamina_cost_policy.effective_commitment(
            requested=initiator_commitment,
            available_stamina=initiator_stamina,
        )
        responder_effective = match.stamina_cost_policy.effective_commitment(
            requested=responder_commitment,
            available_stamina=responder_stamina,
        )
        submission_stage_before = (
            match.submission_state.stage
            if action_id.endswith("americana_submission_finish")
            else None
        )
        return _AttemptSnapshot(
            match_index=self._require_current()["match_index"],
            elapsed_seconds=match.elapsed_simulated_time,
            state=self.state(match),
            initiator=initiator,
            action_id=action_id,
            initiator_stamina=initiator_stamina,
            responder_stamina=responder_stamina,
            initiator_affordability=self.affordability(match, initiator_stamina),
            responder_affordability=self.affordability(match, responder_stamina),
            initiator_requested=initiator_commitment,
            initiator_effective=initiator_effective,
            responder_requested=responder_commitment,
            responder_effective=responder_effective,
            responder_requested_cost=match.stamina_cost_policy.cost(
                responder_commitment
            ),
            submission_stage_before=submission_stage_before,
            hold_history_len=len(
                match.history.submission_hold_stamina_requested_history
            ),
        )

    def after_attempt(
        self,
        match: MountMatch,
        *,
        snapshot: _AttemptSnapshot,
        result: AttemptResult,
    ) -> None:
        current = self._require_current()
        current["initiator_spend"][snapshot.initiator] += result.stamina.charged
        if result.response_stamina is not None:
            current["responder_spend"][snapshot.initiator.opponent] += (
                result.response_stamina.charged
            )

        hold_added = (
            len(match.history.submission_hold_stamina_requested_history)
            > snapshot.hold_history_len
        )
        hold_requested = 0
        hold_charged = 0
        hold_shortfall = 0
        hold_status: str | None = None
        if hold_added:
            hold_requested = match.history.submission_hold_stamina_requested_history[-1]
            hold_charged = match.history.submission_hold_stamina_charged_history[-1]
            hold_shortfall = match.history.submission_hold_stamina_shortfall_history[-1]
            current["hold_spend"][snapshot.initiator.opponent] += hold_charged
            if hold_charged == hold_requested:
                hold_status = "FULL"
            elif hold_charged == 0:
                hold_status = "NONE"
            else:
                hold_status = "PARTIAL"

        submission_stage_after: str | None
        if match.submission_tapped:
            submission_stage_after = "Tap"
        elif match.submission_state.active:
            submission_stage_after = match.submission_state.stage.value
        else:
            submission_stage_after = None

        before_label = (
            snapshot.submission_stage_before.value
            if snapshot.submission_stage_before is not None
            else None
        )
        submission_advanced = (
            before_label is not None
            and submission_stage_after is not None
            and submission_stage_after != before_label
            and result.resolution.final_grade.successful
        )
        transition_into_threat = (
            before_label is None
            and submission_stage_after == SubmissionStage.THREAT.value
        )
        transition_into_control = (
            submission_stage_after == SubmissionStage.CONTROL.value
            and before_label != SubmissionStage.CONTROL.value
        )
        transition_into_finish = (
            submission_stage_after == SubmissionStage.FINISH.value
            and before_label != SubmissionStage.FINISH.value
        )

        tapped = match.submission_tapped and submission_stage_after == "Tap"
        undercommitment_caused_tap = (
            tapped
            and result.response_undercommitment_modifier > 0
            and result.resolution.final_grade.successful
            and not result.resolution.final_grade.shift(-1).successful
        )

        hedge_target: Commitment | None
        if snapshot.initiator_effective is None:
            hedge_target = Commitment.LOW
        elif snapshot.initiator_effective is Commitment.LOW:
            hedge_target = Commitment.MEDIUM
        elif snapshot.initiator_effective is Commitment.MEDIUM:
            hedge_target = Commitment.HIGH
        else:
            hedge_target = None
        hedge_possible = (
            None
            if hedge_target is None
            else snapshot.responder_stamina
            >= match.stamina_cost_policy.cost(hedge_target)
        )

        requested_plus_hold_fundable = (
            snapshot.responder_stamina
            >= snapshot.responder_requested_cost + hold_requested
            if hold_added
            else None
        )
        effective_response_cost = result.response_effective_cost
        effective_plus_hold_fundable = (
            snapshot.responder_stamina
            >= effective_response_cost + hold_requested
            if hold_added
            else None
        )

        self._exchange_records.append(
            StaminaEconomyExchangeRecord(
                match_index=snapshot.match_index,
                elapsed_seconds=snapshot.elapsed_seconds,
                state=snapshot.state,
                initiator=snapshot.initiator,
                action_id=snapshot.action_id,
                initiator_stamina=snapshot.initiator_stamina,
                responder_stamina=snapshot.responder_stamina,
                responder_band_before=(
                    result.responder_stamina_band_before_action.value
                ),
                responder_stamina_after_response=(
                    snapshot.responder_stamina
                    - (
                        result.response_stamina.charged
                        if result.response_stamina is not None
                        else 0
                    )
                ),
                responder_stamina_after_all_costs=(
                    match.competitor(snapshot.initiator.opponent).stamina.current
                ),
                responder_band_after_all_costs=(
                    match.competitor(snapshot.initiator.opponent).stamina.band.value
                ),
                initiator_affordability=_label(snapshot.initiator_affordability),
                responder_affordability=_label(snapshot.responder_affordability),
                initiator_requested_commitment=snapshot.initiator_requested.value,
                initiator_effective_commitment=_label(
                    snapshot.initiator_effective
                ),
                initiator_effective_cost=result.effective_cost,
                responder_requested_commitment=snapshot.responder_requested.value,
                responder_effective_commitment=_label(
                    snapshot.responder_effective
                ),
                responder_effective_cost=result.response_effective_cost,
                initiator_requested_fundable=(
                    snapshot.initiator_stamina
                    >= match.stamina_cost_policy.cost(
                        snapshot.initiator_requested
                    )
                ),
                responder_requested_fundable=(
                    snapshot.responder_stamina
                    >= snapshot.responder_requested_cost
                ),
                responder_has_higher_ceiling=(
                    _rank(snapshot.responder_affordability)
                    > _rank(snapshot.initiator_affordability)
                ),
                responder_same_ceiling=(
                    _rank(snapshot.responder_affordability)
                    == _rank(snapshot.initiator_affordability)
                ),
                responder_lower_ceiling=(
                    _rank(snapshot.responder_affordability)
                    < _rank(snapshot.initiator_affordability)
                ),
                hedge_target=_label(hedge_target) if hedge_target is not None else None,
                hedge_one_level_fundable=hedge_possible,
                response_undercommitment_modifier=(
                    result.response_undercommitment_modifier
                ),
                submission_stage_before=before_label,
                submission_stage_after=submission_stage_after,
                submission_advanced=submission_advanced,
                transition_into_threat=transition_into_threat,
                transition_into_control=transition_into_control,
                transition_into_finish=transition_into_finish,
                tapped=tapped,
                undercommitment_caused_tap=undercommitment_caused_tap,
                escape_destination=(
                    match.exit_destination.value
                    if match.exit_destination is not None
                    else None
                ),
                final_grade=result.resolution.final_grade.display,
                final_grade_successful=result.resolution.final_grade.successful,
                submission_hold=hold_added,
                response_commitment_requested_cost=(
                    snapshot.responder_requested_cost
                ),
                response_commitment_charged=(
                    result.response_stamina.charged
                    if result.response_stamina is not None
                    else 0
                ),
                response_commitment_shortfall=(
                    snapshot.responder_requested_cost
                    - (
                        result.response_stamina.charged
                        if result.response_stamina is not None
                        else 0
                    )
                ),
                hold_requested=hold_requested,
                hold_charged=hold_charged,
                hold_shortfall=hold_shortfall,
                hold_payment_status=hold_status,
                requested_plus_hold_fundable=requested_plus_hold_fundable,
                effective_plus_hold_fundable=effective_plus_hold_fundable,
                commitment_only_fundable_but_requested_plus_hold_not=(
                    hold_added
                    and snapshot.responder_stamina
                    >= snapshot.responder_requested_cost
                    and snapshot.responder_stamina
                    < snapshot.responder_requested_cost + hold_requested
                ),
            )
        )
        self.observe_state(match)

    def finish_match(self, match: MountMatch, *, outcome: str) -> None:
        current = self._require_current()
        self.observe_state(match)

        def totals(side: Side) -> StaminaSourceTotals:
            starting = current["starting"][side]
            final = match.competitor(side).stamina.current
            recovery = current["behavior_recovery"][side]
            behavior_spend = current["behavior_spend"][side]
            initiator_spend = current["initiator_spend"][side]
            responder_spend = current["responder_spend"][side]
            hold_spend = current["hold_spend"][side]
            expected_final = (
                starting
                + recovery
                - behavior_spend
                - initiator_spend
                - responder_spend
                - hold_spend
            )
            return StaminaSourceTotals(
                behavior_spend=behavior_spend,
                behavior_recovery=recovery,
                initiator_commitment_spend=initiator_spend,
                responder_commitment_spend=responder_spend,
                provisional_hold_spend=hold_spend,
                unexplained_delta=final - expected_final,
            )

        entries = current["entries"]
        seconds = current["seconds"]
        self._match_records.append(
            StaminaEconomyMatchRecord(
                match_index=current["match_index"],
                elapsed_seconds=match.elapsed_simulated_time,
                outcome=outcome,
                top_final_stamina=match.top.stamina.current,
                bottom_final_stamina=match.bottom.stamina.current,
                top_first_exhausted_time=current["first_exhausted"][Side.TOP],
                bottom_first_exhausted_time=current["first_exhausted"][Side.BOTTOM],
                first_state2_time=current["first_state2"],
                first_state3_time=current["first_state3"],
                first_state2_exit_to_state1_time=current["first_state2_exit"],
                state1_entries=entries[
                    StaminaEconomyState.NOT_MUTUALLY_EXHAUSTED
                ],
                state2_entries=entries[
                    StaminaEconomyState.MUTUALLY_EXHAUSTED_NOT_BOTH_ZERO
                ],
                state3_entries=entries[StaminaEconomyState.MUTUALLY_ZERO],
                state2_exits_to_state1=current["state2_exits"],
                state2_reentries_after_state1=current[
                    "state2_reentries_after_state1"
                ],
                state1_seconds=seconds[
                    StaminaEconomyState.NOT_MUTUALLY_EXHAUSTED
                ],
                state2_seconds=seconds[
                    StaminaEconomyState.MUTUALLY_EXHAUSTED_NOT_BOTH_ZERO
                ],
                state3_seconds=seconds[StaminaEconomyState.MUTUALLY_ZERO],
                bottom_switches_to_conserve=current["bottom_to_conserve"],
                bottom_switches_to_escape=current["bottom_to_escape"],
                bottom_exhausted_latch_clears=len(
                    current["bottom_latch_clears"]
                ),
                bottom_latch_clear_stamina=tuple(
                    current["bottom_latch_clears"]
                ),
                top_sources=totals(Side.TOP),
                bottom_sources=totals(Side.BOTTOM),
            )
        )
        self._current = None

    def measurement(self) -> StaminaEconomyMeasurement:
        if self._current is not None:
            raise RuntimeError("cannot finalize measurement with active match")
        return StaminaEconomyMeasurement(
            interval_seconds=self.interval_seconds,
            behavior_quantum_seconds=self.behavior_quantum_seconds,
            matches=tuple(self._match_records),
            exchanges=tuple(self._exchange_records),
        )
