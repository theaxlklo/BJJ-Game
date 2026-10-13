extends SceneTree

# Replays the independent Python feint oracle fixture (tests/oracles/half_guard_v0_feint_scenarios.py, written from
# HALF_GUARD_V0_RULES.md section 13, never from this GDScript) through the typed Godot engine: the feint grid and the funding boundary grid
# (rebuilt from full snapshots, with the final snapshot compared), every refusal with its precedence (whole-state equality), the published
# timeout fallback against direct and feint attackers, window trajectories through the gateway's submit / submit_feint (replayed twice), the
# funding table, and the public intent view through the sealed protocol. Expectations are read from the generated fixture; Godot never produces them.
# Generate the fixture first: python GODOT_V1/tests/generate_half_guard_feint_reference.py
const FIXTURE: String = "res://tests/generated/half_guard_feint_reference.jsonl"

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
        push_error("Generate the Half Guard feint oracle fixture first")
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
            "feint_grid", "feint_funding", "feint_refusal", "timeout_fallback":
                _attempt_row(row)
            "feint_trajectory":
                _trajectory_row(row)
            "funding_table":
                _funding_table_row(row)
            "published_fallback":
                operations += 1
                check("published fallback %s" % row.defender_role, BjjHalfGuardCatalog.timeout_fallback(str(row.defender_role)),
                    {"response_id": row.expected.response_id, "commitment": row.expected.commitment})
            "public_view":
                _public_view_row(row)
            _:
                failures += 1
                push_error("unknown fixture family %s" % family)
    if rows == 0:
        push_error("empty fixture")
        quit(1)
        return
    print("Half Guard feint reference: %d rows %s; %d operations; %d leaf comparisons; %d mismatches" % [rows, families, operations, leaves, failures])
    if failures > 0:
        push_error("Half Guard feint reference: %d / %d assertions failed" % [failures, checks])
        quit(1)
        return
    print("Half Guard feint reference PASS: %d assertions" % checks)
    quit(0)


# Rebuild a match from a full snapshot: the public entry path, then direct assignment of the plain state fields.
func _match_from_snapshot(snapshot: Dictionary) -> BjjHalfGuardMatch:
    var request := {"role_map": snapshot.role_map.duplicate(true), "fighters": snapshot.fighters.duplicate(true),
        "clock": {"initial_seconds": snapshot.initial_clock, "remaining_seconds": snapshot.clock_seconds},
        "window": {"last_issued_id": snapshot.window_id}, "interval_seconds": snapshot.interval_seconds}
    var state := BjjHalfGuardMatch.from_entry(request).match_state
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
    var real := str(command.get("real_action_id", ""))
    # The pure admission check (the one the sealed protocol uses at seal time), asked BEFORE the attempt mutates anything: it must say "admissible"
    # exactly when the oracle accepts, and name the oracle's own code for every feint-specific refusal.
    var predicted := state.feint_error(str(command.action_id), real, str(command.commitment)) if not real.is_empty() else ""
    var result := state.attempt(str(command.action_id), str(command.response_id), str(command.commitment), str(command.response_commitment), real)
    var actual: Dictionary = {"error": result.error}
    if result.ok():
        actual = result.values.duplicate(true)
        actual["error"] = ""
    var label := "%s %s->%s vs %s" % [row.family, command.action_id, real, command.response_id]
    check(label, actual, row.expected)
    check(label + " final snapshot", state.snapshot(), row.final)
    var expected_error := str(row.expected.error)
    if not real.is_empty() and (expected_error.is_empty() or expected_error.begins_with("feint_")):
        check(label + " pure admission", predicted, expected_error)


func _funding_table_row(row: Dictionary) -> void:
    operations += 1
    var request := {"role_map": {"top": "fighter_a", "bottom": "fighter_b"}, "fighters": {
        "fighter_a": _fighter(int(row.stamina)), "fighter_b": _fighter(100)},
        "clock": {"initial_seconds": 300, "remaining_seconds": 300}, "window": {"last_issued_id": 0}, "interval_seconds": 5}
    var state := BjjHalfGuardMatch.from_entry(request).match_state
    var cf := BjjHalfGuardCatalog.TOP_CROSSFACE
    var ks := BjjHalfGuardCatalog.TOP_KNEE_SLICE
    var result := state.attempt(cf, BjjHalfGuardCatalog.BOTTOM_HIP_FRAME, str(row.requested), "MEDIUM", ks)
    var actual := {"effective": "", "total_cost": 0}
    if result.ok():
        actual = {"effective": result.values.initiator_effective, "total_cost": result.values.feint.total_cost}
    check("funding table %d %s" % [row.stamina, row.requested], actual, row.expected)


func _fighter(current: int) -> Dictionary:
    return {"stamina_current": current, "stamina_maximum": 100, "exhaustion_latched": current <= 25, "behavior_remainder_units": 0}


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
                var real := str(command.get("real_action_id", ""))
                if real.is_empty():
                    results.append(_report_dictionary(gateway.submit(int(command.window_id), str(command.fighter_id), str(command.action_id),
                        str(command.response_id), str(command.commitment), str(command.response_commitment))))
                else:
                    results.append(_report_dictionary(gateway.submit_feint(int(command.window_id), str(command.fighter_id), str(command.action_id), real,
                        str(command.response_id), str(command.commitment), str(command.response_commitment))))
            _:
                push_error("unknown trajectory operation")
    return {"entry_error": "", "results": results, "final": gateway.snapshot()}


func _trajectory_row(row: Dictionary) -> void:
    var entry: Variant = _decode(row.entry)
    var commands: Array = _decode(row.commands)
    operations += commands.size()
    for replay_pass in range(2):
        check("trajectory %s replay %d" % [row.name, replay_pass], _run_trajectory(entry, commands), row.expected)


# The public intent view through the sealed protocol: sealed as a direct command and, where eligible and funded, as the feint, the view is the
# oracle's pure function of (public state, apparent technique, requested commitment) either way.
func _public_view_row(row: Dictionary) -> void:
    operations += 1
    var snapshot: Dictionary = _decode(row.snapshot)
    var apparent := str(row.apparent_action_id)
    var commitment := str(row.commitment)
    var variants: Array = [""]
    var eligible := BjjHalfGuardCatalog.eligible_real_ids(apparent, int(snapshot.top_base), int(snapshot.bottom_frame))
    for real: String in eligible:
        variants.append(real)
    for real: String in variants:
        var request := {"role_map": snapshot.role_map.duplicate(true), "fighters": snapshot.fighters.duplicate(true),
            "clock": {"initial_seconds": snapshot.initial_clock, "remaining_seconds": snapshot.clock_seconds},
            "window": {"last_issued_id": snapshot.window_id}, "interval_seconds": snapshot.interval_seconds}
        var protocol := BjjHalfGuardSealedProtocol.create(request).protocol
        var state := protocol._gateway._match
        state.axis_tenths = snapshot.axis_tenths
        state.band = snapshot.band
        state.initiator = snapshot.initiator
        state.top_base = snapshot.top_base
        state.bottom_frame = snapshot.bottom_frame
        state.window_open = true
        state.window_side = snapshot.initiator
        protocol._serial = int(row.intent_serial) - 1
        var sealed := protocol.seal_intent(int(snapshot.window_id), str(snapshot.role_map[snapshot.initiator]), apparent, commitment, real)
        check("public view seal accepted (%s as %s)" % [apparent, real], sealed.error, "")
        check("public view (%s as '%s' at '%s')" % [apparent, real, commitment], sealed.values, row.expected)
        check("public view read-back (%s as '%s')" % [apparent, real], protocol.public_intent_view().values, row.expected)
