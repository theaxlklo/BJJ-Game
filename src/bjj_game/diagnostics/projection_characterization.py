"""Projection-error characterization for the failed Stage 1A tactical evaluator
(docs/TACTICAL_EVALUATOR_STAGE1A_RESULT.md, 2d2778d; preregistration 4e61bad).

Read-only. Nothing here is used by TE-1 or by gameplay, and no projection,
gate or threshold changes. The question: between a baseline Top builder
decision and its Ready use, which state changes did the frozen section 2.4
projection omit, and which of them decide C3?

Method
------
1. Re-observation, not a new population. The Stage 1A per-event records hold
   outcomes and projections but no per-window state. The frozen surfaces are
   re-run under the unchanged baseline with a state recorder (scoped wrappers
   on advance, attempt, reset_window, recovery_hold and the real policy
   decision; no evaluator runs during play). Identity with the committed
   Stage 1A records is checked per decision and per exchange, and the RNG
   sequence and summary are checked against an uninstrumented run, so the
   trajectories are the frozen populations.
2. Exact decomposition. For each Top builder decision whose chain reached a
   Ready use, the change from the decision state to the use state is split
   into stamina and axis components that sum exactly to the realized change.
3. Layered attribution (P0-P6). Historical future values are substituted into
   the frozen projection one component group at a time and the frozen use
   valuation (outcome_distribution at the projected state) is re-applied.
   This is attribution only: it reads the actual future and is never a
   candidate evaluator. P0 must reproduce the committed Stage 1A projections
   exactly; P6 must equal the realized use state exactly.

Candidate continuation models are deliberately not scored against C3/C4 here
(rerunning the gates under a revised evaluator is outside this slice and would
fit the model to the failed dataset).
"""
from __future__ import annotations

from collections import Counter
from contextlib import ExitStack
from dataclasses import dataclass, replace
import gzip
import json
from pathlib import Path
from statistics import mean, median
from unittest.mock import patch

from ..domain.model import Side
from ..domain.stamina import StaminaBand
from ..engine.match import MountMatch
from ..interfaces import batch as batch_module
from ..interfaces import tactical_evaluator as te
from ..interfaces.batch import EscapeFirstInitiatorPolicy, run_escape_first_batch
from ..interfaces.handoff_policy import D3BTokenLockoutController, HandoffDecisionKind
from ..positions.mount.catalog import TOP_AMERICANA_ARM_ISOLATION
from . import tactical_evaluator as stage1a
from .stamina_adoption_verification import _match_gameplay_signature

STAGE1A_HEAD = "2d2778d88205874e30aeda37579dc45d5d9f885e"
SUMMARY_EVIDENCE = Path("docs/evidence/tactical_evaluator_projection_characterization.json")
STAGE1A_RECORDS = stage1a.RECORDS_EVIDENCE

# Component groups of the use-state change (decision state -> Ready-use state).
STAMINA_COMPONENTS = {
    # Top (the builder, "own")
    "top_flow": "Top passive behavior flow",
    "top_builder_spend": "Top commitment spend on its builder exchanges",
    "top_other_initiation_spend": "Top commitment spend on its non-builder exchanges",
    "top_response_spend": "Top response spend during Bottom initiations",
    # Bottom (the defender, "opponent")
    "bottom_flow": "Bottom passive behavior flow",
    "bottom_builder_response_spend": "Bottom response (+hold) spend on Top builder exchanges",
    "bottom_other_response_spend": "Bottom response (+hold) spend on Top non-builder exchanges",
    "bottom_initiation_spend": "Bottom commitment spend on its own initiations",
}
AXIS_COMPONENTS = {
    "axis_builder": "Top builder exchange movement",
    "axis_drift": "ordinary drift (advance)",
    "axis_bottom_initiation": "Bottom-initiated exchange movement",
    "axis_top_other": "Top non-builder exchange movement",
    "axis_stalling": "stalling penalty / position reset movement",
}

