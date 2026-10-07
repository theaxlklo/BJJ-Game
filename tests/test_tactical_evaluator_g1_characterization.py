"""G1 characterization instruments (read-only diagnostics): the exact route
search and the trajectory reconstructions behave as preregistered
(docs/TACTICAL_EVALUATOR_G1_CHARACTERIZATION_PREREGISTRATION.md, section 6).

No acting policy is changed and no candidate gameplay is run: the candidate
trajectory is an inertness replay of the committed Stage 1B records."""
from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import json
from pathlib import Path
import unittest

from bjj_game.diagnostics import tactical_evaluator_g1_characterization as g
from bjj_game.diagnostics import tactical_evaluator as stage1a
from bjj_game.domain.model import Side
from bjj_game.domain.submission import SubmissionStage
from bjj_game.interfaces import tactical_evaluator as te
from bjj_game.interfaces import tactical_projection_v2 as v2

ROOT = Path(__file__).resolve().parents[1]


class RouteSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = g.make_template("A-PROD")
        cls.kwargs = g.kwargs_for("A-PROD")
        cls.search = g.RouteSearch(cls.template, cls.kwargs, "O-EF")

    def _opening(self):
        # The A-PROD opening state as reconstructed (window 0, Top to move).
        records = g._load_gz(str(ROOT / "docs/evidence/tactical_evaluator_stage1a_v2_records.json.gz"))
        base = g.reconstruct_baseline("A-PROD", records)
        return base["windows"][0][0].branch

    def test_success_and_horizon_zero(self):
        b = self._opening()
        solver = g.Solver(self.search, g.success)
        self.assertEqual(solver.value(b, 0, 0), 0)
        threat = replace(b, state=replace(b.state, stage=SubmissionStage.THREAT))
        self.assertEqual(g.Solver(self.search, g.success).value(threat, 0, 0), 1)

    def test_reset_passes_initiative_then_advances(self):
        b = self._opening()
        self.assertIs(b.state.initiator, Side.TOP)
        out = self.search.transitions(b, ("RESET", None))
        self.assertEqual(len(out), 1)
        w, after = out[0]
        self.assertEqual(w, 1)
        swapped = v2.Branch(replace(b.state, initiator=Side.BOTTOM), b.clock, b.d3b)
        self.assertEqual(after, self.search.cont.advance(swapped))

    def test_transition_weights_sum_to_one(self):
        b = self._opening()
        for option in self.search.options(b):
            self.assertEqual(sum(w for w, _ in self.search.transitions(b, option)), 1, option)

    def test_ready_use_value_equals_immediate_evaluator(self):
        """At a Ready, Bottom-latched state, Q_1 of the target use equals the
        frozen evaluator's progress (Threat entry from stage None)."""
        b = self._opening()
        s = b.state
        tiers = tuple((t, 2 if t == g.TARGET else n) for t, n in s.tiers)
        ready = replace(s, ready=s.ready | {g.TARGET}, tiers=tiers,
                        bottom=te.Pool(5, True, s.bottom.maximum))
        branch = v2.Branch(ready, b.clock, b.d3b)
        m = self.search.queries.load(branch)
        self.assertIn(g.TARGET, m.legal_action_ids(Side.TOP))
        for action, c in self.search.options(branch):
            if action != g.TARGET:
                continue
            expected = te.evaluate(m, self.search.context.model, ready, action, c,
                                   project=False).progress
            got = g.Solver(self.search, g.success).q(branch, (action, c), 0, 1)
            self.assertEqual(got, expected, c)

    def test_search_draws_no_rng_and_is_deterministic(self):
        b = self._opening()
        trace = stage1a.RngTrace()
        with stage1a.count_rng(trace):
            first = g.Solver(g.RouteSearch(self.template, self.kwargs, "O-TE1"), g.success)
            v1 = first.value(b, 0, 7)
            second = g.Solver(g.RouteSearch(self.template, self.kwargs, "O-TE1"), g.success)
            v2_ = second.value(b, 0, 7)
        self.assertEqual(trace.baseline_draws + sum(trace.evaluator_draws.values()), 0)
        self.assertEqual(v1, v2_)
        self.assertEqual(len(first.memo), len(second.memo))

    def test_budget_overflow_is_infeasible_not_approximated(self):
        b = self._opening()
        original = g.BUDGET_NODES
        g.BUDGET_NODES = 5
        try:
            with self.assertRaises(g.Infeasible):
                g.Solver(self.search, g.success).value(b, 0, 9)
        finally:
            g.BUDGET_NODES = original


class ReconstructionTests(unittest.TestCase):
    def test_candidate_replay_matches_committed_stage1b(self):
        records = g._load_gz(str(ROOT / "docs/evidence/tactical_evaluator_stage1b_records.json.gz"))
        summary = json.loads((ROOT / "docs/evidence/tactical_evaluator_stage1b.json")
                             .read_text(encoding="utf-8"))["surfaces"]
        for surface in g.SURFACES:
            c = g.reconstruct_candidate(surface, records, summary[surface])
            self.assertTrue(c["summary_identical"], surface)
            self.assertTrue(c["events_identical"], surface)

    def test_baseline_matches_frozen_and_committed(self):
        records = g._load_gz(str(ROOT / "docs/evidence/tactical_evaluator_stage1a_v2_records.json.gz"))
        for surface in g.SURFACES:
            b = g.reconstruct_baseline(surface, records)
            self.assertTrue(b["baseline_exact"], surface)
            self.assertTrue(b["events_identical"], surface)

    def test_frozen_inputs_unchanged(self):
        self.assertTrue(all(g.frozen_inputs_unchanged().values()))


if __name__ == "__main__":
    unittest.main()
