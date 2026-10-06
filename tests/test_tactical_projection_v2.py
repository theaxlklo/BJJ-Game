"""Projection v2 mechanics (docs/TACTICAL_EVALUATOR_PROJECTION_V2_PREREGISTRATION.md,
binding at 5b57017).

Window ordering is pinned against the real runtime: on real baseline matches,
every continuation step started from a recorded real state must reproduce
the recorded real successor state exactly (advance), or contain it in its
exact support (exchange, opponent window). Small prefixes of the frozen
surfaces are used (match i uses seed base_seed + i).
"""
from contextlib import ExitStack
from dataclasses import fields
from fractions import Fraction
import random
import unittest
from unittest.mock import patch

from bjj_game.diagnostics import tactical_evaluator as stage1a
from bjj_game.diagnostics import tactical_evaluator_v2 as diag
from bjj_game.domain.model import Side
from bjj_game.engine.match import MountMatch
from bjj_game.interfaces import batch as batch_module
from bjj_game.interfaces import tactical_evaluator as te
from bjj_game.interfaces import tactical_projection_v2 as v2
from bjj_game.interfaces.batch import EscapeFirstInitiatorPolicy, run_escape_first_batch
from bjj_game.interfaces.handoff_policy import D3BTokenLockoutController
from bjj_game.diagnostics.stamina_adoption_verification import _match_gameplay_signature

MATCHES = 3
SURFACES = ("A-PROD", "B-PROD", "E-PROD 42 OFF", "E-PROD 42 ON", "PROTECT probe")


def record(name):
    """Real baseline run; per match an ordered list of (kind, branch, data):
    'start' = a decision window's state before any controller decision,
    'after' = the state after the window (attempt, reset or hold)."""
    kwargs = dict(stage1a.surfaces()[name], matches=MATCHES)
    created, logs, controllers = [], [], {}
    o_choose, o_attempt = EscapeFirstInitiatorPolicy.choose, MountMatch.attempt
    o_reset, o_hold = MountMatch.reset_window, MountMatch.recovery_hold
    o_decide, o_for = D3BTokenLockoutController.decide, batch_module.handoff_controller_for
    open_window: set = set()

    def idx(match):
        return next((i for i, m in enumerate(created) if m is match), None)

    def factory(*a, **k):
        match = MountMatch(*a, **k)
        created.append(match)
        logs.append([])
        return match

    def controller_for(mode, match):
        controllers[id(match)] = c = o_for(mode, match)
        return c

    def start(match):
        # One start per window, before any controller decision.
        i = idx(match)
        if i is not None and i not in open_window:
            open_window.add(i)
            logs[i].append(("start", v2.branch_of(match, controllers.get(id(match))), None))

    def decide(controller, match, *, armed):
        start(match)
        return o_decide(controller, match, armed=armed)

    def choose(policy, match):
        start(match)
        return o_choose(policy, match)

    def after(kind, original):
        def wrapped(match, *a, **k):
            i = idx(match)
            result = original(match, *a, **k)
            if i is not None:
                open_window.discard(i)
                logs[i].append((kind, v2.branch_of(match, controllers.get(id(match))),
                                (k.get("action_id"), k.get("commitment"), match.ended)))
            return result
        return wrapped

    with ExitStack() as stack:
        stack.enter_context(patch.object(batch_module, "MountMatch", factory))
        stack.enter_context(patch.object(batch_module, "handoff_controller_for", controller_for))
        stack.enter_context(patch.object(EscapeFirstInitiatorPolicy, "choose", choose))
        stack.enter_context(patch.object(D3BTokenLockoutController, "decide", decide))
        stack.enter_context(patch.object(MountMatch, "attempt", after("attempt", o_attempt)))
        stack.enter_context(patch.object(MountMatch, "reset_window", after("reset", o_reset)))
        stack.enter_context(patch.object(MountMatch, "recovery_hold", after("hold", o_hold)))
        run_escape_first_batch(**kwargs)
    return kwargs, created, logs


