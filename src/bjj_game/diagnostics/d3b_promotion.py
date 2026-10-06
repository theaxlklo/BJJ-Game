"""D3-B production-promotion frozen equivalence verification (PG1-PG9).

Implements docs/BURST_RECOVERY_LOCKOUT_D3B_PROMOTION_PREREGISTRATION.md
(1eb0a30). Not a candidate measurement: it proves that the canonical
PRODUCTION_STAMINA_RECOVERY_POLICY route reproduces the measured diagnostic
D3-B of 1b96ffc exactly, on the frozen seeds 42/142, 100 matches, 300 s,
OFF + shadow and ON.

    python -m bjj_game.diagnostics.d3b_promotion REFERENCE_1b96ffc.json

REFERENCE_1b96ffc.json is produced by d3b_promotion_reference.py run against
a 1b96ffc source tree (PG5/PG6). Not thread-safe (patches module state).
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import gzip
import json
from pathlib import Path
import subprocess
import sys
from unittest import mock

from ..interfaces.batch import BatchBehaviorMode
from ..interfaces.handoff_policy import PostClearHandoffMode
from ..interfaces.production_policy import (
    GATE_G_STAMINA_RECOVERY_POLICY,
    PRODUCTION_STAMINA_RECOVERY_POLICY,
)
from . import d3b_promotion_reference as ref
from . import handoff_d2_v1e as d2
from . import handoff_d3b as d3
from .stamina_adoption_candidate import _surface_e_prod_kwargs
from .stamina_adoption_verification import _run_captured, effective_settings

PREREGISTRATION_SHA = "1eb0a30ad2896dad53f9248e218c3da9a48ab557"
D3B_RESULT_SHA = "1b96ffc4ae60307e1c7842ca1d46fea540457c69"
# Qualified promotion head (PR #11). PG8 reviews the fixed historical interval
# D3B_RESULT_SHA -> PROMOTION_HEAD_SHA, never the current HEAD.
PROMOTION_HEAD_SHA = "0aa23db5089476982eb6eaf94d91b316d857cee1"
RUNS = d3.RUNS
D3B = PostClearHandoffMode.D3B_EXHAUSTED_TOKEN_LOCKOUT

# Exactly the measured D3-B values (1b96ffc) that PG3 must reproduce.
FROZEN_D3B = {
    "original_100": {"escapes": 30, "Half Guard": 17, "Open Guard": 5, "Reversal": 8,
                     "timeouts": 65, "taps": 5},
    "seed_142": {"escapes": 31, "Half Guard": 24, "Open Guard": 6, "Reversal": 1,
                 "timeouts": 65, "taps": 4},
    "p3_median": 29.0,
    "p5_exposure": 13,
    "g1_g2": (53, 97, 0, 0),
    "g3": (25, 25),
    "g6": {"mismatches": 0, "plus10": (18, 18), "token_escapes": True},
    "g7": (5, (12, 24, 38, 48, 76)),
}
# PG4(b): the hook-removed canonical run must equal the Gate-G adopted control.
GATE_G_ORIGINAL_100 = {"escapes": 35, "Half Guard": 16, "Open Guard": 10, "Reversal": 9,
                       "timeouts": 60, "taps": 5}
ALLOWED_PATHS = (
    "src/bjj_game/interfaces/production_policy.py",
    "src/bjj_game/diagnostics/handoff_characterization.py",
    "src/bjj_game/diagnostics/handoff_d2_v1e.py",
    "src/bjj_game/diagnostics/stamina_adoption_verification.py",
    "src/bjj_game/diagnostics/d3b_promotion.py",
    "src/bjj_game/diagnostics/d3b_promotion_reference.py",
    "tests/",
    "docs/",
)
FORBIDDEN_PATHS = (
    "src/bjj_game/engine/",
    "src/bjj_game/interfaces/batch.py",
    "src/bjj_game/interfaces/handoff_policy.py",
    "src/bjj_game/domain/",
    "src/bjj_game/diagnostics/handoff_d3b.py",
)


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


def canonical_kwargs(seed: int, stalling: str) -> dict:
    """E-PROD with every stamina/recovery setting from the canonical policy."""
    on = stalling == "ON"
    base = {k: v for k, v in _surface_e_prod_kwargs(stalling=on, shadow=not on, base_seed=seed).items()
            if k not in d2.POLICY_KEYS}
    return {**base,
            **PRODUCTION_STAMINA_RECOVERY_POLICY.batch_settings(
                bottom_behavior_mode=base["bottom_behavior_mode"]),
            "measure_post_clear_handoff": True}


def hook_removed_kwargs(seed: int, stalling: str) -> dict:
    """PG4 negative control: canonical route with the D3-B hook removed (test-only)."""
    return {k: v for k, v in canonical_kwargs(seed, stalling).items() if k != "post_clear_handoff_mode"}


# ---------------------------------------------------------------------------
# Equivalence checker (PG2 / PG4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Captured:
    summary: object
    matches: tuple
    traces: list


def capture(kwargs: dict) -> Captured:
    summary, matches = _run_captured(kwargs)
    trace_summary, raw = d3._op_trace_run(kwargs)
    if trace_summary != summary:
        raise RuntimeError("op-trace run diverged from captured run")
    return Captured(summary, matches, d3.split_op_traces(raw, summary))


def compare(a: Captured, b: Captured) -> dict:
    events_a = [m.events for m in a.summary.post_clear_handoff.matches]
    events_b = [m.events for m in b.summary.post_clear_handoff.matches]
    diverged = sorted(
        i for i in range(max(len(a.matches), len(b.matches)))
        if i >= len(a.matches) or i >= len(b.matches)
        or a.matches[i] != b.matches[i] or events_a[i] != events_b[i] or a.traces[i] != b.traces[i]
    )
    return {"summary_equal": a.summary == b.summary, "matches": len(a.matches),
            "diverged": diverged,
            "diverged_captured": sum(x != y for x, y in zip(a.matches, b.matches)),
            "diverged_event_logs": sum(x != y for x, y in zip(events_a, events_b)),
            "diverged_op_traces": sum(x != y for x, y in zip(a.traces, b.traces))}


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------


@contextmanager
def _d3b_route(kwargs_fn):
    """Score the frozen D3-B pipeline with its candidate kwargs from kwargs_fn."""
    caches = (d3.runs, d3.views, d3.gates)
    for c in caches:
        c.cache_clear()
    try:
        with mock.patch.object(d3, "d3b_kwargs", kwargs_fn):
            yield
    finally:
        for c in caches:
            c.cache_clear()


def pg1() -> dict:
    rows = {f"{s}/{m}": effective_settings(canonical_kwargs(s, m)) == effective_settings(d3.d3b_kwargs(s, m))
            for s, m in RUNS}
    return {"status": "PASS" if all(rows.values()) else "FAIL", "settings_equal": rows}


def pg2_pg4() -> tuple[dict, dict]:
    pg2, pg4 = {}, {}
    stored = json.loads(gzip.decompress((_root() / "docs/evidence/handoff_d2_v1e_evidence.json.gz").read_bytes()))
    base = d2.runs()
    for seed, stalling in RUNS:
        key = f"{seed}/{stalling}"
        diag = capture(d3.d3b_kwargs(seed, stalling))
        canon = capture(canonical_kwargs(seed, stalling))
        removed = capture(hook_removed_kwargs(seed, stalling))
        pg2[key] = compare(canon, diag)
        neg = compare(removed, diag)
        stored_events = [m["events"] for m in stored["runs"][f"control/{key}"]["matches"]]
        removed_events = json.loads(json.dumps(
            [list(m.events) for m in removed.summary.post_clear_handoff.matches]))
        pg4[key] = {
            "diverged_vs_diagnostic_d3b": len(neg["diverged"]),
            "diverged_matches": neg["diverged"],
            "equals_gate_g_control_summary": removed.summary == base.control[(seed, stalling)],
            "equals_gate_g_control_captured": removed.matches == base.control_matches[(seed, stalling)],
            "equals_stored_fe229cb_control_events": removed_events == stored_events,
            "outcomes": d2._outcome_metrics(removed.summary),
        }
    ok2 = all(v["summary_equal"] and v["matches"] == 100 and not v["diverged"] for v in pg2.values())
    ok4 = all(v["diverged_vs_diagnostic_d3b"] >= 1 and v["equals_gate_g_control_summary"]
              and v["equals_gate_g_control_captured"] and v["equals_stored_fe229cb_control_events"]
              for v in pg4.values())
    ok4 = ok4 and all(pg4[f"42/{m}"]["outcomes"] == GATE_G_ORIGINAL_100 for m in d3.STALLING)
    return ({"status": "PASS" if ok2 else "FAIL", "runs": pg2},
            {"status": "PASS" if ok4 else "FAIL", "runs": pg4})


def pg3() -> dict:
    committed_evidence = json.loads(gzip.decompress(
        (_root() / "docs/evidence/handoff_d3b_evidence.json.gz").read_bytes()))
    committed_report = (_root() / "docs/BURST_RECOVERY_LOCKOUT_D3B_MEASUREMENT_DATA.md").read_text()
    with _d3b_route(canonical_kwargs):
        r = d3.runs()
        evidence_equal = json.loads(json.dumps(d3.evidence(), sort_keys=True)) == committed_evidence
        report_equal = d3.report() == committed_report
        gates = {g.gate_id: g.status for g in d3.gates()}
        measured = {
            "original_100": [d2._outcome_metrics(r.d3b[(42, m)]) for m in d3.STALLING],
            "seed_142": [d2._outcome_metrics(r.d3b[(142, m)]) for m in d3.STALLING],
            "p3_median": d2._cell(r.d3b[(42, "OFF+shadow")], "OFF+shadow").bottom_final_median,
            "p5_exposure": d2._cell(r.d3b[(42, "OFF+shadow")], "OFF+shadow").shadow_bottom_resets_with_route,
            "g1_g2": [(g["tokens"], g["lockout_holds"], len(g["g1_violations"]), len(g["g2_violations"]))
                      for g in (d3.g1_g2(m) for m in d3.STALLING)],
            "g3": [(g["eligible"], g["success"]) for g in (d3.g3(m) for m in d3.STALLING)],
            "g6": d3.g6(),
            "g7": [(g["escapes"], tuple(sorted(row["match"] for row in g["rows"] if row["d3b"] in d3.ESCAPES)))
                   for g in (d3.g7(m) for m in d3.STALLING)],
            "gate_evidence": {g.gate_id: g.evidence for g in d3.gates()},
        }
    g6 = measured["g6"]
    g6_flat = {
        "mismatches": sum(len(g6[k]["mismatches"]) for k in RUNS),
        "plus10": tuple({(v["count"], v["restored"]) for v in g6["plus10_restored"].values()})[0]
        if len({(v["count"], v["restored"]) for v in g6["plus10_restored"].values()}) == 1 else None,
        "token_escapes": all(p["token_escapes"] for p in g6["populations"].values()),
        "matches_per_run": [g6[k]["matches"] for k in RUNS],
    }
    exact = (
        all(m == FROZEN_D3B["original_100"] for m in measured["original_100"])
        and all(m == FROZEN_D3B["seed_142"] for m in measured["seed_142"])
        and measured["p3_median"] == FROZEN_D3B["p3_median"]
        and measured["p5_exposure"] == FROZEN_D3B["p5_exposure"]
        and all(v == FROZEN_D3B["g1_g2"] for v in measured["g1_g2"])
        and all(v == FROZEN_D3B["g3"] for v in measured["g3"])
        and g6_flat["mismatches"] == 0 and g6_flat["plus10"] == FROZEN_D3B["g6"]["plus10"]
        and g6_flat["token_escapes"] and g6_flat["matches_per_run"] == [100] * 4
        and all(v == FROZEN_D3B["g7"] for v in measured["g7"])
    )
    ok = exact and evidence_equal and report_equal and set(gates.values()) == {"PASS"}
    return {"status": "PASS" if ok else "FAIL", "exact_frozen_values": exact,
            "evidence_byte_identical": evidence_equal, "report_identical": report_equal,
            "d3b_gates": gates, "measured": {k: v for k, v in measured.items() if k != "g6"},
            "g6": g6_flat}


def pg5_pg6(reference: dict) -> tuple[dict, dict]:
    current = ref.reference()
    pg5 = {
        "batch_defaults_equal": current["batch_defaults"] == reference["batch_defaults"],
        "match_defaults_equal": current["match_defaults"] == reference["match_defaults"],
        "post_clear_handoff_mode_default": current["batch_defaults"]["post_clear_handoff_mode"],
        "raw_default_batch_equal": current["raw_default_batch"] == reference["raw_default_batch"],
    }
    pg5["status"] = "PASS" if (pg5["batch_defaults_equal"] and pg5["match_defaults_equal"]
                               and pg5["raw_default_batch_equal"]
                               and pg5["post_clear_handoff_mode_default"] == repr(PostClearHandoffMode.NONE)) else "FAIL"
    settings_equal = {}
    for name in ("A", "B"):
        base = ref.diagnostic_kwargs(name)
        mode = base.get("bottom_behavior_mode", BatchBehaviorMode.FIXED)
        settings_equal[name] = (PRODUCTION_STAMINA_RECOVERY_POLICY.batch_settings(bottom_behavior_mode=mode)
                                == GATE_G_STAMINA_RECOVERY_POLICY.batch_settings(bottom_behavior_mode=mode))
    p1 = next(g for g in d3.gates() if g.gate_id == "P1")
    holds = 0
    original_hold = d3.MountMatch.recovery_hold

    def counted(self, *a, **k):
        nonlocal holds
        holds += 1
        return original_hold(self, *a, **k)

    with mock.patch.object(d3.MountMatch, "recovery_hold", counted):
        for name in ("A", "B"):
            _run_captured(ref.canonical_surface_kwargs(name))
    pg6 = {
        "settings_equal_to_gate_g": settings_equal,
        "gameplay_equal_to_1b96ffc": {n: current[f"canonical_{n}"] == reference[f"canonical_{n}"] for n in ("A", "B")},
        "recovery_hold_calls": holds,
        "p1_values": p1.evidence,
    }
    pg6["status"] = "PASS" if (all(settings_equal.values()) and all(pg6["gameplay_equal_to_1b96ffc"].values())
                               and holds == 0 and "A 78/1950/0; B Tap 9" in p1.evidence) else "FAIL"
    return pg5, pg6


def pg7() -> dict:
    p = PRODUCTION_STAMINA_RECOVERY_POLICY
    flags = {"rule1": p.unfunded_responder_cost_waiver, "rule2": p.supplemental_hold_settlement,
             "umbrella": p.match_settings()["enable_stamina_settlement_rules"],
             "recover_low": p.exhausted_recovery_initiation.value,
             "post_clear_handoff": p.post_clear_handoff_mode.value}
    with _d3b_route(canonical_kwargs):
        p2 = next(g for g in d3.gates() if g.gate_id == "P2")
    ok = (flags == {"rule1": True, "rule2": False, "umbrella": False, "recover_low": "LOW_WHILE_EXHAUSTED",
                    "post_clear_handoff": D3B.value} and p2.status == "PASS")
    return {"status": "PASS" if ok else "FAIL", "flags": flags, "rule1_rule2_on_canonical_runs": p2.evidence}


def pg8() -> dict:
    """Nothing bundled between the measured D3-B result and the qualified promotion."""
    changed = subprocess.run(["git", "diff", "--name-only", D3B_RESULT_SHA, PROMOTION_HEAD_SHA], cwd=_root(),
                             capture_output=True, text=True, check=True).stdout.split()
    forbidden = [p for p in changed if p.startswith(FORBIDDEN_PATHS)]
    unexpected = [p for p in changed if not p.startswith(ALLOWED_PATHS)]
    return {"status": "PASS" if not forbidden and not unexpected else "FAIL",
            "changed_since_1b96ffc": changed, "forbidden": forbidden, "unexpected": unexpected}


def pg9() -> dict:
    snapshot = (_root() / "docs/evidence/d3b_promotion/pre_promotion_canonical_policy_outputs.txt").read_text()
    p = GATE_G_STAMINA_RECOVERY_POLICY
    lines = [repr(sorted(p.match_settings().items()))]
    for m in BatchBehaviorMode:
        lines.append(f"{m.value} {sorted(p.batch_settings(bottom_behavior_mode=m).items(), key=lambda kv: kv[0])!r}")
    # Same text as print() produced for the snapshot (str(), not format()).
    lines.append(" ".join(map(str, (p.unfunded_responder_cost_waiver, p.supplemental_hold_settlement,
                                    p.exhausted_recovery_initiation))))
    equal = "\n".join(lines) + "\n" == snapshot
    independent = p is not PRODUCTION_STAMINA_RECOVERY_POLICY and p.post_clear_handoff_mode is PostClearHandoffMode.NONE
    stored = json.loads(gzip.decompress((_root() / "docs/evidence/handoff_d2_v1e_evidence.json.gz").read_bytes()))
    fe229cb = json.loads(json.dumps(d2.evidence(), sort_keys=True, separators=(",", ":"))) == stored
    ok = equal and independent and fe229cb
    return {"status": "PASS" if ok else "FAIL", "gate_g_outputs_equal_pre_promotion": equal,
            "gate_g_independent_instance": independent, "fe229cb_evidence_reproduced": fe229cb,
            "pinned_suites": "Gate G, D1, v1e and D3-B pinned tests: see local/CI evidence"}


def verify(reference: dict) -> dict:
    out = {"preregistration": PREREGISTRATION_SHA, "d3b_result": D3B_RESULT_SHA}
    out["PG1"] = pg1()
    out["PG2"], out["PG4"] = pg2_pg4()
    out["PG3"] = pg3()
    out["PG5"], out["PG6"] = pg5_pg6(reference)
    out["PG7"] = pg7()
    out["PG8"] = pg8()
    out["PG9"] = pg9()
    out["reference_1b96ffc"] = reference
    statuses = [out[g]["status"] for g in ("PG1", "PG2", "PG3", "PG4", "PG5", "PG6", "PG7", "PG8", "PG9")]
    out["decision_PG1_PG9"] = d2._combine(*statuses)
    return out


def report(result: dict) -> str:
    lines = ["# D3-B promotion verification data (generated)", "",
             f"Preregistration `{PREREGISTRATION_SHA}`; reproduces D3-B `{D3B_RESULT_SHA}`. "
             "Generated by `python -m bjj_game.diagnostics.d3b_promotion`. "
             "Raw evidence: `docs/evidence/d3b_promotion/verification.json.gz`. "
             "PG10/PG11 (digest, checkers, suites, CI) are recorded in the result document.", "",
             f"## PG1-PG9: {result['decision_PG1_PG9']}", "", "| Gate | Status |", "|---|---|"]
    for g in ("PG1", "PG2", "PG3", "PG4", "PG5", "PG6", "PG7", "PG8", "PG9"):
        lines.append(f"| {g} | **{result[g]['status']}** |")
    for g in ("PG1", "PG2", "PG3", "PG4", "PG5", "PG6", "PG7", "PG8", "PG9"):
        lines += ["", f"## {g}", "", "```text", json.dumps(result[g], indent=1, sort_keys=True, default=repr), "```"]
    return "\n".join(lines) + "\n"


def main() -> None:
    reference = json.loads(Path(sys.argv[1]).read_text())
    result = verify(reference)
    root = Path.cwd()
    out = root / "docs/evidence/d3b_promotion"
    out.mkdir(parents=True, exist_ok=True)
    (out / "verification.json.gz").write_bytes(gzip.compress(
        (json.dumps(result, sort_keys=True, default=repr) + "\n").encode(), mtime=0))
    (out / "reference_1b96ffc.json").write_text(json.dumps(reference, indent=1, sort_keys=True) + "\n")
    (root / "docs/BURST_RECOVERY_LOCKOUT_D3B_PROMOTION_VERIFICATION_DATA.md").write_text(report(result))
    print(f"PG1-PG9={result['decision_PG1_PG9']}")
    for g in ("PG1", "PG2", "PG3", "PG4", "PG5", "PG6", "PG7", "PG8", "PG9"):
        print(f"{g}: {result[g]['status']}")


if __name__ == "__main__":
    main()
