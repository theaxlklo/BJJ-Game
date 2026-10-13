extends SceneTree

# Replays the independent Python Side Control v0 oracle fixture (tests/oracles/side_control_v0.py, written from
# SIDE_CONTROL_V0_RULES.md, never from this GDScript) through the typed GDScript engine. Expectations are read from the generated
# fixture and are never produced by Godot. Families: band update, entry validation, the exchange and break grids and the command /
# context refusals (all rebuilt from full snapshots) and multi-operation window trajectories (replayed twice).
# Generate the fixture first: python GODOT_V1/tests/generate_side_control_reference.py
const FIXTURE: String = "res://tests/generated/side_control_reference.jsonl"

var checks: int = 0
var failures: int = 0
var rows: int = 0
var operations: int = 0
var leaves: int = 0
var families: Dictionary = {}


func check(label: String, actual: Variant, expected: Variant) -> void:
    checks += 1
    if not _same(actual, expected):
        failures += 1
        if failures <= 25:
            push_error("%s: first difference at %s" % [label, _first_difference(actual, expected, "$")])


# Numeric comparison (JSON has one number type); bool, null, string, array and dictionary comparison are strict.
func _same(actual: Variant, expected: Variant) -> bool:
    var a := typeof(actual)
    var e := typeof(expected)
    var numeric_a := a == TYPE_INT or a == TYPE_FLOAT
    var numeric_e := e == TYPE_INT or e == TYPE_FLOAT
    if numeric_a and numeric_e:
        leaves += 1
        # Every number the oracle emits is an integer (JSON just cannot say so): an engine returning 20.0 for 20 would serialize
        # differently, so an integral expectation demands a real int. Only a genuinely fractional expectation is compared as a float.
        if e == TYPE_INT or (float(expected) == floorf(float(expected)) and absf(float(expected)) <= 9007199254740992.0):
            return a == TYPE_INT and float(actual) == float(expected)
        return absf(float(actual) - float(expected)) < 1e-9
    if a != e:
        return false
    if a == TYPE_DICTIONARY:
        var da: Dictionary = actual
        var de: Dictionary = expected
        if da.size() != de.size():
            return false
        for key: Variant in de:
            if not da.has(key) or not _same(da[key], de[key]):
                return false
        return true
    if a == TYPE_ARRAY:
        var aa: Array = actual
        var ae: Array = expected
        if aa.size() != ae.size():
            return false
        for i in range(aa.size()):
            if not _same(aa[i], ae[i]):
                return false
        return true
    leaves += 1
    return actual == expected


func _first_difference(actual: Variant, expected: Variant, path: String) -> String:
    if _same(actual, expected):
        return ""
    var a := typeof(actual)
    if a == TYPE_DICTIONARY and typeof(expected) == TYPE_DICTIONARY:
        for key: Variant in expected:
            if not actual.has(key):
                return "%s.%s missing (expected %s)" % [path, key, JSON.stringify(expected[key])]
            var inner := _first_difference(actual[key], expected[key], "%s.%s" % [path, key])
            if not inner.is_empty():
                return inner
        for key: Variant in actual:
            if not expected.has(key):
                return "%s.%s unexpected (got %s)" % [path, key, JSON.stringify(actual[key])]
    elif a == TYPE_ARRAY and typeof(expected) == TYPE_ARRAY:
        for i in range(mini(actual.size(), expected.size())):
            var element := _first_difference(actual[i], expected[i], "%s[%d]" % [path, i])
            if not element.is_empty():
                return element
        return "%s length %d expected %d" % [path, actual.size(), expected.size()]
    return "%s got %s expected %s" % [path, JSON.stringify(actual), JSON.stringify(expected)]


# Inputs: {"$float": x} is a float (to be refused); every other integral JSON number is an integer.
func _decode(value: Variant) -> Variant:
    match typeof(value):
        TYPE_DICTIONARY:
            var dictionary: Dictionary = value
            if dictionary.size() == 1 and dictionary.has("$float"):
                return float(dictionary["$float"])
            var out := {}
            for key: Variant in dictionary:
                out[key] = _decode(dictionary[key])
            return out
        TYPE_ARRAY:
            var out_array: Array = []
            for item: Variant in value:
                out_array.append(_decode(item))
            return out_array
        TYPE_FLOAT:
            var number: float = value
            if number == floorf(number) and absf(number) <= 9007199254740992.0:
                return int(number)
            return number
    return value


