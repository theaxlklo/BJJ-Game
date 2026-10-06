"""Stage 1A shadow observer and C1-C4 scoring for the joint tactical evaluator
(docs/TACTICAL_EVALUATOR_PREREGISTRATION.md, frozen at 4e61bad).

The baseline batch policy (ESCAPE_FIRST, fixed commitments) is unchanged. Scoped
wrappers, all restored on exit and on exceptions:

- EscapeFirstInitiatorPolicy.choose: at every real decision window, TE-1's
  values and shadow choice are computed from a snapshot, then the real policy
  is delegated exactly once. D3-B LOCKOUT_HOLD counterfactual choose() calls
  (the window then holds) are delegated but never evaluated.
- MountMatch.attempt: the baseline's actual (action, commitment) is valued
  from the pre-exchange snapshot, the real attempt is delegated exactly once,
  and realized events are read from the engine's own history.
- D3BTokenLockoutController.decide: read-only, to recognize LOCKOUT_HOLD.
- random.Random draw methods: counted, never substituted. Draws made while the
  evaluator runs must be 0 (P4); every other draw is hashed in order so the
  baseline RNG sequence can be compared with an evaluator-free run.

Not thread-safe: run standalone, never concurrently with gameplay.
"""
from __future__ import annotations

from collections import Counter
from contextlib import ExitStack, contextmanager
from fractions import Fraction
import gzip
import hashlib
import json
import math
from pathlib import Path
import random
from statistics import median
from unittest.mock import patch

from ..domain.action import Commitment
from ..domain.model import Side
from ..engine.match import MountMatch
from ..interfaces import batch as batch_module
from ..interfaces import tactical_evaluator as te
from ..interfaces.batch import (
    BatchBehaviorMode,
    BatchResponderMode,
    BatchResponseCommitmentMode,
    EscapeFirstInitiatorPolicy,
    run_escape_first_batch,
)
from ..interfaces.handoff_policy import D3BTokenLockoutController, HandoffDecisionKind
from ..interfaces.recovery_policy import RecoveryInitiationMode
from ..positions.mount.catalog import (
    BOTTOM_TRAP_AND_ROLL_ESCAPE,
    TOP_AMERICANA_ARM_ISOLATION,
    TOP_HIGH_MOUNT_CLIMB,
)
from .d3b_promotion import canonical_kwargs
from .setup_policy import surfaces as setup_surfaces
from .stamina_adoption_verification import _match_gameplay_signature

PREREGISTRATION = "4e61bada3998e1d97bdeaba975e92aa282c92bfb"
SUMMARY_EVIDENCE = Path("docs/evidence/tactical_evaluator_stage1a.json")
RECORDS_EVIDENCE = Path("docs/evidence/tactical_evaluator_stage1a_records.json.gz")

_RANDOM_METHODS = ("random", "randrange", "randint", "choice", "choices", "getrandbits",
                   "shuffle", "sample", "uniform", "triangular", "gauss", "normalvariate",
                   "betavariate", "expovariate", "seed", "getstate", "setstate", "binomialvariate")


def surfaces() -> dict[str, dict]:
    """Frozen Stage-1A surfaces (section 4): A-PROD, B-PROD, E-PROD seeds 42 and
    142 with stalling OFF + shadow and ON, and the v0.3a PROTECT probe."""
    base = setup_surfaces()
    return {
        "A-PROD": base["A-PROD"],
        "B-PROD": base["B-PROD"],
        "E-PROD 42 OFF": canonical_kwargs(42, "OFF"),
        "E-PROD 42 ON": canonical_kwargs(42, "ON"),
        "E-PROD 142 OFF": canonical_kwargs(142, "OFF"),
        "E-PROD 142 ON": canonical_kwargs(142, "ON"),
        "PROTECT probe": base["v0.3a PROTECT probe (historical debt)"],
    }


