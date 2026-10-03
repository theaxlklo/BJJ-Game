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
    TOP_AMERICANA_ARM_ISOLATION,
    TOP_AMERICANA_SUBMISSION_FINISH,
    BOTTOM_RESPONSE_FOREARM_FRAME,
    BOTTOM_RESPONSE_TURN_IN_RECOVERY,
    actions_for,
    modern_actions_for,
    responses_for,
)
from ..positions.mount.matchups import RAW_GRADES, raw_grade
from ..engine.mount_engine import MOUNT_ENGINE
from ..engine.stamina import DEFAULT_STAMINA_COST_POLICY
from ..positions.mount.rules import MOUNT_RULES
from ..domain.action import Commitment
from ..domain.model import Band, BottomBehavior, ExitDestination, Grade, Side, TopBehavior
from ..domain.stamina import StaminaBand
from ..domain.submission import SubmissionStage
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


@lru_cache(maxsize=1)
def _v03_informed_standard_batch():
    """Gate-B competent-defender batch: Bottom chooses best legal response."""
    from ..interfaces.batch import (
        BatchResponderMode,
        run_escape_first_batch,
    )

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
        bottom_responder_mode=BatchResponderMode.INFORMED,
        enable_v02_setup=True,
        enable_v03_submissions=True,
    )


@lru_cache(maxsize=1)
def _v03_standard_batch():
    """Frozen v0.3a standard batch from the pre-implementation DoD."""
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
        enable_v03_submissions=True,
    )


@lru_cache(maxsize=1)
def _v04_informed_standard_batch():
    """v0.4a Gate-B batch: informed response choice + public MATCH commitment."""
    from ..interfaces.batch import (
        BatchResponderMode,
        BatchResponseCommitmentMode,
        run_escape_first_batch,
    )

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
        bottom_responder_mode=BatchResponderMode.INFORMED,
        response_commitment_mode=BatchResponseCommitmentMode.MATCH,
        enable_v02_setup=True,
        enable_v03_submissions=True,
        enable_v04_commitment_semantics=True,
    )


