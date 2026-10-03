import unittest

from bjj_game.diagnostics.checker import (
    V02GateStatus,
    measure_v04b_definition_of_done,
)
from bjj_game.domain.action import Commitment
from bjj_game.domain.recognition import (
    CommitmentRecognitionRead,
    DEFAULT_COMMITMENT_RECOGNITION_POLICY,
)
from bjj_game.engine.match import MountMatch
from bjj_game.interfaces.batch import (
    BatchResponderMode,
    BatchResponseCommitmentMode,
    _informed_bottom_response_id,
    _response_commitment_for_exchange,
    run_escape_first_batch,
)
from bjj_game.domain.model import BottomBehavior, TopBehavior
from bjj_game.positions.mount.catalog import (
    BOTTOM_RESPONSE_FOREARM_FRAME,
    TOP_HIGH_MOUNT_CLIMB,
)


class V04BRecognitionPolicyTests(unittest.TestCase):
    def test_requested_intent_mapping_is_adjacent_and_clamped(self):
        policy = DEFAULT_COMMITMENT_RECOGNITION_POLICY
        expected = {
            Commitment.LOW: {
                1: Commitment.LOW,
                2: Commitment.LOW,
                3: Commitment.LOW,
                4: Commitment.LOW,
                5: Commitment.LOW,
                6: Commitment.MEDIUM,
            },
            Commitment.MEDIUM: {
                1: Commitment.LOW,
                2: Commitment.MEDIUM,
                3: Commitment.MEDIUM,
                4: Commitment.MEDIUM,
                5: Commitment.MEDIUM,
                6: Commitment.HIGH,
            },
            Commitment.HIGH: {
                1: Commitment.MEDIUM,
                2: Commitment.HIGH,
                3: Commitment.HIGH,
                4: Commitment.HIGH,
                5: Commitment.HIGH,
                6: Commitment.HIGH,
            },
        }
        for truth, by_roll in expected.items():
            for roll, perceived in by_roll.items():
                read = policy.read(
                    requested=truth,
                    effective=Commitment.MEDIUM,
                    intent_roll=roll,
                    capability_roll=3,
                )
                self.assertIs(read.perceived_requested, perceived)

    def test_effective_capability_mapping_includes_unfunded(self):
        policy = DEFAULT_COMMITMENT_RECOGNITION_POLICY
        levels = (None, Commitment.LOW, Commitment.MEDIUM, Commitment.HIGH)
        for index, truth in enumerate(levels):
            lower = levels[max(0, index - 1)]
            higher = levels[min(len(levels) - 1, index + 1)]
            self.assertIs(
                policy.read(
                    requested=Commitment.MEDIUM,
                    effective=truth,
                    intent_roll=3,
                    capability_roll=1,
                ).perceived_effective,
                lower,
            )
            for exact_roll in (2, 3, 4, 5):
                self.assertIs(
                    policy.read(
                        requested=Commitment.MEDIUM,
                        effective=truth,
                        intent_roll=3,
                        capability_roll=exact_roll,
                    ).perceived_effective,
                    truth,
                )
            self.assertIs(
                policy.read(
                    requested=Commitment.MEDIUM,
                    effective=truth,
                    intent_roll=3,
                    capability_roll=6,
                ).perceived_effective,
                higher,
            )

    def test_signal_rolls_are_independent(self):
        policy = DEFAULT_COMMITMENT_RECOGNITION_POLICY
        baseline = policy.read(
            requested=Commitment.MEDIUM,
            effective=Commitment.LOW,
            intent_roll=3,
            capability_roll=3,
        )
        intent_changed = policy.read(
            requested=Commitment.MEDIUM,
            effective=Commitment.LOW,
            intent_roll=1,
            capability_roll=3,
        )
        capability_changed = policy.read(
            requested=Commitment.MEDIUM,
            effective=Commitment.LOW,
            intent_roll=3,
            capability_roll=6,
        )

        self.assertIs(
            intent_changed.perceived_effective,
            baseline.perceived_effective,
        )
        self.assertIsNot(
            intent_changed.perceived_requested,
            baseline.perceived_requested,
        )
        self.assertIs(
            capability_changed.perceived_requested,
            baseline.perceived_requested,
        )
        self.assertIsNot(
            capability_changed.perceived_effective,
            baseline.perceived_effective,
        )

    def test_v04b_requires_v04a_and_exposes_real_capability(self):
        with self.assertRaises(ValueError):
            MountMatch(enable_v04b_recognition=True)

        disabled = MountMatch(enable_v04_commitment_semantics=True)
        enabled = MountMatch(
            enable_v04_commitment_semantics=True,
            enable_v04b_recognition=True,
        )
        self.assertFalse(disabled.recognition_enabled)
        self.assertTrue(enabled.recognition_enabled)

    def test_recognition_reads_true_prefunded_effective_commitment(self):
        match = MountMatch(
            enable_v04_commitment_semantics=True,
            enable_v04b_recognition=True,
        )
        match.top.stamina.set_current(5)
        read = match.recognize_commitment(
            requested=Commitment.HIGH,
            intent_roll=3,
            capability_roll=3,
        )
        self.assertIs(read.true_requested, Commitment.HIGH)
        self.assertIs(read.true_effective, Commitment.LOW)
        self.assertIs(read.perceived_requested, Commitment.HIGH)
        self.assertIs(read.perceived_effective, Commitment.LOW)

    def test_recognition_response_policy_uses_perception_not_true_request(self):
        match = MountMatch(
            enable_v04_commitment_semantics=True,
            enable_v04b_recognition=True,
        )
        read = CommitmentRecognitionRead(
            true_requested=Commitment.HIGH,
            perceived_requested=Commitment.MEDIUM,
            true_effective=Commitment.HIGH,
            perceived_effective=Commitment.MEDIUM,
            intent_roll=1,
            capability_roll=1,
        )

        high_truth = _response_commitment_for_exchange(
            match,
            initiator_commitment=Commitment.HIGH,
            mode=BatchResponseCommitmentMode.RECOGNITION,
            rng=__import__("random").Random(1),
            recognition_read=read,
        )
        low_truth = _response_commitment_for_exchange(
            match,
            initiator_commitment=Commitment.LOW,
            mode=BatchResponseCommitmentMode.RECOGNITION,
            rng=__import__("random").Random(1),
            recognition_read=read,
        )
        self.assertIs(high_truth, Commitment.MEDIUM)
        self.assertIs(low_truth, Commitment.MEDIUM)

    def test_perceived_low_intent_conserves_response_commitment(self):
        match = MountMatch(
            enable_v04_commitment_semantics=True,
            enable_v04b_recognition=True,
        )
        read = CommitmentRecognitionRead(
            true_requested=Commitment.MEDIUM,
            perceived_requested=Commitment.LOW,
            true_effective=Commitment.MEDIUM,
            perceived_effective=Commitment.HIGH,
            intent_roll=1,
            capability_roll=6,
        )
        selected = _response_commitment_for_exchange(
            match,
            initiator_commitment=Commitment.MEDIUM,
            mode=BatchResponseCommitmentMode.RECOGNITION,
            rng=__import__("random").Random(1),
            recognition_read=read,
        )
        self.assertIs(selected, Commitment.LOW)

    def test_informed_response_choice_ignores_true_commitment_when_recognition_is_used(self):
        match = MountMatch(
            enable_v04_commitment_semantics=True,
            enable_v04b_recognition=True,
        )
        first = _informed_bottom_response_id(
            match,
            action_id=TOP_HIGH_MOUNT_CLIMB,
            commitment=Commitment.LOW,
            response_commitment=Commitment.MEDIUM,
            use_recognition=True,
            perceived_effective_commitment=Commitment.MEDIUM,
        )
        second = _informed_bottom_response_id(
            match,
            action_id=TOP_HIGH_MOUNT_CLIMB,
            commitment=Commitment.HIGH,
            response_commitment=Commitment.MEDIUM,
            use_recognition=True,
            perceived_effective_commitment=Commitment.MEDIUM,
        )
        self.assertEqual(first, second)

    def test_true_resolution_is_independent_of_recognition_read(self):
        def resolve(intent_roll: int, capability_roll: int):
            match = MountMatch(
                starting_axis=1.50,
                enable_v04_commitment_semantics=True,
                enable_v04b_recognition=True,
            )
            read = match.recognize_commitment(
                requested=Commitment.MEDIUM,
                intent_roll=intent_roll,
                capability_roll=capability_roll,
            )
            result = match.attempt(
                action_id=TOP_HIGH_MOUNT_CLIMB,
                response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
                commitment=Commitment.MEDIUM,
                response_commitment=Commitment.MEDIUM,
                recognition_read=read,
            )
            return (
                result.resolution,
                result.effective_cost,
                result.response_effective_cost,
                match.axis,
            )

        self.assertEqual(resolve(1, 1), resolve(6, 6))

    def test_recognition_batch_is_replayable_and_observable(self):
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
            bottom_responder_mode=BatchResponderMode.INFORMED,
            response_commitment_mode=BatchResponseCommitmentMode.RECOGNITION,
            enable_v02_setup=True,
            enable_v03_submissions=True,
            enable_v04_commitment_semantics=True,
            enable_v04b_recognition=True,
        )
        first = run_escape_first_batch(**kwargs)
        second = run_escape_first_batch(**kwargs)
        self.assertEqual(first, second)
        self.assertGreater(
            sum(first.recognition_intent_direction_counts.values()),
            0,
        )
        self.assertGreater(
            sum(first.recognition_capability_direction_counts.values()),
            0,
        )
        self.assertGreater(
            sum(first.response_requested_commitment_counts.values()),
            0,
        )



class V04BDefinitionOfDoneMeasurementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gates = {
            gate.letter: gate
            for gate in measure_v04b_definition_of_done()
        }

    def test_frozen_gate_surface_exists(self):
        self.assertEqual(tuple(self.gates), tuple("ABCDEFGH"))

    def test_non_outcome_gates_pass_before_gate_f_is_pinned(self):
        for letter in "ABCDEGH":
            self.assertIs(
                self.gates[letter].status,
                V02GateStatus.PASS,
                self.gates[letter].render(),
            )

    def test_gate_f_reports_the_unchanged_gate_b_measurement(self):
        self.assertIn("informed Tap=", self.gates["F"].metric)
        self.assertIn("v0.3a Gate B=", self.gates["F"].metric)


if __name__ == "__main__":
    unittest.main()
