extends SceneTree

# Negative-first tests for the Mount -> Half Guard edge adapter (B1c). Source records come from REAL Mount gateway runs (public
# carryover_segment()), or are single-field mutations of such a record. Expected values are literals or come from PUBLIC Mount views
# (state_fields, window_fields, roles); the request is never compared with itself. Every refusal is checked for a stable code, an empty
# request and whole-record equality before/after. Nothing here injects state into a production object; the only private reads are
# the behavior-meter remainders, read-only, because no public Mount view exposes them.
const C = preload("res://scripts/positions/mount/mount_catalog.gd")
const SCRIPT_PATH: String = "res://scripts/positions/half_guard/half_guard_mount_edge.gd"
const MAXIMUM: int = BjjStaminaPool.MAXIMUM_EXACT
const TOP: String = "fighter_alpha"
const BOTTOM: String = "fighter_bravo"
const MOUNT_STATE_KEYS: Array[String] = ["top_stamina", "bottom_stamina", "top_maximum", "bottom_maximum", "top_band", "bottom_band", "clock_seconds", "initial_clock"]

var checks: int = 0
var failures: int = 0
var exits: Dictionary = {}          # label -> real Mount gateway that exited to that label (default ids)
var half_guard_exits: Array = []    # several real Half Guard exits with distinct stamina / latch / clock / window values


func check(label: String, actual: Variant, expected: Variant) -> void:
    checks += 1
    if typeof(actual) != typeof(expected) or JSON.stringify(actual, "", true, true) != JSON.stringify(expected, "", true, true):
        failures += 1
        if failures <= 40:
            push_error("%s: got %s expected %s" % [label, JSON.stringify(actual), JSON.stringify(expected)])


func rules() -> Dictionary:
    var settings := BjjProductionStaminaPolicy.settings()
    settings["enable_v02_setup"] = true
    settings["enable_v03_submissions"] = true
    settings["enable_v04_commitment_semantics"] = true
    return settings


func plain_rules() -> Dictionary:
    var settings := BjjProductionStaminaPolicy.settings()
    settings["enable_v02_setup"] = true
    settings["enable_v04_commitment_semantics"] = true
    return settings


func mount_gateway(extra: Dictionary = {}, top_id: String = TOP, bottom_id: String = BOTTOM, rule_set: Dictionary = {}) -> BjjMatchWindowGateway:
    var configuration := {"rules": rule_set if not rule_set.is_empty() else rules()}
    configuration.merge(extra, true)
    var created := BjjMatchWindowGateway.create(configuration, top_id, bottom_id)
    check("mount gateway built for %s / %s" % [top_id, bottom_id], created.ok(), true)
    return created.gateway


# Every exposed read view of a Mount gateway, plus the read-only private remainders (see header).
func everything(g: BjjMatchWindowGateway) -> Dictionary:
    return {"state": g.state_fields(), "history": g.history_fields(), "controller": g.controller_fields(), "window": g.window_fields(),
        "behavior": g.behavior_fields(), "roles": g.roles().fields(), "terminal": g.is_terminal(), "commitment": g.selected_commitment(),
        "segment": g.carryover_segment().record, "top_meter": g._match.top_meter.remainder_units, "bottom_meter": g._match.bottom_meter.remainder_units}


# Directed real Mount run: Top RESETs, then Bottom prepares if needed and attempts one escape. Returns null unless the run exits.
func escape_run(configuration: Dictionary, action: String, response: String, top_id: String = TOP, bottom_id: String = BOTTOM, rule_set: Dictionary = {}, rounds: int = 0) -> BjjMatchWindowGateway:
    var configured := BjjMatchWindowGateway.create({"rules": rule_set if not rule_set.is_empty() else rules()}.merged(configuration, true), top_id, bottom_id)
    if not configured.ok():
        return null
    var g := configured.gateway
    # `rounds` extra real Top RESET + Bottom RESET window pairs, so the last issued window id differs between runs
    for round_index in range(rounds):
        var top_round := g.open_window_for(0)
        if not top_round.ok() or not g.submit(top_round.values.window_id, top_id).ok():
            return null
        var bottom_round := g.open_window_for(0)
        if not bottom_round.ok() or not g.submit(bottom_round.values.window_id, bottom_id).ok() or g.state_fields().exit_destination != "":
            return null
    var opened := g.open_window_for(0)
    if not opened.ok() or not g.submit(opened.values.window_id, top_id).ok():
        return null
    if not g.open_window_for(0).ok():
        return null
    var tries := 0
    while action == C.BOTTOM_TRAP_AND_ROLL_ESCAPE and not g.action_options(bottom_id).available_ids().has(action) and tries < 6:
        tries += 1
        var prep := g.submit(g.window_fields().window_id, bottom_id, C.BOTTOM_BRIDGE, response)
        if not prep.ok() or g.state_fields().exit_destination != "":
            return null
        var top_window := g.open_window_for(0)
        if not top_window.ok() or not g.submit(top_window.values.window_id, top_id).ok():
            return null
        if not g.open_window_for(0).ok():
            return null
    if not g.action_options(bottom_id).available_ids().has(action):
        return null
    if not g.submit(g.window_fields().window_id, bottom_id, action, response).ok():
        return null
    return g if g.state_fields().exit_destination != "" else null


# Directed real tap: Top works the Americana to its Finish stage. Returns null if not reached.
func tap_run() -> BjjMatchWindowGateway:
    var g := mount_gateway({"axis": 1.5})
    for index in range(60):
        var opened := g.open_window_for(0)
        if not opened.ok() or opened.values.get("closed", false) or g.state_fields().submission_tapped:
            break
        if opened.values.role == "bottom":
            g.submit(opened.values.window_id, BOTTOM)
            continue
        var ids := g.action_options(TOP).available_ids()
        var pick: String = ids[0]
        if ids.has("mount.top.americana_submission_finish"):
            pick = "mount.top.americana_submission_finish"
        elif ids.has(C.TOP_AMERICANA_ARM_ISOLATION):
            pick = C.TOP_AMERICANA_ARM_ISOLATION
        var responses := g.response_options(pick).available_ids()
        if not g.submit(opened.values.window_id, TOP, pick, responses[0], "HIGH").ok():
            return null
        if g.state_fields().submission_tapped:
            return g
    return null


