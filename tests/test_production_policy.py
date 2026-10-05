from inspect import signature
import unittest

from bjj_game.engine.match import MountMatch
from bjj_game.interfaces.batch import BatchBehaviorMode, run_escape_first_batch
from bjj_game.interfaces.production_policy import (
    GATE_G_STAMINA_RECOVERY_POLICY,
    PRODUCTION_STAMINA_RECOVERY_POLICY,
    ProductionStaminaRecoveryPolicy,
    production_stamina_recovery_policy,
)
from bjj_game.interfaces.recovery_policy import RecoveryInitiationMode


class ProductionStaminaRecoveryPolicyTests(unittest.TestCase):
    """Gate-G adopted policy, now frozen as GATE_G_STAMINA_RECOVERY_POLICY.

    The canonical policy promoted D3-B on top of it; see
    tests/test_d3b_promotion.py.
    """

    policy = GATE_G_STAMINA_RECOVERY_POLICY

    def test_single_canonical_instance(self):
        self.assertIs(production_stamina_recovery_policy(), PRODUCTION_STAMINA_RECOVERY_POLICY)
        self.assertEqual(ProductionStaminaRecoveryPolicy(), self.policy)

    def test_selects_rule1_on_rule2_off_low(self):
        self.assertTrue(self.policy.unfunded_responder_cost_waiver)
        self.assertFalse(self.policy.supplemental_hold_settlement)
        self.assertIs(
            self.policy.exhausted_recovery_initiation,
            RecoveryInitiationMode.LOW_WHILE_EXHAUSTED,
        )

    def test_match_settings_select_only_settlement(self):
        self.assertEqual(
            self.policy.match_settings(),
            {
                "enable_stamina_settlement_rules": False,
                "enable_unfunded_responder_cost_waiver": True,
                "enable_supplemental_hold_settlement": False,
            },
        )

    def test_batch_settings_low_only_under_recover(self):
        recover = self.policy.batch_settings(
            bottom_behavior_mode=BatchBehaviorMode.RECOVER
        )
        fixed = self.policy.batch_settings(
            bottom_behavior_mode=BatchBehaviorMode.FIXED
        )
        self.assertIs(
            recover["recovery_initiation_mode"],
            RecoveryInitiationMode.LOW_WHILE_EXHAUSTED,
        )
        self.assertIs(
            fixed["recovery_initiation_mode"],
            RecoveryInitiationMode.CURRENT,
        )
        self.assertEqual(
            set(recover),
            set(self.policy.match_settings()) | {"recovery_initiation_mode"},
        )

    def test_does_not_select_unrelated_systems(self):
        settings = self.policy.batch_settings(
            bottom_behavior_mode=BatchBehaviorMode.RECOVER
        )
        for unrelated in (
            "enable_v03b_stalling",
            "shadow_stalling",
            "enable_v04_commitment_semantics",
            "enable_v04b_recognition",
            "enable_v02_setup",
            "enable_v03_submissions",
            "commitment",
            "response_commitment_mode",
            "bottom_behavior_mode",
        ):
            self.assertNotIn(unrelated, settings)

    def test_raw_defaults_unchanged(self):
        match = MountMatch()
        self.assertFalse(match.enable_unfunded_responder_cost_waiver)
        self.assertFalse(match.enable_supplemental_hold_settlement)
        self.assertFalse(match.enable_stamina_settlement_rules)
        params = signature(run_escape_first_batch).parameters
        self.assertFalse(params["enable_unfunded_responder_cost_waiver"].default)
        self.assertFalse(params["enable_supplemental_hold_settlement"].default)
        self.assertFalse(params["enable_stamina_settlement_rules"].default)
        self.assertIs(
            params["recovery_initiation_mode"].default,
            RecoveryInitiationMode.CURRENT,
        )

    def test_composes_with_match_when_v04a_enabled(self):
        match = MountMatch(
            enable_v04_commitment_semantics=True,
            **self.policy.match_settings(),
        )
        self.assertTrue(match.unfunded_responder_cost_waiver_enabled)
        self.assertFalse(match.supplemental_hold_settlement_enabled)
        with self.assertRaises(ValueError):
            MountMatch(**self.policy.match_settings())


if __name__ == "__main__":
    unittest.main()
