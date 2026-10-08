"""TE-2 measurement driver and CLI (docs/TACTICAL_EVALUATOR_TE2_PREREGISTRATION.md,
binding at 218f1c0ab94d6999abd06157876f48704e8ba6e1; implementation 8cfff50).

Two modes:

- preflight: synthetic surfaces only (each a shortened copy of a gated or
  fresh-holdout surface, at seeds >= 910000). It exercises the whole
  measurement stack: lock, ESCAPE_FIRST baselines first, then one TACTICAL_V2
  surface process at a time (candidate, second run, inertness replay,
  uninstrumented run), budgets, scoring of P/G/HG-shaped results, and the
  evidence and report files. Its verdict is labelled PREFLIGHT and is not a
  design verdict. A hard guard refuses any reserved seed (42, 142, 4242, 4342,
  685800, 23316 and the other used base seeds) and any authoritative surface.
- authoritative: the one-time TE-2 measurement. LOCKED in this slice:
  AUTHORITATIVE_AUTHORIZED is False and the mode refuses to run.

Observation reuses the Stage 1B instruments (diagnostics/tactical_evaluator_
stage1b.py: Observation, the real-match routers, outcome rows, P3, scoring,
G1-G6); the policy is observed through a TacticalV2Policy subclass that
delegates every decision unchanged.
"""
from __future__ import annotations

from collections import Counter
from contextlib import ExitStack
from fractions import Fraction
import gzip
import json
import math
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

from ..domain.action import Commitment
from ..domain.model import Side
from ..engine.match import MountMatch
from ..interfaces import batch as batch_module
from ..interfaces import tactical_evaluator as te
from ..interfaces import tactical_policy as tp
from ..interfaces import tactical_policy_v2 as tp2
from ..interfaces import tactical_projection_v2 as v2
from ..interfaces import tactical_route as route
from ..interfaces.batch import BatchInitiatorPolicy, run_batch
from ..interfaces.handoff_policy import D3BTokenLockoutController
from . import late_recovery
from . import tactical_evaluator as stage1a
from . import tactical_evaluator_stage1b as s1b
from .d3b_promotion import canonical_kwargs

PREREGISTRATION = route.PREREGISTRATION
IMPLEMENTATION = "8cfff503b94e6ecb11ed28e443f9aed9b4fefc59"
AUTHORITATIVE_AUTHORIZED = False      # changed only by a separately authorized commit

V2 = BatchInitiatorPolicy.TACTICAL_V2
V1 = BatchInitiatorPolicy.TACTICAL_V1
EF = BatchInitiatorPolicy.ESCAPE_FIRST

H1, H2 = 685800, 23316
FRESH_HOLDOUT_SEEDS = (H1, H2)
RESERVED_BASE_SEEDS = (0, 7, 42, 142, 4242, 4342, H1, H2)
SYNTHETIC_MIN_SEED = 910_000
PREFLIGHT_MAX_MATCHES = 10
SURFACE_WALL_SECONDS = 48 * 3600
AUTHORITATIVE_SUMMARY = Path("docs/evidence/tactical_evaluator_te2.json")
AUTHORITATIVE_RECORDS = Path("docs/evidence/tactical_evaluator_te2_records.json.gz")

GATED = s1b.GATED_SURFACES
HOLDOUTS = ("A-PROD-H", "B-PROD-H", "E-PROD-H1 OFF", "E-PROD-H1 ON",
            "E-PROD-H2 OFF", "E-PROD-H2 ON", "PROTECT-H")
ROLES = (*GATED, *HOLDOUTS)
E_HOLDOUTS = HOLDOUTS[2:6]
PREFIX = "PREFLIGHT "


class PreflightRefused(RuntimeError):
    """The preflight guard refused a surface (reserved seed or authoritative)."""


class AuthoritativeLocked(RuntimeError):
    """The authoritative TE-2 measurement is not authorized in this slice."""


# ---------------------------------------------------------------------------
# Surfaces
# ---------------------------------------------------------------------------


def authoritative_surfaces() -> dict:
    """Gated (Stage 1B, frozen) and fresh-holdout surfaces (section 7). Defined
    for the guard and for the future authoritative run; never run here."""
    gated = stage1a.surfaces()
    out = dict(gated)
    out["A-PROD-H"] = {**gated["A-PROD"], "base_seed": H1}
    out["B-PROD-H"] = {**gated["B-PROD"], "base_seed": H1}
    for label, seed in (("H1", H1), ("H2", H2)):
        for mode in ("OFF", "ON"):
            out[f"E-PROD-{label} {mode}"] = canonical_kwargs(seed, mode)
    out["PROTECT-H"] = {**gated["PROTECT probe"], "base_seed": H1}
    return out