@lru_cache(maxsize=1)
def _v04_random_standard_batch():
    """v0.4a random-response/commitment contrast with independent commitment RNG."""
    from ..interfaces.batch import (
        BatchResponderMode,
        BatchResponseCommitmentMode,
        run_escape_first_batch,
    )

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
        bottom_responder_mode=BatchResponderMode.RANDOM,
        response_commitment_mode=BatchResponseCommitmentMode.RANDOM,
        enable_v02_setup=True,
        enable_v03_submissions=True,
        enable_v04_commitment_semantics=True,
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
                                    enable_v04_commitment_semantics=True,
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
    probe_match = MountMatch(enable_v04_commitment_semantics=True)
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
                                    enable_v04_commitment_semantics=True,
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
                                    response_commitment=Commitment.MEDIUM,
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
        for action in modern_actions_for(side)
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
    v03b_top_stall = _v03b_top_stall_probe()
    v03b_top_stall_sweep = _v03b_top_stall_sweep()
    v03b_stalling_resolves_lock = _v03b_gate_a_sweep_passes(
        v03b_top_stall_sweep
    )

    # Gate 4 stays pinned to the v0.2 batch that proved Bridge's setup role.
    standard_batch = _v02_standard_batch()
    bridge_count = standard_batch.bottom_action_counts.get("Bridge", 0)
    bridge_setup_count = standard_batch.bottom_setup_action_count
    bridge_completed_setup_builds = standard_batch.bottom_completed_setup_build_count
    bottom_completed_setup_chains = standard_batch.bottom_completed_setup_chain_count

    # Gate 5 observes the current mechanics surface. Once a real submission
    # finish exists, follow-up submission attempts count as meaningful work
    # without changing the frozen >1.000 threshold.
    activity_batch = (
        _v03_standard_batch()
        if submission_finish_present
        else standard_batch
    )
    top_followup_position_attacks_per_match = (
        activity_batch.top_followup_position_attack_count
        / activity_batch.matches
    )
    top_followup_completed_setup_builds_per_match = (
        activity_batch.top_followup_completed_setup_build_count
        / activity_batch.matches
    )
    top_followup_submission_attempts_per_match = (
        activity_batch.top_submission_attempt_count / activity_batch.matches
        if submission_finish_present
        else 0.0
    )
    top_followup_meaningful_per_match = (
        top_followup_position_attacks_per_match
        + top_followup_completed_setup_builds_per_match
        + top_followup_submission_attempts_per_match
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
                V02GateStatus.DEFERRED
                if reset_locked_timeout and not submission_finish_present
                else (
                    V02GateStatus.PASS
                    if (
                        not reset_locked_timeout
                        or v03b_stalling_resolves_lock
                    )
                    else V02GateStatus.OPEN
                )
            ),
            metric=(
                f"legacy_locked_timeout={reset_locked_timeout}; "
                f"submission_finish_present={submission_finish_present}; "
                f"v03b_sweep_cases={len(v03b_top_stall_sweep)}; "
                f"v03b_sweep_failing="
                f"{sum(not _v03b_gate_a_case_passes(item) for item in v03b_top_stall_sweep)}; "
                f"v03b_max_post_reset_locked_time_share="
                f"{max(item.steady_state_locked_time_share for item in v03b_top_stall_sweep):.3f}; "
                f"v03b_max_post_reset_window_share="
                f"{max(item.steady_state_locked_share for item in v03b_top_stall_sweep):.3f}; "
                f"v03b_max_post_reset_locked_dwell="
                f"{max(item.steady_state_longest_locked_dwell_seconds for item in v03b_top_stall_sweep)}s; "
                f"v03b_locked_timeout_cases="
                f"{sum(item.locked_timeout for item in v03b_top_stall_sweep)}"
            ),
            evidence=(
                reset_probe
                + (
                    "; deferred to v0.3 because Locked Top currently has no "
                    "submission-finish/progress action, so a stalling penalty "
                    "would punish a state with no legal way to advance"
                    if reset_locked_timeout and not submission_finish_present
                    else (
                        "; v0.3b fixed interval/length sweep shows deliberate "
                        "stalling cannot keep Locked as the steady state; "
                        "timeout band is no longer the gate criterion"
                        if v03b_stalling_resolves_lock
                        else "; v0.3b stalling evidence has not resolved the lock"
                    )
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
                f"completed-setup-builds:{top_followup_completed_setup_builds_per_match:.3f},"
                f"submission-attempts:{top_followup_submission_attempts_per_match:.3f}); "
                f"threshold={top_followup_threshold:.3f}; "
                f"margin={top_followup_margin:+.3f}"
            ),
            evidence="opening attack excluded; setup builders count only when their Ready target is later consumed; v0.3 submission attempts count as terminal follow-up work; margin is measured against the unchanged >1.000 threshold",
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


@dataclass(frozen=True, slots=True)
class V03GateMeasurement:
    letter: str
    name: str
    status: V02GateStatus
    metric: str
    evidence: str

    def render(self) -> str:
        return (
            f"V0.3a DOD GATE {self.letter} [{self.status.value}]: "
            f"{self.name} — {self.metric}; {self.evidence}"
        )


@lru_cache(maxsize=1)
def _v03_locked_submission_probe() -> tuple[float, bool]:
    """Return (submission progress probability, policy selected submission)."""
    from ..engine.match import MountMatch
    from ..interfaces.batch import EscapeFirstInitiatorPolicy

    match = MountMatch(
        starting_axis=3.50,
        enable_v02_setup=True,
        enable_v03_submissions=True,
    )
    match.submission_state.stage = SubmissionStage.THREAT
    match.initiator = Side.TOP
    match.set_behaviors(
        top=TopBehavior.PRESSURE,
        bottom=BottomBehavior.ESCAPE,
    )
    decision = EscapeFirstInitiatorPolicy().choose(match)
    return (
        decision.submission_progress_probability,
        decision.reason == "submission"
        and decision.action_id == TOP_AMERICANA_SUBMISSION_FINISH,
    )


@dataclass(frozen=True, slots=True)
class V03DefenseStageEvidence:
    reachable_states: int
    best_contested_states: int
    best_defender_win_states: int
    guaranteed_advance_states: int


@lru_cache(maxsize=1)
def _v03_best_defense_evidence() -> dict[SubmissionStage, V03DefenseStageEvidence]:
    """Reachable fresh baseline stages must have exactly Contested best defense."""
    from ..engine.match import MountMatch

    evidence: dict[SubmissionStage, V03DefenseStageEvidence] = {}
    reachable_anchors = {
        Band.STRONG: _V02_BAND_ANCHORS[Band.STRONG],
        Band.LOCKED: _V02_BAND_ANCHORS[Band.LOCKED],
    }
    for stage in SubmissionStage:
        reachable = 0
        best_contested = 0
        defender_wins = 0
        guaranteed = 0
        for band, axis in reachable_anchors.items():
            match = MountMatch(
                starting_axis=axis,
                enable_v02_setup=True,
                enable_v03_submissions=True,
            )
            match.submission_state.stage = stage
            match.initiator = Side.TOP
            match.set_behaviors(
                top=TopBehavior.PRESSURE,
                bottom=BottomBehavior.ESCAPE,
            )
            if match.band is not band:
                raise AssertionError(
                    f"v0.3a band anchor mismatch: expected {band}, got {match.band}"
                )
            legal = match.legal_response_ids(TOP_AMERICANA_SUBMISSION_FINISH)
            finals = [
                match.preview_submission_stage(
                    response_id=response_id
                ).final_grade
                for response_id in legal
            ]
            if not finals:
                raise RuntimeError(
                    f"v0.3a {stage.value} has no legal fresh defense"
                )
            best = min(finals)
            reachable += 1
            if best is Grade.CONTESTED:
                best_contested += 1
            if best.failed:
                defender_wins += 1
            if all(grade.successful for grade in finals):
                guaranteed += 1
        evidence[stage] = V03DefenseStageEvidence(
            reachable_states=reachable,
            best_contested_states=best_contested,
            best_defender_win_states=defender_wins,
            guaranteed_advance_states=guaranteed,
        )
    return evidence


def _v03_stage_signature(stage: SubmissionStage, result) -> tuple:
    if result.final_grade.successful:
        disposition = "tap" if stage is SubmissionStage.FINISH else "advance"
        tapped = stage is SubmissionStage.FINISH
        if stage is SubmissionStage.THREAT:
            after_stage = SubmissionStage.CONTROL
        elif stage is SubmissionStage.CONTROL:
            after_stage = SubmissionStage.FINISH
        else:
            after_stage = SubmissionStage.FINISH
    elif result.final_grade.failed:
        disposition = "break"
        tapped = False
        after_stage = None
    else:
        disposition = "hold"
        tapped = False
        after_stage = stage
    return (
        disposition,
        tapped,
        after_stage,
        round(result.axis_after, 8),
        result.band_after,
    )


@lru_cache(maxsize=1)
def _v03_exhaustion_differentials() -> tuple[int, int, int, int]:
    """Return attacker changes, defender changes, cancellation mismatches, cases."""
    from ..engine.match import MountMatch

    attacker_changes = 0
    defender_changes = 0
    cancellation_mismatches = 0
    cases = 0
    for stage in SubmissionStage:
        for _band, axis in _V02_BAND_ANCHORS.items():
            for bottom_behavior in BottomBehavior:
                match = MountMatch(
                    starting_axis=axis,
                    enable_v02_setup=True,
                    enable_v03_submissions=True,
                )
                match.submission_state.stage = stage
                match.initiator = Side.TOP
                match.set_behaviors(
                    top=TopBehavior.PRESSURE,
                    bottom=bottom_behavior,
                )
                modifiers = {
                    "fresh": match.exhaustion_policy.exchange_grade_modifier(
                        initiator_band=StaminaBand.FRESH,
                        responder_band=StaminaBand.FRESH,
                    ),
                    "attacker": match.exhaustion_policy.exchange_grade_modifier(
                        initiator_band=StaminaBand.EXHAUSTED,
                        responder_band=StaminaBand.FRESH,
                    ),
                    "defender": match.exhaustion_policy.exchange_grade_modifier(
                        initiator_band=StaminaBand.FRESH,
                        responder_band=StaminaBand.EXHAUSTED,
                    ),
                    "both": match.exhaustion_policy.exchange_grade_modifier(
                        initiator_band=StaminaBand.EXHAUSTED,
                        responder_band=StaminaBand.EXHAUSTED,
                    ),
                }
                for response_id in match.legal_response_ids(
                    TOP_AMERICANA_SUBMISSION_FINISH
                ):
                    results = {
                        key: match.preview_submission_stage(
                            response_id=response_id,
                            external_grade_modifier=modifier,
                        )
                        for key, modifier in modifiers.items()
                    }
                    fresh_sig = _v03_stage_signature(stage, results["fresh"])
                    if _v03_stage_signature(stage, results["attacker"]) != fresh_sig:
                        attacker_changes += 1
                    if _v03_stage_signature(stage, results["defender"]) != fresh_sig:
                        defender_changes += 1
                    if _v03_stage_signature(stage, results["both"]) != fresh_sig:
                        cancellation_mismatches += 1
                    cases += 1
    return attacker_changes, defender_changes, cancellation_mismatches, cases


@dataclass(frozen=True, slots=True)
class V03InformedExhaustedEvidence:
    tapped: bool
    selected_responses: tuple[str, ...]
    final_grades: tuple[Grade, ...]


@lru_cache(maxsize=1)
def _v03_informed_exhausted_defender_probe() -> V03InformedExhaustedEvidence:
    """Best legal exhausted defense must not recreate a perfect-response lock."""
    from ..engine.match import MountMatch

    match = MountMatch(
        starting_axis=3.50,
        enable_v02_setup=True,
        enable_v03_submissions=True,
    )
    match.submission_state.stage = SubmissionStage.THREAT
    match.top.stamina.set_current(100)
    match.bottom.stamina.set_current(25)
    match.set_behaviors(
        top=TopBehavior.PRESSURE,
        bottom=BottomBehavior.ESCAPE,
    )

    selected: list[str] = []
    grades: list[Grade] = []
    for _stage in SubmissionStage:
        match.initiator = Side.TOP
        legal = match.legal_response_ids(TOP_AMERICANA_SUBMISSION_FINISH)
        candidates = [
            (
                match.preview_submission_stage(response_id=response_id).final_grade,
                response_id,
            )
            for response_id in legal
        ]
        if not candidates:
            break
        best_grade, best_response = min(candidates)
        selected.append(best_response)
        result = match.attempt(
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            response_id=best_response,
            commitment=Commitment.LOW,
        )
        grades.append(result.resolution.final_grade)
        if match.submission_tapped:
            break
        if not match.submission_state.active:
            break

    return V03InformedExhaustedEvidence(
        tapped=match.submission_tapped,
        selected_responses=tuple(selected),
        final_grades=tuple(grades),
    )


@dataclass(frozen=True, slots=True)
class V03InformedMatchRow:
    label: str
    taps: int
    reached_threat: int
    escapes: int
    timeouts: int
    top_stamina_median: float
    bottom_stamina_median: float
    top_resets: int
    bottom_resets: int
    setup_builds: int


@lru_cache(maxsize=1)
def _v03_informed_defender_sweep() -> tuple[V03InformedMatchRow, ...]:
    """Non-gating full-match probe with informed Bottom defense."""
    from ..interfaces.batch import (
        BatchBehaviorMode,
        BatchResponderMode,
        run_escape_first_batch,
    )

    specs = (
        (
            "PRESSURE/ESCAPE fixed",
            TopBehavior.PRESSURE,
            BottomBehavior.ESCAPE,
            BatchBehaviorMode.FIXED,
        ),
        (
            "PRESSURE/ESCAPE recover",
            TopBehavior.PRESSURE,
            BottomBehavior.ESCAPE,
            BatchBehaviorMode.RECOVER,
        ),
        (
            "PRESSURE/PROTECT",
            TopBehavior.PRESSURE,
            BottomBehavior.PROTECT,
            BatchBehaviorMode.FIXED,
        ),
        (
            "PRESSURE/CONSERVE",
            TopBehavior.PRESSURE,
            BottomBehavior.CONSERVE,
            BatchBehaviorMode.FIXED,
        ),
        (
            "HOLD/ESCAPE",
            TopBehavior.HOLD,
            BottomBehavior.ESCAPE,
            BatchBehaviorMode.FIXED,
        ),
        (
            "CONSERVE/ESCAPE",
            TopBehavior.CONSERVE,
            BottomBehavior.ESCAPE,
            BatchBehaviorMode.FIXED,
        ),
        (
            "CONSERVE/PROTECT",
            TopBehavior.CONSERVE,
            BottomBehavior.PROTECT,
            BatchBehaviorMode.FIXED,
        ),
    )

    rows: list[V03InformedMatchRow] = []
    for label, top_behavior, bottom_behavior, bottom_mode in specs:
        summary = run_escape_first_batch(
            matches=100,
            base_seed=42,
            top_behavior=top_behavior,
            bottom_behavior=bottom_behavior,
            commitment=Commitment.MEDIUM,
            initial_clock=300,
            starting_axis=1.50,
            interval_seconds=5,
            top_stamina=100,
            bottom_stamina=100,
            bottom_behavior_mode=bottom_mode,
            bottom_responder_mode=BatchResponderMode.INFORMED,
            enable_v02_setup=True,
            enable_v03_submissions=True,
        )
        escapes = sum(
            summary.outcome_counts.get(destination.value, 0)
            for destination in ExitDestination
        )
        rows.append(
            V03InformedMatchRow(
                label=label,
                taps=summary.outcome_counts.get("TAP — Americana", 0),
                reached_threat=summary.matches_reached_submission_threat,
                escapes=escapes,
                timeouts=summary.outcome_counts.get("TIMEOUT — Mount retained", 0),
                top_stamina_median=summary.top_final_stamina_median,
                bottom_stamina_median=summary.bottom_final_stamina_median,
                top_resets=summary.top_reset_count,
                bottom_resets=summary.bottom_reset_count,
                setup_builds=summary.top_completed_setup_build_count,
            )
        )
    return tuple(rows)


def render_v03a_informed_defender_probe() -> str:
    random_batch = _v03_standard_batch()
    rows = _v03_informed_defender_sweep()
    random_taps = random_batch.outcome_counts.get("TAP — Americana", 0)
    return (
        "V0.3a INFORMED DEFENDER PROBE — 100 matched seeds: "
        + "; ".join(
            f"{row.label} taps={row.taps},Threat={row.reached_threat},"
            f"escapes={row.escapes},timeouts={row.timeouts},"
            f"stamina={row.top_stamina_median:.0f}/{row.bottom_stamina_median:.0f},"
            f"RESETs={row.top_resets}/{row.bottom_resets},"
            f"setup-builds={row.setup_builds}"
            for row in rows
        )
        + f"; random PRESSURE/ESCAPE taps={random_taps}. "
        "Historical v0.3a observation only; after v0.4a capability exists, "
        "Gate B uses the v0.4a informed MATCH-commitment batch."
    )


@dataclass(frozen=True, slots=True)
class V03RecoveryPredictionRow:
    label: str
    taps: int
    escapes: int
    timeouts: int
    submission_attempts: int


@lru_cache(maxsize=1)
def _v03_bottom_recovery_prediction_probe() -> tuple[V03RecoveryPredictionRow, ...]:
    """Non-gating prediction probe for exhausted Bottom under Top PRESSURE.

    All three rows use the same 100 seeds and v0.3a mechanics. The only
    intended differences are Bottom's starting stamina and whether the existing
    adaptive recovery policy may switch an Exhausted Bottom to CONSERVE until
    the 35-point latch clears.
    """
    from ..interfaces.batch import BatchBehaviorMode, run_escape_first_batch

    specs = (
        ("fresh-fixed", 100, BatchBehaviorMode.FIXED),
        ("exhausted-fixed", 25, BatchBehaviorMode.FIXED),
        ("exhausted-recover", 25, BatchBehaviorMode.RECOVER),
    )
    rows: list[V03RecoveryPredictionRow] = []
    for label, bottom_stamina, bottom_mode in specs:
        summary = run_escape_first_batch(
            matches=100,
            base_seed=42,
            top_behavior=TopBehavior.PRESSURE,
            bottom_behavior=BottomBehavior.ESCAPE,
            commitment=Commitment.MEDIUM,
            initial_clock=300,
            starting_axis=1.50,
            interval_seconds=5,
            top_stamina=100,
            bottom_stamina=bottom_stamina,
            bottom_behavior_mode=bottom_mode,
            enable_v02_setup=True,
            enable_v03_submissions=True,
        )
        escapes = sum(
            summary.outcome_counts.get(destination.value, 0)
            for destination in ExitDestination
        )
        rows.append(
            V03RecoveryPredictionRow(
                label=label,
                taps=summary.outcome_counts.get("TAP — Americana", 0),
                escapes=escapes,
                timeouts=summary.outcome_counts.get("TIMEOUT — Mount retained", 0),
                submission_attempts=summary.top_submission_attempt_count,
            )
        )
    return tuple(rows)


def render_v03a_recovery_prediction_probe() -> str:
    rows = _v03_bottom_recovery_prediction_probe()
    return (
        "V0.3a PREDICTION PROBE — Top PRESSURE / Bottom ESCAPE, 100 matched seeds: "
        + "; ".join(
            f"{row.label} taps={row.taps},escapes={row.escapes},"
            f"timeouts={row.timeouts},submission-attempts={row.submission_attempts}"
            for row in rows
        )
        + ". Observational only; no gate or threshold."
    )


@dataclass(frozen=True, slots=True)
class V03BehaviorSweepRow:
    bottom_behavior: BottomBehavior
    taps: int
    escapes: int
    timeouts: int
    completed_setup_builds: int
    submission_attempts: int


@lru_cache(maxsize=1)
def _v03_defender_behavior_sweep() -> tuple[V03BehaviorSweepRow, ...]:
    """Non-gating matched-seed sweep of Bottom strategic behavior."""
    from ..interfaces.batch import run_escape_first_batch

    rows: list[V03BehaviorSweepRow] = []
    for bottom_behavior in BottomBehavior:
        summary = run_escape_first_batch(
            matches=100,
            base_seed=42,
            top_behavior=TopBehavior.PRESSURE,
            bottom_behavior=bottom_behavior,
            commitment=Commitment.MEDIUM,
            initial_clock=300,
            starting_axis=1.50,
            interval_seconds=5,
            top_stamina=100,
            bottom_stamina=100,
            enable_v02_setup=True,
            enable_v03_submissions=True,
        )
        escapes = sum(
            summary.outcome_counts.get(destination.value, 0)
            for destination in ExitDestination
        )
        rows.append(
            V03BehaviorSweepRow(
                bottom_behavior=bottom_behavior,
                taps=summary.outcome_counts.get("TAP — Americana", 0),
                escapes=escapes,
                timeouts=summary.outcome_counts.get("TIMEOUT — Mount retained", 0),
                completed_setup_builds=summary.top_completed_setup_build_count,
                submission_attempts=summary.top_submission_attempt_count,
            )
        )
    return tuple(rows)


@dataclass(frozen=True, slots=True)
class V03ReacquisitionRow:
    band: Band
    bottom_behavior: BottomBehavior
    probability: float


@lru_cache(maxsize=1)
def _v03_reacquisition_probability_sweep() -> tuple[V03ReacquisitionRow, ...]:
    """Exact probability High Mount Climb advances Americana setup from None.

    This measures the existing generic v0.2 setup rule as-is; it does not alter
    setup semantics or the v0.3a gates.
    """
    from ..engine.match import MountMatch
    from ..interfaces.batch import EscapeFirstInitiatorPolicy
    from ..positions.mount.catalog import TOP_HIGH_MOUNT_CLIMB

    rows: list[V03ReacquisitionRow] = []
    policy = EscapeFirstInitiatorPolicy()
    for band, axis in _V02_BAND_ANCHORS.items():
        for bottom_behavior in BottomBehavior:
            match = MountMatch(
                starting_axis=axis,
                enable_v02_setup=True,
                enable_v03_submissions=True,
            )
            match.initiator = Side.TOP
            match.set_behaviors(
                top=TopBehavior.PRESSURE,
                bottom=bottom_behavior,
            )
            modifier = match.exhaustion_policy.exchange_grade_modifier(
                initiator_band=StaminaBand.FRESH,
                responder_band=StaminaBand.FRESH,
            )
            probability = policy._setup_advance_probability(
                match,
                action_id=TOP_HIGH_MOUNT_CLIMB,
                external_grade_modifier=modifier,
            )
            rows.append(
                V03ReacquisitionRow(
                    band=band,
                    bottom_behavior=bottom_behavior,
                    probability=probability,
                )
            )
    return tuple(rows)


def render_v03a_stamina_saturation_observation() -> str:
    batch = _v03_standard_batch()
    return (
        "V0.3a STAMINA SATURATION — standard batch: "
        f"Top median={batch.top_final_stamina_median:.1f},"
        f"Bottom median={batch.bottom_final_stamina_median:.1f},"
        f"Top RESETs={batch.top_reset_count},Bottom RESETs={batch.bottom_reset_count}. "
        "Observational only; no stamina tuning in v0.3a."
    )


def render_v03a_behavior_and_reacquisition_probe() -> tuple[str, str]:
    behavior_rows = _v03_defender_behavior_sweep()
    reacquisition_rows = _v03_reacquisition_probability_sweep()
    behavior = (
        "V0.3a BEHAVIOR SWEEP — Top PRESSURE, 100 matched seeds: "
        + "; ".join(
            f"Bottom {row.bottom_behavior.value} taps={row.taps},escapes={row.escapes},"
            f"timeouts={row.timeouts},setup-builds={row.completed_setup_builds},"
            f"submission-attempts={row.submission_attempts}"
            for row in behavior_rows
        )
        + ". Observational only."
    )
    reacquisition = (
        "V0.3a REACQUISITION SWEEP — exact High Mount Climb setup-advance probability: "
        + "; ".join(
            f"{row.band.value}/{row.bottom_behavior.value}={row.probability:.3f}"
            for row in reacquisition_rows
        )
        + ". Observational only."
    )
    return behavior, reacquisition


def _v03_response_commitment_present() -> bool:
    """Auto-expiry signal from the real runtime capability, not catalog metadata."""
    from ..engine.match import MountMatch

    enabled = MountMatch(enable_v04_commitment_semantics=True)
    disabled = MountMatch(enable_v04_commitment_semantics=False)
    return (
        enabled.response_commitment_enabled
        and not disabled.response_commitment_enabled
    )


def _v03_recognition_mechanic_present() -> bool:
    """Auto-expiry signal: match/competitor exposes real information state."""
    from ..engine.match import MountMatch

    probe = MountMatch(
        enable_v02_setup=True,
        enable_v03_submissions=True,
    )
    attribute_names = (
        "recognition",
        "recognition_state",
        "information",
        "information_state",
        "information_policy",
    )
    for owner in (probe, probe.top, probe.bottom):
        for name in attribute_names:
            if getattr(owner, name, None) is not None:
                return True
    return False


def _v03_gate_b_status(
    *,
    tap_rate: float,
    response_commitment_present: bool,
    recognition_present: bool,
) -> V02GateStatus:
    """Gate B self-expires from DEFERRED when either future capability exists."""
    if not response_commitment_present and not recognition_present:
        return V02GateStatus.DEFERRED
    return (
        V02GateStatus.PASS
        if 0 < tap_rate < 0.50
        else V02GateStatus.OPEN
    )


def render_v03a_setup_policy_debt() -> str:
    """Keep the informed setup-churn problem visible in --check."""
    protect = next(
        row
        for row in _v03_informed_defender_sweep()
        if row.label == "PRESSURE/PROTECT"
    )
    return (
        "V0.3a SETUP-POLICY DEBT: builder progress is ranked above axis loss; "
        f"informed PROTECT builds={protect.setup_builds}, "
        f"Threat entries={protect.reached_threat}."
    )


def render_v03a_hold_cost_status() -> str:
    informed = _v03_informed_standard_batch()
    return (
        "V0.3a SUBMISSION-HOLD COST: PROVISIONAL — Ready/active Contested "
        "Americana holds cost the responder LOW=3 after resolution; "
        "recorded pre-cost informed Threat=0/100, "
        f"current informed Threat={informed.matches_reached_submission_threat}/100; "
        "this rule is retained as measured access evidence, not as a closed "
        "Gate-B tuning value."
    )


V03B_GATE_A_INTERVALS = (5, 7)
V03B_GATE_A_MATCH_LENGTHS = tuple(range(240, 301, 5))
V03B_GATE_A_LOCKED_SHARE_LIMIT = 0.50
V03B_GATE_A_LOCKED_DWELL_LIMIT_SECONDS = 20


@dataclass(frozen=True, slots=True)
class V03BTopStallEvidence:
    interval_seconds: int
    match_length_seconds: int
    warnings: int
    penalties: int
    position_resets: int
    final_axis: float
    final_band: Band
    locked_timeout: bool
    decision_windows: int
    locked_windows: int
    locked_seconds: int
    elapsed_seconds: int
    longest_locked_dwell_seconds: int
    steady_state_decision_windows: int
    steady_state_locked_windows: int
    steady_state_locked_seconds: int
    steady_state_elapsed_seconds: int
    steady_state_longest_locked_dwell_seconds: int

    @property
    def locked_share(self) -> float:
        return (
            self.locked_windows / self.decision_windows
            if self.decision_windows
            else 0.0
        )

    @property
    def steady_state_locked_share(self) -> float:
        """Decision-window share retained as a sampling diagnostic only."""
        return (
            self.steady_state_locked_windows
            / self.steady_state_decision_windows
            if self.steady_state_decision_windows
            else 0.0
        )

    @property
    def locked_time_share(self) -> float:
        return (
            self.locked_seconds / self.elapsed_seconds
            if self.elapsed_seconds
            else 0.0
        )

    @property
    def steady_state_locked_time_share(self) -> float:
        return (
            self.steady_state_locked_seconds
            / self.steady_state_elapsed_seconds
            if self.steady_state_elapsed_seconds
            else 0.0
        )


@dataclass(frozen=True, slots=True)
class V03BStallActiveBottomEvidence:
    matches: int
    timeouts: int
    escapes: int
    warnings: int
    penalties: int
    position_resets: int


@dataclass(frozen=True, slots=True)
class V03BStalemateEvidence:
    attempts: int
    top_penalties: int
    bottom_penalties: int
    final_stage: SubmissionStage | None
    top_clock: int
    bottom_clock: int


@dataclass(frozen=True, slots=True)
class V03BSymmetryEvidence:
    top_warnings: int
    top_penalties: int
    bottom_warnings: int
    bottom_penalties: int


@dataclass(frozen=True, slots=True)
class V03BBoundaryEvidence:
    warnings: int
    free_windows: int
    axis_before: float
    axis_after: float
    band_after: Band
    clock_before: int
    clock_after: int


@dataclass(frozen=True, slots=True)
class V03BEscalationInvariantEvidence:
    cases: int
    backward_effects: int
    weaker_escalations: int
    boundary_mismatches: int
    bottom_axis_lowering_cases: int
    classic_bottom_axis_lowering: int


@dataclass(frozen=True, slots=True)
class V03BGateMeasurement:
    letter: str
    name: str
    status: V02GateStatus
    metric: str
    evidence: str

    def render(self) -> str:
        return (
            f"V0.3b DOD GATE {self.letter} [{self.status.value}]: "
            f"{self.name} — {self.metric}; {self.evidence}"
        )


def _v03b_match(
    *,
    axis: float,
    initial_clock: int = 300,
    interval_seconds: int = 5,
):
    from ..engine.match import MountMatch

    match = MountMatch(
        initial_clock=initial_clock,
        starting_axis=axis,
        interval_seconds=interval_seconds,
        enable_v02_setup=True,
        enable_v03_submissions=True,
        enable_v03b_stalling=True,
    )
    match.set_behaviors(
        top=TopBehavior.PRESSURE,
        bottom=BottomBehavior.ESCAPE,
    )
    return match


def _drift_band_segments(drift) -> tuple[tuple[Band, int], ...]:
    """Exact persisted-band durations from the engine's per-second drift trace."""
    total = drift.start_clock - drift.end_clock
    band = drift.start_band
    segment_start = 0
    segments: list[tuple[Band, int]] = []

    for change in drift.band_changes:
        if change.clock_seconds is None:
            raise RuntimeError("drift band change is missing clock evidence")
        elapsed_at_change = drift.start_clock - change.clock_seconds
        duration = elapsed_at_change - segment_start
        if duration > 0:
            segments.append((band, duration))
        band = change.after
        segment_start = elapsed_at_change

    remaining = total - segment_start
    if remaining > 0:
        segments.append((band, remaining))
    return tuple(segments)


def _v03b_top_stall_case(
    *,
    match_length_seconds: int,
    interval_seconds: int,
) -> V03BTopStallEvidence:
    """Measure deliberate Top stalling without opponent-engagement confounding."""
    match = _v03b_match(
        axis=4.00,
        initial_clock=match_length_seconds,
        interval_seconds=interval_seconds,
    )
    match.submission_state.stage = SubmissionStage.THREAT

    decision_windows = 0
    locked_windows = 0
    locked_seconds = 0
    elapsed_seconds = 0
    current_locked_dwell = 0
    longest_locked_dwell = 0

    steady_state_started = False
    steady_state_decision_windows = 0
    steady_state_locked_windows = 0
    steady_state_locked_seconds = 0
    steady_state_elapsed_seconds = 0
    steady_state_current_locked_dwell = 0
    steady_state_longest_locked_dwell = 0

    while not match.ended:
        advance = match.advance()
        segments = _drift_band_segments(advance.drift)

        for segment_band, duration in segments:
            elapsed_seconds += duration
            if segment_band is Band.LOCKED:
                locked_seconds += duration
                current_locked_dwell += duration
                longest_locked_dwell = max(
                    longest_locked_dwell,
                    current_locked_dwell,
                )
            else:
                current_locked_dwell = 0

            if steady_state_started:
                steady_state_elapsed_seconds += duration
                if segment_band is Band.LOCKED:
                    steady_state_locked_seconds += duration
                    steady_state_current_locked_dwell += duration
                    steady_state_longest_locked_dwell = max(
                        steady_state_longest_locked_dwell,
                        steady_state_current_locked_dwell,
                    )
                else:
                    steady_state_current_locked_dwell = 0

        if match.ended:
            break

        decision_windows += 1
        if match.band is Band.LOCKED:
            locked_windows += 1

        if steady_state_started:
            steady_state_decision_windows += 1
            if match.band is Band.LOCKED:
                steady_state_locked_windows += 1

        if match.initiator is Side.BOTTOM:
            # Preserve elapsed game time and ordinary alternating cadence, but
            # isolate Top's advancement obligation by suppressing Bottom's
            # intervening initiation rather than recording fake engagement.
            match.initiator = Side.TOP
            continue

        resets_before = len(match.history.stalling_position_reset_history)
        match.reset_window()
        resets_after = len(match.history.stalling_position_reset_history)

        if match.band is not Band.LOCKED:
            current_locked_dwell = 0
            if steady_state_started:
                steady_state_current_locked_dwell = 0

        if not steady_state_started and resets_after > resets_before:
            # The first Position Reset marks the transition from the initial
            # Warning/first-penalty grace into the repeating enforcement regime.
            steady_state_started = True
            steady_state_current_locked_dwell = 0

    return V03BTopStallEvidence(
        interval_seconds=interval_seconds,
        match_length_seconds=match_length_seconds,
        warnings=len(match.history.stalling_warning_history),
        penalties=len(match.history.stalling_penalty_history),
        position_resets=len(match.history.stalling_position_reset_history),
        final_axis=match.axis,
        final_band=match.band,
        locked_timeout=(
            match.exit_reason == "TIMEOUT — Mount retained"
            and match.band is Band.LOCKED
        ),
        decision_windows=decision_windows,
        locked_windows=locked_windows,
        locked_seconds=locked_seconds,
        elapsed_seconds=elapsed_seconds,
        longest_locked_dwell_seconds=longest_locked_dwell,
        steady_state_decision_windows=steady_state_decision_windows,
        steady_state_locked_windows=steady_state_locked_windows,
        steady_state_locked_seconds=steady_state_locked_seconds,
        steady_state_elapsed_seconds=steady_state_elapsed_seconds,
        steady_state_longest_locked_dwell_seconds=(
            steady_state_longest_locked_dwell
        ),
    )


@lru_cache(maxsize=1)
def _v03b_top_stall_probe() -> V03BTopStallEvidence:
    """Historical/default 5:00, 5-second case retained for diagnostics."""
    return _v03b_top_stall_case(
        match_length_seconds=300,
        interval_seconds=5,
    )


@lru_cache(maxsize=1)
def _v03b_top_stall_sweep() -> tuple[V03BTopStallEvidence, ...]:
    return tuple(
        _v03b_top_stall_case(
            match_length_seconds=match_length,
            interval_seconds=interval,
        )
        for interval in V03B_GATE_A_INTERVALS
        for match_length in V03B_GATE_A_MATCH_LENGTHS
    )


def _v03b_gate_a_case_passes(item: V03BTopStallEvidence) -> bool:
    return (
        item.warnings >= 1
        and item.penalties >= 1
        and item.position_resets >= 1
        and item.steady_state_elapsed_seconds > 0
        and item.steady_state_locked_time_share < V03B_GATE_A_LOCKED_SHARE_LIMIT
        and item.steady_state_longest_locked_dwell_seconds
        < V03B_GATE_A_LOCKED_DWELL_LIMIT_SECONDS
    )


def _v03b_gate_a_sweep_passes(
    sweep: tuple[V03BTopStallEvidence, ...],
) -> bool:
    return len(sweep) == (
        len(V03B_GATE_A_INTERVALS) * len(V03B_GATE_A_MATCH_LENGTHS)
    ) and all(_v03b_gate_a_case_passes(item) for item in sweep)


@lru_cache(maxsize=1)
def _v03b_stalemated_attacker_probe() -> V03BStalemateEvidence:
    """A real submission attempt and legal defense engage both players."""
    match = _v03b_match(axis=3.50)
    match.submission_state.stage = SubmissionStage.THREAT

    attempts = 0
    for _ in range(3):
        for _tick in range(4):
            match.advance()
        match.initiator = Side.TOP
        match.attempt(
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            response_id=BOTTOM_RESPONSE_TURN_IN_RECOVERY,
            commitment=Commitment.LOW,
        )
        attempts += 1

    top_penalties = sum(
        entry.startswith("top@")
        for entry in match.history.stalling_penalty_history
    )
    bottom_penalties = sum(
        entry.startswith("bottom@")
        for entry in match.history.stalling_penalty_history
    )
    return V03BStalemateEvidence(
        attempts=attempts,
        top_penalties=top_penalties,
        bottom_penalties=bottom_penalties,
        final_stage=match.submission_state.stage,
        top_clock=match.advancement_clock(Side.TOP),
        bottom_clock=match.advancement_clock(Side.BOTTOM),
    )


def _v03b_force_warning_then_penalty(*, side: Side, axis: float):
    match = _v03b_match(axis=axis)
    if side is Side.TOP:
        match.submission_state.stage = SubmissionStage.THREAT
    match.initiator = side
    match.stalling_tracker.advance(20)
    match.reset_window()
    match.initiator = side
    match.stalling_tracker.advance(20)
    second = match.reset_window()
    return match, second


@lru_cache(maxsize=1)
def _v03b_symmetry_probe() -> V03BSymmetryEvidence:
    top, _ = _v03b_force_warning_then_penalty(
        side=Side.TOP,
        axis=4.00,
    )
    bottom, _ = _v03b_force_warning_then_penalty(
        side=Side.BOTTOM,
        axis=1.50,
    )
    return V03BSymmetryEvidence(
        top_warnings=len(top.history.stalling_warning_history),
        top_penalties=len(top.history.stalling_penalty_history),
        bottom_warnings=len(bottom.history.stalling_warning_history),
        bottom_penalties=len(bottom.history.stalling_penalty_history),
    )


@lru_cache(maxsize=1)
def _v03b_boundary_probe() -> V03BBoundaryEvidence:
    match = _v03b_match(axis=0.50)
    match.submission_state.stage = SubmissionStage.THREAT

    match.stalling_tracker.advance(20)
    match.reset_window()
    match.initiator = Side.TOP
    match.stalling_tracker.advance(20)
    clock_before = match.clock_seconds
    axis_before = match.axis
    second = match.reset_window()

    return V03BBoundaryEvidence(
        warnings=len(match.history.stalling_warning_history),
        free_windows=len(match.history.stalling_free_initiative_history),
        axis_before=axis_before,
        axis_after=match.axis,
        band_after=match.band,
        clock_before=clock_before,
        clock_after=match.clock_seconds,
    )


def _v03b_effect_strength(
    *,
    offender: Side,
    axis_before: float,
    axis_after: float,
) -> float:
    return (
        axis_before - axis_after
        if offender is Side.TOP
        else axis_after - axis_before
    )


@lru_cache(maxsize=1)
def _v03b_escalation_invariant_probe() -> V03BEscalationInvariantEvidence:
    cases = 0
    backward = 0
    weaker = 0
    boundary_mismatches = 0
    bottom_lowering = 0

    for offender in (Side.TOP, Side.BOTTOM):
        for step in range(1, 41):
            axis = round(step / 10, 1)
            for band in Band:
                if not MOUNT_RULES.axis_can_have_band(axis, band):
                    continue
                cases += 1

                penalty_match = _v03b_match(axis=axis)
                penalty_match.position.apply_control(axis, band)
                (
                    penalty_before,
                    penalty_after,
                    penalty_free,
                ) = penalty_match._apply_stalling_penalty(
                    offender=offender
                )

                escalation_match = _v03b_match(axis=axis)
                escalation_match.position.apply_control(axis, band)
                (
                    escalation_effect,
                    escalation_before,
                    escalation_after,
                    escalation_free,
                ) = escalation_match._apply_stalling_position_reset_rung(
                    offender=offender
                )

                penalty_strength = _v03b_effect_strength(
                    offender=offender,
                    axis_before=penalty_before,
                    axis_after=penalty_after,
                )
                escalation_strength = _v03b_effect_strength(
                    offender=offender,
                    axis_before=escalation_before,
                    axis_after=escalation_after,
                )

                escalation_beneficiary = (
                    escalation_match.free_initiative_beneficiary
                    if escalation_free
                    else None
                )
                if escalation_free:
                    if escalation_beneficiary is not offender.opponent:
                        boundary_mismatches += 1
                elif escalation_strength <= 0:
                    backward += 1

                if offender is Side.BOTTOM and escalation_after < escalation_before:
                    bottom_lowering += 1

                if penalty_free:
                    if not escalation_free:
                        weaker += 1
                elif not escalation_free and escalation_strength + 1e-12 < penalty_strength:
                    weaker += 1

    classic_bottom_lowering = _v03b_classic_two_sided_bottom_lowering_count()
    return V03BEscalationInvariantEvidence(
        cases=cases,
        backward_effects=backward,
        weaker_escalations=weaker,
        boundary_mismatches=boundary_mismatches,
        bottom_axis_lowering_cases=bottom_lowering,
        classic_bottom_axis_lowering=classic_bottom_lowering,
    )


@lru_cache(maxsize=1)
def _v03b_classic_two_sided_bottom_lowering_count() -> int:
    match = _v03b_match(axis=1.50)
    lowering = 0

    while not match.ended:
        free_window = match.consume_free_initiative_window()
        if free_window is None:
            match.advance()
            if match.ended:
                break

        offender = match.initiator
        axis_before = match.axis
        reset = match.reset_window()
        if (
            offender is Side.BOTTOM
            and reset.stalling_offense
            and match.axis < axis_before - 1e-12
        ):
            lowering += 1

    return lowering


def measure_v03b_definition_of_done() -> tuple[V03BGateMeasurement, ...]:
    top_stall = _v03b_top_stall_probe()
    top_stall_sweep = _v03b_top_stall_sweep()
    stalemate = _v03b_stalemated_attacker_probe()
    symmetry = _v03b_symmetry_probe()
    boundary = _v03b_boundary_probe()
    escalation = _v03b_escalation_invariant_probe()

    response_commitment_present = _v03_response_commitment_present()
    recognition_present = _v03_recognition_mechanic_present()
    v03a_gate_b = next(
        gate
        for gate in measure_v03a_definition_of_done()
        if gate.letter == "B"
    )

    gate_a_pass = _v03b_gate_a_sweep_passes(top_stall_sweep)
    gate_a_max_locked_time_share = max(
        item.steady_state_locked_time_share for item in top_stall_sweep
    )
    gate_a_max_locked_window_share = max(
        item.steady_state_locked_share for item in top_stall_sweep
    )
    gate_a_max_locked_dwell = max(
        item.steady_state_longest_locked_dwell_seconds
        for item in top_stall_sweep
    )
    gate_a_whole_match_max_locked_share = max(
        item.locked_share for item in top_stall_sweep
    )
    gate_a_whole_match_max_locked_time_share = max(
        item.locked_time_share for item in top_stall_sweep
    )
    gate_a_whole_match_max_locked_dwell = max(
        item.longest_locked_dwell_seconds for item in top_stall_sweep
    )
    gate_a_locked_endings = sum(
        item.locked_timeout for item in top_stall_sweep
    )
    gate_a_failing_items = tuple(
        item
        for item in top_stall_sweep
        if not _v03b_gate_a_case_passes(item)
    )
    gate_a_failing_cases = len(gate_a_failing_items)
    gate_a_failing_labels = ",".join(
        f"i{item.interval_seconds}/t{item.match_length_seconds}:"
        f"time_share={item.steady_state_locked_time_share:.3f},"
        f"window_share={item.steady_state_locked_share:.3f},"
        f"dwell={item.steady_state_longest_locked_dwell_seconds}s"
        for item in gate_a_failing_items
    ) or "none"
    gate_b_pass = (
        stalemate.attempts > 0
        and stalemate.top_penalties == 0
        and stalemate.bottom_penalties == 0
        and stalemate.final_stage is SubmissionStage.THREAT
        and stalemate.top_clock == 0
        and stalemate.bottom_clock == 0
    )
    gate_c_pass = (
        symmetry.top_warnings == 1
        and symmetry.top_penalties >= 1
        and symmetry.bottom_warnings == 1
        and symmetry.bottom_penalties >= 1
    )
    gate_d_pass = (
        boundary.warnings == 1
        and boundary.free_windows == 1
        and abs(boundary.axis_after - boundary.axis_before) <= 1e-12
        and boundary.band_after is Band.LOOSE
        and boundary.clock_after == boundary.clock_before
    )
    from ..engine.match import MountMatch

    v03b_scope = MountMatch(
        enable_v02_setup=True,
        enable_v03_submissions=True,
        enable_v03b_stalling=True,
        enable_v04_commitment_semantics=False,
    )
    v03b_response_commitment_present = (
        v03b_scope.response_commitment_enabled
    )
    gate_e_pass = (
        not v03b_response_commitment_present
        and not recognition_present
    )
    gate_f_pass = (
        escalation.cases > 0
        and escalation.backward_effects == 0
        and escalation.weaker_escalations == 0
        and escalation.boundary_mismatches == 0
        and escalation.bottom_axis_lowering_cases == 0
        and escalation.classic_bottom_axis_lowering == 0
    )

    return (
        V03BGateMeasurement(
            letter="A",
            name="one-sided RESET lock is penalized",
            status=V02GateStatus.PASS if gate_a_pass else V02GateStatus.OPEN,
            metric=(
                f"sweep_cases={len(top_stall_sweep)}; "
                f"failing_cases={gate_a_failing_cases}; "
                f"max_post_reset_Locked_time_share={gate_a_max_locked_time_share:.3f}"
                f"<{V03B_GATE_A_LOCKED_SHARE_LIMIT:.2f}; "
                f"max_post_reset_window_share={gate_a_max_locked_window_share:.3f}; "
                f"max_post_reset_Locked_dwell={gate_a_max_locked_dwell}s"
                f"<{V03B_GATE_A_LOCKED_DWELL_LIMIT_SECONDS}s; "
                f"whole_match_max_window_share={gate_a_whole_match_max_locked_share:.3f}; "
                f"whole_match_max_time_share={gate_a_whole_match_max_locked_time_share:.3f}; "
                f"whole_match_max_dwell={gate_a_whole_match_max_locked_dwell}s; "
                f"Locked_timeout_cases={gate_a_locked_endings}/{len(top_stall_sweep)}; "
                f"failing={gate_a_failing_labels}; "
                f"default_5m_5s=warnings:{top_stall.warnings},"
                f"penalties:{top_stall.penalties},"
                f"resets:{top_stall.position_resets},"
                f"Locked:{top_stall.locked_windows}/{top_stall.decision_windows}"
            ),
            evidence=(
                "fixed 26-case interval/length sweep measures the repeating "
                "post-first-Position-Reset regime in simulated time: every case "
                "must keep Locked below half of elapsed time and below one full "
                "20s uninterrupted dwell; decision-window share is diagnostic only"
            ),
        ),
        V03BGateMeasurement(
            letter="B",
            name="stalemated attacker remains engaged",
            status=V02GateStatus.PASS if gate_b_pass else V02GateStatus.OPEN,
            metric=(
                f"attempts={stalemate.attempts}; "
                f"Top penalties={stalemate.top_penalties}; "
                f"Bottom penalties={stalemate.bottom_penalties}; "
                f"stage={stalemate.final_stage.value if stalemate.final_stage else 'None'}; "
                f"clocks={stalemate.top_clock}/{stalemate.bottom_clock}"
            ),
            evidence=(
                "legal Americana attempts into informed Turn-In Contested holds "
                "reset both attacker and defender advancement clocks"
            ),
        ),
        V03BGateMeasurement(
            letter="C",
            name="stalling attribution is symmetric",
            status=V02GateStatus.PASS if gate_c_pass else V02GateStatus.OPEN,
            metric=(
                f"Top warnings/penalties={symmetry.top_warnings}/{symmetry.top_penalties}; "
                f"Bottom warnings/penalties={symmetry.bottom_warnings}/{symmetry.bottom_penalties}"
            ),
            evidence="the same 20-second persistent-warning ladder can penalize either side",
        ),
        V03BGateMeasurement(
            letter="D",
            name="penalty stops at Neutral-side boundary",
            status=V02GateStatus.PASS if gate_d_pass else V02GateStatus.OPEN,
            metric=(
                f"warnings={boundary.warnings}; free_windows={boundary.free_windows}; "
                f"axis={boundary.axis_before:+.2f}->{boundary.axis_after:+.2f}; "
                f"band={boundary.band_after.value}; "
                f"clock={boundary.clock_before}->{boundary.clock_after}"
            ),
            evidence=(
                "Top offending at Loose cannot cross Neutral; Bottom receives a "
                "zero-simulated-time free initiative window instead"
            ),
        ),
        V03BGateMeasurement(
            letter="E",
            name="Gate-B deferral guard remains intact",
            status=V02GateStatus.PASS if gate_e_pass else V02GateStatus.OPEN,
            metric=(
                f"v03b_response_commitment_present={v03b_response_commitment_present}; "
                f"recognition_present={recognition_present}; "
                f"current v0.3a Gate B={v03a_gate_b.status.value}"
            ),
            evidence=(
                "v0.3b itself still adds no response commitment or "
                "Recognition/information mechanic; later v0.4a capability may "
                "legitimately expire the global v0.3a Gate-B deferral"
            ),
        ),
        V03BGateMeasurement(
            letter="F",
            name="stalling consequences are directional and monotonic",
            status=V02GateStatus.PASS if gate_f_pass else V02GateStatus.OPEN,
            metric=(
                f"cases={escalation.cases}; "
                f"backward={escalation.backward_effects}; "
                f"weaker_later={escalation.weaker_escalations}; "
                f"boundary_mismatches={escalation.boundary_mismatches}; "
                f"Bottom-lowering={escalation.bottom_axis_lowering_cases}; "
                f"classic Bottom-lowering={escalation.classic_bottom_axis_lowering}"
            ),
            evidence=(
                "for both offender sides across every 0.1-axis state compatible "
                "with each persisted band, offense 3+ must move toward the "
                "non-staller (or grant that player free initiative) and may "
                "not be weaker than offense 2 from the same state"
            ),
        ),
    )


def render_v03b_definition_of_done() -> tuple[str, ...]:
    return tuple(gate.render() for gate in measure_v03b_definition_of_done())


@lru_cache(maxsize=1)
def _v03b_random_standard_batch():
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
        enable_v03_submissions=True,
        enable_v03b_stalling=True,
    )


