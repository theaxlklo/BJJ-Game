from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from statistics import median, quantiles

from ..domain.action import Commitment
from ..domain.model import BottomBehavior, ExitDestination, Side, TopBehavior
from ..positions.mount.catalog import (
    TOP_AMERICANA_ARM_ISOLATION,
    TOP_AMERICANA_SUBMISSION_FINISH,
)
from ..interfaces.batch import (
    BatchBehaviorMode,
    BatchResponderMode,
    BatchResponseCommitmentMode,
    BatchSummary,
    run_escape_first_batch,
)
from ..interfaces.stamina_economy import (
    StaminaEconomyExchangeRecord,
    StaminaEconomyMeasurement,
    StaminaEconomyState,
)


class StaminaMeasurementGateStatus(str, Enum):
    PASS = "PASS"
    OPEN = "OPEN"


@dataclass(frozen=True, slots=True)
class StaminaMeasurementGate:
    letter: str
    name: str
    status: StaminaMeasurementGateStatus
    metric: str
    evidence: str

    def render(self) -> str:
        return (
            f"STAMINA-ECONOMY MEASUREMENT GATE {self.letter} "
            f"[{self.status.value}]: {self.name} — {self.metric}; {self.evidence}"
        )


@dataclass(frozen=True, slots=True)
class StaminaEconomySurface:
    label: str
    summary: BatchSummary


@dataclass(frozen=True, slots=True)
class DefenderDrainObservation:
    surface_label: str
    selector: str
    initiator_side: Side
    exchange_count: int
    response_charged: int
    hold_charged: int
    total_charged: int
    by_state: tuple[tuple[str, int], ...]
    by_action: tuple[tuple[str, int], ...]
    submission_charged: int
    non_submission_charged: int
    responder_behavior_recovery: int | None = None

    @property
    def recovery_share(self) -> float | None:
        if not self.responder_behavior_recovery:
            return None
        return self.total_charged / self.responder_behavior_recovery


_SURFACE_ORDER = (
    "A public MATCH",
    "B trusts reads",
    "C one level above",
    "D always HIGH",
    "E trusts reads + Bottom RECOVER",
)


def _surface_kwargs(label: str) -> dict:
    common = dict(
        matches=100,
        base_seed=42,
        top_behavior=TopBehavior.PRESSURE,
        bottom_behavior=BottomBehavior.ESCAPE,
        commitment=Commitment.MEDIUM,
        initial_clock=300,
        starting_axis=1.50,
        interval_seconds=5,
        top_stamina=100,
        bottom_stamina=100,
        bottom_responder_mode=BatchResponderMode.INFORMED,
        enable_v02_setup=True,
        enable_v03_submissions=True,
        enable_v04_commitment_semantics=True,
    )
    if label == "A public MATCH":
        return {
            **common,
            "response_commitment_mode": BatchResponseCommitmentMode.MATCH,
            "enable_v04b_recognition": False,
        }
    if label == "B trusts reads":
        return {
            **common,
            "response_commitment_mode": BatchResponseCommitmentMode.RECOGNITION,
            "enable_v04b_recognition": True,
        }
    if label == "C one level above":
        return {
            **common,
            "response_commitment_mode": (
                BatchResponseCommitmentMode.RECOGNITION_HEDGE_ONE
            ),
            "enable_v04b_recognition": True,
        }
    if label == "D always HIGH":
        return {
            **common,
            "response_commitment_mode": (
                BatchResponseCommitmentMode.RECOGNITION_ALWAYS_HIGH
            ),
            "enable_v04b_recognition": True,
        }
    if label == "E trusts reads + Bottom RECOVER":
        return {
            **common,
            "bottom_behavior_mode": BatchBehaviorMode.RECOVER,
            "response_commitment_mode": BatchResponseCommitmentMode.RECOGNITION,
            "enable_v04b_recognition": True,
        }
    raise ValueError(f"unknown stamina-economy surface: {label}")


@lru_cache(maxsize=1)
def measured_surfaces() -> tuple[StaminaEconomySurface, ...]:
    return tuple(
        StaminaEconomySurface(
            label=label,
            summary=run_escape_first_batch(
                **_surface_kwargs(label),
                measure_stamina_economy=True,
            ),
        )
        for label in _SURFACE_ORDER
    )


