from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache

from ..positions.mount.catalog import (
    BOTTOM_ELBOW_KNEE_ESCAPE,
    ENTITY_BY_ID,
    ENTITIES,
    TOP_ACTIONS,
    BOTTOM_ACTIONS,
    TOP_RESPONSES,
    BOTTOM_RESPONSES,
    actions_for,
    responses_for,
)
from ..positions.mount.matchups import RAW_GRADES, raw_grade
from ..engine.mount_engine import MOUNT_ENGINE
from ..positions.mount.rules import MOUNT_RULES
from ..domain.action import Commitment
from ..domain.model import Band, BottomBehavior, ExitDestination, Grade, Side, TopBehavior
from ..positions.mount.names import RESOLVER, normalize_name

V0_TOP_BEHAVIORS = (TopBehavior.PRESSURE, TopBehavior.HOLD)


@dataclass(frozen=True, slots=True)
class ReachabilityHit:
    action_id: str
    top_behavior: TopBehavior
    destination: ExitDestination
    band: Band
    axis: float
    response_id: str
    final_grade: Grade


@dataclass(slots=True)
class CheckReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)
    reachable_exits: dict[ExitDestination, list[str]] = field(default_factory=dict)
    escape_reachability: dict[
        tuple[str, TopBehavior, ExitDestination], list[ReachabilityHit]
    ] = field(default_factory=dict)
    never_best_responses: list[str] = field(default_factory=list)
    perfect_response_lock: bool = False

    @property
    def ok(self) -> bool:
        return not self.errors


def _sample_axes() -> list[float]:
    return [round(i / 100, 2) for i in range(10, 401)]


def _final_grade_without_behavior(action_id: str, response_id: str, side: Side, band: Band) -> Grade:
    result = MOUNT_ENGINE.resolve_action(
        axis={Band.LOOSE: 0.50, Band.STABLE: 1.50, Band.STRONG: 2.50, Band.LOCKED: 3.50}[band],
        band=band,
        initiator=side,
        action_id=action_id,
        response_id=response_id,
        top_behavior=TopBehavior.PRESSURE,
        bottom_behavior=BottomBehavior.ESCAPE,
    )
    return result.final_grade


def _collect_escape_reachability(
    *, external_grade_modifier: int = 0
) -> dict[
    tuple[str, TopBehavior, ExitDestination], list[ReachabilityHit]
]:
    reachability: dict[
        tuple[str, TopBehavior, ExitDestination], list[ReachabilityHit]
    ] = {}
    for action in BOTTOM_ACTIONS:
        if not action.escape_capable:
            continue
        destinations = set(action.exit_map.values()) | set(action.band_exit_overrides.values())
        for top_behavior in V0_TOP_BEHAVIORS:
            for destination in destinations:
                reachability[(action.id, top_behavior, destination)] = []
            for band in Band:
                for axis in _sample_axes():
                    if not MOUNT_RULES.axis_can_have_band(axis, band):
                        continue
                    for response in TOP_RESPONSES:
                        result = MOUNT_ENGINE.resolve_action(
                            axis=axis,
                            band=band,
                            initiator=Side.BOTTOM,
                            action_id=action.id,
                            response_id=response.id,
                            top_behavior=top_behavior,
                            bottom_behavior=BottomBehavior.ESCAPE,
                            external_grade_modifier=external_grade_modifier,
                        )
                        if result.exit_destination is None:
                            continue
                        reachability[(action.id, top_behavior, result.exit_destination)].append(
                            ReachabilityHit(
                                action_id=action.id,
                                top_behavior=top_behavior,
                                destination=result.exit_destination,
                                band=band,
                                axis=axis,
                                response_id=response.id,
                                final_grade=result.final_grade,
                            )
                        )
    return reachability


def _axis_range(hits: list[ReachabilityHit]) -> tuple[float, float] | None:
    if not hits:
        return None
    axes = [hit.axis for hit in hits]
    return min(axes), max(axes)



def render_exhausted_reachability_summary() -> list[str]:
    """Modern v0.1e diagnostic; intentionally excluded from frozen --enumerate."""
    reachability = _collect_escape_reachability(external_grade_modifier=-1)
    lines: list[str] = []
    for action in BOTTOM_ACTIONS:
        if not action.escape_capable:
            continue
        destinations = sorted(
            set(action.exit_map.values()) | set(action.band_exit_overrides.values()),
            key=lambda destination: destination.value,
        )
        for top_behavior in V0_TOP_BEHAVIORS:
            parts: list[str] = []
            for destination in destinations:
                hits = reachability[(action.id, top_behavior, destination)]
                axis_range = _axis_range(hits)
                if axis_range is None:
                    parts.append(f"{destination.value}=UNREACHABLE")
                else:
                    parts.append(
                        f"{destination.value}={axis_range[0]:+.2f}..{axis_range[1]:+.2f}"
                    )
            lines.append(
                f"EXHAUSTED REACHABILITY: {action.canonical_name} / "
                f"Top {top_behavior.value}: {'; '.join(parts)}"
            )
    return lines


