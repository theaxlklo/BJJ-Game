"""Stage 1B candidate measurement and scoring: P1-P6 and G1-G6
(docs/TACTICAL_EVALUATOR_STAGE1B_PREREGISTRATION.md, binding at ae786af).

The acting policy is the qualified implementation (fd19dd0):
run_batch(initiator_policy=TACTICAL_V1) with tactical_policy.TacticalV1Policy.
This module never changes a decision. It observes through scoped wrappers,
all restored on exit:

- tactical_policy.create_policy: returns _ObservedPolicy, a TacticalV1Policy
  subclass whose choose() delegates to the unchanged TacticalV1Policy.choose
  exactly once. Around it, it marks the RNG trace as evaluator time (P4a),
  captures the candidate values and the TE-1 choice that call computed (by
  recording the last v2.candidates / te.choose_te1 results; nothing is
  recomputed), checks the stamina guard (P5) and computes the O-3 surrogate
  decision at every executed window (6.3, reported only);
- batch_module.MountMatch: records the batch's real matches; projection-v2
  sandboxes are recognized by identity and pass straight through every
  wrapper;
- MountMatch.advance / attempt / reset_window / recovery_hold /
  consume_free_initiative_window: per-event records on real matches (P3
  precedence, realized outcomes, time per (initiative, band) cell);
- D3BTokenLockoutController.decide: read-only; the D3-B kind of each real
  window and its pre-decision branch for the O-3 surrogate;
- random.Random draw methods: counted, never substituted (Stage 1A RngTrace).

On E-PROD the unchanged late-recovery observer (diagnostics/late_recovery.py)
is wrapped around the run, with sandboxes routed past it, for G5's Bottom
Exhausted share.

Runs per gated surface: the ESCAPE_FIRST baseline (5.4), the candidate run,
a second identical candidate run (P4b), and the inertness replay from the
recorded tape (P4c). Holdouts: the candidate run only (6.4, reported).

Not thread-safe: run standalone, never concurrently with gameplay.
"""
from __future__ import annotations

from collections import Counter
from contextlib import ExitStack
from fractions import Fraction
import gzip
import json
from pathlib import Path
import subprocess
from unittest.mock import patch

from ..domain.action import Commitment
from ..domain.model import Side
from ..engine.match import MountMatch
from ..interfaces import batch as batch_module
from ..interfaces import tactical_evaluator as te
from ..interfaces import tactical_policy as tp
from ..interfaces import tactical_projection_v2 as v2
from ..interfaces.batch import BatchBehaviorMode, BatchInitiatorPolicy, run_batch
from ..interfaces.handoff_policy import D3BTokenLockoutController, HandoffDecisionKind
from ..interfaces.recovery_policy import RecoveryInitiationMode
from ..domain.stamina import StaminaBand
from ..positions.mount.catalog import TOP_AMERICANA_ARM_ISOLATION
from . import late_recovery
from . import tactical_evaluator as stage1a
from . import tactical_evaluator_v2 as stage1a_v2
from .stamina_adoption_verification import _match_gameplay_signature

PREREGISTRATION = "ae786af483d109785f172cb10a17170ece2ed241"
IMPLEMENTATION = "fd19dd0f6220753d4e135e98db2abd1f03963a3b"
SUMMARY_EVIDENCE = Path("docs/evidence/tactical_evaluator_stage1b.json")
RECORDS_EVIDENCE = Path("docs/evidence/tactical_evaluator_stage1b_records.json.gz")

TACTICAL = BatchInitiatorPolicy.TACTICAL_V1
ESCAPE_FIRST = BatchInitiatorPolicy.ESCAPE_FIRST

GATED_SURFACES = tuple(stage1a.surfaces())
HOLDOUT_SURFACES = stage1a_v2.HOLDOUT_SURFACES
E_PROD = ("E-PROD 42 OFF", "E-PROD 42 ON", "E-PROD 142 OFF", "E-PROD 142 ON")
FROZEN_BASELINES = stage1a.FROZEN_BASELINES
BASELINE_FIELDS = ("threat_matches", "tap", "escapes", "timeouts", "top_completed_builds")

# Section 3 holdout baselines (ESCAPE_FIRST; committed in the Stage 1A-v2
# evidence; E-PROD OFF and ON are identical). Cross-checked against the
# committed evidence file before use.
HOLDOUT_BASELINES = {
    "A-PROD 4242": (77, 0, 23, 77, 308),
    "B-PROD 4242": (49, 8, 21, 71, 824),
    "E-PROD 4242 OFF": (49, 2, 42, 56, 790),
    "E-PROD 4242 ON": (49, 2, 42, 56, 790),
    "E-PROD 4342 OFF": (57, 1, 42, 57, 725),
    "E-PROD 4342 ON": (57, 1, 42, 57, 725),
}

# P2: files whose content must be identical to the binding preregistration.
PROTECTED_PATHS = (
    "src/bjj_game/engine",
    "src/bjj_game/domain",
    "src/bjj_game/positions",
    "src/bjj_game/interfaces/handoff_policy.py",
    "src/bjj_game/interfaces/production_policy.py",
    "src/bjj_game/interfaces/recovery_policy.py",
    "src/bjj_game/interfaces/stamina_economy.py",
    "src/bjj_game/interfaces/tactical_evaluator.py",
)

_TAP = "TAP — Americana"
_TIMEOUT = "TIMEOUT — Mount retained"
_ROUTED = ("advance", "attempt", "reset_window", "recovery_hold",
           "consume_free_initiative_window")
_TRUE = {name: getattr(MountMatch, name) for name in _ROUTED}


