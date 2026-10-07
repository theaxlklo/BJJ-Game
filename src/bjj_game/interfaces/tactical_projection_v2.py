"""Projection v2: bounded alternating-window continuation (Stage 1A-v2).

Implements section 2 of docs/TACTICAL_EVALUATOR_PROJECTION_V2_PREREGISTRATION.md
(binding at 5b57017). It replaces only the forward-state projection of the
frozen evaluator (tactical_evaluator.project_setup). The immediate exchange
and Ready-use valuation are the frozen ones and are reused unchanged.

The continuation carries an exact finite distribution over public branch
states (Fraction weights). Identical branches merge only when every
continuation-relevant field is equal. There is no pruning, cutoff, sampling
or averaging.

Every step runs the engine's own code on a sandbox MountMatch (a fresh
instance with the live match's configuration, loaded with the branch state):
attempt() for each enumerated chance case of an exchange, advance() between
windows, recovery_hold() for D3-B LOCKOUT_HOLD. The window ordering is
therefore the runtime ordering by construction. MountMatch holds no RNG, and
the live match is never touched.

Opponent windows use O-3: the opponent's declared initiator policy evaluated
on the branch state, with recovery precedence and a copied D3-B controller.
Under ESCAPE_FIRST (Stage 1A-v2) that is the batch EscapeFirstInitiatorPolicy
at the batch commitment. Under TACTICAL_V1 (Stage 1B, ae786af section 2.2) it
is TE-1 (tiers, tie-breaks, stamina guard, precedence) whose nested setup
valuation is the frozen single-chain projection (te.project_setup), never this
continuation: nesting depth is exactly 1, and Continuation.project refuses
re-entry.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from fractions import Fraction

from ..domain.action import Commitment
from ..domain.model import Band, Side
from ..domain.setup import SetupTier
from ..domain.stamina import StaminaBand
from ..engine.match import MountMatch
from ..engine.stamina import BehaviorStaminaMeter
from . import tactical_evaluator as te
from .batch import (
    AdaptiveBehaviorPolicy,
    BatchBehaviorMode,
    BatchInitiatorPolicy,
    BatchResponderMode,
    BatchResponseCommitmentMode,
    EscapeFirstInitiatorPolicy,
)
from .blind import RandomBlindResponder
from .handoff_policy import (
    D3BTokenLockoutController,
    HandoffDecisionKind,
    PostClearHandoffMode,
)
from .recovery_policy import RecoveryInitiationMode

ZERO = te.ZERO
EXIT = "exit"
TAP = "tap"
TIMEOUT = "timeout"


# ---------------------------------------------------------------------------
# Declared policy contracts of the surface (public)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Context:
    model: te.OpponentModel
    commitment: Commitment
    top_policy: AdaptiveBehaviorPolicy
    bottom_policy: AdaptiveBehaviorPolicy
    bottom_behavior_mode: BatchBehaviorMode
    recovery_initiation_mode: RecoveryInitiationMode
    d3b: bool
    # The declared opponent initiator contract (O-3). Both initiators use the
    # batch's initiator policy, so the opponent's contract is that policy.
    initiator_policy: BatchInitiatorPolicy = BatchInitiatorPolicy.ESCAPE_FIRST

    @classmethod
    def from_batch_kwargs(cls, kwargs: dict) -> "Context":
        mode = kwargs.get("post_clear_handoff_mode", PostClearHandoffMode.NONE)
        if mode not in (PostClearHandoffMode.NONE,
                        PostClearHandoffMode.D3B_EXHAUSTED_TOKEN_LOCKOUT):
            raise ValueError(f"projection v2 does not model handoff mode {mode}")
        bottom_mode = kwargs.get("bottom_behavior_mode", BatchBehaviorMode.FIXED)
        return cls(
            model=te.OpponentModel.from_settings(
                bottom_responder_mode=kwargs.get(
                    "bottom_responder_mode", BatchResponderMode.RANDOM),
                response_commitment_mode=kwargs.get(
                    "response_commitment_mode", BatchResponseCommitmentMode.FIXED_MEDIUM),
                recognition=bool(kwargs.get("enable_v04b_recognition", False)),
            ),
            commitment=kwargs.get("commitment", Commitment.MEDIUM),
            top_policy=AdaptiveBehaviorPolicy(
                side=Side.TOP, baseline=kwargs["top_behavior"],
                mode=kwargs.get("top_behavior_mode", BatchBehaviorMode.FIXED)),
            bottom_policy=AdaptiveBehaviorPolicy(
                side=Side.BOTTOM, baseline=kwargs["bottom_behavior"], mode=bottom_mode),
            bottom_behavior_mode=bottom_mode,
            recovery_initiation_mode=kwargs.get(
                "recovery_initiation_mode", RecoveryInitiationMode.CURRENT),
            d3b=mode is PostClearHandoffMode.D3B_EXHAUSTED_TOKEN_LOCKOUT,
            initiator_policy=BatchInitiatorPolicy(kwargs.get(
                "initiator_policy", BatchInitiatorPolicy.ESCAPE_FIRST)),
        )


# ---------------------------------------------------------------------------
# Branch state (every continuation-relevant field; merge key)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Branch:
    """te.State (axis, band, initiative, behaviors, pools + latches, Ready set,
    tiers, submission stage) plus the clock and the copied D3-B controller
    fields (armed, token_consumed, last observed Exhausted). Behavior-meter
    remainders are always 0 here (asserted: the interval is a whole number of
    quanta), so they need no field."""

    state: te.State
    clock: int
    d3b: tuple[bool, bool, bool] | None


def controller_fields(controller) -> tuple[bool, bool, bool] | None:
    if controller is None:
        return None
    if not isinstance(controller, D3BTokenLockoutController):
        raise ValueError("projection v2 models only the D3-B controller")
    return (controller.armed, controller.token_consumed, controller._exhausted)


def branch_of(match: MountMatch, controller) -> Branch:
    return Branch(te.State.of(match), match.clock_seconds, controller_fields(controller))


# ---------------------------------------------------------------------------
# Sandbox: the engine's own transitions on a loaded copy
# ---------------------------------------------------------------------------


class Sandbox:
    def __init__(self, match: MountMatch) -> None:
        # A fresh MountMatch with the same configuration; never the live match.
        self.match = replace(match)
        policy = self.match.behavior_stamina_policy
        if self.match.interval_seconds % policy.quantum_seconds:
            raise ValueError("interval must be a whole number of behavior quanta")

    def load(self, branch: Branch) -> MountMatch:
        m, s = self.match, branch.state
        m.history = type(m.history)()
        m.initiator = s.initiator
        m.clock_seconds = branch.clock
        m.exit_destination = None
        m.exit_reason = None
        m.submission_tapped = False
        m.free_initiative_pending = False
        m.free_initiative_beneficiary = None
        m.position.broken = False
        m.position.crossing_axis = None
        m.position.apply_control(s.axis, s.band)
        m.set_behaviors(top=s.top_behavior, bottom=s.bottom_behavior)
        for pool, value in ((m.top.stamina, s.top), (m.bottom.stamina, s.bottom)):
            # Public latch path, as te.Pool._real.
            pool.set_current(0 if value.latched else pool.maximum)
            pool.set_current(value.current)
        tiers = dict(s.tiers)
        for target, track in m.setup_state.tracks.items():
            track.tier = SetupTier(tiers.get(target, 0))
        m.submission_state.stage = s.stage
        m.top_behavior_stamina_meter = BehaviorStaminaMeter()
        m.bottom_behavior_stamina_meter = BehaviorStaminaMeter()
        return m

    @staticmethod
    def controller(fields: tuple[bool, bool, bool] | None):
        if fields is None:
            return None
        controller = D3BTokenLockoutController.__new__(D3BTokenLockoutController)
        controller.armed, controller.token_consumed, controller._exhausted = fields
        return controller

    def read(self, controller) -> Branch | str:
        m = self.match
        if m.submission_tapped:
            return TAP
        if m.exit_destination is not None:
            return EXIT
        if m.clock_seconds <= 0:
            return TIMEOUT
        for meter in (m.top_behavior_stamina_meter, m.bottom_behavior_stamina_meter):
            if meter.remainder_units:
                raise RuntimeError("behavior-meter remainder outside the merge key")
        return branch_of(m, controller)


# ---------------------------------------------------------------------------
# Exact exchange cases (the frozen outcome_distribution, with the case data
# attempt() needs: Recognition read, requested response commitment, response)
# ---------------------------------------------------------------------------


def exchange_cases(match: MountMatch, model: te.OpponentModel, state: te.State,
                   action_id: str, requested: Commitment):
    """Exact ((weight, read, response_commitment, response_id), ...). The same
    enumeration as te.outcome_distribution (pinned by tests)."""
    side = state.initiator
    initiator_eff = te.funded(match, requested, state.pool(side).current)
    responder_stamina = state.pool(side.opponent).current
    legal = te.legal_responses(match, state, action_id)
    out = []
    for w_read, read in te.recognition_cases(match, model, requested, initiator_eff):
        if match.enable_v04_commitment_semantics:
            responses = te.response_commitment(model.response_mode, initiator_eff, read)
        else:
            responses = ((None, Fraction(1)),)
        for response_c, w_c in responses:
            responder_eff = (te.funded(match, response_c, responder_stamina)
                             if response_c is not None else None)
            if side is Side.TOP and model.bottom_informed:
                perceived = read.perceived_effective if read is not None else initiator_eff
                candidates = []
                for order, response_id in enumerate(legal):
                    predicted = te.resolve(match, state, action_id, response_id,
                                           perceived, responder_eff).final_grade
                    candidates.append((predicted, order, response_id))
                chosen = ((min(candidates)[2], Fraction(1)),)
            else:
                weighted = RandomBlindResponder.weighted_policy(
                    side.opponent, allowed_response_ids=legal,
                    fallback_response_id=te._fallback(match, state, action_id))
                total = sum(w for _, w in weighted)
                chosen = tuple((rid, Fraction(w, total)) for rid, w in weighted)
            for response_id, w_r in chosen:
                out.append((w_read * w_c * w_r, read, response_c, response_id))
    return tuple(out)


# ---------------------------------------------------------------------------
# Continuation
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ContinuationProjection:
    """Section 2 trace for one builder candidate."""

    target: str
    builds_remaining: int
    setup_future: Fraction                     # Σ P(branch) · max_c' V (TE-1)
    setup_future_requested: tuple[tuple[Commitment, Fraction], ...]  # Σ P · V(requested c)
    ready_mass: Fraction                       # P(target Ready at the use window)
    terminal_mass: tuple[tuple[str, Fraction], ...]
    use_branches: int
    max_branches: int
    # Use-state summary over branches reaching the use window (reported).
    p_opponent_exhausted: Fraction
    p_strong_or_locked: Fraction
    expected_axis: Fraction
    expected_own: Fraction
    expected_opponent: Fraction


def _merge(dist: dict, item, weight: Fraction, terminals: Counter) -> None:
    if isinstance(item, str):
        terminals[item] += weight
    else:
        dist[item] = dist.get(item, ZERO) + weight


class Continuation:
    """Bounded continuation for one live match. Caches are keyed by the full
    branch state, so they are exact; clear them between matches."""

    def __init__(self, match: MountMatch, context: Context) -> None:
        self.live = match
        self.context = context
        self.sandbox = Sandbox(match)
        self.policy = EscapeFirstInitiatorPolicy()
        self._exchange: dict = {}
        self._advance: dict = {}
        self._opponent: dict = {}
        self._use: dict = {}
        self._projecting = False

    # -- one exchange (W1/W3 builder, or the opponent's chosen action) ---------

    def exchange(self, branch: Branch, action_id: str, requested: Commitment):
        # attempt() changes neither the clock nor the controller, so outcomes
        # are cached by (state, action, commitment) and re-attached to the
        # input clock and controller fields (exact).
        key = (branch.state, action_id, requested)
        cached = self._exchange.get(key)
        if cached is None:
            states: dict = {}
            terminals: Counter = Counter()
            cases = exchange_cases(self.sandbox.match, self.context.model, branch.state,
                                   action_id, requested)
            for weight, read, response_c, response_id in cases:
                m = self.sandbox.load(branch)
                m.attempt(action_id=action_id, response_id=response_id, commitment=requested,
                          response_commitment=response_c, recognition_read=read)
                after = self.sandbox.read(Sandbox.controller(branch.d3b))
                if isinstance(after, Branch):
                    if after.clock != branch.clock or after.d3b != branch.d3b:
                        raise RuntimeError("attempt changed clock or controller state")
                    after = after.state
                _merge(states, after, weight, terminals)
            cached = self._exchange[key] = (tuple(states.items()), tuple(terminals.items()))
        states, terminals = cached
        return (tuple((Branch(s, branch.clock, branch.d3b), w) for s, w in states),
                terminals)

    # -- between windows: batch behavior choice, advance(), D3-B observation ----

    def advance(self, branch: Branch) -> Branch | str:
        if branch in self._advance:
            return self._advance[branch]
        m = self.sandbox.load(branch)
        controller = Sandbox.controller(branch.d3b)
        top = self.context.top_policy.choose(m)
        bottom = self.context.bottom_policy.choose(m)
        if controller is not None:
            bottom = controller.pre_advance_bottom_behavior(bottom)
        m.set_behaviors(top=top, bottom=bottom)
        m.advance()
        if controller is not None:
            controller.observe_advance(m)
        if not m.ended:
            # Post-advance re-choice (the latch may have cleared).
            m.set_behaviors(top=self.context.top_policy.choose(m),
                            bottom=self.context.bottom_policy.choose(m))
        result = self.sandbox.read(controller)
        self._advance[branch] = result
        return result

    # -- the opponent's window (O-3) -------------------------------------------

    def opponent_decision(self, branch: Branch):
        """(kind, action_id, requested) the batch would take at this window."""
        m = self.sandbox.load(branch)
        side = branch.state.initiator
        controller = Sandbox.controller(branch.d3b)
        kind = None
        if controller is not None and side is Side.BOTTOM:
            decision = controller.decide(m, armed=False)
            kind = decision.kind
            if decision.hold:
                return kind, None, None, controller
        exhausted_recover = (side is Side.BOTTOM
                             and self.context.bottom_behavior_mode is BatchBehaviorMode.RECOVER
                             and m.bottom.stamina.band is StaminaBand.EXHAUSTED)
        if exhausted_recover and (self.context.recovery_initiation_mode
                                  is RecoveryInitiationMode.RESET_WHILE_EXHAUSTED):
            return kind, None, None, controller
        low_forced = (exhausted_recover and self.context.recovery_initiation_mode
                      is RecoveryInitiationMode.LOW_WHILE_EXHAUSTED)
        if self.context.initiator_policy is BatchInitiatorPolicy.TACTICAL_V1:
            # O-3 under TACTICAL_V1: TE-1 on the branch state, with the frozen
            # single-chain projection as the nested setup surrogate (te.evaluate
            # projects through te.project_setup, never through this
            # continuation). Precedence as in play: a forced LOW leaves TE-1
            # the action only.
            allowed = (Commitment.LOW,) if low_forced else te.COMMITMENTS
            choice = te.choose_te1(
                m, te.candidates(m, self.context.model, branch.state, allowed))
            if choice.value is None:
                return kind, None, None, controller
            return kind, choice.value.action_id, choice.value.requested, controller
        requested = Commitment.LOW if low_forced else self.context.commitment
        decision = self.policy.choose(m)
        return kind, decision.action_id, requested, controller

    def opponent(self, branch: Branch):
        if branch in self._opponent:
            return self._opponent[branch]
        kind, action_id, requested, controller = self.opponent_decision(branch)
        fields = controller_fields(controller)
        if kind is HandoffDecisionKind.LOCKOUT_HOLD:
            m = self.sandbox.load(branch)
            m.recovery_hold()
            result = (((self.sandbox.read(controller), Fraction(1)),), ())
        elif action_id is None:
            # RESET: initiative passes; stalling evaluation is not modeled (2.4 step 1).
            state = replace(branch.state, initiator=branch.state.initiator.opponent)
            result = (((Branch(state, branch.clock, fields), Fraction(1)),), ())
        else:
            result = self.exchange(replace(branch, d3b=fields), action_id, requested)
        self._opponent[branch] = result
        return result

    # -- use window (frozen valuation) -----------------------------------------

    def use_values(self, branch: Branch, target: str):
        # The frozen use valuation reads only te.State (not clock or controller).
        key = (branch.state, target)
        if key in self._use:
            return self._use[key]
        m, state = self.live, branch.state
        own = state.pool(state.initiator)

        def success(requested):
            outcomes = te.outcome_distribution(m, self.context.model, state, target, requested)
            if state.initiator is Side.TOP:
                return te._expect(outcomes, lambda r: te.is_progress(m, state, target, requested, r))
            return te._expect(outcomes, lambda r: r.exit_destination is not None)

        values = {c: success(c) for c in te.COMMITMENTS}
        fundable = [values[c] for c in te.COMMITMENTS if te.funded(m, c, own.current) is c]
        result = (max(fundable, default=ZERO), tuple(values.items()))
        self._use[key] = result
        return result

    # -- section 2 -------------------------------------------------------------

    def project(self, branch: Branch, action_id: str, requested: Commitment
                ) -> ContinuationProjection | None:
        """Section 2, at nesting depth exactly 1: a continuation started from
        inside another continuation (for example by an opponent window) is a
        contract violation, not an approximation."""
        if self._projecting:
            raise RuntimeError("nested continuation: projection v2 depth is exactly 1")
        self._projecting = True
        try:
            return self._project(branch, action_id, requested)
        finally:
            self._projecting = False

    def _project(self, branch: Branch, action_id: str, requested: Commitment
                 ) -> ContinuationProjection | None:
        m = self.live
        state = branch.state
        target = m.setup_policy.target_for_builder(action_id)
        if not m.enable_v02_setup or target is None or target in state.ready:
            return None
        side = state.initiator
        remaining = 2 - state.tier(target)
        terminals: Counter = Counter()
        dist = {branch: Fraction(1)}
        widest = 1
        for window in range(2 * remaining):
            nxt: dict = {}
            for b, w in dist.items():
                if window % 2 == 0:
                    if b.state.initiator is not side:
                        raise RuntimeError("builder window off initiative")
                    items, ends = self.exchange(b, action_id, requested)
                else:
                    if b.state.initiator is side:
                        raise RuntimeError("opponent window off initiative")
                    items, ends = self.opponent(b)
                for item, p in items:
                    after = self.advance(item)
                    _merge(nxt, after, w * p, terminals)
                for label, p in ends:
                    terminals[label] += w * p
            dist = nxt
            widest = max(widest, len(dist))
        total = sum(dist.values(), ZERO)
        future = ZERO
        by_request = Counter()
        ready = opp_exhausted = strong = axis = own = opp = ZERO
        for b, w in dist.items():
            s = b.state
            if s.initiator is not side:
                raise RuntimeError("use window off initiative")
            axis += w * Fraction(s.axis)
            own += w * s.pool(side).current
            opp += w * s.pool(side.opponent).current
            opp_exhausted += w * s.pool(side.opponent).latched
            strong += w * (s.band in (Band.STRONG, Band.LOCKED))
            if target not in s.ready:
                continue
            ready += w
            best, requested_values = self.use_values(b, target)
            future += w * best
            for c, v in requested_values:
                by_request[c] += w * v
        norm = (lambda x: x / total) if total else (lambda x: ZERO)
        return ContinuationProjection(
            target=target, builds_remaining=remaining, setup_future=future,
            setup_future_requested=tuple((c, by_request[c]) for c in te.COMMITMENTS),
            ready_mass=ready, terminal_mass=tuple(sorted(terminals.items())),
            use_branches=len(dist), max_branches=widest,
            p_opponent_exhausted=norm(opp_exhausted), p_strong_or_locked=norm(strong),
            expected_axis=norm(axis), expected_own=norm(own), expected_opponent=norm(opp),
        )


# ---------------------------------------------------------------------------
# TacticalValue with the v2 projection (immediate layer unchanged)
# ---------------------------------------------------------------------------


def evaluate(continuation: Continuation, branch: Branch, action_id: str,
             requested: Commitment) -> te.TacticalValue:
    live = continuation.live
    value = te.evaluate(live, continuation.context.model, branch.state, action_id,
                        requested, project=False)
    projection = continuation.project(branch, action_id, requested)
    if projection is None:
        return value
    return replace(value, setup_future=projection.setup_future, projection=projection)


def candidates(continuation: Continuation, branch: Branch,
               allowed: tuple[Commitment, ...] = te.COMMITMENTS) -> tuple[te.TacticalValue, ...]:
    """te.candidates with the v2 projection (same duplicate drop)."""
    live, state = continuation.live, branch.state
    side = state.initiator
    values = []
    for action_id in live.legal_action_ids(side):
        seen = set()
        for c in allowed:
            effective = te.funded(live, c, state.pool(side).current)
            if effective in seen:
                continue
            seen.add(effective)
            values.append(evaluate(continuation, branch, action_id, c))
    return tuple(values)