def render_reset_lock_probe() -> str:
    """Modern v0.1 diagnostic for the always-RESET full-information strategy."""
    from ..engine.match import MountMatch

    match = MountMatch(
        initial_clock=300,
        starting_axis=1.50,
        interval_seconds=5,
    )
    match.set_behaviors(
        top=TopBehavior.PRESSURE,
        bottom=BottomBehavior.ESCAPE,
    )

    while not match.ended:
        match.advance()
        if match.ended:
            break
        match.reset_window()

    reason = match.exit_reason or "None"
    return (
        "RESET LOCK PROBE: Top PRESSURE+RESET vs Bottom ESCAPE+RESET "
        f"-> {reason}; axis {match.axis:+.2f}; band {match.band.value}; "
        f"Top stamina {match.top.stamina.current}; "
        f"Bottom stamina {match.bottom.stamina.current}"
    )


class V02GateStatus(str, Enum):
    OPEN = "OPEN"
    PASS = "PASS"
    ACCEPTED = "ACCEPTED"
    REVIEW = "REVIEW"
    UNAVAILABLE = "UNAVAILABLE"
    DEFERRED = "DEFERRED"


@dataclass(frozen=True, slots=True)
class V02GateMeasurement:
    number: int
    name: str
    status: V02GateStatus
    metric: str
    evidence: str

    def render(self) -> str:
        return (
            f"V0.2 DOD GATE {self.number} [{self.status.value}]: "
            f"{self.name} — {self.metric}; {self.evidence}"
        )


_V02_BAND_ANCHORS = {
    Band.LOOSE: 0.50,
    Band.STABLE: 1.50,
    Band.STRONG: 2.50,
    Band.LOCKED: 3.50,
}


@dataclass(frozen=True, slots=True)
class V02ReadyGateEvidence:
    reachable_states: int
    contested_best_states: int
    lock_free_states: int
    guaranteed_attacker_states: int


def _best_counter_response_id(match, action_id: str) -> str:
    """Choose the legal response that is worst for the current initiator."""
    side = match.initiator
    top_behavior = match.top.behavior
    bottom_behavior = match.bottom.behavior
    candidates: list[tuple[int, float, str]] = []
    for response_id in match.legal_response_ids(action_id):
        result = match.engine.resolve_action(
            axis=match.axis,
            band=match.band,
            initiator=side,
            action_id=action_id,
            response_id=response_id,
            top_behavior=top_behavior,
            bottom_behavior=bottom_behavior,
        )
        world_delta = result.axis_after - match.axis
        attacker_delta = world_delta if side is Side.TOP else -world_delta
        candidates.append(
            (int(result.final_grade), attacker_delta, response_id)
        )
    if not candidates:
        raise RuntimeError(f"No legal response to {action_id!r}")
    return min(candidates)[2]


@lru_cache(maxsize=1)
def _v02_ready_gate_evidence() -> dict[Side, V02ReadyGateEvidence]:
    """Measure reachable Ready states against best-counter play.

    A state counts only if two builder attempts can reach Ready while the
    responder always chooses the legal response that is worst for the builder.

    Gate 1 also rejects the opposite solved extreme: any reachable Ready state
    where every legal response yields Success-or-better is counted as a
    guaranteed-attacker state.
    """
    from ..engine.match import MountMatch

    totals = {
        Side.TOP: [0, 0, 0, 0],
        Side.BOTTOM: [0, 0, 0, 0],
    }
    probe = MountMatch(enable_v02_setup=True)

    for rule in probe.setup_policy.rules:
        target_action_id = rule.target_action_id
        builder_action_id = rule.builder_action_id
        action = probe.engine.catalog.get(target_action_id)
        side = action.side

        for _band, axis in _V02_BAND_ANCHORS.items():
            for top_behavior in TopBehavior:
                for bottom_behavior in BottomBehavior:
                    match = MountMatch(
                        initial_clock=300,
                        starting_axis=axis,
                        interval_seconds=5,
                        enable_v02_setup=True,
                    )
                    match.initiator = side
                    match.set_behaviors(
                        top=top_behavior,
                        bottom=bottom_behavior,
                    )

                    for _ in range(2):
                        match.initiator = side
                        response_id = _best_counter_response_id(
                            match,
                            builder_action_id,
                        )
                        match.attempt(
                            action_id=builder_action_id,
                            response_id=response_id,
                            commitment=Commitment.MEDIUM,
                        )

                    if not match.setup_state.is_ready(target_action_id):
                        continue

                    totals[side][0] += 1
                    match.initiator = side
                    legal = match.legal_response_ids(target_action_id)
                    finals = [
                        match.engine.resolve_action(
                            axis=match.axis,
                            band=match.band,
                            initiator=side,
                            action_id=target_action_id,
                            response_id=response_id,
                            top_behavior=match.top.behavior,
                            bottom_behavior=match.bottom.behavior,
                            post_positional_grade_override=(
                                match.setup_policy.ready_final_grade_override(
                                    target_action_id,
                                    response_id,
                                )
                            ),
                        ).final_grade
                        for response_id in legal
                    ]
                    best_counter = min(finals) if finals else None
                    if best_counter is Grade.CONTESTED:
                        totals[side][1] += 1
                    if best_counter is not None and best_counter > Grade.FAILURE:
                        totals[side][2] += 1
                    if best_counter is not None and best_counter >= Grade.SUCCESS:
                        totals[side][3] += 1

    return {
        side: V02ReadyGateEvidence(
            reachable_states=values[0],
            contested_best_states=values[1],
            lock_free_states=values[2],
            guaranteed_attacker_states=values[3],
        )
        for side, values in totals.items()
    }