def surfaces() -> dict[str, dict]:
    """Gated surfaces (Stage 1A, frozen) and the six C3-H holdouts."""
    every = stage1a_v2.surfaces()
    return {name: every[name] for name in (*GATED_SURFACES, *HOLDOUT_SURFACES)}


def _q(value) -> str:
    return str(value)


def _band(pool) -> str:
    return pool.band.value


# ---------------------------------------------------------------------------
# Observed TACTICAL_V1 policy
# ---------------------------------------------------------------------------


class _Capture:
    """Last results of v2.candidates and te.choose_te1 (call-through only)."""

    def __init__(self) -> None:
        self.values = None
        self.choice = None

    def candidates(self, original):
        def recorded(*args, **kwargs):
            result = original(*args, **kwargs)
            self.values = result
            return result
        return recorded

    def choose_te1(self, original):
        def recorded(*args, **kwargs):
            result = original(*args, **kwargs)
            self.choice = result
            return result
        return recorded


def guard_violation(values, choice) -> str | None:
    """P5, independent of te.choose_te1's code path: None if the chosen value
    respects the stamina guard (tiers A/B) or the cheapest-qualifying rule
    (tiers C/D), else the violated rule."""
    if choice.value is None:
        return None
    chosen = choice.value
    same = [v for v in values if v.action_id == chosen.action_id]
    if choice.tier in ("terminal", "progress"):
        metric = (lambda v: v.terminal) if choice.tier == "terminal" else (lambda v: v.progress)
        if chosen.enters_exhausted:
            others = [o for o in same if not o.enters_exhausted and metric(o) > 0]
            if not all(metric(chosen) > metric(o) for o in others):
                return "AB_enters_exhausted_not_strictly_better"
        return None
    if choice.tier == "setup":
        qualifies = lambda v: v.setup_future > 0  # noqa: E731
    elif choice.tier == "position":
        qualifies = lambda v: v.axis_raw > 0 and v.axis_realized > 0  # noqa: E731
    else:
        return "unknown_tier"
    rank = {Commitment.LOW: 1, Commitment.MEDIUM: 2, Commitment.HIGH: 3}
    cheapest = min((v for v in same if qualifies(v)),
                   key=lambda v: (v.stamina_cost, rank[v.requested]), default=None)
    if cheapest is None or (cheapest.stamina_cost, cheapest.requested) != (
            chosen.stamina_cost, chosen.requested):
        return "CD_above_cheapest_qualifying"
    return None


def _value_row(v) -> dict:
    return dict(action=v.action_id, requested=v.requested.value,
                effective=v.effective.value if v.effective else None,
                terminal=_q(v.terminal), progress=_q(v.progress),
                setup_future=_q(v.setup_future), setup_advance=_q(v.setup_advance),
                axis_realized=_q(v.axis_realized), axis_raw=_q(v.axis_raw),
                cost=v.stamina_cost, enters_exhausted=v.enters_exhausted,
                r=(v.projection.builds_remaining
                   if getattr(v.projection, "builds_remaining", None) is not None else None))


class Observation:
    """Per-run state shared by the wrappers."""

    def __init__(self, *, evaluate: bool) -> None:
        self.evaluate = evaluate
        self.trace = stage1a.RngTrace()
        self.capture = _Capture()
        self.created: list[MountMatch] = []
        self.index_of: dict[int, int] = {}
        self.timelines: list[list[dict]] = []
        self.last_kind: dict[int, HandoffDecisionKind] = {}
        self.pre_decide: dict[int, v2.Branch] = {}
        self.pending: dict[int, dict] = {}
        self.p3 = Counter()
        self.p5 = Counter()
        self.o3 = Counter()
        self.cells = Counter()
        self.first_ready: list[int | None] = []
        self.policy: _ObservedPolicy | None = None
        self.batch_run = None

    def real(self, match) -> bool:
        return id(match) in self.index_of


def _observed_policy_class(obs: Observation):
    class _ObservedPolicy(tp.TacticalV1Policy):
        def choose(self, match, *, handoff_decision, executed):
            capture = obs.capture
            capture.values = capture.choice = None
            obs.trace.active = True
            try:
                selection = super().choose(match, handoff_decision=handoff_decision,
                                           executed=executed)
            finally:
                obs.trace.active = False
            values, choice = capture.values, capture.choice
            entry = self._tape[-1]
            if values is None or choice is None or choice.tier != entry.tier or (
                    (choice.value.action_id if choice.value else None)
                    != entry.decision.action_id):
                raise RuntimeError("observer capture does not match the taped call")
            side = match.initiator
            kind = handoff_decision.kind if handoff_decision is not None else None
            record = dict(
                kind="decision", executed=executed, t=match.elapsed_simulated_time,
                side=side.value, call=entry.call_index, tier=entry.tier,
                action=entry.decision.action_id, reason=entry.decision.reason,
                requested=entry.requested.value if entry.requested else None,
                allowed=[c.value for c in entry.allowed],
                forced_by=entry.forced_by.value if entry.forced_by else None,
                d3b=kind.value if kind else None,
                initiative=side.value,
                top_band=_band(match.top.stamina), bottom_band=_band(match.bottom.stamina),
                top_ready=match.setup_state.is_ready(TOP_AMERICANA_ARM_ISOLATION),
            )
            violation = guard_violation(values, choice)
            obs.p5["checked"] += 1
            if violation is not None:
                obs.p5[violation] += 1
            record["p5_violation"] = violation
            if choice.value is not None:
                record["chosen"] = _value_row(choice.value)
            if choice.tier == "setup":
                position = [v for v in values if v.axis_raw > 0 and v.axis_realized > 0]
                best = max((v.axis_realized for v in position), default=None)
                record["forgone_better_position"] = (
                    best is not None and best > choice.value.axis_realized)
            if executed:
                before = obs.pre_decide.pop(id(match), entry.branch)
                obs.trace.active = True
                try:
                    s_kind, s_action, s_requested, _ = self._continuation.opponent_decision(
                        before)
                finally:
                    obs.trace.active = False
                same_action = s_action == entry.decision.action_id and s_kind is kind
                same_full = same_action and s_requested == (
                    entry.requested if entry.decision.action_id is not None else None)
                key = f"{side.value}:{entry.tier}"
                obs.o3[f"{key}:checked"] += 1
                obs.o3[f"{key}:action_exact"] += same_action
                obs.o3[f"{key}:action_commitment_exact"] += same_full
                record["o3_action_exact"] = same_action
                record["o3_full_exact"] = same_full
                obs.pending[id(match)] = record
            else:
                obs.pre_decide.pop(id(match), None)
            obs.timelines[obs.index_of[id(match)]].append(record)
            return selection

    return _ObservedPolicy


