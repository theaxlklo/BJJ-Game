extends SceneTree

# Negative-first tests for F1.1, the explicitly selected two-sided Mount practice mode. They live in their
# own file so the original 1036-assertion F1 suite stays byte-for-byte unchanged: that suite, unchanged and
# still passing, is the proof that the default scripted practice behaves exactly as before.
#
# Everything simulated goes through BjjPositionGraphMatch. A separately driven REFERENCE graph that receives
# the same window ids, fighter ids and arguments is the oracle for what the controller did. Test-side
# private access (controller._graph, graph._gateway) is used only as that oracle or to read engine state,
# as the existing graph, gateway and F1 suites do; the production presentation code never does it.
const TOP_ID: String = "fighter_alpha"
const BOTTOM_ID: String = "fighter_bravo"
const ALPHA_RES: String = "res://tests/resources/fighter_test_alpha.tres"
const BRAVO_RES: String = "res://tests/resources/fighter_test_bravo.tres"
const CLIMB: String = "mount.top.high_mount_climb"
const FOREARM: String = "mount.bottom_response.forearm_frame"
const BRIDGE: String = "mount.bottom.bridge"
const ELBOW: String = "mount.bottom.elbow_knee_escape"
const TRAP: String = "mount.bottom.trap_and_roll_escape"
const POST: String = "mount.top_response.post_and_base"
const WIDE: String = "mount.top_response.wide_mount_base"
const HIP: String = "mount.top_response.hip_follow_repummel"
const NO_ACTION: String = "practice.bottom_no_action"
const HALTED: String = "halted_unsupported_transition"

var checks: int = 0
var failures: int = 0


func check(label: String, actual: Variant, expected: Variant) -> void:
    checks += 1
    if typeof(actual) != typeof(expected) or JSON.stringify(actual, "", true, true) != JSON.stringify(expected, "", true, true):
        failures += 1
        if failures <= 25:
            push_error("%s: got %s expected %s" % [label, actual, expected])


func _initialize() -> void:
    _test_mode_selection_and_fresh_reset()
    _test_scripted_default_is_unchanged()
    _test_two_sided_bottom_rows_and_selection()
    _test_refusals_change_nothing()
    _test_bottom_decision_equals_reference()
    _test_bottom_no_action_uses_the_production_path()
    _test_hold_replaces_the_requested_technique()
    _test_armed_window_reports_the_engine_decision_kind()
    _test_stale_replayed_and_wrong_actor_commands()
    _test_blocked_transitions_are_shown_as_blocked()
    _test_terminal_and_no_duplicate_effects()
    _test_refreshes_are_inert()
    _test_source_boundaries()
    await _test_scene()
    # Same completion contract as the other suites: one PASS line with the exact count, validated together
    # with the exit status and the whole log by tools/ci/validate_mount_slice_log.py.
    if failures > 0:
        push_error("Mount practice two-sided: %d / %d assertions failed" % [failures, checks])
        quit(1)
        return
    print("Mount practice two-sided PASS: %d assertions" % checks)
    quit(0)


# --- helpers ---------------------------------------------------------------------------

func alpha() -> BjjFighterDefinition:
    return load(ALPHA_RES)


func bravo() -> BjjFighterDefinition:
    return load(BRAVO_RES)


# A controller already in the requested mode with a fresh match.
func started(mode: String, extra: Dictionary = {}) -> BjjMountPracticeController:
    var c := BjjMountPracticeController.new()
    check("mode %s accepted before the first match" % mode, c.set_practice_mode(mode).ok, true)
    check("practice match started", c.start_new_match(alpha(), bravo(), extra), {"ok": true, "error": ""})
    return c


func reference(extra: Dictionary = {}) -> BjjPositionGraphMatch:
    var config := BjjMountPracticeController.match_configuration()
    config.merge(extra, true)
    return BjjPositionGraphMatch.create(config, TOP_ID, BOTTOM_ID).graph


func views(g: BjjPositionGraphMatch) -> Dictionary:
    var carry := g.carryover_export()
    return {"state": g.state_fields(), "history": g.history_fields(), "controller": g.controller_fields(), "window": g.window_fields(),
        "behaviors": g.behavior_fields(), "roles": g.roles().fields(), "status": g.status(), "events": g.events(),
        "blocked": g.blocked_transition(), "commitment": g.selected_commitment(), "carryover": {"error": carry.error, "record": carry.record},
        "lifecycle": g._gateway._match.lifecycle_fields()}


func refused(label: String, result: Dictionary, expected_error: String) -> void:
    check(label + ": refused with the exact code", result, {"ok": false, "error": expected_error})


func available_ids(c: BjjMountPracticeController, rows_key: String) -> Array:
    return c.view()[rows_key].filter(func(r: Dictionary) -> bool: return r.available).map(func(r: Dictionary) -> String: return r.id)


# Plays the Top window through the controller and mirrors it on the reference graph (first admitted
# technique, first admitted response). Returns the Top window's id.
func top_decision(c: BjjMountPracticeController, ref: BjjPositionGraphMatch) -> int:
    check("a Top window opens", c.next_window().ok, true)
    ref.open_window()
    var action: String = available_ids(c, "actions")[0]
    check("a Top technique is selected", c.select_action(action).ok, true)
    var response: String = available_ids(c, "responses")[0]
    check("a response is selected", c.select_response(response).ok, true)
    var window_id: int = ref.window_fields().window_id
    check("the Top decision is accepted", c.submit_decision().ok, true)
    check("the reference accepts the same Top decision", ref.submit(window_id, TOP_ID, action, response).ok(), true)
    return window_id


# A two-sided controller and a reference graph, both with the Bottom's window open (window 2).
func at_bottom_window(extra: Dictionary = {}) -> Array:
    var c := started("two_sided", extra)
    var ref := reference(extra)
    top_decision(c, ref)
    check("the Bottom window opens", c.next_window().ok, true)
    ref.open_window()
    check("it is window 2 owned by the Bottom", [c.view().window.window_id, c.view().window.role, ref.window_fields().window_id], [2, "bottom", 2])
    return [c, ref]


# --- 1. mode selection and a fresh match ---------------------------------------------------

