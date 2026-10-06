"""Stage 1A mechanics tests for the pure tactical evaluator
(docs/TACTICAL_EVALUATOR_PREREGISTRATION.md, frozen at 4e61bad)."""
from collections import Counter
import copy
from fractions import Fraction
import inspect
import random
import unittest
from unittest.mock import patch

from bjj_game.diagnostics import tactical_evaluator as diag
from bjj_game.domain.action import Commitment
from bjj_game.domain.model import Band, BottomBehavior, Grade, Side, TopBehavior
from bjj_game.domain.stamina import StaminaBand, StaminaPool
from bjj_game.engine.match import MountMatch
from bjj_game.interfaces import batch as batch_module
from bjj_game.interfaces import blind
from bjj_game.interfaces import tactical_evaluator as te
from bjj_game.interfaces.batch import (
    BatchBehaviorMode,
    BatchResponseCommitmentMode,
    EscapeFirstInitiatorPolicy,
    run_escape_first_batch,
)
from bjj_game.interfaces.handoff_policy import D3BTokenLockoutController
from bjj_game.interfaces.recovery_policy import RecoveryInitiationMode
from bjj_game.positions.mount.catalog import (
    BOTTOM_BRIDGE,
    BOTTOM_ELBOW_KNEE_ESCAPE,
    BOTTOM_RESPONSE_FOREARM_FRAME,
    BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE,
    BOTTOM_RESPONSE_TURN_IN_RECOVERY,
    BOTTOM_TRAP_AND_ROLL_ESCAPE,
    TOP_AMERICANA_ARM_ISOLATION,
    TOP_AMERICANA_SUBMISSION_FINISH,
    TOP_CROSSFACE_PRESSURE,
    TOP_HIGH_MOUNT_CLIMB,
    TOP_RESPONSE_HIP_FOLLOW_REPUMMEL,
    TOP_RESPONSE_WIDE_MOUNT_BASE,
)

L, M, H = Commitment.LOW, Commitment.MEDIUM, Commitment.HIGH
INFORMED_MATCH = te.OpponentModel(bottom_informed=True,
                                  response_mode=BatchResponseCommitmentMode.MATCH,
                                  recognition=False)
INFORMED_RECOGNITION = te.OpponentModel(bottom_informed=True,
                                        response_mode=BatchResponseCommitmentMode.RECOGNITION,
                                        recognition=True)


def _match(**flags):
    base = dict(enable_v02_setup=True, enable_v03_submissions=True,
                enable_v04_commitment_semantics=True)
    base.update(flags)
    return MountMatch(**base)


def _state(*, axis=2.5, band=Band.STRONG, initiator=Side.TOP, top=100, bottom=100,
           ready=(), tiers=None, stage=None, top_behavior=TopBehavior.PRESSURE,
           bottom_behavior=BottomBehavior.ESCAPE):
    pool = lambda v: te.Pool(v, v <= 25)
    targets = (BOTTOM_TRAP_AND_ROLL_ESCAPE, TOP_AMERICANA_ARM_ISOLATION)
    tiers = tiers or {t: (2 if t in ready else 0) for t in targets}
    return te.State(axis=axis, band=band, initiator=initiator,
                    top_behavior=top_behavior, bottom_behavior=bottom_behavior,
                    top=pool(top), bottom=pool(bottom), ready=frozenset(ready),
                    tiers=tuple((t, tiers.get(t, 0)) for t in targets),
                    stage=stage, interval_seconds=5)


def _grades(outcomes):
    out = Counter()
    for w, result, _, _ in outcomes:
        out[result.final_grade] += w
    return dict(out)


def _live_states(name, matches=3, limit=150):
    """Capture (match copy, kwargs) just before real attempts on a short run.

    The live match is deep-copied (immutable policy objects shared) so the
    pre-exchange state can be replayed after the batch continues."""
    seen = []
    original = MountMatch.attempt

    def capture(match, *args, **kw):
        if len(seen) < limit:
            seen.append((_copy(match), dict(kw)))
        return original(match, *args, **kw)

    with patch.object(MountMatch, "attempt", capture):
        run_escape_first_batch(**{**diag.surfaces()[name], "matches": matches})
    return seen


def _copy(match):
    memo = {id(getattr(match, f)): getattr(match, f) for f in (
        "engine", "stamina_cost_policy", "behavior_stamina_policy", "exhaustion_policy",
        "recognition_policy", "setup_policy")}
    return copy.deepcopy(match, memo)


SURFACES = ("A-PROD", "B-PROD", "E-PROD 42 OFF", "E-PROD 142 ON", "PROTECT probe")


