"""Stage 1B: TACTICAL_V1 initiator policy wiring (implementation only).

Implements section 2 of docs/TACTICAL_EVALUATOR_STAGE1B_PREREGISTRATION.md
(binding at ae786af483d109785f172cb10a17170ece2ed241) on top of the frozen
evaluator (tactical_evaluator, 4e61bad) and projection v2
(tactical_projection_v2, 5b57017). Nothing here changes the engine, the
domain, settlement, costs, rates, thresholds, D3-B, the production policy,
the response policy, Recognition or scoring.

- validate_tactical_v1: the supported-configuration contract (2.1 and 9.1).
  Unsupported configurations raise ValueError; there is no fallback.
- precedence: production constraints win (2.1, 4e61bad 2.6). D3-B and the
  force-RESET rule are applied by the batch before the policy is asked; a
  precedence-forced commitment leaves TE-1 the action only.
- TacticalV1Policy: TE-1 with projection v2 for both initiators. Its
  opponent windows are O-3 (projection v2 Context.initiator_policy =
  TACTICAL_V1): TE-1 with the frozen single-chain surrogate, depth 1.
- Every policy.choose call, executed or D3-B collector counterfactual, is
  appended to a replay tape (5.1), and every executed initiator exchange is
  recorded with the source of its commitment (G6, 5.3).
- ReplayInitiatorPolicy: the inertness replay (P4c). It returns the recorded
  decisions without evaluating anything and fails on any desynchronization.

The evaluator is pure: no RNG, no mutation of the live match or of the live
D3-B controller (branch states are snapshots; continuations run on sandboxes).
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from enum import Enum

from ..domain.action import Commitment
from ..domain.model import BottomBehavior, Side, TopBehavior
from ..domain.stamina import StaminaBand
from ..engine.stamina import DEFAULT_BEHAVIOR_STAMINA_POLICY
from . import tactical_evaluator as te
from . import tactical_projection_v2 as v2
from .batch import (
    BatchBehaviorMode,
    BatchDecision,
    BatchInitiatorPolicy,
    BatchResponderMode,
    BatchResponseCommitmentMode,
    BatchRun,
    run_batch,
)
from .handoff_policy import HandoffDecisionKind, PostClearHandoffMode
from .recovery_policy import RecoveryInitiationMode

PREREGISTRATION = "ae786af483d109785f172cb10a17170ece2ed241"


class TacticalContractError(RuntimeError):
    """A state the binding contract declares impossible was reached."""


class CommitmentSource(str, Enum):
    """Who selected the requested commitment of an initiator exchange."""

    TE1 = "TE1"
    LOW_WHILE_EXHAUSTED = "LOW_WHILE_EXHAUSTED"
    D3B_TOKEN = "D3B_TOKEN"
    HANDOFF_REQUESTED = "HANDOFF_REQUESTED"


class CallKind(str, Enum):
    EXECUTED = "executed"
    COUNTERFACTUAL = "counterfactual"


# ---------------------------------------------------------------------------
# Supported configurations (2.1, 9.1)
# ---------------------------------------------------------------------------

# The frozen G4 PROTECT probe (diagnostics/setup_policy.py:
# historical_protect_probe_kwargs() at 3494fa5) with every other batch option
# at its default. Written out in full so a later default change cannot widen
# the exception silently; a test pins it against the probe and the signature.
PROTECT_PROBE_ENVELOPE: dict = dict(
    matches=100,
    base_seed=42,
    top_behavior=TopBehavior.PRESSURE,
    bottom_behavior=BottomBehavior.PROTECT,
    commitment=Commitment.MEDIUM,
    initial_clock=300,
    starting_axis=1.50,
    interval_seconds=5,
    top_stamina=100,
    bottom_stamina=100,
    top_behavior_mode=BatchBehaviorMode.FIXED,
    bottom_behavior_mode=BatchBehaviorMode.FIXED,
    bottom_responder_mode=BatchResponderMode.INFORMED,
    response_commitment_mode=BatchResponseCommitmentMode.FIXED_MEDIUM,
    enable_v02_setup=True,
    enable_v03_submissions=True,
    enable_v03b_stalling=False,
    enable_v04_commitment_semantics=False,
    enable_v04b_recognition=False,
    enable_stamina_settlement_rules=False,
    enable_unfunded_responder_cost_waiver=False,
    enable_supplemental_hold_settlement=False,
    recovery_initiation_mode=RecoveryInitiationMode.CURRENT,
    measure_stamina_economy=False,
    measure_recovery_policy=False,
    measure_reexhaustion_handoffs=False,
    shadow_stalling=False,
    post_clear_handoff_mode=PostClearHandoffMode.NONE,
    measure_post_clear_handoff=False,
)

_MODELED_HANDOFF_MODES = (
    PostClearHandoffMode.NONE,
    PostClearHandoffMode.D3B_EXHAUSTED_TOKEN_LOCKOUT,
)


def _identical(a, b) -> bool:
    return type(a) is type(b) and a == b


def is_protect_probe_envelope(settings: dict) -> bool:
    """Exactly the frozen probe: same keys, same types, same values."""
    return (set(settings) == set(PROTECT_PROBE_ENVELOPE)
            and all(_identical(settings[k], v) for k, v in PROTECT_PROBE_ENVELOPE.items()))


def validate_tactical_v1(settings: dict) -> None:
    """Raise ValueError unless TACTICAL_V1 supports these batch settings.

    `settings` is every run_batch option except initiator_policy, resolved
    to its value. The general contract requires v0.2 setup, v0.3a
    submissions, v0.4a commitment semantics and the informed Bottom
    responder, and only the handoff modes projection v2 models (NONE, D3-B).
    With v0.4a off, only the exact frozen PROTECT probe is admitted.
    """
    if set(settings) != set(PROTECT_PROBE_ENVELOPE):
        raise ValueError("TACTICAL_V1 validation needs every batch option")
    if not settings["enable_v04_commitment_semantics"]:
        if is_protect_probe_envelope(settings):
            return
        raise ValueError(
            "TACTICAL_V1 requires v0.4a commitment semantics; with v0.4a off "
            "only the exact frozen G4 PROTECT probe is admitted"
        )
    problems = []
    if not settings["enable_v02_setup"]:
        problems.append("v0.2 setup")
    if not settings["enable_v03_submissions"]:
        problems.append("v0.3a submissions")
    if settings["bottom_responder_mode"] is not BatchResponderMode.INFORMED:
        problems.append("the informed Bottom responder")
    if settings["post_clear_handoff_mode"] not in _MODELED_HANDOFF_MODES:
        problems.append("a handoff mode projection v2 models (NONE or D3-B)")
    if settings["interval_seconds"] % DEFAULT_BEHAVIOR_STAMINA_POLICY.quantum_seconds:
        problems.append("an interval that is a whole number of behavior quanta")
    if problems:
        raise ValueError("TACTICAL_V1 requires " + ", ".join(problems))


# ---------------------------------------------------------------------------
# Precedence (production constraints win)
# ---------------------------------------------------------------------------


def precedence(match, *, context: v2.Context, handoff_decision
               ) -> tuple[tuple[Commitment, ...], CommitmentSource | None]:
    """(commitments TE-1 may request, the precedence rule forcing it or None).

    Mirrors the batch exactly: Bottom RECOVER + Exhausted under
    LOW_WHILE_EXHAUSTED forces LOW (at a D3-B TOKEN window this is the
    adopted LOW path), and a handoff-requested commitment overrides it. A
    LOCKOUT_HOLD or forced RESET never reaches TE-1 as an executed call.
    """
    if handoff_decision is not None and handoff_decision.requested_commitment is not None:
        return (handoff_decision.requested_commitment,), CommitmentSource.HANDOFF_REQUESTED
    exhausted_recover = (
        match.initiator is Side.BOTTOM
        and context.bottom_behavior_mode is BatchBehaviorMode.RECOVER
        and match.bottom.stamina.band is StaminaBand.EXHAUSTED
    )
    if (exhausted_recover and context.recovery_initiation_mode
            is RecoveryInitiationMode.LOW_WHILE_EXHAUSTED):
        token = (handoff_decision is not None
                 and handoff_decision.kind is HandoffDecisionKind.TOKEN)
        return ((Commitment.LOW,),
                CommitmentSource.D3B_TOKEN if token else CommitmentSource.LOW_WHILE_EXHAUSTED)
    return te.COMMITMENTS, None


# ---------------------------------------------------------------------------
# Decision-reason mapping (2.1)
# ---------------------------------------------------------------------------

_REASONS = {
    (Side.TOP, "terminal"): "submission",
    (Side.BOTTOM, "terminal"): "escape",
    (Side.TOP, "progress"): "submission",
    # (Side.BOTTOM, "progress") is n/a: Bottom progress is always 0.
    (Side.TOP, "setup"): "setup",
    (Side.BOTTOM, "setup"): "setup",
    (Side.TOP, "position"): "position",
    (Side.BOTTOM, "position"): "position",
    (Side.TOP, "reset"): "reset",
    (Side.BOTTOM, "reset"): "reset",
}


def reason_for(side: Side, tier: str) -> str:
    try:
        return _REASONS[(side, tier)]
    except KeyError:
        raise TacticalContractError(
            f"TE-1 tier {tier!r} has no {side.value} reason in the binding mapping"
        ) from None


def decision_for(side: Side, choice: te.ShadowChoice) -> BatchDecision:
    reason = reason_for(side, choice.tier)
    value = choice.value
    if (value is None) != (choice.tier == "reset"):
        raise TacticalContractError("TE-1 returned an action-less non-reset tier")
    if value is None:
        return BatchDecision(action_id=None, reason=reason, escape_probability=0.0,
                             submission_progress_probability=0.0,
                             expected_raw_axis=0.0, expected_realized_axis=0.0)
    return BatchDecision(
        action_id=value.action_id,
        reason=reason,
        escape_probability=float(value.terminal) if side is Side.BOTTOM else 0.0,
        submission_progress_probability=(
            float(max(value.terminal, value.progress)) if side is Side.TOP else 0.0),
        expected_raw_axis=float(value.axis_raw),
        expected_realized_axis=float(value.axis_realized),
    )


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TacticalSelection:
    decision: BatchDecision
    tier: str
    requested: Commitment | None          # None for RESET
    allowed: tuple[Commitment, ...]
    forced_by: CommitmentSource | None


@dataclass(frozen=True, slots=True)
class TapeEntry:
    """One policy.choose call, in call order (5.1)."""

    match_index: int
    call_index: int                       # per match, from 0
    kind: CallKind
    side: Side
    branch: v2.Branch                     # public state + clock + D3-B fields
    allowed: tuple[Commitment, ...]
    forced_by: CommitmentSource | None
    tier: str
    decision: BatchDecision
    requested: Commitment | None


@dataclass(frozen=True, slots=True)
class InitiatorExchange:
    """One executed initiator exchange (resets and holds are not exchanges)."""

    match_index: int
    side: Side
    tier: str
    requested: Commitment
    source: CommitmentSource


@dataclass(frozen=True, slots=True)
class TacticalMeasurement:
    tape: tuple[TapeEntry, ...]
    exchanges: tuple[InitiatorExchange, ...]


@dataclass(frozen=True, slots=True)
class G6Tally:
    """Stage 1B 5.3 over a set of runs (computed, never gated, here)."""

    te1_chosen: int                       # denominator
    high: int                             # numerator
    excluded_forced: tuple[tuple[str, int], ...]
    by_side: tuple[tuple[str, int, int], ...]  # (side, te1_chosen, high)


def g6_tally(exchanges) -> G6Tally:
    """Share of HIGH among exchanges whose commitment TE-1 selected, both
    sides pooled. Precedence-forced exchanges are excluded and counted."""
    chosen = high = 0
    excluded: dict[str, int] = {}
    sides = {side: [0, 0] for side in Side}
    for exchange in exchanges:
        if exchange.source is not CommitmentSource.TE1:
            excluded[exchange.source.value] = excluded.get(exchange.source.value, 0) + 1
            continue
        is_high = exchange.requested is Commitment.HIGH
        chosen += 1
        high += is_high
        sides[exchange.side][0] += 1
        sides[exchange.side][1] += is_high
    return G6Tally(
        te1_chosen=chosen, high=high,
        excluded_forced=tuple(sorted(excluded.items())),
        by_side=tuple((side.value, n, h) for side, (n, h) in sides.items()),
    )


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------


class _RecordingPolicy:
    """Shared call protocol: start_match, choose (every call taped), finish."""

    def __init__(self, context: v2.Context) -> None:
        if context.initiator_policy is not BatchInitiatorPolicy.TACTICAL_V1:
            raise ValueError("TACTICAL_V1 policy needs a TACTICAL_V1 context")
        self.context = context
        self._tape: list[TapeEntry] = []
        self._exchanges: list[InitiatorExchange] = []
        self._match = None
        self._match_index: int | None = None
        self._controller = None
        self._calls = 0

    def start_match(self, *, match_index: int, match, controller) -> None:
        self._match, self._match_index, self._controller = match, match_index, controller
        self._calls = 0

    def choose(self, match, *, handoff_decision, executed: bool) -> TacticalSelection:
        if match is not self._match:
            raise RuntimeError("choose called outside the active match")
        allowed, forced_by = precedence(match, context=self.context,
                                        handoff_decision=handoff_decision)
        kind = CallKind.EXECUTED if executed else CallKind.COUNTERFACTUAL
        branch = v2.branch_of(match, self._controller)
        entry = self._entry(match, kind=kind, branch=branch, allowed=allowed,
                            forced_by=forced_by)
        if entry.requested is not None and entry.requested not in allowed:
            raise TacticalContractError("requested commitment outside precedence")
        self._tape.append(entry)
        self._calls += 1
        if executed and entry.decision.action_id is not None:
            self._exchanges.append(InitiatorExchange(
                match_index=self._match_index, side=entry.side, tier=entry.tier,
                requested=entry.requested,
                source=forced_by if forced_by is not None else CommitmentSource.TE1))
        return TacticalSelection(decision=entry.decision, tier=entry.tier,
                                 requested=entry.requested, allowed=allowed,
                                 forced_by=forced_by)

    def finish(self) -> TacticalMeasurement:
        return TacticalMeasurement(tape=tuple(self._tape), exchanges=tuple(self._exchanges))

    def _entry(self, match, *, kind, branch, allowed, forced_by) -> TapeEntry:
        raise NotImplementedError


class TacticalV1Policy(_RecordingPolicy):
    """TE-1 (4e61bad 2.5) with projection v2 (5b57017) as the acting policy."""

    def start_match(self, *, match_index: int, match, controller) -> None:
        super().start_match(match_index=match_index, match=match, controller=controller)
        # One continuation per live match; its caches are keyed by full
        # branch state (exact), as in the Stage 1A-v2 shadow.
        self._continuation = v2.Continuation(match, self.context)

    def _entry(self, match, *, kind, branch, allowed, forced_by) -> TapeEntry:
        side = match.initiator
        values = v2.candidates(self._continuation, branch, allowed)
        choice = te.choose_te1(match, values)
        return TapeEntry(
            match_index=self._match_index, call_index=self._calls, kind=kind,
            side=side, branch=branch, allowed=allowed, forced_by=forced_by,
            tier=choice.tier, decision=decision_for(side, choice),
            requested=choice.value.requested if choice.value is not None else None,
        )


class ReplayDesync(RuntimeError):
    """Inertness-replay integrity failure (Stage 1B 5.1: OPEN, never PASS)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


