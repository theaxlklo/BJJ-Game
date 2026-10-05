"""D2 v1e frozen measurement and scoring.

Runs exactly the experiment preregistered in
docs/HANDOFF_OSCILLATION_D2_PREREGISTRATION_V1E.md
(c4a9c3369b53911eda4d47dd9d814d385470ba8a): E-PROD, base seeds 42 and 142,
100 matches each, 300 s, stalling OFF + shadow and ON, with v1e enabled, plus
adopted canonical controls on the same seeds. No extensions, no seed
replacement, no tuning, no exclusions.

Not thread-safe (instrumented replays patch class attributes); run standalone.

    python -m bjj_game.diagnostics.handoff_d2_v1e
"""

from __future__ import annotations

from collections import Counter
from contextlib import ExitStack
from dataclasses import asdict, dataclass, fields
from functools import lru_cache
import gzip
import json
import math
from pathlib import Path
import random
from statistics import median
from unittest import mock

from ..domain.model import ExitDestination, Side
from ..engine.match import MountMatch
from ..engine.stalling import STALLING_THRESHOLD_SECONDS
from ..interfaces import batch as batch_module
from ..interfaces.batch import (
    BatchBehaviorMode,
    BatchSummary,
    HandoffEpisodeStatus,
    ReExhaustionHandoffEpisode,
    run_escape_first_batch,
)
from ..interfaces.handoff_policy import PostClearHandoffMode
from ..interfaces.production_policy import PRODUCTION_STAMINA_RECOVERY_POLICY
from ..interfaces.recovery_policy import RecoveryInitiationMode, RecoveryPolicyCollector
from .stamina_adoption_candidate import (
    _surface_ab_kwargs,
    _surface_e_prod_kwargs,
)
from .stamina_adoption_handoff import horizon_counts
from .stamina_adoption_verification import (
    POLICY_KEYS,
    _run_captured,
    effective_settings,
)
from .stamina_economy import StaminaEconomySurface
from .stamina_recovery_policy import (
    SettlementAttributionMode,
    _attribution_cell,
    _candidate_cell,
    _first_divergence_for_match,
)

PREREGISTRATION_SHA = "c4a9c3369b53911eda4d47dd9d814d385470ba8a"
V1E = PostClearHandoffMode.V1E_PERSISTENT_CONSERVE_HOLD
SEEDS = (42, 142)
STALLING = ("OFF+shadow", "ON")
RUNS = tuple((seed, stalling) for seed in SEEDS for stalling in STALLING)
HORIZONS = (5, 10, 15, 20, 30)
TAP = "TAP — Americana"
TIMEOUT = "TIMEOUT — Mount retained"
ESCAPES = {d.value for d in ExitDestination}

# Frozen thresholds (criteria 3-5, 9-13, 16).
C3_FINAL_MEDIAN_MIN = 29
C4_ESCAPES_MIN = 25
C4_SPLIT = {"Half Guard": 16, "Open Guard": 10, "Reversal": 9}
C4_SPLIT_TOLERANCE = 10
C4_TIMEOUTS_MAX = 70
C4_TAP_MAX = 9
C5_EXPOSURE_MAX = 23
C9_RATE_MAX = 0.20
C10_RATE_MAX = 0.35
C11_MIN = 43
C12_ORIGINAL_CLEAR_MIN = 40
C12_POOLED_CLEAR_MIN = 75
C12_MEDIAN_MAX = 250
C13_MIN = 43
C16_REMAINING_MIN = 40
C16_ELIGIBLE_MIN = 35
C16_TIMELY_SECONDS = 40
C16_TIMELY_RATE_MIN = 0.80


def v1e_kwargs(seed: int, stalling: str) -> dict:
    on = stalling == "ON"
    kwargs = _surface_e_prod_kwargs(stalling=on, shadow=not on, base_seed=seed)
    kwargs.update(post_clear_handoff_mode=V1E, measure_post_clear_handoff=True)
    return kwargs


def control_kwargs(seed: int, stalling: str) -> dict:
    """Adopted canonical policy on the same surface (A9/D1 control route)."""
    on = stalling == "ON"
    base = {
        key: value
        for key, value in _surface_e_prod_kwargs(
            stalling=on, shadow=not on, base_seed=seed
        ).items()
        if key not in POLICY_KEYS
    }
    return {
        **base,
        **PRODUCTION_STAMINA_RECOVERY_POLICY.batch_settings(
            bottom_behavior_mode=base["bottom_behavior_mode"]
        ),
        "measure_post_clear_handoff": True,
    }


def v1e_canonical_route_kwargs(seed: int, stalling: str) -> dict:
    """Criterion 7: v1e built on top of the canonical policy settings."""
    return {**control_kwargs(seed, stalling), "post_clear_handoff_mode": V1E}


def v1e_plain_kwargs(seed: int) -> dict:
    kwargs = v1e_kwargs(seed, "OFF+shadow")
    kwargs.update(
        measure_stamina_economy=False,
        measure_recovery_policy=False,
        measure_reexhaustion_handoffs=False,
        measure_post_clear_handoff=False,
        shadow_stalling=False,
    )
    return kwargs


MEASUREMENT_FIELDS = frozenset(
    {"stamina_economy", "recovery_policy", "reexhaustion_handoffs", "post_clear_handoff"}
)


def gameplay_fields(summary: BatchSummary) -> tuple:
    return tuple(
        (f.name, getattr(summary, f.name))
        for f in fields(summary)
        if f.name not in MEASUREMENT_FIELDS
    )


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------


class _HoldCounter:
    def __init__(self) -> None:
        self.calls = 0

    def __enter__(self):
        original = MountMatch.recovery_hold

        def counting(match):
            self.calls += 1
            return original(match)

        self._patch = mock.patch.object(MountMatch, "recovery_hold", counting)
        self._patch.start()
        return self

    def __exit__(self, *exc):
        self._patch.stop()
        return False


def _instrumented_run(kwargs: dict) -> tuple[BatchSummary, dict]:
    """Replay with RNG and hold-inertness instrumentation (observer only)."""
    counter = [0]
    log: list[tuple] = []
    hold_checks = {"holds": 0, "unchanged": 0}
    before_reset_calls = [0]
    reset_calls = [0]
    rng_originals = {n: getattr(random.Random, n) for n in ("random", "getrandbits")}

    def counted(name):
        def wrapper(self, *args, **kw):
            counter[0] += 1
            return rng_originals[name](self, *args, **kw)
        return wrapper

    def op(name):
        original = getattr(MountMatch, name)

        def wrapper(match, *args, **kw):
            start = counter[0]
            if name == "reset_window":
                reset_calls[0] += 1
            if name == "recovery_hold":
                state = _hold_state(match)
            result = original(match, *args, **kw)
            if name == "recovery_hold":
                hold_checks["holds"] += 1
                after = _hold_state(match)
                if after == state:
                    hold_checks["unchanged"] += 1
            log.append((name, start, counter[0]))
            return result
        return wrapper

    original_before_reset = RecoveryPolicyCollector.before_reset

    def before_reset(self, *args, **kw):
        before_reset_calls[0] += 1
        return original_before_reset(self, *args, **kw)

    with ExitStack() as stack:
        for name in rng_originals:
            stack.enter_context(mock.patch.object(random.Random, name, counted(name)))
        for name in ("advance", "attempt", "reset_window", "recovery_hold"):
            stack.enter_context(mock.patch.object(MountMatch, name, op(name)))
        stack.enter_context(
            mock.patch.object(RecoveryPolicyCollector, "before_reset", before_reset)
        )
        summary = run_escape_first_batch(**kwargs)

    rng_clean = 0
    holds = 0
    for index, (name, start, end) in enumerate(log):
        if name != "recovery_hold":
            continue
        holds += 1
        previous_end = log[index - 1][2] if index else start
        next_start = log[index + 1][1] if index + 1 < len(log) else end
        if start == end == previous_end == next_start:
            rng_clean += 1
    return summary, {
        "holds": holds,
        "holds_without_rng": rng_clean,
        "holds_state_unchanged": hold_checks["unchanged"],
        "reset_window_calls": reset_calls[0],
        "recovery_collector_before_reset_calls": before_reset_calls[0],
    }


