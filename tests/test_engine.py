import unittest

from mount_v0.catalog import BOTTOM_ELBOW_KNEE_ESCAPE, TOP_RESPONSE_WIDE_MOUNT_BASE
from mount_v0.engine import MountRun
from mount_v0.model import BottomBehavior, ExitDestination, Side, TopBehavior


class EngineTests(unittest.TestCase):
    def test_default_first_initiator_is_top(self):
        run = MountRun()
        self.assertIs(run.initiator, Side.TOP)

    def test_initiator_alternates_after_non_exit_decision(self):
        from mount_v0.catalog import TOP_HIGH_MOUNT_CLIMB, BOTTOM_RESPONSE_TURN_IN_RECOVERY

        run = MountRun(initial_clock=30, starting_axis=1.50, interval_seconds=5)
        run.drift(TopBehavior.HOLD, BottomBehavior.PROTECT)
        run.decide(
            action_id=TOP_HIGH_MOUNT_CLIMB,
            response_id=BOTTOM_RESPONSE_TURN_IN_RECOVERY,
            top_behavior=TopBehavior.HOLD,
            bottom_behavior=BottomBehavior.PROTECT,
        )
        self.assertIs(run.initiator, Side.BOTTOM)

    def test_exit_ends_run(self):
        run = MountRun(initial_clock=30, starting_axis=0.60, interval_seconds=1)
        run.initiator = Side.BOTTOM
        result = run.decide(
            action_id=BOTTOM_ELBOW_KNEE_ESCAPE,
            response_id=TOP_RESPONSE_WIDE_MOUNT_BASE,
            top_behavior=TopBehavior.PRESSURE,
            bottom_behavior=BottomBehavior.ESCAPE,
        )
        self.assertEqual(result.exit_destination, ExitDestination.HALF_GUARD)
        self.assertTrue(run.ended)

    def test_mount_duration_kept_separate_but_equal_in_v0(self):
        run = MountRun(initial_clock=10, interval_seconds=7)
        run.drift(TopBehavior.HOLD, BottomBehavior.PROTECT)
        self.assertEqual(run.elapsed_simulated_time, 7)
        self.assertEqual(run.mount_duration, 7)
