"""G1 post-failure characterization (read-only)
(docs/TACTICAL_EVALUATOR_G1_CHARACTERIZATION_PREREGISTRATION.md, ab50f7e).

Nothing here is an acting policy or runs in gameplay. It reconstructs the
frozen trajectories, finds first divergences, and runs an exact bounded route
search on frozen states with projection v2's engine-native steps
(Continuation.exchange / advance / opponent, Sandbox). No sampling, pruning
or approximation; an over-budget cell is INFEASIBLE.

Reconstruction:
- baseline: the unchanged ESCAPE_FIRST batch, observed by the Stage 1B driver
  (diagnostics/tactical_evaluator_stage1b.observe) plus a read-only wrapper on
  EscapeFirstInitiatorPolicy.choose that snapshots each window's Branch;
- candidate: an inertness replay from the committed Stage 1B records. The
  recorded-decision policy returns each recorded decision in call order and
  evaluates nothing.
"""
from __future__ import annotations

from collections import Counter
from contextlib import ExitStack
from dataclasses import dataclass, replace
from fractions import Fraction
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

from ..domain.action import Commitment
from ..domain.model import Side
from ..interfaces import tactical_evaluator as te
from ..interfaces import tactical_policy as tp
from ..interfaces import tactical_projection_v2 as v2
from ..interfaces.batch import BatchDecision, BatchInitiatorPolicy, EscapeFirstInitiatorPolicy
from ..positions.mount.catalog import TOP_AMERICANA_ARM_ISOLATION
from . import tactical_evaluator as stage1a
from . import tactical_evaluator_stage1b as s1b
from . import tactical_evaluator_v2 as stage1a_v2

PREREGISTRATION = "ab50f7ef908f1f174aba3c5fad331f8b3ff2c060"
STAGE1B_RESULT = "27ef5e54095b2915f776cb6287dba73bbe28d026"
SUMMARY_EVIDENCE = Path("docs/evidence/tactical_evaluator_g1_characterization.json")
FROZEN_INPUTS = {
    "docs/evidence/tactical_evaluator_stage1b.json":
        "d5ee3c8c8101c09a14a4a6524317ad6d44ba3deebd111b9c0e35d47def87b750",
    "docs/evidence/tactical_evaluator_stage1b_records.json.gz":
        "9775a2f4b42d8b7b60d9f2b3d860630290e3697429ca0b1057209f22b8649c72",
    "docs/TACTICAL_EVALUATOR_STAGE1B_RESULT.md":
        "c58ae09e9a2f337f82fb13164167d469e803658da7f96cbc0c24e19d4611107e",
    "docs/evidence/tactical_evaluator_stage1a_v2.json":
        "c0394a27bbf4faa031a8a530d792167ee5f1ffaba777af6168ca5e83176691e3",
    "docs/evidence/tactical_evaluator_stage1a_v2_records.json.gz":
        "eba5dd73d2ee91b483caff95b51565d53c6662b1b0f63ec03b87f44edde69bc9",
}
SURFACES = ("A-PROD", "PROTECT probe")
OPPONENTS = ("O-TE1", "O-EF")
HORIZON_STEPS = (0, 2, 4, 8)
BUDGET_NODES = 3_000_000
BUDGET_SECONDS = 30 * 60
TARGET = TOP_AMERICANA_ARM_ISOLATION
TACTICAL = BatchInitiatorPolicy.TACTICAL_V1
ESCAPE_FIRST = BatchInitiatorPolicy.ESCAPE_FIRST


def sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def frozen_inputs_unchanged() -> dict:
    return {p: sha256(p) == h for p, h in FROZEN_INPUTS.items()}


def kwargs_for(surface: str) -> dict:
    return stage1a.surfaces()[surface]


def _load_gz(path: str) -> dict:
    with gzip.open(path) as handle:
        return json.loads(handle.read())


# ---------------------------------------------------------------------------
# Reconstruction
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Window:
    index: int                    # window order within the match, from 0
    side: str
    action: str | None            # None = RESET
    requested: str | None
    reason: str
    branch: v2.Branch
    t: int


class _RecordedDecisionPolicy(tp._RecordingPolicy):
    """Inertness replay from committed Stage 1B records (no evaluation)."""

    def __init__(self, context, per_match) -> None:
        super().__init__(context)
        self._records = [[e for e in events if e["kind"] == "decision"]
                         for events in per_match]
        self.windows: list[list[Window]] = [[] for _ in per_match]

    def _entry(self, match, *, kind, branch, allowed, forced_by):
        records = self._records[self._match_index]
        if self._calls >= len(records):
            raise tp.ReplayDesync("underflow", "more calls than recorded decisions")
        r = records[self._calls]
        side = match.initiator
        executed = kind is tp.CallKind.EXECUTED
        if (r["call"] != self._calls or r["side"] != side.value or r["executed"] != executed
                or r["allowed"] != [c.value for c in allowed]
                or r["forced_by"] != (forced_by.value if forced_by else None)
                or r["t"] != match.elapsed_simulated_time):
            raise tp.ReplayDesync("context", f"match {self._match_index} call {self._calls}")
        requested = Commitment(r["requested"]) if r["requested"] else None
        if executed:
            self.windows[self._match_index].append(Window(
                index=len(self.windows[self._match_index]), side=side.value,
                action=r["action"], requested=r["requested"], reason=r["reason"],
                branch=branch, t=r["t"]))
        decision = BatchDecision(r["action"], r["reason"], 0.0, 0.0, 0.0, 0.0)
        return tp.TapeEntry(match_index=self._match_index, call_index=self._calls,
                            kind=kind, side=side, branch=branch, allowed=allowed,
                            forced_by=forced_by, tier=r["tier"], decision=decision,
                            requested=requested)

    def finish(self):
        for i, records in enumerate(self._records):
            used = sum(1 for _ in self.windows[i])
            if used != sum(1 for r in records if r["executed"]):
                raise tp.ReplayDesync("leftover", f"match {i}")
        return super().finish()


