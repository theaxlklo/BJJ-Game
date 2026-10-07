"""Stage 1B implementation tests: TACTICAL_V1 wiring (no measurement).

Pins docs/TACTICAL_EVALUATOR_STAGE1B_PREREGISTRATION.md (binding at
ae786af483d109785f172cb10a17170ece2ed241), section 2 and the instrumentation
of sections 5.1-5.3. Integration checks use synthetic fixtures only
(non-canonical seeds >= 910_000, short clocks, non-surface stamina) and assert
wiring invariants, never outcome metrics. No frozen Stage 1B surface
(A-PROD, B-PROD, E-PROD, PROTECT probe, holdouts) is run under TACTICAL_V1,
and no G1-G6 value is computed.
"""

from __future__ import annotations

import copy
from dataclasses import fields, replace
from enum import Enum
from functools import lru_cache
import inspect
import random
import unittest
from unittest import mock

from bjj_game.diagnostics import tactical_evaluator as stage1a
from bjj_game.diagnostics.d3b_promotion_reference import canonical_surface_kwargs
from bjj_game.diagnostics.setup_policy import historical_protect_probe_kwargs
from bjj_game.diagnostics.stamina_adoption_candidate import _surface_e_prod_kwargs
from bjj_game.diagnostics.stamina_adoption_verification import _match_gameplay_signature
from bjj_game.domain.action import Commitment
from bjj_game.domain.model import BottomBehavior, Side, TopBehavior
from bjj_game.engine.match import MountMatch
from bjj_game.engine.setup import MountSetupPolicy
from bjj_game.interfaces import batch as batch_module
from bjj_game.interfaces import tactical_evaluator as te
from bjj_game.interfaces import tactical_policy as tp
from bjj_game.interfaces import tactical_projection_v2 as v2
from bjj_game.interfaces.batch import (
    BatchBehaviorMode,
    BatchDecision,
    BatchInitiatorPolicy,
    BatchResponderMode,
    BatchRun,
    BatchSummary,
    run_batch,
    run_escape_first_batch,
)
from bjj_game.interfaces.handoff_policy import HandoffDecisionKind, PostClearHandoffMode
from bjj_game.interfaces.production_policy import PRODUCTION_STAMINA_RECOVERY_POLICY
from bjj_game.positions.mount.catalog import (
    BOTTOM_BRIDGE,
    TOP_AMERICANA_ARM_ISOLATION,
    TOP_HIGH_MOUNT_CLIMB,
)

TACTICAL = BatchInitiatorPolicy.TACTICAL_V1
ESCAPE_FIRST = BatchInitiatorPolicy.ESCAPE_FIRST


# ---------------------------------------------------------------------------
# Synthetic fixtures (never a frozen surface)
# ---------------------------------------------------------------------------


def _a_shape(**overrides) -> dict:
    """A-PROD shape (v0.4a, informed, MATCH, no D3-B) at synthetic values."""
    kwargs = canonical_surface_kwargs("A")
    kwargs.pop("measure_stamina_economy")
    kwargs.update(matches=1, base_seed=910_400, initial_clock=100,
                  top_stamina=90, bottom_stamina=90)
    kwargs.update(overrides)
    return kwargs


def _d3b_shape(**overrides) -> dict:
    """E-PROD shape (Recognition, RECOVER, production policy with D3-B) at
    synthetic values; reaches D3-B TOKEN and LOCKOUT_HOLD windows."""
    kwargs = _surface_e_prod_kwargs(stalling=False, shadow=False, base_seed=910_000)
    kwargs.update(PRODUCTION_STAMINA_RECOVERY_POLICY.batch_settings(
        bottom_behavior_mode=kwargs["bottom_behavior_mode"]))
    kwargs.update(matches=1, initial_clock=200, top_stamina=40, bottom_stamina=30,
                  measure_post_clear_handoff=True, measure_stamina_economy=False,
                  measure_recovery_policy=False, measure_reexhaustion_handoffs=False,
                  shadow_stalling=False)
    kwargs.update(overrides)
    return kwargs


def _settings(kwargs: dict) -> dict:
    """Every run_batch option except initiator_policy, defaults resolved."""
    params = inspect.signature(run_batch).parameters
    out = {name: p.default for name, p in params.items()
           if p.default is not inspect.Parameter.empty and name != "initiator_policy"}
    out.update(kwargs)
    return out


def _captured(kwargs: dict, **run_kwargs):
    created: list[MountMatch] = []

    def factory(*args, **factory_kwargs):
        match = MountMatch(*args, **factory_kwargs)
        created.append(match)
        return match

    with mock.patch.object(batch_module, "MountMatch", factory):
        result = run_batch(**kwargs, **run_kwargs)
    return result, tuple(_match_gameplay_signature(m) for m in created)


