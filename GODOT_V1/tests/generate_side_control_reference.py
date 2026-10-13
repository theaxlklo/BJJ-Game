#!/usr/bin/env python3
"""Deterministic Side Control v0 reference-fixture generator (B2c Python-to-Godot parity gate).

Every expectation comes from the independent test-only oracle (``tests/oracles/side_control_v0.py``), which was written from
``GODOT_V1/docs/SIDE_CONTROL_V0_RULES.md`` (B2b-2). No GDScript is executed or read here. The Godot suite
``test_side_control_reference.gd`` replays these rows through the typed engine.

Usage:  python GODOT_V1/tests/generate_side_control_reference.py [output.jsonl]
Default output: GODOT_V1/tests/generated/side_control_reference.jsonl (git-ignored). The script fails (non-zero exit) on an empty
fixture and prints the oracle's measured scenario / operation / comparison counts and the SHA-256 of the oracle's own canonical
fixture; it asserts none of them (the oracle test pins them). The written file differs from that canonical fixture only by the
``$float`` input markers below, so it prints its own digest as well.
"""
import hashlib
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "tests"))

from oracles import side_control_v0_scenarios as scenarios  # noqa: E402

# JSON (and Godot's parser) cannot tell the int 10 from the float 10.0. Inputs that the oracle must treat as a *float* (and therefore
# refuse) are written as {"$float": value}; every other JSON number in an input is an integer. Expected outputs are plain numbers.
INPUT_KEYS = ("entry", "state", "operation", "operations")


def _mark_floats(value):
    if isinstance(value, float):
        return {"$float": value}
    if isinstance(value, dict):
        return {key: _mark_floats(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_mark_floats(item) for item in value]
    return value


def write(path, rows=None):
    rows = scenarios.all_rows() if rows is None else rows
    if not rows:
        raise SystemExit("side control fixture generation produced no scenarios")
    digest = hashlib.sha256()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="ascii", newline="\n") as handle:
        for row in rows:
            encoded = {key: (_mark_floats(item) if key in INPUT_KEYS else item) for key, item in row.items()}
            line = json.dumps(encoded, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            handle.write(line + "\n")
            digest.update(line.encode("ascii") + b"\n")
    summary = scenarios.summarize(rows)
    summary["file_sha256"] = digest.hexdigest()
    return summary


def main(argv):
    default = os.path.join(REPO, "GODOT_V1", "tests", "generated", "side_control_reference.jsonl")
    summary = write(argv[1] if len(argv) > 1 else default)
    print("side_control_reference: scenarios=%(scenarios)d operations=%(operations)d comparisons=%(comparisons)d oracle_sha256=%(sha256)s file_sha256=%(file_sha256)s" % summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