_ATTEMPT_FIELDS = ("t", "side", "action", "requested", "effective", "realized_grade",
                   "threat_entry", "setup_advanced", "exit", "ready_use", "builder_target",
                   "builder_not_ready", "terminal", "progress")


def _events_comparable(events, kinds=("attempt", "reset", "hold")) -> list:
    out = []
    for e in events:
        if e["kind"] not in kinds:
            continue
        if e["kind"] == "attempt":
            out.append(("attempt",) + tuple(e.get(k) for k in _ATTEMPT_FIELDS))
        else:
            out.append((e["kind"], e["t"], e["side"]))
    return out


def reconstruct_candidate(surface: str, committed_records: dict, committed_summary: dict):
    """Inertness replay of the committed Stage 1B trajectory."""
    per_match = committed_records[surface]["per_match"]
    holder = {}

    def factory(settings):
        ctx = v2.Context.from_batch_kwargs({**settings, "initiator_policy": TACTICAL})
        holder["policy"] = policy = _RecordedDecisionPolicy(ctx, per_match)
        return policy

    with patch.object(tp, "create_policy", factory):
        obs, _ = s1b.observe(kwargs_for(surface), policy=TACTICAL, tape=())
    policy = holder["policy"]
    run = obs.batch_run
    row = s1b.outcome_row(run.summary, run.top_completed_setup_builder_attempt_count)
    summary_ok = (row == committed_summary["outcomes"]
                  and json.loads(json.dumps(s1b._summary_report(run.summary), default=str))
                  == committed_summary["summary"])
    events_ok = all(_events_comparable(a) == _events_comparable(b)
                    for a, b in zip(obs.timelines, per_match)) and len(obs.timelines) == len(per_match)
    return dict(windows=policy.windows, timelines=obs.timelines, created=obs.created,
                summary_identical=summary_ok, events_identical=events_ok, row=row)


def reconstruct_baseline(surface: str, committed_v2_records: dict):
    """The unchanged ESCAPE_FIRST batch, with window snapshots."""
    windows: list[list[Window]] = []
    current = {"match": None}
    original = EscapeFirstInitiatorPolicy.choose

    def choose(policy, match):
        if current["match"] is not match:
            current["match"] = match
            windows.append([])
        branch = v2.branch_of(match, None)
        decision = original(policy, match)
        windows[-1].append(Window(index=len(windows[-1]), side=match.initiator.value,
                                  action=decision.action_id, requested=None,
                                  reason=decision.reason, branch=branch,
                                  t=match.elapsed_simulated_time))
        return decision

    with patch.object(EscapeFirstInitiatorPolicy, "choose", choose):
        obs, _ = s1b.observe(kwargs_for(surface), policy=ESCAPE_FIRST)
    # Requested commitment of each window from its attempt (k-th attempt =
    # k-th non-RESET window).
    for m, events in enumerate(obs.timelines):
        attempts = [e for e in events if e["kind"] == "attempt"]
        acting = [w for w in windows[m] if w.action is not None]
        if len(attempts) != len(acting):
            raise RuntimeError("baseline window/attempt alignment failed")
        fixed = {w.index: replace(w, requested=a["requested"]) for w, a in zip(acting, attempts)}
        windows[m] = [fixed.get(w.index, w) for w in windows[m]]
    run = obs.batch_run
    row = s1b.outcome_row(run.summary, run.top_completed_setup_builder_attempt_count)
    observed = [row[k] for k in s1b.BASELINE_FIELDS]
    committed = committed_v2_records[surface]["per_match"]

    def v2_rows(events):
        out = []
        for e in events:
            if e["kind"] == "decision":
                out.append(("d", e["side"], e["action"], e["reason"], e["t"]))
            else:
                out.append(("a", e["side"], e["action"], e["requested"], e["realized_grade"],
                            e["effective"], e["threat_entry"], e["t"]))
        return out

    mine = []
    for m, events in enumerate(obs.timelines):
        attempts = iter(e for e in events if e["kind"] == "attempt")
        rows = []
        for w in windows[m]:
            rows.append(("d", w.side, w.action, w.reason, w.t))
            if w.action is not None:
                a = next(attempts)
                rows.append(("a", a["side"], a["action"], a["requested"], a["realized_grade"],
                             a["effective"], a["threat_entry"], a["t"]))
        mine.append(rows)
    events_ok = (len(mine) == len(committed)
                 and all(a == v2_rows(b) for a, b in zip(mine, committed)))
    return dict(windows=windows, timelines=obs.timelines, created=obs.created,
                baseline_exact=observed == list(s1b.FROZEN_BASELINES[surface]),
                events_identical=events_ok, row=row)


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------


def state_fields(branch: v2.Branch) -> dict:
    s = branch.state
    return dict(
        clock=branch.clock, initiative=s.initiator.value, axis=s.axis, band=s.band.value,
        top=dict(current=s.top.current, band=s.top.band.value, latched=s.top.latched),
        bottom=dict(current=s.bottom.current, band=s.bottom.band.value,
                    latched=s.bottom.latched),
        top_behavior=s.top_behavior.value, bottom_behavior=s.bottom_behavior.value,
        tiers=dict(s.tiers), ready=sorted(s.ready),
        stage=s.stage.value if s.stage else None, d3b=branch.d3b)


