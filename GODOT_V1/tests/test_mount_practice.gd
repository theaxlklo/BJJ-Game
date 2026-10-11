extends SceneTree

# Negative-first tests for F1: the graph-backed fighter snapshot adapter, the presentation controller
# and the 2D Mount practice scene. Everything simulated goes through BjjPositionGraphMatch; a
# separately driven REFERENCE graph with identical inputs is the oracle for what the controller
# did. Test-side private access (controller._graph, graph._gateway) is used only as an oracle or to
# drive the engine into states the scripted practice opponent never reaches, as the existing graph
# and gateway suites do; the production presentation code never does it.
const TOP_ID: String = "fighter_alpha"
const BOTTOM_ID: String = "fighter_bravo"
const ALPHA_RES: String = "res://tests/resources/fighter_test_alpha.tres"
const BRAVO_RES: String = "res://tests/resources/fighter_test_bravo.tres"
const CLIMB: String = "mount.top.high_mount_climb"
const CROSSFACE: String = "mount.top.crossface_pressure"
const ISOLATION: String = "mount.top.americana_arm_isolation"
const FINISH: String = "mount.top.americana_submission_finish"
const FOREARM: String = "mount.bottom_response.forearm_frame"
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
    _test_graph_pass_through()
    _test_adapter_over_graph_negatives()
    _test_adapter_over_graph_matches_gateway()
    _test_practice_configuration_and_settings()
    _test_controller_refusals_change_nothing()
    _test_controller_equals_reference_graph()
    _test_scripted_bottom_decision()
    await _test_unavailable_responses_cannot_be_chosen()
    _test_refreshes_are_inert()
    _test_blocked_transitions()
    _test_terminal_timeout_and_tap()
    _test_new_match_independence()
    _test_source_boundaries()
    await _test_scene()
    # Same completion contract as the other suites: one PASS line with the exact count. CI also
    # validates the whole log, because a script error can abort one test function and still
    # end here with exit 0 and a smaller count.
    if failures > 0:
        push_error("Mount practice: %d / %d assertions failed" % [failures, checks])
        quit(1)
        return
    print("Mount practice PASS: %d assertions" % checks)
    quit(0)


# --- helpers ---------------------------------------------------------------------------

class FakeSource extends RefCounted:
    func roles() -> BjjPositionContract.Roles:
        var roles := BjjPositionContract.Roles.new()
        roles.fighter_by_role = {"top": "fighter_alpha", "bottom": "fighter_bravo"}
        return roles

    func state_fields() -> Dictionary:
        return {}

    func behavior_fields() -> Dictionary:
        return {}


func alpha() -> BjjFighterDefinition:
    return load(ALPHA_RES)


func bravo() -> BjjFighterDefinition:
    return load(BRAVO_RES)


func started(extra: Dictionary = {}) -> BjjMountPracticeController:
    var c := BjjMountPracticeController.new()
    var result := c.start_new_match(alpha(), bravo(), extra)
    check("practice match started", result, {"ok": true, "error": ""})
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


func gateway_views(g: BjjMatchWindowGateway) -> Dictionary:
    return {"state": g.state_fields(), "history": g.history_fields(), "controller": g.controller_fields(), "window": g.window_fields(),
        "behaviors": g.behavior_fields(), "roles": g.roles().fields(), "lifecycle": g._match.lifecycle_fields()}


func config_with(extra: Dictionary) -> Dictionary:
    var config := BjjMountPracticeController.match_configuration()
    config.merge(extra, true)
    return config


# Picks by preference among the AVAILABLE actions the controller's own view lists.
func play_window(c: BjjMountPracticeController, preference: Array, response_index: int) -> void:
    check("a window opens", c.next_window().ok, true)
    var view := c.view()
    if view.status_kind != "active" or not view.window.open:
        return
    if not view.window.scripted:
        var chosen: String = ""
        for wanted: String in preference:
            for row: Dictionary in view.actions:
                if row.available and row.id.ends_with(wanted):
                    chosen = row.id
                    break
            if not chosen.is_empty():
                break
        check("an action was chosen", c.select_action(chosen).ok, true)
        var responses: Array = c.view().responses
        check("a response was chosen", c.select_response(responses[mini(response_index, responses.size() - 1)].id).ok, true)
    check("a decision is accepted", c.submit_decision().ok, true)


func play_to_end(c: BjjMountPracticeController, preference: Array, response_index: int) -> void:
    for step: int in 200:
        if c.view().status_kind != "active":
            return
        play_window(c, preference, response_index)


# --- 1. the graph's read-only pass-through ----------------------------------------------

func _test_graph_pass_through() -> void:
    var g := reference()
    check("initial held behaviors", g.behavior_fields(), {"top": "PRESSURE", "bottom": "ESCAPE"})
    check("agrees with the gateway behind the graph", g.behavior_fields(), g._gateway.behavior_fields())
    var tampered := g.behavior_fields()
    tampered["top"] = "tampered"
    tampered["extra"] = 1
    check("a returned dictionary is detached", g.behavior_fields(), {"top": "PRESSURE", "bottom": "ESCAPE"})
    var before := views(g)
    for i: int in 25:
        g.behavior_fields()
    check("reading behaviors through the graph is inert", views(g), before)
    var public_names: Array = []
    for method: Dictionary in (BjjPositionGraphMatch as Script).get_script_method_list():
        var name: String = str(method.name)
        if not name.begins_with("_") and not name.begins_with("@"):
            public_names.append(name)
    check("the graph exposes no accessor for its gateway", public_names.filter(func(n: String) -> bool: return n.contains("gateway")), [])
    check("the pass-through is part of the graph's public surface", public_names.has("behavior_fields"), true)


# --- 2. the adapter over a graph: negatives first ---------------------------------------

func rejected_graph(label: String, source: Variant, definitions: Variant, expected_error: String) -> void:
    var before: Dictionary = views(source) if source is BjjPositionGraphMatch else {}
    var created := BjjFighterSnapshotAdapter.create(source, definitions)
    check(label + ": rejected", created.ok(), false)
    check(label + ": code", created.error, expected_error)
    check(label + ": no adapter", created.adapter == null, true)
    if source is BjjPositionGraphMatch:
        check(label + ": graph untouched", views(source), before)