class CommitmentTransformTests(unittest.TestCase):
    def transform(self, grade, initiator, responder):
        return MountMatch._commitment_grade_transform(
            grade_after_exhaustion=grade, initiator_commitment=initiator,
            responder_commitment=responder)[0]

    def test_hand_computed_magnitude_and_undercommitment(self):
        G = Grade
        cases = [
            # (grade after exhaustion, initiator eff, responder eff) -> final
            (G.SUCCESS, H, H, G.STRONG_SUCCESS),         # HIGH: S -> SS
            (G.FAILURE, H, H, G.STRONG_FAILURE),         # HIGH: F -> SF
            (G.CONTESTED, H, H, G.CONTESTED),
            (G.STRONG_SUCCESS, L, L, G.SUCCESS),         # LOW: SS -> S
            (G.STRONG_FAILURE, L, L, G.FAILURE),         # LOW: SF -> F
            (G.SUCCESS, L, L, G.SUCCESS),
            (G.STRONG_SUCCESS, None, L, G.SUCCESS),      # UNFUNDED behaves as LOW
            (G.STRONG_FAILURE, None, None, G.FAILURE),
            (G.SUCCESS, M, M, G.SUCCESS),                # MEDIUM: no change
            (G.STRONG_FAILURE, M, M, G.STRONG_FAILURE),
            (G.CONTESTED, M, L, G.SUCCESS),              # undercommitment +1
            (G.CONTESTED, L, None, G.SUCCESS),           # UNFUNDED responder rank 0
            (G.CONTESTED, None, None, G.CONTESTED),      # equal rank 0: none
            (G.CONTESTED, L, M, G.CONTESTED),            # overcommitted responder
            # Order: magnitude first, then undercommitment.
            (G.CONTESTED, H, M, G.SUCCESS),              # reversed order would give SS
            (G.FAILURE, H, M, G.FAILURE),                # F->SF, +1 -> F (reversed: Contested)
            (G.STRONG_SUCCESS, L, None, G.STRONG_SUCCESS),  # SS->S, +1 -> SS
        ]
        for grade, ini, resp, expected in cases:
            with self.subTest(grade=grade, initiator=ini, responder=resp):
                self.assertEqual(self.transform(grade, ini, resp), expected)

    def test_resolve_applies_exhaustion_before_commitment(self):
        # Top Exhausted (2 stamina, UNFUNDED): Ready Arm Isolation vs Turn-in
        # Recovery is Contested by override, -1 exhaustion -> Failure; LOW
        # magnitude does not touch Failure; MATCH responder LOW (rank 1) is
        # not under UNFUNDED (rank 0).
        match = _match()
        state = _state(top=2, ready=(TOP_AMERICANA_ARM_ISOLATION,))
        result = te.resolve(match, state, TOP_AMERICANA_ARM_ISOLATION,
                            BOTTOM_RESPONSE_TURN_IN_RECOVERY, None, L)
        self.assertEqual(result.final_grade, Grade.FAILURE)


class FundingTests(unittest.TestCase):
    def test_requested_to_effective_is_exact(self):
        match = _match()
        for stamina in range(0, 20):
            for requested in te.COMMITMENTS:
                expected = (None if stamina < 3 else
                            L if stamina < 7 or requested is L else
                            M if stamina < 12 or requested is M else H)
                with self.subTest(stamina=stamina, requested=requested):
                    self.assertIs(te.funded(match, requested, stamina), expected)
                    self.assertIs(te.funded(match, requested, stamina),
                                  match.stamina_cost_policy.effective_commitment(
                                      requested=requested, available_stamina=stamina))

    def test_value_reports_effective_cost_and_drops_duplicate_requests(self):
        match = _match()
        state = _state(top=9)  # MEDIUM funds; HIGH downgrades to MEDIUM
        values = te.candidates(match, INFORMED_MATCH, state)
        climb = [v for v in values if v.action_id == TOP_HIGH_MOUNT_CLIMB]
        self.assertEqual([(v.requested, v.effective, v.stamina_cost) for v in climb],
                         [(L, L, 3), (M, M, 7)])
        state = _state(top=2)  # everything UNFUNDED: only LOW kept
        climb = [v for v in te.candidates(match, INFORMED_MATCH, state)
                 if v.action_id == TOP_HIGH_MOUNT_CLIMB]
        self.assertEqual([(v.requested, v.effective, v.stamina_cost) for v in climb],
                         [(L, None, 0)])

    def test_enters_exhausted_flag(self):
        match = _match()
        self.assertTrue(te.evaluate(match, INFORMED_MATCH, _state(top=32),
                                    TOP_HIGH_MOUNT_CLIMB, M).enters_exhausted)   # 32-7=25
        self.assertFalse(te.evaluate(match, INFORMED_MATCH, _state(top=33),
                                     TOP_HIGH_MOUNT_CLIMB, M).enters_exhausted)  # 26
        self.assertFalse(te.evaluate(match, INFORMED_MATCH, _state(top=20),
                                     TOP_HIGH_MOUNT_CLIMB, L).enters_exhausted)  # latched


