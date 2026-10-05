"""Pinned D3-B promotion verification results (recorded, not tuned).

Re-executes the frozen equivalence verification of
docs/BURST_RECOVERY_LOCKOUT_D3B_PROMOTION_PREREGISTRATION.md (1eb0a30) and
requires it to equal the committed evidence. PG5/PG6 use the committed
1b96ffc reference fingerprints. PG8 (a git diff against 1b96ffc) is checked
only where that history is available, since its file list grows with later
commits. See docs/BURST_RECOVERY_LOCKOUT_D3B_PROMOTION_RESULT.md.
"""

from functools import lru_cache
import gzip
import json
from pathlib import Path
import subprocess
import unittest

from bjj_game.diagnostics import d3b_promotion as promo
from bjj_game.diagnostics import handoff_d2_v1e as d2

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/d3b_promotion"
GATES = ("PG1", "PG2", "PG3", "PG4", "PG5", "PG6", "PG7", "PG8", "PG9")


def _committed() -> dict:
    return json.loads(gzip.decompress((EVIDENCE / "verification.json.gz").read_bytes()))


@lru_cache(maxsize=1)
def _verified() -> dict:
    reference = json.loads((EVIDENCE / "reference_1b96ffc.json").read_text())
    return json.loads(json.dumps(promo.verify(reference), sort_keys=True, default=repr))


def _has_history() -> bool:
    return subprocess.run(["git", "cat-file", "-e", f"{promo.D3B_RESULT_SHA}^{{commit}}"],
                          cwd=ROOT, capture_output=True).returncode == 0


class D3BPromotionVerificationTests(unittest.TestCase):
    def test_committed_decision_every_gate_pass(self):
        committed = _committed()
        self.assertEqual(committed["decision_PG1_PG9"], "PASS")
        self.assertEqual({g: committed[g]["status"] for g in GATES}, {g: "PASS" for g in GATES})

    def test_reexecution_equals_committed_evidence(self):
        committed, verified = _committed(), _verified()
        for gate in GATES:
            if gate == "PG8":
                continue
            with self.subTest(gate=gate):
                self.assertEqual(verified[gate], committed[gate])
        self.assertEqual(verified["reference_1b96ffc"], committed["reference_1b96ffc"])

    def test_pg2_zero_divergence(self):
        for key, run in _verified()["PG2"]["runs"].items():
            with self.subTest(run=key):
                self.assertTrue(run["summary_equal"])
                self.assertEqual(run["matches"], 100)
                self.assertEqual((run["diverged"], run["diverged_captured"], run["diverged_event_logs"],
                                  run["diverged_op_traces"]), ([], 0, 0, 0))

    def test_pg3_exact_frozen_d3b_values(self):
        pg3 = _verified()["PG3"]
        m = pg3["measured"]
        for metrics in m["original_100"]:
            self.assertEqual(metrics, {"escapes": 30, "Half Guard": 17, "Open Guard": 5, "Reversal": 8,
                                       "timeouts": 65, "taps": 5})
        for metrics in m["seed_142"]:
            self.assertEqual(metrics, {"escapes": 31, "Half Guard": 24, "Open Guard": 6, "Reversal": 1,
                                       "timeouts": 65, "taps": 4})
        self.assertEqual(m["p3_median"], 29.0)
        self.assertEqual(m["p5_exposure"], 13)
        self.assertEqual(m["g1_g2"], [[53, 97, 0, 0]] * 2)
        self.assertEqual(m["g3"], [[25, 25]] * 2)
        self.assertEqual(m["g7"], [[5, [12, 24, 38, 48, 76]]] * 2)
        self.assertEqual(pg3["g6"], {"matches_per_run": [100] * 4, "mismatches": 0, "plus10": [18, 18],
                                     "token_escapes": True})
        self.assertTrue(pg3["evidence_byte_identical"] and pg3["report_identical"])

    def test_pg4_negative_control(self):
        for key, run in _verified()["PG4"]["runs"].items():
            with self.subTest(run=key):
                self.assertGreaterEqual(run["diverged_vs_diagnostic_d3b"], 1)
                self.assertTrue(run["equals_gate_g_control_summary"])
                self.assertTrue(run["equals_gate_g_control_captured"])
                self.assertTrue(run["equals_stored_fe229cb_control_events"])
        self.assertEqual(_verified()["PG4"]["runs"]["42/OFF+shadow"]["outcomes"],
                         {"escapes": 35, "Half Guard": 16, "Open Guard": 10, "Reversal": 9,
                          "timeouts": 60, "taps": 5})

    def test_pg4_hook_removal_diverges_in_gameplay_not_only_metadata(self):
        for seed, stalling in promo.RUNS:
            with self.subTest(run=(seed, stalling)):
                removed = promo.capture(promo.hook_removed_kwargs(seed, stalling))
                diagnostic = promo.capture(promo.d3.d3b_kwargs(seed, stalling))
                result = promo.compare(removed, diagnostic)
                self.assertFalse(result["summary_equal"])
                self.assertGreaterEqual(result["diverged_captured"], 1)
                self.assertGreaterEqual(result["diverged_op_traces"], 1)
                self.assertNotEqual(d2._outcome_metrics(removed.summary),
                                    d2._outcome_metrics(diagnostic.summary))

    def test_pg8_nothing_bundled(self):
        if not _has_history():
            self.skipTest("1b96ffc history unavailable (shallow checkout)")
        pg8 = promo.pg8()
        self.assertEqual((pg8["forbidden"], pg8["unexpected"]), ([], []))


if __name__ == "__main__":
    unittest.main()
