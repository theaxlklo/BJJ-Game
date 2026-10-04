from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from statistics import median

from ..domain.action import Commitment
from ..domain.model import Side
from ..engine.match import MountMatch
from ..engine.stamina import DEFAULT_STAMINA_COST_POLICY
from ..interfaces.batch import BatchSummary, run_escape_first_batch
from ..positions.mount.catalog import (
    BOTTOM_RESPONSE_FOREARM_FRAME,
    BOTTOM_RESPONSE_TURN_IN_RECOVERY,
    TOP_AMERICANA_SUBMISSION_FINISH,
    TOP_HIGH_MOUNT_CLIMB,
)
from ..positions.mount.matchups import RAW_GRADES
from .stamina_economy import (
    StaminaEconomyState,
    StaminaEconomySurface,
    _measurement,
    _surface_kwargs,
    measured_surfaces,
    measure_stamina_economy_definition_of_done,
    prechange_defender_drain_observations,
)


class StaminaRuleGateStatus(str, Enum):
    PASS = "PASS"
    OPEN = "OPEN"


@dataclass(frozen=True, slots=True)
class StaminaRuleGate:
    letter: str
    name: str
    status: StaminaRuleGateStatus
    metric: str
    evidence: str

    def render(self) -> str:
        return (
            f"STAMINA-RULE GATE {self.letter} [{self.status.value}]: "
            f"{self.name} — {self.metric}; {self.evidence}"
        )


def _taps(summary: BatchSummary) -> int:
    return summary.outcome_counts.get("TAP — Americana", 0)


def _escapes(summary: BatchSummary) -> int:
    from ..domain.model import ExitDestination

    return sum(
        summary.outcome_counts.get(destination.value, 0)
        for destination in ExitDestination
    )


def _timeouts(summary: BatchSummary) -> int:
    return summary.outcome_counts.get("TIMEOUT — Mount retained", 0)


@lru_cache(maxsize=1)
def postchange_surfaces() -> tuple[StaminaEconomySurface, ...]:
    surfaces: list[StaminaEconomySurface] = []
    for label in (
        "A public MATCH",
        "B trusts reads",
        "C one level above",
        "D always HIGH",
        "E trusts reads + Bottom RECOVER",
    ):
        kwargs = _surface_kwargs(label)
        summary = run_escape_first_batch(
            **kwargs,
            enable_stamina_settlement_rules=True,
            measure_stamina_economy=True,
        )
        surfaces.append(StaminaEconomySurface(label=label, summary=summary))
    return tuple(surfaces)


def _fresh_postchange_surfaces() -> tuple[StaminaEconomySurface, ...]:
    surfaces: list[StaminaEconomySurface] = []
    for label in (
        "A public MATCH",
        "B trusts reads",
        "C one level above",
        "D always HIGH",
        "E trusts reads + Bottom RECOVER",
    ):
        kwargs = _surface_kwargs(label)
        summary = run_escape_first_batch(
            **kwargs,
            enable_stamina_settlement_rules=True,
            measure_stamina_economy=True,
        )
        surfaces.append(StaminaEconomySurface(label=label, summary=summary))
    return tuple(surfaces)


def _prechange_gate_a() -> tuple[bool, str]:
    obs = {
        (item.surface_label, item.selector, item.initiator_side): item
        for item in prechange_defender_drain_observations()
    }
    b_top = obs[("B trusts reads", "exact-zero", Side.TOP)]
    b_bottom = obs[("B trusts reads", "exact-zero", Side.BOTTOM)]
    e_top = obs[("E trusts reads + Bottom RECOVER", "exact-zero", Side.TOP)]
    ok = (
        b_top.total_charged == 29
        and b_bottom.total_charged == 66
        and b_top.total_charged + b_bottom.total_charged == 95
        and e_top.exchange_count == 1949
        and e_top.response_charged == 5010
        and e_top.hold_charged == 1192
        and e_top.total_charged == 6202
        and e_top.responder_behavior_recovery == 8658
    )
    return (
        ok,
        (
            f"Surface B exact-zero Top->Bottom={b_top.total_charged}, "
            f"Bottom->Top={b_bottom.total_charged}, combined="
            f"{b_top.total_charged + b_bottom.total_charged}; "
            f"Surface E Top exact-zero exchanges={e_top.exchange_count}, "
            f"response/hold/total={e_top.response_charged}/"
            f"{e_top.hold_charged}/{e_top.total_charged}, "
            f"Bottom recovery={e_top.responder_behavior_recovery}, "
            f"share={e_top.recovery_share:.4f}"
        ),
    )


