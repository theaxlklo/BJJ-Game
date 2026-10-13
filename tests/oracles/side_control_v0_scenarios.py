"""Deterministic Side Control v0 scenario families and fixture generator (B2b-2, test-only).

Every row's expectation is produced by the independent oracle (``side_control_v0``), which is written from the rules sheet.
The rows are also the input a later Godot reference test would replay; until B2c exists nothing consumes the file, so no
parity with any engine is claimed. Everything here is a pure function of constants: the only "random" source is a seeded
integer LCG used to *choose commands*, never to decide an outcome.

Run ``python -m oracles.side_control_v0_scenarios [output.jsonl]`` from ``tests/`` to print the measured counts and the
SHA-256 of the canonical fixture (and optionally write it).
"""
import copy
import hashlib
import json
import sys

from . import side_control_v0 as O

TOP_ID, BOTTOM_ID = "fighter_a", "fighter_b"
A = {action.split(".", 2)[2]: action for action in O.ACTIONS}  # short name -> id, e.g. A["stabilize"]
R = {response.split(".", 2)[2]: response for response in O.RESPONSES}
TIER_PAIRS = [(top, bottom) for top in (0, 1, 2) for bottom in (0, 1, 2)]
COMMITMENT_PAIRS = [(i, r) for i in ("LOW", "MEDIUM", "HIGH") for r in ("LOW", "MEDIUM", "HIGH")]
# (initiator stamina, responder stamina) of 100: fresh, each Exhausted, both, and the unfunded/LOW-only/HIGH-boundary cases
STAMINA_PROFILES = [(100, 100), (20, 100), (100, 20), (20, 20), (2, 100), (5, 100), (100, 2), (100, 5), (100, 12), (100, 11)]


def pool(current, maximum=100, latched=None, remainder=0):
    """A pool whose latch is the consistent one unless the caller asks for a between-thresholds value."""
    if latched is None:
        latched = current <= O.enter_threshold(maximum)
    return {"stamina_current": current, "stamina_maximum": maximum, "exhaustion_latched": latched, "behavior_remainder_units": remainder}


def entry(initiator="top", top=None, bottom=None, initial=300, remaining=None, last_issued=0, interval=10):
    return {
        "role_map": {"top": TOP_ID, "bottom": BOTTOM_ID},
        "initiator": initiator,
        "fighters": {TOP_ID: top or pool(100), BOTTOM_ID: bottom or pool(100)},
        "clock": {"initial_seconds": initial, "remaining_seconds": initial if remaining is None else remaining},
        "window": {"last_issued_id": last_issued},
        "interval_seconds": interval,
    }


def fresh(**kwargs):
    match, error = O.SideControl.from_entry(entry(**kwargs))
    assert not error, error
    return match


def state_with(initiator="top", axis=None, band=None, top_pin=None, bottom_space=None, initiator_current=None, responder_current=None, **entry_kwargs):
    """A legal mid-position snapshot built from a fresh entry; stamina is set by role of the *initiator* for grids."""
    state = fresh(initiator=initiator, **entry_kwargs).snapshot()
    ids = state["role_map"]
    other = "bottom" if initiator == "top" else "top"
    if initiator_current is not None:
        state["fighters"][ids[initiator]] = pool(initiator_current)
    if responder_current is not None:
        state["fighters"][ids[other]] = pool(responder_current)
    for key, value in (("axis_tenths", axis), ("band", band), ("top_pin", top_pin), ("bottom_space", bottom_space)):
        if value is not None:
            state[key] = value
    return state


def _leaves(value):
    if isinstance(value, dict):
        return sum(_leaves(v) for v in value.values())
    if isinstance(value, list):
        return sum(_leaves(v) for v in value) or 1
    return 1


# ---------------------------------------------------------------------------------------------------------------
# Command-refusal tables (one definition, shared by the fixture and the tests)
# ---------------------------------------------------------------------------------------------------------------
def base_open_state():
    """A fresh position with window 1 open for the Top: the neutral ground every submit violation starts from."""
    match = fresh()
    assert match.open_window()["status"] == "opened"
    return match.snapshot()