func _test_adapter_over_graph_negatives() -> void:
    var g := reference()
    var pair := {TOP_ID: alpha(), BOTTOM_ID: bravo()}
    for bad: Variant in [null, 5, "graph", [], {}, RefCounted.new(), BjjMountMatch.create({}).match_state, BjjMountPracticeController.new()]:
        rejected_graph("not a source: " + var_to_str(bad).substr(0, 20), bad, pair, "missing_gateway")
    for bad_map: Variant in [null, 5, "map", [alpha(), bravo()]]:
        rejected_graph("definitions not a Dictionary: " + var_to_str(bad_map).substr(0, 20), g, bad_map, "invalid_definitions")
    rejected_graph("empty mapping", g, {}, "missing_fighter_definition")
    rejected_graph("duck-typed object with the same methods", FakeSource.new(), pair, "missing_gateway")
    rejected_graph("only the top fighter", g, {TOP_ID: alpha()}, "missing_fighter_definition")
    rejected_graph("only the bottom fighter", g, {BOTTOM_ID: bravo()}, "missing_fighter_definition")
    rejected_graph("unknown id", g, {TOP_ID: alpha(), "fighter_charlie": bravo()}, "unknown_fighter_id")
    rejected_graph("a third fighter", g, {TOP_ID: alpha(), BOTTOM_ID: bravo(), "fighter_charlie": alpha()}, "unknown_fighter_id")
    rejected_graph("case mismatch", g, {"Fighter_alpha": alpha(), BOTTOM_ID: bravo()}, "unknown_fighter_id")
    rejected_graph("whitespace mismatch", g, {TOP_ID + " ": alpha(), BOTTOM_ID: bravo()}, "unknown_fighter_id")
    rejected_graph("empty-string id", g, {"": alpha(), BOTTOM_ID: bravo()}, "unknown_fighter_id")
    rejected_graph("definition ids used as fighter ids", g, {"test_template_alpha": alpha(), "test_template_bravo": bravo()}, "unknown_fighter_id")
    rejected_graph("a non-String key among valid ones", g, {TOP_ID: alpha(), BOTTOM_ID: bravo(), 3: alpha()}, "invalid_fighter_id_key")
    rejected_graph("integer keys", g, {1: alpha(), 2: bravo()}, "invalid_fighter_id_key")
    rejected_graph("StringName keys", g, {&"fighter_alpha": alpha(), &"fighter_bravo": bravo()}, "invalid_fighter_id_key")
    rejected_graph("null definition", g, {TOP_ID: null, BOTTOM_ID: bravo()}, "invalid_fighter_definition")
    rejected_graph("null definition for the bottom fighter", g, {TOP_ID: alpha(), BOTTOM_ID: null}, "invalid_fighter_definition")
    for wrong: Variant in ["alpha", 5, {}, [], Resource.new(), RefCounted.new()]:
        rejected_graph("wrong value type: " + var_to_str(wrong).substr(0, 20), g, {TOP_ID: wrong, BOTTOM_ID: bravo()}, "invalid_fighter_definition")
    rejected_graph("a fresh definition", g, {TOP_ID: BjjFighterDefinition.new(), BOTTOM_ID: bravo()}, "invalid_definition_id")
    var padded := BjjFighterDefinition.new()
    padded.definition_id = "padded_one"
    padded.display_name = " Padded "
    rejected_graph("a padded name", g, {TOP_ID: alpha(), BOTTOM_ID: padded}, "invalid_display_name")
    check("a rejected definition keeps its padding (never trimmed)", padded.display_name, " Padded ")
    var shouting := BjjFighterDefinition.new()
    shouting.definition_id = "Shouting_Id"
    shouting.display_name = "Shouting"
    rejected_graph("an upper-case id", g, {TOP_ID: alpha(), BOTTOM_ID: shouting}, "invalid_definition_id")
    check("a rejected definition keeps its id (never lowered)", shouting.definition_id, "Shouting_Id")
    var nameless := BjjFighterDefinition.new()
    nameless.definition_id = "nameless_one"
    rejected_graph("a definition with no name", g, {TOP_ID: alpha(), BOTTOM_ID: nameless}, "invalid_display_name")
    rejected_graph("the first failing fighter (sorted by id) decides", g, {TOP_ID: shouting, BOTTOM_ID: nameless}, "invalid_definition_id")
    rejected_graph("the bottom fighter's own error is reported", g, {TOP_ID: alpha(), BOTTOM_ID: shouting}, "invalid_definition_id")
    # While a window is open and after a decision, refusals still change nothing.
    g.open_window()
    rejected_graph("while a window is open", g, {TOP_ID: alpha()}, "missing_fighter_definition")
    # A graph that has halted or ended can still be read.
    var halted_graph := _halted_graph("Half Guard")
    check("a halting scenario exists for the read-source check", halted_graph != null, true)
    check("a halted graph is still a valid read source", BjjFighterSnapshotAdapter.create(halted_graph, pair).ok(), true)
    var ended := started({"clock": 10})
    play_to_end(ended, ["crossface_pressure"], 0)
    var ended_adapter := BjjFighterSnapshotAdapter.create(ended._graph, pair)
    check("an ended graph is still a valid read source", ended_adapter.ok(), true)
    check("and reads its final state", [ended_adapter.adapter.snapshots()[TOP_ID].role, ended_adapter.adapter.snapshots()[TOP_ID].stamina_current],
        ["top", ended._graph.state_fields().top_stamina])
    # Identity metadata is copied at creation over a graph too.
    var shared := alpha().duplicate()
    var copied := BjjFighterSnapshotAdapter.create(reference(), {TOP_ID: shared, BOTTOM_ID: bravo()}).adapter
    var before_edit := copied.snapshots()
    shared.display_name = "Edited Later"
    check("later edits to a definition do not leak into graph-backed snapshots", copied.snapshots(), before_edit)


# --- 3. the adapter over a graph agrees with the gateway-backed path -------------------

func _test_adapter_over_graph_matches_gateway() -> void:
    var config := config_with({"top_stamina": 80, "bottom_stamina": 35})
    var graph := BjjPositionGraphMatch.create(config, TOP_ID, BOTTOM_ID).graph
    var gateway := BjjMatchWindowGateway.create(config, TOP_ID, BOTTOM_ID).gateway
    var pair := {TOP_ID: alpha(), BOTTOM_ID: bravo()}
    var over_graph := BjjFighterSnapshotAdapter.create(graph, pair).adapter
    var over_gateway := BjjFighterSnapshotAdapter.create(gateway, pair).adapter
    check("before a window: both paths agree", over_graph.snapshots(), over_gateway.snapshots())
    check("fighter ids agree", over_graph.fighter_ids(), over_gateway.fighter_ids())
    var start := over_graph.snapshots()
    check("literal start values (graph path)", [start[TOP_ID].stamina_current, start[TOP_ID].exhaustion_band, start[BOTTOM_ID].stamina_current,
        start[BOTTOM_ID].exhaustion_band, start[TOP_ID].behavior, start[BOTTOM_ID].behavior], [80, "Fresh", 35, "Tired", "PRESSURE", "ESCAPE"])
    for step: int in 8:
        graph.open_window()
        gateway.open_window()
        check("step %d window open: both paths agree" % step, over_graph.snapshots(), over_gateway.snapshots())
        var window := graph.window_fields()
        check("step %d: both opened the same window" % step, window, gateway.window_fields())
        var graph_report: BjjMatchWindowGateway.Report
        var gateway_report: BjjMatchWindowGateway.Report
        if window.role == "top":
            var action: String = graph.action_options(window.fighter_id).available_ids()[0]
            var response: String = graph.response_options(action).available_ids()[0]
            graph_report = graph.submit(window.window_id, window.fighter_id, action, response)
            gateway_report = gateway.submit(window.window_id, window.fighter_id, action, response)
        else:
            graph_report = graph.submit(window.window_id, window.fighter_id)
            gateway_report = gateway.submit(window.window_id, window.fighter_id)
        check("step %d: both decisions accepted" % step, [graph_report.ok(), gateway_report.ok()], [true, true])
        check("step %d after the decision: both paths agree" % step, over_graph.snapshots(), over_gateway.snapshots())
        var after := over_graph.snapshots()
        var state := graph.state_fields()
        for role: String in ["top", "bottom"]:
            var id: String = graph.roles().fighter_by_role[role]
            check("step %d %s agrees with the graph's state_fields()" % [step, role],
                [after[id].stamina_current, after[id].stamina_maximum, after[id].exhaustion_band, after[id].role],
                [state[role + "_stamina"], state[role + "_maximum"], state[role + "_band"], role])
            check("step %d %s behavior agrees with the match" % [step, role], after[id].behavior, graph._gateway._match.lifecycle_fields()[role + "_behavior"])
    # Detached, inert and role-by-identity semantics hold over the graph too.
    var before := views(graph)
    var expected := over_graph.snapshots()
    for i: int in 30:
        over_graph.snapshots()
    check("repeated reads over a graph are inert", views(graph), before)
    var tampered := over_graph.snapshots()
    tampered[TOP_ID].stamina_current = 99999
    tampered[BOTTOM_ID]["extra"] = true
    tampered.erase(TOP_ID)
    check("tampering with a snapshot never reaches the graph", views(graph), before)
    check("later snapshots are unaffected", over_graph.snapshots(), expected)
    var swapped := BjjPositionGraphMatch.create(config_with({"top_stamina": 80, "bottom_stamina": 35}), BOTTOM_ID, TOP_ID).graph
    var swapped_snaps := BjjFighterSnapshotAdapter.create(swapped, {TOP_ID: _named("Top Dog"), BOTTOM_ID: _named("Bottom Feeder")}).adapter.snapshots()
    check("roles follow identity, not display names, over a graph", [swapped_snaps[BOTTOM_ID].role, swapped_snaps[BOTTOM_ID].stamina_current,
        swapped_snaps[TOP_ID].role, swapped_snaps[TOP_ID].stamina_current], ["top", 80, "bottom", 35])