func find_runs() -> void:
    for rule_set: Dictionary in [rules(), plain_rules()]:
        for axis: float in [0.2, 0.4, 0.8, 1.5, 3.0]:
            for top_stamina: int in [100, 20, 60]:
                for bottom_stamina: int in [100, 60, 20]:
                    for action_id: String in [C.BOTTOM_ELBOW_KNEE_ESCAPE, C.BOTTOM_TRAP_AND_ROLL_ESCAPE]:
                        for response_id: String in [C.TOP_RESPONSE_POST_AND_BASE, C.TOP_RESPONSE_WIDE_MOUNT_BASE, C.TOP_RESPONSE_HIP_FOLLOW_REPUMMEL]:
                            for rounds: int in [0, 2]:
                                var run := escape_run({"axis": axis, "top_stamina": top_stamina, "bottom_stamina": bottom_stamina}, action_id, response_id, TOP, BOTTOM, rule_set, rounds)
                                if run == null:
                                    continue
                                var label: String = run.carryover_segment().record.exit.raw_destination
                                if not exits.has(label):
                                    exits[label] = run
                                if label == "Half Guard" and half_guard_exits.size() < 40:
                                    var seen := false
                                    var signature := JSON.stringify(run.carryover_segment().record)
                                    for known: BjjMatchWindowGateway in half_guard_exits:
                                        if JSON.stringify(known.carryover_segment().record) == signature:
                                            seen = true
                                    if not seen:
                                        half_guard_exits.append(run)


func base_record() -> Dictionary:
    return (exits["Half Guard"] as BjjMatchWindowGateway).carryover_segment().record


func mutated(path: Array, value: Variant, source: Dictionary = {}) -> Dictionary:
    var record: Dictionary = (source if not source.is_empty() else base_record()).duplicate(true)
    var node: Dictionary = record
    for index in range(path.size() - 1):
        node = node[path[index]]
    node[path[path.size() - 1]] = value
    return record


func without(path: Array) -> Dictionary:
    var record := base_record()
    var node: Dictionary = record
    for index in range(path.size() - 1):
        node = node[path[index]]
    node.erase(path[path.size() - 1])
    return record


# A refusal: stable code, no request, and whole-record equality (and an untouched interval value) before and after.
func refuses(label: String, record: Variant, code: String, interval: Variant = 5) -> void:
    var before: Variant = record.duplicate(true) if record is Dictionary or record is Array else record
    var interval_before: Variant = interval.duplicate(true) if interval is Dictionary or interval is Array else interval
    var result := BjjHalfGuardMountEdge.entry_from_record(record, interval)
    check(label + " refused", result.ok(), false)
    check(label + " code", result.error, code)
    check(label + " builds no request", result.request, {})
    check(label + " record untouched", record, before)
    check(label + " interval untouched", interval, interval_before)


func accepted(label: String, record: Dictionary, interval: Variant = 5) -> BjjHalfGuardMountEdge.Result:
    var before := record.duplicate(true)
    var result := BjjHalfGuardMountEdge.entry_from_record(record, interval)
    check(label + " accepted", [result.ok(), result.error], [true, ""])
    check(label + " entry validates", BjjHalfGuardEntry.validate(result.request), "")
    check(label + " record untouched", record, before)
    return result


func _initialize() -> void:
    find_runs()
    check("a real Half Guard exit was reached", exits.has("Half Guard"), true)
    check("a real Open Guard exit was reached", exits.has("Open Guard"), true)
    check("a real unresolved Reversal exit was reached", exits.has("Reversal"), true)
    check("several distinct real Half Guard exits were reached", half_guard_exits.size() >= 6, true)
    if not exits.has("Half Guard") or not exits.has("Open Guard") or not exits.has("Reversal"):
        push_error("Half Guard Mount edge: required real Mount exits were not reached")
        quit(1)
        return
    _test_refuses_non_records_and_malformed_records()
    _test_refuses_non_half_guard_sources_and_exits()
    _test_refuses_incomplete_tapped_and_zero_clock_records()
    _test_refusal_precedence()
    _test_interval()
    _test_vocabulary_matches_mount()
    _test_accepts_real_exits()
    _test_rekeys_by_fighter_id()
    _test_distinct_values_and_boundaries()
    _test_determinism_and_detachment()
    _test_gateway_construction()
    _test_source_gateway_untouched()
    _test_scope_and_hygiene()
    if failures > 0:
        push_error("Half Guard Mount edge: %d / %d assertions failed" % [failures, checks])
        quit(1)
        return
    print("Half Guard Mount edge PASS: %d assertions" % checks)
    quit(0)


# ---- 1. Records that are not valid A3b segments: refused with the Mount validator's own code ------------------------------------

