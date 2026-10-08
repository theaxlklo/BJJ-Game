"""TE-2: TACTICAL_V2 initiator policy (implementation only).

Implements docs/TACTICAL_EVALUATOR_TE2_PREREGISTRATION.md (binding at
218f1c0ab94d6999abd06157876f48704e8ba6e1):

- Top windows use TE-2E (section 3): TE-1 tiers A (terminal) and B (progress)
  unchanged, then Tier R (exact route value Q over every option, RESET
  included; interfaces/tactical_route.py), then TE-1's position tier, then
  RESET.
- Bottom windows use TE-1 with projection v2 exactly as Stage 1B
  (tactical_policy.TacticalV1Policy, fd19dd0), including precedence and the
  D3-B collector's counterfactual calls. A Bottom window never starts a route
  search.
- Supported configurations are TACTICAL_V1's, with the v0.4a-off PROTECT
  envelope admitted at base_seed 42 and 685800 only (section 5).

Every policy.choose call is taped (executed and counterfactual) for the
inertness replay, as in Stage 1B.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from fractions import Fraction

from ..domain.action import Commitment
from ..domain.model import Side
from . import tactical_evaluator as te
from . import tactical_policy as tp
from . import tactical_projection_v2 as v2
from . import tactical_route as route
from .batch import BatchDecision, BatchInitiatorPolicy, BatchRun, run_batch

PREREGISTRATION = route.PREREGISTRATION
PROTECT_SEEDS = (42, 685800)
_RANK = {Commitment.LOW: 1, Commitment.MEDIUM: 2, Commitment.HIGH: 3}


# ---------------------------------------------------------------------------
# Supported configurations (section 5)
# ---------------------------------------------------------------------------


def _is_envelope(settings: dict, seed: int) -> bool:
    expected = {**tp.PROTECT_PROBE_ENVELOPE, "base_seed": seed}
    return (set(settings) == set(expected)
            and all(tp._identical(settings[k], v) for k, v in expected.items()))


def validate_tactical_v2(settings: dict) -> None:
    """ValueError unless TACTICAL_V2 supports these batch settings."""
    if set(settings) != set(tp.PROTECT_PROBE_ENVELOPE):
        raise ValueError("TACTICAL_V2 validation needs every batch option")
    if not settings["enable_v04_commitment_semantics"]:
        if any(_is_envelope(settings, seed) for seed in PROTECT_SEEDS):
            return
        raise ValueError(
            "TACTICAL_V2 requires v0.4a commitment semantics; with v0.4a off only "
            "the exact frozen PROTECT probe at base_seed 42 or 685800 is admitted")
    tp.validate_tactical_v1(settings)


# ---------------------------------------------------------------------------
# Tier R selection (section 3, R2-R5; pure)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RouteChoice:
    option: tuple            # route.RESET or (action_id, commitment)
    q: Fraction
    value: te.TacticalValue | None


def guard_admissible(values, q: dict) -> list:
    """R2: TE-1's stamina guard with the metric Q. An Exhausted-entering
    commitment is admissible only if its Q strictly exceeds every
    non-entering commitment of the same action."""
    kept = []
    for v in values:
        if v.enters_exhausted:
            others = [o for o in values if o.action_id == v.action_id and not o.enters_exhausted]
            if not all(q[(v.action_id, v.requested)] > q[(o.action_id, o.requested)]
                       for o in others):
                continue
        kept.append(v)
    return kept


def select_route(values, q: dict, order: dict) -> RouteChoice | None:
    """R3-R5. None when Tier R is empty (every admissible Q, RESET included,
    is 0). RESET wins only with strictly greater Q; a positive tie goes to the
    non-RESET option; ties among those follow TE-1's ordering."""
    admissible = guard_admissible(values, q)
    q_reset = q[route.RESET]
    best = max((q[(v.action_id, v.requested)] for v in admissible), default=Fraction(0))
    if max(q_reset, best) == 0:
        return None
    if q_reset > best:
        return RouteChoice(route.RESET, q_reset, None)
    tied = [v for v in admissible if q[(v.action_id, v.requested)] == best]
    chosen = max(tied, key=lambda v: (v.axis_realized, v.axis_raw, -v.stamina_cost,
                                      -order[v.action_id], -_RANK[v.requested]))
    return RouteChoice((chosen.action_id, chosen.requested), best, chosen)


def te1_tiers_ab(values, order: dict):
    """TE-1 tiers A and B exactly (te.choose_te1's first loop)."""
    for name, metric in (("terminal", lambda v: v.terminal),
                         ("progress", lambda v: v.progress)):
        admitted = te._guarded([v for v in values if metric(v) > 0], metric)
        if admitted:
            return name, max(admitted, key=te._tiebreak(order, metric))
    return None


def te1_tier_d(values, order: dict):
    """TE-1 position tier exactly (reduce to the cheapest qualifying)."""
    position = te._reduced(values, lambda v: v.axis_raw > 0 and v.axis_realized > 0)
    if position:
        return max(position, key=te._tiebreak(order, lambda v: v.axis_realized))
    return None


def reason_for(side: Side, tier: str, action_id: str | None, match) -> str:
    if side is Side.BOTTOM:
        return tp.reason_for(side, tier)
    if tier in ("terminal", "progress"):
        return "submission"
    if tier == "route":
        if action_id is None:
            return "reset"
        return "setup" if match.setup_policy.target_for_builder(action_id) else "position"
    if tier == "position":
        return "position"
    if tier == "reset":
        return "reset"
    raise tp.TacticalContractError(f"TE-2E tier {tier!r} has no Top reason")