func _test_mode_selection_and_fresh_reset() -> void:
    var c := BjjMountPracticeController.new()
    check("the default mode is scripted practice", [c.practice_mode, BjjMountPracticeController.MODES], ["scripted", ["scripted", "two_sided"]])
    check("the mode labels", BjjMountPracticeController.MODE_LABELS, {"scripted": "Scripted practice", "two_sided": "Two-sided practice"})
    refused("an unknown mode", c.set_practice_mode("tournament"), "unknown_practice_mode")
    refused("an empty mode", c.set_practice_mode(""), "unknown_practice_mode")
    check("a refused mode changed nothing", [c.practice_mode, c.has_match(), c.match_serial], ["scripted", false, 0])
    check("a mode can be chosen before the first match", [c.set_practice_mode("two_sided").ok, c.practice_mode, c.has_match(), c.view()], [true, "two_sided", false, {"has_match": false}])
    check("the first match uses the chosen mode", [c.start_new_match(alpha(), bravo()).ok, c.view().mode, c.view().mode_label, c.match_serial], [true, "two_sided", "Two-sided practice", 1])

    # Changing the mode mid-match starts a fresh match; the old one is discarded, never re-run or converted.
    var ref := reference()
    top_decision(c, ref)
    check("a Top window is accepted and a Bottom window opens", c.next_window().ok, true)
    check("a Bottom technique and response are selected before the switch", [c.select_action(BRIDGE).ok, c.select_response(POST).ok, c.selected_action, c.selected_response], [true, true, BRIDGE, POST])
    var old_graph := c._graph
    var old_views := views(old_graph)
    check("the old match has events and an open window", [old_graph.events().size(), old_graph.window_fields().open], [3, true])
    refused("an unknown mode mid-match", c.set_practice_mode("nonsense"), "unknown_practice_mode")
    check("a refused mode left the match untouched", [c._graph == old_graph, views(old_graph), c.match_serial], [true, old_views, 1])
    check("choosing the same mode is a no-op and keeps the selections", [c.set_practice_mode("two_sided").ok, c._graph == old_graph, c.match_serial, views(old_graph), c.selected_action, c.selected_response],
        [true, true, 1, old_views, BRIDGE, POST])
    check("switching to scripted succeeds", c.set_practice_mode("scripted").ok, true)
    check("a fresh independent match replaced the graph", [c._graph != old_graph, c.match_serial, c.practice_mode], [true, 2, "scripted"])
    var view := c.view()
    check("the fresh match has no window, events or progress", [view.window.open, view.window.window_id, view.events, view.clock_seconds, view.status_kind], [false, 0, [], 300, "active"])
    check("selections were cleared", [c.selected_action, c.selected_response, c.selected_commitment], ["", "", ""])
    check("fighters are fresh", view.fighters.map(func(f: Dictionary) -> int: return f.stamina_current), [100, 100])
    check("the change is explained", view.last_message, "Practice mode changed to Scripted practice: a fresh practice match was started and the previous match was discarded.")
    check("the old match was not re-run or modified by the switch", views(old_graph), old_views)
    check("switching back also starts a fresh match", [c.set_practice_mode("two_sided").ok, c.match_serial, c.view().events], [true, 3, []])
    # A Top commitment selected in a Top window is also discarded by a mode switch.
    check("a Top window is open with a technique, response and commitment selected", [c.next_window().ok, c.select_action(CLIMB).ok, c.select_response(FOREARM).ok, c.select_commitment("HIGH").ok,
        c.selected_commitment], [true, true, true, true, "HIGH"])
    check("switching mode clears them and the open window", [c.set_practice_mode("scripted").ok, c.selected_action, c.selected_response, c.selected_commitment, c.view().window.open], [true, "", "", "", false])
    # Settings the match was started with survive a mode switch (still a fresh match).
    var short := started("two_sided", {"clock": 10})
    check("a custom clock is kept across a mode switch", [short.set_practice_mode("scripted").ok, short.view().clock_seconds, short.view().initial_clock, short.match_serial], [true, 10, 10, 2])
    check("two-sided is chosen again", [c.set_practice_mode("two_sided").ok, c.match_serial], [true, 5])
    check("New Practice Match keeps the chosen mode", [c.start_new_match(alpha(), bravo()).ok, c.practice_mode, c.match_serial], [true, "two_sided", 6])


# --- 2. the default scripted practice is unchanged ---------------------------------------------

func _test_scripted_default_is_unchanged() -> void:
    var plain := BjjMountPracticeController.new()
    plain.start_new_match(alpha(), bravo())
    var chosen := started("scripted")
    check("explicitly choosing scripted is the same as the default", [plain.practice_mode, chosen.practice_mode, plain.view().mode], ["scripted", "scripted", "scripted"])
    for step: int in 8:
        var a := plain.next_window()
        var b := chosen.next_window()
        check("step %d: the same Next Window result" % step, a, b)
        var window: Dictionary = plain.view().window
        if window.role == "top":
            var action: String = available_ids(plain, "actions")[0]
            plain.select_action(action)
            chosen.select_action(action)
            var response: String = available_ids(plain, "responses")[0]
            plain.select_response(response)
            chosen.select_response(response)
        else:
            check("step %d: a scripted Bottom window offers no selection and no No-action row" % step, [plain.view().window.scripted, plain.view().window.two_sided_bottom,
                plain.view().actions.all(func(r: Dictionary) -> bool: return not r.available), plain.view().actions.map(func(r: Dictionary) -> String: return r.id).has(NO_ACTION)], [true, false, true, false])
            refused("step %d: selecting a Bottom technique in scripted mode" % step, plain.select_action(BRIDGE), "not_selectable")
            refused("step %d: selecting the no-action row in scripted mode" % step, plain.select_action(NO_ACTION), "not_selectable")
        check("step %d: the same decision result" % step, plain.submit_decision(), chosen.submit_decision())
        check("step %d: identical presentation models" % step, plain.view(), chosen.view())
        check("step %d: identical engine states" % step, views(plain._graph), views(chosen._graph))
    # The scripted Bottom decision is still the engine's no-action path.
    var c := started("scripted")
    var ref2 := reference()
    top_decision(c, ref2)
    c.next_window()
    ref2.open_window()
    check("scripted Submit equals the reference no-action Bottom decision", [c.submit_decision().ok, c.last_report()], [true, ref2.submit(2, BOTTOM_ID).fields()])