def _hold_state(match: MountMatch) -> tuple:
    history = match.history
    return (
        match.bottom.stamina.current,
        match.top.stamina.current,
        match.clock_seconds,
        match.axis,
        match.band,
        repr(match.setup_state),
        repr(match.submission_state),
        len(history.recognition_history),
        len(history.reset_window_history),
        len(history.stalling_progress_opportunity_history),
        len(history.stalling_progress_engagement_history),
        repr(match.stalling_tracker),
        match.free_initiative_pending,
    )


@dataclass(frozen=True)
class Runs:
    v1e: dict
    v1e_matches: dict
    control: dict
    control_matches: dict
    control_hold_calls: int
    ab: dict
    ab_hold_calls: int
    replay_equal: dict
    plain_identity: dict
    canonical_route: dict
    instrumented: dict
    v1e_rejected_on_ab: dict


@lru_cache(maxsize=1)
def runs() -> Runs:
    v1e = {}
    v1e_matches = {}
    for key in RUNS:
        v1e[key], v1e_matches[key] = _run_captured(v1e_kwargs(*key))

    control = {}
    control_matches = {}
    ab = {}
    with _HoldCounter() as counter:
        for key in RUNS:
            control[key], control_matches[key] = _run_captured(control_kwargs(*key))
        control_hold_calls = counter.calls
    with _HoldCounter() as counter:
        for name, label in (("A", "A public MATCH"), ("B", "B trusts reads")):
            ab[name] = run_escape_first_batch(**_surface_ab_kwargs(label))
        ab_hold_calls = counter.calls

    rejected = {}
    for name, label in (("A", "A public MATCH"), ("B", "B trusts reads")):
        try:
            run_escape_first_batch(
                **{**_surface_ab_kwargs(label), "matches": 1,
                   "post_clear_handoff_mode": V1E}
            )
            rejected[name] = False
        except ValueError:
            rejected[name] = True

    replay_equal = {}
    for key in RUNS:
        summary, matches = _run_captured(v1e_kwargs(*key))
        replay_equal[key] = summary == v1e[key] and matches == v1e_matches[key]

    plain_identity = {}
    for seed in SEEDS:
        summary, matches = _run_captured(v1e_plain_kwargs(seed))
        reference = v1e[(seed, "OFF+shadow")]
        plain_identity[seed] = (
            gameplay_fields(summary) == gameplay_fields(reference)
            and matches == v1e_matches[(seed, "OFF+shadow")]
        )

    canonical_route = {}
    for key in RUNS:
        route = v1e_canonical_route_kwargs(*key)
        summary, matches = _run_captured(route)
        canonical_route[key] = {
            "settings_equal": effective_settings(route) == effective_settings(v1e_kwargs(*key)),
            "summary_equal": summary == v1e[key],
            "diverged": sum(a != b for a, b in zip(matches, v1e_matches[key])),
        }

    instrumented = {}
    for key in RUNS:
        summary, proof = _instrumented_run(v1e_kwargs(*key))
        proof["summary_equal_to_uninstrumented"] = summary == v1e[key]
        instrumented[key] = proof

    return Runs(
        v1e=v1e,
        v1e_matches=v1e_matches,
        control=control,
        control_matches=control_matches,
        control_hold_calls=control_hold_calls,
        ab=ab,
        ab_hold_calls=ab_hold_calls,
        replay_equal=replay_equal,
        plain_identity=plain_identity,
        canonical_route=canonical_route,
        instrumented=instrumented,
        v1e_rejected_on_ab=rejected,
    )


# ---------------------------------------------------------------------------
# Event-log views
# ---------------------------------------------------------------------------


@dataclass
class MatchView:
    seed: int
    stalling: str
    index: int  # pooled index: seed 142 matches are offset by 100
    initial_clock: int
    outcome: str
    events: tuple
    clears: list
    reentries: list  # (t, cause, event position)
    end_t: int


def _cause(event: dict) -> str:
    if event["k"] == "adv":
        return "behavior drain" if event["bnet"] < 0 else "advance (other)"
    if event["k"] == "att":
        return "initiation spend" if event["side"] == "bottom" else "responder/provisional-hold spend"
    return event["k"]


def match_views(summary: BatchSummary, seed: int, stalling: str) -> list[MatchView]:
    views = []
    offset = 0 if seed == SEEDS[0] else 100
    for record in summary.post_clear_handoff.matches:
        previous = None
        clears, reentries = [], []
        for position, event in enumerate(record.events):
            if "bx" not in event:
                continue
            if previous is not None:
                if previous and not event["bx"]:
                    clears.append(event["t"])
                elif not previous and event["bx"]:
                    reentries.append((event["t"], _cause(event), position))
            previous = event["bx"]
        views.append(
            MatchView(
                seed=seed,
                stalling=stalling,
                index=record.match_index + offset,
                initial_clock=record.initial_clock,
                outcome=record.outcome,
                events=record.events,
                clears=clears,
                reentries=reentries,
                end_t=record.events[-1]["t"],
            )
        )
    return views


def episodes(view: MatchView) -> list[ReExhaustionHandoffEpisode]:
    out = []
    for i, clear in enumerate(view.clears):
        limit = view.clears[i + 1] if i + 1 < len(view.clears) else None
        reex = next(
            (t for t, _, _ in view.reentries
             if t >= clear and (limit is None or t <= limit)),
            None,
        )
        out.append(ReExhaustionHandoffEpisode(
            match_index=view.index,
            clear_elapsed_seconds=clear,
            reexhausted_elapsed_seconds=reex,
            match_end_elapsed_seconds=view.end_t,
        ))
    return out


def a9_consistent(summary: BatchSummary, views: list[MatchView]) -> bool:
    """Collector-derived episodes equal the A9 observer's episodes."""
    offset = views[0].index - summary.post_clear_handoff.matches[0].match_index
    observed = sorted(
        (e.match_index + offset, e.clear_elapsed_seconds,
         e.reexhausted_elapsed_seconds, e.match_end_elapsed_seconds)
        for e in summary.reexhaustion_handoffs.episodes
    )
    derived = sorted(
        (e.match_index, e.clear_elapsed_seconds,
         e.reexhausted_elapsed_seconds, e.match_end_elapsed_seconds)
        for v in views for e in episodes(v)
    )
    return observed == derived


def bottom_windows(view: MatchView) -> list[tuple[int, dict]]:
    return [(i, e) for i, e in enumerate(view.events)
            if e["k"] == "win" and e["side"] == "bottom"]


@dataclass
class Cycle:
    view: MatchView
    entry_pos: int
    entry: dict
    windows: list
    end_kind: str  # RELEASE | CLEARED_BY_EXHAUSTION | PENDING_AT_END
    end_t: int
    end_pos: int
    reexhausted_t: int | None
    reexhaust_cause: str | None

    @property
    def holds(self) -> int:
        return sum(1 for w in self.windows if w["kind"] in {"ENTER_HOLD", "HOLD"})

    @property
    def release_delay(self) -> int | None:
        return self.end_t - self.entry["t"] if self.end_kind == "RELEASE" else None

    @property
    def advances(self) -> int:
        return sum(1 for e in self.view.events[self.entry_pos:self.end_pos + 1] if e["k"] == "adv")