class ReplayInitiatorPolicy(_RecordingPolicy):
    """Returns recorded results in order without evaluating anything."""

    def __init__(self, context: v2.Context, tape) -> None:
        super().__init__(context)
        self._recorded = tuple(tape)
        self._position = 0

    def _entry(self, match, *, kind, branch, allowed, forced_by) -> TapeEntry:
        if self._position >= len(self._recorded):
            raise ReplayDesync("underflow", "more policy.choose calls than tape entries")
        entry = self._recorded[self._position]
        self._position += 1
        if (entry.match_index, entry.call_index) != (self._match_index, self._calls):
            raise ReplayDesync(
                "order", f"expected call {(self._match_index, self._calls)}, "
                         f"tape has {(entry.match_index, entry.call_index)}")
        if entry.kind is not kind:
            raise ReplayDesync("flag", f"call is {kind.value}, tape entry is {entry.kind.value}")
        side = match.initiator
        if (entry.side, entry.branch, entry.allowed, entry.forced_by) != (
                side, branch, allowed, forced_by):
            raise ReplayDesync("context", "window state differs from the recorded call")
        legal = (entry.decision.action_id is None
                 or entry.decision.action_id in match.legal_action_ids(side))
        if (not legal or entry.decision.reason != reason_for(side, entry.tier)
                or (entry.requested is None) != (entry.decision.action_id is None)):
            raise ReplayDesync("decision", "recorded decision does not fit this window")
        return entry

    def finish(self) -> TacticalMeasurement:
        if self._position != len(self._recorded):
            raise ReplayDesync(
                "leftover", f"{len(self._recorded) - self._position} tape entries unused")
        return super().finish()


_REPLAY_TAPE: ContextVar[tuple[TapeEntry, ...] | None] = ContextVar(
    "tactical_v1_replay_tape", default=None)


@contextmanager
def replaying(tape):
    """Within this block, TACTICAL_V1 batches replay `tape` (P4c)."""
    token = _REPLAY_TAPE.set(tuple(tape))
    try:
        yield
    finally:
        _REPLAY_TAPE.reset(token)


def create_policy(settings: dict) -> _RecordingPolicy:
    """The batch's TACTICAL_V1 policy for validated settings."""
    context = v2.Context.from_batch_kwargs(
        {**settings, "initiator_policy": BatchInitiatorPolicy.TACTICAL_V1})
    tape = _REPLAY_TAPE.get()
    if tape is not None:
        return ReplayInitiatorPolicy(context, tape)
    return TacticalV1Policy(context)


def replay_batch(tape, **kwargs) -> BatchRun:
    """Inertness replay of a TACTICAL_V1 batch from its recorded tape."""
    with replaying(tape):
        return run_batch(initiator_policy=BatchInitiatorPolicy.TACTICAL_V1, **kwargs)
