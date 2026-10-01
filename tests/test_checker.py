import unittest

from mount_v0.catalog import BOTTOM_ELBOW_KNEE_ESCAPE, BOTTOM_TRAP_AND_ROLL_ESCAPE
from mount_v0.checker import render_enumeration, run_checks
from mount_v0.model import ExitDestination, TopBehavior


class CheckerTests(unittest.TestCase):
    def test_semantic_checker_passes(self):
        report = run_checks()
        self.assertEqual(report.errors, [])
        self.assertTrue(report.ok)

    def test_both_elbow_escape_branches_reachable(self):
        report = run_checks()
        self.assertTrue(report.reachable_exits[ExitDestination.HALF_GUARD])
        self.assertTrue(report.reachable_exits[ExitDestination.OPEN_GUARD])

    def test_elbow_escape_branch_ranges_are_reported(self):
        report = run_checks()
        half = report.escape_reachability[
            (BOTTOM_ELBOW_KNEE_ESCAPE, TopBehavior.PRESSURE, ExitDestination.HALF_GUARD)
        ]
        open_guard = report.escape_reachability[
            (BOTTOM_ELBOW_KNEE_ESCAPE, TopBehavior.PRESSURE, ExitDestination.OPEN_GUARD)
        ]
        self.assertEqual((min(h.axis for h in half), max(h.axis for h in half)), (0.10, 2.10))
        self.assertEqual((min(h.axis for h in open_guard), max(h.axis for h in open_guard)), (0.10, 1.19))

    def test_trap_and_roll_reversal_reachable_under_pressure_and_hold(self):
        report = run_checks()
        pressure = report.escape_reachability[
            (BOTTOM_TRAP_AND_ROLL_ESCAPE, TopBehavior.PRESSURE, ExitDestination.REVERSAL)
        ]
        hold = report.escape_reachability[
            (BOTTOM_TRAP_AND_ROLL_ESCAPE, TopBehavior.HOLD, ExitDestination.REVERSAL)
        ]
        self.assertTrue(pressure)
        self.assertTrue(hold)
        self.assertEqual(max(h.axis for h in pressure), 2.10)
        self.assertEqual(max(h.axis for h in hold), 1.10)

    def test_perfect_response_lock_is_reported_not_error(self):
        report = run_checks()
        self.assertTrue(report.perfect_response_lock)
        self.assertEqual(report.errors, [])

    def test_never_best_hedges_are_reported(self):
        report = run_checks()
        self.assertEqual(set(report.never_best_responses), {"Turn-In Recovery", "Wide Mount Base"})

    def test_enumerate_contains_diagnostics_and_full_tuning_watch(self):
        text = render_enumeration()
        self.assertIn("PERFECT-RESPONSE LOCK: PRESENT", text)
        self.assertIn("NEVER-BEST (hedge response): Turn-In Recovery", text)
        self.assertIn("NEVER-BEST (hedge response): Wide Mount Base", text)
        self.assertIn("ESCAPE BRANCH REACHABILITY — FULL TUNING WATCH", text)
        self.assertIn("Elbow-Knee Escape — Top PRESSURE", text)
        self.assertIn("Half Guard: REACHABLE", text)
        self.assertIn("Overall axis range: +0.10..+2.10", text)
        self.assertIn("Open Guard: REACHABLE", text)
        self.assertIn("Overall axis range: +0.10..+1.19", text)
        self.assertIn("Stable +0.81..+2.10", text)
        self.assertIn("Loose  +0.10..+1.19", text)
        self.assertIn("Trap-and-Roll Escape — Top HOLD", text)
        self.assertIn("Reversal: REACHABLE", text)
        self.assertIn(
            "TOP-BEHAVIOR REACHABILITY EFFECT: Trap-and-Roll Escape -> Reversal; PRESSURE +0.10..+2.10; HOLD +0.10..+1.10",
            text,
        )
        self.assertIn("STATUS: PASS", text)
