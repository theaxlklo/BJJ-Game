"""Stage 1A-v2 shadow observer and scoring: C1-C5 and C3-H
(docs/TACTICAL_EVALUATOR_PROJECTION_V2_PREREGISTRATION.md, binding at 5b57017).

The baseline batch policy (ESCAPE_FIRST, fixed commitments) is unchanged. This
module mirrors the Stage 1A observer (diagnostics/tactical_evaluator.py, which
stays frozen) with the setup projection replaced by projection v2
(interfaces/tactical_projection_v2.py). The immediate evaluator is the frozen
one, so C1 and C2 are re-scored through the same code paths and must equal
the committed Stage 1A values.

Scoped wrappers, all restored on exit:
- handoff_controller_for (batch module): records each match's D3-B controller
  so its fields can be copied into branch states (never mutated);
- D3BTokenLockoutController.decide: read-only; records LOCKOUT_HOLD and the
  pre-decision branch for the O-3 surrogate check;
- EscapeFirstInitiatorPolicy.choose: TE-1 values with projection v2 at every
  real decision window; the O-3 surrogate is compared with every real Bottom
  decision; the real policy is then delegated exactly once;
- MountMatch.attempt: as Stage 1A (immediate valuation, C0 replay);
- random.Random draw methods: counted, never substituted (Stage 1A RngTrace).

Not thread-safe: run standalone, never concurrently with gameplay.
"""
from __future__ import annotations

from collections import Counter
from contextlib import ExitStack
from fractions import Fraction
import gzip
import json
from pathlib import Path
from unittest.mock import patch

from ..domain.model import Side
from ..engine.match import MountMatch
from ..interfaces import batch as batch_module
from ..interfaces import tactical_evaluator as te
from ..interfaces import tactical_projection_v2 as v2
from ..interfaces.batch import EscapeFirstInitiatorPolicy, run_escape_first_batch
from ..interfaces.handoff_policy import D3BTokenLockoutController, HandoffDecisionKind
from ..positions.mount.catalog import TOP_AMERICANA_ARM_ISOLATION
from . import tactical_evaluator as stage1a
from .d3b_promotion import canonical_kwargs
from .setup_policy import surfaces as setup_surfaces
from .stamina_adoption_verification import _match_gameplay_signature

PREREGISTRATION = "5b57017434514e75bee005834d6b04884e17194f"
STAGE1A_HEAD = "2d2778d88205874e30aeda37579dc45d5d9f885e"
SUMMARY_EVIDENCE = Path("docs/evidence/tactical_evaluator_stage1a_v2.json")
RECORDS_EVIDENCE = Path("docs/evidence/tactical_evaluator_stage1a_v2_records.json.gz")

C3_SURFACES = stage1a.C3_SURFACES
C4_SURFACES = stage1a.C4_SURFACES
C5_SURFACES = (*stage1a.C3_SURFACES, *stage1a.C4_SURFACES)
HOLDOUT_SURFACES = ("A-PROD 4242", "B-PROD 4242", "E-PROD 4242 OFF", "E-PROD 4242 ON",
                    "E-PROD 4342 OFF", "E-PROD 4342 ON")


def surfaces() -> dict[str, dict]:
    """Frozen Stage 1A surfaces plus the C3-H holdouts (D4: A-PROD and B-PROD
    at base_seed 4242; E-PROD seeds 4242 and 4342, both stalling modes; all
    other kwargs identical)."""
    base = setup_surfaces()
    out = dict(stage1a.surfaces())
    out["A-PROD 4242"] = {**base["A-PROD"], "base_seed": 4242}
    out["B-PROD 4242"] = {**base["B-PROD"], "base_seed": 4242}
    for seed in (4242, 4342):
        for mode in ("OFF", "ON"):
            out[f"E-PROD {seed} {mode}"] = canonical_kwargs(seed, mode)
    return out


# ---------------------------------------------------------------------------
# Observer
# ---------------------------------------------------------------------------


