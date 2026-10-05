"""Pinned D3-B frozen-measurement results (recorded, not tuned).

Reproduces the single frozen run of
docs/BURST_RECOVERY_LOCKOUT_D3B_PREREGISTRATION.md (dc4fc16) and pins its
verdicts and gate-defining numbers, so any later code change that alters the
recorded evidence fails. See docs/BURST_RECOVERY_LOCKOUT_D3B_RESULT.md.
"""

import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

from bjj_game.diagnostics import handoff_d2_v1e as d2
from bjj_game.diagnostics import handoff_d3b as d3

ROOT = Path(__file__).resolve().parents[1]
FROZEN_DIGEST = "3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2"


class D3BMeasurementTests(unittest.TestCase):
    def test_decision_is_pass_with_every_gate_pass(self):
        self.assertEqual(d3.decision(), "PASS")
        self.assertEqual(
            {g.gate_id: g.status for g in d3.gates()},
            {g: "PASS" for g in ("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9",
                                 "G1", "G2", "G3", "G6", "G7")},
        )

    def test_p4_outcomes(self):
        r = d3.runs()
        for stalling in d3.STALLING:
            self.assertEqual(
                d2._outcome_metrics(r.d3b[(42, stalling)]),
                {"escapes": 30, "Half Guard": 17, "Open Guard": 5, "Reversal": 8,
                 "timeouts": 65, "taps": 5},
            )
            self.assertEqual(
                d2._outcome_metrics(r.d3b[(142, stalling)]),
                {"escapes": 31, "Half Guard": 24, "Open Guard": 6, "Reversal": 1,
                 "timeouts": 65, "taps": 4},
            )

    def test_surfaces_a_b_preserved_and_d3b_rejected(self):
        evidence = {g.gate_id: g.evidence for g in d3.gates()}["P1"]
        self.assertIn("A 78/1950/0; B Tap 9", evidence)
        self.assertEqual(d3.runs().rejected_on_ab, {"A": True, "B": True})

    def test_p3_and_p5_values(self):
        r = d3.runs()
        self.assertEqual(d2._cell(r.d3b[(42, "OFF+shadow")], "OFF+shadow").bottom_final_median, 29.0)
        self.assertEqual(
            d2._cell(r.d3b[(42, "OFF+shadow")], "OFF+shadow").shadow_bottom_resets_with_route, 13)
        for seed in d3.SEEDS:
            on = r.d3b[(seed, "ON")]
            cell = d2._cell(on, "ON")
            self.assertEqual(
                (cell.bottom_stalling_warnings, cell.bottom_stalling_penalties,
                 cell.bottom_stalling_position_resets, on.top_stalling_warning_count,
                 on.top_stalling_penalty_count, on.top_stalling_position_reset_count),
                (0, 0, 0, 0, 0, 0),
            )
        self.assertIn("OFF/ON diverged (trajectory, hold/exit)={42: (0, 0), 142: (0, 0)}",
                      {g.gate_id: g.evidence for g in d3.gates()}["P5"])

    def test_g1_g2_exactness(self):
        for stalling in d3.STALLING:
            g = d3.g1_g2(stalling)
            self.assertEqual((g["tokens"], g["lockout_holds"]), (53, 97))
            self.assertEqual((g["g1_violations"], g["g2_violations"]), ([], []))

    def test_g3_population_and_rate(self):
        for stalling in d3.STALLING:
            g = d3.g3(stalling)
            self.assertTrue(g["population_matches_frozen"])
            self.assertEqual((g["eligible"], g["success"], g["continued_after_token"],
                              g["still_exhausted_at_60"]), (25, 25, 22, 0))
            self.assertEqual(g["counts"], {"cleared<=60": 22, "token-escape": 3})

    def test_g6_prefix_identity(self):
        g = d3.g6()
        for key in d3.RUNS:
            self.assertEqual(g[key]["matches"], 100)
            self.assertEqual(g[key]["mismatches"], [])
            self.assertEqual(g[key]["traces_equal_summaries"], (True, True))
        for stalling in d3.STALLING:
            self.assertEqual(g["populations"][stalling],
                             {"g7_population": True, "g3_population": True, "token_escapes": True})
            self.assertEqual(g["plus10_restored"][stalling], {"count": 18, "restored": 18})
        self.assertEqual(g["status"], "PASS")

    def test_g7_outcome_count(self):
        for stalling in d3.STALLING:
            g = d3.g7(stalling)
            self.assertEqual(g["escapes"], 5)
            self.assertEqual(
                {row["match"]: row["d3b"] for row in g["rows"] if row["d3b"] in d3.ESCAPES},
                {12: "Half Guard", 24: "Reversal", 38: "Half Guard", 48: "Reversal", 76: "Reversal"},
            )

    def test_isolation_proofs(self):
        r = d3.runs()
        self.assertTrue(all(r.replay_equal.values()))
        self.assertTrue(all(r.plain_identity.values()))
        for proof in r.instrumented.values():
            self.assertEqual(proof["holds"], proof["holds_without_rng"])
            self.assertEqual(proof["holds"], proof["holds_state_unchanged"])
            self.assertEqual(proof["reset_window_calls"],
                             proof["recovery_collector_before_reset_calls"])
            self.assertTrue(proof["summary_equal_to_uninstrumented"])

    def test_generated_evidence_and_report_match_committed(self):
        committed = json.loads(gzip.decompress(
            (ROOT / "docs/evidence/handoff_d3b_evidence.json.gz").read_bytes()))
        self.assertEqual(json.loads(json.dumps(d3.evidence(), sort_keys=True)), committed)
        self.assertEqual(
            d3.report(), (ROOT / "docs/BURST_RECOVERY_LOCKOUT_D3B_MEASUREMENT_DATA.md").read_text())

    def test_frozen_digest(self):
        out = subprocess.run([sys.executable, "-m", "bjj_game", "--enumerate"],
                             capture_output=True, check=True,
                             env={"PYTHONPATH": str(ROOT / "src")})
        self.assertEqual(hashlib.sha256(out.stdout).hexdigest(), FROZEN_DIGEST)


if __name__ == "__main__":
    unittest.main()