@lru_cache(maxsize=1)
def _v02_ready_lock_free_states() -> dict[Side, int]:
    """Compatibility view of Gate 1 lock-free Ready states."""
    evidence = _v02_ready_gate_evidence()
    return {
        side: item.lock_free_states
        for side, item in evidence.items()
    }


@lru_cache(maxsize=1)
def _v02_standard_batch():
    """One reproducible batch shared by Gates 4 and 5."""
    from ..interfaces.batch import run_escape_first_batch

    return run_escape_first_batch(
        matches=100,
        base_seed=42,
        top_behavior=TopBehavior.PRESSURE,
        bottom_behavior=BottomBehavior.ESCAPE,
        commitment=Commitment.MEDIUM,
        initial_clock=300,
        starting_axis=1.50,
        interval_seconds=5,
        top_stamina=100,
        bottom_stamina=100,
        enable_v02_setup=True,
    )


def _resolution_signature(result) -> tuple:
    return (
        result.final_grade,
        round(result.axis_after, 8),
        result.band_after,
        result.exit_destination,
        result.escape_threshold_reached,
        result.failure_clamp_used,
        result.floor_clamp_used,
    )


@lru_cache(maxsize=1)
def _responder_exhaustion_differential_count() -> int:
    """Count current one-exchange outcomes changed only by responder exhaustion.

    This deliberately holds the initiator fresh and skips normal-speed advance,
    isolating responder stamina from the existing initiator exhaustion rule.
    """
    from ..engine.match import MountMatch

    differences = 0
    for side in (Side.TOP, Side.BOTTOM):
        for band, axis in _V02_BAND_ANCHORS.items():
            for top_behavior in V0_TOP_BEHAVIORS:
                for bottom_behavior in (BottomBehavior.ESCAPE, BottomBehavior.PROTECT):
                    for action in actions_for(side):
                        for response in responses_for(side.opponent):
                            signatures = []
                            for responder_stamina in (100, 25):
                                match = MountMatch(
                                    initial_clock=300,
                                    starting_axis=axis,
                                    interval_seconds=5,
                                )
                                match.initiator = side
                                match.set_behaviors(
                                    top=top_behavior,
                                    bottom=bottom_behavior,
                                )
                                match.competitor(side).stamina.set_current(100)
                                match.competitor(side.opponent).stamina.set_current(
                                    responder_stamina
                                )
                                try:
                                    attempt = match.attempt(
                                        action_id=action.id,
                                        response_id=response.id,
                                        commitment=Commitment.MEDIUM,
                                    )
                                except Exception as exc:
                                    signatures.append(
                                        ("ERROR", type(exc).__name__, str(exc))
                                    )
                                else:
                                    signatures.append(
                                        _resolution_signature(attempt.resolution)
                                    )
                            if signatures[0] != signatures[1]:
                                differences += 1
    return differences


@lru_cache(maxsize=1)
def _exhausted_positive_weight_escape_routes_by_top_behavior() -> dict[
    TopBehavior, frozenset[tuple[str, ExitDestination]]
]:
    """Exhausted Bottom routes reachable against positive-weight batch responses.

    Gate 6 is condition-sensitive: it passes only when every current Top
    behavior leaves at least one positive-weight route.
    """
    from ..interfaces.blind import RandomBlindResponder

    positive_responses = tuple(
        response_id
        for response_id, weight in RandomBlindResponder.POLICY[Side.TOP]
        if weight > 0
    )
    routes: dict[TopBehavior, set[tuple[str, ExitDestination]]] = {
        behavior: set() for behavior in TopBehavior
    }

    for top_behavior in TopBehavior:
        for action in BOTTOM_ACTIONS:
            if not action.escape_capable:
                continue
            for band in Band:
                for axis in _sample_axes():
                    if not MOUNT_RULES.axis_can_have_band(axis, band):
                        continue
                    for response_id in positive_responses:
                        result = MOUNT_ENGINE.resolve_action(
                            axis=axis,
                            band=band,
                            initiator=Side.BOTTOM,
                            action_id=action.id,
                            response_id=response_id,
                            top_behavior=top_behavior,
                            bottom_behavior=BottomBehavior.ESCAPE,
                            external_grade_modifier=-1,
                        )
                        if result.exit_destination is not None:
                            routes[top_behavior].add(
                                (action.id, result.exit_destination)
                            )

    return {
        behavior: frozenset(found)
        for behavior, found in routes.items()
    }


@lru_cache(maxsize=1)
def _exhausted_positive_weight_escape_hits() -> tuple[ReachabilityHit, ...]:
    """Compatibility view of Gate 6 reachability, including CONSERVE."""
    from ..interfaces.blind import RandomBlindResponder

    positive_responses = tuple(
        response_id
        for response_id, weight in RandomBlindResponder.POLICY[Side.TOP]
        if weight > 0
    )
    hits: list[ReachabilityHit] = []
    seen: set[tuple] = set()

    for top_behavior in TopBehavior:
        for action in BOTTOM_ACTIONS:
            if not action.escape_capable:
                continue
            for band in Band:
                for axis in _sample_axes():
                    if not MOUNT_RULES.axis_can_have_band(axis, band):
                        continue
                    for response_id in positive_responses:
                        result = MOUNT_ENGINE.resolve_action(
                            axis=axis,
                            band=band,
                            initiator=Side.BOTTOM,
                            action_id=action.id,
                            response_id=response_id,
                            top_behavior=top_behavior,
                            bottom_behavior=BottomBehavior.ESCAPE,
                            external_grade_modifier=-1,
                        )
                        if result.exit_destination is None:
                            continue
                        key = (
                            action.id,
                            top_behavior,
                            result.exit_destination,
                            band,
                            axis,
                            response_id,
                            result.final_grade,
                        )
                        if key in seen:
                            continue
                        seen.add(key)
                        hits.append(
                            ReachabilityHit(
                                action_id=action.id,
                                top_behavior=top_behavior,
                                destination=result.exit_destination,
                                band=band,
                                axis=axis,
                                response_id=response_id,
                                final_grade=result.final_grade,
                            )
                        )
    return tuple(hits)


