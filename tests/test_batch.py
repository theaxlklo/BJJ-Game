import unittest

from bjj_game.domain.action import Commitment
from bjj_game.domain.model import BottomBehavior, Side, TopBehavior
from bjj_game.engine.match import MountMatch
from bjj_game.interfaces.batch import GreedyInitiatorPolicy, run_greedy_batch


class GreedyInitiatorPolicyTests(unittest.TestCase):
    def test_top_attacks_from_stable_when_realized_expectation_is_positive(self):
        match = MountMatch(starting_axis=1.50)
        match.set_behaviors(top=TopBehavior.PRESSURE, bottom=BottomBehavior.ESCAPE)

        decision = GreedyInitiatorPolicy().choose(match)

        self.assertIsNotNone(decision.action_id)
        self.assertGreater(decision.expected_realized_axis, 0)

    def test_bottom_resets_from_strong_when_every_realized_expectation_is_negative(self):
        match = MountMatch(starting_axis=2.50)
        match.initiator = Side.BOTTOM
        match.set_behaviors(top=TopBehavior.PRESSURE, bottom=BottomBehavior.ESCAPE)

        decision = GreedyInitiatorPolicy().choose(match)

        self.assertIsNone(decision.action_id)
        self.assertLess(decision.expected_realized_axis, 0)

    def test_top_resets_from_locked_when_cap_skew_removes_positive_realized_gain(self):
        match = MountMatch(starting_axis=3.50)
        match.set_behaviors(top=TopBehavior.PRESSURE, bottom=BottomBehavior.ESCAPE)

        decision = GreedyInitiatorPolicy().choose(match)

        self.assertIsNone(decision.action_id)
        self.assertLessEqual(decision.expected_realized_axis, 0)


class BatchSimulationTests(unittest.TestCase):
    def _run(self):
        return run_greedy_batch(
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

    def test_batch_render_keeps_outcomes_stamina_and_decisions_separate(self):
        text = self._run().render()

        self.assertIn("BATCH SUMMARY", text)
        self.assertIn("Initiator policy: greedy realized-axis (>0 attack, otherwise RESET)", text)
        self.assertIn("OUTCOMES", text)
        self.assertIn("FINAL STAMINA", text)
        self.assertIn("DECISIONS", text)
        self.assertIn("Top RESET count:", text)
        self.assertIn("Bottom RESET count:", text)


if __name__ == "__main__":
    unittest.main()