def cycles(view: MatchView) -> list[Cycle]:
    out = []
    events = view.events
    i = 0
    while i < len(events):
        e = events[i]
        if e["k"] == "win" and e["side"] == "bottom" and e.get("tr") == "ENTER":
            windows = [e]
            end_kind = end_t = end_pos = None
            j = i + 1
            while j < len(events):
                x = events[j]
                if x["k"] == "win" and x["side"] == "bottom":
                    windows.append(x)
                    if x.get("tr") in {"RELEASE", "CLEARED_BY_EXHAUSTION"}:
                        end_kind, end_t, end_pos = x["tr"], x["t"], j
                        break
                if x["k"] == "mode_end":
                    end_kind, end_t, end_pos = "PENDING_AT_END", x["t"], j
                    break
                j += 1
            if end_kind is None:
                raise RuntimeError("unterminated recovery-hold cycle")
            reex = next(((t, c) for t, c, p in view.reentries if i < p <= end_pos), None)
            out.append(Cycle(
                view=view, entry_pos=i, entry=e, windows=windows,
                end_kind=end_kind, end_t=end_t, end_pos=end_pos,
                reexhausted_t=reex[0] if reex else None,
                reexhaust_cause=reex[1] if reex else None,
            ))
            i = end_pos
        i += 1
    return out


def _status_from(t0: int, reex: int | None, end_t: int, horizon: int) -> HandoffEpisodeStatus:
    if reex is not None and reex - t0 <= horizon:
        return HandoffEpisodeStatus.REEXHAUSTED_WITHIN_HORIZON
    if end_t - t0 >= horizon:
        return HandoffEpisodeStatus.SURVIVED_THROUGH_HORIZON
    return HandoffEpisodeStatus.RIGHT_CENSORED


def _next_reentry(view: MatchView, t0: int, after_pos: int) -> int | None:
    return next((t for t, _, p in view.reentries if p > after_pos and t >= t0), None)


def _p90(values: list[int]) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.ceil(0.9 * len(ordered)) - 1]


def _hist(values) -> str:
    counts = Counter(values)
    return ", ".join(f"{k}: {v}" for k, v in sorted(counts.items(), key=lambda kv: str(kv[0]))) or "none"


# ---------------------------------------------------------------------------
# Criteria
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Criterion:
    number: str
    title: str
    status: str  # PASS | FAIL | OPEN | REPORTED
    evidence: str


def _combine(*statuses: str) -> str:
    if "FAIL" in statuses:
        return "FAIL"
    if "OPEN" in statuses:
        return "OPEN"
    return "PASS"


def _rate_status(k: int, n: int, limit: float, floor: int) -> str:
    if n < floor:
        return "OPEN"
    return "PASS" if k / n <= limit else "FAIL"


def _cell(summary: BatchSummary, stalling: str):
    return _candidate_cell(
        StaminaEconomySurface(label="E-PROD v1e", summary=summary),
        RecoveryInitiationMode.LOW_WHILE_EXHAUSTED,
        stalling=stalling == "ON",
        shadow=stalling != "ON",
    )


@lru_cache(maxsize=1)
def views() -> dict:
    r = runs()
    return {
        "v1e": {key: match_views(r.v1e[key], *key) for key in RUNS},
        "control": {key: match_views(r.control[key], *key) for key in RUNS},
    }


def pooled(kind: str, stalling: str) -> list[MatchView]:
    v = views()[kind]
    return v[(42, stalling)] + v[(142, stalling)]


def stability(stalling: str, kind: str = "v1e") -> dict:
    vs = pooled(kind, stalling)
    eps = [e for v in vs for e in episodes(v)]
    first = []
    for v in vs:
        es = episodes(v)
        if es:
            first.append(es[0])
    return {
        "episodes": {h: horizon_counts(tuple(eps), h) for h in HORIZONS},
        "first": {h: horizon_counts(tuple(first), h) for h in HORIZONS},
        "n_episodes": len(eps),
        "n_first": len(first),
    }


def handoff_returns(stalling: str, kind: str = "v1e") -> dict:
    """Criterion 13 on each match's first clear episode."""
    rows = []
    for v in pooled(kind, stalling):
        if not v.clears:
            continue
        clear = v.clears[0]
        clear_pos = next(p for p, e in enumerate(v.events)
                         if "bx" in e and e["t"] == clear and not e["bx"]
                         and p > 0)
        reex_before = None
        ret = None
        for p in range(clear_pos, len(v.events)):
            e = v.events[p]
            if any(pp == p for _, _, pp in v.reentries):
                reex_before = e["t"]
                break
            if (e["k"] == "att" and e["side"] == "bottom" and e["req"] == "MEDIUM"
                    and not e["bx_before"]):
                ret = (e["t"], p)
                break
        if ret is not None:
            reex = _next_reentry(v, ret[0], ret[1] - 1)
            rows.append({"match": v.index, "clear": clear, "return": ret[0],
                         "delay": ret[0] - clear, "reex": reex, "end": v.end_t,
                         "failed": False})
        elif reex_before is not None:
            rows.append({"match": v.index, "clear": clear, "return": None,
                         "delay": None, "reex": reex_before, "end": v.end_t,
                         "failed": True})
        else:
            rows.append({"match": v.index, "clear": clear, "return": None,
                         "delay": None, "reex": None, "end": v.end_t,
                         "failed": False, "pending": True})
    result = {"rows": rows}
    returns = [r for r in rows if r["return"] is not None]
    failed = [r for r in rows if r["failed"]]
    result["matches_with_return"] = len(returns)
    result["failed_handoffs"] = len(failed)
    result["pending"] = sum(1 for r in rows if r.get("pending"))
    for h in (10, 30):
        statuses = [_status_from(r["return"], r["reex"], r["end"], h) for r in returns]
        k = statuses.count(HandoffEpisodeStatus.REEXHAUSTED_WITHIN_HORIZON)
        s = statuses.count(HandoffEpisodeStatus.SURVIVED_THROUGH_HORIZON)
        c = statuses.count(HandoffEpisodeStatus.RIGHT_CENSORED)
        result[h] = {"reexhausted": k, "survived": s, "censored": c,
                     "admissible": k + s, "failed_handoffs": len(failed),
                     "rate_k": k + len(failed), "rate_n": k + s + len(failed)}
    result["delays"] = [r["delay"] for r in returns]
    return result


def criterion16(stalling: str) -> dict:
    rows = []
    for v in pooled("v1e", stalling):
        cs = cycles(v)
        if not cs:
            continue
        c = cs[0]
        remaining = v.initial_clock - c.entry["t"]
        if c.reexhausted_t is not None:
            result = "re-exhausted-before-release"
        elif c.end_kind == "RELEASE":
            result = "timely" if c.release_delay <= C16_TIMELY_SECONDS else "late"
        else:
            result = "pending-at-end"
        rows.append({
            "match": v.index, "entry_t": c.entry["t"], "remaining": remaining,
            "eligible": remaining >= C16_REMAINING_MIN, "result": result,
            "delay": c.release_delay, "outcome": v.outcome,
        })
    eligible = [r for r in rows if r["eligible"]]
    timely = sum(1 for r in eligible if r["result"] == "timely")
    out = {
        "rows": rows,
        "eligible": len(eligible),
        "timely": timely,
        "late": sum(1 for r in eligible if r["result"] == "late"),
        "reexhausted": sum(1 for r in eligible if r["result"] == "re-exhausted-before-release"),
        "pending": sum(1 for r in eligible if r["result"] == "pending-at-end"),
        "pending_by_outcome": dict(Counter(r["outcome"] for r in eligible if r["result"] == "pending-at-end")),
        "ineligible": len(rows) - len(eligible),
        "ineligible_results": dict(Counter(r["result"] for r in rows if not r["eligible"])),
        "delays_all": [r["delay"] for r in rows if r["delay"] is not None],
        "delays_eligible": [r["delay"] for r in eligible if r["delay"] is not None],
        "matches_ever_releasing": sum(
            1 for v in pooled("v1e", stalling) if any(c.end_kind == "RELEASE" for c in cycles(v))
        ),
        "cycles_per_match": dict(Counter(len(cycles(v)) for v in pooled("v1e", stalling))),
    }
    if len(eligible) < C16_ELIGIBLE_MIN:
        out["status"] = "OPEN"
    else:
        out["status"] = "PASS" if timely / len(eligible) >= C16_TIMELY_RATE_MIN else "FAIL"
    return out