@lru_cache(maxsize=1)
def _exhausted_bottom_dynamic_escape_counts() -> dict[TopBehavior, int]:
    """100-match path-B probe for behavior-specific exhausted lockouts.

    Bottom starts Exhausted at 25 while Top starts fresh at 100. Behaviors stay
    fixed and v0.2 setup is enabled. A nonzero escape count demonstrates a real
    route out of the static lockout through match evolution (currently Top
    exhaustion from setup work), without giving Bottom recovery behavior.
    """
    from ..interfaces.batch import run_escape_first_batch

    counts: dict[TopBehavior, int] = {}
    for top_behavior in TopBehavior:
        summary = run_escape_first_batch(
            matches=100,
            base_seed=42,
            top_behavior=top_behavior,
            bottom_behavior=BottomBehavior.ESCAPE,
            commitment=Commitment.MEDIUM,
            initial_clock=300,
            starting_axis=1.50,
            interval_seconds=5,
            top_stamina=100,
            bottom_stamina=25,
            enable_v02_setup=True,
        )
        counts[top_behavior] = sum(
            summary.outcome_counts.get(destination.value, 0)
            for destination in ExitDestination
        )
    return counts


@lru_cache(maxsize=1)
def _commitment_low_dominance_probe() -> tuple[bool, int]:
    """Return (LOW strictly dominates higher commitments, advantage-state count).

    A higher commitment breaks LOW dominance when, in an otherwise-identical
    fully funded state, it produces a strictly better current resolution
    outcome for the initiator: higher final grade, a terminal exit LOW did not
    obtain, or more favorable realized axis movement.

    When v0.2 adds setup/readiness/recognition state, extend this outcome
    comparison rather than manually changing Gate 7.
    """
    from ..engine.match import MountMatch

    advantage_states = 0
    probe_match = MountMatch()
    low_cost = probe_match.stamina_cost_policy.cost(Commitment.LOW)
    higher_costs = [
        probe_match.stamina_cost_policy.cost(Commitment.MEDIUM),
        probe_match.stamina_cost_policy.cost(Commitment.HIGH),
    ]
    low_has_strict_cost_advantage = all(
        low_cost < cost for cost in higher_costs
    )

    for side in (Side.TOP, Side.BOTTOM):
        for band, axis in _V02_BAND_ANCHORS.items():
            for top_behavior in V0_TOP_BEHAVIORS:
                for bottom_behavior in (BottomBehavior.ESCAPE, BottomBehavior.PROTECT):
                    for action in actions_for(side):
                        for response in responses_for(side.opponent):
                            results = {}
                            for commitment in Commitment:
                                match = MountMatch(
                                    initial_clock=300,
                                    starting_axis=axis,
                                    interval_seconds=5,
                                )
                                match.initiator = side
                                match.set_behaviors(
                                    top=top_behavior,
                                    bottom=bottom_behavior,
                                )
                                match.competitor(side).stamina.set_current(100)
                                attempt = match.attempt(
                                    action_id=action.id,
                                    response_id=response.id,
                                    commitment=commitment,
                                )
                                results[commitment] = attempt.resolution

                            low = results[Commitment.LOW]
                            low_world_delta = low.axis_after - axis
                            low_axis = (
                                low_world_delta
                                if side is Side.TOP
                                else -low_world_delta
                            )
                            for higher in (Commitment.MEDIUM, Commitment.HIGH):
                                candidate = results[higher]
                                candidate_world_delta = candidate.axis_after - axis
                                candidate_axis = (
                                    candidate_world_delta
                                    if side is Side.TOP
                                    else -candidate_world_delta
                                )
                                better = (
                                    candidate.final_grade > low.final_grade
                                    or (
                                        candidate.exit_destination is not None
                                        and low.exit_destination is None
                                    )
                                    or candidate_axis > low_axis + 1e-12
                                )
                                if better:
                                    advantage_states += 1

    low_strictly_dominates = (
        low_has_strict_cost_advantage
        and advantage_states == 0
    )
    return low_strictly_dominates, advantage_states



def _submission_finish_present() -> bool:
    """Whether Mount currently has a real submission-finish action.

    Gate 2's deferral expires automatically once v0.3 supplies a finish
    surface. At that point a still-locked RESET probe becomes OPEN again and
    must be solved by the actual stalling/progress rule.
    """
    return any(
        action.category == "SUBMISSION_FINISH"
        for side in (Side.TOP, Side.BOTTOM)
        for action in actions_for(side)
    )