func _test_refuses_non_records_and_malformed_records() -> void:
    for bad: Variant in [null, 5, 5.0, true, "x", [], {}, [1], {"schema": "mount_carryover"}]:
        refuses("non-record %s" % [bad], bad, "invalid_carryover_shape")
    var top_level: Array[String] = ["schema", "version", "source_position_id", "fighter_by_role", "fighters", "clock", "window", "d3b", "terminal", "exit"]
    for key in top_level:
        refuses("missing %s" % key, without([key]), "invalid_carryover_shape")
    var extra := base_record()
    extra["event_count"] = 3
    refuses("extra top-level key (the graph's envelope facts are not segment fields)", extra, "invalid_carryover_shape")
    var nested: Array = [["fighter_by_role", "top"], ["fighter_by_role", "bottom"], ["clock", "initial_seconds"], ["clock", "remaining_seconds"],
        ["window", "last_issued_id"], ["d3b", "armed"], ["terminal", "ended"], ["terminal", "submission_tapped"], ["exit", "kind"],
        ["exit", "raw_destination"], ["exit", "destination_position_id"], ["exit", "resolved"]]
    for role in ["top", "bottom"]:
        for key in ["stamina_current", "stamina_maximum", "exhaustion_latched", "behavior_remainder_units"]:
            nested.append(["fighters", role, key])
    for path: Array in nested:
        refuses("missing %s" % [path], without(path), "invalid_carryover_shape")
    # wrong types: float for int, bool for int, int for bool, string for either
    var ints: Array = [["clock", "initial_seconds"], ["clock", "remaining_seconds"], ["window", "last_issued_id"], ["fighters", "top", "stamina_current"],
        ["fighters", "bottom", "stamina_maximum"], ["fighters", "top", "behavior_remainder_units"], ["fighters", "bottom", "behavior_remainder_units"]]
    for path: Array in ints:
        for wrong: Variant in [1.0, true, "1", null]:
            refuses("%s as %s" % [path, wrong], mutated(path, wrong), "invalid_carryover_shape")
    for path: Array in [["terminal", "ended"], ["terminal", "submission_tapped"], ["exit", "resolved"], ["fighters", "top", "exhaustion_latched"], ["fighters", "bottom", "exhaustion_latched"]]:
        for wrong: Variant in [1, 0, "true", null]:
            refuses("%s as %s" % [path, wrong], mutated(path, wrong), "invalid_carryover_shape")
    refuses("schema name", mutated(["schema"], "position_graph_carryover"), "unsupported_carryover_schema")
    refuses("version 0", mutated(["version"], 0), "unsupported_carryover_schema")
    refuses("version 2", mutated(["version"], 2), "unsupported_carryover_schema")
    # fighter ids
    refuses("empty top id", mutated(["fighter_by_role", "top"], ""), "invalid_fighter_ids")
    refuses("empty bottom id", mutated(["fighter_by_role", "bottom"], ""), "invalid_fighter_ids")
    refuses("same fighter in both roles", mutated(["fighter_by_role", "bottom"], TOP), "invalid_fighter_ids")
    refuses("padded top id", mutated(["fighter_by_role", "top"], " %s" % TOP), "invalid_fighter_ids")
    refuses("padded bottom id", mutated(["fighter_by_role", "bottom"], "%s\t" % BOTTOM), "invalid_fighter_ids")
    # stamina, latch, clock, window
    refuses("current above maximum", mutated(["fighters", "top", "stamina_current"], 101), "invalid_stamina")
    refuses("negative current", mutated(["fighters", "bottom", "stamina_current"], -1), "invalid_stamina")
    refuses("zero maximum", mutated(["fighters", "top", "stamina_maximum"], 0), "invalid_stamina")
    refuses("maximum beyond exact range", mutated(["fighters", "top", "stamina_maximum"], MAXIMUM + 1), "invalid_stamina")
    refuses("remainder beyond exact range", mutated(["fighters", "bottom", "behavior_remainder_units"], MAXIMUM + 1), "invalid_stamina")
    refuses("remainder below exact range", mutated(["fighters", "bottom", "behavior_remainder_units"], -MAXIMUM - 1), "invalid_stamina")
    var healthy := base_record()
    for role in ["top", "bottom"]:
        var fighter: Dictionary = healthy.fighters[role]
        if not fighter.exhaustion_latched:
            refuses("%s healthy fighter marked latched" % role, mutated(["fighters", role, "exhaustion_latched"], true), "invalid_exhaustion_latch")
        else:
            refuses("%s exhausted fighter marked unlatched" % role, mutated(["fighters", role, "exhaustion_latched"], false), "invalid_exhaustion_latch")
    refuses("negative last issued id", mutated(["window", "last_issued_id"], -1), "invalid_window")
    refuses("initial clock 0", mutated(["clock", "initial_seconds"], 0), "invalid_clock")
    refuses("remaining above initial", mutated(["clock", "remaining_seconds"], 301), "invalid_clock")
    refuses("negative remaining", mutated(["clock", "remaining_seconds"], -1), "invalid_clock")
    refuses("initial clock beyond exact range", mutated(["clock", "initial_seconds"], MAXIMUM + 1), "invalid_clock")
    refuses("D3-B token consumed while not armed", mutated(["d3b", "token_consumed"], true, mutated(["d3b", "armed"], false)), "invalid_d3b_state")


# ---- 2. Valid Mount records whose destination is not Half Guard --------------------------------------------------------------

func _test_refuses_non_half_guard_sources_and_exits() -> void:
    var open_guard: Dictionary = (exits["Open Guard"] as BjjMatchWindowGateway).carryover_segment().record
    check("the Open Guard source is a valid resolved exit", [BjjMountCarryover.validate_segment(open_guard), open_guard.exit.resolved, open_guard.exit.destination_position_id], ["", true, "open_guard"])
    refuses("Mount -> Open Guard (resolved, wrong destination)", open_guard, BjjHalfGuardMountEdge.E_WRONG_DESTINATION)
    var reversal: Dictionary = (exits["Reversal"] as BjjMatchWindowGateway).carryover_segment().record
    check("the Reversal source is a valid unresolved exit", [BjjMountCarryover.validate_segment(reversal), reversal.exit.resolved, reversal.exit.destination_position_id], ["", false, ""])
    refuses("Mount Reversal (unresolved; no destination is invented)", reversal, BjjHalfGuardMountEdge.E_UNRESOLVED_EXIT)
    # a source that is not Mount at all
    refuses("source position half_guard", mutated(["source_position_id"], "half_guard"), "unsupported_carryover_schema")
    refuses("source position empty", mutated(["source_position_id"], ""), "unsupported_carryover_schema")
    refuses("source position capitalised", mutated(["source_position_id"], "Mount"), "unsupported_carryover_schema")
    # exit blocks that disagree with Mount's own declared mapping are invalid records, never silently accepted
    refuses("Half Guard label with the Open Guard destination", mutated(["exit", "destination_position_id"], "open_guard"), "invalid_exit")
    refuses("Half Guard label marked unresolved", mutated(["exit", "resolved"], false), "invalid_exit")
    refuses("Half Guard label with an empty destination", mutated(["exit", "destination_position_id"], ""), "invalid_exit")
    refuses("Open Guard label relabelled Half Guard", mutated(["exit", "raw_destination"], "Half Guard", open_guard), "invalid_exit")
    refuses("Reversal label relabelled Half Guard", mutated(["exit", "raw_destination"], "Half Guard", reversal), "invalid_exit")
    for label: String in ["half guard", "HALF GUARD", " Half Guard", "Half Guard ", "half_guard", "Side Control", "Mount", "Standing", ""]:
        refuses("exit label '%s'" % label, mutated(["exit", "raw_destination"], label), "invalid_exit")
    # the Mount validator checks the terminal state before the exit block, so these are terminal-state errors, not exit errors
    refuses("unknown exit kind", mutated(["exit", "kind"], "transition"), "invalid_terminal_state")
    refuses("kind none carrying a Half Guard destination", mutated(["exit", "kind"], "none"), "invalid_terminal_state")


# ---- 3. Incomplete, tapped and zero-remaining-clock records ----------------------------------------------------------------

