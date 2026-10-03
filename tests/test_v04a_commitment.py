import unittest

from bjj_game.diagnostics.checker import (
    V02GateStatus,
    _v04_double_cost_probe,
    _v04_fixed_medium_standard_batch,
    measure_v04a_definition_of_done,
)
from bjj_game.domain.action import Commitment
from bjj_game.domain.model import BottomBehavior, Grade, Side, TopBehavior
from bjj_game.domain.stamina import StaminaBand
from bjj_game.domain.submission import SubmissionStage
from bjj_game.engine.match import MountMatch
from bjj_game.interfaces.batch import (
    BatchResponderMode,
    BatchResponseCommitmentMode,
    run_escape_first_batch,
)
from bjj_game.positions.mount.catalog import (
    BOTTOM_RESPONSE_FOREARM_FRAME,
    BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE,
    BOTTOM_RESPONSE_TURN_IN_RECOVERY,
    TOP_AMERICANA_ARM_ISOLATION,
    TOP_AMERICANA_SUBMISSION_FINISH,
    TOP_HIGH_MOUNT_CLIMB,
)


class V04ACommitmentSemanticsTests(unittest.TestCase):
    def _match(self, *, axis=1.50, v04=True):
        return MountMatch(
            starting_axis=axis,
            enable_v04_commitment_semantics=v04,
        )

    def test_feature_off_ignores_response_commitment_and_spends_no_response_stamina(self):
        baseline = self._match(v04=False)
        with_response_arg = self._match(v04=False)

        expected = baseline.attempt(
            action_id=TOP_HIGH_MOUNT_CLIMB,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
            commitment=Commitment.MEDIUM,
        )
        actual = with_response_arg.attempt(
            action_id=TOP_HIGH_MOUNT_CLIMB,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
            commitment=Commitment.MEDIUM,
            response_commitment=Commitment.HIGH,
        )

        self.assertEqual(actual.resolution, expected.resolution)
        self.assertIsNone(actual.response_requested_commitment)
        self.assertIsNone(actual.response_effective_commitment)
        self.assertIsNone(actual.response_stamina)
        self.assertEqual(with_response_arg.bottom.stamina.current, 100)

    def test_enabled_medium_medium_preserves_current_resolution_and_charges_responder(self):
        baseline = self._match(v04=False)
        enabled = self._match(v04=True)

        expected = baseline.attempt(
            action_id=TOP_HIGH_MOUNT_CLIMB,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
            commitment=Commitment.MEDIUM,
        )
        actual = enabled.attempt(
            action_id=TOP_HIGH_MOUNT_CLIMB,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
            commitment=Commitment.MEDIUM,
            response_commitment=Commitment.MEDIUM,
        )

        self.assertEqual(actual.resolution, expected.resolution)
        self.assertIs(actual.response_effective_commitment, Commitment.MEDIUM)
        self.assertEqual(actual.response_stamina.charged, 7)
        self.assertEqual(enabled.bottom.stamina.current, 93)

    def test_high_amplifies_success_and_failure_away_from_contested(self):
        success = self._match(v04=True).attempt(
            action_id=TOP_HIGH_MOUNT_CLIMB,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
            commitment=Commitment.HIGH,
            response_commitment=Commitment.HIGH,
        )
        failure = self._match(v04=True).attempt(
            action_id=TOP_HIGH_MOUNT_CLIMB,
            response_id=BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE,
            commitment=Commitment.HIGH,
            response_commitment=Commitment.HIGH,
        )

        self.assertIs(success.base_resolution.final_grade, Grade.SUCCESS)
        self.assertIs(success.resolution.final_grade, Grade.STRONG_SUCCESS)
        self.assertEqual(success.initiator_commitment_modifier, 1)
        self.assertIs(failure.base_resolution.final_grade, Grade.FAILURE)
        self.assertIs(failure.resolution.final_grade, Grade.STRONG_FAILURE)
        self.assertEqual(failure.initiator_commitment_modifier, -1)

    def test_low_compresses_extreme_outcomes(self):
        success = self._match(v04=True).attempt(
            action_id=TOP_AMERICANA_ARM_ISOLATION,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
            commitment=Commitment.LOW,
            response_commitment=Commitment.LOW,
        )
        failure = self._match(v04=True).attempt(
            action_id=TOP_AMERICANA_ARM_ISOLATION,
            response_id=BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE,
            commitment=Commitment.LOW,
            response_commitment=Commitment.LOW,
        )

        self.assertIs(success.base_resolution.final_grade, Grade.STRONG_SUCCESS)
        self.assertIs(success.resolution.final_grade, Grade.SUCCESS)
        self.assertEqual(success.initiator_commitment_modifier, -1)
        self.assertIs(failure.base_resolution.final_grade, Grade.STRONG_FAILURE)
        self.assertIs(failure.resolution.final_grade, Grade.FAILURE)
        self.assertEqual(failure.initiator_commitment_modifier, 1)

    def test_modifier_order_is_exhaustion_then_magnitude_then_undercommitment(self):
        match = self._match(v04=True)
        result = match.attempt(
            action_id=TOP_HIGH_MOUNT_CLIMB,
            response_id=BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE,
            commitment=Commitment.HIGH,
            response_commitment=Commitment.LOW,
        )

        # Failure -> HIGH Strong Failure -> undercommitment +1 -> Failure.
        # Applying mismatch before HIGH would incorrectly yield Contested.
        self.assertIs(result.base_resolution.final_grade, Grade.FAILURE)
        self.assertEqual(result.initiator_commitment_modifier, -1)
        self.assertEqual(result.response_undercommitment_modifier, 1)
        self.assertIs(result.resolution.final_grade, Grade.FAILURE)

    def test_modifier_order_handles_clamp_before_later_undercommitment(self):
        match = self._match(v04=True)
        match.top.stamina.set_current(20)
        result = match.attempt(
            action_id=TOP_AMERICANA_ARM_ISOLATION,
            response_id=BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE,
            commitment=Commitment.MEDIUM,
            response_commitment=Commitment.LOW,
        )

        # Base Strong Failure; exhausted initiator stays Strong Failure at the
        # clamp; MEDIUM is identity; under-committed LOW response then moves
        # one step back to ordinary Failure. A summed-modifier implementation
        # incorrectly stayed at Strong Failure here.
        self.assertIs(result.base_resolution.final_grade, Grade.STRONG_FAILURE)
        self.assertEqual(result.initiator_exhaustion_modifier, -1)
        self.assertEqual(result.responder_exhaustion_modifier, 0)
        self.assertEqual(result.initiator_commitment_modifier, 0)
        self.assertEqual(result.response_undercommitment_modifier, 1)
        self.assertIs(result.resolution.final_grade, Grade.FAILURE)

    def test_modifier_order_is_exhaustive_over_grade_and_commitment_states(self):
        commitments = (
            None,
            Commitment.LOW,
            Commitment.MEDIUM,
            Commitment.HIGH,
        )
        for base_grade in Grade:
            for exhaustion_modifier in (-1, 0, 1):
                exhausted = base_grade.shift(exhaustion_modifier)
                for initiator_commitment in commitments:
                    for responder_commitment in commitments:
                        magnitude_modifier = (
                            MountMatch._initiator_commitment_modifier(
                                initiator_commitment,
                                exhausted,
                            )
                        )
                        after_magnitude = exhausted.shift(
                            magnitude_modifier
                        )
                        response_modifier = (
                            MountMatch._response_undercommitment_modifier(
                                initiator_commitment=initiator_commitment,
                                responder_commitment=responder_commitment,
                            )
                        )
                        expected = after_magnitude.shift(response_modifier)
                        (
                            actual,
                            actual_magnitude,
                            actual_response,
                        ) = MountMatch._commitment_grade_transform(
                            grade_after_exhaustion=exhausted,
                            initiator_commitment=initiator_commitment,
                            responder_commitment=responder_commitment,
                        )
                        self.assertIs(actual, expected)
                        self.assertEqual(
                            actual_magnitude,
                            magnitude_modifier,
                        )
                        self.assertEqual(
                            actual_response,
                            response_modifier,
                        )

    def test_undercommitted_response_can_turn_contested_into_success(self):
        match = self._match(v04=True)
        result = match.attempt(
            action_id=TOP_HIGH_MOUNT_CLIMB,
            response_id=BOTTOM_RESPONSE_TURN_IN_RECOVERY,
            commitment=Commitment.MEDIUM,
            response_commitment=Commitment.LOW,
        )
        self.assertIs(result.base_resolution.final_grade, Grade.CONTESTED)
        self.assertEqual(result.response_undercommitment_modifier, 1)
        self.assertIs(result.resolution.final_grade, Grade.SUCCESS)

    def test_response_affordability_uses_effective_commitment(self):
        match = self._match(v04=True)
        match.bottom.stamina.set_current(5)
        result = match.attempt(
            action_id=TOP_HIGH_MOUNT_CLIMB,
            response_id=BOTTOM_RESPONSE_TURN_IN_RECOVERY,
            commitment=Commitment.HIGH,
            response_commitment=Commitment.HIGH,
        )

        self.assertIs(result.response_requested_commitment, Commitment.HIGH)
        self.assertIs(result.response_effective_commitment, Commitment.LOW)
        self.assertEqual(result.response_requested_cost, 12)
        self.assertEqual(result.response_effective_cost, 3)
        self.assertEqual(result.response_funding_gap, 9)
        self.assertEqual(result.response_stamina.charged, 3)
        self.assertEqual(result.response_undercommitment_modifier, 1)
        self.assertEqual(match.bottom.stamina.current, 2)

    def test_unfunded_response_gets_no_requested_commitment_credit(self):
        match = self._match(v04=True)
        match.bottom.stamina.set_current(2)
        result = match.attempt(
            action_id=TOP_HIGH_MOUNT_CLIMB,
            response_id=BOTTOM_RESPONSE_TURN_IN_RECOVERY,
            commitment=Commitment.HIGH,
            response_commitment=Commitment.HIGH,
        )

        self.assertIsNone(result.response_effective_commitment)
        self.assertEqual(result.response_effective_cost, 0)
        self.assertEqual(result.response_funding_gap, 12)
        self.assertEqual(result.response_stamina.charged, 0)
        self.assertEqual(result.response_undercommitment_modifier, 1)

    def test_current_exchange_uses_pre_cost_responder_stamina_band(self):
        reference = self._match(v04=True)
        expected = reference.attempt(
            action_id=TOP_HIGH_MOUNT_CLIMB,
            response_id=BOTTOM_RESPONSE_TURN_IN_RECOVERY,
            commitment=Commitment.MEDIUM,
            response_commitment=Commitment.MEDIUM,
        )

        match = self._match(v04=True)
        match.bottom.stamina.set_current(26)
        actual = match.attempt(
            action_id=TOP_HIGH_MOUNT_CLIMB,
            response_id=BOTTOM_RESPONSE_TURN_IN_RECOVERY,
            commitment=Commitment.MEDIUM,
            response_commitment=Commitment.MEDIUM,
        )

        self.assertIs(actual.responder_stamina_band_before_action, StaminaBand.TIRED)
        self.assertEqual(actual.responder_exhaustion_modifier, 0)
        self.assertEqual(actual.resolution, expected.resolution)
        self.assertIs(match.bottom.stamina.band, StaminaBand.EXHAUSTED)

    def test_low_ready_americana_can_still_create_real_threat(self):
        match = MountMatch(
            starting_axis=2.50,
            enable_v02_setup=True,
            enable_v03_submissions=True,
            enable_v04_commitment_semantics=True,
        )
        match.setup_state.advance(TOP_AMERICANA_ARM_ISOLATION)
        match.setup_state.advance(TOP_AMERICANA_ARM_ISOLATION)
        result = match.attempt(
            action_id=TOP_AMERICANA_ARM_ISOLATION,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
            commitment=Commitment.LOW,
            response_commitment=Commitment.LOW,
        )

        self.assertTrue(result.resolution.final_grade.successful)
        self.assertIs(match.submission_state.stage, SubmissionStage.THREAT)

    def test_low_active_submission_success_is_feint_capped(self):
        match = MountMatch(
            starting_axis=2.50,
            enable_v02_setup=True,
            enable_v03_submissions=True,
            enable_v04_commitment_semantics=True,
        )
        match.submission_state.stage = SubmissionStage.THREAT
        result = match.attempt(
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
            commitment=Commitment.LOW,
            response_commitment=Commitment.LOW,
        )

        self.assertTrue(result.resolution.final_grade.successful)
        self.assertIs(match.submission_state.stage, SubmissionStage.THREAT)
        self.assertEqual(len(match.history.submission_feint_cap_history), 1)

    def test_requested_low_remains_feint_capped_when_unfunded(self):
        match = MountMatch(
            starting_axis=2.50,
            enable_v02_setup=True,
            enable_v03_submissions=True,
            enable_v04_commitment_semantics=True,
        )
        match.submission_state.stage = SubmissionStage.THREAT
        match.top.stamina.set_current(2)
        match.bottom.stamina.set_current(2)
        result = match.attempt(
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
            commitment=Commitment.LOW,
            response_commitment=Commitment.LOW,
        )

        self.assertIsNone(result.attempt.effective_commitment)
        self.assertTrue(result.resolution.final_grade.successful)
        self.assertIs(match.submission_state.stage, SubmissionStage.THREAT)
        self.assertEqual(len(match.history.submission_feint_cap_history), 1)
        self.assertIn(
            "requested=LOW:effective=UNFUNDED",
            match.history.submission_feint_cap_history[0],
        )

    def test_requested_medium_downgraded_to_low_is_not_feint_capped(self):
        match = MountMatch(
            starting_axis=2.50,
            enable_v02_setup=True,
            enable_v03_submissions=True,
            enable_v04_commitment_semantics=True,
        )
        match.submission_state.stage = SubmissionStage.THREAT
        match.top.stamina.set_current(5)
        match.bottom.stamina.set_current(2)
        result = match.attempt(
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
            commitment=Commitment.MEDIUM,
            response_commitment=Commitment.MEDIUM,
        )

        self.assertIs(result.attempt.effective_commitment, Commitment.LOW)
        self.assertTrue(result.resolution.final_grade.successful)
        self.assertIs(match.submission_state.stage, SubmissionStage.CONTROL)
        self.assertEqual(len(match.history.submission_feint_cap_history), 0)

    def test_requested_high_downgraded_to_unfunded_is_not_feint_capped(self):
        match = MountMatch(
            starting_axis=2.50,
            enable_v02_setup=True,
            enable_v03_submissions=True,
            enable_v04_commitment_semantics=True,
        )
        match.submission_state.stage = SubmissionStage.THREAT
        match.top.stamina.set_current(2)
        match.bottom.stamina.set_current(2)
        result = match.attempt(
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
            commitment=Commitment.HIGH,
            response_commitment=Commitment.HIGH,
        )

        self.assertIsNone(result.attempt.effective_commitment)
        self.assertTrue(result.resolution.final_grade.successful)
        self.assertIs(match.submission_state.stage, SubmissionStage.CONTROL)
        self.assertEqual(len(match.history.submission_feint_cap_history), 0)

    def test_medium_active_submission_can_advance(self):
        match = MountMatch(
            starting_axis=2.50,
            enable_v02_setup=True,
            enable_v03_submissions=True,
            enable_v04_commitment_semantics=True,
        )
        match.submission_state.stage = SubmissionStage.THREAT
        match.attempt(
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
            commitment=Commitment.MEDIUM,
            response_commitment=Commitment.MEDIUM,
        )
        self.assertIs(match.submission_state.stage, SubmissionStage.CONTROL)

    def test_feint_resets_defender_stalling_clock_but_not_attacker(self):
        match = MountMatch(
            starting_axis=2.50,
            enable_v02_setup=True,
            enable_v03_submissions=True,
            enable_v03b_stalling=True,
            enable_v04_commitment_semantics=True,
        )
        match.submission_state.stage = SubmissionStage.THREAT
        match.stalling_tracker.advance(20)
        match.attempt(
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
            commitment=Commitment.LOW,
            response_commitment=Commitment.LOW,
        )

        self.assertEqual(match.advancement_clock(Side.TOP), 20)
        self.assertEqual(match.advancement_clock(Side.BOTTOM), 0)

    def test_funding_downgrade_does_not_inherit_feint_stalling_classification(self):
        match = MountMatch(
            starting_axis=2.50,
            enable_v02_setup=True,
            enable_v03_submissions=True,
            enable_v03b_stalling=True,
            enable_v04_commitment_semantics=True,
        )
        match.submission_state.stage = SubmissionStage.THREAT
        match.top.stamina.set_current(5)
        match.bottom.stamina.set_current(2)
        match.stalling_tracker.advance(20)
        result = match.attempt(
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
            commitment=Commitment.MEDIUM,
            response_commitment=Commitment.MEDIUM,
        )

        self.assertIs(result.attempt.effective_commitment, Commitment.LOW)
        self.assertEqual(match.advancement_clock(Side.TOP), 0)
        self.assertEqual(match.advancement_clock(Side.BOTTOM), 0)

    def test_random_response_commitment_batch_is_replayable(self):
        kwargs = dict(
            matches=10,
            base_seed=42,
            top_behavior=TopBehavior.PRESSURE,
            bottom_behavior=BottomBehavior.ESCAPE,
            commitment=Commitment.MEDIUM,
            initial_clock=300,
            starting_axis=1.50,
            interval_seconds=5,
            top_stamina=100,
            bottom_stamina=100,
            bottom_responder_mode=BatchResponderMode.RANDOM,
            response_commitment_mode=BatchResponseCommitmentMode.RANDOM,
            enable_v02_setup=True,
            enable_v03_submissions=True,
            enable_v04_commitment_semantics=True,
        )
        first = run_escape_first_batch(**kwargs)
        second = run_escape_first_batch(**kwargs)
        self.assertEqual(first, second)

    def test_fixed_medium_batch_has_no_intent_or_funding_downgrade_caps(self):
        summary = _v04_fixed_medium_standard_batch()
        self.assertEqual(summary.requested_low_feint_cap_count, 0)
        self.assertGreater(summary.funding_downgrade_success_count, 0)
        self.assertEqual(summary.funding_downgrade_feint_cap_count, 0)
        self.assertEqual(summary.submission_feint_cap_count, 0)

    def test_response_commitment_and_hold_cost_are_separate_spends(self):
        response_cost, hold_cost, bottom_after = _v04_double_cost_probe()
        self.assertEqual(response_cost, 7)
        self.assertEqual(hold_cost, 3)
        self.assertEqual(bottom_after, 90)

    def test_runtime_response_commitment_capability_tracks_feature_flag(self):
        self.assertFalse(
            MountMatch(enable_v04_commitment_semantics=False)
            .response_commitment_enabled
        )
        self.assertTrue(
            MountMatch(enable_v04_commitment_semantics=True)
            .response_commitment_enabled
        )