class ProjectionV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = {name: record(name) for name in SURFACES}

    def _windows(self, name):
        kwargs, created, logs = self.runs[name]
        context = v2.Context.from_batch_kwargs(kwargs)
        for m, log in enumerate(logs):
            cont = v2.Continuation(created[m], context)
            starts = [(i, e) for i, e in enumerate(log) if e[0] == "start"]
            for (i, s), nxt in zip(starts, starts[1:] + [(len(log), None)]):
                after = next((e for e in log[i + 1:nxt[0]] if e[0] != "start"), None)
                yield cont, s, after, nxt[1]

    def test_exchange_cases_equal_frozen_outcome_distribution(self):
        checked = 0
        for name in SURFACES:
            kwargs, created, logs = self.runs[name]
            model = v2.Context.from_batch_kwargs(kwargs).model
            for m, log in enumerate(logs):
                for kind, branch, _ in log[:40]:
                    if kind != "start":
                        continue
                    state = branch.state
                    for action_id in created[m].legal_action_ids(state.initiator):
                        for c in te.COMMITMENTS:
                            cases = v2.exchange_cases(created[m], model, state, action_id, c)
                            frozen = te.outcome_distribution(created[m], model, state, action_id, c)
                            self.assertEqual([w for w, *_ in cases], [w for w, *_ in frozen])
                            self.assertEqual([r for *_, r in cases], [o[3] for o in frozen])
                            checked += 1
        self.assertGreater(checked, 100)

    def test_advance_reproduces_the_runtime_exactly(self):
        """Between windows: behavior choice, advance() (drift, clock, flow,
        latch), D3-B observation and the post-advance re-choice, in runtime
        order, equal the real next window's starting state."""
        checked = 0
        for name in SURFACES:
            for cont, start, after, next_start in self._windows(name):
                if after is None or next_start is None or after[2][2]:
                    continue
                if next_start[1].clock == after[1].clock:
                    continue  # free initiative window: no advance in the runtime
                self.assertEqual(cont.advance(after[1]), next_start[1], name)
                checked += 1
        self.assertGreater(checked, 200)

    def test_exchange_support_contains_the_realized_state(self):
        checked = 0
        for name in SURFACES:
            for cont, start, after, _ in self._windows(name):
                if after is None or after[0] != "attempt" or after[2][2]:
                    continue
                action_id, requested, _ = after[2]
                if start[1].state.initiator is Side.BOTTOM and start[1].d3b is not None:
                    # The controller decided before the attempt; continue from
                    # its post-decision fields, exactly as the runtime.
                    _, _, _, controller = cont.opponent_decision(start[1])
                    origin = v2.Branch(start[1].state, start[1].clock,
                                       v2.controller_fields(controller))
                else:
                    origin = start[1]
                items, _ = cont.exchange(origin, action_id, requested)
                support = dict(items)
                self.assertIn(after[1], support, name)
                self.assertGreater(support[after[1]], 0)
                if name in ("A-PROD", "PROTECT probe") and start[1].state.initiator is Side.TOP:
                    self.assertEqual(len(support), 1)  # informed Bottom, no Recognition
                checked += 1
        self.assertGreater(checked, 200)

    def test_opponent_window_contains_the_realized_state(self):
        """O-3 on stalling-OFF surfaces: the real Bottom window (D3-B decision,
        policy, commitment, attempt / reset / hold) is in the exact support."""
        checked = 0
        for name in ("A-PROD", "B-PROD", "E-PROD 42 OFF", "PROTECT probe"):
            for cont, start, after, _ in self._windows(name):
                if (after is None or after[2][2]
                        or start[1].state.initiator is not Side.BOTTOM):
                    continue
                items, _ = cont.opponent(start[1])
                self.assertIn(after[1], dict(items), name)
                checked += 1
        self.assertGreater(checked, 100)

    def test_probability_is_conserved_and_branches_are_exact(self):
        for name in ("B-PROD", "E-PROD 42 ON"):
            kwargs, created, logs = self.runs[name]
            context = v2.Context.from_batch_kwargs(kwargs)
            cont = v2.Continuation(created[0], context)
            for kind, branch, _ in logs[0][:60]:
                if kind != "start" or branch.state.initiator is not Side.TOP:
                    continue
                for c in te.COMMITMENTS:
                    p = cont.project(branch, "mount.top.high_mount_climb", c)
                    if p is None:
                        continue
                    for _, w in p.setup_future_requested:
                        self.assertIsInstance(w, Fraction)
                    mass = sum((w for _, w in p.terminal_mass), Fraction(0))
                    self.assertLessEqual(p.ready_mass + mass, 1)
                    self.assertLessEqual(p.setup_future, p.ready_mass)

    def test_merge_key_covers_every_continuation_field(self):
        self.assertEqual([f.name for f in fields(v2.Branch)], ["state", "clock", "d3b"])
        self.assertEqual([f.name for f in fields(te.State)],
                         ["axis", "band", "initiator", "top_behavior", "bottom_behavior",
                          "top", "bottom", "ready", "tiers", "stage", "interval_seconds"])

    def test_projection_is_pure_and_depth_one(self):
        """No RNG, no live-match mutation, and no nested TE-1 evaluation."""
        kwargs, created, logs = self.runs["E-PROD 42 OFF"]
        match = created[0]
        before = _match_gameplay_signature(match)
        cont = v2.Continuation(match, v2.Context.from_batch_kwargs(kwargs))
        trace = stage1a.RngTrace()
        trace.active = True
        with stage1a.count_rng(trace), \
                patch.object(te, "evaluate", side_effect=AssertionError("nested TE-1")), \
                patch.object(te, "candidates", side_effect=AssertionError("nested TE-1")):
            for kind, branch, _ in logs[0][:80]:
                if kind == "start" and branch.state.initiator is Side.TOP:
                    for c in te.COMMITMENTS:
                        cont.project(branch, "mount.top.high_mount_climb", c)
        self.assertEqual(sum(trace.evaluator_draws.values()), 0)
        self.assertEqual(_match_gameplay_signature(match), before)

    def test_c5_population_is_every_chain_start(self):
        d = lambda t: dict(kind="decision", side="top", reason="setup", t=t)
        use = lambda ok: dict(kind="attempt", side="top", ready_use=True,
                              action="mount.top.americana_arm_isolation", threat_entry=ok)
        events = [d(5), d(15), use(False), d(35), d(45), use(True), d(65)]
        found = diag.chains(events)
        self.assertEqual([c["decisions"][0]["t"] for c in found], [5, 35, 65])
        self.assertEqual([c["converted"] for c in found], [False, True, False])
        self.assertIsNone(found[-1]["use"])

    def test_holdout_surfaces_are_frozen(self):
        s = diag.surfaces()
        self.assertEqual(s["A-PROD 4242"], {**stage1a.surfaces()["A-PROD"], "base_seed": 4242})
        self.assertEqual(s["B-PROD 4242"], {**stage1a.surfaces()["B-PROD"], "base_seed": 4242})
        for seed in (4242, 4342):
            for mode in ("OFF", "ON"):
                self.assertEqual(s[f"E-PROD {seed} {mode}"]["base_seed"], seed)
        self.assertEqual(set(diag.HOLDOUT_SURFACES) | set(stage1a.surfaces()), set(s))


if __name__ == "__main__":
    unittest.main()