def _outcome_metrics(summary: BatchSummary) -> dict:
    o = summary.outcome_counts
    return {
        "escapes": sum(o.get(d, 0) for d in ESCAPES),
        "Half Guard": o.get("Half Guard", 0),
        "Open Guard": o.get("Open Guard", 0),
        "Reversal": o.get("Reversal", 0),
        "timeouts": o.get(TIMEOUT, 0),
        "taps": o.get(TAP, 0),
    }


@lru_cache(maxsize=1)
def criteria() -> tuple[Criterion, ...]:
    r = runs()
    out: list[Criterion] = []

    # 1 — Surfaces A/B preserved; v1e rejected (inactive) there.
    a = _attribution_cell(StaminaEconomySurface("A", r.ab["A"]), SettlementAttributionMode.RULE1_ONLY)
    b = _attribution_cell(StaminaEconomySurface("B", r.ab["B"]), SettlementAttributionMode.RULE1_ONLY)
    ok = ((a.threat_matches, a.threat_entries, a.taps) == (78, 1950, 0) and b.taps == 9
          and all(r.v1e_rejected_on_ab.values()) and r.ab_hold_calls == 0)
    out.append(Criterion("1", "Surface A 78/1950/Tap 0; Surface B Tap 9; v1e inactive on non-RECOVER",
        "PASS" if ok else "FAIL",
        f"A Threat matches/entries/Tap={a.threat_matches}/{a.threat_entries}/{a.taps}; "
        f"B Tap={b.taps}/100; v1e request rejected on A/B={r.v1e_rejected_on_ab}; "
        f"recovery_hold calls on A/B={r.ab_hold_calls}"))

    # 2 — Rule 1 exact; Rule 2 OFF.
    parts, ok = [], True
    for key in RUNS:
        cell = _attribution_cell(StaminaEconomySurface(str(key), r.v1e[key]), SettlementAttributionMode.RULE1_ONLY)
        ok &= (cell.unfunded_responder_spend == 0 and cell.unfunded_initiator_hold_charged == 0
               and cell.hold_covered == 0)
        parts.append(f"{key[0]}/{key[1]} unfunded exchanges={cell.unfunded_initiator_exchanges} "
                     f"responder spend={cell.unfunded_responder_spend} "
                     f"unfunded hold charged={cell.unfunded_initiator_hold_charged} "
                     f"hold covered={cell.hold_covered}")
    out.append(Criterion("2", "Rule 1 exact on unfunded exchanges; Rule 2 OFF", "PASS" if ok else "FAIL",
                         "; ".join(parts)))

    # 3 — stamina bounds, no fabricated recovery, final median.
    bounds_ok, fabricated, negative = True, 0, 0
    for kind in ("v1e",):
        for key in RUNS:
            for v in views()[kind][key]:
                prev = None
                for e in v.events:
                    if "bs" in e and not 0 <= e["bs"] <= 100:
                        bounds_ok = False
                    if prev is not None and "bs" in e and e["bs"] > prev:
                        if not (e["k"] == "adv" and e["behavior"] == "CONSERVE" and e["bs"] - prev == e["bnet"]):
                            fabricated += 1
                    if e["k"] == "att" and e["bs"] > e["b_before"]:
                        negative += 1
                    if "bs" in e:
                        prev = e["bs"]
    cell42 = _cell(r.v1e[(42, "OFF+shadow")], "OFF+shadow")
    ok = bounds_ok and fabricated == 0 and negative == 0 and cell42.bottom_final_median >= C3_FINAL_MEDIAN_MIN
    out.append(Criterion("3", "Bottom stamina in [0,100]; no fabricated recovery/negative cost; final median >=29",
        "PASS" if ok else "FAIL",
        f"bounds ok={bounds_ok}; non-CONSERVE stamina increases={fabricated}; negative costs={negative}; "
        f"original-100 Bottom final median={cell42.bottom_final_median}; "
        f"Bottom setup actions={r.v1e[(42, 'OFF+shadow')].bottom_setup_action_count}, "
        f"completed builds={r.v1e[(42, 'OFF+shadow')].bottom_completed_setup_build_count}"))

    # 4 — original-100 outcome tolerances.
    statuses, parts = [], []
    for stalling in STALLING:
        m = _outcome_metrics(r.v1e[(42, stalling)])
        ok = (m["escapes"] >= C4_ESCAPES_MIN and m["timeouts"] <= C4_TIMEOUTS_MAX
              and m["taps"] <= C4_TAP_MAX
              and all(abs(m[k] - v) <= C4_SPLIT_TOLERANCE for k, v in C4_SPLIT.items()))
        statuses.append("PASS" if ok else "FAIL")
        parts.append(f"{stalling}: escapes={m['escapes']} (>=25), Half/Open/Reversal="
                     f"{m['Half Guard']}/{m['Open Guard']}/{m['Reversal']} (16/10/9 +/-10), "
                     f"timeouts={m['timeouts']} (<=70), Tap={m['taps']} (<=9)")
    out.append(Criterion("4", "Original-100 escapes/exits/timeouts/Tap tolerances", _combine(*statuses), "; ".join(parts)))

    # 5 — RESET-with-route exposure, real offenses, OFF/ON divergence.
    off42 = _cell(r.v1e[(42, "OFF+shadow")], "OFF+shadow")
    exposure142 = _cell(r.v1e[(142, "OFF+shadow")], "OFF+shadow").shadow_bottom_resets_with_route
    offenses = {}
    diverged = {}
    for seed in SEEDS:
        on = _cell(r.v1e[(seed, "ON")], "ON")
        offenses[seed] = (on.bottom_stalling_warnings, on.bottom_stalling_penalties, on.bottom_stalling_position_resets)
        off_rec = r.v1e[(seed, "OFF+shadow")].recovery_policy.matches
        on_rec = r.v1e[(seed, "ON")].recovery_policy.matches
        traj = sum(_first_divergence_for_match(a_, b_) is not None for a_, b_ in zip(off_rec, on_rec))
        hold_div = sum(
            a_[0].recovery_hold_history != b_[0].recovery_hold_history or a_[13] != b_[13]
            for a_, b_ in zip(r.v1e_matches[(seed, "OFF+shadow")], r.v1e_matches[(seed, "ON")])
        )
        diverged[seed] = (traj, hold_div)
    offense_free = all(v == (0, 0, 0) for v in offenses.values())
    ok = (off42.shadow_bottom_resets_with_route <= C5_EXPOSURE_MAX and offense_free
          and all(v == (0, 0) for v in diverged.values()))
    out.append(Criterion("5", "RESET-with-route <=23; no real W/P/PR; OFF/ON divergence 0/100",
        "PASS" if ok else "FAIL",
        f"original-100 exposure={off42.shadow_bottom_resets_with_route} (<=23; seed-142 batch {exposure142}); "
        f"real W/P/PR={offenses}; OFF/ON diverged matches (trajectory, hold/exit)={diverged}"))

    # 6 — digest/unit/checker (external), replay, observer identity, hold isolation.
    control_holds_empty = all(not m[0].recovery_hold_history for key in RUNS for m in r.control_matches[key])
    ok = (all(r.replay_equal.values()) and all(r.plain_identity.values())
          and r.control_hold_calls == 0 and r.ab_hold_calls == 0 and control_holds_empty)
    out.append(Criterion("6", "Deterministic replay; observer ON/OFF identity; recovery_hold isolated to v1e",
        "PASS" if ok else "FAIL",
        f"replay equal={r.replay_equal}; observers ON/OFF identical={r.plain_identity}; "
        f"recovery_hold calls on controls/A/B={r.control_hold_calls}/{r.ab_hold_calls}; "
        f"recovery_hold_history empty on controls={control_holds_empty}. "
        "Digest, unit suite, semantic checker and legacy entry point: see local/CI evidence"))

    # 7 — diagnostic entry-point equivalence; canonical unchanged.
    canonical_unchanged = all(
        gameplay_fields(r.control[(42, s)]) == gameplay_fields(_adopted_reference(s)) for s in STALLING
    )
    route_ok = all(v["settings_equal"] and v["summary_equal"] and v["diverged"] == 0
                   for v in r.canonical_route.values())
    out.append(Criterion("7", "v1e entry-point equivalence; canonical production entry point unchanged",
        "PASS" if route_ok and canonical_unchanged else "FAIL",
        f"v1e explicit vs canonical+v1e route={r.canonical_route}; "
        f"canonical control == adoption diagnostic (seed 42)={canonical_unchanged}"))

    # 8 — historical evidence preserved.
    root = Path(__file__).resolve().parents[3]
    docs = [
        "docs/HANDOFF_OSCILLATION_CHARACTERIZATION_AND_DOD.md",
        "docs/HANDOFF_OSCILLATION_D1_DISTRIBUTIONS.md",
        "docs/HANDOFF_OSCILLATION_D2_PREREGISTRATION.md",
        "docs/HANDOFF_OSCILLATION_D2_PREREGISTRATION_V1B.md",
        "docs/HANDOFF_OSCILLATION_D2_PREREGISTRATION_V1C.md",
        "docs/HANDOFF_OSCILLATION_D2_PREREGISTRATION_V1D.md",
        "docs/HANDOFF_OSCILLATION_D2_PREREGISTRATION_V1E.md",
        "docs/STAMINA_PRODUCTION_POLICY_ADOPTION_VERIFICATION.md",
        "docs/evidence/handoff_d1_trace.json.gz",
    ]
    present = all((root / d).exists() for d in docs) if (root / "docs").exists() else None
    out.append(Criterion("8", "Historical evidence preserved",
        "PASS" if present else ("OPEN" if present is None else "FAIL"),
        f"D1/v1/v1b/v1c/v1d/v1e preregistrations, adoption verification and D1 trace present={present}"))

    # 9-11 — clear-anchored stability.
    for number, h, limit in (("9", 10, C9_RATE_MAX), ("10", 30, C10_RATE_MAX)):
        statuses, parts = [], []
        for stalling in STALLING:
            st = stability(stalling)
            ep, fi = st["episodes"][h], st["first"][h]
            statuses += [_rate_status(ep.reexhausted_within, ep.admissible, limit, C11_MIN),
                         _rate_status(fi.reexhausted_within, fi.admissible, limit, C11_MIN)]
            parts.append(f"{stalling}: episodes {ep.reexhausted_within}/{ep.admissible}"
                         f" (censored {ep.right_censored}); first-clear {fi.reexhausted_within}/"
                         f"{fi.admissible} (censored {fi.right_censored})")
        out.append(Criterion(number, f"Re-exhaustion within {h} s <= {limit}", _combine(*statuses), "; ".join(parts)))
    statuses, parts = [], []
    for stalling in STALLING:
        st = stability(stalling)
        ns = [st["episodes"][10].admissible, st["episodes"][30].admissible,
              st["first"][10].admissible, st["first"][30].admissible]
        statuses.append("PASS" if min(ns) >= C11_MIN else "OPEN")
        parts.append(f"{stalling}: admissible episodes@10/30={ns[0]}/{ns[1]}, first-clear@10/30={ns[2]}/{ns[3]}")
    out.append(Criterion("11", "Pooled denominators >=43 at 10 s and 30 s", _combine(*statuses), "; ".join(parts)))

    # 12 — anti-removal floors.
    statuses, parts = [], []
    for stalling in STALLING:
        orig = [v for v in views()["v1e"][(42, stalling)] if v.clears]
        pool = [v for v in pooled("v1e", stalling) if v.clears]
        med_o = median(v.clears[0] for v in orig) if orig else None
        med_p = median(v.clears[0] for v in pool) if pool else None
        ok = (len(orig) >= C12_ORIGINAL_CLEAR_MIN and len(pool) >= C12_POOLED_CLEAR_MIN
              and med_o is not None and med_o <= C12_MEDIAN_MAX and med_p <= C12_MEDIAN_MAX)
        statuses.append("PASS" if ok else "FAIL")
        parts.append(f"{stalling}: clearing matches original/pooled={len(orig)}/{len(pool)} (>=40/>=75); "
                     f"first-clear median original/pooled={med_o}/{med_p} (<=250)")
    out.append(Criterion("12", "Anti-removal floors", _combine(*statuses), "; ".join(parts)))

    # 13 — clear-window policy handoff.
    statuses, parts = [], []
    for stalling in STALLING:
        hr = handoff_returns(stalling)
        s_ = []
        s_.append("PASS" if hr["matches_with_return"] >= C13_MIN else "OPEN")
        for h, limit in ((10, C9_RATE_MAX), (30, C10_RATE_MAX)):
            row = hr[h]
            s_.append("OPEN" if row["admissible"] < C13_MIN else
                      ("PASS" if row["rate_k"] / row["rate_n"] <= limit else "FAIL"))
        statuses.append(_combine(*s_))
        parts.append(
            f"{stalling}: matches with return={hr['matches_with_return']} (>=43), failed handoffs="
            f"{hr['failed_handoffs']}, pending={hr['pending']}, return delays {_hist(hr['delays'])}; "
            f"+10 s re-entry {hr[10]['rate_k']}/{hr[10]['rate_n']} (admissible returns {hr[10]['admissible']}); "
            f"+30 s re-entry {hr[30]['rate_k']}/{hr[30]['rate_n']} (admissible returns {hr[30]['admissible']})")
    out.append(Criterion("13", "Clear-window policy handoff (return to baseline MEDIUM)", _combine(*statuses), "; ".join(parts)))

    # 14 — required hold diagnostics (reported).
    out.append(Criterion("14", "Hold diagnostics (mandatory reporting)", "REPORTED",
                         "see diagnostics section"))

    # 16 — post-hold return gate.
    statuses, parts = [], []
    for stalling in STALLING:
        g = criterion16(stalling)
        statuses.append(g["status"])
        rate = g["timely"] / g["eligible"] if g["eligible"] else None
        parts.append(
            f"{stalling}: eligible={g['eligible']} (>=35), timely={g['timely']} "
            f"({rate!r}; >=0.80), late={g['late']}, re-exhausted-before-release={g['reexhausted']}, "
            f"pending-at-end={g['pending']} {g['pending_by_outcome']}, ineligible={g['ineligible']}; "
            f"release delay median/p90 eligible={_median(g['delays_eligible'])}/{_p90(g['delays_eligible'])}, "
            f"all={_median(g['delays_all'])}/{_p90(g['delays_all'])}; matches ever releasing={g['matches_ever_releasing']}")
    out.append(Criterion("16", "Post-hold return gate", _combine(*statuses), "; ".join(parts)))
    return tuple(out)


