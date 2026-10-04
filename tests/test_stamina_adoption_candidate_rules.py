"""Synthetic tests for the Stage-2 scoring rubric and frozen A9 rule.

These never execute a production-candidate surface.
"""

import unittest

from bjj_game.diagnostics.stamina_adoption_candidate import (
    A9_FROZEN_X,
    A9Verdict,
    PROPOSED_PRODUCTION_DIAGNOSTIC,
    PROPOSED_PRODUCTION_SETTLEMENT,
    Prediction,
    a9_verdict,
    ext_100_triggered,
    ordering_flip,
    score_a1,
    score_a2,
    score_a3,
    score_a4,
    score_a5,
    score_a6,
    score_a7,
    score_a8,
    score_a9,
    score_a10,
)
from bjj_game.interfaces.recovery_policy import RecoveryInitiationMode


class ProposedProductionConfigTests(unittest.TestCase):
    def test_config_is_rule1_on_rule2_off_low(self):
        self.assertTrue(
            PROPOSED_PRODUCTION_SETTLEMENT["enable_unfunded_responder_cost_waiver"]
        )
        self.assertFalse(
            PROPOSED_PRODUCTION_SETTLEMENT["enable_supplemental_hold_settlement"]
        )
        self.assertFalse(
            PROPOSED_PRODUCTION_SETTLEMENT["enable_stamina_settlement_rules"]
        )
        self.assertIs(
            PROPOSED_PRODUCTION_DIAGNOSTIC["recovery_initiation_mode"],
            RecoveryInitiationMode.LOW_WHILE_EXHAUSTED,
        )


class A9CandidateRuleTests(unittest.TestCase):
    def test_pass_requires_43_and_p_at_or_below_x(self):
        self.assertEqual(a9_verdict(43, 0)[1], A9Verdict.PASS)
        self.assertEqual(a9_verdict(100, 97)[1], A9Verdict.PASS)
        self.assertEqual(a9_verdict(100, 98)[1], A9Verdict.FAIL)
        self.assertEqual(a9_verdict(42, 0)[1], A9Verdict.UNSCOREABLE)
        self.assertEqual(a9_verdict(0, 0), (None, A9Verdict.UNSCOREABLE))

    def test_boundary_is_inclusive_and_unrounded(self):
        # 0.98 display would wrongly pass 0.9751; unrounded X must not.
        self.assertLess(A9_FROZEN_X, 0.98)
        self.assertEqual(a9_verdict(10_000, 9_750)[1], A9Verdict.PASS)
        self.assertEqual(a9_verdict(10_000, 9_751)[1], A9Verdict.FAIL)

    def test_ext_trigger_is_sample_adequacy_only(self):
        self.assertTrue(ext_100_triggered(42))
        self.assertFalse(ext_100_triggered(43))

    def test_ordering_flip_strict_signs_only(self):
        # Baseline: p_episode=59/63~0.9365, p_match=58/61~0.9508.
        self.assertTrue(
            ordering_flip(p_episode_candidate=0.95, p_match_candidate=0.90)
        )
        self.assertFalse(
            ordering_flip(p_episode_candidate=0.50, p_match_candidate=0.50)
        )
        self.assertFalse(
            ordering_flip(
                p_episode_candidate=59 / 63,
                p_match_candidate=0.10,
            )
        )


class PredictionRubricTests(unittest.TestCase):
    def test_a1_exact(self):
        self.assertIs(score_a1(78, 1950, 0), Prediction.CONFIRMED)
        self.assertIs(score_a1(78, 1949, 0), Prediction.NOT_CONFIRMED)

    def test_a2_a3_floor_and_range(self):
        self.assertIs(score_a2(40), Prediction.CONFIRMED)
        self.assertIs(score_a2(120), Prediction.CONFIRMED)
        self.assertIs(score_a2(34), Prediction.PARTIAL)
        self.assertIs(score_a2(121), Prediction.PARTIAL)
        self.assertIs(score_a2(33), Prediction.NOT_CONFIRMED)
        self.assertIs(score_a3(800), Prediction.CONFIRMED)
        self.assertIs(score_a3(557), Prediction.PARTIAL)
        self.assertIs(score_a3(556), Prediction.NOT_CONFIRMED)

    def test_a4_a5_ranges(self):
        self.assertIs(score_a4(20), Prediction.CONFIRMED)
        self.assertIs(score_a4(35.5), Prediction.NOT_CONFIRMED)
        self.assertIs(score_a5(75), Prediction.CONFIRMED)
        self.assertIs(score_a5(29), Prediction.NOT_CONFIRMED)

    def test_a6_exposure_and_offenses(self):
        self.assertIs(score_a6(15, 0, 0, 0), Prediction.CONFIRMED)
        self.assertIs(score_a6(16, 0, 0, 0), Prediction.PARTIAL)
        self.assertIs(score_a6(7, 1, 0, 0), Prediction.PARTIAL)
        self.assertIs(score_a6(16, 1, 0, 0), Prediction.NOT_CONFIRMED)

    def test_a7_divergence(self):
        self.assertIs(
            score_a7(real_offense_fired=False, diverged_matches=0),
            Prediction.CONFIRMED,
        )
        self.assertIs(
            score_a7(real_offense_fired=True, diverged_matches=3),
            Prediction.PARTIAL,
        )
        self.assertIs(
            score_a7(real_offense_fired=False, diverged_matches=1),
            Prediction.NOT_CONFIRMED,
        )

    def test_a8_exit_split(self):
        self.assertIs(score_a8(31, 15, 5, 100), Prediction.CONFIRMED)
        self.assertIs(score_a8(31, 15, 15, 100), Prediction.PARTIAL)
        self.assertIs(score_a8(10, 15, 5, 100), Prediction.PARTIAL)
        self.assertIs(score_a8(10, 15, 20, 100), Prediction.NOT_CONFIRMED)

    def test_a9_a10(self):
        self.assertIs(score_a9(A9Verdict.PASS), Prediction.CONFIRMED)
        self.assertIs(score_a9(A9Verdict.FAIL), Prediction.NOT_CONFIRMED)
        self.assertIs(score_a9(A9Verdict.UNSCOREABLE), Prediction.NOT_CONFIRMED)
        self.assertIs(score_a10(1, 100), Prediction.CONFIRMED)
        self.assertIs(score_a10(0, 100), Prediction.NOT_CONFIRMED)
        self.assertIs(score_a10(50, 100), Prediction.NOT_CONFIRMED)


if __name__ == "__main__":
    unittest.main()
