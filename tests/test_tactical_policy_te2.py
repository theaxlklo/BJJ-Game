"""TE-2 implementation tests (docs/TACTICAL_EVALUATOR_TE2_PREREGISTRATION.md,
binding at 218f1c0ab94d6999abd06157876f48704e8ba6e1).

Synthetic fixtures only: seeds >= 910000 and short clocks. No frozen Stage 1B
surface is run under TACTICAL_V2, the fresh holdout seeds (685800, 23316) are
never run (685800 appears only in validation calls, which run nothing), and no
G or HG value is computed. The characterization-equivalence test reads the
development states of 3b08cea (A-PROD / PROTECT seed 42) and runs only the
route search on them."""
from __future__ import annotations

from dataclasses import fields, replace
from enum import Enum
from fractions import Fraction
from functools import lru_cache
import os
import random
import tempfile
import unittest
from unittest import mock

from bjj_game.diagnostics import tactical_evaluator as stage1a
from bjj_game.diagnostics import tactical_evaluator_g1_characterization as g1
from bjj_game.diagnostics.stamina_adoption_candidate import _surface_e_prod_kwargs
from bjj_game.diagnostics.stamina_adoption_verification import _match_gameplay_signature
from bjj_game.domain.action import Commitment
from bjj_game.domain.model import Band, Side
from bjj_game.engine.match import MountMatch
from bjj_game.engine.stalling import STALLING_THRESHOLD_SECONDS
from bjj_game.interfaces import batch as batch_module
from bjj_game.interfaces import tactical_evaluator as te
from bjj_game.interfaces import tactical_policy as tp
from bjj_game.interfaces import tactical_policy_v2 as tp2
from bjj_game.interfaces import tactical_projection_v2 as v2
from bjj_game.interfaces import tactical_route as route
from bjj_game.interfaces.batch import (
    BatchBehaviorMode,
    BatchInitiatorPolicy,
    BatchResponderMode,
    run_batch,
)
from bjj_game.interfaces.handoff_policy import PostClearHandoffMode
from bjj_game.interfaces.production_policy import PRODUCTION_STAMINA_RECOVERY_POLICY

import te2_harness as harness
from test_tactical_policy_stage1b import _a_shape, _d3b_shape, _settings

V2 = BatchInitiatorPolicy.TACTICAL_V2
V1 = BatchInitiatorPolicy.TACTICAL_V1
EF = BatchInitiatorPolicy.ESCAPE_FIRST
FRESH_HOLDOUTS = (685800, 23316)
Z = Fraction(0)
LOW, MED, HIGH = Commitment.LOW, Commitment.MEDIUM, Commitment.HIGH


def _e_stall(**overrides) -> dict:
    """E-PROD shape with v0.3b stalling ON and D3-B, at synthetic values."""
    kwargs = _surface_e_prod_kwargs(stalling=True, shadow=False, base_seed=910_200)
    kwargs.update(PRODUCTION_STAMINA_RECOVERY_POLICY.batch_settings(
        bottom_behavior_mode=kwargs["bottom_behavior_mode"]))
    kwargs.update(matches=3, measure_stamina_economy=False, measure_recovery_policy=False,
                  measure_reexhaustion_handoffs=False, measure_post_clear_handoff=True,
                  shadow_stalling=False, top_stamina=40, bottom_stamina=30, initial_clock=200)
    kwargs.update(overrides)
    return kwargs


def _a_stall(**overrides) -> dict:
    kwargs = _a_shape(matches=3, initial_clock=300, enable_v03b_stalling=True,
                      base_seed=910_300)
    kwargs.update(overrides)
    return kwargs


def _value(action, requested, *, cost, axis=Z, raw=None, enters=False):
    return te.TacticalValue(
        action_id=action, requested=requested, effective=requested, terminal=Z,
        progress=Z, setup_future=Z, axis_realized=axis,
        axis_raw=axis if raw is None else raw, stamina_cost=cost,
        enters_exhausted=enters, setup_advance=Z)


# ---------------------------------------------------------------------------
# Tier R selection (T3, T4)
# ---------------------------------------------------------------------------