# ---------------------------------------------------------------------------
# Real-match event wrappers
# ---------------------------------------------------------------------------


def _routers(obs: Observation, context: v2.Context, inner: dict):
    """MountMatch method wrappers: sandboxes pass straight to the true
    originals; real matches go through `inner` (the late-recovery observer's
    wrappers when present, else the originals) after recording."""

    def advance(match, *args, **kw):
        if not obs.real(match):
            return _TRUE["advance"](match, *args, **kw)
        key = (match.initiator.value, _band(match.top.stamina), _band(match.bottom.stamina))
        t0 = match.elapsed_simulated_time
        result = inner["advance"](match, *args, **kw)
        obs.cells["|".join(key)] += match.elapsed_simulated_time - t0
        return result

    def reset_window(match, *args, **kw):
        if not obs.real(match):
            return _TRUE["reset_window"](match, *args, **kw)
        obs.last_kind.pop(id(match), None)
        decision = obs.pending.pop(id(match), None)
        obs.timelines[obs.index_of[id(match)]].append(dict(
            kind="reset", t=match.elapsed_simulated_time, side=match.initiator.value,
            decided=decision is not None))
        return inner["reset_window"](match, *args, **kw)

    def recovery_hold(match, *args, **kw):
        if not obs.real(match):
            return _TRUE["recovery_hold"](match, *args, **kw)
        kind = obs.last_kind.pop(id(match), None)
        if kind is not HandoffDecisionKind.LOCKOUT_HOLD:
            obs.p3["hold_without_lockout_decision"] += 1
        obs.p3["holds"] += 1
        obs.timelines[obs.index_of[id(match)]].append(dict(
            kind="hold", t=match.elapsed_simulated_time, side=match.initiator.value))
        return inner["recovery_hold"](match, *args, **kw)

    def consume_free_initiative_window(match, *args, **kw):
        result = _TRUE["consume_free_initiative_window"](match, *args, **kw)
        if obs.real(match) and result is not None:
            obs.timelines[obs.index_of[id(match)]].append(dict(
                kind="free_window", t=match.elapsed_simulated_time, side=result.value))
        return result

    def attempt(match, *args, **kw):
        if not obs.real(match):
            return _TRUE["attempt"](match, *args, **kw)
        side = match.initiator
        kind = obs.last_kind.pop(id(match), None)
        requested = kw["commitment"]
        action_id = kw["action_id"]
        if kind is HandoffDecisionKind.LOCKOUT_HOLD:
            obs.p3["attempt_in_lockout_hold_window"] += 1
        exhausted_recover = (
            side is Side.BOTTOM
            and context.bottom_behavior_mode is BatchBehaviorMode.RECOVER
            and match.bottom.stamina.band is StaminaBand.EXHAUSTED
            and context.recovery_initiation_mode is RecoveryInitiationMode.LOW_WHILE_EXHAUSTED)
        if exhausted_recover:
            obs.p3["bottom_recover_exhausted_initiations"] += 1
            obs.p3["bottom_recover_exhausted_not_low"] += requested is not Commitment.LOW
        decision = obs.pending.pop(id(match), None)
        if obs.evaluate and (decision is None or decision["action"] != action_id
                             or decision["requested"] != requested.value):
            raise RuntimeError("attempt without its TACTICAL_V1 decision")
        target = match.setup_policy.target_for_builder(action_id)
        record = dict(
            kind="attempt", t=match.elapsed_simulated_time, side=side.value,
            action=action_id, requested=requested.value,
            ready_use=match.setup_state.is_ready(action_id),
            builder_target=target,
            builder_not_ready=(target is not None and not match.setup_state.is_ready(target)),
            bottom_exhausted=match.bottom.stamina.band is StaminaBand.EXHAUSTED,
            d3b=kind.value if kind else None,
        )
        history = match.history
        marks = (len(history.submission_change_history), len(history.setup_change_history))
        result = inner["attempt"](match, *args, **kw)
        submission = history.submission_change_history[marks[0]:]
        setup = history.setup_change_history[marks[1]:]
        threat_entry = any(e.startswith("entry:") for e in submission)
        stage_advance = any(":" not in e and not e.endswith("->Tap") for e in submission)
        record.update(
            effective=stage1a._c(result.attempt.effective_commitment),
            realized_grade=result.resolution.final_grade.display,
            terminal=(result.resolution.exit_destination is not None
                      if side is Side.BOTTOM else match.submission_tapped),
            progress=side is Side.TOP and (threat_entry or stage_advance),
            threat_entry=threat_entry, setup_advanced=bool(setup),
            exit=(result.resolution.exit_destination.value
                  if result.resolution.exit_destination is not None else None),
        )
        index = obs.index_of[id(match)]
        if obs.first_ready[index] is None and match.setup_state.is_ready(
                TOP_AMERICANA_ARM_ISOLATION):
            obs.first_ready[index] = match.elapsed_simulated_time
        if decision is not None:
            decision["attempt"] = len(obs.timelines[index])
        obs.timelines[index].append(record)
        return result

    return dict(advance=advance, reset_window=reset_window, recovery_hold=recovery_hold,
                consume_free_initiative_window=consume_free_initiative_window,
                attempt=attempt)