func _test_refuses_incomplete_tapped_and_zero_clock_records() -> void:
    # real, valid, but not an exit: a fresh segment, a mid-match segment, a timeout and a real tap
    var fresh := mount_gateway()
    var fresh_record: Dictionary = fresh.carryover_segment().record
    check("a fresh segment is valid and not ended", [BjjMountCarryover.validate_segment(fresh_record), fresh_record.terminal.ended, fresh_record.exit.kind], ["", false, "none"])
    refuses("incomplete: fresh segment with no exit", fresh_record, BjjHalfGuardMountEdge.E_NOT_AN_EXIT)
    var mid := mount_gateway()
    var opened := mid.open_window_for(0)
    mid.submit(opened.values.window_id, TOP)
    var mid_record: Dictionary = mid.carryover_segment().record
    check("the mid-match segment is valid, active and has issued a window", [BjjMountCarryover.validate_segment(mid_record), mid_record.terminal.ended, mid_record.window.last_issued_id], ["", false, 1])
    refuses("incomplete: mid-match segment", mid_record, BjjHalfGuardMountEdge.E_NOT_AN_EXIT)
    var timed_out := mount_gateway()
    timed_out.open_window_for(300)
    var timeout_record: Dictionary = timed_out.carryover_segment().record
    check("the timeout segment is valid and ended with zero time", [BjjMountCarryover.validate_segment(timeout_record), timeout_record.terminal.ended, timeout_record.clock.remaining_seconds], ["", true, 0])
    refuses("zero remaining clock: real timeout (no exit)", timeout_record, BjjHalfGuardMountEdge.E_NOT_AN_EXIT)
    var tapped := tap_run()
    check("a real tap was reached", tapped != null, true)
    if tapped != null:
        var tap_record: Dictionary = tapped.carryover_segment().record
        check("the tap segment is valid, tapped and has no exit", [BjjMountCarryover.validate_segment(tap_record), tap_record.terminal.submission_tapped, tap_record.exit.kind], ["", true, "none"])
        refuses("tapped: real tap (no exit)", tap_record, BjjHalfGuardMountEdge.E_NOT_AN_EXIT)
    # an exit record that is ALSO tapped is a valid A3b record; the edge refuses it
    var tapped_exit := mutated(["terminal", "submission_tapped"], true)
    check("an exit record marked tapped still validates as a record", BjjMountCarryover.validate_segment(tapped_exit), "")
    refuses("tapped: Half Guard exit marked tapped", tapped_exit, BjjHalfGuardMountEdge.E_TAPPED)
    # zero remaining clock or not ended on an exit: the Mount validator refuses these terminal states first
    refuses("zero remaining clock: Half Guard exit with 0 seconds", mutated(["clock", "remaining_seconds"], 0), "invalid_terminal_state")
    refuses("not ended: Half Guard exit with ended false", mutated(["terminal", "ended"], false), "invalid_terminal_state")
    refuses("no exit but ended with time and no tap", mutated(["exit", "kind"], "none", mutated(["exit", "raw_destination"], "", mutated(["exit", "destination_position_id"], "", mutated(["exit", "resolved"], false)))), "invalid_terminal_state")
    # one second remaining is the smallest accepted clock (see the boundary grid)
    var one_second := accepted("one second remaining", mutated(["clock", "remaining_seconds"], 1))
    check("one second remaining is carried", one_second.request.clock.remaining_seconds, 1)


# ---- 4. Precedence: record, then edge decisions, then the interval ----------------------------------------------------------

func _test_refusal_precedence() -> void:
    refuses("a malformed record beats a bad interval", {}, "invalid_carryover_shape", 0)
    refuses("an invalid record beats a bad interval", mutated(["clock", "remaining_seconds"], 0), "invalid_terminal_state", "x")
    refuses("a non-exit record beats a bad interval", mount_gateway().carryover_segment().record, BjjHalfGuardMountEdge.E_NOT_AN_EXIT, -3)
    var open_guard: Dictionary = (exits["Open Guard"] as BjjMatchWindowGateway).carryover_segment().record
    refuses("a wrong destination beats a bad interval", open_guard, BjjHalfGuardMountEdge.E_WRONG_DESTINATION, 0)
    refuses("unresolved beats wrong destination ordering on the Reversal record", (exits["Reversal"] as BjjMatchWindowGateway).carryover_segment().record, BjjHalfGuardMountEdge.E_UNRESOLVED_EXIT, 0)
    refuses("tapped beats a bad interval", mutated(["terminal", "submission_tapped"], true), BjjHalfGuardMountEdge.E_TAPPED, MAXIMUM + 1)
    refuses("last issued id beyond the entry's range (a valid A3b value the entry refuses)", mutated(["window", "last_issued_id"], MAXIMUM + 1), "invalid_window_id")
    refuses("a bad last issued id beats a bad interval", mutated(["window", "last_issued_id"], MAXIMUM + 1), "invalid_window_id", 0)


# ---- 5. interval_seconds is the caller's, validated by the entry ------------------------------------------------------------

func _test_interval() -> void:
    for interval: int in [1, 2, 3, 5, 7, 60, 299, 300, 1000, MAXIMUM - 1, MAXIMUM]:
        var result := accepted("interval %d" % interval, base_record(), interval)
        check("interval %d is carried verbatim" % interval, result.request.interval_seconds, interval)
        check("interval %d type" % interval, typeof(result.request.interval_seconds), TYPE_INT)
    for interval: int in [0, -1, -5, MAXIMUM + 1, -MAXIMUM]:
        refuses("interval %d" % interval, base_record(), "invalid_interval", interval)
    for wrong: Variant in [5.0, 0.5, true, false, "5", "", null, [5], {"interval": 5}, Vector2i(5, 5)]:
        refuses("interval of type %s (%s)" % [type_string(typeof(wrong)), wrong], base_record(), "entry_malformed", wrong)
    # the Mount record carries no interval: the same record accepted under different intervals differs only there
    var a := BjjHalfGuardMountEdge.entry_from_record(base_record(), 5).request
    var b := BjjHalfGuardMountEdge.entry_from_record(base_record(), 9).request
    var a_rest := a.duplicate(true)
    var b_rest := b.duplicate(true)
    a_rest.erase("interval_seconds")
    b_rest.erase("interval_seconds")
    check("only interval_seconds differs between two intervals", a_rest, b_rest)
    check("the two intervals", [a.interval_seconds, b.interval_seconds], [5, 9])


# ---- 6. The edge's vocabulary is Mount's own ---------------------------------------------------------------------------------

