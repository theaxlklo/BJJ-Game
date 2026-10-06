"""Pins the frozen Stage 1A evidence (docs/TACTICAL_EVALUATOR_STAGE1A_RESULT.md):
re-running the shadow measurement reproduces the committed summary exactly.

The baseline RNG draw count and digest depend on the interpreter's internal
random.Random call structure, so they are compared within a run (observed vs
evaluator-free reference), never against the committed values."""
import json
from pathlib import Path
import unittest

from bjj_game.diagnostics import tactical_evaluator as diag

EVIDENCE = Path(__file__).resolve().parents[1] / diag.SUMMARY_EVIDENCE
_VERSION_DEPENDENT = ("baseline_rng_draws", "baseline_rng_draws_reference",
                      "baseline_rng_digest", "baseline_rng_digest_reference")


def _comparable(result: dict) -> dict:
    result = json.loads(json.dumps(result))
    for key in _VERSION_DEPENDENT:
        result["integrity"].pop(key)
    return result


class Stage1AEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recorded = json.loads(EVIDENCE.read_text())

    def test_recorded_rollup(self):
        recorded = self.recorded
        self.assertEqual(recorded["preregistration"], diag.PREREGISTRATION)
        self.assertEqual(set(recorded["surfaces"]), set(diag.surfaces()))
        self.assertTrue(recorded["integrity_ok"])
        for gate in ("C1", "C2", "C3", "C4"):
            statuses = [v[gate]["status"] for v in recorded["surfaces"].values()
                        if v[gate]["status"] != "N/A"]
            expected = ("FAIL" if "FAIL" in statuses else
                        "OPEN" if (not statuses or "OPEN" in statuses) else "PASS")
            self.assertEqual(recorded["gates"][gate], expected)

    def _check(self, name):
        result, _ = diag.measure_surface(name, diag.surfaces()[name])
        self.assertTrue(result["integrity"]["rng_sequence_identical"])
        self.assertEqual(_comparable(result), _comparable(self.recorded["surfaces"][name]))

    def test_a_prod(self):
        self._check("A-PROD")

    def test_b_prod(self):
        self._check("B-PROD")

    def test_e_prod_42_off(self):
        self._check("E-PROD 42 OFF")

    def test_e_prod_42_on(self):
        self._check("E-PROD 42 ON")

    def test_e_prod_142_off(self):
        self._check("E-PROD 142 OFF")

    def test_e_prod_142_on(self):
        self._check("E-PROD 142 ON")

    def test_protect_probe(self):
        self._check("PROTECT probe")


if __name__ == "__main__":
    unittest.main()