@lru_cache(maxsize=1)
def unmeasured_surfaces() -> tuple[StaminaEconomySurface, ...]:
    return tuple(
        StaminaEconomySurface(
            label=label,
            summary=run_escape_first_batch(**_surface_kwargs(label)),
        )
        for label in _SURFACE_ORDER
    )


def _measurement(surface: StaminaEconomySurface) -> StaminaEconomyMeasurement:
    measurement = surface.summary.stamina_economy
    if measurement is None:
        raise RuntimeError(f"missing stamina-economy measurement for {surface.label}")
    return measurement


def _taps(summary: BatchSummary) -> int:
    return summary.outcome_counts.get("TAP — Americana", 0)


def _escapes(summary: BatchSummary) -> int:
    return sum(
        summary.outcome_counts.get(destination.value, 0)
        for destination in ExitDestination
    )


def _percentiles(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    if len(values) == 1:
        return values[0], values[0]
    q1, _, q3 = quantiles(values, n=4, method="inclusive")
    return q1, q3


def _median_or_none(values):
    return median(values) if values else None


def _mechanical_signature(summary: BatchSummary) -> tuple:
    fields = summary.__dataclass_fields__
    return tuple(
        (name, getattr(summary, name))
        for name in fields
        if name != "stamina_economy"
    )


def _state_share(seconds: int, elapsed: int) -> float:
    return 0.0 if elapsed == 0 else seconds / elapsed


def _state_rows(measurement: StaminaEconomyMeasurement, state):
    return [row for row in measurement.exchanges if row.state is state]


def _surface_overview_line(surface: StaminaEconomySurface) -> str:
    summary = surface.summary
    return (
        f"{surface.label}: taps={_taps(summary)}, escapes={_escapes(summary)}, "
        f"timeouts={summary.outcome_counts.get('TIMEOUT — Mount retained', 0)}, "
        f"final stamina median={summary.top_final_stamina_median:.1f}/"
        f"{summary.bottom_final_stamina_median:.1f}, "
        f"response commitment spend="
        f"{summary.total_response_commitment_stamina_charged}, "
        f"Top/Bottom behavior mode="
        f"{summary.top_behavior_mode.value}/{summary.bottom_behavior_mode.value}"
    )


def _surface_duration_line(surface: StaminaEconomySurface) -> str:
    m = _measurement(surface)
    matches = list(m.matches)
    state2 = [x for x in matches if x.state2_entries > 0]
    state3 = [x for x in matches if x.state3_entries > 0]
    state2_shares = [
        _state_share(x.state2_seconds, x.elapsed_seconds) for x in matches
    ]
    state3_shares = [
        _state_share(x.state3_seconds, x.elapsed_seconds) for x in matches
    ]
    q2 = _percentiles(state2_shares)
    q3 = _percentiles(state3_shares)
    exits = sum(x.state2_exits_to_state1 > 0 for x in matches)
    reentries = sum(x.state2_reentries_after_state1 > 0 for x in matches)
    clears = sum(x.bottom_exhausted_latch_clears > 0 for x in matches)
    return (
        f"{surface.label}: entries State1/2/3="
        f"{sum(x.state1_entries for x in matches)}/"
        f"{sum(x.state2_entries for x in matches)}/"
        f"{sum(x.state3_entries for x in matches)}, "
        f"State2 entered={len(state2)}, exited-to-State1={exits}, "
        f"reentered={reentries}, State3 entered={len(state3)}, "
        f"Top/Bottom first Exhausted median="
        f"{_median_or_none([x.top_first_exhausted_time for x in matches if x.top_first_exhausted_time is not None])}/"
        f"{_median_or_none([x.bottom_first_exhausted_time for x in matches if x.bottom_first_exhausted_time is not None])}, "
        f"State2 first median={_median_or_none([x.first_state2_time for x in state2])}, "
        f"State3 first median={_median_or_none([x.first_state3_time for x in state3])}, "
        f"State2 seconds median={median([x.state2_seconds for x in matches]):.1f}, "
        f"share median={median(state2_shares):.3f} "
        f"p25/p75={q2[0]:.3f}/{q2[1]:.3f}, "
        f"State3 seconds median={median([x.state3_seconds for x in matches]):.1f}, "
        f"share median={median(state3_shares):.3f} "
        f"p25/p75={q3[0]:.3f}/{q3[1]:.3f}, "
        f"Bottom latch-clearing matches={clears}"
    )


def _affordability_counter(rows, attr: str) -> Counter:
    return Counter(getattr(row, attr) for row in rows)


def _fundability_counts(rows, attr: str) -> dict[str, int]:
    order = {"UNFUNDED": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
    ranks = [order[getattr(row, attr)] for row in rows]
    return {
        "LOW": sum(rank >= 1 for rank in ranks),
        "MEDIUM": sum(rank >= 2 for rank in ranks),
        "HIGH": sum(rank >= 3 for rank in ranks),
    }


def _surface_affordability_line(surface: StaminaEconomySurface) -> str:
    rows = _state_rows(
        _measurement(surface),
        StaminaEconomyState.MUTUALLY_EXHAUSTED_NOT_BOTH_ZERO,
    )
    initiator = _affordability_counter(rows, "initiator_affordability")
    responder = _affordability_counter(rows, "responder_affordability")
    cross = Counter(
        (row.initiator_affordability, row.responder_affordability)
        for row in rows
    )
    transitions_i = Counter(
        (
            row.initiator_requested_commitment,
            row.initiator_effective_commitment,
        )
        for row in rows
    )
    transitions_r = Counter(
        (
            row.responder_requested_commitment,
            row.responder_effective_commitment,
        )
        for row in rows
    )
    relation = {
        "defender>attacker": sum(row.responder_has_higher_ceiling for row in rows),
        "equal": sum(row.responder_same_ceiling for row in rows),
        "defender<attacker": sum(row.responder_lower_ceiling for row in rows),
    }
    hedge_eligible = [row for row in rows if row.hedge_target is not None]
    high_attackers = sum(row.hedge_target is None for row in rows)
    hedge_possible = sum(
        row.hedge_one_level_fundable is True for row in hedge_eligible
    )
    initiator_request_fundable = sum(row.initiator_requested_fundable for row in rows)
    response_request_fundable = sum(row.responder_requested_fundable for row in rows)
    holds = [row for row in rows if row.submission_hold]
    hold_status = Counter(row.hold_payment_status for row in holds)
    hold_gap = sum(
        row.commitment_only_fundable_but_requested_plus_hold_not for row in holds
    )
    requested_plus_hold = sum(
        row.requested_plus_hold_fundable is True for row in holds
    )
    effective_plus_hold = sum(
        row.effective_plus_hold_fundable is True for row in holds
    )
    return (
        f"{surface.label}: State2 exchanges={len(rows)}, "
        f"initiator ceiling={dict(initiator)}, responder ceiling={dict(responder)}, "
        f"can-fund initiator={_fundability_counts(rows, 'initiator_affordability')}, "
        f"can-fund responder={_fundability_counts(rows, 'responder_affordability')}, "
        f"ceiling relation={relation}, hedge-one possible={hedge_possible}/"
        f"{len(hedge_eligible)}, HIGH-attacker/no-higher={high_attackers}, "
        f"initiator request fundable={initiator_request_fundable}/{len(rows)}, "
        f"responder request fundable={response_request_fundable}/{len(rows)}, "
        f"initiator transitions={dict(transitions_i)}, "
        f"responder transitions={dict(transitions_r)}, cross={dict(cross)}, "
        f"State2 holds={len(holds)}, hold payment={dict(hold_status)}, "
        f"requested+hold fundable={requested_plus_hold}/{len(holds)}, "
        f"effective+hold fundable={effective_plus_hold}/{len(holds)}, "
        f"commitment-fundable but requested+hold-not={hold_gap}"
    )


def _surface_decisive_line(surface: StaminaEconomySurface) -> str:
    measurement = _measurement(surface)
    parts = []
    for state in StaminaEconomyState:
        rows = _state_rows(measurement, state)
        submission_attempts = sum(
            row.submission_stage_before is not None for row in rows
        )
        parts.append(
            f"{state.value}: exchanges={len(rows)}, "
            f"undercommit={sum(row.response_undercommitment_modifier > 0 for row in rows)}, "
            f"submission attempts={submission_attempts}, "
            f"advances={sum(row.submission_advanced for row in rows)}, "
            f"Threat/Control/Finish="
            f"{sum(row.transition_into_threat for row in rows)}/"
            f"{sum(row.transition_into_control for row in rows)}/"
            f"{sum(row.transition_into_finish for row in rows)}, "
            f"taps={sum(row.tapped for row in rows)}, "
            f"undercommit-caused taps="
            f"{sum(row.undercommitment_caused_tap for row in rows)}, "
            f"escapes={sum(row.escape_destination is not None for row in rows)}"
        )
    timeout_state = Counter()
    for record in measurement.matches:
        if not record.outcome.startswith("TIMEOUT"):
            continue
        if record.state1_entries:
            timeout_state[StaminaEconomyState.NOT_MUTUALLY_EXHAUSTED.value] += 1
        if record.state2_entries:
            timeout_state[
                StaminaEconomyState.MUTUALLY_EXHAUSTED_NOT_BOTH_ZERO.value
            ] += 1
        if record.state3_entries:
            timeout_state[StaminaEconomyState.MUTUALLY_ZERO.value] += 1
    return f"{surface.label}: " + " | ".join(parts) + f"; timeout-entered={dict(timeout_state)}"


def _surface_state2_decisive_affordability_line(
    surface: StaminaEconomySurface,
) -> str:
    rows = _state_rows(
        _measurement(surface),
        StaminaEconomyState.MUTUALLY_EXHAUSTED_NOT_BOTH_ZERO,
    )
    tap_rows = [row for row in rows if row.tapped]
    advance_rows = [row for row in rows if row.submission_advanced]
    escape_rows = [row for row in rows if row.escape_destination is not None]

    def describe(selected) -> str:
        pairs = Counter(
            (row.initiator_affordability, row.responder_affordability)
            for row in selected
        )
        responder_request_fundable = sum(
            row.responder_requested_fundable for row in selected
        )
        hedge_eligible = [row for row in selected if row.hedge_target is not None]
        hedge_possible = sum(
            row.hedge_one_level_fundable is True for row in hedge_eligible
        )
        undercommit = sum(
            row.response_undercommitment_modifier > 0 for row in selected
        )
        return (
            f"n={len(selected)}, pairs={dict(pairs)}, "
            f"responder-request-fundable={responder_request_fundable}/"
            f"{len(selected)}, hedge-one-possible={hedge_possible}/"
            f"{len(hedge_eligible)}, undercommit={undercommit}"
        )

    return (
        f"{surface.label}: State2 taps[{describe(tap_rows)}], "
        f"submission advances[{describe(advance_rows)}], "
        f"escapes[{describe(escape_rows)}]"
    )


def _aggregate_sources(surface: StaminaEconomySurface) -> str:
    m = _measurement(surface)
    def side_totals(attr: str):
        records = [getattr(x, attr) for x in m.matches]
        return {
            "behavior_spend": sum(x.behavior_spend for x in records),
            "behavior_recovery": sum(x.behavior_recovery for x in records),
            "initiator_commitment": sum(
                x.initiator_commitment_spend for x in records
            ),
            "responder_commitment": sum(
                x.responder_commitment_spend for x in records
            ),
            "hold": sum(x.provisional_hold_spend for x in records),
            "unexplained": sum(x.unexplained_delta for x in records),
        }
    holds = [row for row in m.exchanges if row.submission_hold]
    hold_status = Counter(row.hold_payment_status for row in holds)
    combined_requested = sum(
        row.response_commitment_requested_cost + row.hold_requested
        for row in holds
    )
    combined_charged = sum(
        row.response_commitment_charged + row.hold_charged for row in holds
    )
    exhausted_moves = sum(
        row.responder_band_before != "Exhausted"
        and row.responder_band_after_all_costs == "Exhausted"
        for row in holds
    )
    zero_moves = sum(
        row.responder_stamina > 0
        and row.responder_stamina_after_all_costs == 0
        for row in holds
    )
    pre_values = [row.responder_stamina for row in holds]
    after_response_values = [
        row.responder_stamina_after_response for row in holds
    ]
    pre_q = _percentiles([float(v) for v in pre_values])
    after_q = _percentiles([float(v) for v in after_response_values])
    requested_plus_hold = sum(
        row.requested_plus_hold_fundable is True for row in holds
    )
    effective_plus_hold = sum(
        row.effective_plus_hold_fundable is True for row in holds
    )
    return (
        f"{surface.label}: Top={side_totals('top_sources')}, "
        f"Bottom={side_totals('bottom_sources')}, holds={len(holds)}, "
        f"response requested/charged/shortfall="
        f"{sum(r.response_commitment_requested_cost for r in holds)}/"
        f"{sum(r.response_commitment_charged for r in holds)}/"
        f"{sum(r.response_commitment_shortfall for r in holds)}, "
        f"hold requested/charged/shortfall="
        f"{sum(r.hold_requested for r in holds)}/"
        f"{sum(r.hold_charged for r in holds)}/"
        f"{sum(r.hold_shortfall for r in holds)}, "
        f"combined requested/charged/shortfall="
        f"{combined_requested}/{combined_charged}/{combined_requested-combined_charged}, "
        f"hold payment={dict(hold_status)}, "
        f"pre-charge stamina median/p25/p75="
        f"{_median_or_none(pre_values)}/{pre_q[0]}/{pre_q[1]}, "
        f"post-response stamina median/p25/p75="
        f"{_median_or_none(after_response_values)}/{after_q[0]}/{after_q[1]}, "
        f"requested+hold fundable={requested_plus_hold}/{len(holds)}, "
        f"effective+hold fundable={effective_plus_hold}/{len(holds)}, "
        f"moved-to-Exhausted={exhausted_moves}, moved-to-zero={zero_moves}"
    )


def _surface_funding_line(surface: StaminaEconomySurface) -> str:
    m = _measurement(surface)
    categories = Counter()
    both_unfunded_undercommit = Counter()
    both_unfunded_submission_attempts = 0
    both_unfunded_advances = 0
    both_unfunded_taps = 0
    both_unfunded_escapes = 0
    by_state = Counter()
    for row in m.exchanges:
        i_funded = row.initiator_effective_commitment != "UNFUNDED"
        r_funded = row.responder_effective_commitment != "UNFUNDED"
        if i_funded and r_funded:
            category = "both funded"
        elif i_funded:
            category = "initiator funded / responder UNFUNDED"
        elif r_funded:
            category = "initiator UNFUNDED / responder funded"
        else:
            category = "both UNFUNDED"
        categories[category] += 1
        by_state[(row.state.value, category)] += 1
        if category == "both UNFUNDED":
            both_unfunded_undercommit[row.response_undercommitment_modifier] += 1
            both_unfunded_submission_attempts += row.submission_stage_before is not None
            both_unfunded_advances += row.submission_advanced
            both_unfunded_taps += row.tapped
            both_unfunded_escapes += row.escape_destination is not None
    return (
        f"{surface.label}: funding={dict(categories)}, by-state={dict(by_state)}, "
        f"both-UNFUNDED undercommit={dict(both_unfunded_undercommit)}, "
        f"submission attempts/advances/taps="
        f"{both_unfunded_submission_attempts}/{both_unfunded_advances}/"
        f"{both_unfunded_taps}, escapes={both_unfunded_escapes}"
    )


def _drain_observation(
    surface: StaminaEconomySurface,
    *,
    initiator_side: Side,
    selector: str,
) -> DefenderDrainObservation:
    measurement = _measurement(surface)
    if selector == "exact-zero":
        rows = [
            row
            for row in measurement.exchanges
            if row.initiator is initiator_side and row.initiator_stamina == 0
        ]
    elif selector == "true-UNFUNDED":
        rows = [
            row
            for row in measurement.exchanges
            if row.initiator is initiator_side
            and row.initiator_effective_commitment == "UNFUNDED"
        ]
    else:
        raise ValueError(f"unknown defender-drain selector: {selector}")

    def spend(row) -> int:
        return row.response_commitment_charged + row.hold_charged

    by_state = Counter()
    by_action = Counter()
    submission_charged = 0
    non_submission_charged = 0
    submission_action_ids = {
        TOP_AMERICANA_ARM_ISOLATION,
        TOP_AMERICANA_SUBMISSION_FINISH,
    }
    for row in rows:
        charged = spend(row)
        by_state[row.state.value] += charged
        by_action[row.action_id] += charged
        if row.action_id in submission_action_ids:
            submission_charged += charged
        else:
            non_submission_charged += charged

    responder_side = initiator_side.opponent
    responder_behavior_recovery = sum(
        (
            record.top_sources.behavior_recovery
            if responder_side is Side.TOP
            else record.bottom_sources.behavior_recovery
        )
        for record in measurement.matches
    )
    return DefenderDrainObservation(
        surface_label=surface.label,
        selector=selector,
        initiator_side=initiator_side,
        exchange_count=len(rows),
        response_charged=sum(row.response_commitment_charged for row in rows),
        hold_charged=sum(row.hold_charged for row in rows),
        total_charged=sum(spend(row) for row in rows),
        by_state=tuple(sorted(by_state.items())),
        by_action=tuple(sorted(by_action.items())),
        submission_charged=submission_charged,
        non_submission_charged=non_submission_charged,
        responder_behavior_recovery=responder_behavior_recovery,
    )


@lru_cache(maxsize=1)
def prechange_defender_drain_observations() -> tuple[DefenderDrainObservation, ...]:
    surfaces = measured_surfaces()
    observations: list[DefenderDrainObservation] = []
    for surface in surfaces:
        for initiator_side in (Side.TOP, Side.BOTTOM):
            observations.append(
                _drain_observation(
                    surface,
                    initiator_side=initiator_side,
                    selector="exact-zero",
                )
            )
            observations.append(
                _drain_observation(
                    surface,
                    initiator_side=initiator_side,
                    selector="true-UNFUNDED",
                )
            )
    return tuple(observations)


def _render_defender_drain_observation(
    observation: DefenderDrainObservation,
) -> str:
    recovery = observation.responder_behavior_recovery
    share = observation.recovery_share
    return (
        f"{observation.surface_label}: selector={observation.selector}, "
        f"initiator={observation.initiator_side.value}, "
        f"exchanges={observation.exchange_count}, "
        f"response/hold/total="
        f"{observation.response_charged}/"
        f"{observation.hold_charged}/"
        f"{observation.total_charged}, "
        f"by-state={dict(observation.by_state)}, "
        f"by-action={dict(observation.by_action)}, "
        f"submission/non-submission="
        f"{observation.submission_charged}/"
        f"{observation.non_submission_charged}, "
        f"responder behavior recovery={recovery}, "
        f"drain/recovery="
        f"{'n/a' if share is None else f'{share:.4f}'}"
    )


def _surface_zero_attack_line(surface: StaminaEconomySurface) -> str:
    rows = [
        row
        for row in _measurement(surface).exchanges
        if row.initiator_stamina == 0
    ]
    actions = Counter(row.action_id for row in rows)
    requested = Counter(row.initiator_requested_commitment for row in rows)
    effective = Counter(row.initiator_effective_commitment for row in rows)
    grades = Counter(row.final_grade for row in rows)
    submission_attempts = sum(row.submission_stage_before is not None for row in rows)
    advances = sum(row.submission_advanced for row in rows)
    taps = sum(row.tapped for row in rows)
    escapes = sum(row.escape_destination is not None for row in rows)
    positional_successes = sum(
        row.submission_stage_before is None
        and row.final_grade_successful
        and not row.tapped
        for row in rows
    )
    responder_ceiling = Counter(row.responder_affordability for row in rows)
    effective_costs = Counter(row.initiator_effective_cost for row in rows)
    response_requested = Counter(
        row.responder_requested_commitment for row in rows
    )
    response_effective = Counter(
        row.responder_effective_commitment for row in rows
    )
    return (
        f"{surface.label}: zero-stamina attacks={len(rows)}, actions={dict(actions)}, "
        f"requested={dict(requested)}, effective={dict(effective)}, "
        f"effective costs={dict(effective_costs)}, "
        f"response requested/effective={dict(response_requested)}/{dict(response_effective)}, "
        f"grades={dict(grades)}, positional successes={positional_successes}, "
        f"submission attempts/advances/taps={submission_attempts}/{advances}/{taps}, "
        f"escapes={escapes}, responder ceilings={dict(responder_ceiling)}"
    )


def _surface_e_recovery_line(surface: StaminaEconomySurface) -> str:
    m = _measurement(surface)
    records = m.matches
    return (
        f"{surface.label}: Bottom switches to CONSERVE="
        f"{sum(x.bottom_switches_to_conserve for x in records)}, "
        f"back to ESCAPE={sum(x.bottom_switches_to_escape for x in records)}, "
        f"latch clears={sum(x.bottom_exhausted_latch_clears for x in records)}, "
        f"matches clearing={sum(x.bottom_exhausted_latch_clears > 0 for x in records)}, "
        f"clear stamina={Counter(v for x in records for v in x.bottom_latch_clear_stamina)}"
    )


def _fresh_measured_surface(label: str) -> BatchSummary:
    return run_escape_first_batch(
        **_surface_kwargs(label),
        measure_stamina_economy=True,
    )


@lru_cache(maxsize=1)
def measure_stamina_economy_definition_of_done() -> tuple[StaminaMeasurementGate, ...]:
    measured = measured_surfaces()
    unmeasured = unmeasured_surfaces()
    measurements = [_measurement(surface) for surface in measured]

    gate_a = (
        len(measured) == 5
        and all(m.timing_alignment_valid for m in measurements)
        and all(len(m.matches) == 100 for m in measurements)
        and all(
            record.duration_reconciles
            for m in measurements
            for record in m.matches
        )
    )

    valid_ceiling = {"UNFUNDED", "LOW", "MEDIUM", "HIGH"}
    gate_b_rows = [
        row
        for surface in measured[1:]
        for row in _state_rows(
            _measurement(surface),
            StaminaEconomyState.MUTUALLY_EXHAUSTED_NOT_BOTH_ZERO,
        )
    ]
    hold_rows = [row for row in gate_b_rows if row.submission_hold]
    gate_b = (
        bool(gate_b_rows)
        and all(row.initiator_affordability in valid_ceiling for row in gate_b_rows)
        and all(row.responder_affordability in valid_ceiling for row in gate_b_rows)
        and all(
            row.hold_payment_status in {"FULL", "PARTIAL", "NONE"}
            for row in hold_rows
        )
        and all(
            row.requested_plus_hold_fundable is not None
            and row.effective_plus_hold_fundable is not None
            for row in hold_rows
        )
    )

    gate_c = all(
        row.state in set(StaminaEconomyState)
        and row.final_grade != ""
        for m in measurements
        for row in m.exchanges
    )

    gate_d = all(
        record.top_stamina_reconciles and record.bottom_stamina_reconciles
        for m in measurements
        for record in m.matches
    )

    gate_e = all(
        len(m.exchanges)
        == sum(
            1
            for row in m.exchanges
            if (
                row.initiator_effective_commitment in valid_ceiling
                and row.responder_effective_commitment in valid_ceiling
            )
        )
        and all(
            row.response_undercommitment_modifier == 0
            for row in m.exchanges
            if (
                row.initiator_effective_commitment == "UNFUNDED"
                and row.responder_effective_commitment == "UNFUNDED"
            )
        )
        for m in measurements
    )

    gate_f = all(
        all(
            row.initiator_effective_commitment == "UNFUNDED"
            for row in m.exchanges
            if row.initiator_stamina == 0
        )
        for m in measurements
    )

    mechanical_equal = all(
        _mechanical_signature(measured_surface.summary)
        == _mechanical_signature(unmeasured_surface.summary)
        for measured_surface, unmeasured_surface in zip(measured, unmeasured)
    )
    replay_equal = all(
        surface.summary == _fresh_measured_surface(surface.label)
        for surface in measured
    )
    trust = measured[1].summary
    hedge = measured[2].summary
    high = measured[3].summary
    historical_pinned = (
        _taps(trust) == 6
        and _escapes(trust) == 11
        and trust.total_response_commitment_stamina_charged == 7352
        and trust.top_final_stamina_median == 0
        and trust.bottom_final_stamina_median == 0
        and _taps(hedge) == 0
        and _escapes(hedge) == 22
        and hedge.total_response_commitment_stamina_charged == 8843
        and hedge.top_final_stamina_median == 0
        and hedge.bottom_final_stamina_median == 0
        and _taps(high) == 0
        and _escapes(high) == 22
        and high.total_response_commitment_stamina_charged == 9480
        and high.top_final_stamina_median == 0
        and high.bottom_final_stamina_median == 0
    )
    gate_g = mechanical_equal and replay_equal and historical_pinned

    gates_so_far = (gate_a, gate_b, gate_c, gate_d, gate_e, gate_f, gate_g)
    gate_h = all(gates_so_far) and all(
        surface.summary.stamina_economy is not None for surface in measured
    )

    return (
        StaminaMeasurementGate(
            "A",
            "exact three-state duration accounting",
            StaminaMeasurementGateStatus.PASS if gate_a else StaminaMeasurementGateStatus.OPEN,
            f"surfaces={len(measured)}; matches={sum(len(m.matches) for m in measurements)}; "
            f"duration_reconciled={sum(r.duration_reconciles for m in measurements for r in m.matches)}/500",
            "5-second interval equals 5-second behavior quantum; duration must reconcile exactly",
        ),
        StaminaMeasurementGate(
            "B",
            "middle-window affordability and hold-aware burden",
            StaminaMeasurementGateStatus.PASS if gate_b else StaminaMeasurementGateStatus.OPEN,
            f"State2 exchanges B-E={len(gate_b_rows)}; actual hold exchanges={len(hold_rows)}; "
            f"hold statuses={dict(Counter(r.hold_payment_status for r in hold_rows))}",
            "attacker/defender ceilings, requested funding, hedge headroom, and commitment+hold funding are structured",
        ),
        StaminaMeasurementGate(
            "C",
            "decisive exchanges classified by stamina state",
            StaminaMeasurementGateStatus.PASS if gate_c else StaminaMeasurementGateStatus.OPEN,
            f"exchange records={sum(len(m.exchanges) for m in measurements)}",
            "under-commitment, submission progress, taps, escapes, and terminal context are preserved per exchange",
        ),
        StaminaMeasurementGate(
            "D",
            "stamina-source accounting reconciles",
            StaminaMeasurementGateStatus.PASS if gate_d else StaminaMeasurementGateStatus.OPEN,
            f"side reconciliations={sum(r.top_stamina_reconciles + r.bottom_stamina_reconciles for m in measurements for r in m.matches)}/1000",
            "behavior spend/recovery, both commitment roles, and hold spend reconcile to final stamina",
        ),
        StaminaMeasurementGate(
            "E",
            "funded and UNFUNDED exchange states measured",
            StaminaMeasurementGateStatus.PASS if gate_e else StaminaMeasurementGateStatus.OPEN,
            f"exchange records={sum(len(m.exchanges) for m in measurements)}",
            "true initiator/responder effective funding pair is recorded for every exchange",
        ),
        StaminaMeasurementGate(
            "F",
            "zero-stamina attacks exposed",
            StaminaMeasurementGateStatus.PASS if gate_f else StaminaMeasurementGateStatus.OPEN,
            f"zero-stamina attacks={sum(row.initiator_stamina == 0 for m in measurements for row in m.exchanges)}",
            "every zero-stamina initiator remains UNFUNDED; outcomes are observational",
        ),
        StaminaMeasurementGate(
            "G",
            "policy continuity and deterministic replay",
            StaminaMeasurementGateStatus.PASS if gate_g else StaminaMeasurementGateStatus.OPEN,
            f"mechanical_equal={mechanical_equal}; replay_equal={replay_equal}; historical_A-D={historical_pinned}",
            "measurement cannot perturb outcomes; reviewed v0.4b B-D numbers stay pinned; Surface E has no outcome target",
        ),
        StaminaMeasurementGate(
            "H",
            "checker-owned structured measurement evidence",
            StaminaMeasurementGateStatus.PASS if gate_h else StaminaMeasurementGateStatus.OPEN,
            f"A-G pass={all(gates_so_far)}; structured surfaces={len(measured)}",
            "measurement PASS means evidence exists/reconciles/replays, not that the economy is healthy",
        ),
    )


def render_stamina_economy_measurement() -> tuple[str, ...]:
    surfaces = measured_surfaces()
    gates = measure_stamina_economy_definition_of_done()
    lines = [gate.render() for gate in gates]
    lines.append(
        "STAMINA-ECONOMY MEASUREMENT NOTE: gate PASS means complete, "
        "reconciled, deterministic evidence; it is not a gameplay-health verdict."
    )
    lines.extend(
        "STAMINA-ECONOMY SURFACE — " + _surface_overview_line(s)
        for s in surfaces
    )
    lines.extend("STAMINA-ECONOMY DURATION — " + _surface_duration_line(s) for s in surfaces)
    lines.append("STAMINA-ECONOMY RECOVERY — " + _surface_e_recovery_line(surfaces[4]))
    lines.extend(
        "STAMINA-ECONOMY AFFORDABILITY — " + _surface_affordability_line(s)
        for s in surfaces[1:]
    )
    lines.extend(
        "STAMINA-ECONOMY DECISIVE — " + _surface_decisive_line(s)
        for s in surfaces
    )
    lines.extend(
        "STAMINA-ECONOMY STATE2 DECISIVE AFFORDABILITY — "
        + _surface_state2_decisive_affordability_line(s)
        for s in surfaces
    )
    lines.extend(
        "STAMINA-ECONOMY SOURCES — " + _aggregate_sources(s)
        for s in surfaces
    )
    lines.extend(
        "STAMINA-ECONOMY FUNDING — " + _surface_funding_line(s)
        for s in surfaces
    )
    lines.extend(
        "STAMINA-ECONOMY ZERO — " + _surface_zero_attack_line(s)
        for s in surfaces
    )
    lines.extend(
        "STAMINA-RULE PRECHANGE DEFENDER DRAIN — "
        + _render_defender_drain_observation(observation)
        for observation in prechange_defender_drain_observations()
    )
    return tuple(lines)