class HandComputedOpponentModelTests(unittest.TestCase):
    def test_informed_bottom_ready_isolation_without_recognition(self):
        match = _match()
        ready = (TOP_AMERICANA_ARM_ISOLATION,)
        value = lambda c, **kw: te.evaluate(match, INFORMED_MATCH, _state(ready=ready, **kw),
                                            TOP_AMERICANA_ARM_ISOLATION, c)
        # Fresh vs fresh: Bottom matches and takes the Contested stalemate.
        self.assertEqual([value(c).progress for c in te.COMMITMENTS], [0, 0, 0])
        # Bottom alone Exhausted (+1): Contested -> Success at every commitment.
        self.assertEqual([value(c, bottom=5).progress for c in te.COMMITMENTS], [1, 1, 1])
        # Both Exhausted (net 0). Top 20 funds every level; Bottom 5 funds only
        # LOW, so MATCH MEDIUM/HIGH is undercommitted -> +1 -> Success.
        self.assertEqual([value(c, top=20, bottom=5).progress for c in te.COMMITMENTS], [0, 1, 1])
        # Bottom 2: the UNFUNDED response (rank 0) is under even Top LOW.
        self.assertEqual([value(c, top=20, bottom=2).progress for c in te.COMMITMENTS], [1, 1, 1])
        # Band Stable: Threat entry needs Strong/Locked.
        self.assertEqual(value(H, top=20, bottom=5, axis=1.5, band=Band.STABLE).progress, 0)

    def test_informed_bottom_commitment_order_is_observable(self):
        # Informed Bottom, FIXED_MEDIUM response, Top HIGH climb at Strong:
        # Frame S->SS(+1 clamp), Turn-in C->S, Tight elbow F->SF->F. Minimum
        # is Failure (Tight elbow). Undercommitment-first would give Contested.
        model = te.OpponentModel(True, BatchResponseCommitmentMode.FIXED_MEDIUM, False)
        outcomes = te.outcome_distribution(_match(), model, _state(), TOP_HIGH_MOUNT_CLIMB, H)
        self.assertEqual(_grades(outcomes), {Grade.FAILURE: 1})
        self.assertEqual(outcomes[0][3], BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE)

    def test_random_blind_bottom_high_and_low_magnitude(self):
        # Random-blind Bottom (Frame 4, Tight elbow 3), FIXED_MEDIUM response.
        model = te.OpponentModel(False, BatchResponseCommitmentMode.FIXED_MEDIUM, False)
        match, state = _match(), _state()
        high = te.evaluate(match, model, state, TOP_CROSSFACE_PRESSURE, H)
        # Frame: F -> SF -> +1 -> F ; Tight elbow: SS -> SS -> +1 clamp SS.
        self.assertEqual(_grades(te.outcome_distribution(match, model, state, TOP_CROSSFACE_PRESSURE, H)),
                         {Grade.FAILURE: Fraction(4, 7), Grade.STRONG_SUCCESS: Fraction(3, 7)})
        self.assertEqual(high.axis_raw, Fraction(2, 7))
        # LOW: Frame F stays F; Tight elbow SS -> S. No undercommitment.
        low = te.evaluate(match, model, state, TOP_CROSSFACE_PRESSURE, L)
        self.assertEqual(low.axis_raw, Fraction(-1, 7))

    def test_recognition_ready_isolation_hand_computed(self):
        match = _match(enable_v04b_recognition=True)
        state = _state(ready=(TOP_AMERICANA_ARM_ISOLATION,))
        value = lambda c: te.evaluate(match, INFORMED_RECOGNITION, state,
                                      TOP_AMERICANA_ARM_ISOLATION, c).progress
        # HIGH: only a capability under-read (roll 1, 1/6) makes Bottom answer
        # MEDIUM, under true HIGH -> +1 -> Success.
        self.assertEqual(value(H), Fraction(1, 6))
        # MEDIUM: Bottom answers LOW when intent reads LOW (1/6) or capability
        # reads LOW (5/6 * 1/6): 11/36.
        self.assertEqual(value(M), Fraction(11, 36))
        # LOW: trusted LOW whenever intent reads LOW; otherwise capability
        # LOW/UNFUNDED -> LOW or MEDIUM: never under LOW.
        self.assertEqual(value(L), 0)

    def test_recognition_response_commitment_distribution(self):
        match = _match(enable_v04b_recognition=True)
        dist = Counter()
        for w, read in te.recognition_cases(match, INFORMED_RECOGNITION, M, M):
            for c, wc in te.response_commitment(BatchResponseCommitmentMode.RECOGNITION, M, read):
                dist[c] += w * wc
        self.assertEqual(dict(dist), {L: Fraction(11, 36), M: Fraction(20, 36), H: Fraction(5, 36)})

    def test_recognition_under_accurate_over_reads(self):
        policy = _match(enable_v04b_recognition=True).recognition_policy
        read = lambda req, eff, i, k: (lambda r: (r.perceived_requested, r.perceived_effective))(
            policy.read(requested=req, effective=eff, intent_roll=i, capability_roll=k))
        self.assertEqual(read(M, M, 1, 1), (L, L))      # under-read both
        self.assertEqual(read(M, M, 3, 4), (M, M))      # accurate
        self.assertEqual(read(M, M, 6, 6), (H, H))      # over-read both
        self.assertEqual(read(L, None, 1, 1), (L, None))  # clamped at the bottom
        self.assertEqual(read(L, None, 6, 6), (M, L))
        self.assertEqual(read(H, H, 6, 6), (H, H))      # clamped at the top
        self.assertEqual(read(H, M, 2, 1), (H, L))      # downgraded truth read low

    def test_random_blind_top_weights(self):
        match = _match()
        model = INFORMED_MATCH  # Bottom initiator: Top stays random-blind
        state = _state(initiator=Side.BOTTOM, axis=1.5, band=Band.STABLE)
        bridge = te.outcome_distribution(match, model, state, BOTTOM_BRIDGE, M)
        self.assertEqual({rid: w for w, _, _, rid in bridge},
                         {TOP_RESPONSE_WIDE_MOUNT_BASE: Fraction(2, 3),
                          TOP_RESPONSE_HIP_FOLLOW_REPUMMEL: Fraction(1, 3)})
        ready = _state(initiator=Side.BOTTOM, axis=1.5, band=Band.STABLE,
                       ready=(BOTTOM_TRAP_AND_ROLL_ESCAPE,))
        trap = te.outcome_distribution(match, model, ready, BOTTOM_TRAP_AND_ROLL_ESCAPE, M)
        self.assertEqual({rid: w for w, _, _, rid in trap},
                         {TOP_RESPONSE_WIDE_MOUNT_BASE: Fraction(2, 3),
                          TOP_RESPONSE_HIP_FOLLOW_REPUMMEL: Fraction(1, 3)})
        for rid, weight in blind.RandomBlindResponder.POLICY[Side.TOP]:
            self.assertGreater(weight, 0)


class RecognitionEnumerationTests(unittest.TestCase):
    def test_enumeration_has_mass_one_and_equals_36_roll_enumeration(self):
        match = _match(enable_v04b_recognition=True)
        for requested in te.COMMITMENTS:
            for effective in (None, *te.COMMITMENTS):
                cases = te.recognition_cases(match, INFORMED_RECOGNITION, requested, effective)
                self.assertEqual(len(cases), 9)
                self.assertEqual(sum(w for w, _ in cases), 1)
                full = Counter()
                for i in range(1, 7):
                    for k in range(1, 7):
                        read = match.recognition_policy.read(
                            requested=requested, effective=effective,
                            intent_roll=i, capability_roll=k)
                        full[(read.perceived_requested, read.perceived_effective)] += Fraction(1, 36)
                classes = Counter()
                for w, read in cases:
                    classes[(read.perceived_requested, read.perceived_effective)] += w
                self.assertEqual(full, classes)

    def test_enumeration_uses_real_recognition_reads(self):
        match = _match(enable_v04b_recognition=True)
        match.top.stamina.set_current(9)
        for requested in te.COMMITMENTS:
            effective = te.funded(match, requested, 9)
            reads = [r for _, r in te.recognition_cases(match, INFORMED_RECOGNITION,
                                                        requested, effective)]
            expected = [match.recognize_commitment(requested=requested, intent_roll=i,
                                                   capability_roll=k)
                        for i in (1, 2, 6) for k in (1, 2, 6)]
            self.assertEqual(reads, expected)

    def test_no_recognition_is_a_single_certain_case(self):
        self.assertEqual(te.recognition_cases(_match(), INFORMED_MATCH, M, M),
                         ((Fraction(1), None),))