def measure_v02_definition_of_done(
    report: CheckReport | None = None,
) -> tuple[V02GateMeasurement, ...]:
    """Compute v0.2 gate status from current executable evidence."""
    if report is None:
        report = run_checks()

    # Gate 1: Ready must be reachable against best-counter play, break the
    # defender's perfect-response lock, and avoid the opposite solved extreme
    # where every legal Ready response is Success-or-better.
    ready_evidence = _v02_ready_gate_evidence()
    gate1_pass = all(
        ready_evidence[side].reachable_states > 0
        and ready_evidence[side].contested_best_states
        == ready_evidence[side].reachable_states
        for side in (Side.TOP, Side.BOTTOM)
    )

    # Gate 2: existing standardized RESET probe.
    reset_probe = render_reset_lock_probe()
    reset_locked_timeout = (
        "TIMEOUT — Mount retained" in reset_probe
        and "band Locked" in reset_probe
    )
    submission_finish_present = _submission_finish_present()

    # Gates 4/5 share the same deterministic standard batch.
    standard_batch = _v02_standard_batch()
    bridge_count = standard_batch.bottom_action_counts.get("Bridge", 0)
    bridge_setup_count = standard_batch.bottom_setup_action_count
    bridge_completed_setup_builds = standard_batch.bottom_completed_setup_build_count
    bottom_completed_setup_chains = standard_batch.bottom_completed_setup_chain_count
    top_followup_position_attacks_per_match = (
        standard_batch.top_followup_position_attack_count
        / standard_batch.matches
    )
    top_followup_completed_setup_builds_per_match = (
        standard_batch.top_followup_completed_setup_build_count
        / standard_batch.matches
    )
    top_followup_meaningful_per_match = (
        top_followup_position_attacks_per_match
        + top_followup_completed_setup_builds_per_match
    )
    top_followup_threshold = 1.0
    top_followup_margin = (
        top_followup_meaningful_per_match - top_followup_threshold
    )

    # Gate 3: responder-only outcome differential.
    responder_differences = _responder_exhaustion_differential_count()

    # Gate 6: every current Top behavior must leave at least one
    # positive-weight Exhausted-Bottom escape route.
    exhausted_routes_by_behavior = (
        _exhausted_positive_weight_escape_routes_by_top_behavior()
    )
    exhausted_route_counts = {
        behavior: len(routes)
        for behavior, routes in exhausted_routes_by_behavior.items()
    }
    every_behavior_has_escape = all(
        count > 0 for count in exhausted_route_counts.values()
    )
    exhausted_dynamic_escape_counts = (
        _exhausted_bottom_dynamic_escape_counts()
    )
    static_lockout_behaviors = tuple(
        behavior
        for behavior, count in exhausted_route_counts.items()
        if count == 0
    )
    every_static_lockout_has_dynamic_route = (
        bool(static_lockout_behaviors)
        and all(
            exhausted_dynamic_escape_counts[behavior] > 0
            for behavior in static_lockout_behaviors
        )
    )

    # Gate 7: exhaustive funded LOW-dominance probe.
    low_dominates, commitment_advantages = _commitment_low_dominance_probe()

    return (
        V02GateMeasurement(
            number=1,
            name="perfect-response lock",
            status=V02GateStatus.PASS if gate1_pass else V02GateStatus.OPEN,
            metric=(
                "Ready states against best counters="
                f"top:{ready_evidence[Side.TOP].reachable_states}/"
                f"best-contested:{ready_evidence[Side.TOP].contested_best_states}/"
                f"guaranteed:{ready_evidence[Side.TOP].guaranteed_attacker_states},"
                f"bottom:{ready_evidence[Side.BOTTOM].reachable_states}/"
                f"best-contested:{ready_evidence[Side.BOTTOM].contested_best_states}/"
                f"guaranteed:{ready_evidence[Side.BOTTOM].guaranteed_attacker_states}"
            ),
            evidence=(
                "every reachable Ready state has exactly Contested as the responder's best legal result"
                if gate1_pass
                else
                "Gate requires Ready reachability against best-counter play and exactly Contested as the best legal response in every reachable Ready state"
            ),
        ),
        V02GateMeasurement(
            number=2,
            name="RESET/stalling",
            status=(
                V02GateStatus.PASS
                if not reset_locked_timeout
                else (
                    V02GateStatus.DEFERRED
                    if not submission_finish_present
                    else V02GateStatus.OPEN
                )
            ),
            metric=(
                f"locked_timeout={reset_locked_timeout}; "
                f"submission_finish_present={submission_finish_present}"
            ),
            evidence=(
                reset_probe
                + (
                    "; deferred to v0.3 because Locked Top currently has no "
                    "submission-finish/progress action, so a stalling penalty "
                    "would punish a state with no legal way to advance"
                    if reset_locked_timeout and not submission_finish_present
                    else ""
                )
            ),
        ),
        V02GateMeasurement(
            number=3,
            name="responder stamina",
            status=(
                V02GateStatus.PASS
                if responder_differences > 0
                else V02GateStatus.OPEN
            ),
            metric=f"fresh-vs-exhausted responder outcome differences={responder_differences}",
            evidence=(
                "at least one isolated exchange changes when only responder stamina changes"
                if responder_differences > 0
                else
                "isolated responder exhaustion changes no current exchange outcome"
            ),
        ),
        V02GateMeasurement(
            number=4,
            name="Bridge setup role",
            status=(
                V02GateStatus.PASS
                if bridge_completed_setup_builds > 0
                else V02GateStatus.OPEN
            ),
            metric=(
                f"standard batch Bridge selections={bridge_count}/"
                f"{standard_batch.matches}; setup-priority selections="
                f"{bridge_setup_count}; completed-chain Bridge builds="
                f"{bridge_completed_setup_builds}; completed Bottom chains="
                f"{bottom_completed_setup_chains}"
            ),
            evidence=(
                "Bridge setup work contributes to at least one consumed Trap-and-Roll chain"
                if bridge_completed_setup_builds > 0
                else
                "Bridge may be attempted, but no Bridge setup work completes into a consumed Trap-and-Roll chain"
            ),
        ),
        V02GateMeasurement(
            number=5,
            name="Top post-opening activity",
            status=(
                V02GateStatus.PASS
                if top_followup_meaningful_per_match > top_followup_threshold
                else V02GateStatus.OPEN
            ),
            metric=(
                "standard batch Top follow-up meaningful initiations/match="
                f"{top_followup_meaningful_per_match:.3f} "
                f"(position:{top_followup_position_attacks_per_match:.3f},"
                f"completed-setup-builds:{top_followup_completed_setup_builds_per_match:.3f}); "
                f"threshold={top_followup_threshold:.3f}; "
                f"margin={top_followup_margin:+.3f}"
            ),
            evidence="opening attack excluded; setup builders count only when their Ready target is later consumed; margin is measured against the unchanged >1.000 threshold",
        ),
        V02GateMeasurement(
            number=6,
            name="Exhausted Bottom escape reachability",
            status=(
                V02GateStatus.PASS
                if every_behavior_has_escape
                else (
                    V02GateStatus.ACCEPTED
                    if every_static_lockout_has_dynamic_route
                    else V02GateStatus.OPEN
                )
            ),
            metric=(
                "positive-weight exhausted escape routes by Top behavior="
                + ",".join(
                    f"{behavior.value}:{exhausted_route_counts[behavior]}"
                    for behavior in TopBehavior
                )
                + "; dynamic exhausted-Bottom escapes/100="
                + ",".join(
                    f"{behavior.value}:{exhausted_dynamic_escape_counts[behavior]}"
                    for behavior in TopBehavior
                )
            ),
            evidence=(
                "every Top behavior leaves at least one static Exhausted-Bottom escape route"
                if every_behavior_has_escape
                else (
                    "path B accepted: each static lockout behavior has a measured no-recovery escape route through match evolution"
                    if every_static_lockout_has_dynamic_route
                    else
                    "at least one static lockout behavior has no measured no-recovery route out"
                )
            ),
        ),
        V02GateMeasurement(
            number=7,
            name="commitment meaning",
            status=(
                V02GateStatus.OPEN
                if low_dominates
                else V02GateStatus.PASS
            ),
            metric=(
                f"low_strictly_dominates={low_dominates}; "
                f"higher-commitment advantage states={commitment_advantages}"
            ),
            evidence=(
                "cost-only LOW dominance remains on the measured outcome surface"
                if low_dominates
                else
                "LOW no longer strictly dominates the measured commitment outcome surface"
            ),
        ),
    )


