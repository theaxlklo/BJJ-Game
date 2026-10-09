extends SceneTree

# Run: godot --headless --path GODOT_V1 --script res://tests/test_mount_slice.gd
# Derived from Python Mount v0 source and tests/test_mechanics.py.
# Later: verify a larger generated fixture corpus via the original Python engine.

var failed: int = 0
var checked: int = 0


func _initialize() -> void:
    _test_bands()
    _test_drift()
    _test_matrix()
    _test_resolution()
    _test_position()
    if failed > 0:
        push_error("Mount slice: %d / %d assertions failed" % [failed, checked])
        quit(1)
    else:
        print("Mount slice PASS: %d assertions" % checked)
        quit(0)


func _eq(actual: Variant, expected: Variant, case_name: String) -> void:
    checked += 1
    if actual != expected:
        failed += 1
        print("FAIL %s: got %s; expected %s" % [case_name, str(actual), str(expected)])


func _near(actual: float, expected: float, case_name: String) -> void:
    checked += 1
    if not is_equal_approx(actual, expected):
        failed += 1
        print("FAIL %s: got %.12f; expected %.12f" % [case_name, actual, expected])


func _test_bands() -> void:
    _eq(BjjMountRules.initial_band(0.1), BjjMountRules.Band.LOOSE, "0.10 Loose")
    _eq(BjjMountRules.initial_band(1.0), BjjMountRules.Band.STABLE, "1.00 Stable")
    _eq(BjjMountRules.initial_band(2.0), BjjMountRules.Band.STRONG, "2.00 Strong")
    _eq(BjjMountRules.initial_band(3.0), BjjMountRules.Band.LOCKED, "3.00 Locked")
    var up: Dictionary = BjjMountRules.update_band(3.50, BjjMountRules.Band.STABLE)
    _eq(up["band"], BjjMountRules.Band.LOCKED, "multiband up")
    _eq((up["changes"] as Array).size(), 2, "multiband up events")
    var down: Dictionary = BjjMountRules.update_band(1.0, BjjMountRules.Band.LOCKED)
    _eq(down["band"], BjjMountRules.Band.STABLE, "multiband down")
    _eq((down["changes"] as Array).size(), 2, "multiband down events")
    _eq(BjjMountRules.update_band(1.9, BjjMountRules.Band.STABLE)["band"],
        BjjMountRules.Band.STABLE, "hysteresis stable")
    _eq(BjjMountRules.update_band(1.9, BjjMountRules.Band.STRONG)["band"],
        BjjMountRules.Band.STRONG, "hysteresis strong")


func _test_drift() -> void:
    var low: Dictionary = BjjMountDrift.simulate(
        0.15, BjjMountRules.Band.LOOSE, 5, 5, "HOLD", "ESCAPE")
    _near(float(low["end_axis"]), 0.10, "drift floor")
    var high: Dictionary = BjjMountDrift.simulate(
        3.95, BjjMountRules.Band.LOCKED, 5, 5, "PRESSURE", "PROTECT")
    _near(float(high["end_axis"]), 4.0, "drift ceiling")
    var partial: Dictionary = BjjMountDrift.simulate(
        1.50, BjjMountRules.Band.STABLE, 4, 7, "PRESSURE", "ESCAPE")
    _eq(partial["end_clock"], 0, "partial last tick clock")
    _near(float(partial["total_drift"]), 0.4, "partial drift total")
    _near(BjjMountRules.drift_rate("CONSERVE", "CONSERVE"), 0.0,
        "conserve behavior alias")


func _test_matrix() -> void:
    _eq(BjjMountCatalog.ENTITIES.size(), 12, "12 frozen entities")
    _eq(BjjMountCatalog.RAW_GRADES.size(), 18, "18 frozen matchups")
    _eq(BjjMountCatalog.raw_grade(
        BjjMountCatalog.TOP_HIGH_MOUNT_CLIMB,
        BjjMountCatalog.BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE), -1,
        "high mount vs tight elbows")
    _eq(BjjMountCatalog.raw_grade(
        BjjMountCatalog.BOTTOM_ELBOW_KNEE_ESCAPE,
        BjjMountCatalog.TOP_RESPONSE_WIDE_MOUNT_BASE), 1,
        "elbow knee vs wide base")


