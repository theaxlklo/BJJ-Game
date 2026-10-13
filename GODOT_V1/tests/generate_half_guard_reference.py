#!/usr/bin/env python3
"""Deterministic Half Guard v0 reference-fixture generator (B1b oracle checkpoint).

Every expectation comes from the independent test-only oracle (``tests/oracles/half_guard_v0.py``), which is written
from ``GODOT_V1/docs/HALF_GUARD_V0_RULES.md``. No GDScript and no Mount engine is executed or read. The later Godot
parity suite will replay these rows; until then nothing consumes the file, so it is *not wired into CI* yet.

Usage:  python GODOT_V1/tests/generate_half_guard_reference.py [output.jsonl]
Default output: GODOT_V1/tests/generated/half_guard_reference.jsonl (git-ignored). The script fails (non-zero exit) on an
empty fixture and prints the measured scenario / operation / comparison counts; it asserts none of them.
"""
import hashlib
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "tests"))

from oracles import half_guard_v0_scenarios as scenarios  # noqa: E402


def _leaves(value):
    if isinstance(value, dict):
        return sum(_leaves(v) for v in value.values())
    if isinstance(value, list):
        return sum(_leaves(v) for v in value)
    return 1


# JSON (and Godot's parser) cannot tell the int 300 from the float 300.0. Inputs that the oracle must treat as a *float* (and
# therefore refuse) are written as {"$float": value}; every other JSON number in an input is an integer. Expected outputs are
# plain numbers and are compared numerically by the Godot suite.
INPUT_KEYS = ("request", "entry", "commands", "command")


def _mark_floats(value):
    if isinstance(value, float):
        return {"$float": value}
    if isinstance(value, dict):
        return {key: _mark_floats(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_mark_floats(item) for item in value]
    return value


def _encode(row):
    return {key: (_mark_floats(item) if key in INPUT_KEYS else item) for key, item in row.items()}


def _operations(row):
    if row["family"] == "trajectory":
        return len(row["commands"])
    return 1 if row["family"] in ("entry", "exchange_grid", "break_grid") else 0


def write(path, rows=None):
    rows = scenarios.all_rows() if rows is None else rows
    if not rows:
        raise SystemExit("half guard fixture generation produced no scenarios")
    digest = hashlib.sha256()
    comparisons = operations = 0
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="ascii", newline="\n") as handle:
        for row in rows:
            line = json.dumps(_encode(row), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            handle.write(line + "\n")
            digest.update(line.encode("ascii") + b"\n")
            comparisons += _leaves(row.get("expected", row.get("expected_snapshot", row.get("expected_error"))))
            operations += _operations(row)
    return {"scenarios": len(rows), "operations": operations, "comparisons": comparisons, "sha256": digest.hexdigest()}


def main(argv):
    default = os.path.join(REPO, "GODOT_V1", "tests", "generated", "half_guard_reference.jsonl")
    summary = write(argv[1] if len(argv) > 1 else default)
    print("half_guard_reference: scenarios=%(scenarios)d operations=%(operations)d comparisons=%(comparisons)d sha256=%(sha256)s" % summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
