"""D2 post-clear handoff candidate v1e (diagnostic, opt-in).

Implements exactly the semantics frozen in
docs/HANDOFF_OSCILLATION_D2_PREREGISTRATION_V1E.md (preregistration SHA
c4a9c3369b53911eda4d47dd9d814d385470ba8a):

    safe(c) = current_stamina - cost(c) - behavior_reserve > enter_threshold
    behavior_reserve = 2

At an armed (post-first-clear), non-Exhausted Bottom decision window:

    mode active:   RELEASE + ordinary MEDIUM decision if safe(MEDIUM),
                   otherwise RECOVERY HOLD (LOW is never considered)
    mode inactive: MEDIUM if safe(MEDIUM), else LOW if safe(LOW),
                   else ENTER mode + RECOVERY HOLD

An Exhausted Bottom decision window clears the mode (CLEARED_BY_EXHAUSTION)
and uses the adopted LOW_WHILE_EXHAUSTED path unchanged. While the mode is
active, every normal-speed advance uses Bottom CONSERVE (pre-advance only);
the batch's existing post-advance behavior re-choice is unchanged.

The controller holds one boolean per match. The collector is read-only: it
consumes no RNG and mutates no engine state.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..domain.action import AttemptResult, Commitment, RecoveryHoldResult, ResetWindowResult
from ..domain.model import BottomBehavior, Side
from ..domain.stamina import StaminaBand
from ..engine.match import MountMatch

V1E_BEHAVIOR_RESERVE = 2


class PostClearHandoffMode(str, Enum):
    NONE = "NONE"
    V1E_PERSISTENT_CONSERVE_HOLD = "V1E_PERSISTENT_CONSERVE_HOLD"
    # D3-B (docs/BURST_RECOVERY_LOCKOUT_D3B_PREREGISTRATION.md, dc4fc16):
    # one Exhausted LOW token per armed Exhausted episode, then strict
    # initiation lockout until the Exhausted latch clears.
    D3B_EXHAUSTED_TOKEN_LOCKOUT = "D3B_EXHAUSTED_TOKEN_LOCKOUT"


class HandoffDecisionKind(str, Enum):
    """Bottom decision-window classification under v1e."""

    EXHAUSTED = "EXHAUSTED"  # adopted LOW_WHILE_EXHAUSTED path
    UNARMED = "UNARMED"  # before the first clear: adopted behavior
    ORDINARY_MEDIUM = "ORDINARY_MEDIUM"
    ORDINARY_LOW = "ORDINARY_LOW"  # reserve-rule LOW outside the mode
    ENTER_HOLD = "ENTER_HOLD"
    HOLD = "HOLD"
    RELEASE_MEDIUM = "RELEASE_MEDIUM"
    # D3-B kinds.
    ARMED_NORMAL = "ARMED_NORMAL"  # armed, non-Exhausted: adopted decision
    TOKEN = "TOKEN"  # first armed Exhausted decision: adopted LOW path
    LOCKOUT_HOLD = "LOCKOUT_HOLD"  # token consumed, still Exhausted

    @property
    def is_hold(self) -> bool:
        return self in {
            HandoffDecisionKind.ENTER_HOLD,
            HandoffDecisionKind.HOLD,
            HandoffDecisionKind.LOCKOUT_HOLD,
        }


class ModeTransition(str, Enum):
    ENTER = "ENTER"
    RELEASE = "RELEASE"
    CLEARED_BY_EXHAUSTION = "CLEARED_BY_EXHAUSTION"
    PENDING_AT_END = "PENDING_AT_END"


def reserve_safe(
    *,
    stamina: int,
    cost: int,
    enter_threshold: int,
    behavior_reserve: int = V1E_BEHAVIOR_RESERVE,
) -> bool:
    return stamina - cost - behavior_reserve > enter_threshold


@dataclass(frozen=True, slots=True)
class HandoffDecision:
    kind: HandoffDecisionKind
    requested_commitment: Commitment | None
    transition: ModeTransition | None
    mode_before: bool
    mode_after: bool

    @property
    def hold(self) -> bool:
        return self.kind.is_hold


class PostClearHandoffController:
    """Per-match v1e state machine. One boolean; no timer, no counter."""

    def __init__(self) -> None:
        self.recovery_hold_mode = False

    def pre_advance_bottom_behavior(self, chosen: BottomBehavior) -> BottomBehavior:
        """Persistent pre-advance CONSERVE while the mode is active."""
        return BottomBehavior.CONSERVE if self.recovery_hold_mode else chosen

    def observe_advance(self, match: MountMatch) -> None:
        """v1e keeps no latch history of its own."""

    def armed_flag(self, default: bool) -> bool:
        return default

    def pending(self, match: MountMatch) -> bool:
        return self.recovery_hold_mode

    def decide(self, match: MountMatch, *, armed: bool) -> HandoffDecision:
        """Bottom decision window. Must be called only when Bottom initiates."""
        if match.initiator is not Side.BOTTOM:
            raise RuntimeError("v1e decides only at Bottom decision windows")
        before = self.recovery_hold_mode
        pool = match.bottom.stamina
        if pool.band is StaminaBand.EXHAUSTED:
            self.recovery_hold_mode = False
            return HandoffDecision(
                kind=HandoffDecisionKind.EXHAUSTED,
                requested_commitment=None,
                transition=(
                    ModeTransition.CLEARED_BY_EXHAUSTION if before else None
                ),
                mode_before=before,
                mode_after=False,
            )
        if not armed:
            if before:
                raise RuntimeError("recovery-hold mode active before arming")
            return HandoffDecision(
                kind=HandoffDecisionKind.UNARMED,
                requested_commitment=None,
                transition=None,
                mode_before=False,
                mode_after=False,
            )

        threshold = pool.exhaustion_enter_threshold
        stamina = pool.current
        costs = match.stamina_cost_policy
        medium_safe = reserve_safe(
            stamina=stamina,
            cost=costs.cost(Commitment.MEDIUM),
            enter_threshold=threshold,
        )
        if before:
            if medium_safe:
                self.recovery_hold_mode = False
                return HandoffDecision(
                    kind=HandoffDecisionKind.RELEASE_MEDIUM,
                    requested_commitment=Commitment.MEDIUM,
                    transition=ModeTransition.RELEASE,
                    mode_before=True,
                    mode_after=False,
                )
            return HandoffDecision(
                kind=HandoffDecisionKind.HOLD,
                requested_commitment=None,
                transition=None,
                mode_before=True,
                mode_after=True,
            )

        if medium_safe:
            return HandoffDecision(
                kind=HandoffDecisionKind.ORDINARY_MEDIUM,
                requested_commitment=Commitment.MEDIUM,
                transition=None,
                mode_before=False,
                mode_after=False,
            )
        if reserve_safe(
            stamina=stamina,
            cost=costs.cost(Commitment.LOW),
            enter_threshold=threshold,
        ):
            return HandoffDecision(
                kind=HandoffDecisionKind.ORDINARY_LOW,
                requested_commitment=Commitment.LOW,
                transition=None,
                mode_before=False,
                mode_after=False,
            )
        self.recovery_hold_mode = True
        return HandoffDecision(
            kind=HandoffDecisionKind.ENTER_HOLD,
            requested_commitment=None,
            transition=ModeTransition.ENTER,
            mode_before=False,
            mode_after=True,
        )


class D3BTokenLockoutController:
    """D3-B state machine (frozen at dc4fc16). Behavior is never overridden.

    armed:          True from Bottom's first Exhausted -> non-Exhausted clear.
    token_consumed: per Exhausted episode; reset whenever the latch clears.

    At a Bottom decision window (normal or free):
      not armed or not Exhausted -> adopted decision (no override)
      armed, Exhausted, token unused -> TOKEN: consume it; adopted LOW path
          (attempt, or genuine RESET if the policy picks no action)
      armed, Exhausted, token used -> LOCKOUT_HOLD (recovery_hold())

    The latch can clear only inside advance() (behavior recovery), so clears
    are observed after every advance.
    """

    def __init__(self, match: MountMatch) -> None:
        self.armed = False
        self.token_consumed = False
        self._exhausted = match.bottom.stamina.band is StaminaBand.EXHAUSTED

    @property
    def recovery_hold_mode(self) -> bool:
        """Post-token lockout pending (until the latch clears)."""
        return self.armed and self.token_consumed

    def pre_advance_bottom_behavior(self, chosen: BottomBehavior) -> BottomBehavior:
        return chosen

    def observe_advance(self, match: MountMatch) -> None:
        exhausted = match.bottom.stamina.band is StaminaBand.EXHAUSTED
        if self._exhausted and not exhausted:
            self.armed = True
            self.token_consumed = False
        self._exhausted = exhausted

    def armed_flag(self, default: bool) -> bool:
        return self.armed

    def pending(self, match: MountMatch) -> bool:
        return (
            self.armed
            and match.bottom.stamina.band is StaminaBand.EXHAUSTED
        )

    def decide(self, match: MountMatch, *, armed: bool) -> HandoffDecision:
        """Bottom decision window. The `armed` argument is ignored (own state)."""
        if match.initiator is not Side.BOTTOM:
            raise RuntimeError("D3-B decides only at Bottom decision windows")
        exhausted = match.bottom.stamina.band is StaminaBand.EXHAUSTED
        self._exhausted = exhausted
        if not self.armed:
            kind = HandoffDecisionKind.UNARMED
            before = after = False
        elif not exhausted:
            kind = HandoffDecisionKind.ARMED_NORMAL
            before = after = False
        elif not self.token_consumed:
            self.token_consumed = True
            kind = HandoffDecisionKind.TOKEN
            before, after = False, True
        else:
            kind = HandoffDecisionKind.LOCKOUT_HOLD
            before = after = True
        return HandoffDecision(
            kind=kind,
            requested_commitment=None,
            transition=None,
            mode_before=before,
            mode_after=after,
        )


def handoff_controller_for(mode: PostClearHandoffMode, match: MountMatch):
    if mode is PostClearHandoffMode.V1E_PERSISTENT_CONSERVE_HOLD:
        return PostClearHandoffController()
    if mode is PostClearHandoffMode.D3B_EXHAUSTED_TOKEN_LOCKOUT:
        return D3BTokenLockoutController(match)
    return None


# ---------------------------------------------------------------------------
# Read-only event collector (diagnostics only)
# ---------------------------------------------------------------------------


def _snapshot(match: MountMatch) -> dict:
    return {
        "t": match.elapsed_simulated_time,
        "bs": match.bottom.stamina.current,
        "bx": match.bottom.stamina.band is StaminaBand.EXHAUSTED,
        "ts": match.top.stamina.current,
        "ax": round(match.axis, 10),
        "band": match.band.value,
    }


@dataclass(frozen=True, slots=True)
class PostClearHandoffMatchRecord:
    match_index: int
    initial_clock: int
    outcome: str
    events: tuple[dict, ...]


@dataclass(frozen=True, slots=True)
class PostClearHandoffMeasurement:
    mode: PostClearHandoffMode
    matches: tuple[PostClearHandoffMatchRecord, ...]


class PostClearHandoffCollector:
    """Ordered per-match event log for D2 scoring. Observer only.

    Every hook reads engine state through public queries (including the
    pure progress previews) and never mutates the match or draws RNG.
    """

    def __init__(self, *, mode: PostClearHandoffMode) -> None:
        self.mode = mode
        self._matches: list[PostClearHandoffMatchRecord] = []
        self._current: dict | None = None

    def _require(self) -> dict:
        if self._current is None:
            raise RuntimeError("post-clear handoff match is not active")
        return self._current

    def _events(self) -> list[dict]:
        return self._require()["events"]

    def start_match(self, match: MountMatch, *, match_index: int) -> None:
        if self._current is not None:
            raise RuntimeError("post-clear handoff match already active")
        self._current = {
            "match_index": match_index,
            "initial_clock": match.initial_clock,
            "events": [{"k": "start", **_snapshot(match)}],
        }

    def before_advance(
        self,
        match: MountMatch,
        *,
        bottom_behavior: BottomBehavior,
        rechoice_behavior: BottomBehavior,
        forced: bool,
        mode_active: bool,
    ) -> dict:
        before = _snapshot(match)
        context = {
            "before": before,
            "behavior": bottom_behavior.value,
            "policy_behavior": rechoice_behavior.value,
            "forced": forced,
            "mode": mode_active,
            "escape_axis": None,
            "escape_band": None,
        }
        if bottom_behavior is BottomBehavior.CONSERVE:
            # Counterfactual one-advance drift under baseline ESCAPE from the
            # same start (pure function of its arguments).
            drift = match.engine.simulate_drift(
                axis=match.position.control.value,
                band=match.band,
                clock_seconds=match.clock_seconds,
                duration_seconds=match.interval_seconds,
                top_behavior=match.top.behavior,
                bottom_behavior=BottomBehavior.ESCAPE,
            )
            context["escape_axis"] = round(drift.end_axis, 10)
            context["escape_band"] = drift.end_band.value
        return context

    def after_advance(self, match: MountMatch, *, context: dict, result) -> None:
        self._events().append(
            {
                "k": "adv",
                "behavior": context["behavior"],
                "policy_behavior": context["policy_behavior"],
                "forced": context["forced"],
                "mode": context["mode"],
                "b0": context["before"],
                "bnet": result.bottom_stamina.net_change,
                "escape_axis": context["escape_axis"],
                "escape_band": context["escape_band"],
                "band_changes": len(result.drift.band_changes),
                **_snapshot(match),
            }
        )

    def window(
        self,
        match: MountMatch,
        *,
        side: Side,
        free: bool,
        decision: HandoffDecision | None,
        armed: bool,
        policy_behavior: BottomBehavior,
        counterfactual_action: str | None = None,
    ) -> None:
        event = {
            "k": "win",
            "side": side.value,
            "free": free,
            "armed": armed,
            "seen_behavior": match.bottom.behavior.value,
            "policy_behavior": policy_behavior.value,
            "stall_b": match.advancement_clock(Side.BOTTOM),
            **_snapshot(match),
        }
        if side is Side.BOTTOM:
            event["kind"] = decision.kind.value if decision is not None else None
            event["req"] = (
                decision.requested_commitment.value
                if decision is not None and decision.requested_commitment is not None
                else None
            )
            event["tr"] = (
                decision.transition.value
                if decision is not None and decision.transition is not None
                else None
            )
            event["mode_before"] = decision.mode_before if decision is not None else False
            event["mode_after"] = decision.mode_after if decision is not None else False
            if decision is not None and decision.hold:
                legal = match.legal_action_ids(Side.BOTTOM)
                builders = [
                    action_id
                    for action_id in legal
                    if (target := match.setup_policy.target_for_builder(action_id))
                    is not None
                    and not match.setup_state.is_ready(target)
                ]
                event["builder_available"] = bool(builders)
                event["progress_route"] = bool(match.progress_capable_action_ids())
            if counterfactual_action is not None:
                # D3-B only: inert adopted counterfactual (deterministic policy).
                event["cf_action"] = counterfactual_action
        self._events().append(event)

    def after_hold(self, match: MountMatch, *, result: RecoveryHoldResult) -> None:
        self._events().append(
            {"k": "hold", "next": result.next_initiator.value, **_snapshot(match)}
        )

    def after_reset(
        self,
        match: MountMatch,
        *,
        side: Side,
        result: ResetWindowResult,
        stamina_before: int,
    ) -> None:
        self._events().append(
            {
                "k": "reset",
                "side": side.value,
                "route": result.progress_route_available,
                "offense": result.stalling_offense,
                "b_before": stamina_before,
                **_snapshot(match),
            }
        )

    def after_attempt(
        self,
        match: MountMatch,
        *,
        side: Side,
        action_id: str,
        requested: Commitment | None,
        result: AttemptResult,
        stamina_before: int,
        exhausted_before: bool,
        band_before: str,
    ) -> None:
        effective = result.attempt.effective_commitment
        response_charged = (
            result.response_stamina.charged
            if side is Side.TOP and result.response_stamina is not None
            else 0
        )
        self._events().append(
            {
                "k": "att",
                "side": side.value,
                "action": action_id,
                "req": requested.value if requested is not None else None,
                "eff": effective.value if effective is not None else None,
                "grade": result.resolution.final_grade.value,
                "resp_charged": response_charged,
                "b_before": stamina_before,
                "bx_before": exhausted_before,
                "band_before": band_before,
                "exit": (
                    match.exit_destination.value
                    if match.exit_destination is not None
                    else None
                ),
                **_snapshot(match),
            }
        )

    def finish_match(
        self,
        match: MountMatch,
        *,
        outcome: str,
        mode_active: bool,
    ) -> None:
        current = self._require()
        events = current["events"]
        if mode_active:
            events.append(
                {"k": "mode_end", "tr": ModeTransition.PENDING_AT_END.value, **_snapshot(match)}
            )
        events.append({"k": "end", "outcome": outcome, **_snapshot(match)})
        self._matches.append(
            PostClearHandoffMatchRecord(
                match_index=current["match_index"],
                initial_clock=current["initial_clock"],
                outcome=outcome,
                events=tuple(events),
            )
        )
        self._current = None

    def measurement(self) -> PostClearHandoffMeasurement:
        if self._current is not None:
            raise RuntimeError("cannot finalize with an active match")
        return PostClearHandoffMeasurement(
            mode=self.mode,
            matches=tuple(self._matches),
        )
