"""Bounded, deterministic scenario families for the Half Guard v0 oracle (B1b checkpoint).

Shared by the focused unit tests and the fixture generator. Every family is a plain function that returns
JSON-able rows; the *counts are measured by running them*, never asserted from documentation. Expected values
always come from ``half_guard_v0`` (the oracle) -- never from the GDScript, which does not exist yet.
Structured boundary coverage is used wherever the state space is large; exhaustive enumeration only where it is
small (15 matchups x 9 tier pairs x a short list of stamina and commitment profiles).
"""
import copy
import functools

from . import half_guard_v0 as O

TOP_ID, BOTTOM_ID = "fighter_a", "fighter_b"
COMMITMENTS = ("LOW", "MEDIUM", "HIGH")


def fighter(current=100, maximum=100, latched=None, remainder=0):
    if latched is None:
        latched = O.latch_after(current, maximum, current <= O.enter_threshold(maximum))
    return {"stamina_current": current, "stamina_maximum": maximum, "exhaustion_latched": latched,
            "behavior_remainder_units": remainder}


def entry(top_current=100, bottom_current=100, maximum=100, swap=False, clock=300, interval=5, last_issued=0,
          top_remainder=0, bottom_remainder=0):
    """Fighter-id keyed entry. ``swap`` binds the same two fighters to the opposite roles."""
    a, b = fighter(top_current, maximum, remainder=top_remainder), fighter(bottom_current, maximum, remainder=bottom_remainder)
    role_map = {"top": BOTTOM_ID, "bottom": TOP_ID} if swap else {"top": TOP_ID, "bottom": BOTTOM_ID}
    return {"role_map": role_map, "fighters": {TOP_ID: a, BOTTOM_ID: b},
            "clock": {"initial_seconds": clock, "remaining_seconds": clock}, "window": {"last_issued_id": last_issued},
            "interval_seconds": interval}


def state_with(**overrides):
    """A legal snapshot built from the standard entry plus overrides (used for grids and boundary states)."""
    match, error = O.HalfGuard.from_entry(entry())
    assert not error
    state = match.snapshot()
    for key, value in overrides.items():
        if key in ("top_current", "bottom_current"):
            role = key.split("_")[0]
            f = state["fighters"][state["role_map"][role]]
            f["stamina_current"] = value
            f["exhaustion_latched"] = O.latch_after(value, f["stamina_maximum"], value <= O.enter_threshold(f["stamina_maximum"]))
        else:
            state[key] = value
    return state


# NOTE: the cached families return shared lists; callers must treat the rows as read-only.


def matchups():
    rows = []
    for side in ("top", "bottom"):
        for action, responses in O.RAW[side].items():
            for response in responses:
                rows.append((side, action, response))
    return rows


# ---- families -------------------------------------------------------------------------------------
def band_rows():
    rows = []
    for axis in range(O.AXIS_MIN, O.AXIS_MAX + 1):
        rows.append({"family": "initial_band", "axis": axis, "expected": O.initial_band(axis)})
        for band in (-2, -1, 0, 1, 2):
            rows.append({"family": "band_update", "axis": axis, "band": band, "expected": O.band_update(axis, band)})
    return rows


STAMINA_PROFILES = (  # (initiator current, responder current) on capacity 100 (enter 25, recover 35): one profile per rule class
    (100, 100),   # both fresh
    (20, 100),    # initiator Exhausted (latched), still funded MEDIUM
    (100, 20),    # responder Exhausted
    (20, 20),     # both Exhausted (modifiers cancel)
    (9, 100),     # initiator funded only MEDIUM
    (5, 100),     # initiator funded only LOW
    (2, 100),     # initiator unfunded: Rule 1 waives the responder's charge
    (100, 12),    # responder exactly HIGH-funded
    (100, 11),    # responder HIGH funded down to MEDIUM
    (100, 6),     # responder funded down to LOW
    (100, 2),     # responder unfunded
)


@functools.lru_cache(maxsize=None)
def exchange_rows():
    """Entry-state exchange grid: 15 matchups x 9 tier pairs x stamina profiles x 9 commitment pairs."""
    rows = []
    for side, action, response in matchups():
        for top_base in range(3):
            for bottom_frame in range(3):
                for init_cur, resp_cur in STAMINA_PROFILES:
                    top_cur, bottom_cur = (init_cur, resp_cur) if side == "top" else (resp_cur, init_cur)
                    state = state_with(top_base=top_base, bottom_frame=bottom_frame, initiator=side,
                                       top_current=top_cur, bottom_current=bottom_cur)
                    for commitment in COMMITMENTS:
                        for response_commitment in COMMITMENTS:
                            rows.append(_attempt_row("exchange_grid", state, action, response, commitment, response_commitment))
    return rows