# Preregistration section 4 baselines: (Threat matches, Tap, escapes, timeouts,
# Top completed builds). E-PROD OFF + shadow and ON are identical
# (docs/LATE_RECOVERY_CHARACTERIZATION.md).
FROZEN_BASELINES = {
    "A-PROD": (78, 0, 22, 78, 312),
    "B-PROD": (59, 9, 12, 79, 880),
    "E-PROD 42 OFF": (61, 5, 30, 65, 844),
    "E-PROD 42 ON": (61, 5, 30, 65, 844),
    "E-PROD 142 OFF": (57, 4, 31, 65, 841),
    "E-PROD 142 ON": (57, 4, 31, 65, 841),
    "PROTECT probe": (0, 0, 2, 98, 1768),
}

C1_SURFACES = ("A-PROD",)
C3_SURFACES = ("A-PROD", "B-PROD", "E-PROD 42 OFF", "E-PROD 42 ON",
               "E-PROD 142 OFF", "E-PROD 142 ON")
C4_SURFACES = ("PROTECT probe",)


def model_for(kwargs: dict) -> te.OpponentModel:
    return te.OpponentModel.from_settings(
        bottom_responder_mode=kwargs.get("bottom_responder_mode", BatchResponderMode.RANDOM),
        response_commitment_mode=kwargs.get(
            "response_commitment_mode", BatchResponseCommitmentMode.FIXED_MEDIUM),
        recognition=bool(kwargs.get("enable_v04b_recognition", False)),
    )


# ---------------------------------------------------------------------------
# RNG instrumentation (count only; never substitutes or reorders a draw)
# ---------------------------------------------------------------------------


class RngTrace:
    def __init__(self) -> None:
        self.active = False
        self.evaluator_draws: Counter = Counter()
        self.baseline_draws = 0
        self._digest = hashlib.sha256()

    @property
    def baseline_digest(self) -> str:
        return self._digest.hexdigest()

    def note(self, name: str, result) -> None:
        if self.active:
            self.evaluator_draws[name] += 1
        else:
            self.baseline_draws += 1
            self._digest.update(f"{name}:{result!r};".encode())


@contextmanager
def count_rng(trace: RngTrace):
    """Wrap every random.Random draw method; the original runs exactly once with
    the same arguments and its result is returned unchanged."""
    def wrap(name, original):
        def counted(self, *args, **kwargs):
            result = original(self, *args, **kwargs)
            trace.note(name, result)
            return result
        return counted

    with ExitStack() as stack:
        for name in _RANDOM_METHODS:
            original = getattr(random.Random, name, None)
            if original is not None:
                stack.enter_context(patch.object(random.Random, name, wrap(name, original)))
        yield trace


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _q(value: Fraction) -> str:
    return str(value)


def _c(commitment: Commitment | None) -> str:
    return commitment.value if commitment is not None else "UNFUNDED"


def _projection(p: te.SetupProjection | None) -> dict | None:
    if p is None:
        return None
    return dict(
        r=p.builds_remaining, delta_s=p.elapsed_seconds, p_adv=_q(p.p_advance),
        own=[p.own.current, p.own.band.value], opp=[p.opponent.current, p.opponent.band.value],
        axis=p.axis, band=p.band.value,
        use_values={c.value: _q(v) for c, v in p.use_values},
        use_value=_q(p.use_value), chain=_q(p.chain_probability),
        setup_future=_q(p.setup_future),
    )


def _value(v: te.TacticalValue) -> dict:
    return dict(
        action=v.action_id, requested=v.requested.value, effective=_c(v.effective),
        terminal=_q(v.terminal), progress=_q(v.progress), setup_future=_q(v.setup_future),
        axis_realized=_q(v.axis_realized), axis_raw=_q(v.axis_raw),
        stamina_cost=v.stamina_cost, enters_exhausted=v.enters_exhausted,
        setup_advance=_q(v.setup_advance), projection=_projection(v.projection),
    )


def _new_entries(history: list, before: int) -> list:
    return list(history[before:])


# ---------------------------------------------------------------------------
# Observer
# ---------------------------------------------------------------------------