class TierRSelectionTests(unittest.TestCase):
    order = {"a": 0, "b": 1}

    def test_positive_tie_action_beats_reset(self):
        a = _value("a", LOW, cost=3)
        q = {route.RESET: Fraction(1, 3), ("a", LOW): Fraction(1, 3)}
        choice = tp2.select_route([a], q, self.order)
        self.assertEqual(choice.option, ("a", LOW))

    def test_reset_with_strictly_greater_q_wins(self):
        a = _value("a", LOW, cost=3)
        q = {route.RESET: Fraction(1, 2), ("a", LOW): Fraction(1, 3)}
        self.assertEqual(tp2.select_route([a], q, self.order).option, route.RESET)

    def test_reset_wins_when_every_action_is_zero(self):
        a = _value("a", LOW, cost=3)
        q = {route.RESET: Fraction(1, 9), ("a", LOW): Z}
        self.assertEqual(tp2.select_route([a], q, self.order).option, route.RESET)

    def test_all_zero_tier_r_is_empty(self):
        a = _value("a", LOW, cost=3)
        self.assertIsNone(tp2.select_route([a], {route.RESET: Z, ("a", LOW): Z}, self.order))

    def test_non_reset_ties_follow_te1_ordering(self):
        cheap = _value("a", LOW, cost=3, axis=Fraction(1))
        better_axis = _value("b", MED, cost=7, axis=Fraction(2))
        q = {route.RESET: Z, ("a", LOW): Fraction(1, 2), ("b", MED): Fraction(1, 2)}
        self.assertEqual(tp2.select_route([cheap, better_axis], q, self.order).option,
                         ("b", MED))
        same_axis = _value("b", MED, cost=7, axis=Fraction(1))
        q = {route.RESET: Z, ("a", LOW): Fraction(1, 2), ("b", MED): Fraction(1, 2)}
        self.assertEqual(tp2.select_route([cheap, same_axis], q, self.order).option, ("a", LOW))
        low, high = _value("a", LOW, cost=3), _value("a", HIGH, cost=3)
        q = {route.RESET: Z, ("a", LOW): Fraction(1, 2), ("a", HIGH): Fraction(1, 2)}
        self.assertEqual(tp2.select_route([high, low], q, self.order).option, ("a", LOW))

    def test_stamina_guard_on_q(self):
        safe = _value("a", LOW, cost=3)
        entering = _value("a", HIGH, cost=12, enters=True)
        tie = {route.RESET: Z, ("a", LOW): Fraction(1, 3), ("a", HIGH): Fraction(1, 3)}
        self.assertEqual(tp2.select_route([safe, entering], tie, self.order).option, ("a", LOW))
        self.assertNotIn(entering, tp2.guard_admissible([safe, entering], tie))
        better = {route.RESET: Z, ("a", LOW): Fraction(1, 3), ("a", HIGH): Fraction(1, 2)}
        self.assertEqual(tp2.select_route([safe, entering], better, self.order).option,
                         ("a", HIGH))
        # An entering option alone (no non-entering commitment) is admissible.
        alone = {route.RESET: Z, ("a", HIGH): Fraction(1, 3)}
        self.assertEqual(tp2.select_route([entering], alone, self.order).option, ("a", HIGH))

    def test_frozen_horizon_constants(self):
        self.assertEqual((route.BASE_WINDOWS, route.BOUND_WINDOWS), (5, 13))
        self.assertEqual(route.PREREGISTRATION, "218f1c0ab94d6999abd06157876f48704e8ba6e1")
        self.assertEqual((route.DECISION_NODE_LIMIT, route.MATCH_MEMO_LIMIT,
                          route.RSS_LIMIT_BYTES), (3_000_000, 20_000_000, 16 * 1024 ** 3))


# ---------------------------------------------------------------------------
# Supported configurations (section 5, T7)
# ---------------------------------------------------------------------------


def _envelope(**overrides) -> dict:
    return {**tp.PROTECT_PROBE_ENVELOPE, **overrides}


def _perturbed(value):
    if isinstance(value, bool):
        return not value
    if isinstance(value, Enum):
        return next(m for m in type(value) if m is not value)
    if isinstance(value, int):
        return value + 1
    if isinstance(value, float):
        return value + 0.25
    raise TypeError(value)