class ResponseCommitmentTests(unittest.TestCase):
    def test_response_commitment_mirrors_batch(self):
        match = _match(enable_v04b_recognition=True)
        rng = random.Random(0)
        modes = [m for m in BatchResponseCommitmentMode if m is not BatchResponseCommitmentMode.RANDOM]
        for stamina in (2, 5, 9, 100):
            match.top.stamina.set_current(stamina)
            for mode in modes:
                for requested in te.COMMITMENTS:
                    effective = te.funded(match, requested, stamina)
                    for i in range(1, 7):
                        for k in range(1, 7):
                            read = match.recognize_commitment(requested=requested,
                                                              intent_roll=i, capability_roll=k)
                            expected = batch_module._response_commitment_for_exchange(
                                match, initiator_commitment=requested, mode=mode, rng=rng,
                                recognition_read=read)
                            got = te.response_commitment(mode, effective, read)
                            self.assertEqual(got, ((expected, Fraction(1)),))

    def test_random_mode_is_uniform_over_commitments(self):
        dist = te.response_commitment(BatchResponseCommitmentMode.RANDOM, M, None)
        self.assertEqual(dict(dist), {c: Fraction(1, 3) for c in Commitment})


class LiveEngineEquivalenceTests(unittest.TestCase):
    """Exhaustive reachable cases: every live pre-attempt state of short runs
    on each surface family, every legal action x response x commitment pair."""

    @classmethod
    def setUpClass(cls):
        cls.states = {name: _live_states(name) for name in SURFACES}

    def test_pure_resolution_equals_engine_previews(self):
        for name, states in self.states.items():
            total = mismatches = 0
            for match, _ in states:
                state = te.State.of(match)
                for action_id in match.legal_action_ids():
                    for response_id in match.legal_response_ids(action_id):
                        for c in te.COMMITMENTS:
                            for rc in (te.COMMITMENTS if match.enable_v04_commitment_semantics
                                       else (None,)):
                                expected = match.preview_attempt_resolution(
                                    action_id=action_id, response_id=response_id,
                                    commitment=c, response_commitment=rc)
                                ieff = te.funded(match, c, state.pool(state.initiator).current)
                                reff = (te.funded(match, rc, state.pool(state.initiator.opponent).current)
                                        if rc is not None else None)
                                got = te.resolve(match, state, action_id, response_id, ieff, reff)
                                total += 1
                                mismatches += got != expected
            with self.subTest(surface=name):
                self.assertGreater(total, 0)
                self.assertEqual(mismatches, 0)

    def test_perceived_resolution_equals_engine_preview_from_effective(self):
        for name in ("B-PROD", "E-PROD 42 OFF"):
            for match, _ in self.states[name]:
                state = te.State.of(match)
                for action_id in match.legal_action_ids():
                    for response_id in match.legal_response_ids(action_id):
                        for perceived in (None, *te.COMMITMENTS):
                            for rc in te.COMMITMENTS:
                                expected = match.preview_attempt_resolution_from_effective(
                                    action_id=action_id, response_id=response_id,
                                    initiator_effective_commitment=perceived,
                                    response_commitment=rc)
                                reff = te.funded(match, rc, state.pool(state.initiator.opponent).current)
                                self.assertEqual(te.resolve(match, state, action_id, response_id,
                                                            perceived, reff), expected)

    def test_informed_bottom_choice_equals_runtime_helper(self):
        for name in ("A-PROD", "B-PROD", "E-PROD 42 OFF", "PROTECT probe"):
            model = diag.model_for(diag.surfaces()[name])
            checked = 0
            for match, _ in self.states[name]:
                if match.initiator is not Side.TOP:
                    continue
                state = te.State.of(match)
                for action_id in match.legal_action_ids():
                    for requested in te.COMMITMENTS:
                        effective = te.funded(match, requested, state.top.current)
                        outcomes = te.outcome_distribution(match, model, state, action_id, requested)
                        cases = te.recognition_cases(match, model, requested, effective)
                        self.assertEqual(len(outcomes), len(cases))
                        for (w, read), (_, _, _, response_id) in zip(cases, outcomes):
                            rc = (batch_module._response_commitment_for_exchange(
                                match, initiator_commitment=requested,
                                mode=model.response_mode, rng=random.Random(0),
                                recognition_read=read)
                                if match.enable_v04_commitment_semantics else None)
                            expected = batch_module._informed_bottom_response_id(
                                match, action_id=action_id, commitment=requested,
                                response_commitment=rc, use_recognition=read is not None,
                                perceived_effective_commitment=(
                                    read.perceived_effective if read is not None else None))
                            self.assertEqual(response_id, expected)
                            checked += 1
            with self.subTest(surface=name):
                self.assertGreater(checked, 0)

    def test_random_blind_weights_equal_runtime_policy(self):
        for name in ("A-PROD", "E-PROD 142 ON", "PROTECT probe"):
            model = diag.model_for(diag.surfaces()[name])
            for match, _ in self.states[name]:
                if match.initiator is not Side.BOTTOM:
                    continue
                state = te.State.of(match)
                for action_id in match.legal_action_ids():
                    weighted = blind.RandomBlindResponder.weighted_policy(
                        Side.TOP, allowed_response_ids=match.legal_response_ids(action_id),
                        fallback_response_id=EscapeFirstInitiatorPolicy._ready_fallback_response_id(
                            match, action_id))
                    total = sum(w for _, w in weighted)
                    outcomes = te.outcome_distribution(match, model, state, action_id, M)
                    got = Counter()
                    for w, _, _, rid in outcomes:
                        got[rid] += w
                    self.assertEqual(dict(got), {rid: Fraction(w, total) for rid, w in weighted})

    def test_event_predicates_equal_engine_outcomes(self):
        """Apply every (response, commitment, response commitment) to a copy of
        the live match and compare terminal / progress / setup advance."""
        for name in SURFACES:
            checked = 0
            for match, kw in self.states[name]:
                state = te.State.of(match)
                action_id = kw["action_id"]
                for response_id in match.legal_response_ids(action_id):
                    for c in te.COMMITMENTS:
                        for rc in (te.COMMITMENTS if match.enable_v04_commitment_semantics
                                   else (None,)):
                            real = _copy(match)
                            read = (real.recognize_commitment(requested=c, intent_roll=3,
                                                              capability_roll=3)
                                    if real.enable_v04b_recognition else None)
                            subs = len(real.history.submission_change_history)
                            result = real.attempt(action_id=action_id, response_id=response_id,
                                                  commitment=c, response_commitment=rc,
                                                  recognition_read=read)
                            new = real.history.submission_change_history[subs:]
                            engine_progress = state.initiator is Side.TOP and any(
                                e.startswith("entry:") or (":" not in e and not e.endswith("->Tap"))
                                for e in new)
                            engine_terminal = (result.resolution.exit_destination is not None
                                               if state.initiator is Side.BOTTOM
                                               else real.submission_tapped)
                            engine_setup = bool(real.history.setup_change_history[
                                len(match.history.setup_change_history):])
                            res = result.resolution
                            self.assertEqual(te.is_progress(match, state, action_id, c, res),
                                             engine_progress)
                            self.assertEqual(te.is_terminal(match, state, action_id, c, res),
                                             engine_terminal)
                            self.assertEqual(te.advances_setup(match, state, action_id, res),
                                             engine_setup)
                            checked += 1
            with self.subTest(surface=name):
                self.assertGreater(checked, 0)


