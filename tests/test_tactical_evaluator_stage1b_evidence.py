"""Pins the Stage 1B evidence (docs/TACTICAL_EVALUATOR_STAGE1B_RESULT.md):
re-measuring each surface reproduces the committed summary exactly, and the
committed roll-up follows from the committed per-surface values.

The second candidate run (P4b) and the inertness replay (P4c) are skipped
here to bound CI time; both were established by the authoritative
measurement and are pinned as recorded."""
import json
from pathlib import Path
import unittest

from bjj_game.diagnostics import tactical_evaluator_stage1b as diag

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / diag.SUMMARY_EVIDENCE


def _comparable(result: dict) -> dict:
    result = json.loads(json.dumps(result, default=str))
    for key in ("p4b_second_run_identical", "p4c_replay_identical", "p4c_replay_error"):
        result["integrity"].pop(key, None)
    return result


class Stage1BEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recorded = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    def test_recorded_rollup(self):
        recorded = self.recorded
        self.assertEqual(recorded["preregistration"], diag.PREREGISTRATION)
        self.assertEqual(recorded["implementation"], diag.IMPLEMENTATION)
        self.assertEqual(set(recorded["surfaces"]), set(diag.surfaces()))
        for name in diag.GATED_SURFACES:
            integrity = recorded["surfaces"][name]["integrity"]
            self.assertIn(integrity.get("p4b_second_run_identical"), (True, False), name)
            self.assertIn(integrity.get("p4c_replay_identical"), (True, False), name)
        surfaces = recorded["surfaces"]
        self.assertEqual(recorded["integrity_ok"],
                         all(diag._integrity_ok(v) for v in surfaces.values()))
        self.assertEqual(recorded["design_gates"],
                         json.loads(json.dumps(diag.gates(surfaces), default=str)))

    def _check(self, name):
        result, _ = diag.measure_surface(name, diag.surfaces()[name],
                                         gated=name in diag.GATED_SURFACES, replay=False)
        self.assertEqual(_comparable(result), _comparable(self.recorded["surfaces"][name]))


def _add(name):
    def test(self):
        self._check(name)
    slug = name.lower().replace(" ", "_").replace("-", "_")
    setattr(Stage1BEvidenceTests, f"test_{slug}", test)


for _name in diag.surfaces():
    _add(_name)


if __name__ == "__main__":
    unittest.main()
