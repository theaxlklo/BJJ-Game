extends SceneTree

# Negative-first tests for the opt-in Mount -> Half Guard graph integration (B1d, HALF_GUARD_V0_PROPOSAL.md section 6).
# Source runs are REAL Mount runs through the public graph/gateway API (never injected state). Expected values are literals, come
# from a twin driven through the bare Mount gateway with identical inputs, or come from the validated request; the graph is never
# compared with itself. The only private reads are read-only (the retained Mount gateway and the Half Guard slot), which is how the
# frozen-segment and "exactly one active owner" invariants are observed.
const C = preload("res://scripts/positions/mount/mount_catalog.gd")
const TOP: String = "fighter_alpha"
const BOTTOM: String = "fighter_bravo"
const HALTED_CODE: String = "halted_unsupported_transition"

var checks: int = 0
var failures: int = 0
var plans: Array = []            # real Mount -> Half Guard exit plans (distinct stamina / latch / clock / window / interval)
var open_guard_plan: Dictionary = {}
var reversal_plan: Dictionary = {}


func check(label: String, actual: Variant, expected: Variant) -> void:
    checks += 1
    if typeof(actual) != typeof(expected) or JSON.stringify(actual, "", true, true) != JSON.stringify(expected, "", true, true):
        failures += 1
        if failures <= 40:
            push_error("%s: got %s expected %s" % [label, JSON.stringify(actual).left(500), JSON.stringify(expected).left(500)])


func same(label: String, actual: Variant, expected: Variant) -> void:
    check(label, actual, expected)


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


# ---- Construction -----------------------------------------------------------------------------------------------------------

func config_of(plan: Dictionary) -> Dictionary:
    var configuration := {"rules": plain_rules() if plan.rule_set == "plain" else rules()}
    configuration.merge(plan.config, true)
    return configuration


func make_default(plan: Dictionary) -> BjjPositionGraphMatch:
    return BjjPositionGraphMatch.create(config_of(plan), TOP, BOTTOM).graph


func make_empty(plan: Dictionary) -> BjjPositionGraphMatch:
    return BjjPositionGraphMatch.create_with_receivers(config_of(plan), TOP, BOTTOM, {}).graph


func make_optin(plan: Dictionary, receivers: Variant = null) -> BjjPositionGraphMatch:
    var table: Variant = BjjPositionGraphMatch.default_receivers() if receivers == null else receivers
    var created := BjjPositionGraphMatch.create_with_receivers(config_of(plan), TOP, BOTTOM, table)
    check("opt-in graph built", [created.ok(), created.error], [true, ""])
    return created.graph


func make_bare(plan: Dictionary) -> BjjMatchWindowGateway:
    return BjjMatchWindowGateway.create(config_of(plan), TOP, BOTTOM).gateway


# ---- Views and fingerprints --------------------------------------------------------------------------------------------------

func mount_views(gateway: BjjMatchWindowGateway) -> Dictionary:
    return {"state": gateway.state_fields(), "history": gateway.history_fields(), "controller": gateway.controller_fields(), "window": gateway.window_fields(),
        "behavior": gateway.behavior_fields(), "roles": gateway.roles().fields(), "terminal": gateway.is_terminal(), "commitment": gateway.selected_commitment(),
        "segment": gateway.carryover_segment().record}


func graph_views(g: BjjPositionGraphMatch) -> Dictionary:
    return {"status": g.status(), "events": g.events(), "blocked": g.blocked_transition(), "active": g.active_position_id(), "state": g.state_fields(),
        "history": g.history_fields(), "controller": g.controller_fields(), "window": g.window_fields(), "behavior": g.behavior_fields(),
        "roles": g.roles().fields(), "commitment": g.selected_commitment(), "export_error": g.carryover_export().error}


# Everything observable, including the retained Mount segment and the Half Guard slot (read-only private reads).
func everything(g: BjjPositionGraphMatch) -> Dictionary:
    var all := graph_views(g)
    all["mount"] = mount_views(g._gateway)
    all["half_guard"] = g._half_guard.snapshot() if g._half_guard != null else {}
    return all


# Exactly one active positional relationship and exactly one command-accepting simulation owner while the graph is active.
func single_active(label: String, g: BjjPositionGraphMatch) -> void:
    var active := g.active_position_id()
    check(label + ": the active position is one of the two", ["mount", "half_guard"].has(active), true)
    check(label + ": the active position agrees with the Half Guard slot", g._half_guard != null, active == "half_guard")
    if g.status() == "active":
        check(label + ": the roles view is the active position's", g.roles().fields().position_id, active)
        check(label + ": the active position is playable", g.state_fields().ended, false)
        if g._half_guard != null:
            check(label + ": the retained Mount segment is terminal history, never a second owner", [g._gateway.is_terminal(), g._gateway.window_fields().open], [true, false])
            check(label + ": a frozen Mount segment accepts no window", g._gateway.open_window_for(0).ok(), false)
        else:
            check(label + ": no Half Guard slot while Mount is active", g._half_guard == null, true)


func strip(report: BjjMatchWindowGateway.Report) -> Dictionary:
    var values := report.values.duplicate(true)
    values.erase("graph")
    return {"error": report.error, "values": values}


# ---- Directed real runs ------------------------------------------------------------------------------------------------------

# Drives `target` (graph or bare gateway; both expose the same command and view names) through one directed Mount run: rounds of
# real Top/Bottom RESET windows, then Bottom prepares if needed and attempts one escape. Returns the trace and whether it exited.
func run_plan(target: Variant, plan: Dictionary, observe: bool = true) -> Dictionary:
    var trace: Array = []
    var out := {"trace": trace, "exited": false, "events_before_exit": -1, "exit_window_id": -1}
    var is_graph: bool = target is BjjPositionGraphMatch
    for index in range(int(plan.rounds)):
        var top_round: BjjMatchWindowGateway.Report = target.open_window_for(0)
        trace.append(strip(top_round))
        if not top_round.ok():
            return out
        var top_done: BjjMatchWindowGateway.Report = target.submit(top_round.values.window_id, TOP)
        trace.append(strip(top_done))
        if not top_done.ok():
            return out
        var bottom_round: BjjMatchWindowGateway.Report = target.open_window_for(0)
        trace.append(strip(bottom_round))
        if not bottom_round.ok():
            return out
        var bottom_done: BjjMatchWindowGateway.Report = target.submit(bottom_round.values.window_id, BOTTOM)
        trace.append(strip(bottom_done))
        if not bottom_done.ok() or str(bottom_done.values.transition.raw_destination) != "":
            return out
        if is_graph and observe:
            single_active("round %d" % index, target)
    var opened: BjjMatchWindowGateway.Report = target.open_window_for(0)
    trace.append(strip(opened))
    if not opened.ok():
        return out
    var passed: BjjMatchWindowGateway.Report = target.submit(opened.values.window_id, TOP)
    trace.append(strip(passed))
    if not passed.ok():
        return out
    var second: BjjMatchWindowGateway.Report = target.open_window_for(0)
    trace.append(strip(second))
    if not second.ok():
        return out
    var tries := 0
    while plan.action == C.BOTTOM_TRAP_AND_ROLL_ESCAPE and not target.action_options(BOTTOM).available_ids().has(plan.action) and tries < 6:
        tries += 1
        var prep: BjjMatchWindowGateway.Report = target.submit(target.window_fields().window_id, BOTTOM, C.BOTTOM_BRIDGE, plan.response)
        trace.append(strip(prep))
        if not prep.ok() or str(prep.values.transition.raw_destination) != "":
            return out
        var top_window: BjjMatchWindowGateway.Report = target.open_window_for(0)
        trace.append(strip(top_window))
        if not top_window.ok():
            return out
        var top_pass: BjjMatchWindowGateway.Report = target.submit(top_window.values.window_id, TOP)
        trace.append(strip(top_pass))
        if not top_pass.ok() or not target.open_window_for(0).ok():
            return out
    if not target.action_options(BOTTOM).available_ids().has(plan.action):
        return out
    if is_graph:
        out.events_before_exit = target.events().size()
    out.exit_window_id = target.window_fields().window_id
    var exit_report: BjjMatchWindowGateway.Report = target.submit(target.window_fields().window_id, BOTTOM, plan.action, plan.response)
    trace.append(strip(exit_report))
    out.exited = exit_report.ok() and str(exit_report.values.transition.raw_destination) == plan.label
    if is_graph and observe:
        single_active("after the exit submit", target)
    return out


