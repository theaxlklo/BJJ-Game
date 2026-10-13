extends SceneTree

# Negative-first tests for the typed standalone Side Control v0 engine (BjjSideControlRules / Catalog / Resolver / Entry / Match).
# Every rejected call must leave the whole position (state, history, window record, clock) exactly as it was. Expected values are
# literals hand-computed from SIDE_CONTROL_V0_RULES.md (the sheet's worked examples plus cases derived the same way); nothing is read
# back from the engine. The independent Python oracle replay lives in test_side_control_reference.gd.
const TOP_ID: String = "fighter_a"
const BOTTOM_ID: String = "fighter_b"
const ST: String = BjjSideControlCatalog.TOP_STABILIZE
const AM: String = BjjSideControlCatalog.TOP_ADVANCE_TO_MOUNT
const EB: String = BjjSideControlCatalog.TOP_EXPOSE_BACK
const SH: String = BjjSideControlCatalog.BOTTOM_SHRIMP
const RH: String = BjjSideControlCatalog.BOTTOM_RECOVER_HALF_GUARD
const TK: String = BjjSideControlCatalog.BOTTOM_TURN_TO_KNEES
const FF: String = BjjSideControlCatalog.BOTTOM_FOREARM_FRAME
const HE: String = BjjSideControlCatalog.BOTTOM_HIP_ESCAPE
const BD: String = BjjSideControlCatalog.BOTTOM_BRIDGE_DEFENSE
const SP: String = BjjSideControlCatalog.TOP_SHOULDER_PRESSURE
const HB: String = BjjSideControlCatalog.TOP_HIP_BLOCK
const FH: String = BjjSideControlCatalog.TOP_FOLLOW_THE_HIPS
const SOURCES: Array[String] = [
    "res://scripts/positions/side_control/side_control_rules.gd", "res://scripts/positions/side_control/side_control_catalog.gd",
    "res://scripts/positions/side_control/side_control_resolver.gd", "res://scripts/positions/side_control/side_control_entry.gd",
    "res://scripts/positions/side_control/side_control_match.gd",
]

var checks: int = 0
var failures: int = 0


func check(label: String, actual: Variant, expected: Variant) -> void:
    checks += 1
    if typeof(actual) != typeof(expected) or JSON.stringify(actual, "", true, true) != JSON.stringify(expected, "", true, true):
        failures += 1
        if failures <= 25:
            push_error("%s: got %s expected %s" % [label, JSON.stringify(actual), JSON.stringify(expected)])


func _initialize() -> void:
    _test_rejected_entries()
    _test_entry_type_matrix()
    _test_fighter_id_edges()
    _test_latch_boundaries()
    _test_entry_state()
    _test_context_corruption()
    _test_unusable_shapes_are_quarantined()
    _test_command_refusals_and_precedence()
    _test_open_window_precedence()
    _test_window_lifecycle()
    _test_window_id_ceiling()
    _test_pass()
    _test_worked_examples()
    _test_grade_pipeline_literals()
    _test_readiness_and_wear()
    _test_rule_one_and_paid_effort()
    _test_exits_and_terminal_states()
    _test_rules_tables_and_bands()
    _test_catalog()
    _test_views_are_detached()
    _test_determinism()
    _test_scope_and_hygiene()
    if failures > 0:
        push_error("Side Control boundaries: %d / %d assertions failed" % [failures, checks])
        quit(1)
        return
    print("Side Control boundaries PASS: %d assertions" % checks)
    quit(0)


# --- Builders -------------------------------------------------------------------------------

func fighter(current: int = 100, maximum: int = 100, remainder: int = 0) -> Dictionary:
    var enter := int(floor(float(maximum) * 0.25))
    return {"stamina_current": current, "stamina_maximum": maximum, "exhaustion_latched": current <= enter, "behavior_remainder_units": remainder}


func entry(initiator: String = "top", top_current: int = 100, bottom_current: int = 100, swap: bool = false, clock: int = 300,
        interval: int = 10, last_issued: int = 0) -> Dictionary:
    return {"role_map": {"top": BOTTOM_ID if swap else TOP_ID, "bottom": TOP_ID if swap else BOTTOM_ID}, "initiator": initiator,
        "fighters": {TOP_ID: fighter(top_current), BOTTOM_ID: fighter(bottom_current)},
        "clock": {"initial_seconds": clock, "remaining_seconds": clock}, "window": {"last_issued_id": last_issued}, "interval_seconds": interval}


func position(request: Dictionary = {}) -> BjjSideControlMatch:
    var created := BjjSideControlMatch.from_entry(entry() if request.is_empty() else request)
    check("fixture entry builds", created.ok(), true)
    return created.match_state


# A mid-position built from a fresh entry with direct state assignment (the public typed fields).
func at(initiator: String = "top", axis: int = 10, band_value: int = 1, pin: int = 1, space: int = 1, top_current: int = 100,
        bottom_current: int = 100) -> BjjSideControlMatch:
    var state := position(entry(initiator, top_current, bottom_current))
    state.axis_tenths = axis
    state.band = band_value
    state.top_pin = pin
    state.bottom_space = space
    return state


func canon(state: BjjSideControlMatch) -> String:
    return JSON.stringify(state.snapshot(), "", true, true)


# One refusal: the exact code, no payload, and the whole snapshot byte-identical.
func refused(label: String, state: BjjSideControlMatch, result: BjjSideControlMatch.Result, before: String, code: String) -> void:
    check("%s: refused" % label, result.ok(), false)
    check("%s: code" % label, result.error, code)
    check("%s: no payload" % label, result.values.is_empty(), true)
    check("%s: nothing changed" % label, canon(state), before)


# A successful exchange record (and the match is mutated).
func record_of(result: BjjSideControlMatch.Result) -> Dictionary:
    check("accepted", result.ok(), true)
    return result.values.get("record", {})


func subset(source: Dictionary, keys: Array[String]) -> Dictionary:
    var out := {}
    for key: String in keys:
        out[key] = source.get(key)
    return out


# --- Entry ------------------------------------------------------------------------------------

func _entry_with(change: Callable) -> Dictionary:
    var request := entry()
    change.call(request)
    return request