func _test_vocabulary_matches_mount() -> void:
    check("source position id is Mount's", BjjHalfGuardMountEdge.SOURCE_POSITION_ID, BjjMountContract.POSITION_ID)
    check("source position id literal", BjjHalfGuardMountEdge.SOURCE_POSITION_ID, "mount")
    check("destination position id literal", BjjHalfGuardMountEdge.DESTINATION_POSITION_ID, "half_guard")
    check("Mount declares the Half Guard label", BjjMountContract.EXIT_DESTINATIONS.get(BjjHalfGuardMountEdge.RAW_DESTINATION, ""), BjjHalfGuardMountEdge.DESTINATION_POSITION_ID)
    var declared := BjjMountContract.transition_for(BjjHalfGuardMountEdge.RAW_DESTINATION).fields()
    check("Mount's declared transition for the label", declared, {"kind": "exit", "raw_destination": "Half Guard", "destination_position_id": "half_guard", "resolved": true})
    check("the real exit block equals Mount's declared transition", base_record().exit, declared)
    check("edge error codes are distinct and stable", [BjjHalfGuardMountEdge.E_NOT_AN_EXIT, BjjHalfGuardMountEdge.E_UNRESOLVED_EXIT, BjjHalfGuardMountEdge.E_WRONG_DESTINATION, BjjHalfGuardMountEdge.E_TAPPED],
        ["mount_edge_not_an_exit", "mount_edge_unresolved_exit", "mount_edge_wrong_destination", "mount_edge_submission_tapped"])
    check("the Half Guard engine's own position id is the destination", BjjHalfGuardRules.POSITION_ID, BjjHalfGuardMountEdge.DESTINATION_POSITION_ID)


# ---- 7. Real exits are accepted; expected values come from PUBLIC Mount views -------------------------------------------------

func _test_accepts_real_exits() -> void:
    var index := 0
    for g: BjjMatchWindowGateway in half_guard_exits:
        index += 1
        var state := g.state_fields()
        var window := g.window_fields()
        var record: Dictionary = g.carryover_segment().record
        var result := accepted("real exit %d" % index, record, 5)
        var request := result.request
        check("exit %d top id" % index, request.role_map.top, TOP)
        check("exit %d bottom id" % index, request.role_map.bottom, BOTTOM)
        check("exit %d Mount top -> Half Guard top: stamina" % index, request.fighters[TOP].stamina_current, state.top_stamina)
        check("exit %d Mount bottom -> Half Guard bottom: stamina" % index, request.fighters[BOTTOM].stamina_current, state.bottom_stamina)
        check("exit %d top maximum" % index, request.fighters[TOP].stamina_maximum, state.top_maximum)
        check("exit %d bottom maximum" % index, request.fighters[BOTTOM].stamina_maximum, state.bottom_maximum)
        check("exit %d top latch from the public band" % index, request.fighters[TOP].exhaustion_latched, state.top_band == "Exhausted")
        check("exit %d bottom latch from the public band" % index, request.fighters[BOTTOM].exhaustion_latched, state.bottom_band == "Exhausted")
        check("exit %d top remainder" % index, request.fighters[TOP].behavior_remainder_units, g._match.top_meter.remainder_units)
        check("exit %d bottom remainder" % index, request.fighters[BOTTOM].behavior_remainder_units, g._match.bottom_meter.remainder_units)
        check("exit %d initial clock" % index, request.clock.initial_seconds, state.initial_clock)
        check("exit %d remaining clock" % index, request.clock.remaining_seconds, state.clock_seconds)
        check("exit %d last issued window id" % index, request.window.last_issued_id, window.window_id)
        check("exit %d exposes exactly the entry's keys" % index, request.keys(), BjjHalfGuardEntry.KEYS)
        check("exit %d fighters are exactly the two ids" % index, request.fighters.keys(), [TOP, BOTTOM])
    # the grid really exercised distinct values
    var latches: Dictionary = {}
    var stamina_pairs: Dictionary = {}
    var windows: Dictionary = {}
    for g: BjjMatchWindowGateway in half_guard_exits:
        var state := g.state_fields()
        latches["%s/%s" % [state.top_band == "Exhausted", state.bottom_band == "Exhausted"]] = true
        stamina_pairs["%d/%d" % [state.top_stamina, state.bottom_stamina]] = true
        windows[g.window_fields().window_id] = true
    check("the real exits cover more than one latch combination", latches.size() > 1, true)
    check("the real exits cover several distinct stamina pairs", stamina_pairs.size() >= 4, true)
    check("the real exits cover several last-issued window ids", windows.size() >= 2, true)
    check("the real exits cover a latched fighter", latches.has("true/false") or latches.has("false/true") or latches.has("true/true"), true)


# ---- 8. Role re-keying: state follows the fighter ID, never the role label ------------------------------------------------

