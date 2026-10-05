"""Pinned D2 v1e frozen-measurement results (recorded, not tuned).

Reproduces the single frozen run of
docs/HANDOFF_OSCILLATION_D2_PREREGISTRATION_V1E.md and pins its verdicts and
key numbers, so any later code change that alters the recorded evidence fails.
"""

from pathlib import Path
import unittest

from bjj_game.diagnostics import handoff_d2_v1e as d2

ROOT = Path(__file__).resolve().parents[1]


class D2V1EMeasurementTests(unittest.TestCase):
    def test_decision_is_fail_on_criterion_4_only(self):
        statuses = {c.number: c.status for c in d2.criteria()}
        self.assertEqual(d2.decision(), "FAIL")
        self.assertEqual(statuses, {
            "1": "PASS", "2": "PASS", "3": "PASS", "4": "FAIL", "5": "PASS",
            "6": "PASS", "7": "PASS", "8": "PASS", "9": "PASS", "10": "PASS",
            "11": "PASS", "12": "PASS", "13": "PASS", "14": "REPORTED",
            "16": "PASS",
        })

    def test_criterion_4_numbers(self):
        r = d2.runs()
        for stalling in d2.STALLING:
            self.assertEqual(
                d2._outcome_metrics(r.v1e[(42, stalling)]),
                {"escapes": 17, "Half Guard": 7, "Open Guard": 5, "Reversal": 5,
                 "timeouts": 78, "taps": 5},
            )
            self.assertEqual(
                d2._outcome_metrics(r.control[(42, stalling)]),
                {"escapes": 35, "Half Guard": 16, "Open Guard": 10, "Reversal": 9,
                 "timeouts": 60, "taps": 5},
            )

    def test_stability_and_return_gate(self):
        for stalling in d2.STALLING:
            st = d2.stability(stalling)
            self.assertEqual(
                (st["episodes"][10].reexhausted_within, st["episodes"][10].admissible),
                (0, 68),
            )
            self.assertEqual(
                (st["episodes"][30].reexhausted_within, st["episodes"][30].admissible),
                (0, 59),
            )
            g = d2.criterion16(stalling)
            self.assertEqual((g["eligible"], g["timely"], g["late"], g["reexhausted"], g["pending"]),
                             (44, 44, 0, 0, 0))
        control = d2.stability("OFF+shadow", "control")["episodes"][10]
        self.assertEqual((control.reexhausted_within, control.admissible), (64, 69))

    def test_isolation_proofs(self):
        r = d2.runs()
        self.assertTrue(all(r.replay_equal.values()))
        self.assertTrue(all(r.plain_identity.values()))
        self.assertEqual((r.control_hold_calls, r.ab_hold_calls), (0, 0))
        for proof in r.instrumented.values():
            self.assertEqual(proof["holds"], proof["holds_without_rng"])
            self.assertEqual(proof["holds"], proof["holds_state_unchanged"])
            # Shadow/recovery RESET hooks fire only for real RESETs, never holds.
            self.assertEqual(proof["reset_window_calls"],
                             proof["recovery_collector_before_reset_calls"])
            self.assertTrue(proof["summary_equal_to_uninstrumented"])

    def test_generated_report_matches_committed(self):
        committed = (ROOT / "docs/HANDOFF_OSCILLATION_D2_V1E_MEASUREMENT_DATA.md").read_text()
        self.assertEqual(d2.report(), committed)


if __name__ == "__main__":
    unittest.main()