def base_submit_args():
    return {"window_id": 1, "fighter_id": TOP_ID, "action_id": A["stabilize"], "response_id": R["forearm_frame"],
            "commitment": "MEDIUM", "response_commitment": "MEDIUM"}


def base_attempt_args():
    return {"action_id": A["stabilize"], "response_id": R["forearm_frame"], "commitment": "MEDIUM", "response_commitment": "MEDIUM"}


def _set(**changes):
    return lambda state, args: args.update(changes)


def _state(**changes):
    return lambda state, args: state.update(changes)


# (code, resources it touches, modifier). Two violations that touch the same resource cannot be applied together.
SUBMIT_VIOLATIONS = [
    ("malformed_command", {"window_id"}, _set(window_id="1")),
    ("no_open_window", {"window"}, _state(window_open=False, window_initiator="")),
    ("stale_window", {"window_id"}, _set(window_id=2)),
    ("terminal_exchange", {"clock"}, _state(clock_seconds=0)),
    ("window_initiator_changed", {"window"}, _state(window_initiator="bottom")),
    ("missing_fighter_id", {"fighter"}, _set(fighter_id="")),
    ("unknown_fighter", {"fighter"}, _set(fighter_id="nobody")),
    ("not_initiator", {"fighter"}, _set(fighter_id=BOTTOM_ID)),
    ("response_without_action", {"action", "response"}, _set(action_id="")),
    ("commitment_without_action", {"action", "response", "commitment"}, _set(action_id="", response_id="", commitment="LOW")),
    ("invalid_commitment", {"commitment"}, _set(commitment="EXTREME")),
    ("invalid_response_commitment", {"response_commitment"}, _set(response_commitment="EXTREME")),
    ("unknown_action", {"action"}, _set(action_id="side_control.top.kimura_route")),
    ("incorrect_action_side_or_kind", {"action"}, _set(action_id=A["shrimp"])),
    ("unknown_response", {"response"}, _set(response_id="")),
    ("incorrect_response_side_or_kind", {"response"}, _set(response_id=R["shoulder_pressure"])),
]
ATTEMPT_VIOLATIONS = [
    ("malformed_command", {"action"}, _set(action_id=None)),
    ("window_already_open", {"window"}, _state(window_open=True, window_initiator="top")),
    ("terminal_exchange", {"clock"}, _state(clock_seconds=0)),
    ("invalid_commitment", {"commitment"}, _set(commitment="EXTREME")),
    ("invalid_response_commitment", {"response_commitment"}, _set(response_commitment="EXTREME")),
    ("unknown_action", {"action"}, _set(action_id="")),
    ("incorrect_action_side_or_kind", {"action"}, _set(action_id=R["hip_block"])),
    ("unknown_response", {"response"}, _set(response_id="half_guard.bottom_response.hip_frame")),
    ("incorrect_response_side_or_kind", {"response"}, _set(response_id=A["shrimp"])),
]


def _drop_top_pin(state, args):
    del state["top_pin"]


def _corrupt_top_pool(state, args):
    state["fighters"][TOP_ID]["stamina_current"] = 150


def _corrupt_bottom_latch(state, args):
    state["fighters"][BOTTOM_ID].update(stamina_current=10, exhaustion_latched=False)


# Corrupted snapshots, in context order; each is reported by the next operation as a context error, never by a crash.
CONTEXT_VIOLATIONS = [
    ("missing_state", {"shape"}, _drop_top_pin),
    ("invalid_stamina_state", {"pool_top"}, _corrupt_top_pool),
    ("invalid_exhaustion_latch", {"pool_bottom"}, _corrupt_bottom_latch),
    ("invalid_initiator", {"initiator"}, _state(initiator="nobody")),
    ("invalid_clock_context", {"clock"}, _state(clock_seconds=301)),
    ("terminal_exchange", {"exit"}, _state(exit_destination="Mount")),
    ("invalid_side_control_context", {"axis"}, _state(axis_tenths=41)),
]