def preflight_surfaces(*, matches: int = 1, clock: int = 60) -> dict:
    """Synthetic shortened copies of every role (seeds >= 910000). The PROTECT
    roles run with v0.4a on: the v0.4a-off envelope is admitted only at the
    frozen seeds (T7), so a synthetic PROTECT probe cannot be run as is."""
    auth = authoritative_surfaces()
    out = {}
    for k, role in enumerate(ROLES):
        kwargs = {**auth[role], "base_seed": SYNTHETIC_MIN_SEED + 500 + 10 * k,
                  "matches": matches, "initial_clock": clock}
        if role in ("PROTECT probe", "PROTECT-H"):
            kwargs["enable_v04_commitment_semantics"] = True
        out[PREFIX + role] = kwargs
    return out


def _ranges_overlap(a: int, a_len: int, b: int, b_len: int) -> bool:
    return not (a + a_len - 1 < b or b + b_len - 1 < a)


def assert_preflight_safe(surfaces: dict) -> None:
    """Hard guard: refuse any reserved seed range, any authoritative surface,
    any non-preflight name and any long synthetic surface."""
    auth = list(authoritative_surfaces().values())
    for name, kwargs in surfaces.items():
        if not name.startswith(PREFIX) or name[len(PREFIX):] not in ROLES:
            raise PreflightRefused(f"{name!r} is not a preflight surface")
        seed, matches = kwargs["base_seed"], kwargs["matches"]
        if seed < SYNTHETIC_MIN_SEED:
            raise PreflightRefused(f"{name!r}: base_seed {seed} below {SYNTHETIC_MIN_SEED}")
        for reserved in RESERVED_BASE_SEEDS:
            if _ranges_overlap(seed, matches, reserved, 100):
                raise PreflightRefused(f"{name!r}: overlaps reserved seed {reserved}")
        if matches > PREFLIGHT_MAX_MATCHES:
            raise PreflightRefused(f"{name!r}: {matches} matches (max {PREFLIGHT_MAX_MATCHES})")
        if any(kwargs == a for a in auth):
            raise PreflightRefused(f"{name!r} equals an authoritative surface")


def role_of(name: str) -> str:
    return name[len(PREFIX):] if name.startswith(PREFIX) else name


# ---------------------------------------------------------------------------
# Observation (TACTICAL_V2)
# ---------------------------------------------------------------------------


def _label_q(q_pairs) -> dict:
    return {label: Fraction(x) for label, x in q_pairs}


def top_rule_violation(tier: str, values, chosen, record) -> str | None:
    """P5 and the Tier R rules at a Top decision, re-derived independently."""
    if tier in ("terminal", "progress", "position"):
        return s1b.guard_violation(values, te.ShadowChoice(tier, chosen))
    if tier != "route":
        return None
    q = _label_q(record.q)
    reset = q["RESET"]
    labels = {(v.action_id, v.requested): f"{v.action_id}|{v.requested.value}" for v in values}
    admissible = []
    for v in values:
        if v.enters_exhausted:
            others = [o for o in values if o.action_id == v.action_id and not o.enters_exhausted]
            if not all(q[labels[(v.action_id, v.requested)]] > q[labels[(o.action_id, o.requested)]]
                       for o in others):
                continue
        admissible.append(v)
    best = max((q[labels[(v.action_id, v.requested)]] for v in admissible), default=Fraction(0))
    if chosen is None:
        return None if reset > best else "R_reset_without_strict_advantage"
    if reset > best:
        return "R_action_against_stronger_reset"
    if chosen not in admissible:
        return "R_guard_on_Q"
    if q[labels[(chosen.action_id, chosen.requested)]] != best:
        return "R_not_best_Q"
    return None


def _immediate_values(match, model, state, allowed):
    out = []
    for action_id in match.legal_action_ids(Side.TOP):
        seen = set()
        for c in allowed:
            effective = te.funded(match, c, state.top.current)
            if effective in seen:
                continue
            seen.add(effective)
            out.append(te.evaluate(match, model, state, action_id, c, project=False))
    return out