def _rule_b_evidence(surfaces: tuple[StaminaEconomySurface, ...]):
    rows = [
        row
        for surface in surfaces
        for row in _measurement(surface).exchanges
        if row.initiator_effective_commitment == "UNFUNDED"
    ]
    exact_zero = [row for row in rows if row.initiator_stamina == 0]
    charged_rows = [
        row
        for row in rows
        if row.response_commitment_charged != 0 or row.hold_charged != 0
    ]
    return rows, exact_zero, charged_rows


def _rule_c_evidence(surfaces: tuple[StaminaEconomySurface, ...]):
    holds = [
        row
        for surface in surfaces
        for row in _measurement(surface).exchanges
        if row.submission_hold
    ]
    mismatches = []
    additive_double = []
    for row in holds:
        if row.initiator_effective_commitment == "UNFUNDED":
            expected_covered = 0
            expected_request = 0
        else:
            expected_covered = min(
                row.hold_nominal_cost,
                row.response_commitment_charged,
            )
            expected_request = max(
                0,
                row.hold_nominal_cost - row.response_commitment_charged,
            )
        if (
            row.hold_covered_by_response != expected_covered
            or row.hold_requested != expected_request
        ):
            mismatches.append(row)
        if (
            row.response_commitment_charged >= 3
            and row.hold_charged > 0
        ):
            additive_double.append(row)
    return holds, mismatches, additive_double


def _resolution_signature(match: MountMatch, result) -> tuple:
    return (
        result.base_resolution,
        result.resolution,
        match.axis,
        match.submission_state.stage,
        match.submission_tapped,
        match.exit_destination,
    )


def _immediate_resolution_probe() -> tuple[int, int]:
    cases = (
        (0, 20, TOP_AMERICANA_SUBMISSION_FINISH, BOTTOM_RESPONSE_TURN_IN_RECOVERY, Commitment.LOW, Commitment.HIGH, True),
        (100, 100, TOP_HIGH_MOUNT_CLIMB, BOTTOM_RESPONSE_FOREARM_FRAME, Commitment.MEDIUM, Commitment.MEDIUM, False),
    )
    mismatches = 0
    for (
        top_stamina,
        bottom_stamina,
        action_id,
        response_id,
        commitment,
        response_commitment,
        active_submission,
    ) in cases:
        signatures = []
        for enabled in (False, True):
            match = MountMatch(
                starting_axis=4.0,
                enable_v02_setup=True,
                enable_v03_submissions=True,
                enable_v04_commitment_semantics=True,
                enable_v04b_recognition=True,
                enable_stamina_settlement_rules=enabled,
            )
            match.top.stamina.set_current(top_stamina)
            match.bottom.stamina.set_current(bottom_stamina)
            match.initiator = Side.TOP
            if active_submission:
                from ..domain.submission import SubmissionStage

                match.submission_state.stage = SubmissionStage.THREAT
            read = match.recognize_commitment(
                requested=commitment,
                intent_roll=3,
                capability_roll=3,
            )
            result = match.attempt(
                action_id=action_id,
                response_id=response_id,
                commitment=commitment,
                response_commitment=response_commitment,
                recognition_read=read,
            )
            signatures.append(_resolution_signature(match, result))
        mismatches += signatures[0] != signatures[1]
    return len(cases), mismatches


def _surface_e_recovery(surface: StaminaEconomySurface) -> dict[str, object]:
    measurement = _measurement(surface)
    records = measurement.matches
    clear_times = [
        record.first_state2_exit_to_state1_time
        for record in records
        if record.first_state2_exit_to_state1_time is not None
    ]
    return {
        "matches_clearing": sum(
            record.bottom_exhausted_latch_clears > 0 for record in records
        ),
        "latch_clears": sum(
            record.bottom_exhausted_latch_clears for record in records
        ),
        "to_escape": sum(record.bottom_switches_to_escape for record in records),
        "state2_exits": sum(record.state2_exits_to_state1 for record in records),
        "state2_reentries": sum(
            record.state2_reentries_after_state1 for record in records
        ),
        "clear_time_median": median(clear_times) if clear_times else None,
        "clear_stamina": Counter(
            value
            for record in records
            for value in record.bottom_latch_clear_stamina
        ),
    }


