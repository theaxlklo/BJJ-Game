"""Replays of playtests 11 and 12: one bad choice hands the opponent a dominant state.

These lock in how hard v0 punishes a blunder, so later tuning changes it on purpose.
"""

import unittest

from mount_v0.catalog import (
    BOTTOM_ELBOW_KNEE_ESCAPE,
    BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE,
    BOTTOM_RESPONSE_TURN_IN_RECOVERY,
    BOTTOM_TRAP_AND_ROLL_ESCAPE,
    TOP_AMERICANA_ARM_ISOLATION,
    TOP_CROSSFACE_PRESSURE,
    TOP_RESPONSE_POST_AND_BASE,
)
from mount_v0.engine import MountRun
from mount_v0.model import Band, BottomBehavior, ExitDestination, Grade, TopBehavior

P, H = TopBehavior.PRESSURE, TopBehavior.HOLD
E = BottomBehavior.ESCAPE


class BlunderReplayTests(unittest.TestCase):
    def test_11_bottom_blunder_jumps_stable_to_locked_and_mount_survives(self):
        run = MountRun(initial_clock=25, starting_axis=1.60, interval_seconds=5)

        run.drift(P, E)
        run.decide(action_id=TOP_AMERICANA_ARM_ISOLATION, response_id=BOTTOM_RESPONSE_TURN_IN_RECOVERY,
                   top_behavior=P, bottom_behavior=E)
        self.assertAlmostEqual(run.axis, 2.10)

        run.drift(H, E)
        self.assertAlmostEqual(run.axis, 1.60)
        self.assertIs(run.band, Band.STABLE)

        blunder = run.decide(action_id=BOTTOM_TRAP_AND_ROLL_ESCAPE, response_id=TOP_RESPONSE_POST_AND_BASE,
                             top_behavior=H, bottom_behavior=E)
        self.assertIs(blunder.final_grade, Grade.STRONG_FAILURE)
        self.assertAlmostEqual(run.axis, 3.60)
        self.assertIs(run.band, Band.LOCKED)

        run.drift(P, E)
        self.assertAlmostEqual(run.axis, 4.00)
        capped = run.decide(action_id=TOP_CROSSFACE_PRESSURE, response_id=BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE,
                            top_behavior=P, bottom_behavior=E)
        self.assertIs(capped.final_grade, Grade.STRONG_SUCCESS)
        self.assertAlmostEqual(run.axis, 4.00)

        run.drift(P, E)
        best_reply = run.decide(action_id=BOTTOM_ELBOW_KNEE_ESCAPE, response_id=TOP_RESPONSE_POST_AND_BASE,
                                top_behavior=P, bottom_behavior=E)
        self.assertIs(best_reply.final_grade, Grade.SUCCESS)
        self.assertAlmostEqual(run.axis, 3.00)
        self.assertIs(run.band, Band.LOCKED)

        run.drift(P, E)
        self.assertTrue(run.ended)
        self.assertIsNone(run.exit_destination)

    def test_12_top_blunder_is_clamped_then_punished_with_open_guard(self):
        run = MountRun(initial_clock=15, starting_axis=1.50, interval_seconds=5)

        run.drift(P, E)
        self.assertAlmostEqual(run.axis, 2.00)

        blunder = run.decide(action_id=TOP_AMERICANA_ARM_ISOLATION,
                             response_id=BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE,
                             top_behavior=P, bottom_behavior=E)
        self.assertIs(blunder.final_grade, Grade.STRONG_FAILURE)
        self.assertTrue(blunder.failure_clamp_used)
        self.assertAlmostEqual(run.axis, 0.10)
        self.assertIs(run.band, Band.LOOSE)
        self.assertFalse(run.ended)

        run.drift(P, E)
        self.assertAlmostEqual(run.axis, 0.60)
        punish = run.decide(action_id=BOTTOM_ELBOW_KNEE_ESCAPE, response_id=TOP_RESPONSE_POST_AND_BASE,
                            top_behavior=P, bottom_behavior=E)
        self.assertEqual(punish.exit_destination, ExitDestination.OPEN_GUARD)
        self.assertTrue(run.ended)


if __name__ == "__main__":
    unittest.main()
