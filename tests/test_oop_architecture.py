import unittest

from bjj_game.domain.competitor import Competitor
from bjj_game.domain.model import Band, Side
from bjj_game.engine.match import MountMatch
from bjj_game.engine.mount_engine import MountResolutionEngine
from bjj_game.positions.base import Position
from bjj_game.positions.mount.catalog import MOUNT_CATALOG, TOP_HIGH_MOUNT_CLIMB
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

    def test_resolution_engine_is_injectable(self):
        engine = MountResolutionEngine()
        match = MountMatch(engine=engine)
        self.assertIs(match.engine, engine)


if __name__ == "__main__":
    unittest.main()