func _test_rejected_entries() -> void:
    var cases: Array = [
        ["entry_not_a_dictionary", [1]], ["entry_not_a_dictionary", null], ["entry_not_a_dictionary", "entry"],
        ["entry_malformed", _entry_with(func(r: Dictionary) -> void: r["tiers"] = {"top_pin": 2})],
        ["entry_malformed", _entry_with(func(r: Dictionary) -> void: r["axis_tenths"] = 10)],
        ["entry_malformed", _entry_with(func(r: Dictionary) -> void: r.erase("initiator"))],
        ["entry_malformed", _entry_with(func(r: Dictionary) -> void: r.erase("clock"))],
        ["entry_malformed", _entry_with(func(r: Dictionary) -> void: r["initiator"] = 1)],
        ["entry_malformed", _entry_with(func(r: Dictionary) -> void: r["interval_seconds"] = 10.0)],
        ["entry_malformed", _entry_with(func(r: Dictionary) -> void: r["interval_seconds"] = true)],
        ["entry_malformed", _entry_with(func(r: Dictionary) -> void: r["fighters"][TOP_ID]["stamina_current"] = true)],
        ["entry_malformed", _entry_with(func(r: Dictionary) -> void: r["fighters"][TOP_ID]["exhaustion_latched"] = 0)],
        ["entry_malformed", _entry_with(func(r: Dictionary) -> void: r["fighters"][TOP_ID]["band"] = "Fresh")],
        ["entry_malformed", _entry_with(func(r: Dictionary) -> void: r["role_map"]["top"] = 5)],
        ["entry_malformed", _entry_with(func(r: Dictionary) -> void: r["clock"]["remaining_seconds"] = 5.5)],
        ["entry_malformed", _entry_with(func(r: Dictionary) -> void: r["window"]["last_issued_id"] = "0")],
        ["invalid_fighter_id", _entry_with(func(r: Dictionary) -> void: r["role_map"]["top"] = "")],
        ["invalid_fighter_id", _entry_with(func(r: Dictionary) -> void: r["role_map"]["bottom"] = TOP_ID)],
        ["fighters_mismatch", _entry_with(func(r: Dictionary) -> void: r["fighters"] = {TOP_ID: fighter(), "x": fighter()})],
        ["fighters_mismatch", _entry_with(func(r: Dictionary) -> void: r["fighters"][BOTTOM_ID + "2"] = fighter())],
        ["invalid_initiator", entry("middle")], ["invalid_initiator", entry("")], ["invalid_initiator", entry("TOP")],
        ["invalid_stamina_maximum", _entry_with(func(r: Dictionary) -> void: r["fighters"][TOP_ID]["stamina_maximum"] = 0)],
        ["invalid_stamina_maximum", _entry_with(func(r: Dictionary) -> void: r["fighters"][BOTTOM_ID]["stamina_maximum"] = 9007199254740992)],
        ["invalid_stamina_current", _entry_with(func(r: Dictionary) -> void: r["fighters"][TOP_ID]["stamina_current"] = -1)],
        ["invalid_stamina_current", _entry_with(func(r: Dictionary) -> void: r["fighters"][BOTTOM_ID]["stamina_current"] = 101)],
        ["inconsistent_exhaustion_latch", _entry_with(func(r: Dictionary) -> void: r["fighters"][TOP_ID] = {"stamina_current": 25,
            "stamina_maximum": 100, "exhaustion_latched": false, "behavior_remainder_units": 0})],
        ["inconsistent_exhaustion_latch", _entry_with(func(r: Dictionary) -> void: r["fighters"][BOTTOM_ID] = {"stamina_current": 35,
            "stamina_maximum": 100, "exhaustion_latched": true, "behavior_remainder_units": 0})],
        ["invalid_behavior_remainder", _entry_with(func(r: Dictionary) -> void: r["fighters"][TOP_ID]["behavior_remainder_units"] = 9007199254740992)],
        ["invalid_behavior_remainder", _entry_with(func(r: Dictionary) -> void: r["fighters"][BOTTOM_ID]["behavior_remainder_units"] = -9007199254740992)],
        ["invalid_clock", _entry_with(func(r: Dictionary) -> void: r["clock"]["remaining_seconds"] = 0)],
        ["invalid_clock", _entry_with(func(r: Dictionary) -> void: r["clock"] = {"initial_seconds": 5, "remaining_seconds": 6})],
        ["invalid_clock", _entry_with(func(r: Dictionary) -> void: r["clock"] = {"initial_seconds": 0, "remaining_seconds": 0})],
        ["invalid_window_id", entry("top", 100, 100, false, 300, 10, -1)],
        ["invalid_window_id", entry("top", 100, 100, false, 300, 10, 9007199254740992)],
        ["invalid_interval", entry("top", 100, 100, false, 300, 0)],
        ["invalid_interval", entry("top", 100, 100, false, 300, -3)],
    ]
    for case: Array in cases:
        var request: Variant = case[1]
        var before := JSON.stringify(request, "", true, true)
        check("validate %s" % case[0], BjjSideControlEntry.validate(request), case[0])
        var created := BjjSideControlMatch.from_entry(request)
        check("builds nothing for %s" % case[0], created.match_state == null and not created.ok() and created.error == case[0], true)
        check("request untouched for %s" % case[0], JSON.stringify(request, "", true, true), before)
    # Earlier codes win: the first failing code of the sheet's order is reported.
    var two := entry("middle")
    two["fighters"][TOP_ID]["stamina_maximum"] = 0
    check("invalid_initiator precedes invalid_stamina_maximum", BjjSideControlEntry.validate(two), "invalid_initiator")
    var three := entry()
    three["clock"]["remaining_seconds"] = 0
    three["interval_seconds"] = 0
    check("invalid_clock precedes invalid_interval", BjjSideControlEntry.validate(three), "invalid_clock")
    var four := entry()
    four["role_map"]["bottom"] = TOP_ID
    four["initiator"] = "middle"
    check("invalid_fighter_id precedes invalid_initiator", BjjSideControlEntry.validate(four), "invalid_fighter_id")
    var five := entry()
    five["tiers"] = 1
    five["role_map"]["bottom"] = TOP_ID
    check("entry_malformed precedes invalid_fighter_id", BjjSideControlEntry.validate(five), "entry_malformed")
    # Role order inside one code: Top is checked before Bottom (both bad -> still one code, but the Top value is reported by position).
    var both := entry()
    both["fighters"][TOP_ID]["stamina_current"] = 500
    both["fighters"][BOTTOM_ID]["stamina_maximum"] = 0
    check("maximum is checked for both fighters before any current", BjjSideControlEntry.validate(both), "invalid_stamina_maximum")
    # An entry carrying no time left is refused as inconsistent; a valid partial clock and a carried window id are legal.
    var partial := entry("bottom", 100, 100, false, 300, 10, 41)
    partial["clock"]["remaining_seconds"] = 1
    check("a one-second remainder is a valid entry", BjjSideControlEntry.validate(partial), "")
    # The remainder bound is two comparisons: absi(-2^63) would overflow and slip through for a typed caller.
    for extreme: int in [-9223372036854775807 - 1, 9223372036854775807, -9007199254740992]:
        var wide := entry()
        wide["fighters"][TOP_ID]["behavior_remainder_units"] = extreme
        check("remainder %d is refused" % extreme, BjjSideControlEntry.validate(wide), "invalid_behavior_remainder")
    # A valid request is never mutated by being accepted (plain, swapped role map, between-thresholds latched).
    var latched_request := entry()
    latched_request["fighters"][TOP_ID] = {"stamina_current": 30, "stamina_maximum": 100, "exhaustion_latched": true, "behavior_remainder_units": 0}
    for request: Dictionary in [entry(), entry("bottom", 100, 100, true), latched_request]:
        var before := JSON.stringify(request, "", true, true)
        check("accepted request is built", BjjSideControlMatch.from_entry(request).ok(), true)
        check("accepted request is untouched", JSON.stringify(request, "", true, true), before)


# Every leaf and container of a valid entry replaced by each wrong type, and every key of each exact-key container removed or doubled:
# all are `entry_malformed`, build nothing and leave the request untouched.
func _test_entry_type_matrix() -> void:
    var strings: Array = [["role_map", "top"], ["role_map", "bottom"], ["initiator"]]
    var integers: Array = [["interval_seconds"], ["clock", "initial_seconds"], ["clock", "remaining_seconds"], ["window", "last_issued_id"]]
    var booleans: Array = []
    var containers: Array = [["role_map"], ["fighters"], ["clock"], ["window"]]
    for id: String in [TOP_ID, BOTTOM_ID]:
        integers.append(["fighters", id, "stamina_current"])
        integers.append(["fighters", id, "stamina_maximum"])
        integers.append(["fighters", id, "behavior_remainder_units"])
        booleans.append(["fighters", id, "exhaustion_latched"])
        containers.append(["fighters", id])
    var cases: Array = []
    for path: Array in strings:
        for wrong: Variant in [null, true, 1.5, 5, []]:
            cases.append([path, wrong])
    for path: Array in integers:
        for wrong: Variant in [null, true, 1.5, "x", []]:
            cases.append([path, wrong])
    for path: Array in booleans:
        for wrong: Variant in [null, 0, 1.5, "x", []]:
            cases.append([path, wrong])
    for path: Array in containers:
        for wrong: Variant in [null, true, 1.5, "x", 5]:
            cases.append([path, wrong])
    for case: Array in cases:
        var request := entry()
        var parent: Dictionary = request
        var path: Array = case[0]
        for step in range(path.size() - 1):
            parent = parent[path[step]]
        parent[path[path.size() - 1]] = case[1]
        _expect_malformed(request, "%s := %s" % [path, JSON.stringify(case[1])])
    # Missing and extra keys inside each exact-key container (the fighters map itself is keyed by id, so it is excluded).
    for path: Array in [[], ["role_map"], ["clock"], ["window"], ["fighters", TOP_ID], ["fighters", BOTTOM_ID]]:
        var keys: Array = _node(entry(), path).keys()
        for key: Variant in keys:
            var missing := entry()
            _node(missing, path).erase(key)
            _expect_malformed(missing, "%s missing %s" % [path, key])
        var extra := entry()
        _node(extra, path)["extra_key"] = 1
        _expect_malformed(extra, "%s extra key" % [path])


func _node(request: Dictionary, path: Array) -> Dictionary:
    var node: Dictionary = request
    for step: String in path:
        node = node[step]
    return node


func _expect_malformed(request: Dictionary, label: String) -> void:
    var before := JSON.stringify(request, "", true, true)
    var created := BjjSideControlMatch.from_entry(request)
    check("malformed %s" % label, created.error, "entry_malformed")
    check("malformed builds nothing %s" % label, created.match_state == null, true)
    check("malformed leaves the request untouched %s" % label, JSON.stringify(request, "", true, true), before)


func _test_fighter_id_edges() -> void:
    var padded: Array[String] = ["\u0001a", "a\u0001", " a", "a ", "a\n", "\ta", " ", "a\u001f"]
    for id: String in padded:
        var request := entry()
        request["role_map"]["top"] = id
        request["fighters"] = {id: fighter(), BOTTOM_ID: fighter()}
        check("padded id refused %s" % JSON.stringify(id), BjjSideControlEntry.validate(request), "invalid_fighter_id")
    # Godot 4.7.2 strip_edges strips exactly 0x01..0x20: these are NOT stripped, so they are accepted ids (also interior whitespace).
    var accepted: Array[String] = ["\u007fa", "a\u007f", "\u0085a", " a", "a ", " a", "﻿a", "a b", "a  b"]
    for id: String in accepted:
        var request := entry()
        request["role_map"]["top"] = id
        request["fighters"] = {id: fighter(), BOTTOM_ID: fighter()}
        check("unstripped id accepted %s" % JSON.stringify(id), BjjSideControlEntry.validate(request), "")


