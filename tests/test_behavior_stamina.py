import unittest

from bjj_game.domain.model import Band, BottomBehavior, Side, TopBehavior
from bjj_game.engine.match import MountMatch
from bjj_game.engine.mount_engine import MOUNT_ENGINE
from bjj_game.positions.mount.catalog import (
    BOTTOM_BRIDGE,
    BOTTOM_RESPONSE_FOREARM_FRAME,
    TOP_AMERICANA_ARM_ISOLATION,
    TOP_RESPONSE_HIP_FOLLOW_REPUMMEL,
)


class BehaviorStaminaTests(unittest.TestCase):
    def test_pressure_and_escape_cost_one_per_five_seconds(self):
        match = MountMatch(initial_clock=10, starting_axis=1.50, interval_seconds=5)
        match.set_behaviors(top=TopBehavior.PRESSURE, bottom=BottomBehavior.ESCAPE)
        result = match.advance()
        self.assertEqual(result.top_stamina.spent, 1)
        self.assertEqual(result.bottom_stamina.spent, 1)
        self.assertEqual(match.top.stamina.current, 99)
        self.assertEqual(match.bottom.stamina.current, 99)

    def test_hold_and_protect_cost_nothing(self):
        match = MountMatch(initial_clock=10, starting_axis=1.50, interval_seconds=5)
        match.set_behaviors(top=TopBehavior.HOLD, bottom=BottomBehavior.PROTECT)
        result = match.advance()
        self.assertEqual(result.top_stamina.net_change, 0)
        self.assertEqual(result.bottom_stamina.net_change, 0)
        self.assertEqual(match.top.stamina.current, 100)
        self.assertEqual(match.bottom.stamina.current, 100)

    def test_conserve_recovers_two_per_five_seconds_and_caps_at_max(self):
        match = MountMatch(initial_clock=10, starting_axis=1.50, interval_seconds=5)
        match.top.stamina.set_current(50)
        match.bottom.stamina.set_current(99)
        match.set_behaviors(top=TopBehavior.CONSERVE, bottom=BottomBehavior.CONSERVE)

        result = match.advance()

        self.assertEqual(result.top_stamina.recovered, 2)
        self.assertEqual(match.top.stamina.current, 52)
        self.assertEqual(result.bottom_stamina.recovered, 1)
        self.assertEqual(result.bottom_stamina.recovery_overflow, 1)
        self.assertEqual(match.bottom.stamina.current, 100)
        self.assertAlmostEqual(match.axis, 1.50)

    def test_five_one_second_windows_equal_one_five_second_window(self):
        one = MountMatch(initial_clock=10, starting_axis=1.50, interval_seconds=5)
        one.set_behaviors(top=TopBehavior.PRESSURE, bottom=BottomBehavior.PROTECT)
        one.advance()

        five = MountMatch(initial_clock=10, starting_axis=1.50, interval_seconds=1)
        five.set_behaviors(top=TopBehavior.PRESSURE, bottom=BottomBehavior.PROTECT)
        for _ in range(5):
            five.advance()

        self.assertEqual(one.top.stamina.current, five.top.stamina.current)
        self.assertEqual(one.top_behavior_stamina_meter.remainder_units, 0)
        self.assertEqual(five.top_behavior_stamina_meter.remainder_units, 0)

    def test_carry_is_visible_across_behavior_changes(self):
        match = MountMatch(initial_clock=12, starting_axis=1.50, interval_seconds=4)
        match.top.stamina.set_current(50)
        match.set_behaviors(top=TopBehavior.PRESSURE, bottom=BottomBehavior.PROTECT)

        first = match.advance()
        self.assertEqual(first.top_stamina.remainder_before, 0)
        self.assertEqual(first.top_stamina.remainder_after, -4)
        self.assertEqual(match.top.stamina.current, 50)

        match.set_behaviors(top=TopBehavior.CONSERVE)
        second = match.advance()
        self.assertEqual(second.top_stamina.remainder_before, -4)
        self.assertEqual(second.top_stamina.remainder_after, 4)
        self.assertEqual(match.top.stamina.current, 50)

    def test_legacy_drift_does_not_apply_behavior_stamina(self):
        match = MountMatch(initial_clock=10, starting_axis=1.50, interval_seconds=5)
        match.set_behaviors(top=TopBehavior.PRESSURE, bottom=BottomBehavior.ESCAPE)
        match.drift()
        self.assertEqual(match.top.stamina.current, 100)
        self.assertEqual(match.bottom.stamina.current, 100)
        self.assertEqual(match.history.top_behavior_stamina_history, [])
        self.assertEqual(match.history.bottom_behavior_stamina_history, [])

    def test_top_conserve_uses_hold_drift_but_not_hold_action_modifier(self):
        conserve = MOUNT_ENGINE.resolve_action(
            axis=1.50,
            band=Band.STABLE,
            initiator=Side.BOTTOM,
            action_id=BOTTOM_BRIDGE,
            response_id=TOP_RESPONSE_HIP_FOLLOW_REPUMMEL,
            top_behavior=TopBehavior.CONSERVE,
            bottom_behavior=BottomBehavior.ESCAPE,
        )
        hold = MOUNT_ENGINE.resolve_action(
            axis=1.50,
            band=Band.STABLE,
            initiator=Side.BOTTOM,
            action_id=BOTTOM_BRIDGE,
            response_id=TOP_RESPONSE_HIP_FOLLOW_REPUMMEL,
            top_behavior=TopBehavior.HOLD,
            bottom_behavior=BottomBehavior.ESCAPE,
        )
        self.assertEqual(conserve.behavior_modifier, 0)
        self.assertEqual(hold.behavior_modifier, -1)

        conserve_match = MountMatch(initial_clock=10, starting_axis=1.50, interval_seconds=5)
        conserve_match.top.stamina.set_current(50)
        conserve_match.set_behaviors(top=TopBehavior.CONSERVE, bottom=BottomBehavior.ESCAPE)
        conserve_advance = conserve_match.advance()

        hold_match = MountMatch(initial_clock=10, starting_axis=1.50, interval_seconds=5)
        hold_match.set_behaviors(top=TopBehavior.HOLD, bottom=BottomBehavior.ESCAPE)
        hold_advance = hold_match.advance()

        self.assertEqual(conserve_advance.drift.end_axis, hold_advance.drift.end_axis)
        self.assertEqual(conserve_match.top.stamina.current, 52)

    def test_bottom_conserve_uses_protect_drift_but_not_protect_modifier(self):
        conserve = MOUNT_ENGINE.resolve_action(
            axis=1.50,
            band=Band.STABLE,
            initiator=Side.TOP,
            action_id=TOP_AMERICANA_ARM_ISOLATION,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
            top_behavior=TopBehavior.PRESSURE,
            bottom_behavior=BottomBehavior.CONSERVE,
        )
        protect = MOUNT_ENGINE.resolve_action(
            axis=1.50,
            band=Band.STABLE,
            initiator=Side.TOP,
            action_id=TOP_AMERICANA_ARM_ISOLATION,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
            top_behavior=TopBehavior.PRESSURE,
            bottom_behavior=BottomBehavior.PROTECT,
        )
        self.assertEqual(conserve.behavior_modifier, 0)
        self.assertEqual(protect.behavior_modifier, -1)


if __name__ == "__main__":
    unittest.main()
