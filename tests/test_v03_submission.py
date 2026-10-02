import unittest

from bjj_game.domain.action import Commitment
from bjj_game.domain.model import Band, BottomBehavior, Grade, Side
from bjj_game.domain.submission import SubmissionStage
from bjj_game.engine.match import MountMatch
from bjj_game.positions.mount.catalog import (
    BOTTOM_RESPONSE_FOREARM_FRAME,
    BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE,
    BOTTOM_RESPONSE_TURN_IN_RECOVERY,
    TOP_AMERICANA_ARM_ISOLATION,
    TOP_AMERICANA_SUBMISSION_FINISH,
    actions_for,
    modern_actions_for,
)


class V03AmericanaSubmissionTests(unittest.TestCase):
    def _ready_americana(self, *, axis: float = 2.50) -> MountMatch:
        match = MountMatch(
            starting_axis=axis,
            enable_v02_setup=True,
            enable_v03_submissions=True,
        )
        match.setup_state.advance(TOP_AMERICANA_ARM_ISOLATION)
        match.setup_state.advance(TOP_AMERICANA_ARM_ISOLATION)
        match.initiator = Side.TOP
        return match

    def _active_stage(
        self,
        *,
        axis: float = 3.50,
        stage: SubmissionStage = SubmissionStage.THREAT,
    ) -> MountMatch:
        match = MountMatch(
            starting_axis=axis,
            enable_v02_setup=True,
            enable_v03_submissions=True,
        )
        match.submission_state.stage = stage
        match.initiator = Side.TOP
        return match

    def test_v03_requires_v02_setup_ready(self):
        with self.assertRaises(ValueError):
            MountMatch(enable_v03_submissions=True)

    def test_modern_finish_action_does_not_enter_frozen_action_catalog(self):
        self.assertNotIn(
            TOP_AMERICANA_SUBMISSION_FINISH,
            {action.id for action in actions_for(Side.TOP)},
        )
        self.assertIn(
            TOP_AMERICANA_SUBMISSION_FINISH,
            {action.id for action in modern_actions_for(Side.TOP)},
        )

    def test_ready_americana_success_from_strong_starts_threat(self):
        match = self._ready_americana(axis=2.50)
        result = match.attempt(
            action_id=TOP_AMERICANA_ARM_ISOLATION,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
            commitment=Commitment.LOW,
        )
        self.assertTrue(result.resolution.final_grade.successful)
        self.assertIs(match.submission_state.stage, SubmissionStage.THREAT)
        self.assertIn(
            TOP_AMERICANA_SUBMISSION_FINISH,
            match.legal_action_ids(Side.TOP),
        )

    def test_ready_americana_success_from_stable_does_not_start_track(self):
        match = self._ready_americana(axis=1.50)
        result = match.attempt(
            action_id=TOP_AMERICANA_ARM_ISOLATION,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
            commitment=Commitment.LOW,
        )
        self.assertTrue(result.resolution.final_grade.successful)
        self.assertIsNone(match.submission_state.stage)

    def test_submission_stage_uses_existing_bottom_responses(self):
        match = self._active_stage()
        self.assertEqual(
            set(match.legal_response_ids(TOP_AMERICANA_SUBMISSION_FINISH)),
            {
                BOTTOM_RESPONSE_FOREARM_FRAME,
                BOTTOM_RESPONSE_TURN_IN_RECOVERY,
                BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE,
            },
        )

    def test_successful_stage_advances_without_free_axis_gain(self):
        match = self._active_stage(axis=3.50)
        before = match.axis
        result = match.attempt(
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
            commitment=Commitment.LOW,
        )
        self.assertTrue(result.resolution.final_grade.successful)
        self.assertEqual(match.axis, before)
        self.assertIs(match.submission_state.stage, SubmissionStage.CONTROL)

    def test_defended_stage_moves_axis_one_step_toward_bottom(self):
        match = self._active_stage(axis=4.00)
        result = match.attempt(
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            response_id=BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE,
            commitment=Commitment.LOW,
        )
        self.assertFalse(result.resolution.final_grade.successful)
        self.assertEqual(result.resolution.proposed_axis, 3.00)
        self.assertEqual(match.axis, 3.00)
        self.assertIsNone(match.submission_state.stage)
        self.assertNotIn(
            TOP_AMERICANA_SUBMISSION_FINISH,
            match.legal_action_ids(Side.TOP),
        )

    def test_defended_control_breaks_submission_track(self):
        match = self._active_stage(
            axis=4.00,
            stage=SubmissionStage.CONTROL,
        )
        match.attempt(
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            response_id=BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE,
            commitment=Commitment.LOW,
        )
        self.assertEqual(match.axis, 3.00)
        self.assertIsNone(match.submission_state.stage)

    def test_defended_finish_breaks_submission_track(self):
        match = self._active_stage(
            axis=4.00,
            stage=SubmissionStage.FINISH,
        )
        match.attempt(
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            response_id=BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE,
            commitment=Commitment.LOW,
        )
        self.assertEqual(match.axis, 3.00)
        self.assertIsNone(match.submission_state.stage)

    def test_success_from_finish_taps_and_ends_match(self):
        match = self._active_stage(stage=SubmissionStage.FINISH)
        match.attempt(
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
            commitment=Commitment.LOW,
        )
        self.assertTrue(match.submission_tapped)
        self.assertTrue(match.ended)
        self.assertEqual(match.exit_reason, "TAP — Americana")
        self.assertEqual(match.history.submission_tap_count, 1)

    def test_exhausted_top_can_turn_fresh_progress_into_defense(self):
        fresh = self._active_stage(axis=3.50)
        fresh.set_behaviors(bottom=BottomBehavior.PROTECT)
        fresh_result = fresh.attempt(
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
            commitment=Commitment.LOW,
        )
        self.assertIs(fresh_result.resolution.final_grade, Grade.SUCCESS)
        self.assertIs(fresh.submission_state.stage, SubmissionStage.CONTROL)

        exhausted = self._active_stage(axis=3.50)
        exhausted.set_behaviors(bottom=BottomBehavior.PROTECT)
        exhausted.top.stamina.set_current(25)
        exhausted_result = exhausted.attempt(
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
            commitment=Commitment.LOW,
        )
        self.assertIs(exhausted_result.resolution.final_grade, Grade.CONTESTED)
        self.assertIsNone(exhausted.submission_state.stage)
        self.assertEqual(exhausted.axis, 2.50)

    def test_exhausted_defender_can_turn_fresh_stalemate_into_progress(self):
        fresh = self._active_stage(axis=3.50)
        fresh_result = fresh.attempt(
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            response_id=BOTTOM_RESPONSE_TURN_IN_RECOVERY,
            commitment=Commitment.LOW,
        )
        self.assertIs(fresh_result.resolution.final_grade, Grade.CONTESTED)
        self.assertIsNone(fresh.submission_state.stage)

        exhausted = self._active_stage(axis=3.50)
        exhausted.bottom.stamina.set_current(25)
        exhausted_result = exhausted.attempt(
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            response_id=BOTTOM_RESPONSE_TURN_IN_RECOVERY,
            commitment=Commitment.LOW,
        )
        self.assertIs(exhausted_result.resolution.final_grade, Grade.SUCCESS)
        self.assertIs(exhausted.submission_state.stage, SubmissionStage.CONTROL)

    def test_both_exhausted_cancel_to_fresh_submission_result(self):
        fresh = self._active_stage(axis=3.50)
        fresh_result = fresh.attempt(
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            response_id=BOTTOM_RESPONSE_TURN_IN_RECOVERY,
            commitment=Commitment.LOW,
        )

        both = self._active_stage(axis=3.50)
        both.top.stamina.set_current(25)
        both.bottom.stamina.set_current(25)
        both_result = both.attempt(
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            response_id=BOTTOM_RESPONSE_TURN_IN_RECOVERY,
            commitment=Commitment.LOW,
        )

        self.assertEqual(
            both_result.resolution.final_grade,
            fresh_result.resolution.final_grade,
        )
        self.assertEqual(
            both.submission_state.stage,
            fresh.submission_state.stage,
        )
        self.assertEqual(both.axis, fresh.axis)


if __name__ == "__main__":
    unittest.main()
