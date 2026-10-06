"""Pins the projection-error characterization evidence
(docs/TACTICAL_EVALUATOR_PROJECTION_CHARACTERIZATION.md): re-running the
read-only characterization reproduces the committed summary exactly, and the
Stage 1A evidence it re-analyses is untouched."""
import gzip
import hashlib
import json
from pathlib import Path
import unittest

from bjj_game.diagnostics import projection_characterization as pc
from bjj_game.diagnostics import tactical_evaluator as stage1a

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / pc.SUMMARY_EVIDENCE
# sha256 of the Stage 1A evidence as committed at 2d2778d (immutable).
STAGE1A_SUMMARY_SHA256 = "f8156b1f990d7ad7a8fae409576500b62b79e535e480e500730c5ab6984162fb"
STAGE1A_RECORDS_SHA256 = "999af9507ee99391824abc21ccf75a4954129afc6891003760ba39e302424b26"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ProjectionCharacterizationEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recorded = json.loads(EVIDENCE.read_text())
        with gzip.open(ROOT / pc.STAGE1A_RECORDS) as handle:
            cls.frozen = json.load(handle)

    def test_stage1a_evidence_unchanged(self):
        self.assertEqual(_sha(ROOT / stage1a.SUMMARY_EVIDENCE), STAGE1A_SUMMARY_SHA256)
        self.assertEqual(_sha(ROOT / stage1a.RECORDS_EVIDENCE), STAGE1A_RECORDS_SHA256)

    def test_recorded_rollup(self):
        self.assertEqual(self.recorded["stage1a_head"], pc.STAGE1A_HEAD)
        self.assertEqual(self.recorded["preregistration"], stage1a.PREREGISTRATION)
        self.assertEqual(set(self.recorded["surfaces"]), set(stage1a.surfaces()))
        self.assertTrue(self.recorded["integrity_ok"])

    def _check(self, name):
        result = pc.analyse_surface(name, stage1a.surfaces()[name], self.frozen[name])
        result.pop("rows")
        self.assertEqual(json.loads(json.dumps(result, sort_keys=True, default=str)),
                         self.recorded["surfaces"][name])

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