def compatible_pairs(violations):
    """Every (earlier, later) pair of violations that touch different resources, in table order."""
    return [(a, b) for i, a in enumerate(violations) for b in violations[i + 1:] if not (a[1] & b[1])]


def _violated(violations, base_state, base_args):
    state, args = copy.deepcopy(base_state), dict(base_args)
    for _code, _touches, modify in violations:
        modify(state, args)
    return state, args


def run_submit(state, args):
    match = O.SideControl.from_snapshot(state)
    return match, match.submit(**args)


def run_attempt(state, args):
    match = O.SideControl.from_snapshot(state)
    return match, match.attempt(**args)


# ---------------------------------------------------------------------------------------------------------------
# Row families
# ---------------------------------------------------------------------------------------------------------------
def band_update_rows():
    return [{"family": "band_update", "id": "a%d_b%d" % (axis, band), "axis": axis, "band": band, "expected": O.band_update(axis, band)}
            for axis in range(O.AXIS_MIN, O.AXIS_MAX + 1) for band in (-2, -1, 0, 1, 2)]


def entry_rows():
    cases = [("valid_default", entry()), ("valid_bottom_initiator", entry(initiator="bottom")),
             ("valid_between_thresholds_latched", entry(top=pool(30, 100, latched=True))),
             ("valid_between_thresholds_unlatched", entry(top=pool(30, 100, latched=False))),
             ("valid_small_capacity_thresholds", entry(top=pool(7, 30), bottom=pool(11, 30))),
             ("valid_remainders", entry(top=pool(50, remainder=-9007199254740991), bottom=pool(50, remainder=3))),
             ("valid_clock_partial", entry(initial=300, remaining=1, last_issued=41)),
             ("not_a_dictionary", [1]), ("malformed_extra_key", dict(entry(), tiers={"top_pin": 2})),
             ("malformed_missing_clock", {k: v for k, v in entry().items() if k != "clock"}),
             ("malformed_bool_stamina", entry(top=pool(True))), ("malformed_float_interval", entry(interval=10.0)),
             ("malformed_initiator_type", entry(initiator=1)),
             ("invalid_fighter_id_equal", dict(entry(), role_map={"top": TOP_ID, "bottom": TOP_ID})),
             ("invalid_fighter_id_padded", dict(entry(), role_map={"top": TOP_ID + " ", "bottom": BOTTOM_ID})),
             ("fighters_mismatch", dict(entry(), fighters={TOP_ID: pool(100), "x": pool(100)})),
             ("invalid_initiator_value", entry(initiator="middle")),
             ("invalid_stamina_maximum", entry(top=pool(0, 0))), ("invalid_stamina_current", entry(top=pool(101))),
             ("inconsistent_latch_low", entry(top=pool(25, 100, latched=False))),
             ("inconsistent_latch_high", entry(top=pool(35, 100, latched=True))),
             ("invalid_behavior_remainder", entry(top=pool(50, remainder=9007199254740992))),
             ("invalid_clock_zero_remaining", entry(remaining=0)), ("invalid_clock_remaining_above_initial", entry(initial=5, remaining=6)),
             ("invalid_window_id", entry(last_issued=-1)), ("invalid_interval", entry(interval=0))]
    rows = []
    for name, request in cases:
        match, error = O.SideControl.from_entry(request)
        rows.append({"family": "entry", "id": name, "entry": request, "expected": {"error": error, "snapshot": match.snapshot() if match else None}})
    return rows


