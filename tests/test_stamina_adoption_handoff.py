import math
from dataclasses import replace
from pathlib import Path
import unittest

from bjj_game.diagnostics.stamina_adoption_handoff import (
    A9_HORIZONS_SECONDS,
    HandoffSurfaceReport,
    a9_baseline,
    a9_control,
    current_rule1_control_summary,
    low_both_baseline_summary,
    display_round_up,
    horizon_counts,
    match_level_sensitivity,
    minimum_admissible_clears,
    select_a9,
    wilson_upper_bound,
)
from bjj_game.interfaces.batch import ReExhaustionHandoffEpisode


def _episode(match_index, clear, again, end):
    return ReExhaustionHandoffEpisode(
        match_index=match_index,
        clear_elapsed_seconds=clear,
        reexhausted_elapsed_seconds=again,
        match_end_elapsed_seconds=end,
    )


def _report(episodes):
    episodes = tuple(episodes)
    return HandoffSurfaceReport(
        label="synthetic",
        matches=100,
        clear_events=len(episodes),
        eventual_reexhaustions=0,
        clears_non_exhausted_through_match_end=0,
        time_to_reexhaustion_median=None,
        time_to_reexhaustion_p25=None,
        time_to_reexhaustion_p75=None,
        horizons=tuple(
            horizon_counts(episodes, horizon)
            for horizon in A9_HORIZONS_SECONDS
        ),
    )


class A9FrozenFormulaTests(unittest.TestCase):
    def test_wilson_matches_closed_form_values(self):
        z2 = 1.96 ** 2
        self.assertAlmostEqual(
            wilson_upper_bound(0, 10), z2 / (10 + z2), places=12
        )
        self.assertAlmostEqual(
            wilson_upper_bound(5, 10), 0.7634, places=4
        )
        self.assertAlmostEqual(
            wilson_upper_bound(10, 10), 1.0, places=12
        )

    def test_wilson_matches_dod_formula_term_by_term(self):
        k, n, z = 17, 50, 1.96
        phat = k / n
        center = (phat + z**2 / (2 * n)) / (1 + z**2 / n)
        half = (z / (1 + z**2 / n)) * math.sqrt(
            phat * (1 - phat) / n + z**2 / (4 * n**2)
        )
        self.assertEqual(wilson_upper_bound(k, n), center + half)

    def test_wilson_rejects_empty_denominator(self):
        with self.assertRaises(ValueError):
            wilson_upper_bound(0, 0)

    def test_display_rounding_is_upward_to_hundredths(self):
        self.assertEqual(display_round_up(0.401), 0.41)
        self.assertEqual(display_round_up(0.41), 0.41)
        self.assertEqual(display_round_up(0.4099999), 0.41)

    def test_m_is_43(self):
        self.assertEqual(minimum_admissible_clears(), 43)
        self.assertGreater(1.96 * math.sqrt(0.25 / 42), 0.15)
        self.assertLessEqual(1.96 * math.sqrt(0.25 / 43), 0.15)

    def test_n_is_smallest_horizon_reaching_80_percent_of_t(self):
        # 10 re-exhaustions at +5s, 2 at +15s, 1 at +20s: T=13, 0.8T=10.4.
        # R(5)=10, R(10)=10, R(15)=12 -> N=15.
        episodes = (
            [_episode(i, 10, 15, 300) for i in range(10)]
            + [_episode(i, 10, 25, 300) for i in range(10, 12)]
            + [_episode(12, 10, 30, 300)]
            + [_episode(i, 10, None, 300) for i in range(13, 63)]
        )
        selection = select_a9(_report(episodes))
        self.assertEqual(
            selection.reexhaustions_by_horizon,
            ((5, 10), (10, 10), (15, 12), (20, 13)),
        )
        self.assertEqual(selection.total_t, 13)
        self.assertEqual(selection.selected_n, 15)
        self.assertEqual(selection.reexhausted_at_n, 12)
        self.assertEqual(selection.admissible_at_n, 63)
        self.assertEqual(selection.p_baseline, 12 / 63)
        self.assertEqual(selection.x_upper, wilson_upper_bound(12, 63))
        self.assertFalse(selection.stopped)

    def test_selection_boundary_is_inclusive_at_80_percent(self):
        # T=10, R(5)=8 = 0.8*T exactly -> N=5.
        episodes = (
            [_episode(i, 0, 5, 300) for i in range(8)]
            + [_episode(i, 0, 20, 300) for i in range(8, 10)]
            + [_episode(i, 0, None, 300) for i in range(10, 60)]
        )
        self.assertEqual(select_a9(_report(episodes)).selected_n, 5)

    def test_stop_when_t_below_ten_including_zero(self):
        for count in (0, 9):
            with self.subTest(t=count):
                episodes = (
                    [_episode(i, 0, 5, 300) for i in range(count)]
                    + [_episode(i, 0, None, 300) for i in range(count, 60)]
                )
                selection = select_a9(_report(episodes))
                self.assertTrue(selection.stopped)
                self.assertIsNone(selection.selected_n)
                self.assertIsNone(selection.x_upper)

    def test_stop_when_admissible_clears_at_n_below_43(self):
        episodes = (
            [_episode(i, 0, 5, 300) for i in range(10)]
            + [_episode(i, 0, None, 300) for i in range(10, 42)]
        )
        selection = select_a9(_report(episodes))
        self.assertEqual(selection.admissible_at_n, 42)
        self.assertTrue(selection.stopped)

    def test_censored_clears_excluded_from_admissible_denominator(self):
        episodes = (
            [_episode(i, 0, 5, 300) for i in range(10)]
            + [_episode(i, 0, None, 300) for i in range(10, 43)]
            + [_episode(i, 298, None, 300) for i in range(43, 60)]
        )
        selection = select_a9(_report(episodes))
        self.assertEqual(selection.selected_n, 5)
        self.assertEqual(selection.admissible_at_n, 43)
        self.assertEqual(selection.censored_at_n, 17)
        self.assertFalse(selection.stopped)

    def test_match_level_counts_match_once_and_skips_censored_only(self):
        episodes = (
            _episode(0, 10, 15, 300),   # rapid
            _episode(0, 50, None, 300),  # survived
            _episode(1, 10, None, 300),  # survived only
            _episode(2, 298, None, 300),  # censored only
        )
        sensitivity = match_level_sensitivity(episodes, 5)
        self.assertEqual(sensitivity.matches_with_admissible_clear, 2)
        self.assertEqual(sensitivity.matches_with_rapid_reexhaustion, 1)
        self.assertEqual(sensitivity.p_match, 0.5)