def _threat_observation(surface: StaminaEconomySurface) -> dict[str, int]:
    measurement = _measurement(surface)
    rows = measurement.exchanges
    return {
        "matches_threat": surface.summary.matches_reached_submission_threat,
        "threat_entries": sum(row.transition_into_threat for row in rows),
        "control_entries": sum(row.transition_into_control for row in rows),
        "finish_entries": sum(row.transition_into_finish for row in rows),
        "taps": _taps(surface.summary),
    }


@lru_cache(maxsize=1)
def measure_stamina_rule_definition_of_done() -> tuple[StaminaRuleGate, ...]:
    post = postchange_surfaces()

    gate_a_ok, gate_a_metric = _prechange_gate_a()

    unfunded_rows, zero_rows, charged_unfunded = _rule_b_evidence(post)
    gate_b_ok = bool(unfunded_rows) and not charged_unfunded

    holds, hold_mismatches, additive_double = _rule_c_evidence(post)
    gate_c_ok = bool(holds) and not hold_mismatches and not additive_double

    recovery = _surface_e_recovery(post[4])
    gate_d_ok = (
        recovery["latch_clears"] > 0
        and recovery["to_escape"] > 0
    )

    from .checker import measure_v04b_definition_of_done, V02GateStatus

    recognition_gates = measure_v04b_definition_of_done()
    recognition_invariants_ok = all(
        gate.status is V02GateStatus.PASS
        for gate in recognition_gates
        if gate.letter in {"B", "C", "D", "E"}
    )
    probe_cases, probe_mismatches = _immediate_resolution_probe()
    gate_e_ok = recognition_invariants_ok and probe_mismatches == 0

    trust_taps = _taps(post[1].summary)
    gate_f_ok = 0 < trust_taps < post[1].summary.matches / 2

    reconciled = [
        record
        for surface in post
        for record in _measurement(surface).matches
        if record.top_stamina_reconciles and record.bottom_stamina_reconciles
    ]
    all_match_records = [
        record for surface in post for record in _measurement(surface).matches
    ]
    waived = sum(
        row.response_commitment_waived
        for surface in post
        for row in _measurement(surface).exchanges
    )
    covered = sum(
        row.hold_covered_by_response
        for surface in post
        for row in _measurement(surface).exchanges
    )
    gate_g_ok = len(reconciled) == len(all_match_records) == 500

    historical_measurement_ok = all(
        gate.status.value == "PASS"
        for gate in measure_stamina_economy_definition_of_done()
    )
    costs_ok = (
        DEFAULT_STAMINA_COST_POLICY.cost(Commitment.LOW) == 3
        and DEFAULT_STAMINA_COST_POLICY.cost(Commitment.MEDIUM) == 7
        and DEFAULT_STAMINA_COST_POLICY.cost(Commitment.HIGH) == 12
    )
    unfunded_equality_ok = (
        MountMatch._response_undercommitment_modifier(
            initiator_commitment=None,
            responder_commitment=None,
        )
        == 0
    )
    gate_h_ok = (
        len(RAW_GRADES) == 18
        and historical_measurement_ok
        and costs_ok
        and unfunded_equality_ok
    )

    replay_equal = post == _fresh_postchange_surfaces()
    gate_i_ok = replay_equal and len(post) == 5

    return (
        StaminaRuleGate(
            "A",
            "pre-change defender-drain evidence is frozen",
            StaminaRuleGateStatus.PASS if gate_a_ok else StaminaRuleGateStatus.OPEN,
            gate_a_metric,
            "checker-owned baseline precedes Rule 1 / Rule 2",
        ),
        StaminaRuleGate(
            "B",
            "UNFUNDED initiator imposes zero responder stamina cost",
            StaminaRuleGateStatus.PASS if gate_b_ok else StaminaRuleGateStatus.OPEN,
            (
                f"UNFUNDED exchanges={len(unfunded_rows)}; exact-zero subset={len(zero_rows)}; "
                f"charged violations={len(charged_unfunded)}"
            ),
            "response commitment and supplemental hold charge must both be zero",
        ),
        StaminaRuleGate(
            "C",
            "provisional hold is supplemental rather than additive",
            StaminaRuleGateStatus.PASS if gate_c_ok else StaminaRuleGateStatus.OPEN,
            (
                f"hold exchanges={len(holds)}; settlement mismatches={len(hold_mismatches)}; "
                f"additive double-charge cases={len(additive_double)}"
            ),
            "response commitment covers the first 3 points of hold burden",
        ),
        StaminaRuleGate(
            "D",
            "existing RECOVER can leave Exhausted",
            StaminaRuleGateStatus.PASS if gate_d_ok else StaminaRuleGateStatus.OPEN,
            (
                f"matches clearing={recovery['matches_clearing']}; "
                f"latch clears={recovery['latch_clears']}; "
                f"CONSERVE->ESCAPE={recovery['to_escape']}; "
                f"State2->State1 exits={recovery['state2_exits']}; "
                f"reentries={recovery['state2_reentries']}; "
                f"first clear median={recovery['clear_time_median']}; "
                f"clear stamina={dict(recovery['clear_stamina'])}"
            ),
            "nonzero recovery proves the old deadlock is broken; frequency is observational",
        ),
        StaminaRuleGate(
            "E",
            "Recognition and immediate resolution semantics remain intact",
            StaminaRuleGateStatus.PASS if gate_e_ok else StaminaRuleGateStatus.OPEN,
            (
                f"Recognition B-E pass={recognition_invariants_ok}; "
                f"isolated equivalence mismatches={probe_mismatches}/{probe_cases}"
            ),
            "settlement may change stamina and later trajectory, not the current exchange result",
        ),
        StaminaRuleGate(
            "F",
            "v0.3a competent-defender Gate B remeasurement",
            StaminaRuleGateStatus.PASS if gate_f_ok else StaminaRuleGateStatus.OPEN,
            (
                f"historical trust-read Tap=6/100; "
                f"post-change trust-read Tap={trust_taps}/{post[1].summary.matches}"
            ),
            "unchanged criterion is 0% < informed Tap < 50%; OPEN is recorded, never tuned in-place",
        ),
        StaminaRuleGate(
            "G",
            "stamina accounting remains exact",
            StaminaRuleGateStatus.PASS if gate_g_ok else StaminaRuleGateStatus.OPEN,
            (
                f"reconciled matches={len(reconciled)}/{len(all_match_records)}; "
                f"response stamina waived={waived}; hold burden covered by response={covered}"
            ),
            "actual charges reconcile while waived/covered amounts remain separately visible",
        ),
        StaminaRuleGate(
            "H",
            "deferred mechanics remain frozen",
            StaminaRuleGateStatus.PASS if gate_h_ok else StaminaRuleGateStatus.OPEN,
            (
                f"matrix entries={len(RAW_GRADES)}; historical measurement pass={historical_measurement_ok}; "
                f"costs=3/7/12:{costs_ok}; UNFUNDED equality={unfunded_equality_ok}"
            ),
            "Recognition, commitment costs, exhaustion, action legality, and UNFUNDED equality are unchanged",
        ),
        StaminaRuleGate(
            "I",
            "checker-owned structured evidence and deterministic replay",
            StaminaRuleGateStatus.PASS if gate_i_ok else StaminaRuleGateStatus.OPEN,
            f"surfaces={len(post)}; replay_equal={replay_equal}",
            "design-gate OPEN states remain visible without converting them into checker execution failures",
        ),
    )