func _test_resolution() -> void:
    var bridge: Dictionary = BjjMountResolver.resolve_action(
        0.50, BjjMountRules.Band.LOOSE, "bottom",
        BjjMountCatalog.BOTTOM_BRIDGE,
        BjjMountCatalog.TOP_RESPONSE_HIP_FOLLOW_REPUMMEL)
    _eq(bridge["floor_clamp_used"], true, "bridge special floor clamp")
    _near(float(bridge["axis_after"]), 0.10, "bridge never exits")
    _eq(bridge["exit_destination"], "", "bridge has no exit")

    var half: Dictionary = BjjMountResolver.resolve_action(
        1.10, BjjMountRules.Band.STABLE, "bottom",
        BjjMountCatalog.BOTTOM_ELBOW_KNEE_ESCAPE,
        BjjMountCatalog.TOP_RESPONSE_WIDE_MOUNT_BASE)
    _eq(half["exit_destination"], "Half Guard", "success -> half guard")
    _eq(half["final_grade"], 1, "success grade")

    var override: Dictionary = BjjMountResolver.resolve_action(
        2.10, BjjMountRules.Band.STABLE, "bottom",
        BjjMountCatalog.BOTTOM_ELBOW_KNEE_ESCAPE,
        BjjMountCatalog.TOP_RESPONSE_POST_AND_BASE)
    _eq(override["exit_destination"], "Half Guard", "strong success stable override")
    _eq(override["final_grade"], 2, "strong success grade")

    var open_guard: Dictionary = BjjMountResolver.resolve_action(
        0.60, BjjMountRules.Band.LOOSE, "bottom",
        BjjMountCatalog.BOTTOM_ELBOW_KNEE_ESCAPE,
        BjjMountCatalog.TOP_RESPONSE_POST_AND_BASE)
    _eq(open_guard["exit_destination"], "Open Guard", "loose strong -> open guard")
    _near(float(open_guard["axis_after"]), -1.40, "escape crossing retained")

    var bottom_strong: Dictionary = BjjMountResolver.resolve_action(
        1.90, BjjMountRules.Band.STRONG, "bottom",
        BjjMountCatalog.BOTTOM_ELBOW_KNEE_ESCAPE,
        BjjMountCatalog.TOP_RESPONSE_POST_AND_BASE)
    _eq(bottom_strong["raw_grade"], 2, "strong-band raw grade")
    _eq(bottom_strong["final_grade"], 1, "strong-band bottom penalty")
    _eq(bottom_strong["exit_destination"], "", "strong-band no exit")

    var top_loose: Dictionary = BjjMountResolver.resolve_action(
        0.50, BjjMountRules.Band.LOOSE, "top",
        BjjMountCatalog.TOP_HIGH_MOUNT_CLIMB,
        BjjMountCatalog.BOTTOM_RESPONSE_FOREARM_FRAME)
    _eq(top_loose["raw_grade"], 1, "loose top raw")
    _eq(top_loose["final_grade"], 0, "loose top positional penalty")

    var behavior: Dictionary = BjjMountResolver.resolve_action(
        1.50, BjjMountRules.Band.STABLE, "bottom",
        BjjMountCatalog.BOTTOM_BRIDGE,
        BjjMountCatalog.TOP_RESPONSE_HIP_FOLLOW_REPUMMEL, "HOLD", "ESCAPE")
    _eq(behavior["raw_grade"], 1, "hold raw")
    _eq(behavior["behavior_grade"], 0, "hold behavior modifier")

    var failed_clamp: Dictionary = BjjMountResolver.resolve_action(
        0.50, BjjMountRules.Band.LOOSE, "top",
        BjjMountCatalog.TOP_CROSSFACE_PRESSURE,
        BjjMountCatalog.BOTTOM_RESPONSE_FOREARM_FRAME)
    _eq(failed_clamp["failure_clamp_used"], true, "failed action floor clamp")
    _near(float(failed_clamp["axis_after"]), 0.10, "failed clamp axis")


func _test_position() -> void:
    var position: BjjMountPosition = BjjMountPosition.new(0.60)
    position.break_mount(-1.40)
    _eq(position.broken, true, "Mount broken")
    _near(position.axis, 0.60, "last legal axis preserved")
    _near(position.reported_axis(), -1.40, "crossing axis reported")