func _test_rekeys_by_fighter_id() -> void:
    var base := base_record()
    var request := accepted("default ids", base).request
    # swap ONLY the id assignment of the roles: the role-keyed numbers stay where they are, so the ids now own the other numbers
    var swapped := base.duplicate(true)
    swapped.fighter_by_role.top = BOTTOM
    swapped.fighter_by_role.bottom = TOP
    var swapped_request := accepted("swapped fighter_by_role", swapped).request
    check("swapped: role map top follows the record", swapped_request.role_map, {"top": BOTTOM, "bottom": TOP})
    check("swapped: the id that now holds Top owns Top's numbers", swapped_request.fighters[BOTTOM], base.fighters.top)
    check("swapped: the id that now holds Bottom owns Bottom's numbers", swapped_request.fighters[TOP], base.fighters.bottom)
    check("swapped: not the same assignment as the default", swapped_request.fighters[TOP] != request.fighters[TOP] or base.fighters.top == base.fighters.bottom, true)
    # a fully distinct record makes any index-based pairing visible
    var distinct := base.duplicate(true)
    distinct.fighters.top = {"stamina_current": 61, "stamina_maximum": 100, "exhaustion_latched": false, "behavior_remainder_units": 17}
    distinct.fighters.bottom = {"stamina_current": 12, "stamina_maximum": 70, "exhaustion_latched": true, "behavior_remainder_units": -9}
    check("the distinct record is a valid segment", BjjMountCarryover.validate_segment(distinct), "")
    var distinct_request := accepted("distinct values", distinct).request
    check("distinct: top id owns the top numbers", distinct_request.fighters[TOP], {"stamina_current": 61, "stamina_maximum": 100, "exhaustion_latched": false, "behavior_remainder_units": 17})
    check("distinct: bottom id owns the bottom numbers", distinct_request.fighters[BOTTOM], {"stamina_current": 12, "stamina_maximum": 70, "exhaustion_latched": true, "behavior_remainder_units": -9})
    var distinct_swapped := distinct.duplicate(true)
    distinct_swapped.fighter_by_role.top = BOTTOM
    distinct_swapped.fighter_by_role.bottom = TOP
    var distinct_swapped_request := accepted("distinct values, swapped ids", distinct_swapped).request
    check("distinct swapped: the Top role's id owns the top numbers", distinct_swapped_request.fighters[BOTTOM], {"stamina_current": 61, "stamina_maximum": 100, "exhaustion_latched": false, "behavior_remainder_units": 17})
    check("distinct swapped: the Bottom role's id owns the bottom numbers", distinct_swapped_request.fighters[TOP], {"stamina_current": 12, "stamina_maximum": 70, "exhaustion_latched": true, "behavior_remainder_units": -9})
    # roles are preserved, never swapped by the edge: Mount Top -> Half Guard Top, Mount Bottom -> Half Guard Bottom
    check("identity role map: top", distinct_swapped_request.role_map.top, distinct_swapped.fighter_by_role.top)
    check("identity role map: bottom", distinct_swapped_request.role_map.bottom, distinct_swapped.fighter_by_role.bottom)
    # unusual but valid ids, through REAL Mount runs built with those ids
    var id_pairs: Array = [["fighter_bravo", "fighter_alpha"], ["α", "β"], ["柔術", "道場"], ["a b", "c d"], ["1", "2"], ["x", "X"], ["a".repeat(64), "b".repeat(64)],
        [" x", "y "], ["🥋", "🥇"], ["Top", "Bottom"], ["bottom", "top"], ["a b", "c　d"]]
    for pair: Array in id_pairs:
        var top_id: String = pair[0]
        var bottom_id: String = pair[1]
        var run: BjjMatchWindowGateway = null
        for axis: float in [0.4, 0.8, 1.5]:
            for stamina: int in [100, 60]:
                for response_id: String in [C.TOP_RESPONSE_POST_AND_BASE, C.TOP_RESPONSE_WIDE_MOUNT_BASE, C.TOP_RESPONSE_HIP_FOLLOW_REPUMMEL]:
                    if run == null:
                        var attempt := escape_run({"axis": axis, "top_stamina": 100 - stamina + 20, "bottom_stamina": stamina}, C.BOTTOM_ELBOW_KNEE_ESCAPE, response_id, top_id, bottom_id)
                        if attempt != null and attempt.carryover_segment().record.exit.raw_destination == "Half Guard":
                            run = attempt
        check("a real Half Guard exit was reached for ids %s / %s" % [top_id, bottom_id], run != null, true)
        if run == null:
            continue
        var source: Dictionary = run.carryover_segment().record
        var state := run.state_fields()
        var made := accepted("ids %s / %s" % [top_id, bottom_id], source, 5).request
        check("ids %s / %s: role map" % [top_id, bottom_id], made.role_map, {"top": top_id, "bottom": bottom_id})
        check("ids %s / %s: fighters keyed by those ids" % [top_id, bottom_id], made.fighters.keys(), [top_id, bottom_id])
        check("ids %s / %s: top stamina follows the top id" % [top_id, bottom_id], made.fighters[top_id].stamina_current, state.top_stamina)
        check("ids %s / %s: bottom stamina follows the bottom id" % [top_id, bottom_id], made.fighters[bottom_id].stamina_current, state.bottom_stamina)
        var created := BjjHalfGuardWindowGateway.create(made)
        check("ids %s / %s: a Half Guard gateway is built" % [top_id, bottom_id], created.ok(), true)
        if created.ok():
            check("ids %s / %s: Half Guard roles keep the ids" % [top_id, bottom_id], created.gateway.roles().fields().fighter_by_role, {"top": top_id, "bottom": bottom_id})
            check("ids %s / %s: the Half Guard top pool is the top id's" % [top_id, bottom_id], created.gateway.state_fields().top_stamina, state.top_stamina)
    # the ids the Mount record cannot legally carry never reach the entry
    for bad: Array in [["", "b"], ["a", ""], ["a", "a"], [" a", "b"], ["a", "b "], ["\u0001a", "b"]]:
        var broken := mutated(["fighter_by_role", "top"], bad[0], mutated(["fighter_by_role", "bottom"], bad[1]))
        refuses("ids %s" % [bad], broken, "invalid_fighter_ids")


# ---- 9. Distinct values and boundaries survive unchanged -----------------------------------------------------------------------