def branch_key(branch: v2.Branch) -> str:
    return json.dumps(state_fields(branch), sort_keys=True)


def success(state: te.State) -> bool:
    return state.stage is not None


def ready_or_success(state: te.State) -> bool:
    return state.stage is not None or TARGET in state.ready


def n0(branch: v2.Branch) -> int:
    s = branch.state
    if TARGET in s.ready:
        return 1
    return 2 * (2 - s.tier(TARGET)) + 1


class Infeasible(Exception):
    pass


# ---------------------------------------------------------------------------
# Exact route search
# ---------------------------------------------------------------------------


class RouteSearch:
    """Exact finite-horizon route value for Top against a frozen opponent.

    Top windows: max over RESET and the Stage 1B candidate set (legal actions
    x commitments, funding duplicates dropped as v2.candidates). Chance:
    exact exchange_cases. Bottom windows: the frozen opponent contract
    (Continuation.opponent). Between windows: Continuation.advance."""

    def __init__(self, template, kwargs: dict, opponent: str) -> None:
        policy = TACTICAL if opponent == "O-TE1" else ESCAPE_FIRST
        self.context = v2.Context.from_batch_kwargs({**kwargs, "initiator_policy": policy})
        self.queries = v2.Sandbox(template)
        self.cont = v2.Continuation(v2.Sandbox(template).match, self.context)
        self._options: dict = {}

    # -- options -------------------------------------------------------------

    def options(self, branch: v2.Branch) -> tuple:
        """Top's options at a Top window: (('RESET', None), (action, c), ...)."""
        key = branch.state
        if key in self._options:
            return self._options[key]
        m = self.queries.load(branch)
        pool = branch.state.top.current
        out = [("RESET", None)]
        for action_id in m.legal_action_ids(Side.TOP):
            seen = set()
            for c in te.COMMITMENTS:
                effective = te.funded(m, c, pool)
                if effective in seen:
                    continue
                seen.add(effective)
                out.append((action_id, c))
        self._options[key] = tuple(out)
        return self._options[key]

    def transitions(self, branch: v2.Branch, option) -> tuple:
        """((weight, Branch-or-label), ...) after the window and the advance."""
        if branch.state.initiator is Side.TOP:
            action, c = option
            if action == "RESET":
                state = replace(branch.state, initiator=Side.BOTTOM)
                items, ends = ((v2.Branch(state, branch.clock, branch.d3b), Fraction(1)),), ()
            else:
                items, ends = self.cont.exchange(branch, action, c)
        else:
            items, ends = self.cont.opponent(branch)
        out = [(w, label) for label, w in ends]
        for item, w in items:
            if isinstance(item, v2.Branch) and success(item.state):
                out.append((w, v2.TAP))       # success before the advance
                continue
            out.append((w, item if isinstance(item, str) else self.cont.advance(item)))
        return tuple(out)


class Solver:
    """One evaluation cell: fresh memo, budget, cost counters."""

    def __init__(self, search: RouteSearch, goal, *, quiescence=None) -> None:
        self.search = search
        self.goal = goal
        self.quiescence = quiescence      # (n0, bound, unresolved) or None
        self.memo: dict = {}
        self.frontier = Counter()
        self.started = time.monotonic()

    def _leaf(self, item) -> Fraction | None:
        if isinstance(item, str):
            return Fraction(1) if item == v2.TAP else Fraction(0)
        if self.goal(item.state):
            return Fraction(1)
        return None

    def value(self, branch: v2.Branch, depth: int, limit: int) -> Fraction:
        if self.goal(branch.state):
            return Fraction(1)
        if depth >= limit:
            return Fraction(0)
        if self.quiescence is not None:
            base, bound, unresolved = self.quiescence
            if depth >= base and not unresolved(self.search, branch):
                return Fraction(0)
        key = (branch, limit - depth if self.quiescence is None else depth)
        if key in self.memo:
            return self.memo[key]
        if len(self.memo) >= BUDGET_NODES or time.monotonic() - self.started > BUDGET_SECONDS:
            raise Infeasible()
        self.frontier[depth] += 1
        if branch.state.initiator is Side.TOP:
            best = max(self.q(branch, o, depth, limit) for o in self.search.options(branch))
        else:
            best = self._expect(self.search.transitions(branch, None), depth, limit)
        self.memo[key] = best
        return best

    def _expect(self, transitions, depth, limit) -> Fraction:
        total = Fraction(0)
        for w, item in transitions:
            leaf = self._leaf(item)
            total += w * (leaf if leaf is not None else self.value(item, depth + 1, limit))
        return total

    def q(self, branch, option, depth, limit) -> Fraction:
        return self._expect(self.search.transitions(branch, option), depth, limit)

    def cost(self) -> dict:
        return dict(nodes=len(self.memo), wall_seconds=round(time.monotonic() - self.started, 3),
                    largest_frontier=max(self.frontier.values(), default=0))


def unresolved_qa(search: RouteSearch, branch: v2.Branch) -> bool:
    s = branch.state
    if TARGET in s.ready or s.tier(TARGET) > 0:
        return True
    if s.initiator is Side.TOP:
        m = search.queries.load(branch)
        for action_id in m.legal_action_ids(Side.TOP):
            for c in te.COMMITMENTS:
                if te.funded(m, c, s.top.current) is not c:
                    continue
                v = te.evaluate(m, search.context.model, s, action_id, c, project=False)
                if v.terminal > 0 or v.progress > 0:
                    return True
    return False


