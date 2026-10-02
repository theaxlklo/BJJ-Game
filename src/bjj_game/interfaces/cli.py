from __future__ import annotations

import argparse
import getpass
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO

from ..domain.action import Commitment
from ..positions.mount.catalog import ENTITY_BY_ID, actions_for, responses_for
from ..diagnostics.checker import render_enumeration, render_exhausted_reachability_summary, render_reset_lock_probe, run_checks
from ..engine.match import MountRun
from ..engine.stamina import conserve_cycle_net, project_active_stamina_pacing
from .blind import BlindResponseChoice, RandomBlindResponder, render_random_mix_band_metrics
from .formatting import format_advance_result, format_attempt_result, format_clock, format_drift, format_reset_window, format_resolution
from ..positions.mount.rules import DEFAULT_AXIS, DEFAULT_CLOCK_SECONDS, DEFAULT_INTERVAL_SECONDS
from ..domain.model import BottomBehavior, EntityKind, Side, TopBehavior
from ..positions.mount.names import RESOLVER


def parse_clock(value: str) -> int:
    value = value.strip()
    if ":" in value:
        parts = value.split(":")
        if len(parts) != 2:
            raise argparse.ArgumentTypeError("clock must be M:SS or positive seconds")
        try:
            minutes, seconds = map(int, parts)
        except ValueError as exc:
            raise argparse.ArgumentTypeError("clock must be M:SS or positive seconds") from exc
        if minutes < 0 or not 0 <= seconds < 60:
            raise argparse.ArgumentTypeError("clock must be M:SS with seconds 00..59")
        total = minutes * 60 + seconds
    else:
        try:
            total = int(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError("clock must be M:SS or positive seconds") from exc
    if total <= 0:
        raise argparse.ArgumentTypeError("clock must be > 0")
    return total


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    return parsed


def stamina_value(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("stamina must be an integer") from exc
    if not 0 <= parsed <= 100:
        raise argparse.ArgumentTypeError("stamina must be between 0 and 100")
    return parsed


def commitment_value(value: str) -> Commitment:
    try:
        return Commitment(value.strip().upper())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("commitment must be LOW, MEDIUM, or HIGH") from exc


def top_behavior_value(value: str) -> TopBehavior:
    try:
        return TopBehavior(value.strip().upper())
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "top behavior must be PRESSURE, HOLD, or CONSERVE"
        ) from exc


def bottom_behavior_value(value: str) -> BottomBehavior:
    try:
        return BottomBehavior(value.strip().upper())
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "bottom behavior must be ESCAPE, PROTECT, or CONSERVE"
        ) from exc