def _attempt_row(family, state, action, response, commitment, response_commitment):
    match = O.HalfGuard.from_snapshot(state)
    result = match.attempt(action, response, commitment, response_commitment)
    return {"family": family, "snapshot": state, "command": {"op": "attempt", "action_id": action, "response_id": response,
            "commitment": commitment, "response_commitment": response_commitment}, "expected": result, "final": match.snapshot()}


BOUNDARY_AXES = (-40, -35, -30, -25, -20, -12, -5, 0, 5, 12, 15, 20, 25, 30, 35, 40)


@functools.lru_cache(maxsize=None)
def break_rows():
    """Break-capable matchups across axis boundaries, all tier pairs, three initiator commitments."""
    rows = []
    for side, action, response in matchups():
        if action not in O.BREAK_CAPABLE:
            continue
        for axis in BOUNDARY_AXES:
            for band in (-2, -1, 0, 1, 2):
                if not O.legal_pair(axis, band):
                    continue
                for top_base in range(3):
                    for bottom_frame in range(3):
                        state = state_with(axis_tenths=axis, band=band, top_base=top_base, bottom_frame=bottom_frame, initiator=side)
                        for commitment in COMMITMENTS:
                            rows.append(_attempt_row("break_grid", state, action, response, commitment, "MEDIUM"))
    return rows


def entry_rows():
    rows = []
    good = [entry(), entry(swap=True), entry(top_current=2, bottom_current=7), entry(top_current=25, bottom_current=35),
            entry(maximum=1, top_current=0, bottom_current=1), entry(maximum=O.MAXIMUM_EXACT, top_current=O.MAXIMUM_EXACT,
                                                                       bottom_current=O.recover_threshold(O.MAXIMUM_EXACT)),
            entry(last_issued=41, interval=7, clock=11, top_remainder=-3, bottom_remainder=O.MAXIMUM_EXACT)]
    for request in good + refusal_entries():
        match, error = O.HalfGuard.from_entry(request)
        rows.append({"family": "entry", "request": copy.deepcopy(request), "expected_error": error,
                     "expected_snapshot": match.snapshot() if match else None})
    return rows


def refusal_entries():
    """One entry per refusal code plus precedence combinations (several faults at once)."""
    base = entry
    out = []

    def mutated(fn):
        request = base()
        fn(request)
        out.append(request)

    out.append("not a dict")
    mutated(lambda r: r.pop("interval_seconds"))
    mutated(lambda r: r.update(extra=1))
    mutated(lambda r: r["role_map"].update(middle="x"))
    mutated(lambda r: r["clock"].update(initial_seconds=300.0))
    mutated(lambda r: r["fighters"][TOP_ID].update(stamina_current=True))
    mutated(lambda r: r["fighters"][TOP_ID].update(top_base=2))
    mutated(lambda r: r["fighters"][BOTTOM_ID].pop("exhaustion_latched"))
    mutated(lambda r: r["role_map"].update(top=""))
    mutated(lambda r: r["role_map"].update(top=" padded"))
    mutated(lambda r: r["role_map"].update(bottom="id\n"))
    mutated(lambda r: r["role_map"].update(bottom=TOP_ID))
    mutated(lambda r: r["fighters"].pop(BOTTOM_ID) or r["fighters"].update(stranger=fighter()))
    mutated(lambda r: r["fighters"][TOP_ID].update(stamina_maximum=0))
    mutated(lambda r: r["fighters"][TOP_ID].update(stamina_maximum=O.MAXIMUM_EXACT + 1))
    mutated(lambda r: r["fighters"][BOTTOM_ID].update(stamina_current=101))
    mutated(lambda r: r["fighters"][BOTTOM_ID].update(stamina_current=-1))
    mutated(lambda r: r["fighters"][TOP_ID].update(stamina_current=25, exhaustion_latched=False))
    mutated(lambda r: r["fighters"][TOP_ID].update(stamina_current=35, exhaustion_latched=True))
    mutated(lambda r: r["fighters"][BOTTOM_ID].update(behavior_remainder_units=O.MAXIMUM_EXACT + 1))
    mutated(lambda r: r["clock"].update(remaining_seconds=0))
    mutated(lambda r: r["clock"].update(remaining_seconds=301))
    mutated(lambda r: r["clock"].update(initial_seconds=0, remaining_seconds=0))
    mutated(lambda r: r["window"].update(last_issued_id=-1))
    mutated(lambda r: r.update(interval_seconds=0))
    mutated(lambda r: r.update(interval_seconds=-5))
    # precedence: several faults at once -> the earliest rule in the sheet's order wins
    mutated(lambda r: (r.update(interval_seconds=0), r["window"].update(last_issued_id=-1), r["clock"].update(remaining_seconds=0)))
    mutated(lambda r: (r["role_map"].update(bottom=TOP_ID), r["fighters"][TOP_ID].update(stamina_maximum=0)))
    return out