def exchange_grid_rows():
    """Every matchup x every tier pair x every commitment pair x the stamina profiles, run window-less from the entry axis."""
    rows = []
    for action in O.ACTIONS:
        side = O.ACTIONS[action]["side"]
        for response in (r for r in O.RESPONSES if O.RESPONSES[r]["side"] != side):
            for tops, bottoms in TIER_PAIRS:
                for commitment, response_commitment in COMMITMENT_PAIRS:
                    for initiator_current, responder_current in STAMINA_PROFILES:
                        state = state_with(initiator=side, top_pin=tops, bottom_space=bottoms, initiator_current=initiator_current,
                                           responder_current=responder_current)
                        operation = {"op": "attempt", "action_id": action, "response_id": response, "commitment": commitment,
                                     "response_commitment": response_commitment}
                        rows.append(_state_row("exchange_grid", "%s|%s|t%d%d|%s%s|s%d_%d" % (action, response, tops, bottoms, commitment[0],
                                                                                          response_commitment[0], initiator_current, responder_current), state, operation))
    return rows


def break_grid_rows():
    """Each break-capable technique around its exit line: every legal (axis, band), own track tier, and initiator commitment."""
    rows = []
    for action, info in O.ACTIONS.items():
        if not info["break"]:
            continue
        side = info["side"]
        axes = [a for a in range(-40, 41, 5)] + [a for a in (-31, -29, -21, -19, -11, -9, 9, 11, 19, 21, 29, 31)]
        for response in (r for r in O.RESPONSES if O.RESPONSES[r]["side"] != side):
            for axis in sorted(axes):
                for band in (-2, -1, 0, 1, 2):
                    if not O.legal_pair(axis, band):
                        continue
                    for tier in (0, 1, 2):
                        for commitment in ("LOW", "MEDIUM", "HIGH"):
                            tiers = {"top_pin": 1, "bottom_space": 1}
                            tiers[info["track"]] = tier
                            state = state_with(initiator=side, axis=axis, band=band, **tiers)
                            operation = {"op": "attempt", "action_id": action, "response_id": response, "commitment": commitment,
                                         "response_commitment": "MEDIUM"}
                            rows.append(_state_row("break_grid", "%s|%s|a%d|b%d|t%d|%s" % (action, response, axis, band, tier, commitment[0]), state, operation))
    return rows


def _state_row(family, name, state, operation):
    match = O.SideControl.from_snapshot(state)
    result = match.attempt(operation["action_id"], operation["response_id"], operation["commitment"], operation["response_commitment"])
    return {"family": family, "id": name, "state": state, "operation": operation, "expected": {"result": result, "snapshot": match.snapshot()}}


def refusal_rows():
    """Each command refusal alone and each compatible pair together: the earlier code must win and nothing may change."""
    rows = []
    base = base_open_state()
    attempt_base = fresh().snapshot()
    for label, table, state0, args0, runner, operation in (("submit", SUBMIT_VIOLATIONS, base, base_submit_args(), run_submit, "submit"),
                                                          ("attempt", ATTEMPT_VIOLATIONS, attempt_base, base_attempt_args(), run_attempt, "attempt")):
        groups = [[v] for v in table] + [list(pair) for pair in compatible_pairs(table)]
        for group in groups:
            state, args = _violated(group, state0, args0)
            before = copy.deepcopy(state)
            match, result = runner(state, args)
            rows.append({"family": "refusal", "id": "%s:%s" % (label, "+".join(v[0] for v in group)), "state": before,
                         "operation": dict(args, op=operation), "expected": {"result": result, "snapshot": match.snapshot()}})
    for group in [[v] for v in CONTEXT_VIOLATIONS] + [list(pair) for pair in compatible_pairs(CONTEXT_VIOLATIONS)]:
        state, args = _violated(group, attempt_base, base_attempt_args())
        before = copy.deepcopy(state)
        match, result = run_attempt(state, args)
        rows.append({"family": "refusal", "id": "context:" + "+".join(v[0] for v in group), "state": before,
                     "operation": dict(args, op="attempt"), "expected": {"result": result, "snapshot": match.snapshot()}})
    return rows


def _lcg(seed):
    """Seeded 31-bit linear congruential generator (integers only) used to pick commands, never outcomes."""
    value = seed
    while True:
        value = (value * 1103515245 + 12345) % 2147483648
        yield value >> 8