def observe_batch(*, evaluate: bool = True, **kwargs):
    """Run the unchanged baseline batch with the v2 shadow observer.

    Returns (summary, signatures, timelines, RngTrace, LOCKOUT_HOLD
    counterfactual count, O-3 surrogate checks)."""
    context = v2.Context.from_batch_kwargs(kwargs)
    model = context.model
    behavior_mode = context.bottom_behavior_mode
    recovery_mode = context.recovery_initiation_mode
    original_choose = EscapeFirstInitiatorPolicy.choose
    original_attempt = MountMatch.attempt
    original_decide = D3BTokenLockoutController.decide
    original_controller_for = batch_module.handoff_controller_for
    created: list[MountMatch] = []
    timelines: list[list[dict]] = []
    index_of: dict[int, int] = {}
    controllers: dict[int, object] = {}
    continuations: dict[int, v2.Continuation] = {}
    last_handoff: dict[int, HandoffDecisionKind] = {}
    pre_decide: dict[int, v2.Branch] = {}
    pending: dict[int, dict] = {}
    trace = stage1a.RngTrace()
    counterfactuals = [0]
    surrogate = Counter()

    def factory(*args, **factory_kwargs):
        match = MountMatch(*args, **factory_kwargs)
        index_of[id(match)] = len(created)
        created.append(match)
        timelines.append([])
        return match

    def controller_for(mode, match):
        controller = original_controller_for(mode, match)
        controllers[id(match)] = controller
        return controller

    def continuation(match) -> v2.Continuation:
        key = id(match)
        if key not in continuations:
            continuations.clear()  # one live match at a time: exact caches per match
            continuations[key] = v2.Continuation(match, context)
        return continuations[key]

    def observed_decide(controller, match, *, armed):
        if id(match) not in index_of:
            # A projection-v2 sandbox (copied controller): pass straight through.
            return original_decide(controller, match, armed=armed)
        if evaluate:
            pre_decide[id(match)] = v2.branch_of(match, controller)
        decision = original_decide(controller, match, armed=armed)
        last_handoff[id(match)] = decision.kind
        return decision

    def observed_choose(policy, match):
        if id(match) not in index_of:
            # O-3 opponent window inside a continuation: the real policy only,
            # never a nested TE-1 evaluation (depth exactly 1).
            return original_choose(policy, match)
        kind = last_handoff.pop(id(match), None)
        if match.initiator is Side.BOTTOM and kind is HandoffDecisionKind.LOCKOUT_HOLD:
            counterfactuals[0] += 1
            pre_decide.pop(id(match), None)
            return original_choose(policy, match)
        record = dict(kind="decision", t=match.elapsed_simulated_time,
                      side=match.initiator.value, d3b=kind.value if kind else None)
        controller = controllers.get(id(match))
        surrogate_decision = None
        if evaluate:
            branch = v2.branch_of(match, controller)
            allowed = te.allowed_commitments(
                match, bottom_behavior_mode=behavior_mode,
                recovery_initiation_mode=recovery_mode)
            trace.active = True
            try:
                cont = continuation(match)
                values = v2.candidates(cont, branch, allowed)
                choice = te.choose_te1(match, values)
                if match.initiator is Side.BOTTOM:
                    before = pre_decide.pop(id(match), branch)
                    surrogate_decision = cont.opponent_decision(before)
            finally:
                trace.active = False
            record.update(
                branch=branch, allowed=[c.value for c in allowed],
                te1_tier=choice.tier,
                te1_action=choice.value.action_id if choice.value else None,
                te1_requested=choice.value.requested.value if choice.value else None,
                values=values,
            )
        decision = original_choose(policy, match)
        record.update(action=decision.action_id, reason=decision.reason)
        if evaluate and match.initiator is Side.TOP and decision.reason == "setup":
            # C5: the baseline's builder at the baseline's commitment (Top's
            # batch commitment; recovery precedence applies to Bottom only).
            trace.active = True
            try:
                record["c5_projection"] = continuation(match).project(
                    record["branch"], decision.action_id, context.commitment)
            finally:
                trace.active = False
        if surrogate_decision is not None:
            s_kind, s_action, s_requested, _ = surrogate_decision
            same = s_action == decision.action_id and s_kind is kind
            surrogate["bottom_checked"] += 1
            surrogate["bottom_exact"] += same
            record["surrogate_exact"] = same
        timelines[index_of[id(match)]].append(record)
        pending[id(match)] = record
        return decision

    def observed_attempt(match, *args, **kw):
        if id(match) not in index_of:
            # A projection-v2 sandbox exchange: pass straight through.
            return original_attempt(match, *args, **kw)
        decision = pending.pop(id(match), None)
        action_id, requested = kw["action_id"], kw["commitment"]
        if decision is None or decision["action"] != action_id:
            raise RuntimeError("attempt without its real policy decision")
        state = te.State.of(match)
        record = dict(kind="attempt", t=match.elapsed_simulated_time,
                      side=state.initiator.value, action=action_id,
                      requested=requested.value, ready_use=action_id in state.ready,
                      state=state)
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
                          p_setup_advance=value.setup_advance, predicted_grades=dict(grades))
        history = match.history
        marks = (len(history.submission_change_history), len(history.setup_change_history))
        result = original_attempt(match, *args, **kw)
        submission = history.submission_change_history[marks[0]:]
        setup = history.setup_change_history[marks[1]:]
        threat_entry = any(e.startswith("entry:") for e in submission)
        stage_advance = any(":" not in e and not e.endswith("->Tap") for e in submission)
        record.update(
            effective=stage1a._c(result.attempt.effective_commitment),
            response=kw["response_id"],
            realized_grade=result.resolution.final_grade.display,
            terminal=(result.resolution.exit_destination is not None
                      if state.initiator is Side.BOTTOM else match.submission_tapped),
            progress=state.initiator is Side.TOP and (threat_entry or stage_advance),
            threat_entry=threat_entry, setup_advanced=bool(setup),
            exit=(result.resolution.exit_destination.value
                  if result.resolution.exit_destination is not None else None),
        )
        if evaluate:
            replay = te.resolve(match, state, action_id, kw["response_id"],
                                result.attempt.effective_commitment,
                                result.response_effective_commitment)
            record["integrity"] = (
                replay.final_grade == result.resolution.final_grade
                and replay.axis_after == result.resolution.axis_after
                and replay.exit_destination == result.resolution.exit_destination)
        decision["attempt"] = len(timelines[index_of[id(match)]])
        timelines[index_of[id(match)]].append(record)
        return result

    with ExitStack() as stack:
        stack.enter_context(stage1a.count_rng(trace))
        stack.enter_context(patch.object(batch_module, "MountMatch", factory))
        stack.enter_context(patch.object(batch_module, "handoff_controller_for", controller_for))
        stack.enter_context(patch.object(EscapeFirstInitiatorPolicy, "choose", observed_choose))
        stack.enter_context(patch.object(MountMatch, "attempt", observed_attempt))
        stack.enter_context(patch.object(D3BTokenLockoutController, "decide", observed_decide))
        summary = run_escape_first_batch(**kwargs)
    if (EscapeFirstInitiatorPolicy.choose is not original_choose
            or MountMatch.attempt is not original_attempt
            or D3BTokenLockoutController.decide is not original_decide
            or batch_module.handoff_controller_for is not original_controller_for
            or batch_module.MountMatch is not MountMatch):
        raise RuntimeError("observer wrappers not restored")
    signatures = tuple(_match_gameplay_signature(m) for m in created)
    return summary, signatures, timelines, trace, counterfactuals[0], dict(surrogate)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _q(value) -> str:
    return str(value)