class _Probe(tp.TacticalV1Policy):
    """TACTICAL_V1 policy that checks every call: purity (live match,
    controller, global RNG, 0 batch RNG draws) and TE-1 equality against an
    independent recomputation with a fresh continuation."""

    trace: stage1a.RngTrace | None = None

    def __init__(self, context):
        super().__init__(context)
        self.calls: list[dict] = []

    def choose(self, match, *, handoff_decision, executed):
        before = copy.deepcopy(_match_gameplay_signature(match))
        controller_before = v2.controller_fields(self._controller)
        global_state = random.getstate()
        self.trace.active = True
        try:
            selection = super().choose(match, handoff_decision=handoff_decision,
                                       executed=executed)
        finally:
            self.trace.active = False
        record = dict(
            executed=executed, side=match.initiator, selection=selection,
            handoff=handoff_decision.kind if handoff_decision is not None else None,
            match_pure=_match_gameplay_signature(match) == before,
            controller_pure=v2.controller_fields(self._controller) == controller_before,
            global_rng_pure=random.getstate() == global_state,
        )
        fresh = v2.Continuation(match, self.context)
        choice = te.choose_te1(match, v2.candidates(
            fresh, v2.branch_of(match, self._controller), selection.allowed))
        record["independent"] = (
            choice.tier,
            choice.value.action_id if choice.value is not None else None,
            choice.value.requested if choice.value is not None else None,
        )
        self.calls.append(record)
        return selection


@lru_cache(maxsize=None)
def _probed_d3b_run():
    """(BatchRun, probe, trace, gameplay signatures) on the D3-B fixture."""
    holder = {}
    trace = stage1a.RngTrace()

    def factory(settings):
        context = v2.Context.from_batch_kwargs({**settings, "initiator_policy": TACTICAL})
        holder["probe"] = probe = _Probe(context)
        probe.trace = trace
        return probe

    with stage1a.count_rng(trace), mock.patch.object(tp, "create_policy", factory):
        result, signatures = _captured(_d3b_shape(), initiator_policy=TACTICAL)
    return result, holder["probe"], trace, signatures


@lru_cache(maxsize=None)
def _plain_d3b_run():
    return _captured(_d3b_shape(), initiator_policy=TACTICAL)


# ---------------------------------------------------------------------------
# Scripted policy for G4 (decision labels chosen by the test)
# ---------------------------------------------------------------------------


class _ScriptedBuilder(tp._RecordingPolicy):
    """Top: Ready Arm Isolation if Ready, else High Mount Climb labelled
    with `label`'s tier; Bottom: RESET. Logs (action, Ready-before, tier)."""

    label = "position"

    def __init__(self, context):
        super().__init__(context)
        self.log: list[list[tuple[str, bool, int]]] = []

    def start_match(self, **kwargs):
        super().start_match(**kwargs)
        self.log.append([])

    def _entry(self, match, *, kind, branch, allowed, forced_by):
        side, tier, action = match.initiator, "reset", None
        if side is Side.TOP:
            if match.setup_state.is_ready(TOP_AMERICANA_ARM_ISOLATION):
                tier, action = "progress", TOP_AMERICANA_ARM_ISOLATION
            elif TOP_HIGH_MOUNT_CLIMB in match.legal_action_ids(side):
                tier, action = self.label, TOP_HIGH_MOUNT_CLIMB
        if action is not None:
            self.log[-1].append((
                action, match.setup_state.is_ready(TOP_AMERICANA_ARM_ISOLATION),
                int(match.setup_state.tier(TOP_AMERICANA_ARM_ISOLATION))))
        decision = BatchDecision(action, tp.reason_for(side, tier), 0.0, 0.0, 0.0, 0.0)
        return tp.TapeEntry(
            match_index=self._match_index, call_index=self._calls, kind=kind, side=side,
            branch=branch, allowed=allowed, forced_by=forced_by, tier=tier,
            decision=decision, requested=allowed[0] if action is not None else None)


def _scripted_run(label: str, kwargs: dict, *, fail_every: int | None = None):
    holder = {}

    def factory(settings):
        context = v2.Context.from_batch_kwargs({**settings, "initiator_policy": TACTICAL})
        holder["policy"] = policy = _ScriptedBuilder(context)
        policy.label = label
        return policy

    original = MountSetupPolicy.setup_advances_from
    builder_calls = [0]

    def sometimes_absorbed(self, result):
        # Test-only: every `fail_every`-th builder attempt does not advance,
        # as when the Mount cap absorbs it.
        advances = original(self, result)
        if self.rule_for_builder(result.action_id) is None:
            return advances
        builder_calls[0] += 1
        return advances and builder_calls[0] % fail_every != 0

    with mock.patch.object(tp, "create_policy", factory):
        if fail_every is None:
            result = run_batch(initiator_policy=TACTICAL, **kwargs)
        else:
            with mock.patch.object(MountSetupPolicy, "setup_advances_from",
                                   sometimes_absorbed):
                result = run_batch(initiator_policy=TACTICAL, **kwargs)
    return result, holder["policy"].log


def _oracle(log) -> tuple[int, int, int, bool]:
    """(credited builder attempts, all not-Ready builder attempts, failed
    attempts inside credited chains, some chain left incomplete)."""
    credited = total = failed = 0
    incomplete = False
    for match in log:
        pending, pending_failed, previous_tier = 0, 0, None
        for action, ready, tier in match:
            if action == TOP_HIGH_MOUNT_CLIMB and not ready:
                total += 1
                pending += 1
                if previous_tier is not None and tier == previous_tier:
                    pending_failed += 1
                previous_tier = tier
            elif action == TOP_AMERICANA_ARM_ISOLATION and ready:
                credited += pending
                failed += pending_failed
                pending = pending_failed = 0
                previous_tier = None
        incomplete = incomplete or pending > 0
    return credited, total, failed, incomplete


