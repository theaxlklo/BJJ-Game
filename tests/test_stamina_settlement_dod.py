import unittest

from bjj_game.diagnostics.stamina_settlement import (
    StaminaRuleGateStatus,
    measure_stamina_rule_definition_of_done,
    postchange_surfaces,
    render_prediction_comparison,
)
from bjj_game.interfaces.stamina_economy import StaminaEconomyState


class StaminaSettlementDefinitionOfDoneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.surfaces = postchange_surfaces()
        cls.gates = {
            gate.letter: gate
            for gate in measure_stamina_rule_definition_of_done()
        }

    def test_exact_five_postchange_surfaces(self):
        self.assertEqual(
            tuple(surface.label for surface in self.surfaces),
            (
                "A public MATCH",
                "B trusts reads",
                "C one level above",
                "D always HIGH",
                "E trusts reads + Bottom RECOVER",
            ),
        )
        self.assertTrue(
            all(surface.summary.stamina_economy is not None for surface in self.surfaces)
        )

    def test_gates_a_through_i_exist(self):
        self.assertEqual(tuple(self.gates), tuple("ABCDEFGHI"))

    def test_local_rule_and_accounting_gates_pass(self):
        for letter in "ABCEGHI":
            self.assertIs(
                self.gates[letter].status,
                StaminaRuleGateStatus.PASS,
                self.gates[letter].render(),
            )

    def test_recovery_and_gate_b_outcome_are_measured_not_tuned(self):
        self.assertIn(
            self.gates["D"].status,
            {StaminaRuleGateStatus.PASS, StaminaRuleGateStatus.OPEN},
        )
        self.assertIn(
            self.gates["F"].status,
            {StaminaRuleGateStatus.PASS, StaminaRuleGateStatus.OPEN},
        )

    def test_postchange_unfunded_exchanges_never_charge_responder(self):
        rows = [
            row
            for surface in self.surfaces
            for row in surface.summary.stamina_economy.exchanges
            if row.initiator_effective_commitment == "UNFUNDED"
        ]
        self.assertGreater(len(rows), 0)
        self.assertTrue(
            all(
                row.response_commitment_charged == 0
                and row.hold_charged == 0
                for row in rows
            )
        )

    def test_no_additive_double_charge_on_funded_response_hold(self):
        holds = [
            row
            for surface in self.surfaces
            for row in surface.summary.stamina_economy.exchanges
            if row.submission_hold
        ]
        self.assertGreater(len(holds), 0)
        self.assertFalse(
            any(
                row.response_commitment_charged >= 3
                and row.hold_charged > 0
                for row in holds
            )
        )

    def test_postchange_stamina_reconciles(self):
        for surface in self.surfaces:
            for record in surface.summary.stamina_economy.matches:
                self.assertTrue(record.top_stamina_reconciles)
                self.assertTrue(record.bottom_stamina_reconciles)

    def test_prediction_comparison_reports_p1_through_p6(self):
        lines = render_prediction_comparison()
        self.assertEqual(len(lines), 6)
        for index, line in enumerate(lines, start=1):
            self.assertTrue(line.startswith(f"P{index} "), line)

    def test_surface_e_recovery_observation_is_structured(self):
        measurement = self.surfaces[4].summary.stamina_economy
        self.assertEqual(len(measurement.matches), 100)
        self.assertTrue(
            all(
                record.state1_seconds
                + record.state2_seconds
                + record.state3_seconds
                == record.elapsed_seconds
                for record in measurement.matches
            )
        )
        self.assertGreater(
            sum(
                row.state
                is StaminaEconomyState.MUTUALLY_EXHAUSTED_NOT_BOTH_ZERO
                for row in measurement.exchanges
            ),
            0,
        )


if __name__ == "__main__":
    unittest.main()