func _test_latch_boundaries() -> void:
    # (capacity, current, latched, expected): enter = floor(0.25 m), recover = ceil(0.35 m); between them either value is carried.
    var rows: Array = [[100, 25, false, "inconsistent_exhaustion_latch"], [100, 25, true, ""], [100, 26, false, ""], [100, 26, true, ""],
        [100, 34, true, ""], [100, 35, true, "inconsistent_exhaustion_latch"], [100, 35, false, ""], [100, 0, false, "inconsistent_exhaustion_latch"],
        [30, 7, false, "inconsistent_exhaustion_latch"], [30, 8, false, ""], [30, 10, true, ""], [30, 11, true, "inconsistent_exhaustion_latch"],
        [1, 0, false, "inconsistent_exhaustion_latch"], [1, 1, true, "inconsistent_exhaustion_latch"], [1, 1, false, ""]]
    for row: Array in rows:
        var request := entry()
        request["fighters"][TOP_ID] = {"stamina_current": row[1], "stamina_maximum": row[0], "exhaustion_latched": row[2], "behavior_remainder_units": 0}
        check("latch %s" % [row], BjjSideControlEntry.validate(request), row[3])
    # A between-thresholds value is carried exactly (hysteresis survives a boundary) and an exchange keeps it.
    var latched := entry()
    latched["fighters"][TOP_ID] = {"stamina_current": 30, "stamina_maximum": 100, "exhaustion_latched": true, "behavior_remainder_units": 0}
    var state := position(latched)
    check("carried latched", state.snapshot()["fighters"][TOP_ID]["exhaustion_latched"], true)
    check("a latched fighter below the recover threshold is Exhausted for grading",
        record_of(state.attempt(ST, BD))["final_grade"], -1)  # raw 0, exhaustion -1 for the initiator


func _test_entry_state() -> void:
    var state := position(entry("bottom", 80, 60, true, 120, 5, 41))
    # Roles map onto ids; stamina state follows the FIGHTER ID under a swapped role map (fighter_b is the Top here).
    var expected := {"position_id": "side_control", "role_map": {"top": BOTTOM_ID, "bottom": TOP_ID}, "initiator": "bottom", "axis_tenths": 10,
        "band": 1, "top_pin": 1, "bottom_space": 1,
        "fighters": {TOP_ID: {"stamina_current": 80, "stamina_maximum": 100, "exhaustion_latched": false, "behavior_remainder_units": 0},
            BOTTOM_ID: {"stamina_current": 60, "stamina_maximum": 100, "exhaustion_latched": false, "behavior_remainder_units": 0}},
        "initial_seconds": 120, "clock_seconds": 120, "interval_seconds": 5, "window_id": 41, "window_open": false, "window_initiator": "",
        "exit_destination": "", "exit_reason": "", "decision_history": []}
    check("built state", state.snapshot(), expected)
    check("authority is reported by the axis sign: the Top fighter's id", state.authority_id(), BOTTOM_ID)
    check("not ended", state.is_ended(), false)
    # The initiator is an explicit input, never derived from role, axis or authority.
    for who: String in ["top", "bottom"]:
        check("initiator %s is honored" % who, position(entry(who)).initiator, who)
    # The Top fighter pays for the Top's exchange even when its id is second in the request (identity, not label).
    var swapped := position(entry("top", 100, 40, true))
    check("swapped attempt charges the Top role's fighter", swapped.attempt(ST, FF).ok(), true)
    check("swapped charge lands on fighter_b", subset(swapped.snapshot()["fighters"][BOTTOM_ID], ["stamina_current"]), {"stamina_current": 33})
    check("and not on fighter_a", subset(swapped.snapshot()["fighters"][TOP_ID], ["stamina_current"]), {"stamina_current": 93})
    # Behavior remainders are carried and never changed by v0.
    var carried := entry()
    carried["fighters"][TOP_ID]["behavior_remainder_units"] = -9007199254740991
    carried["fighters"][BOTTOM_ID]["behavior_remainder_units"] = 3
    var remainder_state := position(carried)
    remainder_state.attempt(ST, FF)
    check("remainders untouched", [remainder_state.snapshot()["fighters"][TOP_ID]["behavior_remainder_units"],
        remainder_state.snapshot()["fighters"][BOTTOM_ID]["behavior_remainder_units"]], [-9007199254740991, 3])


# --- Context and shapes -----------------------------------------------------------------------

func _corrupt(change: Callable, open: bool = false) -> BjjSideControlMatch:
    var base := position()
    if open:
        base.open_window()
    var snapshot := base.snapshot()
    change.call(snapshot)
    var created := BjjSideControlMatch.from_snapshot(snapshot)
    check("a corrupted snapshot is still restorable", created.ok(), true)
    return created.match_state


func _test_context_corruption() -> void:
    # (code, mutation) in the sheet's context order; every operation reports it, and nothing changes.
    var rows: Array = [
        ["invalid_stamina_state", func(s: Dictionary) -> void: s["fighters"][TOP_ID]["stamina_current"] = 150],
        ["invalid_stamina_state", func(s: Dictionary) -> void: s["fighters"][BOTTOM_ID]["stamina_maximum"] = 0],
        ["invalid_stamina_state", func(s: Dictionary) -> void: s["fighters"][TOP_ID]["stamina_current"] = -1],
        ["invalid_exhaustion_latch", func(s: Dictionary) -> void: s["fighters"][BOTTOM_ID].merge({"stamina_current": 10, "exhaustion_latched": false}, true)],
        ["invalid_exhaustion_latch", func(s: Dictionary) -> void: s["fighters"][TOP_ID]["exhaustion_latched"] = true],
        ["invalid_initiator", func(s: Dictionary) -> void: s["initiator"] = "nobody"],
        ["invalid_clock_context", func(s: Dictionary) -> void: s["clock_seconds"] = 301],
        ["invalid_clock_context", func(s: Dictionary) -> void: s["clock_seconds"] = -1],
        ["invalid_clock_context", func(s: Dictionary) -> void: s["interval_seconds"] = 0],
        ["invalid_clock_context", func(s: Dictionary) -> void: s["initial_seconds"] = 0],
        ["terminal_exchange", func(s: Dictionary) -> void: s["exit_destination"] = "Mount"],
        ["terminal_exchange", func(s: Dictionary) -> void: s["exit_destination"] = "Reversal"],
        ["terminal_exchange", func(s: Dictionary) -> void: s["clock_seconds"] = 0],
        ["invalid_side_control_context", func(s: Dictionary) -> void: s["axis_tenths"] = 41],
        ["invalid_side_control_context", func(s: Dictionary) -> void: s["axis_tenths"] = -41],
        ["invalid_side_control_context", func(s: Dictionary) -> void: s["band"] = 2],
        ["invalid_side_control_context", func(s: Dictionary) -> void: s["band"] = 7],
        ["invalid_side_control_context", func(s: Dictionary) -> void: s["top_pin"] = 3],
        ["invalid_side_control_context", func(s: Dictionary) -> void: s["bottom_space"] = -1],
        ["invalid_side_control_context", func(s: Dictionary) -> void: s["position_id"] = "half_guard"],
        ["invalid_side_control_context", func(s: Dictionary) -> void: s["window_id"] = -1],
        ["invalid_side_control_context", func(s: Dictionary) -> void: s["window_initiator"] = "middle"],
    ]
    for row: Array in rows:
        var label: String = "%s %s" % [row[0], rows.find(row)]
        var state := _corrupt(row[1])
        var before := canon(state)
        refused("attempt " + label, state, state.attempt(ST, FF), before, row[0])
        refused("open_window " + label, state, state.open_window(), before, row[0])
        refused("open_window(5) " + label, state, state.open_window(5), before, row[0])
        var open_state := _corrupt(row[1], true)
        var open_before := canon(open_state)
        # The window id the snapshot itself carries, so the stale-window precheck passes and the CONTEXT code is what is reported.
        refused("submit " + label, open_state, open_state.submit(open_state.window_id, TOP_ID, ST, FF, "MEDIUM", "MEDIUM"), open_before, row[0])
    # The earlier context code wins when two corruptions coexist.
    var pair := _corrupt(func(s: Dictionary) -> void:
        s["fighters"][TOP_ID]["stamina_current"] = 150
        s["initiator"] = "nobody"
        s["axis_tenths"] = 99)
    check("stamina state precedes initiator and axis", pair.attempt(ST, FF).error, "invalid_stamina_state")
    var late := _corrupt(func(s: Dictionary) -> void:
        s["exit_destination"] = "Mount"
        s["axis_tenths"] = 99)
    check("a terminal state is reported before any Side Control context", late.attempt(ST, FF).error, "terminal_exchange")