def axis_value(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("axis must be numeric") from exc
    if not 0.10 <= parsed <= 4.00:
        raise argparse.ArgumentTypeError("axis must be between 0.10 and 4.00")
    return parsed


def _choose_entity(prompt: str, side: Side, kind: EntityKind):
    entities = actions_for(side) if kind is EntityKind.ACTION else responses_for(side)
    while True:
        print(f"\n{prompt}")
        for i, entity in enumerate(entities, 1):
            print(f"  {i}. {entity.canonical_name}")
        value = _read_input("> ").strip()
        if not value:
            continue
        if value.isdigit() and 1 <= int(value) <= len(entities):
            return entities[int(value) - 1]
        try:
            return RESOLVER.resolve(value, kind=kind, side=side)
        except ValueError as exc:
            print(exc)




def _read_hidden_input(prompt: str = "") -> str:
    """Read a hot-seat secret without echoing it to the next player."""
    value = getpass.getpass(prompt)
    if isinstance(sys.stdout, _TeeStdout):
        sys.stdout.write_log_only("<hidden input>\n")
    return value



def _random_blind_response(
    responder: Side,
    policy: RandomBlindResponder,
) -> BlindResponseChoice:
    choice = policy.choose(responder)
    print(f"\n{responder.value.upper()} RESPONSE — RANDOM BLIND LOCK")
    print("Response locked by seeded random policy.")
    return choice


def _choose_blind_response(side: Side):
    entities = responses_for(side)
    while True:
        print(f"\n{side.value.upper()} RESPONSE — BLIND LOCK")
        for i, entity in enumerate(entities, 1):
            print(f"  {i}. {entity.canonical_name}")
        value = _read_hidden_input("> ").strip()
        if not value:
            continue
        if value.isdigit() and 1 <= int(value) <= len(entities):
            print("Response locked.")
            return entities[int(value) - 1]
        try:
            entity = RESOLVER.resolve(value, kind=EntityKind.RESPONSE, side=side)
        except ValueError:
            print("Unknown response")
            continue
        print("Response locked.")
        return entity


def _choose_modern_initiation(side: Side):
    entities = actions_for(side)
    while True:
        print(f"\n{side.value.upper()} INITIATES")
        for i, entity in enumerate(entities, 1):
            print(f"  {i}. {entity.canonical_name}")
        print(f"  {len(entities) + 1}. RESET / NO ACTION — yield this decision window")
        value = _read_input("> ").strip()
        if not value:
            continue
        if value.isdigit():
            index = int(value)
            if 1 <= index <= len(entities):
                return entities[index - 1]
            if index == len(entities) + 1:
                return None
        if value.upper() in {
            "RESET",
            "NO ACTION",
            "NO-ACTION",
            "REST",
            "YIELD",
            "HAND FIGHT",
            "HAND-FIGHT",
        }:
            return None
        try:
            return RESOLVER.resolve(value, kind=EntityKind.ACTION, side=side)
        except ValueError as exc:
            print(exc)


def _choose_behavior(side: Side, current=None, *, conserve_enabled: bool = True):
    enum_cls = TopBehavior if side is Side.TOP else BottomBehavior
    choices = [
        behavior
        for behavior in enum_cls
        if conserve_enabled or behavior.value != "CONSERVE"
    ]
    while True:
        label = f"{side.value.title()} behavior"
        if current is not None:
            label += f" [Enter keeps {current.value}]"
        print(f"\n{label}")
        for i, behavior in enumerate(choices, 1):
            print(f"  {i}. {behavior.value} — {behavior.display}")
        value = _read_input("> ").strip()
        if not value and current is not None:
            return current
        if value.isdigit() and 1 <= int(value) <= len(choices):
            return choices[int(value) - 1]
        upper = value.upper()
        for behavior in choices:
            if upper in {behavior.value, behavior.display.upper()}:
                return behavior
        print("Unknown behavior")


def _run_interactive(args: argparse.Namespace, *, commitment_enabled: bool = True) -> int:
    run = MountRun(initial_clock=args.clock, starting_axis=args.axis, interval_seconds=args.interval)
    run.top.stamina.set_current(args.top_stamina)
    run.bottom.stamina.set_current(args.bottom_stamina)
    print("MOUNT v0.1e — HOT-SEAT PROTOTYPE" if commitment_enabled else "MOUNT v0 — HOT-SEAT PROTOTYPE")
    print(f"Clock: {format_clock(run.initial_clock)}")
    print(f"Starting axis: {run.axis:+.2f}")
    print(f"Initial visible band: {run.band.value}")
    print(f"Decision interval: {run.interval_seconds} simulated seconds")
    print("First initiator: Top")
    print(f"Top stamina: {run.top.stamina.display}")
    print(f"Bottom stamina: {run.bottom.stamina.display}")
    random_blind = (
        RandomBlindResponder(args.seed)
        if commitment_enabled and args.blind and args.blind_responder == "random"
        else None
    )

    if commitment_enabled:
        print("Action stamina costs: ON (LOW=3, MEDIUM=7, HIGH=12)")
        print(f"Standard commitment: {args.commitment.value}")
        print("Commitment resolution effects: OFF (LOW remains dominant; standard play defaults MEDIUM)")
        print("Exhaustion consequence: Exhausted initiator -1 grade")
        print("Behavior stamina: PRESSURE/ESCAPE -1 per 5s; HOLD/PROTECT 0; CONSERVE +2 per 5s")
        if args.blind:
            if random_blind is None:
                print("Blind hot-seat testing: human responder locks hidden response before action/RESET is chosen")
            else:
                print("Blind hot-seat testing: seeded random responder locks response before action/RESET is chosen")
                print(f"Random blind responder seed: {random_blind.seed}")
                print(
                    "Random blind Bottom response mix: "
                    + RandomBlindResponder.mix_description(Side.BOTTOM)
                )
                print(
                    "Random blind Top response mix: "
                    + RandomBlindResponder.mix_description(Side.TOP)
                )
    else:
        print("Stamina effects: OFF (legacy Mount v0 path)")

    try:
        top_behavior = (
            args.top_behavior
            if commitment_enabled and args.top_behavior is not None
            else _choose_behavior(Side.TOP, conserve_enabled=commitment_enabled)
        )
        bottom_behavior = (
            args.bottom_behavior
            if commitment_enabled and args.bottom_behavior is not None
            else _choose_behavior(Side.BOTTOM, conserve_enabled=commitment_enabled)
        )
        if commitment_enabled and args.top_behavior is not None:
            print(f"Top behavior fixed for session: {top_behavior.value}")
        if commitment_enabled and args.bottom_behavior is not None:
            print(f"Bottom behavior fixed for session: {bottom_behavior.value}")
        run.set_behaviors(top=top_behavior, bottom=bottom_behavior)

        while not run.ended:
            if commitment_enabled:
                advance = run.advance()
                print(
                    "\n"
                    + format_advance_result(
                        advance,
                        top_behavior.value,
                        bottom_behavior.value,
                    )
                )
            else:
                drift = run.drift()
                print("\n" + format_drift(drift, top_behavior.value, bottom_behavior.value))
            if run.ended:
                break

            initiator = run.initiator
            if commitment_enabled:
                responder = initiator.opponent
                blind_choice = (
                    _random_blind_response(responder, random_blind)
                    if random_blind is not None
                    else None
                )
                blind_response = (
                    blind_choice.response
                    if blind_choice is not None
                    else _choose_blind_response(responder)
                    if args.blind
                    else None
                )
                action = _choose_modern_initiation(initiator)
                if action is None:
                    reset_result = run.reset_window()
                    print("\n" + format_reset_window(reset_result))
                    if blind_choice is not None:
                        print(
                            "RANDOM BLIND RESPONSE "
                            f"#{blind_choice.ordinal} UNUSED (RESET): "
                            f"{blind_choice.response.canonical_name} "
                            f"[draw {blind_choice.draw}/{blind_choice.total_weight - 1}]"
                        )
                else:
                    response = (
                        blind_response
                        if blind_response is not None
                        else _choose_entity(
                            f"{responder.value.upper()} RESPONSE",
                            responder,
                            EntityKind.RESPONSE,
                        )
                    )
                    attempt_result = run.attempt(
                        action_id=action.id,
                        response_id=response.id,
                        commitment=args.commitment,
                    )
                    print(
                        "\n"
                        + format_attempt_result(
                            attempt_result,
                            run.clock_seconds,
                            top_behavior.value,
                            bottom_behavior.value,
                        )
                    )
                    if blind_choice is not None:
                        print(
                            "RANDOM BLIND RESPONSE "
                            f"#{blind_choice.ordinal}: "
                            f"{blind_choice.response.canonical_name} "
                            f"[draw {blind_choice.draw}/{blind_choice.total_weight - 1}]"
                        )
            else:
                action = _choose_entity(
                    f"{initiator.value.upper()} INITIATES",
                    initiator,
                    EntityKind.ACTION,
                )
                responder = initiator.opponent
                response = _choose_entity(
                    f"{responder.value.upper()} RESPONSE",
                    responder,
                    EntityKind.RESPONSE,
                )
                result = run.decide(
                    action_id=action.id,
                    response_id=response.id,
                )
                print(
                    "\n"
                    + format_resolution(
                        result,
                        run.clock_seconds,
                        top_behavior.value,
                        bottom_behavior.value,
                    )
                )
            if run.ended:
                break

            if not (commitment_enabled and args.top_behavior is not None):
                top_behavior = _choose_behavior(
                    Side.TOP,
                    current=top_behavior,
                    conserve_enabled=commitment_enabled,
                )
            if not (commitment_enabled and args.bottom_behavior is not None):
                bottom_behavior = _choose_behavior(
                    Side.BOTTOM,
                    current=bottom_behavior,
                    conserve_enabled=commitment_enabled,
                )
            run.set_behaviors(top=top_behavior, bottom=bottom_behavior)
    except (EOFError, KeyboardInterrupt):
        run.exit_reason = "CANCELLED"
        print("\nRun cancelled.")
        _print_summary(run, status="CANCELLED")
        return 130

    _print_summary(run)
    return 0


def _print_summary(run: MountRun, *, status: str | None = None) -> None:
    h = run.history
    print("\nRUN SUMMARY")
    print("=" * 11)
    if status is not None:
        print(f"Run status: {status}")
    print(f"Initial clock: {format_clock(run.initial_clock)}")
    print(f"Elapsed simulated time: {format_clock(run.elapsed_simulated_time)}")
    print(f"Mount duration: {format_clock(run.mount_duration)}")
    print(f"Starting axis: {run.starting_axis:+.2f}")
    print(f"Final axis: {run.axis:+.2f}")
    print(f"Top stamina: {run.top.stamina.display}")
    print(f"Bottom stamina: {run.bottom.stamina.display}")
    if run.exit_destination is None:
        print(f"Final visible band: {run.band.value}")
    else:
        print(f"Final visible band: Mount broken (last visible: {run.band.value})")
    print(f"Top behavior history: {h.top_behavior_history}")
    print(f"Bottom behavior history: {h.bottom_behavior_history}")
    if h.top_behavior_stamina_history or h.bottom_behavior_stamina_history:
        print(f"Top behavior-stamina history: {h.top_behavior_stamina_history}")
        print(f"Bottom behavior-stamina history: {h.bottom_behavior_stamina_history}")
    print(f"Top initiation count: {h.top_initiation_count}")
    print(f"Bottom initiation count: {h.bottom_initiation_count}")
    if h.reset_window_history:
        print(f"Reset / no-action history: {h.reset_window_history}")
    action_history = [ENTITY_BY_ID[action_id].short_name for action_id in h.initiated_action_history]
    response_history = [ENTITY_BY_ID[response_id].short_name for response_id in h.response_history]
    print(f"Initiated-action history: {action_history}")
    print(f"Response history: {response_history}")
    print(f"Raw-grade history: {h.raw_grade_history}")
    print(f"Modified-grade history: {h.modified_grade_history}")
    if h.commitment_history:
        print(f"Commitment initiator history: {h.commitment_initiator_history}")
        print(f"Requested commitment history: {h.commitment_history}")
        print(f"Effective commitment history: {h.effective_commitment_history}")
        print(f"Stamina requested history: {h.stamina_requested_history}")
        print(f"Stamina charged history: {h.stamina_charged_history}")
        print(f"Stamina shortfall history: {h.stamina_shortfall_history}")
        print(f"Stamina funding gap history: {h.stamina_funding_gap_history}")
        print(f"Stamina band at initiation history: {h.stamina_band_at_initiation_history}")
        print(f"Exhaustion modifier history: {h.exhaustion_modifier_history}")
    print(f"Clamp count: {h.clamp_count}")
    print(f"Escape threshold reached?: {'Yes' if h.escape_threshold_reached else 'No'}")
    print(f"Exit reason: {run.exit_reason or 'None'}")
    print(f"Exit destination: {run.exit_destination.value if run.exit_destination else 'None'}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mount v0 deterministic BJJ prototype")
    parser.add_argument("--axis", type=axis_value, default=DEFAULT_AXIS, help="starting Mount axis, 0.10..4.00")
    parser.add_argument("--clock", type=parse_clock, default=DEFAULT_CLOCK_SECONDS, help="M:SS or positive seconds")
    parser.add_argument("--interval", type=positive_int, default=DEFAULT_INTERVAL_SECONDS, help="decision interval in simulated seconds")
    parser.add_argument("--top-stamina", type=stamina_value, default=100, help="starting Top stamina telemetry, 0..100")
    parser.add_argument("--bottom-stamina", type=stamina_value, default=100, help="starting Bottom stamina telemetry, 0..100")
    parser.add_argument("--commitment", type=commitment_value, default=Commitment.MEDIUM, help="fixed v0.1c action commitment; defaults to MEDIUM")
    parser.add_argument("--blind", action="store_true", help="testing mode: responder locks a hidden response before the action/RESET choice")
    parser.add_argument("--blind-responder", choices=("human", "random"), default="human", help="blind responder source; random requires --blind and --seed")
    parser.add_argument("--seed", type=int, help="deterministic seed for --blind-responder random")
    parser.add_argument("--top-behavior", type=top_behavior_value, help="fix Top behavior for the entire modern playtest session")
    parser.add_argument("--bottom-behavior", type=bottom_behavior_value, help="fix Bottom behavior for the entire modern playtest session")
    parser.add_argument("--enumerate", action="store_true", help="print exhaustive matrix/checker report and exit")
    parser.add_argument("--check", action="store_true", help="run semantic invariant checks without the interactive simulation")
    parser.add_argument("--log", type=Path, help="save all printed output to a text log while still showing it in the terminal")
    return parser


def _read_input(prompt: str = "") -> str:
    """Read a hot-seat choice and mirror the typed text into --log when active.

    A real terminal already echoes the user's keystrokes, so the text is written only
    to the log side of the tee to avoid duplicating it on screen.
    """
    if prompt:
        print(prompt, end="", flush=True)
    value = input()
    if isinstance(sys.stdout, _TeeStdout):
        sys.stdout.write_log_only(value + "\n")
    return value


class _TeeStdout:
    def __init__(self, terminal: TextIO, logfile: TextIO) -> None:
        self.terminal = terminal
        self.logfile = logfile

    @property
    def encoding(self):
        return getattr(self.terminal, "encoding", None)

    @property
    def errors(self):
        return getattr(self.terminal, "errors", None)

    def fileno(self) -> int:
        return self.terminal.fileno()

    def write_log_only(self, text: str) -> int:
        self.logfile.write(text)
        self.logfile.flush()
        return len(text)

    def write(self, text: str) -> int:
        self.terminal.write(text)
        self.logfile.write(text)
        return len(text)

    def flush(self) -> None:
        self.terminal.flush()
        self.logfile.flush()

    def isatty(self) -> bool:
        return self.terminal.isatty()


@contextmanager
def _tee_to_log(path: Path):
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    previous = sys.stdout
    with path.open("w", encoding="utf-8", buffering=1) as logfile:
        sys.stdout = _TeeStdout(previous, logfile)
        try:
            print(f"LOG FILE: {path}")
            yield
        finally:
            sys.stdout.flush()
            sys.stdout = previous


def _dispatch(args: argparse.Namespace, *, commitment_enabled: bool = True) -> int:
    if not commitment_enabled and (
        args.blind
        or args.blind_responder != "human"
        or args.seed is not None
        or args.top_behavior is not None
        or args.bottom_behavior is not None
    ):
        print(
            "ERROR: modern playtest flags (--blind/--blind-responder/--seed/"
            "--top-behavior/--bottom-behavior) are available only on bjj_game."
        )
        return 2
    if args.blind_responder == "random" and not args.blind:
        print("ERROR: --blind-responder random requires --blind.")
        return 2
    if args.blind_responder == "random" and args.seed is None:
        print("ERROR: --blind-responder random requires --seed N for replayability.")
        return 2
    if args.seed is not None and args.blind_responder != "random":
        print("ERROR: --seed is only valid with --blind-responder random.")
        return 2
    if args.enumerate:
        print(render_enumeration())
        return 0 if run_checks().ok else 1
    if args.check:
        if commitment_enabled:
            print("INFO: COMMITMENT DOMINANCE: LOW strictly dominates MEDIUM/HIGH while commitment effects are OFF; standard play defaults to MEDIUM.")
            print("INFO: COMMITMENT VISIBILITY: public in v0.1e; hidden/recognized commitment is deferred to the v0.2 information layer.")
            for commitment in Commitment:
                projection = project_active_stamina_pacing(commitment=commitment)
                print(
                    "INFO: STAMINA PACING "
                    f"{commitment.value}: active PRESSURE/ESCAPE, forced attack each initiative, start 100, "
                    f"Exhausted Top {format_clock(projection.top_exhausted_seconds)}, "
                    f"Bottom {format_clock(projection.bottom_exhausted_seconds)}; "
                    f"zero Top {format_clock(projection.top_zero_seconds)}, "
                    f"Bottom {format_clock(projection.bottom_zero_seconds)}."
                )
            cycle_parts = []
            for commitment in Commitment:
                cycle = conserve_cycle_net(commitment)
                cycle_parts.append(
                    f"{commitment.value} {cycle.attack_net:+d}"
                )
            reset_cycle = conserve_cycle_net(Commitment.MEDIUM).reset_net
            print(
                "INFO: CONSERVE CYCLE NET (10s): "
                + ", ".join(cycle_parts)
                + f"; RESET {reset_cycle:+d}. "
                "Negative attack net means forced attacks cannot recover exhaustion while fully funded."
            )
            print("INFO: EXHAUSTION HYSTERESIS: enter Exhausted at <=25; recover only at >=35.")
            for line in render_exhausted_reachability_summary():
                print(f"INFO: {line}")
            print(
                "INFO: V0.2 RESPONSE-STAMINA DEBT: exhausted responders still defend at full strength "
                "and responses have no direct cost; revisit with triggered initiative."
            )
            print(
                "INFO: RESET/STALLING DEBT: RESET solves forced-action recovery but repeated no-action "
                "windows need the future progress-based stalling system."
            )
            print("INFO: " + render_reset_lock_probe())
            print(
                "INFO: BLIND PLAYTEST MODE: use --blind to lock the responder before the action is shown; "
                "testing only, no resolution rules change."
            )
            print(
                "INFO: RANDOM BLIND RESPONDER MIX: Bottom "
                + RandomBlindResponder.mix_description(Side.BOTTOM)
                + "; Top "
                + RandomBlindResponder.mix_description(Side.TOP)
                + ". Use --blind --blind-responder random --seed N for solo replayable sessions."
            )
            for line in render_random_mix_band_metrics():
                print(f"INFO: {line}")
        report = run_checks()
        for message in report.info:
            print(f"INFO: {message}")
        for warning in report.warnings:
            print(f"WARN: {warning}")
        for error in report.errors:
            print(f"ERROR: {error}")
        print(f"STATUS: {'PASS' if report.ok else 'FAIL'}")
        return 0 if report.ok else 1
    return _run_interactive(args, commitment_enabled=commitment_enabled)


def main(
    argv: list[str] | None = None,
    *,
    commitment_enabled: bool = True,
) -> int:
    args = build_parser().parse_args(argv)
    if args.log is not None:
        with _tee_to_log(args.log):
            return _dispatch(args, commitment_enabled=commitment_enabled)
    return _dispatch(args, commitment_enabled=commitment_enabled)


if __name__ == "__main__":
    sys.exit(main())
