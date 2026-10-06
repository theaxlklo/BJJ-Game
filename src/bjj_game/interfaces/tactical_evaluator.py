"""Joint tactical evaluator (debts 4 + 5), Stage 1A: pure valuation only.

Implements the contract of docs/TACTICAL_EVALUATOR_PREREGISTRATION.md
(frozen at 4e61bad). Nothing here is wired into gameplay. Every value is an
exact finite weighted sum over the declared opponent model: Recognition rolls
and random-blind responses are enumerated with their exact weights, and no RNG
is read or drawn. The resolution path mirrors
MountMatch._resolve_attempt_resolution on an explicit state snapshot so the
same code can value the current state and the bounded setup projection.

All probabilities and expectations are exact Fractions, so every TE-1
comparison and tie-break is exact (no epsilon) and calibration sums carry no
rounding.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction

from ..domain.action import Commitment
from ..domain.model import Band, BottomBehavior, Side, TopBehavior
from ..domain.recognition import CommitmentRecognitionRead
from ..domain.stamina import StaminaBand, StaminaPool
from ..domain.submission import SubmissionStage
from ..engine.match import MountMatch
from ..positions.mount.catalog import (
    TOP_AMERICANA_ARM_ISOLATION,
    TOP_AMERICANA_SUBMISSION_FINISH,
)
from .batch import BatchBehaviorMode, BatchResponderMode, BatchResponseCommitmentMode
from .blind import RandomBlindResponder
from .recovery_policy import RecoveryInitiationMode

COMMITMENTS = (Commitment.LOW, Commitment.MEDIUM, Commitment.HIGH)
_RANK = {None: 0, Commitment.LOW: 1, Commitment.MEDIUM: 2, Commitment.HIGH: 3}
# d6 Recognition: roll 1 shifts down, 2-5 exact, 6 shifts up (weights 1, 4, 1).
# The representative roll of each class is passed to the real policy.
_ROLL_CLASSES = ((1, 1), (2, 4), (6, 1))
ZERO = Fraction(0)


# ---------------------------------------------------------------------------
# State snapshot (public information only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Pool:
    current: int
    latched: bool
    maximum: int = 100

    def _real(self) -> StaminaPool:
        """A real StaminaPool in this latch state (existing latch code)."""
        # Unlatched pools have current > enter; latched ones < recover. Start
        # from a value with the same latch, then move with set_current().
        pool = StaminaPool(current=0 if self.latched else self.maximum,
                           maximum=self.maximum)
        pool.set_current(self.current)
        return pool

    @property
    def band(self) -> StaminaBand:
        return self._real().band

    @property
    def enter_threshold(self) -> int:
        return self._real().exhaustion_enter_threshold

    def moved_to(self, value: int) -> "Pool":
        """Existing hysteresis latch applied to a projected value (clamped)."""
        pool = self._real()
        pool.set_current(max(0, min(self.maximum, value)))
        return Pool(current=pool.current,
                    latched=pool.band is StaminaBand.EXHAUSTED,
                    maximum=self.maximum)


@dataclass(frozen=True, slots=True)
class State:
    axis: float
    band: Band
    initiator: Side
    top_behavior: TopBehavior
    bottom_behavior: BottomBehavior
    top: Pool
    bottom: Pool
    ready: frozenset[str]
    tiers: tuple[tuple[str, int], ...]
    stage: SubmissionStage | None
    interval_seconds: int

    def pool(self, side: Side) -> Pool:
        return self.top if side is Side.TOP else self.bottom

    def tier(self, target: str) -> int:
        return dict(self.tiers).get(target, 0)

    @classmethod
    def of(cls, match: MountMatch) -> "State":
        targets = match.setup_policy.target_action_ids
        return cls(
            axis=match.position.control.value,
            band=match.band,
            initiator=match.initiator,
            top_behavior=match.top.behavior,
            bottom_behavior=match.bottom.behavior,
            top=Pool(match.top.stamina.current,
                     match.top.stamina.band is StaminaBand.EXHAUSTED,
                     match.top.stamina.maximum),
            bottom=Pool(match.bottom.stamina.current,
                        match.bottom.stamina.band is StaminaBand.EXHAUSTED,
                        match.bottom.stamina.maximum),
            ready=frozenset(t for t in targets if match.setup_state.is_ready(t)),
            tiers=tuple((t, int(match.setup_state.tier(t))) for t in targets),
            stage=match.submission_state.stage if match.submission_state.active else None,
            interval_seconds=match.interval_seconds,
        )


# ---------------------------------------------------------------------------
# Opponent model (E1) with exact Recognition enumeration (A6)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class OpponentModel:
    bottom_informed: bool
    response_mode: BatchResponseCommitmentMode
    recognition: bool

    @classmethod
    def from_settings(cls, *, bottom_responder_mode: BatchResponderMode,
                      response_commitment_mode: BatchResponseCommitmentMode,
                      recognition: bool) -> "OpponentModel":
        return cls(
            bottom_informed=bottom_responder_mode is BatchResponderMode.INFORMED,
            response_mode=response_commitment_mode,
            recognition=recognition,
        )


def response_commitment(mode: BatchResponseCommitmentMode,
                        initiator_effective: Commitment | None,
                        read: CommitmentRecognitionRead | None) -> tuple[tuple[Commitment, Fraction], ...]:
    """Mirror of batch._response_commitment_for_exchange as an exact distribution."""
    if mode is BatchResponseCommitmentMode.FIXED_MEDIUM:
        return ((Commitment.MEDIUM, Fraction(1)),)
    if mode is BatchResponseCommitmentMode.MATCH:
        return ((Commitment.LOW if initiator_effective is None else initiator_effective, Fraction(1)),)
    if mode is BatchResponseCommitmentMode.RANDOM:
        return tuple((c, Fraction(1, len(Commitment))) for c in Commitment)
    if read is None:
        raise ValueError("recognition response policy requires a Recognition read")
    if mode is BatchResponseCommitmentMode.RECOGNITION_ALWAYS_HIGH:
        return ((Commitment.HIGH, Fraction(1)),)
    trust = (
        Commitment.LOW
        if read.perceived_requested is Commitment.LOW or read.perceived_effective is None
        else read.perceived_effective
    )
    if mode is BatchResponseCommitmentMode.RECOGNITION:
        return ((trust, Fraction(1)),)
    return (({Commitment.LOW: Commitment.MEDIUM, Commitment.MEDIUM: Commitment.HIGH,
              Commitment.HIGH: Commitment.HIGH}[trust], Fraction(1)),)


def recognition_cases(match: MountMatch, model: OpponentModel, requested: Commitment,
                      effective: Commitment | None):
    """Exact (weight, read) cases; one case with read None without Recognition."""
    if not model.recognition:
        return ((Fraction(1), None),)
    cases = []
    for intent_roll, w_intent in _ROLL_CLASSES:
        for capability_roll, w_capability in _ROLL_CLASSES:
            read = match.recognition_policy.read(
                requested=requested, effective=effective,
                intent_roll=intent_roll, capability_roll=capability_roll,
            )
            cases.append((Fraction(w_intent * w_capability, 36), read))
    return tuple(cases)


# ---------------------------------------------------------------------------
# Resolution on an explicit state (mirror of MountMatch internals)
# ---------------------------------------------------------------------------


def _ready_override(match: MountMatch, state: State, action_id: str, response_id: str):
    if (match.enable_v02_setup and action_id in match.setup_policy.target_action_ids
            and action_id in state.ready):
        return match.setup_policy.ready_final_grade_override(action_id, response_id)
    return None


def _resolve_raw(match: MountMatch, state: State, action_id: str, response_id: str,
                 external: int):
    engine = match.engine
    if action_id == TOP_AMERICANA_SUBMISSION_FINISH:
        # Mirror of MountMatch._resolve_submission_stage.
        proxy = engine.resolve_action(
            axis=state.axis, band=state.band, initiator=Side.TOP,
            action_id=TOP_AMERICANA_ARM_ISOLATION, response_id=response_id,
            top_behavior=state.top_behavior, bottom_behavior=state.bottom_behavior,
            external_grade_modifier=external,
        )
        proposed = round(state.axis - 1.0, 10) if proxy.final_grade.failed else state.axis
        axis_after = engine.rules.clamp_axis(proposed)
        band_after, changes = engine.rules.update_band(axis_after, state.band)
        return replace(
            proxy, action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            axis_delta=round(axis_after - state.axis, 10), proposed_axis=proposed,
            axis_after=axis_after, band_after=band_after, band_changes=changes,
            failure_clamp_used=False, floor_clamp_used=False,
            escape_threshold_reached=False, exit_capable_action=False,
            exit_destination=None,
        )
    return engine.resolve_action(
        axis=state.axis, band=state.band, initiator=state.initiator,
        action_id=action_id, response_id=response_id,
        top_behavior=state.top_behavior, bottom_behavior=state.bottom_behavior,
        external_grade_modifier=external,
        post_positional_grade_override=_ready_override(match, state, action_id, response_id),
    )


def resolve(match: MountMatch, state: State, action_id: str, response_id: str,
            initiator_effective: Commitment | None, responder_effective: Commitment | None):
    """Final resolution exactly as MountMatch._resolve_attempt_resolution:
    matchup/Ready/submission, then exhaustion, then the v0.4a commitment
    transform (initiator magnitude, then responder undercommitment)."""
    exhaustion = match.exhaustion_policy.exchange_grade_modifier(
        initiator_band=state.pool(state.initiator).band,
        responder_band=state.pool(state.initiator.opponent).band,
    )
    base = _resolve_raw(match, state, action_id, response_id, 0)
    exhausted = base if exhaustion == 0 else _resolve_raw(match, state, action_id, response_id, exhaustion)
    if not match.enable_v04_commitment_semantics:
        return exhausted
    final_grade, magnitude, under = MountMatch._commitment_grade_transform(
        grade_after_exhaustion=exhausted.final_grade,
        initiator_commitment=initiator_effective,
        responder_commitment=responder_effective,
    )
    if magnitude == 0 and under == 0:
        return exhausted
    return _resolve_raw(match, state, action_id, response_id,
                        int(final_grade) - int(base.final_grade))


def legal_responses(match: MountMatch, state: State, action_id: str) -> tuple[str, ...]:
    """Mirror of MountMatch.legal_response_ids on a snapshot."""
    side = state.initiator
    all_ids = tuple(r.id for r in match.engine.catalog.responses_for(side.opponent))
    if action_id == TOP_AMERICANA_SUBMISSION_FINISH:
        ready_ids = match.setup_policy.ready_response_ids(TOP_AMERICANA_ARM_ISOLATION)
        return tuple(r for r in ready_ids if r in all_ids)
    if not match.enable_v02_setup or action_id not in state.ready:
        return all_ids
    ready_ids = match.setup_policy.ready_response_ids(action_id)
    if ready_ids is None:
        return all_ids
    return tuple(r for r in ready_ids if r in all_ids)


def _fallback(match: MountMatch, state: State, action_id: str) -> str | None:
    """Mirror of EscapeFirstInitiatorPolicy._ready_fallback_response_id."""
    if not match.enable_v02_setup:
        return None
    if (action_id == TOP_AMERICANA_SUBMISSION_FINISH and match.enable_v03_submissions
            and state.stage is not None):
        rule = match.setup_policy.rule_for_target(TOP_AMERICANA_ARM_ISOLATION)
        return rule.stalemate_response_id if rule is not None else None
    if action_id not in state.ready:
        return None
    rule = match.setup_policy.rule_for_target(action_id)
    return rule.stalemate_response_id if rule is not None else None


def funded(match: MountMatch, requested: Commitment, stamina: int) -> Commitment | None:
    """Existing StaminaCostPolicy.effective_commitment (None = UNFUNDED)."""
    return match.stamina_cost_policy.effective_commitment(
        requested=requested, available_stamina=stamina)


def _cost(match: MountMatch, effective: Commitment | None) -> int:
    return match.stamina_cost_policy.cost(effective) if effective is not None else 0


def outcome_distribution(match: MountMatch, model: OpponentModel, state: State,
                         action_id: str, requested: Commitment):
    """Exact ((weight, resolution, initiator_effective, response_id), ...).

    The defender chooses from its perceived state; the exchange resolves from
    the true effective commitments."""
    side = state.initiator
    initiator_eff = funded(match, requested, state.pool(side).current)
    responder_stamina = state.pool(side.opponent).current
    legal = legal_responses(match, state, action_id)
    outcomes = []
    for w_read, read in recognition_cases(match, model, requested, initiator_eff):
        if match.enable_v04_commitment_semantics:
            responses = response_commitment(model.response_mode, initiator_eff, read)
        else:
            responses = ((None, Fraction(1)),)
        for response_c, w_c in responses:
            responder_eff = (funded(match, response_c, responder_stamina)
                             if response_c is not None else None)
            if side is Side.TOP and model.bottom_informed:
                # Mirror of _informed_bottom_response_id: minimum predicted grade
                # under the perceived effective commitment (truth without
                # Recognition), first legal response on ties.
                perceived = read.perceived_effective if read is not None else initiator_eff
                candidates = []
                for order, response_id in enumerate(legal):
                    predicted = resolve(match, state, action_id, response_id,
                                        perceived, responder_eff).final_grade
                    candidates.append((predicted, order, response_id))
                chosen = ((min(candidates)[2], Fraction(1)),)
            else:
                weighted = RandomBlindResponder.weighted_policy(
                    side.opponent, allowed_response_ids=legal,
                    fallback_response_id=_fallback(match, state, action_id))
                total = sum(w for _, w in weighted)
                chosen = tuple((rid, Fraction(w, total)) for rid, w in weighted)
            for response_id, w_r in chosen:
                result = resolve(match, state, action_id, response_id,
                                 initiator_eff, responder_eff)
                outcomes.append((w_read * w_c * w_r, result, initiator_eff, response_id))
    return tuple(outcomes)


# ---------------------------------------------------------------------------
# Event predicates (engine semantics)
# ---------------------------------------------------------------------------


def is_terminal(match: MountMatch, state: State, action_id: str, requested: Commitment,
                result) -> bool:
    """Bottom: escape. Top: Tap (successful Finish-stage attempt, not feint-capped)."""
    if state.initiator is Side.BOTTOM:
        return result.exit_destination is not None
    feint = match.enable_v04_commitment_semantics and requested is Commitment.LOW
    return (match.enable_v03_submissions
            and action_id == TOP_AMERICANA_SUBMISSION_FINISH
            and state.stage is SubmissionStage.FINISH
            and result.final_grade.successful and not feint)


def is_progress(match: MountMatch, state: State, action_id: str, requested: Commitment,
                result) -> bool:
    """Top only: Ready-isolation Threat entry, or a Threat/Control stage advance
    (mirror of MountMatch._apply_submission_after_attempt)."""
    if state.initiator is not Side.TOP or not match.enable_v03_submissions:
        return False
    if action_id == TOP_AMERICANA_ARM_ISOLATION and action_id in state.ready:
        return result.band_before in {Band.STRONG, Band.LOCKED} and result.final_grade.successful
    if action_id == TOP_AMERICANA_SUBMISSION_FINISH and state.stage in {
            SubmissionStage.THREAT, SubmissionStage.CONTROL}:
        feint = match.enable_v04_commitment_semantics and requested is Commitment.LOW
        return result.final_grade.successful and not feint
    return False


def advances_setup(match: MountMatch, state: State, action_id: str, result) -> bool:
    """Mirror of MountMatch._apply_setup_after_attempt (builder branch)."""
    target = match.setup_policy.target_for_builder(action_id)
    return (match.enable_v02_setup and target is not None and target not in state.ready
            and match.setup_policy.setup_advances_from(result))


def _expect(outcomes, fn) -> Fraction:
    return sum((w for w, r, _, _ in outcomes if fn(r)), ZERO)


# ---------------------------------------------------------------------------
# TacticalValue (A2, A3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SetupProjection:
    """Section 2.4 trace for one builder candidate (all inputs to setup_future)."""

    target: str
    builds_remaining: int
    elapsed_seconds: int
    p_advance: Fraction
    own: Pool
    opponent: Pool
    axis: float
    band: Band
    use_values: tuple[tuple[Commitment, Fraction], ...]
    use_value: Fraction
    chain_probability: Fraction
    setup_future: Fraction


@dataclass(frozen=True, slots=True)
class TacticalValue:
    action_id: str
    requested: Commitment
    effective: Commitment | None
    terminal: Fraction
    progress: Fraction
    setup_future: Fraction
    axis_realized: Fraction
    axis_raw: Fraction
    stamina_cost: int
    enters_exhausted: bool
    # Auxiliary (not ranked by TE-1): P(builder advances now), the input to
    # the chain probability and the C2 setup-advance component.
    setup_advance: Fraction
    projection: SetupProjection | None = None


def evaluate(match: MountMatch, model: OpponentModel, state: State, action_id: str,
             requested: Commitment, *, project: bool = True) -> TacticalValue:
    side = state.initiator
    outcomes = outcome_distribution(match, model, state, action_id, requested)
    sign = 1 if side is Side.TOP else -1
    pool = state.pool(side)
    effective = funded(match, requested, pool.current)
    cost = _cost(match, effective)
    axis_realized = sum((w * Fraction(sign * (r.axis_after - state.axis))
                         for w, r, _, _ in outcomes), ZERO)
    setup_advance = _expect(outcomes, lambda r: advances_setup(match, state, action_id, r))
    projection = (project_setup(match, model, state, action_id, effective,
                                setup_advance, axis_realized) if project else None)
    return TacticalValue(
        action_id=action_id,
        requested=requested,
        effective=effective,
        terminal=_expect(outcomes, lambda r: is_terminal(match, state, action_id, requested, r)),
        progress=_expect(outcomes, lambda r: is_progress(match, state, action_id, requested, r)),
        setup_future=projection.setup_future if projection is not None else ZERO,
        axis_realized=axis_realized,
        axis_raw=sum((w * r.grade_value for w, r, _, _ in outcomes), ZERO),
        stamina_cost=cost,
        enters_exhausted=(not pool.latched) and pool.current - cost <= pool.enter_threshold,
        setup_advance=setup_advance,
        projection=projection,
    )


# ---------------------------------------------------------------------------
# Bounded setup projection (A5, E2)
# ---------------------------------------------------------------------------


def behavior_flow(match: MountMatch, behavior, seconds: int) -> int:
    """Existing behavior stamina rate applied over `seconds` (rate x time)."""
    policy = match.behavior_stamina_policy
    units = policy.points_per_quantum[behavior] * seconds
    if units % policy.quantum_seconds:
        raise ValueError("projection horizon must align with the behavior quantum")
    return units // policy.quantum_seconds


def project_setup(match: MountMatch, model: OpponentModel, state: State, action_id: str,
                  effective: Commitment | None, p_advance: Fraction,
                  axis_realized: Fraction) -> SetupProjection | None:
    """Section 2.4: setup_future = p_adv ** r * max_c' P(target success at the
    projected use state). One chain, r builder windows plus one use window;
    the opponent's discretionary spends are deliberately not projected."""
    target = match.setup_policy.target_for_builder(action_id)
    if not match.enable_v02_setup or target is None or target in state.ready:
        return None
    side = state.initiator
    remaining = 2 - state.tier(target)
    elapsed = 2 * remaining * state.interval_seconds
    own_behavior = state.top_behavior if side is Side.TOP else state.bottom_behavior
    opp_behavior = state.bottom_behavior if side is Side.TOP else state.top_behavior
    own = state.pool(side).moved_to(
        state.pool(side).current - remaining * _cost(match, effective)
        + behavior_flow(match, own_behavior, elapsed))
    opp = state.pool(side.opponent).moved_to(
        state.pool(side.opponent).current + behavior_flow(match, opp_behavior, elapsed))
    world_delta = axis_realized if side is Side.TOP else -axis_realized
    axis = match.engine.rules.clamp_axis(state.axis + float(remaining * world_delta))
    band, _ = match.engine.rules.update_band(axis, state.band)
    projected = replace(
        state, axis=axis, band=band,
        top=own if side is Side.TOP else opp,
        bottom=opp if side is Side.TOP else own,
        ready=state.ready | {target},
    )
    use_values = []
    for use in COMMITMENTS:
        # Fundable at the projected own stamina: the level is fully payable.
        if funded(match, use, own.current) is not use:
            continue
        outcomes = outcome_distribution(match, model, projected, target, use)
        if side is Side.TOP:
            value = _expect(outcomes, lambda r: is_progress(match, projected, target, use, r))
        else:
            value = _expect(outcomes, lambda r: r.exit_destination is not None)
        use_values.append((use, value))
    use_value = max((v for _, v in use_values), default=ZERO)
    chain = p_advance ** remaining
    return SetupProjection(
        target=target, builds_remaining=remaining, elapsed_seconds=elapsed,
        p_advance=p_advance, own=own, opponent=opp, axis=axis, band=band,
        use_values=tuple(use_values), use_value=use_value,
        chain_probability=chain, setup_future=chain * use_value,
    )


