extends SceneTree

# Compare frozen Python-engine fixture values with the existing GDScript port.
const PATH = "res://tests/generated/mount_reference.json"
const MAX_REPORTED = 12

var checked: int = 0
var mismatches: int = 0


func _initialize() -> void:
    if not FileAccess.file_exists(PATH):
        push_error("Missing Python fixtures: generate_mount_reference.py must run first")
        quit(1)
        return
    var data: Variant = JSON.parse_string(FileAccess.get_file_as_string(PATH))
    if not (data is Dictionary):
        push_error("Invalid Python-reference fixture JSON")
        quit(1)
        return
    var fixture: Dictionary = data as Dictionary
    if int(fixture.get("schema", 0)) != 1:
        push_error("Unsupported fixture schema")
        quit(1)
        return
    var actions: Array = fixture["actions"] as Array
    var drifts: Array = fixture["drifts"] as Array

    for i in range(actions.size()):
        var x: Dictionary = actions[i] as Dictionary
        var actual: Dictionary = BjjMountResolver.resolve_action(
            float(x["axis"]), int(x["band"]), str(x["initiator"]),
            str(x["action_id"]), str(x["response_id"]),
            str(x["top_behavior"]), str(x["bottom_behavior"]),
            int(x["external_grade_modifier"]), int(x["override"]))
        _compare("action[%d]" % i, actual, x["expected"])

    for i in range(drifts.size()):
        var x: Dictionary = drifts[i] as Dictionary
        var actual: Dictionary = BjjMountDrift.simulate(
            float(x["axis"]), int(x["band"]), int(x["clock_seconds"]),
            int(x["duration_seconds"]), str(x["top_behavior"]), str(x["bottom_behavior"]))
        _compare("drift[%d]" % i, actual, x["expected"])

    if mismatches > 0:
        push_error("Python–Godot parity FAILED: %d mismatches / %d checks" % [mismatches, checked])
        quit(1)
        return
    print("Python–Godot Mount parity PASS: %d actions, %d drifts, %d field checks" % [
        actions.size(), drifts.size(), checked])
    quit(0)


func _compare(label: String, actual: Variant, expected: Variant) -> void:
    checked += 1
    if expected is Dictionary and actual is Dictionary:
        var e: Dictionary = expected as Dictionary
        var a: Dictionary = actual as Dictionary
        for k in e.keys():
            if not a.has(k):
                _fail(label + "." + str(k), "<missing>", e[k])
            else:
                _compare(label + "." + str(k), a[k], e[k])
        return
    if expected is Array and actual is Array:
        var e: Array = expected as Array
        var a: Array = actual as Array
        if a.size() != e.size():
            _fail(label + ".size", a.size(), e.size())
            return
        for i in range(e.size()):
            _compare(label + "[%d]" % i, a[i], e[i])
        return
    if typeof(expected) == TYPE_FLOAT and (typeof(actual) == TYPE_FLOAT or typeof(actual) == TYPE_INT):
        if absf(float(actual) - float(expected)) > 0.00000001:
            _fail(label, actual, expected)
        return
    if actual != expected:
        _fail(label, actual, expected)


func _fail(label: String, actual: Variant, expected: Variant) -> void:
    mismatches += 1
    if mismatches <= MAX_REPORTED:
        print("MISMATCH %s: actual=%s expected=%s" % [label, str(actual), str(expected)])
