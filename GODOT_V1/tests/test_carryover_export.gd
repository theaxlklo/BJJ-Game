extends SceneTree

# Negative-first tests for the Mount carry-over export (A3b). Expected values are literal or come
# from PUBLIC views (state_fields, controller_fields, window_fields, roles); the export is never
# compared against itself. Nothing here injects state into production objects.
const C = preload("res://scripts/positions/mount/mount_catalog.gd")
const TOP_ID: String = "fighter_alpha"
const BOTTOM_ID: String = "fighter_bravo"

var checks: int = 0
var failures: int = 0

func check(label: String, actual: Variant, expected: Variant) -> void:
    checks += 1
    if typeof(actual) != typeof(expected) or actual != expected:
        failures += 1
        if failures <= 30:
            push_error("%s: got %s expected %s" % [label, actual, expected])

func same(label: String, actual: Variant, expected: Variant) -> void:
    checks += 1
    if JSON.stringify(actual, "", true, true) != JSON.stringify(expected, "", true, true):
        failures += 1
        if failures <= 30:
            push_error("%s: structures differ" % label)

func rules() -> Dictionary:
    var s := BjjProductionStaminaPolicy.settings()
    s["enable_v02_setup"] = true
    s["enable_v03_submissions"] = true
    s["enable_v04_commitment_semantics"] = true
    return s

func plain_rules() -> Dictionary:
    var s := BjjProductionStaminaPolicy.settings()
    s["enable_v02_setup"] = true
    s["enable_v04_commitment_semantics"] = true
    return s

func gateway(extra: Dictionary = {}) -> BjjMatchWindowGateway:
    var config := {"rules": rules()}
    config.merge(extra, true)
    return BjjMatchWindowGateway.create(config, TOP_ID, BOTTOM_ID).gateway

func graph(extra: Dictionary = {}, settings: Dictionary = {}) -> BjjPositionGraphMatch:
    var config := {"rules": settings if not settings.is_empty() else rules()}
    config.merge(extra, true)
    return BjjPositionGraphMatch.create(config, TOP_ID, BOTTOM_ID).graph

func everything(g: BjjMatchWindowGateway) -> Dictionary:
    return {"state": g.state_fields(), "history": g.history_fields(), "controller": g.controller_fields(),
        "window": g.window_fields(), "top_meter": g._match.top_meter.remainder_units,
        "bottom_meter": g._match.bottom_meter.remainder_units, "d3b_initialized": g._match.d3b.initialized,
        "initiator": g._match.initiator, "interval": g._match.interval_seconds}

# One zero-argument step through the public gateway: open the next window and RESET it.
func step(g: BjjMatchWindowGateway) -> bool:
    var opened := g.open_window()
    if not opened.ok() or opened.values.closed:
        return false
    var who: String = TOP_ID if opened.values.role == "top" else BOTTOM_ID
    return g.submit(opened.values.window_id, who).ok()

func valid_segment() -> Dictionary:
    return gateway().carryover_segment().record

func with_mutation(path: Array, value: Variant) -> Dictionary:
    var record := valid_segment()
    var node: Dictionary = record
    for index in range(path.size() - 1):
        node = node[path[index]]
    node[path[path.size() - 1]] = value
    return record

func without(path: Array) -> Dictionary:
    var record := valid_segment()
    var node: Dictionary = record
    for index in range(path.size() - 1):
        node = node[path[index]]
    node.erase(path[path.size() - 1])
    return record

func rejects(label: String, record: Variant, code: String = "") -> void:
    var before: Variant = record.duplicate(true) if record is Dictionary else record
    var error := BjjMountCarryover.validate_segment(record)
    check(label + " rejected", error.is_empty(), false)
    if not code.is_empty():
        check(label + " code", error, code)
    same(label + " input untouched", record, before)