class AxisExpectationTests(unittest.TestCase):
    """Where the evaluator's model coincides with the existing random-blind
    helpers (v0.4a off, so commitment cannot change grades), its raw/realized
    axis and escape values must equal them exactly: floor/cap clamps, escape
    crossings and Ready overrides included."""

    def test_axis_and_escape_equal_existing_helpers_on_a_state_grid(self):
        match = MountMatch(enable_v02_setup=True, enable_v03_submissions=True)
        model = te.OpponentModel(False, BatchResponseCommitmentMode.FIXED_MEDIUM, False)
        rules = match.engine.rules
        checked = 0
        for step in range(10, 401, 5):
            axis = round(step / 100, 2)
            for band in Band:
                if not rules.axis_can_have_band(axis, band):
                    continue
                for side in Side:
                    for ready in ((), (BOTTOM_TRAP_AND_ROLL_ESCAPE,), (TOP_AMERICANA_ARM_ISOLATION,)):
                        for top_b, bottom_b in ((TopBehavior.PRESSURE, BottomBehavior.ESCAPE),
                                                (TopBehavior.HOLD, BottomBehavior.PROTECT)):
                            state = _state(axis=axis, band=band, initiator=side, ready=ready,
                                           top_behavior=top_b, bottom_behavior=bottom_b)
                            actions = [a.id for a in match.engine.catalog.actions_for(side)
                                       if match.setup_policy.rule_for_target(a.id) is None
                                       or a.id in ready]
                            for action_id in actions:
                                v = te.evaluate(match, model, state, action_id, M, project=False)
                                allowed = te.legal_responses(match, state, action_id)
                                fallback = te._fallback(match, state, action_id)
                                overrides = {r: o for r in allowed if (
                                    o := te._ready_override(match, state, action_id, r)) is not None}
                                kw = dict(side=side, action_id=action_id, axis=axis, band=band,
                                          top_behavior=top_b, bottom_behavior=bottom_b,
                                          allowed_response_ids=allowed,
                                          fallback_response_id=fallback,
                                          ready_grade_overrides=overrides)
                                self.assertAlmostEqual(float(v.axis_raw),
                                                       blind.expected_raw_attacker_axis_delta(**kw), 12)
                                self.assertAlmostEqual(float(v.axis_realized),
                                                       blind.expected_realized_attacker_axis_delta(**kw), 12)
                                if side is Side.BOTTOM:
                                    self.assertEqual(float(v.terminal),
                                                     blind.exact_escape_probability(**kw))
                                checked += 1
        self.assertGreater(checked, 1000)

    def test_hand_computed_cap_floor_and_escape(self):
        model = te.OpponentModel(False, BatchResponseCommitmentMode.FIXED_MEDIUM, False)
        match = MountMatch(enable_v02_setup=True, enable_v03_submissions=True)
        # Climb at 3.90 Locked vs random Bottom (Frame 4: S +1; Tight elbow 3: F -1).
        v = te.evaluate(match, model, _state(axis=3.9, band=Band.LOCKED), TOP_HIGH_MOUNT_CLIMB, M)
        self.assertEqual(v.axis_raw, Fraction(1, 7))                  # (4 - 3) / 7
        self.assertAlmostEqual(float(v.axis_realized), (4 * 0.1 - 3 * 1.0) / 7, 12)  # capped at 4.00
        # Climb at the 4.00 cap: success fully absorbed -> no setup advance.
        v = te.evaluate(match, model, _state(axis=4.0, band=Band.LOCKED), TOP_HIGH_MOUNT_CLIMB, M)
        self.assertEqual(v.setup_advance, Fraction(3, 7))
        # Bridge (floor clamp) at 0.10 Loose: never below the floor, never exits.
        v = te.evaluate(match, model, _state(axis=0.1, band=Band.LOOSE, initiator=Side.BOTTOM),
                        BOTTOM_BRIDGE, M)
        self.assertEqual(v.terminal, 0)


