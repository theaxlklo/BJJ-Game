import unittest

from bjj_game.diagnostics.checker import (
    V02GateStatus,
    _v04b_informed_always_high_batch,
    _v04b_informed_hedge_one_batch,
    _v04b_informed_standard_batch,
    measure_v04b_definition_of_done,
    render_v04b_defender_policy_hedge_observation,
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

    def test_hedge_one_raises_trust_choice_exactly_one_selectable_level(self):
        match = MountMatch(
            enable_v04_commitment_semantics=True,
            enable_v04b_recognition=True,
        )
        cases = (
            (Commitment.LOW, None, Commitment.MEDIUM),
            (Commitment.MEDIUM, Commitment.LOW, Commitment.MEDIUM),
            (Commitment.MEDIUM, Commitment.MEDIUM, Commitment.HIGH),
            (Commitment.HIGH, Commitment.HIGH, Commitment.HIGH),
        )
        for perceived_requested, perceived_effective, expected in cases:
            read = CommitmentRecognitionRead(
                true_requested=Commitment.MEDIUM,
                perceived_requested=perceived_requested,
                true_effective=Commitment.MEDIUM,
                perceived_effective=perceived_effective,
                intent_roll=3,
                capability_roll=3,
            )
            selected = _response_commitment_for_exchange(
                match,
                initiator_commitment=Commitment.MEDIUM,
                mode=BatchResponseCommitmentMode.RECOGNITION_HEDGE_ONE,
                rng=__import__("random").Random(1),
                recognition_read=read,
            )
            self.assertIs(selected, expected)

    def test_always_high_policy_ignores_read_for_commitment_only(self):
        match = MountMatch(
            enable_v04_commitment_semantics=True,
            enable_v04b_recognition=True,
        )
        read = CommitmentRecognitionRead(
            true_requested=Commitment.MEDIUM,
            perceived_requested=Commitment.LOW,
            true_effective=Commitment.MEDIUM,
            perceived_effective=None,
            intent_roll=1,
            capability_roll=1,
        )
        selected = _response_commitment_for_exchange(
            match,
            initiator_commitment=Commitment.MEDIUM,
            mode=BatchResponseCommitmentMode.RECOGNITION_ALWAYS_HIGH,
            rng=__import__("random").Random(1),
            recognition_read=read,
        )
        self.assertIs(selected, Commitment.HIGH)

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



class V04BDefenderPolicyObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.trust = _v04b_informed_standard_batch()
        cls.hedge = _v04b_informed_hedge_one_batch()
        cls.always_high = _v04b_informed_always_high_batch()

    @staticmethod
    def _taps(summary):
        return summary.outcome_counts.get("TAP — Americana", 0)

    @staticmethod
    def _escapes(summary):
        from bjj_game.domain.model import ExitDestination

        return sum(
            summary.outcome_counts.get(destination.value, 0)
            for destination in ExitDestination
        )

    def test_three_named_policies_reproduce_review_measurements(self):
        self.assertEqual(self._taps(self.trust), 6)
        self.assertEqual(self._escapes(self.trust), 11)
        self.assertEqual(
            self.trust.total_response_commitment_stamina_charged,
            7352,
        )
        self.assertEqual(self.trust.top_final_stamina_median, 0)
        self.assertEqual(self.trust.bottom_final_stamina_median, 0)

        self.assertEqual(self._taps(self.hedge), 0)
        self.assertEqual(self._escapes(self.hedge), 22)
        self.assertEqual(
            self.hedge.total_response_commitment_stamina_charged,
            8843,
        )
        self.assertEqual(
            self.hedge.response_requested_commitment_counts,
            {"HIGH": 582, "MEDIUM": 4054},
        )
        self.assertEqual(self.hedge.top_final_stamina_median, 0)
        self.assertEqual(self.hedge.bottom_final_stamina_median, 0)

        self.assertEqual(self._taps(self.always_high), 0)
        self.assertEqual(self._escapes(self.always_high), 22)
        self.assertEqual(
            self.always_high.total_response_commitment_stamina_charged,
            9480,
        )
        self.assertEqual(
            self.always_high.response_requested_commitment_counts,
            {"HIGH": 4612},
        )
        self.assertEqual(self.always_high.top_final_stamina_median, 0)
        self.assertEqual(self.always_high.bottom_final_stamina_median, 0)

    def test_undercommitment_is_split_by_pre_exchange_mutual_exhaustion(self):
        self.assertEqual(
            (
                self.trust.undercommitment_events_before_mutual_exhaustion,
                self.trust.undercommitment_events_after_mutual_exhaustion,
            ),
            (311, 108),
        )
        self.assertEqual(
            (
                self.trust.undercommitment_caused_taps_before_mutual_exhaustion,
                self.trust.undercommitment_caused_taps_after_mutual_exhaustion,
            ),
            (1, 4),
        )
        self.assertEqual(
            (
                self.hedge.undercommitment_events_before_mutual_exhaustion,
                self.hedge.undercommitment_events_after_mutual_exhaustion,
            ),
            (1, 45),
        )
        self.assertEqual(
            (
                self.hedge.undercommitment_caused_taps_before_mutual_exhaustion,
                self.hedge.undercommitment_caused_taps_after_mutual_exhaustion,
            ),
            (0, 0),
        )
        self.assertEqual(
            (
                self.always_high.undercommitment_events_before_mutual_exhaustion,
                self.always_high.undercommitment_events_after_mutual_exhaustion,
            ),
            (0, 78),
        )
        self.assertEqual(
            (
                self.always_high.undercommitment_caused_taps_before_mutual_exhaustion,
                self.always_high.undercommitment_caused_taps_after_mutual_exhaustion,
            ),
            (0, 0),
        )

    def test_checker_names_all_three_policies_and_scopes_gate_f(self):
        rendered = render_v04b_defender_policy_hedge_observation()
        self.assertIn("trusts reads", rendered)
        self.assertIn("one level above", rendered)
        self.assertIn("always HIGH", rendered)
        self.assertIn("Gate F applies only to the frozen trusts-reads policy", rendered)
        self.assertIn("STAMINA-ECONOMY DEBT", rendered)


class V04BDefinitionOfDoneMeasurementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gates = {
            gate.letter: gate
            for gate in measure_v04b_definition_of_done()
        }

    def test_frozen_gate_surface_exists(self):
        self.assertEqual(tuple(self.gates), tuple("ABCDEFGH"))

    def test_all_frozen_v04b_gates_pass(self):
        for letter in "ABCDEFGH":
            self.assertIs(
                self.gates[letter].status,
                V02GateStatus.PASS,
                self.gates[letter].render(),
            )

    def test_gate_f_pins_first_untuned_gate_b_measurement(self):
        self.assertIn("informed Tap=6/100", self.gates["F"].metric)
        self.assertIn("v0.3a Gate B=PASS", self.gates["F"].metric)

    def test_mapping_and_replay_invariants_are_explicit(self):
        self.assertIn("cases=432", self.gates["B"].metric)
        self.assertIn("mismatches=0", self.gates["B"].metric)
        self.assertIn("replay_equal=True", self.gates["G"].metric)


if __name__ == "__main__":
    unittest.main()