def _decision(side: Side, tier: str, value: te.TacticalValue | None, match) -> BatchDecision:
    reason = reason_for(side, tier, value.action_id if value else None, match)
    if value is None:
        return BatchDecision(None, reason, 0.0, 0.0, 0.0, 0.0)
    return BatchDecision(
        action_id=value.action_id, reason=reason, escape_probability=0.0,
        submission_progress_probability=float(max(value.terminal, value.progress)),
        expected_raw_axis=float(value.axis_raw),
        expected_realized_axis=float(value.axis_realized))


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RouteRecord:
    """One Top decision's Tier R evaluation (reported, not part of the tape)."""

    match_index: int
    call_index: int
    tier: str
    q: tuple                  # ((option label, Q as str), ...)
    chosen: str | None
    nodes: int


def _label(option) -> str:
    action, c = option
    return "RESET" if option == route.RESET else f"{action}|{c.value}"


class TacticalV2Policy(tp.TacticalV1Policy):
    """TE-2E for Top, Stage 1B TE-1 for Bottom. The context is the TACTICAL_V1
    projection-v2 Context: Bottom's TE-1 and both O-3 contracts are TE-1."""

    budget = route.RouteBudget()

    def __init__(self, context: v2.Context) -> None:
        super().__init__(context)
        self.route_records: list[RouteRecord] = []

    def start_match(self, *, match_index: int, match, controller) -> None:
        super().start_match(match_index=match_index, match=match, controller=controller)
        self._route = route.RouteModel(match, self.context, budget=self.budget)

    def _entry(self, match, *, kind, branch, allowed, forced_by) -> tp.TapeEntry:
        side = match.initiator
        if side is Side.BOTTOM:
            return super()._entry(match, kind=kind, branch=branch, allowed=allowed,
                                  forced_by=forced_by)
        tier, value, record = self._te2e(match, branch, allowed)
        self.route_records.append(record)
        return tp.TapeEntry(
            match_index=self._match_index, call_index=self._calls, kind=kind, side=side,
            branch=branch, allowed=allowed, forced_by=forced_by, tier=tier,
            decision=_decision(side, tier, value, match),
            requested=value.requested if value is not None else None)

    def _te2e(self, match, branch, allowed):
        state = branch.state
        model = self.context.model
        legal = match.legal_action_ids(Side.TOP)
        order = {a: i for i, a in enumerate(match.legal_action_ids())}
        values = []
        for action_id in legal:
            seen = set()
            for c in allowed:
                effective = te.funded(match, c, state.top.current)
                if effective in seen:
                    continue
                seen.add(effective)
                values.append(te.evaluate(match, model, state, action_id, c, project=False))
        ab = te1_tiers_ab(values, order)

        def record(tier, q=(), chosen=None, nodes=0):
            return RouteRecord(self._match_index, self._calls, tier, q, chosen, nodes)

        if ab is not None:
            return ab[0], ab[1], record(ab[0])
        rb = route.route_branch_of(match, self._controller)
        q = self._route.root_values(rb, tuple(allowed))
        labels = tuple((_label(o), str(x)) for o, x in q.items())
        nodes = self._route.decision_nodes
        choice = select_route(values, q, order)
        if choice is not None:
            return "route", choice.value, record("route", labels, _label(choice.option), nodes)
        position = te1_tier_d(values, order)
        if position is not None:
            return "position", position, record("position", labels, None, nodes)
        return "reset", None, record("reset", labels, None, nodes)


class ReplayV2Policy(tp.ReplayInitiatorPolicy):
    """Inertness replay for TACTICAL_V2 (no evaluation, desync = failure)."""

    def _entry(self, match, *, kind, branch, allowed, forced_by):
        if self._position >= len(self._recorded):
            raise tp.ReplayDesync("underflow", "more policy.choose calls than tape entries")
        entry = self._recorded[self._position]
        self._position += 1
        if (entry.match_index, entry.call_index) != (self._match_index, self._calls):
            raise tp.ReplayDesync("order", f"call {(self._match_index, self._calls)}")
        if entry.kind is not kind:
            raise tp.ReplayDesync("flag", f"call is {kind.value}, tape is {entry.kind.value}")
        side = match.initiator
        if (entry.side, entry.branch, entry.allowed, entry.forced_by) != (
                side, branch, allowed, forced_by):
            raise tp.ReplayDesync("context", "window state differs from the recorded call")
        action = entry.decision.action_id
        if ((action is not None and action not in match.legal_action_ids(side))
                or entry.decision.reason != reason_for(side, entry.tier, action, match)
                or (entry.requested is None) != (action is None)):
            raise tp.ReplayDesync("decision", "recorded decision does not fit this window")
        return entry


_REPLAY_TAPE: ContextVar = ContextVar("tactical_v2_replay_tape", default=None)


@contextmanager
def replaying(tape):
    token = _REPLAY_TAPE.set(tuple(tape))
    try:
        yield
    finally:
        _REPLAY_TAPE.reset(token)


def create_policy(settings: dict):
    """The batch's TACTICAL_V2 policy for validated settings."""
    context = v2.Context.from_batch_kwargs(
        {**settings, "initiator_policy": BatchInitiatorPolicy.TACTICAL_V1})
    tape = _REPLAY_TAPE.get()
    if tape is not None:
        return ReplayV2Policy(context, tape)
    return TacticalV2Policy(context)


def replay_batch(tape, **kwargs) -> BatchRun:
    with replaying(tape):
        return run_batch(initiator_policy=BatchInitiatorPolicy.TACTICAL_V2, **kwargs)