def _surface_state_shares(surface: StaminaEconomySurface) -> tuple[float, float, float]:
    records = _measurement(surface).matches
    total_elapsed = sum(record.elapsed_seconds for record in records)
    if total_elapsed == 0:
        return 0.0, 0.0, 0.0
    return (
        sum(record.state1_seconds for record in records) / total_elapsed,
        sum(record.state2_seconds for record in records) / total_elapsed,
        sum(record.state3_seconds for record in records) / total_elapsed,
    )


def render_prediction_comparison() -> tuple[str, ...]:
    pre = measured_surfaces()
    post = postchange_surfaces()
    recovery = _surface_e_recovery(post[4])

    lines = []

    lines.append(
        "P1 trust-read taps — predicted decrease/stay low; "
        f"baseline={_taps(pre[1].summary)}, post={_taps(post[1].summary)}, "
        f"direction={'down' if _taps(post[1].summary) < 6 else 'same' if _taps(post[1].summary) == 6 else 'up'}"
    )
    lines.append(
        "P2 public-MATCH informed taps — predicted remain at/near 0; "
        f"baseline={_taps(pre[0].summary)}, post={_taps(post[0].summary)}"
    )

    stamina_parts = []
    for before, after in zip(pre, post):
        stamina_parts.append(
            f"{after.label} "
            f"{before.summary.top_final_stamina_median:.1f}/"
            f"{before.summary.bottom_final_stamina_median:.1f}"
            f"->{after.summary.top_final_stamina_median:.1f}/"
            f"{after.summary.bottom_final_stamina_median:.1f}"
        )
    lines.append(
        "P3 final stamina — predicted responder increase on some surfaces, especially E; "
        + "; ".join(stamina_parts)
    )

    pre_e_shares = _surface_state_shares(pre[4])
    post_e_shares = _surface_state_shares(post[4])
    lines.append(
        "P4 depleted-state occupancy/recovery — predicted weaker trap and >=1 return to State1; "
        f"Surface E State1/2/3 share "
        f"{pre_e_shares[0]:.3f}/{pre_e_shares[1]:.3f}/{pre_e_shares[2]:.3f}"
        f"->{post_e_shares[0]:.3f}/{post_e_shares[1]:.3f}/{post_e_shares[2]:.3f}; "
        f"latch clears={recovery['latch_clears']}; State2->State1={recovery['state2_exits']}"
    )

    lines.append(
        "P5 hedge comparison — predicted hedge-one/always-HIGH at least as submission-resistant as trust-read; "
        f"trust/hedge/high taps={_taps(post[1].summary)}/"
        f"{_taps(post[2].summary)}/{_taps(post[3].summary)}; "
        f"response spend={post[1].summary.total_response_commitment_stamina_charged}/"
        f"{post[2].summary.total_response_commitment_stamina_charged}/"
        f"{post[3].summary.total_response_commitment_stamina_charged}"
    )

    public_threat = _threat_observation(post[0])
    trust_threat = _threat_observation(post[1])
    lines.append(
        "P6 Threat reach — predicted possible fall, observational only; "
        f"public matches-Threat/entries/Control/Finish/Tap="
        f"{public_threat['matches_threat']}/{public_threat['threat_entries']}/"
        f"{public_threat['control_entries']}/{public_threat['finish_entries']}/"
        f"{public_threat['taps']}; "
        f"trust={trust_threat['matches_threat']}/{trust_threat['threat_entries']}/"
        f"{trust_threat['control_entries']}/{trust_threat['finish_entries']}/"
        f"{trust_threat['taps']}"
    )
    return tuple(lines)