func find_plans() -> void:
    var seen: Dictionary = {}
    for rule_set: String in ["modern", "plain"]:
        for interval: int in [5, 7]:
            for axis: float in [0.2, 0.4, 0.8, 1.5, 3.0]:
                for top_stamina: int in [100, 20, 60]:
                    for bottom_stamina: int in [100, 60, 20]:
                        for action_id: String in [C.BOTTOM_ELBOW_KNEE_ESCAPE, C.BOTTOM_TRAP_AND_ROLL_ESCAPE]:
                            for response_id: String in [C.TOP_RESPONSE_POST_AND_BASE, C.TOP_RESPONSE_WIDE_MOUNT_BASE, C.TOP_RESPONSE_HIP_FOLLOW_REPUMMEL]:
                                for rounds: int in [0, 2]:
                                    var plan := {"rule_set": rule_set, "config": {"axis": axis, "top_stamina": top_stamina, "bottom_stamina": bottom_stamina, "interval": interval},
                                        "action": action_id, "response": response_id, "rounds": rounds, "label": ""}
                                    var bare := make_bare(plan)
                                    plan.label = "Half Guard"  # placeholder: the real label is read from the bare gateway after the run
                                    run_plan(bare, plan, false)
                                    var label: String = bare.state_fields().exit_destination
                                    if label.is_empty():
                                        continue
                                    plan.label = label
                                    var signature := JSON.stringify(bare.carryover_segment().record) + label
                                    if seen.has(signature):
                                        continue
                                    seen[signature] = true
                                    if label == "Half Guard" and plans.size() < 10:
                                        plans.append(plan)
                                    elif label == "Open Guard" and open_guard_plan.is_empty():
                                        open_guard_plan = plan
                                    elif label == "Reversal" and reversal_plan.is_empty():
                                        reversal_plan = plan


func _initialize() -> void:
    find_plans()
    check("several real Half Guard exit plans were found", plans.size() >= 6, true)
    check("a real Open Guard exit plan was found", open_guard_plan.is_empty(), false)
    check("a real Reversal exit plan was found", reversal_plan.is_empty(), false)
    if plans.size() < 6 or open_guard_plan.is_empty() or reversal_plan.is_empty():
        push_error("Half Guard graph: required real Mount exits were not reached")
        quit(1)
        return
    _test_invalid_receivers_build_no_graph()
    _test_default_graph_and_empty_table_are_the_mount_only_graph()
    _test_other_exits_still_halt_on_an_optin_graph()
    _test_valid_transition()
    _test_commands_after_the_transition()
    _test_half_guard_exits_timeout_and_halts()
    _test_faulty_receivers_halt_without_partial_activation()
    _test_receiver_seam_contract()
    _test_double_replay_is_deterministic()
    _test_static_classification_and_scope()
    if failures > 0:
        push_error("Half Guard graph: %d / %d assertions failed" % [failures, checks])
        quit(1)
        return
    print("Half Guard graph PASS: %d assertions" % checks)
    quit(0)


# ---- 1. A bad receiver table builds no graph ----------------------------------------------------------------------------------

func _test_invalid_receivers_build_no_graph() -> void:
    var good := Callable(self, "_receiver_two_arguments")
    var one_argument := Callable(self, "_receiver_one_argument")
    var three_arguments := Callable(self, "_receiver_three_arguments")
    var freed := Node.new()
    var freed_callable := Callable(freed, "get_name")
    freed.free()
    var bad_tables: Array = [
        ["null", null], ["int", 5], ["string", "half_guard"], ["array", [good]], ["callable", good], ["float", 1.5], ["bool", true],
        ["unknown key open_guard", {"open_guard": good}], ["unknown key side_control", {"side_control": good}], ["unknown key closed_guard", {"closed_guard": good}],
        ["key mount", {"mount": good}], ["empty key", {"": good}], ["wrong case", {"Half Guard": good}], ["padded key", {" half_guard": good}],
        ["int key", {1: good}], ["StringName key", {&"half_guard": good}], ["null key", {null: good}],
        ["null value", {"half_guard": null}], ["string value", {"half_guard": "x"}], ["int value", {"half_guard": 3}], ["dictionary value", {"half_guard": {}}],
        ["array value", {"half_guard": [good]}], ["empty callable", {"half_guard": Callable()}], ["freed target", {"half_guard": freed_callable}],
        ["one argument", {"half_guard": one_argument}], ["three arguments", {"half_guard": three_arguments}],
        ["valid plus unknown", {"half_guard": good, "open_guard": good}], ["valid plus bad value", {"half_guard": good, "extra": null}],
    ]
    var plan: Dictionary = plans[0]
    for entry: Array in bad_tables:
        var table: Variant = entry[1]
        var before: Variant = table.duplicate(true) if table is Dictionary or table is Array else table
        var created := BjjPositionGraphMatch.create_with_receivers(config_of(plan), TOP, BOTTOM, table)
        check("%s: refused" % entry[0], [created.ok(), created.error, created.graph == null], [false, "invalid_receivers", true])
        check("%s: the caller's table is untouched" % entry[0], table, before)
        # receivers are validated before the graph (and before configuration), so no combination builds anything
        var worse := BjjPositionGraphMatch.create_with_receivers({}, "", "", table)
        check("%s: beats configuration and id errors" % entry[0], [worse.error, worse.graph == null], ["invalid_receivers", true])
    # an accepted table is copied: later changes by the caller cannot register, unregister or swap a receiver
    var table := {"half_guard": good}
    var built := BjjPositionGraphMatch.create_with_receivers(config_of(plan), TOP, BOTTOM, table)
    check("a valid table builds a graph", [built.ok(), built.error], [true, ""])
    table.clear()
    table["open_guard"] = good
    check("the graph kept its own copy of the table", built.graph._receivers.keys(), ["half_guard"])
    check("the valid graph is Mount-active with an empty Half Guard slot", [built.graph.active_position_id(), built.graph._half_guard == null], ["mount", true])
    # configuration errors with an EMPTY table are exactly `create`'s errors
    for configuration: Dictionary in [{}, {"rules": rules(), "production": false}, {"rules": rules(), "clock": 0}, {"rules": rules(), "interval": 0}, {"rules": rules(), "axis": -1.0},
            {"rules": rules(), "unknown": 1}, {"rules": rules(), "clock": 5.0}]:
        var plain := BjjPositionGraphMatch.create(configuration, TOP, BOTTOM)
        var opt := BjjPositionGraphMatch.create_with_receivers(configuration, TOP, BOTTOM, {})
        check("empty table error equals create for %s" % [configuration.keys()], [opt.error, opt.graph == null], [plain.error, plain.graph == null])
    for ids: Array in [["", "b"], ["a", ""], ["a", "a"], [" a", "b"]]:
        var plain := BjjPositionGraphMatch.create({"rules": rules()}, ids[0], ids[1])
        var opt := BjjPositionGraphMatch.create_with_receivers({"rules": rules()}, ids[0], ids[1], {})
        check("empty table id error equals create for %s" % [ids], [opt.error, opt.graph == null], [plain.error, plain.graph == null])
        var with_receiver := BjjPositionGraphMatch.create_with_receivers({"rules": rules()}, ids[0], ids[1], {"half_guard": good})
        check("a valid table does not hide the id error for %s" % [ids], [with_receiver.error, with_receiver.graph == null], [plain.error, plain.graph == null])


