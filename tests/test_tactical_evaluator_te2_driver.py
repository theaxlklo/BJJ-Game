"""TE-2 measurement driver and CLI (diagnostics/tactical_evaluator_te2.py):
scoring, PASS / FAIL / OPEN logic, the preflight guard, the authoritative
lock, the one-process lock, budgets, ordering and integrity plumbing.

Preflight surfaces only (seeds >= 910000); the authoritative mode is locked
and the fresh holdout seeds are never run."""
from __future__ import annotations

from fractions import Fraction
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from bjj_game.diagnostics import tactical_evaluator_te2 as te2
from bjj_game.domain.action import Commitment
from bjj_game.domain.model import Side
from bjj_game.interfaces import tactical_evaluator as te
from bjj_game.interfaces import tactical_policy as tp
from bjj_game.interfaces import tactical_policy_v2 as tp2
from bjj_game.interfaces import tactical_route as route

ROOT = Path(__file__).resolve().parents[1]


def _outcomes(threat=60, tap=5, escapes=30, timeouts=65, builds=800, attempts=None):
    return dict(threat_matches=threat, tap=tap, escapes=escapes, timeouts=timeouts,
                top_completed_builds=builds,
                top_completed_builder_attempts=builds if attempts is None else attempts)


def _result(role, **outcome_overrides):
    integrity = dict(evaluator_rng_draws=0, p3_ok=True, p5_ok=True, bottom_route_searches=0,
                     historical_counter_le_reason_independent=True,
                     p4b_second_run_identical=True, p4c_replay_identical=True,
                     uninstrumented_identical=True)
    return dict(role=role, status="OK", gated=role in te2.GATED,
                outcomes=_outcomes(**outcome_overrides),
                summary=dict(bottom_first_exhausted_time_median=75),
                bottom_exhausted_share_exact=dict(exhausted_seconds=60, match_seconds=100),
                g6=dict(te1_chosen=100, high=20, excluded_forced={}),
                baseline=dict(g4_equivalence=True, exact=True if role in te2.GATED else None),
                integrity=integrity)


def _fabricated(**per_role):
    results = {r: _result(r) for r in te2.ROLES}
    for role in ("PROTECT probe", "PROTECT-H"):
        results[role] = _result(role, threat=0, tap=0, escapes=2, timeouts=98, builds=0)
    results["A-PROD"] = _result("A-PROD", threat=70)
    results["A-PROD-H"] = _result("A-PROD-H", threat=70)
    results.update(per_role)
    baselines = {r: _outcomes() for r in te2.HOLDOUTS}
    baselines["A-PROD-H"] = _outcomes(threat=77)
    baselines["PROTECT-H"] = _outcomes(threat=0, builds=1768)
    return results, baselines


class ArithmeticTests(unittest.TestCase):
    def test_ceil_80_and_floor_50_are_exact(self):
        for x in range(0, 2000):
            self.assertEqual(te2.ceil_80(x), math.ceil(Fraction(4 * x, 5)))
            self.assertEqual(te2.floor_50(x), math.floor(Fraction(x, 2)))
        self.assertEqual(te2.ceil_80(77), 62)
        self.assertEqual(te2.ceil_80(177), 142)
        self.assertEqual(te2.floor_50(1768), 884)