def _projection(p: v2.ContinuationProjection | None) -> dict | None:
    if p is None:
        return None
    return dict(
        r=p.builds_remaining, setup_future=_q(p.setup_future),
        setup_future_requested={c.value: _q(v) for c, v in p.setup_future_requested},
        ready_mass=_q(p.ready_mass),
        terminal_mass={k: _q(v) for k, v in p.terminal_mass},
        use_branches=p.use_branches, max_branches=p.max_branches,
        p_opponent_exhausted=float(p.p_opponent_exhausted),
        p_strong_or_locked=float(p.p_strong_or_locked),
        expected_axis=float(p.expected_axis),
        expected_own=float(p.expected_own), expected_opponent=float(p.expected_opponent),
    )


def chains(events: list[dict]) -> list[dict]:
    """Stage 1A C3 chains: Top setup decisions closed by the next Top Ready
    use of Americana Arm Isolation, or open at the end of the match."""
    out, open_chain = [], []
    for e in events:
        if e["kind"] == "decision" and e["side"] == "top" and e["reason"] == "setup":
            open_chain.append(e)
        if (e["kind"] == "attempt" and e["side"] == "top"
                and e["action"] == TOP_AMERICANA_ARM_ISOLATION and e["ready_use"]):
            if open_chain:
                out.append(dict(decisions=open_chain, use=e, converted=e["threat_entry"]))
            open_chain = []
    if open_chain:
        out.append(dict(decisions=open_chain, use=None, converted=False))
    return out