func _receiver_two_arguments(record: Dictionary, interval_seconds: int) -> BjjHalfGuardWindowGateway.Creation:
    return BjjPositionGraphMatch.default_receivers()["half_guard"].call(record, interval_seconds)


func _receiver_one_argument(record: Dictionary) -> BjjHalfGuardWindowGateway.Creation:
    return null


func _receiver_three_arguments(record: Dictionary, interval_seconds: int, extra: int) -> BjjHalfGuardWindowGateway.Creation:
    return null


# ---- 2. Default behavior is preserved ---------------------------------------------------------------------------------------

func _test_default_graph_and_empty_table_are_the_mount_only_graph() -> void:
    for plan: Dictionary in plans:
        var twin := make_bare(plan)
        var twin_run := run_plan(twin, plan)
        var default_graph := make_default(plan)
        var empty_graph := make_empty(plan)
        var default_run := run_plan(default_graph, plan)
        var empty_run := run_plan(empty_graph, plan)
        check("twin run exits", twin_run.exited, true)
        # command-for-command lockstep: every report (minus the graph's own block) equals the bare gateway's
        check("default graph reports equal the bare gateway's", default_run.trace, twin_run.trace)
        check("empty-table graph reports equal the bare gateway's", empty_run.trace, twin_run.trace)
        check("default graph exited", default_run.exited, true)
        check("empty-table graph exited", empty_run.exited, true)
        # the opt-in graph with no receivers is observably the default graph
        check("empty table is observably identical to create (every view, event and the retained Mount segment)", everything(empty_graph), everything(default_graph))
        # and it halts exactly as the Mount-only graph always did
        check("default graph halts", default_graph.status(), "halted_at_unsupported_transition")
        check("default graph still reports Mount as the only position", [default_graph.active_position_id(), default_graph._half_guard == null], ["mount", true])
        check("default graph blocked transition", default_graph.blocked_transition(),
            {"from_position_id": "mount", "label": "Half Guard", "reason": "destination_not_implemented", "destination_position_id": "half_guard"})
        var kinds: Array = []
        for event: Dictionary in default_graph.events():
            kinds.append(event.kind)
        check("default graph event tail", kinds.slice(-2), ["decision_accepted", "transition_blocked"])
        check("default graph halts at the event index the Mount-only graph always did", default_graph.events().size(), default_run.events_before_exit + 2)
        check("halt event index", default_graph.events()[-1].index, default_run.events_before_exit + 2)
        check("default graph keeps the Mount state the bare gateway reached", mount_views(default_graph._gateway), mount_views(twin))
        check("default export is the unchanged halted envelope", default_graph.carryover_export().ok(), true)
        for command: Array in [["open_window", []], ["submit", [1, TOP]]]:
            var before := everything(default_graph)
            var report: BjjMatchWindowGateway.Report = default_graph.callv(command[0], command[1])
            check("halted default graph refuses %s" % command[0], [report.ok(), report.error], [false, HALTED_CODE])
            check("halted default graph unchanged after %s" % command[0], everything(default_graph), before)
    # a default graph is built by `create` alone: no receiver can ever be registered on it
    var plain := make_default(plans[0])
    check("a default graph has no receivers and the default cadence", [plain._receivers, plain._interval_seconds], [{}, BjjMountRules.DEFAULT_INTERVAL_SECONDS])


# ---- 3. Other exits are unchanged on an opt-in graph --------------------------------------------------------------------------

func _test_other_exits_still_halt_on_an_optin_graph() -> void:
    for plan: Dictionary in [open_guard_plan, reversal_plan]:
        var calls: Array = []
        var counting := func(record: Dictionary, interval_seconds: int) -> BjjHalfGuardWindowGateway.Creation:
            calls.append([record, interval_seconds])
            return BjjPositionGraphMatch.default_receivers()["half_guard"].call(record, interval_seconds)
        var default_graph := make_default(plan)
        var optin := make_optin(plan, {"half_guard": counting})
        var default_run := run_plan(default_graph, plan)
        var optin_run := run_plan(optin, plan)
        check("%s: exits on both graphs" % plan.label, [default_run.exited, optin_run.exited], [true, true])
        check("%s: no receiver is called" % plan.label, calls.size(), 0)
        check("%s: identical to the default graph (views, events, blocked, Mount segment)" % plan.label, everything(optin), everything(default_graph))
        check("%s: halted at the Mount segment" % plan.label, [optin.status(), optin.active_position_id(), optin._half_guard == null], ["halted_at_unsupported_transition", "mount", true])
        check("%s: reason" % plan.label, optin.blocked_transition().reason, "unresolved_destination" if plan.label == "Reversal" else "destination_not_implemented")
        check("%s: the unchanged v1 envelope still exports" % plan.label, optin.carryover_export().ok(), true)
        check("%s: and validates" % plan.label, BjjMountCarryover.validate_envelope(optin.carryover_export().record), "")


# ---- 4. A valid Mount exit to Half Guard commits atomically ---------------------------------------------------------------------