def observe(kwargs: dict, *, policy: BatchInitiatorPolicy, tape=None,
            late: bool = False):
    """One run. policy ESCAPE_FIRST: the baseline. TACTICAL_V1 with tape None:
    the observed candidate. TACTICAL_V1 with a tape: the inertness replay
    (no evaluation). Returns (Observation, late-recovery characterization)."""
    evaluate = policy is TACTICAL and tape is None
    obs = Observation(evaluate=evaluate)
    context = v2.Context.from_batch_kwargs({**kwargs, "initiator_policy": policy})
    original_create = tp.create_policy
    original_decide = D3BTokenLockoutController.decide
    observed_class = _observed_policy_class(obs)

    def factory(*args, **factory_kwargs):
        match = MountMatch(*args, **factory_kwargs)
        obs.index_of[id(match)] = len(obs.created)
        obs.created.append(match)
        obs.timelines.append([])
        obs.first_ready.append(None)
        return match

    def create_policy(settings):
        if tape is not None:
            return original_create(settings)
        ctx = v2.Context.from_batch_kwargs({**settings, "initiator_policy": TACTICAL})
        obs.policy = observed_class(ctx)
        return obs.policy

    def decide(controller, match, *, armed):
        if not obs.real(match):
            return original_decide(controller, match, armed=armed)
        if evaluate:
            obs.pre_decide[id(match)] = v2.branch_of(match, controller)
        decision = original_decide(controller, match, armed=armed)
        obs.last_kind[id(match)] = decision.kind
        obs.p3[f"d3b:{decision.kind.value}"] += 1
        return decision

    def run(**run_kwargs):
        inner = {name: getattr(MountMatch, name) for name in _ROUTED}
        routers = _routers(obs, context, inner)
        with ExitStack() as stack:
            for name, fn in routers.items():
                stack.enter_context(patch.object(MountMatch, name, fn))
            if tape is not None:
                stack.enter_context(tp.replaying(tape))
            obs.batch_run = run_batch(initiator_policy=policy, **run_kwargs)
        return obs.batch_run.summary

    with ExitStack() as stack:
        stack.enter_context(stage1a.count_rng(obs.trace))
        stack.enter_context(patch.object(batch_module, "MountMatch", factory))
        stack.enter_context(patch.object(tp, "create_policy", create_policy))
        stack.enter_context(patch.object(D3BTokenLockoutController, "decide", decide))
        stack.enter_context(patch.object(v2, "candidates",
                                         obs.capture.candidates(v2.candidates)))
        stack.enter_context(patch.object(te, "choose_te1",
                                         obs.capture.choose_te1(te.choose_te1)))
        if late:
            # The unchanged late-recovery observer; it forces
            # measure_stamina_economy=True, which E-PROD already sets.
            if not kwargs.get("measure_stamina_economy"):
                raise RuntimeError("late-recovery observer would change the surface")
            stack.enter_context(patch.object(late_recovery, "run_escape_first_batch", run))
            summary, timelines = late_recovery.observe_batch(**kwargs)
            characterization = late_recovery.characterize(summary, timelines)
        else:
            run(**kwargs)
            characterization = None
    if (tp.create_policy is not original_create
            or D3BTokenLockoutController.decide is not original_decide
            or batch_module.MountMatch is not MountMatch
            or any(getattr(MountMatch, n) is not _TRUE[n] for n in _ROUTED)):
        raise RuntimeError("observer wrappers not restored")
    return obs, characterization


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def outcome_row(summary, builds_reason_independent: int) -> dict:
    outcomes = summary.outcome_counts
    tap = outcomes.get(_TAP, 0)
    timeouts = outcomes.get(_TIMEOUT, 0)
    return dict(
        threat_matches=summary.matches_reached_submission_threat,
        tap=tap, escapes=summary.matches - tap - timeouts, timeouts=timeouts,
        top_completed_builds=summary.top_completed_setup_build_count,
        top_completed_builder_attempts=builds_reason_independent,
    )


def _summary_report(summary) -> dict:
    keys = ("outcome_counts", "top_final_stamina_mean", "top_final_stamina_median",
            "bottom_final_stamina_mean", "bottom_final_stamina_median",
            "top_first_exhausted_time_median", "bottom_first_exhausted_time_median",
            "matches_top_ever_exhausted", "matches_bottom_ever_exhausted",
            "matches_both_ever_exhausted", "final_axis_mean", "top_reset_count",
            "bottom_reset_count", "free_initiative_window_count",
            "top_escape_priority_count", "bottom_escape_priority_count",
            "top_submission_priority_count", "top_submission_attempt_count",
            "matches_reached_submission_threat", "matches_reached_submission_control",
            "matches_reached_submission_finish", "top_position_attack_count",
            "bottom_position_attack_count", "top_setup_action_count",
            "bottom_setup_action_count", "top_completed_setup_chain_count",
            "top_completed_setup_build_count", "top_action_counts", "bottom_action_counts",
            "response_requested_commitment_counts")
    out = {}
    for k in keys:
        value = getattr(summary, k)
        out[k] = dict(value) if isinstance(value, dict) else value
    return out


