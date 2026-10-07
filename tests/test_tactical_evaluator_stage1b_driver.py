"""Stage 1B measurement driver (diagnostics/tactical_evaluator_stage1b.py):
its integrity checks detect what they claim to detect.

Synthetic fixtures only (non-canonical seeds >= 910_000, short clocks); no
frozen surface is run here and no outcome metric is asserted.
"""
from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import unittest

from bjj_game.diagnostics import tactical_evaluator_stage1b as d
from bjj_game.domain.action import Commitment
from bjj_game.interfaces import tactical_evaluator as te
from bjj_game.interfaces import tactical_policy as tp

from test_tactical_policy_stage1b import _d3b_shape

Z = Fraction(0)


def _value(action, requested, *, cost, terminal=Z, progress=Z, setup=Z, axis=Z,
           enters=False):
    return te.TacticalValue(
        action_id=action, requested=requested, effective=requested, terminal=terminal,
        progress=progress, setup_future=setup, axis_realized=axis, axis_raw=axis,
        stamina_cost=cost, enters_exhausted=enters, setup_advance=Z)


LOW, MED, HIGH = Commitment.LOW, Commitment.MEDIUM, Commitment.HIGH


class GuardViolationTests(unittest.TestCase):
    def test_terminal_entering_choice_must_be_strictly_better(self):
        safe = _value("a", LOW, cost=3, terminal=Fraction(1, 2))
        entering = _value("a", HIGH, cost=12, terminal=Fraction(1, 2), enters=True)
        better = _value("a", HIGH, cost=12, terminal=Fraction(3, 4), enters=True)
        self.assertEqual(d.guard_violation((safe, entering), te.ShadowChoice("terminal", entering)),
                         "AB_enters_exhausted_not_strictly_better")
        self.assertIsNone(d.guard_violation((safe, better), te.ShadowChoice("terminal", better)))

    def test_setup_and_position_choices_must_be_cheapest_qualifying(self):
        low = _value("b", LOW, cost=3, setup=Fraction(1, 3))
        med = _value("b", MED, cost=7, setup=Fraction(1, 2))
        self.assertEqual(d.guard_violation((low, med), te.ShadowChoice("setup", med)),
                         "CD_above_cheapest_qualifying")
        self.assertIsNone(d.guard_violation((low, med), te.ShadowChoice("setup", low)))
        pos_low = _value("c", LOW, cost=3, axis=Fraction(1, 4))
        pos_high = _value("c", HIGH, cost=12, axis=Fraction(1, 2))
        self.assertEqual(
            d.guard_violation((pos_low, pos_high), te.ShadowChoice("position", pos_high)),
            "CD_above_cheapest_qualifying")

    def test_te1_choices_on_synthetic_values_never_violate(self):
        values = (_value("a", LOW, cost=3, axis=Fraction(1, 4)),
                  _value("a", HIGH, cost=12, axis=Fraction(1, 2)),
                  _value("b", MED, cost=7, setup=Fraction(1, 5)))

        class _Match:
            @staticmethod
            def legal_action_ids(side=None):
                return ("a", "b")

        choice = te.choose_te1(_Match(), values)
        self.assertIsNone(d.guard_violation(values, choice))


class IntegrityDetectionTests(unittest.TestCase):
    """A corrupted tape must fail P4c; an evaluator RNG draw must count."""

    @classmethod
    def setUpClass(cls):
        cls.kwargs = _d3b_shape(matches=1, initial_clock=150, measure_stamina_economy=True)
        cls.obs, _ = d.observe(cls.kwargs, policy=d.TACTICAL)

    def test_clean_replay_is_identical(self):
        rep, _ = d.observe(self.kwargs, policy=d.TACTICAL, tape=self.obs.batch_run.tactical.tape)
        self.assertEqual(rep.batch_run.summary, self.obs.batch_run.summary)
        self.assertEqual(rep.trace.baseline_digest, self.obs.trace.baseline_digest)

    def test_flipped_executed_flag_desynchronizes(self):
        tape = list(self.obs.batch_run.tactical.tape)
        tape[0] = replace(tape[0], kind=tp.CallKind.COUNTERFACTUAL
                          if tape[0].kind is tp.CallKind.EXECUTED else tp.CallKind.EXECUTED)
        with self.assertRaises(tp.ReplayDesync):
            d.observe(self.kwargs, policy=d.TACTICAL, tape=tape)

    def test_truncated_tape_desynchronizes(self):
        with self.assertRaises(tp.ReplayDesync):
            d.observe(self.kwargs, policy=d.TACTICAL,
                      tape=self.obs.batch_run.tactical.tape[:-1])

    def test_evaluator_rng_draw_is_counted(self):
        import random
        original = tp.TacticalV1Policy._entry

        def drawing(policy, *args, **kwargs):
            random.Random(910_999).random()
            return original(policy, *args, **kwargs)

        from unittest import mock
        with mock.patch.object(tp.TacticalV1Policy, "_entry", drawing):
            obs, _ = d.observe(self.kwargs, policy=d.TACTICAL)
        self.assertGreater(sum(obs.trace.evaluator_draws.values()), 0)
        self.assertEqual(sum(self.obs.trace.evaluator_draws.values()), 0)

    def test_p3_counts_are_consistent(self):
        p3 = d._p3(self.obs, self.obs.batch_run)
        self.assertTrue(d._p3_ok(p3))
        broken = dict(p3, attempts_in_lockout_hold_window=1)
        self.assertFalse(d._p3_ok(broken))


if __name__ == "__main__":
    unittest.main()
