import unittest

from bjj_game.domain.action import Commitment
from bjj_game.domain.model import BottomBehavior, Grade, Side
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
    def test_setup_dependent_targets_are_illegal_before_ready(self):
        match = MountMatch(starting_axis=1.50, enable_v02_setup=True)

        match.initiator = Side.BOTTOM
        self.assertNotIn(
            BOTTOM_TRAP_AND_ROLL_ESCAPE,
            match.legal_action_ids(),
        )
        with self.assertRaises(ValueError):
            match.attempt(
                action_id=BOTTOM_TRAP_AND_ROLL_ESCAPE,
                response_id=TOP_RESPONSE_HIP_FOLLOW_REPUMMEL,
                commitment=Commitment.MEDIUM,
            )

        match.initiator = Side.TOP
        self.assertNotIn(
            TOP_AMERICANA_ARM_ISOLATION,
            match.legal_action_ids(),
        )

    def test_best_counter_cannot_freeze_setup_progress(self):
        bottom = MountMatch(starting_axis=1.50, enable_v02_setup=True)
        for expected in (SetupTier.PARTIAL, SetupTier.READY):
            bottom.initiator = Side.BOTTOM
            bottom.attempt(
                action_id=BOTTOM_BRIDGE,
                response_id=TOP_RESPONSE_POST_AND_BASE,
                commitment=Commitment.MEDIUM,
            )
            self.assertIs(
                bottom.setup_tier(BOTTOM_TRAP_AND_ROLL_ESCAPE),
                expected,
            )

        top = MountMatch(starting_axis=1.50, enable_v02_setup=True)
        for expected in (SetupTier.PARTIAL, SetupTier.READY):
            top.initiator = Side.TOP
            top.attempt(
                action_id=TOP_HIGH_MOUNT_CLIMB,
                response_id=BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE,
                commitment=Commitment.MEDIUM,
            )
            self.assertIs(
                top.setup_tier(TOP_AMERICANA_ARM_ISOLATION),
                expected,
            )

    def test_upper_cap_fully_absorbed_builder_does_not_advance_setup(self):
        match = MountMatch(starting_axis=4.00, enable_v02_setup=True)
        match.initiator = Side.BOTTOM
        match.attempt(
            action_id=BOTTOM_BRIDGE,
            response_id=TOP_RESPONSE_POST_AND_BASE,
            commitment=Commitment.MEDIUM,
        )

        self.assertIs(
            match.setup_tier(BOTTOM_TRAP_AND_ROLL_ESCAPE),
            SetupTier.NONE,
        )

    def test_partial_move_into_upper_cap_still_advances_setup(self):
        match = MountMatch(starting_axis=3.50, enable_v02_setup=True)
        match.initiator = Side.BOTTOM
        match.attempt(
            action_id=BOTTOM_BRIDGE,
            response_id=TOP_RESPONSE_POST_AND_BASE,
            commitment=Commitment.MEDIUM,
        )

        self.assertEqual(match.axis, 4.00)
        self.assertIs(
            match.setup_tier(BOTTOM_TRAP_AND_ROLL_ESCAPE),
            SetupTier.PARTIAL,
        )

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
            set(match.legal_response_ids(BOTTOM_TRAP_AND_ROLL_ESCAPE)),
            {
                TOP_RESPONSE_WIDE_MOUNT_BASE,
                TOP_RESPONSE_HIP_FOLLOW_REPUMMEL,
            },
        )

        stalled = match.attempt(
            action_id=BOTTOM_TRAP_AND_ROLL_ESCAPE,
            response_id=TOP_RESPONSE_WIDE_MOUNT_BASE,
            commitment=Commitment.MEDIUM,
        )
        self.assertIs(stalled.resolution.final_grade, Grade.CONTESTED)
        self.assertIs(
            match.setup_tier(BOTTOM_TRAP_AND_ROLL_ESCAPE),
            SetupTier.NONE,
        )
        self.assertEqual(len(match.history.setup_consumption_history), 1)

    def test_ready_stalemate_response_is_post_positional_but_pre_exhaustion(self):
        match = MountMatch(starting_axis=3.50, enable_v02_setup=True)
        match.setup_state.advance(BOTTOM_TRAP_AND_ROLL_ESCAPE)
        match.setup_state.advance(BOTTOM_TRAP_AND_ROLL_ESCAPE)
        match.initiator = Side.BOTTOM

        fresh = match.attempt(
            action_id=BOTTOM_TRAP_AND_ROLL_ESCAPE,
            response_id=TOP_RESPONSE_WIDE_MOUNT_BASE,
            commitment=Commitment.MEDIUM,
        )
        self.assertIs(fresh.resolution.final_grade, Grade.CONTESTED)

        exhausted = MountMatch(starting_axis=3.50, enable_v02_setup=True)
        exhausted.setup_state.advance(BOTTOM_TRAP_AND_ROLL_ESCAPE)
        exhausted.setup_state.advance(BOTTOM_TRAP_AND_ROLL_ESCAPE)
        exhausted.initiator = Side.BOTTOM
        exhausted.bottom.stamina.set_current(25)
        tired = exhausted.attempt(
            action_id=BOTTOM_TRAP_AND_ROLL_ESCAPE,
            response_id=TOP_RESPONSE_WIDE_MOUNT_BASE,
            commitment=Commitment.MEDIUM,
        )
        self.assertIs(tired.resolution.final_grade, Grade.FAILURE)

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

    def test_ready_americana_turn_in_is_stalemate_across_position_modifiers(self):
        match = MountMatch(starting_axis=0.50, enable_v02_setup=True)
        match.set_behaviors(
            bottom=BottomBehavior.PROTECT,
        )
        match.setup_state.advance(TOP_AMERICANA_ARM_ISOLATION)
        match.setup_state.advance(TOP_AMERICANA_ARM_ISOLATION)
        match.initiator = Side.TOP

        result = match.attempt(
            action_id=TOP_AMERICANA_ARM_ISOLATION,
            response_id=BOTTOM_RESPONSE_TURN_IN_RECOVERY,
            commitment=Commitment.MEDIUM,
        )
        self.assertIs(result.resolution.final_grade, Grade.CONTESTED)

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