def _decisions(timelines, *, executed=True):
    return [e for events in timelines for e in events
            if e["kind"] == "decision" and e["executed"] is executed]


def chains(events: list[dict]) -> list[dict]:
    """Reason-independent Top chains (5.2): Top builder attempts whose target
    is not Ready, closed by Top's next attempt of that target while Ready."""
    out, open_chains = [], {}
    for i, e in enumerate(events):
        if e["kind"] != "attempt" or e["side"] != Side.TOP.value:
            continue
        if e["builder_not_ready"]:
            open_chains.setdefault(e["builder_target"], []).append(i)
        if e["ready_use"] and e["action"] in open_chains:
            out.append(dict(attempts=open_chains.pop(e["action"]), use=i,
                            converted=e["threat_entry"]))
    for target, attempts in open_chains.items():
        out.append(dict(attempts=attempts, use=None, converted=False))
    return out


def _decision_of(events, attempt_index):
    for e in reversed(events[:attempt_index]):
        if e["kind"] == "decision" and e.get("attempt") == attempt_index:
            return e
    return None


def score_candidate(name: str, obs: Observation, late) -> tuple[dict, dict]:
    run = obs.batch_run
    summary = run.summary
    timelines = obs.timelines
    executed = _decisions(timelines)
    counterfactual = _decisions(timelines, executed=False)
    attempts = [e for events in timelines for e in events if e["kind"] == "attempt"]
    g6 = tp.g6_tally(run.tactical.exchanges)

    tiers, commitments, forced = Counter(), Counter(), Counter()
    for d in executed:
        tiers[f"{d['side']}:{d['tier']}"] += 1
        if d["action"] is not None:
            commitments[f"{d['side']}:{d['tier']}:{d['requested']}"] += 1
            if d["forced_by"]:
                forced[f"{d['side']}:{d['forced_by']}"] += 1

    # Calibration per component (C2 style) over executed exchanges, at the
    # value TE-1 executed.
    pairs = {k: [] for k in ("terminal", "progress", "setup_advance")}
    for events in timelines:
        for i, e in enumerate(events):
            if e["kind"] != "attempt":
                continue
            d = _decision_of(events, i)
            chosen = d["chosen"]
            pairs["terminal"].append((Fraction(chosen["terminal"]), e["terminal"]))
            pairs["progress"].append((Fraction(chosen["progress"]), e["progress"]))
            pairs["setup_advance"].append((Fraction(chosen["setup_advance"]),
                                           e["setup_advanced"]))
    calibration = {k: stage1a.calibration(v) for k, v in pairs.items()}

    # Setup calibration (C5 style) and horizon mismatches over every chain begun.
    c5_pairs, horizon = [], Counter()
    ready_pred, ready_actual, ready_uses = Fraction(0), 0, 0
    setup_decisions_top = sum(1 for d in executed
                              if d["side"] == Side.TOP.value and d["tier"] == "setup")
    for events in timelines:
        for chain in chains(events):
            first = _decision_of(events, chain["attempts"][0])
            p = Fraction(first["chosen"]["setup_future"])
            c5_pairs.append((p, bool(chain["converted"])))
            r = first["chosen"]["r"]
            if chain["use"] is not None and r is not None:
                start, use = chain["attempts"][0], chain["use"]
                windows = sum(1 for e in events[start:use]
                              if (e["kind"] == "decision" and e["executed"])
                              or e["kind"] == "hold")
                horizon["closed_chains_with_r"] += 1
                horizon["real_horizon_differs_from_2r"] += windows != 2 * r
            elif r is None:
                horizon["chain_start_without_projection"] += 1
        for i, e in enumerate(events):
            if (e["kind"] == "attempt" and e["side"] == Side.TOP.value
                    and e["action"] == TOP_AMERICANA_ARM_ISOLATION and e["ready_use"]):
                d = _decision_of(events, i)
                ready_uses += 1
                ready_pred += Fraction(d["chosen"]["progress"])
                ready_actual += e["progress"]
    setup_calibration = stage1a.calibration(c5_pairs)

    o3 = {}
    for key, n in obs.o3.items():
        side_tier, metric = key.rsplit(":", 1)
        o3.setdefault(side_tier, {})[metric] = n
    free = sum(1 for events in timelines for e in events if e["kind"] == "free_window")
    first_ready = [t for t in obs.first_ready if t is not None]
    threat = summary.matches_reached_submission_threat
    result = dict(
        outcomes=outcome_row(summary, run.top_completed_setup_builder_attempt_count),
        summary=_summary_report(summary),
        g6=dict(te1_chosen=g6.te1_chosen, high=g6.high,
                excluded_forced=dict(g6.excluded_forced),
                by_side={s: dict(te1_chosen=n, high=h) for s, n, h in g6.by_side}),
        reported=dict(
            te1_tier_distribution=dict(tiers),
            commitment_distribution=dict(commitments),
            precedence_forced_exchanges=dict(forced),
            baseline_reason_counters_candidate=dict(
                top_escape=summary.top_escape_priority_count,
                top_submission=summary.top_submission_priority_count,
                top_setup=summary.top_setup_action_count,
                top_position=summary.top_position_attack_count,
                top_reset=summary.top_reset_count,
                bottom_escape=summary.bottom_escape_priority_count,
                bottom_setup=summary.bottom_setup_action_count,
                bottom_position=summary.bottom_position_attack_count,
                bottom_reset=summary.bottom_reset_count),
            top_setup_tier_decisions=setup_decisions_top,
            setup_decisions_per_threat_entry=(setup_decisions_top / threat if threat else None),
            builder_attempts_per_threat_entry=(
                run.top_completed_setup_builder_attempt_count / threat if threat else None),
            forgone_better_position=sum(bool(d.get("forgone_better_position"))
                                        for d in executed),
            ready_conversion_top=dict(uses=ready_uses, predicted=float(ready_pred),
                                      predicted_exact=_q(ready_pred), actual=ready_actual),
            calibration=calibration,
            setup_calibration_chains=setup_calibration,
            horizon=dict(horizon),
            o3_fidelity=o3,
            resets_per_match=dict(
                top=summary.top_reset_count / summary.matches,
                bottom=summary.bottom_reset_count / summary.matches),
            time_by_initiative_band=dict(sorted(obs.cells.items())),
            free_initiative_windows=free,
            mean_time_to_first_top_ready=(sum(first_ready) / len(first_ready)
                                          if first_ready else None),
            matches_reaching_top_ready=len(first_ready),
            executed_decisions=len(executed),
            counterfactual_calls=len(counterfactual),
            exchanges=len(attempts),
        ),
    )
    if late is not None:
        exhausted = sum(r["bottom_exhausted_seconds"] for r in late["per_match"])
        total = sum(r["end"] for r in late["per_match"])
        result["late_recovery"] = {k: v for k, v in late.items() if k != "per_match"}
        result["bottom_exhausted_share_exact"] = dict(exhausted_seconds=exhausted,
                                                      match_seconds=total)
    records = dict(per_match=timelines,
                   late_recovery_per_match=late["per_match"] if late is not None else None)
    return result, records