func _test_unusable_shapes_are_quarantined() -> void:
    var snapshot := position().snapshot()
    var broken: Array = []
    for key: String in snapshot:
        var without := snapshot.duplicate(true)
        without.erase(key)
        broken.append(without)
    for change: Array in [["axis_tenths", "10"], ["axis_tenths", 10.0], ["window_open", 1], ["fighters", []], ["role_map", {"top": TOP_ID}],
            ["decision_history", {}], ["band", true], ["initiator", 1], ["exit_reason", null]]:
        var changed := snapshot.duplicate(true)
        changed[change[0]] = change[1]
        broken.append(changed)
    var partial := snapshot.duplicate(true)
    partial["fighters"][TOP_ID] = {"stamina_current": 1}
    broken.append(partial)
    var extra := snapshot.duplicate(true)  # strict by design: an unknown key cannot be held in typed fields
    extra["axis_label"] = "x"
    broken.append(extra)
    var same_ids := snapshot.duplicate(true)  # equal ids would alias one stamina record
    same_ids["role_map"]["bottom"] = TOP_ID
    broken.append(same_ids)
    for raw: Dictionary in broken:
        var created := BjjSideControlMatch.from_snapshot(raw)
        check("quarantined restore succeeds", created.ok(), true)
        var state := created.match_state
        var before := JSON.stringify(raw, "", true, true)
        check("a quarantined snapshot is returned verbatim", canon(state), before)
        refused("attempt on a quarantined snapshot", state, state.attempt(ST, FF), before, "missing_state")
        refused("open_window on a quarantined snapshot", state, state.open_window(), before, "missing_state")
    check("a non-dictionary snapshot builds nothing", BjjSideControlMatch.from_snapshot([1]).error, "snapshot_not_a_dictionary")
    # Window prechecks read the raw snapshot exactly like the oracle's `.get`: an open window is reported before the context.
    var open_raw := position().snapshot()
    open_raw["window_open"] = true
    open_raw["window_id"] = 7
    open_raw["window_initiator"] = "top"
    open_raw.erase("top_pin")
    var open_state := BjjSideControlMatch.from_snapshot(open_raw).match_state
    var before_open := canon(open_state)
    refused("attempt while a window is open", open_state, open_state.attempt(ST, FF), before_open, "window_already_open")
    refused("open_window while a window is open", open_state, open_state.open_window(), before_open, "window_already_open")
    refused("stale id on a quarantined open window", open_state, open_state.submit(6, TOP_ID, ST, FF), before_open, "stale_window")
    refused("matching id on a quarantined open window", open_state, open_state.submit(7, TOP_ID, ST, FF), before_open, "missing_state")
    open_raw.erase("window_id")
    var no_id := BjjSideControlMatch.from_snapshot(open_raw).match_state
    refused("an absent window id is stale for every command", no_id, no_id.submit(0, TOP_ID, ST, FF), canon(no_id), "stale_window")
    check("a quarantined match says so", [no_id.is_quarantined(), position().is_quarantined()], [true, false])
    # Stricter than the oracle by design (the sheet defines no such restore): a float, bool or string window id is never a match, so the
    # command is stale even when Python equality (7.0 == 7, True == 1) would have matched it.
    for wrong: Variant in [7.0, true, "7"]:
        var typed := position().snapshot()
        typed["window_open"] = true
        typed["window_id"] = wrong
        typed.erase("top_pin")
        var typed_state := BjjSideControlMatch.from_snapshot(typed).match_state
        refused("a %s window id is stale" % type_string(typeof(wrong)), typed_state, typed_state.submit(7, TOP_ID, ST, FF), canon(typed_state), "stale_window")
    # Other shapes the typed restore cannot hold: a third fighter and a non-int behavior remainder come back verbatim as missing_state.
    var third := position().snapshot()
    third["fighters"]["fighter_c"] = third["fighters"][TOP_ID].duplicate()
    var remainder := position().snapshot()
    remainder["fighters"][TOP_ID]["behavior_remainder_units"] = 1.0
    for raw: Dictionary in [third, remainder]:
        var held := BjjSideControlMatch.from_snapshot(raw).match_state
        refused("a snapshot the typed state cannot hold", held, held.attempt(ST, FF), JSON.stringify(raw, "", true, true), "missing_state")


func _submit_state() -> BjjSideControlMatch:
    var state := position()
    check("window opens", state.open_window().ok(), true)
    return state


func _test_command_refusals_and_precedence() -> void:
    # (code, mutation of the base submit arguments or of the base state); each alone, with nothing changed.
    var base := {"window_id": 1, "fighter_id": TOP_ID, "action_id": ST, "response_id": FF, "commitment": "MEDIUM", "response_commitment": "MEDIUM"}
    var rows: Array = [
        ["malformed_command", {"window_id": "1"}], ["malformed_command", {"window_id": 1.0}], ["malformed_command", {"window_id": true}],
        ["malformed_command", {"fighter_id": null}], ["malformed_command", {"action_id": 5}], ["malformed_command", {"response_id": []}],
        ["malformed_command", {"commitment": 1}], ["malformed_command", {"response_commitment": {}}],
        ["stale_window", {"window_id": 2}], ["stale_window", {"window_id": 0}], ["stale_window", {"window_id": -1}],
        ["missing_fighter_id", {"fighter_id": ""}], ["unknown_fighter", {"fighter_id": "nobody"}], ["not_initiator", {"fighter_id": BOTTOM_ID}],
        ["response_without_action", {"action_id": ""}],
        ["commitment_without_action", {"action_id": "", "response_id": "", "commitment": "LOW"}],
        ["commitment_without_action", {"action_id": "", "response_id": "", "commitment": "", "response_commitment": "LOW"}],
        ["invalid_commitment", {"commitment": "EXTREME"}], ["invalid_commitment", {"commitment": "medium"}],
        ["invalid_response_commitment", {"response_commitment": "EXTREME"}],
        ["unknown_action", {"action_id": "side_control.top.kimura_route"}], ["unknown_action", {"action_id": "side_control.top.armbar_route"}],
        ["unknown_action", {"action_id": "half_guard.top.knee_slice"}], ["unknown_action", {"action_id": "mount.top.americana"}],
        ["incorrect_action_side_or_kind", {"action_id": SH}], ["incorrect_action_side_or_kind", {"action_id": HB}],
        ["unknown_response", {"response_id": ""}], ["unknown_response", {"response_id": "half_guard.bottom_response.hip_frame"}],
        ["incorrect_response_side_or_kind", {"response_id": SP}], ["incorrect_response_side_or_kind", {"response_id": AM}],
    ]
    for row: Array in rows:
        var state := _submit_state()
        var before := canon(state)
        var args: Dictionary = base.duplicate()
        args.merge(row[1], true)
        var result := state.submit(args.window_id, args.fighter_id, args.action_id, args.response_id, args.commitment, args.response_commitment)
        refused("submit %s %s" % [row[0], JSON.stringify(row[1])], state, result, before, row[0])
        check("the window is still open after %s" % row[0], state.window_open and state.window_id == 1, true)
    # Precedence: the earlier code of the sheet wins over a later one.
    var order: Array = [
        ["malformed_command", "stale_window", {"window_id": "x", "fighter_id": "nobody"}],
        ["stale_window", "unknown_fighter", {"window_id": 9, "fighter_id": "nobody"}],
        ["unknown_fighter", "invalid_commitment", {"fighter_id": "nobody", "commitment": "EXTREME"}],
        ["not_initiator", "unknown_action", {"fighter_id": BOTTOM_ID, "action_id": "nope"}],
        ["response_without_action", "invalid_commitment", {"action_id": "", "commitment": "EXTREME"}],
        ["invalid_commitment", "invalid_response_commitment", {"commitment": "X", "response_commitment": "Y"}],
        ["invalid_response_commitment", "unknown_action", {"response_commitment": "Y", "action_id": "nope"}],
        ["unknown_action", "unknown_response", {"action_id": "nope", "response_id": ""}],
        ["incorrect_action_side_or_kind", "unknown_response", {"action_id": SH, "response_id": ""}],
        ["unknown_response", "incorrect_response_side_or_kind", {"response_id": "nope"}],
    ]
    for row: Array in order:
        var state := _submit_state()
        var args: Dictionary = base.duplicate()
        args.merge(row[2], true)
        var result := state.submit(args.window_id, args.fighter_id, args.action_id, args.response_id, args.commitment, args.response_commitment)
        check("%s beats %s" % [row[0], row[1]], result.error, row[0])
    # No open window; the window-less path; a duplicate delivery of an accepted decision.
    var closed := position()
    refused("submit with no window", closed, closed.submit(0, TOP_ID, ST, FF), canon(closed), "no_open_window")
    var open := _submit_state()
    check("accepted once", open.submit(1, TOP_ID, ST, FF, "MEDIUM", "MEDIUM").ok(), true)
    var after_one := canon(open)
    refused("duplicate delivery", open, open.submit(1, TOP_ID, ST, FF, "MEDIUM", "MEDIUM"), after_one, "no_open_window")
    var attempt_rows: Array = [
        ["malformed_command", [null, FF, "MEDIUM", "MEDIUM"]], ["malformed_command", [ST, 1, "", ""]], ["invalid_commitment", [ST, FF, "X", ""]],
        ["invalid_response_commitment", [ST, FF, "", "X"]], ["unknown_action", ["", FF, "", ""]], ["unknown_action", ["side_control.top.kimura_route", FF, "", ""]],
        ["incorrect_action_side_or_kind", [SH, FF, "", ""]], ["incorrect_action_side_or_kind", [FF, FF, "", ""]],
        ["unknown_response", [ST, "", "", ""]], ["incorrect_response_side_or_kind", [ST, SP, "", ""]],
    ]
    for row: Array in attempt_rows:
        var state := position()
        var args: Array = row[1]
        refused("attempt %s" % row[0], state, state.attempt(args[0], args[1], args[2], args[3]), canon(state), row[0])
    var windowed := _submit_state()
    refused("attempt while a window is open", windowed, windowed.attempt(ST, FF), canon(windowed), "window_already_open")
    # A wrong-side action is wrong for the CURRENT initiator: after a Top exchange the Bottom acts and a Top action is refused.
    var turn := position()
    check("top acts", turn.attempt(ST, FF).ok(), true)
    refused("a Top action when the Bottom is the initiator", turn, turn.attempt(ST, FF), canon(turn), "incorrect_action_side_or_kind")
    refused("a Bottom response given as the Top's... response", turn, turn.attempt(SH, FF), canon(turn), "incorrect_response_side_or_kind")
    var wrong_initiative := position(entry("bottom"))
    wrong_initiative.open_window()
    refused("Top may not submit on the Bottom's window", wrong_initiative, wrong_initiative.submit(1, TOP_ID, ST, FF), canon(wrong_initiative), "not_initiator")
    # window_initiator_changed is unreachable through the public API and exercised through a corrupted open snapshot.
    var changed := _corrupt(func(s: Dictionary) -> void: s["window_initiator"] = "bottom", true)
    refused("window_initiator_changed", changed, changed.submit(1, TOP_ID, ST, FF), canon(changed), "window_initiator_changed")