def _median(values):
    return median(values) if values else None


@lru_cache(maxsize=None)
def _adopted_reference(stalling: str) -> BatchSummary:
    """The adoption-measured diagnostic surface (seed 42), re-run here."""
    on = stalling == "ON"
    return run_escape_first_batch(**_surface_e_prod_kwargs(stalling=on, shadow=not on))


def decision() -> str:
    mandatory = [c for c in criteria() if c.status != "REPORTED"]
    return _combine(*(c.status for c in mandatory))


# ---------------------------------------------------------------------------
# Diagnostics (14, 15, 15b, 15c, 15d, drift, prediction vs reality)
# ---------------------------------------------------------------------------


def _v1_decision(s: int) -> str:
    return "MEDIUM" if s - 7 > 25 else ("LOW" if s - 3 > 25 else "HOLD")


def _v1c_decision(s: int) -> str:
    return "MEDIUM" if s - 9 > 25 else ("LOW" if s - 5 > 25 else "HOLD")


def _actual(kind: str) -> str:
    return {"ORDINARY_MEDIUM": "MEDIUM", "RELEASE_MEDIUM": "MEDIUM",
            "ORDINARY_LOW": "LOW", "ENTER_HOLD": "HOLD", "HOLD": "HOLD"}[kind]


def diagnostics(stalling: str) -> dict:
    vs = pooled("v1e", stalling)
    d: dict = {}
    all_cycles = [c for v in vs for c in cycles(v)]
    hold_windows = [(v, i, e) for v in vs for i, e in bottom_windows(v)
                    if e["kind"] in {"ENTER_HOLD", "HOLD"}]
    armed_views = [v for v in vs if v.clears]

    # 14 / 15b — holds.
    per_match = Counter(v.index for v, _, _ in hold_windows)
    d["holds_total"] = len(hold_windows)
    d["holds_per_match"] = _hist(per_match.get(v.index, 0) for v in vs)
    d["holds_per_armed_match"] = _hist(per_match.get(v.index, 0) for v in armed_views)
    runs_ = []
    for v in vs:
        run = 0
        for _, e in bottom_windows(v):
            if e["kind"] in {"ENTER_HOLD", "HOLD"}:
                run += 1
            elif run:
                runs_.append(run)
                run = 0
        if run:
            runs_.append(run)
    d["consecutive_holds"] = _hist(runs_)
    d["longest_consecutive_holds"] = max(runs_) if runs_ else 0
    to_funded = []
    pending_funded = 0
    for v, i, e in hold_windows:
        nxt = next((x for x in v.events[i + 1:] if x["k"] == "att" and x["side"] == "bottom" and x["eff"] is not None), None)
        if nxt is None:
            pending_funded += 1
        else:
            to_funded.append(nxt["t"] - e["t"])
    d["hold_to_funded_initiation"] = _hist(to_funded)
    d["hold_to_funded_pending"] = pending_funded
    d["free_windows_consumed_by_hold"] = sum(1 for _, _, e in hold_windows if e["free"])
    d["holds_builder_available"] = sum(1 for _, _, e in hold_windows if e["builder_available"])
    d["holds_progress_route"] = sum(1 for _, _, e in hold_windows if e["progress_route"])
    d["first_safe_medium_stamina_after_hold"] = _hist(
        c.windows[-1]["bs"] for c in all_cycles if c.end_kind == "RELEASE")
    never = [v for v in vs if cycles(v) and not any(
        c.end_kind == "RELEASE" for c in cycles(v))]
    d["matches_never_returning_to_medium_after_first_hold"] = len(never)
    d["never_release_split"] = dict(Counter(
        "cleared-by-exhaustion" if any(c.end_kind == "CLEARED_BY_EXHAUSTION" or c.reexhausted_t for c in cycles(v))
        else ("ended-by-timeout" if v.outcome == TIMEOUT else "ended-by-exit")
        for v in never))
    lows = [(v, i, e) for v in vs for i, e in bottom_windows(v) if e["kind"] == "ORDINARY_LOW"]
    d["reserve_rule_low_requests"] = len(lows)
    d["reserve_rule_low_preceding"] = _hist(
        next((x["k"] + ("/" + x.get("side", "") if x["k"] in {"att", "reset"} else "")
              for x in reversed(v.events[:i]) if x["k"] in {"att", "reset", "hold"}), "start")
        + f"@{e['bs']}" for v, i, e in lows)
    exhausted_lows = sum(1 for v in vs for e in v.events
                         if e["k"] == "att" and e["side"] == "bottom" and e["bx_before"] and e["req"] == "LOW")
    d["exhausted_low_requests"] = exhausted_lows
    reent = Counter(c for v in vs for _, c, _ in v.reentries)
    d["reentries_by_cause"] = dict(reent)

    # 15 — reserve model + v1/v1c attribution.
    violations, drains, truncated = [], [], 0
    hold_net = Counter()
    hold_net_violations = []
    classes_v1, classes_v1c = Counter(), Counter()
    for v in vs:
        bw = bottom_windows(v)
        for n, (i, e) in enumerate(bw):
            if not e["armed"] or e["bx"]:
                continue
            j = bw[n + 1][0] if n + 1 < len(bw) else len(v.events)
            segment = v.events[i + 1:j]
            drain = -sum(x["bnet"] for x in segment if x["k"] == "adv" and x["bnet"] < 0)
            drains.append(drain)
            if n + 1 >= len(bw):
                truncated += 1
            if drain > 2:
                violations.append(f"m{v.index}@{e['t']}s drain={drain}: " + ",".join(
                    x["k"] + (f"({x.get('side')})" if "side" in x else "") for x in segment))
            actual = _actual(e["kind"])
            for counter, cf in ((classes_v1, _v1_decision(e["bs"])), (classes_v1c, _v1c_decision(e["bs"]))):
                if cf == actual:
                    counter["same"] += 1
                elif counter is classes_v1c and cf == "LOW" and actual == "HOLD" and e["mode_before"]:
                    counter["LOW-safe held by mode"] += 1
                else:
                    counter[f"{cf} -> {actual}"] += 1
            if actual == "HOLD" and n + 1 < len(bw):
                nxt = bw[n + 1][1]
                net = nxt["bs"] - e["bs"]
                hold_net[net] += 1
                if net < 0:
                    hold_net_violations.append(f"m{v.index}@{e['t']}s net={net}")
    d["reserve_predicted"] = 2
    d["behavior_drain_to_next_bottom_window"] = _hist(drains)
    d["reserve_drain_truncated_at_end"] = truncated
    d["reserve_model_violations"] = violations
    d["attribution_vs_v1"] = dict(classes_v1)
    d["attribution_vs_v1c"] = dict(classes_v1c)
    d["hold_net_change_to_next_bottom_window"] = dict(sorted(hold_net.items()))
    d["hold_net_negative"] = hold_net_violations

    # 15b — stalling clock at holds (real on ON; shadow on OFF via trajectory).
    clocks = []
    if stalling == "ON":
        clocks = [e["stall_b"] for _, _, e in hold_windows]
    else:
        r = runs()
        for seed in SEEDS:
            rec = r.v1e[(seed, stalling)].recovery_policy.matches
            for v in views()["v1e"][(seed, stalling)]:
                traj = rec[v.index % 100].trajectory
                wins = [e for e in v.events if e["k"] == "win"]
                if len(traj) != len(wins):
                    raise RuntimeError("trajectory/window alignment failed")
                clocks += [traj[n].shadow_bottom_clock for n, e in enumerate(wins)
                           if e["side"] == "bottom" and e.get("kind") in {"ENTER_HOLD", "HOLD"}]
    d["stalling_clock_at_holds"] = _hist(clocks)
    d["stalling_clock_at_holds_max"] = max(clocks) if clocks else None
    d["holds_at_or_over_threshold"] = sum(1 for c in clocks if c is not None and c >= STALLING_THRESHOLD_SECONDS)
    post_clear_share = []
    for v in armed_views:
        bw = [e for _, e in bottom_windows(v) if e["armed"]]
        if bw:
            post_clear_share.append(sum(1 for e in bw if e["kind"] in {"ENTER_HOLD", "HOLD"}) / len(bw))
    d["matches_over_half_post_clear_windows_held"] = sum(1 for x in post_clear_share if x > 0.5)

    # 15c — cycles and releases.
    d["cycles_total"] = len(all_cycles)
    d["cycles_per_match"] = _hist(len(cycles(v)) for v in vs)
    d["cycle_end_kinds"] = dict(Counter(c.end_kind for c in all_cycles))
    d["cycle_entry_stamina"] = _hist(c.entry["bs"] for c in all_cycles)
    d["release_stamina"] = _hist(c.windows[-1]["bs"] for c in all_cycles if c.end_kind == "RELEASE")
    d["release_delay"] = _hist(c.release_delay for c in all_cycles if c.end_kind == "RELEASE")
    d["holds_before_release"] = _hist(c.holds for c in all_cycles if c.end_kind == "RELEASE")
    d["advances_before_release"] = _hist(c.advances for c in all_cycles if c.end_kind == "RELEASE")
    d["pending_cycles"] = sum(1 for c in all_cycles if c.end_kind == "PENDING_AT_END")
    shares, shares_nx = [], []
    for v in armed_views:
        first = v.clears[0]
        span = v.end_t - first
        if span <= 0:
            continue
        in_mode = 0
        for c in cycles(v):
            end = c.reexhausted_t if c.reexhausted_t is not None else c.end_t
            in_mode += end - c.entry["t"]
        exhausted = 0
        state = None
        last_t = first
        for e in v.events:
            if "bx" not in e or e["t"] < first:
                continue
            if state is True:
                exhausted += e["t"] - last_t
            state, last_t = e["bx"], e["t"]
        shares.append(in_mode / span)
        if span - exhausted > 0:
            shares_nx.append(in_mode / (span - exhausted))
    d["post_clear_time_in_mode_share_median"] = _median(shares)
    d["post_clear_time_in_mode_share_pooled"] = None
    d["post_clear_time_in_mode_share_non_exhausted_median"] = _median(shares_nx)
    after_release_first = []
    release_was_reset = 0
    post_release = {h: Counter() for h in (10, 30)}
    first_release = {h: Counter() for h in (10, 30)}
    for v in vs:
        seen_first = False
        for c in cycles(v):
            if c.end_kind != "RELEASE":
                continue
            nxt = v.events[c.end_pos + 1] if c.end_pos + 1 < len(v.events) else None
            if nxt is not None and nxt["k"] == "reset":
                release_was_reset += 1
            funded = next((x for x in v.events[c.end_pos + 1:] if x["k"] == "att" and x["side"] == "bottom"
                           and x["eff"] is not None), None)
            after_release_first.append(
                f"{funded['action']}/{funded['req']}->{funded['eff']}/{funded['grade']}"
                + (f"/exit={funded['exit']}" if funded and funded["exit"] else "")
                if funded else "none")
            reex = _next_reentry(v, c.end_t, c.end_pos)
            for h in (10, 30):
                st = _status_from(c.end_t, reex, v.end_t, h).value
                post_release[h][st] += 1
                if not seen_first:
                    first_release[h][st] += 1
            seen_first = True
    d["first_funded_action_after_release"] = _hist(after_release_first)
    d["first_requested_after_release"] = _hist(
        next((x["req"] for x in v.events[c.end_pos + 1:] if x["k"] == "att" and x["side"] == "bottom"), "none")
        for v in vs for c in cycles(v) if c.end_kind == "RELEASE")
    d["release_window_policy_reset"] = release_was_reset
    d["post_release_reexhaustion"] = {h: dict(post_release[h]) for h in (10, 30)}
    d["first_release_reexhaustion"] = {h: dict(first_release[h]) for h in (10, 30)}
    d["reexhaustion_in_mode"] = dict(Counter(c.reexhaust_cause for c in all_cycles if c.reexhausted_t is not None))
    d["free_bottom_windows_in_mode"] = sum(1 for v in vs for _, e in bottom_windows(v) if e["free"] and e["mode_before"])

    # 15d — persistent CONSERVE.
    forced = [e for v in vs for e in v.events if e["k"] == "adv" and e["mode"]]
    d["forced_conserve_advances"] = len(forced)
    d["forced_conserve_stamina_gained"] = sum(e["bnet"] for e in forced)
    realized = sum(e["ax"] - e["b0"]["ax"] for e in forced)
    escape = sum(e["escape_axis"] - e["b0"]["ax"] for e in forced if e["escape_axis"] is not None)
    d["forced_drift_realized"] = round(realized, 6)
    d["forced_drift_escape_counterfactual"] = round(escape, 6)
    d["forced_drift_extra_realized"] = round(realized - escape, 6)
    d["forced_advances_clamped_both"] = sum(1 for e in forced if e["b0"]["ax"] >= 4.0 - 1e-9)
    d["forced_advances_band_changed"] = sum(1 for e in forced if e["band_changes"])
    d["forced_advances_band_differs_from_escape"] = sum(1 for e in forced if e["escape_band"] != e["band"])
    d["band_at_entry"] = _hist(c.entry["band"] for c in all_cycles)
    d["band_at_release"] = _hist(c.windows[-1]["band"] for c in all_cycles if c.end_kind == "RELEASE")
    d["bottom_initiations_after_release_by_band"] = _hist(
        x["band_before"] for v in vs for c in cycles(v) if c.end_kind == "RELEASE"
        for x in v.events[c.end_pos + 1:c.end_pos + 2] if x["k"] == "att")
    summaries = runs().v1e
    total_switches = sum(summaries[(s, stalling)].bottom_behavior_switch_count for s in SEEDS)
    mode_flips = 2 * sum(1 for e in forced if e["forced"])
    d["behavior_switches_total"] = total_switches
    d["behavior_switches_mode_induced"] = mode_flips
    d["behavior_switches_other"] = total_switches - mode_flips
    d["windows_seen_equals_rechoice"] = all(
        e["seen_behavior"] == e["policy_behavior"]
        for v in vs for e in v.events if e["k"] == "win" and not e["free"])
    d["a9_consistent"] = all(
        a9_consistent(summaries[(s, stalling)], views()["v1e"][(s, stalling)]) for s in SEEDS)
    return d


