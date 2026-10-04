import unittest

from bjj_game.diagnostics.stamina_recovery_policy import (
    RecoveryAmendmentGateStatus,
    measure_recovery_policy_amendment_definition_of_done,
    render_recovery_policy_predictions,
)


class StaminaRecoveryPolicyAmendmentDodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gates = {
            gate.letter: gate
            for gate in measure_recovery_policy_amendment_definition_of_done()
        }

    def test_gates_a_through_j_exist(self):
        self.assertEqual(tuple(self.gates), tuple("ABCDEFGHIJ"))

    def test_all_measurement_and_compatibility_gates_pass(self):
        for letter in "ABCDEFGHIJ":
            self.assertIs(
                self.gates[letter].status,
                RecoveryAmendmentGateStatus.PASS,
                self.gates[letter].render(),
            )

    def test_predictions_p1_through_p8_are_reported(self):
        lines = render_recovery_policy_predictions()
        self.assertEqual(len(lines), 8)
        for index, line in enumerate(lines, start=1):
            self.assertTrue(line.startswith(f"P{index} "), line)

    def test_prediction_verdicts_preserve_misses(self):
        lines = render_recovery_policy_predictions()
        self.assertIn("[PARTIAL]", lines[6])
        self.assertIn("[NOT CONFIRMED]", lines[7])


if __name__ == "__main__":
    unittest.main()