func _test_distinct_values_and_boundaries() -> void:
    var base := base_record()
    # (current, maximum, latched) triples that validate; thresholds are the pool's own
    var staminas: Array = [[100, 100, false], [0, 100, true], [25, 100, true], [26, 100, true], [34, 100, true], [35, 100, false], [36, 100, false], [1, 1, false],
        [0, 1, true], [1, 7, true], [2, 7, true], [2, 7, false], [3, 7, false], [3, 20, true], [MAXIMUM, MAXIMUM, false], [0, MAXIMUM, true], [MAXIMUM - 1, MAXIMUM, false], [37, 64, false]]
    var remainders: Array = [0, 1, -1, 99, -99, MAXIMUM, -MAXIMUM]
    for top_stamina: Array in staminas:
        for bottom_stamina: Array in [staminas[1], staminas[3], staminas[5], staminas[12], staminas[0]]:
            var record := base.duplicate(true)
            record.fighters.top = {"stamina_current": top_stamina[0], "stamina_maximum": top_stamina[1], "exhaustion_latched": top_stamina[2], "behavior_remainder_units": remainders[(top_stamina[0] + 3) % remainders.size()]}
            record.fighters.bottom = {"stamina_current": bottom_stamina[0], "stamina_maximum": bottom_stamina[1], "exhaustion_latched": bottom_stamina[2], "behavior_remainder_units": remainders[(bottom_stamina[0] + 5) % remainders.size()]}
            var validity := BjjMountCarryover.validate_segment(record)
            check("stamina %s / %s is a valid Mount record" % [top_stamina, bottom_stamina], validity, "")
            if not validity.is_empty():
                continue
            var request := accepted("stamina %s / %s" % [top_stamina, bottom_stamina], record, 5).request
            check("stamina %s / %s top fighter" % [top_stamina, bottom_stamina], request.fighters[TOP], record.fighters.top)
            check("stamina %s / %s bottom fighter" % [top_stamina, bottom_stamina], request.fighters[BOTTOM], record.fighters.bottom)
            var built := BjjHalfGuardWindowGateway.create(request)
            check("stamina %s / %s builds a gateway" % [top_stamina, bottom_stamina], built.ok(), true)
            if built.ok():
                var view := built.gateway.state_fields()
                check("stamina %s / %s top pool restored" % [top_stamina, bottom_stamina], [view.top_stamina, view.top_maximum, view.top_latched], [top_stamina[0], top_stamina[1], top_stamina[2]])
                check("stamina %s / %s bottom pool restored" % [top_stamina, bottom_stamina], [view.bottom_stamina, view.bottom_maximum, view.bottom_latched], [bottom_stamina[0], bottom_stamina[1], bottom_stamina[2]])
    for remainder: int in remainders:
        for role in ["top", "bottom"]:
            var record := mutated(["fighters", role, "behavior_remainder_units"], remainder)
            var request := accepted("%s remainder %d" % [role, remainder], record).request
            check("%s remainder %d is carried" % [role, remainder], request.fighters[TOP if role == "top" else BOTTOM].behavior_remainder_units, remainder)
            var snapshot := BjjHalfGuardWindowGateway.create(request).gateway.snapshot()
            check("%s remainder %d reaches the Half Guard meter" % [role, remainder], snapshot.fighters[TOP if role == "top" else BOTTOM].behavior_remainder_units, remainder)
    # clock and window boundaries
    for clock: Array in [[300, 300], [300, 299], [300, 6], [300, 5], [300, 1], [1, 1], [2, 1], [2, 2], [MAXIMUM, MAXIMUM], [MAXIMUM, 1], [MAXIMUM, MAXIMUM - 1], [3600, 1789]]:
        var record := mutated(["clock", "remaining_seconds"], clock[1], mutated(["clock", "initial_seconds"], clock[0]))
        var request := accepted("clock %s" % [clock], record).request
        check("clock %s carried" % [clock], request.clock, {"initial_seconds": clock[0], "remaining_seconds": clock[1]})
        var view := BjjHalfGuardWindowGateway.create(request).gateway.state_fields()
        check("clock %s reaches the Half Guard clock" % [clock], [view.initial_clock, view.clock_seconds], [clock[0], clock[1]])
    for window_id: int in [0, 1, 2, 5, 99, 1000, MAXIMUM - 1, MAXIMUM]:
        var record := mutated(["window", "last_issued_id"], window_id)
        var request := accepted("last issued id %d" % window_id, record).request
        check("last issued id %d carried" % window_id, request.window.last_issued_id, window_id)
        var gateway := BjjHalfGuardWindowGateway.create(request).gateway
        check("last issued id %d seeds the gateway's window view" % window_id, gateway.window_fields().window_id, window_id)
        if window_id < MAXIMUM - 1:
            var next := gateway.open_window()
            check("the next window after %d is %d" % [window_id, window_id + 1], [next.ok(), next.values.window_id], [true, window_id + 1])
    # D3-B state never travels: any D3-B flags give the same request
    var reference := BjjHalfGuardMountEdge.entry_from_record(base, 5).request
    for armed: bool in [false, true]:
        for consumed: bool in [false, true]:
            for previous: bool in [false, true]:
                if consumed and not armed:
                    continue
                var record := mutated(["d3b", "previous_exhausted"], previous, mutated(["d3b", "token_consumed"], consumed, mutated(["d3b", "armed"], armed)))
                check("D3-B %s/%s/%s does not change the request" % [armed, consumed, previous], BjjHalfGuardMountEdge.entry_from_record(record, 5).request, reference)


# ---- 10. Determinism and detachment ------------------------------------------------------------------------------------------

func _test_determinism_and_detachment() -> void:
    var base := base_record()
    var first := BjjHalfGuardMountEdge.entry_from_record(base, 5)
    var second := BjjHalfGuardMountEdge.entry_from_record(base, 5)
    check("the same record and interval give the same request", first.request, second.request)
    check("the request is a new dictionary each call", is_same(first.request, second.request), false)
    check("the nested dictionaries are new each call", [is_same(first.request.fighters, second.request.fighters), is_same(first.request.clock, second.request.clock), is_same(first.request.role_map, second.request.role_map), is_same(first.request.window, second.request.window)], [false, false, false, false])
    # mutating a request cannot reach the record, and the record cannot reach an earlier request
    var before := base.duplicate(true)
    first.request.fighters[TOP].stamina_current = -77
    first.request.clock.remaining_seconds = -77
    first.request.role_map.top = "mutated"
    first.request.window.last_issued_id = -77
    first.request.erase("interval_seconds")
    check("mutating a request leaves the record equal", base, before)
    check("mutating a request leaves a second request alone", second.request, BjjHalfGuardMountEdge.entry_from_record(before, 5).request)
    var request_before := second.request.duplicate(true)
    base.fighters.top.stamina_current = 1
    base.clock.remaining_seconds = 1
    base.fighter_by_role.top = "mutated"
    check("mutating the record afterwards leaves an earlier request alone", second.request, request_before)
    # repeated and interleaved calls do not interact (the adapter keeps no state)
    var records: Array = []
    for g: BjjMatchWindowGateway in half_guard_exits:
        records.append(g.carryover_segment().record)
    var forward: Array = []
    for record: Dictionary in records:
        forward.append(BjjHalfGuardMountEdge.entry_from_record(record, 7).request)
    var backward: Array = []
    for index in range(records.size() - 1, -1, -1):
        BjjHalfGuardMountEdge.entry_from_record(exits["Open Guard"].carryover_segment().record, 7)
        backward.push_front(BjjHalfGuardMountEdge.entry_from_record(records[index], 7).request)
    check("call order does not matter", forward, backward)


# ---- 11. The generated request builds a Half Guard gateway ---------------------------------------------------------------------