# Attribution groups. Each maps the frozen projection's term to the actual one.
GROUPS = (
    "builder_settlement",     # P1: actual builder spend (own) + Bottom's responses to builders
    "intervening_stamina",    # P2: Bottom initiations, Top responses, Top non-builder exchanges
    "drift",                  # P3: ordinary drift
    "intervening_axis",       # P4: Bottom-initiated and Top non-builder exchange movement
    "passive_flow",           # P5: actual passive flow (horizon, behavior) replaces rate x delta
    "builder_axis",           # P5: actual builder movement replaces r x E[realized]
    "stalling_axis",          # P5: stalling penalties / position resets
    "path",                   # P6: actual stamina latches, axis band hysteresis, behaviors
)
LAYERS = (
    ("P0", ()),
    ("P1", ("builder_settlement",)),
    ("P2", ("builder_settlement", "intervening_stamina")),
    ("P3", ("builder_settlement", "intervening_stamina", "drift")),
    ("P4", ("builder_settlement", "intervening_stamina", "drift", "intervening_axis")),
    ("P5", ("builder_settlement", "intervening_stamina", "drift", "intervening_axis",
            "passive_flow", "builder_axis", "stalling_axis")),
    ("P6", GROUPS),
)
COMPOSITES = {
    "stamina_only": ("builder_settlement", "intervening_stamina", "passive_flow"),
    "axis_only": ("drift", "intervening_axis", "builder_axis", "stalling_axis"),
    "stamina_and_axis_without_path": tuple(g for g in GROUPS if g != "path"),
    # Is the opponent's own window needed? Top's windows and the advances only
    # (builder settlement, flow, drift, builder movement), then the opponent
    # window's stamina, then its movement.
    "own_windows_and_advances": ("builder_settlement", "passive_flow", "drift", "builder_axis"),
    "own_windows_and_advances_path": ("builder_settlement", "passive_flow", "drift",
                                      "builder_axis", "path"),
    "own_windows_advances_opponent_stamina": ("builder_settlement", "passive_flow", "drift",
                                              "builder_axis", "intervening_stamina"),
    "own_windows_advances_opponent_stamina_path": ("builder_settlement", "passive_flow",
                                                   "drift", "builder_axis",
                                                   "intervening_stamina", "path"),
}


# ---------------------------------------------------------------------------
# Read-only state recorder
# ---------------------------------------------------------------------------


def _snap(match: MountMatch) -> dict:
    return dict(
        t=match.elapsed_simulated_time,
        top=match.top.stamina.current, bottom=match.bottom.stamina.current,
        top_latched=match.top.stamina.band is StaminaBand.EXHAUSTED,
        bottom_latched=match.bottom.stamina.band is StaminaBand.EXHAUSTED,
        axis=match.position.control.value, band=match.band,
        top_behavior=match.top.behavior, bottom_behavior=match.bottom.behavior,
    )