# ---------------------------------------------------------------------------
# Default and entry points
# ---------------------------------------------------------------------------


class EntryPointTests(unittest.TestCase):
    def test_escape_first_signature_is_unchanged_and_run_batch_adds_only_the_option(self):
        legacy = inspect.signature(run_escape_first_batch).parameters
        new = inspect.signature(run_batch).parameters
        self.assertEqual(list(new)[-1], "initiator_policy")
        self.assertEqual(
            [(n, p.kind, p.default) for n, p in legacy.items()],
            [(n, p.kind, p.default) for n, p in new.items() if n != "initiator_policy"])
        self.assertNotIn("initiator_policy", legacy)
        self.assertIs(new["initiator_policy"].default, ESCAPE_FIRST)

    def test_escape_first_forwards_every_argument_unchanged(self):
        params = inspect.signature(run_escape_first_batch).parameters
        sentinels = {name: object() for name in params}
        seen = {}

        def capture(**kwargs):
            seen.update(kwargs)
            return BatchRun(summary="summary", initiator_policy=ESCAPE_FIRST,
                            top_completed_setup_builder_attempt_count=0)

        with mock.patch.object(batch_module, "run_batch", capture):
            self.assertEqual(run_escape_first_batch(**sentinels), "summary")
        self.assertIs(seen.pop("initiator_policy"), ESCAPE_FIRST)
        self.assertEqual(seen.keys(), sentinels.keys())
        for name in sentinels:
            self.assertIs(seen[name], sentinels[name], name)

    def test_batch_summary_carries_no_stage1b_field(self):
        names = {f.name for f in fields(BatchSummary)}
        self.assertNotIn("tactical", names)
        self.assertNotIn("initiator_policy", names)
        self.assertNotIn("top_completed_setup_builder_attempt_count", names)

    def test_escape_first_is_the_default_and_never_builds_a_tactical_policy(self):
        kwargs = _a_shape(initial_clock=60)
        with mock.patch.object(tp, "create_policy", side_effect=AssertionError):
            result = run_batch(**kwargs)
            explicit = run_batch(initiator_policy=ESCAPE_FIRST, **kwargs)
        self.assertIs(result.initiator_policy, ESCAPE_FIRST)
        self.assertIsNone(result.tactical)
        self.assertEqual(result, explicit)
        self.assertEqual(result.summary, run_escape_first_batch(**kwargs))

    def test_escape_first_rng_sequence_and_choose_calls_unchanged(self):
        kwargs = _d3b_shape(initial_clock=120)
        traces, calls = [], []
        original = batch_module.EscapeFirstInitiatorPolicy.choose

        def counted(policy, match):
            calls[-1] += 1
            return original(policy, match)

        for runner in (run_escape_first_batch, lambda **k: run_batch(**k).summary):
            trace = stage1a.RngTrace()
            calls.append(0)
            with stage1a.count_rng(trace), mock.patch.object(
                    batch_module.EscapeFirstInitiatorPolicy, "choose", counted):
                traces.append((runner(**kwargs), trace.baseline_digest, trace.baseline_draws))
        self.assertEqual(traces[0], traces[1])
        self.assertEqual(calls[0], calls[1])
        self.assertGreater(calls[0], 0)

    def test_unknown_policy_value_rejected(self):
        with self.assertRaises(ValueError):
            run_batch(initiator_policy="TACTICAL_V1", **_a_shape())


# ---------------------------------------------------------------------------
# Configuration contract (2.1, 9.1)
# ---------------------------------------------------------------------------


def _other(value):
    """A same-type value different from `value` (one-argument perturbation)."""
    if isinstance(value, bool):
        return not value
    if isinstance(value, Enum):
        return next(member for member in type(value) if member is not value)
    if isinstance(value, int):
        return value + 1
    if isinstance(value, float):
        return value + 0.25
    raise TypeError(value)