def trajectory_rows():
    """Deterministic multi-command trajectories (windows, passes, refusals, timeouts, waiver, exits)."""
    rows = []
    for name, (request, commands) in trajectories().items():
        rows.append({"family": "trajectory", "name": name, "entry": request, "commands": commands,
                     "expected": O.replay(request, commands)})
    return rows


A = {"cf": "half_guard.top.crossface", "fl": "half_guard.top.flatten", "ks": "half_guard.top.knee_slice",
     "uh": "half_guard.bottom.underhook", "rg": "half_guard.bottom.recover_guard"}
R = {"hf": "half_guard.bottom_response.hip_frame", "uf": "half_guard.bottom_response.underhook_fight",
     "ks": "half_guard.bottom_response.knee_shield", "hc": "half_guard.top_response.head_control",
     "hp": "half_guard.top_response.hip_pressure", "kp": "half_guard.top_response.knee_pin"}


def _o():
    return {"op": "open"}


def _s(window_id, who, action="", response="", commitment="", response_commitment=""):
    return {"op": "submit", "window_id": window_id, "fighter_id": who, "action_id": action, "response_id": response,
            "commitment": commitment, "response_commitment": response_commitment}


def trajectories():
    a, b = TOP_ID, BOTTOM_ID
    out = {}
    out["opening_and_alternation"] = (entry(last_issued=9), [
        _o(), _s(10, a, A["cf"], R["uf"]), _o(), _s(11, b, A["uh"], R["hc"]), _o(), _s(12, a, "", ""), _o(), _s(13, b)])
    out["double_open_and_stale"] = (entry(), [_o(), _o(), _s(2, a, A["cf"], R["hf"]), _s(1, b, A["uh"], R["hp"]),
                                              _s(1, a, A["cf"], R["hf"]), _s(1, a, A["cf"], R["hf"])])
    out["pass_pass_timeout"] = (entry(clock=20, interval=5), [
        _o(), _s(1, a), _o(), _s(2, b), _o(), _s(3, a), _o(), _o(), _s(3, a)])
    out["zero_time_window"] = (entry(clock=10), [
        {"op": "open", "duration": -1}, {"op": "open", "duration": True}, {"op": "open", "duration": "5"},
        {"op": "open", "duration": 2.5}, {"op": "open", "duration": 0}, _s(1, a, A["fl"], R["hf"]),
        {"op": "open", "duration": 99}])
    out["timeout_exact_boundary"] = (entry(clock=5, interval=5), [_o(), _o(), _s(1, a, A["cf"], R["hf"])])
    out["rule1_waiver_high_unpaid"] = (entry(top_current=2, bottom_current=100), [
        _o(), _s(1, a, A["ks"], R["ks"], "HIGH", "HIGH")])
    out["rule1_paid_high_preserved"] = (entry(top_current=5, bottom_current=100), [
        _o(), _s(1, a, A["ks"], R["ks"], "LOW", "HIGH")])
    out["refusal_matrix"] = (entry(), [
        _s(1, a, A["cf"], R["hf"]), _o(), _s(0, a, A["cf"], R["hf"]), _s(1, "", A["cf"], R["hf"]), _s(1, "ghost", A["cf"], R["hf"]),
        _s(1, b, A["uh"], R["hc"]), _s(1, a, "", R["hf"]), _s(1, a, "", "", "LOW"), _s(1, a, "", "", "", "LOW"),
        _s(1, a, A["cf"], R["hf"], "EXTREME"), _s(1, a, A["cf"], R["hf"], "", "EXTREME"), _s(1, a, "nope", R["hf"]),
        _s(1, a, A["uh"], R["hf"]), _s(1, a, R["hf"], R["hf"]), _s(1, a, A["cf"], "nope"), _s(1, a, A["cf"], ""),
        _s(1, a, A["cf"], R["hc"]), _s(1, a, A["cf"], A["uh"]), _s(1, a, A["cf"], R["hf"])])
    out["cooperative_exit_side_control"] = (entry(), [
        _o(), _s(1, a, A["ks"], R["uf"]), _o(), _s(2, b, A["uh"], R["hc"]), _o(), _s(3, a, A["ks"], R["uf"]),
        _o(), _s(4, b, "", ""), _o(), _s(5, a, A["cf"], R["hf"])])
    out["post_exit_refusals"] = (entry(), [
        _o(), _s(1, a, A["ks"], R["uf"]), _o(), _s(2, b), _o(), _s(3, a, A["ks"], R["uf"]),
        {"op": "attempt", "action_id": A["cf"], "response_id": R["hf"], "commitment": "MEDIUM"}, _o(), _s(3, a, A["cf"], R["hf"])])
    return out