def unresolved_qb(search: RouteSearch, branch: v2.Branch) -> bool:
    return branch.state.bottom.latched or unresolved_qa(search, branch)


def _q(x: Fraction) -> str:
    return str(x)


def analyze_state(surface: str, branch: v2.Branch, template, opponent: str,
                  *, root_options: bool) -> dict:
    """Route values for one state and opponent at every horizon, plus the
    quiescence variants. Returns exact values as strings."""
    kwargs = kwargs_for(surface)
    search = RouteSearch(template, kwargs, opponent)
    base = n0(branch)
    out = dict(n0=base, horizons={}, quiescence={})
    infeasible = False
    for step in HORIZON_STEPS:
        limit = base + step
        cell = dict(limit=limit)
        if infeasible:
            cell["status"] = "INFEASIBLE"
            out["horizons"][str(step)] = cell
            continue
        try:
            solver = Solver(search, success)
            v = solver.value(branch, 0, limit)
            cell.update(status="OK", V=_q(v), cost=solver.cost())
            if root_options and branch.state.initiator is Side.TOP:
                cell["Q"] = {f"{a}|{c.value if c else ''}": _q(solver.q(branch, (a, c), 0, limit))
                             for a, c in search.options(branch)}
            ready_solver = Solver(search, ready_or_success)
            cell["Ready"] = _q(ready_solver.value(branch, 0, limit))
            cell["ready_cost"] = ready_solver.cost()
        except Infeasible:
            infeasible = True
            cell["status"] = "INFEASIBLE"
        out["horizons"][str(step)] = cell
    for name, predicate in (("QA", unresolved_qa), ("QB", unresolved_qb)):
        cell = {}
        try:
            solver = Solver(search, success, quiescence=(base, base + 8, predicate))
            v = solver.value(branch, 0, base + 8)
            cell.update(status="OK", V=_q(v), cost=solver.cost())
        except Infeasible:
            cell["status"] = "INFEASIBLE"
        out["quiescence"][name] = cell
    out["exchange_cache_entries"] = len(search.cont._exchange)
    out["advance_cache_entries"] = len(search.cont._advance)
    return out


# ---------------------------------------------------------------------------
# TE-1 forensics at a state
# ---------------------------------------------------------------------------


def _value_row(v: te.TacticalValue) -> dict:
    p = v.projection
    return dict(
        action=v.action_id, requested=v.requested.value,
        effective=v.effective.value if v.effective else None,
        terminal=_q(v.terminal), progress=_q(v.progress), setup_future=_q(v.setup_future),
        setup_advance=_q(v.setup_advance), axis_realized=_q(v.axis_realized),
        axis_raw=_q(v.axis_raw), stamina_cost=v.stamina_cost,
        enters_exhausted=v.enters_exhausted, projection=p is not None,
        r=p.builds_remaining if p is not None else None,
        ready_mass=_q(p.ready_mass) if p is not None else None,
        setup_future_requested=({c.value: _q(x) for c, x in p.setup_future_requested}
                                if p is not None else None),
        terminal_mass=dict((k, _q(x)) for k, x in p.terminal_mass) if p is not None else None,
    )


def fail_reason(v: te.TacticalValue, values) -> str:
    """First TE-1 tier condition the candidate fails (it was not chosen)."""
    if v.terminal > 0 or v.progress > 0:
        metric = (lambda x: x.terminal) if v.terminal > 0 else (lambda x: x.progress)
        if v.enters_exhausted:
            others = [o for o in values if o.action_id == v.action_id
                      and not o.enters_exhausted and metric(o) > 0]
            if not all(metric(v) > metric(o) for o in others):
                return "stamina_guard"
        return "outranked"
    if v.setup_future > 0:
        return "outranked"
    if v.axis_raw > 0 and v.axis_realized > 0:
        return "outranked"
    reasons = ["terminal<=0", "progress<=0", "setup_future<=0"]
    if not v.axis_raw > 0:
        reasons.append("axis_raw<=0")
    if not v.axis_realized > 0:
        reasons.append("axis_realized<=0")
    return ";".join(reasons)


def te1_forensics(surface: str, branch: v2.Branch, template) -> dict:
    ctx = v2.Context.from_batch_kwargs({**kwargs_for(surface), "initiator_policy": TACTICAL})
    sandbox = v2.Sandbox(template)
    live = sandbox.load(branch)
    cont = v2.Continuation(live, ctx)
    allowed, forced = tp.precedence(live, context=ctx, handoff_decision=None)
    values = v2.candidates(cont, branch, allowed)
    choice = te.choose_te1(live, values)
    rows = []
    for v in values:
        row = _value_row(v)
        chosen = choice.value is not None and v == choice.value
        row["chosen"] = chosen
        row["fail_reason"] = None if chosen else fail_reason(v, values)
        row["builder_target"] = live.setup_policy.target_for_builder(v.action_id)
        rows.append(row)
    return dict(
        legal_actions=list(live.legal_action_ids(branch.state.initiator)),
        allowed=[c.value for c in allowed], forced_by=forced.value if forced else None,
        te1_tier=choice.tier,
        te1_action=choice.value.action_id if choice.value else None,
        te1_requested=choice.value.requested.value if choice.value else None,
        candidates=rows,
        r1_no_terminal=all(v.terminal <= 0 for v in values),
        r2_no_progress=all(v.progress <= 0 for v in values),
        r4_no_position=all(not (v.axis_raw > 0 and v.axis_realized > 0) for v in values),
        r5_guard_removed=any(r["fail_reason"] == "stamina_guard" for r in rows),
    )


