extends SceneTree

# Replays the independent Python Half Guard v0 oracle fixture (tests/oracles/half_guard_v0.py, written from
# HALF_GUARD_V0_RULES.md, never from this GDScript) through the typed GDScript engine. Expectations are read from the
# generated fixture and are never produced by Godot. Families: initial band, band update, entry validation, the exchange
# and break grids (rebuilt from full snapshots) and multi-command window trajectories (replayed twice).
# Generate the fixture first: python GODOT_V1/tests/generate_half_guard_reference.py
const FIXTURE: String = "res://tests/generated/half_guard_reference.jsonl"

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
        push_error("Generate the Half Guard Python oracle fixture first")
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
            "initial_band":
                var axis: int = _decode(row.axis)
                check("initial band %d" % axis, BjjHalfGuardRules.initial_band(axis), row.expected)
            "band_update":
                var axis_value: int = _decode(row.axis)
                var from_band: int = _decode(row.band)
                check("band update %d from %d" % [axis_value, from_band], BjjHalfGuardRules.band_update(axis_value, from_band), row.expected)
            "entry":
                _entry_row(row)
            "exchange_grid", "break_grid":
                _attempt_row(row)
            "trajectory":
                _trajectory_row(row)
            _:
                failures += 1
                push_error("unknown fixture family %s" % family)
    if rows == 0:
        push_error("empty fixture")
        quit(1)
        return
    print("Half Guard reference: %d rows %s; %d operations; %d leaf comparisons; %d mismatches" % [rows, families, operations, leaves, failures])
    if failures > 0:
        push_error("Half Guard reference: %d / %d assertions failed" % [failures, checks])
        quit(1)
        return
    print("Half Guard reference PASS: %d assertions" % checks)
    quit(0)


func _entry_row(row: Dictionary) -> void:
    operations += 1
    var request: Variant = _decode(row.request)
    var error := BjjHalfGuardEntry.validate(request)
    check("entry error", error, row.expected_error)
    var created := BjjHalfGuardMatch.from_entry(request)
    check("entry creation agrees", created.ok(), str(row.expected_error).is_empty())
    if str(row.expected_error).is_empty() and created.ok():
        check("entry snapshot", created.match_state.snapshot(), row.expected_snapshot)
        # replay determinism: a second build from the same request is identical
        check("entry snapshot (second build)", BjjHalfGuardMatch.from_entry(request).match_state.snapshot(), row.expected_snapshot)
    else:
        check("entry builds nothing", created.match_state == null, true)


# Rebuild a match from a full snapshot: the public entry path, then direct assignment of the plain state fields.
func _match_from_snapshot(snapshot: Dictionary) -> BjjHalfGuardMatch:
    var top_id: String = snapshot.role_map.top
    var bottom_id: String = snapshot.role_map.bottom
    var request := {"role_map": {"top": top_id, "bottom": bottom_id}, "fighters": snapshot.fighters.duplicate(true),
        "clock": {"initial_seconds": snapshot.initial_clock, "remaining_seconds": snapshot.clock_seconds},
        "window": {"last_issued_id": snapshot.window_id}, "interval_seconds": snapshot.interval_seconds}
    var created := BjjHalfGuardMatch.from_entry(request)
    var state := created.match_state
    state.axis_tenths = snapshot.axis_tenths
    state.band = snapshot.band
    state.initiator = snapshot.initiator
    state.top_base = snapshot.top_base
    state.bottom_frame = snapshot.bottom_frame
    state.window_open = snapshot.window_open
    state.window_side = snapshot.window_side
    state.exit_destination = snapshot.exit_destination
    state.exit_reason = snapshot.exit_reason
    state.history = snapshot.history.duplicate(true)
    return state


func _attempt_row(row: Dictionary) -> void:
    operations += 1
    var snapshot: Dictionary = _decode(row.snapshot)
    var command: Dictionary = _decode(row.command)
    var state := _match_from_snapshot(snapshot)
    check("rebuilt snapshot", state.snapshot(), snapshot)
    var result := state.attempt(str(command.action_id), str(command.response_id), str(command.commitment), str(command.response_commitment))
    var actual: Dictionary = {"error": ""}
    if result.ok():
        actual = result.values
        actual["error"] = ""
    else:
        actual = {"error": result.error}
    check("%s %s vs %s" % [row.family, command.action_id, command.response_id], actual, row.expected)
    check("final snapshot", state.snapshot(), row.final)


func _report_dictionary(report: BjjMatchWindowGateway.Report) -> Dictionary:
    if not report.ok():
        return {"error": report.error}
    var values := report.values.duplicate(true)
    values["error"] = ""
    return values


func _run_trajectory(entry: Variant, commands: Array) -> Dictionary:
    var created := BjjHalfGuardWindowGateway.create(entry)
    if not created.ok():
        return {"entry_error": created.error, "results": [], "final": null}
    var gateway := created.gateway
    var results: Array = []
    for command: Dictionary in commands:
        match str(command.op):
            "open":
                results.append(_report_dictionary(gateway.open_window_for(command.duration)))
            "submit":
                results.append(_report_dictionary(gateway.submit(int(command.window_id), str(command.fighter_id), str(command.action_id),
                    str(command.response_id), str(command.commitment), str(command.response_commitment))))
            "attempt":
                var attempted := gateway._match.attempt(str(command.action_id), str(command.response_id), str(command.commitment), str(command.response_commitment))
                var as_dictionary := {"error": attempted.error}
                if attempted.ok():
                    as_dictionary = attempted.values.duplicate(true)
                    as_dictionary["error"] = ""
                results.append(as_dictionary)
            _:
                push_error("unknown trajectory operation")
    return {"entry_error": "", "results": results, "final": gateway.snapshot()}


func _trajectory_row(row: Dictionary) -> void:
    var entry: Variant = _decode(row.entry)
    var commands: Array = _decode(row.commands)
    operations += commands.size()
    for replay_pass in range(2):
        var actual := _run_trajectory(entry, commands)
        check("trajectory %s replay %d" % [row.name, replay_pass], actual, row.expected)
