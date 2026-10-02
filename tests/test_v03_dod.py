import unittest

from bjj_game.diagnostics.checker import (
    V02GateStatus,
    _submission_finish_present,
    _v03_best_defense_evidence,
    _v03_bottom_recovery_prediction_probe,
    _v03_exhaustion_differentials,
    _v03_locked_submission_probe,
    _v03_standard_batch,
    measure_v02_definition_of_done,
    measure_v03a_definition_of_done,
)
from bjj_game.domain.submission import SubmissionStage


class V03DefinitionOfDoneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gates = {
            gate.letter: gate
            for gate in measure_v03a_definition_of_done()
        }

    def test_submission_surface_expires_gate_2_deferral(self):
        self.assertTrue(_submission_finish_present())
        v02 = {gate.number: gate for gate in measure_v02_definition_of_done()}
        self.assertIs(v02[2].status, V02GateStatus.OPEN)
        self.assertIn("submission_finish_present=True", v02[2].metric)

    def test_gate_a_uses_positive_submission_probability_and_policy_order(self):
        probability, selected = _v03_locked_submission_probe()
        expected = (
            V02GateStatus.PASS
            if probability > 0 and selected
            else V02GateStatus.OPEN
        )
        self.assertIs(self.gates["A"].status, expected)
        self.assertGreater(probability, 0.0)
        self.assertTrue(selected)
        self.assertIn(
            f"Locked submission-progress probability={probability:.3f}",
            self.gates["A"].metric,
        )

    def test_gate_b_uses_frozen_nonzero_below_half_tap_range(self):
        batch = _v03_standard_batch()
        taps = batch.outcome_counts.get("TAP — Americana", 0)
        rate = taps / batch.matches
        expected = (
            V02GateStatus.PASS
            if 0 < rate < 0.50
            else V02GateStatus.OPEN
        )
        self.assertIs(self.gates["B"].status, expected)
        self.assertIn(f"Tap={taps}/{batch.matches}", self.gates["B"].metric)
        self.assertIn(
            f"Threat={batch.matches_reached_submission_threat}",
            self.gates["B"].metric,
        )
        self.assertIn(
            f"Control={batch.matches_reached_submission_control}",
            self.gates["B"].metric,
        )
        self.assertIn(
            f"Finish={batch.matches_reached_submission_finish}",
            self.gates["B"].metric,
        )

    def test_gate_c_requires_best_fresh_defense_to_stop_every_stage(self):
        evidence = _v03_best_defense_evidence()
        expected = (
            V02GateStatus.PASS
            if all(
                item.reachable_states > 0
                and item.best_defense_stops == item.reachable_states
                and item.guaranteed_advance_states == 0
                for item in evidence.values()
            )
            else V02GateStatus.OPEN
        )
        self.assertIs(self.gates["C"].status, expected)
        self.assertEqual(set(evidence), set(SubmissionStage))
        for stage, item in evidence.items():
            self.assertGreater(item.reachable_states, 0)
            self.assertEqual(item.best_defense_stops, item.reachable_states)
            self.assertEqual(item.guaranteed_advance_states, 0)
            self.assertIn(
                f"{stage.value}:{item.reachable_states}/"
                f"stopped:{item.best_defense_stops}/"
                f"guaranteed:{item.guaranteed_advance_states}",
                self.gates["C"].metric,
            )

    def test_recovery_prediction_probe_is_observational_and_matched(self):
        rows = _v03_bottom_recovery_prediction_probe()
        self.assertEqual(
            [row.label for row in rows],
            ["fresh-fixed", "exhausted-fixed", "exhausted-recover"],
        )
        for row in rows:
            self.assertGreaterEqual(row.taps, 0)
            self.assertGreaterEqual(row.escapes, 0)
            self.assertGreaterEqual(row.timeouts, 0)
            self.assertGreaterEqual(row.submission_attempts, 0)

    def test_gate_d_checks_both_one_sided_directions_and_cancellation(self):
        attacker, defender, mismatches, cases = _v03_exhaustion_differentials()
        expected = (
            V02GateStatus.PASS
            if attacker > 0 and defender > 0 and mismatches == 0
            else V02GateStatus.OPEN
        )
        self.assertIs(self.gates["D"].status, expected)
        self.assertGreater(attacker, 0)
        self.assertGreater(defender, 0)
        self.assertEqual(mismatches, 0)
        self.assertGreater(cases, 0)
        self.assertIn(f"attacker-only changes={attacker}", self.gates["D"].metric)
        self.assertIn(f"defender-only changes={defender}", self.gates["D"].metric)
        self.assertIn(
            f"both-Exhausted cancellation mismatches={mismatches}/{cases}",
            self.gates["D"].metric,
        )


if __name__ == "__main__":
    unittest.main()