func _test_valid_transition() -> void:
    var index := 0
    for plan: Dictionary in plans:
        index += 1
        var twin := make_bare(plan)
        run_plan(twin, plan)
        var mount_at_exit := mount_views(twin)
        var record: Dictionary = mount_at_exit.segment
        var g := make_optin(plan)
        var run := run_plan(g, plan)
        var label := "plan %d" % index
        check(label + ": exited", run.exited, true)
        check(label + ": the graph is active, not halted, and Half Guard is the only active position", [g.status(), g.active_position_id(), g.blocked_transition()], ["active", "half_guard", {}])
        # events: decision_accepted -> transition_committed, nothing between, nothing after
        var events := g.events()
        check(label + ": exactly two events were added by the exit", events.size(), int(run.events_before_exit) + 2)
        check(label + ": decision_accepted", events[-2], {"kind": "decision_accepted", "window_id": run.exit_window_id, "fighter_id": BOTTOM, "role": "bottom",
            "decision": "bottom_decision", "index": int(run.events_before_exit) + 1})
        check(label + ": transition_committed", events[-1], {"kind": "transition_committed", "from_position_id": "mount", "to_position_id": "half_guard", "label": "Half Guard",
            "index": int(run.events_before_exit) + 2})
        for position in range(events.size()):
            if int(events[position].index) != position + 1:
                check(label + ": event indices are 1..n", events[position].index, position + 1)
        var committed := 0
        var blocked_events := 0
        for event: Dictionary in events:
            committed += 1 if event.kind == "transition_committed" else 0
            blocked_events += 1 if event.kind == "transition_blocked" else 0
        check(label + ": exactly one transition_committed and no transition_blocked", [committed, blocked_events], [1, 0])
        # no window, no clock, no stamina during the transition
        check(label + ": no window is open and the counter is Mount's last issued id", g.window_fields(), {"open": false, "window_id": record.window.last_issued_id, "fighter_id": "", "role": ""})
        check(label + ": the exit window stays consumed", g.window_fields().window_id, run.exit_window_id)
        # continuity: identities, pools, latches, meters, clocks, windows
        var views := g.state_fields()
        var mount_state: Dictionary = mount_at_exit.state
        for key: String in ["top_stamina", "bottom_stamina", "top_maximum", "bottom_maximum", "top_band", "bottom_band", "clock_seconds", "initial_clock"]:
            check(label + ": %s carries over" % key, views[key], mount_state[key])
        check(label + ": clock equals the record's", [views.clock_seconds, views.initial_clock], [record.clock.remaining_seconds, record.clock.initial_seconds])
        check(label + ": fresh Half Guard axis, band and initiative", [views.axis_tenths, views.band, views.initiator, views.ended, views.exit_destination], [5, 0, "top", false, ""])
        check(label + ": fresh readiness", [views.top_base, views.bottom_frame], [1, 1])
        var snapshot: Dictionary = g._half_guard.snapshot()
        for role: String in ["top", "bottom"]:
            var id: String = record.fighter_by_role[role]
            check(label + ": %s fighter %s: stamina, maximum, latch and meter" % [role, id], snapshot.fighters[id], record.fighters[role])
        check(label + ": roles keep both fighter ids on the same roles", g.roles().fields().fighter_by_role, {"top": TOP, "bottom": BOTTOM})
        check(label + ": the roles view is Half Guard's", g.roles().fields().position_id, "half_guard")
        check(label + ": Top holds the initiative", g.roles().fields().initiative_id, TOP)
        check(label + ": empty Half Guard history", g.history_fields(), BjjHalfGuardMatch.empty_history())
        check(label + ": no D3-B controller or behaviors for Half Guard", [g.controller_fields(), g.behavior_fields()], [{}, {"top": "", "bottom": ""}])
        check(label + ": the carry-over export is refused (no v2 schema exists)", [g.carryover_export().ok(), g.carryover_export().error], [false, "carryover_unsupported_position"])
        # the retained Mount segment is frozen history: identical to the bare twin at the exit, D3-B and histories included
        check(label + ": the retained Mount segment equals the twin at the exit", mount_views(g._gateway), mount_at_exit)
        check(label + ": the Mount D3-B record is untouched", g._gateway.controller_fields(), mount_at_exit.controller)
        # the first Half Guard window opens only on an explicit request
        var events_before := g.events().size()
        var opened := g.open_window()
        check(label + ": the explicit request opens Top's window", [opened.ok(), opened.values.window_id, opened.values.fighter_id, opened.values.role],
            [true, record.window.last_issued_id + 1, TOP, "top"])
        check(label + ": window_opened follows transition_committed", g.events().slice(events_before), [{"kind": "window_opened", "window_id": record.window.last_issued_id + 1,
            "fighter_id": TOP, "role": "top", "index": events_before + 1}])
        var interval: int = int(plan.config.interval)
        if int(record.clock.remaining_seconds) > interval:
            check(label + ": the caller-configured cadence advances the clock", g.state_fields().clock_seconds, int(record.clock.remaining_seconds) - interval)
        check(label + ": opening advanced the graph's own counters only", [opened.values.graph.status, opened.values.graph.event_count], ["active", events_before + 1])
        single_active(label + " after the first Half Guard window", g)
        # play on, then re-prove the Mount segment never moved
        var played := _play_without_exit(g)
        check(label + ": Half Guard play is accepted", played, true)
        check(label + ": the retained Mount segment is still frozen after Half Guard play", mount_views(g._gateway), mount_at_exit)
        single_active(label + " after Half Guard play", g)


# Three accepted Half Guard windows that cannot exit: Top Flatten, Bottom pass, Top Crossface.
func _play_without_exit(g: BjjPositionGraphMatch) -> bool:
    var steps: Array = [["half_guard.top.flatten", "half_guard.bottom_response.hip_frame"], ["", ""], ["half_guard.top.crossface", "half_guard.bottom_response.hip_frame"]]
    for step: Array in steps:
        var window := g.window_fields()
        if not window.open:
            var report := g.open_window()
            if not report.ok() or report.values.closed:
                return false
            window = g.window_fields()
        if not g.submit(window.window_id, window.fighter_id, step[0], step[1]).ok() or g.status() != "active":
            return false
    return true


# ---- 5. Commands after the transition ------------------------------------------------------------------------------------------

func _test_commands_after_the_transition() -> void:
    var plan: Dictionary = plans[0]
    var g := make_optin(plan)
    run_plan(g, plan)
    check("committed", g.active_position_id(), "half_guard")
    var window_view := g.window_fields()
    var consumed_id: int = window_view.window_id
    # refusals before any window is open: whole-graph nonmutation
    var idle: Array = [
        ["no open window", consumed_id, TOP, "", "", "", ""], ["stale consumed Mount window", consumed_id, BOTTOM, "", "", "", ""],
        ["next id, none open", consumed_id + 1, TOP, "", "", "", ""], ["unknown fighter", consumed_id + 1, "nobody", "", "", "", ""],
        ["Mount action", consumed_id + 1, TOP, C.TOP_AMERICANA_ARM_ISOLATION, "", "", ""], ["Mount escape", consumed_id, BOTTOM, C.BOTTOM_ELBOW_KNEE_ESCAPE, C.TOP_RESPONSE_POST_AND_BASE, "", ""]]
    for case: Array in idle:
        var before := everything(g)
        var report := g.submit(case[1], case[2], case[3], case[4], case[5], case[6])
        check("%s: refused" % case[0], report.ok(), false)
        check("%s: whole graph unchanged" % case[0], everything(g), before)
    var opened := g.open_window()
    var window_id: int = opened.values.window_id
    var acting: String = opened.values.fighter_id
    var other: String = BOTTOM if acting == TOP else TOP
    var refusals: Array = [
        ["stale Mount window id", consumed_id, acting, "half_guard.top.crossface", "half_guard.bottom_response.hip_frame"],
        ["future window id", window_id + 1, acting, "half_guard.top.crossface", "half_guard.bottom_response.hip_frame"],
        ["the other fighter", window_id, other, "half_guard.bottom.underhook", "half_guard.top_response.head_control"],
        ["unknown fighter", window_id, "nobody", "half_guard.top.crossface", "half_guard.bottom_response.hip_frame"],
        ["empty fighter", window_id, "", "half_guard.top.crossface", "half_guard.bottom_response.hip_frame"],
        ["Mount action id", window_id, acting, C.TOP_AMERICANA_ARM_ISOLATION, C.BOTTOM_ELBOW_KNEE_ESCAPE],
        ["Mount response id", window_id, acting, "half_guard.top.crossface", C.TOP_RESPONSE_POST_AND_BASE],
        ["the other side's action", window_id, acting, "half_guard.bottom.underhook", "half_guard.top_response.head_control"],
        ["unknown action", window_id, acting, "half_guard.top.suplex", "half_guard.bottom_response.hip_frame"],
        ["response without action", window_id, acting, "", "half_guard.bottom_response.hip_frame"]]
    for case: Array in refusals:
        var before := everything(g)
        var report := g.submit(case[1], case[2], case[3], case[4])
        check("%s: refused" % case[0], report.ok(), false)
        check("%s: whole graph unchanged" % case[0], everything(g), before)
    var before_commitment := everything(g)
    check("an invalid commitment is refused", g.submit(window_id, acting, "half_guard.top.crossface", "half_guard.bottom_response.hip_frame", "EXTREME").ok(), false)
    check("an invalid commitment changes nothing", everything(g), before_commitment)
    check("a second window cannot be opened while one is pending", g.open_window().ok(), false)
    check("a refused second open changes nothing", everything(g), before_commitment)
    # the Half Guard menus are served through the graph
    var menu := g.action_options(TOP).available_ids()
    check("Top's menu is Half Guard's", menu, ["half_guard.top.crossface", "half_guard.top.flatten", "half_guard.top.knee_slice"])
    check("response menu is Half Guard's", g.response_options("half_guard.top.knee_slice").available_ids(),
        ["half_guard.bottom_response.hip_frame", "half_guard.bottom_response.underhook_fight", "half_guard.bottom_response.knee_shield"])
    check("the selected commitment is Half Guard's baseline", g.selected_commitment(), "MEDIUM")
    check("a Mount action offers no response menu", g.response_options(C.TOP_AMERICANA_ARM_ISOLATION).available_ids(), [])
    # an accepted decision, then the duplicate and stale resubmissions
    var events_before := g.events().size()
    var accepted := g.submit(window_id, acting, "half_guard.top.crossface", "half_guard.bottom_response.hip_frame")
    check("a Half Guard decision is accepted", [accepted.ok(), accepted.values.kind], [true, "exchange"])
    check("decision_accepted is appended once", g.events().slice(events_before), [{"kind": "decision_accepted", "window_id": window_id, "fighter_id": acting, "role": "top",
        "decision": "exchange", "index": events_before + 1}])
    check("the graph block rides the report", accepted.values.graph, {"status": "active", "event_count": events_before + 1})
    for case: Array in [["duplicate decision", window_id, acting], ["duplicate by the other fighter", window_id, other], ["stale Mount window", consumed_id, acting]]:
        var before := everything(g)
        check("%s: refused" % case[0], g.submit(case[1], case[2]).ok(), false)
        check("%s: whole graph unchanged" % case[0], everything(g), before)
    var next_window := g.open_window()
    check("windows stay monotonic and initiative alternates", [next_window.values.window_id, next_window.values.role, next_window.values.fighter_id], [window_id + 1, "bottom", BOTTOM])
    check("Bottom's menu is Half Guard's in Bottom's own window", g.action_options(BOTTOM).available_ids(), ["half_guard.bottom.underhook", "half_guard.bottom.recover_guard"])
    check("Top has no menu in Bottom's window", g.action_options(TOP).available_ids(), [])
    check("Bottom's Half Guard action works", g.submit(next_window.values.window_id, BOTTOM, "half_guard.bottom.underhook", "half_guard.top_response.head_control").ok(), true)
    single_active("after Half Guard exchanges", g)