class ValidationTests(unittest.TestCase):
    def test_protect_envelope_admitted_at_42_and_685800_only(self):
        for seed in (42, 685800):
            tp2.validate_tactical_v2(_envelope(base_seed=seed))   # runs nothing

    def test_third_protect_seed_rejected(self):
        for seed in (43, 4242, 23316, 910_123):
            with self.assertRaises(ValueError, msg=seed):
                tp2.validate_tactical_v2(_envelope(base_seed=seed))

    def test_every_single_argument_perturbation_rejected(self):
        for seed in (42, 685800):
            for key, value in tp.PROTECT_PROBE_ENVELOPE.items():
                if key in ("base_seed", "enable_v04_commitment_semantics"):
                    continue
                settings = _envelope(base_seed=seed, **{key: _perturbed(value)})
                with self.assertRaises(ValueError, msg=(seed, key)):
                    tp2.validate_tactical_v2(settings)

    def test_general_contract_equals_tactical_v1(self):
        ok = _settings(_a_shape())
        tp.validate_tactical_v1(ok)
        tp2.validate_tactical_v2(ok)
        for bad in (dict(bottom_responder_mode=BatchResponderMode.RANDOM),
                    dict(post_clear_handoff_mode=PostClearHandoffMode.V1E_PERSISTENT_CONSERVE_HOLD),
                    dict(enable_v02_setup=False, enable_v03_submissions=False)):
            settings = {**ok, **bad}
            with self.assertRaises(ValueError):
                tp.validate_tactical_v1(settings)
            with self.assertRaises(ValueError, msg=bad):
                tp2.validate_tactical_v2(settings)

    def test_tactical_v1_validator_unchanged_for_seed_685800(self):
        with self.assertRaises(ValueError):
            tp.validate_tactical_v1(_envelope(base_seed=685800))


# ---------------------------------------------------------------------------
# Route steps: full state, successors and stalling (section 4.1, T5)
# ---------------------------------------------------------------------------


class RouteStepExactnessTests(unittest.TestCase):
    def _check(self, kwargs, policy, expect):
        result, events, failures = harness.observe_steps(kwargs, policy)
        self.assertEqual(failures, [])
        kinds = {e[0] for e in events}
        self.assertTrue(set(expect) <= kinds, (expect, kinds))
        return events

    def test_stalling_on_attempt_loop_and_reset(self):
        self._check(_a_stall(), EF, {"attempt", "loop"})
        self._check(_e_stall(), EF, {"attempt", "loop", "reset_window"})

    def test_stalling_off_and_d3b_hold(self):
        self._check(_d3b_shape(initial_clock=200), V1, {"attempt", "reset_window",
                                                        "recovery_hold"})

    def test_stalling_on_d3b_hold(self):
        self._check(_e_stall(matches=3), V1, {"attempt", "loop", "recovery_hold"})

    def test_tactical_v2_trajectory(self):
        self._check(_a_stall(matches=1, initial_clock=150, base_seed=910_310), V2,
                    {"attempt", "loop"})

    def test_mutable_field_list_is_complete(self):
        """Every init=False MountMatch field except the history log is compared."""
        names = {f.name for f in fields(MountMatch) if not f.init}
        self.assertEqual(names - set(harness.MUTABLE_FIELDS), {"history"})
        self.assertIn("stalling_tracker", harness.MUTABLE_FIELDS)
        self.assertIn("free_initiative_pending", harness.MUTABLE_FIELDS)
        self.assertIn("free_initiative_beneficiary", harness.MUTABLE_FIELDS)

    def test_stalling_off_branch_has_no_stall_fields(self):
        m = MountMatch(**_engine_kwargs(stalling=False))
        self.assertIsNone(route.route_branch_of(m, None).stall)
        m = MountMatch(**_engine_kwargs(stalling=True))
        self.assertIsNotNone(route.route_branch_of(m, None).stall)


def _engine_kwargs(*, stalling: bool) -> dict:
    return dict(initial_clock=120, starting_axis=1.5, interval_seconds=5,
                enable_v02_setup=True, enable_v03_submissions=True,
                enable_v03b_stalling=stalling, enable_v04_commitment_semantics=True)


class _Found(Exception):
    def __init__(self, match):
        super().__init__("found")
        self.match = match