def _observed_v2_class(obs):
    class Observed(tp2.TacticalV2Policy):
        def choose(self, match, *, handoff_decision, executed):
            capture = obs.capture
            capture.values = capture.choice = None
            records_before = len(self.route_records)
            started = time.perf_counter()
            obs.trace.active = True
            try:
                selection = super().choose(match, handoff_decision=handoff_decision,
                                           executed=executed)
            finally:
                obs.trace.active = False
            elapsed = time.perf_counter() - started
            entry = self._tape[-1]
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
                top_band=match.top.stamina.band.value,
                bottom_band=match.bottom.stamina.band.value)
            obs.trace.active = True
            try:
                if side is Side.BOTTOM:
                    values, choice = capture.values, capture.choice
                    if values is None or choice is None or choice.tier != entry.tier:
                        raise RuntimeError("observer capture does not match the taped call")
                    violation = s1b.guard_violation(values, choice)
                    chosen = choice.value
                    if choice.tier == "setup":
                        position = [v for v in values if v.axis_raw > 0 and v.axis_realized > 0]
                        best = max((v.axis_realized for v in position), default=None)
                        record["forgone_better_position"] = (
                            best is not None and best > chosen.axis_realized)
                else:
                    if len(self.route_records) != records_before + 1:
                        raise RuntimeError("Top decision without its route record")
                    rr = self.route_records[-1]
                    values = _immediate_values(match, self.context.model, entry.branch.state,
                                               entry.allowed)
                    chosen = next((v for v in values if (v.action_id, v.requested)
                                   == (entry.decision.action_id, entry.requested)), None)
                    violation = top_rule_violation(entry.tier, values, chosen, rr)
                    record["route"] = dict(tier=rr.tier, q=dict(rr.q), chosen=rr.chosen,
                                           nodes=rr.nodes)
                    obs.route_timing.append((rr.nodes, elapsed))
                    rss = route.rss_bytes()
                    if rss is not None:
                        obs.peak_rss = max(obs.peak_rss, rss)
                obs.p5["checked"] += 1
                if violation is not None:
                    obs.p5[violation] += 1
                record["p5_violation"] = violation
                if chosen is not None:
                    record["chosen"] = s1b._value_row(chosen)
                if executed:
                    before = obs.pre_decide.pop(id(match), entry.branch)
                    s_kind, s_action, s_requested, _ = (
                        self._route.opponent_contract.opponent_decision(before))
                    same = s_action == entry.decision.action_id and s_kind is kind
                    full = same and s_requested == (
                        entry.requested if entry.decision.action_id is not None else None)
                    key = f"{side.value}:{entry.tier}"
                    obs.o3[f"{key}:checked"] += 1
                    obs.o3[f"{key}:action_exact"] += same
                    obs.o3[f"{key}:action_commitment_exact"] += full
                    obs.pending[id(match)] = record
                else:
                    obs.pre_decide.pop(id(match), None)
            finally:
                obs.trace.active = False
            obs.bottom_route_searches += self._route.searches_by_side[Side.BOTTOM]
            obs.timelines[obs.index_of[id(match)]].append(record)
            return selection

    return Observed