func _named(display: String) -> BjjFighterDefinition:
    var d := BjjFighterDefinition.new()
    d.definition_id = "named_" + display.to_lower().replace(" ", "_")
    d.display_name = display
    return d


# --- 3b. the practice configuration and the settings allow-list ------------------------

func _test_practice_configuration_and_settings() -> void:
    var config := BjjMountPracticeController.match_configuration()
    check("the configuration holds only the rules block", config.keys(), ["rules"])
    var rules: Dictionary = config.rules
    var base := BjjProductionStaminaPolicy.settings()
    check("setup, submissions and commitment semantics are enabled", [rules.enable_v02_setup, rules.enable_v03_submissions, rules.enable_v04_commitment_semantics], [true, true, true])
    var unexpected: Array = []
    for key: Variant in rules:
        if not ["enable_v02_setup", "enable_v03_submissions", "enable_v04_commitment_semantics"].has(key) and (not base.has(key) or rules[key] != base[key]):
            unexpected.append(key)
    for key: Variant in base:
        if not rules.has(key):
            unexpected.append(key)
    check("every other policy value is the production policy's own", unexpected, [])
    # The settings a caller may override: only the allow-listed, engine-validated ones.
    check("the allow-list", BjjMountPracticeController.SETTINGS_ALLOW_LIST, ["clock", "interval", "axis", "top_stamina", "bottom_stamina"])
    var c := started()
    var graph := c._graph
    var serial := c.match_serial
    for bad: Dictionary in [{"rules": {}}, {"production": false}, {"capacity": 50}, {"unknown": 1}, {5: 1}, {"clock": 10, "rules": {}}]:
        check("a refused setting: " + var_to_str(bad), c.start_new_match(alpha(), bravo(), bad), {"ok": false, "error": "unsupported_practice_setting"})
        check("the current match survives: " + var_to_str(bad), [c._graph == graph, c.match_serial], [true, serial])
    var invalid := c.start_new_match(alpha(), bravo(), {"clock": -1})
    check("an allowed key with an invalid value is refused by the engine", [invalid.ok, invalid.error != "unsupported_practice_setting"], [false, true])
    check("and the current match survives that too", [c._graph == graph, c.match_serial], [true, serial])
    check("allowed settings are applied", c.start_new_match(alpha(), bravo(), {"clock": 20, "interval": 4, "axis": 1.0, "top_stamina": 50, "bottom_stamina": 60}), {"ok": true, "error": ""})
    var state := c._graph.state_fields()
    check("the engine holds the chosen settings", [state.initial_clock, state.top_stamina, state.bottom_stamina, state.axis], [20, 50, 60, 1.0])


# --- 4. controller refusals change nothing ---------------------------------------------

func refused(label: String, _controller: BjjMountPracticeController, result: Dictionary, expected_error: String) -> void:
    check(label + ": refused with the exact code", result, {"ok": false, "error": expected_error})


func _test_controller_refusals_change_nothing() -> void:
    var c := started()
    var before := views(c._graph)
    check("before a window: submit is disabled", c.view().commands.submit, {"enabled": false, "reason": "no_open_window"})
    check("before a window: next window is enabled", c.view().commands.next_window, {"enabled": true, "reason": ""})
    refused("submit with no window", c, c.submit_decision(), "no_open_window")
    refused("select an action with no window", c, c.select_action(CLIMB), "not_selectable")
    refused("select a response before a technique", c, c.select_response(FOREARM), "technique_required")
    refused("select a commitment with no window", c, c.select_commitment("HIGH"), "commitment_is_policy_selected")
    check("no action rows are offered before a window", c.view().actions, [])
    check("refusals before a window changed nothing", views(c._graph), before)

    check("next window is accepted", c.next_window().ok, true)
    var open_state := views(c._graph)
    refused("a second Next Window", c, c.next_window(), "window_already_open")
    check("Next Window is disabled while a window is open", c.view().commands.next_window, {"enabled": false, "reason": "window_already_open"})
    refused("an unavailable technique (setup not ready)", c, c.select_action(ISOLATION), "setup_not_ready")
    refused("an unavailable technique (inactive submission)", c, c.select_action(FINISH), "inactive_submission")
    refused("an unknown technique", c, c.select_action("mount.top.nonsense"), "unknown_action")
    refused("a bottom technique in the top window", c, c.select_action("mount.bottom.bridge"), "unknown_action")
    check("nothing was selected by the refusals", [c.selected_action, c.selected_response, c.selected_commitment], ["", "", ""])
    refused("a response with no technique selected", c, c.select_response(FOREARM), "technique_required")
    refused("submit with no technique", c, c.submit_decision(), "technique_required")
    check("submit is disabled with its exact reason", c.view().commands.submit, {"enabled": false, "reason": "technique_required"})
    check("a legal technique is accepted", c.select_action(CLIMB).ok, true)
    refused("an unknown response", c, c.select_response("mount.bottom_response.nonsense"), "unknown_response")
    refused("a Top response is not a Bottom response", c, c.select_response("mount.top_response.post_and_base"), "unknown_response")
    refused("submit with no response", c, c.submit_decision(), "response_required")
    check("an unknown commitment is never stored", c.selected_commitment, "")
    check("submit is disabled with its exact reason (response)", c.view().commands.submit, {"enabled": false, "reason": "response_required"})
    refused("an unknown commitment", c, c.select_commitment("EXTREME"), "unknown_commitment")
    check("changing the technique clears the response", c.select_response(FOREARM).ok and c.select_action(CROSSFACE).ok and c.selected_response == "", true)
    check("none of the refusals touched the simulation", views(c._graph), open_state)
    check("the enabled rows are exactly the engine's available ones", c.view().actions.filter(func(r: Dictionary) -> bool: return r.available).map(
        func(r: Dictionary) -> String: return r.id), c._graph.action_options(TOP_ID).available_ids())
    check("every unavailable row carries the engine's exact reason", c.view().actions.filter(func(r: Dictionary) -> bool: return not r.available).map(
        func(r: Dictionary) -> String: return r.reason), ["setup_not_ready", "inactive_submission"])

    # Stale, replayed and wrong-fighter decisions are refused by the graph without mutation.
    var g := c._graph
    var window := g.window_fields()
    for attempt: Array in [[window.window_id + 1, TOP_ID, CLIMB, FOREARM, "stale_window"], [window.window_id - 1, TOP_ID, CLIMB, FOREARM, "stale_window"],
            [window.window_id, BOTTOM_ID, CLIMB, FOREARM, "not_initiator"], [window.window_id, "fighter_zzz", CLIMB, FOREARM, "unknown_fighter"],
            [window.window_id, TOP_ID, "mount.top.nonsense", FOREARM, "unknown_action"], [window.window_id, TOP_ID, CLIMB, "", "missing_response"]]:
        var report := g.submit(attempt[0], attempt[1], attempt[2], attempt[3])
        check("direct graph refusal %s" % attempt[4], [report.ok(), report.error != ""], [false, true])
        check("direct graph refusal changes nothing: %s" % attempt[4], views(g), open_state)
    # An accepted decision makes the same window id stale.
    check("select the technique", c.select_action(CLIMB).ok and c.select_response(FOREARM).ok, true)
    check("the decision is accepted", c.submit_decision().ok, true)
    var after_decision := views(g)
    var replay := g.submit(window.window_id, TOP_ID, CLIMB, FOREARM)
    check("a replayed decision is refused", [replay.ok(), replay.error], [false, "no_open_window"])
    refused("a second submit", c, c.submit_decision(), "no_open_window")
    check("replays changed nothing", views(g), after_decision)