def _live_state(predicate, kwargs=None):
    """A live real stalling-ON match (the batch's own object, history intact),
    stopped before the first attempt whose pre-state satisfies predicate."""
    original = MountMatch.attempt
    real = set()

    def factory(*a, **k):
        m = MountMatch(*a, **k)
        real.add(id(m))
        return m

    def attempt(match, *a, **kw):
        if id(match) in real and predicate(match):
            raise _Found(match)
        return original(match, *a, **kw)

    try:
        with mock.patch.object(batch_module, "MountMatch", factory),                 mock.patch.object(MountMatch, "attempt", attempt):
            run_batch(initiator_policy=EF, **(kwargs or _a_stall(matches=8)))
    except _Found as found:
        return found.match
    return None


class StallingConsequenceTests(unittest.TestCase):
    """A live real match driven into each v0.3b reset consequence: the route
    step equals the real reset_window(), and the window loop honors a free
    initiative window (no advance)."""

    @classmethod
    def setUpClass(cls):
        cls.context = v2.Context.from_batch_kwargs({**_a_stall(), "initiator_policy": V1})

    def _find(self, predicate):
        m = _live_state(predicate)
        if m is None:
            self.fail("no synthetic state satisfies the precondition")
        return m

    @staticmethod
    def _offend(real, side, offenses):
        t = real.stalling_tracker
        t.clocks[side] = STALLING_THRESHOLD_SECONDS
        t.offenses[side] = offenses
        t.warned[side] = offenses > 0
        return real

    def _reset_matches(self, real):
        model = route.RouteModel(real, self.context, budget=route.RouteBudget(rss_bytes=None))
        rb = route.route_branch_of(real, None)
        got = model.reset(rb)[0][0]
        real.reset_window()
        self.assertEqual(got, route.route_branch_of(real, None))
        swapped = route.RouteBranch(
            v2.Branch(replace(rb.state, initiator=rb.state.initiator.opponent),
                      rb.branch.clock, rb.branch.d3b), rb.stall)
        self.assertNotEqual(got, swapped, "an initiative swap would miss the consequence")
        return model, got

    @staticmethod
    def _top_with_route(m):
        return m.initiator is Side.TOP and bool(m.progress_capable_action_ids())

    def test_warning_reset(self):
        real = self._offend(self._find(self._top_with_route), Side.TOP, 0)
        warnings = len(real.history.stalling_warning_history)
        _, got = self._reset_matches(real)
        self.assertEqual(len(real.history.stalling_warning_history), warnings + 1)
        self.assertEqual(got.stall[4], 1)          # Top offenses
        self.assertTrue(got.stall[2])              # Top warned
        self.assertEqual(got.stall[0], 0)          # Top clock restarted

    def test_penalty_reset(self):
        real = self._offend(self._find(
            lambda m: self._top_with_route(m)
            and m.band in (Band.STABLE, Band.STRONG, Band.LOCKED)), Side.TOP, 1)
        axis_before = real.axis
        penalties = len(real.history.stalling_penalty_history)
        _, got = self._reset_matches(real)
        self.assertEqual(len(real.history.stalling_penalty_history), penalties + 1)
        self.assertLess(got.state.axis, axis_before)
        self.assertEqual(got.stall[4], 2)

    def test_position_reset(self):
        real = self._offend(self._find(
            lambda m: self._top_with_route(m) and m.band in (Band.STRONG, Band.LOCKED)),
            Side.TOP, 2)
        resets = len(real.history.stalling_position_reset_history)
        _, got = self._reset_matches(real)
        self.assertEqual(len(real.history.stalling_position_reset_history), resets + 1)
        self.assertEqual(got.state.axis, 1.5)

    def test_free_initiative_window(self):
        real = self._offend(self._find(
            lambda m: m.initiator is Side.BOTTOM and m.band is Band.LOCKED
            and bool(m.progress_capable_action_ids())), Side.BOTTOM, 1)
        model, got = self._reset_matches(real)
        self.assertTrue(real.free_initiative_pending)
        self.assertEqual(got.stall[6:], (True, Side.TOP))
        # The window loop: a pending free window is consumed with no advance.
        clock = real.clock_seconds
        looped = model.window_loop(got)
        self.assertIs(real.consume_free_initiative_window(), Side.TOP)
        self.assertEqual(looped, route.route_branch_of(real, None))
        self.assertEqual(looped.branch.clock, clock)
        self.assertEqual(looped.stall[6:], (False, None))

    def test_stalling_paths_draw_no_rng(self):
        warning = self._offend(self._find(self._top_with_route), Side.TOP, 0)
        position = self._offend(self._find(
            lambda m: self._top_with_route(m) and m.band in (Band.STRONG, Band.LOCKED)),
            Side.TOP, 2)
        trace = stage1a.RngTrace()
        with stage1a.count_rng(trace):
            for real in (warning, position):
                model = route.RouteModel(real, self.context,
                                         budget=route.RouteBudget(rss_bytes=None))
                rb = model.reset(route.route_branch_of(real, None))[0][0]
                model.window_loop(rb)
        self.assertEqual(trace.baseline_draws + sum(trace.evaluator_draws.values()), 0)