# ---------------------------------------------------------------------------
# State sets (section 3)
# ---------------------------------------------------------------------------


def _acting_window_of_attempts(windows, events) -> dict:
    """events index of each attempt -> its window (k-th attempt = k-th
    non-RESET window)."""
    acting = iter(w for w in windows if w.action is not None)
    return {i: next(acting) for i, e in enumerate(events) if e["kind"] == "attempt"}


def state_sets(surface: str, base: dict, cand: dict) -> dict:
    threat_matches = [m for m, events in enumerate(base["timelines"])
                      if any(e["kind"] == "attempt" and e["threat_entry"] for e in events)]
    s1 = []
    for m in range(len(base["windows"])):
        bw, cw = base["windows"][m], cand["windows"][m]
        for x, y in zip(bw, cw):
            if (x.side, x.action, x.requested) != (y.side, y.action, y.requested):
                s1.append(dict(match=m, seed=kwargs_for(surface)["base_seed"] + m,
                               window=x.index, branch=x.branch,
                               same_state=x.branch == y.branch,
                               baseline=(x.action, x.requested, x.reason),
                               candidate=(y.action, y.requested, y.reason),
                               threat_match=m in threat_matches))
                break
        else:
            s1.append(dict(match=m, window=None, branch=None, same_state=True,
                           threat_match=m in threat_matches))
    s2 = []
    for m, events in enumerate(base["timelines"]):
        by_attempt = _acting_window_of_attempts(base["windows"][m], events)
        chains = s1b.chains(events)
        chains.sort(key=lambda c: c["attempts"][0])
        if surface == "A-PROD":
            chains = [c for c in chains if c["converted"]]
        if chains:
            w = by_attempt[chains[0]["attempts"][0]]
            s2.append(dict(match=m, window=w.index, branch=w.branch))
    s3 = []
    for m, windows in enumerate(cand["windows"]):
        for w in windows:
            if w.side == Side.TOP.value:
                s3.append(dict(match=m, window=w.index, branch=w.branch))
    return dict(S1=s1, S2=s2, S3=s3, threat_matches=threat_matches)


# ---------------------------------------------------------------------------
# Parallel analysis (independent states only; each search is sequential)
# ---------------------------------------------------------------------------

_TEMPLATES: dict = {}


def make_template(surface: str):
    from ..engine.match import MountMatch
    from ..interfaces import batch as batch_module
    created = []

    def factory(*args, **kwargs):
        match = MountMatch(*args, **kwargs)
        created.append(match)
        return match

    with patch.object(batch_module, "MountMatch", factory):
        batch_module.run_batch(initiator_policy=ESCAPE_FIRST,
                               **{**kwargs_for(surface), "matches": 1})
    return created[0]


def _template(surface: str):
    if surface not in _TEMPLATES:
        _TEMPLATES[surface] = make_template(surface)
    return _TEMPLATES[surface]


def run_job(job: tuple) -> tuple:
    """(kind, surface, state_id, branch, opponent) -> (key, result, rng draws)."""
    kind, surface, state_id, branch, opponent = job
    template = _template(surface)
    trace = stage1a.RngTrace()
    with stage1a.count_rng(trace):
        trace.active = True
        try:
            if kind == "te1":
                result = te1_forensics(surface, branch, template)
            else:
                result = analyze_state(surface, branch, template, opponent,
                                       root_options=branch.state.initiator is Side.TOP)
        finally:
            trace.active = False
    draws = sum(trace.evaluator_draws.values()) + trace.baseline_draws
    return (kind, surface, state_id, opponent), result, draws


def run_jobs(jobs: list, workers: int) -> dict:
    if workers <= 1:
        return {key: (res, draws) for key, res, draws in map(run_job, jobs)}
    from concurrent.futures import ProcessPoolExecutor
    out = {}
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for key, res, draws in pool.map(run_job, jobs, chunksize=1):
            out[key] = (res, draws)
    return out


# ---------------------------------------------------------------------------
# Scoring (section 5)
# ---------------------------------------------------------------------------


def _F(x) -> Fraction:
    return Fraction(x)


def _horizon_cells(analysis: dict):
    return [(int(step), cell) for step, cell in analysis["horizons"].items()]


def _best_non_reset(cell: dict):
    if "Q" not in cell:
        return None
    return max((_F(v) for k, v in cell["Q"].items() if not k.startswith("RESET|")),
               default=Fraction(0))


def _reset_q(cell: dict):
    return _F(cell["Q"]["RESET|"]) if "Q" in cell else None


def _cheapest_preserves(cell: dict, te1):
    """Interpretation (disclosed): some non-RESET action at its cheapest
    fundable commitment has Q > 0."""
    if "Q" not in cell or te1 is None:
        return None
    cheapest = {}
    for row in te1["candidates"]:
        a = row["action"]
        if a not in cheapest or row["stamina_cost"] < cheapest[a][0]:
            cheapest[a] = (row["stamina_cost"], row["requested"])
    return any(_F(cell["Q"].get(f"{a}|{c}", "0")) > 0 for a, (_, c) in cheapest.items())


