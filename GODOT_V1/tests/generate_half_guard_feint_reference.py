#!/usr/bin/env python3
"""Deterministic Half Guard feint reference-fixture generator (B1h oracle checkpoint).

Every expectation comes from the independent test-only oracle (``tests/oracles/half_guard_v0.py``, written from
``GODOT_V1/docs/HALF_GUARD_V0_RULES.md`` section 13). No GDScript and no Mount engine is executed or read. The direct-technique
fixture (``generate_half_guard_reference.py``) is a separate file and is not touched by this generator.

Usage:  python GODOT_V1/tests/generate_half_guard_feint_reference.py [output.jsonl]
Default output: GODOT_V1/tests/generated/half_guard_feint_reference.jsonl (git-ignored). The script fails (non-zero exit) on an
empty fixture and prints the measured scenario / operation / comparison counts; it asserts none of them.
"""
import hashlib
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "tests"))
sys.path.insert(0, os.path.join(REPO, "GODOT_V1", "tests"))

from oracles import half_guard_v0_feint_scenarios as scenarios  # noqa: E402
import generate_half_guard_reference as direct  # noqa: E402  (only its input-encoding helpers are reused)


def _operations(row):
    if row["family"] == "feint_trajectory":
        return len(row["commands"])
    return 1 if row["family"] in ("feint_grid", "feint_funding", "feint_refusal", "timeout_fallback", "public_view") else 0


def write(path, rows=None):
    rows = scenarios.all_rows() if rows is None else rows
    if not rows:
        raise SystemExit("half guard feint fixture generation produced no scenarios")
    digest = hashlib.sha256()
    comparisons = operations = 0
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="ascii", newline="\n") as handle:
        for row in rows:
            line = json.dumps(direct._encode(row), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            handle.write(line + "\n")
            digest.update(line.encode("ascii") + b"\n")
            comparisons += direct._leaves(row.get("expected"))
            operations += _operations(row)
    return {"scenarios": len(rows), "operations": operations, "comparisons": comparisons, "sha256": digest.hexdigest()}


def main(argv):
    default = os.path.join(REPO, "GODOT_V1", "tests", "generated", "half_guard_feint_reference.jsonl")
    summary = write(argv[1] if len(argv) > 1 else default)
    print("half_guard_feint_reference: scenarios=%(scenarios)d operations=%(operations)d comparisons=%(comparisons)d sha256=%(sha256)s" % summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
