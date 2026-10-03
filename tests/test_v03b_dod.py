import unittest

from bjj_game.diagnostics.checker import (
    V02GateStatus,
    _v03_recognition_mechanic_present,
    _v03_response_commitment_present,
    _v03b_boundary_probe,
    _v03b_stalemated_attacker_probe,
    _v03b_symmetry_probe,
    V03B_GATE_A_LOCKED_DWELL_LIMIT_SECONDS,
    V03B_GATE_A_LOCKED_SHARE_LIMIT,
    _v03b_gate_a_case_passes,
    _v03b_stall_vs_active_bottom_probe,
    _v03b_top_stall_probe,
    _v03b_top_stall_sweep,
    measure_v03a_definition_of_done,
    measure_v03b_definition_of_done,
    render_v03b_normal_play_guard,
)
from bjj_game.domain.model import Band
from bjj_game.domain.submission import SubmissionStage


class V03BDefinitionOfDoneTests(unittest.TestCase):
    def setUp(self):
        self.gates = {
            gate.letter: gate
            for gate in measure_v03b_definition_of_done()
        }

    def test_gate_a_post_reset_sweep_is_open_on_three_exact_half_cases(self):
        sweep = _v03b_top_stall_sweep()
        self.assertEqual(len(sweep), 26)
        failing = [
            item for item in sweep if not _v03b_gate_a_case_passes(item)
        ]
        self.assertEqual(
            [(item.interval_seconds, item.match_length_seconds) for item in failing],
            [(7, 250), (7, 275), (7, 280)],
        )
        self.assertTrue(
            all(item.steady_state_locked_share == 0.50 for item in failing)
        )
        self.assertTrue(
            all(item.steady_state_longest_locked_dwell_seconds == 7 for item in failing)
        )
        self.assertEqual(
            max(item.steady_state_locked_share for item in sweep),
            0.50,
        )
        self.assertEqual(
            max(item.steady_state_longest_locked_dwell_seconds for item in sweep),
            7,
        )
        self.assertIs(self.gates["A"].status, V02GateStatus.OPEN)

    def test_stall_vs_active_bottom_observation_reproduces_timeout_surface(self):
        evidence = _v03b_stall_vs_active_bottom_probe()
        self.assertEqual(evidence.matches, 100)
        self.assertEqual(evidence.timeouts, 100)
        self.assertEqual(evidence.escapes, 0)
        self.assertEqual(evidence.warnings, 100)
        self.assertEqual(evidence.penalties, 100)
        self.assertEqual(evidence.position_resets, 800)

    def test_normal_play_guard_keeps_stronger_escalation_out_of_engaged_batches(self):
        self.assertIn(
            "V0.3b NORMAL-PLAY GUARD [PASS]",
            render_v03b_normal_play_guard(),
        )

    def test_gate_b_stalemated_attacker_and_defender_remain_engaged(self):
        evidence = _v03b_stalemated_attacker_probe()
        self.assertGreater(evidence.attempts, 0)
        self.assertEqual(evidence.top_penalties, 0)
        self.assertEqual(evidence.bottom_penalties, 0)
        self.assertIs(evidence.final_stage, SubmissionStage.THREAT)
        self.assertEqual(evidence.top_clock, 0)
        self.assertEqual(evidence.bottom_clock, 0)
        self.assertIs(self.gates["B"].status, V02GateStatus.PASS)

    def test_gate_c_same_ladder_penalizes_both_sides(self):
        evidence = _v03b_symmetry_probe()
        self.assertEqual(evidence.top_warnings, 1)
        self.assertGreaterEqual(evidence.top_penalties, 1)
        self.assertEqual(evidence.bottom_warnings, 1)
        self.assertGreaterEqual(evidence.bottom_penalties, 1)
        self.assertIs(self.gates["C"].status, V02GateStatus.PASS)

    def test_gate_d_loose_boundary_uses_free_initiative(self):
        evidence = _v03b_boundary_probe()
        self.assertEqual(evidence.warnings, 1)
        self.assertEqual(evidence.free_windows, 1)
        self.assertAlmostEqual(evidence.axis_before, evidence.axis_after)
        self.assertIs(evidence.band_after, Band.LOOSE)
        self.assertEqual(evidence.clock_before, evidence.clock_after)
        self.assertIs(self.gates["D"].status, V02GateStatus.PASS)

    def test_gate_e_does_not_expire_v03a_gate_b(self):
        self.assertFalse(_v03_response_commitment_present())
        self.assertFalse(_v03_recognition_mechanic_present())
        v03a_gate_b = next(
            gate
            for gate in measure_v03a_definition_of_done()
            if gate.letter == "B"
        )
        self.assertIs(v03a_gate_b.status, V02GateStatus.DEFERRED)
        self.assertIs(self.gates["E"].status, V02GateStatus.PASS)


if __name__ == "__main__":
    unittest.main()