# --- 3. the Bottom's rows and selection in two-sided practice -----------------------------------

func _test_two_sided_bottom_rows_and_selection() -> void:
    var pair := at_bottom_window()
    var c: BjjMountPracticeController = pair[0]
    var ref: BjjPositionGraphMatch = pair[1]
    var view := c.view()
    check("the Bottom is the decision owner and the window is not scripted", [view.window.owner_name, view.window.scripted, view.window.two_sided_bottom], ["Test Bravo", false, true])
    check("the rows are the engine's Bottom options plus the explicit No-action row", view.actions.map(func(r: Dictionary) -> Array: return [r.id, r.available, r.reason]),
        [[BRIDGE, true, ""], [ELBOW, true, ""], [TRAP, false, "setup_not_ready"], [NO_ACTION, true, ""]])
    check("every engine row equals the graph's own option", view.actions.slice(0, 3).map(func(r: Dictionary) -> Array: return [r.id, r.available, r.reason]),
        ref.action_options(BOTTOM_ID).options.map(func(o: BjjPositionContract.Option) -> Array: return [o.id, o.available, o.reason]))
    check("no response rows before a technique is selected", view.responses, [])
    check("Submit needs an explicit choice in a two-sided Bottom window", view.commands.submit, {"enabled": false, "reason": "technique_required"})
    check("the commitment control is not offered to the Bottom", [view.commitment.selectable, view.commitment.policy_selected], [false, ref.selected_commitment()])

    check("an available Bottom technique is selected", c.select_action(BRIDGE), {"ok": true, "error": ""})
    view = c.view()
    check("its responses are the Top's admitted responses, equal to the graph's", view.responses.map(func(r: Dictionary) -> Array: return [r.id, r.available, r.reason]),
        ref.response_options(BRIDGE).options.map(func(o: BjjPositionContract.Option) -> Array: return [o.id, o.available, o.reason]))
    check("the three Top responses are listed", view.responses.map(func(r: Dictionary) -> String: return r.id), [POST, WIDE, HIP])
    check("Submit now needs a response", view.commands.submit, {"enabled": false, "reason": "response_required"})
    check("a response is selected", c.select_response(WIDE), {"ok": true, "error": ""})
    check("Submit is enabled", c.view().commands.submit, {"enabled": true, "reason": ""})
    check("selecting a different technique clears the response", [c.select_action(ELBOW).ok, c.selected_response, c.view().commands.submit.reason], [true, "", "response_required"])
    check("the explicit no-action row is selectable and has no responses", [c.select_action(NO_ACTION).ok, c.selected_action, c.view().responses, c.view().commands.submit], [true, NO_ACTION, [], {"enabled": true, "reason": ""}])
    check("changing away from no-action works", [c.select_action(BRIDGE).ok, c.selected_action], [true, BRIDGE])


# --- 4. refusals change nothing ---------------------------------------------------------------

func _test_refusals_change_nothing() -> void:
    var pair := at_bottom_window()
    var c: BjjMountPracticeController = pair[0]
    var g := c._graph
    var before := views(g)
    var snapshot := c.view()
    refused("a Top technique in the Bottom window", c.select_action(CLIMB), "unknown_action")
    refused("an unknown technique", c.select_action("mount.bottom.unknown"), "unknown_action")
    refused("an empty technique", c.select_action(""), "unknown_action")
    refused("an unavailable technique shows the engine's exact reason", c.select_action(TRAP), "setup_not_ready")
    refused("a response before a technique", c.select_response(POST), "technique_required")
    refused("Submit with nothing selected", c.submit_decision(), "technique_required")
    refused("a commitment in the Bottom window", c.select_commitment("HIGH"), "commitment_is_policy_selected")
    refused("an unknown commitment is still policy-selected for the Bottom", c.select_commitment("EXTREME"), "commitment_is_policy_selected")
    refused("Next Window with the window open", c.next_window(), "window_already_open")
    check("nothing is selected", [c.selected_action, c.selected_response, c.selected_commitment], ["", "", ""])
    check("the engine state is unchanged", views(g), before)
    var after_refusals := c.view()
    snapshot.erase("last_message")
    after_refusals.erase("last_message")
    check("only the message changed in the model", after_refusals, snapshot)
    c.select_action(BRIDGE)
    refused("a Bottom response id is not a Top response", c.select_response(FOREARM), "unknown_response")
    refused("an unknown response", c.select_response("mount.top_response.unknown"), "unknown_response")
    refused("an empty response", c.select_response(""), "unknown_response")
    refused("Submit with a technique but no response", c.submit_decision(), "response_required")
    c.select_action(NO_ACTION)
    refused("a response for the no-action decision", c.select_response(POST), "no_response_for_no_action")
    check("selecting nothing valid changed nothing", views(g), before)
    # The controller's own handling of a refusal that comes from the graph (not from its gates). Selections are written
    # directly, as a script could, so the engine's admission is the only thing that can refuse.
    var g2 := c._graph
    c.select_action(BRIDGE)
    c.selected_response = FOREARM
    var kept := views(g2)
    refused("the graph refuses a Bottom response id as the Top's response, and the controller passes the code through", c.submit_decision(), "incorrect_response_side_or_kind")
    check("that refusal changed nothing and kept the selections", [views(g2), c.selected_action, c.selected_response], [kept, BRIDGE, FOREARM])
    # A stray commitment value can never reach a Bottom window: it is not forwarded, so the decision is the plain one.
    var pair2 := at_bottom_window()
    var bc: BjjMountPracticeController = pair2[0]
    var bref: BjjPositionGraphMatch = pair2[1]
    bc.select_action(BRIDGE)
    bc.select_response(POST)
    bc.selected_commitment = "HIGH"
    var plain := bref.submit(2, BOTTOM_ID, BRIDGE, POST)
    check("a forced commitment is ignored in a Bottom window: the report equals the commitment-free reference", [bc.submit_decision().ok, bc.last_report(), views(bc._graph)], [true, plain.fields(), views(bref)])
    # The scripted mode still refuses what two-sided now allows.
    var scripted := started("scripted")
    top_decision(scripted, reference())
    scripted.next_window()
    refused("scripted: a Bottom technique", scripted.select_action(BRIDGE), "not_selectable")
    refused("scripted: the no-action row", scripted.select_action(NO_ACTION), "not_selectable")
    refused("scripted: a response", scripted.select_response(POST), "technique_required")