class ConfigurationContractTests(unittest.TestCase):
    def test_envelope_is_the_frozen_probe_with_every_other_default(self):
        self.assertEqual(tp.PROTECT_PROBE_ENVELOPE, _settings(historical_protect_probe_kwargs()))
        self.assertEqual(set(tp.PROTECT_PROBE_ENVELOPE),
                         set(inspect.signature(run_batch).parameters) - {"initiator_policy"})
        self.assertFalse(tp.PROTECT_PROBE_ENVELOPE["enable_v04_commitment_semantics"])

    def test_exact_frozen_envelope_accepted(self):
        tp.validate_tactical_v1(_settings(historical_protect_probe_kwargs()))
        tp.validate_tactical_v1(dict(tp.PROTECT_PROBE_ENVELOPE))

    def test_exact_frozen_envelope_passes_batch_validation_without_gameplay(self):
        class Reached(Exception):
            pass

        def no_match(*args, **kwargs):
            raise Reached

        with mock.patch.object(batch_module, "MountMatch", no_match):
            with self.assertRaises(Reached):
                run_batch(initiator_policy=TACTICAL, **historical_protect_probe_kwargs())

    def _perturbations(self):
        """Every single-argument perturbation that keeps v0.4a off, plus type
        perturbations of an equal value."""
        cases = []
        for key, value in tp.PROTECT_PROBE_ENVELOPE.items():
            if key == "enable_v04_commitment_semantics":
                continue  # turning v0.4a on leaves the v0.4a-off envelope
            cases.append((key, _other(value)))
        cases += [("matches", 100.0), ("interval_seconds", 5.0),
                  ("starting_axis", 3 / 2 + 1e-9), ("enable_v02_setup", 1)]
        return cases

    def test_every_v04a_off_perturbation_rejected(self):
        cases = self._perturbations()
        self.assertEqual(len(cases), 32)
        for key, value in cases:
            settings = {**tp.PROTECT_PROBE_ENVELOPE, key: value}
            with self.subTest(key=key, value=value):
                self.assertFalse(tp.is_protect_probe_envelope(settings))
                with self.assertRaises(ValueError):
                    tp.validate_tactical_v1(settings)

    def test_every_v04a_off_perturbation_rejected_by_the_batch_before_gameplay(self):
        for key, value in self._perturbations():
            kwargs = {**tp.PROTECT_PROBE_ENVELOPE, key: value}
            with self.subTest(key=key, value=value), mock.patch.object(
                    batch_module, "MountMatch", side_effect=AssertionError("ran")):
                with self.assertRaises(ValueError):
                    run_batch(initiator_policy=TACTICAL, **kwargs)

    def test_no_fallback_to_escape_first(self):
        kwargs = {**historical_protect_probe_kwargs(), "base_seed": 910_000}
        with mock.patch.object(batch_module.EscapeFirstInitiatorPolicy, "choose",
                               side_effect=AssertionError("fallback")):
            with self.assertRaises(ValueError):
                run_batch(initiator_policy=TACTICAL, **kwargs)

    def test_v04a_on_supported_shapes_accepted(self):
        for kwargs in (_a_shape(), canonical_surface_kwargs("B"), _d3b_shape(),
                       _d3b_shape(enable_v03b_stalling=True),
                       {**tp.PROTECT_PROBE_ENVELOPE, "enable_v04_commitment_semantics": True}):
            with self.subTest(kwargs=sorted(kwargs)):
                tp.validate_tactical_v1(_settings(kwargs))

    def test_v04a_on_unsupported_configurations_rejected(self):
        base = _a_shape()
        cases = {
            "no v0.3a": dict(enable_v03_submissions=False),
            "no v0.2 / v0.3a": dict(enable_v02_setup=False, enable_v03_submissions=False),
            "random Bottom responder": dict(bottom_responder_mode=BatchResponderMode.RANDOM),
            "v1e handoff": dict(post_clear_handoff_mode=PostClearHandoffMode.V1E_PERSISTENT_CONSERVE_HOLD),
            "interval off the behavior quantum": dict(interval_seconds=7),
        }
        for name, change in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(ValueError):
                    tp.validate_tactical_v1(_settings({**base, **change}))

    def test_v1e_rejected_by_the_batch(self):
        kwargs = _d3b_shape(post_clear_handoff_mode=PostClearHandoffMode.V1E_PERSISTENT_CONSERVE_HOLD)
        with mock.patch.object(batch_module, "MountMatch", side_effect=AssertionError("ran")):
            with self.assertRaises(ValueError):
                run_batch(initiator_policy=TACTICAL, **kwargs)

    def test_validation_requires_every_option(self):
        settings = dict(tp.PROTECT_PROBE_ENVELOPE)
        settings.pop("measure_stamina_economy")
        with self.assertRaises(ValueError):
            tp.validate_tactical_v1(settings)


# ---------------------------------------------------------------------------
# Reason mapping (2.1)
# ---------------------------------------------------------------------------


class ReasonMappingTests(unittest.TestCase):
    def test_exact_table(self):
        expected = {
            ("terminal", Side.TOP): "submission", ("terminal", Side.BOTTOM): "escape",
            ("progress", Side.TOP): "submission",
            ("setup", Side.TOP): "setup", ("setup", Side.BOTTOM): "setup",
            ("position", Side.TOP): "position", ("position", Side.BOTTOM): "position",
            ("reset", Side.TOP): "reset", ("reset", Side.BOTTOM): "reset",
        }
        for (tier, side), reason in expected.items():
            with self.subTest(tier=tier, side=side):
                self.assertEqual(tp.reason_for(side, tier), reason)

    def test_bottom_tier_b_is_a_contract_violation(self):
        with self.assertRaises(tp.TacticalContractError):
            tp.reason_for(Side.BOTTOM, "progress")
        value = te.TacticalValue(
            action_id=BOTTOM_BRIDGE, requested=Commitment.LOW, effective=Commitment.LOW,
            terminal=te.ZERO, progress=te.ZERO + 1, setup_future=te.ZERO,
            axis_realized=te.ZERO, axis_raw=te.ZERO, stamina_cost=3,
            enters_exhausted=False, setup_advance=te.ZERO)
        with self.assertRaises(tp.TacticalContractError):
            tp.decision_for(Side.BOTTOM, te.ShadowChoice("progress", value))

    def test_unknown_tier_and_inconsistent_reset_rejected(self):
        with self.assertRaises(tp.TacticalContractError):
            tp.reason_for(Side.TOP, "other")
        with self.assertRaises(tp.TacticalContractError):
            tp.decision_for(Side.TOP, te.ShadowChoice("position", None))

    def test_reset_decision(self):
        decision = tp.decision_for(Side.BOTTOM, te.ShadowChoice("reset", None))
        self.assertIsNone(decision.action_id)
        self.assertEqual(decision.reason, "reset")


