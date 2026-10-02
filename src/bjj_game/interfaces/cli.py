from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO

from ..domain.action import Commitment
from ..positions.mount.catalog import ENTITY_BY_ID, actions_for, responses_for
from ..diagnostics.checker import render_enumeration, run_checks
from ..engine.match import MountRun
from .formatting import format_attempt_result, format_clock, format_drift, format_resolution
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


def _choose_behavior(side: Side, current=None):
    enum_cls = TopBehavior if side is Side.TOP else BottomBehavior
    choices = list(enum_cls)
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


def _choose_commitment() -> Commitment:
    choices = list(Commitment)
    while True:
        print("\nCommitment")
        for i, commitment in enumerate(choices, 1):
            print(f"  {i}. {commitment.value}")
        value = _read_input("> ").strip()
        if value.isdigit() and 1 <= int(value) <= len(choices):
            return choices[int(value) - 1]
        upper = value.upper()
        for commitment in choices:
            if upper == commitment.value:
                return commitment
        print("Unknown commitment")


def _run_interactive(args: argparse.Namespace, *, commitment_enabled: bool = True) -> int:
    run = MountRun(initial_clock=args.clock, starting_axis=args.axis, interval_seconds=args.interval)
    run.top.stamina.set_current(args.top_stamina)
    run.bottom.stamina.set_current(args.bottom_stamina)
    print("MOUNT v0.1b — HOT-SEAT PROTOTYPE" if commitment_enabled else "MOUNT v0 — HOT-SEAT PROTOTYPE")
    print(f"Clock: {format_clock(run.initial_clock)}")
    print(f"Starting axis: {run.axis:+.2f}")
    print(f"Initial visible band: {run.band.value}")
    print(f"Decision interval: {run.interval_seconds} simulated seconds")
    print("First initiator: Top")
    print(f"Top stamina: {run.top.stamina.display}")
    print(f"Bottom stamina: {run.bottom.stamina.display}")
    if commitment_enabled:
        print("Stamina costs: ON (LOW=3, MEDIUM=7, HIGH=12)")
        print("Commitment resolution effects: OFF (v0.1b cost-only slice)")
    else:
        print("Stamina effects: OFF (legacy Mount v0 path)")

    try:
        top_behavior = _choose_behavior(Side.TOP)
        bottom_behavior = _choose_behavior(Side.BOTTOM)
        run.set_behaviors(top=top_behavior, bottom=bottom_behavior)

        while not run.ended:
            drift = run.drift()
            print("\n" + format_drift(drift, top_behavior.value, bottom_behavior.value))
            if run.ended:
                break

            initiator = run.initiator
            action = _choose_entity(f"{initiator.value.upper()} INITIATES", initiator, EntityKind.ACTION)
            commitment = _choose_commitment() if commitment_enabled else None
            responder = initiator.opponent
            response = _choose_entity(f"{responder.value.upper()} RESPONSE", responder, EntityKind.RESPONSE)
            if commitment_enabled:
                attempt_result = run.attempt(
                    action_id=action.id,
                    response_id=response.id,
                    commitment=commitment,
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
            else:
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

            top_behavior = _choose_behavior(Side.TOP, current=top_behavior)
            bottom_behavior = _choose_behavior(Side.BOTTOM, current=bottom_behavior)
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
    print(f"Top initiation count: {h.top_initiation_count}")
    print(f"Bottom initiation count: {h.bottom_initiation_count}")
    action_history = [ENTITY_BY_ID[action_id].short_name for action_id in h.initiated_action_history]
    response_history = [ENTITY_BY_ID[response_id].short_name for response_id in h.response_history]
    print(f"Initiated-action history: {action_history}")
    print(f"Response history: {response_history}")
    print(f"Raw-grade history: {h.raw_grade_history}")
    print(f"Modified-grade history: {h.modified_grade_history}")
    if h.commitment_history:
        print(f"Commitment initiator history: {h.commitment_initiator_history}")
        print(f"Commitment history: {h.commitment_history}")
        print(f"Stamina requested history: {h.stamina_requested_history}")
        print(f"Stamina charged history: {h.stamina_charged_history}")
        print(f"Stamina shortfall history: {h.stamina_shortfall_history}")
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
    if args.enumerate:
        print(render_enumeration())
        return 0 if run_checks().ok else 1
    if args.check:
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