# --- 5. a manual Bottom decision is exactly the graph's decision ---------------------------------

func _test_bottom_decision_equals_reference() -> void:
    for combo: Array in [[BRIDGE, POST], [BRIDGE, WIDE], [BRIDGE, HIP], [ELBOW, POST], [ELBOW, WIDE], [ELBOW, HIP]]:
        var label: String = "%s / %s" % [combo[0].get_slice(".", 2), combo[1].get_slice(".", 2)]
        var pair := at_bottom_window()
        var c: BjjMountPracticeController = pair[0]
        var ref: BjjPositionGraphMatch = pair[1]
        check(label + ": the technique is selected", c.select_action(combo[0]).ok, true)
        check(label + ": the response is selected", c.select_response(combo[1]).ok, true)
        var expected := ref.submit(2, BOTTOM_ID, combo[0], combo[1])
        check(label + ": the decision is accepted", c.submit_decision(), {"ok": true, "error": ""})
        check(label + ": the report equals the reference graph's report for window 2 and the Bottom fighter", c.last_report(), expected.fields())
        check(label + ": it is a Bottom decision through the production path", [c.last_report().kind, c.last_report().role, c.last_report().fighter_id, c.last_report().window_id],
            ["bottom_decision", "bottom", BOTTOM_ID, 2])
        check(label + ": the whole engine state equals the reference", views(c._graph), views(ref))
        check(label + ": exactly two windows and two decisions were recorded", c._graph.events().slice(0, 4).map(func(e: Dictionary) -> String: return e.kind),
            ["window_opened", "decision_accepted", "window_opened", "decision_accepted"])
        var lines: Array = c.view().last_lines
        check(label + ": the result text names the Bottom, the technique and the Top's response", lines[0].begins_with("Test Bravo (Bottom): %s; Top's response: " % ("Bridge" if combo[0] == BRIDGE else "Elbow-Knee Escape")), true)
        check(label + ": the result is not labelled scripted", lines.any(func(l: String) -> bool: return l.contains("SCRIPTED")), false)
        check(label + ": grade and axis lines are shown", [lines[1].begins_with("Bottom's grade: "), lines[2].begins_with("Axis ")], [true, true])
        check(label + ": both stamina lines and the clock line are shown", [lines.filter(func(l: String) -> bool: return l.contains(" stamina ")).size(), lines.back().begins_with("Clock ")], [2, true])
        var after: Dictionary = c._graph.state_fields()
        check(label + ": the clock and stamina equal the reference's single settlement", [after.clock_seconds, after.top_stamina, after.bottom_stamina],
            [ref.state_fields().clock_seconds, ref.state_fields().top_stamina, ref.state_fields().bottom_stamina])
        check(label + ": selections were cleared", [c.selected_action, c.selected_response], ["", ""])


# --- 6. the explicit Bottom no-action decision uses the existing production path ------------------------

func _test_bottom_no_action_uses_the_production_path() -> void:
    var pair := at_bottom_window()
    var c: BjjMountPracticeController = pair[0]
    var ref: BjjPositionGraphMatch = pair[1]
    c.select_action(NO_ACTION)
    var expected := ref.submit(2, BOTTOM_ID)
    check("the no-action decision is accepted", c.submit_decision(), {"ok": true, "error": ""})
    check("it equals the graph's own empty-action Bottom decision", c.last_report(), expected.fields())
    check("it equals the engine state of the reference", views(c._graph), views(ref))
    check("the engine, not the UI, classified it (D3-B decision kind is reported)", [c.last_report().kind, c.last_report().detail.decision.kind], ["bottom_decision", "UNARMED"])
    var lines: Array = c.view().last_lines
    check("the text names the engine's decision kind and makes no rule claim", lines[0], "Test Bravo (Bottom): no-action decision (engine decision kind UNARMED); the engine reset the window.")
    # It is the same engine path the scripted mode uses.
    var scripted := started("scripted")
    top_decision(scripted, reference())
    scripted.next_window()
    scripted.submit_decision()
    check("the scripted mode's Bottom decision leaves the same engine state", views(scripted._graph), views(c._graph))
    refused("the old window cannot be decided again", c.submit_decision(), "no_open_window")
    check("a no-action decision opens no extra window", c._graph.events().size(), 4)


# --- 7. a hold can replace the requested technique, and the UI says so ---------------------------------

# Searches (deterministically) for a Bottom window whose engine controller fields satisfy `wanted`.
func hold_pair() -> Array:
    return window_pair(func(fields: Dictionary) -> bool: return fields.recovery_hold_mode)


func window_pair(wanted: Callable) -> Array:
    for stamina: int in [100, 40, 12, 3]:
        for axis: float in [1.5, 0.5, 3.0]:
            var extra := {"bottom_stamina": stamina, "axis": axis}
            var c := started("two_sided", extra)
            var ref := reference(extra)
            for step: int in 60:
                if c.view().status_kind != "active" or not c.next_window().ok:
                    break
                ref.open_window()
                var window: Dictionary = c.view().window
                if not window.open:
                    break
                if window.role == "top":
                    var action: String = available_ids(c, "actions")[0]
                    c.select_action(action)
                    var response: String = available_ids(c, "responses")[0]
                    c.select_response(response)
                    c.submit_decision()
                    ref.submit(window.window_id, TOP_ID, action, response)
                else:
                    if wanted.call(c._graph.controller_fields()):
                        return [c, ref]
                    c.select_action(NO_ACTION)
                    c.submit_decision()
                    ref.submit(window.window_id, BOTTOM_ID)
    return []