def _builder_future(decision) -> Fraction | None:
    vals = [v for v in decision["values"]
            if v.action_id == decision["action"] and v.projection is not None]
    return max(v.setup_future for v in vals) if vals else None


def _attempt_of(events, decision):
    return events[decision["attempt"]] if "attempt" in decision else None


def score(name: str, summary, timelines, context: v2.Context) -> tuple[dict, dict]:
    attempts = [e for events in timelines for e in events if e["kind"] == "attempt"]
    top_attempts = [e for e in attempts if e["side"] == Side.TOP.value]

    # C1 / C2: immediate layer, same code paths as Stage 1A.
    deterministic = [e for e in top_attempts if max(e["predicted_grades"].values()) == 1]
    exact = [e for e in deterministic if e["predicted_grades"].get(e["realized_grade"], 0) == 1]
    c1 = dict(applies=name in stage1a.C1_SURFACES, top_exchanges=len(top_attempts),
              deterministic_predictions=len(deterministic), exact=len(exact),
              mismatches=len(top_attempts) - len(exact))
    c1["status"] = (("PASS" if c1["mismatches"] == 0 and top_attempts else "FAIL")
                    if c1["applies"] else "N/A")
    components = (("terminal", "terminal"), ("progress", "progress"),
                  ("setup_advance", "setup_advanced"))
    c2 = {k: stage1a.calibration([(e[f"p_{k}"], e[key]) for e in attempts])
          for k, key in components}
    applies_c2 = name in stage1a.surfaces()
    c2_status = (("PASS" if all(v["within_3_sigma"] for v in c2.values()) else "FAIL")
                 if applies_c2 else "N/A")

    # C3 / C4 (and C3-H on holdouts): Top setup decisions, v2 setup_future.
    rows = []
    converted = positive = top_setup = zero = 0
    c5_pairs, c5_rows = [], []
    fidelity = Counter()
    fidelity_axis_error = []
    for m, events in enumerate(timelines):
        for chain in chains(events):
            for i, d in enumerate(chain["decisions"]):
                future = _builder_future(d)
                top_setup += 1
                zero += future == 0
                if chain["converted"]:
                    converted += 1
                    positive += future > 0
                rows.append(dict(match=m, t=d["t"], setup_future=_q(future),
                                 chain_converted=chain["converted"] if chain["use"] else None,
                                 te1_tier=d["te1_tier"], te1_action=d["te1_action"],
                                 te1_requested=d["te1_requested"],
                                 projections={v.requested.value: _projection(v.projection)
                                              for v in d["values"]
                                              if v.action_id == d["action"]}))
            # C5: the first builder decision of every chain begun.
            first = chain["decisions"][0]
            builder_attempt = _attempt_of(events, first)
            requested = next(c for c in te.COMMITMENTS
                             if c.value == builder_attempt["requested"])
            if chain["use"] is not None and chain["use"]["requested"] != context.commitment.value:
                raise RuntimeError("C5: actual use commitment differs from the baseline's")
            if requested is not context.commitment:
                raise RuntimeError("C5: baseline builder commitment differs from the batch's")
            projection = first["c5_projection"]
            p = dict(projection.setup_future_requested)[context.commitment]
            c5_pairs.append((p, bool(chain["converted"])))
            c5_rows.append(dict(match=m, t=first["t"], requested=requested.value,
                                p=_q(p), observed=bool(chain["converted"]),
                                used=chain["use"] is not None))
            if chain["converted"]:
                use = chain["use"]["state"]
                fidelity["converted_chain_starts"] += 1
                fidelity["realized_bottom_exhausted"] += use.bottom.latched
                fidelity["realized_strong_or_locked"] += use.band.value in ("Strong", "Locked")
                fidelity["p_bottom_exhausted_sum"] += projection.p_opponent_exhausted
                fidelity["p_strong_or_locked_sum"] += projection.p_strong_or_locked
                fidelity_axis_error.append(float(projection.expected_axis) - use.axis)
    c3_applies = name in C3_SURFACES or name in HOLDOUT_SURFACES
    c3 = dict(applies=c3_applies, population=converted, setup_future_positive=positive,
              share=(positive / converted if converted else None))
    c3["status"] = ((("PASS" if 5 * positive >= 4 * converted else "FAIL")
                     if converted else "OPEN") if c3_applies else "N/A")
    c4 = dict(applies=name in C4_SURFACES, population=top_setup, setup_future_zero=zero,
              share=(zero / top_setup if top_setup else None))
    c4["status"] = ((("PASS" if 2 * zero >= top_setup else "FAIL") if top_setup else "OPEN")
                    if c4["applies"] else "N/A")
    c5 = dict(applies=name in C5_SURFACES, **stage1a.calibration(c5_pairs))
    c5["status"] = (("PASS" if c5["within_3_sigma"] else "FAIL") if c5_pairs else "OPEN") \
        if c5["applies"] else "N/A"

    decisions = [e for events in timelines for e in events if e["kind"] == "decision"]
    shadow, commitments = Counter(), Counter()
    branches = []
    for d in decisions:
        shadow[f"{d['side']}:{d['te1_tier']}"] += 1
        if d["te1_action"] is not None:
            commitments[f"{d['side']}:{d['te1_tier']}:{d['te1_requested']}"] += 1
        branches += [v.projection.max_branches for v in d["values"] if v.projection is not None]
    n = fidelity["converted_chain_starts"]
    result = dict(
        matches=summary.matches, outcomes=dict(summary.outcome_counts),
        threat_matches=summary.matches_reached_submission_threat,
        top_completed_setup_builds=summary.top_completed_setup_build_count,
        exchanges=len(attempts), decisions=len(decisions),
        c0_integrity=dict(checked=len(attempts),
                          exact=sum(bool(e["integrity"]) for e in attempts)),
        C1=c1, C2=dict(status=c2_status, **c2), C3=c3, C4=c4, C5=c5,
        reported=dict(
            te1_tier_distribution=dict(shadow),
            te1_commitment_distribution=dict(commitments),
            top_setup_decisions=top_setup,
            chains=dict(total=len(c5_rows), used=sum(r["used"] for r in c5_rows),
                        converted=sum(r["observed"] for r in c5_rows)),
            use_state_fidelity_converted_chain_starts=dict(
                n=n,
                realized_bottom_exhausted=fidelity["realized_bottom_exhausted"],
                predicted_bottom_exhausted=float(fidelity["p_bottom_exhausted_sum"]),
                realized_strong_or_locked=fidelity["realized_strong_or_locked"],
                predicted_strong_or_locked=float(fidelity["p_strong_or_locked_sum"]),
                mean_axis_error=(round(sum(fidelity_axis_error) / n, 6) if n else None)),
            projection_max_branches=dict(
                n=len(branches), max=max(branches, default=0),
                mean=round(sum(branches) / len(branches), 3) if branches else None),
        ),
    )
    return result, dict(builder_decisions=rows, c5=c5_rows)