# ---------------------------------------------------------------------------
# Wiring under real (synthetic) play
# ---------------------------------------------------------------------------


class WiringTests(unittest.TestCase):
    def setUp(self):
        self.result, self.probe, self.trace, self.signatures = _probed_d3b_run()
        self.tape = self.result.tactical.tape

    def test_fixture_exercises_both_sides_and_every_precedence_path(self):
        executed = [e for e in self.tape if e.kind is tp.CallKind.EXECUTED]
        self.assertEqual({e.side for e in executed}, {Side.TOP, Side.BOTTOM})
        sources = {x.source for x in self.result.tactical.exchanges}
        self.assertEqual(sources, {tp.CommitmentSource.TE1,
                                   tp.CommitmentSource.LOW_WHILE_EXHAUSTED,
                                   tp.CommitmentSource.D3B_TOKEN})
        kinds = {c["handoff"] for c in self.probe.calls}
        self.assertTrue({HandoffDecisionKind.TOKEN, HandoffDecisionKind.LOCKOUT_HOLD} <= kinds)
        self.assertTrue(any(e.kind is tp.CallKind.COUNTERFACTUAL for e in self.tape))
        tiers = {(e.side, e.tier) for e in executed}
        self.assertIn((Side.TOP, "setup"), tiers)
        self.assertIn((Side.BOTTOM, "position"), tiers)

    def test_both_initiators_use_te1_with_projection_v2(self):
        self.assertEqual(len(self.probe.calls), len(self.tape))
        for call in self.probe.calls:
            s = call["selection"]
            with self.subTest(side=call["side"], executed=call["executed"]):
                self.assertEqual((s.tier, s.decision.action_id, s.requested), call["independent"])
                self.assertEqual(s.decision.reason, tp.reason_for(call["side"], s.tier))

    def test_tape_records_every_call_in_order(self):
        for index, entry in enumerate(self.tape):
            self.assertEqual((entry.match_index, entry.call_index), (0, index))
        self.assertEqual([c["executed"] for c in self.probe.calls],
                         [e.kind is tp.CallKind.EXECUTED for e in self.tape])

    def test_evaluator_is_pure_and_draws_no_rng(self):
        self.assertEqual(sum(self.trace.evaluator_draws.values()), 0)
        self.assertGreater(self.trace.baseline_draws, 0)
        for call in self.probe.calls:
            with self.subTest(executed=call["executed"]):
                self.assertTrue(call["match_pure"])
                self.assertTrue(call["controller_pure"])
                self.assertTrue(call["global_rng_pure"])

    def test_counterfactual_calls_only_at_lockout_hold_and_pure(self):
        counterfactual = [c for c in self.probe.calls if not c["executed"]]
        self.assertTrue(counterfactual)
        for call in counterfactual:
            self.assertIs(call["handoff"], HandoffDecisionKind.LOCKOUT_HOLD)
            self.assertTrue(call["match_pure"] and call["controller_pure"])
        for call in self.probe.calls:
            if call["executed"]:
                self.assertIsNot(call["handoff"], HandoffDecisionKind.LOCKOUT_HOLD)

    def test_no_te1_gameplay_action_at_lockout_hold(self):
        events = [e for m in self.result.summary.post_clear_handoff.matches for e in m.events]
        locks = [i for i, e in enumerate(events)
                 if e["k"] == "win" and e.get("kind") == HandoffDecisionKind.LOCKOUT_HOLD.value]
        self.assertTrue(locks)
        for i in locks:
            self.assertEqual(events[i + 1]["k"], "hold")
        counterfactual = [e for e in self.tape if e.kind is tp.CallKind.COUNTERFACTUAL]
        self.assertEqual(len(counterfactual), len(locks))
        executed_actions = [e for e in self.tape
                            if e.kind is tp.CallKind.EXECUTED and e.decision.action_id is not None]
        self.assertEqual(len(self.result.tactical.exchanges), len(executed_actions))
        attempts = [e for e in events if e["k"] == "att"]
        self.assertEqual(len(attempts), len(executed_actions))

    def test_low_while_exhausted_and_d3b_token_preserved(self):
        events = [e for m in self.result.summary.post_clear_handoff.matches for e in m.events]
        exhausted_bottom = [e for e in events
                            if e["k"] == "att" and e["side"] == "bottom" and e["bx_before"]]
        self.assertTrue(exhausted_bottom)
        self.assertEqual({e["req"] for e in exhausted_bottom}, {"LOW"})
        for entry in self.tape:
            latched = entry.branch.state.bottom.latched
            if entry.side is Side.BOTTOM and latched:
                self.assertEqual(entry.allowed, (Commitment.LOW,))
                self.assertIn(entry.forced_by, (tp.CommitmentSource.LOW_WHILE_EXHAUSTED,
                                                tp.CommitmentSource.D3B_TOKEN))
                if entry.requested is not None:
                    self.assertIs(entry.requested, Commitment.LOW)
            else:
                self.assertEqual(entry.allowed, te.COMMITMENTS)
                self.assertIsNone(entry.forced_by)
        tokens = [c for c in self.probe.calls if c["handoff"] is HandoffDecisionKind.TOKEN]
        self.assertTrue(tokens)
        for call in tokens:
            self.assertIs(call["selection"].forced_by, tp.CommitmentSource.D3B_TOKEN)

    def test_executed_commitment_is_the_selection_or_the_forced_one(self):
        events = [e for m in self.result.summary.post_clear_handoff.matches for e in m.events]
        attempts = [e for e in events if e["k"] == "att"]
        exchanges = self.result.tactical.exchanges
        self.assertEqual([(a["side"], a["req"]) for a in attempts],
                         [(x.side.value, x.requested.value) for x in exchanges])

    def test_forced_commitment_never_overwritten(self):
        """Even if TE-1 somehow returned another commitment at a forced
        window, the batch must refuse rather than execute it."""
        original = tp.TacticalV1Policy._entry

        def disobedient(policy, match, **kwargs):
            entry = original(policy, match, **kwargs)
            if kwargs["forced_by"] is not None and entry.requested is not None:
                return replace(entry, requested=Commitment.HIGH)
            return entry

        with mock.patch.object(tp.TacticalV1Policy, "_entry", disobedient):
            with self.assertRaises(tp.TacticalContractError):
                run_batch(initiator_policy=TACTICAL, **_d3b_shape())

    def test_batch_cross_checks_precedence(self):
        with mock.patch.object(tp, "precedence", return_value=((Commitment.HIGH,),
                                                               tp.CommitmentSource.LOW_WHILE_EXHAUSTED)):
            with self.assertRaises(RuntimeError):
                run_batch(initiator_policy=TACTICAL, **_d3b_shape())

    def test_deterministic_rerun(self):
        result, signatures = _plain_d3b_run()
        self.assertEqual(result, self.result)
        self.assertEqual(signatures, self.signatures)

    def test_policy_rejects_calls_outside_its_match(self):
        context = v2.Context.from_batch_kwargs({**_d3b_shape(), "initiator_policy": TACTICAL})
        policy = tp.TacticalV1Policy(context)
        with self.assertRaises(RuntimeError):
            policy.choose(MountMatch(), handoff_decision=None, executed=True)
        with self.assertRaises(ValueError):
            tp.TacticalV1Policy(v2.Context.from_batch_kwargs(_d3b_shape()))