func _test_hold_replaces_the_requested_technique() -> void:
    var pair := hold_pair()
    check("a recovery-hold Bottom window exists", pair.size(), 2)
    if pair.size() != 2:
        return
    var c: BjjMountPracticeController = pair[0]
    var ref: BjjPositionGraphMatch = pair[1]
    var window_id: int = c.view().window.window_id
    check("the engine is in its recovery-hold mode", c._graph.controller_fields().recovery_hold_mode, true)
    check("the technique rows are still the engine's real options", c.view().actions.slice(0, 3).map(func(r: Dictionary) -> Array: return [r.id, r.available]),
        ref.action_options(BOTTOM_ID).options.map(func(o: BjjPositionContract.Option) -> Array: return [o.id, o.available]))
    check("a technique is selected", [c.select_action(BRIDGE).ok, c.select_response(POST).ok], [true, true])
    var expected := ref.submit(window_id, BOTTOM_ID, BRIDGE, POST)
    check("the decision is accepted", c.submit_decision(), {"ok": true, "error": ""})
    check("the report equals the reference graph's report", c.last_report(), expected.fields())
    check("the engine ran a recovery hold, not the requested technique", [c.last_report().detail.decision.kind, c.last_report().detail.settlement.has("resolution"),
        c.last_report().detail.settlement.has("elapsed_seconds")], ["LOCKOUT_HOLD", false, true])
    check("the engine state equals the reference", views(c._graph), views(ref))
    check("the text tells the player exactly what happened", c.view().last_lines[0],
        "Test Bravo (Bottom): You chose Bridge, but the engine's D3-B decision ran a recovery hold instead (decision kind LOCKOUT_HOLD); no technique was attempted.")
    check("the No-action choice in the same state reads without a replaced technique",
        no_action_in_hold_window(), "Test Bravo (Bottom): the engine's D3-B decision ran a recovery hold (decision kind LOCKOUT_HOLD); no technique was attempted.")
    check("no grade or axis claim is made for a technique that was not attempted", c.view().last_lines.any(func(l: String) -> bool: return l.contains("grade") or l.begins_with("Axis ")), false)


func no_action_in_hold_window() -> String:
    var pair := hold_pair()
    if pair.size() != 2:
        return "no hold window"
    var c: BjjMountPracticeController = pair[0]
    var ref: BjjPositionGraphMatch = pair[1]
    c.select_action(NO_ACTION)
    var expected := ref.submit(c.view().window.window_id, BOTTOM_ID)
    c.submit_decision()
    check("the no-action decision in the hold window equals the reference", [c.last_report(), views(c._graph)], [expected.fields(), views(ref)])
    return c.view().last_lines[0]


# An armed (not yet locked-out) Bottom window: the technique is attempted and the engine decision kind is reported.
func _test_armed_window_reports_the_engine_decision_kind() -> void:
    var pair := window_pair(func(fields: Dictionary) -> bool: return fields.armed and not fields.recovery_hold_mode)
    check("an armed Bottom window exists", pair.size(), 2)
    if pair.size() != 2:
        return
    var c: BjjMountPracticeController = pair[0]
    var ref: BjjPositionGraphMatch = pair[1]
    var window_id: int = c.view().window.window_id
    c.select_action(BRIDGE)
    c.select_response(POST)
    var expected := ref.submit(window_id, BOTTOM_ID, BRIDGE, POST)
    check("the decision is accepted and equals the reference", [c.submit_decision().ok, c.last_report(), views(c._graph)], [true, expected.fields(), views(ref)])
    var kind: String = str(c.last_report().detail.decision.kind)
    check("the engine classified it as something other than UNARMED", kind != "UNARMED", true)
    check("the technique was attempted and the engine's decision kind is reported", [c.last_report().detail.settlement.has("resolution"), c.view().last_lines.has("Engine decision kind: %s" % kind)], [true, true])


# --- 8. stale, replayed and wrong-actor commands ------------------------------------------------

func _test_stale_replayed_and_wrong_actor_commands() -> void:
    var pair := at_bottom_window()
    var c: BjjMountPracticeController = pair[0]
    var g := c._graph
    var before := views(g)
    # Direct graph refusals with the engine's own codes; none of them can change anything.
    var cases: Array = [
        ["the Top fighter in the Bottom's window", 2, TOP_ID, BRIDGE, POST, "not_initiator"],
        ["a stale window id", 7, BOTTOM_ID, BRIDGE, POST, "stale_window"],
        ["window 1 again", 1, BOTTOM_ID, BRIDGE, POST, "stale_window"],
        ["a Top technique by the Bottom", 2, BOTTOM_ID, CLIMB, POST, "incorrect_action_side_or_kind"],
        ["a Bottom response id as the Top's response", 2, BOTTOM_ID, BRIDGE, FOREARM, "incorrect_response_side_or_kind"],
        ["a technique without a response", 2, BOTTOM_ID, BRIDGE, "", "unknown_response"],
        ["a response without a technique", 2, BOTTOM_ID, "", POST, "response_without_action"],
        ["an unavailable technique", 2, BOTTOM_ID, TRAP, POST, "setup_not_ready"],
        ["an unknown fighter", 2, "nobody", BRIDGE, POST, "unknown_fighter"]]
    for case: Array in cases:
        var report := g.submit(case[1], case[2], case[3], case[4])
        check("graph: %s" % case[0], [report.ok(), report.error], [false, case[5]])
    var with_commitment := g.submit(2, BOTTOM_ID, BRIDGE, POST, "HIGH")
    check("graph: a Bottom commitment", [with_commitment.ok(), with_commitment.error], [false, "commitment_is_policy_selected"])
    check("every refusal left the engine untouched", views(g), before)
    # After an accepted decision the same window is dead.
    c.select_action(BRIDGE)
    c.select_response(POST)
    check("the Bottom decision is accepted once", c.submit_decision(), {"ok": true, "error": ""})
    var settled := views(g)
    refused("Submit again (replay through the controller)", c.submit_decision(), "no_open_window")
    refused("selecting after the decision, with no window", c.select_action(BRIDGE), "not_selectable")
    var replay := g.submit(2, BOTTOM_ID, BRIDGE, POST)
    check("graph: replaying the accepted window", [replay.ok(), replay.error], [false, "no_open_window"])
    check("nothing changed after the replays", views(g), settled)
    # A Top window refuses the Bottom fighter.
    check("the next window is the Top's", [c.next_window().ok, c.view().window.role, c.view().window.window_id], [true, "top", 3])
    var wrong := g.submit(3, BOTTOM_ID, BRIDGE, POST)
    check("graph: the Bottom fighter in the Top's window", [wrong.ok(), wrong.error], [false, "not_initiator"])
    refused("the no-action row in a Top window", c.select_action(NO_ACTION), "unknown_action")
    refused("Submit in a Top window with nothing selected", c.submit_decision(), "technique_required")


