"""D3-B frozen measurement and scoring.

Runs exactly the experiment preregistered in
docs/BURST_RECOVERY_LOCKOUT_D3B_PREREGISTRATION.md
(dc4fc16947546dc3277d75dc1fbbd2e3d7a88310): E-PROD, base seeds 42 and 142,
100 matches each, 300 s, stalling OFF + shadow and ON, D3-B enabled; adopted
canonical controls and the frozen v1e comparator on the same seeds.

Not thread-safe (op-trace replays patch class attributes); run standalone.

    python -m bjj_game.diagnostics.handoff_d3b
"""

from __future__ import annotations

from collections import Counter
from contextlib import ExitStack
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from functools import lru_cache
import gzip
import hashlib
import json
from pathlib import Path
import random
from statistics import mean, median
from unittest import mock

from ..domain.stamina import StaminaBand
from ..engine.match import MountMatch
from ..interfaces.batch import BatchSummary, run_escape_first_batch
from ..interfaces.handoff_policy import PostClearHandoffMode
from . import handoff_d2_v1e as d2
from .stamina_adoption_candidate import _surface_ab_kwargs
from .stamina_adoption_verification import _run_captured, effective_settings
from .stamina_economy import StaminaEconomySurface
from .stamina_recovery_policy import (
    SettlementAttributionMode,
    _attribution_cell,
    _first_divergence_for_match,
)

PREREGISTRATION_SHA = "dc4fc16947546dc3277d75dc1fbbd2e3d7a88310"
D3B = PostClearHandoffMode.D3B_EXHAUSTED_TOKEN_LOCKOUT
SEEDS = d2.SEEDS
STALLING = d2.STALLING
RUNS = d2.RUNS
ESCAPES = d2.ESCAPES
TAP = d2.TAP
TIMEOUT = d2.TIMEOUT

# Frozen populations (preregistration section 1; within-batch indices).
G7_POPULATION = (0, 1, 7, 12, 13, 21, 23, 24, 26, 32, 36, 38, 44, 48, 50,
                 51, 56, 68, 69, 74, 75, 76, 88, 90, 96)
G3_ELIGIBLE = {42: (0, 7, 12, 21, 23, 26, 38, 44, 48, 51, 56, 69, 74, 75, 76),
               142: (6, 22, 24, 25, 27, 45, 66, 70, 92, 95)}
TOKEN_WINDOW_ESCAPES = {42: (24, 48, 76), 142: (45,)}

# Frozen gate values.
G3_REMAINING_MIN = 60
G3_ELIGIBLE_MIN = 20
G3_CLEAR_SECONDS = 60
G3_RATE_MIN = 0.80
G7_ESCAPES_MIN = 5
TRACE_CLEAR_SECONDS = {(19, "MEDIUM"): 50, (20, "MEDIUM"): 45, (21, "MEDIUM"): 45,
                       (22, "MEDIUM"): 40, (25, "drain"): 35}


def d3b_kwargs(seed: int, stalling: str) -> dict:
    return {**d2.v1e_kwargs(seed, stalling), "post_clear_handoff_mode": D3B}


def d3b_canonical_route_kwargs(seed: int, stalling: str) -> dict:
    return {**d2.control_kwargs(seed, stalling), "post_clear_handoff_mode": D3B}


def d3b_plain_kwargs(seed: int) -> dict:
    return {**d2.v1e_plain_kwargs(seed), "post_clear_handoff_mode": D3B}


# ---------------------------------------------------------------------------
# Op-level gameplay trace (RNG order included)
# ---------------------------------------------------------------------------