def record_batch(**kwargs):
    """Run the unchanged baseline with the state recorder.

    Returns (summary, signatures, per-match op lists, matches, RngTrace)."""
    original = dict(advance=MountMatch.advance, attempt=MountMatch.attempt,
                    reset=MountMatch.reset_window, hold=MountMatch.recovery_hold,
                    choose=EscapeFirstInitiatorPolicy.choose,
                    decide=D3BTokenLockoutController.decide)
    created: list[MountMatch] = []
    ops: list[list[dict]] = []
    index_of: dict[int, int] = {}
    last_handoff: dict[int, HandoffDecisionKind] = {}
    trace = stage1a.RngTrace()

    def factory(*args, **factory_kwargs):
        match = MountMatch(*args, **factory_kwargs)
        index_of[id(match)] = len(created)
        created.append(match)
        ops.append([])
        return match

    def log(match, op):
        ops[index_of[id(match)]].append(op)

    def advance(match):
        before = _snap(match)
        result = original["advance"](match)
        after = _snap(match)
        log(match, dict(kind="advance", before=before, after=after,
                        drift=result.drift.total_drift))
        return result

    def decide(controller, match, *, armed):
        decision = original["decide"](controller, match, armed=armed)
        last_handoff[id(match)] = decision.kind
        return decision

    def choose(policy, match):
        kind = last_handoff.pop(id(match), None)
        decision = original["choose"](policy, match)
        if match.initiator is Side.BOTTOM and kind is HandoffDecisionKind.LOCKOUT_HOLD:
            return decision  # D3-B counterfactual call; the window holds
        log(match, dict(kind="decision", t=match.elapsed_simulated_time,
                        side=match.initiator.value, action=decision.action_id,
                        reason=decision.reason, state=te.State.of(match)))
        return decision

    def attempt(match, *args, **kw):
        state = te.State.of(match)
        before = _snap(match)
        action_id = kw["action_id"]
        target = match.setup_policy.target_for_builder(action_id)
        builder = (match.enable_v02_setup and target is not None
                   and not match.setup_state.is_ready(target))
        history = match.history
        marks = (len(history.submission_change_history), len(history.setup_change_history))
        result = original["attempt"](match, *args, **kw)
        after = _snap(match)
        submission = history.submission_change_history[marks[0]:]
        log(match, dict(
            kind="attempt", before=before, after=after, state=state,
            side=state.initiator.value, action=action_id, builder=builder,
            requested=kw["commitment"].value,
            effective=stage1a._c(result.attempt.effective_commitment),
            response=kw["response_id"],
            response_effective=stage1a._c(result.response_effective_commitment),
            realized_grade=result.resolution.final_grade.display,
            ready_use=action_id in state.ready,
            threat_entry=any(e.startswith("entry:") for e in submission),
            setup_advanced=len(history.setup_change_history) > marks[1],
            exit=(result.resolution.exit_destination.value
                  if result.resolution.exit_destination is not None else None),
            initiator_charged=result.stamina.charged,
            response_charged=(result.response_stamina.charged
                              if result.response_stamina is not None else 0),
            hold_charged=(result.submission_hold_stamina.charged
                          if result.submission_hold_stamina is not None else 0),
            axis_after=result.resolution.axis_after,
        ))
        return result

    def reset(match):
        before = _snap(match)
        result = original["reset"](match)
        log(match, dict(kind="reset", before=before, after=_snap(match),
                        side=result.initiator.value,
                        free_next=result.free_initiative_window))
        return result

    def hold(match):
        before = _snap(match)
        result = original["hold"](match)
        log(match, dict(kind="hold", before=before, after=_snap(match), side="bottom"))
        return result

    with ExitStack() as stack:
        stack.enter_context(stage1a.count_rng(trace))
        stack.enter_context(patch.object(batch_module, "MountMatch", factory))
        stack.enter_context(patch.object(MountMatch, "advance", advance))
        stack.enter_context(patch.object(MountMatch, "attempt", attempt))
        stack.enter_context(patch.object(MountMatch, "reset_window", reset))
        stack.enter_context(patch.object(MountMatch, "recovery_hold", hold))
        stack.enter_context(patch.object(EscapeFirstInitiatorPolicy, "choose", choose))
        stack.enter_context(patch.object(D3BTokenLockoutController, "decide", decide))
        summary = run_escape_first_batch(**kwargs)
    if (MountMatch.advance is not original["advance"]
            or MountMatch.attempt is not original["attempt"]
            or MountMatch.reset_window is not original["reset"]
            or MountMatch.recovery_hold is not original["hold"]
            or EscapeFirstInitiatorPolicy.choose is not original["choose"]
            or D3BTokenLockoutController.decide is not original["decide"]
            or batch_module.MountMatch is not MountMatch):
        raise RuntimeError("recorder wrappers not restored")
    signatures = tuple(_match_gameplay_signature(m) for m in created)
    return summary, signatures, ops, created, trace


# ---------------------------------------------------------------------------
# Identity with the committed Stage 1A records
# ---------------------------------------------------------------------------

_ATTEMPT_FIELDS = ("t", "side", "action", "requested", "effective", "response",
                   "realized_grade", "ready_use", "threat_entry", "setup_advanced", "exit")
_DECISION_FIELDS = ("t", "side", "action", "reason")