# ---------------------------------------------------------------------------
# TE-1 selection (section 2.5), used for Stage-1A shadow reporting only
# ---------------------------------------------------------------------------


def allowed_commitments(match: MountMatch, *, bottom_behavior_mode: BatchBehaviorMode,
                        recovery_initiation_mode: RecoveryInitiationMode) -> tuple[Commitment, ...]:
    """Section 2.6 precedence: in a Bottom RECOVER window while Exhausted the
    production policy keeps LOW (LOW_WHILE_EXHAUSTED); TE-1 picks the action only."""
    if (match.initiator is Side.BOTTOM
            and bottom_behavior_mode is BatchBehaviorMode.RECOVER
            and match.bottom.stamina.band is StaminaBand.EXHAUSTED
            and recovery_initiation_mode is RecoveryInitiationMode.LOW_WHILE_EXHAUSTED):
        return (Commitment.LOW,)
    return COMMITMENTS


def candidates(match: MountMatch, model: OpponentModel, state: State,
               allowed: tuple[Commitment, ...] = COMMITMENTS) -> tuple[TacticalValue, ...]:
    """All (action, commitment) values; requests funding identically to a lower
    request are dropped (lowest request kept)."""
    side = state.initiator
    values = []
    for action_id in match.legal_action_ids(side):
        seen = set()
        for c in allowed:
            effective = funded(match, c, state.pool(side).current)
            if effective in seen:
                continue
            seen.add(effective)
            values.append(evaluate(match, model, state, action_id, c))
    return tuple(values)