def _record(e) -> dict:
    skip = {"values", "branch", "state", "c5_projection"}
    out = {k: v for k, v in e.items() if k not in skip}
    for k in ("p_terminal", "p_progress", "p_setup_advance"):
        if k in out:
            out[k] = _q(out[k])
    if "predicted_grades" in out:
        out["predicted_grades"] = {k: _q(v) for k, v in out["predicted_grades"].items()}
    return out


def _comparable(timelines) -> list:
    out = []
    for events in timelines:
        rows = []
        for e in events:
            row = _record(e)
            if e["kind"] == "decision" and "values" in e:
                row["values"] = [(v.action_id, v.requested.value, _q(v.setup_future),
                                  _q(v.terminal), _q(v.progress)) for v in e["values"]]
                row["c5"] = _projection(e.get("c5_projection"))
            rows.append(row)
        out.append(rows)
    return out


def measure_surface(name: str, kwargs: dict, stage1a_summary: dict | None, *,
                    replay: bool = True) -> tuple[dict, dict]:
    """replay=False skips the second observed run (evidence pin in CI only;
    the authoritative measurement always replays)."""
    context = v2.Context.from_batch_kwargs(kwargs)
    _, reference_signatures, _, reference_trace, *_ = observe_batch(evaluate=False, **kwargs)
    plain = run_escape_first_batch(**kwargs)
    summary, signatures, timelines, trace, counterfactuals, surrogate = observe_batch(**kwargs)
    second = observe_batch(**kwargs) if replay else None
    handoff = getattr(summary, "post_clear_handoff", None)
    holds = (sum(event.get("k") == "hold" for match in handoff.matches for event in match.events)
             if handoff is not None else 0)
    result, records = score(name, summary, timelines, context)
    result["integrity"] = dict(
        evaluator_rng_draws=sum(trace.evaluator_draws.values()),
        rng_sequence_identical=(trace.baseline_digest == reference_trace.baseline_digest
                                and trace.baseline_draws == reference_trace.baseline_draws),
        summary_identical_to_uninstrumented=summary == plain,
        gameplay_signatures_identical=signatures == reference_signatures,
        lockout_hold_counterfactuals_excluded=counterfactuals, d3b_holds=holds,
        replay_identical=(None if second is None else (
            second[0] == summary and second[1] == signatures
            and _comparable(second[2]) == _comparable(timelines)
            and second[3].baseline_digest == trace.baseline_digest
            and sum(second[3].evaluator_draws.values()) == 0)),
        o3_surrogate_bottom=dict(checked=surrogate.get("bottom_checked", 0),
                                 exact=surrogate.get("bottom_exact", 0)),
    )
    outcomes = summary.outcome_counts
    tap = outcomes.get("TAP — Americana", 0)
    timeouts = outcomes.get("TIMEOUT — Mount retained", 0)
    observed = [summary.matches_reached_submission_threat, tap,
                summary.matches - tap - timeouts, timeouts,
                summary.top_completed_setup_build_count]
    frozen = stage1a.FROZEN_BASELINES.get(name)
    result["baseline"] = dict(
        fields=["threat_matches", "tap", "escapes", "timeouts", "top_completed_builds"],
        observed=observed, frozen=list(frozen) if frozen else None,
        exact=(observed == list(frozen)) if frozen else None)
    if stage1a_summary is not None:
        # The immediate evaluator is unchanged: C1 and C2 equal Stage 1A exactly.
        result["integrity"]["c1_c2_equal_stage1a"] = (
            json.loads(json.dumps(result["C1"])) == stage1a_summary["C1"]
            and json.loads(json.dumps(result["C2"])) == stage1a_summary["C2"])
    records["per_match"] = [[_record(e) for e in events] for events in timelines]
    return result, records


