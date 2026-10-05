"""Pins the first untuned Stage-2 production-candidate measurement."""

from pathlib import Path
import unittest

from bjj_game.diagnostics.stamina_adoption_candidate import (
    A9Verdict,
    GateStatus,
    Prediction,
    a9_candidate,
    candidate_surface,
    clustering_explanation_required,
    handoff_report,
    matched_divergences,
    measure_adoption_gates,
    recovery_cell,
    score_predictions,
    settlement_cell,
)

DOCS = Path(__file__).resolve().parents[1] / "docs"


class StaminaAdoptionCandidateMeasurementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gates = {gate.letter: gate for gate in measure_adoption_gates()}
        cls.predictions = {
            key: (score, metric) for key, score, metric in score_predictions()
        }
        cls.a9 = a9_candidate()

    def test_gates(self):
        for letter in "ABCDEFH":
            self.assertIs(
                self.gates[letter].status,
                GateStatus.PASS,
                self.gates[letter].render(),
            )
        self.assertIs(self.gates["G"].status, GateStatus.NOT_EVALUATED)

    def test_predictions_all_confirmed(self):
        self.assertEqual(
            tuple(self.predictions),
            tuple(f"A{index}" for index in range(1, 11)),
        )
        for key, (score, metric) in self.predictions.items():
            self.assertIs(score, Prediction.CONFIRMED, f"{key}: {metric}")

    def test_surface_a_and_b(self):
        a = settlement_cell("A")
        self.assertEqual((a.threat_matches, a.threat_entries, a.taps), (78, 1950, 0))
        self.assertEqual(settlement_cell("B").taps, 9)
        for name in ("A", "B", "E-PROD OFF+shadow", "E-PROD ON"):
            cell = settlement_cell(name)
            self.assertEqual(cell.unfunded_responder_spend, 0, name)
            self.assertEqual(cell.hold_covered, 0, name)

    def test_e_prod_counters(self):
        off = recovery_cell("E-PROD OFF+shadow")
        self.assertEqual(
            (off.taps, off.half_guard, off.open_guard, off.reversal, off.timeouts),
            (5, 16, 10, 9, 60),
        )
        self.assertEqual(off.bottom_final_median, 29.0)
        self.assertEqual(
            (
                off.bottom_latch_clears,
                off.bottom_conserve_to_escape,
                off.state2_to_state1_exits,
            ),
            (46, 38, 46),
        )
        self.assertEqual(
            (
                off.exhausted_bridge_attempts,
                off.exhausted_setup_builder_attempts,
                off.exhausted_completed_setup_builds,
            ),
            (1227, 1227, 1107),
        )
        self.assertEqual(dict(off.exhausted_requested_commitments), {"LOW": 1839})
        self.assertEqual(off.shadow_bottom_resets_with_route, 13)
        self.assertEqual(settlement_cell("E-PROD OFF+shadow").additive_double_charge_cases, 179)

    def test_stalling_on_identical_and_offense_free(self):
        on = recovery_cell("E-PROD ON")
        self.assertEqual(
            (
                on.bottom_stalling_warnings,
                on.bottom_stalling_penalties,
                on.bottom_stalling_position_resets,
                on.bottom_stalling_free_initiative,
            ),
            (0, 0, 0, 0),
        )
        self.assertEqual(matched_divergences(), ())

    def test_handoff_original_100(self):
        report = handoff_report()
        self.assertEqual(report.clear_events, 46)
        self.assertEqual(report.eventual_reexhaustions, 34)
        self.assertEqual(report.clears_non_exhausted_through_match_end, 12)
        self.assertEqual(
            tuple(
                (c.horizon_seconds, c.reexhausted_within, c.survived_through, c.right_censored)
                for c in report.horizons
            ),
            ((5, 0, 37, 9), (10, 34, 3, 9), (15, 34, 0, 12), (20, 34, 0, 12)),
        )

    def test_a9_ext_triggered_and_pooled_verdict(self):
        a9 = self.a9
        self.assertEqual(a9.original_at_n.admissible, 37)
        self.assertTrue(a9.ext_triggered)
        self.assertEqual(
            (a9.ext_at_n.reexhausted_within, a9.ext_at_n.survived_through, a9.ext_at_n.right_censored),
            (30, 2, 5),
        )
        self.assertEqual(
            (a9.pooled_at_n.reexhausted_within, a9.pooled_at_n.admissible, a9.pooled_at_n.right_censored),
            (64, 69, 14),
        )
        self.assertEqual(a9.p_candidate, 64 / 69)
        self.assertIs(a9.verdict, A9Verdict.PASS)
        self.assertEqual(
            (
                a9.sensitivity.matches_with_admissible_clear,
                a9.sensitivity.matches_with_rapid_reexhaustion,
            ),
            (68, 63),
        )
        self.assertFalse(clustering_explanation_required(a9))
        self.assertEqual(candidate_surface("E-PROD OFF+shadow EXT-100").base_seed, 142)

    def test_measurement_document_matches(self):
        text = (
            DOCS / "STAMINA_PRODUCTION_POLICY_ADOPTION_FIRST_MEASUREMENT.md"
        ).read_text(encoding="utf-8")
        for fragment in (
            f"p_candidate (pooled, unrounded)=64/69={self.a9.p_candidate!r}",
            "original-100 admissible clears at N=37 < 43",
            "pooled at N:             R=64, survived=5, censored=14, admissible=69",
            f"| candidate (pooled) | 69 | 64 | {self.a9.p_candidate!r} | 68 | 63 | "
            f"{self.a9.sensitivity.p_match!r} |",
        ):
            self.assertIn(fragment, text)
        for letter in "ABCDEFH":
            self.assertIn(f"| {self.gates[letter].letter} — ", text)


if __name__ == "__main__":
    unittest.main()