def state_metrics(analyses: dict, te1) -> dict:
    """Per-state signals for both opponents and every horizon."""
    out = {}
    for opp, a in analyses.items():
        rows = {}
        first = None
        for step, cell in sorted(_horizon_cells(a)):
            if cell["status"] != "OK":
                rows[step] = dict(status=cell["status"])
                continue
            v = _F(cell["V"])
            if v > 0 and first is None:
                first = step
            best, reset = _best_non_reset(cell), _reset_q(cell)
            rows[step] = dict(
                status="OK", V=cell["V"], route=v > 0, ready=_F(cell["Ready"]) > 0,
                reset_preserves=(reset > 0) if reset is not None else None,
                reset_destroys=(reset == 0 and best > 0) if reset is not None else None,
                non_reset_preserves=(best > 0) if best is not None else None,
                reset_better=(reset > best) if reset is not None else None,
                equivalent=(reset == best) if reset is not None else None,
                cheapest_preserves=_cheapest_preserves(cell, te1),
                nodes=cell["cost"]["nodes"], wall=cell["cost"]["wall_seconds"],
                largest_frontier=cell["cost"]["largest_frontier"])
        quiescence = {}
        for k, c in a["quiescence"].items():
            quiescence[k] = dict(status=c["status"], V=c.get("V"),
                                 route=(_F(c["V"]) > 0) if c.get("V") is not None else None,
                                 nodes=c.get("cost", {}).get("nodes"),
                                 wall=c.get("cost", {}).get("wall_seconds"))
        out[opp] = dict(horizons=rows, first_route_step=first, quiescence=quiescence,
                        n0=a["n0"])
    return out


def reset_causes(te1: dict, analyses: dict) -> list:
    codes = []
    if te1["r1_no_terminal"]:
        codes.append("R1")
    if te1["r2_no_progress"]:
        codes.append("R2")
    te1_cells = [c for _, c in sorted(_horizon_cells(analyses["O-TE1"])) if c["status"] == "OK"]
    builders = [r for r in te1["candidates"] if r["builder_target"] and _F(r["setup_future"]) == 0]
    if any(_F(c["Q"].get(f"{r['action']}|{r['requested']}", "0")) > 0
           for r in builders for c in te1_cells if "Q" in c):
        codes.append("R3")
    if te1["r4_no_position"]:
        codes.append("R4")
    if te1["r5_guard_removed"]:
        codes.append("R5")
    if te1_cells and "Q" in te1_cells[0]:
        if _best_non_reset(te1_cells[0]) == 0 and any(
                _best_non_reset(c) > 0 for c in te1_cells[1:]):
            codes.append("R6")
    for (_, c1), (_, c2) in zip(sorted(_horizon_cells(analyses["O-TE1"])),
                                sorted(_horizon_cells(analyses["O-EF"]))):
        if c1["status"] == c2["status"] == "OK" and _F(c1["V"]) == 0 < _F(c2["V"]):
            codes.append("R7")
            break
    every = [c for opp in OPPONENTS for _, c in _horizon_cells(analyses[opp])]
    if all(c["status"] == "OK" and _F(c["V"]) == 0 for c in every):
        codes.append("R8")
    if not {"R3", "R5", "R6", "R7", "R8"} & set(codes):
        codes.append("R9")
    return codes


def zero_decomposition(te1: dict, analyses: dict) -> list:
    rows = []
    for r in te1["candidates"]:
        if not r["builder_target"] or _F(r["setup_future"]) != 0:
            continue
        codes = []
        if _F(r["setup_advance"]) == 0:
            codes.append("Z1")
        elif r["ready_mass"] is not None and _F(r["ready_mass"]) == 0:
            codes.append("Z2")
        elif r["ready_mass"] is not None:
            requested = {c: _F(x) for c, x in (r["setup_future_requested"] or {}).items()}
            codes.append("Z3a" if any(x > 0 for x in requested.values()) else "Z3b")
        key = f"{r['action']}|{r['requested']}"
        te1_cells = sorted(_horizon_cells(analyses["O-TE1"]))
        if any(step > 0 and c["status"] == "OK" and "Q" in c and _F(c["Q"].get(key, "0")) > 0
               for step, c in te1_cells):
            codes.append("Z4")
        every = [c for opp in OPPONENTS for _, c in _horizon_cells(analyses[opp])]
        if all(c["status"] == "OK" and "Q" in c and _F(c["Q"].get(key, "0")) == 0
               for c in every):
            codes.append("Z5")
        rows.append(dict(action=r["action"], requested=r["requested"], codes=codes,
                         primary=codes[0] if codes else None))
    return rows


def te1_vs_route(te1: dict, analyses: dict) -> list:
    """TE-1 setup_future against Q_N0 of the same builder (5.2)."""
    cell = analyses["O-TE1"]["horizons"]["0"]
    out = []
    for r in te1["candidates"]:
        if not r["builder_target"] or "Q" not in cell:
            continue
        q = _F(cell["Q"].get(f"{r['action']}|{r['requested']}", "0"))
        out.append(dict(action=r["action"], requested=r["requested"],
                        setup_future=r["setup_future"], q_n0=str(q),
                        sf_positive=_F(r["setup_future"]) > 0, q_positive=q > 0))
    return out


# ---------------------------------------------------------------------------
# Aggregation and main
# ---------------------------------------------------------------------------

SIGNALS = ("route", "ready", "reset_preserves", "reset_destroys", "non_reset_preserves",
           "reset_better", "equivalent", "cheapest_preserves")