def band_comparison(stalling: str) -> dict:
    """Post-first-clear Mount band exposure, v1e vs adopted control."""
    out = {}
    for kind in ("v1e", "control"):
        windows = Counter()
        bottom_inits = Counter()
        for v in pooled(kind, stalling):
            if not v.clears:
                continue
            first = v.clears[0]
            for e in v.events:
                if e["k"] == "win" and e["t"] >= first:
                    windows[e["band"]] += 1
                if e["k"] == "att" and e["side"] == "bottom" and e["t"] >= first:
                    bottom_inits[e["band_before"]] += 1
        total = sum(windows.values())
        out[kind] = {
            "post_clear_windows_by_band": dict(windows),
            "strong_locked_share": (windows["Strong"] + windows["Locked"]) / total if total else None,
            "post_clear_bottom_initiations_by_band": dict(bottom_inits),
        }
    return out


def outcome_comparison(stalling: str) -> dict:
    """Seed-matched per-match outcome change, v1e vs adopted control."""
    pairs = list(zip(pooled("control", stalling), pooled("v1e", stalling)))
    changed = Counter()
    rows = []
    for c, v in pairs:
        if c.outcome == v.outcome:
            continue
        changed[(c.outcome, v.outcome)] += 1
        sl = _strong_locked_share_post_clear(v)
        sl_c = _strong_locked_share_post_clear(c)
        rows.append({"match": v.index, "control": c.outcome, "v1e": v.outcome,
                     "v1e_strong_locked": sl, "control_strong_locked": sl_c,
                     "first_clear": v.clears[0] if v.clears else None})
    lost = [r for r in rows if r["control"] in ESCAPES and r["v1e"] not in ESCAPES]
    gained = [r for r in rows if r["control"] not in ESCAPES and r["v1e"] in ESCAPES]
    return {
        "changed_matches": len(rows),
        "transitions": {f"{a} -> {b}": n for (a, b), n in sorted(changed.items())},
        "escape_lost": len(lost),
        "escape_gained": len(gained),
        "escape_lost_strong_locked_median_v1e": _median([r["v1e_strong_locked"] for r in lost if r["v1e_strong_locked"] is not None]),
        "escape_lost_strong_locked_median_control": _median([r["control_strong_locked"] for r in lost if r["control_strong_locked"] is not None]),
        "rows": rows,
    }