def _integrity_ok(v: dict) -> bool:
    i = v["integrity"]
    return (i["evaluator_rng_draws"] == 0 and i["rng_sequence_identical"]
            and i["summary_identical_to_uninstrumented"]
            and i["gameplay_signatures_identical"]
            and i["lockout_hold_counterfactuals_excluded"] == i["d3b_holds"]
            and i["replay_identical"]
            and i["o3_surrogate_bottom"]["checked"] == i["o3_surrogate_bottom"]["exact"]
            and i.get("c1_c2_equal_stage1a", True)
            and v["baseline"]["exact"] in (True, None)
            and v["c0_integrity"]["checked"] == v["c0_integrity"]["exact"])


def _measure_one(name: str) -> tuple[str, dict, dict]:
    stage1a_summary = json.loads(stage1a.SUMMARY_EVIDENCE.read_text())["surfaces"]
    result, records = measure_surface(name, surfaces()[name], stage1a_summary.get(name))
    return name, result, records


def _run_parts(names: list[str], jobs: int, workdir: Path) -> list[tuple[str, dict, dict]]:
    """Each surface in its own fresh interpreter (no forked state); parts are
    merged in surface order. Results are identical to a sequential run."""
    import subprocess
    import sys
    import time
    workdir.mkdir(parents=True, exist_ok=True)
    queue, running, done = list(names), [], {}
    while queue or running:
        while queue and len(running) < jobs:
            name = queue.pop(0)
            part = workdir / f"{len(done) + len(running)}_{name.replace(' ', '_')}.json"
            proc = subprocess.Popen([sys.executable, "-m",
                                     "bjj_game.diagnostics.tactical_evaluator_v2",
                                     "--surface", name, "--part", str(part)])
            running.append((name, part, proc))
        for item in list(running):
            name, part, proc = item
            if proc.poll() is not None:
                running.remove(item)
                if proc.returncode != 0:
                    raise RuntimeError(f"surface {name!r} failed ({proc.returncode})")
                payload = json.loads(part.read_text())
                done[name] = (name, payload["result"], payload["records"])
        if running:
            time.sleep(1)
    return [done[name] for name in names]