def _scalar(value):
    if is_dataclass(value):
        return _scalar(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _scalar(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        return [_scalar(v) for v in value]
    return value


def _op_trace_run(kwargs: dict) -> tuple[BatchSummary, list[list[tuple]]]:
    """Run once, recording every engine operation per match.

    Each op: (name, inputs, initiator_before, bottom_exhausted_before,
    rng_draws_before, rng_draws_after, post-state). RNG draws are counted per
    match (draws since the match's first operation).
    """
    counter = [0]
    traces: dict[int, list] = {}
    order: list[int] = []
    base: dict[int, int] = {}
    rng_originals = {n: getattr(random.Random, n) for n in ("random", "getrandbits")}

    def counted(name):
        def wrapper(self, *a, **k):
            counter[0] += 1
            return rng_originals[name](self, *a, **k)
        return wrapper

    def op(name):
        original = getattr(MountMatch, name)

        def wrapper(match, *a, **k):
            key = id(match)
            if key not in traces:
                traces[key] = []
                order.append(key)
                base[key] = counter[0]
            initiator = match.initiator.value
            exhausted = match.bottom.stamina.band is StaminaBand.EXHAUSTED
            start = counter[0] - base[key]
            result = original(match, *a, **k)
            traces[key].append((
                name, json.dumps(_scalar(k), sort_keys=True), initiator, exhausted,
                start, counter[0] - base[key],
                (match.clock_seconds, round(match.axis, 10), match.band.value,
                 match.bottom.stamina.current, match.top.stamina.current,
                 match.bottom.stamina.band is StaminaBand.EXHAUSTED,
                 match.initiator.value,
                 match.exit_destination.value if match.exit_destination else None,
                 match.exit_reason,
                 json.dumps(_scalar(match.setup_state), sort_keys=True),
                 json.dumps(_scalar(match.submission_state), sort_keys=True),
                 json.dumps(_scalar(match.stalling_tracker), sort_keys=True)),
            ))
            return result
        return wrapper

    with ExitStack() as stack:
        for n in rng_originals:
            stack.enter_context(mock.patch.object(random.Random, n, counted(n)))
        for n in ("advance", "attempt", "reset_window", "recovery_hold"):
            stack.enter_context(mock.patch.object(MountMatch, n, op(n)))
        summary = run_escape_first_batch(**kwargs)
    return summary, [traces[k] for k in order]


def token_op_index(trace: list[tuple]) -> int | None:
    """Index of the first armed-Exhausted Bottom attempt/RESET (the token)."""
    armed = False
    prev_exhausted = False
    for i, entry in enumerate(trace):
        name, _, initiator, exhausted_before = entry[:4]
        if name in {"attempt", "reset_window"} and initiator == "bottom" and armed and exhausted_before:
            return i
        exhausted_after = entry[6][5]
        if name == "advance" and prev_exhausted and not exhausted_after:
            armed = True
        prev_exhausted = exhausted_after
    return None


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Runs:
    d3b: dict
    d3b_matches: dict
    replay_equal: dict
    plain_identity: dict
    canonical_route: dict
    d3b_traces: dict
    control_traces: dict
    trace_summary_equal: dict
    rejected_on_ab: dict
    instrumented: dict


@lru_cache(maxsize=1)
def runs() -> Runs:
    d3b, d3b_matches = {}, {}
    for key in RUNS:
        d3b[key], d3b_matches[key] = _run_captured(d3b_kwargs(*key))
    replay_equal = {}
    for key in RUNS:
        summary, matches = _run_captured(d3b_kwargs(*key))
        replay_equal[key] = summary == d3b[key] and matches == d3b_matches[key]
    plain_identity = {}
    for seed in SEEDS:
        summary, matches = _run_captured(d3b_plain_kwargs(seed))
        plain_identity[seed] = (
            d2.gameplay_fields(summary) == d2.gameplay_fields(d3b[(seed, "OFF+shadow")])
            and matches == d3b_matches[(seed, "OFF+shadow")]
        )
    canonical_route = {}
    for key in RUNS:
        route = d3b_canonical_route_kwargs(*key)
        summary, matches = _run_captured(route)
        canonical_route[key] = {
            "settings_equal": effective_settings(route) == effective_settings(d3b_kwargs(*key)),
            "summary_equal": summary == d3b[key],
            "diverged": sum(a != b for a, b in zip(matches, d3b_matches[key])),
        }
    d3b_traces, control_traces, trace_equal = {}, {}, {}
    controls = d2.runs().control
    for key in RUNS:
        s1, d3b_traces[key] = _op_trace_run(d3b_kwargs(*key))
        s2, control_traces[key] = _op_trace_run(d2.control_kwargs(*key))
        trace_equal[key] = (s1 == d3b[key], s2 == controls[key])
    rejected = {}
    for name, label in (("A", "A public MATCH"), ("B", "B trusts reads")):
        try:
            run_escape_first_batch(**{**_surface_ab_kwargs(label), "matches": 1,
                                      "post_clear_handoff_mode": D3B})
            rejected[name] = False
        except ValueError:
            rejected[name] = True
    instrumented = {}
    for key in RUNS:
        summary, proof = d2._instrumented_run(d3b_kwargs(*key))
        proof["summary_equal_to_uninstrumented"] = summary == d3b[key]
        instrumented[key] = proof
    return Runs(d3b, d3b_matches, replay_equal, plain_identity, canonical_route,
                d3b_traces, control_traces, trace_equal, rejected, instrumented)


@lru_cache(maxsize=1)
def views() -> dict:
    r = runs()
    return {key: d2.match_views(r.d3b[key], *key) for key in RUNS}


def pooled(stalling: str, kind: str = "d3b") -> list:
    if kind == "d3b":
        v = views()
    else:
        v = d2.views()[kind]
    return v[(42, stalling)] + v[(142, stalling)]


# ---------------------------------------------------------------------------
# Episodes
# ---------------------------------------------------------------------------


@dataclass
class Episode:
    view: object
    number: int
    entry_t: int
    entry_pos: int
    entry_stamina: int
    cause: str
    entry_kind: str  # MEDIUM / LOW / drain / responder / other
    end_kind: str  # CLEARED / PENDING_AT_END
    end_t: int
    end_pos: int
    token_window: dict | None
    token_result: dict | None
    windows: list

    @property
    def token_escape(self) -> bool:
        r = self.token_result
        return r is not None and r["k"] == "att" and r["exit"] in ESCAPES

    @property
    def duration(self) -> int:
        return self.end_t - self.entry_t


def episodes(view) -> list[Episode]:
    events = view.events
    out = []
    if not view.clears:
        return out
    first_clear = view.clears[0]
    prev = None
    armed = False
    current = None
    for pos, e in enumerate(events):
        if "bx" in e:
            if prev is not None and prev and not e["bx"]:
                if current is not None:
                    current.update(end_kind="CLEARED", end_t=e["t"], end_pos=pos)
                    out.append(current)
                    current = None
                armed = True
            elif prev is not None and not prev and e["bx"] and armed:
                if e["k"] == "adv":
                    entry_kind = "drain"
                elif e["k"] == "att" and e["side"] == "bottom":
                    entry_kind = e["req"]
                elif e["k"] == "att":
                    entry_kind = "responder"
                else:
                    entry_kind = "other"
                current = dict(entry_t=e["t"], entry_pos=pos, entry_stamina=e["bs"],
                               cause=d2._cause(e), entry_kind=entry_kind,
                               windows=[], token_window=None, token_result=None)
            prev = e["bx"]
        if current is not None and e["k"] == "win" and e["side"] == "bottom" and pos >= current["entry_pos"]:
            current["windows"].append(e)
            if e.get("kind") == "TOKEN" and current["token_window"] is None:
                current["token_window"] = e
                current["token_result"] = events[pos + 1] if pos + 1 < len(events) else None
    if current is not None:
        current.update(end_kind="PENDING_AT_END", end_t=view.end_t, end_pos=len(events) - 1)
        out.append(current)
    return [Episode(view=view, number=i, **{k: c[k] for k in (
        "entry_t", "entry_pos", "entry_stamina", "cause", "entry_kind", "end_kind",
        "end_t", "end_pos", "token_window", "token_result", "windows")})
        for i, c in enumerate(out)]


def _hist(values):
    return d2._hist(values)


def _escape_attempt(view):
    return next((e for e in view.events if e["k"] == "att" and e["exit"] in ESCAPES), None)


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Gate:
    gate_id: str
    title: str
    status: str
    evidence: str


def g3(stalling: str) -> dict:
    rows = []
    for v in pooled(stalling):
        eps = episodes(v)
        if not eps:
            continue
        ep = eps[0]
        if v.end_t <= ep.entry_t:
            continue  # the entry attempt ended the match
        seed = v.seed
        remaining = v.initial_clock - ep.entry_t
        if ep.token_escape:
            result = "token-escape"
        elif ep.end_kind == "CLEARED":
            result = "cleared<=60" if ep.duration <= G3_CLEAR_SECONDS else "late-clear"
        elif v.outcome in ESCAPES:
            result = "bottom-exit-before-clear-not-token"
        elif v.outcome == TAP:
            result = "tap-before-clear"
        elif v.outcome == TIMEOUT:
            result = "timeout-before-clear"
        else:
            result = "other-terminal-before-clear"
        still_exhausted_at_60 = (
            result not in {"token-escape", "cleared<=60"}
            and min(ep.end_t, v.end_t) - ep.entry_t >= G3_CLEAR_SECONDS
        )
        rows.append({"seed": seed, "match": v.index % 100, "entry_t": ep.entry_t,
                     "still_exhausted_at_60": still_exhausted_at_60,
                     "remaining": remaining, "eligible": remaining >= G3_REMAINING_MIN,
                     "result": result, "duration": ep.duration if ep.end_kind == "CLEARED" else None,
                     "entry_stamina": ep.entry_stamina, "outcome": v.outcome})
    eligible = [r for r in rows if r["eligible"]]
    counts = Counter(r["result"] for r in eligible)
    success = counts["token-escape"] + counts["cleared<=60"]
    frozen = {seed: tuple(sorted(r["match"] for r in eligible if r["seed"] == seed)) for seed in SEEDS}
    out = {"rows": rows, "eligible": len(eligible), "success": success, "counts": dict(counts),
           "continued_after_token": sum(1 for r in eligible if r["result"] != "token-escape"),
           "still_exhausted_at_60": sum(1 for r in eligible if r["still_exhausted_at_60"]),
           "eligible_matches": frozen,
           "population_matches_frozen": frozen == {s: tuple(sorted(G3_ELIGIBLE[s])) for s in SEEDS}}
    if len(eligible) < G3_ELIGIBLE_MIN:
        out["status"] = "OPEN"
    else:
        out["status"] = "PASS" if success / len(eligible) >= G3_RATE_MIN else "FAIL"
    return out


def g7(stalling: str) -> dict:
    v1e = {v.index: v for v in d2.views()["v1e"][(42, stalling)]}
    control = {v.index: v for v in d2.views()["control"][(42, stalling)]}
    d3b = {v.index: v for v in views()[(42, stalling)]}
    rows = []
    for idx in G7_POPULATION:
        v, c, e = d3b[idx], control[idx], v1e[idx]
        esc = _escape_attempt(v) if v.outcome in ESCAPES else None
        first_clear = v.clears[0] if v.clears else None
        detail = None
        if esc is not None:
            eps = [ep for ep in episodes(v) if ep.entry_t <= esc["t"]]
            last = eps[-1] if eps else None
            kind = "?"
            window = next((w for w in reversed(v.events[:v.events.index(esc)])
                           if w["k"] == "win" and w["side"] == esc["side"]), None)
            if window is not None:
                kind = window.get("kind")
            detail = {
                "side": esc["side"], "axis_before": window["ax"] if window is not None else None,
                "t": esc["t"], "since_first_clear": esc["t"] - first_clear if first_clear is not None else None,
                "since_episode_entry": esc["t"] - last.entry_t if last else None,
                "decision": kind, "action": esc["action"], "req": esc["req"], "eff": esc["eff"],
                "band": esc["band_before"], "exhausted": esc["bx_before"], "exit": esc["exit"],
            }
        rows.append({"match": idx, "adopted": c.outcome, "v1e": e.outcome, "d3b": v.outcome,
                     "escape": detail,
                     "by_construction": idx in TOKEN_WINDOW_ESCAPES[42],
                     "relation": (None if v.outcome not in ESCAPES else
                                  "replaces adopted escape" if c.outcome in ESCAPES else "new escape")})
    escapes = sum(1 for r in rows if r["d3b"] in ESCAPES)
    return {"rows": rows, "escapes": escapes,
            "status": "PASS" if escapes >= G7_ESCAPES_MIN else "FAIL"}


def g6() -> dict:
    r = runs()
    out = {}
    for key in RUNS:
        mismatches = []
        for i, (t_d, t_c) in enumerate(zip(r.d3b_traces[key], r.control_traces[key])):
            cut = token_op_index(t_d)
            if cut is None:
                if t_d != t_c:
                    mismatches.append(i)
            elif t_d[:cut + 1] != t_c[:cut + 1]:
                mismatches.append(i)
        out[key] = {"matches": len(r.d3b_traces[key]), "mismatches": mismatches,
                    "traces_equal_summaries": r.trace_summary_equal[key]}
    # Frozen populations reproduced from the D3-B prefix.
    pops = {}
    for stalling in STALLING:
        g7_pop = tuple(sorted(v.index for v in views()[(42, stalling)]
                              if episodes(v) and v.end_t > episodes(v)[0].entry_t))
        token_escapes = {seed: tuple(sorted(v.index % 100 for v in views()[(seed, stalling)]
                                            if episodes(v) and episodes(v)[0].token_escape))
                         for seed in SEEDS}
        pops[stalling] = {"g7_population": g7_pop == G7_POPULATION,
                          "g3_population": g3(stalling)["population_matches_frozen"],
                          "token_escapes": token_escapes == TOKEN_WINDOW_ESCAPES}
    # The 18 adopted +10 s MEDIUM escapes v1e lost.
    restored = {}
    for stalling in STALLING:
        rows = d2.outcome_comparison(stalling)["rows"]
        ten = [row["match"] for row in rows if row["control_escape_attempt"]
               and "(+10s) MEDIUM" in row["control_escape_attempt"]
               and row["control"] in ESCAPES and row["v1e"] not in ESCAPES]
        d3b = {v.index: v.outcome for v in pooled(stalling)}
        control = {v.index: v.outcome for v in pooled(stalling, "control")}
        restored[stalling] = {"count": len(ten),
                              "restored": sum(1 for m in ten if d3b[m] == control[m])}
    out["populations"] = pops
    out["plus10_restored"] = restored
    ok = (all(not v["mismatches"] and all(v["traces_equal_summaries"]) for k, v in out.items() if k in RUNS)
          and all(all(p.values()) for p in pops.values())
          and all(v["count"] == 18 and v["restored"] == 18 for v in restored.values()))
    out["status"] = "PASS" if ok else "FAIL"
    return out


def g1_g2(stalling: str) -> dict:
    violations_g1, violations_g2 = [], []
    tokens = locks = episodes_with_window = 0
    for v in pooled(stalling):
        eps = episodes(v)
        for ep in eps:
            bottom_windows = [w for w in ep.windows]
            if bottom_windows:
                episodes_with_window += 1
            kinds = [w.get("kind") for w in bottom_windows if w["bx"]]
            if kinds:
                if kinds[0] != "TOKEN" or any(k != "LOCKOUT_HOLD" for k in kinds[1:]):
                    violations_g2.append(f"m{v.index}@{ep.entry_t}:{kinds}")
            tokens += kinds.count("TOKEN")
            locks += kinds.count("LOCKOUT_HOLD")
            # G1: no Bottom initiation after the token while the episode lasts.
            if ep.token_window is not None:
                start = v.events.index(ep.token_window) + 2
                for e in v.events[start:ep.end_pos + 1]:
                    if e["k"] in {"att", "reset"} and e["side"] == "bottom":
                        violations_g1.append(f"m{v.index}@{e['t']}:{e['k']}")
        for e in v.events:
            if e["k"] == "win" and e["side"] == "bottom" and e.get("kind") == "LOCKOUT_HOLD" and not (e["bx"] and e["armed"]):
                violations_g2.append(f"m{v.index}@{e['t']}:lockout-while-not-armed-exhausted")
            if e["k"] == "win" and e["side"] == "bottom" and e.get("kind") == "TOKEN" and not (e["bx"] and e["armed"]):
                violations_g2.append(f"m{v.index}@{e['t']}:token-while-not-armed-exhausted")
    return {"g1_violations": violations_g1, "g2_violations": violations_g2,
            "tokens": tokens, "lockout_holds": locks, "episodes_with_window": episodes_with_window,
            "g1": "PASS" if not violations_g1 else "FAIL",
            "g2": "PASS" if not violations_g2 else "FAIL"}


@lru_cache(maxsize=1)
def gates() -> tuple[Gate, ...]:
    r = runs()
    base = d2.runs()
    out = []

    a = _attribution_cell(StaminaEconomySurface("A", base.ab["A"]), SettlementAttributionMode.RULE1_ONLY)
    b = _attribution_cell(StaminaEconomySurface("B", base.ab["B"]), SettlementAttributionMode.RULE1_ONLY)
    ok = ((a.threat_matches, a.threat_entries, a.taps) == (78, 1950, 0) and b.taps == 9
          and all(r.rejected_on_ab.values()) and base.ab_hold_calls == 0)
    out.append(Gate("P1", "Surface A 78/1950/0; B Tap 9; D3-B inactive off E-PROD", "PASS" if ok else "FAIL",
                    f"A {a.threat_matches}/{a.threat_entries}/{a.taps}; B Tap {b.taps}; "
                    f"D3-B rejected on A/B={r.rejected_on_ab}; recovery_hold calls on A/B={base.ab_hold_calls}"))

    parts, ok = [], True
    for key in RUNS:
        cell = _attribution_cell(StaminaEconomySurface(str(key), r.d3b[key]), SettlementAttributionMode.RULE1_ONLY)
        ok &= (cell.unfunded_responder_spend == 0 and cell.unfunded_initiator_hold_charged == 0
               and cell.hold_covered == 0)
        parts.append(f"{key[0]}/{key[1]}: unfunded={cell.unfunded_initiator_exchanges} responder spend="
                     f"{cell.unfunded_responder_spend} hold charged={cell.unfunded_initiator_hold_charged} "
                     f"covered={cell.hold_covered}")
    out.append(Gate("P2", "Rule 1 exact; Rule 2 OFF", "PASS" if ok else "FAIL", "; ".join(parts)))

    bounds_ok, fabricated, negative = True, 0, 0
    for key in RUNS:
        for v in views()[key]:
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
    cell42 = d2._cell(r.d3b[(42, "OFF+shadow")], "OFF+shadow")
    ok = bounds_ok and fabricated == 0 and negative == 0 and cell42.bottom_final_median >= d2.C3_FINAL_MEDIAN_MIN
    out.append(Gate("P3", "Stamina bounds; no fabricated recovery; final median >=29", "PASS" if ok else "FAIL",
                    f"bounds={bounds_ok}; non-CONSERVE increases={fabricated}; negative costs={negative}; "
                    f"original-100 Bottom final median={cell42.bottom_final_median}"))

    statuses, parts = [], []
    for stalling in STALLING:
        m = d2._outcome_metrics(r.d3b[(42, stalling)])
        ok = (m["escapes"] >= d2.C4_ESCAPES_MIN and m["timeouts"] <= d2.C4_TIMEOUTS_MAX and m["taps"] <= d2.C4_TAP_MAX
              and all(abs(m[k] - v) <= d2.C4_SPLIT_TOLERANCE for k, v in d2.C4_SPLIT.items()))
        statuses.append("PASS" if ok else "FAIL")
        parts.append(f"{stalling}: escapes={m['escapes']}, Half/Open/Reversal={m['Half Guard']}/"
                     f"{m['Open Guard']}/{m['Reversal']}, timeouts={m['timeouts']}, Tap={m['taps']}")
    out.append(Gate("P4", "Original-100 escapes>=25, exits +/-10, timeouts<=70, Tap<=9", d2._combine(*statuses),
                    "; ".join(parts)))

    off42 = d2._cell(r.d3b[(42, "OFF+shadow")], "OFF+shadow")
    offenses, diverged = {}, {}
    for seed in SEEDS:
        on = d2._cell(r.d3b[(seed, "ON")], "ON")
        offenses[seed] = (on.bottom_stalling_warnings, on.bottom_stalling_penalties,
                          on.bottom_stalling_position_resets, r.d3b[(seed, "ON")].top_stalling_warning_count,
                          r.d3b[(seed, "ON")].top_stalling_penalty_count,
                          r.d3b[(seed, "ON")].top_stalling_position_reset_count)
        off_rec = r.d3b[(seed, "OFF+shadow")].recovery_policy.matches
        on_rec = r.d3b[(seed, "ON")].recovery_policy.matches
        traj = sum(_first_divergence_for_match(x, y) is not None for x, y in zip(off_rec, on_rec))
        holds = sum(x[0].recovery_hold_history != y[0].recovery_hold_history or x[13] != y[13]
                    for x, y in zip(r.d3b_matches[(seed, "OFF+shadow")], r.d3b_matches[(seed, "ON")]))
        diverged[seed] = (traj, holds)
    ok = (off42.shadow_bottom_resets_with_route <= d2.C5_EXPOSURE_MAX
          and all(all(x == 0 for x in v) for v in offenses.values())
          and all(v == (0, 0) for v in diverged.values()))
    out.append(Gate("P5", "RESET-with-route <=23; any real offense FAILS; OFF/ON divergence 0", "PASS" if ok else "FAIL",
                    f"original-100 exposure={off42.shadow_bottom_resets_with_route}; real Bottom W/P/PR and "
                    f"Top W/P/PR={offenses}; OFF/ON diverged (trajectory, hold/exit)={diverged}"))

    stored = json.loads(gzip.decompress((_root() / "docs/evidence/handoff_d2_v1e_evidence.json.gz").read_bytes()))
    regenerated = json.loads(json.dumps(d2.evidence(), sort_keys=True, separators=(",", ":")))
    v1e_ok = regenerated == stored
    control_empty = all(not m[0].recovery_hold_history for key in RUNS for m in base.control_matches[key])
    ok = (all(r.replay_equal.values()) and all(r.plain_identity.values()) and base.control_hold_calls == 0
          and base.ab_hold_calls == 0 and control_empty and v1e_ok)
    out.append(Gate("P6", "Replay; observer identity; hold isolation; v1e reproduces fe229cb", "PASS" if ok else "FAIL",
                    f"replay={r.replay_equal}; observers ON/OFF identical={r.plain_identity}; recovery_hold calls "
                    f"controls/A/B={base.control_hold_calls}/{base.ab_hold_calls}; control holds empty={control_empty}; "
                    f"v1e evidence regenerated == stored fe229cb evidence: {v1e_ok}. Digest/suite/checkers: see "
                    "local/CI evidence"))

    canonical_unchanged = all(d2.gameplay_fields(base.control[(42, s)]) == d2.gameplay_fields(d2._adopted_reference(s))
                              for s in STALLING)
    route_ok = all(v["settings_equal"] and v["summary_equal"] and v["diverged"] == 0 for v in r.canonical_route.values())
    out.append(Gate("P7", "D3-B entry-point equivalence; canonical unchanged", "PASS" if route_ok and canonical_unchanged else "FAIL",
                    f"explicit vs canonical+D3-B={r.canonical_route}; canonical control == adoption diagnostic={canonical_unchanged}"))

    root = _root()
    docs = ["docs/HANDOFF_OSCILLATION_D2_PREREGISTRATION_V1E.md", "docs/HANDOFF_OSCILLATION_D2_PREREGISTRATION_V1F.md",
            "docs/HANDOFF_OSCILLATION_D2_V1E_RESULT.md", "docs/evidence/handoff_d2_v1e_evidence.json.gz",
            "docs/BURST_RECOVERY_LOCKOUT_D3_RESEARCH_AND_PREREGISTRATION.md",
            "docs/BURST_RECOVERY_LOCKOUT_D3B_PREREGISTRATION.md", "docs/evidence/handoff_d1_trace.json.gz",
            "docs/HANDOFF_OSCILLATION_CHARACTERIZATION_AND_DOD.md"]
    present = all((root / d).exists() for d in docs)
    out.append(Gate("P8", "Historical evidence preserved", "PASS" if present else "FAIL", f"present={present}"))

    statuses, parts = [], []
    for stalling in STALLING:
        orig = [v for v in views()[(42, stalling)] if v.clears]
        pool = [v for v in pooled(stalling) if v.clears]
        mo = median(v.clears[0] for v in orig) if orig else None
        mp = median(v.clears[0] for v in pool) if pool else None
        ok = (len(orig) >= 40 and len(pool) >= 75 and mo is not None and mo <= 250
              and mp is not None and mp <= 250)
        statuses.append("PASS" if ok else "FAIL")
        parts.append(f"{stalling}: clearing {len(orig)}/{len(pool)}; first-clear median {mo}/{mp}")
    out.append(Gate("P9", "Anti-removal floors", d2._combine(*statuses), "; ".join(parts)))

    s1, s2, parts = [], [], []
    for stalling in STALLING:
        g = g1_g2(stalling)
        s1.append(g["g1"])
        s2.append(g["g2"])
        parts.append(f"{stalling}: tokens={g['tokens']}, lockout holds={g['lockout_holds']}, "
                     f"G1 violations={g['g1_violations'][:5]}, G2 violations={g['g2_violations'][:5]}")
    out.append(Gate("G1", "No Bottom initiation spend after the token", d2._combine(*s1), "; ".join(parts)))
    out.append(Gate("G2", "Token and lockout exactness", d2._combine(*s2), "; ".join(parts)))

    statuses, parts = [], []
    for stalling in STALLING:
        g = g3(stalling)
        statuses.append(g["status"])
        parts.append(f"{stalling}: eligible={g['eligible']} (>=20; frozen population reproduced="
                     f"{g['population_matches_frozen']}), successes={g['success']} "
                     f"({g['success'] / g['eligible'] if g['eligible'] else None!r}; >=0.80), breakdown={g['counts']}")
    out.append(Gate("G3", "Bounded recovery after the token", d2._combine(*statuses), "; ".join(parts)))

    g = g6()
    out.append(Gate("G6", "Prefix identity through the token; populations; +10 s escapes", g["status"],
                    f"op-trace prefix mismatches={ {f'{k[0]}/{k[1]}': v['mismatches'] for k, v in g.items() if k in RUNS} }; "
                    f"populations reproduced={g['populations']}; +10 s MEDIUM escapes restored={g['plus10_restored']}"))

    statuses, parts = [], []
    for stalling in STALLING:
        g = g7(stalling)
        statuses.append(g["status"])
        parts.append(f"{stalling}: Bottom escapes in frozen 25 = {g['escapes']} (>=5)")
    out.append(Gate("G7", "Affected-match tactical retention", d2._combine(*statuses), "; ".join(parts)))
    return tuple(out)


def decision() -> str:
    return d2._combine(*(g.status for g in gates()))


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


def diagnostics(stalling: str) -> dict:
    vs = pooled(stalling)
    eps = [ep for v in vs for ep in episodes(v)]
    d = {}
    d["episodes_total"] = len(eps)
    d["episodes_per_match"] = _hist(len(episodes(v)) for v in vs)
    per = sorted(len(episodes(v)) for v in vs if episodes(v))
    d["episodes_per_armed_match_median_p90_max"] = (median(per), d2._p90(per), max(per)) if per else None
    cleared = [ep for ep in eps if ep.end_kind == "CLEARED"]
    d["episode_end"] = dict(Counter(ep.end_kind for ep in eps))
    d["entry_cases"] = dict(Counter(f"{ep.entry_stamina}/{ep.entry_kind}" for ep in eps))
    by_case = {}
    for ep in cleared:
        by_case.setdefault(f"{ep.entry_stamina}/{ep.entry_kind}", []).append(ep.duration)
    d["entry_to_clear_by_case"] = {k: _hist(v) for k, v in sorted(by_case.items())}
    off_trace = []
    for ep in cleared:
        key = (ep.entry_stamina, "drain" if ep.entry_kind == "drain" else ep.entry_kind)
        expected = TRACE_CLEAR_SECONDS.get(key)
        if expected is None or ep.duration != expected:
            ledger = [
                (e["k"], e.get("side"), e["t"], e["bs"], e.get("resp_charged"), e.get("bnet"))
                for e in ep.view.events[ep.entry_pos:ep.end_pos + 1]
                if e["k"] in {"adv", "att"} and (e["k"] != "att" or e["side"] == "top" or e["bs"] != e.get("b_before"))
            ]
            off_trace.append({"match": ep.view.index, "entry": ep.entry_t, "case": f"{ep.entry_stamina}/{ep.entry_kind}",
                              "duration": ep.duration, "expected": expected, "ledger": ledger})
    d["episodes_off_trace"] = off_trace
    d["durations"] = (min(x.duration for x in cleared), median(x.duration for x in cleared),
                      max(x.duration for x in cleared)) if cleared else None
    d["episodes_under_25s_or_unexplained"] = [f"m{ep.view.index}@{ep.entry_t}" for ep in cleared if ep.duration < 25]
    # G4: clear -> next entry
    gaps = []
    for v in vs:
        es = episodes(v)
        for a, b in zip(es, es[1:]):
            if a.end_kind == "CLEARED":
                gaps.append(b.entry_t - a.end_t)
    d["clear_to_next_entry"] = _hist(gaps)
    d["clear_to_next_entry_within_10s_share"] = (sum(1 for g in gaps if g <= 10) / len(gaps)) if gaps else None
    # Token.
    tok = [ep for ep in eps if ep.token_window is not None]
    d["token_decisions"] = dict(Counter(("TOKEN_LOW" if ep.token_result["k"] == "att" else "TOKEN_RESET")
                                        for ep in tok if ep.token_result))
    d["token_attempts"] = _hist(f"{ep.token_result['action']}/{ep.token_result['eff']}/{ep.token_result['grade']}"
                                for ep in tok if ep.token_result and ep.token_result["k"] == "att")
    d["token_exits"] = dict(Counter(ep.token_result["exit"] for ep in tok
                                    if ep.token_result and ep.token_result["k"] == "att" and ep.token_result["exit"]))
    d["token_free_windows"] = sum(1 for ep in tok if ep.token_window["free"])
    d["token_band"] = _hist(ep.token_window["band"] for ep in tok)
    # Lockout opportunities.
    locks = [e for v in vs for e in v.events if e["k"] == "win" and e.get("kind") == "LOCKOUT_HOLD"]
    d["lockout_holds"] = len(locks)
    d["lockout_counterfactual_action"] = _hist(e.get("cf_action") for e in locks)
    d["lockout_progress_route"] = sum(1 for e in locks if e.get("progress_route"))
    d["lockout_builder_available"] = sum(1 for e in locks if e.get("builder_available"))
    d["lockout_free_windows"] = sum(1 for e in locks if e["free"])
    d["lockout_stalling_clock_bottom"] = _hist(e["stall_b"] for e in locks) if stalling == "ON" else "shadow only"
    # Stamina ledger inside episodes.
    ledger = Counter()
    top_attempts_in_lockout = 0
    for ep in eps:
        for e in ep.view.events[ep.entry_pos + 1:ep.end_pos + 1]:
            if e["k"] == "adv":
                ledger["CONSERVE recovery" if e["bnet"] > 0 else "behavior drain"] += abs(e["bnet"])
            elif e["k"] == "att" and e["side"] == "bottom":
                ledger["initiation spend (token)"] += e["b_before"] - e["bs"]
            elif e["k"] == "att":
                top_attempts_in_lockout += 1
                ledger["response commitment"] += e["resp_charged"]
                ledger["provisional hold / other"] += (e["b_before"] - e["bs"]) - e["resp_charged"]
    d["episode_stamina_ledger"] = dict(ledger)
    d["top_attempts_during_episodes"] = top_attempts_in_lockout
    top_in_eps = [e for ep in eps for e in ep.view.events[ep.entry_pos + 1:ep.end_pos + 1]
                  if e["k"] == "att" and e["side"] == "top"]
    d["top_attempts_during_episodes_by_effective"] = _hist(e["eff"] for e in top_in_eps)
    d["top_attempts_during_episodes_bottom_charged"] = sum(1 for e in top_in_eps if e["b_before"] != e["bs"])
    d["token_stamina"] = _hist(ep.token_window["bs"] for ep in tok)
    d["clear_stamina"] = _hist(ep.view.events[ep.end_pos]["bs"] for ep in cleared)
    d["lockout_holds_per_episode"] = _hist(sum(1 for w in ep.windows if w.get("kind") == "LOCKOUT_HOLD")
                                           for ep in eps)
    d["entry_stamina"] = _hist(ep.entry_stamina for ep in eps)
    d["lockout_counterfactual_request"] = "LOW (adopted LOW_WHILE_EXHAUSTED; every hold is Exhausted)"
    # Tactical effect.
    def counts(kind):
        out = Counter()
        for v in pooled(stalling, kind) if kind != "d3b" else vs:
            if not v.clears:
                continue
            fc = v.clears[0]
            for e in v.events:
                if e["k"] == "att" and e["side"] == "bottom" and e["t"] >= fc:
                    out["after first clear"] += 1
                    out["while Exhausted" if e["bx_before"] else "non-Exhausted"] += 1
                    out[f"req {e['req']}"] += 1
        return dict(out)
    d["bottom_attempts_post_clear"] = {k: counts(k) for k in ("d3b", "control", "v1e")}
    summaries = {"d3b": runs().d3b, "control": d2.runs().control, "v1e": d2.runs().v1e}
    d["setup_and_submission"] = {
        k: {"bottom setup actions": sum(s[(seed, stalling)].bottom_setup_action_count for seed in SEEDS),
            "bottom completed builds": sum(s[(seed, stalling)].bottom_completed_setup_build_count for seed in SEEDS),
            "Threat/Control/Finish matches": tuple(
                sum(getattr(s[(seed, stalling)], f) for seed in SEEDS)
                for f in ("matches_reached_submission_threat", "matches_reached_submission_control",
                          "matches_reached_submission_finish"))}
        for k, s in summaries.items()}
    return d


def episode_records(stalling: str) -> list[dict]:
    rows = []
    for v in pooled(stalling):
        for ep in episodes(v):
            entry = v.events[ep.entry_pos]
            tw, tr = ep.token_window, ep.token_result
            rows.append({
                "match": v.index, "episode": ep.number, "entry_t": ep.entry_t,
                "remaining_at_entry": v.initial_clock - ep.entry_t, "entry_stamina": ep.entry_stamina,
                "cause": ep.cause, "entry_kind": ep.entry_kind, "entry_event": entry["k"],
                "entry_action": entry.get("action"), "entry_req": entry.get("req"), "entry_eff": entry.get("eff"),
                "entry_axis": entry["ax"], "entry_band": entry["band"],
                "token": (None if tr is None else "TOKEN_LOW" if tr["k"] == "att" else
                          "TOKEN_RESET" if tr["k"] == "reset" else tr["k"]),
                "token_t": tw["t"] if tw else None, "token_free": tw["free"] if tw else None,
                "token_stamina": tw["bs"] if tw else None, "token_band": tw["band"] if tw else None,
                "token_action": tr.get("action") if tr else None, "token_eff": tr.get("eff") if tr else None,
                "token_grade": tr.get("grade") if tr else None, "token_exit": tr.get("exit") if tr else None,
                "lockout_holds": sum(1 for w in ep.windows if w.get("kind") == "LOCKOUT_HOLD"),
                "end": ep.end_kind, "duration": ep.duration,
                "clear_stamina": v.events[ep.end_pos]["bs"] if ep.end_kind == "CLEARED" else None,
                "match_outcome": v.outcome,
            })
    return rows


def band_comparison(stalling: str) -> dict:
    out = {}
    for kind in ("d3b", "control", "v1e"):
        vs = pooled(stalling) if kind == "d3b" else pooled(stalling, kind)
        windows, axes = Counter(), []
        for v in vs:
            if not v.clears:
                continue
            for e in v.events:
                if e["k"] == "win" and e["t"] >= v.clears[0]:
                    windows[e["band"]] += 1
                    axes.append(e["ax"])
        total = sum(windows.values())
        out[kind] = {"post_clear_windows_by_band": dict(windows),
                     "strong_locked_share": (windows["Strong"] + windows["Locked"]) / total if total else None,
                     "mean_axis_post_clear": round(mean(axes), 4) if axes else None}
    return out


def transitions(stalling: str, comparator: str) -> dict:
    ref = {v.index: v for v in pooled(stalling, comparator)}
    rows, counter = [], Counter()
    for v in pooled(stalling):
        c = ref[v.index]
        if c.outcome == v.outcome:
            continue
        counter[f"{c.outcome} -> {v.outcome}"] += 1
        esc = _escape_attempt(v) if v.outcome in ESCAPES else None
        rows.append({"match": v.index, comparator: c.outcome, "d3b": v.outcome,
                     "class": ("escape lost" if c.outcome in ESCAPES and v.outcome not in ESCAPES else
                               "new escape" if v.outcome in ESCAPES and c.outcome not in ESCAPES else
                               "exit-type change" if v.outcome in ESCAPES else
                               "Tap change" if TAP in (c.outcome, v.outcome) else "other"),
                     "d3b_escape_t_since_clear": (esc["t"] - v.clears[0]) if esc and v.clears else None})
    return {"changed": len(rows), "transitions": dict(sorted(counter.items())),
            "classes": dict(Counter(r["class"] for r in rows)), "rows": rows}


def prediction_vs_reality(stalling: str) -> dict:
    vs = pooled(stalling)
    shares = Counter()
    for v in vs:
        eps = episodes(v)
        if not eps:
            continue
        t0 = eps[0].entry_t
        for e in v.events:
            if e["k"] == "win" and e["side"] == "bottom" and e["t"] > t0:
                k = e.get("kind")
                if k == "ARMED_NORMAL":
                    i = v.events.index(e)
                    nxt = v.events[i + 1] if i + 1 < len(v.events) else None
                    k = f"ARMED_NORMAL/{nxt['req'] if nxt and nxt['k'] == 'att' else (nxt['k'] if nxt else 'end')}"
                shares[k] += 1
    return {"predicted": "entry 19 -> clear 50 s; super-cycle 19 (60 s) -> 20 (60 s) -> drain 25 (50 s); "
                         "8 attempts / 17 Bottom windows",
            "bottom_window_decisions_after_first_entry": dict(shares)}


# ---------------------------------------------------------------------------
# Evidence and report
# ---------------------------------------------------------------------------


def evidence() -> dict:
    r = runs()
    out = {"preregistration": PREREGISTRATION_SHA, "runs": {}}
    for key in RUNS:
        s = r.d3b[key]
        out["runs"][f"d3b/{key[0]}/{key[1]}"] = {
            "outcomes": s.outcome_counts,
            "matches": [{"match_index": m.match_index, "outcome": m.outcome, "events": list(m.events)}
                        for m in s.post_clear_handoff.matches],
        }
    def digest(trace):
        return hashlib.sha256(json.dumps(trace, sort_keys=True).encode()).hexdigest()

    out["op_trace_prefix"] = {}
    for key in RUNS:
        rows = []
        for t_d, t_c in zip(r.d3b_traces[key], r.control_traces[key]):
            cut = token_op_index(t_d)
            end = len(t_d) if cut is None else cut + 1
            rows.append({"token_op": cut, "d3b_prefix_sha256": digest(t_d[:end]),
                         "control_prefix_sha256": digest(t_c[:end]),
                         "d3b_full_sha256": digest(t_d), "control_full_sha256": digest(t_c)})
        out["op_trace_prefix"][f"{key[0]}/{key[1]}"] = rows
    out["episodes"] = {stalling: episode_records(stalling) for stalling in STALLING}
    out["comparator_evidence"] = {
        "file": "docs/evidence/handoff_d2_v1e_evidence.json.gz (fe229cb; adopted control + v1e event logs)",
        "sha256": hashlib.sha256((_root() / "docs/evidence/handoff_d2_v1e_evidence.json.gz").read_bytes()).hexdigest(),
    }
    out["proofs"] = {
        "replay_equal": {f"{k[0]}/{k[1]}": v for k, v in r.replay_equal.items()},
        "observer_identity": {str(k): v for k, v in r.plain_identity.items()},
        "canonical_route": {f"{k[0]}/{k[1]}": v for k, v in r.canonical_route.items()},
        "instrumented": {f"{k[0]}/{k[1]}": v for k, v in r.instrumented.items()},
        "trace_summary_equal": {f"{k[0]}/{k[1]}": list(v) for k, v in r.trace_summary_equal.items()},
        "rejected_on_ab": r.rejected_on_ab,
    }
    return out


def _fmt(d: dict) -> list[str]:
    lines = []
    for k, v in d.items():
        if isinstance(v, list) and len(v) > 15:
            v = v[:15] + [f"... ({len(v)} total)"]
        lines.append(f"- `{k}`: {v}")
    return lines


def report() -> str:
    lines = ["# D3-B measurement data (generated)", "",
             f"Preregistration: `{PREREGISTRATION_SHA}`. Generated by `python -m bjj_game.diagnostics.handoff_d3b`. "
             "Raw evidence: `docs/evidence/handoff_d3b_evidence.json.gz`.", "",
             f"## Decision: {decision()}", "", "| Gate | Title | Status | Evidence |", "|---|---|---|---|"]
    for g in gates():
        lines.append(f"| {g.gate_id} | {g.title} | **{g.status}** | {g.evidence} |")
    r, base = runs(), d2.runs()
    lines += ["", "## Outcomes", "", "| Run | Tap | Half | Open | Reversal | Escapes | Timeouts |", "|---|---|---|---|---|---|---|"]
    for label, store in (("D3-B", r.d3b), ("adopted", base.control), ("v1e", base.v1e)):
        for key in RUNS:
            m = d2._outcome_metrics(store[key])
            lines.append(f"| {label} {key[0]} {key[1]} | {m['taps']} | {m['Half Guard']} | {m['Open Guard']} | "
                         f"{m['Reversal']} | {m['escapes']} | {m['timeouts']} |")
    for stalling in STALLING:
        g = g7(stalling)
        lines += ["", f"## G7 frozen population — {stalling}", "",
                  f"Escapes: {g['escapes']} (>=5 required; 3 preserved by the token by construction).", "",
                  "| match | adopted | v1e | D3-B | relation | D3-B escaping attempt |", "|---|---|---|---|---|---|"]
        for row in g["rows"]:
            lines.append(f"| {row['match']} | {row['adopted']} | {row['v1e']} | {row['d3b']} | "
                         f"{row['relation'] or ''}{' (token, by construction)' if row['by_construction'] and row['d3b'] in ESCAPES else ''} | "
                         f"{row['escape'] or ''} |")
        g = g3(stalling)
        lines += ["", f"## G3 breakdown — {stalling}", "",
                  f"eligible={g['eligible']}, token escapes={g['counts'].get('token-escape', 0)}, "
                  f"continued after token={g['continued_after_token']}, cleared<=60 s={g['counts'].get('cleared<=60', 0)}, "
                  f"late clears={g['counts'].get('late-clear', 0)}, Tap before clear={g['counts'].get('tap-before-clear', 0)}, "
                  f"timeout before clear={g['counts'].get('timeout-before-clear', 0)}, "
                  f"other terminal={g['counts'].get('other-terminal-before-clear', 0)}, "
                  f"Bottom exit before clear (not token)={g['counts'].get('bottom-exit-before-clear-not-token', 0)}, "
                  f"still Exhausted 60 s after entry={g['still_exhausted_at_60']}", "",
                  "| seed | match | entry t | remaining | eligible | entry stamina | result | entry->clear | outcome |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for row in g["rows"]:
            lines.append(f"| {row['seed']} | {row['match']} | {row['entry_t']} | {row['remaining']} | {row['eligible']} | "
                         f"{row['entry_stamina']} | {row['result']} | {row['duration']} | {row['outcome']} |")
        lines += ["", f"## Diagnostics — {stalling}", ""] + _fmt(diagnostics(stalling))
        lines += ["", f"## Band / drift after first clear — {stalling}", ""] + _fmt(band_comparison(stalling))
        for comparator in ("control", "v1e"):
            t = transitions(stalling, comparator)
            name = "adopted" if comparator == "control" else "v1e"
            lines += ["", f"## Seed-matched transitions, {name} vs D3-B — {stalling}", ""]
            lines += _fmt({k: v for k, v in t.items() if k != "rows"})
            lines += ["", f"| match | {name} | D3-B | class | D3-B escape t since clear |", "|---|---|---|---|---|"]
            for row in t["rows"]:
                lines.append(f"| {row['match']} | {row[comparator]} | {row['d3b']} | {row['class']} | "
                             f"{row['d3b_escape_t_since_clear']} |")
        lines += ["", f"## Prediction vs reality — {stalling}", ""] + _fmt(prediction_vs_reality(stalling))
        cols = ("match", "episode", "entry_t", "remaining_at_entry", "entry_stamina", "entry_kind", "cause",
                "entry_band", "token", "token_t", "token_free", "token_stamina", "token_action", "token_eff",
                "token_band", "token_exit", "lockout_holds", "end", "duration", "clear_stamina", "match_outcome")
        lines += ["", f"## Episode records — {stalling}", "", "| " + " | ".join(cols) + " |",
                  "|" + "---|" * len(cols)]
        for row in episode_records(stalling):
            lines.append("| " + " | ".join(str(row[c]) for c in cols) + " |")
    g = g6()
    lines += ["", "## G6 detail", ""] + _fmt({k if isinstance(k, str) else f"{k[0]}/{k[1]}": v for k, v in g.items()})
    lines += ["", "## Proofs", ""] + _fmt({k: v for k, v in evidence()["proofs"].items()})
    return "\n".join(lines) + "\n"


def main() -> None:
    root = Path.cwd()
    path = root / "docs/evidence/handoff_d3b_evidence.json.gz"
    path.write_bytes(gzip.compress(
        (json.dumps(evidence(), sort_keys=True, separators=(",", ":")) + "\n").encode(), mtime=0))
    (root / "docs/BURST_RECOVERY_LOCKOUT_D3B_MEASUREMENT_DATA.md").write_text(report())
    print(f"decision={decision()}")
    for g in gates():
        print(f"{g.gate_id}: {g.status}")


if __name__ == "__main__":
    main()