# --- 5. the controller equals a separately driven reference graph -----------------------

func _test_controller_equals_reference_graph() -> void:
    var c := started()
    var ref := reference()
    check("fresh controller graph equals a fresh reference graph", views(c._graph), views(ref))
    var commitments := ["", "HIGH", "LOW", "MEDIUM"]
    var top_windows: int = 0
    for step: int in 8:
        check("step %d: next window is accepted" % step, c.next_window().ok, true)
        var ref_open := ref.open_window()
        check("step %d: the reference opened a window" % step, ref_open.ok(), true)
        check("step %d: the open windows are identical" % step, views(c._graph), views(ref))
        var window := ref.window_fields()
        var ref_report: BjjMatchWindowGateway.Report
        if window.role == "top":
            var action: String = ref.action_options(TOP_ID).available_ids()[step % 2]
            var response: String = ref.response_options(action).available_ids()[step % 3]
            check("step %d: technique selected" % step, c.select_action(action).ok, true)
            check("step %d: response selected" % step, c.select_response(response).ok, true)
            var commitment: String = commitments[top_windows % commitments.size()]
            top_windows += 1
            if not commitment.is_empty():
                check("step %d: commitment %s selected" % [step, commitment], c.select_commitment(commitment).ok, true)
            ref_report = ref.submit(window.window_id, TOP_ID, action, response, commitment)
        else:
            ref_report = ref.submit(window.window_id, BOTTOM_ID)
        check("step %d: the controller's decision is accepted" % step, c.submit_decision().ok, true)
        check("step %d: the reference's decision is accepted" % step, ref_report.ok(), true)
        check("step %d: identical simulation report" % step, c.last_report(), ref_report.fields())
        check("step %d: identical simulation state, events and histories" % step, views(c._graph), views(ref))
    check("the four Top windows used every commitment choice", top_windows, 4)
    check("the event lines are formatted from the graph's events", c.view().events.slice(0, 3), ["#1 window_opened - window 1, Test Alpha (top)",
        "#2 decision_accepted - window 1, Test Alpha (top), top_exchange", "#3 window_opened - window 2, Test Bravo (bottom)"])
    check("grade names cover the five engine grades", BjjMountPracticeController.GRADE_NAMES, {-2: "Strong Failure", -1: "Failure", 0: "Contested", 1: "Success", 2: "Strong Success"})
    var detached_report := c.last_report()
    detached_report["state"]["clock_seconds"] = -1
    check("a returned report is a deep copy", c.last_report().state.clock_seconds != -1, true)
    var detached_lines: Array = c.view().last_lines
    detached_lines.append("tampered")
    check("the result lines are a copy", c.view().last_lines.has("tampered"), false)
    var tampered := c.last_report()
    tampered["state"] = {}
    check("tampering with the report copy changes nothing", c.last_report().state.is_empty(), false)
    check("a commitment that was never chosen is not sent", c.selected_commitment, "")
    var hands := started()
    check("a commitment is selectable only in a Top window", [hands.view().commitment.selectable, hands.next_window().ok, hands.view().commitment.selectable,
        hands.view().commitment.selected, hands.view().commitment.policy_selected], [false, true, true, "MEDIUM", "MEDIUM"])
    check("selecting HIGH is shown", [hands.select_commitment("HIGH").ok, hands.view().commitment.selected], [true, "HIGH"])


# --- 6. the deterministic scripted Bottom decision -------------------------------------

func _test_scripted_bottom_decision() -> void:
    var c := started()
    var ref := reference()
    c.next_window()
    ref.open_window()
    c.select_action(CLIMB)
    c.select_response(FOREARM)
    c.submit_decision()
    ref.submit(1, TOP_ID, CLIMB, FOREARM)
    check("the bottom window opens", c.next_window().ok, true)
    ref.open_window()
    var view := c.view()
    check("the window belongs to the Bottom fighter and is labelled scripted", [view.window.role, view.window.fighter_id, view.window.scripted],
        ["bottom", BOTTOM_ID, true])
    check("the Bottom's techniques are informational and not selectable", view.actions.filter(func(r: Dictionary) -> bool: return r.available), [])
    check("the scripted reason is shown for techniques that are legal for the engine", view.actions.filter(func(r: Dictionary) -> bool: return r.reason == "scripted_practice_opponent").size() > 0, true)
    check("engine reasons stay exact for the others", view.actions.filter(func(r: Dictionary) -> bool: return r.reason == "setup_not_ready").size(), 1)
    check("the player cannot pick a Bottom technique", c.select_action("mount.bottom.bridge").error, "not_selectable")
    check("the player cannot pick a commitment for the Bottom", c.select_commitment("HIGH").error, "commitment_is_policy_selected")
    check("submit is enabled without any selection", c.view().commands.submit, {"enabled": true, "reason": ""})
    var before_events := c._graph.events().size()
    check("the scripted decision is accepted", c.submit_decision().ok, true)
    var ref_report := ref.submit(2, BOTTOM_ID)
    check("it equals the existing no-action Bottom decision on the reference graph", c.last_report(), ref_report.fields())
    check("it used the existing admitted path", [c.last_report().kind, c.last_report().detail.decision.kind], ["bottom_decision", "UNARMED"])
    check("exactly one decision event was added by the graph", c._graph.events().size(), before_events + 1)
    check("the decision is labelled as scripted", c.view().last_lines[0].contains("SCRIPTED"), true)
    check("it is not described as combat AI", c.view().last_lines[0].contains("combat AI"), false)
    check("states are identical afterwards", views(c._graph), views(ref))


# --- 6b. a response the engine marks unavailable --------------------------------------------

# Builds the engine state in which the Americana arm isolation is ready (High Mount Climb builds
# its setup) and selects it; the engine then marks some responses incompatible with the ready setup.
func _controller_with_isolation_selected() -> BjjMountPracticeController:
    var c := started()
    for step: int in 40:
        check("a window opens", c.next_window().ok, true)
        var view := c.view()
        if view.window.scripted:
            check("scripted decision accepted", c.submit_decision().ok, true)
            continue
        var isolation_ready: bool = view.actions.any(func(r: Dictionary) -> bool: return r.id == ISOLATION and r.available)
        if isolation_ready:
            check("the ready isolation is selectable", c.select_action(ISOLATION).ok, true)
            return c
        check("climb selected", c.select_action(CLIMB).ok and c.select_response(FOREARM).ok, true)
        check("climb accepted", c.submit_decision().ok, true)
    return null


