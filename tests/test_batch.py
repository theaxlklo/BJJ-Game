import unittest

from bjj_game.domain.action import Commitment
from bjj_game.domain.model import BottomBehavior, Side, TopBehavior
from bjj_game.domain.submission import SubmissionStage
from bjj_game.engine.match import MountMatch
from bjj_game.positions.mount.catalog import (
    TOP_AMERICANA_ARM_ISOLATION,
    TOP_AMERICANA_SUBMISSION_FINISH,
    TOP_HIGH_MOUNT_CLIMB,
)
from bjj_game.interfaces.batch import AdaptiveBehaviorPolicy, BatchBehaviorMode, EscapeFirstInitiatorPolicy, run_escape_first_batch


class AdaptiveBehaviorPolicyTests(unittest.TestCase):
    def test_bottom_recover_policy_uses_conserve_until_hysteresis_clears(self):
        match = MountMatch(starting_axis=1.50)
        match.bottom.stamina.set_current(25)
        policy = AdaptiveBehaviorPolicy(
            side=Side.BOTTOM,
            baseline=BottomBehavior.PROTECT,
            mode=BatchBehaviorMode.RECOVER,
        )

        self.assertIs(policy.choose(match), BottomBehavior.CONSERVE)
        match.bottom.stamina.recover_up_to(9)
        self.assertEqual(match.bottom.stamina.current, 34)
        self.assertIs(policy.choose(match), BottomBehavior.CONSERVE)

        match.bottom.stamina.recover_up_to(1)
        self.assertEqual(match.bottom.stamina.current, 35)
        self.assertIs(policy.choose(match), BottomBehavior.PROTECT)

    def test_fixed_policy_never_switches_to_conserve(self):
        match = MountMatch(starting_axis=1.50)
        match.top.stamina.set_current(0)
        policy = AdaptiveBehaviorPolicy(
            side=Side.TOP,
            baseline=TopBehavior.PRESSURE,
            mode=BatchBehaviorMode.FIXED,
        )
        self.assertIs(policy.choose(match), TopBehavior.PRESSURE)