# ---------------------------------------------------------------------------
# Stalling-off equivalence with the 3b08cea characterization instrument
# ---------------------------------------------------------------------------


@lru_cache(maxsize=None)
def _characterization_states():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    records = g1._load_gz(str(root / "docs/evidence/tactical_evaluator_stage1b_records.json.gz"))
    summary = json.loads((root / "docs/evidence/tactical_evaluator_stage1b.json")
                         .read_text(encoding="utf-8"))["surfaces"]
    v2_records = g1._load_gz(str(root / "docs/evidence/tactical_evaluator_stage1a_v2_records.json.gz"))
    out = {}
    for surface in g1.SURFACES:
        cand = g1.reconstruct_candidate(surface, records, summary[surface])
        base = g1.reconstruct_baseline(surface, v2_records)
        sets = g1.state_sets(surface, base, cand)
        states = []
        for name in ("S1", "S2", "S3"):
            for item in sets[name]:
                b = item["branch"]
                if b is not None and b not in states and b.state.initiator is Side.TOP:
                    states.append(b)
        out[surface] = tuple(states)
    return out


class CharacterizationEquivalenceTests(unittest.TestCase):
    def test_q_equals_3b08cea_instrument_on_every_characterization_state(self):
        checked = 0
        for surface, states in _characterization_states().items():
            kwargs = g1.kwargs_for(surface)
            template = g1.make_template(surface)
            context = v2.Context.from_batch_kwargs({**kwargs, "initiator_policy": V1})
            model = route.RouteModel(template, context, budget=route.RouteBudget(rss_bytes=None))
            for b in states:
                search = g1.RouteSearch(template, kwargs, "O-TE1")
                solver = g1.Solver(search, g1.success,
                                   quiescence=(5, 13, g1.unresolved_qb))
                expected = {o: solver.q(b, o, 0, 13) for o in search.options(b)}
                got = model.root_values(route.RouteBranch(b, None))
                self.assertEqual(set(got), set(expected), surface)
                for option, q in expected.items():
                    self.assertEqual(got[option], q, (surface, option))
                checked += 1
        self.assertEqual(checked, sum(len(s) for s in _characterization_states().values()))
        self.assertGreaterEqual(checked, 60)


# ---------------------------------------------------------------------------
# Policy integration (synthetic fixtures)
# ---------------------------------------------------------------------------


class _ProbeV2(tp2.TacticalV2Policy):
    """Checks purity and the Bottom = TE-1 contract at every call."""

    trace = None
    log = None

    def choose(self, match, *, handoff_decision, executed):
        before = _match_gameplay_signature(match)
        controller_before = v2.controller_fields(self._controller)
        global_state = random.getstate()
        self.trace.active = True
        try:
            selection = super().choose(match, handoff_decision=handoff_decision,
                                       executed=executed)
        finally:
            self.trace.active = False
        entry = self._tape[-1]
        independent = None
        if match.initiator is Side.TOP and entry.tier in ("terminal", "progress"):
            fresh = v2.Continuation(match, self.context)
            choice = te.choose_te1(match, v2.candidates(
                fresh, v2.branch_of(match, self._controller), selection.allowed))
            independent = (choice.tier, choice.value.action_id, choice.value.requested)
        if match.initiator is Side.BOTTOM:
            fresh = v2.Continuation(match, self.context)
            choice = te.choose_te1(match, v2.candidates(
                fresh, v2.branch_of(match, self._controller), selection.allowed))
            independent = (choice.tier,
                           choice.value.action_id if choice.value else None,
                           choice.value.requested if choice.value else None)
        self.log.append(dict(
            side=match.initiator, executed=executed, tier=entry.tier,
            decision=(entry.decision.action_id, entry.requested), independent=independent,
            pure=(_match_gameplay_signature(match) == before
                  and v2.controller_fields(self._controller) == controller_before
                  and random.getstate() == global_state)))
        return selection