def trajectory_rows():
    """Deterministic multi-command trajectories (windows, passes, refusals, timeouts, waiver, exits)."""
    rows = []
    for name, (request, commands) in trajectories().items():
        rows.append({"family": "trajectory", "name": name, "entry": request, "commands": commands,
                     "expected": O.replay(request, commands)})
    return rows


A = {"cf": "half_guard.top.crossface", "fl": "half_guard.top.flatten", "ks": "half_guard.top.knee_slice",
     "uh": "half_guard.bottom.underhook", "rg": "half_guard.bottom.recover_guard"}
R = {"hf": "half_guard.bottom_response.hip_frame", "uf": "half_guard.bottom_response.underhook_fight",
     "ks": "half_guard.bottom_response.knee_shield", "hc": "half_guard.top_response.head_control",
     "hp": "half_guard.top_response.hip_pressure", "kp": "half_guard.top_response.knee_pin"}


def _o():
    return {"op": "open"}


def _s(window_id, who, action="", response="", commitment="", response_commitment=""):
    return {"op": "submit", "window_id": window_id, "fighter_id": who, "action_id": action, "response_id": response,
            "commitment": commitment, "response_commitment": response_commitment}


def trajectories():
    a, b = TOP_ID, BOTTOM_ID
    out = {}
    out["opening_and_alternation"] = (entry(last_issued=9), [
        _o(), _s(10, a, A["cf"], R["uf"]), _o(), _s(11, b, A["uh"], R["hc"]), _o(), _s(12, a, "", ""), _o(), _s(13, b)])
    out["double_open_and_stale"] = (entry(), [_o(), _o(), _s(2, a, A["cf"], R["hf"]), _s(1, b, A["uh"], R["hp"]),
                                              _s(1, a, A["cf"], R["hf"]), _s(1, a, A["cf"], R["hf"])])
    out["pass_pass_timeout"] = (entry(clock=20, interval=5), [
        _o(), _s(1, a), _o(), _s(2, b), _o(), _s(3, a), _o(), _o(), _s(3, a)])
    out["zero_time_window"] = (entry(clock=10), [
        {"op": "open", "duration": -1}, {"op": "open", "duration": True}, {"op": "open", "duration": "5"},
        {"op": "open", "duration": 2.5}, {"op": "open", "duration": 0}, _s(1, a, A["fl"], R["hf"]),
        {"op": "open", "duration": 99}])
    out["timeout_exact_boundary"] = (entry(clock=5, interval=5), [_o(), _o(), _s(1, a, A["cf"], R["hf"])])
    out["rule1_waiver_high_unpaid"] = (entry(top_current=2, bottom_current=100), [
        _o(), _s(1, a, A["ks"], R["ks"], "HIGH", "HIGH")])
    out["rule1_paid_high_preserved"] = (entry(top_current=5, bottom_current=100), [
        _o(), _s(1, a, A["ks"], R["ks"], "LOW", "HIGH")])
    out["refusal_matrix"] = (entry(), [
        _s(1, a, A["cf"], R["hf"]), _o(), _s(0, a, A["cf"], R["hf"]), _s(1, "", A["cf"], R["hf"]), _s(1, "ghost", A["cf"], R["hf"]),
        _s(1, b, A["uh"], R["hc"]), _s(1, a, "", R["hf"]), _s(1, a, "", "", "LOW"), _s(1, a, "", "", "", "LOW"),
        _s(1, a, A["cf"], R["hf"], "EXTREME"), _s(1, a, A["cf"], R["hf"], "", "EXTREME"), _s(1, a, "nope", R["hf"]),
        _s(1, a, A["uh"], R["hf"]), _s(1, a, R["hf"], R["hf"]), _s(1, a, A["cf"], "nope"), _s(1, a, A["cf"], ""),
        _s(1, a, A["cf"], R["hc"]), _s(1, a, A["cf"], A["uh"]), _s(1, a, A["cf"], R["hf"])])
    out["cooperative_exit_side_control"] = (entry(), [
        _o(), _s(1, a, A["ks"], R["uf"]), _o(), _s(2, b, A["uh"], R["hc"]), _o(), _s(3, a, A["ks"], R["uf"]), _o(),
        _s(4, b, "", ""), _o(), _s(5, a, A["ks"], R["uf"]), _o(), _s(6, a, A["cf"], R["hf"])])
    out["post_exit_refusals"] = (entry(), [
        _o(), _s(1, a, A["ks"], R["uf"]), _o(), _s(2, b, "", ""), _o(), _s(3, a, A["ks"], R["uf"]), _o(), _s(4, b, "", ""),
        _o(), _s(5, a, A["ks"], R["uf"]), {"op": "attempt", "action_id": A["cf"], "response_id": R["hf"], "commitment": "MEDIUM"}, _o(), _s(5, a, A["cf"], R["hf"])])
    return out