@lru_cache(maxsize=1)
def _v03b_informed_standard_batch():
    from ..interfaces.batch import (
        BatchResponderMode,
        run_escape_first_batch,
    )

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
        bottom_responder_mode=BatchResponderMode.INFORMED,
        enable_v02_setup=True,
        enable_v03_submissions=True,
        enable_v03b_stalling=True,
    )


def render_v03b_prediction_probe() -> str:
    baseline_random = _v03_standard_batch()
    stalling_random = _v03b_random_standard_batch()
    baseline_informed = _v03_informed_standard_batch()
    stalling_informed = _v03b_informed_standard_batch()

    baseline_random_taps = baseline_random.outcome_counts.get(
        "TAP — Americana",
        0,
    )
    stalling_random_taps = stalling_random.outcome_counts.get(
        "TAP — Americana",
        0,
    )
    baseline_informed_taps = baseline_informed.outcome_counts.get(
        "TAP — Americana",
        0,
    )
    stalling_informed_taps = stalling_informed.outcome_counts.get(
        "TAP — Americana",
        0,
    )

    return (
        "V0.3b PREDICTION PROBE — matched 100-seed PRESSURE/ESCAPE: "
        f"Top RESETs {baseline_random.top_reset_count}"
        f"->{stalling_random.top_reset_count}; "
        f"random taps {baseline_random_taps}->{stalling_random_taps}; "
        f"informed taps {baseline_informed_taps}->{stalling_informed_taps}; "
        f"v0.3b warnings Top/Bottom="
        f"{stalling_random.top_stalling_warning_count}/"
        f"{stalling_random.bottom_stalling_warning_count}; "
        f"penalties Top/Bottom="
        f"{stalling_random.top_stalling_penalty_count}/"
        f"{stalling_random.bottom_stalling_penalty_count}; "
        f"Position Resets Top/Bottom="
        f"{stalling_random.top_stalling_position_reset_count}/"
        f"{stalling_random.bottom_stalling_position_reset_count}. "
        "Observational only; no prediction is a tuning gate."
    )