def render_v02_definition_of_done(
    report: CheckReport | None = None,
) -> tuple[str, ...]:
    return tuple(
        gate.render()
        for gate in measure_v02_definition_of_done(report)
    )


def render_v02_definition_of_done_baseline() -> tuple[str, ...]:
    """Compatibility alias for the original fixed-string renderer."""
    return render_v02_definition_of_done()

def run_checks() -> CheckReport:
    report = CheckReport()

    if len(ENTITIES) != 12:
        report.errors.append(f"Expected 12 canonical entities, found {len(ENTITIES)}")
    if len(TOP_ACTIONS) != 3 or len(BOTTOM_ACTIONS) != 3:
        report.errors.append("Expected exactly three actions per side")
    if len(TOP_RESPONSES) != 3 or len(BOTTOM_RESPONSES) != 3:
        report.errors.append("Expected exactly three responses per side")
    if len(RAW_GRADES) != 18:
        report.errors.append(f"Expected 18 raw lookup entries, found {len(RAW_GRADES)}")

    expected = {
        (action.id, response.id)
        for side in (Side.TOP, Side.BOTTOM)
        for action in actions_for(side)
        for response in responses_for(side.opponent)
    }
    actual = set(RAW_GRADES)
    for missing in sorted(expected - actual):
        report.errors.append(f"Missing lookup entry: {missing[0]} vs {missing[1]}")
    for extra in sorted(actual - expected):
        report.errors.append(f"Unexpected lookup entry: {extra[0]} vs {extra[1]}")

    ids = [entity.id for entity in ENTITIES]
    if len(ids) != len(set(ids)):
        report.errors.append("Stable IDs are not unique")

    if RESOLVER.collision_map():
        report.errors.append(f"Normalized aliases collide: {RESOLVER.collision_map()}")

    for forbidden in ("S-Mount", "Elbow-Knee Connection", "High Mount", "Hip Frame", "Body Frame"):
        try:
            RESOLVER.resolve(forbidden)
        except ValueError:
            pass
        else:
            report.errors.append(f"Reserved/misleading name unexpectedly resolves: {forbidden!r}")

    try:
        upa = RESOLVER.resolve("upa")
        if upa.canonical_name != "Trap-and-Roll Escape":
            report.errors.append("'upa' does not resolve to Trap-and-Roll Escape")
    except ValueError as exc:
        report.errors.append(str(exc))

    for entity in ENTITIES:
        if "+" in entity.canonical_name or "&" in entity.canonical_name:
            report.errors.append(f"Canonical name contains + or &: {entity.canonical_name}")

    if normalize_name("follow+knee") != "follow and knee":
        report.errors.append("'+' is not replaced as a character during normalization")
    if normalize_name("follow&knee") != "follow and knee":
        report.errors.append("'&' is not replaced as a character during normalization")
    for value in (
        "Repummel",
        "Hip Follow + Knee Re-Pummel",
        "Hip Follow & Knee Repummel",
        "hip_follow_and_knee_repummel",
        "HIP-FOLLOW-AND-KNEE-RE-PUMMEL",
    ):
        try:
            if RESOLVER.resolve(value).canonical_name != "Hip Follow and Knee Re-Pummel":
                report.errors.append(f"Hip Follow alias resolves incorrectly: {value!r}")
        except ValueError as exc:
            report.errors.append(str(exc))

    bridge = next(e for e in ENTITIES if e.canonical_name == "Bridge")
    elbow = ENTITY_BY_ID[BOTTOM_ELBOW_KNEE_ESCAPE]
    trap = next(e for e in ENTITIES if e.canonical_name == "Trap-and-Roll Escape")
    americana = next(e for e in ENTITIES if e.canonical_name == "Americana Arm Isolation")
    if bridge.escape_capable:
        report.errors.append("Bridge must not be escape-capable")
    if not elbow.escape_capable or not trap.escape_capable:
        report.errors.append("Elbow-Knee and Trap-and-Roll must be escape-capable")
    if americana.exit_map:
        report.errors.append("Americana Arm Isolation must not have a submission finish in v0")

    for responder_side in (Side.TOP, Side.BOTTOM):
        responses = responses_for(responder_side)
        initiator_side = responder_side.opponent
        actions = actions_for(initiator_side)
        for response in responses:
            grades = [raw_grade(action.id, response.id) for action in actions]
            if all(grade <= Grade.FAILURE for grade in grades):
                report.errors.append(f"Response beats every initiated action: {response.canonical_name}")
    for side in (Side.TOP, Side.BOTTOM):
        for action in actions_for(side):
            grades = [raw_grade(action.id, response.id) for response in responses_for(side.opponent)]
            if all(not grade.successful for grade in grades):
                report.errors.append(f"Initiated action never succeeds raw: {action.canonical_name}")
            if all(grade.successful for grade in grades):
                report.errors.append(f"Initiated action always succeeds raw: {action.canonical_name}")

    report.escape_reachability = _collect_escape_reachability()
    aggregate: dict[ExitDestination, list[str]] = {dest: [] for dest in ExitDestination}
    for (action_id, top_behavior, destination), hits in report.escape_reachability.items():
        action = ENTITY_BY_ID[action_id]
        if not hits:
            report.errors.append(
                f"Unreachable Exit Map branch under Top {top_behavior.value}: "
                f"{action.canonical_name} -> {destination.value}"
            )
            continue
        for hit in hits:
            response = ENTITY_BY_ID[hit.response_id]
            aggregate[destination].append(
                f"{action.canonical_name}; Top {top_behavior.value}; {hit.band.value} "
                f"axis={hit.axis:+.2f} vs {response.canonical_name} -> {hit.final_grade.display}"
            )
    report.reachable_exits = aggregate

    for action in BOTTOM_ACTIONS:
        if not action.escape_capable:
            continue
        for destination in sorted(set(action.exit_map.values()) | set(action.band_exit_overrides.values()), key=lambda d: d.value):
            p_hits = report.escape_reachability[(action.id, TopBehavior.PRESSURE, destination)]
            h_hits = report.escape_reachability[(action.id, TopBehavior.HOLD, destination)]
            p_range = _axis_range(p_hits)
            h_range = _axis_range(h_hits)
            if p_range and h_range and p_range != h_range:
                report.info.append(
                    f"TOP-BEHAVIOR REACHABILITY EFFECT: {action.canonical_name} -> {destination.value}; "
                    f"PRESSURE {p_range[0]:+.2f}..{p_range[1]:+.2f}; "
                    f"HOLD {h_range[0]:+.2f}..{h_range[1]:+.2f}"
                )

    response_is_best: dict[str, bool] = {
        response.id: False for response in (*TOP_RESPONSES, *BOTTOM_RESPONSES)
    }
    all_actions_have_failure_counter = True
    for side in (Side.TOP, Side.BOTTOM):
        for action in actions_for(side):
            pairs = [(response, raw_grade(action.id, response.id)) for response in responses_for(side.opponent)]
            best_grade = min(grade for _, grade in pairs)
            if best_grade > Grade.FAILURE:
                all_actions_have_failure_counter = False
            for response, grade in pairs:
                if grade == best_grade:
                    response_is_best[response.id] = True
    report.perfect_response_lock = all_actions_have_failure_counter
    if report.perfect_response_lock:
        report.info.append(
            "PERFECT-RESPONSE LOCK: PRESENT — every initiated action has an unrestricted response that holds it to Failure or worse; known v0 scaffolding limitation"
        )
    for response_id, is_best in response_is_best.items():
        if not is_best:
            response = ENTITY_BY_ID[response_id]
            report.never_best_responses.append(response.canonical_name)
            report.info.append(f"NEVER-BEST (hedge response): {response.canonical_name}")

    cap_hits = 0
    modifier_applications = 0
    for side in (Side.TOP, Side.BOTTOM):
        for action in actions_for(side):
            for response in responses_for(side.opponent):
                raw = raw_grade(action.id, response.id)
                for band in Band:
                    shift = -1 if (
                        (side is Side.BOTTOM and band in {Band.STRONG, Band.LOCKED})
                        or (side is Side.TOP and band is Band.LOOSE)
                    ) else 0
                    if shift:
                        modifier_applications += 1
                        if raw is Grade.STRONG_FAILURE:
                            cap_hits += 1
    if cap_hits:
        report.info.append(
            f"POSITIONAL MODIFIER CAP-HITS: {cap_hits}/{modifier_applications} applicable raw-grade cases clamp at Strong Failure"
        )

    return report


