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
def _exhausted_positive_weight_escape_hits() -> tuple[ReachabilityHit, ...]:
    """Exhausted Bottom exits reachable against positive-weight batch responses."""
    from ..interfaces.blind import RandomBlindResponder

    positive_response_ids = {
        response_id
        for response_id, weight in RandomBlindResponder.POLICY[Side.TOP]
        if weight > 0
    }
    reachability = _collect_escape_reachability(external_grade_modifier=-1)
    hits: list[ReachabilityHit] = []
    for route_hits in reachability.values():
        hits.extend(
            hit for hit in route_hits if hit.response_id in positive_response_ids
        )
    return tuple(hits)


@lru_cache(maxsize=1)
def _commitment_outcome_effect_count() -> int:
    """Count states where funded LOW/MEDIUM/HIGH change the current outcome surface."""
    from ..engine.match import MountMatch

    changed = 0
    for side in (Side.TOP, Side.BOTTOM):
        for band, axis in _V02_BAND_ANCHORS.items():
            for top_behavior in V0_TOP_BEHAVIORS:
                for bottom_behavior in (BottomBehavior.ESCAPE, BottomBehavior.PROTECT):
                    for action in actions_for(side):
                        for response in responses_for(side.opponent):
                            signatures = []
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
                                signatures.append(
                                    _resolution_signature(attempt.resolution)
                                )
                            if len(set(signatures)) > 1:
                                changed += 1
    return changed


def measure_v02_definition_of_done(
    report: CheckReport | None = None,
) -> tuple[V02GateMeasurement, ...]:
    """Compute v0.2 gate status from current executable evidence."""
    if report is None:
        report = run_checks()

    # Gate 1: current perfect-response measurement. When v0.2 introduces
    # Ready-aware legality, run_checks().perfect_response_lock is the hook that
    # must become Ready-aware rather than this gate being manually flipped.
    gate1_pass = not report.perfect_response_lock

    # Gate 2: existing standardized RESET probe.
    reset_probe = render_reset_lock_probe()
    reset_locked_timeout = (
        "TIMEOUT — Mount retained" in reset_probe
        and "band Locked" in reset_probe
    )

    # Gates 4/5 share the same deterministic standard batch.
    standard_batch = _v02_standard_batch()
    bridge_count = standard_batch.bottom_action_counts.get("Bridge", 0)
    top_position_attacks_per_match = (
        standard_batch.top_position_attack_count / standard_batch.matches
    )

    # Gate 3: responder-only outcome differential.
    responder_differences = _responder_exhaustion_differential_count()

    # Gate 6: current positive-weight exhausted escape reachability.
    exhausted_hits = _exhausted_positive_weight_escape_hits()
    exhausted_routes = {
        (hit.action_id, hit.top_behavior, hit.destination)
        for hit in exhausted_hits
    }

    # Gate 7: exhaustive funded commitment outcome differential.
    commitment_effects = _commitment_outcome_effect_count()

    return (
        V02GateMeasurement(
            number=1,
            name="perfect-response lock",
            status=V02GateStatus.PASS if gate1_pass else V02GateStatus.OPEN,
            metric=f"perfect_response_lock={report.perfect_response_lock}",
            evidence=(
                "current checker no longer finds an unrestricted Failure-or-worse "
                "counter for every action"
                if gate1_pass
                else
                "current checker still finds the unrestricted lock"
            ),
        ),
        V02GateMeasurement(
            number=2,
            name="RESET/stalling",
            status=(
                V02GateStatus.OPEN
                if reset_locked_timeout
                else V02GateStatus.PASS
            ),
            metric=f"locked_timeout={reset_locked_timeout}",
            evidence=reset_probe,
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
                if bridge_count > 0
                else V02GateStatus.OPEN
            ),
            metric=(
                f"standard batch Bridge selections={bridge_count}/"
                f"{standard_batch.matches}"
            ),
            evidence=(
                "Bridge is selected by the scripted policy"
                if bridge_count > 0
                else
                "Bridge is never selected in the standard batch"
            ),
        ),
        V02GateMeasurement(
            number=5,
            name="Top post-opening activity",
            status=(
                V02GateStatus.PASS
                if top_position_attacks_per_match > 1.0
                else V02GateStatus.OPEN
            ),
            metric=(
                "standard batch Top position attacks/match="
                f"{top_position_attacks_per_match:.3f}"
            ),
            evidence="pass threshold is >1.000 per match",
        ),
        V02GateMeasurement(
            number=6,
            name="Exhausted Bottom escape reachability",
            status=(
                V02GateStatus.PASS
                if exhausted_routes
                else V02GateStatus.OPEN
            ),
            metric=(
                "positive-weight exhausted escape routes="
                f"{len(exhausted_routes)}"
            ),
            evidence=(
                "at least one route is currently reachable under the batch response mix"
                if exhausted_routes
                else
                "no positive-weight exhausted escape route is reachable"
            ),
        ),
        V02GateMeasurement(
            number=7,
            name="commitment meaning",
            status=(
                V02GateStatus.PASS
                if commitment_effects > 0
                else V02GateStatus.OPEN
            ),
            metric=(
                "funded LOW/MEDIUM/HIGH outcome-differential states="
                f"{commitment_effects}"
            ),
            evidence=(
                "commitment changes at least one current outcome surface"
                if commitment_effects > 0
                else
                "funded commitments remain outcome-equivalent; cost-only LOW dominance remains"
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