def render_v03b_normal_play_guard() -> str:
    random = _v03b_random_standard_batch()
    informed = _v03b_informed_standard_batch()

    random_clear = (
        random.top_stalling_warning_count == 0
        and random.bottom_stalling_warning_count == 0
        and random.top_stalling_penalty_count == 0
        and random.bottom_stalling_penalty_count == 0
        and random.top_stalling_position_reset_count == 0
        and random.bottom_stalling_position_reset_count == 0
    )
    informed_clear = (
        informed.top_stalling_warning_count == 0
        and informed.bottom_stalling_warning_count == 0
        and informed.top_stalling_penalty_count == 0
        and informed.bottom_stalling_penalty_count == 0
        and informed.top_stalling_position_reset_count == 0
        and informed.bottom_stalling_position_reset_count == 0
    )
    status = "PASS" if random_clear and informed_clear else "OPEN"
    return (
        f"V0.3b NORMAL-PLAY GUARD [{status}]: "
        f"random warnings={random.top_stalling_warning_count}/"
        f"{random.bottom_stalling_warning_count}, penalties="
        f"{random.top_stalling_penalty_count}/"
        f"{random.bottom_stalling_penalty_count}, Position Resets="
        f"{random.top_stalling_position_reset_count}/"
        f"{random.bottom_stalling_position_reset_count}; "
        f"informed warnings={informed.top_stalling_warning_count}/"
        f"{informed.bottom_stalling_warning_count}, penalties="
        f"{informed.top_stalling_penalty_count}/"
        f"{informed.bottom_stalling_penalty_count}, Position Resets="
        f"{informed.top_stalling_position_reset_count}/"
        f"{informed.bottom_stalling_position_reset_count}. "
        "Executable guard; stronger stalling escalation must not punish engaged standard play."
    )



