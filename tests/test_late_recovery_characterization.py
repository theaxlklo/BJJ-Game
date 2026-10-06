import json
from pathlib import Path
import unittest
from unittest.mock import patch

from bjj_game.diagnostics import late_recovery as lr
from bjj_game.engine.match import MountMatch
from bjj_game.interfaces.batch import run_escape_first_batch

EVIDENCE = (
    Path(__file__).resolve().parents[1]
    / "docs/evidence/late_recovery_characterization.json"
)


class LateRecoveryObserverTests(unittest.TestCase):
    def test_observer_is_inert_replayable_and_restored(self):
        originals = {name: getattr(MountMatch, name)
                     for name in ("advance", "attempt", "reset_window")}
        kwargs = lr.production_runs()["E-PROD 42 OFF"]
        summary, timelines = lr.observe_batch(**kwargs)
        for name, original in originals.items():
            self.assertIs(getattr(MountMatch, name), original)
        self.assertEqual(
            summary,
            run_escape_first_batch(**{**kwargs, "measure_stamina_economy": True}),
        )
        replay, replay_timelines = lr.observe_batch(**kwargs)
        self.assertEqual(summary, replay)
        self.assertEqual(timelines, replay_timelines)

    def test_wrappers_restore_after_exception(self):
        original = MountMatch.attempt
        with patch.object(lr, "run_escape_first_batch", side_effect=RuntimeError("probe")):
            with self.assertRaisesRegex(RuntimeError, "probe"):
                lr.observe_batch(**lr.production_runs()["E-PROD 42 OFF"])
        self.assertIs(MountMatch.attempt, original)

    def test_bottom_stamina_fully_attributed_and_baseline_reproduced(self):
        report = lr.characterize(*lr.observe_batch(**lr.production_runs()["E-PROD 42 OFF"]))
        self.assertEqual(report["unexplained_bottom_delta"], 0)
        self.assertEqual(report["bottom_first_clear"]["n"], 45)
        self.assertEqual(report["bottom_first_clear"]["median"], 240)
        outcomes = report["outcomes"]
        self.assertEqual(sum(outcomes.get(name, 0) for name in lr.ESCAPES), 30)
        self.assertEqual(outcomes["TIMEOUT — Mount retained"], 65)
        self.assertEqual(outcomes["TAP — Americana"], 5)

    def test_committed_evidence_matches_characterization(self):
        recorded = json.loads(EVIDENCE.read_text())
        self.assertEqual(set(recorded), set(lr.production_runs()))
        for name, kwargs in lr.production_runs().items():
            with self.subTest(run=name):
                self.assertEqual(
                    json.loads(json.dumps(lr.characterize(*lr.observe_batch(**kwargs)))),
                    recorded[name],
                )


if __name__ == "__main__":
    unittest.main()