class ProjectionTests(unittest.TestCase):
    def test_pool_projection_matches_stamina_pool_hysteresis(self):
        for start in range(0, 101):
            for target in range(-10, 111, 3):
                pool = StaminaPool(current=start)
                snapshot = te.Pool(pool.current, pool.band is StaminaBand.EXHAUSTED)
                self.assertEqual(snapshot.band, pool.band)
                pool.set_current(max(0, min(100, target)))
                moved = snapshot.moved_to(target)
                self.assertEqual((moved.current, moved.band), (pool.current, pool.band))

    def test_projection_is_bounded_and_hand_computed(self):
        match = _match()
        model = INFORMED_MATCH
        # Top tier None: r = 2, Δ = 20 s. Own 60 - 2*7 - 4 (PRESSURE) = 42;
        # opponent 30 latched - 4 (ESCAPE) = 26, still latched.
        state = _state(top=60, bottom=30, axis=2.5, band=Band.STRONG)
        state = te.State(**{**{f: getattr(state, f) for f in te.State.__slots__},
                            "bottom": te.Pool(30, True)})
        calls = Counter()
        real = te.outcome_distribution

        def spy(*a, **k):
            calls["n"] += 1
            return real(*a, **k)

        with patch.object(te, "outcome_distribution", spy):
            v = te.evaluate(match, model, state, TOP_HIGH_MOUNT_CLIMB, M)
        p = v.projection
        self.assertEqual((p.builds_remaining, p.elapsed_seconds), (2, 20))
        self.assertEqual((p.own.current, p.own.latched), (42, False))
        self.assertEqual((p.opponent.current, p.opponent.latched), (26, True))
        self.assertEqual(p.axis, match.engine.rules.clamp_axis(2.5 + float(2 * v.axis_realized)))
        self.assertEqual(p.chain_probability, v.setup_advance ** 2)
        self.assertEqual(p.setup_future, p.chain_probability * p.use_value)
        self.assertEqual(p.use_value, max(val for _, val in p.use_values))
        self.assertEqual([c for c, _ in p.use_values], [L, M, H])  # 42 funds all three
        # One distribution for the current exchange plus one per fundable use
        # commitment: no recursion, no search tree.
        self.assertEqual(calls["n"], 1 + 3)

    def test_projection_partial_tier_and_fundability(self):
        match = _match()
        targets = {TOP_AMERICANA_ARM_ISOLATION: 1}
        # r = 1, Δ = 10 s: own 14 - 7 - 2 = 5 -> only LOW is fully payable.
        v = te.evaluate(match, INFORMED_MATCH, _state(top=40, tiers=targets),
                        TOP_HIGH_MOUNT_CLIMB, M)
        self.assertEqual((v.projection.builds_remaining, v.projection.elapsed_seconds), (1, 10))
        s = _state(tiers=targets)
        s = te.State(**{**{f: getattr(s, f) for f in te.State.__slots__}, "top": te.Pool(14, True)})
        v = te.evaluate(match, INFORMED_MATCH, s, TOP_HIGH_MOUNT_CLIMB, M)
        self.assertEqual(v.projection.own.current, 5)
        self.assertEqual([c for c, _ in v.projection.use_values], [L])
        # Projected own stamina 2: nothing fundable -> use value 0.
        s = te.State(**{**{f: getattr(s, f) for f in te.State.__slots__}, "top": te.Pool(11, True)})
        v = te.evaluate(match, INFORMED_MATCH, s, TOP_HIGH_MOUNT_CLIMB, M)
        self.assertEqual((v.projection.own.current, v.projection.use_values,
                          v.projection.setup_future), (2, (), 0))

    def test_opponent_projection_ignores_discretionary_spend(self):
        match = _match()
        s = _state(initiator=Side.BOTTOM, axis=1.5, band=Band.STABLE, top=50, bottom=80)
        v = te.evaluate(match, INFORMED_MATCH, s, BOTTOM_BRIDGE, L)
        # Opponent (Top, PRESSURE): 50 - 4 only; own 80 - 2*3 - 4 (ESCAPE) = 70.
        self.assertEqual((v.projection.opponent.current, v.projection.own.current), (46, 70))

    def test_non_builders_and_ready_targets_have_no_setup_future(self):
        match = _match()
        v = te.evaluate(match, INFORMED_MATCH, _state(), TOP_CROSSFACE_PRESSURE, M)
        self.assertIsNone(v.projection)
        self.assertEqual(v.setup_future, 0)
        v = te.evaluate(match, INFORMED_MATCH, _state(ready=(TOP_AMERICANA_ARM_ISOLATION,)),
                        TOP_HIGH_MOUNT_CLIMB, M)
        self.assertEqual((v.projection, v.setup_future, v.setup_advance), (None, 0, 0))


