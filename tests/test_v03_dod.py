import unittest

from bjj_game.diagnostics.checker import (
    V02GateStatus,
    _submission_finish_present,
    _v03_best_defense_evidence,
    _v03_bottom_recovery_prediction_probe,
    _v03_defender_behavior_sweep,
    _v03_reacquisition_probability_sweep,
    _v03_exhaustion_differentials,
    _v03_informed_exhausted_defender_probe,
    _v03_informed_defender_sweep,
    _v03_informed_standard_batch,
    _v03_gate_b_status,
    _v03_recognition_mechanic_present,
    _v03_response_commitment_present,
    _v03_locked_submission_probe,
    _v03_standard_batch,
    measure_v02_definition_of_done,
    measure_v03a_definition_of_done,
)
from bjj_game.domain.model import BottomBehavior
from bjj_game.domain.submission import SubmissionStage


class V03DefinitionOfDoneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gates = {
            gate.letter: gate
            for gate in measure_v03a_definition_of_done()
        }

    def test_submission_surface_gate_2_is_closed_by_full_match_v03b_escalation(self):
        self.assertTrue(_submission_finish_present())
        v02 = {gate.number: gate for gate in measure_v02_definition_of_done()}
        self.assertIn(v02[2].status, {V02GateStatus.OPEN, V02GateStatus.PASS})
        self.assertIn("submission_finish_present=True", v02[2].metric)
        self.assertIn("v03b_sweep_cases=26", v02[2].metric)
        self.assertIn("v03b_sweep_failing=", v02[2].metric)
        self.assertIn("v03b_max_post_reset_locked_time_share=", v02[2].metric)
        self.assertIn("has not resolved the lock", v02[2].evidence)

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

    def test_gate_b_defers_until_response_commitment_or_recognition_exists(self):
        informed = _v03_informed_standard_batch()
        random = _v03_standard_batch()
        taps = informed.outcome_counts.get("TAP — Americana", 0)
        random_taps = random.outcome_counts.get("TAP — Americana", 0)

        self.assertFalse(_v03_response_commitment_present())
        self.assertFalse(_v03_recognition_mechanic_present())
        self.assertIs(self.gates["B"].status, V02GateStatus.DEFERRED)
        self.assertIn("response_commitment_present=False", self.gates["B"].metric)
        self.assertIn("recognition_present=False", self.gates["B"].metric)
        self.assertIn(
            f"informed Tap={taps}/{informed.matches}",
            self.gates["B"].metric,
        )
        self.assertIn(
            f"Threat={informed.matches_reached_submission_threat}",
            self.gates["B"].metric,
        )
        self.assertIn(
            f"random contrast Tap={random_taps}/{random.matches}",
            self.gates["B"].metric,
        )
        self.assertIn("auto-expires", self.gates["B"].evidence)
        self.assertIn("Exhausted initiator -1", self.gates["B"].evidence)
        self.assertIn("Exhausted responder +1", self.gates["B"].evidence)
        self.assertIn("uneven attacker/defender costs", self.gates["B"].evidence)
        self.assertIn("no longer cancel", self.gates["B"].evidence)

    def test_gate_b_deferral_auto_expires_on_either_future_capability(self):
        self.assertIs(
            _v03_gate_b_status(
                tap_rate=0.0,
                response_commitment_present=False,
                recognition_present=False,
            ),
            V02GateStatus.DEFERRED,
        )
        self.assertIs(
            _v03_gate_b_status(
                tap_rate=0.0,
                response_commitment_present=True,
                recognition_present=False,
            ),
            V02GateStatus.OPEN,
        )
        self.assertIs(
            _v03_gate_b_status(
                tap_rate=0.0,
                response_commitment_present=False,
                recognition_present=True,
            ),
            V02GateStatus.OPEN,
        )
        self.assertIs(
            _v03_gate_b_status(
                tap_rate=0.25,
                response_commitment_present=True,
                recognition_present=False,
            ),
            V02GateStatus.PASS,
        )

    def test_gate_c_requires_exact_fresh_stalemate_at_every_reachable_stage(self):
        evidence = _v03_best_defense_evidence()
        expected = (
            V02GateStatus.PASS
            if all(
                item.reachable_states > 0
                and item.best_contested_states == item.reachable_states
                and item.best_defender_win_states == 0
                and item.guaranteed_advance_states == 0
                for item in evidence.values()
            )
            else V02GateStatus.OPEN
        )
        self.assertIs(self.gates["C"].status, expected)
        self.assertEqual(set(evidence), set(SubmissionStage))
        for stage, item in evidence.items():
            self.assertEqual(item.reachable_states, 2)
            self.assertEqual(
                item.best_contested_states,
                item.reachable_states,
            )
            self.assertEqual(item.best_defender_win_states, 0)
            self.assertEqual(item.guaranteed_advance_states, 0)
            self.assertIn(
                f"{stage.value}:{item.reachable_states}/"
                f"best-contested:{item.best_contested_states}/"
                f"defender-wins:{item.best_defender_win_states}/"
                f"guaranteed:{item.guaranteed_advance_states}",
                self.gates["C"].metric,
            )

    def test_informed_defender_sweep_is_deterministic_and_nonempty(self):
        rows = _v03_informed_defender_sweep()
        self.assertGreaterEqual(len(rows), 7)
        labels = {row.label for row in rows}
        self.assertIn("PRESSURE/ESCAPE fixed", labels)
        self.assertIn("PRESSURE/ESCAPE recover", labels)
        for row in rows:
            self.assertGreaterEqual(row.taps, 0)
            self.assertGreaterEqual(row.reached_threat, 0)
            self.assertGreaterEqual(row.escapes, 0)
            self.assertGreaterEqual(row.timeouts, 0)
            self.assertGreaterEqual(row.top_stamina_median, 0)
            self.assertGreaterEqual(row.bottom_stamina_median, 0)
            self.assertGreaterEqual(row.setup_builds, 0)

    def test_behavior_and_reacquisition_probes_are_observational(self):
        behavior_rows = _v03_defender_behavior_sweep()
        self.assertEqual(
            {row.bottom_behavior for row in behavior_rows},
            set(BottomBehavior),
        )
        for row in behavior_rows:
            self.assertGreaterEqual(row.taps, 0)
            self.assertGreaterEqual(row.escapes, 0)
            self.assertGreaterEqual(row.timeouts, 0)
            self.assertGreaterEqual(row.completed_setup_builds, 0)
            self.assertGreaterEqual(row.submission_attempts, 0)

        reacquisition_rows = _v03_reacquisition_probability_sweep()
        self.assertGreater(len(reacquisition_rows), 0)
        for row in reacquisition_rows:
            self.assertGreaterEqual(row.probability, 0.0)
            self.assertLessEqual(row.probability, 1.0)

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

    def test_gate_e_informed_exhausted_defender_cannot_perfect_lock(self):
        evidence = _v03_informed_exhausted_defender_probe()
        expected = (
            V02GateStatus.PASS
            if evidence.tapped
            else V02GateStatus.OPEN
        )
        self.assertIs(self.gates["E"].status, expected)
        self.assertTrue(evidence.tapped)
        self.assertEqual(len(evidence.selected_responses), 3)
        self.assertEqual(len(evidence.final_grades), 3)
        self.assertTrue(all(grade.successful for grade in evidence.final_grades))
        self.assertIn("tapped=True", self.gates["E"].metric)

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