def _p3(obs: Observation, run) -> dict:
    lockouts = obs.p3.get(f"d3b:{HandoffDecisionKind.LOCKOUT_HOLD.value}", 0)
    hold_history = sum(len(m.history.recovery_hold_history) for m in obs.created)
    counterfactual = sum(1 for e in run.tactical.tape
                         if e.kind is tp.CallKind.COUNTERFACTUAL)
    return dict(
        bottom_recover_exhausted_initiations=obs.p3["bottom_recover_exhausted_initiations"],
        bottom_recover_exhausted_not_low=obs.p3["bottom_recover_exhausted_not_low"],
        d3b_decisions={k.split(":", 1)[1]: n for k, n in obs.p3.items()
                       if k.startswith("d3b:")},
        lockout_hold_decisions=lockouts, recovery_hold_history=hold_history,
        holds_executed=obs.p3["holds"], counterfactual_tape_entries=counterfactual,
        attempts_in_lockout_hold_window=obs.p3["attempt_in_lockout_hold_window"],
        holds_without_lockout_decision=obs.p3["hold_without_lockout_decision"],
    )


def _p3_ok(p3: dict) -> bool:
    return (p3["bottom_recover_exhausted_not_low"] == 0
            and p3["attempts_in_lockout_hold_window"] == 0
            and p3["holds_without_lockout_decision"] == 0
            and p3["lockout_hold_decisions"] == p3["recovery_hold_history"]
            == p3["holds_executed"] == p3["counterfactual_tape_entries"])


def _signatures(obs: Observation):
    return tuple(_match_gameplay_signature(m) for m in obs.created)


def _comparable(timelines) -> str:
    return json.dumps(timelines, sort_keys=True, default=str)


def measure_surface(name: str, kwargs: dict, *, gated: bool, replay: bool = True
                    ) -> tuple[dict, dict]:
    """Gated: baseline, candidate, second candidate (P4b) and inertness replay
    (P4c). Holdout: candidate only. replay=False skips P4b and P4c (CI
    evidence pin only; the authoritative measurement always runs them)."""
    late = name.startswith("E-PROD")
    out: dict = dict(gated=gated)
    if gated:
        base, _ = observe(kwargs, policy=ESCAPE_FIRST)
        row = outcome_row(base.batch_run.summary,
                          base.batch_run.top_completed_setup_builder_attempt_count)
        observed = [row[k] for k in BASELINE_FIELDS]
        frozen = list(FROZEN_BASELINES[name])
        out["baseline"] = dict(
            fields=list(BASELINE_FIELDS), observed=observed, frozen=frozen,
            exact=observed == frozen,
            reason_independent_builder_attempts=row["top_completed_builder_attempts"],
            g4_equivalence=(row["top_completed_builder_attempts"]
                            == row["top_completed_builds"]),
            evaluator_rng_draws=sum(base.trace.evaluator_draws.values()))
    else:
        frozen = list(HOLDOUT_BASELINES[name])
        committed = json.loads(stage1a_v2.SUMMARY_EVIDENCE.read_text(encoding="utf-8"))
        if committed["surfaces"][name]["baseline"]["observed"] != frozen:
            raise RuntimeError(f"holdout baseline {name!r} differs from committed evidence")
        out["baseline"] = dict(fields=list(BASELINE_FIELDS), frozen=frozen,
                               source="Stage 1A-v2 committed evidence")

    cand, late_char = observe(kwargs, policy=TACTICAL, late=late)
    result, records = score_candidate(name, cand, late_char)
    out.update(result)
    run = cand.batch_run
    p3 = _p3(cand, run)
    integrity = dict(
        evaluator_rng_draws=sum(cand.trace.evaluator_draws.values()),
        p3=p3, p3_ok=_p3_ok(p3),
        p5=dict(cand.p5), p5_ok=set(cand.p5) <= {"checked"},
        tape_entries=len(run.tactical.tape),
        tape_executed=sum(1 for e in run.tactical.tape if e.kind is tp.CallKind.EXECUTED),
        historical_counter_le_reason_independent=(
            run.summary.top_completed_setup_build_count
            <= run.top_completed_setup_builder_attempt_count),
    )
    if gated and replay:
        second, _ = observe(kwargs, policy=TACTICAL, late=late)
        integrity["p4b_second_run_identical"] = (
            second.batch_run.summary == run.summary
            and _signatures(second) == _signatures(cand)
            and second.batch_run.tactical == run.tactical
            and second.batch_run.top_completed_setup_builder_attempt_count
            == run.top_completed_setup_builder_attempt_count
            and _comparable(second.timelines) == _comparable(cand.timelines)
            and second.trace.baseline_digest == cand.trace.baseline_digest
            and second.trace.baseline_draws == cand.trace.baseline_draws
            and sum(second.trace.evaluator_draws.values()) == 0)
        try:
            rep, _ = observe(kwargs, policy=TACTICAL, tape=run.tactical.tape)
        except tp.ReplayDesync as error:
            integrity["p4c_replay_identical"] = False
            integrity["p4c_replay_error"] = error.code
        else:
            integrity["p4c_replay_identical"] = (
                rep.batch_run.summary == run.summary
                and _signatures(rep) == _signatures(cand)
                and rep.batch_run.tactical == run.tactical
                and rep.trace.baseline_digest == cand.trace.baseline_digest
                and rep.trace.baseline_draws == cand.trace.baseline_draws)
    out["integrity"] = integrity
    out["rng"] = dict(baseline_draws=cand.trace.baseline_draws,
                      digest=cand.trace.baseline_digest)
    return out, records