def observe_v2(kwargs: dict, *, policy: BatchInitiatorPolicy, tape=None, late: bool = False,
               budget: route.RouteBudget | None = None):
    """One run. ESCAPE_FIRST: baseline. TACTICAL_V2 with tape None: observed
    candidate. TACTICAL_V2 with a tape: inertness replay (no evaluation)."""
    evaluate = policy is V2 and tape is None
    obs = s1b.Observation(evaluate=evaluate)
    obs.route_timing, obs.peak_rss, obs.bottom_route_searches = [], 0, 0
    context = v2.Context.from_batch_kwargs({**kwargs, "initiator_policy": V1})
    original_create = tp2.create_policy
    original_decide = D3BTokenLockoutController.decide
    observed_class = _observed_v2_class(obs)

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
        ctx = v2.Context.from_batch_kwargs({**settings, "initiator_policy": V1})
        obs.policy = observed_class(ctx)
        if budget is not None:
            obs.policy.budget = budget
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
        inner = {name: getattr(MountMatch, name) for name in s1b._ROUTED}
        routers = s1b._routers(obs, context, inner)
        with ExitStack() as stack:
            for name, fn in routers.items():
                stack.enter_context(patch.object(MountMatch, name, fn))
            if tape is not None:
                stack.enter_context(tp2.replaying(tape))
            obs.batch_run = run_batch(initiator_policy=policy, **run_kwargs)
        return obs.batch_run.summary

    with ExitStack() as stack:
        stack.enter_context(stage1a.count_rng(obs.trace))
        stack.enter_context(patch.object(batch_module, "MountMatch", factory))
        stack.enter_context(patch.object(tp2, "create_policy", create_policy))
        stack.enter_context(patch.object(D3BTokenLockoutController, "decide", decide))
        stack.enter_context(patch.object(v2, "candidates", obs.capture.candidates(v2.candidates)))
        stack.enter_context(patch.object(te, "choose_te1", obs.capture.choose_te1(te.choose_te1)))
        if late:
            if not kwargs.get("measure_stamina_economy"):
                raise RuntimeError("late-recovery observer would change the surface")
            stack.enter_context(patch.object(late_recovery, "run_escape_first_batch", run))
            summary, timelines = late_recovery.observe_batch(**kwargs)
            characterization = late_recovery.characterize(summary, timelines)
        else:
            run(**kwargs)
            characterization = None
    if (tp2.create_policy is not original_create
            or D3BTokenLockoutController.decide is not original_decide
            or batch_module.MountMatch is not MountMatch
            or any(getattr(MountMatch, n) is not s1b._TRUE[n] for n in s1b._ROUTED)):
        raise RuntimeError("observer wrappers not restored")
    return obs, characterization


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def ceil_80(x: int) -> int:
    """⌈0.8·x⌉ exactly."""
    return -(-4 * x // 5)


def floor_50(x: int) -> int:
    """⌊0.5·x⌋ exactly."""
    return x // 2


def route_report(obs, timelines) -> dict:
    decisions = [e for events in timelines for e in events
                 if e["kind"] == "decision" and e["executed"] and e["side"] == "top"]
    tiers, types, commitments = Counter(), Counter(), Counter()
    q_chosen, empty, reset_won = [], 0, 0
    for d in decisions:
        tiers[d["tier"]] += 1
        r = d.get("route")
        if r is None:
            continue
        if r["q"] and r["tier"] != "route":
            empty += 1
        if r["tier"] == "route":
            if d["action"] is None:
                reset_won += 1
                types["RESET"] += 1
                q_chosen.append(Fraction(r["q"]["RESET"]))
            else:
                types["builder" if d["reason"] == "setup" else "other action"] += 1
                commitments[d["requested"]] += 1
                q_chosen.append(Fraction(r["q"][f"{d['action']}|{d['requested']}"]))
    # Calibration: ΣQ at Tier-R choices vs realized Threat entry within the
    # next 13 windows (executed decisions and holds), reported only.
    pairs = []
    for events in timelines:
        windows = [i for i, e in enumerate(events)
                   if (e["kind"] == "decision" and e["executed"]) or e["kind"] == "hold"]
        for k, i in enumerate(windows):
            d = events[i]
            if d["kind"] != "decision" or d["side"] != "top" or d["tier"] != "route":
                continue
            label = "RESET" if d["action"] is None else f"{d['action']}|{d['requested']}"
            q = Fraction(d["route"]["q"][label])
            end = windows[k + 13] if k + 13 < len(windows) else len(events)
            hit = any(e["kind"] == "attempt" and e["threat_entry"] for e in events[i:end])
            pairs.append((q, hit))
    nodes = [n for n, _ in obs.route_timing]
    walls = [w for _, w in obs.route_timing]
    return dict(
        top_tiers=dict(tiers), tier_r_choice_types=dict(types),
        tier_r_commitments=dict(commitments), tier_r_empty=empty, reset_won_tier_r=reset_won,
        q_at_choices=dict(n=len(q_chosen),
                          mean=float(sum(q_chosen, Fraction(0)) / len(q_chosen)) if q_chosen else None,
                          min=float(min(q_chosen)) if q_chosen else None,
                          max=float(max(q_chosen)) if q_chosen else None),
        calibration_q_13_windows=stage1a.calibration(pairs),
        nodes_per_decision=dict(n=len(nodes), max=max(nodes, default=0),
                                mean=(sum(nodes) / len(nodes)) if nodes else None))


def stalling_report(obs) -> dict:
    out = Counter()
    for m in obs.created:
        for attr, label in (("stalling_warning_history", "warning"),
                            ("stalling_penalty_history", "penalty"),
                            ("stalling_position_reset_history", "position_reset"),
                            ("stalling_free_initiative_history", "free_window")):
            for entry in getattr(m.history, attr):
                out[f"{entry.split('@', 1)[0]}:{label}"] += 1
    return dict(out)


def resource_report(obs) -> dict:
    walls = [w for _, w in obs.route_timing]
    return dict(route_decisions=len(walls),
                route_wall_seconds_max=round(max(walls, default=0.0), 3),
                route_wall_seconds_mean=round(sum(walls) / len(walls), 3) if walls else None,
                peak_rss_bytes=obs.peak_rss)


def g_view(results: dict) -> dict:
    """Role-keyed view of the gated roles for s1b.gates (G1-G6 formulas)."""
    return {role: results[role] for role in GATED}


def hg_gates(results: dict, baselines: dict) -> dict:
    """HG1-HG6 (section 6.2) from candidate results and the holdouts' own
    ESCAPE_FIRST baselines (recorded before the candidate runs)."""
    o = {r: results[r]["outcomes"] for r in HOLDOUTS}
    b = {r: baselines[r] for r in HOLDOUTS}
    g = {}
    pooled = {mode: (["B-PROD-H", f"E-PROD-H1 {mode}", f"E-PROD-H2 {mode}"]) for mode in ("OFF", "ON")}
    a_floor = ceil_80(b["A-PROD-H"]["threat_matches"])
    g["HG1"] = dict(a_prod=o["A-PROD-H"]["threat_matches"], a_floor=a_floor, pooled={})
    ok = o["A-PROD-H"]["threat_matches"] >= a_floor
    for mode, roles in pooled.items():
        value = sum(o[r]["threat_matches"] for r in roles)
        floor = ceil_80(sum(b[r]["threat_matches"] for r in roles))
        g["HG1"]["pooled"][mode] = dict(value=value, floor=floor)
        ok = ok and value >= floor
    g["HG1"]["status"] = "PASS" if ok else "FAIL"
    taps = {r: o[r]["tap"] for r in HOLDOUTS}
    g["HG2"] = dict(tap=taps, status="PASS" if all(t <= 20 for t in taps.values()) else "FAIL")
    g["HG3"] = dict(pooled={})
    ok = True
    for mode in ("OFF", "ON"):
        roles = [f"E-PROD-H1 {mode}", f"E-PROD-H2 {mode}"]
        value = sum(o[r]["escapes"] for r in roles)
        floor = ceil_80(sum(b[r]["escapes"] for r in roles))
        g["HG3"]["pooled"][mode] = dict(value=value, floor=floor)
        ok = ok and value >= floor
    b_floor = ceil_80(b["B-PROD-H"]["escapes"])
    g["HG3"].update(b_prod=o["B-PROD-H"]["escapes"], b_floor=b_floor)
    g["HG3"]["status"] = "PASS" if ok and o["B-PROD-H"]["escapes"] >= b_floor else "FAIL"
    cap = floor_50(b["PROTECT-H"]["top_completed_builder_attempts"])
    value = o["PROTECT-H"]["top_completed_builder_attempts"]
    g["HG4"] = dict(value=value, cap=cap, status="PASS" if value <= cap else "FAIL")
    runs = {}
    for r in E_HOLDOUTS:
        median = results[r]["summary"]["bottom_first_exhausted_time_median"]
        share = results[r]["bottom_exhausted_share_exact"]
        runs[r] = dict(first_exhausted_median=median,
                       median_ok=median is not None and median >= 50,
                       share_ok=5 * share["exhausted_seconds"] <= 4 * share["match_seconds"])
    g["HG5"] = dict(runs=runs, status="PASS" if all(x["median_ok"] and x["share_ok"]
                                                    for x in runs.values()) else "FAIL")
    modes = {}
    for mode in ("OFF", "ON"):
        a, c = results[f"E-PROD-H1 {mode}"]["g6"], results[f"E-PROD-H2 {mode}"]["g6"]
        chosen, high = a["te1_chosen"] + c["te1_chosen"], a["high"] + c["high"]
        modes[mode] = dict(policy_chosen=chosen, high=high, ok=chosen > 0 and 2 * high <= chosen)
    g["HG6"] = dict(modes=modes, status="PASS" if all(m["ok"] for m in modes.values()) else "FAIL")
    return g


def integrity_ok(v: dict, *, gated: bool, authoritative: bool) -> bool:
    if v.get("status") == "OPEN":
        return False
    i = v["integrity"]
    ok = (i["evaluator_rng_draws"] == 0 and i["p3_ok"] and i["p5_ok"]
          and i["bottom_route_searches"] == 0
          and i["historical_counter_le_reason_independent"]
          and i["p4b_second_run_identical"] is True and i["p4c_replay_identical"] is True
          and i["uninstrumented_identical"] is True)
    b = v["baseline"]
    if gated:
        ok = ok and b["g4_equivalence"] and (b["exact"] if authoritative else True)
    return ok


def verdict(results: dict, baselines: dict, *, authoritative: bool) -> dict:
    label = (lambda x: x) if authoritative else (
        lambda x: f"PREFLIGHT {x} (synthetic; not a design verdict)")
    open_roles = [r for r in ROLES if results[r].get("status") != "OK"]
    if open_roles:
        # A surface without valid evidence (budget, infeasible cost): OPEN.
        # Gates are not scored on partial evidence.
        return dict(integrity_ok=False, open_surfaces={
            r: results[r].get("open_reason") for r in open_roles}, te2=label("OPEN"))
    integrity = all(integrity_ok(results[r], gated=r in GATED, authoritative=authoritative)
                    for r in ROLES)
    preservation = dict(
        P1=dict(status="CI"),
        P2=dict(status="PASS" if not _protected_diff() else "FAIL",
                protected_paths_changed=_protected_diff()),
        P3=dict(status="PASS" if all(results[r]["integrity"]["p3_ok"]
                                     and results[r]["integrity"]["bottom_route_searches"] == 0
                                     for r in GATED) else "FAIL"),
        P4=dict(status="PASS" if all(
            results[r]["integrity"]["evaluator_rng_draws"] == 0
            and results[r]["integrity"]["p4b_second_run_identical"] is True
            and results[r]["integrity"]["p4c_replay_identical"] is True
            and results[r]["integrity"]["uninstrumented_identical"] is True
            for r in GATED) else "FAIL"),
        P5=dict(status="PASS" if all(results[r]["integrity"]["p5_ok"] for r in GATED) else "FAIL"),
        P6=dict(status="CI"))
    design = s1b.gates(g_view(results))
    holdout = hg_gates(results, baselines)
    statuses = ([g["status"] for g in design.values()] + [g["status"] for g in holdout.values()]
                + [p["status"] for p in preservation.values()])
    if not integrity:
        overall = "OPEN"
    elif "FAIL" in statuses:
        overall = "FAIL"
    else:
        overall = "PASS (subject to P1 and P6 on exact-head CI)"
    return dict(integrity_ok=integrity, preservation=preservation, design_gates=design,
                holdout_gates=holdout, te2=label(overall))


def _protected_diff() -> list:
    out = subprocess.run(["git", "diff", "--name-only", PREREGISTRATION, "--",
                          *s1b.PROTECTED_PATHS], capture_output=True, text=True)
    return [line for line in out.stdout.splitlines() if line]


# ---------------------------------------------------------------------------
# One surface (worker)
# ---------------------------------------------------------------------------


def baseline_row(kwargs: dict) -> dict:
    run = run_batch(initiator_policy=EF, **kwargs)
    return s1b.outcome_row(run.summary, run.top_completed_setup_builder_attempt_count)


def measure_candidate(role: str, kwargs: dict, baseline: dict, *, authoritative: bool,
                      budget: route.RouteBudget | None = None) -> tuple[dict, dict]:
    """Candidate, second run, inertness replay and uninstrumented run of one
    surface, in this process. A budget overflow returns status OPEN."""
    late = role.startswith("E-PROD")
    started = time.monotonic()
    out = dict(role=role, gated=role in GATED)
    frozen = list(s1b.FROZEN_BASELINES[role]) if role in GATED else None
    observed = [baseline[k] for k in s1b.BASELINE_FIELDS]
    out["baseline"] = dict(
        fields=list(s1b.BASELINE_FIELDS), observed=observed,
        reason_independent_builder_attempts=baseline["top_completed_builder_attempts"],
        g4_equivalence=(baseline["top_completed_builder_attempts"]
                        == baseline["top_completed_builds"]),
        frozen=frozen if authoritative else None,
        exact=(observed == frozen) if (authoritative and frozen) else None)
    try:
        cand, late_char = observe_v2(kwargs, policy=V2, late=late, budget=budget)
        result, records = s1b.score_candidate(role, cand, late_char)
        out.update(result)
        run = cand.batch_run
        p3 = s1b._p3(cand, run)
        integrity = dict(
            evaluator_rng_draws=sum(cand.trace.evaluator_draws.values()),
            p3=p3, p3_ok=s1b._p3_ok(p3), p5=dict(cand.p5),
            p5_ok=set(cand.p5) <= {"checked"},
            bottom_route_searches=cand.bottom_route_searches,
            tape_entries=len(run.tactical.tape),
            historical_counter_le_reason_independent=(
                run.summary.top_completed_setup_build_count
                <= run.top_completed_setup_builder_attempt_count))
        second, _ = observe_v2(kwargs, policy=V2, late=late, budget=budget)
        integrity["p4b_second_run_identical"] = (
            second.batch_run.summary == run.summary
            and s1b._signatures(second) == s1b._signatures(cand)
            and second.batch_run.tactical == run.tactical
            and s1b._comparable(second.timelines) == s1b._comparable(cand.timelines)
            and second.trace.baseline_digest == cand.trace.baseline_digest
            and sum(second.trace.evaluator_draws.values()) == 0)
        try:
            replay, _ = observe_v2(kwargs, policy=V2, tape=run.tactical.tape)
        except tp.ReplayDesync as error:
            integrity["p4c_replay_identical"] = False
            integrity["p4c_replay_error"] = error.code
        else:
            integrity["p4c_replay_identical"] = (
                replay.batch_run.summary == run.summary
                and s1b._signatures(replay) == s1b._signatures(cand)
                and replay.batch_run.tactical == run.tactical
                and replay.trace.baseline_digest == cand.trace.baseline_digest
                and replay.trace.baseline_draws == cand.trace.baseline_draws)
        with patch.object(tp2.TacticalV2Policy, "budget",
                          budget if budget is not None else tp2.TacticalV2Policy.budget):
            plain = run_batch(initiator_policy=V2, **kwargs)
        integrity["uninstrumented_identical"] = (
            plain.summary == run.summary and plain.tactical == run.tactical
            and plain.top_completed_setup_builder_attempt_count
            == run.top_completed_setup_builder_attempt_count)
        out["integrity"] = integrity
        out["te2_route"] = route_report(cand, cand.timelines)
        out["stalling_resets"] = stalling_report(cand)
        out["resources"] = dict(resource_report(cand),
                                surface_wall_seconds=round(time.monotonic() - started, 1))
        out["status"] = "OK"
        records["route_records"] = [dict(match=r.match_index, call=r.call_index, tier=r.tier,
                                         q=dict(r.q), chosen=r.chosen, nodes=r.nodes)
                                    for r in cand.policy.route_records]
    except route.RouteBudgetExceeded as error:
        out.update(status="OPEN", open_reason=f"budget:{error.which}",
                   resources=dict(surface_wall_seconds=round(time.monotonic() - started, 1)))
        records = {}
    return out, records


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def _worker_argv(mode: str, name: str, part: Path, options: dict) -> list:
    argv = [sys.executable, "-m", "bjj_game.diagnostics.tactical_evaluator_te2", "worker",
            "--mode", mode, "--surface", name, "--part", str(part)]
    for key in ("matches", "clock", "decision_node_limit"):
        if options.get(key) is not None:
            argv += [f"--{key.replace('_', '-')}", str(options[key])]
    return argv


def run_preflight(out_dir: Path, *, matches: int = 1, clock: int = 60, only=None,
                  decision_node_limit: int | None = None) -> dict:
    """The whole stack on synthetic surfaces. Writes summary, records and a
    report into out_dir (never the authoritative evidence paths)."""
    out_dir = Path(out_dir).resolve()
    for forbidden in (AUTHORITATIVE_SUMMARY, AUTHORITATIVE_RECORDS):
        if out_dir == forbidden.parent.resolve():
            raise PreflightRefused("preflight output must not be docs/evidence")
    surfaces = preflight_surfaces(matches=matches, clock=clock)
    if only:
        surfaces = {n: k for n, k in surfaces.items() if role_of(n) in only}
    assert_preflight_safe(surfaces)
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    order: list = []
    with route.exclusive_measurement(out_dir / "te2_measurement.lock"):
        baselines = {}
        for name, kwargs in surfaces.items():
            baselines[role_of(name)] = baseline_row(kwargs)
            order.append(("baseline", role_of(name)))
        results, records = {}, {}
        options = dict(matches=matches, clock=clock, decision_node_limit=decision_node_limit)
        for name in surfaces:
            part = out_dir / f"part_{role_of(name).replace(' ', '_')}.json"
            (out_dir / "baselines.json").write_text(json.dumps(baselines, sort_keys=True),
                                                    encoding="utf-8")
            order.append(("candidate", role_of(name)))
            proc = subprocess.run(_worker_argv("preflight", name, part, options),
                                  timeout=SURFACE_WALL_SECONDS, capture_output=True, text=True)
            if proc.returncode != 0:
                raise RuntimeError(f"worker {name!r} failed:\n{proc.stderr[-4000:]}")
            payload = json.loads(part.read_text(encoding="utf-8"))
            results[role_of(name)], records[role_of(name)] = payload["result"], payload["records"]
            part.unlink()
    summary = dict(mode="preflight", preregistration=PREREGISTRATION,
                   implementation=IMPLEMENTATION, surfaces=results, baselines=baselines,
                   order=order, wall_seconds=round(time.monotonic() - started, 1))
    if set(results) == set(ROLES):
        summary["verdict"] = verdict(results, baselines, authoritative=False)
    else:
        summary["verdict"] = dict(te2="PREFLIGHT PARTIAL (subset of roles; gates not scored)")
    _write(out_dir, summary, records)
    return summary


def run_authoritative(*_args, **_kwargs):
    if not AUTHORITATIVE_AUTHORIZED:
        raise AuthoritativeLocked(
            "the authoritative TE-2 measurement is NOT AUTHORIZED in this slice")
    raise AuthoritativeLocked("authoritative mode is implemented in a later authorized slice")


def _write(out_dir: Path, summary: dict, records: dict) -> None:
    (out_dir / "tactical_evaluator_te2_summary.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True, default=str) + "\n",
        encoding="utf-8", newline="\n")
    with gzip.GzipFile(out_dir / "tactical_evaluator_te2_records.json.gz", "wb", mtime=0) as h:
        h.write(json.dumps(records, sort_keys=True, separators=(",", ":"), default=str).encode())
    (out_dir / "tactical_evaluator_te2_report.md").write_text(report(summary),
                                                              encoding="utf-8", newline="\n")


def report(summary: dict) -> str:
    v = summary["verdict"]
    lines = [f"# TE-2 measurement report ({summary['mode']})", "",
             f"Verdict: **{v.get('te2')}**", "",
             f"Preregistration `{summary['preregistration']}`, implementation "
             f"`{summary['implementation']}`, wall {summary['wall_seconds']} s.", "",
             "| Role | Status | Threat | Tap | Escapes | Timeouts | Builder attempts | "
             "Integrity | Route decisions | Max nodes | Peak RSS MB |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for role, r in summary["surfaces"].items():
        if r.get("status") != "OK":
            lines.append(f"| {role} | {r.get('status')} {r.get('open_reason', '')} |"
                         " | | | | | | | | |")
            continue
        o, res = r["outcomes"], r["resources"]
        ok = integrity_ok(r, gated=role in GATED, authoritative=summary["mode"] == "authoritative")
        lines.append(
            f"| {role} | OK | {o['threat_matches']} | {o['tap']} | {o['escapes']} | "
            f"{o['timeouts']} | {o['top_completed_builder_attempts']} | "
            f"{'yes' if ok else 'NO'} | {res['route_decisions']} | "
            f"{r['te2_route']['nodes_per_decision']['max']} | "
            f"{round(res['peak_rss_bytes'] / 2 ** 20, 1)} |")
    for key in ("preservation", "design_gates", "holdout_gates"):
        if key in v:
            lines += ["", f"## {key}", ""]
            lines += [f"- {gate}: {data['status']}" for gate, data in v[key].items()]
    lines += ["", "Order: " + ", ".join(f"{k}:{r}" for k, r in summary["order"]), ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="tactical_evaluator_te2")
    sub = parser.add_subparsers(dest="command", required=True)
    pre = sub.add_parser("preflight", help="synthetic end-to-end run (seeds >= 910000)")
    pre.add_argument("--out", required=True)
    pre.add_argument("--matches", type=int, default=1)
    pre.add_argument("--clock", type=int, default=60)
    pre.add_argument("--only", action="append")
    pre.add_argument("--decision-node-limit", type=int)
    sub.add_parser("authoritative", help="LOCKED: not authorized in this slice")
    work = sub.add_parser("worker")
    work.add_argument("--mode", required=True)
    work.add_argument("--surface", required=True)
    work.add_argument("--part", required=True)
    work.add_argument("--matches", type=int, default=1)
    work.add_argument("--clock", type=int, default=60)
    work.add_argument("--decision-node-limit", type=int)
    args = parser.parse_args(argv)
    if args.command == "authoritative":
        try:
            run_authoritative()
        except AuthoritativeLocked as error:
            print(f"REFUSED: {error}", file=sys.stderr)
            return 3
    if args.command == "preflight":
        try:
            summary = run_preflight(Path(args.out), matches=args.matches, clock=args.clock,
                                    only=args.only, decision_node_limit=args.decision_node_limit)
        except PreflightRefused as error:
            print(f"REFUSED: {error}", file=sys.stderr)
            return 4
        print(summary["verdict"]["te2"])
        return 0
    # worker
    if args.mode != "preflight":
        print("REFUSED: only preflight workers exist in this slice", file=sys.stderr)
        return 3
    surfaces = preflight_surfaces(matches=args.matches, clock=args.clock)
    if args.surface not in surfaces:
        print(f"REFUSED: unknown preflight surface {args.surface!r}", file=sys.stderr)
        return 4
    kwargs = surfaces[args.surface]
    try:
        assert_preflight_safe({args.surface: kwargs})
    except PreflightRefused as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 4
    part = Path(args.part)
    baselines = json.loads((part.parent / "baselines.json").read_text(encoding="utf-8"))
    budget = (route.RouteBudget(decision_nodes=args.decision_node_limit)
              if args.decision_node_limit is not None else None)
    role = role_of(args.surface)
    result, records = measure_candidate(role, kwargs, baselines[role], authoritative=False,
                                        budget=budget)
    part.write_text(json.dumps(dict(result=result, records=records), sort_keys=True,
                               default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
