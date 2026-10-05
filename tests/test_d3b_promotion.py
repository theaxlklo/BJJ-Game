"""D3-B production-promotion wiring tests (written before the verification run).

docs/BURST_RECOVERY_LOCKOUT_D3B_PROMOTION_PREREGISTRATION.md (1eb0a30).
Integration checks use the synthetic D3-B fixture only (seed 910000, Bottom
stamina 20, Top stamina 0); the frozen seeds are verified by the promotion
verification run, not here.
"""

from dataclasses import FrozenInstanceError
from functools import lru_cache
import unittest

from bjj_game.diagnostics import d3b_promotion as promo
from bjj_game.diagnostics import handoff_d2_v1e as d2
from bjj_game.diagnostics import handoff_d3b as d3
from bjj_game.interfaces.batch import BatchBehaviorMode, run_escape_first_batch
from bjj_game.interfaces.handoff_policy import PostClearHandoffMode
from bjj_game.interfaces.production_policy import (
    GATE_G_STAMINA_RECOVERY_POLICY,
    PRODUCTION_STAMINA_RECOVERY_POLICY,
    ProductionStaminaRecoveryPolicy,
    production_stamina_recovery_policy,
)
from bjj_game.interfaces.recovery_policy import RecoveryInitiationMode

D3B = PostClearHandoffMode.D3B_EXHAUSTED_TOKEN_LOCKOUT
SYNTHETIC = {"base_seed": 910_000, "matches": 12, "bottom_stamina": 20, "top_stamina": 0}


def _synthetic(kwargs: dict) -> dict:
    return {**kwargs, **SYNTHETIC}


@lru_cache(maxsize=None)
def _captured(route: str):
    kwargs = {
        "diagnostic": d3.d3b_kwargs(42, "OFF+shadow"),
        "canonical": promo.canonical_kwargs(42, "OFF+shadow"),
        "removed": promo.hook_removed_kwargs(42, "OFF+shadow"),
        "gate_g": d2.control_kwargs(42, "OFF+shadow"),
    }[route]
    return promo.capture(_synthetic(kwargs))


class PromotedPolicyTests(unittest.TestCase):
    canonical = PRODUCTION_STAMINA_RECOVERY_POLICY
    historical = GATE_G_STAMINA_RECOVERY_POLICY

    def test_canonical_entry_point(self):
        self.assertIs(production_stamina_recovery_policy(), self.canonical)
        self.assertIs(self.canonical.post_clear_handoff_mode, D3B)

    def test_rule1_on_rule2_off_low_unchanged(self):
        for policy in (self.canonical, self.historical):
            self.assertTrue(policy.unfunded_responder_cost_waiver)
            self.assertFalse(policy.supplemental_hold_settlement)
            self.assertIs(policy.exhausted_recovery_initiation, RecoveryInitiationMode.LOW_WHILE_EXHAUSTED)

    def test_match_settings_identical(self):
        self.assertEqual(self.canonical.match_settings(), self.historical.match_settings())

    def test_recover_adds_exactly_d3b(self):
        recover = BatchBehaviorMode.RECOVER
        self.assertEqual(
            self.canonical.batch_settings(bottom_behavior_mode=recover),
            {**self.historical.batch_settings(bottom_behavior_mode=recover), "post_clear_handoff_mode": D3B},
        )

    def test_non_recover_identical_to_gate_g(self):
        for mode in BatchBehaviorMode:
            if mode is BatchBehaviorMode.RECOVER:
                continue
            with self.subTest(mode=mode):
                settings = self.canonical.batch_settings(bottom_behavior_mode=mode)
                self.assertEqual(settings, self.historical.batch_settings(bottom_behavior_mode=mode))
                self.assertNotIn("post_clear_handoff_mode", settings)

    def test_historical_instance_is_independent_and_frozen(self):
        self.assertIsNot(self.historical, self.canonical)
        self.assertIs(self.historical.post_clear_handoff_mode, PostClearHandoffMode.NONE)
        self.assertNotIn("post_clear_handoff_mode",
                         self.historical.batch_settings(bottom_behavior_mode=BatchBehaviorMode.RECOVER))
        with self.assertRaises((FrozenInstanceError, AttributeError)):
            self.historical.post_clear_handoff_mode = D3B
        self.assertEqual(ProductionStaminaRecoveryPolicy(), self.historical)

    def test_historical_outputs_equal_pre_promotion_snapshot(self):
        result = promo.pg9()
        self.assertTrue(result["gate_g_outputs_equal_pre_promotion"])
        self.assertTrue(result["gate_g_independent_instance"])

    def test_unmeasured_recover_configuration_raises(self):
        base = _synthetic(promo.canonical_kwargs(42, "OFF+shadow"))
        for change in ({"enable_v02_setup": False}, {"enable_v04_commitment_semantics": False}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                run_escape_first_batch(**{**base, **change, "matches": 1})


class PromotedRouteEquivalenceTests(unittest.TestCase):
    """Synthetic-fixture analogue of PG1/PG2/PG4."""

    def test_settings_equal_diagnostic(self):
        from bjj_game.diagnostics.stamina_adoption_verification import effective_settings
        self.assertEqual(effective_settings(_synthetic(promo.canonical_kwargs(42, "OFF+shadow"))),
                         effective_settings(_synthetic(d3.d3b_kwargs(42, "OFF+shadow"))))

    def test_canonical_equals_diagnostic_d3b(self):
        result = promo.compare(_captured("canonical"), _captured("diagnostic"))
        self.assertTrue(result["summary_equal"])
        self.assertEqual(result["diverged"], [])

    def test_fixture_exercises_lockout(self):
        kinds = {e.get("kind") for m in _captured("canonical").summary.post_clear_handoff.matches
                 for e in m.events}
        self.assertTrue({"TOKEN", "LOCKOUT_HOLD"} <= kinds)

    def test_negative_control_detected_and_equals_gate_g(self):
        removed = _captured("removed")
        self.assertGreaterEqual(len(promo.compare(removed, _captured("diagnostic"))["diverged"]), 1)
        gate_g = promo.compare(removed, _captured("gate_g"))
        self.assertTrue(gate_g["summary_equal"])
        self.assertEqual(gate_g["diverged"], [])


if __name__ == "__main__":
    unittest.main()
