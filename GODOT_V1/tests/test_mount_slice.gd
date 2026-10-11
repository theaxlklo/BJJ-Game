extends SceneTree

# Run: godot --headless --path GODOT_V1 --script res://tests/test_mount_slice.gd
# Derived from Python Mount v0 source and tests/test_mechanics.py.
# Later: verify a larger generated fixture corpus via the original Python engine.

var failed: int = 0
var checked: int = 0


func _initialize() -> void:
    _test_exit_inventory_negative()
    _test_exit_inventory_catalog()
    _test_exit_inventory_resolver()
    _test_exit_inventory_settled()
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


# A3d: pin the frozen inventory, not the eventual position topology. Literal
# tables below are independent expectations, never populated from exit_destination.
# Columns are the pre-action bands LOOSE, STABLE, STRONG, LOCKED; rows are
# final grades -2, -1, 0, 1, 2. A candidate is NOT an emitted exchange exit.
const EXIT_CANDIDATES: Dictionary = {
    "mount.top.high_mount_climb": [
        ["", "", "", ""], ["", "", "", ""], ["", "", "", ""],
        ["", "", "", ""], ["", "", "", ""]],
    "mount.top.crossface_pressure": [
        ["", "", "", ""], ["", "", "", ""], ["", "", "", ""],
        ["", "", "", ""], ["", "", "", ""]],
    "mount.top.americana_arm_isolation": [
        ["", "", "", ""], ["", "", "", ""], ["", "", "", ""],
        ["", "", "", ""], ["", "", "", ""]],
    "mount.bottom.bridge": [
        ["", "", "", ""], ["", "", "", ""], ["", "", "", ""],
        ["", "", "", ""], ["", "", "", ""]],
    "mount.bottom.elbow_knee_escape": [
        ["", "", "", ""], ["", "", "", ""], ["", "", "", ""],
        ["Half Guard", "Half Guard", "Half Guard", "Half Guard"],
        ["Open Guard", "Half Guard", "Open Guard", "Open Guard"]],
    "mount.bottom.trap_and_roll_escape": [
        ["", "", "", ""], ["", "", "", ""], ["", "", "", ""],
        ["Reversal", "Reversal", "Reversal", "Reversal"],
        ["Reversal", "Reversal", "Reversal", "Reversal"]],
}
const EXIT_LABELS: Array[String] = ["Half Guard", "Open Guard", "Reversal"]


func _inventory_candidate(action: String, grade: int, band: int) -> String:
    return EXIT_CANDIDATES[action][grade + 2][band]


func _inventory_keys(values: Dictionary) -> Array:
    var keys := values.keys()
    keys.sort()
    return keys


func _test_exit_inventory_negative() -> void:
    # Negative controls run before the positive inventory. Use valid resolver
    # inputs: rejected-command coverage belongs to the existing contract suites.
    for action: String in EXIT_CANDIDATES:
        for grade: int in [-2, -1, 0]:
            for band: int in [0, 1, 2, 3]:
                _eq(BjjMountCatalog.exit_destination(action, grade, band), "",
                    "unsuccessful catalog action has no candidate")
    for entity_id: String in BjjMountCatalog.ENTITIES:
        if BjjMountCatalog.ENTITIES[entity_id].kind == "response":
            for grade: int in [-2, -1, 0, 1, 2]:
                for band: int in [0, 1, 2, 3]:
                    _eq(BjjMountCatalog.exit_destination(entity_id, grade, band), "",
                        "response never has a catalog exit")
    for id: String in ["", "mount.bottom.unknown", "mount.top.americana_submission_finish"]:
        for grade: int in [-2, -1, 0, 1, 2]:
            for band: int in [0, 1, 2, 3]:
                _eq(BjjMountCatalog.exit_destination(id, grade, band), "", "noncatalog id has no candidate")
    var elbow := BjjMountCatalog.BOTTOM_ELBOW_KNEE_ESCAPE
    var post := BjjMountCatalog.TOP_RESPONSE_POST_AND_BASE
    # Strong-band raw Strong Success is reduced to Success: raw grade must not
    # select an exit. A boost reaches the floor, but 0.01 above it still cannot.
    for row: Array in [[2.10, 0, 1, ""], [2.11, 1, 2, ""], [2.10, 1, 2, "Open Guard"],
            [2.10, -1, 0, ""]]:
        var r := BjjMountResolver.resolve_action(row[0], 2, "bottom", elbow, post, "PRESSURE", "ESCAPE", row[1])
        _eq(r.final_grade, row[2], "external modifier precedes exit selection")
        _eq(r.exit_destination, row[3], "candidate requires settled grade and threshold")
    var bridge := BjjMountResolver.resolve_action(0.10, 0, "bottom",
        BjjMountCatalog.BOTTOM_BRIDGE, BjjMountCatalog.TOP_RESPONSE_HIP_FOLLOW_REPUMMEL)
    _eq(bridge.final_grade, 1, "successful bridge control")
    _eq(bridge.floor_clamp_used, true, "bridge special clamp precedes escape")
    _eq(bridge.escape_threshold_reached, false, "bridge not escape capable")
    _eq(bridge.exit_destination, "", "successful floor-crossing bridge is no exit")
    _eq(BjjMountContract.transition_for("").fields(), {"kind": "none", "raw_destination": "",
        "destination_position_id": "", "resolved": false}, "no candidate means no transition")