def _integrity_ok(v: dict) -> bool:
    i = v["integrity"]
    ok = (i["evaluator_rng_draws"] == 0 and i["p3_ok"] and i["p5_ok"]
          and i["historical_counter_le_reason_independent"])
    if v["gated"]:
        b = v["baseline"]
        ok = ok and b["exact"] and b["g4_equivalence"] and b["evaluator_rng_draws"] == 0
        ok = ok and i.get("p4b_second_run_identical") is True
        ok = ok and i.get("p4c_replay_identical") is True
    return ok


def _protected_diff() -> list[str]:
    out = subprocess.run(["git", "diff", "--name-only", PREREGISTRATION, "--",
                          *PROTECTED_PATHS], capture_output=True, text=True, check=True)
    return [line for line in out.stdout.splitlines() if line]


def gates(out: dict) -> dict:
    s = out
    o = {n: s[n]["outcomes"] for n in GATED_SURFACES}
    g = {}
    g["G1"] = dict(
        a_prod=o["A-PROD"]["threat_matches"],
        pooled_off=(o["B-PROD"]["threat_matches"] + o["E-PROD 42 OFF"]["threat_matches"]
                    + o["E-PROD 142 OFF"]["threat_matches"]),
        pooled_on=(o["B-PROD"]["threat_matches"] + o["E-PROD 42 ON"]["threat_matches"]
                   + o["E-PROD 142 ON"]["threat_matches"]))
    g["G1"]["status"] = ("PASS" if g["G1"]["a_prod"] >= 63 and g["G1"]["pooled_off"] >= 142
                         and g["G1"]["pooled_on"] >= 142 else "FAIL")
    g["G2"] = dict(tap={n: o[n]["tap"] for n in GATED_SURFACES})
    g["G2"]["status"] = "PASS" if all(t <= 20 for t in g["G2"]["tap"].values()) else "FAIL"
    g["G3"] = dict(
        e_pooled_off=o["E-PROD 42 OFF"]["escapes"] + o["E-PROD 142 OFF"]["escapes"],
        e_pooled_on=o["E-PROD 42 ON"]["escapes"] + o["E-PROD 142 ON"]["escapes"],
        b_prod=o["B-PROD"]["escapes"])
    g["G3"]["status"] = ("PASS" if g["G3"]["e_pooled_off"] >= 49
                         and g["G3"]["e_pooled_on"] >= 49 and g["G3"]["b_prod"] >= 10
                         else "FAIL")
    p = o["PROTECT probe"]
    g["G4"] = dict(reason_independent=p["top_completed_builder_attempts"],
                   historical_counter=p["top_completed_builds"], floor=884, baseline=1768)
    g["G4"]["status"] = "PASS" if p["top_completed_builder_attempts"] <= 884 else "FAIL"
    g5 = {}
    for n in E_PROD:
        median = s[n]["summary"]["bottom_first_exhausted_time_median"]
        share = s[n]["bottom_exhausted_share_exact"]
        g5[n] = dict(first_exhausted_median=median,
                     exhausted_share=share["exhausted_seconds"] / share["match_seconds"],
                     median_ok=median is not None and median >= 50,
                     share_ok=5 * share["exhausted_seconds"] <= 4 * share["match_seconds"])
    g["G5"] = dict(runs=g5, status=("PASS" if all(r["median_ok"] and r["share_ok"]
                                                  for r in g5.values()) else "FAIL"))
    g6 = {}
    for mode in ("OFF", "ON"):
        a, b = s[f"E-PROD 42 {mode}"]["g6"], s[f"E-PROD 142 {mode}"]["g6"]
        chosen, high = a["te1_chosen"] + b["te1_chosen"], a["high"] + b["high"]
        excluded = Counter(a["excluded_forced"]) + Counter(b["excluded_forced"])
        g6[mode] = dict(te1_chosen=chosen, high=high,
                        share=(high / chosen if chosen else None),
                        excluded_forced=dict(excluded), ok=chosen > 0 and 2 * high <= chosen)
    g["G6"] = dict(modes=g6, status="PASS" if all(m["ok"] for m in g6.values()) else "FAIL")
    return g