# --- 9. blocked transitions are blocked, not victories ---------------------------------------------

# Drives the controller and a reference in lockstep until the match halts at the wanted exit.
func blocked_pair(label: String) -> Array:
    for axis: float in [0.2, 0.4, 0.8]:
        for action: String in [ELBOW, TRAP, BRIDGE]:
            for wanted: String in [POST, WIDE, HIP]:
                var extra := {"axis": axis}
                var c := started("two_sided", extra)
                var ref := reference(extra)
                for step: int in 40:
                    if c.view().status_kind != "active" or not c.next_window().ok:
                        break
                    ref.open_window()
                    var window: Dictionary = c.view().window
                    if not window.open:
                        break
                    if window.role == "top":
                        var top_action: String = available_ids(c, "actions")[0]
                        c.select_action(top_action)
                        var top_response: String = available_ids(c, "responses")[0]
                        c.select_response(top_response)
                        c.submit_decision()
                        ref.submit(window.window_id, TOP_ID, top_action, top_response)
                    else:
                        var legal: Array = available_ids(c, "actions")
                        var chosen: String = action if legal.has(action) else (BRIDGE if legal.has(BRIDGE) else NO_ACTION)
                        c.select_action(chosen)
                        var response := ""
                        if chosen != NO_ACTION:
                            var offered: Array = available_ids(c, "responses")
                            response = wanted if offered.has(wanted) else offered[0]
                            c.select_response(response)
                        c.submit_decision()
                        ref.submit(window.window_id, BOTTOM_ID, "" if chosen == NO_ACTION else chosen, response)
                if c._graph.status() == "halted_at_unsupported_transition" and c._graph.blocked_transition().label == label:
                    return [c, ref]
    return []


func _test_blocked_transitions_are_shown_as_blocked() -> void:
    for label: String in ["Half Guard", "Reversal"]:
        var pair := blocked_pair(label)
        check("a manual Bottom escape reaching '%s' exists" % label, pair.size(), 2)
        if pair.size() != 2:
            continue
        var c: BjjMountPracticeController = pair[0]
        var ref: BjjPositionGraphMatch = pair[1]
        var view := c.view()
        var blocked: Dictionary = c._graph.blocked_transition()
        check(label + ": the engine state equals the lockstep reference", views(c._graph), views(ref))
        check(label + ": the UI state is blocked, not terminal", [view.status_kind, view.status, view.terminal_reason], ["blocked", "halted_at_unsupported_transition", ""])
        check(label + ": the graph's exact blocked record is shown", view.blocked, blocked)
        check(label + ": the reason", blocked.reason, "unresolved_destination" if label == "Reversal" else "destination_not_implemented")
        check(label + ": the banner names the exit, the reason and says it is not a victory or defeat", [view.banner.contains(label), view.banner.contains(blocked.reason), view.banner.contains("not a victory or defeat")], [true, true, true])
        check(label + ": the banner never claims a landing", view.banner.contains("destination unresolved (no landing)") if label == "Reversal" else view.banner.contains("declared destination half_guard is not implemented"), true)
        check(label + ": no terminal outcome was recorded", c._graph.events().filter(func(e: Dictionary) -> bool: return e.kind == "terminal_outcome").size(), 0)
        check(label + ": the exchange that exited was accepted and then the transition was blocked", c._graph.events().slice(-2).map(func(e: Dictionary) -> String: return e.kind), ["decision_accepted", "transition_blocked"])
        check(label + ": the result text reports the exit and the engine's own result", [view.last_lines[0].begins_with("Test Bravo (Bottom): "), view.last_lines.has("Exit: %s" % label),
            view.last_lines.has("The escape threshold was reached.")], [true, true, true])
        check(label + ": every command is disabled with the graph's exact code", [view.commands.next_window, view.commands.submit], [{"enabled": false, "reason": HALTED}, {"enabled": false, "reason": HALTED}])
        check(label + ": no rows are offered", [view.actions, view.responses], [[], []])
        var before := views(c._graph)
        refused(label + ": Next Window after the halt", c.next_window(), HALTED)
        refused(label + ": Submit after the halt", c.submit_decision(), HALTED)
        refused(label + ": a technique after the halt", c.select_action(BRIDGE), HALTED)
        refused(label + ": no-action after the halt", c.select_action(NO_ACTION), HALTED)
        check(label + ": nothing changed after the refusals", views(c._graph), before)
        check(label + ": switching mode starts a fresh match and leaves the halted one halted", [c.set_practice_mode("scripted").ok, c.view().status_kind, ref.status()],
            [true, "active", "halted_at_unsupported_transition"])


# --- 10. terminal outcomes, and no duplicated effects ----------------------------------------------