def _probed(kwargs):
    holder = {}
    trace = stage1a.RngTrace()

    def factory(settings):
        context = v2.Context.from_batch_kwargs({**settings, "initiator_policy": V1})
        policy = _ProbeV2(context)
        policy.trace, policy.log = trace, []
        holder["policy"] = policy
        return policy

    with stage1a.count_rng(trace), mock.patch.object(tp2, "create_policy", factory):
        result = run_batch(initiator_policy=V2, **kwargs)
    return result, holder["policy"], trace


@lru_cache(maxsize=None)
def _d3b_run():
    return _probed(_d3b_shape(initial_clock=80))


@lru_cache(maxsize=None)
def _a_run():
    return _probed(_a_shape(matches=2, initial_clock=150))


class PolicyIntegrationTests(unittest.TestCase):
    def test_route_search_only_at_top_windows(self):
        for result, policy, _ in (_d3b_run(), _a_run()):
            self.assertEqual(policy._route.searches_by_side[Side.BOTTOM], 0)
            self.assertGreater(policy._route.searches_by_side[Side.TOP], 0)
            self.assertTrue(all(r.match_index is not None for r in policy.route_records))
            top_calls = sum(1 for e in policy.log if e["side"] is Side.TOP)
            self.assertEqual(len(policy.route_records), top_calls)

    def test_bottom_decisions_are_stage1b_te1(self):
        result, policy, _ = _d3b_run()
        bottom = [e for e in policy.log if e["side"] is Side.BOTTOM]
        self.assertTrue(bottom)
        for e in bottom:
            self.assertEqual((e["tier"], *e["decision"]), e["independent"])

    def test_counterfactual_calls_are_bottom_te1_and_replay(self):
        """D3-B LOCKOUT_HOLD collector calls under TACTICAL_V2: Bottom TE-1,
        never a route search, taped as counterfactual and replayed exactly.
        Test-only: Top's TE-2E decision is replaced by Stage 1B TE-1's Top
        choice (a TE-1 setup choice is labelled as a route choice) so that the
        stalling-ON D3-B fixture reaching holds stays cheap; the V2 dispatch,
        Bottom TE-1, tape and replay are the real code."""
        def top_reset(policy, match, branch, allowed):
            choice = te.choose_te1(match, v2.candidates(policy._continuation, branch, allowed))
            tier = "route" if choice.tier == "setup" else choice.tier
            return tier, choice.value, tp2.RouteRecord(policy._match_index, policy._calls,
                                                       tier, (), None, 0)

        kwargs = _e_stall(matches=3)
        log = []

        def factory(settings):
            context = v2.Context.from_batch_kwargs({**settings, "initiator_policy": V1})
            policy = _ProbeV2(context)
            policy.trace, policy.log = stage1a.RngTrace(), log
            return policy

        with mock.patch.object(tp2.TacticalV2Policy, "_te2e", top_reset),                 mock.patch.object(tp2, "create_policy", factory):
            first = run_batch(initiator_policy=V2, **kwargs)
        counterfactual = [e for e in log if not e["executed"]]
        self.assertTrue(counterfactual, "fixture reached no LOCKOUT_HOLD window")
        for e in counterfactual:
            self.assertIs(e["side"], Side.BOTTOM)
            self.assertEqual((e["tier"], *e["decision"]), e["independent"])
        taped = [x for x in first.tactical.tape if x.kind is tp.CallKind.COUNTERFACTUAL]
        self.assertEqual(len(taped), len(counterfactual))
        replayed = tp2.replay_batch(first.tactical.tape, **kwargs)
        self.assertEqual(replayed.summary, first.summary)
        self.assertEqual(replayed.tactical, first.tactical)

    def test_top_tiers_a_b_equal_te1(self):
        for result, policy, _ in (_d3b_run(), _a_run()):
            for e in policy.log:
                if e["side"] is Side.TOP:
                    self.assertIn(e["tier"], ("terminal", "progress", "route",
                                              "position", "reset"))

    def test_purity_and_zero_evaluator_rng(self):
        for result, policy, trace in (_d3b_run(), _a_run()):
            self.assertTrue(all(e["pure"] for e in policy.log))
            self.assertEqual(sum(trace.evaluator_draws.values()), 0)

    def test_deterministic_rerun_and_inertness_replay(self):
        kwargs = _a_shape(matches=2, initial_clock=150)
        first = run_batch(initiator_policy=V2, **kwargs)
        second = run_batch(initiator_policy=V2, **kwargs)
        self.assertEqual(first, second)
        replayed = tp2.replay_batch(first.tactical.tape, **kwargs)
        self.assertEqual(replayed.summary, first.summary)
        self.assertEqual(replayed.tactical, first.tactical)

    def test_corrupted_tape_desynchronizes(self):
        kwargs = _a_shape(matches=1, initial_clock=150)
        tape = list(run_batch(initiator_policy=V2, **kwargs).tactical.tape)
        with self.assertRaises(tp.ReplayDesync):
            tp2.replay_batch(tape[:-1], **kwargs)
        flipped = replace(tape[0], kind=tp.CallKind.COUNTERFACTUAL)
        with self.assertRaises(tp.ReplayDesync):
            tp2.replay_batch([flipped, *tape[1:]], **kwargs)

    def test_top_te1_tiers_a_b_match_choose_te1(self):
        """When TE-2E returns tier A or B, TE-1 on the same window returns the
        same tier, action and commitment."""
        checked = 0
        for result, policy, _ in (_d3b_run(), _a_run()):
            for e in policy.log:
                if e["side"] is Side.TOP and e["tier"] in ("terminal", "progress"):
                    self.assertEqual((e["tier"], *e["decision"]), e["independent"])
                    checked += 1
        self.assertGreater(checked, 0)


