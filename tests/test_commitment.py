import unittest

from bjj_game.domain.action import Commitment
from bjj_game.domain.model import Side
from bjj_game.engine.match import MountMatch
from bjj_game.engine.stamina import DEFAULT_STAMINA_COST_POLICY, StaminaCostPolicy
from bjj_game.positions.mount.catalog import (
    BOTTOM_RESPONSE_TURN_IN_RECOVERY,
    TOP_HIGH_MOUNT_CLIMB,
)


class CommitmentPolicyTests(unittest.TestCase):
    def test_default_costs_are_explicit_prototype_values(self):
        self.assertEqual(DEFAULT_STAMINA_COST_POLICY.cost(Commitment.LOW), 3)
        self.assertEqual(DEFAULT_STAMINA_COST_POLICY.cost(Commitment.MEDIUM), 7)
        self.assertEqual(DEFAULT_STAMINA_COST_POLICY.cost(Commitment.HIGH), 12)

    def test_policy_requires_all_commitments_and_increasing_costs(self):
        with self.assertRaises(ValueError):
            StaminaCostPolicy.build({Commitment.LOW: 3})
        with self.assertRaises(ValueError):
            StaminaCostPolicy.build(
                {
                    Commitment.LOW: 3,
                    Commitment.MEDIUM: 3,
                    Commitment.HIGH: 12,
                }
            )


class CommitmentAttemptTests(unittest.TestCase):
    def _attempt(self, commitment: Commitment, stamina: int = 100):
        match = MountMatch(initial_clock=30, starting_axis=1.50)
        match.top.stamina.set_current(stamina)
        result = match.attempt(
            action_id=TOP_HIGH_MOUNT_CLIMB,
            response_id=BOTTOM_RESPONSE_TURN_IN_RECOVERY,
            commitment=commitment,
        )
        return match, result

    def test_commitment_charges_initiator_only(self):
        match, result = self._attempt(Commitment.MEDIUM)
        self.assertEqual(result.stamina.before, 100)
        self.assertEqual(result.stamina.requested, 7)
        self.assertEqual(result.stamina.charged, 7)
        self.assertEqual(result.stamina.shortfall, 0)
        self.assertEqual(result.stamina.after, 93)
        self.assertEqual(match.top.stamina.current, 93)
        self.assertEqual(match.bottom.stamina.current, 100)
        self.assertIs(result.attempt.initiator, Side.TOP)

    def test_low_medium_high_change_cost_not_resolution(self):
        outcomes = {}
        for commitment in Commitment:
            match, result = self._attempt(commitment)
            outcomes[commitment] = result.resolution
        self.assertEqual(outcomes[Commitment.LOW], outcomes[Commitment.MEDIUM])
        self.assertEqual(outcomes[Commitment.MEDIUM], outcomes[Commitment.HIGH])

    def test_cost_shortfall_is_recorded_without_blocking_or_modifying_action(self):
        exhausted, high = self._attempt(Commitment.HIGH, stamina=5)
        fresh, reference = self._attempt(Commitment.HIGH, stamina=100)

        self.assertEqual(high.stamina.requested, 12)
        self.assertEqual(high.stamina.charged, 5)
        self.assertEqual(high.stamina.shortfall, 7)
        self.assertEqual(high.stamina.after, 0)
        self.assertFalse(high.stamina.fully_paid)
        self.assertEqual(high.resolution, reference.resolution)
        self.assertEqual(exhausted.axis, fresh.axis)
        self.assertEqual(exhausted.band, fresh.band)

    def test_invalid_attempt_does_not_spend_stamina(self):
        match = MountMatch()
        with self.assertRaises(ValueError):
            match.attempt(
                action_id="not.a.real.action",
                response_id=BOTTOM_RESPONSE_TURN_IN_RECOVERY,
                commitment=Commitment.HIGH,
            )
        self.assertEqual(match.top.stamina.current, 100)
        self.assertEqual(match.history.commitment_history, [])

    def test_legacy_decide_path_spends_no_stamina(self):
        match = MountMatch()
        match.decide(
            action_id=TOP_HIGH_MOUNT_CLIMB,
            response_id=BOTTOM_RESPONSE_TURN_IN_RECOVERY,
        )
        self.assertEqual(match.top.stamina.current, 100)
        self.assertEqual(match.history.commitment_history, [])

    def test_attempt_history_records_commitment_and_cost(self):
        match, _ = self._attempt(Commitment.LOW)
        self.assertEqual(match.history.commitment_history, ["LOW"])
        self.assertEqual(match.history.stamina_requested_history, [3])
        self.assertEqual(match.history.stamina_charged_history, [3])
        self.assertEqual(match.history.stamina_shortfall_history, [0])


if __name__ == "__main__":
    unittest.main()