func _test_unavailable_responses_cannot_be_chosen() -> void:
    var c := _controller_with_isolation_selected()
    check("a state with a ready Americana setup is reachable", c != null, true)
    if c == null:
        return
    var rows: Array = c.view().responses
    var engine_rows: Array = c._graph.response_options(ISOLATION).options.map(func(o: BjjPositionContract.Option) -> Dictionary:
        return {"id": o.id, "available": o.available, "reason": o.reason})
    check("the response rows are exactly the engine's options", rows.map(func(r: Dictionary) -> Dictionary:
        return {"id": r.id, "available": r.available, "reason": r.reason}), engine_rows)
    var unavailable: Array = rows.filter(func(r: Dictionary) -> bool: return not r.available)
    var available: Array = rows.filter(func(r: Dictionary) -> bool: return r.available)
    check("the engine marks at least one response unavailable and at least one available", [unavailable.size() > 0, available.size() > 0], [true, true])
    check("every unavailable response carries the engine's exact reason", unavailable.map(func(r: Dictionary) -> String: return r.reason).filter(
        func(reason: String) -> bool: return reason != "incompatible_ready_response"), [])
    var before := views(c._graph)
    for row: Dictionary in unavailable:
        refused("selecting the unavailable response " + row.id, c, c.select_response(row.id), "incompatible_ready_response")
    check("nothing was selected by the refusals", [c.selected_response, c.view().commands.submit], ["", {"enabled": false, "reason": "response_required"}])
    refused("submitting without a legal response", c, c.submit_decision(), "response_required")
    check("the refusals changed nothing", views(c._graph), before)
    check("an available response can be chosen", [c.select_response(available[0].id).ok, c.view().commands.submit.enabled], [true, true])
    check("choosing a response is a UI selection only", c.selected_response, available[0].id)
    c.selected_response = ""
    # The same state through the scene's lists.
    var scene: Control = load("res://scenes/mount_practice.tscn").instantiate()
    root.add_child(scene)
    await process_frame
    scene.controller = c
    scene.refresh()
    var list: ItemList = scene.get_node("%ResponseList")
    var seen_disabled: int = 0
    for index: int in list.item_count:
        var row: Dictionary = c.view().responses[index]
        check("response row %d is disabled exactly when the engine says unavailable" % index, [list.is_item_disabled(index), list.is_item_selectable(index)], [not row.available, row.available])
        if not row.available:
            seen_disabled += 1
            check("response row %d shows the exact reason" % index, list.get_item_text(index).contains("[unavailable: incompatible_ready_response]"), true)
            list.item_selected.emit(index)
            check("forcing response row %d selects nothing" % index, [c.selected_response, (scene.get_node("%SubmitButton") as Button).disabled], ["", true])
    check("the scene showed the disabled rows", seen_disabled, unavailable.size())
    root.remove_child(scene)
    scene.free()
    await process_frame


# --- 7. refreshing is a pure read -----------------------------------------------------

func _test_refreshes_are_inert() -> void:
    var c := started()
    c.next_window()
    var before := views(c._graph)
    for i: int in 50:
        c.view()
    check("window open: 50 view() reads are inert", views(c._graph), before)
    c.select_action(CLIMB)
    c.select_response(FOREARM)
    c.submit_decision()
    var after := views(c._graph)
    for i: int in 50:
        c.view()
    check("after a decision: 50 view() reads are inert", views(c._graph), after)
    check("the clock did not move", c._graph.state_fields().clock_seconds, after.state.clock_seconds)
    check("no window opened by reading", c._graph.window_fields().open, false)
    check("the event log did not grow", c._graph.events(), after.events)
    var fresh := started()
    var fresh_before := views(fresh._graph)
    for i: int in 50:
        fresh.view()
    check("before a window: 50 view() reads are inert", views(fresh._graph), fresh_before)


# --- 8. blocked transitions ----------------------------------------------------------------

# Drives a practice controller's graph (test side) to the first Mount exit with the given label. The
# scripted Bottom never escapes, so the engine itself is asked to run a Bottom escape, reached the way
# the existing graph suite does it: zero-duration windows and a Top no-action reset keep the scenario's axis.
func _to_bottom(g: BjjPositionGraphMatch) -> bool:
    var top := g.open_window_for(0)
    if not top.ok() or not g.window_fields().open or g.window_fields().role != "top":
        return false
    if not g.submit(top.values.window_id, TOP_ID).ok():
        return false
    var bottom := g.open_window_for(0)
    return bottom.ok() and g.window_fields().role == "bottom"


func _halted_controller(label: String) -> BjjMountPracticeController:
    for axis: float in [0.2, 0.4, 0.8, 1.5, 3.0]:
        for stamina: int in [100, 60]:
            for action_id: String in ["mount.bottom.elbow_knee_escape", "mount.bottom.trap_and_roll_escape"]:
                for response_id: String in ["mount.top_response.post_and_base", "mount.top_response.wide_mount_base", "mount.top_response.hip_follow_repummel"]:
                    var c := BjjMountPracticeController.new()
                    c.start_new_match(alpha(), bravo(), {"axis": axis, "bottom_stamina": stamina})
                    var g := c._graph
                    if not _to_bottom(g):
                        continue
                    var tries: int = 0
                    while tries < 6 and g.status() == "active":
                        tries += 1
                        var legal := g.action_options(BOTTOM_ID).available_ids()
                        if legal.has(action_id):
                            g.submit(g.window_fields().window_id, BOTTOM_ID, action_id, response_id)
                            break
                        # Trap-and-Roll needs its setup: the engine's own Bridge builds it.
                        if action_id == "mount.bottom.trap_and_roll_escape" and legal.has("mount.bottom.bridge"):
                            if not g.submit(g.window_fields().window_id, BOTTOM_ID, "mount.bottom.bridge", response_id).ok() or g.status() != "active" or not _to_bottom(g):
                                break
                            continue
                        break
                    if g.status() == "halted_at_unsupported_transition" and g.blocked_transition().label == label:
                        return c
    return null


func _halted_graph(label: String) -> BjjPositionGraphMatch:
    var c := _halted_controller(label)
    return c._graph if c != null else null


