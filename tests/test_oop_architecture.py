import dataclasses
import unittest

from bjj_game.domain.competitor import Competitor
from bjj_game.domain.matchup import MatchupTable
from bjj_game.domain.model import Band, BottomBehavior, Grade, Side, TopBehavior
from bjj_game.engine.match import MountMatch
from bjj_game.engine.mount_engine import MountResolutionEngine
from bjj_game.positions.base import Position
from bjj_game.positions.mount.catalog import (
    BOTTOM_ELBOW_KNEE_ESCAPE,
    BOTTOM_RESPONSE_FOREARM_FRAME,
    MOUNT_CATALOG,
    TOP_HIGH_MOUNT_CLIMB,
    TOP_RESPONSE_POST_AND_BASE,
)
from bjj_game.positions.mount.matchups import MOUNT_MATCHUPS
from bjj_game.positions.mount.position import MountPosition
from bjj_game.positions.mount.rules import MOUNT_RULES
from mount_v0.engine import MountRun


class OOPArchitectureTests(unittest.TestCase):
    def test_mount_run_is_compatibility_alias_for_mount_match(self):
        self.assertIs(MountRun, MountMatch)

    def test_match_owns_competitors_and_position_objects(self):
        match = MountMatch(starting_axis=1.50)
        self.assertIsInstance(match.top, Competitor)
        self.assertIsInstance(match.bottom, Competitor)
        self.assertIs(match.top.side, Side.TOP)
        self.assertIs(match.bottom.side, Side.BOTTOM)
        self.assertIs(match.top.behavior, TopBehavior.PRESSURE)
        self.assertIs(match.bottom.behavior, BottomBehavior.ESCAPE)
        self.assertIsInstance(match.position, Position)
        self.assertIsInstance(match.position, MountPosition)
        self.assertEqual(match.position.id, "mount")
        self.assertIs(match.band, Band.STABLE)

    def test_catalog_is_indexed_object(self):
        entity = MOUNT_CATALOG.get(TOP_HIGH_MOUNT_CLIMB)
        self.assertEqual(entity.canonical_name, "High Mount Climb")
        self.assertEqual(len(MOUNT_CATALOG.entities), 12)

    def test_matchup_table_is_object(self):
        self.assertEqual(len(MOUNT_MATCHUPS.entries), 18)

    def test_rules_are_centralized_policy_object(self):
        self.assertIs(MOUNT_RULES.initial_band(1.50), Band.STABLE)
        self.assertEqual(MOUNT_RULES.clamp_axis(5.0), 4.0)

    def test_resolution_engine_dependencies_are_dataclass_fields(self):
        self.assertEqual(
            [field.name for field in dataclasses.fields(MountResolutionEngine)],
            ["rules", "catalog", "matchups"],
        )

    def test_resolution_engine_accepts_custom_matchup_table(self):
        custom = MatchupTable.build(
            {(TOP_HIGH_MOUNT_CLIMB, BOTTOM_RESPONSE_FOREARM_FRAME): Grade.STRONG_FAILURE}
        )
        engine = MountResolutionEngine(
            rules=MOUNT_RULES,
            catalog=MOUNT_CATALOG,
            matchups=custom,
        )
        result = engine.resolve_action(
            axis=1.50,
            band=Band.STABLE,
            initiator=Side.TOP,
            action_id=TOP_HIGH_MOUNT_CLIMB,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
        )
        self.assertIs(result.raw_grade, Grade.STRONG_FAILURE)

    def test_resolution_engine_default_factory_wires_production_dependencies(self):
        engine = MountResolutionEngine.default()
        self.assertIs(engine.rules, MOUNT_RULES)
        self.assertIs(engine.catalog, MOUNT_CATALOG)
        self.assertIs(engine.matchups, MOUNT_MATCHUPS)

    def test_match_uses_injected_engine(self):
        engine = MountResolutionEngine.default()
        match = MountMatch(engine=engine)
        self.assertIs(match.engine, engine)

    def test_competitor_owned_behavior_is_used_when_method_arguments_are_omitted(self):
        match = MountMatch(initial_clock=10, starting_axis=1.50, interval_seconds=5)
        match.top.set_behavior(TopBehavior.HOLD)
        match.bottom.set_behavior(BottomBehavior.ESCAPE)
        result = match.drift()
        self.assertAlmostEqual(result.end_axis, 1.00)
        self.assertEqual(match.history.top_behavior_history, ["HOLD"])
        self.assertEqual(match.history.bottom_behavior_history, ["ESCAPE"])

    def test_legacy_behavior_arguments_update_competitor_state(self):
        match = MountMatch(initial_clock=10, starting_axis=1.50, interval_seconds=5)
        match.drift(TopBehavior.HOLD, BottomBehavior.PROTECT)
        self.assertIs(match.top.behavior, TopBehavior.HOLD)
        self.assertIs(match.bottom.behavior, BottomBehavior.PROTECT)

    def test_escape_does_not_store_negative_value_in_mount_axis(self):
        match = MountMatch(initial_clock=30, starting_axis=0.60, interval_seconds=5)
        match.initiator = Side.BOTTOM
        result = match.decide(
            action_id=BOTTOM_ELBOW_KNEE_ESCAPE,
            response_id=TOP_RESPONSE_POST_AND_BASE,
        )
        self.assertLess(result.axis_after, MOUNT_RULES.min_axis)
        self.assertTrue(match.position.broken)
        self.assertEqual(match.axis, result.axis_after)
        self.assertEqual(match.position.crossing_axis, result.axis_after)
        self.assertEqual(match.position.control.value, 0.60)
        self.assertGreaterEqual(match.position.control.value, MOUNT_RULES.min_axis)

    def test_behavior_modifiers_are_catalog_data(self):
        bridge = MOUNT_CATALOG.get("mount.bottom.bridge")
        trap = MOUNT_CATALOG.get("mount.bottom.trap_and_roll_escape")
        americana = MOUNT_CATALOG.get("mount.top.americana_arm_isolation")
        self.assertEqual(bridge.behavior_modifiers[TopBehavior.HOLD], -1)
        self.assertEqual(trap.behavior_modifiers[TopBehavior.HOLD], -1)
        self.assertEqual(americana.behavior_modifiers[BottomBehavior.PROTECT], -1)
        self.assertTrue(bridge.clamp_at_mount_floor)


if __name__ == "__main__":
    unittest.main()