DOCS = Path(__file__).resolve().parents[1] / "docs"


class A9Stage1BaselineTests(unittest.TestCase):
    """Pins the Stage-1 preregistration values (frozen at Stage 1B)."""

    @classmethod
    def setUpClass(cls):
        cls.report, cls.selection, cls.sensitivity = a9_baseline()
        cls.control = a9_control()

    def test_baseline_surface_is_unperturbed_historical_cell(self):
        from bjj_game.diagnostics.stamina_recovery_policy import (
            SettlementAttributionMode,
            recovery_candidate_matrix,
            settlement_attribution_matrix,
        )
        from bjj_game.interfaces.recovery_policy import (
            RecoveryInitiationMode,
        )

        low = next(
            cell for cell in recovery_candidate_matrix()
            if cell.mode is RecoveryInitiationMode.LOW_WHILE_EXHAUSTED
            and not cell.stalling_enabled
        )
        self.assertEqual(
            replace(low_both_baseline_summary(), reexhaustion_handoffs=None),
            low.summary,
        )
        self.assertEqual(self.report.clear_events, low.bottom_latch_clears)

        rule1 = next(
            cell for cell in settlement_attribution_matrix()
            if cell.surface_label.startswith("E")
            and cell.mode is SettlementAttributionMode.RULE1_ONLY
        )
        self.assertEqual(
            replace(
                current_rule1_control_summary(),
                reexhaustion_handoffs=None,
            ),
            rule1.summary,
        )
        self.assertEqual(self.control.clear_events, rule1.bottom_latch_clears)

    def test_low_both_horizon_sweep(self):
        self.assertEqual(self.report.matches, 100)
        self.assertEqual(self.report.clear_events, 67)
        self.assertEqual(self.report.eventual_reexhaustions, 59)
        self.assertEqual(self.report.clears_non_exhausted_through_match_end, 8)
        self.assertEqual(self.report.time_to_reexhaustion_median, 10)
        self.assertEqual(self.report.time_to_reexhaustion_p25, 10.0)
        self.assertEqual(self.report.time_to_reexhaustion_p75, 10.0)
        self.assertEqual(
            tuple(
                (
                    counts.horizon_seconds,
                    counts.reexhausted_within,
                    counts.survived_through,
                    counts.right_censored,
                )
                for counts in self.report.horizons
            ),
            ((5, 0, 63, 4), (10, 59, 4, 4), (15, 59, 0, 8), (20, 59, 0, 8)),
        )

    def test_frozen_a9_values(self):
        selection = self.selection
        self.assertFalse(selection.stopped)
        self.assertEqual(selection.total_t, 59)
        self.assertEqual(selection.selected_n, 10)
        self.assertEqual(selection.admissible_at_n, 63)
        self.assertEqual(selection.censored_at_n, 4)
        self.assertEqual(selection.reexhausted_at_n, 59)
        self.assertEqual(selection.p_baseline, 59 / 63)
        self.assertEqual(selection.x_upper, wilson_upper_bound(59, 63))
        self.assertEqual(repr(selection.x_upper), "0.975034786099515")
        self.assertEqual(selection.x_display, 0.98)
        self.assertEqual(selection.m_min, 43)

    def test_low_both_match_level_sensitivity(self):
        self.assertEqual(self.sensitivity.matches_with_admissible_clear, 61)
        self.assertEqual(self.sensitivity.matches_with_rapid_reexhaustion, 58)
        self.assertEqual(self.sensitivity.p_match, 58 / 61)

    def test_current_rule1_control_has_no_denominator(self):
        self.assertEqual(self.control.clear_events, 0)
        for counts in self.control.horizons:
            self.assertEqual(counts.admissible, 0)
            self.assertIsNone(counts.rate)

    def test_preregistration_document_matches_measurement(self):
        text = (
            DOCS / "STAMINA_PRODUCTION_POLICY_ADOPTION_PREREGISTRATION.md"
        ).read_text(encoding="utf-8")
        for horizon, observed in self.selection.reexhaustions_by_horizon:
            self.assertIn(f"R({horizon})={observed}\n", text)
        for line in (
            f"T=R(20)={self.selection.total_t}\n",
            f"N={self.selection.selected_n} s (2 ticks)\n",
            f"baseline admissible clears at N={self.selection.admissible_at_n}\n",
            f"baseline censored clears at N={self.selection.censored_at_n}\n",
            f"p_baseline=59/63={self.selection.p_baseline!r} (unrounded)\n",
            f"X={self.selection.x_upper!r} (unrounded; authoritative)\n",
            f"X display={self.selection.x_display}",
            "M=43 admissible clears",
            "STOP: none",
            f"p_match={self.sensitivity.p_match!r}\n",
        ):
            self.assertIn(line, text)

    def test_preregistration_copies_a1_through_a10_verbatim(self):
        dod = (
            DOCS / "STAMINA_PRODUCTION_POLICY_ADOPTION_DEFINITION_OF_DONE.md"
        ).read_text(encoding="utf-8")
        start = dod.index("# Adoption-run pre-registration\n")
        end = dod.index("---\n\n# Required measurement document\n")
        expected = dod[start:end].rstrip("\n") + "\n"

        prereg = (
            DOCS / "STAMINA_PRODUCTION_POLICY_ADOPTION_PREREGISTRATION.md"
        ).read_text(encoding="utf-8")
        begin_marker = "<!-- BEGIN VERBATIM DoD A1-A10 -->\n"
        end_marker = "<!-- END VERBATIM DoD A1-A10 -->"
        copied = prereg[
            prereg.index(begin_marker) + len(begin_marker):
            prereg.index(end_marker)
        ]
        self.assertEqual(copied, expected)


if __name__ == "__main__":
    unittest.main()