func _test_blocked_transitions() -> void:
    for label: String in ["Half Guard", "Open Guard", "Reversal"]:
        var c := _halted_controller(label)
        check("a %s exit scenario exists" % label, c != null, true)
        if c == null:
            continue
        var g := c._graph
        var view := c.view()
        var blocked := g.blocked_transition()
        check(label + ": the UI state is blocked, not terminal", [view.status_kind, view.status], ["blocked", "halted_at_unsupported_transition"])
        check(label + ": the graph's exact blocked record is shown", view.blocked, blocked)
        check(label + ": reason", blocked.reason, "unresolved_destination" if label == "Reversal" else "destination_not_implemented")
        check(label + ": destination", blocked.destination_position_id, "" if label == "Reversal" else label.to_snake_case())
        check(label + ": banner names the label, the exact reason and says it is not a victory or defeat", [view.banner.contains(label), view.banner.contains(blocked.reason),
            view.banner.contains("not a victory or defeat")], [true, true, true])
        check(label + ": banner never claims a landing", view.banner.contains("destination unresolved (no landing)") if label == "Reversal" else
            view.banner.contains("declared destination %s is not implemented" % blocked.destination_position_id), true)
        check(label + ": banner has no arrow that could read as arrival", view.banner.contains("->"), false)
        check(label + ": not a terminal outcome", [view.terminal_reason, g.events().filter(func(e: Dictionary) -> bool: return e.kind == "terminal_outcome").size()], ["", 0])
        check(label + ": no winner, score or fake receiving position", [blocked.has("winner"), blocked.has("score"), blocked.has("position")], [false, false, false])
        check(label + ": commands are disabled with the graph's exact code", [view.commands.next_window, view.commands.submit],
            [{"enabled": false, "reason": HALTED}, {"enabled": false, "reason": HALTED}])
        check(label + ": no action rows are offered", [view.actions, view.responses], [[], []])
        check(label + ": starting a new match stays available", view.commands.new_match.enabled, true)
        var before := views(g)
        refused(label + ": Next Window after the halt", c, c.next_window(), HALTED)
        refused(label + ": Submit after the halt", c, c.submit_decision(), HALTED)
        refused(label + ": selecting a technique after the halt", c, c.select_action(CLIMB), HALTED)
        refused(label + ": selecting a response after the halt", c, c.select_response(FOREARM), HALTED)
        refused(label + ": selecting a commitment after the halt", c, c.select_commitment("HIGH"), HALTED)
        # Even bypassing the controller, the graph itself refuses.
        var open_again := g.open_window()
        check(label + ": the graph refuses open_window after the halt", [open_again.ok(), open_again.error], [false, HALTED])
        var open_for := g.open_window_for(0)
        check(label + ": the graph refuses open_window_for after the halt", [open_for.ok(), open_for.error], [false, HALTED])
        var submit_again := g.submit(g.window_fields().window_id, TOP_ID, CLIMB, FOREARM)
        check(label + ": the graph refuses submit after the halt", [submit_again.ok(), submit_again.error], [false, HALTED])
        check(label + ": nothing changed after every attempt", views(g), before)
        check(label + ": the exchange that exited stays accepted", g.events().slice(-2).map(func(e: Dictionary) -> String: return e.kind), ["decision_accepted", "transition_blocked"])
        # An explicit new match is independent; the halted one is not restarted invisibly.
        var halted := g
        check(label + ": a new practice match is explicit", c.start_new_match(alpha(), bravo()).ok, true)
        check(label + ": the new match is a different, active graph", [c._graph != halted, c.view().status_kind, c.view().events], [true, "active", []])
        check(label + ": the old graph is still halted", halted.status(), "halted_at_unsupported_transition")


# --- 9. terminal outcomes are not blocked transitions -----------------------------------

func _test_terminal_timeout_and_tap() -> void:
    var tap := started()
    play_to_end(tap, ["americana_submission_finish", "americana_arm_isolation", "high_mount_climb"], 0)
    var view := tap.view()
    check("tap: terminal, not blocked", [view.status_kind, view.status, view.terminal_reason], ["terminal", "ended", "tap"])
    check("tap: the engine recorded a tap", [tap._graph.state_fields().submission_tapped, tap._graph.blocked_transition()], [true, {}])
    check("tap: banner", view.banner, "TERMINAL OUTCOME: tap")
    check("tap: exactly one terminal event and no blocked event", [tap._graph.events().filter(func(e: Dictionary) -> bool: return e.kind == "terminal_outcome").size(),
        tap._graph.events().filter(func(e: Dictionary) -> bool: return e.kind == "transition_blocked").size()], [1, 0])
    check("tap: commands disabled with the match-ended reason", [view.commands.next_window, view.commands.submit],
        [{"enabled": false, "reason": "match_ended"}, {"enabled": false, "reason": "match_ended"}])
    var before := views(tap._graph)
    refused("tap: Next Window", tap, tap.next_window(), "match_ended")
    refused("tap: Submit", tap, tap.submit_decision(), "match_ended")
    refused("tap: selecting a technique", tap, tap.select_action(CLIMB), "match_ended")
    refused("tap: selecting a response", tap, tap.select_response(FOREARM), "match_ended")
    refused("tap: selecting a commitment", tap, tap.select_commitment("HIGH"), "match_ended")
    check("tap: refusals changed nothing", views(tap._graph), before)
    var direct := tap._graph.open_window()
    check("tap: the graph refuses further windows", direct.ok(), false)
    check("tap: the graph is unchanged by that attempt", views(tap._graph), before)

    var timeout := started()
    play_to_end(timeout, ["americana_submission_finish", "americana_arm_isolation", "high_mount_climb"], 1)
    var timeout_view := timeout.view()
    check("timeout (full 300 s match): terminal, not blocked", [timeout_view.status_kind, timeout_view.terminal_reason, timeout_view.blocked], ["terminal", "timeout", {}])
    check("timeout: the clock reached zero", [timeout_view.clock_seconds, timeout._graph.state_fields().submission_tapped], [0, false])
    check("timeout: banner", timeout_view.banner, "TERMINAL OUTCOME: timeout")
    check("the event log shows only the latest 40 events", [timeout_view.events.size(), timeout_view.events[0].begins_with("#80 "), timeout_view.events.back()],
        [40, true, "#119 terminal_outcome - timeout"])
    check("timeout: the last event is the terminal outcome", timeout._graph.events().back().kind, "terminal_outcome")
    var short := started({"clock": 10})
    play_to_end(short, ["crossface_pressure"], 0)
    check("a short practice match also ends by timeout", [short.view().status_kind, short.view().terminal_reason, short.view().clock_seconds], ["terminal", "timeout", 0])
    check("a finished match can be replaced explicitly", [short.start_new_match(alpha(), bravo()).ok, short.view().status_kind], [true, "active"])


# --- 10. a new practice match is independent ---------------------------------------------

func _test_new_match_independence() -> void:
    var c := started()
    play_window(c, ["high_mount_climb"], 0)
    play_window(c, ["high_mount_climb"], 0)
    var old_graph := c._graph
    var old_events := old_graph.events()
    var old_view := c.view()
    check("the first match progressed", [old_events.size() > 0, old_view.fighters[0].stamina_current < 100, old_view.window.window_id > 0], [true, true, true])
    c.select_action(CLIMB)
    var kept := c.start_new_match(alpha(), bravo())
    check("a new match starts", kept.ok, true)
    var fresh := c.view()
    check("a different graph object", c._graph != old_graph, true)
    check("the practice serial increments", [old_view.match_serial, fresh.match_serial], [1, 2])
    check("stamina is fresh", [fresh.fighters[0].stamina_current, fresh.fighters[1].stamina_current], [100, 100])
    check("the event log is empty", fresh.events, [])
    check("the window identity restarts", [fresh.window.window_id, fresh.window.open], [0, false])
    check("UI selections and the last decision are cleared", [c.selected_action, c.selected_response, c.selected_commitment, fresh.last_lines], ["", "", "", []])
    check("the clock is full", fresh.clock_seconds, 300)
    check("the old graph kept its own history untouched", old_graph.events(), old_events)
    check("the old match's decision cannot be replayed into the new one", c._graph.submit(old_view.window.window_id, TOP_ID, CLIMB, FOREARM).error, "no_open_window")
    # An invalid restart keeps the current match.
    var current := c._graph
    var serial := c.match_serial
    var bad := c.start_new_match(null, bravo())
    check("an invalid restart is refused", [bad.ok, bad.error], [false, "invalid_fighter_definition"])
    check("and keeps the current match and serial", [c._graph == current, c.match_serial], [true, serial])
    var duplicated := BjjMountPracticeController.new()
    check("a controller with no match reports it", [duplicated.has_match(), duplicated.view()], [false, {"has_match": false}])
    check("commands on a controller with no match are refused", [duplicated.next_window().error, duplicated.submit_decision().error], ["no_match", "no_match"])