def _render_reachability_ranges(report: CheckReport) -> list[str]:
    lines: list[str] = []
    for action in BOTTOM_ACTIONS:
        if not action.escape_capable:
            continue
        destinations = sorted(set(action.exit_map.values()) | set(action.band_exit_overrides.values()), key=lambda d: d.value)
        for top_behavior in V0_TOP_BEHAVIORS:
            lines.append(f"\n{action.canonical_name} — Top {top_behavior.value}")
            for destination in destinations:
                hits = report.escape_reachability.get((action.id, top_behavior, destination), [])
                lines.append(f"  {destination.value}: {'REACHABLE' if hits else 'UNREACHABLE'}")
                overall = _axis_range(hits)
                if overall is not None:
                    lines.append(f"    Overall axis range: {overall[0]:+.2f}..{overall[1]:+.2f}")
                for band in Band:
                    band_hits = [hit for hit in hits if hit.band is band]
                    band_range = _axis_range(band_hits)
                    if band_range is None:
                        continue
                    responses = sorted({ENTITY_BY_ID[hit.response_id].canonical_name for hit in band_hits})
                    grades = sorted({hit.final_grade.display for hit in band_hits})
                    lines.append(
                        f"    {band.value:<6} {band_range[0]:+.2f}..{band_range[1]:+.2f} | "
                        f"response(s): {', '.join(responses)} | final grade(s): {', '.join(grades)}"
                    )
    return lines


