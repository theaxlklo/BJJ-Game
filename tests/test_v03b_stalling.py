import unittest

from bjj_game.domain.action import Commitment
from bjj_game.domain.model import Band, BottomBehavior, Side, TopBehavior
from bjj_game.domain.submission import SubmissionStage
from bjj_game.engine.match import MountMatch
from bjj_game.engine.stalling import (
    STALLING_THRESHOLD_SECONDS,
    StallingConsequence,
    StallingTracker,
)
from bjj_game.positions.mount.catalog import (
    BOTTOM_RESPONSE_TURN_IN_RECOVERY,
    TOP_AMERICANA_SUBMISSION_FINISH,
)


class V03BStallingTests(unittest.TestCase):
    def _match(
        self,
        *,
        axis: float = 3.50,
        interval: int = 5,
    ) -> MountMatch:
        match = MountMatch(
            initial_clock=300,
            starting_axis=axis,
            interval_seconds=interval,
            enable_v02_setup=True,
            enable_v03_submissions=True,
            enable_v03b_stalling=True,
        )
        match.set_behaviors(
            top=TopBehavior.PRESSURE,
            bottom=BottomBehavior.ESCAPE,
        )
        return match

    def _active_threat(
        self,
        *,
        axis: float = 3.50,
        interval: int = 5,
    ) -> MountMatch:
        match = self._match(axis=axis, interval=interval)
        match.submission_state.stage = SubmissionStage.THREAT
        return match

    def test_v03b_requires_v03a_submissions(self):
        with self.assertRaises(ValueError):
            MountMatch(
                enable_v02_setup=True,
                enable_v03_submissions=False,
                enable_v03b_stalling=True,
            )

    def test_progress_capability_is_pre_response_and_submission_stage_counts(self):
        match = self._active_threat()
        self.assertIn(
            TOP_AMERICANA_SUBMISSION_FINISH,
            match.progress_capable_action_ids(),
        )

    def test_contested_submission_attempt_resets_both_advancement_clocks(self):
        match = self._active_threat()
        match.stalling_tracker.advance(20)
        self.assertEqual(match.advancement_clock(Side.TOP), 20)
        self.assertEqual(match.advancement_clock(Side.BOTTOM), 20)

        result = match.attempt(
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            response_id=BOTTOM_RESPONSE_TURN_IN_RECOVERY,
            commitment=Commitment.LOW,
        )

        self.assertEqual(result.resolution.final_grade.value, 0)
        self.assertIs(match.submission_state.stage, SubmissionStage.THREAT)
        self.assertEqual(match.advancement_clock(Side.TOP), 0)
        self.assertEqual(match.advancement_clock(Side.BOTTOM), 0)
        self.assertEqual(len(match.history.stalling_progress_engagement_history), 1)
        self.assertEqual(len(match.history.stalling_defensive_engagement_history), 1)
        self.assertEqual(match.history.stalling_penalty_history, [])

    def test_first_offense_is_persistent_warning(self):
        match = self._active_threat()
        match.stalling_tracker.advance(STALLING_THRESHOLD_SECONDS)

        reset = match.reset_window()

        self.assertTrue(reset.progress_route_available)
        self.assertTrue(reset.stalling_offense)
        self.assertEqual(
            reset.stalling_consequence,
            StallingConsequence.WARNING.value,
        )
        self.assertTrue(match.stalling_warned(Side.TOP))
        self.assertEqual(match.advancement_clock(Side.TOP), 0)
        self.assertEqual(match.history.stalling_penalty_history, [])

        # Engagement clears the clock but not the match-long warning.
        match.initiator = Side.TOP
        match.stalling_tracker.advance(5)
        match.attempt(
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            response_id=BOTTOM_RESPONSE_TURN_IN_RECOVERY,
            commitment=Commitment.LOW,
        )
        self.assertEqual(match.advancement_clock(Side.TOP), 0)
        self.assertTrue(match.stalling_warned(Side.TOP))

    def test_later_top_offense_moves_exactly_one_band_toward_bottom(self):
        match = self._active_threat(axis=4.00)

        match.stalling_tracker.advance(20)
        warning = match.reset_window()
        self.assertEqual(warning.stalling_consequence, "WARNING")

        match.initiator = Side.TOP
        match.stalling_tracker.advance(20)
        penalty = match.reset_window()

        self.assertEqual(penalty.stalling_consequence, "PENALTY")
        self.assertEqual(penalty.penalty_axis_before, 4.00)
        self.assertEqual(penalty.penalty_axis_after, 2.80)
        self.assertAlmostEqual(match.axis, 2.80)
        self.assertIs(match.band, Band.STRONG)
        self.assertFalse(penalty.free_initiative_window)

    def test_bottom_can_receive_same_penalty_toward_top(self):
        match = self._match(axis=1.50)
        match.initiator = Side.BOTTOM
        self.assertTrue(match.progress_capable_action_ids())

        match.stalling_tracker.advance(20)
        warning = match.reset_window()
        self.assertEqual(warning.stalling_consequence, "WARNING")

        match.initiator = Side.BOTTOM
        match.stalling_tracker.advance(20)
        penalty = match.reset_window()

        self.assertEqual(penalty.stalling_consequence, "PENALTY")
        self.assertAlmostEqual(match.axis, 2.20)
        self.assertIs(match.band, Band.STRONG)

    def test_loose_boundary_uses_zero_time_free_initiative_instead_of_crossing(self):
        match = self._active_threat(axis=0.50)

        match.stalling_tracker.advance(20)
        match.reset_window()  # warning
        match.initiator = Side.TOP
        match.stalling_tracker.advance(20)
        clock_before = match.clock_seconds
        penalty = match.reset_window()

        self.assertTrue(penalty.free_initiative_window)
        self.assertAlmostEqual(match.axis, 0.50)
        self.assertIs(match.band, Band.LOOSE)
        self.assertEqual(match.clock_seconds, clock_before)
        self.assertTrue(match.free_initiative_pending)
        self.assertIs(match.initiator, Side.BOTTOM)
        self.assertIs(match.consume_free_initiative_window(), Side.BOTTOM)
        self.assertFalse(match.free_initiative_pending)

    def test_reset_without_progress_route_never_becomes_offense(self):
        tracker = StallingTracker()
        tracker.advance(60)

        evaluation = tracker.evaluate_reset(
            side=Side.TOP,
            progress_route_available=False,
        )

        self.assertFalse(evaluation.progress_route_available)
        self.assertFalse(evaluation.offense)
        self.assertIs(
            evaluation.consequence,
            StallingConsequence.NONE,
        )
        self.assertFalse(tracker.warned[Side.TOP])
        self.assertEqual(tracker.clock(Side.TOP), 60)

    def test_disabled_v03b_keeps_reset_stamina_and_axis_semantics(self):
        match = MountMatch(
            initial_clock=30,
            starting_axis=1.50,
            interval_seconds=5,
            enable_v02_setup=True,
            enable_v03_submissions=True,
            enable_v03b_stalling=False,
        )
        match.top.stamina.set_current(25)
        axis_before = match.axis

        result = match.reset_window()

        self.assertAlmostEqual(match.axis, axis_before)
        self.assertEqual(match.top.stamina.current, 25)
        self.assertFalse(result.progress_route_available)
        self.assertFalse(result.stalling_offense)
        self.assertIsNone(result.stalling_consequence)

    def test_threshold_is_time_based_not_window_count(self):
        self.assertEqual(STALLING_THRESHOLD_SECONDS, 20)

        for interval in (2, 5, 7):
            with self.subTest(interval=interval):
                tracker = StallingTracker()
                elapsed = 0
                while elapsed < 20:
                    step = min(interval, 20 - elapsed)
                    tracker.advance(step)
                    elapsed += step
                    if elapsed < 20:
                        evaluation = tracker.evaluate_reset(
                            side=Side.TOP,
                            progress_route_available=True,
                        )
                        self.assertFalse(evaluation.offense)
                evaluation = tracker.evaluate_reset(
                    side=Side.TOP,
                    progress_route_available=True,
                )
                self.assertTrue(evaluation.offense)
                self.assertEqual(
                    evaluation.consequence,
                    StallingConsequence.WARNING,
                )
                self.assertGreaterEqual(evaluation.clock_seconds, 20)


if __name__ == "__main__":
    unittest.main()