# ---------------------------------------------------------------------------
# O-3 under TACTICAL_V1 (2.2)
# ---------------------------------------------------------------------------


def _opening(kwargs: dict, initiative: Side = Side.TOP):
    match = MountMatch(
        initial_clock=kwargs["initial_clock"], starting_axis=kwargs["starting_axis"],
        interval_seconds=kwargs["interval_seconds"],
        enable_v02_setup=True, enable_v03_submissions=True,
        enable_v04_commitment_semantics=kwargs["enable_v04_commitment_semantics"],
        enable_v04b_recognition=kwargs.get("enable_v04b_recognition", False),
        enable_unfunded_responder_cost_waiver=kwargs.get(
            "enable_unfunded_responder_cost_waiver", False))
    match.top.stamina.set_current(kwargs["top_stamina"])
    match.bottom.stamina.set_current(kwargs["bottom_stamina"])
    match.set_behaviors(top=kwargs["top_behavior"], bottom=kwargs["bottom_behavior"])
    match.initiator = initiative
    return match


class OpponentWindowTests(unittest.TestCase):
    def _context(self, kwargs, policy=TACTICAL):
        return v2.Context.from_batch_kwargs({**kwargs, "initiator_policy": policy})

    def test_context_default_is_escape_first(self):
        self.assertIs(v2.Context.from_batch_kwargs(_a_shape()).initiator_policy, ESCAPE_FIRST)

    def test_opponent_window_is_te1_with_the_frozen_surrogate(self):
        for kwargs in (_a_shape(), _d3b_shape()):
            for side in Side:
                with self.subTest(side=side, recognition=kwargs.get("enable_v04b_recognition")):
                    live = _opening(kwargs, side)
                    branch = v2.branch_of(live, None)
                    cont = v2.Continuation(live, self._context(kwargs))
                    kind, action, requested, _ = cont.opponent_decision(branch)
                    model = self._context(kwargs).model
                    expected = te.choose_te1(live, te.candidates(live, model, te.State.of(live)))
                    self.assertIsNone(kind)
                    self.assertEqual(
                        (action, requested),
                        (expected.value.action_id, expected.value.requested)
                        if expected.value is not None else (None, None))

    def test_opponent_window_uses_frozen_projection_never_a_continuation(self):
        kwargs = _a_shape()
        live = _opening(kwargs, Side.BOTTOM)
        cont = v2.Continuation(live, self._context(kwargs))
        calls = {"frozen": 0, "continuation": 0}
        frozen, nested = te.project_setup, v2.Continuation.project

        def count_frozen(*a, **k):
            calls["frozen"] += 1
            return frozen(*a, **k)

        def count_nested(*a, **k):
            calls["continuation"] += 1
            return nested(*a, **k)

        with mock.patch.object(te, "project_setup", count_frozen), \
                mock.patch.object(v2.Continuation, "project", count_nested):
            cont.opponent_decision(v2.branch_of(live, None))
        self.assertGreater(calls["frozen"], 0)
        self.assertEqual(calls["continuation"], 0)

    def test_escape_first_context_keeps_the_real_escape_first_choice(self):
        kwargs = _a_shape()
        live = _opening(kwargs, Side.BOTTOM)
        cont = v2.Continuation(live, self._context(kwargs, ESCAPE_FIRST))
        with mock.patch.object(te, "choose_te1", side_effect=AssertionError("TE-1")):
            _, action, requested, _ = cont.opponent_decision(v2.branch_of(live, None))
        self.assertEqual(action, batch_module.EscapeFirstInitiatorPolicy().choose(live).action_id)
        self.assertIs(requested, kwargs["commitment"])

    def test_continuation_depth_is_exactly_one(self):
        kwargs = _a_shape()
        live = _opening(kwargs, Side.TOP)
        branch = v2.branch_of(live, None)
        cont = v2.Continuation(live, self._context(kwargs))
        original = te.candidates

        def recursing(*args, **kw):
            cont.project(branch, TOP_HIGH_MOUNT_CLIMB, Commitment.LOW)
            return original(*args, **kw)

        with mock.patch.object(te, "candidates", recursing):
            with self.assertRaisesRegex(RuntimeError, "nested continuation"):
                cont.project(branch, TOP_HIGH_MOUNT_CLIMB, Commitment.LOW)
        # The guard resets: an ordinary projection still works afterwards.
        self.assertIsNotNone(cont.project(branch, TOP_HIGH_MOUNT_CLIMB, Commitment.LOW))