func _test_exit_inventory_catalog() -> void:
    var actions: Dictionary = {}
    var escape_actions: Dictionary = {}
    for id: String in BjjMountCatalog.ENTITIES:
        var entity: Dictionary = BjjMountCatalog.ENTITIES[id]
        if entity.kind == "action":
            actions[id] = true
        if entity.get("escape_capable", false):
            escape_actions[id] = true
    _eq(_inventory_keys(actions), _inventory_keys(EXIT_CANDIDATES), "exact six frozen initiating actions")
    _eq(_inventory_keys(escape_actions), ["mount.bottom.elbow_knee_escape", "mount.bottom.trap_and_roll_escape"],
        "only two escape-capable actions")
    _eq([BjjGrade.STRONG_FAILURE, BjjGrade.FAILURE, BjjGrade.CONTESTED, BjjGrade.SUCCESS, BjjGrade.STRONG_SUCCESS],
        [-2, -1, 0, 1, 2], "inventory grade domain")
    _eq([BjjMountRules.Band.LOOSE, BjjMountRules.Band.STABLE, BjjMountRules.Band.STRONG, BjjMountRules.Band.LOCKED],
        [0, 1, 2, 3], "inventory band columns")
    var labels: Dictionary = {}
    var cells: int = 0
    for action: String in actions:
        for grade: int in [-2, -1, 0, 1, 2]:
            for band: int in [0, 1, 2, 3]:
                var candidate := BjjMountCatalog.exit_destination(action, grade, band)
                _eq(candidate, _inventory_candidate(action, grade, band),
                    "catalog %s grade=%d band=%d" % [action, grade, band])
                if not candidate.is_empty():
                    labels[candidate] = true
                cells += 1
    _eq(cells, 120, "complete action x final grade x pre-action band inventory")
    _eq(_inventory_keys(labels), EXIT_LABELS, "exact candidate label set")
    _eq(BjjMountContract.EXIT_DESTINATIONS, {"Half Guard": "half_guard", "Open Guard": "open_guard"},
        "exact resolved declarations")
    _eq(BjjMountContract.UNRESOLVED_EXITS, ["Reversal"], "exact unresolved declarations")
    for label: String in EXIT_LABELS:
        var destination: String = {"Half Guard": "half_guard", "Open Guard": "open_guard", "Reversal": ""}[label]
        _eq(BjjMountContract.transition_for(label).fields(), {"kind": "exit", "raw_destination": label,
            "destination_position_id": destination, "resolved": label != "Reversal"}, "literal transition " + label)
    var contract := BjjMountContract.create(BjjMountMatch.create({}).match_state, "a", "b").contract
    var destinations := contract.transition_destinations()
    destinations.sort()
    _eq(destinations, ["half_guard", "open_guard"], "no Reversal destination or other receiving id")


func _inventory_emission(action: String, grade: int, band: int, axis_hundredths: int) -> String:
    var candidate := _inventory_candidate(action, grade, band)
    # Independent integer threshold oracle: Bottom moves -grade; the frozen
    # floor is 10 hundredths. This avoids comparing the resolver to its own flags.
    if candidate.is_empty() or axis_hundredths - grade * 100 > 10:
        return ""
    return candidate