# ---- 6. Half Guard exits, timeout and halts -----------------------------------------------------------------------------------

# Drives an opt-in graph that has already committed until the status changes; Top and Bottom use the given directed choices.
func hg_drive(g: BjjPositionGraphMatch, top: Array, bottom: Array, commitment: String) -> String:
    for window_index in range(40):
        var opened := g.open_window()
        if not opened.ok() or opened.values.get("closed", false):
            return "closed"
        var choice: Array = top if opened.values.role == "top" else bottom
        var report := g.submit(opened.values.window_id, opened.values.fighter_id, choice[0], choice[1], commitment if not String(choice[0]).is_empty() else "")
        if not report.ok():
            return "refused:" + report.error
        if g.status() != "active":
            return g.status()
    return "no_exit"


func _test_half_guard_exits_timeout_and_halts() -> void:
    var plan: Dictionary = plans[0]
    var directed: Dictionary = {
        "Side Control": [["half_guard.top.knee_slice", "half_guard.bottom_response.hip_frame"], ["", ""], "HIGH"],
        "Closed Guard": [["", ""], ["half_guard.bottom.recover_guard", "half_guard.top_response.head_control"], "HIGH"],
    }
    # Open Guard needs exactly Success: find a directed Bottom escape that lands there
    var found_open_guard := false
    for response_id: String in ["half_guard.top_response.hip_pressure", "half_guard.top_response.knee_pin", "half_guard.top_response.head_control"]:
        for commitment: String in ["LOW", "MEDIUM", "HIGH"]:
            var probe := make_optin(plan)
            run_plan(probe, plan, false)
            if hg_drive(probe, ["", ""], ["half_guard.bottom.recover_guard", response_id], commitment) == "halted_at_unsupported_transition" and probe.blocked_transition().label == "Open Guard" and not found_open_guard:
                found_open_guard = true
                directed["Open Guard"] = [["", ""], ["half_guard.bottom.recover_guard", response_id], commitment]
    check("a real Half Guard -> Open Guard exit was reached", found_open_guard, true)
    for label: String in directed:
        var g := make_optin(plan)
        run_plan(g, plan)
        var script: Array = directed[label]
        var outcome := hg_drive(g, script[0], script[1], script[2])
        check("%s: the graph halts" % label, outcome, "halted_at_unsupported_transition")
        var destinations := {"Side Control": "side_control", "Open Guard": "open_guard", "Closed Guard": "closed_guard"}
        check("%s: blocked from half_guard, not mount" % label, g.blocked_transition(),
            {"from_position_id": "half_guard", "label": label, "reason": "destination_not_implemented", "destination_position_id": destinations[label]})
        var events := g.events()
        check("%s: decision_accepted then transition_blocked" % label, [events[-2].kind, events[-1].kind, events[-1].from_position_id], ["decision_accepted", "transition_blocked", "half_guard"])
        check("%s: one transition_committed (Mount's) and no terminal outcome" % label, [events.filter(func(e: Dictionary) -> bool: return e.kind == "transition_committed").size(),
            events.filter(func(e: Dictionary) -> bool: return e.kind == "terminal_outcome").size()], [1, 0])
        check("%s: Half Guard remains the active (halted) segment" % label, [g.active_position_id(), g.status(), g.state_fields().exit_destination], ["half_guard", "halted_at_unsupported_transition", label])
        check("%s: the exit leaves the Half Guard clock alone" % label, g.state_fields().clock_seconds > 0, true)
        var before := everything(g)
        check("%s: further windows refused" % label, [g.open_window().error, g.open_window_for(0).error], [HALTED_CODE, HALTED_CODE])
        check("%s: further decisions refused" % label, g.submit(g.window_fields().window_id, TOP).error, HALTED_CODE)
        check("%s: nothing changed after the refusals" % label, everything(g), before)
        check("%s: no export is invented for the halted Half Guard segment" % label, g.carryover_export().error, "carryover_unsupported_position")
    # timeout is a terminal outcome, never a positional exit
    var timed := make_optin(plan)
    run_plan(timed, plan)
    var mount_before := mount_views(timed._gateway)
    var events_before := timed.events().size()
    var closing := timed.open_window_for(10000)
    check("the explicit long window closes the match", [closing.ok(), closing.values.closed], [true, true])
    check("timeout is a terminal outcome", [timed.status(), timed.blocked_transition(), timed.state_fields().clock_seconds, timed.state_fields().exit_destination], ["ended", {}, 0, ""])
    check("timeout event", timed.events().slice(events_before), [{"kind": "terminal_outcome", "reason": "timeout", "index": events_before + 1}])
    check("no transition after a timeout", timed.events().filter(func(e: Dictionary) -> bool: return e.kind == "transition_blocked").size(), 0)
    check("the ended match stays on Half Guard and refuses more play", [timed.active_position_id(), timed.open_window().ok(), timed.submit(1, TOP).ok()], ["half_guard", false, false])
    check("the Mount segment never moved on the timeout", mount_views(timed._gateway), mount_before)
    check("export remains refused after a Half Guard timeout", timed.carryover_export().error, "carryover_unsupported_position")


# ---- 7. A faulty receiver halts without partial activation -----------------------------------------------------------------------