class BudgetTests(unittest.TestCase):
    def _run(self, budget):
        with mock.patch.object(tp2.TacticalV2Policy, "budget", budget):
            return run_batch(initiator_policy=V2, **_a_shape(matches=1, initial_clock=150))

    def test_decision_node_overflow_is_open(self):
        with self.assertRaises(route.RouteBudgetExceeded) as raised:
            self._run(route.RouteBudget(decision_nodes=3, rss_bytes=None))
        self.assertEqual(raised.exception.which, "decision_nodes")

    def test_match_memo_overflow_is_open(self):
        with self.assertRaises(route.RouteBudgetExceeded) as raised:
            self._run(route.RouteBudget(match_memo=2, rss_bytes=None))
        self.assertEqual(raised.exception.which, "match_memo")

    def test_rss_cap_is_open(self):
        with self.assertRaises(route.RouteBudgetExceeded) as raised:
            self._run(route.RouteBudget(rss_bytes=1))
        self.assertEqual(raised.exception.which, "rss")

    def test_rss_is_measurable_here(self):
        self.assertIsInstance(route.rss_bytes(), int)

    def test_one_measurement_process_at_a_time(self):
        with tempfile.TemporaryDirectory() as d:
            lock = os.path.join(d, "te2.lock")
            with route.exclusive_measurement(lock):
                with self.assertRaises(RuntimeError):
                    with route.exclusive_measurement(lock):
                        pass
            with route.exclusive_measurement(lock):
                pass


class EntryPointTests(unittest.TestCase):
    def test_v1_and_escape_first_paths_never_build_a_v2_policy(self):
        with mock.patch.object(tp2, "create_policy", side_effect=AssertionError):
            run_batch(initiator_policy=EF, **_a_shape(initial_clock=60))
            run_batch(initiator_policy=V1, **_a_shape(initial_clock=60))

    def test_v2_path_never_builds_a_v1_policy(self):
        with mock.patch.object(tp, "create_policy", side_effect=AssertionError):
            run_batch(initiator_policy=V2, **_a_shape(initial_clock=60))

    def test_v2_result_is_labelled(self):
        result = run_batch(initiator_policy=V2, **_a_shape(initial_clock=60))
        self.assertIs(result.initiator_policy, V2)
        self.assertIsNotNone(result.tactical)

    def test_no_fresh_holdout_seed_in_fixtures(self):
        for kwargs in (_a_shape(), _d3b_shape(), _a_stall(), _e_stall()):
            first = kwargs["base_seed"]
            self.assertGreaterEqual(first, 910_000)
            for seed in FRESH_HOLDOUTS:
                self.assertFalse(seed <= first + kwargs["matches"] <= seed + 99)


if __name__ == "__main__":
    unittest.main()
