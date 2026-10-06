"""Mechanics of the projection-error characterization
(docs/TACTICAL_EVALUATOR_PROJECTION_CHARACTERIZATION.md).

Small prefixes of the frozen surfaces: match i of a batch uses seed
base_seed + i, so the first matches of a short batch are the first matches of
the frozen 100-match populations and compare to the committed Stage 1A records.
"""
import copy
import gzip
import json
from pathlib import Path
import unittest

from bjj_game.diagnostics import projection_characterization as pc
from bjj_game.diagnostics import tactical_evaluator as stage1a
from bjj_game.interfaces import tactical_evaluator as te
from bjj_game.interfaces.batch import run_escape_first_batch

ROOT = Path(__file__).resolve().parents[1]
MATCHES = 6


def _frozen(name):
    with gzip.open(ROOT / stage1a.RECORDS_EVIDENCE) as handle:
        return json.load(handle)[name]


class RecorderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = {}
        for name in ("A-PROD", "E-PROD 42 ON"):
            kwargs = dict(stage1a.surfaces()[name], matches=MATCHES)
            cls.runs[name] = (kwargs, pc.record_batch(**kwargs),
                              _frozen(name)["per_match"][:MATCHES])

    def test_recorder_is_inert(self):
        for name, (kwargs, (summary, signatures, _, _, trace), _) in self.runs.items():
            with self.subTest(name):
                _, ref_signatures, ref_trace = stage1a.baseline_reference(**kwargs)
                self.assertEqual(summary, run_escape_first_batch(**kwargs))
                self.assertEqual(signatures, ref_signatures)
                self.assertEqual(sum(trace.evaluator_draws.values()), 0)
                self.assertEqual(trace.baseline_digest, ref_trace.baseline_digest)
                self.assertEqual(trace.baseline_draws, ref_trace.baseline_draws)

    def test_identity_with_stage1a_records(self):
        for name, (_, (_, _, ops, _, _), frozen) in self.runs.items():
            with self.subTest(name):
                self.assertTrue(pc.identity(ops, frozen)["exact"])

    def test_identity_detects_a_changed_exchange(self):
        _, (_, _, ops, _, _), frozen = self.runs["A-PROD"]
        changed = copy.deepcopy(frozen)
        attempt = changed[0]["attempts"][0]
        attempt["realized_grade"] = "Strong Success" if attempt["realized_grade"] != \
            "Strong Success" else "Failure"
        self.assertEqual(pc.identity(ops, changed)["mismatched_matches"], [0])

    def test_components_sum_to_the_realized_change(self):
        checked = 0
        for _, (_, (_, _, ops, _, _), _) in self.runs.items():
            for m, match_ops in enumerate(ops):
                for iv in pc.intervals(match_ops, m):
                    if iv.use is None:
                        continue
                    c = pc.decompose(iv)["components"]
                    start, end = iv.decision["state"], iv.use["before"]
                    self.assertEqual(start.top.current + sum(
                        c.get(k, 0) for k in pc.STAMINA_COMPONENTS if k.startswith("top")),
                        end["top"])
                    self.assertEqual(start.bottom.current + sum(
                        c.get(k, 0) for k in pc.STAMINA_COMPONENTS if k.startswith("bottom")),
                        end["bottom"])
                    self.assertAlmostEqual(start.axis + sum(
                        c.get(k, 0) for k in pc.AXIS_COMPONENTS), end["axis"], places=9)
                    checked += 1
        self.assertGreater(checked, 0)

    def test_p0_is_the_frozen_projection_and_p6_is_the_use_state(self):
        checked = 0
        for name, (kwargs, (_, _, ops, matches, _), _) in self.runs.items():
            model = stage1a.model_for(kwargs)
            for m, match_ops in enumerate(ops):
                for iv in pc.intervals(match_ops, m):
                    if iv.use is None:
                        continue
                    lay = pc.layered(matches[m], model, iv, pc.decompose(iv))
                    for c in te.COMMITMENTS:
                        frozen = lay["frozen"][c].projection
                        p0 = lay["P0"][c]
                        self.assertEqual((p0["top"], p0["bottom"], p0["axis"], p0["band"],
                                          tuple(p0["use_values"]), p0["setup_future"]),
                                         (frozen.own, frozen.opponent, frozen.axis, frozen.band,
                                          frozen.use_values, frozen.setup_future))
                        p6, use = lay["P6"][c], iv.use["before"]
                        self.assertEqual((p6["top"].current, p6["top"].latched,
                                          p6["bottom"].current, p6["bottom"].latched,
                                          p6["band"]),
                                         (use["top"], use["top_latched"], use["bottom"],
                                          use["bottom_latched"], use["band"]))
                        self.assertAlmostEqual(p6["axis"], use["axis"], places=9)
                    checked += 1
        self.assertGreater(checked, 0)


if __name__ == "__main__":
    unittest.main()