# ---------------------------------------------------------------------------
# G4 (5.2) and G6 (5.3) instrumentation
# ---------------------------------------------------------------------------


class G4InstrumentationTests(unittest.TestCase):
    KWARGS = _a_shape(matches=2, initial_clock=100, bottom_behavior=BottomBehavior.PROTECT)

    def test_position_tier_builder_attempts_count(self):
        result, log = _scripted_run("position", self.KWARGS)
        credited, total, _, _ = _oracle(log)
        self.assertGreater(credited, 0)
        self.assertEqual(result.top_completed_setup_builder_attempt_count, credited)
        self.assertEqual(result.summary.top_completed_setup_build_count, 0)

    def test_setup_tier_builder_attempts_count_and_historical_counter_intact(self):
        result, log = _scripted_run("setup", self.KWARGS)
        credited, _, _, _ = _oracle(log)
        self.assertGreater(credited, 0)
        self.assertEqual(result.top_completed_setup_builder_attempt_count, credited)
        self.assertEqual(result.summary.top_completed_setup_build_count, credited)

    def test_failed_builder_attempts_count(self):
        for label in ("position", "setup"):
            with self.subTest(label=label):
                result, log = _scripted_run(label, self.KWARGS, fail_every=2)
                credited, _, failed, _ = _oracle(log)
                self.assertGreater(failed, 0)
                self.assertEqual(result.top_completed_setup_builder_attempt_count, credited)
                if label == "setup":
                    self.assertEqual(result.summary.top_completed_setup_build_count, credited)

    def test_incomplete_chains_not_credited(self):
        result, log = _scripted_run("position", self.KWARGS)
        credited, total, _, incomplete = _oracle(log)
        self.assertTrue(incomplete)
        self.assertLess(credited, total)
        self.assertEqual(result.top_completed_setup_builder_attempt_count, credited)

    def test_escape_first_counts_coincide_on_synthetic_baselines(self):
        for kwargs in (_a_shape(matches=2), _a_shape(matches=2, bottom_behavior=BottomBehavior.PROTECT),
                       _d3b_shape(matches=2, initial_clock=150)):
            with self.subTest(kwargs=kwargs.get("bottom_behavior")):
                result = run_batch(**kwargs)
                self.assertGreater(result.summary.top_completed_setup_build_count, 0)
                self.assertEqual(result.top_completed_setup_builder_attempt_count,
                                 result.summary.top_completed_setup_build_count)


def _exchange(side, requested, source=tp.CommitmentSource.TE1):
    return tp.InitiatorExchange(match_index=0, side=side, tier="position",
                                requested=requested, source=source)


