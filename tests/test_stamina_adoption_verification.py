from pathlib import Path
import unittest

from bjj_game.diagnostics.stamina_adoption_candidate import GateStatus
from bjj_game.diagnostics.stamina_adoption_verification import (
    SURFACES,
    _run_captured,
    adoption_state,
    adoption_verification_gates,
    canonical_equivalence,
    canonical_kwargs,
    effective_settings,
)
from bjj_game.interfaces.recovery_policy import RecoveryInitiationMode

DOCS = Path(__file__).resolve().parents[1] / "docs"


class CanonicalProductionAdoptionVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = {result.surface: result for result in canonical_equivalence()}
        cls.gates = {gate.letter: gate for gate in adoption_verification_gates()}

    def test_canonical_equals_measured_diagnostic_on_every_surface(self):
        self.assertEqual(tuple(self.results), SURFACES)
        for name, result in self.results.items():
            with self.subTest(surface=name):
                self.assertTrue(result.settings_equal)
                self.assertTrue(result.summary_equal)
                self.assertEqual(result.matches, 100)
                self.assertEqual(result.diverged_matches, 0)

    def test_all_gates_pass_and_slice_adopted(self):
        self.assertEqual(tuple(self.gates), tuple("ABCDEFGH"))
        for letter, gate in self.gates.items():
            self.assertIs(gate.status, GateStatus.PASS, gate.render())
        self.assertEqual(adoption_state(), "ADOPTED")

    def test_explicit_and_default_current_are_same_effective_setting(self):
        self.assertEqual(
            effective_settings({"recovery_initiation_mode": RecoveryInitiationMode.CURRENT}),
            effective_settings({}),
        )
        self.assertNotEqual(
            effective_settings(
                {"recovery_initiation_mode": RecoveryInitiationMode.LOW_WHILE_EXHAUSTED}
            ),
            effective_settings({}),
        )

    def test_gate_g_comparison_detects_a_different_policy(self):
        # Negative control: Rule 2 ON must not look equivalent.
        canonical = canonical_kwargs("E-PROD OFF+shadow")
        rule2 = {**canonical, "enable_supplemental_hold_settlement": True}
        canonical_summary, canonical_matches = _run_captured(canonical)
        rule2_summary, rule2_matches = _run_captured(rule2)
        self.assertNotEqual(effective_settings(canonical), effective_settings(rule2))
        self.assertNotEqual(canonical_summary, rule2_summary)
        self.assertGreater(
            sum(1 for left, right in zip(canonical_matches, rule2_matches) if left != right),
            0,
        )

    def test_verification_document_records_gate_g(self):
        text = (
            DOCS / "STAMINA_PRODUCTION_POLICY_ADOPTION_VERIFICATION.md"
        ).read_text(encoding="utf-8")
        self.assertIn("**ADOPTED (Gates A-H all PASS)", text)
        self.assertIn("| G — canonical equals measured | **PASS** |", text)
        self.assertIn("first Gate G evaluation: OPEN", text)


if __name__ == "__main__":
    unittest.main()