def _strip_cost(obj):
    """Results without wall-clock fields (for the determinism comparison)."""
    if isinstance(obj, dict):
        return {k: _strip_cost(v) for k, v in obj.items()
                if k not in ("wall_seconds", "wall", "cost", "ready_cost")}
    if isinstance(obj, list):
        return [_strip_cost(x) for x in obj]
    return obj


def _aggregate(metrics: list, weights: list) -> dict:
    """Counts over distinct states (and match-weighted) per opponent/horizon."""
    out = {}
    for opp in OPPONENTS:
        per_h = {}
        for step in HORIZON_STEPS:
            cells = [(m[opp]["horizons"][step], w) for m, w in zip(metrics, weights)]
            ok = [(c, w) for c, w in cells if c["status"] == "OK"]
            row = dict(states=len(cells), feasible=len(ok),
                       infeasible=len(cells) - len(ok), weighted_states=sum(weights))
            for sig in SIGNALS:
                vals = [(c[sig], w) for c, w in ok if c.get(sig) is not None]
                row[sig] = sum(1 for v, _ in vals if v)
                row[f"{sig}_weighted"] = sum(w for v, w in vals if v)
                row[f"{sig}_defined"] = len(vals)
            row["nodes_max"] = max((c["nodes"] for c, _ in ok), default=0)
            row["nodes_sum"] = sum(c["nodes"] for c, _ in ok)
            row["largest_frontier"] = max((c["largest_frontier"] for c, _ in ok), default=0)
            row["wall_sum"] = round(sum(c["wall"] for c, _ in ok), 2)
            per_h[f"N0+{step}"] = row
        q = {}
        for name in ("QA", "QB"):
            agree = q_only = u_only = routes = feasible = nodes = 0
            wall = 0.0
            for m in metrics:
                qc, uc = m[opp]["quiescence"][name], m[opp]["horizons"][8]
                if qc["status"] != "OK" or uc["status"] != "OK":
                    continue
                feasible += 1
                routes += qc["route"]
                nodes += qc["nodes"]
                wall += qc["wall"]
                if qc["route"] == uc["route"]:
                    agree += 1
                elif qc["route"]:
                    q_only += 1
                else:
                    u_only += 1
            q[name] = dict(feasible=feasible, routes=routes, agree_with_uniform=agree,
                           route_only_quiescent=q_only, route_only_uniform=u_only,
                           nodes_sum=nodes, wall_sum=round(wall, 2),
                           uniform_nodes_sum=per_h["N0+8"]["nodes_sum"],
                           uniform_wall_sum=per_h["N0+8"]["wall_sum"])
        first = Counter(str(m[opp]["first_route_step"]) for m in metrics)
        out[opp] = dict(horizons=per_h, quiescence=q, first_route_step=dict(first))
    return out


def _collection(items):
    ids = Counter(i["state_id"] for i in items if i["state_id"] is not None)
    keys = sorted(ids)
    return keys, [ids[k] for k in keys]