def identity(ops: list[list[dict]], frozen_per_match: list[dict]) -> dict:
    """Every recorded decision and exchange equals the committed Stage 1A record."""
    mismatched = []
    decisions = attempts = 0
    for m, (match_ops, frozen) in enumerate(zip(ops, frozen_per_match, strict=True)):
        mine_d = [tuple(o[k] for k in _DECISION_FIELDS) for o in match_ops
                  if o["kind"] == "decision"]
        theirs_d = [tuple(d[k] for k in _DECISION_FIELDS) for d in frozen["decisions"]]
        mine_a = [tuple(o["before"]["t"] if k == "t" else o[k] for k in _ATTEMPT_FIELDS)
                  for o in match_ops if o["kind"] == "attempt"]
        theirs_a = [tuple(a[k] for k in _ATTEMPT_FIELDS) for a in frozen["attempts"]]
        decisions += len(theirs_d)
        attempts += len(theirs_a)
        if mine_d != theirs_d or mine_a != theirs_a:
            mismatched.append(m)
    return dict(matches=len(frozen_per_match), decisions=decisions, attempts=attempts,
                mismatched_matches=mismatched, exact=not mismatched)


# ---------------------------------------------------------------------------
# Intervals: builder decision -> Ready use
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Interval:
    match: int
    decision: dict          # the Top setup decision op
    use: dict | None        # the closing Ready-use attempt op (None: never used)
    ops: tuple              # ops from the builder attempt up to (excluding) the use attempt
    converted: bool | None


def intervals(match_ops: list[dict], m: int) -> list[Interval]:
    """Top setup decisions with the chain closed by the next Ready use, exactly
    as Stage 1A's C3 assignment."""
    out, open_chain = [], []
    for i, op in enumerate(match_ops):
        if op["kind"] == "decision" and op["side"] == "top" and op["reason"] == "setup":
            open_chain.append(i)
        if (op["kind"] == "attempt" and op["side"] == "top"
                and op["action"] == TOP_AMERICANA_ARM_ISOLATION and op["ready_use"]):
            for d in open_chain:
                out.append(Interval(m, match_ops[d], op, tuple(match_ops[d + 1:i]),
                                    op["threat_entry"]))
            open_chain = []
    for d in open_chain:
        out.append(Interval(m, match_ops[d], None, (), None))
    return sorted(out, key=lambda iv: iv.decision["t"])


def decompose(iv: Interval) -> dict:
    """Exact components of the decision-state -> use-state change."""
    c = Counter()
    windows = Counter()
    for op in iv.ops:
        if op["kind"] == "decision":
            continue
        b, a = op["before"], op["after"]
        if op["kind"] == "advance":
            c["top_flow"] += a["top"] - b["top"]
            c["bottom_flow"] += a["bottom"] - b["bottom"]
            c["axis_drift"] += a["axis"] - b["axis"]
            windows["advance"] += 1
            if a["bottom_behavior"] is not b["bottom_behavior"] or \
                    a["top_behavior"] is not b["top_behavior"]:
                windows["behavior_change_in_advance"] += 1
        elif op["kind"] == "attempt":
            # attempt() changes stamina only through these three charges
            init, resp = op["initiator_charged"], op["response_charged"] + op["hold_charged"]
            if op["side"] == "top":
                assert a["top"] - b["top"] == -init and a["bottom"] - b["bottom"] == -resp
                key = "builder" if op["builder"] else "other"
                c["top_builder_spend" if op["builder"] else "top_other_initiation_spend"] -= init
                c["bottom_builder_response_spend" if op["builder"]
                  else "bottom_other_response_spend"] -= resp
                c["axis_builder" if op["builder"] else "axis_top_other"] += a["axis"] - b["axis"]
                windows[f"top_{key}"] += 1
                windows[f"top_{key}:{op['action']}:{op['effective']}"] += 1
            else:
                assert a["bottom"] - b["bottom"] == -init and a["top"] - b["top"] == -resp
                c["bottom_initiation_spend"] -= init
                c["top_response_spend"] -= resp
                c["axis_bottom_initiation"] += a["axis"] - b["axis"]
                windows["bottom_initiation"] += 1
                windows[f"bottom_initiation:{op['effective']}"] += 1
        elif op["kind"] == "reset":
            assert a["top"] == b["top"] and a["bottom"] == b["bottom"]
            c["axis_stalling"] += a["axis"] - b["axis"]
            windows[f"{op['side']}_reset"] += 1
        elif op["kind"] == "hold":
            assert a == b
            windows["bottom_hold"] += 1
    return dict(components=dict(c), windows=dict(windows))