def _tiebreak(order: dict[str, int], metric):
    """Tier metric, axis_realized, axis_raw, lower cost, catalog order, LOW<MEDIUM<HIGH."""
    return lambda v: (metric(v), v.axis_realized, v.axis_raw, -v.stamina_cost,
                      -order[v.action_id], -_RANK[v.requested])


def _guarded(values, metric):
    """Stamina guard: an Exhausted-entering commitment is admissible only if its
    metric strictly exceeds every admissible non-entering one of the action."""
    kept = []
    for v in values:
        if not v.enters_exhausted:
            kept.append(v)
            continue
        others = [o for o in values if o.action_id == v.action_id and not o.enters_exhausted]
        if all(metric(v) > metric(o) for o in others):
            kept.append(v)
    return kept


def _reduced(values, qualifies):
    """Reduce each action to its cheapest qualifying commitment (tiers C, D)."""
    by_action = {}
    for v in sorted(values, key=lambda v: (v.stamina_cost, _RANK[v.requested])):
        if qualifies(v) and v.action_id not in by_action:
            by_action[v.action_id] = v
    return list(by_action.values())


@dataclass(frozen=True, slots=True)
class ShadowChoice:
    tier: str
    value: TacticalValue | None


def choose_te1(match: MountMatch, values: tuple[TacticalValue, ...]) -> ShadowChoice:
    order = {a: i for i, a in enumerate(match.legal_action_ids())}
    for name, metric in (("terminal", lambda v: v.terminal),
                         ("progress", lambda v: v.progress)):
        admitted = _guarded([v for v in values if metric(v) > 0], metric)
        if admitted:
            return ShadowChoice(name, max(admitted, key=_tiebreak(order, metric)))
    setup = _reduced(values, lambda v: v.setup_future > 0)
    if setup:
        return ShadowChoice("setup", max(setup, key=_tiebreak(order, lambda v: v.setup_future)))
    position = _reduced(values, lambda v: v.axis_raw > 0 and v.axis_realized > 0)
    if position:
        return ShadowChoice("position", max(position, key=_tiebreak(order, lambda v: v.axis_realized)))
    return ShadowChoice("reset", None)