@lru_cache(maxsize=1)
def _v03b_stall_vs_active_bottom_probe() -> V03BStallActiveBottomEvidence:
    from ..interfaces.batch import EscapeFirstInitiatorPolicy
    from ..interfaces.blind import RandomBlindResponder

    matches = 100
    timeouts = 0
    escapes = 0
    warnings = 0
    penalties = 0
    position_resets = 0

    for match_index in range(matches):
        match = _v03b_match(
            axis=1.50,
            initial_clock=300,
            interval_seconds=5,
        )
        match.top.stamina.set_current(100)
        match.bottom.stamina.set_current(100)
        match.set_behaviors(
            top=TopBehavior.PRESSURE,
            bottom=BottomBehavior.ESCAPE,
        )
        policy = EscapeFirstInitiatorPolicy()
        responder = RandomBlindResponder(42 + match_index)

        while not match.ended:
            free_window = match.consume_free_initiative_window()
            if free_window is None:
                match.advance()
                if match.ended:
                    break

            side = match.initiator
            if side is Side.TOP:
                reset = match.reset_window()
                if reset.stalling_consequence == "WARNING":
                    warnings += 1
                elif reset.position_reset:
                    position_resets += 1
                elif (
                    reset.penalty_axis_before is not None
                    and reset.penalty_axis_after is not None
                    and reset.penalty_axis_after != reset.penalty_axis_before
                ):
                    penalties += 1
                continue

            decision = policy.choose(match)
            if decision.action_id is None:
                match.reset_window()
                continue

            hidden = responder.choose(
                Side.TOP,
                allowed_response_ids=match.legal_response_ids(
                    decision.action_id
                ),
                fallback_response_id=policy._ready_fallback_response_id(
                    match,
                    decision.action_id,
                ),
            )
            match.attempt(
                action_id=decision.action_id,
                response_id=hidden.response_id,
                commitment=Commitment.MEDIUM,
            )

        if match.exit_destination is not None:
            escapes += 1
        elif match.exit_reason == "TIMEOUT — Mount retained":
            timeouts += 1

    return V03BStallActiveBottomEvidence(
        matches=matches,
        timeouts=timeouts,
        escapes=escapes,
        warnings=warnings,
        penalties=penalties,
        position_resets=position_resets,
    )