def observe_batch(*, evaluate: bool = True, **kwargs):
    """Run the unchanged baseline batch with the shadow observer.

    Returns (summary, per-match gameplay signatures, per-match event lists,
    RngTrace, LOCKOUT_HOLD counterfactual choose() count)."""
    model = model_for(kwargs)
    behavior_mode = kwargs.get("bottom_behavior_mode", BatchBehaviorMode.FIXED)
    recovery_mode = kwargs.get("recovery_initiation_mode", RecoveryInitiationMode.CURRENT)
    original_choose = EscapeFirstInitiatorPolicy.choose
    original_attempt = MountMatch.attempt
    original_decide = D3BTokenLockoutController.decide
    created: list[MountMatch] = []
    timelines: list[list[dict]] = []
    index_of: dict[int, int] = {}
    last_handoff: dict[int, HandoffDecisionKind] = {}
    pending: dict[int, dict] = {}
    trace = RngTrace()
    counterfactuals = [0]

    def factory(*args, **factory_kwargs):
        match = MountMatch(*args, **factory_kwargs)
        index_of[id(match)] = len(created)
        created.append(match)
        timelines.append([])
        return match

    def observed_decide(controller, match, *, armed):
        decision = original_decide(controller, match, armed=armed)
        last_handoff[id(match)] = decision.kind
        return decision

    def observed_choose(policy, match):
        kind = last_handoff.pop(id(match), None)
        if match.initiator is Side.BOTTOM and kind is HandoffDecisionKind.LOCKOUT_HOLD:
            # Counterfactual call made for the D3-B collector; the window holds.
            counterfactuals[0] += 1
            return original_choose(policy, match)
        record = dict(kind="decision", t=match.elapsed_simulated_time,
                      side=match.initiator.value, d3b=kind.value if kind else None)
        if evaluate:
            state = te.State.of(match)
            allowed = te.allowed_commitments(
                match, bottom_behavior_mode=behavior_mode,
                recovery_initiation_mode=recovery_mode)
            trace.active = True
            try:
                values = te.candidates(match, model, state, allowed)
                choice = te.choose_te1(match, values)
            finally:
                trace.active = False
            record.update(
                allowed=[c.value for c in allowed],
                te1_tier=choice.tier,
                te1_action=choice.value.action_id if choice.value else None,
                te1_requested=choice.value.requested.value if choice.value else None,
                te1_effective=_c(choice.value.effective) if choice.value else None,
                te1_value=_value(choice.value) if choice.value else None,
                values=values,
            )
        decision = original_choose(policy, match)
        record.update(action=decision.action_id, reason=decision.reason)
        timelines[index_of[id(match)]].append(record)
        pending[id(match)] = record
        return decision

    def observed_attempt(match, *args, **kw):
        decision = pending.pop(id(match), None)
        action_id, requested = kw["action_id"], kw["commitment"]
        if decision is None or decision["action"] != action_id:
            raise RuntimeError("attempt without its real policy decision")
        state = te.State.of(match)
        record = dict(kind="attempt", t=match.elapsed_simulated_time,
                      side=state.initiator.value, action=action_id,
                      requested=requested.value,
                      ready_use=action_id in state.ready,
                      tier_before=dict(state.tiers))
        if evaluate:
            trace.active = True
            try:
                value = te.evaluate(match, model, state, action_id, requested, project=False)
                outcomes = te.outcome_distribution(match, model, state, action_id, requested)
            finally:
                trace.active = False
            grades = Counter()
            for weight, result, _, _ in outcomes:
                grades[result.final_grade.display] += weight
            record.update(p_terminal=value.terminal, p_progress=value.progress,
                          p_setup_advance=value.setup_advance,
                          predicted_grades=dict(grades))
        history = match.history
        marks = (len(history.submission_change_history), len(history.setup_change_history))
        result = original_attempt(match, *args, **kw)
        submission = _new_entries(history.submission_change_history, marks[0])
        setup = _new_entries(history.setup_change_history, marks[1])
        threat_entry = any(e.startswith("entry:") for e in submission)
        stage_advance = any(":" not in e and not e.endswith("->Tap") for e in submission)
        record.update(
            effective=_c(result.attempt.effective_commitment),
            response=kw["response_id"],
            realized_grade=result.resolution.final_grade.display,
            terminal=(result.resolution.exit_destination is not None
                      if state.initiator is Side.BOTTOM else match.submission_tapped),
            progress=state.initiator is Side.TOP and (threat_entry or stage_advance),
            threat_entry=threat_entry,
            setup_advanced=bool(setup),
            exit=(result.resolution.exit_destination.value
                  if result.resolution.exit_destination is not None else None),
        )
        if evaluate:
            # C0: the pure path reproduces the real exchange exactly.
            replay = te.resolve(match, state, action_id, kw["response_id"],
                                result.attempt.effective_commitment,
                                result.response_effective_commitment)
            record["integrity"] = (
                replay.final_grade == result.resolution.final_grade
                and replay.axis_after == result.resolution.axis_after
                and replay.exit_destination == result.resolution.exit_destination
            )
        decision["attempt"] = len(timelines[index_of[id(match)]])
        timelines[index_of[id(match)]].append(record)
        return result

    with ExitStack() as stack:
        stack.enter_context(count_rng(trace))
        stack.enter_context(patch.object(batch_module, "MountMatch", factory))
        stack.enter_context(patch.object(EscapeFirstInitiatorPolicy, "choose", observed_choose))
        stack.enter_context(patch.object(MountMatch, "attempt", observed_attempt))
        stack.enter_context(patch.object(D3BTokenLockoutController, "decide", observed_decide))
        summary = run_escape_first_batch(**kwargs)
    if (EscapeFirstInitiatorPolicy.choose is not original_choose
            or MountMatch.attempt is not original_attempt
            or D3BTokenLockoutController.decide is not original_decide
            or batch_module.MountMatch is not MountMatch):
        raise RuntimeError("observer wrappers not restored")
    signatures = tuple(_match_gameplay_signature(m) for m in created)
    return summary, signatures, timelines, trace, counterfactuals[0]