def trajectory_rows(count=64, steps=40):
    """Seeded command streams driven through a live oracle; ~1 in 7 commands is a deliberate refusal case."""
    rows = []
    actions = {role: [a for a in O.ACTIONS if O.ACTIONS[a]["side"] == role] for role in O.ROLES}
    responses = {role: [r for r in O.RESPONSES if O.RESPONSES[r]["side"] == role] for role in O.ROLES}
    for seed in range(count):
        draw = _lcg(seed + 1)
        request = entry(initiator=("top", "bottom")[seed % 2], initial=(60, 120, 300)[seed % 3], interval=(5, 10, 15)[seed % 3],
                        top=pool((100, 60, 30, 8)[seed % 4]), bottom=pool((100, 40, 20, 3)[(seed // 4) % 4]))
        match, error = O.SideControl.from_entry(request)
        assert not error, (seed, error)
        operations = []
        for _ in range(steps):
            snapshot = match.snapshot()
            roll = next(draw) % 7
            if not snapshot["window_open"]:
                operation = {"op": "open_window"} if roll else {"op": "open_window", "duration": next(draw) % 12}
            else:
                role, other = snapshot["initiator"], O.ROLES[1 - O.ROLES.index(snapshot["initiator"])]
                operation = {"op": "submit", "window_id": snapshot["window_id"], "fighter_id": snapshot["role_map"][role], "action_id": "",
                             "response_id": "", "commitment": "", "response_commitment": ""}
                if roll:
                    operation.update(action_id=actions[role][next(draw) % 3], response_id=responses[other][next(draw) % 3],
                                     commitment=("LOW", "MEDIUM", "HIGH")[next(draw) % 3], response_commitment=("LOW", "MEDIUM", "HIGH")[next(draw) % 3])
                if next(draw) % 7 == 0:
                    operation["window_id"] += 1  # a stale id: must be refused and change nothing
            operations.append(operation)
            if operation["op"] == "open_window":
                match.open_window(operation.get("duration"))
            else:
                match.submit(**{k: v for k, v in operation.items() if k != "op"})
        outcome = O.replay(request, operations)
        rows.append({"family": "trajectory", "id": "seed%d" % seed, "entry": request, "operations": operations,
                     "expected": {"results": outcome["results"], "snapshot": outcome["snapshot"]}})
    return rows


def all_rows():
    return band_update_rows() + entry_rows() + exchange_grid_rows() + break_grid_rows() + refusal_rows() + trajectory_rows()


def _operations(row):
    if row["family"] == "trajectory":
        return len(row["operations"])
    return 0 if row["family"] == "band_update" else 1


def fixture_lines(rows=None):
    """Canonical JSONL lines (sorted keys, ASCII, no float surprises): the fixture's exact bytes, one string per row."""
    return [json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True) for row in (all_rows() if rows is None else rows)]


def summarize(rows=None, path=None):
    """Measured scenario / operation / comparison counts and the SHA-256 of the canonical fixture; optionally writes it."""
    rows = all_rows() if rows is None else rows
    if not rows:
        raise SystemExit("side control fixture generation produced no scenarios")
    lines = fixture_lines(rows)
    digest = hashlib.sha256()
    for line in lines:
        digest.update(line.encode("ascii") + b"\n")
    if path:
        with open(path, "w", encoding="ascii", newline="\n") as handle:
            handle.write("".join(line + "\n" for line in lines))
    families = {}
    for row in rows:
        families[row["family"]] = families.get(row["family"], 0) + 1
    return {"scenarios": len(rows), "operations": sum(_operations(row) for row in rows),
            "comparisons": sum(_leaves(row["expected"]) for row in rows), "families": families, "sha256": digest.hexdigest()}


if __name__ == "__main__":
    print(json.dumps(summarize(path=sys.argv[1] if len(sys.argv) > 1 else None), sort_keys=True))