def render_enumeration() -> str:
    lines: list[str] = []
    lines.append("MOUNT v0 — EXHAUSTIVE CHECKER")
    lines.append("=" * 34)

    for side in (Side.TOP, Side.BOTTOM):
        lines.append("")
        lines.append(f"{side.value.upper()} INITIATED — RAW 3x3 MATRIX")
        for action in actions_for(side):
            lines.append(f"\n{action.canonical_name} [{action.id}]")
            for response in responses_for(side.opponent):
                grade = raw_grade(action.id, response.id)
                lines.append(f"  vs {response.canonical_name:<32} -> {grade.display}")

    lines.append("\nVISIBLE-BAND POSITIONAL MODIFIERS (behavior-neutral)")
    lines.append("-" * 52)
    for side in (Side.TOP, Side.BOTTOM):
        for action in actions_for(side):
            for response in responses_for(side.opponent):
                finals = ", ".join(
                    f"{band.value}={_final_grade_without_behavior(action.id, response.id, side, band).display}"
                    for band in Band
                )
                lines.append(f"{action.short_name} vs {response.short_name}: {finals}")

    lines.append("\nBEST-COUNTER ANALYSIS")
    lines.append("-" * 21)
    for side in (Side.TOP, Side.BOTTOM):
        for action in actions_for(side):
            pairs = [(response, raw_grade(action.id, response.id)) for response in responses_for(side.opponent)]
            best_grade = min(grade for _, grade in pairs)
            best = [response for response, grade in pairs if grade == best_grade]
            best_names = ", ".join(response.canonical_name for response in best)
            band_finals = []
            for band in Band:
                finals = [_final_grade_without_behavior(action.id, response.id, side, band) for response in best]
                band_finals.append(f"{band.value}={min(finals).display}")
            succeeds = any(
                _final_grade_without_behavior(action.id, response.id, side, band).successful
                for response in best
                for band in Band
            )
            lines.append(
                f"{action.canonical_name}: best response={best_names}; raw={best_grade.display}; "
                f"{' | '.join(band_finals)}; succeeds vs unrestricted best response={'YES' if succeeds else 'NO'}"
            )

    report = run_checks()
    lines.append("\nESCAPE BRANCH REACHABILITY — FULL TUNING WATCH")
    lines.append("-" * 51)
    lines.extend(_render_reachability_ranges(report))

    lines.append("\nSTRUCTURAL DIAGNOSTICS")
    lines.append("-" * 22)
    if report.perfect_response_lock:
        lines.append("PERFECT-RESPONSE LOCK: PRESENT")
        lines.append("Classification: KNOWN V0 SCAFFOLDING LIMITATION")
        lines.append("Expected future resolution: v0.2 setup/Ready/initiative legality restricts available responses.")
    else:
        lines.append("PERFECT-RESPONSE LOCK: ABSENT")
    for name in report.never_best_responses:
        lines.append(f"INFO: NEVER-BEST (hedge response): {name}")

    lines.append("\nCHECK RESULT")
    lines.append("-" * 12)
    for message in report.info:
        if not message.startswith("PERFECT-RESPONSE") and not message.startswith("NEVER-BEST"):
            lines.append(f"INFO: {message}")
    for warning in report.warnings:
        lines.append(f"WARN: {warning}")
    for error in report.errors:
        lines.append(f"ERROR: {error}")
    lines.append(f"STATUS: {'PASS' if report.ok else 'FAIL'}")
    return "\n".join(lines)