@functools.lru_cache(maxsize=None)
def all_rows():
    return list(band_rows() + entry_rows() + list(exchange_rows()) + list(break_rows()) + trajectory_rows())


# ---- structural searches (reachability; never a balance claim) --------------------------------------
def _key(snapshot):
    f = snapshot["fighters"]
    ids = (snapshot["role_map"]["top"], snapshot["role_map"]["bottom"])
    return (snapshot["axis_tenths"], snapshot["band"], snapshot["initiator"], snapshot["top_base"], snapshot["bottom_frame"],
            tuple((f[i]["stamina_current"], f[i]["exhaustion_latched"]) for i in ids), snapshot["exit_destination"])


def _step(snapshot, action, response, commitment, response_commitment):
    match = O.HalfGuard.from_snapshot(snapshot)
    result = match.attempt(action, response, commitment, response_commitment)
    assert not result["error"], result
    return match.snapshot(), result


def _pass(snapshot):
    match = O.HalfGuard.from_snapshot(snapshot)
    side = match.s["initiator"]
    match.s["initiator"] = "bottom" if side == "top" else "top"
    return match.snapshot()


def earliest_exits(max_windows=8, commitments=("MEDIUM",)):
    """Breadth-first search with *cooperating* players (both choose freely, passes allowed); windows to each exit label."""
    start = O.HalfGuard.from_entry(entry())[0].snapshot()
    seen, frontier, first = {_key(start)}, [start], {}
    for windows in range(1, max_windows + 1):
        nxt = []
        for snap in frontier:
            side = snap["initiator"]
            other = "bottom" if side == "top" else "top"
            options = [(a, r, c, rc) for a in O.ACTIONS[side] for r in O.RESPONSES[other] for c in commitments for rc in commitments]
            for action, response, commitment, response_commitment in options:
                after, result = _step(snap, action, response, commitment, response_commitment)
                if after["exit_destination"]:
                    first.setdefault(after["exit_destination"], windows)
                    continue
                if _key(after) not in seen:
                    seen.add(_key(after))
                    nxt.append(after)
            passed = _pass(snap)
            if _key(passed) not in seen:
                seen.add(_key(passed))
                nxt.append(passed)
        frontier = nxt
    return first, len(seen)


def best_counter(side, action):
    """The response with the lowest raw grade for the initiator (ties: lowest id)."""
    row = O.RAW[side][action]
    return sorted(row, key=lambda r: (row[r], r))[0]


def best_counter_earliest(max_windows=10, attacker_commitments=("LOW", "MEDIUM", "HIGH"), responder_commitment="MEDIUM"):
    """Breadth-first: the earliest window at which each exit label becomes reachable when the *responder* always plays
    the best counter (at ``responder_commitment``) and the *attacker* chooses any action, commitment or pass. Returns
    ({label: windows}, states explored). Passes count as windows. A label that is absent was not reached in the horizon."""
    start = O.HalfGuard.from_entry(entry())[0].snapshot()
    seen, frontier, first = {_key(start)}, [start], {}
    for windows in range(1, max_windows + 1):
        nxt = []
        for snap in frontier:
            side = snap["initiator"]
            for action in O.ACTIONS[side]:
                for commitment in attacker_commitments:
                    after, _ = _step(snap, action, best_counter(side, action), commitment, responder_commitment)
                    if after["exit_destination"]:
                        first.setdefault(after["exit_destination"], windows)
                    elif _key(after) not in seen:
                        seen.add(_key(after))
                        nxt.append(after)
            passed = _pass(snap)
            if _key(passed) not in seen:
                seen.add(_key(passed))
                nxt.append(passed)
        frontier = nxt
    return first, len(seen)