# --- Windows, clock and PASS ----------------------------------------------------------------------

func _test_window_lifecycle() -> void:
    var state := position(entry("top", 100, 100, false, 300, 10, 41))
    var opened := state.open_window()
    check("first window continues from the entry id", opened.values, {"status": "opened", "window_id": 42, "initiator": "top", "elapsed_seconds": 10, "clock_seconds": 290})
    for bad: Array in [["5", "invalid_duration"], [5.0, "invalid_duration"], [true, "invalid_duration"], [[], "invalid_duration"]]:
        var fresh_state := position()
        refused("open_window(%s)" % JSON.stringify(bad[0]), fresh_state, fresh_state.open_window(bad[0]), canon(fresh_state), bad[1])
    var negative := position()
    refused("negative duration", negative, negative.open_window(-1), canon(negative), "invalid_window_request")
    refused("second open", state, state.open_window(), canon(state), "window_already_open")
    var zero := position()
    check("a zero-time window is legal and spends no clock", zero.open_window(0).values, {"status": "opened", "window_id": 1, "initiator": "top", "elapsed_seconds": 0, "clock_seconds": 300})
    var interval := position(entry("top", 100, 100, false, 300, 7))
    check("null means the interval", interval.open_window(null).values["elapsed_seconds"], 7)
    # Window ids are strictly monotonic through exchanges and passes.
    var ids := position()
    var seen: Array = []
    for step in range(4):
        var window := ids.open_window()
        seen.append(window.values["window_id"])
        ids.submit(window.values["window_id"], ids.fighter_id(ids.initiator), "", "")
    check("ids 1..4", seen, [1, 2, 3, 4])
    # Timeout at the exact boundary never opens a window or advances the id; it is terminal and not an exit.
    var timeout := position(entry("top", 100, 100, false, 10, 10))
    check("timeout report", timeout.open_window().values, {"status": "closed", "window_id": 0, "initiator": "", "elapsed_seconds": 10, "clock_seconds": 0})
    check("timeout reason (em dash)", timeout.exit_reason, "TIMEOUT — Side Control retained")
    check("timeout is not an exit", timeout.exit_destination, "")
    check("timeout is ended", timeout.is_ended(), true)
    refused("attempt after timeout", timeout, timeout.attempt(ST, FF), canon(timeout), "terminal_exchange")
    refused("open_window after timeout", timeout, timeout.open_window(), canon(timeout), "terminal_exchange")
    refused("submit after timeout", timeout, timeout.submit(0, TOP_ID, ST, FF), canon(timeout), "no_open_window")
    var clamp := position(entry("top", 100, 100, false, 300, 10))
    check("a duration beyond the clock clamps to it and times out", clamp.open_window(1000).values, {"status": "closed", "window_id": 0, "initiator": "", "elapsed_seconds": 300, "clock_seconds": 0})
    var one_second := entry("top", 100, 100, false, 300, 10)
    one_second["clock"]["remaining_seconds"] = 1
    check("a one-second remainder still times out normally", position(one_second).open_window().values["status"], "closed")


# open_window checks, in order: an open window, the context, then the duration. Every refusal leaves the snapshot byte-identical.
func _test_open_window_precedence() -> void:
    var bad_durations: Array = ["5", 5.0, true, -1]
    var corruptions: Array = [
        ["invalid_stamina_state", func(s: Dictionary) -> void: s["fighters"][TOP_ID]["stamina_current"] = 150],
        ["invalid_initiator", func(s: Dictionary) -> void: s["initiator"] = "nobody"],
        ["terminal_exchange", func(s: Dictionary) -> void: s["exit_destination"] = "Mount"],
        ["invalid_side_control_context", func(s: Dictionary) -> void: s["axis_tenths"] = 41],
    ]
    for bad: Variant in bad_durations:
        for corruption: Array in corruptions:
            var corrupted := _corrupt(corruption[1])
            refused("context beats a bad duration %s (%s)" % [JSON.stringify(bad), corruption[0]], corrupted, corrupted.open_window(bad), canon(corrupted), corruption[0])
        var open := _submit_state()
        refused("an open window beats a bad duration %s" % JSON.stringify(bad), open, open.open_window(bad), canon(open), "window_already_open")


func _test_window_id_ceiling() -> void:
    # SPEC GAP (reported, not fixed): the sheet bounds the entry's last issued id at 2^53-1 but is silent on what happens when a window then
    # opens past it. This pins today's behavior, which equals the oracle's: the window opens with id 2^53, after which submit fails the context
    # check and every other command sees an open window, so the position cannot recover. A later sheet revision must rule on it.
    var state := position(entry("top", 100, 100, false, 300, 10, 9007199254740991))
    check("the entry at the maximum id is valid", state.snapshot()["window_id"], 9007199254740991)
    check("the next window opens past the maximum", state.open_window().values["window_id"], 9007199254740992)
    var before := canon(state)
    refused("submit past the ceiling", state, state.submit(9007199254740992, TOP_ID, ST, FF), before, "invalid_side_control_context")
    refused("attempt past the ceiling", state, state.attempt(ST, FF), before, "window_already_open")
    refused("open_window past the ceiling", state, state.open_window(), before, "window_already_open")


func _test_pass() -> void:
    var state := position()
    state.open_window()
    var before_stamina := JSON.stringify([state.top.record(), state.bottom.record()], "", true, true)
    var passed := state.submit(1, TOP_ID, "", "", "", "")
    check("pass accepted", passed.ok(), true)
    check("pass record is its own kind with the stable fighter id", passed.values, {"kind": "pass",
        "record": {"kind": "pass", "window_id": 1, "fighter_id": TOP_ID, "role": "top"}, "transition": {"kind": "none", "raw_destination": "",
        "destination_position_id": "", "resolved": false}})
    check("pass costs nothing", JSON.stringify([state.top.record(), state.bottom.record()], "", true, true), before_stamina)
    check("pass flips initiative", state.initiator, "bottom")
    check("pass leaves axis, band, tiers and clock", [state.axis_tenths, state.band, state.top_pin, state.bottom_space, state.clock_seconds], [10, 1, 1, 1, 290])
    check("pass closes the window", [state.window_open, state.window_initiator], [false, ""])
    check("a pass is one history record and no more", state.decision_history, [{"kind": "pass", "window_id": 1, "fighter_id": TOP_ID, "role": "top"}])
    # Either role may pass when it is the initiator.
    state.open_window()
    check("bottom passes", state.submit(2, BOTTOM_ID, "", "").ok(), true)
    check("back to top", state.initiator, "top")
    check("bottom pass record", (state.decision_history[1] as Dictionary)["role"], "bottom")
    # A pass is never a way to freeze simulated time: two passing fighters still run the match to the clock.
    var idle := position(entry("top", 100, 100, false, 100, 10))
    var windows := 0
    while true:
        var window := idle.open_window()
        if window.values["status"] == "closed":
            break
        windows += 1
        check("pass ok %d" % windows, idle.submit(window.values["window_id"], idle.fighter_id(idle.initiator), "", "").ok(), true)
        if windows > 50:
            break
    check("ten windows then the clock ends the match", [windows, idle.is_ended(), idle.exit_destination], [9, true, ""])
    check("the position owns no inactivity, stalling, Momentum or Heart of a Lion state", idle.snapshot().keys().size(), 17)
    # A pass carrying a commitment, a response, or sent through attempt is refused and changes nothing.
    var other := position()
    other.open_window()
    var before := canon(other)
    refused("pass with a commitment", other, other.submit(1, TOP_ID, "", "", "LOW", ""), before, "commitment_without_action")
    refused("pass with a response commitment", other, other.submit(1, TOP_ID, "", "", "", "HIGH"), before, "commitment_without_action")
    refused("pass with a response", other, other.submit(1, TOP_ID, "", FF), before, "response_without_action")
    var attempt_pass := position()
    refused("attempt cannot pass", attempt_pass, attempt_pass.attempt("", ""), canon(attempt_pass), "unknown_action")


# --- Grade pipeline and settlement (literals) ----------------------------------------------------

