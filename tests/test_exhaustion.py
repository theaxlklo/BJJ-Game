import unittest

from bjj_game.domain.action import Commitment
from bjj_game.domain.model import BottomBehavior, Grade, Side, TopBehavior
from bjj_game.domain.stamina import StaminaBand
from bjj_game.engine.match import MountMatch
from bjj_game.engine.stamina import (
    DEFAULT_EXHAUSTION_POLICY,
    project_active_stamina_pacing,
)
from bjj_game.positions.mount.catalog import (
    BOTTOM_RESPONSE_FOREARM_FRAME,
    TOP_HIGH_MOUNT_CLIMB,
)


class ExhaustionPolicyTests(unittest.TestCase):
    def test_only_exhausted_band_gets_grade_penalty(self):
        self.assertEqual(
            DEFAULT_EXHAUSTION_POLICY.initiator_grade_modifier(StaminaBand.FRESH), 0
        )
        self.assertEqual(
            DEFAULT_EXHAUSTION_POLICY.initiator_grade_modifier(StaminaBand.WORKING), 0
        )
        self.assertEqual(
            DEFAULT_EXHAUSTION_POLICY.initiator_grade_modifier(StaminaBand.TIRED), 0
        )
        self.assertEqual(
            DEFAULT_EXHAUSTION_POLICY.initiator_grade_modifier(StaminaBand.EXHAUSTED), -1
        )

    def test_exhausted_initiator_drops_one_grade(self):
        match = MountMatch(starting_axis=1.50)
        match.top.stamina.set_current(25)

        result = match.attempt(
            action_id=TOP_HIGH_MOUNT_CLIMB,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
            commitment=Commitment.LOW,
        )

        self.assertIs(result.stamina_band_before_action, StaminaBand.EXHAUSTED)
        self.assertEqual(result.exhaustion_modifier, -1)
        self.assertIs(result.base_resolution.final_grade, Grade.SUCCESS)
        self.assertIs(result.resolution.final_grade, Grade.CONTESTED)
        self.assertAlmostEqual(match.axis, 1.50)

    def test_tired_boundary_at_26_has_no_penalty(self):
        match = MountMatch(starting_axis=1.50)
        match.top.stamina.set_current(26)

        result = match.attempt(
            action_id=TOP_HIGH_MOUNT_CLIMB,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
            commitment=Commitment.LOW,
        )

        self.assertIs(result.stamina_band_before_action, StaminaBand.TIRED)
        self.assertEqual(result.exhaustion_modifier, 0)
        self.assertEqual(result.base_resolution, result.resolution)
        self.assertIs(result.resolution.final_grade, Grade.SUCCESS)

    def test_conserve_from_24_to_26_does_not_clear_exhaustion(self):
        match = MountMatch(initial_clock=10, starting_axis=1.50, interval_seconds=5)
        match.top.stamina.set_current(24)
        match.set_behaviors(top=TopBehavior.CONSERVE, bottom=BottomBehavior.PROTECT)

        advance = match.advance()
        self.assertEqual(match.top.stamina.current, 26)
        self.assertIs(match.top.stamina.band, StaminaBand.EXHAUSTED)
        self.assertEqual(advance.top_stamina.recovered, 2)

        result = match.attempt(
            action_id=TOP_HIGH_MOUNT_CLIMB,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
            commitment=Commitment.LOW,
        )
        self.assertEqual(result.exhaustion_modifier, -1)
        self.assertIs(result.base_resolution.final_grade, Grade.SUCCESS)
        self.assertIs(result.resolution.final_grade, Grade.CONTESTED)

    def test_action_that_enters_exhausted_is_not_retroactively_penalized(self):
        match = MountMatch(starting_axis=1.50)
        match.top.stamina.set_current(30)

        first = match.attempt(
            action_id=TOP_HIGH_MOUNT_CLIMB,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
            commitment=Commitment.MEDIUM,
        )
        self.assertIs(first.stamina_band_before_action, StaminaBand.TIRED)
        self.assertEqual(first.exhaustion_modifier, 0)
        self.assertEqual(match.top.stamina.current, 23)
        self.assertIs(match.top.stamina.band, StaminaBand.EXHAUSTED)

        match.initiator = Side.TOP
        second = match.attempt(
            action_id=TOP_HIGH_MOUNT_CLIMB,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
            commitment=Commitment.LOW,
        )
        self.assertEqual(second.exhaustion_modifier, -1)
        self.assertIs(second.base_resolution.final_grade, Grade.SUCCESS)
        self.assertIs(second.resolution.final_grade, Grade.CONTESTED)

    def test_legacy_decide_ignores_exhaustion(self):
        match = MountMatch(starting_axis=1.50)
        match.top.stamina.set_current(0)

        result = match.decide(
            action_id=TOP_HIGH_MOUNT_CLIMB,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
        )

        self.assertIs(result.final_grade, Grade.SUCCESS)
        self.assertEqual(result.external_grade_modifier, 0)


class StaminaPacingTests(unittest.TestCase):
    def test_current_active_pacing_is_reported_exactly(self):
        low = project_active_stamina_pacing(commitment=Commitment.LOW)
        medium = project_active_stamina_pacing(commitment=Commitment.MEDIUM)
        high = project_active_stamina_pacing(commitment=Commitment.HIGH)

        self.assertEqual(
            (low.top_exhausted_seconds, low.bottom_exhausted_seconds),
            (150, 150),
        )
        self.assertEqual((low.top_zero_seconds, low.bottom_zero_seconds), (200, 200))

        self.assertEqual(
            (medium.top_exhausted_seconds, medium.bottom_exhausted_seconds),
            (85, 90),
        )
        self.assertEqual(
            (medium.top_zero_seconds, medium.bottom_zero_seconds),
            (115, 115),
        )

        self.assertEqual(
            (high.top_exhausted_seconds, high.bottom_exhausted_seconds),
            (55, 60),
        )
        self.assertEqual((high.top_zero_seconds, high.bottom_zero_seconds), (80, 80))


if __name__ == "__main__":
    unittest.main()