func _test_terminal_and_no_duplicate_effects() -> void:
    var c := started("two_sided", {"clock": 10})
    var ref := reference({"clock": 10})
    for step: int in 200:
        if c.view().status_kind != "active":
            break
        c.next_window()
        ref.open_window()
        var window: Dictionary = c.view().window
        if not window.open:
            break
        if window.role == "top":
            var top_action: String = available_ids(c, "actions")[0]
            c.select_action(top_action)
            var top_response: String = available_ids(c, "responses")[0]
            c.select_response(top_response)
            c.submit_decision()
            ref.submit(window.window_id, TOP_ID, top_action, top_response)
        else:
            c.select_action(NO_ACTION)
            c.submit_decision()
            ref.submit(window.window_id, BOTTOM_ID)
    var view := c.view()
    check("a two-sided match can reach a terminal outcome", [view.status_kind, view.terminal_reason, view.banner], ["terminal", "timeout", "TERMINAL OUTCOME: timeout"])
    check("it equals the lockstep reference", views(c._graph), views(ref))
    check("the terminal outcome is not blocked", [view.blocked, view.banner.contains("BLOCKED")], [{}, false])
    refused("Next Window at the end", c.next_window(), "match_ended")
    refused("Submit at the end", c.submit_decision(), "match_ended")
    refused("a technique at the end", c.select_action(BRIDGE), "match_ended")
    refused("no-action at the end", c.select_action(NO_ACTION), "match_ended")
    check("New Practice Match is still possible and keeps the mode", [c.start_new_match(alpha(), bravo()).ok, c.practice_mode, c.view().status_kind], [true, "two_sided", "active"])

    # One decision is exactly one settlement: no extra clock, stamina or events.
    var pair := at_bottom_window()
    var g: BjjPositionGraphMatch = pair[0]._graph
    var before_state := g.state_fields()
    var before_events := g.events().size()
    pair[0].select_action(ELBOW)
    pair[0].select_response(HIP)
    pair[0].submit_decision()
    check("one Bottom decision added exactly one event", g.events().size(), before_events + 1)
    var expected_state: Dictionary = pair[1].state_fields()
    pair[1].submit(2, BOTTOM_ID, ELBOW, HIP)
    check("the clock and both stamina pools moved exactly as one reference settlement moves them", [g.state_fields().clock_seconds, g.state_fields().top_stamina, g.state_fields().bottom_stamina],
        [pair[1].state_fields().clock_seconds, pair[1].state_fields().top_stamina, pair[1].state_fields().bottom_stamina])
    check("the state before was the state the reference started from", [before_state.clock_seconds, before_state.top_stamina, before_state.bottom_stamina],
        [expected_state.clock_seconds, expected_state.top_stamina, expected_state.bottom_stamina])


# --- 11. refreshes are inert -------------------------------------------------------------------

func _test_refreshes_are_inert() -> void:
    var pair := at_bottom_window()
    var c: BjjMountPracticeController = pair[0]
    c.select_action(BRIDGE)
    var before := views(c._graph)
    var model := c.view()
    for i: int in 50:
        c.view()
    check("50 reads of a two-sided Bottom window changed nothing", views(c._graph), before)
    check("and returned the same model", c.view(), model)
    check("the selection survived the reads", [c.selected_action, c.selected_response], [BRIDGE, ""])


# --- 12. source boundaries ---------------------------------------------------------------------

func code_lines(path: String) -> Array:
    var lines: Array = []
    for line: String in FileAccess.get_file_as_string(path).split("\n"):
        if not line.strip_edges().begins_with("#"):
            lines.append(line)
    return lines


func offenders(path: String, forbidden: Array) -> Array:
    var found: Array = []
    for line: String in code_lines(path):
        for token: String in forbidden:
            if line.contains(token):
                found.append("%s :: %s" % [token, line.strip_edges()])
    return found


func _test_source_boundaries() -> void:
    var controller_path := "res://scripts/presentation/mount_practice_controller.gd"
    var scene_path := "res://scripts/presentation/mount_practice_scene.gd"
    check("Bottom decisions never use the low-level contract or match entry points", offenders(controller_path, ["bottom_decision", ".attempt(", "MountContract", "_contract", "reset_window", "recovery_hold", "d3b"]), [])
    check("the controller still sends only open_window and submit (three command lines)", code_lines(controller_path).filter(func(l: String) -> bool:
        return l.contains("_graph.open_window") or l.contains("_graph.submit(")).size(), 3)
    check("the scene reaches the simulation through the controller only", offenders(scene_path, ["_graph", "open_window", ".submit(", "BjjPositionGraphMatch", "state_fields"]), [])
    check("the scene's own state is still the controller handle only", code_lines(scene_path).filter(func(l: String) -> bool: return l.begins_with("var ")),
        ["var controller: BjjMountPracticeController = BjjMountPracticeController.new()"])
    var scene_text := FileAccess.get_file_as_string("res://scenes/mount_practice.tscn")
    check("the mode selector is the only new node", [scene_text.count("[node name=\"ModeOption\" type=\"OptionButton\""), scene_text.count("[ext_resource")], [1, 1])


# --- 13. the scene ---------------------------------------------------------------------------

func label_text(scene: Node, node_name: String) -> String:
    return (scene.get_node("%" + node_name) as Label).text