class G6InstrumentationTests(unittest.TestCase):
    def test_tally_pools_sides_and_excludes_forced(self):
        low, med, high = Commitment.LOW, Commitment.MEDIUM, Commitment.HIGH
        exchanges = [
            _exchange(Side.TOP, high), _exchange(Side.TOP, low),
            _exchange(Side.BOTTOM, high), _exchange(Side.BOTTOM, med),
            _exchange(Side.BOTTOM, low, tp.CommitmentSource.LOW_WHILE_EXHAUSTED),
            _exchange(Side.BOTTOM, low, tp.CommitmentSource.D3B_TOKEN),
            _exchange(Side.BOTTOM, high, tp.CommitmentSource.HANDOFF_REQUESTED),
        ]
        tally = tp.g6_tally(exchanges)
        self.assertEqual((tally.te1_chosen, tally.high), (4, 2))
        self.assertEqual(dict(tally.excluded_forced),
                         {"LOW_WHILE_EXHAUSTED": 1, "D3B_TOKEN": 1, "HANDOFF_REQUESTED": 1})
        self.assertEqual(tally.by_side, (("top", 2, 1), ("bottom", 2, 1)))

    def test_tally_of_nothing(self):
        self.assertEqual(tp.g6_tally([]), tp.G6Tally(0, 0, (), (("top", 0, 0), ("bottom", 0, 0))))

    def test_run_records_every_exchange_with_its_source(self):
        result, probe, _, _ = _probed_d3b_run()
        exchanges = result.tactical.exchanges
        executed = [c for c in probe.calls
                    if c["executed"] and c["selection"].decision.action_id is not None]
        self.assertEqual(len(exchanges), len(executed))
        for exchange, call in zip(exchanges, executed):
            s = call["selection"]
            self.assertIs(exchange.side, call["side"])
            self.assertIs(exchange.source, s.forced_by or tp.CommitmentSource.TE1)
            self.assertIs(exchange.requested, s.requested)
        self.assertEqual({x.side for x in exchanges if x.source is tp.CommitmentSource.TE1},
                         {Side.TOP, Side.BOTTOM})


# ---------------------------------------------------------------------------
# Inertness replay (5.1)
# ---------------------------------------------------------------------------


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.kwargs = _d3b_shape()
        self.result, self.signatures = _plain_d3b_run()
        self.tape = self.result.tactical.tape

    def _replay(self, tape):
        with tp.replaying(tape):
            return _captured(self.kwargs, initiator_policy=TACTICAL)

    def test_replay_reproduces_the_run_without_evaluating(self):
        with mock.patch.object(v2, "candidates", side_effect=AssertionError("evaluated")), \
                mock.patch.object(te, "choose_te1", side_effect=AssertionError("evaluated")):
            result, signatures = self._replay(self.tape)
        self.assertEqual(result, self.result)
        self.assertEqual(signatures, self.signatures)

    def test_replay_batch_helper(self):
        self.assertEqual(tp.replay_batch(self.tape, **self.kwargs), self.result)

    def test_tape_holds_executed_and_counterfactual_calls(self):
        kinds = {e.kind for e in self.tape}
        self.assertEqual(kinds, {tp.CallKind.EXECUTED, tp.CallKind.COUNTERFACTUAL})

    def _desync(self, tape, code):
        with self.assertRaises(tp.ReplayDesync) as raised:
            self._replay(tape)
        self.assertEqual(raised.exception.code, code)

    def test_underflow_detected(self):
        self._desync(self.tape[:-1], "underflow")

    def test_leftover_detected(self):
        self._desync(self.tape + (self.tape[-1],), "leftover")

    def test_ordering_detected(self):
        tape = list(self.tape)
        tape[3], tape[4] = tape[4], tape[3]
        self._desync(tape, "order")
        shifted = [replace(e, match_index=1) if i == 2 else e for i, e in enumerate(self.tape)]
        self._desync(shifted, "order")

    def test_flag_mismatch_detected(self):
        index = next(i for i, e in enumerate(self.tape) if e.kind is tp.CallKind.COUNTERFACTUAL)
        tape = list(self.tape)
        tape[index] = replace(tape[index], kind=tp.CallKind.EXECUTED)
        self._desync(tape, "flag")

    def test_context_mismatch_detected(self):
        index = next(i for i, e in enumerate(self.tape) if e.forced_by is None)
        tape = list(self.tape)
        tape[index] = replace(tape[index], allowed=(Commitment.LOW,))
        self._desync(tape, "context")
        tape = list(self.tape)
        tape[index] = replace(tape[index], branch=replace(tape[index].branch,
                                                          clock=tape[index].branch.clock + 1))
        self._desync(tape, "context")

    def test_decision_mismatch_detected(self):
        index = next(i for i, e in enumerate(self.tape)
                     if e.side is Side.TOP and e.decision.action_id is not None)
        tape = list(self.tape)
        bad = replace(tape[index].decision, action_id=BOTTOM_BRIDGE)
        tape[index] = replace(tape[index], decision=bad)
        self._desync(tape, "decision")
        tape = list(self.tape)
        tape[index] = replace(tape[index], decision=replace(tape[index].decision, reason="escape"))
        self._desync(tape, "decision")

    def test_replay_context_is_scoped(self):
        with tp.replaying(self.tape):
            pass
        result, _ = _captured(self.kwargs, initiator_policy=TACTICAL)
        self.assertEqual(result, self.result)


if __name__ == "__main__":
    unittest.main()