def _strong_locked_share_post_clear(v: MatchView) -> float | None:
    if not v.clears:
        return None
    wins = [e for e in v.events if e["k"] == "win" and e["t"] >= v.clears[0]]
    if not wins:
        return None
    return sum(1 for e in wins if e["band"] in {"Strong", "Locked"}) / len(wins)


def prediction_vs_reality(stalling: str) -> dict:
    vs = pooled("v1e", stalling)
    cycle_lengths, holds_per_cycle = [], []
    medium_after_entry, time_after_entry = 0, 0
    held, bottom_after_entry = 0, 0
    staminas = []
    mode_time = 0
    for v in vs:
        cs = cycles(v)
        if not cs:
            continue
        for a, b in zip(cs, cs[1:]):
            if a.end_kind == "RELEASE":
                cycle_lengths.append(b.entry["t"] - a.entry["t"])
        holds_per_cycle += [c.holds for c in cs if c.end_kind == "RELEASE"]
        t0 = cs[0].entry["t"]
        time_after_entry += v.end_t - t0
        medium_after_entry += sum(1 for e in v.events if e["k"] == "att" and e["side"] == "bottom"
                                  and e["req"] == "MEDIUM" and e["t"] >= t0)
        for _, e in bottom_windows(v):
            if e["t"] >= t0 and not e["bx"]:
                bottom_after_entry += 1
                staminas.append(e["bs"])
                if e["kind"] in {"ENTER_HOLD", "HOLD"}:
                    held += 1
        for c in cs:
            end = c.reexhausted_t if c.reexhausted_t is not None else c.end_t
            mode_time += end - c.entry["t"]
    return {
        "entry_to_next_entry_seconds": _hist(cycle_lengths),
        "holds_per_released_cycle": _hist(holds_per_cycle),
        "medium_initiations_per_100s_after_first_entry": (
            100 * medium_after_entry / time_after_entry if time_after_entry else None),
        "share_bottom_windows_held_after_first_entry": (
            held / bottom_after_entry if bottom_after_entry else None),
        "bottom_window_stamina_range_after_first_entry": (
            (min(staminas), max(staminas)) if staminas else None),
        "time_in_mode_share_after_first_entry": (
            mode_time / time_after_entry if time_after_entry else None),
    }


