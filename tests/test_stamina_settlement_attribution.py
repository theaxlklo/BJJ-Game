import unittest

from bjj_game.diagnostics.stamina_recovery_policy import (
    SettlementAttributionMode,
    attribution_compatibility,
    settlement_attribution_matrix,
)


class StaminaSettlementAttributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cells = settlement_attribution_matrix()

    def test_exact_three_by_four_matrix(self):
        self.assertEqual(len(self.cells), 12)
        self.assertEqual(
            {cell.mode for cell in self.cells},
            set(SettlementAttributionMode),
        )
        self.assertEqual(
            {cell.surface_label for cell in self.cells},
            {
                "A public MATCH",
                "B trusts reads",
                "E trusts reads + Bottom RECOVER",
            },
        )

    def test_none_and_both_compatibility(self):
        none_ok, both_ok = attribution_compatibility()
        self.assertTrue(none_ok)
        self.assertTrue(both_ok)

    def test_rule_one_only_never_charges_unfunded_initiator_responder(self):
        for cell in self.cells:
            if cell.mode is SettlementAttributionMode.RULE1_ONLY:
                self.assertEqual(cell.unfunded_responder_spend, 0)

    def test_rule_two_only_keeps_unfunded_drain_possible(self):
        self.assertTrue(
            any(
                cell.unfunded_responder_spend > 0
                for cell in self.cells
                if cell.mode is SettlementAttributionMode.RULE2_ONLY
            )
        )

    def test_rule_two_only_removes_additive_funded_hold_charging(self):
        for cell in self.cells:
            if cell.mode is SettlementAttributionMode.RULE2_ONLY:
                self.assertEqual(cell.hold_supplemental_charged, 0)


if __name__ == "__main__":
    unittest.main()
