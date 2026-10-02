import unittest

from bjj_game.domain.action import Commitment
from bjj_game.domain.model import BottomBehavior, Side, TopBehavior
from bjj_game.engine.match import MountMatch
from bjj_game.interfaces.batch import EscapeFirstInitiatorPolicy, run_escape_first_batch


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

    def test_batch_render_keeps_outcomes_stamina_and_decisions_separate(self):
        text = self._run().render()

        self.assertIn("BATCH SUMMARY", text)
        self.assertIn("Initiator policy: escape-first lexicographic", text)
        self.assertIn("Escape rule: highest exact escape probability first", text)
        self.assertIn("Position rule: require raw axis > 0 AND realized axis > 0", text)
        self.assertIn("OUTCOMES", text)
        self.assertIn("FINAL STAMINA", text)
        self.assertIn("DECISIONS", text)
        self.assertIn("Top RESET count:", text)
        self.assertIn("Bottom RESET count:", text)
        self.assertIn("Top escape-priority attacks:", text)
        self.assertIn("Bottom escape-priority attacks:", text)


if __name__ == "__main__":
    unittest.main()