func _initialize() -> void:
    # ---- 1. The validator rejects incomplete or malformed records without side effects ---------
    check("fresh record validates", BjjMountCarryover.validate_segment(valid_segment()), "")
    for bad: Variant in [null, 5, "x", [], {}]:
        rejects("non-record %s" % [bad], bad, "invalid_carryover_shape")
    var top_level: Array[String] = ["schema", "version", "source_position_id", "fighter_by_role", "fighters", "clock", "window", "d3b", "terminal", "exit"]
    for key in top_level:
        rejects("missing %s" % key, without([key]), "invalid_carryover_shape")
    var extra := valid_segment()
    extra["event_count"] = 3
    rejects("extra top-level key (event count is graph-owned)", extra, "invalid_carryover_shape")
    var nested: Array = [["fighter_by_role", "top"], ["fighter_by_role", "bottom"], ["clock", "initial_seconds"], ["clock", "remaining_seconds"],
        ["window", "last_issued_id"], ["d3b", "armed"], ["d3b", "token_consumed"], ["d3b", "previous_exhausted"],
        ["terminal", "ended"], ["terminal", "submission_tapped"], ["exit", "kind"], ["exit", "raw_destination"],
        ["exit", "destination_position_id"], ["exit", "resolved"]]
    for role in ["top", "bottom"]:
        for key in ["stamina_current", "stamina_maximum", "exhaustion_latched", "behavior_remainder_units"]:
            nested.append(["fighters", role, key])
    for path: Array in nested:
        rejects("missing %s" % [path], without(path), "invalid_carryover_shape")
        var padded := valid_segment()
        var holder: Dictionary = padded
        for index in range(path.size() - 1):
            holder = holder[path[index]]
        holder["unexpected"] = 1
        rejects("extra key beside %s" % [path], padded, "invalid_carryover_shape")
    # Wrong types: float for int, int for bool, bool for int, string for either.
    var ints: Array = [["clock", "initial_seconds"], ["clock", "remaining_seconds"], ["window", "last_issued_id"],
        ["fighters", "top", "stamina_current"], ["fighters", "bottom", "stamina_maximum"],
        ["fighters", "top", "behavior_remainder_units"], ["fighters", "bottom", "behavior_remainder_units"]]
    for path: Array in ints:
        for bad: Variant in [1.0, true, "1", null]:
            rejects("int %s as %s" % [path, bad], with_mutation(path, bad), "invalid_carryover_shape")
    var bools: Array = [["d3b", "armed"], ["d3b", "token_consumed"], ["d3b", "previous_exhausted"], ["terminal", "ended"],
        ["terminal", "submission_tapped"], ["exit", "resolved"], ["fighters", "top", "exhaustion_latched"], ["fighters", "bottom", "exhaustion_latched"]]
    for path: Array in bools:
        for bad: Variant in [0, 1, "false", null]:
            rejects("bool %s as %s" % [path, bad], with_mutation(path, bad), "invalid_carryover_shape")
    rejects("schema name", with_mutation(["schema"], "other"), "unsupported_carryover_schema")
    rejects("version", with_mutation(["version"], 2), "unsupported_carryover_schema")
    rejects("version float", with_mutation(["version"], 1.0), "invalid_carryover_shape")
    rejects("source position", with_mutation(["source_position_id"], "half_guard"), "unsupported_carryover_schema")
    for pair: Array in [["", BOTTOM_ID], [TOP_ID, ""], [TOP_ID, TOP_ID], [" a", "b"]]:
        var record := valid_segment()
        record.fighter_by_role = {"top": pair[0], "bottom": pair[1]}
        rejects("fighter ids %s" % [pair], record, "invalid_fighter_ids")
    # Numeric ranges and the latch, with literal expectations.
    rejects("current above maximum", with_mutation(["fighters", "top", "stamina_current"], 101), "invalid_stamina")
    rejects("current negative", with_mutation(["fighters", "bottom", "stamina_current"], -1), "invalid_stamina")
    rejects("maximum zero", with_mutation(["fighters", "top", "stamina_maximum"], 0), "invalid_stamina")
    rejects("maximum beyond exact range", with_mutation(["fighters", "top", "stamina_maximum"], BjjStaminaPool.MAXIMUM_EXACT + 1 if BjjStaminaPool.MAXIMUM_EXACT < 9223372036854775807 else 9223372036854775807), "invalid_stamina")
    rejects("remainder beyond exact range", with_mutation(["fighters", "top", "behavior_remainder_units"], BjjStaminaPool.MAXIMUM_EXACT + 1), "invalid_stamina")
    rejects("remainder below exact range", with_mutation(["fighters", "bottom", "behavior_remainder_units"], -BjjStaminaPool.MAXIMUM_EXACT - 1), "invalid_stamina")
    rejects("unlatched at the enter threshold", with_mutation(["fighters", "top", "stamina_current"], 25), "invalid_exhaustion_latch")
    var latched_full := with_mutation(["fighters", "bottom", "exhaustion_latched"], true)
    rejects("latched at full stamina", latched_full, "invalid_exhaustion_latch")
    var recovered := valid_segment()
    recovered.fighters.top.stamina_current = 35
    recovered.fighters.top.exhaustion_latched = true
    rejects("latched at the recover threshold", recovered, "invalid_exhaustion_latch")
    for hysteresis_current in [26, 30, 34]:
        for latched in [false, true]:
            var inside := valid_segment()
            inside.fighters.top.stamina_current = hysteresis_current
            inside.fighters.top.exhaustion_latched = latched
            check("hysteresis %d latched=%s accepted" % [hysteresis_current, latched], BjjMountCarryover.validate_segment(inside), "")
    var small := valid_segment()
    small.fighters.bottom.stamina_maximum = 7
    small.fighters.bottom.stamina_current = 1
    small.fighters.bottom.exhaustion_latched = true
    check("small pool thresholds come from the pool (7: enter 1, recover 3)", BjjMountCarryover.validate_segment(small), "")
    small.fighters.bottom.stamina_current = 2
    small.fighters.bottom.exhaustion_latched = false
    check("small pool, between thresholds, unlatched", BjjMountCarryover.validate_segment(small), "")
    small.fighters.bottom.stamina_current = 3
    small.fighters.bottom.exhaustion_latched = true
    rejects("small pool latched at recover threshold", small, "invalid_exhaustion_latch")
    # Clock and window.
    rejects("initial clock zero", with_mutation(["clock", "initial_seconds"], 0), "invalid_clock")
    rejects("remaining above initial", with_mutation(["clock", "remaining_seconds"], 301), "invalid_clock")
    rejects("remaining negative", with_mutation(["clock", "remaining_seconds"], -1), "invalid_clock")
    rejects("negative window id", with_mutation(["window", "last_issued_id"], -1), "invalid_window")
    # D3-B: a token cannot be consumed unless armed; previous_exhausted is free (not tied to the latch).
    rejects("token without arming", with_mutation(["d3b", "token_consumed"], true), "invalid_d3b_state")
    for armed in [false, true]:
        for consumed in [false, true]:
            for previous in [false, true]:
                var record := valid_segment()
                record.d3b = {"armed": armed, "token_consumed": consumed, "previous_exhausted": previous}
                check("d3b %s/%s/%s" % [armed, consumed, previous], BjjMountCarryover.validate_segment(record), "invalid_d3b_state" if consumed and not armed else "")
    # Terminal facts: ended == (remaining == 0 or tapped or exit).
    rejects("ended while clock runs", with_mutation(["terminal", "ended"], true), "invalid_terminal_state")
    var timed_out := valid_segment()
    timed_out.clock.remaining_seconds = 0
    rejects("clock zero but not ended", timed_out, "invalid_terminal_state")
    timed_out.terminal.ended = true
    check("timeout record", BjjMountCarryover.validate_segment(timed_out), "")
    var tapped := valid_segment()
    tapped.terminal.submission_tapped = true
    rejects("tapped but not ended", tapped, "invalid_terminal_state")
    tapped.terminal.ended = true
    check("tap record", BjjMountCarryover.validate_segment(tapped), "")
    # Exit: only Mount's own labels; Mount's single mapping stays authoritative.
    var exits := {"Half Guard": ["half_guard", true], "Open Guard": ["open_guard", true], "Reversal": ["", false]}
    for label: String in exits:
        var record := valid_segment()
        record.exit = {"kind": "exit", "raw_destination": label, "destination_position_id": exits[label][0], "resolved": exits[label][1]}
        record.terminal.ended = true
        check("exit %s accepted" % label, BjjMountCarryover.validate_segment(record), "")
        record.exit.destination_position_id = "half_guard" if exits[label][0] != "half_guard" else "open_guard"
        rejects("exit %s with a wrong destination" % label, record, "invalid_exit")
        record.exit.destination_position_id = exits[label][0]
        record.exit.resolved = not exits[label][1]
        rejects("exit %s with flipped resolved" % label, record, "invalid_exit")
        record.exit.resolved = exits[label][1]
        record.clock.remaining_seconds = 0
        rejects("exit %s at clock zero" % label, record, "invalid_terminal_state")
    for label in ["Side Control", "half_guard", "", " Half Guard", "reversal", "Mount"]:
        var record := valid_segment()
        record.exit = {"kind": "exit", "raw_destination": label, "destination_position_id": "", "resolved": false}
        record.terminal.ended = true
        rejects("undeclared exit label '%s'" % label, record, "invalid_exit")
    var reversal_landing := valid_segment()
    reversal_landing.exit = {"kind": "exit", "raw_destination": "Reversal", "destination_position_id": "side_control", "resolved": true}
    reversal_landing.terminal.ended = true
    rejects("Reversal must not gain a landing", reversal_landing, "invalid_exit")
    for kind_mutation: Array in [["none", "Half Guard", "half_guard", true], ["none", "", "half_guard", false], ["none", "", "", true], ["bogus", "", "", false]]:
        var record := valid_segment()
        record.exit = {"kind": kind_mutation[0], "raw_destination": kind_mutation[1], "destination_position_id": kind_mutation[2], "resolved": kind_mutation[3]}
        rejects("exit none/bogus mutation %s" % [kind_mutation], record, "invalid_exit")

    # ---- 2. Export from a fresh production gateway ---------------------------------------------
    var g := gateway()
    var fresh := g.carryover_segment()
    check("fresh export ok", fresh.ok(), true)
    var expected_fresh := {
        "schema": "mount_carryover", "version": 1, "source_position_id": "mount",
        "fighter_by_role": {"top": TOP_ID, "bottom": BOTTOM_ID},
        "fighters": {
            "top": {"stamina_current": 100, "stamina_maximum": 100, "exhaustion_latched": false, "behavior_remainder_units": 0},
            "bottom": {"stamina_current": 100, "stamina_maximum": 100, "exhaustion_latched": false, "behavior_remainder_units": 0}},
        "clock": {"initial_seconds": 300, "remaining_seconds": 300},
        "window": {"last_issued_id": 0},
        "d3b": {"armed": false, "token_consumed": false, "previous_exhausted": false},
        "terminal": {"ended": false, "submission_tapped": false},
        "exit": {"kind": "none", "raw_destination": "", "destination_position_id": "", "resolved": false}}
    same("fresh record is the literal schema", fresh.record, expected_fresh)
    var gateway_properties: Array[String] = []
    for p: Dictionary in g.get_property_list():
        if (int(p.usage) & PROPERTY_USAGE_SCRIPT_VARIABLE) != 0:
            gateway_properties.append(str(p.name))
    gateway_properties.sort()
    check("gateway gained no state (and no event counter)", gateway_properties,
        ["_bottom_id", "_contract", "_match", "_top_id", "_window_id", "_window_open", "_window_side"])
    for key in fresh.record:
        check("segment owns no graph key %s" % key, key.contains("event") or key == "graph", false)

    # ---- 3. Read-only: no window, no time, no stamina, no D3-B, no token ------------------------
    var before := everything(g)
    var first := g.carryover_segment()
    var second := g.carryover_segment()
    same("export does not change anything", everything(g), before)
    same("repeated exports are identical", first.record, second.record)
    first.record.fighters.top.stamina_current = -50
    first.record.fighter_by_role.top = "tampered"
    first.record.d3b.armed = true
    first.record.clock.remaining_seconds = 0
    same("mutating one record leaves the other untouched", second.record, expected_fresh)
    same("mutating a record leaves Mount untouched", everything(g), before)
    same("a later export is still pristine", g.carryover_segment().record, expected_fresh)
    var depth_probe := g.carryover_segment().record
    check("record shares no container with another export", is_same(depth_probe.fighters, g.carryover_segment().record.fighters), false)
    check("invalid mutated record is rejected", BjjMountCarryover.validate_segment(first.record).is_empty(), false)

    # ---- 4. Open window: refused, atomically; closed window exports the last ISSUED id ---------
    var opened := g.open_window()
    var before_open := everything(g)
    var refused := g.carryover_segment()
    check("open window refuses export", refused.ok(), false)
    check("open window code", refused.error, "window_open")
    check("refused export carries no record", refused.record.is_empty(), true)
    same("refused export changed nothing", everything(g), before_open)
    check("export did not open or close a window", g.window_fields().open, true)
    g.submit(opened.values.window_id, TOP_ID)
    check("after one issued window", g.carryover_segment().record.window.last_issued_id, 1)
    check("export did not increment (still the issued id)", g.window_fields().window_id, 1)
    check("export agrees with window_fields", g.carryover_segment().record.window.last_issued_id, g.window_fields().window_id)
    for index in range(4):
        check("run step %d" % index, step(g), true)
    check("last issued id counts windows, not next", g.carryover_segment().record.window.last_issued_id, 5)
    check("window_fields agrees", g.window_fields().window_id, 5)

    # ---- 5. Values equal PUBLIC views (stamina, clock, roles, remainders, D3-B) -----------------
    var trip := gateway({"bottom_stamina": 20})
    var saw_between_latched := false
    var saw_between_unlatched := false
    var saw_armed := false
    var saw_token_consumed := false
    var saw_remainder := false
    for index in range(70):
        var state := trip.state_fields()
        var record := trip.carryover_segment().record
        check("trip step %d validates" % index, BjjMountCarryover.validate_segment(record), "")
        check("top current", record.fighters.top.stamina_current, state.top_stamina)
        check("bottom current", record.fighters.bottom.stamina_current, state.bottom_stamina)
        check("top maximum", record.fighters.top.stamina_maximum, state.top_maximum)
        check("bottom maximum", record.fighters.bottom.stamina_maximum, state.bottom_maximum)
        check("top latch is the band", record.fighters.top.exhaustion_latched, state.top_band == "Exhausted")
        check("bottom latch is the band", record.fighters.bottom.exhaustion_latched, state.bottom_band == "Exhausted")
        check("initial clock", record.clock.initial_seconds, state.initial_clock)
        check("remaining clock", record.clock.remaining_seconds, state.clock_seconds)
        check("ended", record.terminal.ended, state.ended)
        check("tapped", record.terminal.submission_tapped, state.submission_tapped)
        check("roles", record.fighter_by_role, trip.roles().fighter_by_role)
        var controller := trip.controller_fields()
        same("d3b is the controller's raw state", record.d3b, {"armed": controller.armed, "token_consumed": controller.token_consumed, "previous_exhausted": controller.previous_exhausted})
        check("top remainder", record.fighters.top.behavior_remainder_units, trip._match.top_meter.remainder_units)
        check("bottom remainder", record.fighters.bottom.behavior_remainder_units, trip._match.bottom_meter.remainder_units)
        if state.bottom_stamina > 25 and state.bottom_stamina < 35:
            saw_between_latched = saw_between_latched or record.fighters.bottom.exhaustion_latched
            saw_between_unlatched = saw_between_unlatched or not record.fighters.bottom.exhaustion_latched
        saw_armed = saw_armed or controller.armed
        saw_token_consumed = saw_token_consumed or controller.token_consumed
        saw_remainder = saw_remainder or record.fighters.top.behavior_remainder_units != 0 or record.fighters.bottom.behavior_remainder_units != 0
        if not step(trip):
            break
    check("hysteresis: Exhausted with current inside 26..34 was exported", saw_between_latched, true)
    check("hysteresis: not Exhausted with current inside 26..34 was exported", saw_between_unlatched, true)
    check("D3-B armed state was exported", saw_armed, true)
    check("D3-B token_consumed state was exported", saw_token_consumed, true)
    # previous_exhausted is D3-B's own memory, not the current latch: a Bottom action can spend
    # Bottom into Exhausted AFTER the controller last observed it. The export must keep D3-B's value.
    var diverged := 0
    for start in range(26, 46):
        var spender := gateway({"bottom_stamina": start})
        if not step(spender):
            continue
        var window := spender.open_window_for(0)
        if not window.ok() or window.values.role != "bottom":
            continue
        if not spender.submit(window.values.window_id, BOTTOM_ID, C.BOTTOM_BRIDGE, C.TOP_RESPONSE_POST_AND_BASE).ok():
            continue
        var spent := spender.carryover_segment().record
        var raw := spender.controller_fields()
        check("spender d3b previous_exhausted is the controller's", spent.d3b.previous_exhausted, raw.previous_exhausted)
        if spent.d3b.previous_exhausted != spent.fighters.bottom.exhaustion_latched:
            diverged += 1
            check("diverged record still validates", BjjMountCarryover.validate_segment(spent), "")
    check("previous_exhausted diverged from the latch in a real match", diverged > 0, true)

    # A short window leaves behavior remainders in the meters.
    var odd := gateway()
    check("one-second window", odd.open_window_for(1).ok(), true)
    check("close it", odd.submit(1, TOP_ID).ok(), true)
    var odd_record := odd.carryover_segment().record
    check("remainder export equals the meters", odd_record.fighters.top.behavior_remainder_units, odd._match.top_meter.remainder_units)
    check("remainder export equals the meters (bottom)", odd_record.fighters.bottom.behavior_remainder_units, odd._match.bottom_meter.remainder_units)
    # Explicit coverage that a nonzero remainder is carried.
    var remainder_gateway := gateway()
    for index in range(7):
        remainder_gateway.open_window_for(1)
        remainder_gateway.submit(remainder_gateway.window_fields().window_id, TOP_ID if remainder_gateway.window_fields().role == "top" else BOTTOM_ID)
    var rr := remainder_gateway.carryover_segment().record
    check("remainders match meters after sevens", [rr.fighters.top.behavior_remainder_units, rr.fighters.bottom.behavior_remainder_units],
        [remainder_gateway._match.top_meter.remainder_units, remainder_gateway._match.bottom_meter.remainder_units])
    check("a nonzero remainder was observed somewhere", saw_remainder or rr.fighters.top.behavior_remainder_units != 0 or rr.fighters.bottom.behavior_remainder_units != 0, true)

    # ---- 6. Export never changes the replay: exporting at every step equals never exporting -----
    for settings: Dictionary in [{"bottom_stamina": 20}, {"bottom_stamina": 60, "top_stamina": 40}, {"axis": 0.4}, {}]:
        var plain_g := gateway(settings)
        var exporting := gateway(settings)
        var trace_plain: Array = []
        var trace_exporting: Array = []
        for index in range(60):
            var a := plain_g.open_window()
            var b := exporting.open_window()
            same("open parity %s/%d" % [settings, index], b.fields(), a.fields())
            if not a.ok() or a.values.closed:
                break
            exporting.carryover_segment()  # refused while open; must be inert
            var who: String = TOP_ID if a.values.role == "top" else BOTTOM_ID
            var ra := plain_g.submit(a.values.window_id, who)
            var rb := exporting.submit(b.values.window_id, who)
            same("submit parity", rb.fields(), ra.fields())
            exporting.carryover_segment()
            trace_plain.append(everything(plain_g))
            trace_exporting.append(everything(exporting))
        same("full trace parity %s" % [settings], trace_exporting, trace_plain)

    # ---- 7. Terminal states export (timeout; every exit label) ---------------------------------
    var finished := gateway()
    var closing := finished.open_window_for(300)
    check("timeout closes the match", closing.values.closed, true)
    var timeout_record := finished.carryover_segment()
    check("timeout export ok", timeout_record.ok(), true)
    check("timeout remaining", timeout_record.record.clock.remaining_seconds, 0)
    check("timeout ended", timeout_record.record.terminal.ended, true)
    check("timeout has no exit", timeout_record.record.exit.kind, "none")
    check("no window was issued at timeout", timeout_record.record.window.last_issued_id, 0)
    var found: Dictionary = {}
    for rule_set: Dictionary in [plain_rules(), rules()]:
        for axis: float in [0.2, 0.4, 0.8, 1.5, 3.0]:
            for stamina: int in [100, 60]:
                for action_id: String in [C.BOTTOM_ELBOW_KNEE_ESCAPE, C.BOTTOM_TRAP_AND_ROLL_ESCAPE]:
                    for response_id: String in [C.TOP_RESPONSE_POST_AND_BASE, C.TOP_RESPONSE_WIDE_MOUNT_BASE, C.TOP_RESPONSE_HIP_FOLLOW_REPUMMEL]:
                        var run := escape_run(rule_set, axis, stamina, action_id, response_id)
                        if run != null and not found.has(run.blocked_transition().label):
                            found[run.blocked_transition().label] = run
    check("all three exit labels reached", found.keys().size(), 3)
    var dests := {"Half Guard": "half_guard", "Open Guard": "open_guard", "Reversal": ""}
    for label: String in found:
        var run: BjjPositionGraphMatch = found[label]
        var gateway_after: BjjMatchWindowGateway = run._gateway
        var before_exit := everything(gateway_after)
        var segment := gateway_after.carryover_segment()
        check("exit %s exports" % label, segment.ok(), true)
        same("exit %s did not mutate" % label, everything(gateway_after), before_exit)
        check("exit %s raw label" % label, segment.record.exit.raw_destination, label)
        check("exit %s destination" % label, segment.record.exit.destination_position_id, dests[label])
        check("exit %s resolved" % label, segment.record.exit.resolved, label != "Reversal")
        check("exit %s ended" % label, segment.record.terminal.ended, true)
        check("exit %s valid" % label, BjjMountCarryover.validate_segment(segment.record), "")
        check("exit %s source id" % label, segment.record.source_position_id, "mount")
        check("exit %s stamina from public state" % label, segment.record.fighters.bottom.stamina_current, gateway_after.state_fields().bottom_stamina)
        # ---- graph envelope: graph-owned facts live beside, never inside, the segment ----------
        var envelope := run.carryover_export()
        check("graph %s export ok" % label, envelope.ok(), true)
        check("graph %s schema" % label, envelope.record.schema, "position_graph_carryover")
        same("graph %s segment equals the gateway segment" % label, envelope.record.segment, segment.record)
        check("graph %s status" % label, envelope.record.graph.status, "halted_at_unsupported_transition")
        check("graph %s event count is the graph's" % label, envelope.record.graph.event_count, run.events().size())
        check("graph %s recorded reason is the one the validator derives" % label, envelope.record.graph.blocked_transition.reason, "unresolved_destination" if label == "Reversal" else "destination_not_implemented")
        same("graph %s blocked transition" % label, envelope.record.graph.blocked_transition, run.blocked_transition())
        check("graph %s validates" % label, BjjMountCarryover.validate_envelope(envelope.record), "")
        check("segment %s still carries no event count" % label, envelope.record.segment.has("event_count"), false)
        var events_before := run.events()
        var status_before := run.status()
        run.carryover_export()
        same("graph %s export leaves the log alone" % label, run.events(), events_before)
        check("graph %s export leaves the halt in place" % label, run.status(), status_before)
        # Envelope negatives.
        var tamper := func(change: Callable, code: String, name: String) -> void:
            var record := run.carryover_export().record
            change.call(record)
            var error := BjjMountCarryover.validate_envelope(record)
            check("%s %s rejected" % [label, name], error.is_empty(), false)
            check("%s %s code" % [label, name], error, code)
        tamper.call(func(r: Dictionary) -> void: r.graph.status = "active", "inconsistent_graph_segment", "active with an exit")
        tamper.call(func(r: Dictionary) -> void: r.graph.status = "ended", "inconsistent_graph_segment", "ended with an exit")
        tamper.call(func(r: Dictionary) -> void: r.graph.blocked_transition = {}, "inconsistent_graph_segment", "halted without a blocked record")
        tamper.call(func(r: Dictionary) -> void: r.graph.blocked_transition.label = "Side Control", "inconsistent_graph_segment", "blocked label differs")
        tamper.call(func(r: Dictionary) -> void: r.graph.blocked_transition.erase("reason"), "invalid_graph_block", "blocked record missing a key")
        tamper.call(func(r: Dictionary) -> void: r.graph.event_count = -1, "invalid_graph_block", "negative event count")
        tamper.call(func(r: Dictionary) -> void: r.graph.event_count = 1.0, "invalid_graph_block", "float event count")
        tamper.call(func(r: Dictionary) -> void: r.graph["extra"] = 1, "invalid_graph_block", "extra graph key")
        tamper.call(func(r: Dictionary) -> void: r.segment["event_count"] = 4, "invalid_carryover_shape", "event count inside the segment")
        tamper.call(func(r: Dictionary) -> void: r.schema = "mount_carryover", "unsupported_carryover_schema", "wrong envelope schema")
        tamper.call(func(r: Dictionary) -> void: r.graph.status = "bogus", "invalid_graph_block", "unknown status")
        tamper.call(func(r: Dictionary) -> void: r.graph.blocked_transition.destination_position_id = "zz", "inconsistent_graph_segment", "blocked destination differs")
        tamper.call(func(r: Dictionary) -> void: r.graph.blocked_transition.from_position_id = "half_guard", "inconsistent_graph_segment", "blocked source differs")
        tamper.call(func(r: Dictionary) -> void: r.graph.blocked_transition.reason = "", "inconsistent_graph_segment", "empty blocked reason")
        tamper.call(func(r: Dictionary) -> void: r.graph.blocked_transition.reason = "because", "inconsistent_graph_segment", "arbitrary blocked reason")
        tamper.call(func(r: Dictionary) -> void: r.graph.blocked_transition.reason = "undeclared_exit_label", "inconsistent_graph_segment", "graph reason Mount never produces for a declared exit")
        tamper.call(func(r: Dictionary) -> void: r.graph.blocked_transition.reason = "unresolved_destination" if label != "Reversal" else "destination_not_implemented", "inconsistent_graph_segment", "contradictory blocked reason")
        tamper.call(func(r: Dictionary) -> void: r.segment.exit = {"kind": "none", "raw_destination": "", "destination_position_id": "", "resolved": false}; r.segment.terminal.ended = false, "inconsistent_graph_segment", "halted graph with a no-exit segment")
        tamper.call(func(r: Dictionary) -> void: r["extra"] = 1, "invalid_carryover_shape", "extra envelope key")
        tamper.call(func(r: Dictionary) -> void: r.version = 2, "unsupported_carryover_schema", "envelope version")
        tamper.call(func(r: Dictionary) -> void: r.segment = "x", "invalid_carryover_shape", "segment not a record")
    # Halt must not be cleared and later commands stay rejected after exporting.
    var any_run: BjjPositionGraphMatch = found.values()[0]
    any_run.carryover_export()
    check("halted graph still rejects open_window", any_run.open_window().error, "halted_unsupported_transition")

    # Post-timeout: the id stays at the last ISSUED value (nothing is issued when the match closes).
    var late := gateway()
    for index in range(3):
        check("late step %d" % index, step(late), true)
    var late_id: int = late.window_fields().window_id
    check("three or more windows were issued", late_id >= 3, true)
    var late_close := late.open_window_for(late.state_fields().clock_seconds)
    check("late timeout closes", late_close.values.closed, true)
    check("timeout keeps the last issued id", late.carryover_segment().record.window.last_issued_id, late_id)
    check("timeout id equals window_fields", late.carryover_segment().record.window.last_issued_id, late.window_fields().window_id)
    # A real tap through the public commands (Americana finish at the Finish stage).
    var tapped_graph := tap_run()
    check("a real tap was reached", tapped_graph != null, true)
    if tapped_graph != null:
        var tap_segment := tapped_graph._gateway.carryover_segment()
        check("tap export ok", tap_segment.ok(), true)
        check("tap tapped", tap_segment.record.terminal.submission_tapped, true)
        check("tap ended", tap_segment.record.terminal.ended, true)
        check("tap has time left", tap_segment.record.clock.remaining_seconds >= 1, true)
        check("tap is not an exit", tap_segment.record.exit.kind, "none")
        check("tap agrees with the public state", tap_segment.record.terminal.submission_tapped, tapped_graph.state_fields().submission_tapped)
        var tap_envelope := tapped_graph.carryover_export()
        check("tap graph status", tap_envelope.record.graph.status, "ended")
        check("tap graph validates", BjjMountCarryover.validate_envelope(tap_envelope.record), "")
        check("tap log ends with the terminal outcome", tapped_graph.events().back().kind, "terminal_outcome")
        check("tap terminal reason", tapped_graph.events().back().reason, "tap")
        var tap_before := {"status": tapped_graph.status(), "events": tapped_graph.events(), "state": tapped_graph.state_fields()}
        check("tap rejects open_window after export", tapped_graph.open_window().ok(), false)
        same("tap export is inert", {"status": tapped_graph.status(), "events": tapped_graph.events(), "state": tapped_graph.state_fields()}, tap_before)
        tap_envelope.record.graph.status = "active"
        check("tap relabelled active is rejected", BjjMountCarryover.validate_envelope(tap_envelope.record), "inconsistent_graph_segment")
    # Graph-status literals are pinned to the graph's own constants.
    check("status literal active", BjjMountCarryover.STATUS_ACTIVE, BjjPositionGraphMatch.STATUS_ACTIVE)
    check("status literal ended", BjjMountCarryover.STATUS_ENDED, BjjPositionGraphMatch.STATUS_ENDED)
    check("status literal halted", BjjMountCarryover.STATUS_HALTED, BjjPositionGraphMatch.STATUS_HALTED)
    # Reason literals are pinned to what the graph actually records for each classification.
    check("reason literal not implemented", BjjMountCarryover.REASON_NOT_IMPLEMENTED, BjjPositionGraphMatch.classify_exit("Half Guard").reason)
    check("reason literal unresolved", BjjMountCarryover.REASON_UNRESOLVED, BjjPositionGraphMatch.classify_exit("Reversal").reason)
    # Accepted records are never modified by validation.
    var accepted := valid_segment()
    var accepted_copy := accepted.duplicate(true)
    check("accepted validates", BjjMountCarryover.validate_segment(accepted), "")
    same("validate_segment leaves an accepted record untouched", accepted, accepted_copy)
    var env_graph := graph()
    var env := env_graph.carryover_export().record
    var env_copy := env.duplicate(true)
    check("accepted envelope validates", BjjMountCarryover.validate_envelope(env), "")
    same("validate_envelope leaves an accepted record untouched", env, env_copy)
    # Envelope aliasing: one envelope's mutation reaches neither a second envelope, the graph nor Mount.
    var env_a := env_graph.carryover_export().record
    var env_b := env_graph.carryover_export().record
    var graph_before := {"status": env_graph.status(), "events": env_graph.events(), "blocked": env_graph.blocked_transition(), "state": env_graph.state_fields()}
    env_a.graph.event_count = 99
    env_a.graph.blocked_transition["x"] = 1
    env_a.segment.fighters.top.stamina_current = -1
    same("second envelope untouched", env_b, env_copy)
    same("graph untouched by envelope mutation", {"status": env_graph.status(), "events": env_graph.events(), "blocked": env_graph.blocked_transition(), "state": env_graph.state_fields()}, graph_before)
    same("a later envelope is still pristine", env_graph.carryover_export().record, env_copy)

    # ---- 8. Fresh graph and an active graph ------------------------------------------------------
    var fresh_graph := graph()
    var fresh_envelope := fresh_graph.carryover_export()
    check("fresh graph export ok", fresh_envelope.ok(), true)
    check("fresh graph status", fresh_envelope.record.graph.status, "active")
    check("fresh graph event count", fresh_envelope.record.graph.event_count, 0)
    same("fresh graph blocked is empty", fresh_envelope.record.graph.blocked_transition, {})
    var injected := fresh_envelope.record.duplicate(true)
    injected.graph.blocked_transition = {"from_position_id": "mount", "label": "Half Guard", "reason": "destination_not_implemented", "destination_position_id": "half_guard"}
    check("blocked record on an active graph is rejected", BjjMountCarryover.validate_envelope(injected), "inconsistent_graph_segment")
    var live := fresh_graph.open_window()
    var live_before := {"status": fresh_graph.status(), "events": fresh_graph.events(), "window": fresh_graph.window_fields()}
    var live_export := fresh_graph.carryover_export()
    check("graph refuses while a window is open", live_export.error, "window_open")
    same("refused graph export changed nothing", {"status": fresh_graph.status(), "events": fresh_graph.events(), "window": fresh_graph.window_fields()}, live_before)
    fresh_graph.submit(live.values.window_id, TOP_ID)
    var after_one := fresh_graph.carryover_export()
    check("graph event count after one window", after_one.record.graph.event_count, fresh_graph.events().size())
    check("graph event count is 2 (opened, accepted)", after_one.record.graph.event_count, 2)
    check("segment window id independent of event count", after_one.record.segment.window.last_issued_id, 1)
    after_one.record.graph.status = "ended"
    check("an active graph relabelled ended is rejected", BjjMountCarryover.validate_envelope(after_one.record).is_empty(), false)
    var ended_graph := graph()
    ended_graph.open_window_for(300)
    var ended_envelope := ended_graph.carryover_export()
    var timeout_active := ended_envelope.record.duplicate(true)
    timeout_active.graph.status = "active"
    check("a timeout graph relabelled active is rejected", BjjMountCarryover.validate_envelope(timeout_active), "inconsistent_graph_segment")
    check("timeout graph status", ended_envelope.record.graph.status, "ended")
    check("timeout graph validates", BjjMountCarryover.validate_envelope(ended_envelope.record), "")
    for bad: Variant in [null, 3, {}, {"schema": "position_graph_carryover"}]:
        check("envelope shape %s" % [bad], BjjMountCarryover.validate_envelope(bad), "invalid_carryover_shape")
    var graph_properties: Array[String] = []
    for p: Dictionary in fresh_graph.get_property_list():
        if (int(p.usage) & PROPERTY_USAGE_SCRIPT_VARIABLE) != 0:
            graph_properties.append(str(p.name))
    graph_properties.sort()
    # HG-16 revises this pin: the B1d Half Guard slot, receiver table and cadence are the only additions (carry-over state is not among them).
    check("graph gained no carry-over state (B1i: only the opt-in sealed protocol slot and flag were added)", graph_properties,
        ["_blocked", "_events", "_gateway", "_half_guard", "_interval_seconds", "_receivers", "_sealed", "_sealed_enabled", "_status", "_terminal_reason"])

    print("carry-over export checks: ", checks)
    print("carry-over export failures: ", failures)
    quit(1 if failures > 0 else 0)