func _test_scene() -> void:
    var scene: Control = (load("res://scenes/mount_practice.tscn") as PackedScene).instantiate()
    root.add_child(scene)
    await process_frame
    var c: BjjMountPracticeController = scene.controller
    var mode: OptionButton = scene.get_node("%ModeOption")
    var next_button: Button = scene.get_node("%NextWindowButton")
    var submit_button: Button = scene.get_node("%SubmitButton")
    var techniques: ItemList = scene.get_node("%TechniqueList")
    var responses: ItemList = scene.get_node("%ResponseList")
    check("the mode selector offers the two modes and starts on scripted", [mode.item_count, mode.get_item_text(0), mode.get_item_text(1), mode.selected, c.practice_mode],
        [2, "Scripted practice", "Two-sided practice", 0, "scripted"])
    check("the mode selector explains itself", mode.tooltip_text.contains("Changing the mode starts a fresh match"), true)

    # Scripted behavior in the scene is untouched.
    next_button.pressed.emit()
    techniques.item_selected.emit(0)
    responses.item_selected.emit(0)
    submit_button.pressed.emit()
    next_button.pressed.emit()
    check("scripted: the Bottom window is labelled scripted", label_text(scene, "WindowLabel").contains("SCRIPTED practice behavior"), true)
    check("scripted: no No-action row and no selectable technique", [techniques.item_count, range(techniques.item_count).all(func(i: int) -> bool: return techniques.is_item_disabled(i))], [3, true])

    # Choosing two-sided starts a fresh match.
    var old_graph := c._graph
    var old_events := old_graph.events().size()
    var old_open: bool = old_graph.window_fields().open
    mode.item_selected.emit(1)
    check("two-sided: a fresh match replaced the graph", [c._graph != old_graph, c.practice_mode, c.match_serial, mode.selected], [true, "two_sided", 2, 1])
    check("two-sided: the message says why the match restarted", label_text(scene, "MessageLabel").begins_with("Practice mode changed to Two-sided practice: a fresh practice match was started"), true)
    check("two-sided: fresh clock, stamina and events", [label_text(scene, "ClockLabel"), label_text(scene, "FighterAStaminaLabel"), (scene.get_node("%EventLog") as RichTextLabel).text],
        ["Clock 5:00 remaining (300 s of 300)", "Stamina 100 / 100 - Fresh", ""])
    check("two-sided: the old match was not re-run", [old_graph.events().size(), old_graph.window_fields().open, old_graph.status()], [old_events, old_open, "active"])

    # A Top decision, then the Bottom's window with real choices.
    var ref := reference()
    ref.open_window()
    next_button.pressed.emit()
    techniques.item_selected.emit(0)
    responses.item_selected.emit(0)
    var ref_top := ref.submit(1, TOP_ID, CLIMB, FOREARM)
    submit_button.pressed.emit()
    check("two-sided: the Top decision equals the reference", c.last_report(), ref_top.fields())
    next_button.pressed.emit()
    ref.open_window()
    check("the Bottom's window is announced as a two-sided decision", label_text(scene, "WindowLabel"),
        "Window #2: Test Bravo (Bottom) decides. Two-sided practice: you choose Bottom's technique and the Top's response, or No action (the engine's existing Bottom decision: a reset or a recovery hold).")
    check("the technique header offers No action", label_text(scene, "TechniqueHeader"), "Choose Test Bravo's technique (or No action)")
    check("the response header waits for a technique", label_text(scene, "ResponseHeader"), "Top's response (choose a Bottom technique first)")
    check("four rows: three engine techniques and No action", techniques.item_count, 4)
    check("the available rows are enabled, the unavailable one shows the engine's reason", [techniques.is_item_disabled(0), techniques.is_item_disabled(1), techniques.is_item_disabled(2), techniques.is_item_disabled(3)],
        [false, false, true, false])
    check("the reason comes first on the disabled row", techniques.get_item_text(2), "[unavailable: setup_not_ready]  Trap-and-Roll Escape")
    check("the No-action row leads with No action and fits the list", techniques.get_item_text(3), "No action (reset or recovery hold)")
    check("engine rows keep their id as tooltip; the No-action row explains itself", [techniques.get_item_tooltip(0), techniques.get_item_tooltip(3)],
        [BRIDGE, "The engine's existing Bottom decision: a reset, or a recovery hold when the production policy says so. No technique is attempted."])
    check("Submit is disabled until the player chooses", submit_button.disabled, true)
    check("the commitment control is disabled for the Bottom", (scene.get_node("%CommitOption") as OptionButton).disabled, true)
    techniques.item_selected.emit(2)
    check("forcing the unavailable technique selects nothing", [c.selected_action, submit_button.disabled], ["", true])
    techniques.item_selected.emit(3)
    check("choosing No action says there is no Top response and enables Submit", [c.selected_action, responses.item_count, label_text(scene, "ResponseHeader"), submit_button.disabled],
        [NO_ACTION, 0, "No Top response: No action was chosen", false])
    techniques.item_selected.emit(0)
    check("choosing Bridge lists the Top's three responses", [c.selected_action, responses.item_count, label_text(scene, "ResponseHeader")], [BRIDGE, 3, "Top's response to the selected Bottom technique"])
    check("Submit still waits for a response", submit_button.disabled, true)
    responses.item_selected.emit(1)
    check("a response enables Submit", [c.selected_response, submit_button.disabled], [WIDE, false])
    var ref_bottom := ref.submit(2, BOTTOM_ID, BRIDGE, WIDE)
    var key := InputEventKey.new()
    key.keycode = KEY_S
    key.pressed = true
    scene._unhandled_key_input(key)
    check("the S hotkey submitted the Bottom's decision, equal to the reference", c.last_report(), ref_bottom.fields())
    check("the result panel names the Bottom's technique and labels the Top's response", label_text(scene, "ResultLabel").begins_with("Test Bravo (Bottom): Bridge; Top's response: "), true)
    check("the graph state equals the reference after both decisions", views(c._graph), views(ref))
    check("the event log lists the four graph events", (scene.get_node("%EventLog") as RichTextLabel).text, "\n".join(c.view().events))

    # No-action through the scene, then repeated refreshes.
    next_button.pressed.emit()
    ref.open_window()
    check("a Top window again", [c.view().window.role, c.view().window.window_id], ["top", 3])
    techniques.item_selected.emit(0)
    responses.item_selected.emit(0)
    var ref_top2 := ref.submit(3, TOP_ID, CLIMB if available_ids(c, "actions").has(CLIMB) else available_ids(c, "actions")[0], available_ids(c, "responses")[0])
    submit_button.pressed.emit()
    check("the second Top decision equals the reference", c.last_report(), ref_top2.fields())
    var settled := views(c._graph)
    for i: int in 30:
        scene.refresh()
    check("30 scene refreshes changed nothing", views(c._graph), settled)

    # New Practice Match keeps the mode; returning to scripted restores the scripted window.
    (scene.get_node("%NewMatchButton") as Button).pressed.emit()
    check("New Practice Match keeps two-sided mode", [c.practice_mode, mode.selected, c.match_serial], ["two_sided", 1, 3])
    mode.item_selected.emit(0)
    check("back to scripted: a fresh match and the scripted window", [c.practice_mode, c.match_serial, c._graph.events().size()], ["scripted", 4, 0])
    next_button.pressed.emit()
    techniques.item_selected.emit(0)
    responses.item_selected.emit(0)
    submit_button.pressed.emit()
    next_button.pressed.emit()
    check("scripted again: the Bottom window is scripted", label_text(scene, "WindowLabel").contains("SCRIPTED practice behavior"), true)
    root.remove_child(scene)
    scene.free()
    await process_frame
