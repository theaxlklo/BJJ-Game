"""Fail-closed validation of the frozen Mount-slice test log.

`test_mount_slice.gd` runs every test group from `_initialize()`. A production
`assert` (or other script error) aborts only the running function: Godot then
continues with the next group, prints `Mount slice PASS` with fewer assertions
and exits 0. The process exit status alone is therefore not evidence. This
validator requires, together: exit status 0, no Godot/test diagnostics, exactly
one well-formed PASS line and an exact assertion count.

The expected count is pinned in `.github/workflows/godot-v1.yml` next to the
step. Change it only in the same reviewed change that adds or removes
`test_mount_slice.gd` assertions. Standard library only; no gameplay imports.
"""
import argparse
import re
import sys
from pathlib import Path

ANSI = re.compile(r'\x1b\[[0-9;?]*[A-Za-z]')
# Any line that mentions the completion marker, so malformed variants are
# reported instead of silently ignored.
COMPLETION_HINT = re.compile(r'mount\s+slice.*pass|pass.*mount\s+slice', re.IGNORECASE)
COMPLETION = re.compile(r'Mount slice PASS: ([1-9][0-9]*) assertions')
# Godot engine diagnostics (ERROR/WARNING with optional SCRIPT/USER/SHADER/EDITOR
# prefix), script aborts and the test's own failure output.
# A callee `assert` can fail without aborting its caller: the count and exit
# status then stay perfect, so this scan is the only detector. It is therefore
# not line-anchored (stdout/stderr may interleave mid-line when both go to one file).
DIAGNOSTIC = re.compile(
    r'^\s*(?:(?:SCRIPT|USER|SHADER|EDITOR)\s+)?(?:ERROR|WARNING)\b'
    r'|(?:ERROR|WARNING):'
    r'|^\s*FAIL\b'
    r'|assertions failed'
    r'|Assertion failed'
    r'|Parse Error'
    r'|GDScript backtrace'
    r'|^\s*Traceback\b'
    r'|crashed',
)
MAX_LISTED = 5


def validate(text, exit_code, expected_assertions):
    """Return a list of human-readable problems; empty means the log is valid."""
    problems = []
    if exit_code != 0:
        problems.append('Godot exited with status %s, expected 0' % exit_code)
    lines = [ANSI.sub('', line).rstrip() for line in text.splitlines()]

    diagnostics = [line for line in lines if DIAGNOSTIC.search(line)]
    for line in diagnostics[:MAX_LISTED]:
        problems.append('unexpected diagnostic: ' + line.strip())
    if len(diagnostics) > MAX_LISTED:
        problems.append('... and %d more unexpected diagnostic lines' % (len(diagnostics) - MAX_LISTED))

    completions = [line for line in lines if COMPLETION_HINT.search(line) and not DIAGNOSTIC.search(line)]
    if not completions:
        problems.append('completion line "Mount slice PASS: <N> assertions" is missing (truncated or aborted output)')
    elif len(completions) > 1:
        problems.append('completion line appears %d times, expected exactly once' % len(completions))
    else:
        match = COMPLETION.fullmatch(completions[0])
        if match is None:
            problems.append('malformed completion line: ' + repr(completions[0]))
        elif int(match.group(1)) != expected_assertions:
            problems.append('assertion count %s != required %d (incomplete run, or the pin needs a reviewed update)'
                            % (match.group(1), expected_assertions))
    return problems


def positive_int(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError('must be positive')
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('log', type=Path, help='captured stdout+stderr of the Godot test run')
    parser.add_argument('--exit-code', type=int, required=True, help='Godot process exit status')
    parser.add_argument('--expected-assertions', type=positive_int, required=True)
    args = parser.parse_args(argv)
    try:
        text = args.log.read_text(encoding='utf-8', errors='replace')
    except OSError as exc:
        print('Mount slice log INVALID: cannot read %s: %s' % (args.log, exc), file=sys.stderr)
        return 1
    problems = validate(text, args.exit_code, args.expected_assertions)
    if problems:
        print('Mount slice log INVALID:', file=sys.stderr)
        for problem in problems:
            print('  - ' + problem, file=sys.stderr)
        return 1
    print('Mount slice log OK: exit 0, no diagnostics, exactly %d assertions' % args.expected_assertions)
    return 0


if __name__ == '__main__':
    sys.exit(main())