# A plan whose two fighters differ at the exit (so swapping or renaming their resources is a real change), preferring a latched one.
func distinct_plan() -> Dictionary:
    var best: Dictionary = {}
    for plan: Dictionary in plans:
        var twin := make_bare(plan)
        run_plan(twin, plan, false)
        var state := twin.state_fields()
        if state.top_stamina == state.bottom_stamina:
            continue
        if state.top_band == "Exhausted" or state.bottom_band == "Exhausted":
            return plan
        if best.is_empty():
            best = plan
    return best


func _valid_request_of(record: Dictionary, interval_seconds: int) -> Dictionary:
    return BjjHalfGuardMountEdge.entry_from_record(record, interval_seconds).request


# A receiver that builds a VALID Half Guard gateway from a deliberately wrong (but entry-valid) request.
func _receiver_from(change: Callable) -> Callable:
    return func(record: Dictionary, interval_seconds: int) -> BjjHalfGuardWindowGateway.Creation:
        var request := _valid_request_of(record, interval_seconds).duplicate(true)
        change.call(request)
        return BjjHalfGuardWindowGateway.create(request)


func _assert_entry_invalid_halt(label: String, plan: Dictionary, receivers: Variant, prepare: Callable = Callable(), mount_untouched: bool = true) -> BjjPositionGraphMatch:
    var twin := make_bare(plan)
    run_plan(twin, plan)
    var g := make_optin(plan, receivers)
    if prepare.is_valid():
        prepare.call(g)
    var run := run_plan(g, plan)
    check(label + ": the exchange was accepted and exited", run.exited, true)
    check(label + ": the graph halts", g.status(), "halted_at_unsupported_transition")
    check(label + ": reason transition_entry_invalid, from Mount, to Half Guard", g.blocked_transition(),
        {"from_position_id": "mount", "label": "Half Guard", "reason": "transition_entry_invalid", "destination_position_id": "half_guard"})
    var events := g.events()
    check(label + ": decision_accepted then transition_blocked, never transition_committed", [events[-2].kind, events[-1].kind, events.filter(func(e: Dictionary) -> bool: return e.kind == "transition_committed").size()],
        ["decision_accepted", "transition_blocked", 0])
    check(label + ": no partial Half Guard activation", [g._half_guard == null, g.active_position_id()], [true, "mount"])
    if mount_untouched:
        check(label + ": the settled Mount exchange stands (no rollback)", mount_views(g._gateway), mount_views(twin))
        check(label + ": the Mount views are the graph's views", [g.state_fields(), g.history_fields(), g.roles().fields()], [twin.state_fields(), twin.history_fields(), twin.roles().fields()])
    else:
        check(label + ": the exchange stands; the exit is still Mount's", [g.state_fields().exit_destination, g.state_fields().top_stamina], [twin.state_fields().exit_destination, twin.state_fields().top_stamina])
    var before := everything(g)
    check(label + ": later commands are refused", [g.open_window().error, g.submit(1, TOP).error], [HALTED_CODE, HALTED_CODE])
    check(label + ": the refusals changed nothing", everything(g), before)
    check(label + ": the unchanged v1 envelope validator refuses the halted graph", g.carryover_export().error, "inconsistent_graph_segment")
    return g


func _test_faulty_receivers_halt_without_partial_activation() -> void:
    var plan: Dictionary = distinct_plan()
    check("a plan with distinct fighters exists for fault injection", plan.is_empty(), false)
    var twin_state := make_bare(plan)
    run_plan(twin_state, plan, false)
    check("its fighters really differ at the exit", twin_state.state_fields().top_stamina != twin_state.state_fields().bottom_stamina, true)
    # wrong output types and shapes
    var wrong_outputs: Array = [["null", "_out_null"], ["an int", "_out_int"], ["a string", "_out_string"], ["a dictionary", "_out_dictionary"], ["an array", "_out_array"],
        ["a bare Half Guard gateway", "_out_bare_gateway"], ["a Mount-gateway Creation", "_out_mount_creation"], ["a Half Guard Creation with an error and no gateway", "_out_error_creation"],
        ["a Half Guard Creation with no error and no gateway", "_out_empty_creation"], ["a Creation that failed the entry", "_out_failed_entry"], ["a plain object", "_out_plain_object"]]
    for entry: Array in wrong_outputs:
        _assert_entry_invalid_halt("malformed output: " + entry[0], plan, {"half_guard": Callable(self, entry[1])})
    # correct ids, incorrect resources, clocks, counters and state (each request is entry-valid, so only the graph's own check can refuse it)
    var mutations: Array = [
        ["top stamina is one off", func(r: Dictionary) -> void: _nudge(r, "top", "stamina_current")],
        ["bottom stamina is one off", func(r: Dictionary) -> void: _nudge(r, "bottom", "stamina_current")],
        ["top maximum differs", func(r: Dictionary) -> void: _nudge(r, "top", "stamina_maximum")],
        ["bottom maximum differs", func(r: Dictionary) -> void: _nudge(r, "bottom", "stamina_maximum")],
        ["top meter remainder differs", func(r: Dictionary) -> void: r.fighters[r.role_map.top].behavior_remainder_units += 1],
        ["bottom meter remainder differs", func(r: Dictionary) -> void: r.fighters[r.role_map.bottom].behavior_remainder_units -= 1],
        ["remaining clock is one second short", func(r: Dictionary) -> void: r.clock.remaining_seconds -= 1],
        ["initial clock differs", func(r: Dictionary) -> void: r.clock.initial_seconds += 1],
        ["window counter is one ahead", func(r: Dictionary) -> void: r.window.last_issued_id += 1],
        ["window counter is reset", func(r: Dictionary) -> void: r.window.last_issued_id = 0],
        ["cadence differs from the graph's", func(r: Dictionary) -> void: r.interval_seconds += 1],
        ["the two fighters' resources are swapped (ids stay)", func(r: Dictionary) -> void: _swap_resources(r)],
        ["the role map is swapped (identity violated)", func(r: Dictionary) -> void: r.role_map = {"top": r.role_map.bottom, "bottom": r.role_map.top}],
        ["other fighter ids entirely", func(r: Dictionary) -> void: _rename(r, "other_top", "other_bottom")],
        ["one fighter renamed", func(r: Dictionary) -> void: _rename(r, "someone_else", r.role_map.bottom)],
    ]
    var exercised := 0
    for entry: Array in mutations:
        # a mutation that happens to leave the request unchanged or invalid would not test the graph; prove each one is a valid, different request
        var probe_twin := make_bare(plan)
        run_plan(probe_twin, plan)
        var honest := _valid_request_of(probe_twin.carryover_segment().record, int(plan.config.interval))
        var altered := honest.duplicate(true)
        (entry[1] as Callable).call(altered)
        check("mutation '%s' yields an entry-valid, different request" % entry[0], [BjjHalfGuardEntry.validate(altered), JSON.stringify(altered) != JSON.stringify(honest)], ["", true])
        _assert_entry_invalid_halt("wrong value: " + entry[0], plan, {"half_guard": _receiver_from(entry[1])})
        exercised += 1
    check("every mutation was exercised", exercised, mutations.size())
    # a gateway that is not fresh: a window already issued, left open, or a decision already made
    for entry: Array in [["window already issued", "_stale_issued"], ["window left open", "_stale_open"], ["a decision already made", "_stale_decided"]]:
        _assert_entry_invalid_halt("stale gateway: " + entry[0], plan, {"half_guard": Callable(self, entry[1])})
    # a receiver that reaches into the retained Mount segment is detected; one that only tries public commands cannot change it
    var holder := {}
    var tamper_private := func(record: Dictionary, interval_seconds: int) -> BjjHalfGuardWindowGateway.Creation:
        holder.mount._match.top_meter.remainder_units += 1
        return BjjHalfGuardWindowGateway.create(_valid_request_of(record, interval_seconds))
    var tampered := _assert_entry_invalid_halt("a receiver mutates the retained Mount segment", plan, {"half_guard": tamper_private},
        func(graph: BjjPositionGraphMatch) -> void: holder["mount"] = graph._gateway, false)
    var untampered_twin := make_bare(plan)
    run_plan(untampered_twin, plan)
    check("the tampering was real (the retained segment's private meter moved by exactly one unit)",
        tampered._gateway._match.top_meter.remainder_units - untampered_twin._match.top_meter.remainder_units, 1)
    var attempts: Array = []
    var tries_public := func(record: Dictionary, interval_seconds: int) -> BjjHalfGuardWindowGateway.Creation:
        attempts.append([holder.mount.open_window_for(0).ok(), holder.mount.submit(1, TOP).ok(), holder.mount.carryover_segment().ok()])
        return BjjHalfGuardWindowGateway.create(_valid_request_of(record, interval_seconds))
    var committed_graph := make_optin(plan, {"half_guard": tries_public})
    holder["mount"] = committed_graph._gateway
    var twin := make_bare(plan)
    run_plan(twin, plan)
    run_plan(committed_graph, plan)
    check("a receiver using only the public Mount API cannot move a terminal segment, so the commit stands", [committed_graph.active_position_id(), committed_graph.status()], ["half_guard", "active"])
    check("its attempts were all refused", attempts, [[false, false, true]])
    check("and the Mount segment still equals the twin's", mount_views(committed_graph._gateway), mount_views(twin))
    # a receiver mutating its own record argument cannot influence the graph: the graph keeps its own copy
    var record_tamper := func(record: Dictionary, interval_seconds: int) -> BjjHalfGuardWindowGateway.Creation:
        var request := _valid_request_of(record, interval_seconds)
        record.fighters.top.stamina_current = 1
        record.clock.remaining_seconds = 1
        record.fighter_by_role.top = "tampered"
        return BjjHalfGuardWindowGateway.create(request)
    var survivor := make_optin(plan, {"half_guard": record_tamper})
    var survivor_twin := make_bare(plan)
    run_plan(survivor_twin, plan)
    run_plan(survivor, plan)
    check("mutating the record argument is harmless: the commit stands on the graph's own copy", [survivor.active_position_id(), survivor.status()], ["half_guard", "active"])
    check("and carried values are the Mount segment's, not the tampered ones", survivor.state_fields().top_stamina, survivor_twin.state_fields().top_stamina)
    check("the retained Mount segment is unaffected by the tampered copy", mount_views(survivor._gateway), mount_views(survivor_twin))
    # the failure is per transition: a graph that halted this way offers no second attempt
    var halted := _assert_entry_invalid_halt("second attempt", plan, {"half_guard": Callable(self, "_out_null")})
    check("a halted graph cannot retry the transition", [halted.open_window().ok(), halted.status()], [false, "halted_at_unsupported_transition"])