# ---------------------------------------------------------------------------
# Layered attribution (historical substitution; attribution only)
# ---------------------------------------------------------------------------


def _use_values(match: MountMatch, model: te.OpponentModel, projected: te.State,
                target: str, own: te.Pool):
    """Frozen section 2.4 step 6 (te.project_setup's use loop) at a given state."""
    values = []
    for use in te.COMMITMENTS:
        if te.funded(match, use, own.current) is not use:
            continue
        outcomes = te.outcome_distribution(match, model, projected, target, use)
        values.append((use, te._expect(
            outcomes, lambda r: te.is_progress(match, projected, target, use, r))))
    return values


def _actual_pool(snap: dict, side: str, maximum: int) -> te.Pool:
    return te.Pool(snap[side], snap[f"{side}_latched"], maximum)


def layered(match: MountMatch, model: te.OpponentModel, iv: Interval, parts: dict) -> dict:
    """setup_future per candidate commitment for every layer and variant."""
    state: te.State = iv.decision["state"]
    target = match.setup_policy.target_for_builder(iv.decision["action"])
    use_state: te.State = iv.use["state"]
    use_snap = iv.use["before"]
    comp = Counter(parts["components"])
    r = 2 - state.tier(target)
    delta = 2 * r * state.interval_seconds
    flow_top_proj = te.behavior_flow(match, state.top_behavior, delta)
    flow_bot_proj = te.behavior_flow(match, state.bottom_behavior, delta)
    rows = {}
    for c in te.COMMITMENTS:
        effective = te.funded(match, c, state.top.current)
        frozen = te.evaluate(match, model, state, iv.decision["action"], c)
        rows[c] = (effective, frozen)

    def project(groups: frozenset, c):
        effective, frozen = rows[c]
        g = groups.__contains__
        own_spend = (comp["top_builder_spend"] if g("builder_settlement")
                     else -iv_cost(match, effective) * r)
        top = (state.top.current + own_spend
               + (comp["top_flow"] if g("passive_flow") else flow_top_proj)
               + (comp["top_response_spend"] + comp["top_other_initiation_spend"]
                  if g("intervening_stamina") else 0))
        bottom = (state.bottom.current
                  + (comp["bottom_flow"] if g("passive_flow") else flow_bot_proj)
                  + (comp["bottom_builder_response_spend"] if g("builder_settlement") else 0)
                  + (comp["bottom_initiation_spend"] + comp["bottom_other_response_spend"]
                     if g("intervening_stamina") else 0))
        axis_move = ((comp["axis_builder"] if g("builder_axis")
                      else float(r * frozen.axis_realized))
                     + (comp["axis_drift"] if g("drift") else 0.0)
                     + (comp["axis_bottom_initiation"] + comp["axis_top_other"]
                        if g("intervening_axis") else 0.0)
                     + (comp["axis_stalling"] if g("stalling_axis") else 0.0))
        if g("path"):
            # Actual latches, band hysteresis and behaviors at use.
            # Clamped like moved_to (a no-op when every group is actual).
            top_pool = te.Pool(max(0, min(state.top.maximum, top)),
                               use_snap["top_latched"], state.top.maximum)
            bottom_pool = te.Pool(max(0, min(state.bottom.maximum, bottom)),
                                  use_snap["bottom_latched"], state.bottom.maximum)
            axis = match.engine.rules.clamp_axis(round(state.axis + axis_move, 10))
            band = use_state.band
            behaviors = dict(top_behavior=use_state.top_behavior,
                             bottom_behavior=use_state.bottom_behavior,
                             stage=use_state.stage)
        else:
            top_pool = state.top.moved_to(top)
            bottom_pool = state.bottom.moved_to(bottom)
            axis = match.engine.rules.clamp_axis(state.axis + axis_move)
            band, _ = match.engine.rules.update_band(axis, state.band)
            behaviors = {}
        projected = replace(state, axis=axis, band=band, top=top_pool, bottom=bottom_pool,
                            ready=state.ready | {target}, **behaviors)
        uses = _use_values(match, model, projected, target, top_pool)
        use_value = max((v for _, v in uses), default=te.ZERO)
        chain = frozen.setup_advance ** r
        return dict(top=top_pool, bottom=bottom_pool, axis=axis, band=band,
                    use_values=uses, use_value=use_value, setup_future=chain * use_value,
                    projected=projected)

    out = dict(r=r, delta=delta, frozen={c: rows[c][1] for c in te.COMMITMENTS})
    variants = {name: frozenset(groups) for name, groups in LAYERS}
    for group in GROUPS:
        variants[f"only:{group}"] = frozenset((group,))
        variants[f"without:{group}"] = frozenset(GROUPS) - {group}
    for name, groups in COMPOSITES.items():
        variants[f"composite:{name}"] = frozenset(groups)
    for name, groups in variants.items():
        out[name] = {c: project(groups, c) for c in rows}
    return out