func _initialize() -> void:
    var fixture := FileAccess.open(FIXTURE, FileAccess.READ)
    if fixture == null:
        push_error("Generate the Side Control Python oracle fixture first")
        quit(1)
        return
    while not fixture.eof_reached():
        var line := fixture.get_line()
        if line.is_empty():
            continue
        var row: Dictionary = JSON.parse_string(line)
        rows += 1
        var family := str(row.family)
        families[family] = int(families.get(family, 0)) + 1
        match family:
            "band_update":
                var axis: int = _decode(row.axis)
                var from_band: int = _decode(row.band)
                check("band update %d from %d" % [axis, from_band], BjjSideControlRules.band_update(axis, from_band), row.expected)
            "entry":
                _entry_row(row)
            "exchange_grid", "break_grid", "refusal":
                _state_row(row)
            "trajectory":
                _trajectory_row(row)
            _:
                failures += 1
                push_error("unknown fixture family %s" % family)
    if rows == 0:
        push_error("empty fixture")
        quit(1)
        return
    # Bind the replay to the pinned oracle fixture (tests/test_side_control_oracle.py PINNED_FIXTURE): a dropped row or family fails here
    # instead of hiding behind a smaller, self-consistent assertion count.
    check("row count", rows, 19259)
    check("family sizes", families, {"band_update": 405, "entry": 26, "exchange_grid": 14580, "break_grid": 3996, "refusal": 188, "trajectory": 64})
    print("Side Control reference: %d rows %s; %d operations; %d leaf comparisons; %d mismatches" % [rows, families, operations, leaves, failures])
    if failures > 0:
        push_error("Side Control reference: %d / %d assertions failed" % [failures, checks])
        quit(1)
        return
    print("Side Control reference PASS: %d assertions" % checks)
    quit(0)


func _entry_row(row: Dictionary) -> void:
    operations += 1
    var request: Variant = _decode(row.entry)
    var expected: Dictionary = row.expected
    var error := BjjSideControlEntry.validate(request)
    check("entry error %s" % row.id, error, expected.error)
    var created := BjjSideControlMatch.from_entry(request)
    check("entry creation agrees %s" % row.id, created.ok(), str(expected.error).is_empty())
    if str(expected.error).is_empty() and created.ok():
        check("entry snapshot %s" % row.id, created.match_state.snapshot(), expected.snapshot)
        # replay determinism: a second build from the same request is identical
        check("entry snapshot (second build) %s" % row.id, BjjSideControlMatch.from_entry(request).match_state.snapshot(), expected.snapshot)
    else:
        check("entry builds nothing %s" % row.id, created.match_state == null, true)


# One operation through the engine, shaped like the oracle's result: {"error": code} or {"error": "", ...payload}.
func _run(state: BjjSideControlMatch, operation: Dictionary) -> Dictionary:
    var result: BjjSideControlMatch.Result
    match str(operation.op):
        "open_window":
            result = state.open_window(operation.get("duration"))
        "submit":
            result = state.submit(operation.get("window_id"), operation.get("fighter_id"), operation.get("action_id"),
                operation.get("response_id"), operation.get("commitment", ""), operation.get("response_commitment", ""))
        "attempt":
            result = state.attempt(operation.get("action_id"), operation.get("response_id"), operation.get("commitment", ""),
                operation.get("response_commitment", ""))
        _:
            return {"error": "unknown_operation"}
    if not result.ok():
        return {"error": result.error}
    var values := result.values.duplicate(true)
    values["error"] = ""
    return values


func _state_row(row: Dictionary) -> void:
    operations += 1
    var snapshot: Dictionary = _decode(row.state)
    var operation: Dictionary = _decode(row.operation)
    var expected: Dictionary = row.expected
    var created := BjjSideControlMatch.from_snapshot(snapshot)
    check("restore %s" % row.id, created.ok(), true)
    var state := created.match_state
    check("rebuilt snapshot %s" % row.id, state.snapshot(), snapshot)
    check("%s %s" % [row.family, row.id], _run(state, operation), expected.result)
    check("final snapshot %s" % row.id, state.snapshot(), expected.snapshot)
    if str(expected.result.error) != "":
        # Atomic rejection against the INPUT, independent of the oracle's own expected snapshot.
        check("refusal leaves the input unchanged %s" % row.id, state.snapshot(), snapshot)


func _run_trajectory(entry: Variant, commands: Array) -> Dictionary:
    var created := BjjSideControlMatch.from_entry(entry)
    if not created.ok():
        return {"entry_error": created.error, "results": [], "snapshot": null}
    var live := created.match_state
    var results: Array = []
    for command: Dictionary in commands:
        var before := live.snapshot()
        # A twin restored from the live snapshot must continue identically: no hidden state may live outside the snapshot.
        var twin := BjjSideControlMatch.from_snapshot(before).match_state
        var result := _run(live, command)
        results.append(result)
        check("twin continues identically", _run(twin, command), result)
        check("twin snapshot", twin.snapshot(), live.snapshot())
        if str(result.error) != "":
            check("a refused step leaves the snapshot unchanged", live.snapshot(), before)
    return {"entry_error": "", "results": results, "snapshot": live.snapshot()}


func _trajectory_row(row: Dictionary) -> void:
    var entry: Variant = _decode(row.entry)
    var commands: Array = _decode(row.operations)
    operations += commands.size()
    var expected: Dictionary = row.expected
    for replay_pass in range(2):
        var actual := _run_trajectory(entry, commands)
        check("trajectory %s replay %d" % [row.id, replay_pass], {"results": actual.results, "snapshot": actual.snapshot},
            {"results": expected.results, "snapshot": expected.snapshot})