func _out_null(record: Dictionary, interval_seconds: int) -> Variant:
    return null


func _out_int(record: Dictionary, interval_seconds: int) -> Variant:
    return 5


func _out_string(record: Dictionary, interval_seconds: int) -> Variant:
    return "creation"


func _out_dictionary(record: Dictionary, interval_seconds: int) -> Variant:
    return {"gateway": null, "error": ""}


func _out_array(record: Dictionary, interval_seconds: int) -> Variant:
    return []


func _out_bare_gateway(record: Dictionary, interval_seconds: int) -> Variant:
    return BjjHalfGuardWindowGateway.create(_valid_request_of(record, interval_seconds)).gateway


func _out_mount_creation(record: Dictionary, interval_seconds: int) -> Variant:
    return BjjMatchWindowGateway.Creation.new()


func _out_error_creation(record: Dictionary, interval_seconds: int) -> Variant:
    var creation := BjjHalfGuardWindowGateway.Creation.new()
    creation.error = "entry_malformed"
    return creation


func _out_empty_creation(record: Dictionary, interval_seconds: int) -> Variant:
    return BjjHalfGuardWindowGateway.Creation.new()


func _out_failed_entry(record: Dictionary, interval_seconds: int) -> Variant:
    return BjjHalfGuardWindowGateway.create({})


func _out_plain_object(record: Dictionary, interval_seconds: int) -> Variant:
    return RefCounted.new()


func _stale_issued(record: Dictionary, interval_seconds: int) -> Variant:
    var creation := BjjHalfGuardWindowGateway.create(_valid_request_of(record, interval_seconds))
    creation.gateway.open_window()
    creation.gateway.submit(creation.gateway.window_fields().window_id, TOP)
    return creation


func _stale_open(record: Dictionary, interval_seconds: int) -> Variant:
    var creation := BjjHalfGuardWindowGateway.create(_valid_request_of(record, interval_seconds))
    creation.gateway.open_window()
    return creation


func _stale_decided(record: Dictionary, interval_seconds: int) -> Variant:
    var creation := BjjHalfGuardWindowGateway.create(_valid_request_of(record, interval_seconds))
    var opened := creation.gateway.open_window()
    creation.gateway.submit(opened.values.window_id, TOP, "half_guard.top.flatten", "half_guard.bottom_response.hip_frame")
    return creation


func _nudge(request: Dictionary, role: String, key: String) -> void:
    var id: String = request.role_map[role]
    for delta: int in [1, -1, 2, -2, 3, -3, 5, -5, 11, -11]:
        var trial := request.duplicate(true)
        trial.fighters[id][key] += delta
        if BjjHalfGuardEntry.validate(trial).is_empty():
            request.fighters[id][key] += delta
            return


func _swap_resources(request: Dictionary) -> void:
    var top_id: String = request.role_map.top
    var bottom_id: String = request.role_map.bottom
    var top_record: Dictionary = request.fighters[top_id]
    request.fighters[top_id] = request.fighters[bottom_id]
    request.fighters[bottom_id] = top_record


func _rename(request: Dictionary, top_id: String, bottom_id: String) -> void:
    var old_top: String = request.role_map.top
    var old_bottom: String = request.role_map.bottom
    var fighters: Dictionary = {top_id: request.fighters[old_top], bottom_id: request.fighters[old_bottom]}
    request.fighters = fighters
    request.role_map = {"top": top_id, "bottom": bottom_id}


# ---- 8. The receiver seam's contract ------------------------------------------------------------------------------------------