def iv_cost(match: MountMatch, effective) -> int:
    return te._cost(match, effective)


# ---------------------------------------------------------------------------
# Per-surface analysis
# ---------------------------------------------------------------------------


def _dedup(match: MountMatch, state: te.State) -> tuple:
    """Stage 1A section 2.3 duplicate drop (requests funding identically)."""
    seen, kept = set(), []
    for c in te.COMMITMENTS:
        effective = te.funded(match, c, state.top.current)
        if effective not in seen:
            seen.add(effective)
            kept.append(c)
    return tuple(kept)


def _stats(values) -> dict:
    values = list(values)
    if not values:
        return dict(n=0)
    s = sorted(values)
    return dict(n=len(s), mean=round(mean(s), 4), median=median(s),
                p10=s[len(s) // 10], p90=s[min(len(s) - 1, 9 * len(s) // 10)],
                min=s[0], max=s[-1])


def _share(hits: int, n: int) -> dict:
    return dict(positive=hits, n=n, share=round(hits / n, 4) if n else None)


def analyse_surface(name: str, kwargs: dict, frozen_records: dict) -> dict:
    model = stage1a.model_for(kwargs)
    reference = run_escape_first_batch(**kwargs)
    _, ref_signatures, ref_trace = stage1a.baseline_reference(**kwargs)
    summary, signatures, ops, matches, trace = record_batch(**kwargs)
    ident = identity(ops, frozen_records["per_match"])
    integrity = dict(
        identity_with_stage1a_records=ident,
        summary_identical_to_uninstrumented=summary == reference,
        gameplay_signatures_identical=signatures == ref_signatures,
        rng_sequence_identical=(trace.baseline_digest == ref_trace.baseline_digest
                                and trace.baseline_draws == ref_trace.baseline_draws),
        recorder_rng_draws=sum(trace.evaluator_draws.values()),
    )

    frozen_rows = frozen_records["builder_decisions"]
    all_iv = [iv for m, match_ops in enumerate(ops) for iv in intervals(match_ops, m)]
    all_iv.sort(key=lambda iv: (iv.match, iv.decision["t"]))
    if len(all_iv) != len(frozen_rows):
        raise RuntimeError("builder decision count differs from Stage 1A")

    p0_exact = closure_exact = use_state_exact = 0
    per_variant = Counter()
    per_variant_nonconverted = Counter()
    decomposition_rows = []
    population = nonconverted = unused = 0
    errors = {k: [] for k in ("top", "bottom", "axis", "elapsed_extra")}
    comps = {k: [] for k in (*STAMINA_COMPONENTS, *AXIS_COMPONENTS)}
    windows = Counter()
    band_confusion = Counter()
    bottom_latch = Counter()
    zero_class = Counter()
    for iv, frozen in zip(all_iv, frozen_rows, strict=True):
        if (frozen["match"], frozen["t"], frozen["action"]) != (
                iv.match, iv.decision["t"], iv.decision["action"]):
            raise RuntimeError("builder decision order differs from Stage 1A")
        if frozen["chain_converted"] != iv.converted:
            raise RuntimeError("chain assignment differs from Stage 1A")
        if iv.use is None:
            unused += 1
            continue
        match = matches[iv.match]
        parts = decompose(iv)
        lay = layered(match, model, iv, parts)
        state = iv.decision["state"]
        kept = _dedup(match, state)

        # P0 reproduces the committed Stage 1A projection exactly.
        ok = all(stage1a._projection(lay["frozen"][c].projection) == frozen["projections"][c.value]
                 for c in kept)
        ok &= all(lay["P0"][c]["setup_future"] == lay["frozen"][c].setup_future for c in kept)
        p0_exact += ok

        # P6 equals the realized use state exactly (stamina, latches, axis, band).
        use = iv.use["before"]
        p6 = lay["P6"][kept[0]]
        closed = (p6["top"].current == use["top"] and p6["bottom"].current == use["bottom"]
                  and p6["top"].latched == use["top_latched"]
                  and p6["bottom"].latched == use["bottom_latched"]
                  and abs(p6["axis"] - use["axis"]) < 1e-9 and p6["band"] is use["band"])
        closure_exact += closed
        direct = _use_values(match, model, iv.use["state"], TOP_AMERICANA_ARM_ISOLATION,
                             iv.use["state"].top)
        use_state_exact += max((v for _, v in direct), default=te.ZERO) == p6["use_value"]

        def positive(variant):
            return max(lay[variant][c]["setup_future"] for c in kept) > 0

        variant_names = [k for k in lay if k not in ("r", "delta", "frozen")]
        if iv.converted:
            population += 1
            for v in variant_names:
                per_variant[v] += positive(v)
            p0 = lay["P0"]
            if not positive("P0"):
                strong = any(p0[c]["band"].value in ("Strong", "Locked") for c in kept)
                zero_class["loose_stable" if not strong else "strong_locked_bottom_not_exhausted"
                           if not any(p0[c]["bottom"].latched for c in kept) else "other"] += 1
            # Use-state error of the frozen projection at the baseline's commitment.
            p = lay["P0"][_baseline_commitment(iv, kept)]
            errors["top"].append(p["top"].current - use["top"])
            errors["bottom"].append(p["bottom"].current - use["bottom"])
            errors["axis"].append(round(p["axis"] - use["axis"], 10))
            errors["elapsed_extra"].append(use["t"] - state_t(iv) - lay["delta"])
            for k in comps:
                comps[k].append(round(parts["components"].get(k, 0), 10))
            windows.update(parts["windows"])
            windows["intervals"] += 1
            band_confusion[f"{p['band'].value}->{use['band'].value}"] += 1
            bottom_latch[f"{'E' if p['bottom'].latched else 'notE'}->"
                         f"{'E' if use['bottom_latched'] else 'notE'}"] += 1
            decomposition_rows.append(dict(
                match=iv.match, t=state_t(iv), use_t=use["t"], r=lay["r"],
                components={k: round(v, 10) for k, v in parts["components"].items()},
                windows=parts["windows"],
                projected_P0=dict(top=p["top"].current, bottom=p["bottom"].current,
                                  bottom_latched=p["bottom"].latched,
                                  axis=p["axis"], band=p["band"].value),
                actual=dict(top=use["top"], bottom=use["bottom"],
                            bottom_latched=use["bottom_latched"],
                            axis=use["axis"], band=use["band"].value),
                positive={v: positive(v) for v in variant_names},
            ))
        else:
            nonconverted += 1
            for v in variant_names:
                per_variant_nonconverted[v] += positive(v)

    used = len(all_iv) - unused
    return dict(
        use_value_drain_sensitivity=drain_sensitivity(matches, model, all_iv),
        integrity=dict(**integrity,
                       p0_reproduces_stage1a_projection=_share(p0_exact, used),
                       p6_equals_realized_use_state=_share(closure_exact, used),
                       p6_use_value_equals_direct_valuation=_share(use_state_exact, used)),
        builder_decisions=len(all_iv), chains_never_used=unused,
        converted_population=population, nonconverted_used=nonconverted,
        setup_future_positive_converted={v: _share(per_variant[v], population)
                                         for v in sorted(per_variant)} if population else {},
        setup_future_positive_nonconverted={v: _share(per_variant_nonconverted[v], nonconverted)
                                            for v in sorted(per_variant_nonconverted)},
        p0_zero_classes=dict(zero_class),
        p0_use_state_error=dict(
            top_stamina=_stats(errors["top"]), bottom_stamina=_stats(errors["bottom"]),
            axis=_stats(errors["axis"]), elapsed_extra_seconds=_stats(errors["elapsed_extra"]),
            band_projected_to_actual=dict(band_confusion),
            bottom_exhausted_projected_to_actual=dict(bottom_latch)),
        components_converted={k: _stats(v) for k, v in comps.items()},
        windows_converted=dict(windows),
        rows=decomposition_rows,
    )


def drain_sensitivity(matches, model, all_iv) -> dict:
    """Reported: how the use value at the realized use state responds to drain
    errors. (a) realized; (b) Bottom over-drained (Exhausted at 0); (c) Top
    under-drained (Top at its decision-time stamina and latch)."""
    hits = Counter()
    n = 0
    for iv in all_iv:
        if iv.use is None:
            continue
        n += 1
        match, use = matches[iv.match], iv.use["state"]
        start = iv.decision["state"]
        for label, state in (
                ("realized", use),
                ("bottom_over_drained", replace(use, bottom=te.Pool(0, True, use.bottom.maximum))),
                ("top_under_drained", replace(use, top=start.top)),
                ("both", replace(use, bottom=te.Pool(0, True, use.bottom.maximum), top=start.top))):
            values = _use_values(match, model, state, TOP_AMERICANA_ARM_ISOLATION, state.top)
            hits[label] += max((v for _, v in values), default=te.ZERO) > 0
    return {k: _share(hits[k], n) for k in ("realized", "bottom_over_drained",
                                            "top_under_drained", "both")}


def state_t(iv: Interval) -> int:
    return iv.decision["t"]


def _baseline_commitment(iv: Interval, kept: tuple):
    """The baseline's actual builder commitment (its first op is that attempt)."""
    requested = iv.ops[0]["requested"] if iv.ops and iv.ops[0]["kind"] == "attempt" else None
    for c in kept:
        if c.value == requested:
            return c
    return kept[-1]


def measure(names=None) -> tuple[dict, dict]:
    all_surfaces = stage1a.surfaces()
    with gzip.open(STAGE1A_RECORDS) as handle:
        frozen = json.load(handle)
    out, rows = {}, {}
    for name in (names or all_surfaces):
        result = analyse_surface(name, all_surfaces[name], frozen[name])
        rows[name] = result.pop("rows")
        out[name] = result
    integrity = all(
        v["integrity"]["identity_with_stage1a_records"]["exact"]
        and v["integrity"]["summary_identical_to_uninstrumented"]
        and v["integrity"]["gameplay_signatures_identical"]
        and v["integrity"]["rng_sequence_identical"]
        and v["integrity"]["recorder_rng_draws"] == 0
        and v["integrity"]["p0_reproduces_stage1a_projection"]["share"] in (1.0, None)
        and v["integrity"]["p6_equals_realized_use_state"]["share"] in (1.0, None)
        and v["integrity"]["p6_use_value_equals_direct_valuation"]["share"] in (1.0, None)
        for v in out.values())
    return dict(stage1a_head=STAGE1A_HEAD, preregistration=stage1a.PREREGISTRATION,
                integrity_ok=integrity, surfaces=out), rows


def main() -> None:
    summary, _ = measure()
    SUMMARY_EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_EVIDENCE.write_text(json.dumps(summary, indent=1, sort_keys=True, default=str) + "\n")
    print(SUMMARY_EVIDENCE)
    print("integrity:", summary["integrity_ok"])


if __name__ == "__main__":
    main()