func _test_worked_examples() -> void:
    # Example 1: plain exchange.
    var one := at()
    var record := record_of(one.attempt(AM, FF, "MEDIUM", "MEDIUM"))
    check("example 1 record", record, {"kind": "exchange", "window_id": 0, "fighter_id": TOP_ID, "role": "top", "responder_id": BOTTOM_ID,
        "action_id": AM, "response_id": FF, "commitment_requested": "MEDIUM", "response_commitment_requested": "MEDIUM",
        "initiator_effective": "MEDIUM", "responder_effective": "MEDIUM", "initiator_charged": 7, "responder_charged": 7, "responder_waived": 0,
        "raw_grade": 1, "final_grade": 1, "axis_before": 10, "axis_after": 20, "band_before": 1, "band_after": 1, "exit_destination": "",
        "readiness_changes": []})
    check("example 1 state", [one.axis_tenths, one.band, one.initiator, one.top.current, one.bottom.current, one.top_pin, one.bottom_space],
        [20, 1, "bottom", 93, 93, 1, 1])
    # Example 2: exit with a Ready track, HIGH vs MEDIUM.
    var two := at("top", 20, 1, 2, 1)
    var two_result := two.attempt(AM, BD, "HIGH", "MEDIUM")
    check("example 2 record", subset(record_of(two_result), ["raw_grade", "final_grade", "axis_after", "band_after", "exit_destination", "initiator_charged",
        "responder_charged", "readiness_changes"]), {"raw_grade": 1, "final_grade": 2, "axis_after": 40, "band_after": 2, "exit_destination": "Mount",
        "initiator_charged": 12, "responder_charged": 7, "readiness_changes": [{"track": "top_pin", "before": 2, "after": 1, "cause": "consume"}]})
    check("example 2 transition", two_result.values["transition"], {"kind": "exit", "raw_destination": "Mount", "destination_position_id": "mount", "resolved": true})
    check("example 2 exit reason", two.exit_reason, "Advance to Mount reached the advance line with final grade Strong Success")
    check("example 2 initiative stays on an exit", two.initiator, "top")
    # Example 3: defense readiness against a None track.
    var three := at("top", 10, 1, 1, 0)
    var three_record := record_of(three.attempt(AM, HE, "MEDIUM", "MEDIUM"))
    check("example 3", subset(three_record, ["raw_grade", "final_grade", "axis_after", "readiness_changes"]), {"raw_grade": -2, "final_grade": 0, "axis_after": 10, "readiness_changes": []})
    # Example 4: an unfunded, Exhausted Bottom initiator (Rule 1 waives the response cost).
    var four := position(entry("bottom", 100, 2))
    var four_record := record_of(four.attempt(TK, SP, "MEDIUM", "MEDIUM"))
    check("example 4", subset(four_record, ["raw_grade", "final_grade", "axis_after", "initiator_effective", "responder_effective", "initiator_charged",
        "responder_charged", "responder_waived", "readiness_changes"]), {"raw_grade": 0, "final_grade": -1, "axis_after": 20, "initiator_effective": "",
        "responder_effective": "MEDIUM", "initiator_charged": 0, "responder_charged": 0, "responder_waived": 7, "readiness_changes": []})
    check("example 4 state", [four.top.current, four.bottom.current, four.bottom.latched, four.initiator], [100, 2, true, "top"])


func _cell(initiator: String, axis: int, band_value: int, pin: int, space: int, action: String, response: String, commitment: String = "MEDIUM",
        response_commitment: String = "MEDIUM", top_current: int = 100, bottom_current: int = 100) -> Array:
    var state := at(initiator, axis, band_value, pin, space, top_current, bottom_current)
    var record := record_of(state.attempt(action, response, commitment, response_commitment))
    return [record, state]


func _test_grade_pipeline_literals() -> void:
    # Positional modifier: an initiator facing the opposing CONTROL band acts uphill (-1).
    var top_uphill := _cell("top", -30, -2, 1, 1, ST, HE)
    check("Top against Bottom CONTROL", subset(top_uphill[0], ["raw_grade", "final_grade", "axis_after", "band_after"]), {"raw_grade": 1, "final_grade": 0, "axis_after": -30, "band_after": -2})
    var bottom_uphill := _cell("bottom", 40, 2, 1, 1, SH, HB)
    check("Bottom against Top CONTROL", subset(bottom_uphill[0], ["raw_grade", "final_grade", "axis_after", "band_after"]), {"raw_grade": 1, "final_grade": 0, "axis_after": 40, "band_after": 2})
    # Exhaustion: -1 for an Exhausted initiator, +1 for an Exhausted responder, from the bands captured BEFORE the charge.
    var weary := _cell("top", 10, 1, 1, 1, ST, BD, "MEDIUM", "MEDIUM", 20, 100)
    check("Exhausted initiator", subset(weary[0], ["final_grade", "axis_after", "band_after", "initiator_charged"]), {"final_grade": -1, "axis_after": 0, "band_after": 0, "initiator_charged": 7})
    check("the latch survives the charge", [(weary[1] as BjjSideControlMatch).top.current, (weary[1] as BjjSideControlMatch).top.latched], [13, true])
    var pressed := _cell("top", 10, 1, 1, 1, ST, BD, "MEDIUM", "MEDIUM", 100, 20)
    check("Exhausted responder", subset(pressed[0], ["final_grade", "axis_after", "readiness_changes"]),
        {"final_grade": 1, "axis_after": 20, "readiness_changes": [{"track": "top_pin", "before": 1, "after": 2, "cause": "build"}]})
    # Magnitude: HIGH presses a Success; LOW softens a Strong Success that would otherwise have reached the exit line.
    var press := _cell("top", 10, 1, 1, 1, ST, HE, "HIGH", "MEDIUM")
    check("HIGH presses Success and undercommitment adds one", subset(press[0], ["raw_grade", "final_grade", "axis_after", "band_after", "initiator_charged", "responder_charged",
        "exit_destination"]), {"raw_grade": 1, "final_grade": 2, "axis_after": 30, "band_after": 2, "initiator_charged": 12, "responder_charged": 7, "exit_destination": ""})
    var soft := _cell("top", 10, 1, 2, 1, AM, FF, "LOW", "MEDIUM")
    check("LOW softens a Strong Success", subset(soft[0], ["final_grade", "axis_after", "exit_destination", "initiator_charged", "responder_charged", "readiness_changes"]),
        {"final_grade": 1, "axis_after": 20, "exit_destination": "", "initiator_charged": 3, "responder_charged": 7,
        "readiness_changes": [{"track": "top_pin", "before": 2, "after": 1, "cause": "consume"}]})
    # Defense readiness: a Ready, MEDIUM defense shifts -1; a LOW defense is token resistance (tier None) whatever its track.
    var ready := _cell("top", 10, 1, 1, 2, AM, HE)
    check("Ready defense", subset(ready[0], ["raw_grade", "final_grade", "axis_after", "band_after", "readiness_changes"]), {"raw_grade": -2, "final_grade": -2, "axis_after": -10, "band_after": 0,
        "readiness_changes": [{"track": "bottom_space", "before": 2, "after": 1, "cause": "wear"}]})
    var token := _cell("top", 10, 1, 1, 2, AM, HE, "MEDIUM", "LOW")
    # raw -2, attack 0, defense tier None +2 -> 0, then undercommitment (LOW rank 1 < MEDIUM rank 2) +1 -> Success; a LOW defense never wears.
    check("a LOW defense is evaluated as tier None", subset(token[0], ["final_grade", "responder_charged", "readiness_changes"]), {"final_grade": 1, "responder_charged": 3, "readiness_changes": []})
    # An exchange by a Bottom initiator moves the axis the other way.
    var shrimp := _cell("bottom", 10, 1, 1, 1, SH, HB)
    check("Shrimp vs Hip Block", subset(shrimp[0], ["raw_grade", "final_grade", "axis_after", "band_after", "readiness_changes"]), {"raw_grade": 1, "final_grade": 1, "axis_after": 0, "band_after": 0,
        "readiness_changes": [{"track": "top_pin", "before": 1, "after": 0, "cause": "wear"}, {"track": "bottom_space", "before": 1, "after": 2, "cause": "build"}]})
    # The grade is decided from the pre-exchange state, not from the charge it causes: a fighter at the funding boundary still grades at
    # its pre-charge band (30 -> 23 would be Exhausted AFTER the charge, but the grade used Working/Tired).
    var boundary := _cell("top", 10, 1, 1, 1, ST, BD, "MEDIUM", "MEDIUM", 32, 100)
    check("the charge cannot change its own exchange's grade", [boundary[0]["final_grade"], (boundary[1] as BjjSideControlMatch).top.latched], [0, true])
    # A between-thresholds fighter that is NOT latched grades as Tired (not Exhausted) and only latches after the charge (30 -> 23 <= 25).
    var unlatched_request := entry()
    unlatched_request["fighters"][TOP_ID] = {"stamina_current": 30, "stamina_maximum": 100, "exhaustion_latched": false, "behavior_remainder_units": 0}
    var unlatched := position(unlatched_request)
    check("unlatched 30 is not Exhausted", record_of(unlatched.attempt(ST, BD))["final_grade"], 0)
    check("and latches only after the charge", [unlatched.top.current, unlatched.top.latched], [23, true])
    # Non-break techniques at the CONTROL bands, near the clamp (oracle-verified literals).
    var stab_control := _cell("top", 40, 2, 1, 1, ST, HE)
    check("Stabilize at +40 builds without moving the axis", subset(stab_control[0], ["final_grade", "axis_after", "band_after", "readiness_changes"]), {"final_grade": 1,
        "axis_after": 40, "band_after": 2, "readiness_changes": [{"track": "bottom_space", "before": 1, "after": 0, "cause": "wear"}, {"track": "top_pin", "before": 1, "after": 2, "cause": "build"}]})
    var shrimp_control := _cell("bottom", -40, -2, 1, 1, SH, FH, "HIGH", "MEDIUM")
    check("Shrimp HIGH at -40", subset(shrimp_control[0], ["raw_grade", "final_grade", "axis_after", "band_after", "initiator_charged", "readiness_changes"]), {"raw_grade": 0,
        "final_grade": 1, "axis_after": -40, "band_after": -2, "initiator_charged": 12, "readiness_changes": [{"track": "bottom_space", "before": 1, "after": 2, "cause": "build"}]})
    var stab_low := _cell("top", 40, 2, 1, 1, ST, FF, "LOW", "MEDIUM")
    check("Stabilize LOW at +40 failing", subset(stab_low[0], ["final_grade", "axis_after", "band_after", "initiator_charged"]), {"final_grade": -1, "axis_after": 30, "band_after": 2, "initiator_charged": 3})
    # Authority is reported from the axis sign by role, and follows the fighter id under a swapped role map.
    var swapped := position(entry("top", 100, 100, true))
    check("authority at +10 is the Top fighter's id (fighter_b here)", swapped.authority_id(), BOTTOM_ID)
    swapped.axis_tenths = -10
    swapped.band = -1
    check("authority at -10 is the Bottom fighter's id", swapped.authority_id(), TOP_ID)
    swapped.axis_tenths = 0
    swapped.band = 0
    check("authority at 0 is nobody", swapped.authority_id(), "")