func _test_exit_inventory_resolver() -> void:
    var emitted: Dictionary = {}
    var calls: int = 0
    var candidate_without_exit: int = 0
    # Every valid hundredth-step axis/band pair, including hysteresis overlap,
    # all 18 legal matchups and all 5 FINAL grades. The override is an existing
    # resolver seam, not a claim that every grade is reachable with raw defaults.
    for hundredths: int in range(10, 401):
        var axis: float = hundredths / 100.0
        for band: int in [0, 1, 2, 3]:
            if not BjjMountRules.axis_can_have_band(axis, band):
                continue
            for matchup: String in BjjMountCatalog.RAW_GRADES:
                var ids := matchup.split("|")
                var side: String = BjjMountCatalog.ENTITIES[ids[0]].side
                for grade: int in [-2, -1, 0, 1, 2]:
                    var expected := _inventory_emission(ids[0], grade, band, hundredths)
                    var r := BjjMountResolver.resolve_action(axis, band, side, ids[0], ids[1], "PRESSURE", "ESCAPE", 0, grade)
                    var context := "%s grade=%d band=%d axis=%d/100" % [matchup, grade, band, hundredths]
                    _eq(r.final_grade, grade, "final-grade seam " + context)
                    _eq(r.exit_destination, expected, "emitted label " + context)
                    _eq(r.escape_threshold_reached, not expected.is_empty(), "escape gate " + context)
                    _eq(r, BjjMountResolver.resolve_action(axis, band, side, ids[0], ids[1], "PRESSURE", "ESCAPE", 0, grade),
                        "deterministic resolver " + context)
                    if not expected.is_empty():
                        emitted[r.exit_destination] = true
                        _eq(r.band_after, band, "exit retains PRE-action band")
                        _eq(r.band_changes, [], "exit does not update Mount band")
                        _near(r.axis_after, (hundredths - grade * 100) / 100.0, "exit retains crossing axis")
                    elif not _inventory_candidate(ids[0], grade, band).is_empty():
                        candidate_without_exit += 1
                    calls += 1
    _eq(calls, 45720, "pinned legal-axis x matchup x final-grade coverage")
    _eq(_inventory_keys(emitted), EXIT_LABELS, "exact resolver-emitted set")
    _eq(candidate_without_exit > 0, true, "catalog candidates blocked by resolver threshold are exercised")
    print("A3d resolver inventory: %d cases; %d candidates without exits" % [calls, candidate_without_exit])


func _test_exit_inventory_settled() -> void:
    var emitted: Dictionary = {}
    var cases: int = 0
    # No grade overrides: prove actual accepted exchanges emit all and only the
    # declared labels through the public low-level contract (not bottom_decision).
    for hundredths: int in range(10, 401):
        var axis: float = hundredths / 100.0
        for band: int in [0, 1, 2, 3]:
            if not BjjMountRules.axis_can_have_band(axis, band):
                continue
            for matchup: String in BjjMountCatalog.RAW_GRADES:
                var ids := matchup.split("|")
                var side: String = BjjMountCatalog.ENTITIES[ids[0]].side
                var m := BjjMountMatch.create({"axis": axis}).match_state
                m.position.apply_control(axis, band)
                m.initiator = side
                var contract := BjjMountContract.create(m, "a", "b").contract
                var outcome := contract.submit(BjjPositionContract.Command.new("mount", "a" if side == "top" else "b",
                    ids[0], ids[1], "MEDIUM", ""))
                _eq(outcome.ok(), true, "inventory exchange admitted")
                if not outcome.ok():
                    continue
                var resolution: Dictionary = outcome.exchange.resolution
                var expected := _inventory_emission(ids[0], resolution.final_grade, band, hundredths)
                _eq(resolution.exit_destination, expected, "settled exchange emission")
                _eq(m.exit_destination, expected, "authoritative emitted label")
                _eq(outcome.transition.raw_destination, expected, "contract receives only emitted label")
                _eq(outcome.transition.kind, "none" if expected.is_empty() else "exit", "settled transition kind")
                _eq(m.ended, not expected.is_empty(), "legal non-exit remains active")
                _eq(m.clock_seconds, 300, "attempt has no clock advance")
                if not expected.is_empty():
                    emitted[expected] = true
                    var destination: String = {"Half Guard": "half_guard", "Open Guard": "open_guard", "Reversal": ""}[expected]
                    _eq(outcome.transition.destination_position_id, destination, "settled destination")
                    _eq(outcome.transition.resolved, expected != "Reversal", "settled Reversal remains unresolved")
                    var before := m.lifecycle_fields()
                    var repeated := contract.submit(BjjPositionContract.Command.new("mount", "a" if side == "top" else "b",
                        ids[0], ids[1], "MEDIUM", ""))
                    _eq(repeated.error, "terminal_exchange", "repeat after exit rejected")
                    _eq(m.lifecycle_fields(), before, "repeat after exit cannot mutate lifecycle")
                cases += 1
    _eq(cases, 9144, "pinned accepted settled-exchange coverage")
    _eq(_inventory_keys(emitted), EXIT_LABELS, "actual settled exits equal exact catalog inventory")
    print("A3d settled inventory: %d accepted exchanges" % cases)