def render_v03b_stall_vs_active_bottom_observation() -> str:
    evidence = _v03b_stall_vs_active_bottom_probe()
    return (
        "V0.3b STALL-vs-ACTIVE-BOTTOM OBSERVATION: "
        f"matches={evidence.matches}; "
        f"timeouts={evidence.timeouts}; escapes={evidence.escapes}; "
        f"warnings={evidence.warnings}; penalties={evidence.penalties}; "
        f"Position Resets={evidence.position_resets}. "
        "Observational only: v0 does not yet define whether a Mount-retained "
        "timeout is a win, draw, or loss; scoring/points consequences belong "
        "to the later ruleset layer."
    )


def measure_v03a_definition_of_done() -> tuple[V03GateMeasurement, ...]:
    locked_probability, policy_selected = _v03_locked_submission_probe()
    response_commitment_present = _v03_response_commitment_present()
    recognition_present = _v03_recognition_mechanic_present()
    random_batch = (
        _v04_random_standard_batch()
        if response_commitment_present
        else _v03_standard_batch()
    )
    informed_batch = (
        _v04_informed_standard_batch()
        if response_commitment_present
        else _v03_informed_standard_batch()
    )
    tap_count = informed_batch.outcome_counts.get("TAP — Americana", 0)
    tap_rate = tap_count / informed_batch.matches
    random_tap_count = random_batch.outcome_counts.get("TAP — Americana", 0)
    random_tap_rate = random_tap_count / random_batch.matches
    gate_b_status = _v03_gate_b_status(
        tap_rate=tap_rate,
        response_commitment_present=response_commitment_present,
        recognition_present=recognition_present,
    )
    gate_b_evidence = (
        (
            "Response commitment is now a live runtime capability, so the "
            "self-expiring deferral has ended and the unchanged "
            "0% < informed Tap < 50% criterion is active. Public MATCH "
            "commitment still lets the informed defender hold conversion at "
            "0 taps; this is evidence for the later Recognition/information "
            "slice, not a reason to retune the Gate-B range. Random response "
            "remains contrast only."
        )
        if response_commitment_present
        else (
            "DEFERRED while response commitment and Recognition/information "
            "are both absent; the deferral auto-expires when either capability "
            "becomes present. LOW=3 moved informed Threat reachability from "
            "0 to 78/100, but full-match conversion remains blocked because "
            "sustained PRESSURE exhausts both fighters: Exhausted initiator -1 "
            "plus Exhausted responder +1 cancels to 0. When the deferral "
            "expires, the unchanged 0% < informed Tap < 50% criterion resumes; "
            "random response remains contrast only."
        )
    )
    defense = _v03_best_defense_evidence()
    defense_pass = all(
        item.reachable_states > 0
        and item.best_contested_states == item.reachable_states
        and item.best_defender_win_states == 0
        and item.guaranteed_advance_states == 0
        for item in defense.values()
    )
    attacker_changes, defender_changes, cancellation_mismatches, cases = (
        _v03_exhaustion_differentials()
    )
    informed = _v03_informed_exhausted_defender_probe()

    defense_metric = ",".join(
        f"{stage.value}:{item.reachable_states}/"
        f"best-contested:{item.best_contested_states}/"
        f"defender-wins:{item.best_defender_win_states}/"
        f"guaranteed:{item.guaranteed_advance_states}"
        for stage, item in defense.items()
    )

    return (
        V03GateMeasurement(
            letter="A",
            name="Locked submission purpose",
            status=(
                V02GateStatus.PASS
                if locked_probability > 0 and policy_selected
                else V02GateStatus.OPEN
            ),
            metric=(
                f"Locked submission-progress probability={locked_probability:.3f}; "
                f"policy_selected={policy_selected}"
            ),
            evidence=(
                "submission progress is ranked before setup/position/RESET with no axis conversion"
            ),
        ),
        V03GateMeasurement(
            letter="B",
            name="competent-defender submission finish rate",
            status=gate_b_status,
            metric=(
                f"response_commitment_present={response_commitment_present}; "
                f"recognition_present={recognition_present}; "
                f"informed Tap={tap_count}/{informed_batch.matches} ({tap_rate:.1%}); "
                f"Threat={informed_batch.matches_reached_submission_threat}; "
                f"Control={informed_batch.matches_reached_submission_control}; "
                f"Finish={informed_batch.matches_reached_submission_finish}; "
                f"stage-attempts={informed_batch.top_submission_attempt_count}; "
                f"random contrast Tap={random_tap_count}/{random_batch.matches} "
                f"({random_tap_rate:.1%})"
            ),
            evidence=gate_b_evidence,
        ),
        V03GateMeasurement(
            letter="C",
            name="fresh best defense holds stage",
            status=V02GateStatus.PASS if defense_pass else V02GateStatus.OPEN,
            metric=defense_metric,
            evidence=(
                "at every reachable PRESSURE/ESCAPE fresh stage state, "
                "informed best defense is exactly Contested: no advance and no defender win"
            ),
        ),
        V03GateMeasurement(
            letter="D",
            name="submission exhaustion sensitivity",
            status=(
                V02GateStatus.PASS
                if attacker_changes > 0
                and defender_changes > 0
                and cancellation_mismatches == 0
                else V02GateStatus.OPEN
            ),
            metric=(
                f"attacker-only changes={attacker_changes}; "
                f"defender-only changes={defender_changes}; "
                f"both-Exhausted cancellation mismatches={cancellation_mismatches}/{cases}"
            ),
            evidence="one-sided exhaustion must matter in both directions and both Exhausted must cancel",
        ),
        V03GateMeasurement(
            letter="E",
            name="informed exhausted defender is not a perfect lock",
            status=(
                V02GateStatus.PASS
                if informed.tapped
                else V02GateStatus.OPEN
            ),
            metric=(
                f"tapped={informed.tapped}; "
                f"best-responses={','.join(informed.selected_responses) or 'none'}; "
                f"final-grades={','.join(grade.display for grade in informed.final_grades) or 'none'}"
            ),
            evidence=(
                "Top Fresh vs Bottom Exhausted at active Threat must reach Tap "
                "even when Bottom chooses the lowest-grade legal response at every stage"
            ),
        ),
    )


def render_v03a_definition_of_done() -> tuple[str, ...]:
    return tuple(gate.render() for gate in measure_v03a_definition_of_done())


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


@dataclass(frozen=True, slots=True)
class V04GateMeasurement:
    letter: str
    name: str
    status: V02GateStatus
    metric: str
    evidence: str

    def render(self) -> str:
        return (
            f"V0.4a DOD GATE {self.letter} [{self.status.value}]: "
            f"{self.name} — {self.metric}; {self.evidence}"
        )


def _v04_axis_value(result) -> float:
    world = result.axis_after - result.axis_before
    return world if result.initiator is Side.TOP else -world


def _v04_outcome_no_worse(candidate, reference) -> bool:
    return (
        candidate.final_grade >= reference.final_grade
        and (
            reference.exit_destination is None
            or candidate.exit_destination is not None
        )
        and _v04_axis_value(candidate) + 1e-12
        >= _v04_axis_value(reference)
    )


def _v04_outcome_strictly_better(candidate, reference) -> bool:
    return (
        candidate.final_grade > reference.final_grade
        or (
            candidate.exit_destination is not None
            and reference.exit_destination is None
        )
        or _v04_axis_value(candidate)
        > _v04_axis_value(reference) + 1e-12
    )


@lru_cache(maxsize=1)
def _v04_medium_identity_probe() -> tuple[int, int, int]:
    """Return cases, enabled MEDIUM mismatches, disabled response-param mismatches."""
    from ..engine.match import MountMatch

    cases = 0
    enabled_mismatches = 0
    disabled_param_mismatches = 0
    stamina_pairs = ((100, 100), (25, 100), (100, 25), (25, 25))

    for side in (Side.TOP, Side.BOTTOM):
        for band, axis in _V02_BAND_ANCHORS.items():
            for top_behavior in V0_TOP_BEHAVIORS:
                for bottom_behavior in (
                    BottomBehavior.ESCAPE,
                    BottomBehavior.PROTECT,
                ):
                    for action in actions_for(side):
                        for response in responses_for(side.opponent):
                            for initiator_stamina, responder_stamina in stamina_pairs:
                                cases += 1
                                disabled = MountMatch(
                                    starting_axis=axis,
                                    enable_v04_commitment_semantics=False,
                                )
                                disabled.initiator = side
                                disabled.set_behaviors(
                                    top=top_behavior,
                                    bottom=bottom_behavior,
                                )
                                disabled.competitor(side).stamina.set_current(
                                    initiator_stamina
                                )
                                disabled.competitor(side.opponent).stamina.set_current(
                                    responder_stamina
                                )
                                baseline = disabled.attempt(
                                    action_id=action.id,
                                    response_id=response.id,
                                    commitment=Commitment.MEDIUM,
                                ).resolution

                                ignored = MountMatch(
                                    starting_axis=axis,
                                    enable_v04_commitment_semantics=False,
                                )
                                ignored.initiator = side
                                ignored.set_behaviors(
                                    top=top_behavior,
                                    bottom=bottom_behavior,
                                )
                                ignored.competitor(side).stamina.set_current(
                                    initiator_stamina
                                )
                                ignored.competitor(side.opponent).stamina.set_current(
                                    responder_stamina
                                )
                                disabled_with_response = ignored.attempt(
                                    action_id=action.id,
                                    response_id=response.id,
                                    commitment=Commitment.MEDIUM,
                                    response_commitment=Commitment.HIGH,
                                ).resolution

                                enabled = MountMatch(
                                    starting_axis=axis,
                                    enable_v04_commitment_semantics=True,
                                )
                                enabled.initiator = side
                                enabled.set_behaviors(
                                    top=top_behavior,
                                    bottom=bottom_behavior,
                                )
                                enabled.competitor(side).stamina.set_current(
                                    initiator_stamina
                                )
                                enabled.competitor(side.opponent).stamina.set_current(
                                    responder_stamina
                                )
                                medium = enabled.attempt(
                                    action_id=action.id,
                                    response_id=response.id,
                                    commitment=Commitment.MEDIUM,
                                    response_commitment=Commitment.MEDIUM,
                                ).resolution

                                if medium != baseline:
                                    enabled_mismatches += 1
                                if disabled_with_response != baseline:
                                    disabled_param_mismatches += 1

    return cases, enabled_mismatches, disabled_param_mismatches