def measure(workers: int = 20, *, repeat: bool = True) -> dict:
    started = time.monotonic()
    before = frozen_inputs_unchanged()
    stage1b_records = _load_gz("docs/evidence/tactical_evaluator_stage1b_records.json.gz")
    stage1b_summary = json.loads(Path("docs/evidence/tactical_evaluator_stage1b.json")
                                 .read_text(encoding="utf-8"))["surfaces"]
    v2_records = _load_gz("docs/evidence/tactical_evaluator_stage1a_v2_records.json.gz")
    recon, sets, distinct = {}, {}, {}
    for surface in SURFACES:
        cand = reconstruct_candidate(surface, stage1b_records, stage1b_summary[surface])
        base = reconstruct_baseline(surface, v2_records)
        recon[surface] = dict(candidate_summary_identical=cand["summary_identical"],
                              candidate_events_identical=cand["events_identical"],
                              baseline_exact=base["baseline_exact"],
                              baseline_events_identical=base["events_identical"])
        sets[surface] = state_sets(surface, base, cand)
        index = {}
        for name in ("S1", "S2", "S3"):
            for item in sets[surface][name]:
                b = item["branch"]
                if b is not None and b not in index:
                    index[b] = len(index)
                item["state_id"] = index.get(b) if b is not None else None
        distinct[surface] = list(index)
    jobs = []
    for surface in SURFACES:
        for sid, b in enumerate(distinct[surface]):
            if b.state.initiator is Side.TOP:
                jobs.append(("te1", surface, sid, b, None))
            for opp in OPPONENTS:
                jobs.append(("route", surface, sid, b, opp))
    results = run_jobs(jobs, workers)
    deterministic = None
    if repeat:
        second = run_jobs(jobs, workers)
        deterministic = all(_strip_cost(results[k][0]) == _strip_cost(second[k][0])
                            for k in results)
    rng_draws = sum(d for _, d in results.values())

    out_surfaces = {}
    for surface in SURFACES:
        te1 = {sid: results[("te1", surface, sid, None)][0]
               for sid, b in enumerate(distinct[surface]) if b.state.initiator is Side.TOP}
        analyses = {sid: {opp: results[("route", surface, sid, opp)][0] for opp in OPPONENTS}
                    for sid in range(len(distinct[surface]))}
        metrics = {sid: state_metrics(analyses[sid], te1.get(sid)) for sid in analyses}
        sv = sets[surface]
        groups = {"S1 threat matches": [i for i in sv["S1"] if i["threat_match"]],
                  "S1 all matches": sv["S1"], "S2": sv["S2"], "S3": sv["S3"]}
        tables = {}
        for gname, items in groups.items():
            keys, weights = _collection(items)
            tables[gname] = dict(distinct_states=len(keys), items=len(items),
                                 **_aggregate([metrics[k] for k in keys], weights))
        s1_states = {}
        for item in sv["S1"]:
            sid = item["state_id"]
            if sid is None:
                continue
            entry = s1_states.setdefault(sid, dict(
                state=state_fields(distinct[surface][sid]), matches=[], threat_matches=0,
                windows=Counter(), baseline=Counter(), candidate=Counter(), same_state=True))
            entry["matches"].append(item["match"])
            entry["threat_matches"] += item["threat_match"]
            entry["windows"][str(item["window"])] += 1
            entry["baseline"]["|".join(str(x) for x in item["baseline"])] += 1
            entry["candidate"]["|".join(str(x) for x in item["candidate"])] += 1
            entry["same_state"] = entry["same_state"] and item["same_state"]
        first_div = {}
        reset_codes = Counter()
        reset_states = 0
        for sid, entry in s1_states.items():
            t = te1.get(sid)
            entry.update(windows=dict(entry["windows"]), baseline=dict(entry["baseline"]),
                         candidate=dict(entry["candidate"]), te1=t, route=analyses[sid],
                         metrics=metrics[sid])
            if t is not None and t["te1_tier"] == "reset":
                codes = reset_causes(t, analyses[sid])
                entry["reset_causes"] = codes
                reset_states += 1
                reset_codes.update(codes)
                entry["te1_vs_route"] = te1_vs_route(t, analyses[sid])
            first_div[str(sid)] = entry
        zero, zero_primary, zero_rows, sf_vs_q = Counter(), Counter(), 0, Counter()
        for gname in ("S1 all matches", "S2"):
            for sid in _collection(groups[gname])[0]:
                if sid not in te1:
                    continue
                for row in zero_decomposition(te1[sid], analyses[sid]):
                    zero_rows += 1
                    zero.update(row["codes"])
                    zero_primary[row["primary"]] += 1
                for row in te1_vs_route(te1[sid], analyses[sid]):
                    sf_vs_q[f"sf>0={row['sf_positive']}|qN0>0={row['q_positive']}"] += 1
        te1_tiers_s2 = Counter(te1[k]["te1_tier"] for k in _collection(groups["S2"])[0]
                               if k in te1)
        out_surfaces[surface] = dict(
            reconstruction=recon[surface], threat_matches=len(sv["threat_matches"]),
            distinct_states=len(distinct[surface]), first_divergence=first_div,
            reset_forensics=dict(states=reset_states, codes=dict(reset_codes)),
            route_tables=tables,
            setup_future_zero=dict(builder_candidates=zero_rows, codes=dict(zero),
                                   primary=dict(zero_primary)),
            setup_future_vs_route_n0=dict(sf_vs_q), te1_tier_on_s2=dict(te1_tiers_s2))
    separation = {}
    for gname in ("S1 all matches", "S2", "S3"):
        for opp in OPPONENTS:
            for step in HORIZON_STEPS:
                for sig in SIGNALS:
                    a = out_surfaces["A-PROD"]["route_tables"][gname][opp]["horizons"][f"N0+{step}"]
                    p = out_surfaces["PROTECT probe"]["route_tables"][gname][opp]["horizons"][f"N0+{step}"]
                    separation[f"{gname}|{opp}|N0+{step}|{sig}"] = dict(
                        a_prod=f"{a[sig]}/{a[sig + '_defined']}",
                        protect=f"{p[sig]}/{p[sig + '_defined']}")
    after = frozen_inputs_unchanged()
    diff = subprocess.run(["git", "diff", "--name-only", STAGE1B_RESULT], capture_output=True,
                          text=True, check=True).stdout.split()
    untracked = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"],
                               capture_output=True, text=True, check=True).stdout.split()
    allowed_paths = {"src/bjj_game/diagnostics/tactical_evaluator_g1_characterization.py",
                     "tests/test_tactical_evaluator_g1_characterization.py",
                     "docs/TACTICAL_EVALUATOR_G1_CHARACTERIZATION_PREREGISTRATION.md",
                     "docs/TACTICAL_EVALUATOR_G1_CHARACTERIZATION.md",
                     SUMMARY_EVIDENCE.as_posix()}
    integrity = dict(
        frozen_inputs_unchanged_before=all(before.values()),
        frozen_inputs_unchanged_after=all(after.values()),
        changed_paths_outside_slice=sorted(set(diff + untracked) - allowed_paths),
        reconstruction_exact=all(all(r.values()) for r in recon.values()),
        first_divergence_states_identical=all(
            i["same_state"] for s in SURFACES for i in sets[s]["S1"]),
        rng_draws=rng_draws, deterministic_rerun=deterministic,
        jobs=len(jobs), workers=workers, wall_seconds=round(time.monotonic() - started, 1),
    )
    return dict(preregistration=PREREGISTRATION, stage1b_result=STAGE1B_RESULT,
                integrity=integrity, surfaces=out_surfaces, separation=separation)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=20)
    args = parser.parse_args()
    summary = measure(args.workers)
    SUMMARY_EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_EVIDENCE.write_text(json.dumps(summary, indent=1, sort_keys=True, default=str)
                                + "\n", encoding="utf-8", newline="\n")
    print(SUMMARY_EVIDENCE)
    print(json.dumps(summary["integrity"], indent=1))


if __name__ == "__main__":
    main()
