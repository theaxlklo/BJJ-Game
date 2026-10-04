import unittest

from bjj_game.diagnostics.stamina_recovery_policy import (
    recovery_policy_starting_evidence,
)


class StaminaRecoveryPolicyStartingEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy, cls.both = recovery_policy_starting_evidence()

    def test_surface_e_legacy_destination_baseline(self):
        self.assertEqual(self.legacy.label, "LEGACY")
        self.assertEqual(self.legacy.defensive_spend, 10821)
        self.assertEqual(self.legacy.own_attack_spend, 6091)
        self.assertEqual(self.legacy.own_attacks, 2516)
        self.assertEqual(self.legacy.resets, 29)

    def test_surface_e_both_destination_baseline(self):
        self.assertEqual(self.both.label, "BOTH")
        self.assertEqual(self.both.defensive_spend, 3872)
        self.assertEqual(self.both.own_attack_spend, 11994)
        self.assertEqual(self.both.own_attacks, 2387)
        self.assertEqual(self.both.resets, 18)

    def test_defensive_spend_is_response_plus_hold(self):
        for evidence in (self.legacy, self.both):
            self.assertEqual(
                evidence.defensive_spend,
                evidence.response_spend + evidence.hold_spend,
            )


if __name__ == "__main__":
    unittest.main()