func _test_receiver_seam_contract() -> void:
    for plan: Dictionary in plans:
        var calls: Array = []
        var recording := func(record: Dictionary, interval_seconds: int) -> BjjHalfGuardWindowGateway.Creation:
            calls.append({"record": record.duplicate(true), "interval": interval_seconds, "type": typeof(interval_seconds)})
            return BjjPositionGraphMatch.default_receivers()["half_guard"].call(record, interval_seconds)
        var g := make_optin(plan, {"half_guard": recording})
        var twin := make_bare(plan)
        run_plan(twin, plan)
        run_plan(g, plan)
        check("the receiver is called exactly once per transition", calls.size(), 1)
        if calls.size() == 1:
            check("it receives the validated Mount segment (detached) and the graph's own configured interval", [calls[0].record, calls[0].interval, calls[0].type],
                [twin.carryover_segment().record, int(plan.config.interval), TYPE_INT])
            check("the record it received validates", BjjMountCarryover.validate_segment(calls[0].record), "")
        check("the commit stands", g.active_position_id(), "half_guard")
    # default_receivers() is the Half Guard edge; it is the only built-in receiver and refuses what the edge refuses
    var table := BjjPositionGraphMatch.default_receivers()
    check("the default table is exactly the Half Guard receiver", table.keys(), ["half_guard"])
    var plan: Dictionary = plans[0]
    var twin := make_bare(plan)
    run_plan(twin, plan)
    var record: Dictionary = twin.carryover_segment().record
    var made: BjjHalfGuardWindowGateway.Creation = table["half_guard"].call(record, 5)
    check("the default receiver builds a gateway from a valid record", [made.ok(), made.error], [true, ""])
    var refused: BjjHalfGuardWindowGateway.Creation = table["half_guard"].call(record, 0)
    check("it refuses an invalid interval with the entry's code", [refused.ok(), refused.error, refused.gateway == null], [false, "invalid_interval", true])
    check("it refuses a non-Half-Guard record with the edge's code", table["half_guard"].call(make_bare(plan).carryover_segment().record, 5).error, "mount_edge_not_an_exit")
    # the cadence is the graph's own configuration; an absent key means the constant Mount itself uses
    var no_interval := {"rule_set": "modern", "config": {"axis": 1.5}, "action": C.BOTTOM_ELBOW_KNEE_ESCAPE, "response": C.TOP_RESPONSE_POST_AND_BASE, "rounds": 0, "label": "Half Guard"}
    var defaulted := make_optin(no_interval)
    check("the default cadence is the Mount constant", defaulted._interval_seconds, BjjMountRules.DEFAULT_INTERVAL_SECONDS)
    # one more window: both graphs advance the clock by the same cadence
    for interval: int in [3, 5, 9]:
        var custom := {"rule_set": "modern", "config": {"axis": 1.5, "interval": interval}, "action": C.BOTTOM_ELBOW_KNEE_ESCAPE, "response": C.TOP_RESPONSE_POST_AND_BASE, "rounds": 0, "label": "Half Guard"}
        var g := make_optin(custom)
        check("cadence %d is captured" % interval, g._interval_seconds, interval)
        if run_plan(g, custom, false).exited and g.active_position_id() == "half_guard":
            var before: int = g.state_fields().clock_seconds
            g.open_window()
            check("cadence %d advances Half Guard time by %d" % [interval, interval], g.state_fields().clock_seconds, before - interval)


# ---- 9. Deterministic double replay ----------------------------------------------------------------------------------------------

func _test_double_replay_is_deterministic() -> void:
    for plan: Dictionary in plans:
        var results: Array = []
        for pass_index in range(2):
            var g := make_optin(plan)
            var run := run_plan(g, plan)
            _play_without_exit(g)
            var tail := hg_drive(g, ["half_guard.top.knee_slice", "half_guard.bottom_response.hip_frame"], ["", ""], "HIGH")
            results.append({"trace": run.trace, "tail": tail, "everything": everything(g)})
        check("two replays of the same plan are identical (reports, events, views, segments)", results[0], results[1])
    # the opt-in graph, the default graph and the twin agree on every Mount command up to the exit across the whole plan list
    var checked := 0
    for plan: Dictionary in plans:
        var opt := run_plan(make_optin(plan), plan, false)
        var bare := run_plan(make_bare(plan), plan, false)
        check("opt-in reports equal the bare gateway's up to and including the exit", opt.trace, bare.trace)
        checked += 1
    check("every plan was compared", checked, plans.size())


# ---- 10. The static classifier is untouched; scope ----------------------------------------------------------------------------------

func _test_static_classification_and_scope() -> void:
    check("Mount Half Guard label", BjjPositionGraphMatch.classify_exit("Half Guard"), {"kind": "blocked", "reason": "destination_not_implemented", "destination_position_id": "half_guard"})
    check("Mount Open Guard label", BjjPositionGraphMatch.classify_exit("Open Guard"), {"kind": "blocked", "reason": "destination_not_implemented", "destination_position_id": "open_guard"})
    check("Mount Reversal label", BjjPositionGraphMatch.classify_exit("Reversal"), {"kind": "blocked", "reason": "unresolved_destination", "destination_position_id": ""})
    check("no label is no exit", BjjPositionGraphMatch.classify_exit(""), {"kind": "none"})
    check("the static classifier still knows no Half Guard source (C-10)", BjjPositionGraphMatch.classify_exit_from("half_guard", "Side Control"),
        {"kind": "blocked", "reason": "unknown_source_position", "destination_position_id": ""})
    check("the static classifier never returns a transition", BjjPositionGraphMatch.classify_exit_from("mount", "Half Guard").kind, "blocked")
    var declared := {"half_guard": {"exits": BjjHalfGuardCatalog.EXIT_DESTINATIONS, "unresolved": []}}
    for label: String in ["Side Control", "Open Guard", "Closed Guard"]:
        check("Half Guard declarations classify %s with the same unchanged function" % label, BjjPositionGraphMatch.classify_exit_from("half_guard", label, declared),
            {"kind": "blocked", "reason": "destination_not_implemented", "destination_position_id": BjjHalfGuardCatalog.EXIT_DESTINATIONS[label]})
    check("an undeclared Half Guard label stays undeclared", BjjPositionGraphMatch.classify_exit_from("half_guard", "Mount", declared).reason, "undeclared_exit_label")
    check("the graph's new constants", [BjjPositionGraphMatch.HALF_GUARD_ID, BjjPositionGraphMatch.RECEIVER_IDS, BjjPositionGraphMatch.ERROR_INVALID_RECEIVERS, BjjPositionGraphMatch.ERROR_UNSUPPORTED_EXPORT,
        BjjPositionGraphMatch.REASON_ENTRY_INVALID], ["half_guard", ["half_guard"], "invalid_receivers", "carryover_unsupported_position", "transition_entry_invalid"])
    # static source scan of the graph: no clock, randomness, files or wall-clock; no reach into a match; no pool mutation
    var file := FileAccess.open("res://scripts/positions/graph_match.gd", FileAccess.READ)
    check("graph source readable", file != null, true)
    if file == null:
        return
    var lines: Array[String] = []
    for source_line: String in file.get_as_text().split("\n"):
        lines.append(source_line.split("#")[0])
    var text := "\n".join(lines)
    for token: String in ["randi", "randf", "RandomNumberGenerator", "Time.", "OS.get_ticks", "await", "get_tree", "Engine.get_frames", "FileAccess", "preload(", "._match", "set_current",
            "BjjMountMatch", "BjjStaminaPool", "BjjBehaviorStaminaPolicy", "BjjD3B"]:
        check("graph has no %s" % token, text.contains(token), false)
    check("the Mount slot is assigned exactly once (in create)", text.count("graph._gateway = "), 1)
    check("the Mount slot is never reassigned", text.count("_gateway = ") - text.count("graph._gateway = "), 0)
    check("the Half Guard slot is assigned in exactly one place (the commit)", text.count("_half_guard = "), 1)
    # no public name of the graph exposes a gateway (F1's own check relies on this)
    var script: GDScript = BjjPositionGraphMatch
    var public_names: Array[String] = []
    for method: Dictionary in script.get_script_method_list():
        var name: String = method.name
        if not name.begins_with("_"):
            public_names.append(name)
            check("public graph name '%s' does not mention a gateway" % name, name.to_lower().contains("gateway"), false)
    check("the new public names are exactly active_position_id, create_with_receivers and default_receivers", public_names.filter(func(n: String) -> bool: return n in ["active_position_id", "create_with_receivers", "default_receivers"]).size(), 3)