class EscapeFirstInitiatorPolicyTests(unittest.TestCase):
    def test_top_attacks_from_stable_when_realized_expectation_is_positive(self):
        match = MountMatch(starting_axis=1.50)
        match.set_behaviors(top=TopBehavior.PRESSURE, bottom=BottomBehavior.ESCAPE)

        decision = EscapeFirstInitiatorPolicy().choose(match)

        self.assertIsNotNone(decision.action_id)
        self.assertGreater(decision.expected_realized_axis, 0)

    def test_bottom_resets_from_strong_when_every_realized_expectation_is_negative(self):
        match = MountMatch(starting_axis=2.50)
        match.initiator = Side.BOTTOM
        match.set_behaviors(top=TopBehavior.PRESSURE, bottom=BottomBehavior.ESCAPE)

        decision = EscapeFirstInitiatorPolicy().choose(match)

        self.assertIsNone(decision.action_id)
        self.assertLess(decision.expected_realized_axis, 0)

    def test_bottom_at_mount_floor_attacks_for_escape_even_without_positive_axis_value(self):
        match = MountMatch(starting_axis=0.10)
        match.initiator = Side.BOTTOM
        match.set_behaviors(top=TopBehavior.HOLD, bottom=BottomBehavior.ESCAPE)

        decision = EscapeFirstInitiatorPolicy().choose(match)

        self.assertEqual(decision.reason, "escape")
        self.assertIsNotNone(decision.action_id)
        self.assertAlmostEqual(decision.escape_probability, 2 / 3)

    def test_submission_progress_precedes_position_and_reset_at_locked(self):
        match = MountMatch(
            starting_axis=3.50,
            enable_v02_setup=True,
            enable_v03_submissions=True,
        )
        match.submission_state.stage = SubmissionStage.THREAT
        match.initiator = Side.TOP
        match.set_behaviors(
            top=TopBehavior.PRESSURE,
            bottom=BottomBehavior.ESCAPE,
        )

        decision = EscapeFirstInitiatorPolicy().choose(match)

        self.assertEqual(decision.action_id, TOP_AMERICANA_SUBMISSION_FINISH)
        self.assertEqual(decision.reason, "submission")
        self.assertAlmostEqual(decision.submission_progress_probability, 4 / 7)
        self.assertEqual(decision.expected_raw_axis, 0.0)
        self.assertEqual(decision.expected_realized_axis, 0.0)

    def test_v03_locked_setup_builder_is_valuable_when_ready_target_can_enter_submission(self):
        match = MountMatch(
            starting_axis=4.00,
            enable_v02_setup=True,
            enable_v03_submissions=True,
        )
        match.bottom.stamina.set_current(25)
        match.set_behaviors(
            top=TopBehavior.PRESSURE,
            bottom=BottomBehavior.ESCAPE,
        )

        decision = EscapeFirstInitiatorPolicy().choose(match)

        self.assertEqual(decision.action_id, TOP_HIGH_MOUNT_CLIMB)
        self.assertEqual(decision.reason, "setup")

    def test_fresh_ready_americana_entry_uses_projected_four_to_three_mix(self):
        match = MountMatch(
            starting_axis=4.00,
            enable_v02_setup=True,
            enable_v03_submissions=True,
        )
        match.setup_state.advance(TOP_AMERICANA_ARM_ISOLATION)
        match.setup_state.advance(TOP_AMERICANA_ARM_ISOLATION)
        match.set_behaviors(
            top=TopBehavior.PRESSURE,
            bottom=BottomBehavior.ESCAPE,
        )

        decision = EscapeFirstInitiatorPolicy().choose(match)

        self.assertEqual(decision.action_id, TOP_AMERICANA_ARM_ISOLATION)
        self.assertEqual(decision.reason, "submission")
        self.assertAlmostEqual(decision.submission_progress_probability, 4 / 7)

    def test_v03_ready_americana_entry_precedes_position_and_reset_at_locked(self):
        match = MountMatch(
            starting_axis=4.00,
            enable_v02_setup=True,
            enable_v03_submissions=True,
        )
        match.setup_state.advance(TOP_AMERICANA_ARM_ISOLATION)
        match.setup_state.advance(TOP_AMERICANA_ARM_ISOLATION)
        match.bottom.stamina.set_current(25)
        match.set_behaviors(
            top=TopBehavior.PRESSURE,
            bottom=BottomBehavior.ESCAPE,
        )

        decision = EscapeFirstInitiatorPolicy().choose(match)

        self.assertEqual(decision.action_id, TOP_AMERICANA_ARM_ISOLATION)
        self.assertEqual(decision.reason, "submission")
        self.assertGreater(decision.submission_progress_probability, 0.0)
        self.assertEqual(decision.expected_realized_axis, 0.0)

    def test_setup_policy_does_not_build_useless_locked_top_target(self):
        match = MountMatch(starting_axis=4.00, enable_v02_setup=True)
        match.set_behaviors(
            top=TopBehavior.PRESSURE,
            bottom=BottomBehavior.ESCAPE,
        )

        decision = EscapeFirstInitiatorPolicy().choose(match)

        self.assertIsNone(decision.action_id)
        self.assertEqual(decision.reason, "reset")

    def test_bottom_at_locked_resets_when_only_cap_skew_makes_realized_axis_look_good(self):
        match = MountMatch(starting_axis=4.00)
        match.initiator = Side.BOTTOM
        match.set_behaviors(top=TopBehavior.PRESSURE, bottom=BottomBehavior.ESCAPE)

        decision = EscapeFirstInitiatorPolicy().choose(match)

        self.assertIsNone(decision.action_id)
        self.assertEqual(decision.reason, "reset")
        self.assertLessEqual(decision.expected_raw_axis, 0)