def measure(names=None, *, jobs: int = 1, workdir: Path | None = None) -> tuple[dict, dict]:
    names = list(names or surfaces())
    if jobs > 1:
        done = _run_parts(names, jobs, workdir or Path("docs/evidence/.stage1b_parts"))
    else:
        done = [_measure_one(n) for n in names]
    out = {n: r for n, r, _ in done}
    records = {n: rec for n, _, rec in done}
    gated = {n: out[n] for n in GATED_SURFACES if n in out}
    integrity = all(_integrity_ok(v) for v in out.values())
    protected = _protected_diff()
    preservation = dict(
        P1=dict(status="CI", local_baselines_exact=all(
            v["baseline"]["exact"] for v in gated.values()),
            note="full suite, digest and both checkers on exact-head CI (3.11, 3.13)"),
        P2=dict(status="PASS" if not protected else "FAIL", protected_paths_changed=protected),
        P3=dict(status="PASS" if all(v["integrity"]["p3_ok"] for v in gated.values())
                else "FAIL"),
        P4=dict(status="PASS" if all(
            v["integrity"]["evaluator_rng_draws"] == 0
            and v["integrity"].get("p4b_second_run_identical") is True
            and v["integrity"].get("p4c_replay_identical") is True
            for v in gated.values()) else "FAIL"),
        P5=dict(status="PASS" if all(v["integrity"]["p5_ok"] for v in gated.values())
                else "FAIL"),
        P6=dict(status="CI"),
    )
    design = gates(out) if len(gated) == len(GATED_SURFACES) else None
    if not integrity or design is None:
        verdict = "OPEN"
    elif any(design[g]["status"] == "FAIL" for g in design) or any(
            preservation[p]["status"] == "FAIL" for p in preservation):
        verdict = "FAIL"
    else:
        verdict = "PASS (subject to P1 and P6 on exact-head CI)"
    holdouts = {}
    for n in HOLDOUT_SURFACES:
        if n not in out:
            continue
        row, base = out[n]["outcomes"], dict(zip(BASELINE_FIELDS, out[n]["baseline"]["frozen"]))
        holdouts[n] = {k: dict(candidate=row[k], baseline=base[k],
                               ratio=(row[k] / base[k] if base[k] else None))
                       for k in BASELINE_FIELDS}
        holdouts[n]["top_completed_builder_attempts"] = row["top_completed_builder_attempts"]
        if "bottom_exhausted_share_exact" in out[n]:
            sh = out[n]["bottom_exhausted_share_exact"]
            holdouts[n]["bottom_first_exhausted_median"] = (
                out[n]["summary"]["bottom_first_exhausted_time_median"])
            holdouts[n]["bottom_exhausted_share"] = sh["exhausted_seconds"] / sh["match_seconds"]
            holdouts[n]["g6"] = out[n]["g6"]
    return dict(preregistration=PREREGISTRATION, implementation=IMPLEMENTATION,
                surfaces=out, preservation=preservation, design_gates=design,
                holdouts_reported=holdouts, integrity_ok=integrity,
                stage_1b=verdict), records


def _measure_one(name: str) -> tuple[str, dict, dict]:
    result, records = measure_surface(name, surfaces()[name],
                                      gated=name in GATED_SURFACES)
    return name, result, records


def _run_parts(names: list[str], jobs: int, workdir: Path) -> list[tuple[str, dict, dict]]:
    """Each surface in its own fresh interpreter; parts merged in surface order."""
    import sys
    import time
    workdir.mkdir(parents=True, exist_ok=True)
    queue, running, done = list(names), [], {}
    while queue or running:
        while queue and len(running) < jobs:
            name = queue.pop(0)
            part = workdir / f"{names.index(name)}_{name.replace(' ', '_')}.json"
            log = open(workdir / f"{names.index(name)}_{name.replace(' ', '_')}.log", "w")
            proc = subprocess.Popen([sys.executable, "-m",
                                     "bjj_game.diagnostics.tactical_evaluator_stage1b",
                                     "--surface", name, "--part", str(part)],
                                    stdout=log, stderr=subprocess.STDOUT)
            running.append((name, part, proc, log))
        for item in list(running):
            name, part, proc, log = item
            if proc.poll() is not None:
                running.remove(item)
                log.close()
                if proc.returncode != 0:
                    raise RuntimeError(f"surface {name!r} failed ({proc.returncode})")
                payload = json.loads(part.read_text(encoding="utf-8"))
                done[name] = (name, payload["result"], payload["records"])
        if running:
            time.sleep(2)
    return [done[n] for n in names]


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
                                              sort_keys=True, default=str), encoding="utf-8")
        return
    summary, records = measure(jobs=args.jobs,
                               workdir=Path(args.workdir) if args.workdir else None)
    SUMMARY_EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_EVIDENCE.write_text(json.dumps(summary, indent=1, sort_keys=True, default=str)
                                + "\n", encoding="utf-8", newline="\n")
    with gzip.GzipFile(RECORDS_EVIDENCE, "wb", mtime=0) as handle:
        handle.write(json.dumps(records, sort_keys=True, separators=(",", ":"),
                                default=str).encode())
    print(SUMMARY_EVIDENCE)
    print(RECORDS_EVIDENCE)
    print("Stage 1B:", summary["stage_1b"])


if __name__ == "__main__":
    main()