class GateTests(unittest.TestCase):
    def test_hg_boundaries(self):
        results, baselines = _fabricated()
        results["A-PROD-H"] = _result("A-PROD-H", threat=62)
        self.assertEqual(te2.hg_gates(results, baselines)["HG1"]["status"], "PASS")
        results["A-PROD-H"] = _result("A-PROD-H", threat=61)
        self.assertEqual(te2.hg_gates(results, baselines)["HG1"]["status"], "FAIL")

    def test_hg_pooled_per_stalling_mode(self):
        results, baselines = _fabricated()
        # Pooled baseline 180 per mode -> floor 144; OFF has 3 x 60 = 180.
        results["E-PROD-H1 ON"] = _result("E-PROD-H1 ON", threat=23)
        g = te2.hg_gates(results, baselines)["HG1"]
        self.assertEqual(g["pooled"]["OFF"], dict(value=180, floor=144))
        self.assertEqual(g["pooled"]["ON"], dict(value=143, floor=144))
        self.assertEqual(g["status"], "FAIL")

    def test_hg2_to_hg6(self):
        results, baselines = _fabricated()
        g = te2.hg_gates(results, baselines)
        self.assertEqual({k: v["status"] for k, v in g.items()},
                         {f"HG{i}": "PASS" for i in range(1, 7)})
        bad = dict(results, **{"B-PROD-H": _result("B-PROD-H", tap=21)})
        self.assertEqual(te2.hg_gates(bad, baselines)["HG2"]["status"], "FAIL")
        bad = dict(results, **{"B-PROD-H": _result("B-PROD-H", escapes=23)})
        self.assertEqual(te2.hg_gates(bad, baselines)["HG3"]["status"], "FAIL")
        bad = dict(results, **{"PROTECT-H": _result("PROTECT-H", threat=0, builds=885)})
        self.assertEqual(te2.hg_gates(bad, baselines)["HG4"]["status"], "FAIL")
        ok = dict(results, **{"PROTECT-H": _result("PROTECT-H", threat=0, builds=884)})
        self.assertEqual(te2.hg_gates(ok, baselines)["HG4"]["status"], "PASS")
        slow = _result("E-PROD-H2 OFF")
        slow["summary"] = dict(bottom_first_exhausted_time_median=45)
        self.assertEqual(te2.hg_gates(dict(results, **{"E-PROD-H2 OFF": slow}),
                                      baselines)["HG5"]["status"], "FAIL")
        heavy = _result("E-PROD-H1 ON")
        heavy["g6"] = dict(te1_chosen=100, high=81, excluded_forced={})
        self.assertEqual(te2.hg_gates(dict(results, **{"E-PROD-H1 ON": heavy}),
                                      baselines)["HG6"]["status"], "FAIL")

    def test_verdict_pass_fail_open(self):
        with mock.patch.object(te2, "_protected_diff", return_value=[]):
            results, baselines = _fabricated()
            v = te2.verdict(results, baselines, authoritative=True)
            self.assertTrue(v["te2"].startswith("PASS"), v)
            fail = dict(results, **{"A-PROD": _result("A-PROD", threat=0)})
            self.assertEqual(te2.verdict(fail, baselines, authoritative=True)["te2"], "FAIL")
            hfail = dict(results, **{"A-PROD-H": _result("A-PROD-H", threat=0)})
            self.assertEqual(te2.verdict(hfail, baselines, authoritative=True)["te2"], "FAIL")
            broken = _result("B-PROD")
            broken["integrity"]["p4c_replay_identical"] = False
            self.assertEqual(te2.verdict(dict(results, **{"B-PROD": broken}), baselines,
                                         authoritative=True)["te2"], "OPEN")
            over = dict(results, **{"E-PROD-H2 ON": dict(status="OPEN",
                                                         open_reason="budget:rss")})
            self.assertEqual(te2.verdict(over, baselines, authoritative=True)["te2"], "OPEN")
            pre = te2.verdict(results, baselines, authoritative=False)["te2"]
            self.assertTrue(pre.startswith("PREFLIGHT ") and "not a design verdict" in pre)

    def test_authoritative_requires_exact_frozen_baseline(self):
        results, _ = _fabricated()
        results["A-PROD"]["baseline"]["exact"] = False
        self.assertFalse(te2.integrity_ok(results["A-PROD"], gated=True, authoritative=True))
        self.assertTrue(te2.integrity_ok(results["A-PROD"], gated=True, authoritative=False))


class GuardTests(unittest.TestCase):
    def test_preflight_surfaces_are_safe_and_synthetic(self):
        surfaces = te2.preflight_surfaces(matches=10, clock=60)
        te2.assert_preflight_safe(surfaces)
        self.assertEqual({te2.role_of(n) for n in surfaces}, set(te2.ROLES))
        for kwargs in surfaces.values():
            self.assertGreaterEqual(kwargs["base_seed"], 910_000)
            for seed in te2.FRESH_HOLDOUT_SEEDS:
                self.assertFalse(te2._ranges_overlap(kwargs["base_seed"], kwargs["matches"],
                                                     seed, 100))

    def test_reserved_seeds_are_refused(self):
        base = te2.preflight_surfaces()
        name = te2.PREFIX + "A-PROD-H"
        for seed in (685800, 23316, 42, 142, 4242, 4342, 685795, 23310, 909_999):
            surfaces = {name: {**base[name], "base_seed": seed, "matches": 10}}
            with self.assertRaises(te2.PreflightRefused, msg=seed):
                te2.assert_preflight_safe(surfaces)

    def test_authoritative_surfaces_are_refused(self):
        auth = te2.authoritative_surfaces()
        with self.assertRaises(te2.PreflightRefused):
            te2.assert_preflight_safe(auth)
        for role, kwargs in auth.items():
            with self.assertRaises(te2.PreflightRefused, msg=role):
                te2.assert_preflight_safe({te2.PREFIX + role: kwargs})
        self.assertEqual(auth["E-PROD-H1 OFF"]["base_seed"], 685800)
        self.assertEqual(auth["E-PROD-H2 ON"]["base_seed"], 23316)

    def test_long_preflight_refused(self):
        with self.assertRaises(te2.PreflightRefused):
            te2.assert_preflight_safe(te2.preflight_surfaces(matches=11))

    def test_authoritative_mode_is_locked(self):
        self.assertFalse(te2.AUTHORITATIVE_AUTHORIZED)
        with self.assertRaises(te2.AuthoritativeLocked):
            te2.run_authoritative()
        self.assertEqual(te2.main(["authoritative"]), 3)

    def test_worker_refuses_non_preflight(self):
        with tempfile.TemporaryDirectory() as d:
            part = str(Path(d) / "p.json")
            self.assertEqual(te2.main(["worker", "--mode", "authoritative", "--surface",
                                       "A-PROD-H", "--part", part]), 3)
            self.assertEqual(te2.main(["worker", "--mode", "preflight", "--surface",
                                       "A-PROD-H", "--part", part]), 4)
            self.assertFalse(Path(part).exists())

    def test_preflight_output_never_docs_evidence(self):
        with self.assertRaises(te2.PreflightRefused):
            te2.run_preflight(ROOT / "docs" / "evidence", only=["A-PROD"])