func _test_readiness_and_wear() -> void:
    # A break-capable attempt at Ready spends one tier whatever the result; non-break techniques never consume.
    var consumed := _cell("top", 10, 1, 2, 1, AM, HE)
    # Consume (initiator's Ready track) then wear (the MEDIUM hip_escape lost a decided exchange), in that fixed order.
    check("consume on a failure", consumed[0]["readiness_changes"], [{"track": "top_pin", "before": 2, "after": 1, "cause": "consume"},
        {"track": "bottom_space", "before": 1, "after": 0, "cause": "wear"}])
    var plain := _cell("top", 10, 1, 2, 1, ST, FF)
    check("Stabilize never consumes", plain[0]["readiness_changes"], [])
    # Tiers saturate at the floor and ceiling without recording a change.
    var floor_state := _cell("top", 10, 1, 1, 0, AM, HE)
    check("no wear below None", floor_state[0]["readiness_changes"], [])
    var ceiling := _cell("top", 10, 1, 2, 1, ST, BD)  # Stabilize vs Bridge: raw 0, a Contested result builds nothing
    check("a Contested result builds nothing", ceiling[0]["readiness_changes"], [])
    var capped := _cell("top", 10, 1, 2, 1, ST, HE)  # raw +1 -> Success: build would exceed Ready, hip_escape wears the Bottom track
    check("a Success wears the governed defense and cannot build past Ready",
        capped[0]["readiness_changes"], [{"track": "bottom_space", "before": 1, "after": 0, "cause": "wear"}])
    check("top_pin stays at Ready", (capped[1] as BjjSideControlMatch).top_pin, 2)
    # A Contested result wears nothing, even on a governed defense.
    var contested := _cell("top", 10, 1, 1, 1, ST, BD)
    check("contested wears nothing", contested[0]["readiness_changes"], [])


func _test_rule_one_and_paid_effort() -> void:
    # A paid HIGH defense is preserved on a result that did not fail it; an unpaid (waived) HIGH defense wears like MEDIUM.
    var paid := _cell("top", 10, 1, 1, 2, AM, HE, "MEDIUM", "HIGH")
    check("paid HIGH defense preserved", subset(paid[0], ["final_grade", "initiator_charged", "responder_charged", "responder_waived", "readiness_changes"]),
        {"final_grade": -2, "initiator_charged": 7, "responder_charged": 12, "responder_waived": 0, "readiness_changes": []})
    var waived := _cell("top", 10, 1, 1, 2, AM, HE, "MEDIUM", "HIGH", 2, 100)
    check("an unfunded initiator waives the response cost", subset(waived[0], ["initiator_effective", "responder_effective", "final_grade", "initiator_charged", "responder_charged",
        "responder_waived", "axis_after", "readiness_changes"]), {"initiator_effective": "", "responder_effective": "HIGH", "final_grade": -1, "initiator_charged": 0,
        "responder_charged": 0, "responder_waived": 12, "axis_after": 0, "readiness_changes": [{"track": "bottom_space", "before": 2, "after": 1, "cause": "wear"}]})
    check("the waived fighter keeps its stamina", (waived[1] as BjjSideControlMatch).bottom.current, 100)
    # An exchange by an unfunded initiator is legal (R-10).
    check("the unfunded initiator is still charged nothing and still flips initiative", [(waived[1] as BjjSideControlMatch).top.current, (waived[1] as BjjSideControlMatch).initiator], [2, "bottom"])
    # Partial funding downgrades without a shortfall; empty commitments default to MEDIUM.
    var partial := _cell("top", 10, 1, 1, 1, ST, FF, "HIGH", "HIGH", 8, 100)
    check("HIGH requested with 8 stamina is funded MEDIUM and charged 7", subset(partial[0], ["initiator_effective", "initiator_charged"]), {"initiator_effective": "MEDIUM", "initiator_charged": 7})
    var defaults := position()
    var default_record := record_of(defaults.attempt(ST, FF, "", ""))
    check("empty commitments default to MEDIUM", subset(default_record, ["commitment_requested", "response_commitment_requested", "initiator_charged", "responder_charged"]),
        {"commitment_requested": "MEDIUM", "response_commitment_requested": "MEDIUM", "initiator_charged": 7, "responder_charged": 7})


func _test_exits_and_terminal_states() -> void:
    var exits: Array = [
        ["top", 20, 1, EB, FF, "Back Control", "back_control", 30, 2, "Expose Back reached the advance line with final grade Success", "top"],
        ["bottom", -20, -1, RH, SP, "Half Guard", "half_guard", -40, -2, "Recover Half Guard reached the escape line with final grade Strong Success", "bottom"],
        ["bottom", -20, -1, TK, HB, "Turtle", "turtle", -40, -2, "Turn to Knees reached the escape line with final grade Strong Success", "bottom"],
    ]
    for row: Array in exits:
        var cell := _cell(row[0], row[1], row[2], 1, 1, row[3], row[4])
        var state: BjjSideControlMatch = cell[1]
        check("exit %s" % row[5], [cell[0]["exit_destination"], state.exit_destination, state.axis_tenths, state.band, state.exit_reason, state.initiator],
            [row[5], row[5], row[7], row[8], row[9], row[10]])
        check("exit transition %s" % row[5], BjjSideControlCatalog.transition_fields(state.exit_destination),
            {"kind": "exit", "raw_destination": row[5], "destination_position_id": row[6], "resolved": true})
        # An exit is terminal: every command is refused before any tier is read, and no successor, window or time is granted.
        check("ended", state.is_ended(), true)
        var before := canon(state)
        refused("attempt after exit", state, state.attempt(row[3], row[4]), before, "terminal_exchange")
        refused("open_window after exit", state, state.open_window(), before, "terminal_exchange")
        refused("submit after exit", state, state.submit(0, TOP_ID, "", ""), before, "no_open_window")
        check("the clock is untouched by an exit", state.clock_seconds, 300)
    # The line is inclusive and needs a Success; a Top at axis 19 reaches 29 and stays.
    var short := _cell("top", 19, 1, 1, 1, AM, FF)
    check("axis 29 does not exit", [short[0]["exit_destination"], short[0]["axis_after"], short[0]["band_after"]], ["", 29, 2])
    var inclusive := _cell("top", 20, 1, 1, 1, AM, FF)
    check("axis 30 exits", inclusive[0]["exit_destination"], "Mount")
    # Non-break techniques never exit, even across the line: Stabilize HIGH from axis 20 proposes 40 and just clamps.
    var crossing := _cell("top", 20, 1, 1, 1, ST, HE, "HIGH", "MEDIUM")
    check("Stabilize across the line does not exit", [crossing[0]["exit_destination"], crossing[0]["axis_after"], crossing[0]["band_after"], (crossing[1] as BjjSideControlMatch).is_ended()],
        ["", 40, 2, false])
    check("and initiative flips", (crossing[1] as BjjSideControlMatch).initiator, "bottom")
    # The axis clamps at the limits without an exit.
    var clamped := _cell("top", 40, 2, 1, 1, ST, FF, "MEDIUM", "MEDIUM")
    check("a failed Stabilize at +40 steps down by one", clamped[0]["axis_after"], 30)
    var floor_clamp := _cell("bottom", -40, -2, 1, 1, SH, SP)
    check("a failed Shrimp at -40 steps up by one", floor_clamp[0]["axis_after"], -30)
    check("the Reversal landing is unresolved and unlabelled", BjjSideControlCatalog.EXIT_DESTINATIONS.has("Reversal"), false)
    check("a label outside the four is not resolved", BjjSideControlCatalog.transition_fields("Reversal"), {"kind": "exit", "raw_destination": "Reversal", "destination_position_id": "", "resolved": false})


