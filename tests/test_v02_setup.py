import unittest

from bjj_game.domain.action import Commitment
from bjj_game.domain.model import Side
from bjj_game.domain.setup import SetupState, SetupTier
from bjj_game.engine.match import MountMatch
from bjj_game.positions.mount.catalog import (
    BOTTOM_BRIDGE,
    BOTTOM_RESPONSE_FOREARM_FRAME,
    BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE,
    BOTTOM_RESPONSE_TURN_IN_RECOVERY,
    BOTTOM_TRAP_AND_ROLL_ESCAPE,
    TOP_AMERICANA_ARM_ISOLATION,
    TOP_HIGH_MOUNT_CLIMB,
    TOP_RESPONSE_HIP_FOLLOW_REPUMMEL,
    TOP_RESPONSE_POST_AND_BASE,
    TOP_RESPONSE_WIDE_MOUNT_BASE,
)


class SetupStateTests(unittest.TestCase):
    def test_discrete_setup_progression_caps_at_ready_and_consumes(self):
        state = SetupState.for_targets(("target",))
        self.assertIs(state.tier("target"), SetupTier.NONE)

        first = state.advance("target")
        self.assertIs(first.before, SetupTier.NONE)
        self.assertIs(first.after, SetupTier.PARTIAL)

        second = state.advance("target")
        self.assertIs(second.before, SetupTier.PARTIAL)
        self.assertIs(second.after, SetupTier.READY)

        capped = state.advance("target")
        self.assertIs(capped.before, SetupTier.READY)
        self.assertIs(capped.after, SetupTier.READY)

        consumed = state.consume("target")
        self.assertIs(consumed.before, SetupTier.READY)
        self.assertIs(consumed.after, SetupTier.NONE)


class MountSetupReadyTests(unittest.TestCase):
    def test_bridge_successes_build_trap_and_roll_to_ready(self):
        match = MountMatch(starting_axis=1.50, enable_v02_setup=True)

        for expected in (SetupTier.PARTIAL, SetupTier.READY):
            match.initiator = Side.BOTTOM
            match.attempt(
                action_id=BOTTOM_BRIDGE,
                response_id=TOP_RESPONSE_HIP_FOLLOW_REPUMMEL,
                commitment=Commitment.MEDIUM,
            )
            self.assertIs(
                match.setup_tier(BOTTOM_TRAP_AND_ROLL_ESCAPE),
                expected,
            )

        self.assertEqual(len(match.history.setup_change_history), 2)

    def test_ready_trap_and_roll_limits_responses_and_consumes_on_use(self):
        match = MountMatch(starting_axis=1.50, enable_v02_setup=True)
        match.setup_state.advance(BOTTOM_TRAP_AND_ROLL_ESCAPE)
        match.setup_state.advance(BOTTOM_TRAP_AND_ROLL_ESCAPE)
        match.initiator = Side.BOTTOM

        self.assertEqual(
            match.legal_response_ids(BOTTOM_TRAP_AND_ROLL_ESCAPE),
            (TOP_RESPONSE_HIP_FOLLOW_REPUMMEL,),
        )

        with self.assertRaises(ValueError):
            match.attempt(
                action_id=BOTTOM_TRAP_AND_ROLL_ESCAPE,
                response_id=TOP_RESPONSE_WIDE_MOUNT_BASE,
                commitment=Commitment.MEDIUM,
            )

        match.attempt(
            action_id=BOTTOM_TRAP_AND_ROLL_ESCAPE,
            response_id=TOP_RESPONSE_HIP_FOLLOW_REPUMMEL,
            commitment=Commitment.MEDIUM,
        )
        self.assertIs(
            match.setup_tier(BOTTOM_TRAP_AND_ROLL_ESCAPE),
            SetupTier.NONE,
        )
        self.assertEqual(len(match.history.setup_consumption_history), 1)

    def test_high_mount_successes_build_americana_ready(self):
        match = MountMatch(starting_axis=1.50, enable_v02_setup=True)

        for expected in (SetupTier.PARTIAL, SetupTier.READY):
            match.initiator = Side.TOP
            match.attempt(
                action_id=TOP_HIGH_MOUNT_CLIMB,
                response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
                commitment=Commitment.MEDIUM,
            )
            self.assertIs(
                match.setup_tier(TOP_AMERICANA_ARM_ISOLATION),
                expected,
            )

        match.initiator = Side.TOP
        self.assertEqual(
            set(match.legal_response_ids(TOP_AMERICANA_ARM_ISOLATION)),
            {
                BOTTOM_RESPONSE_FOREARM_FRAME,
                BOTTOM_RESPONSE_TURN_IN_RECOVERY,
            },
        )

        with self.assertRaises(ValueError):
            match.attempt(
                action_id=TOP_AMERICANA_ARM_ISOLATION,
                response_id=BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE,
                commitment=Commitment.MEDIUM,
            )

    def test_setup_disabled_does_not_build_progress(self):
        match = MountMatch(starting_axis=1.50)
        match.initiator = Side.BOTTOM
        match.attempt(
            action_id=BOTTOM_BRIDGE,
            response_id=TOP_RESPONSE_HIP_FOLLOW_REPUMMEL,
            commitment=Commitment.MEDIUM,
        )
        self.assertIs(
            match.setup_tier(BOTTOM_TRAP_AND_ROLL_ESCAPE),
            SetupTier.NONE,
        )

    def test_frozen_decide_path_does_not_enforce_ready_response_legality(self):
        match = MountMatch(starting_axis=1.50, enable_v02_setup=True)
        match.setup_state.advance(BOTTOM_TRAP_AND_ROLL_ESCAPE)
        match.setup_state.advance(BOTTOM_TRAP_AND_ROLL_ESCAPE)
        match.initiator = Side.BOTTOM

        result = match.decide(
            action_id=BOTTOM_TRAP_AND_ROLL_ESCAPE,
            response_id=TOP_RESPONSE_POST_AND_BASE,
        )

        self.assertEqual(result.response_id, TOP_RESPONSE_POST_AND_BASE)
        self.assertIs(
            match.setup_tier(BOTTOM_TRAP_AND_ROLL_ESCAPE),
            SetupTier.READY,
        )


if __name__ == "__main__":
    unittest.main()