class PipelineTests(unittest.TestCase):
    def test_lock_refuses_concurrent_measurement(self):
        with tempfile.TemporaryDirectory() as d:
            with route.exclusive_measurement(Path(d) / "te2_measurement.lock"):
                with self.assertRaises(RuntimeError):
                    te2.run_preflight(Path(d), only=["A-PROD"])

    def test_budget_overflow_is_open(self):
        with tempfile.TemporaryDirectory() as d:
            summary = te2.run_preflight(Path(d), only=["A-PROD"], decision_node_limit=3)
            r = summary["surfaces"]["A-PROD"]
            self.assertEqual((r["status"], r["open_reason"]), ("OPEN", "budget:decision_nodes"))

    def test_baselines_before_candidates_and_artifacts(self):
        with tempfile.TemporaryDirectory() as d:
            summary = te2.run_preflight(Path(d), only=["A-PROD", "A-PROD-H"])
            kinds = [k for k, _ in summary["order"]]
            self.assertEqual(kinds, ["baseline", "baseline", "candidate", "candidate"])
            for name in ("tactical_evaluator_te2_summary.json",
                         "tactical_evaluator_te2_records.json.gz",
                         "tactical_evaluator_te2_report.md"):
                self.assertTrue((Path(d) / name).exists(), name)
            self.assertFalse((Path(d) / "te2_measurement.lock").exists())
            r = summary["surfaces"]["A-PROD-H"]
            self.assertTrue(te2.integrity_ok(r, gated=False, authoritative=False))

    def test_integrity_plumbing_detects_faults(self):
        kwargs = te2.preflight_surfaces()[te2.PREFIX + "A-PROD"]
        baseline = te2.baseline_row(kwargs)
        clean, _ = te2.measure_candidate("A-PROD", kwargs, baseline, authoritative=False)
        self.assertTrue(te2.integrity_ok(clean, gated=True, authoritative=False))

        original = tp2.TacticalV2Policy._te2e

        def drawing(policy, *a, **k):
            random.Random(910_999).random()
            return original(policy, *a, **k)

        with mock.patch.object(tp2.TacticalV2Policy, "_te2e", drawing):
            dirty, _ = te2.measure_candidate("A-PROD", kwargs, baseline, authoritative=False)
        self.assertGreater(dirty["integrity"]["evaluator_rng_draws"], 0)
        self.assertFalse(te2.integrity_ok(dirty, gated=True, authoritative=False))

        def plain_differs(policy, match, branch, allowed):
            if type(policy) is tp2.TacticalV2Policy:
                action = match.legal_action_ids(Side.TOP)[0]
                value = te.evaluate(match, policy.context.model, branch.state, action,
                                    Commitment.LOW, project=False)
                return "position", value, tp2.RouteRecord(policy._match_index, policy._calls,
                                                          "position", (), None, 0)
            return original(policy, match, branch, allowed)

        with mock.patch.object(tp2.TacticalV2Policy, "_te2e", plain_differs):
            observed, _ = te2.measure_candidate("A-PROD", kwargs, baseline, authoritative=False)
        self.assertFalse(observed["integrity"]["uninstrumented_identical"])

        with mock.patch.object(tp2.ReplayV2Policy, "_entry",
                               side_effect=tp.ReplayDesync("flag", "test")):
            desync, _ = te2.measure_candidate("A-PROD", kwargs, baseline, authoritative=False)
        self.assertFalse(desync["integrity"]["p4c_replay_identical"])


class CliTests(unittest.TestCase):
    def test_cli_preflight_end_to_end_subset(self):
        with tempfile.TemporaryDirectory() as d:
            env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
            proc = subprocess.run(
                [sys.executable, "-m", "bjj_game.diagnostics.tactical_evaluator_te2",
                 "preflight", "--out", d, "--only", "A-PROD", "--only", "PROTECT-H"],
                cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("PREFLIGHT", proc.stdout)
            summary = json.loads((Path(d) / "tactical_evaluator_te2_summary.json")
                                 .read_text(encoding="utf-8"))
            self.assertEqual(set(summary["surfaces"]), {"A-PROD", "PROTECT-H"})
            for r in summary["surfaces"].values():
                self.assertEqual(r["status"], "OK")

    def test_cli_authoritative_refused(self):
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
        proc = subprocess.run(
            [sys.executable, "-m", "bjj_game.diagnostics.tactical_evaluator_te2",
             "authoritative"], cwd=ROOT, env=env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 3)
        self.assertIn("NOT AUTHORIZED", proc.stderr)


if __name__ == "__main__":
    unittest.main()