def measure(names=None, *, jobs: int = 1, workdir: Path | None = None) -> tuple[dict, dict]:
    names = list(names or surfaces())
    if jobs > 1:
        done = _run_parts(names, jobs, workdir or Path("docs/evidence/.stage1a_v2_parts"))
    else:
        done = [_measure_one(name) for name in names]
    out = {name: result for name, result, _ in done}
    records = {name: rec for name, _, rec in done}
    gates = {}
    for gate in ("C1", "C2", "C3", "C4", "C5"):
        statuses = [v[gate]["status"] for n, v in out.items()
                    if n not in HOLDOUT_SURFACES and v[gate]["status"] != "N/A"]
        gates[gate] = ("FAIL" if "FAIL" in statuses else
                       "OPEN" if (not statuses or "OPEN" in statuses) else "PASS")
    holdout = [v["C3"]["status"] for n, v in out.items() if n in HOLDOUT_SURFACES]
    gates["C3-H"] = ("FAIL" if "FAIL" in holdout else
                     "OPEN" if (not holdout or "OPEN" in holdout) else "PASS")
    integrity = all(_integrity_ok(v) for v in out.values())
    overall = ("OPEN" if not integrity or "OPEN" in gates.values()
               else "FAIL" if "FAIL" in gates.values() else "PASS")
    return dict(preregistration=PREREGISTRATION, stage1a_head=STAGE1A_HEAD,
                surfaces=out, gates=gates, integrity_ok=integrity, stage_1a_v2=overall), records


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--surface")
    parser.add_argument("--part")
    parser.add_argument("--workdir")
    args = parser.parse_args()
    if args.surface:
        name, result, records = _measure_one(args.surface)
        Path(args.part).write_text(json.dumps(dict(result=result, records=records),
                                              sort_keys=True, default=str))
        return
    summary, records = measure(jobs=args.jobs,
                               workdir=Path(args.workdir) if args.workdir else None)
    SUMMARY_EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_EVIDENCE.write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    with gzip.GzipFile(RECORDS_EVIDENCE, "wb", mtime=0) as handle:
        handle.write(json.dumps(records, sort_keys=True, separators=(",", ":"),
                                default=str).encode())
    print(SUMMARY_EVIDENCE)
    print(RECORDS_EVIDENCE)
    print("Stage 1A-v2:", summary["stage_1a_v2"], summary["gates"])


if __name__ == "__main__":
    main()