@lru_cache(maxsize=1)
def _v04_commitment_dominance_probe() -> tuple[int, tuple[str, ...]]:
    """Pairwise global dominance across the fully-funded exchange surface.

    Response commitment is itself part of v0.4a state, so every selectable
    responder commitment is included rather than fixing one convenient level.
    """
    from ..engine.match import MountMatch

    pairs = {
        (left, right): {
            "all_no_worse": True,
            "any_strict": (
                DEFAULT_STAMINA_COST_POLICY.cost(left)
                < DEFAULT_STAMINA_COST_POLICY.cost(right)
            ),
        }
        for left in Commitment
        for right in Commitment
        if left is not right
        and DEFAULT_STAMINA_COST_POLICY.cost(left)
        <= DEFAULT_STAMINA_COST_POLICY.cost(right)
    }
    cases = 0

    for side in (Side.TOP, Side.BOTTOM):
        for _band, axis in _V02_BAND_ANCHORS.items():
            for top_behavior in V0_TOP_BEHAVIORS:
                for bottom_behavior in (
                    BottomBehavior.ESCAPE,
                    BottomBehavior.PROTECT,
                ):
                    for action in actions_for(side):
                        for response in responses_for(side.opponent):
                            for responder_commitment in Commitment:
                                cases += 1
                                results = {}
                                for commitment in Commitment:
                                    match = MountMatch(
                                        starting_axis=axis,
                                        enable_v04_commitment_semantics=True,
                                    )
                                    match.initiator = side
                                    match.set_behaviors(
                                        top=top_behavior,
                                        bottom=bottom_behavior,
                                    )
                                    results[commitment] = (
                                        match.preview_attempt_resolution(
                                            action_id=action.id,
                                            response_id=response.id,
                                            commitment=commitment,
                                            response_commitment=responder_commitment,
                                        )
                                    )
                                for pair, state in pairs.items():
                                    left, right = pair
                                    if not _v04_outcome_no_worse(
                                        results[left],
                                        results[right],
                                    ):
                                        state["all_no_worse"] = False
                                    if _v04_outcome_strictly_better(
                                        results[left],
                                        results[right],
                                    ):
                                        state["any_strict"] = True

    dominating = tuple(
        f"{left.value}>{right.value}"
        for (left, right), state in pairs.items()
        if state["all_no_worse"] and state["any_strict"]
    )
    return cases, dominating


@lru_cache(maxsize=1)
def _v04_stalemate_probe() -> tuple[int, int, int]:
    """Return all Contested matched/overmatch cases, breaks, submission cases."""
    from ..engine.match import MountMatch

    cases = 0
    breaks = 0
    submission_cases = 0
    levels = tuple(Commitment)

    # Broad ordinary-exchange surface.
    for side in (Side.TOP, Side.BOTTOM):
        for _band, axis in _V02_BAND_ANCHORS.items():
            for top_behavior in V0_TOP_BEHAVIORS:
                for bottom_behavior in (
                    BottomBehavior.ESCAPE,
                    BottomBehavior.PROTECT,
                ):
                    for action in actions_for(side):
                        for response in responses_for(side.opponent):
                            baseline = MountMatch(starting_axis=axis)
                            baseline.initiator = side
                            baseline.set_behaviors(
                                top=top_behavior,
                                bottom=bottom_behavior,
                            )
                            base_result = baseline.preview_attempt_resolution(
                                action_id=action.id,
                                response_id=response.id,
                                commitment=Commitment.MEDIUM,
                            )
                            if base_result.final_grade is not Grade.CONTESTED:
                                continue
                            for attacker in levels:
                                for defender in levels:
                                    if (
                                        MountMatch._commitment_rank(defender)
                                        < MountMatch._commitment_rank(attacker)
                                    ):
                                        continue
                                    match = MountMatch(
                                        starting_axis=axis,
                                        enable_v04_commitment_semantics=True,
                                    )
                                    match.initiator = side
                                    match.set_behaviors(
                                        top=top_behavior,
                                        bottom=bottom_behavior,
                                    )
                                    result = match.preview_attempt_resolution(
                                        action_id=action.id,
                                        response_id=response.id,
                                        commitment=attacker,
                                        response_commitment=defender,
                                    )
                                    cases += 1
                                    if result.final_grade is not Grade.CONTESTED:
                                        breaks += 1

    # Explicit active Americana stages, restricted to the fresh states
    # that are actually Contested before v0.4a commitment semantics.
    for stage in SubmissionStage:
        for axis in (2.50, 3.50):
            for bottom_behavior in BottomBehavior:
                baseline = MountMatch(
                    starting_axis=axis,
                    enable_v02_setup=True,
                    enable_v03_submissions=True,
                    enable_v04_commitment_semantics=False,
                )
                baseline.submission_state.stage = stage
                baseline.initiator = Side.TOP
                baseline.set_behaviors(
                    top=TopBehavior.PRESSURE,
                    bottom=bottom_behavior,
                )
                baseline_result = baseline.preview_attempt_resolution(
                    action_id=TOP_AMERICANA_SUBMISSION_FINISH,
                    response_id=BOTTOM_RESPONSE_TURN_IN_RECOVERY,
                    commitment=Commitment.MEDIUM,
                )
                if baseline_result.final_grade is not Grade.CONTESTED:
                    continue

                for attacker in levels:
                    for defender in levels:
                        if (
                            MountMatch._commitment_rank(defender)
                            < MountMatch._commitment_rank(attacker)
                        ):
                            continue
                        match = MountMatch(
                            starting_axis=axis,
                            enable_v02_setup=True,
                            enable_v03_submissions=True,
                            enable_v04_commitment_semantics=True,
                        )
                        match.submission_state.stage = stage
                        match.initiator = Side.TOP
                        match.set_behaviors(
                            top=TopBehavior.PRESSURE,
                            bottom=bottom_behavior,
                        )
                        result = match.preview_attempt_resolution(
                            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
                            response_id=BOTTOM_RESPONSE_TURN_IN_RECOVERY,
                            commitment=attacker,
                            response_commitment=defender,
                        )
                        cases += 1
                        submission_cases += 1
                        if result.final_grade is not Grade.CONTESTED:
                            breaks += 1

    return cases, breaks, submission_cases


@lru_cache(maxsize=1)
def _v04_feint_probe() -> tuple[bool, int, int, int]:
    """Return Ready entry, LOW/UNFUNDED violations, ordinary advances, cases."""
    from ..engine.match import MountMatch

    ready = MountMatch(
        starting_axis=2.50,
        enable_v02_setup=True,
        enable_v03_submissions=True,
        enable_v04_commitment_semantics=True,
    )
    ready.setup_state.advance(TOP_AMERICANA_ARM_ISOLATION)
    ready.setup_state.advance(TOP_AMERICANA_ARM_ISOLATION)
    ready.initiator = Side.TOP
    ready.attempt(
        action_id=TOP_AMERICANA_ARM_ISOLATION,
        response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
        commitment=Commitment.LOW,
        response_commitment=Commitment.LOW,
    )
    ready_entry = ready.submission_state.stage is SubmissionStage.THREAT

    violations = 0
    cases = 0
    for stage in SubmissionStage:
        for funded in (True, False):
            match = MountMatch(
                starting_axis=2.50,
                enable_v02_setup=True,
                enable_v03_submissions=True,
                enable_v04_commitment_semantics=True,
            )
            match.submission_state.stage = stage
            match.initiator = Side.TOP
            requested = Commitment.LOW if funded else Commitment.HIGH
            if not funded:
                # Both Exhausted cancels the existing exhaustion modifier so
                # the UNFUNDED case proves the feint cap itself, not a merely
                # Contested exchange caused by one-sided exhaustion.
                match.top.stamina.set_current(2)
                match.bottom.stamina.set_current(2)
            match.attempt(
                action_id=TOP_AMERICANA_SUBMISSION_FINISH,
                response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
                commitment=requested,
                response_commitment=Commitment.LOW,
            )
            cases += 1
            if match.submission_tapped or match.submission_state.stage is not stage:
                violations += 1

    ordinary_advances = 0
    for commitment in (Commitment.MEDIUM, Commitment.HIGH):
        match = MountMatch(
            starting_axis=2.50,
            enable_v02_setup=True,
            enable_v03_submissions=True,
            enable_v04_commitment_semantics=True,
        )
        match.submission_state.stage = SubmissionStage.THREAT
        match.initiator = Side.TOP
        match.attempt(
            action_id=TOP_AMERICANA_SUBMISSION_FINISH,
            response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
            commitment=commitment,
            response_commitment=commitment,
        )
        if match.submission_state.stage is SubmissionStage.CONTROL:
            ordinary_advances += 1

    return ready_entry, violations, ordinary_advances, cases


@lru_cache(maxsize=1)
def _v04_undercommitment_probe() -> tuple[int, int, int]:
    """Return compared states, regressions, strict attacker improvements."""
    from ..engine.match import MountMatch

    comparisons = 0
    regressions = 0
    improvements = 0
    lower = {
        Commitment.MEDIUM: (Commitment.LOW,),
        Commitment.HIGH: (Commitment.LOW, Commitment.MEDIUM),
    }

    for side in (Side.TOP, Side.BOTTOM):
        for _band, axis in _V02_BAND_ANCHORS.items():
            for top_behavior in V0_TOP_BEHAVIORS:
                for bottom_behavior in (
                    BottomBehavior.ESCAPE,
                    BottomBehavior.PROTECT,
                ):
                    for action in actions_for(side):
                        for response in responses_for(side.opponent):
                            for attack_commitment, lower_levels in lower.items():
                                matched_match = MountMatch(
                                    starting_axis=axis,
                                    enable_v04_commitment_semantics=True,
                                )
                                matched_match.initiator = side
                                matched_match.set_behaviors(
                                    top=top_behavior,
                                    bottom=bottom_behavior,
                                )
                                matched = matched_match.preview_attempt_resolution(
                                    action_id=action.id,
                                    response_id=response.id,
                                    commitment=attack_commitment,
                                    response_commitment=attack_commitment,
                                )
                                for defense_commitment in lower_levels:
                                    under_match = MountMatch(
                                        starting_axis=axis,
                                        enable_v04_commitment_semantics=True,
                                    )
                                    under_match.initiator = side
                                    under_match.set_behaviors(
                                        top=top_behavior,
                                        bottom=bottom_behavior,
                                    )
                                    under = under_match.preview_attempt_resolution(
                                        action_id=action.id,
                                        response_id=response.id,
                                        commitment=attack_commitment,
                                        response_commitment=defense_commitment,
                                    )
                                    comparisons += 1
                                    if not _v04_outcome_no_worse(under, matched):
                                        regressions += 1
                                    if _v04_outcome_strictly_better(under, matched):
                                        improvements += 1

    return comparisons, regressions, improvements


@lru_cache(maxsize=1)
def _v04_stalling_feint_probe() -> tuple[int, int, int, int]:
    """Return initiator before/after and defender before/after clocks."""
    from ..engine.match import MountMatch

    match = MountMatch(
        starting_axis=2.50,
        enable_v02_setup=True,
        enable_v03_submissions=True,
        enable_v03b_stalling=True,
        enable_v04_commitment_semantics=True,
    )
    match.submission_state.stage = SubmissionStage.THREAT
    match.initiator = Side.TOP
    match.stalling_tracker.advance(20)
    top_before = match.advancement_clock(Side.TOP)
    bottom_before = match.advancement_clock(Side.BOTTOM)
    match.attempt(
        action_id=TOP_AMERICANA_SUBMISSION_FINISH,
        response_id=BOTTOM_RESPONSE_FOREARM_FRAME,
        commitment=Commitment.LOW,
        response_commitment=Commitment.LOW,
    )
    return (
        top_before,
        match.advancement_clock(Side.TOP),
        bottom_before,
        match.advancement_clock(Side.BOTTOM),
    )