class TE1SelectionTests(unittest.TestCase):
    def setUp(self):
        self.match = _match()
        self.actions = self.match.legal_action_ids()

    def value(self, action_index, c, **kw):
        base = dict(terminal=Fraction(0), progress=Fraction(0), setup_advance=Fraction(0),
                    setup_future=Fraction(0), axis_realized=Fraction(0), axis_raw=Fraction(0),
                    stamina_cost={L: 3, M: 7, H: 12}[c], enters_exhausted=False)
        base.update({k: (v if isinstance(v, bool) or k == "stamina_cost" else Fraction(v))
                     for k, v in kw.items()})
        return te.TacticalValue(action_id=self.actions[action_index], requested=c,
                                effective=c, **base)

    def choose(self, *values):
        return te.choose_te1(self.match, values)

    def test_setup_tier_reduces_then_compares(self):
        low = self.value(0, L, setup_future="1/5")
        medium = self.value(0, M, setup_future="3/5")
        self.assertEqual((self.choose(low, medium).tier, self.choose(low, medium).value), ("setup", low))

    def test_setup_tier_compares_reduced_candidates_across_actions(self):
        a_low = self.value(0, L, setup_future="1/10")
        a_high = self.value(0, H, setup_future="9/10")
        b_medium = self.value(1, M, setup_future="3/10")
        self.assertEqual(self.choose(a_low, a_high, b_medium).value, b_medium)

    def test_position_tier_reduces_then_compares_across_actions(self):
        a_low = self.value(0, L, axis_raw="1/10", axis_realized="1/10")
        a_high = self.value(0, H, axis_raw="9/10", axis_realized="9/10")
        b_medium = self.value(1, M, axis_raw="3/10", axis_realized="3/10")
        choice = self.choose(a_low, a_high, b_medium)
        self.assertEqual((choice.tier, choice.value), ("position", b_medium))

    def test_position_requires_both_raw_and_realized_positive(self):
        a = self.value(0, L, axis_raw="1/10", axis_realized=0)
        b = self.value(0, M, axis_raw="1/10", axis_realized="1/10")
        self.assertEqual(self.choose(a, b).value, b)
        self.assertEqual(self.choose(a).tier, "reset")

    def test_terminal_tier_takes_highest_value_with_strict_stamina_guard(self):
        medium = self.value(0, M, terminal="1/2")
        high_tied = self.value(0, H, terminal="1/2", enters_exhausted=True)
        self.assertEqual(self.choose(medium, high_tied).value, medium)
        high_better = self.value(0, H, terminal="3/5", enters_exhausted=True)
        self.assertEqual(self.choose(medium, high_better).value, high_better)
        # No admissible non-entering commitment of the action: entering admitted.
        self.assertEqual(self.choose(self.value(0, L), high_tied).value, high_tied)

    def test_guard_is_per_action(self):
        a_medium = self.value(0, M, progress="1/2")
        b_high = self.value(1, H, progress="1/2", enters_exhausted=True)
        # b_high has no non-entering sibling: admissible; tie on progress ->
        # axis -> lower cost picks a_medium.
        self.assertEqual(self.choose(a_medium, b_high).value, a_medium)
        self.assertEqual(self.choose(a_medium, b_high).tier, "progress")

    def test_tier_order_terminal_before_progress_before_setup(self):
        t = self.value(1, L, terminal="1/100")
        p = self.value(0, H, progress="99/100")
        s = self.value(0, L, setup_future="1")
        self.assertEqual(self.choose(t, p, s).tier, "terminal")
        self.assertEqual(self.choose(p, s).tier, "progress")
        self.assertEqual(self.choose(s).tier, "setup")

    def test_tie_breaks_in_frozen_order(self):
        # 1. metric equal -> 2. axis_realized
        a = self.value(0, L, terminal="1/2", axis_realized="1/10")
        b = self.value(1, L, terminal="1/2", axis_realized="2/10")
        self.assertEqual(self.choose(a, b).value, b)
        # 3. axis_raw
        a = self.value(0, L, terminal="1/2", axis_raw="3/10")
        b = self.value(1, L, terminal="1/2", axis_raw="2/10")
        self.assertEqual(self.choose(a, b).value, a)
        # 4. lower stamina cost
        a = self.value(0, M, terminal="1/2")
        b = self.value(1, L, terminal="1/2")
        self.assertEqual(self.choose(a, b).value, b)
        # 5. catalog order
        a = self.value(1, M, terminal="1/2")
        b = self.value(0, M, terminal="1/2")
        self.assertEqual(self.choose(a, b).value, b)
        # 6. LOW < MEDIUM < HIGH (same cost only reachable with equal effective cost)
        a = te.TacticalValue(**{**{f: getattr(self.value(0, M, terminal="1/2"), f)
                                   for f in te.TacticalValue.__slots__}, "stamina_cost": 3})
        b = self.value(0, L, terminal="1/2")
        self.assertEqual(self.choose(a, b).value, b)

    def test_reset_when_no_tier_applies(self):
        self.assertEqual(self.choose(self.value(0, L)).tier, "reset")

    def test_precedence_keeps_low_in_bottom_recover_exhausted_windows(self):
        match = _match()
        match.initiator = Side.BOTTOM
        match.bottom.stamina.set_current(20)
        kw = dict(bottom_behavior_mode=BatchBehaviorMode.RECOVER,
                  recovery_initiation_mode=RecoveryInitiationMode.LOW_WHILE_EXHAUSTED)
        self.assertEqual(te.allowed_commitments(match, **kw), (L,))
        match.bottom.stamina.set_current(40)
        self.assertEqual(te.allowed_commitments(match, **kw), te.COMMITMENTS)
        match.initiator = Side.TOP
        match.top.stamina.set_current(20)
        self.assertEqual(te.allowed_commitments(match, **kw), te.COMMITMENTS)
        values = te.candidates(match, INFORMED_MATCH, te.State.of(match), (L,))
        self.assertEqual({v.requested for v in values}, {L})


class RngIntegrityTests(unittest.TestCase):
    def test_evaluator_module_has_no_rng_dependency(self):
        source = inspect.getsource(te)
        self.assertNotIn("import random", source)
        self.assertNotIn("Random(", source)

    def test_counter_counts_without_changing_draws(self):
        plain = random.Random(7)
        expected = [plain.randrange(10), plain.randint(1, 6), plain.choice("abc"), plain.random()]
        before = dict(vars(random.Random))
        trace = diag.RngTrace()
        with diag.count_rng(trace):
            r = random.Random(7)
            got = [r.randrange(10), r.randint(1, 6), r.choice("abc"), r.random()]
            trace.active = True
            random.Random(1).randrange(3)
            trace.active = False
        self.assertEqual(got, expected)
        self.assertGreater(trace.baseline_draws, 0)
        self.assertGreater(sum(trace.evaluator_draws.values()), 0)
        self.assertEqual(dict(vars(random.Random)), before)

    def test_evaluator_draws_nothing_on_live_states(self):
        trace = diag.RngTrace()
        states = _live_states("E-PROD 42 OFF", matches=2)
        model = diag.model_for(diag.surfaces()["E-PROD 42 OFF"])
        with diag.count_rng(trace):
            trace.active = True
            for match, _ in states:
                te.choose_te1(match, te.candidates(match, model, te.State.of(match)))
            trace.active = False
        self.assertEqual(sum(trace.evaluator_draws.values()), 0)