func _test_gateway_construction() -> void:
    for g: BjjMatchWindowGateway in half_guard_exits:
        var record: Dictionary = g.carryover_segment().record
        var state := g.state_fields()
        for interval: int in [1, 5, 7]:
            var request := BjjHalfGuardMountEdge.entry_from_record(record, interval).request
            var created := BjjHalfGuardWindowGateway.create(request)
            check("gateway builds (interval %d)" % interval, [created.ok(), created.error], [true, ""])
            if not created.ok():
                continue
            var h := created.gateway
            var view := h.state_fields()
            check("half guard top stamina", view.top_stamina, state.top_stamina)
            check("half guard bottom stamina", view.bottom_stamina, state.bottom_stamina)
            check("half guard maxima", [view.top_maximum, view.bottom_maximum], [state.top_maximum, state.bottom_maximum])
            check("half guard latches", [view.top_latched, view.bottom_latched], [state.top_band == "Exhausted", state.bottom_band == "Exhausted"])
            check("half guard clock", [view.clock_seconds, view.initial_clock], [state.clock_seconds, state.initial_clock])
            check("half guard starts un-ended with no exit", [view.ended, view.exit_destination], [false, ""])
            check("half guard seeds the window counter with the last issued id", h.window_fields(), {"open": false, "window_id": g.window_fields().window_id, "fighter_id": "", "role": ""})
            check("half guard roles hold the Mount fighters on the same roles", h.roles().fields().fighter_by_role, g.roles().fields().fighter_by_role)
            var opened := h.open_window()
            if state.clock_seconds <= interval:
                check("a clock no longer than the interval closes at the first window", [opened.ok(), opened.values.closed], [true, true])
            else:
                check("the next window id continues the Mount count", [opened.ok(), opened.values.window_id], [true, g.window_fields().window_id + 1])
                check("simulated time advances by the CALLER's interval", h.state_fields().clock_seconds, state.clock_seconds - interval)
                check("Top (initiator) owns the first Half Guard window", [opened.values.role, opened.values.fighter_id], ["top", record.fighter_by_role.top])
    # the Half Guard gateway built from an edge request is a normal gateway: it refuses what a normal one refuses
    var request := BjjHalfGuardMountEdge.entry_from_record(base_record(), 5).request
    var h := BjjHalfGuardWindowGateway.create(request).gateway
    var opened := h.open_window()
    check("a stale window id is refused", h.submit(opened.values.window_id + 1, opened.values.fighter_id).ok(), false)
    check("the right window id passes", h.submit(opened.values.window_id, opened.values.fighter_id).ok(), true)


# ---- 12. Building an entry changes nothing in the source gateway ---------------------------------------------------------------

func _test_source_gateway_untouched() -> void:
    for label: String in ["Half Guard", "Open Guard", "Reversal"]:
        var g: BjjMatchWindowGateway = exits[label]
        var before := everything(g)
        var record: Dictionary = g.carryover_segment().record
        var result := BjjHalfGuardMountEdge.entry_from_record(record, 5)
        check("%s: whole source gateway unchanged after the edge call" % label, everything(g), before)
        check("%s: expected verdict" % label, result.ok(), label == "Half Guard")
        if result.ok():
            var h := BjjHalfGuardWindowGateway.create(result.request).gateway
            h.open_window()
            var opened := h.open_window()
            if opened.ok() and not opened.values.closed:
                h.submit(opened.values.window_id, opened.values.fighter_id)
            check("%s: whole source gateway unchanged after Half Guard construction and play" % label, everything(g), before)
            check("%s: the source segment re-exports identically" % label, g.carryover_segment().record, record)
    # the source record's own state keys do not change either, and the source gateway still refuses further play
    var spent: BjjMatchWindowGateway = exits["Half Guard"]
    var source_state := spent.state_fields()
    for key: String in MOUNT_STATE_KEYS:
        check("source %s still published" % key, spent.state_fields().has(key), true)
    BjjHalfGuardMountEdge.entry_from_record(spent.carryover_segment().record, 5)
    check("source public state is untouched by repeated edge calls", spent.state_fields(), source_state)
    check("the source remains an ended Mount segment", [spent.is_terminal(), spent.state_fields().exit_destination], [true, "Half Guard"])
    check("the source still refuses a new window", spent.open_window().ok(), false)


# ---- 13. Scope: the edge is pure, static and Mount-record-only ------------------------------------------------------------------

func _test_scope_and_hygiene() -> void:
    var file := FileAccess.open(SCRIPT_PATH, FileAccess.READ)
    check("edge source readable", file != null, true)
    if file == null:
        return
    var code_lines: Array[String] = []
    for source_line: String in file.get_as_text().split("\n"):
        code_lines.append(source_line.split("#")[0])  # comments may name what the code must not use
    var text := "\n".join(code_lines)
    for token: String in ["randi", "randf", "RandomNumberGenerator", "Time.", "OS.get_ticks", "await", "get_tree", "Engine.get_frames", "FileAccess", "preload(",
            "BjjMountMatch", "BjjMatchWindowGateway", "BjjMountContract.create", "BjjPositionGraphMatch", "BjjHalfGuardMatch", "BjjHalfGuardWindowGateway", "_match", "feint", "sealed",
            "BjjFighterSnapshotAdapter", "BjjBehaviorStaminaPolicy", "BjjD3BController", "set_current", "BjjStaminaPool.create"]:
        check("edge has no %s" % token, text.contains(token), false)
    var mount_references: Array[String] = []
    for code_line: String in code_lines:
        for token: String in ["BjjMountContract", "BjjMountCarryover"]:
            if code_line.contains(token):
                mount_references.append(token)
    check("the edge uses only Mount's contract constants/transition and the carry-over validator", mount_references.size() > 0, true)
    for code_line: String in code_lines:
        if code_line.contains("BjjMount") and not (code_line.contains("BjjMountContract.POSITION_ID") or code_line.contains("BjjMountCarryover.validate_segment") or code_line.contains("BjjMountCarryover.ROLES")):
            check("unexpected Mount reference: %s" % code_line.strip_edges(), false, true)
    check("every method on the edge is static", text.count("\nfunc "), 0)
    check("the edge keeps no state of its own (no top-level variable)", text.count("\nvar "), 0)
    # the qualified engine sources still know nothing about Mount (the edge is the only bridge)
    for path: String in ["half_guard_rules", "half_guard_catalog", "half_guard_resolver", "half_guard_entry", "half_guard_match", "half_guard_contract", "half_guard_window_gateway"]:
        var engine := FileAccess.open("res://scripts/positions/half_guard/%s.gd" % path, FileAccess.READ)
        check("%s readable" % path, engine != null, true)
        if engine != null:
            var engine_code: Array[String] = []
            for line: String in engine.get_as_text().split("\n"):
                engine_code.append(line.split("#")[0])
            check("%s never references Mount" % path, "\n".join(engine_code).contains("BjjMount"), false)
