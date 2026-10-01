import unittest

from mount_v0.catalog import BOTTOM_BRIDGE, actions_for, responses_for
from mount_v0.mechanics import MIN_AXIS, MAX_AXIS, axis_can_have_band, resolve_action
from mount_v0.model import Band, BottomBehavior, Grade, Side, TopBehavior


class ExhaustiveStateSpaceTests(unittest.TestCase):
    def test_all_reachable_mount_states_preserve_v0_invariants(self):
        axes = [round(i / 100, 2) for i in range(10, 401)]
        behavior_pairs = [
            (top, bottom)
            for top in TopBehavior
            for bottom in BottomBehavior
        ]
        checked = 0
        exits = 0
        for band in Band:
            for axis in axes:
                if not axis_can_have_band(axis, band):
                    continue
                for side in (Side.TOP, Side.BOTTOM):
                    for action in actions_for(side):
                        for response in responses_for(side.opponent):
                            for top_behavior, bottom_behavior in behavior_pairs:
                                result = resolve_action(
                                    axis=axis,
                                    band=band,
                                    initiator=side,
                                    action_id=action.id,
                                    response_id=response.id,
                                    top_behavior=top_behavior,
                                    bottom_behavior=bottom_behavior,
                                )
                                checked += 1
                                if result.exit_destination is None:
                                    self.assertGreaterEqual(result.axis_after, MIN_AXIS)
                                    self.assertLessEqual(result.axis_after, MAX_AXIS)
                                    self.assertFalse(0.0 < result.axis_after < MIN_AXIS)
                                else:
                                    exits += 1
                                    self.assertIs(side, Side.BOTTOM)
                                    self.assertTrue(result.final_grade.successful)
                                    self.assertTrue(result.exit_capable_action)
                                    self.assertLessEqual(result.proposed_axis, MIN_AXIS)

                                if result.final_grade.failed:
                                    self.assertIsNone(result.exit_destination)
                                if action.id == BOTTOM_BRIDGE:
                                    self.assertIsNone(result.exit_destination)

        self.assertGreater(checked, 30_000)
        self.assertGreater(exits, 0)