class ObserverIntegrityTests(unittest.TestCase):
    def test_observer_is_inert_on_every_surface(self):
        for name, kwargs in diag.surfaces().items():
            kwargs = {**kwargs, "matches": 6}
            with self.subTest(surface=name):
                summary, signatures, timelines, trace, counterfactuals = diag.observe_batch(**kwargs)
                ref_summary, ref_signatures, ref_trace = diag.baseline_reference(**kwargs)
                self.assertEqual(summary, run_escape_first_batch(**kwargs))
                self.assertEqual((summary, signatures), (ref_summary, ref_signatures))
                self.assertEqual((trace.baseline_draws, trace.baseline_digest),
                                 (ref_trace.baseline_draws, ref_trace.baseline_digest))
                self.assertEqual(sum(trace.evaluator_draws.values()), 0)
                attempts = [e for ev in timelines for e in ev if e["kind"] == "attempt"]
                self.assertTrue(attempts and all(e["integrity"] for e in attempts))

    def test_observer_delegates_each_real_call_exactly_once(self):
        kwargs = {**diag.surfaces()["E-PROD 42 OFF"], "matches": 4}
        calls = Counter()
        original_attempt, original_choose = MountMatch.attempt, EscapeFirstInitiatorPolicy.choose

        def attempt_spy(match, *a, **k):
            calls["attempt"] += 1
            return original_attempt(match, *a, **k)

        def choose_spy(policy, match):
            calls["choose"] += 1
            return original_choose(policy, match)

        with patch.object(MountMatch, "attempt", attempt_spy), \
                patch.object(EscapeFirstInitiatorPolicy, "choose", choose_spy):
            run_escape_first_batch(**kwargs)
            plain = dict(calls)
            calls.clear()
            _, _, timelines, _, counterfactuals = diag.observe_batch(**kwargs)
        events = [e for ev in timelines for e in ev]
        self.assertEqual(calls, plain)
        self.assertEqual(calls["attempt"], sum(e["kind"] == "attempt" for e in events))
        self.assertEqual(calls["choose"],
                         sum(e["kind"] == "decision" for e in events) + counterfactuals)
        self.assertGreater(counterfactuals, 0)

    def test_wrappers_restore_after_normal_exit_and_exceptions(self):
        originals = lambda: (EscapeFirstInitiatorPolicy.choose, MountMatch.attempt,
                             D3BTokenLockoutController.decide, batch_module.MountMatch,
                             dict(vars(random.Random)))
        before = originals()
        diag.observe_batch(**{**diag.surfaces()["A-PROD"], "matches": 2})
        self.assertEqual(originals(), before)
        # Exception raised inside the wrapped attempt, mid-run.
        with patch.object(te, "evaluate", side_effect=RuntimeError("probe")):
            with self.assertRaisesRegex(RuntimeError, "probe"):
                diag.observe_batch(**{**diag.surfaces()["E-PROD 42 OFF"], "matches": 2})
        self.assertEqual(originals(), before)
        with patch.object(diag, "run_escape_first_batch", side_effect=RuntimeError("probe")):
            with self.assertRaisesRegex(RuntimeError, "probe"):
                diag.observe_batch(**diag.surfaces()["A-PROD"])
        self.assertEqual(originals(), before)

    def test_deterministic_replay(self):
        kwargs = {**diag.surfaces()["B-PROD"], "matches": 4}
        first = diag.observe_batch(**kwargs)
        second = diag.observe_batch(**kwargs)
        self.assertEqual(first[:3], second[:3])
        self.assertEqual(first[3].baseline_digest, second[3].baseline_digest)


class CalibrationScoringTests(unittest.TestCase):
    def test_scoring_is_read_only_and_measurement_self_checks(self):
        name = "E-PROD 42 ON"
        kwargs = {**diag.surfaces()[name], "matches": 3}
        summary, _, timelines, _, _ = diag.observe_batch(**kwargs)
        snapshot = copy.deepcopy(timelines)
        diag.score(name, summary, timelines)
        self.assertEqual(timelines, snapshot)
        result, _ = diag.measure_surface(name, kwargs)
        integrity = result["integrity"]
        self.assertTrue(integrity["replay_identical"])
        self.assertTrue(integrity["rng_sequence_identical"])
        self.assertEqual(integrity["evaluator_rng_draws"], 0)
        self.assertEqual(integrity["lockout_hold_counterfactuals_excluded"],
                         integrity["d3b_holds"])

    def test_exact_three_sigma_boundary(self):
        # Σp = 1, Σp(1-p) = 1/4 + 1/4 = 1/2 -> 3σ = 2.1213...
        pairs = [(Fraction(1, 2), True), (Fraction(1, 2), True)]
        self.assertTrue(diag.calibration(pairs)["within_3_sigma"])
        # Degenerate σ = 0: realized must equal Σp exactly.
        self.assertTrue(diag.calibration([(Fraction(1), True), (Fraction(0), False)])["within_3_sigma"])
        self.assertFalse(diag.calibration([(Fraction(0), True)])["within_3_sigma"])
        # Just outside: 10 events at p = 1/100: σ² = 99/1000; deviation 1 - 1/10.
        out = diag.calibration([(Fraction(1, 100), i < 2) for i in range(10)])
        self.assertEqual(out["actual"], 2)
        self.assertFalse(out["within_3_sigma"])  # 1.9² = 3.61 > 9 * 0.099 = 0.891


if __name__ == "__main__":
    unittest.main()