def baseline_reference(**kwargs):
    """Evaluator-free reference run: (summary, signatures, RNG trace)."""
    summary, signatures, _, trace, _ = observe_batch(evaluate=False, **kwargs)
    return summary, signatures, trace


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def calibration(pairs) -> dict:
    """Sum of predicted probabilities vs realized count, exact ±3σ test:
    |realized - Σp| <= 3·sqrt(Σp(1-p))  <=>  (realized - Σp)² <= 9·Σp(1-p)."""
    expected = sum((p for p, _ in pairs), Fraction(0))
    variance = sum((p * (1 - p) for p, _ in pairs), Fraction(0))
    realized = sum(1 for _, hit in pairs if hit)
    deviation = realized - expected
    sigma = math.sqrt(variance)
    return dict(
        n=len(pairs),
        predicted=float(expected), predicted_exact=_q(expected),
        actual=realized,
        sigma=sigma, variance_exact=_q(variance),
        deviation=float(deviation),
        z=(float(deviation) / sigma if sigma > 0 else None),
        within_3_sigma=deviation * deviation <= 9 * variance,
    )


def _real_decisions(events):
    return [e for e in events if e["kind"] == "decision"]


def _builder_future(decision) -> Fraction | None:
    """TE-1 setup_future of the baseline's chosen builder: maximum over its
    (deduplicated) candidate commitments; None if it is not a live builder."""
    vals = [v for v in decision["values"] if v.action_id == decision["action"]
            and v.projection is not None]
    return max((v.setup_future for v in vals), default=None) if vals else None