# --- Tables ---------------------------------------------------------------------------------------

func _test_rules_tables_and_bands() -> void:
    var literal: Array = [[12, 0, 1], [11, 0, 0], [27, 1, 2], [26, 1, 1], [8, 1, 0], [9, 1, 1], [23, 2, 1], [24, 2, 2], [-8, -1, 0], [-9, -1, -1],
        [-23, -2, -1], [-24, -2, -2], [-12, 0, -1], [-11, 0, 0], [-27, -1, -2], [-26, -1, -1], [40, 0, 2], [-40, 0, -2], [10, 1, 1], [0, 2, 0]]
    for row: Array in literal:
        check("band_update(%d, %d)" % [row[0], row[1]], BjjSideControlRules.band_update(row[0], row[1]), row[2])
    var legal := 0
    for axis in range(-40, 41):
        for from_band in [-2, -1, 0, 1, 2]:
            var target := BjjSideControlRules.band_update(axis, from_band)
            check("band_update(%d,%d) lands on a legal pair" % [axis, from_band], BjjSideControlRules.legal_pair(axis, target), true)
            check("band_update is idempotent at (%d,%d)" % [axis, from_band], BjjSideControlRules.band_update(axis, target), target)
            if BjjSideControlRules.legal_pair(axis, from_band):
                legal += 1
                check("a legal pair is a fixed point (%d,%d)" % [axis, from_band], target, from_band)
    check("number of legal (axis, band) pairs over -40..40", legal, 23 + 18 + 17 + 18 + 17)  # bands 0, +1, +2, -1, -2
    check("the entry pair is legal", BjjSideControlRules.legal_pair(10, 1), true)
    check("an unknown band is never legal", BjjSideControlRules.legal_pair(10, 3), false)
    check("authority follows the axis sign only", [BjjSideControlRules.authority_id(10, "t", "b"), BjjSideControlRules.authority_id(-10, "t", "b"), BjjSideControlRules.authority_id(0, "t", "b")], ["t", "b", ""])
    check("constants", [BjjSideControlRules.AXIS_MIN, BjjSideControlRules.AXIS_MAX, BjjSideControlRules.ENTRY_AXIS, BjjSideControlRules.ENTRY_BAND, BjjSideControlRules.STEP_TENTHS,
        BjjSideControlRules.EXIT_LINE], [-40, 40, 10, 1, 10, 30])


func _test_catalog() -> void:
    check("twelve catalog ids", BjjSideControlCatalog.ENTITIES.size(), 12)
    var actions := 0
    var responses := 0
    for id: String in BjjSideControlCatalog.ENTITIES:
        if BjjSideControlCatalog.is_action(id):
            actions += 1
            check("every action has a full row of responses %s" % id, (BjjSideControlCatalog.RAW[id] as Dictionary).size(), 3)
        else:
            responses += 1
    check("six actions and six responses", [actions, responses], [6, 6])
    check("break-capable techniques", [BjjSideControlCatalog.is_break_capable(ST), BjjSideControlCatalog.is_break_capable(AM), BjjSideControlCatalog.is_break_capable(EB),
        BjjSideControlCatalog.is_break_capable(SH), BjjSideControlCatalog.is_break_capable(RH), BjjSideControlCatalog.is_break_capable(TK)], [false, true, true, false, true, true])
    check("every response and a reserved id is not an action", [BjjSideControlCatalog.is_action(FF), BjjSideControlCatalog.is_action("side_control.top.kimura_route"),
        BjjSideControlCatalog.is_response(AM), BjjSideControlCatalog.is_response("")], [false, false, false, false])
    check("the four declared exits", BjjSideControlCatalog.EXIT_DESTINATIONS, {"Mount": "mount", "Back Control": "back_control", "Half Guard": "half_guard", "Turtle": "turtle"})
    check("sample raw cells", [BjjSideControlCatalog.RAW[ST][FF], BjjSideControlCatalog.RAW[AM][HE], BjjSideControlCatalog.RAW[EB][BD], BjjSideControlCatalog.RAW[RH][SP],
        BjjSideControlCatalog.RAW[TK][HB], BjjSideControlCatalog.RAW[TK][FH]], [-1, -2, -2, 2, 2, -2])
    check("no transition for a non-exit", BjjSideControlCatalog.transition_fields(""), {"kind": "none", "raw_destination": "", "destination_position_id": "", "resolved": false})
    # Each response holds one action and loses to another (no dominated response): the structural property the proposal checks.
    for row: Array in [[[ST, AM, EB], [FF, HE, BD]], [[SH, RH, TK], [SP, HB, FH]]]:
        for response: String in row[1]:
            var best := -9
            var worst := 9
            for action: String in row[0]:
                best = maxi(best, int(BjjSideControlCatalog.RAW[action][response]))
                worst = mini(worst, int(BjjSideControlCatalog.RAW[action][response]))
            check("response %s is neither dominant nor useless for the initiator" % response, best > worst, true)


# --- Views, determinism, scope ---------------------------------------------------------------------

func _test_views_are_detached() -> void:
    var state := position()
    var request := entry()
    var before_request := JSON.stringify(request, "", true, true)
    var built := BjjSideControlMatch.from_entry(request).match_state
    check("building from a request never touches it", JSON.stringify(request, "", true, true), before_request)
    request["fighters"][TOP_ID]["stamina_current"] = 1
    check("a request is copied, never aliased", built.snapshot()["fighters"][TOP_ID]["stamina_current"], 100)
    var snapshot := state.snapshot()
    snapshot["axis_tenths"] = 40
    snapshot["fighters"][TOP_ID]["stamina_current"] = 0
    (snapshot["decision_history"] as Array).append("x")
    check("mutating a snapshot never affects the position", [state.axis_tenths, state.top.current, state.decision_history.size()], [10, 100, 0])
    var result := state.attempt(ST, FF)
    var record: Dictionary = result.values["record"]
    record["final_grade"] = 99
    (record["readiness_changes"] as Array).append("x")
    check("mutating a result never affects the history", (state.decision_history[0] as Dictionary)["final_grade"], -1)  # Stabilize vs Forearm Frame
    var restored := BjjSideControlMatch.from_snapshot(state.snapshot()).match_state
    var raw := state.snapshot()
    (raw["decision_history"] as Array).clear()
    check("a restored position owns its history", restored.decision_history.size(), 1)
    check("a snapshot round trip is exact", canon(restored), canon(state))


func _run_script(state: BjjSideControlMatch) -> String:
    var log: Array = []
    for step in range(30):
        var window := state.open_window()
        log.append(window.values if window.ok() else {"error": window.error})
        if not window.ok() or window.values["status"] == "closed":
            break
        var role := state.initiator
        var actions: Array = [[AM, BD, "HIGH", "MEDIUM"], [EB, FF, "MEDIUM", "LOW"], [ST, HE, "LOW", "HIGH"]] if role == "top" else [[RH, SP, "MEDIUM", "MEDIUM"], [SH, HB, "HIGH", "MEDIUM"], [TK, FH, "LOW", "LOW"]]
        var pick: Array = actions[step % 3]
        var result := state.submit(window.values["window_id"], state.fighter_id(role), "" if step % 7 == 6 else pick[0], "" if step % 7 == 6 else pick[1],
            "" if step % 7 == 6 else pick[2], "" if step % 7 == 6 else pick[3])
        log.append(result.values if result.ok() else {"error": result.error})
    log.append(state.snapshot())
    return JSON.stringify(log, "", true, true)


func _test_determinism() -> void:
    for request: Dictionary in [entry(), entry("bottom", 60, 30, true, 90, 4), entry("top", 8, 100)]:
        var first := _run_script(position(request))
        var second := _run_script(position(request))
        check("the same entry and the same operations reproduce the same bytes", first, second)
        check("the run did something", first.length() > 400, true)


func _test_scope_and_hygiene() -> void:
    # The engine is standalone and deterministic: no other position, graph, gateway, clock, randomness, I/O or frame loop.
    var forbidden: Array[String] = ["BjjMount", "BjjHalfGuard", "BjjD3B", "BjjPositionGraph", "BjjPositionRegistry", "BjjMatchWindowGateway", "BjjBehaviorStaminaPolicy",
        "sealed", "randi", "randf", "RandomNumberGenerator", "Time.", "OS.get_", "await", "get_tree", "Engine.get_frames", "FileAccess", "preload(", "_process", "@export", "assert("]
    for path: String in SOURCES:
        var file := FileAccess.open(path, FileAccess.READ)
        check("source readable %s" % path, file != null, true)
        var code_lines: Array[String] = []
        for source_line: String in file.get_as_text().split("\n"):
            code_lines.append(source_line.split("#")[0])  # comments may name what the code must not use
        var text := "\n".join(code_lines)
        for token: String in forbidden:
            check("%s has no %s" % [path, token], text.contains(token), false)
