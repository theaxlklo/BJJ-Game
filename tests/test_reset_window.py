import unittest

from bjj_game.domain.action import Commitment
from bjj_game.domain.model import BottomBehavior, Side, TopBehavior
from bjj_game.domain.stamina import StaminaBand
from bjj_game.engine.match import MountMatch
from bjj_game.engine.stamina import conserve_cycle_net


class ResetWindowTests(unittest.TestCase):
    def test_conserve_cycle_net_exposes_forced_attack_deadlock(self):
        low = conserve_cycle_net(Commitment.LOW)
        medium = conserve_cycle_net(Commitment.MEDIUM)
        high = conserve_cycle_net(Commitment.HIGH)

        self.assertEqual(low.attack_net, 1)
        self.assertEqual(medium.attack_net, -3)
        self.assertEqual(high.attack_net, -8)
        self.assertEqual(medium.reset_net, 4)

    def test_reset_yields_initiative_without_action_cost_or_axis_change(self):
        match = MountMatch(initial_clock=30, starting_axis=1.50, interval_seconds=5)
        match.top.stamina.set_current(25)
        axis_before = match.axis
        clock_before = match.clock_seconds

        result = match.reset_window()

        self.assertIs(result.initiator, Side.TOP)
        self.assertIs(result.next_initiator, Side.BOTTOM)
        self.assertIs(match.initiator, Side.BOTTOM)
        self.assertAlmostEqual(match.axis, axis_before)
        self.assertEqual(match.clock_seconds, clock_before)
        self.assertEqual(match.top.stamina.current, 25)
        self.assertEqual(match.history.initiated_action_history, [])
        self.assertEqual(match.history.commitment_history, [])
        self.assertEqual(match.history.reset_window_history, ["top"])

    def test_pure_conserve_plus_reset_can_escape_exhaustion(self):
        match = MountMatch(initial_clock=30, starting_axis=1.50, interval_seconds=5)
        match.top.stamina.set_current(25)
        match.bottom.stamina.set_current(25)
        match.set_behaviors(
            top=TopBehavior.CONSERVE,
            bottom=BottomBehavior.CONSERVE,
        )

        for _ in range(5):
            match.advance()
            match.reset_window()

        self.assertEqual(match.elapsed_simulated_time, 25)
        self.assertEqual(match.top.stamina.current, 35)
        self.assertEqual(match.bottom.stamina.current, 35)
        self.assertIs(match.top.stamina.band, StaminaBand.TIRED)
        self.assertIs(match.bottom.stamina.band, StaminaBand.TIRED)
        self.assertEqual(
            match.history.reset_window_history,
            ["top", "bottom", "top", "bottom", "top"],
        )

    def test_reset_does_not_bypass_behavior_tradeoff(self):
        match = MountMatch(initial_clock=10, starting_axis=1.50, interval_seconds=5)
        match.top.stamina.set_current(25)
        match.set_behaviors(
            top=TopBehavior.CONSERVE,
            bottom=BottomBehavior.ESCAPE,
        )

        advance = match.advance()
        axis_after_drift = match.axis
        stamina_after_drift = match.top.stamina.current
        match.reset_window()

        self.assertEqual(stamina_after_drift, 27)
        self.assertAlmostEqual(match.axis, axis_after_drift)
        self.assertLess(axis_after_drift, 1.50)
        self.assertIs(match.top.stamina.band, StaminaBand.EXHAUSTED)


if __name__ == "__main__":
    unittest.main()