def score(name: str, summary, timelines) -> tuple[dict, list]:
    attempts = [e for events in timelines for e in events if e["kind"] == "attempt"]
    top_attempts = [e for e in attempts if e["side"] == Side.TOP.value]

    # C1 — deterministic exactness at the baseline's actual commitment.
    deterministic = [e for e in top_attempts if max(e["predicted_grades"].values()) == 1]
    exact = [e for e in deterministic if e["predicted_grades"].get(e["realized_grade"], 0) == 1]
    c1 = dict(applies=name in C1_SURFACES, top_exchanges=len(top_attempts),
              deterministic_predictions=len(deterministic), exact=len(exact),
              mismatches=len(top_attempts) - len(exact))
    c1["status"] = ("PASS" if c1["mismatches"] == 0 and top_attempts else "FAIL") \
        if c1["applies"] else "N/A"

    # C2 — stochastic calibration, all baseline exchanges of the surface.
    c2 = {component: calibration([(e[f"p_{component}"], e[key]) for e in attempts])
          for component, key in (("terminal", "terminal"), ("progress", "progress"),
                                 ("setup_advance", "setup_advanced"))}
    by_side = {side.value: {component: calibration(
        [(e[f"p_{component}"], e[key]) for e in attempts if e["side"] == side.value])
        for component, key in (("terminal", "terminal"), ("progress", "progress"),
                               ("setup_advance", "setup_advanced"))}
        for side in Side}
    c2_status = "PASS" if all(v["within_3_sigma"] for v in c2.values()) else "FAIL"

    # C3 / C4 — Top setup decisions (baseline reason "setup") and their chains.
    rows, chain_rows = [], []
    converted_total = positive_total = 0
    top_setup = zero_total = 0
    for m, events in enumerate(timelines):
        builder_decisions = []
        for e in events:
            if e["kind"] == "decision" and e["side"] == Side.TOP.value and e["reason"] == "setup":
                future = _builder_future(e)
                builder_decisions.append((e, future))
        # Assign each setup decision to the chain closed by the next Ready use
        # (None: the chain was never used before the match ended).
        chain_of: dict[int, bool | None] = {}
        open_chain = []
        for e in events:
            if e["kind"] == "decision" and e["side"] == Side.TOP.value and e["reason"] == "setup":
                open_chain.append(e)
            if (e["kind"] == "attempt" and e["side"] == Side.TOP.value
                    and e["action"] == TOP_AMERICANA_ARM_ISOLATION and e["ready_use"]):
                chain_rows.append(dict(match=m, t=e["t"], builders=len(open_chain),
                                       threat_entry=e["threat_entry"],
                                       p_progress=_q(e["p_progress"])))
                for d in open_chain:
                    chain_of[id(d)] = e["threat_entry"]
                open_chain = []
        for d, future in builder_decisions:
            top_setup += 1
            zero_total += future == 0
            converted = chain_of.get(id(d))
            if converted:
                converted_total += 1
                positive_total += future > 0
            rows.append(dict(match=m, t=d["t"], action=d["action"],
                             setup_future=_q(future) if future is not None else None,
                             chain_converted=converted,
                             te1_tier=d["te1_tier"], te1_action=d["te1_action"],
                             te1_requested=d["te1_requested"],
                             projections={v.requested.value: _projection(v.projection)
                                          for v in d["values"]
                                          if v.action_id == d["action"]}))
    c3 = dict(applies=name in C3_SURFACES, population=converted_total,
              setup_future_positive=positive_total,
              share=(positive_total / converted_total if converted_total else None))
    c3["status"] = (("PASS" if 5 * positive_total >= 4 * converted_total else "FAIL")
                    if converted_total else "OPEN") if c3["applies"] else "N/A"
    c4 = dict(applies=name in C4_SURFACES, population=top_setup,
              setup_future_zero=zero_total,
              share=(zero_total / top_setup if top_setup else None))
    c4["status"] = (("PASS" if 2 * zero_total >= top_setup else "FAIL")
                    if top_setup else "OPEN") if c4["applies"] else "N/A"

    # Reported (not gated).
    decisions = [e for events in timelines for e in _real_decisions(events)]
    shadow = Counter()
    commitments = Counter()
    agreement = Counter()
    for d in decisions:
        shadow[f"{d['side']}:{d['te1_tier']}"] += 1
        if d["te1_action"] is not None:
            commitments[f"{d['side']}:{d['te1_tier']}:{d['te1_requested']}"] += 1
        agreement[f"{d['side']}:baseline={d['reason']}:te1={d['te1_tier']}"] += 1
        agreement[f"{d['side']}:same_action" if d["action"] == d["te1_action"]
                  else f"{d['side']}:different_action"] += 1
    futures = [Fraction(r["setup_future"]) for r in rows if r["setup_future"] is not None]
    ready = {}
    for target, side, key in ((TOP_AMERICANA_ARM_ISOLATION, Side.TOP, "threat_entry"),
                              (BOTTOM_TRAP_AND_ROLL_ESCAPE, Side.BOTTOM, "terminal")):
        uses = [e for e in attempts if e["action"] == target and e["ready_use"]]
        p_key = "p_progress" if side is Side.TOP else "p_terminal"
        ready[target] = dict(uses=len(uses),
                             predicted=float(sum((e[p_key] for e in uses), Fraction(0))),
                             actual=sum(bool(e[key]) for e in uses))
    climbs = [d for d in decisions if d["side"] == Side.TOP.value
              and d["action"] == TOP_HIGH_MOUNT_CLIMB]
    projected_own_unfundable = sum(
        1 for r in rows for p in r["projections"].values()
        if p is not None and p["own"][0] < 3)
    result = dict(
        matches=summary.matches,
        outcomes=dict(summary.outcome_counts),
        threat_matches=summary.matches_reached_submission_threat,
        top_completed_setup_builds=summary.top_completed_setup_build_count,
        exchanges=len(attempts), decisions=len(decisions),
        c0_integrity=dict(checked=len(attempts),
                          exact=sum(bool(e["integrity"]) for e in attempts)),
        C1=c1, C2=dict(status=c2_status, **c2), C3=c3, C4=c4,
        reported=dict(
            calibration_by_side=by_side,
            te1_tier_distribution=dict(shadow),
            te1_commitment_distribution=dict(commitments),
            baseline_vs_te1=dict(agreement),
            top_setup_decisions=top_setup,
            top_high_mount_climb_decisions_by_reason=dict(Counter(d["reason"] for d in climbs)),
            setup_future_distribution=dict(
                n=len(futures), zero=sum(f == 0 for f in futures),
                positive=sum(f > 0 for f in futures),
                median=float(median(futures)) if futures else None,
                maximum=float(max(futures)) if futures else None,
                deciles=[float(sorted(futures)[min(len(futures) - 1, len(futures) * k // 10)])
                         for k in range(1, 10)] if futures else []),
            builder_projections_with_own_stamina_below_low_cost=projected_own_unfundable,
            ready_conversion_predicted_vs_actual=ready,
            chains=dict(total=len(chain_rows),
                        converted=sum(bool(c["threat_entry"]) for c in chain_rows)),
        ),
    )
    records = dict(builder_decisions=rows, chains=chain_rows)
    return result, records


def _attempt_record(e) -> dict:
    out = {k: v for k, v in e.items() if k not in {"p_terminal", "p_progress",
                                                   "p_setup_advance", "predicted_grades"}}
    out.update(p_terminal=_q(e["p_terminal"]), p_progress=_q(e["p_progress"]),
               p_setup_advance=_q(e["p_setup_advance"]),
               predicted_grades={k: _q(v) for k, v in e["predicted_grades"].items()})
    return out


def _decision_record(e) -> dict:
    return {k: v for k, v in e.items() if k != "values"}


def measure_surface(name: str, kwargs: dict) -> tuple[dict, dict]:
    reference_summary, reference_signatures, reference_trace = baseline_reference(**kwargs)
    plain = run_escape_first_batch(**kwargs)
    summary, signatures, timelines, trace, counterfactuals = observe_batch(**kwargs)
    replay = observe_batch(**kwargs)
    handoff = getattr(summary, "post_clear_handoff", None)
    holds = (sum(event.get("k") == "hold" for match in handoff.matches for event in match.events)
             if handoff is not None else 0)
    result, records = score(name, summary, timelines)
    result["integrity"] = dict(
        evaluator_rng_draws=sum(trace.evaluator_draws.values()),
        evaluator_rng_draws_by_method=dict(trace.evaluator_draws),
        baseline_rng_draws=trace.baseline_draws,
        baseline_rng_draws_reference=reference_trace.baseline_draws,
        baseline_rng_digest=trace.baseline_digest,
        baseline_rng_digest_reference=reference_trace.baseline_digest,
        rng_sequence_identical=(trace.baseline_digest == reference_trace.baseline_digest
                                and trace.baseline_draws == reference_trace.baseline_draws),
        summary_identical_to_uninstrumented=summary == plain,
        summary_identical_to_reference=summary == reference_summary,
        gameplay_signatures_identical=signatures == reference_signatures,
        lockout_hold_counterfactuals_excluded=counterfactuals,
        d3b_holds=holds,
        replay_identical=(replay[:3] == (summary, signatures, timelines)
                          and replay[3].baseline_digest == trace.baseline_digest
                          and replay[3].evaluator_draws == trace.evaluator_draws),
    )
    outcomes = summary.outcome_counts
    tap = outcomes.get("TAP — Americana", 0)
    timeouts = outcomes.get("TIMEOUT — Mount retained", 0)
    observed = (summary.matches_reached_submission_threat, tap,
                summary.matches - tap - timeouts, timeouts,
                summary.top_completed_setup_build_count)
    result["baseline_reproduction"] = dict(
        fields=["threat_matches", "tap", "escapes", "timeouts", "top_completed_builds"],
        observed=list(observed), frozen=list(FROZEN_BASELINES[name]),
        exact=observed == FROZEN_BASELINES[name])
    per_match = [dict(match=m,
                      decisions=[_decision_record(e) for e in events if e["kind"] == "decision"],
                      attempts=[_attempt_record(e) for e in events if e["kind"] == "attempt"])
                 for m, events in enumerate(timelines)]
    return result, dict(records, per_match=per_match)


def measure(names=None) -> tuple[dict, dict]:
    all_surfaces = surfaces()
    out, records = {}, {}
    for name in (names or all_surfaces):
        out[name], records[name] = measure_surface(name, all_surfaces[name])
    gates = {}
    for gate in ("C1", "C2", "C3", "C4"):
        statuses = [v[gate]["status"] for v in out.values() if v[gate].get("status") != "N/A"]
        gates[gate] = ("FAIL" if "FAIL" in statuses else
                       "OPEN" if (not statuses or "OPEN" in statuses) else "PASS")
    integrity = all(
        v["integrity"]["evaluator_rng_draws"] == 0
        and v["integrity"]["rng_sequence_identical"]
        and v["integrity"]["summary_identical_to_uninstrumented"]
        and v["integrity"]["summary_identical_to_reference"]
        and v["integrity"]["gameplay_signatures_identical"]
        and v["integrity"]["lockout_hold_counterfactuals_excluded"] == v["integrity"]["d3b_holds"]
        and v["integrity"]["replay_identical"]
        and v["baseline_reproduction"]["exact"]
        and v["c0_integrity"]["checked"] == v["c0_integrity"]["exact"]
        for v in out.values())
    overall = ("OPEN" if not integrity or "OPEN" in gates.values()
               else "FAIL" if "FAIL" in gates.values() else "PASS")
    return dict(preregistration=PREREGISTRATION, surfaces=out, gates=gates,
                integrity_ok=integrity, stage_1a=overall), records


def main() -> None:
    summary, records = measure()
    SUMMARY_EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_EVIDENCE.write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    with gzip.GzipFile(RECORDS_EVIDENCE, "wb", mtime=0) as handle:
        handle.write(json.dumps(records, sort_keys=True, separators=(",", ":")).encode())
    print(SUMMARY_EVIDENCE)
    print(RECORDS_EVIDENCE)
    print("Stage 1A:", summary["stage_1a"], summary["gates"])


if __name__ == "__main__":
    main()
