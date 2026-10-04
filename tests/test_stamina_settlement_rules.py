import unittest

from bjj_game.domain.action import Commitment
from bjj_game.domain.model import Grade, Side
from bjj_game.domain.submission import SubmissionStage
from bjj_game.engine.match import MountMatch
from bjj_game.positions.mount.catalog import (
    BOTTOM_RESPONSE_FOREARM_FRAME,
    BOTTOM_RESPONSE_TURN_IN_RECOVERY,
    TOP_AMERICANA_SUBMISSION_FINISH,
    TOP_HIGH_MOUNT_CLIMB,
)


class StaminaSettlementRuleTests(unittest.TestCase):
    def _match(
        self,
        *,
        top_stamina=100,
        bottom_stamina=100,
        settlement=True,
    ):
        match = MountMatch(
            starting_axis=4.0,
            enable_v02_setup=True,
            enable_v03_submissions=True,
            enable_v04_commitment_semantics=True,
            enable_stamina_settlement_rules=settlement,
        )
        match.top.stamina.set_current(top_stamina)
        match.bottom.stamina.set_current(bottom_stamina)
        match.initiator = Side.TOP
        return match

    def _active_hold_match(
        self,
        *,
        top_stamina=100,
        bottom_stamina=100,
        settlement=True,
    ):
        match = self._match(
            top_stamina=top_stamina,
            bottom_stamina=bottom_stamina,
            settlement=settlement,
        )
        match.submission_state.stage = SubmissionStage.THREAT
        return match

    def test_settlement_rules_require_v04a_commitment_semantics(self):
        with self.assertRaises(ValueError):
            MountMatch(enable_stamina_settlement_rules=True)

    def test_unfunded_initiator_waives_response_cost_at_zero_one_two(self):
        cases = (
            (0, Commitment.MEDIUM, Commitment.LOW),
            (1, Commitment.MEDIUM, Commitment.MEDIUM),
            (2, Commitment.HIGH, Commitment.HIGH),
        )
        for top_stamina, attack_request, response_request in cases:
            with self.subTest(
                top_stamina=top_stamina,
                attack_request=attack_request,
                response_request=response_request,
            ):
                match = self._match(
                    top_stamina=top_stamina,
                    bottom_stamina=100,
                )
                before = match.bottom.stamina.current
                result = match.attempt(
                    action_id=TOP_HIGH_MOUNT_CLIMB,
                    response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
                    commitment=attack_request,
                    response_commitment=response_request,
                )
                self.assertIsNone(result.attempt.effective_commitment)
                self.assertEqual(result.response_stamina.charged, 0)
                self.assertEqual(
                    result.response_stamina_waived,
                    result.response_effective_cost,
                )
                self.assertEqual(match.bottom.stamina.current, before)

    def test_three_stamina_low_funded_boundary_does_not_trigger_rule_one(self):
        match = self._active_hold_match(top_stamina=3, bottom_stamina=20)
        result = match.attempt(
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            response_id=BOTTOM_RESPONSE_TURN_IN_RECOVERY,
            commitment=Commitment.LOW,
            response_commitment=Commitment.HIGH,
        )
        self.assertIs(result.attempt.effective_commitment, Commitment.LOW)
        self.assertEqual(result.response_stamina_waived, 0)
        self.assertEqual(result.response_stamina.charged, 12)
        self.assertEqual(result.submission_hold_nominal_cost, 3)
        self.assertEqual(result.submission_hold_covered_by_response, 3)
        self.assertEqual(result.submission_hold_stamina.requested, 0)
        self.assertEqual(result.submission_hold_stamina.charged, 0)

    def test_funded_response_covers_entire_three_point_hold(self):
        for response, expected_cost in (
            (Commitment.LOW, 3),
            (Commitment.MEDIUM, 7),
            (Commitment.HIGH, 12),
        ):
            with self.subTest(response=response):
                match = self._active_hold_match()
                result = match.attempt(
                    action_id=TOP_AMERICANA_SUBMISSION_FINISH,
                    response_id=BOTTOM_RESPONSE_TURN_IN_RECOVERY,
                    commitment=Commitment.LOW,
                    response_commitment=response,
                )
                self.assertIs(result.resolution.final_grade, Grade.CONTESTED)
                self.assertEqual(result.response_stamina.charged, expected_cost)
                self.assertEqual(result.submission_hold_nominal_cost, 3)
                self.assertEqual(result.submission_hold_covered_by_response, 3)
                self.assertEqual(result.submission_hold_stamina.requested, 0)
                self.assertEqual(result.submission_hold_stamina.charged, 0)
                self.assertEqual(
                    100 - match.bottom.stamina.current,
                    expected_cost,
                )

    def test_unfunded_responder_can_pay_partial_supplemental_hold(self):
        match = self._active_hold_match(top_stamina=20, bottom_stamina=2)
        result = match.attempt(
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            response_id=BOTTOM_RESPONSE_TURN_IN_RECOVERY,
            commitment=Commitment.LOW,
            response_commitment=Commitment.HIGH,
        )
        self.assertIs(result.resolution.final_grade, Grade.CONTESTED)
        self.assertIsNone(result.response_effective_commitment)
        self.assertEqual(result.response_stamina.charged, 0)
        self.assertEqual(result.submission_hold_covered_by_response, 0)
        self.assertEqual(result.submission_hold_stamina.requested, 3)
        self.assertEqual(result.submission_hold_stamina.charged, 2)
        self.assertEqual(result.submission_hold_stamina.shortfall, 1)
        self.assertEqual(match.bottom.stamina.current, 0)

    def test_unfunded_initiator_waives_response_and_hold(self):
        match = self._active_hold_match(top_stamina=0, bottom_stamina=20)
        before = match.bottom.stamina.current
        result = match.attempt(
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            response_id=BOTTOM_RESPONSE_TURN_IN_RECOVERY,
            commitment=Commitment.LOW,
            response_commitment=Commitment.HIGH,
        )
        self.assertIs(result.resolution.final_grade, Grade.CONTESTED)
        self.assertIsNone(result.attempt.effective_commitment)
        self.assertEqual(result.response_stamina.charged, 0)
        self.assertEqual(result.response_stamina_waived, 12)
        self.assertEqual(result.submission_hold_nominal_cost, 3)
        self.assertEqual(result.submission_hold_covered_by_response, 0)
        self.assertEqual(result.submission_hold_stamina.requested, 0)
        self.assertEqual(result.submission_hold_stamina.charged, 0)
        self.assertEqual(match.bottom.stamina.current, before)

    def test_settlement_changes_costs_not_immediate_resolution(self):
        legacy = self._active_hold_match(
            top_stamina=0,
            bottom_stamina=20,
            settlement=False,
        )
        changed = self._active_hold_match(
            top_stamina=0,
            bottom_stamina=20,
            settlement=True,
        )

        expected = legacy.attempt(
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            response_id=BOTTOM_RESPONSE_TURN_IN_RECOVERY,
            commitment=Commitment.LOW,
            response_commitment=Commitment.HIGH,
        )
        actual = changed.attempt(
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            response_id=BOTTOM_RESPONSE_TURN_IN_RECOVERY,
            commitment=Commitment.LOW,
            response_commitment=Commitment.HIGH,
        )

        self.assertEqual(actual.base_resolution, expected.base_resolution)
        self.assertEqual(actual.resolution, expected.resolution)
        self.assertEqual(changed.axis, legacy.axis)
        self.assertEqual(changed.submission_state.stage, legacy.submission_state.stage)
        self.assertEqual(changed.submission_tapped, legacy.submission_tapped)
        self.assertNotEqual(
            changed.bottom.stamina.current,
            legacy.bottom.stamina.current,
        )

    def test_unfunded_equality_is_unchanged(self):
        self.assertEqual(
            MountMatch._response_undercommitment_modifier(
                initiator_commitment=None,
                responder_commitment=None,
            ),
            0,
        )


if __name__ == "__main__":
    unittest.main()
