import json
from pathlib import Path
import unittest
from unittest.mock import patch

from bjj_game.diagnostics import r1_affordability as r1
from bjj_game.interfaces import batch as batch_module
from bjj_game.interfaces.batch import run_escape_first_batch

EVIDENCE = (
    Path(__file__).resolve().parents[1]
    / "docs/evidence/r1_affordability_characterization.json"
)


class R1ObserverTests(unittest.TestCase):
    def test_observer_is_inert_and_restored(self):
        original = batch_module._informed_bottom_response_id
        for name in ("A-PROD", "E-PROD 42"):
            with self.subTest(surface=name):
                kwargs = r1.production_surfaces()[name]
                summary, decisions = r1.observe_batch(**kwargs)
                self.assertIs(batch_module._informed_bottom_response_id, original)
                self.assertEqual(
                    summary,
                    run_escape_first_batch(**{**kwargs, "measure_stamina_economy": True}),
                )
                replay, replay_decisions = r1.observe_batch(**kwargs)
                self.assertEqual(decisions, replay_decisions)

    def test_wrapper_restores_after_exception(self):
        original = batch_module._informed_bottom_response_id
        with patch.object(r1, "run_escape_first_batch", side_effect=RuntimeError("probe")):
            with self.assertRaisesRegex(RuntimeError, "probe"):
                r1.observe_batch(**r1.production_surfaces()["A-PROD"])
        self.assertIs(batch_module._informed_bottom_response_id, original)

    def test_frozen_baselines_reproduce(self):
        a = r1.characterize(*r1.observe_batch(**r1.production_surfaces()["A-PROD"]))
        self.assertEqual((a["threat_matches"], a["threat_entries"], a["taps"]), (78, 1950, 0))
        self.assertEqual(a["holds_outside_known_path"], 0)
        self.assertEqual(a["paths"]["FINISH"]["projected_burden_unaffordable"], 78)
        self.assertEqual(a["paths"]["FINISH"]["projected_unaffordable_free_downgrade_exists"], 0)
        e = r1.characterize(*r1.observe_batch(**r1.production_surfaces()["E-PROD 42"]))
        self.assertEqual(e["additive_response_plus_hold"], 179)
        self.assertEqual(e["commitment_only_fundable_but_plus_hold_not"], 0)
        self.assertEqual(e["taps"], 5)

    def test_committed_evidence_matches_production_characterization(self):
        recorded = json.loads(EVIDENCE.read_text())["production"]
        for name, kwargs in r1.production_surfaces().items():
            with self.subTest(surface=name):
                self.assertEqual(
                    json.loads(json.dumps(r1.characterize(*r1.observe_batch(**kwargs)))),
                    recorded[name],
                )


if __name__ == "__main__":
    unittest.main()