@lru_cache(maxsize=1)
def _v04_affordability_probe() -> tuple[int, int, int, int, int, int]:
    """Funding evidence for HIGH response requested at 5 and 2 stamina."""
    from ..engine.match import MountMatch

    low_funded = MountMatch(
        starting_axis=1.50,
        enable_v04_commitment_semantics=True,
    )
    low_funded.bottom.stamina.set_current(5)
    low_result = low_funded.attempt(
        action_id=actions_for(Side.TOP)[0].id,
        response_id=responses_for(Side.BOTTOM)[0].id,
        commitment=Commitment.HIGH,
        response_commitment=Commitment.HIGH,
    )

    unfunded = MountMatch(
        starting_axis=1.50,
        enable_v04_commitment_semantics=True,
    )
    unfunded.bottom.stamina.set_current(2)
    unfunded_result = unfunded.attempt(
        action_id=actions_for(Side.TOP)[0].id,
        response_id=responses_for(Side.BOTTOM)[0].id,
        commitment=Commitment.HIGH,
        response_commitment=Commitment.HIGH,
    )

    same_low = MountMatch(
        starting_axis=1.50,
        enable_v04_commitment_semantics=True,
    )
    same_low.bottom.stamina.set_current(5)
    same_low_result = same_low.attempt(
        action_id=actions_for(Side.TOP)[0].id,
        response_id=responses_for(Side.BOTTOM)[0].id,
        commitment=Commitment.HIGH,
        response_commitment=Commitment.LOW,
    )

    same_unfunded = MountMatch(
        starting_axis=1.50,
        enable_v04_commitment_semantics=True,
    )
    same_unfunded.bottom.stamina.set_current(2)
    same_unfunded_result = same_unfunded.attempt(
        action_id=actions_for(Side.TOP)[0].id,
        response_id=responses_for(Side.BOTTOM)[0].id,
        commitment=Commitment.HIGH,
        response_commitment=Commitment.LOW,
    )

    equivalence_mismatches = int(
        low_result.resolution != same_low_result.resolution
    ) + int(
        unfunded_result.resolution != same_unfunded_result.resolution
    )

    return (
        low_result.response_effective_cost,
        low_result.response_funding_gap,
        low_result.response_undercommitment_modifier,
        unfunded_result.response_effective_cost,
        unfunded_result.response_funding_gap,
        equivalence_mismatches,
    )


@lru_cache(maxsize=1)
def _v04_double_cost_probe() -> tuple[int, int, int]:
    from ..engine.match import MountMatch

    match = MountMatch(
        starting_axis=2.50,
        enable_v02_setup=True,
        enable_v03_submissions=True,
        enable_v04_commitment_semantics=True,
    )
    match.submission_state.stage = SubmissionStage.THREAT
    match.initiator = Side.TOP
    result = match.attempt(
        action_id=TOP_AMERICANA_SUBMISSION_FINISH,
        response_id=BOTTOM_RESPONSE_TURN_IN_RECOVERY,
        commitment=Commitment.MEDIUM,
        response_commitment=Commitment.MEDIUM,
    )
    hold = (
        match.history.submission_hold_stamina_charged_history[-1]
        if match.history.submission_hold_stamina_charged_history
        else 0
    )
    response = (
        result.response_stamina.charged
        if result.response_stamina is not None
        else 0
    )
    return response, hold, match.bottom.stamina.current


@lru_cache(maxsize=1)
def measure_v04a_definition_of_done() -> tuple[V04GateMeasurement, ...]:
    identity_cases, identity_mismatches, disabled_mismatches = (
        _v04_medium_identity_probe()
    )
    v02_gate7 = next(
        gate for gate in measure_v02_definition_of_done()
        if gate.number == 7
    )
    _, advantage_states = _commitment_low_dominance_probe()
    dominance_cases, dominating = _v04_commitment_dominance_probe()
    stalemate_cases, stalemate_breaks, submission_stalemates = (
        _v04_stalemate_probe()
    )
    ready_entry, feint_violations, ordinary_advances, feint_cases = (
        _v04_feint_probe()
    )
    under_cases, under_regressions, under_improvements = (
        _v04_undercommitment_probe()
    )

    from ..engine.match import MountMatch

    disabled_capability = MountMatch(
        enable_v04_commitment_semantics=False
    ).response_commitment_enabled
    enabled_capability = MountMatch(
        enable_v04_commitment_semantics=True
    ).response_commitment_enabled
    v03_gate_b = next(
        gate for gate in measure_v03a_definition_of_done()
        if gate.letter == "B"
    )
    informed_mode = _v04_informed_standard_batch().response_commitment_mode.value

    top_before, top_after, bottom_before, bottom_after = (
        _v04_stalling_feint_probe()
    )
    (
        funded_cost,
        funded_gap,
        funded_mismatch,
        unfunded_cost,
        unfunded_gap,
        affordability_equivalence_mismatches,
    ) = _v04_affordability_probe()

    gate_a = (
        identity_cases > 0
        and identity_mismatches == 0
        and disabled_mismatches == 0
    )
    gate_b = (
        v02_gate7.status is V02GateStatus.PASS
        and advantage_states > 0
    )
    gate_c = dominance_cases > 0 and not dominating
    gate_d = stalemate_cases > 0 and stalemate_breaks == 0
    gate_e = (
        ready_entry
        and feint_cases == 6
        and feint_violations == 0
        and ordinary_advances == 2
    )
    gate_f = (
        under_cases > 0
        and under_regressions == 0
        and under_improvements > 0
    )
    gate_g = (
        not disabled_capability
        and enabled_capability
        and _v03_response_commitment_present()
        and v03_gate_b.status is not V02GateStatus.DEFERRED
        and informed_mode == "match"
    )
    gate_h = (
        top_before == 20
        and top_after == 20
        and bottom_before == 20
        and bottom_after == 0
    )
    gate_i = (
        funded_cost == 3
        and funded_gap == 9
        and funded_mismatch == 1
        and unfunded_cost == 0
        and unfunded_gap == 12
        and affordability_equivalence_mismatches == 0
    )

    return (
        V04GateMeasurement(
            letter="A",
            name="feature-off compatibility and MEDIUM identity",
            status=V02GateStatus.PASS if gate_a else V02GateStatus.OPEN,
            metric=(
                f"cases={identity_cases}; enabled_MEDIUM_mismatches={identity_mismatches}; "
                f"disabled_response-param_mismatches={disabled_mismatches}"
            ),
            evidence=(
                "response commitment is inert when disabled and effective MEDIUM/MEDIUM "
                "preserves the current exchange ResolutionResult"
            ),
        ),
        V04GateMeasurement(
            letter="B",
            name="v0.2 Gate 7 closes from real commitment meaning",
            status=V02GateStatus.PASS if gate_b else V02GateStatus.OPEN,
            metric=(
                f"v0.2 Gate 7={v02_gate7.status.value}; "
                f"higher-commitment advantage states={advantage_states}"
            ),
            evidence="existing Gate-7 dominance probe runs on v0.4a-enabled exchanges",
        ),
        V04GateMeasurement(
            letter="C",
            name="no selectable commitment globally dominates",
            status=V02GateStatus.PASS if gate_c else V02GateStatus.OPEN,
            metric=(
                f"states={dominance_cases}; "
                f"dominating_pairs={','.join(dominating) if dominating else 'none'}"
            ),
            evidence=(
                "dominance requires no-worse grade/exit/realized-axis in every state "
                "plus no-greater cost and at least one strict advantage"
            ),
        ),
        V04GateMeasurement(
            letter="D",
            name="matched commitment preserves Contested stalemates",
            status=V02GateStatus.PASS if gate_d else V02GateStatus.OPEN,
            metric=(
                f"cases={stalemate_cases}; breaks={stalemate_breaks}; "
                f"active-Americana cases={submission_stalemates}"
            ),
            evidence=(
                "fresh Contested exchanges remain Contested whenever defender "
                "effective commitment matches or exceeds attacker commitment"
            ),
        ),
        V04GateMeasurement(
            letter="E",
            name="LOW/UNFUNDED feints cannot advance beyond Threat",
            status=V02GateStatus.PASS if gate_e else V02GateStatus.OPEN,
            metric=(
                f"LOW Ready entry={ready_entry}; capped_cases={feint_cases}; "
                f"violations={feint_violations}; MEDIUM/HIGH advances={ordinary_advances}/2"
            ),
            evidence=(
                "LOW may create Threat, but LOW/UNFUNDED active-stage success "
                "cannot reach Control, Finish, or Tap"
            ),
        ),
        V04GateMeasurement(
            letter="F",
            name="response under-commitment only helps attacker",
            status=V02GateStatus.PASS if gate_f else V02GateStatus.OPEN,
            metric=(
                f"comparisons={under_cases}; regressions={under_regressions}; "
                f"strict improvements={under_improvements}"
            ),
            evidence=(
                "lower response commitment is compared with matched commitment "
                "on identical fully-funded exchange states"
            ),
        ),
        V04GateMeasurement(
            letter="G",
            name="Gate-B deferral expires from real runtime capability",
            status=V02GateStatus.PASS if gate_g else V02GateStatus.OPEN,
            metric=(
                f"disabled={disabled_capability}; enabled={enabled_capability}; "
                f"v0.3a Gate B={v03_gate_b.status.value}; informed response commitment={informed_mode}"
            ),
            evidence=(
                "capability is a match runtime feature and Gate-B informed batch "
                "actually runs MATCH response commitment"
            ),
        ),
        V04GateMeasurement(
            letter="H",
            name="feints cannot dodge stalling clock",
            status=V02GateStatus.PASS if gate_h else V02GateStatus.OPEN,
            metric=(
                f"Top clock {top_before}->{top_after}; "
                f"Bottom clock {bottom_before}->{bottom_after}"
            ),
            evidence=(
                "feint-capped initiator gets no progress-clock reset while the "
                "legal defender receives defensive-engagement credit"
            ),
        ),
        V04GateMeasurement(
            letter="I",
            name="response affordability controls tactical credit",
            status=V02GateStatus.PASS if gate_i else V02GateStatus.OPEN,
            metric=(
                f"5-stamina HIGH request: cost={funded_cost},gap={funded_gap},"
                f"mismatch={funded_mismatch}; 2-stamina HIGH request: "
                f"cost={unfunded_cost},gap={unfunded_gap}; "
                f"effective-equivalence mismatches={affordability_equivalence_mismatches}"
            ),
            evidence=(
                "requested HIGH downgrades to payable LOW or UNFUNDED and cannot "
                "leak unaffordable tactical benefit"
            ),
        ),
    )


def render_v04a_definition_of_done() -> tuple[str, ...]:
    return tuple(gate.render() for gate in measure_v04a_definition_of_done())


def render_v04a_prediction_probe() -> str:
    baseline_random = _v03_standard_batch()
    baseline_informed = _v03_informed_standard_batch()
    random = _v04_random_standard_batch()
    informed = _v04_informed_standard_batch()
    response_cost, hold_cost, bottom_after = _v04_double_cost_probe()

    def taps(summary) -> int:
        return summary.outcome_counts.get("TAP — Americana", 0)

    return (
        "V0.4a PREDICTION PROBE — 100 matched PRESSURE/ESCAPE seeds: "
        f"random taps {taps(baseline_random)}->{taps(random)}; "
        f"informed taps {taps(baseline_informed)}->{taps(informed)}; "
        f"Bottom median stamina random {baseline_random.bottom_final_stamina_median:.1f}"
        f"->{random.bottom_final_stamina_median:.1f}; "
        f"informed {baseline_informed.bottom_final_stamina_median:.1f}"
        f"->{informed.bottom_final_stamina_median:.1f}; "
        f"isolated Contested hold responder cost={response_cost}+{hold_cost}, "
        f"Bottom stamina after={bottom_after}. Observational only."
    )


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
