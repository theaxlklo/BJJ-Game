"""Pins the Stage 1A-v2 evidence (docs/TACTICAL_EVALUATOR_STAGE1A_V2_RESULT.md):
re-measuring each surface reproduces the committed summary exactly.

The second (replay) observed run is skipped here to bound CI time; replay
identity was established by the authoritative measurement and is pinned as
recorded."""
import json
from pathlib import Path
import unittest

from bjj_game.diagnostics import tactical_evaluator as stage1a
from bjj_game.diagnostics import tactical_evaluator_v2 as diag

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / diag.SUMMARY_EVIDENCE


def _comparable(result: dict) -> dict:
    result = json.loads(json.dumps(result))
    result["integrity"].pop("replay_identical")
    return result


class Stage1Av2EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recorded = json.loads(EVIDENCE.read_text())
        cls.stage1a = json.loads((ROOT / stage1a.SUMMARY_EVIDENCE).read_text())["surfaces"]

    def test_recorded_rollup(self):
        recorded = self.recorded
        self.assertEqual(recorded["preregistration"], diag.PREREGISTRATION)
        self.assertEqual(set(recorded["surfaces"]), set(diag.surfaces()))
        self.assertTrue(recorded["integrity_ok"])
        for name, v in recorded["surfaces"].items():
            self.assertTrue(v["integrity"]["replay_identical"], name)
        for gate in ("C1", "C2", "C3", "C4", "C5"):
            statuses = [v[gate]["status"] for n, v in recorded["surfaces"].items()
                        if n not in diag.HOLDOUT_SURFACES and v[gate]["status"] != "N/A"]
            expected = ("FAIL" if "FAIL" in statuses else
                        "OPEN" if (not statuses or "OPEN" in statuses) else "PASS")
            self.assertEqual(recorded["gates"][gate], expected)
        holdout = [recorded["surfaces"][n]["C3"]["status"] for n in diag.HOLDOUT_SURFACES]
        self.assertEqual(recorded["gates"]["C3-H"],
                         "FAIL" if "FAIL" in holdout else
                         "OPEN" if "OPEN" in holdout else "PASS")

    def _check(self, name):
        result, _ = diag.measure_surface(name, diag.surfaces()[name],
                                         self.stage1a.get(name), replay=False)
        self.assertEqual(_comparable(result), _comparable(self.recorded["surfaces"][name]))


def _add(name):
    def test(self):
        self._check(name)
    slug = name.lower().replace(" ", "_").replace("-", "_")
    setattr(Stage1Av2EvidenceTests, f"test_{slug}", test)


for _name in diag.surfaces():
    _add(_name)


if __name__ == "__main__":
    unittest.main()