# Returns a halted graph if Mount exits through the directed Bottom escape attempt, else null.
func escape_run(rule_set: Dictionary, axis: float, stamina: int, action: String, response: String) -> BjjPositionGraphMatch:
    var g := graph({"axis": axis, "bottom_stamina": stamina}, rule_set)
    var opened := g.open_window_for(0)
    if not opened.ok() or not g.submit(opened.values.window_id, TOP_ID).ok():
        return null
    if not g.open_window_for(0).ok():
        return null
    var tries := 0
    while action == C.BOTTOM_TRAP_AND_ROLL_ESCAPE and not g.action_options(BOTTOM_ID).available_ids().has(action) and tries < 6:
        tries += 1
        var prep := g.submit(g.window_fields().window_id, BOTTOM_ID, C.BOTTOM_BRIDGE, response)
        if not prep.ok() or g.status() != "active":
            return null
        var top_window := g.open_window_for(0)
        if not top_window.ok() or not g.submit(top_window.values.window_id, TOP_ID).ok():
            return null
        if not g.open_window_for(0).ok():
            return null
    if not g.action_options(BOTTOM_ID).available_ids().has(action):
        return null
    if not g.submit(g.window_fields().window_id, BOTTOM_ID, action, response).ok():
        return null
    return g if g.status() == "halted_at_unsupported_transition" else null

# Directed real tap: Top works the Americana to its Finish stage and finishes. Returns null if not reached.
func tap_run() -> BjjPositionGraphMatch:
    var g := graph({"axis": 1.5})
    for index in range(60):
        var opened := g.open_window_for(0)
        if not opened.ok() or g.status() != "active" or opened.values.get("closed", false):
            break
        if opened.values.role == "bottom":
            g.submit(opened.values.window_id, BOTTOM_ID)
            continue
        var ids := g.action_options(TOP_ID).available_ids()
        var pick: String = ids[0]
        if ids.has("mount.top.americana_submission_finish"):
            pick = "mount.top.americana_submission_finish"
        elif ids.has(C.TOP_AMERICANA_ARM_ISOLATION):
            pick = C.TOP_AMERICANA_ARM_ISOLATION
        var responses := g.response_options(pick).available_ids()
        if not g.submit(opened.values.window_id, TOP_ID, pick, responses[0], "HIGH").ok():
            return null
        if g.state_fields().submission_tapped:
            return g
    return null