class BatchSimulationTests(unittest.TestCase):
    def _run(self):
        return run_escape_first_batch(
            matches=12,
            base_seed=42,
            top_behavior=TopBehavior.HOLD,
            bottom_behavior=BottomBehavior.CONSERVE,
            commitment=Commitment.MEDIUM,
            initial_clock=60,
            starting_axis=1.50,
            interval_seconds=5,
            top_stamina=100,
            bottom_stamina=100,
        )

    def test_batch_is_deterministic_for_same_seed_and_condition(self):
        self.assertEqual(self._run(), self._run())

    def test_batch_outcomes_cover_every_match_and_stamina_stays_bounded(self):
        summary = self._run()

        self.assertEqual(sum(summary.outcome_counts.values()), summary.matches)
        self.assertGreaterEqual(summary.top_final_stamina_mean, 0)
        self.assertLessEqual(summary.top_final_stamina_mean, 100)
        self.assertGreaterEqual(summary.bottom_final_stamina_mean, 0)
        self.assertLessEqual(summary.bottom_final_stamina_mean, 100)

    def test_escape_first_batch_produces_real_escape_outcomes(self):
        summary = run_escape_first_batch(
            matches=40,
            base_seed=42,
            top_behavior=TopBehavior.HOLD,
            bottom_behavior=BottomBehavior.ESCAPE,
            commitment=Commitment.MEDIUM,
            initial_clock=300,
            starting_axis=1.50,
            interval_seconds=5,
            top_stamina=100,
            bottom_stamina=100,
        )

        escaped = (
            summary.outcome_counts.get("Half Guard", 0)
            + summary.outcome_counts.get("Open Guard", 0)
            + summary.outcome_counts.get("Reversal", 0)
        )
        self.assertGreater(escaped, 0)
        self.assertGreater(summary.bottom_escape_priority_count, 0)

    def test_recover_batch_exercises_conserve_then_returns_to_baseline(self):
        summary = run_escape_first_batch(
            matches=1,
            base_seed=42,
            top_behavior=TopBehavior.HOLD,
            bottom_behavior=BottomBehavior.PROTECT,
            commitment=Commitment.MEDIUM,
            initial_clock=60,
            starting_axis=3.50,
            interval_seconds=5,
            top_stamina=25,
            bottom_stamina=25,
            top_behavior_mode=BatchBehaviorMode.RECOVER,
            bottom_behavior_mode=BatchBehaviorMode.RECOVER,
        )

        self.assertGreater(summary.top_behavior_window_counts.get("CONSERVE", 0), 0)
        self.assertGreater(summary.bottom_behavior_window_counts.get("CONSERVE", 0), 0)
        self.assertGreater(summary.top_behavior_window_counts.get("HOLD", 0), 0)
        self.assertGreater(summary.bottom_behavior_window_counts.get("PROTECT", 0), 0)
        self.assertGreaterEqual(summary.top_behavior_switch_count, 1)
        self.assertGreaterEqual(summary.bottom_behavior_switch_count, 1)

    def test_followup_position_count_excludes_each_match_first_top_attack(self):
        summary = run_escape_first_batch(
            matches=12,
            base_seed=42,
            top_behavior=TopBehavior.PRESSURE,
            bottom_behavior=BottomBehavior.ESCAPE,
            commitment=Commitment.MEDIUM,
            initial_clock=300,
            starting_axis=1.50,
            interval_seconds=5,
            top_stamina=100,
            bottom_stamina=100,
        )

        self.assertLessEqual(
            summary.top_followup_position_attack_count,
            summary.top_position_attack_count,
        )
        first_attacks = (
            summary.top_position_attack_count
            - summary.top_followup_position_attack_count
        )
        self.assertLessEqual(first_attacks, summary.matches)
        self.assertGreater(first_attacks, 0)

    def test_setup_builds_only_get_completed_chain_credit_after_target_use(self):
        summary = run_escape_first_batch(
            matches=30,
            base_seed=42,
            top_behavior=TopBehavior.PRESSURE,
            bottom_behavior=BottomBehavior.ESCAPE,
            commitment=Commitment.MEDIUM,
            initial_clock=300,
            starting_axis=1.50,
            interval_seconds=5,
            top_stamina=100,
            bottom_stamina=100,
            enable_v02_setup=True,
        )

        self.assertLessEqual(
            summary.top_completed_setup_build_count,
            summary.top_setup_action_count,
        )
        self.assertLessEqual(
            summary.bottom_completed_setup_build_count,
            summary.bottom_setup_action_count,
        )
        self.assertGreaterEqual(summary.bottom_completed_setup_chain_count, 0)
        self.assertGreaterEqual(summary.top_completed_setup_chain_count, 0)

    def test_batch_render_keeps_outcomes_stamina_and_decisions_separate(self):
        text = self._run().render()

        self.assertIn("BATCH SUMMARY", text)
        self.assertIn("Initiator policy: escape-first lexicographic", text)
        self.assertIn("Escape rule: highest exact escape probability first", text)
        self.assertIn("Position rule: require raw axis > 0 AND realized axis > 0", text)
        self.assertIn("OUTCOMES", text)
        self.assertIn("FINAL STAMINA", text)
        self.assertIn("DECISIONS", text)
        self.assertIn("BEHAVIOR USAGE", text)
        self.assertIn("Top RESET count:", text)
        self.assertIn("Bottom RESET count:", text)
        self.assertIn("Top escape-priority attacks:", text)
        self.assertIn("Bottom escape-priority attacks:", text)
        self.assertIn("Top follow-up position attacks:", text)
        self.assertIn("Top completed setup chains:", text)
        self.assertIn("Top setup builds in completed chains:", text)


if __name__ == "__main__":
    unittest.main()