class V04ADefinitionOfDoneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gates = {
            gate.letter: gate
            for gate in measure_v04a_definition_of_done()
        }

    def test_all_nine_gates_pass_with_frozen_measurements(self):
        self.assertEqual(tuple(self.gates), tuple("ABCDEFGHI"))
        self.assertTrue(
            all(gate.status is V02GateStatus.PASS for gate in self.gates.values())
        )
        self.assertIn("cases=1152", self.gates["A"].metric)
        self.assertIn("enabled_MEDIUM_mismatches=0", self.gates["A"].metric)
        self.assertIn("higher-commitment advantage states=172", self.gates["B"].metric)
        self.assertIn("states=864", self.gates["C"].metric)
        self.assertIn("dominating_pairs=none", self.gates["C"].metric)
        self.assertIn("cases=360", self.gates["D"].metric)
        self.assertIn("breaks=0", self.gates["D"].metric)
        self.assertIn("active-Americana cases=72", self.gates["D"].metric)
        self.assertIn("violations=0", self.gates["E"].metric)
        self.assertIn("downgrade advances=2/2", self.gates["E"].metric)
        self.assertIn("fixed-medium requested-LOW caps=0", self.gates["E"].metric)
        self.assertIn("fixed-medium downgrade caps=0", self.gates["E"].metric)
        self.assertIn("comparisons=864", self.gates["F"].metric)
        self.assertIn("regressions=0", self.gates["F"].metric)
        self.assertIn("strict improvements=646", self.gates["F"].metric)
        self.assertIn("v0.3a Gate B=OPEN", self.gates["G"].metric)
        self.assertIn("Top clock 20->20", self.gates["H"].metric)
        self.assertIn("Bottom clock 20->0", self.gates["H"].metric)
        self.assertIn("downgraded MEDIUM effective-LOW=True", self.gates["H"].metric)
        self.assertIn("Top clock 20->0", self.gates["H"].metric)
        self.assertIn("5-stamina HIGH request: cost=3,gap=9,mismatch=1", self.gates["I"].metric)
        self.assertIn("2-stamina HIGH request: cost=0,gap=12", self.gates["I"].metric)


if __name__ == "__main__":
    unittest.main()