# --- 11. source boundaries of the presentation layer -----------------------------------

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
    var shared: Array = ["_gateway", "._match", "open_window_for", "BjjMountMatch", "BjjStaminaPool", "BjjD3BController", "lifecycle_fields", "carryover",
        "_process", "_physics_process", "create_timer", "Timer", "get_ticks", "Time.get", "randi", "randf", "await", "OS."]
    check("the controller reaches only public graph, adapter and catalog APIs", offenders(controller_path, shared), [])
    check("the scene never touches the simulation", offenders(scene_path, shared + ["open_window", ".submit(", "BjjPositionGraphMatch", "BjjMatchWindowGateway",
        "state_fields", "roles()"]), [])
    check("the only commands the controller sends are open_window and submit", code_lines(controller_path).filter(func(l: String) -> bool:
        return l.contains("_graph.open_window") or l.contains("_graph.submit(")).size(), 3)
    check("open_window is the only window command", code_lines(controller_path).filter(func(l: String) -> bool: return l.contains("_graph.open_window(")).size(), 1)
    var scene_text := FileAccess.get_file_as_string("res://scenes/mount_practice.tscn")
    var node_types: Array = []
    var type_pattern := RegEx.create_from_string("^\\[node .*type=\"([A-Za-z0-9]+)\"")
    for line: String in scene_text.split("\n"):
        var found := type_pattern.search(line)
        if found != null and not node_types.has(found.get_string(1)):
            node_types.append(found.get_string(1))
    node_types.sort()
    check("the scene uses only 2D Control nodes and containers (no Timer, Animation, Tween or 3D nodes)", node_types, ["Button", "Control", "HBoxContainer", "ItemList",
        "Label", "MarginContainer", "OptionButton", "PanelContainer", "ProgressBar", "RichTextLabel", "ScrollContainer", "VBoxContainer"])
    check("the scene file's only external resource is the scene script", scene_text.count("[ext_resource"), 1)
    var scene_script: Script = load(scene_path)
    var scene_methods: Array = scene_script.get_script_method_list().map(func(m: Dictionary) -> String: return str(m.name))
    check("the scene script defines no per-frame simulation hooks", [scene_methods.has("_process"), scene_methods.has("_physics_process")], [false, false])
    check("the controller extends RefCounted (no Node, no scene tree)", code_lines(controller_path).filter(func(l: String) -> bool: return l.begins_with("extends ")), ["extends RefCounted"])
    check("the scene's own state is the controller handle only", code_lines(scene_path).filter(func(l: String) -> bool: return l.begins_with("var ")),
        ["var controller: BjjMountPracticeController = BjjMountPracticeController.new()"])


# --- 12. the scene ---------------------------------------------------------------------------

func label_text(scene: Node, node_name: String) -> String:
    return (scene.get_node("%" + node_name) as Label).text