# ---------------------------------------------------------------------------
# Evidence and report
# ---------------------------------------------------------------------------


def evidence() -> dict:
    r = runs()
    out = {"preregistration": PREREGISTRATION_SHA, "runs": {}}
    for label, store in (("v1e", r.v1e), ("control", r.control)):
        for key in RUNS:
            s = store[key]
            out["runs"][f"{label}/{key[0]}/{key[1]}"] = {
                "outcomes": s.outcome_counts,
                "a9_episodes": [asdict(e) for e in s.reexhaustion_handoffs.episodes],
                "matches": [
                    {"match_index": m.match_index, "outcome": m.outcome, "events": list(m.events)}
                    for m in s.post_clear_handoff.matches
                ],
            }
    out["proofs"] = {
        "replay_equal": {f"{k[0]}/{k[1]}": v for k, v in r.replay_equal.items()},
        "observer_identity": {str(k): v for k, v in r.plain_identity.items()},
        "canonical_route": {f"{k[0]}/{k[1]}": v for k, v in r.canonical_route.items()},
        "instrumented": {f"{k[0]}/{k[1]}": v for k, v in r.instrumented.items()},
        "control_hold_calls": r.control_hold_calls,
        "ab_hold_calls": r.ab_hold_calls,
        "v1e_rejected_on_ab": r.v1e_rejected_on_ab,
    }
    return out


def _fmt(d: dict) -> list[str]:
    lines = []
    for k, v in d.items():
        if isinstance(v, list) and len(v) > 12:
            v = v[:12] + [f"... ({len(v)} total)"]
        lines.append(f"- `{k}`: {v}")
    return lines


def report() -> str:
    lines = ["# D2 v1e measurement data (generated)", "",
             f"Preregistration: `{PREREGISTRATION_SHA}`. Generated by "
             "`python -m bjj_game.diagnostics.handoff_d2_v1e`. Raw evidence: "
             "`docs/evidence/handoff_d2_v1e_evidence.json.gz`.", "",
             f"## Decision: {decision()}", "",
             "| # | Criterion | Status | Evidence |", "|---|---|---|---|"]
    for c in criteria():
        lines.append(f"| {c.number} | {c.title} | **{c.status}** | {c.evidence} |")
    r = runs()
    lines += ["", "## Outcomes (v1e vs adopted control)", "",
              "| Run | Tap | Half | Open | Reversal | Escapes | Timeouts |", "|---|---|---|---|---|---|---|"]
    for label, store in (("v1e", r.v1e), ("control", r.control)):
        for key in RUNS:
            m = _outcome_metrics(store[key])
            lines.append(f"| {label} {key[0]} {key[1]} | {m['taps']} | {m['Half Guard']} | {m['Open Guard']} | "
                         f"{m['Reversal']} | {m['escapes']} | {m['timeouts']} |")
    for stalling in STALLING:
        st = stability(stalling)
        ctl = stability(stalling, "control")
        lines += ["", f"## Clear-anchored horizons — {stalling}", "",
                  "| h | v1e episodes R/adm (cens) | v1e first-clear R/adm (cens) | control episodes R/adm (cens) |",
                  "|---|---|---|---|"]
        for h in HORIZONS:
            e, f, c = st["episodes"][h], st["first"][h], ctl["episodes"][h]
            lines.append(f"| {h} | {e.reexhausted_within}/{e.admissible} ({e.right_censored}) | "
                         f"{f.reexhausted_within}/{f.admissible} ({f.right_censored}) | "
                         f"{c.reexhausted_within}/{c.admissible} ({c.right_censored}) |")
        lines += ["", f"## Diagnostics 14/15/15b/15c/15d — {stalling}", ""]
        lines += _fmt(diagnostics(stalling))
        lines += ["", f"## Mount band exposure after first clear — {stalling}", ""]
        lines += _fmt(band_comparison(stalling))
        oc = outcome_comparison(stalling)
        lines += ["", f"## Seed-matched outcome changes vs control — {stalling}", ""]
        lines += _fmt({k: v for k, v in oc.items() if k != "rows"})
        lines += ["", "| match | control | v1e | first clear | v1e Strong/Locked share | control Strong/Locked share |",
                  "|---|---|---|---|---|---|"]
        for row in oc["rows"]:
            lines.append(f"| {row['match']} | {row['control']} | {row['v1e']} | {row['first_clear']} | "
                         f"{row['v1e_strong_locked']} | {row['control_strong_locked']} |")
        lines += ["", f"## Traced prediction vs reality — {stalling}", "",
                  "Predicted: ~130 s period, 4 MEDIUM + 9 holds, ~69% of Bottom windows held, stamina 26-38.", ""]
        lines += _fmt(prediction_vs_reality(stalling))
        g = criterion16(stalling)
        lines += ["", f"## Criterion 16 first-cycle rows — {stalling}", "",
                  "| match | entry t | remaining | eligible | result | delay | outcome |", "|---|---|---|---|---|---|---|"]
        for row in g["rows"]:
            lines.append(f"| {row['match']} | {row['entry_t']} | {row['remaining']} | {row['eligible']} | "
                         f"{row['result']} | {row['delay']} | {row['outcome']} |")
    lines += ["", "## Inertness / isolation proofs", ""]
    lines += _fmt(evidence()["proofs"])
    return "\n".join(lines) + "\n"


def main() -> None:
    root = Path.cwd()
    evidence_path = root / "docs/evidence/handoff_d2_v1e_evidence.json.gz"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_bytes(gzip.compress(
        (json.dumps(evidence(), sort_keys=True, separators=(",", ":")) + "\n").encode(),
        mtime=0,
    ))
    (root / "docs/HANDOFF_OSCILLATION_D2_V1E_MEASUREMENT_DATA.md").write_text(report())
    print(f"decision={decision()}")
    for c in criteria():
        print(f"{c.number}: {c.status}")


if __name__ == "__main__":
    main()