def render_stamina_rule_change() -> tuple[str, ...]:
    post = postchange_surfaces()
    lines = [gate.render() for gate in measure_stamina_rule_definition_of_done()]
    lines.append(
        "STAMINA-RULE NOTE: Gates D/F may be OPEN as measured regressions; "
        "OPEN does not authorize tuning inside this slice."
    )

    for surface in post:
        measurement = _measurement(surface)
        unfunded = [
            row
            for row in measurement.exchanges
            if row.initiator_effective_commitment == "UNFUNDED"
        ]
        exact_zero = [row for row in unfunded if row.initiator_stamina == 0]
        holds = [row for row in measurement.exchanges if row.submission_hold]
        waived = sum(row.response_commitment_waived for row in measurement.exchanges)
        covered = sum(row.hold_covered_by_response for row in holds)
        supplemental = sum(row.hold_charged for row in holds)
        threat = _threat_observation(surface)
        lines.append(
            f"STAMINA-RULE SURFACE — {surface.label}: "
            f"taps={_taps(surface.summary)}, escapes={_escapes(surface.summary)}, "
            f"timeouts={_timeouts(surface.summary)}, "
            f"final stamina={surface.summary.top_final_stamina_median:.1f}/"
            f"{surface.summary.bottom_final_stamina_median:.1f}, "
            f"UNFUNDED/exact-zero exchanges={len(unfunded)}/{len(exact_zero)}, "
            f"waived response={waived}, hold covered={covered}, "
            f"supplemental hold charged={supplemental}, "
            f"Threat matches/entries/Control/Finish="
            f"{threat['matches_threat']}/{threat['threat_entries']}/"
            f"{threat['control_entries']}/{threat['finish_entries']}"
        )

    lines.extend(
        "STAMINA-RULE PREDICTION — " + line
        for line in render_prediction_comparison()
    )
    return tuple(lines)
