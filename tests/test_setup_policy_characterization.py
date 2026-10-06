import json
from pathlib import Path
import unittest
from unittest.mock import patch

from bjj_game.diagnostics import setup_policy as sp
from bjj_game.engine.match import MountMatch
from bjj_game.interfaces.batch import EscapeFirstInitiatorPolicy, run_escape_first_batch

EVIDENCE = (
    Path(__file__).resolve().parents[1]
    / "docs/evidence/setup_policy_characterization.json"
)


class SetupPolicyObserverTests(unittest.TestCase):
    def test_observer_is_inert_replayable_and_restored(self):
        originals = (EscapeFirstInitiatorPolicy.choose,
                     EscapeFirstInitiatorPolicy._setup_advance_probability,
                     MountMatch.attempt)
        for name in ("A-PROD", "E-PROD 42"):
            with self.subTest(surface=name):
                kwargs = sp.surfaces()[name]
                summary, timelines = sp.observe_batch(**kwargs)
                self.assertEqual(
                    (EscapeFirstInitiatorPolicy.choose,
                     EscapeFirstInitiatorPolicy._setup_advance_probability,
                     MountMatch.attempt),
                    originals,
                )
                self.assertEqual(summary, run_escape_first_batch(**kwargs))
                replay, replay_timelines = sp.observe_batch(**kwargs)
                self.assertEqual(timelines, replay_timelines)

    def test_wrappers_restore_after_exception(self):
        original = EscapeFirstInitiatorPolicy.choose
        with patch.object(sp, "run_escape_first_batch", side_effect=RuntimeError("probe")):
            with self.assertRaisesRegex(RuntimeError, "probe"):
                sp.observe_batch(**sp.surfaces()["A-PROD"])
        self.assertIs(EscapeFirstInitiatorPolicy.choose, original)

    def test_historical_debt_and_production_baselines_reproduce(self):
        protect = sp.characterize(*sp.observe_batch(
            **sp.surfaces()["v0.3a PROTECT probe (historical debt)"]))
        self.assertEqual((protect["top_completed_setup_builds"], protect["threat_matches"]),
                         (1768, 0))
        a = sp.characterize(*sp.observe_batch(**sp.surfaces()["A-PROD"]))
        self.assertEqual(a["threat_matches"], 78)
        calibration = a["ready_target_calibration"]
        key = "top:mount.top.americana_arm_isolation"
        # Without Recognition the informed-defender model is exact.
        self.assertEqual(calibration[f"{key}:informed_model_predicted_successes"],
                         calibration[f"{key}:actual_successes"])

    def test_committed_evidence_matches_characterization(self):
        recorded = json.loads(EVIDENCE.read_text())
        self.assertEqual(set(recorded), set(sp.surfaces()))
        for name, kwargs in sp.surfaces().items():
            with self.subTest(surface=name):
                self.assertEqual(
                    json.loads(json.dumps(sp.characterize(*sp.observe_batch(**kwargs)))),
                    recorded[name],
                )


if __name__ == "__main__":
    unittest.main()
