import unittest

from bjj_game.diagnostics.stamina_economy import (
    StaminaMeasurementGateStatus,
    measure_stamina_economy_definition_of_done,
    measured_surfaces,
    unmeasured_surfaces,
)
from bjj_game.interfaces.batch import BatchBehaviorMode
from bjj_game.interfaces.stamina_economy import (
    StaminaEconomyCollector,
    StaminaEconomyState,
)


class StaminaEconomyMeasurementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.measured = measured_surfaces()
        cls.unmeasured = unmeasured_surfaces()
        cls.gates = {
            gate.letter: gate
            for gate in measure_stamina_economy_definition_of_done()
        }

    def test_measurement_refuses_misaligned_duration_attribution(self):
        with self.assertRaises(ValueError):
            StaminaEconomyCollector(
                interval_seconds=7,
                behavior_quantum_seconds=5,
            )
        with self.assertRaises(ValueError):
            StaminaEconomyCollector(
                interval_seconds=5,
                behavior_quantum_seconds=7,
            )

    def test_five_frozen_surfaces_are_measured(self):
        self.assertEqual(
            tuple(surface.label for surface in self.measured),
            (
                "A public MATCH",
                "B trusts reads",
                "C one level above",
                "D always HIGH",
                "E trusts reads + Bottom RECOVER",
            ),
        )
        for surface in self.measured:
            measurement = surface.summary.stamina_economy
            self.assertIsNotNone(measurement)
            self.assertTrue(measurement.timing_alignment_valid)
            self.assertEqual(len(measurement.matches), 100)
            self.assertTrue(
                all(record.duration_reconciles for record in measurement.matches)
            )

    def test_measurement_gates_a_through_h_pass(self):
        self.assertEqual(tuple(self.gates), tuple("ABCDEFGH"))
        for letter in "ABCDEFGH":
            self.assertIs(
                self.gates[letter].status,
                StaminaMeasurementGateStatus.PASS,
                self.gates[letter].render(),
            )

    def test_instrumentation_does_not_change_mechanical_batch_summary(self):
        for measured, unmeasured in zip(self.measured, self.unmeasured):
            for name in measured.summary.__dataclass_fields__:
                if name == "stamina_economy":
                    continue
                self.assertEqual(
                    getattr(measured.summary, name),
                    getattr(unmeasured.summary, name),
                    f"{measured.label}: {name}",
                )

    def test_reviewed_v04b_policy_numbers_remain_pinned(self):
        trust = self.measured[1].summary
        hedge = self.measured[2].summary
        high = self.measured[3].summary

        self.assertEqual(trust.outcome_counts.get("TAP — Americana", 0), 6)
        self.assertEqual(trust.total_response_commitment_stamina_charged, 7352)
        self.assertEqual(trust.top_final_stamina_median, 0)
        self.assertEqual(trust.bottom_final_stamina_median, 0)

        self.assertEqual(hedge.outcome_counts.get("TAP — Americana", 0), 0)
        self.assertEqual(hedge.total_response_commitment_stamina_charged, 8843)
        self.assertEqual(hedge.top_final_stamina_median, 0)
        self.assertEqual(hedge.bottom_final_stamina_median, 0)

        self.assertEqual(high.outcome_counts.get("TAP — Americana", 0), 0)
        self.assertEqual(high.total_response_commitment_stamina_charged, 9480)
        self.assertEqual(high.top_final_stamina_median, 0)
        self.assertEqual(high.bottom_final_stamina_median, 0)

    def test_middle_window_has_structured_affordability_and_hold_burden(self):
        valid = {"UNFUNDED", "LOW", "MEDIUM", "HIGH"}
        state2_rows = []
        hold_rows = []
        for surface in self.measured[1:]:
            measurement = surface.summary.stamina_economy
            rows = [
                row
                for row in measurement.exchanges
                if row.state
                is StaminaEconomyState.MUTUALLY_EXHAUSTED_NOT_BOTH_ZERO
            ]
            state2_rows.extend(rows)
            hold_rows.extend(row for row in rows if row.submission_hold)

        self.assertGreater(len(state2_rows), 0)
        for row in state2_rows:
            self.assertIn(row.initiator_affordability, valid)
            self.assertIn(row.responder_affordability, valid)
            self.assertIn(row.initiator_effective_commitment, valid)
            self.assertIn(row.responder_effective_commitment, valid)
            if row.hedge_target is None:
                self.assertEqual(row.initiator_effective_commitment, "HIGH")
                self.assertIsNone(row.hedge_one_level_fundable)
            else:
                self.assertIn(row.hedge_target, {"LOW", "MEDIUM", "HIGH"})
                self.assertIsInstance(row.hedge_one_level_fundable, bool)

        self.assertGreater(len(hold_rows), 0)
        for row in hold_rows:
            self.assertIn(row.hold_payment_status, {"FULL", "PARTIAL", "NONE"})
            self.assertEqual(row.hold_requested, 3)
            self.assertEqual(
                row.hold_charged + row.hold_shortfall,
                row.hold_requested,
            )
            self.assertIsInstance(row.requested_plus_hold_fundable, bool)
            self.assertIsInstance(row.effective_plus_hold_fundable, bool)

    def test_every_side_stamina_account_reconciles(self):
        for surface in self.measured:
            measurement = surface.summary.stamina_economy
            for record in measurement.matches:
                self.assertTrue(
                    record.top_stamina_reconciles,
                    f"{surface.label} match {record.match_index} Top",
                )
                self.assertTrue(
                    record.bottom_stamina_reconciles,
                    f"{surface.label} match {record.match_index} Bottom",
                )

    def test_zero_stamina_initiators_are_unfunded(self):
        zero_rows = []
        for surface in self.measured:
            measurement = surface.summary.stamina_economy
            zero_rows.extend(
                row for row in measurement.exchanges if row.initiator_stamina == 0
            )
        self.assertGreater(len(zero_rows), 0)
        self.assertTrue(
            all(
                row.initiator_effective_commitment == "UNFUNDED"
                for row in zero_rows
            )
        )

    def test_surface_e_uses_existing_bottom_recover_policy(self):
        surface = self.measured[4]
        self.assertIs(
            surface.summary.bottom_behavior_mode,
            BatchBehaviorMode.RECOVER,
        )
        measurement = surface.summary.stamina_economy
        self.assertEqual(len(measurement.matches), 100)
        # No outcome or recovery-count target is frozen for Surface E.
        self.assertTrue(
            all(record.duration_reconciles for record in measurement.matches)
        )


if __name__ == "__main__":
    unittest.main()