func _test_scene() -> void:
    var packed: PackedScene = load("res://scenes/mount_practice.tscn")
    check("the scene loads", packed != null, true)
    var scene: Control = packed.instantiate()
    check("a scene is not ready until it enters the tree", scene.is_node_ready(), false)
    root.add_child(scene)
    await process_frame
    var c: BjjMountPracticeController = scene.controller
    var g := c._graph
    check("the scene starts a fresh valid match", [c.has_match(), c.match_serial, g.status(), g.window_fields().window_id], [true, 1, "active", 0])
    check("per-frame processing is off", [scene.is_processing(), scene.is_physics_processing()], [false, false])
    check("both fighters are shown with names from the F0 definitions", [label_text(scene, "FighterAName"), label_text(scene, "FighterBName")], ["Test Alpha", "Test Bravo"])
    check("roles are shown", [label_text(scene, "FighterARole"), label_text(scene, "FighterBRole")], ["Role: Top", "Role: Bottom"])
    check("stamina, band and behavior are shown before the first decision", [label_text(scene, "FighterAStaminaLabel"), label_text(scene, "FighterBStaminaLabel"),
        label_text(scene, "FighterABehavior"), label_text(scene, "FighterBBehavior")], ["Stamina 100 / 100 - Fresh", "Stamina 100 / 100 - Fresh", "Behavior: PRESSURE", "Behavior: ESCAPE"])
    check("the stamina bars follow the snapshots", [(scene.get_node("%FighterAStaminaBar") as ProgressBar).value, (scene.get_node("%FighterAStaminaBar") as ProgressBar).max_value], [100.0, 100.0])
    check("the clock is shown", label_text(scene, "ClockLabel"), "Clock 5:00 remaining (300 s of 300)")
    check("the control axis and band are shown", [label_text(scene, "AxisLabel"), label_text(scene, "BandLabel")], ["Axis 1.5 (positive = Top control)", "Band: STABLE"])
    check("the banner says the match is active", label_text(scene, "BannerLabel"), "Active Mount practice match")
    var next_button: Button = scene.get_node("%NextWindowButton")
    var submit_button: Button = scene.get_node("%SubmitButton")
    var techniques: ItemList = scene.get_node("%TechniqueList")
    var responses: ItemList = scene.get_node("%ResponseList")
    check("Next Window is enabled and Submit is disabled", [next_button.disabled, submit_button.disabled], [false, true])
    check("no technique rows before a window", [techniques.item_count, responses.item_count], [0, 0])
    check("the commitment control is disabled before a window", (scene.get_node("%CommitOption") as OptionButton).disabled, true)

    # Illegal input first: pressing Submit while disabled, selecting nothing.
    var before := views(g)
    scene._on_submit_pressed()
    check("a forced Submit with no window changed nothing", views(g), before)
    check("and says why", label_text(scene, "MessageLabel").contains("no_open_window"), true)

    next_button.pressed.emit()
    check("a window opened through the graph", [g.window_fields().open, g.window_fields().window_id, g.events().size()], [true, 1, 1])
    check("the window owner is shown", label_text(scene, "WindowLabel"), "Window #1: Test Alpha (Top) decides.")
    check("legal techniques are listed", techniques.item_count, 4)
    for index: int in techniques.item_count:
        var available: bool = not techniques.is_item_disabled(index)
        check("technique row %d: selectable exactly when disabled is false" % index, techniques.is_item_selectable(index), available)
        if not available:
            check("technique row %d shows the engine's exact reason" % index, techniques.get_item_text(index).contains("[unavailable: "), true)
    check("the engine's exact reason codes are shown", [techniques.get_item_text(2).contains("setup_not_ready"), techniques.get_item_text(3).contains("inactive_submission")], [true, true])
    check("the technique ids are available as tooltips", [techniques.get_item_tooltip(0), techniques.get_item_tooltip(2)], [CLIMB, ISOLATION])
    # Forced selection of a disabled row (as a script could) is still refused by the controller.
    techniques.item_selected.emit(2)
    check("forcing an unavailable technique selects nothing", [c.selected_action, submit_button.disabled, responses.item_count], ["", true, 0])
    techniques.item_selected.emit(3)
    check("forcing the inactive finish selects nothing", c.selected_action, "")
    techniques.item_selected.emit(0)
    check("a legal technique is selected through the list", [c.selected_action, responses.item_count, submit_button.disabled], [CLIMB, 3, true])
    check("the selected technique row is highlighted", techniques.is_selected(0), true)
    check("list type-ahead is off so hotkeys are not swallowed", [techniques.allow_search, responses.allow_search], [false, false])
    check("every response row is enabled exactly when the engine says so", [responses.is_item_disabled(0), responses.is_item_disabled(1), responses.is_item_disabled(2)], [false, false, false])
    responses.item_selected.emit(0)
    check("a legal response enables Submit", [c.selected_response, submit_button.disabled], [FOREARM, false])
    check("the selected response row is highlighted", responses.is_selected(0), true)
    check("the commitment control is enabled for the Top fighter", (scene.get_node("%CommitOption") as OptionButton).disabled, false)

    # The scene's result equals a reference graph driven separately.
    var ref := reference()
    ref.open_window()
    var ref_report := ref.submit(1, TOP_ID, CLIMB, FOREARM)
    submit_button.pressed.emit()
    check("the decision went through the graph and equals the reference report", c.last_report(), ref_report.fields())
    check("the graph state equals the reference", views(g), views(ref))
    var ref_state := ref.state_fields()
    check("stamina is rendered from the authoritative state", [label_text(scene, "FighterAStaminaLabel"), label_text(scene, "FighterBStaminaLabel")],
        ["Stamina %d / %d - %s" % [ref_state.top_stamina, ref_state.top_maximum, ref_state.top_band], "Stamina %d / %d - %s" % [ref_state.bottom_stamina, ref_state.bottom_maximum, ref_state.bottom_band]])
    check("the result panel shows the resolution", Array(label_text(scene, "ResultLabel").split("\n").slice(0, 3)), ["Test Alpha (Top): High Mount Climb vs Forearm Frame",
        "Grade: Success (raw 1, final 1)", "Axis 2.0 -> 3.0; band STABLE -> STRONG"])
    check("the message says the decision was accepted", label_text(scene, "MessageLabel").begins_with("Decision accepted."), true)
    check("the event log lists the graph's events", (scene.get_node("%EventLog") as RichTextLabel).text, "\n".join(c.view().events))
    check("selections were cleared by the accepted decision", [techniques.item_count, c.selected_action, submit_button.disabled, next_button.disabled], [0, "", true, false])

    # Hotkeys call the same handlers; N opens the Bottom's scripted window.
    var key := InputEventKey.new()
    key.keycode = KEY_N
    key.pressed = true
    scene._unhandled_key_input(key)
    check("the N hotkey opened the next window through the graph", [g.window_fields().open, g.window_fields().role], [true, "bottom"])
    check("the scripted Bottom window is labelled", label_text(scene, "WindowLabel").contains("SCRIPTED practice behavior"), true)
    check("the response header says no response is chosen in a scripted window", label_text(scene, "ResponseHeader"), "No response choice in a scripted Bottom window")
    check("the technique header says the rows are informational", label_text(scene, "TechniqueHeader"), "Test Bravo's legal techniques (informational only)")
    check("all the Bottom's rows are disabled", range(techniques.item_count).map(func(i: int) -> bool: return techniques.is_item_disabled(i)).all(func(d: bool) -> bool: return d), true)
    check("the commitment control is disabled for the Bottom", (scene.get_node("%CommitOption") as OptionButton).disabled, true)
    techniques.item_selected.emit(0)
    check("forcing a Bottom technique selects nothing", c.selected_action, "")
    check("Submit is enabled for the scripted decision", submit_button.disabled, false)
    key = InputEventKey.new()
    key.keycode = KEY_S
    key.pressed = true
    scene._unhandled_key_input(key)
    ref.open_window()
    var ref_bottom := ref.submit(2, BOTTOM_ID)
    check("the S hotkey submitted the scripted decision, equal to the reference", c.last_report(), ref_bottom.fields())
    check("the scripted decision is labelled in the result", label_text(scene, "ResultLabel").contains("SCRIPTED practice behavior"), true)

    # Repeated refreshes are pure reads.
    var settled := views(g)
    for i: int in 30:
        scene.refresh()
    check("30 scene refreshes changed nothing", views(g), settled)

    # A new explicit match: independent state, not an invisible restart.
    var old_graph := g
    (scene.get_node("%NewMatchButton") as Button).pressed.emit()
    check("a new practice match replaced the controller's graph", [c._graph != old_graph, c.match_serial], [true, 2])
    check("fresh stamina, events and window", [label_text(scene, "FighterAStaminaLabel"), (scene.get_node("%EventLog") as RichTextLabel).text, c._graph.window_fields().window_id],
        ["Stamina 100 / 100 - Fresh", "", 0])
    check("the message says it is a new independent match", label_text(scene, "MessageLabel").begins_with("New independent practice match started."), true)
    check("the old match is untouched", old_graph.events().size() > 0, true)

    # The commitment widget reaches the controller and the graph (compared with a reference).
    next_button.pressed.emit()
    check("a new Top window is open", [c.view().window.role, c._graph.window_fields().window_id], ["top", 1])
    techniques.item_selected.emit(0)
    responses.item_selected.emit(0)
    var commit: OptionButton = scene.get_node("%CommitOption")
    commit.item_selected.emit(2)
    check("the commitment widget selected HIGH", [c.selected_commitment, c.view().commitment.selected], ["HIGH", "HIGH"])
    var ref_high := reference()
    ref_high.open_window()
    var ref_high_report := ref_high.submit(1, TOP_ID, CLIMB, FOREARM, "HIGH")
    submit_button.pressed.emit()
    check("the decision with the widget's commitment equals the reference", c.last_report(), ref_high_report.fields())
    check("the graph state equals the reference after it", views(c._graph), views(ref_high))
    # Hotkey guards: key releases, echoes and other keys do nothing.
    var idle := views(c._graph)
    for guard: Array in [[KEY_N, false, false], [KEY_N, true, true], [KEY_S, false, false], [KEY_S, true, true], [KEY_X, true, false], [KEY_SPACE, true, false]]:
        var guard_key := InputEventKey.new()
        guard_key.keycode = guard[0]
        guard_key.pressed = guard[1]
        guard_key.echo = guard[2]
        scene._unhandled_key_input(guard_key)
    check("releases, echoes and unrelated keys changed nothing", views(c._graph), idle)
    var disabled_key := InputEventKey.new()
    disabled_key.keycode = KEY_S
    disabled_key.pressed = true
    scene._unhandled_key_input(disabled_key)
    check("S with Submit disabled changed nothing", views(c._graph), idle)

    # A blocked transition is rendered as such, with every command disabled.
    var halted := _halted_controller("Half Guard")
    check("a halting scenario exists for the scene", halted != null, true)
    scene.controller = halted
    c = halted
    scene.refresh()
    check("the banner shows a blocked transition", label_text(scene, "BannerLabel"),
        "BLOCKED POSITION TRANSITION (not a victory or defeat): exit 'Half Guard'; declared destination half_guard is not implemented [destination_not_implemented]. Mount play stops here.")
    check("both commands are disabled", [next_button.disabled, submit_button.disabled], [true, true])
    check("the window label says the match is not active", label_text(scene, "WindowLabel"), "No window: the match is not active.")
    var blocked_before := views(c._graph)
    scene._on_next_pressed()
    scene._on_submit_pressed()
    check("forced button handlers cannot bypass the graph", views(c._graph), blocked_before)
    check("the refusal is explained with the graph's code", label_text(scene, "MessageLabel").contains(HALTED), true)
    check("starting a new match remains possible", (scene.get_node("%NewMatchButton") as Button).disabled, false)
    # A terminal outcome is rendered differently from a blocked one.
    var finished := started({"clock": 10})
    play_to_end(finished, ["crossface_pressure"], 0)
    scene.controller = finished
    scene.refresh()
    check("the banner shows a terminal outcome, not a blocked transition", [label_text(scene, "BannerLabel"), label_text(scene, "BannerLabel").contains("BLOCKED")], ["TERMINAL OUTCOME: timeout", false])
    check("commands are disabled at the end", [next_button.disabled, submit_button.disabled], [true, true])
    root.remove_child(scene)
    scene.free()
    await process_frame
