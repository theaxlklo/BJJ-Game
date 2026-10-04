import unittest

from bjj_game.domain.model import Side
from bjj_game.engine.match import MountMatch
from bjj_game.interfaces.recovery_policy import RecoveryPolicyCollector
from bjj_game.diagnostics.stamina_recovery_policy import (
    RecoveryInitiationMode,
    recovery_candidate_matrix,
    recovery_candidate_off_shadow_surfaces,
    shadow_nonperturbation,
)
from bjj_game.diagnostics.stamina_settlement import postchange_surfaces


class StaminaRecoveryCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cells = recovery_candidate_matrix()
        cls.off_surfaces = recovery_candidate_off_shadow_surfaces()

    def test_exact_three_by_two_candidate_matrix(self):
        self.assertEqual(len(self.cells), 6)
        self.assertEqual(
            {cell.mode for cell in self.cells},
            set(RecoveryInitiationMode),
        )
        for mode in RecoveryInitiationMode:
            selected = [cell for cell in self.cells if cell.mode is mode]
            self.assertEqual(len(selected), 2)
            self.assertEqual(
                {cell.stalling_enabled for cell in selected},
                {False, True},
            )

    def test_shadow_observer_does_not_perturb_off_runs(self):
        self.assertEqual(shadow_nonperturbation(), (True, True, True))

    def test_current_off_reproduces_pr8_both_surface_e(self):
        current = self.off_surfaces[0].summary
        expected = postchange_surfaces()[4].summary
        for name in current.__dataclass_fields__:
            if name == "recovery_policy":
                continue
            self.assertEqual(
                getattr(current, name),
                getattr(expected, name),
                name,
            )

    def test_current_exhausted_bottom_requests_medium(self):
        current = next(
            cell
            for cell in self.cells
            if cell.mode is RecoveryInitiationMode.CURRENT
            and not cell.stalling_enabled
        )
        counts = dict(current.exhausted_requested_commitments)
        self.assertGreater(sum(counts.values()), 0)
        self.assertEqual(set(counts), {"MEDIUM"})

    def test_reset_exhausted_bottom_does_not_attempt_actions(self):
        reset = next(
            cell
            for cell in self.cells
            if cell.mode is RecoveryInitiationMode.RESET_WHILE_EXHAUSTED
            and not cell.stalling_enabled
        )
        self.assertEqual(dict(reset.exhausted_requested_commitments), {})
        self.assertGreater(reset.exhausted_resets, 0)

    def test_low_exhausted_bottom_requests_only_low(self):
        low = next(
            cell
            for cell in self.cells
            if cell.mode is RecoveryInitiationMode.LOW_WHILE_EXHAUSTED
            and not cell.stalling_enabled
        )
        counts = dict(low.exhausted_requested_commitments)
        self.assertGreater(sum(counts.values()), 0)
        self.assertEqual(set(counts), {"LOW"})

    def test_stalling_on_has_no_shadow_events(self):
        for cell in self.cells:
            if cell.stalling_enabled:
                self.assertEqual(cell.shadow_warnings, 0)
                self.assertEqual(cell.shadow_penalties, 0)
                self.assertEqual(cell.shadow_position_resets, 0)
                self.assertEqual(cell.shadow_free_initiative, 0)

    def test_shadow_tracker_uses_frozen_warning_then_penalty_escalation(self):
        match = MountMatch(
            starting_axis=1.50,
            enable_v02_setup=True,
            enable_v03_submissions=True,
            enable_v04_commitment_semantics=True,
        )
        match.initiator = Side.BOTTOM
        collector = RecoveryPolicyCollector(
            mode=RecoveryInitiationMode.RESET_WHILE_EXHAUSTED,
            shadow_stalling=True,
        )
        collector.start_match(match, match_index=0)

        before = (
            match.axis,
            match.clock_seconds,
            match.top.stamina.current,
            match.bottom.stamina.current,
        )
        collector.after_advance(match, duration_seconds=20)
        progress = collector.before_reset(
            match,
            forced_recovery_reset=True,
        )
        self.assertTrue(progress)

        collector.after_advance(match, duration_seconds=20)
        progress = collector.before_reset(
            match,
            forced_recovery_reset=True,
        )
        self.assertTrue(progress)

        after = (
            match.axis,
            match.clock_seconds,
            match.top.stamina.current,
            match.bottom.stamina.current,
        )
        self.assertEqual(after, before)

        collector.finish_match(
            match,
            outcome="TIMEOUT — Mount retained",
        )
        record = collector.measurement().matches[0]
        self.assertEqual(
            tuple(event.tracker_consequence for event in record.shadow_events),
            ("WARNING", "PENALTY"),
        )
        self.assertEqual(
            tuple(event.effective_consequence for event in record.shadow_events),
            ("WARNING", "PENALTY"),
        )
        self.assertEqual(
            tuple(event.clock_seconds for event in record.shadow_events),
            (20, 20),
        )

    def test_stalling_off_exposes_shadow_counters(self):
        for cell in self.cells:
            if not cell.stalling_enabled:
                self.assertGreaterEqual(cell.shadow_bottom_resets_with_route, 0)
                self.assertGreaterEqual(cell.shadow_warnings, 0)
                self.assertGreaterEqual(cell.shadow_penalties, 0)
                self.assertGreaterEqual(cell.shadow_position_resets, 0)
                self.assertGreaterEqual(cell.shadow_free_initiative, 0)


if __name__ == "__main__":
    unittest.main()
