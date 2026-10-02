import unittest

from mount_v0.catalog import (
    BOTTOM_BRIDGE,
    BOTTOM_ELBOW_KNEE_ESCAPE,
    TOP_HIGH_MOUNT_CLIMB,
    TOP_RESPONSE_HIP_FOLLOW_REPUMMEL,
    TOP_RESPONSE_POST_AND_BASE,
    TOP_RESPONSE_WIDE_MOUNT_BASE,
    BOTTOM_RESPONSE_FOREARM_FRAME,
)
from mount_v0.mechanics import initial_band, resolve_action, simulate_drift, update_band
from mount_v0.model import Band, BottomBehavior, ExitDestination, Side, TopBehavior


class MechanicsTests(unittest.TestCase):
    def test_initial_raw_bands(self):
        self.assertIs(initial_band(0.10), Band.LOOSE)
        self.assertIs(initial_band(1.00), Band.STABLE)
        self.assertIs(initial_band(2.00), Band.STRONG)
        self.assertIs(initial_band(3.00), Band.LOCKED)
        self.assertIs(initial_band(4.00), Band.LOCKED)

    def test_multi_band_jump_up(self):
        band, changes = update_band(3.50, Band.STABLE)
        self.assertIs(band, Band.LOCKED)
        self.assertEqual([(c.before, c.after) for c in changes], [(Band.STABLE, Band.STRONG), (Band.STRONG, Band.LOCKED)])

    def test_multi_band_jump_down(self):
        band, changes = update_band(1.00, Band.LOCKED)
        self.assertIs(band, Band.STABLE)
        self.assertEqual([(c.before, c.after) for c in changes], [(Band.LOCKED, Band.STRONG), (Band.STRONG, Band.STABLE)])

    def test_hysteresis_state_depends_on_history(self):
        stable, _ = update_band(1.90, Band.STABLE)
        strong, _ = update_band(1.90, Band.STRONG)
        self.assertIs(stable, Band.STABLE)
        self.assertIs(strong, Band.STRONG)

    def test_drift_clamps_low_and_high(self):
        low = simulate_drift(
            axis=0.15, band=Band.LOOSE, clock_seconds=5, duration_seconds=5,
            top_behavior=TopBehavior.HOLD, bottom_behavior=BottomBehavior.ESCAPE,
        )
        self.assertEqual(low.end_axis, 0.10)
        high = simulate_drift(
            axis=3.95, band=Band.LOCKED, clock_seconds=5, duration_seconds=5,
            top_behavior=TopBehavior.PRESSURE, bottom_behavior=BottomBehavior.PROTECT,
        )
        self.assertEqual(high.end_axis, 4.00)

    def test_partial_final_interval_uses_real_time(self):
        result = simulate_drift(
            axis=1.50, band=Band.STABLE, clock_seconds=4, duration_seconds=7,
            top_behavior=TopBehavior.PRESSURE, bottom_behavior=BottomBehavior.ESCAPE,
        )
        self.assertEqual(result.start_clock, 4)
        self.assertEqual(result.end_clock, 0)
        self.assertAlmostEqual(result.total_drift, 0.40)

    def test_bridge_never_escapes(self):
        result = resolve_action(
            axis=0.50,
            band=Band.LOOSE,
            initiator=Side.BOTTOM,
            action_id=BOTTOM_BRIDGE,
            response_id=TOP_RESPONSE_HIP_FOLLOW_REPUMMEL,
        )
        self.assertTrue(result.floor_clamp_used)
        self.assertTrue(result.bridge_clamp_used)  # legacy read-only alias
        self.assertEqual(result.axis_after, 0.10)
        self.assertIsNone(result.exit_destination)

    def test_elbow_knee_half_guard_reachable(self):
        result = resolve_action(
            axis=1.10,
            band=Band.STABLE,
            initiator=Side.BOTTOM,
            action_id=BOTTOM_ELBOW_KNEE_ESCAPE,
            response_id=TOP_RESPONSE_WIDE_MOUNT_BASE,
        )
        self.assertEqual(result.exit_destination, ExitDestination.HALF_GUARD)
        self.assertEqual(result.final_grade.value, 1)

    def test_elbow_knee_strong_success_from_stable_exits_to_half_guard(self):
        result = resolve_action(
            axis=2.10,
            band=Band.STABLE,
            initiator=Side.BOTTOM,
            action_id=BOTTOM_ELBOW_KNEE_ESCAPE,
            response_id=TOP_RESPONSE_POST_AND_BASE,
        )
        self.assertEqual(result.exit_destination, ExitDestination.HALF_GUARD)
        self.assertEqual(result.final_grade.value, 2)

    def test_elbow_knee_open_guard_requires_loose_mount(self):
        result = resolve_action(
            axis=0.60,
            band=Band.LOOSE,
            initiator=Side.BOTTOM,
            action_id=BOTTOM_ELBOW_KNEE_ESCAPE,
            response_id=TOP_RESPONSE_POST_AND_BASE,
        )
        self.assertEqual(result.exit_destination, ExitDestination.OPEN_GUARD)
        self.assertEqual(result.final_grade.value, 2)

    def test_strong_band_downgrades_bottom_initiation(self):
        result = resolve_action(
            axis=1.90,
            band=Band.STRONG,
            initiator=Side.BOTTOM,
            action_id=BOTTOM_ELBOW_KNEE_ESCAPE,
            response_id=TOP_RESPONSE_POST_AND_BASE,
        )
        self.assertEqual(result.raw_grade.value, 2)
        self.assertEqual(result.final_grade.value, 1)
        self.assertIsNone(result.exit_destination)

    def test_loose_band_downgrades_top_initiation(self):
        result = resolve_action(
            axis=0.50,
            band=Band.LOOSE,
            initiator=Side.TOP,
            action_id=TOP_HIGH_MOUNT_CLIMB,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
        )
        self.assertEqual(result.raw_grade.value, 1)
        self.assertEqual(result.final_grade.value, 0)

    def test_hold_modifier_uses_real_table_grade(self):
        result = resolve_action(
            axis=1.50,
            band=Band.STABLE,
            initiator=Side.BOTTOM,
            action_id=BOTTOM_BRIDGE,
            response_id=TOP_RESPONSE_HIP_FOLLOW_REPUMMEL,
            top_behavior=TopBehavior.HOLD,
            bottom_behavior=BottomBehavior.ESCAPE,
        )
        self.assertEqual(result.raw_grade.value, 1)
        self.assertEqual(result.behavior_grade.value, 0)
