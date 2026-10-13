extends SceneTree

# Negative-first tests for F1.2, the Top RESPONDER's commitment in two-sided Mount practice. They live in their own file
# so the F1 (1036) and F1.1 (491) suites stay byte-for-byte unchanged and keep proving that scripted practice, the Top's own
# commitment and manual Bottom decisions behave as before.
#
# Everything simulated goes through BjjPositionGraphMatch. A separately driven REFERENCE graph that receives the same window
# ids, fighter ids and arguments (including the sixth `response_commitment` argument) is the oracle. Test-side private
# access (controller._graph, graph._gateway) is used only as that oracle or to read engine state; the production
# presentation code never does it.
const TOP_ID: String = "fighter_alpha"
const BOTTOM_ID: String = "fighter_bravo"
const ALPHA_RES: String = "res://tests/resources/fighter_test_alpha.tres"
const BRAVO_RES: String = "res://tests/resources/fighter_test_bravo.tres"
const CLIMB: String = "mount.top.high_mount_climb"
const FOREARM: String = "mount.bottom_response.forearm_frame"
const TIGHT: String = "mount.bottom_response.tight_elbow_arm_defense"
const BRIDGE: String = "mount.bottom.bridge"
const ELBOW: String = "mount.bottom.elbow_knee_escape"
const POST: String = "mount.top_response.post_and_base"
const WIDE: String = "mount.top_response.wide_mount_base"
const HIP: String = "mount.top_response.hip_follow_repummel"
const NO_ACTION: String = "practice.bottom_no_action"
const HALTED: String = "halted_unsupported_transition"
const LABELS: Array = ["Engine default (MEDIUM)", "LOW", "MEDIUM", "HIGH"]

var checks: int = 0
var failures: int = 0


func check(label: String, actual: Variant, expected: Variant) -> void:
    checks += 1
    if typeof(actual) != typeof(expected) or JSON.stringify(actual, "", true, true) != JSON.stringify(expected, "", true, true):
        failures += 1
        if failures <= 25:
            push_error("%s: got %s expected %s" % [label, actual, expected])


func _initialize() -> void:
    _test_defaults_and_applicability()
    _test_invalid_values_and_no_action()
    _test_stale_selections_are_cleared()
    _test_explicit_choices_equal_the_graph_pathway()
    _test_engine_default_is_the_documented_default()
    _test_no_action_and_forced_values_are_never_forwarded()
    _test_a_recovery_hold_reports_no_response_commitment()
    _test_an_underfunded_top_is_reported_honestly()
    _test_blocked_and_terminal_states()
    _test_refreshes_are_inert()
    _test_source_boundaries()
    await _test_scene()
    # Same completion contract as the other suites: one PASS line with the exact count, validated together with the
    # exit status and the whole log by tools/ci/validate_mount_slice_log.py.
    if failures > 0:
        push_error("Mount practice response commitment: %d / %d assertions failed" % [failures, checks])
        quit(1)
        return
    print("Mount practice response commitment PASS: %d assertions" % checks)
    quit(0)


# --- helpers ---------------------------------------------------------------------------

func alpha() -> BjjFighterDefinition:
    return load(ALPHA_RES)


func bravo() -> BjjFighterDefinition:
    return load(BRAVO_RES)


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


# Plays the Top window through the controller (first admitted technique and response) and mirrors it on the reference.
func top_decision(c: BjjMountPracticeController, ref: BjjPositionGraphMatch) -> void:
    check("a Top window opens", c.next_window().ok, true)
    ref.open_window()
    var action: String = available_ids(c, "actions")[0]
    check("a Top technique is selected", c.select_action(action).ok, true)
    var response: String = available_ids(c, "responses")[0]
    check("a response is selected", c.select_response(response).ok, true)
    var window_id: int = ref.window_fields().window_id
    check("the Top decision is accepted", c.submit_decision().ok, true)
    check("the reference accepts the same Top decision", ref.submit(window_id, TOP_ID, action, response).ok(), true)


# A two-sided controller and a reference graph, both with the Bottom's window (window 2) open.
func at_bottom_window(extra: Dictionary = {}) -> Array:
    var c := started("two_sided", extra)
    var ref := reference(extra)
    top_decision(c, ref)
    check("the Bottom window opens", c.next_window().ok, true)
    ref.open_window()
    check("it is window 2 owned by the Bottom", [c.view().window.window_id, c.view().window.role, ref.window_fields().window_id], [2, "bottom", 2])
    return [c, ref]


# --- 1. defaults and where the control applies ---------------------------------------------

func _test_defaults_and_applicability() -> void:
    var none := BjjMountPracticeController.new()
    check("a new controller has the engine default selected", none.selected_response_commitment, "")
    refused("no match yet", none.select_response_commitment("HIGH"), "no_match")

    var c := started("two_sided")
    var idle: Dictionary = c.view().commitment.responder
    check("with no window the responder control is inactive and offers the engine default plus the three commitments", idle,
        {"active": false, "state": "inactive", "selectable": false, "values": ["", "LOW", "MEDIUM", "HIGH"], "labels": LABELS, "selected": ""})
    refused("no window is open", c.select_response_commitment("HIGH"), "response_commitment_not_applicable")
    c.next_window()
    check("a Top window does not host the responder control", c.view().commitment.responder.active, false)
    refused("a Top window (the Top's own commitment is a different control)", c.select_response_commitment("HIGH"), "response_commitment_not_applicable")
    check("the Top's own commitment is still selectable there", [c.view().commitment.selectable, c.select_commitment("HIGH").ok, c.selected_commitment], [true, true, "HIGH"])
    check("and the two selections are independent", c.selected_response_commitment, "")

    var pair := at_bottom_window()
    var b: BjjMountPracticeController = pair[0]
    var g := b._graph
    var before := views(g)
    check("a two-sided Bottom window hosts the control, waiting for a technique", [b.view().commitment.responder.active, b.view().commitment.responder.state, b.view().commitment.responder.selectable],
        [true, "waiting", false])
    check("the Bottom's own commitment is never selectable", [b.view().commitment.selectable, b.view().commitment.policy_selected], [false, g.selected_commitment()])
    refused("before any technique", b.select_response_commitment("HIGH"), "technique_required")
    b.select_action(BRIDGE)
    refused("a technique but no response", b.select_response_commitment("HIGH"), "response_required")
    check("still waiting", [b.view().commitment.responder.state, b.view().commitment.responder.selectable], ["waiting", false])
    b.select_response(POST)
    check("technique and response chosen: the control is ready", [b.view().commitment.responder.state, b.view().commitment.responder.selectable], ["ready", true])
    check("the refusals changed nothing in the engine", views(g), before)
    check("and selected nothing", b.selected_response_commitment, "")

    var scripted := started("scripted")
    top_decision(scripted, reference())
    scripted.next_window()
    var sg := scripted._graph
    var sbefore := views(sg)
    check("a scripted Bottom window does not host the control", scripted.view().commitment.responder.active, false)
    refused("scripted Bottom window", scripted.select_response_commitment("HIGH"), "response_commitment_not_applicable")
    check("nothing changed", [views(sg), scripted.selected_response_commitment], [sbefore, ""])


# --- 2. invalid values and No action -------------------------------------------------------------

func _test_invalid_values_and_no_action() -> void:
    var pair := at_bottom_window()
    var c: BjjMountPracticeController = pair[0]
    var g := c._graph
    c.select_action(BRIDGE)
    c.select_response(POST)
    var before := views(g)
    for bad: String in ["EXTREME", "low", "Medium", " ", "HIGH ", "0", "default"]:
        refused("the invalid commitment '%s'" % bad, c.select_response_commitment(bad), "unknown_commitment")
    check("invalid names selected nothing and changed nothing", [c.selected_response_commitment, views(g)], ["", before])
    check("HIGH is accepted", [c.select_response_commitment("HIGH").ok, c.selected_response_commitment], [true, "HIGH"])
    refused("a bad name does not disturb the earlier valid choice", c.select_response_commitment("EXTREME"), "unknown_commitment")
    check("the earlier valid choice is kept", c.selected_response_commitment, "HIGH")
    check("the engine default can be chosen again explicitly", [c.select_response_commitment("").ok, c.selected_response_commitment], [true, ""])

    check("No action is chosen", c.select_action(NO_ACTION).ok, true)
    check("the control reports that No action has no response commitment", [c.view().commitment.responder.state, c.view().commitment.responder.selectable, c.view().commitment.responder.selected],
        ["no_action", false, ""])
    refused("a commitment for No action", c.select_response_commitment("HIGH"), "no_response_for_no_action")
    refused("even the engine default value for No action", c.select_response_commitment(""), "no_response_for_no_action")
    check("No action carries no responder commitment", [c.selected_response_commitment, c.selected_response], ["", ""])


# --- 3. stale selections never leak ---------------------------------------------------------------

func _test_stale_selections_are_cleared() -> void:
    var pair := at_bottom_window()
    var c: BjjMountPracticeController = pair[0]
    var ref: BjjPositionGraphMatch = pair[1]
    c.select_action(BRIDGE)
    c.select_response(POST)
    c.select_response_commitment("HIGH")
    check("a choice is held", c.selected_response_commitment, "HIGH")
    c.select_action(ELBOW)
    check("a different technique clears it", [c.selected_response_commitment, c.selected_response], ["", ""])
    c.select_response(POST)
    c.select_response_commitment("LOW")
    c.select_response(WIDE)
    check("a different response clears it", [c.selected_response_commitment, c.selected_response], ["", WIDE])
    c.select_response_commitment("HIGH")
    c.select_action(NO_ACTION)
    check("choosing No action clears it", [c.selected_response_commitment, c.selected_action], ["", NO_ACTION])
    c.select_action(BRIDGE)
    c.select_response(POST)
    check("returning to a technique does not bring it back", c.selected_response_commitment, "")
    refused("a refused technique does not touch the choice", c.select_action("mount.bottom.unknown"), "unknown_action")

    # An accepted decision clears it, and the next Bottom window starts from the engine default.
    c.select_response_commitment("HIGH")
    var ref_first := ref.submit(2, BOTTOM_ID, BRIDGE, POST, "", "HIGH")
    check("the decision with HIGH is accepted and equals the reference", [c.submit_decision().ok, c.last_report()], [true, ref_first.fields()])
    check("the choice does not survive the decision", c.selected_response_commitment, "")
    top_decision(c, ref)
    check("the next Bottom window opens", [c.next_window().ok, c.view().window.window_id], [true, 4])
    ref.open_window()
    check("it starts at the engine default", [c.selected_response_commitment, c.view().commitment.responder.selected], ["", ""])
    c.select_action(ELBOW)
    c.select_response(WIDE)
    var ref_second := ref.submit(4, BOTTOM_ID, ELBOW, WIDE)
    check("a decision made without choosing equals the reference with no commitment: no leak from the earlier HIGH", [c.submit_decision().ok, c.last_report(), views(c._graph)], [true, ref_second.fields(), views(ref)])

    # Mode switches and new matches clear it.
    var d := at_bottom_window()[0] as BjjMountPracticeController
    d.select_action(BRIDGE)
    d.select_response(POST)
    d.select_response_commitment("HIGH")
    check("the mode switch succeeds", d.set_practice_mode("scripted").ok, true)
    check("a mode switch clears it", d.selected_response_commitment, "")
    check("and leaves the control inactive", d.view().commitment.responder.active, false)
    var e := at_bottom_window()[0] as BjjMountPracticeController
    e.select_action(BRIDGE)
    e.select_response(POST)
    e.select_response_commitment("LOW")
    check("a new match succeeds", e.start_new_match(alpha(), bravo()).ok, true)
    check("a new match clears it", [e.selected_response_commitment, e.selected_action, e.selected_response], ["", "", ""])
    # Opening a window also clears it, so a value written between windows (as a script could) cannot ride into the next decision.
    var f := at_bottom_window()[0] as BjjMountPracticeController
    f.select_action(BRIDGE)
    f.select_response(POST)
    check("the first decision is accepted", f.submit_decision().ok, true)
    f.selected_response_commitment = "LOW"
    check("a stray value written between windows is held until the next window", f.selected_response_commitment, "LOW")
    check("the next window opens", f.next_window().ok, true)
    check("opening it cleared the stray value", f.selected_response_commitment, "")


# --- 4. explicit choices equal the existing graph pathway ----------------------------------------------

func _test_explicit_choices_equal_the_graph_pathway() -> void:
    var top_stamina := {}
    for response_commitment: String in ["", "LOW", "MEDIUM", "HIGH"]:
        var label := "'%s'" % response_commitment if not response_commitment.is_empty() else "default"
        var pair := at_bottom_window()
        var c: BjjMountPracticeController = pair[0]
        var ref: BjjPositionGraphMatch = pair[1]
        c.select_action(BRIDGE)
        c.select_response(POST)
        check(label + ": the commitment is selected", c.select_response_commitment(response_commitment).ok, true)
        var expected := ref.submit(2, BOTTOM_ID, BRIDGE, POST, "", response_commitment)
        check(label + ": the decision is accepted", c.submit_decision(), {"ok": true, "error": ""})
        check(label + ": the report equals the direct graph call with the sixth argument", c.last_report(), expected.fields())
        check(label + ": the whole engine state equals the reference", views(c._graph), views(ref))
        var settlement: Dictionary = c.last_report().detail.settlement
        var expected_label: String = "MEDIUM" if response_commitment.is_empty() else response_commitment
        check(label + ": the engine used the expected responder commitment", [settlement.response_requested_commitment, settlement.response_effective_commitment], [expected_label, expected_label])
        check(label + ": the Bottom's own commitment was not supplied", c.last_report().detail.decision.requested_commitment, null)
        top_stamina[response_commitment] = c._graph.state_fields().top_stamina
    check("the responder commitment really reached the engine: a harder response costs the Top more stamina", [top_stamina["LOW"] > top_stamina["MEDIUM"], top_stamina["MEDIUM"] > top_stamina["HIGH"]], [true, true])
    check("the literal stamina values of this scripted window", [top_stamina["LOW"], top_stamina["MEDIUM"], top_stamina["HIGH"]], [88, 84, 79])
    for combo: Array in [[ELBOW, WIDE, "HIGH"], [ELBOW, HIP, "LOW"], [BRIDGE, HIP, "MEDIUM"]]:
        var pair := at_bottom_window()
        var c: BjjMountPracticeController = pair[0]
        var ref: BjjPositionGraphMatch = pair[1]
        c.select_action(combo[0])
        c.select_response(combo[1])
        c.select_response_commitment(combo[2])
        var expected := ref.submit(2, BOTTOM_ID, combo[0], combo[1], "", combo[2])
        check("%s / %s / %s: accepted and equal to the reference" % [combo[0].get_slice(".", 2), combo[1].get_slice(".", 2), combo[2]], [c.submit_decision().ok, c.last_report(), views(c._graph)],
            [true, expected.fields(), views(ref)])
    # The result text states what the engine used.
    var shown := at_bottom_window()[0] as BjjMountPracticeController
    shown.select_action(BRIDGE)
    shown.select_response(POST)
    shown.select_response_commitment("HIGH")
    shown.submit_decision()
    check("the result text names the chosen responder commitment", shown.view().last_lines.has("Top's response commitment: HIGH (chosen)"), true)


# --- 5. what "engine default" means ---------------------------------------------------------------

func _test_engine_default_is_the_documented_default() -> void:
    var default_pair := at_bottom_window()
    var medium_pair := at_bottom_window()
    for pair: Array in [default_pair, medium_pair]:
        pair[0].select_action(BRIDGE)
        pair[0].select_response(POST)
    medium_pair[0].select_response_commitment("MEDIUM")
    default_pair[0].submit_decision()
    medium_pair[0].submit_decision()
    check("the engine default and an explicit MEDIUM settle identically under the practice rules (reports)", default_pair[0].last_report(), medium_pair[0].last_report())
    check("and leave identical engine states", views(default_pair[0]._graph), views(medium_pair[0]._graph))
    check("the controller still forwards exactly what was selected: the default sends nothing and MEDIUM sends MEDIUM",
        [default_pair[0].view().last_lines.has("Top's response commitment: MEDIUM (engine default)"), medium_pair[0].view().last_lines.has("Top's response commitment: MEDIUM (chosen)")], [true, true])
    # The same on the direct pathway, so the equivalence is the engine's, not the controller's.
    var direct_default := reference()
    var direct_medium := reference()
    for g: BjjPositionGraphMatch in [direct_default, direct_medium]:
        g.open_window()
        g.submit(1, TOP_ID, CLIMB, FOREARM)
        g.open_window()
    var a := direct_default.submit(2, BOTTOM_ID, BRIDGE, POST, "", "")
    var b := direct_medium.submit(2, BOTTOM_ID, BRIDGE, POST, "", "MEDIUM")
    check("directly on the graph: an omitted responder commitment equals MEDIUM", [a.fields(), views(direct_default)], [b.fields(), views(direct_medium)])


# --- 6. forced values are never forwarded ---------------------------------------------------------------

func _test_no_action_and_forced_values_are_never_forwarded() -> void:
    # Values written straight into the controller field, as a script could, must not reach the engine except in the one legal place.
    var pair := at_bottom_window()
    var c: BjjMountPracticeController = pair[0]
    var ref: BjjPositionGraphMatch = pair[1]
    c.select_action(NO_ACTION)
    c.selected_response_commitment = "HIGH"
    var expected := ref.submit(2, BOTTOM_ID)
    check("No action with a forced responder commitment sends none and equals the plain no-action decision", [c.submit_decision().ok, c.last_report(), views(c._graph)], [true, expected.fields(), views(ref)])

    var top := started("two_sided")
    var top_ref := reference()
    top.next_window()
    top_ref.open_window()
    top.select_action(CLIMB)
    top.select_response(FOREARM)
    top.selected_response_commitment = "HIGH"
    var top_expected := top_ref.submit(1, TOP_ID, CLIMB, FOREARM)
    check("a Top window ignores a forced responder commitment", [top.submit_decision().ok, top.last_report(), views(top._graph)], [true, top_expected.fields(), views(top_ref)])

    var scripted := started("scripted")
    var scripted_ref := reference()
    top_decision(scripted, scripted_ref)
    scripted.next_window()
    scripted_ref.open_window()
    scripted.selected_response_commitment = "HIGH"
    var scripted_expected := scripted_ref.submit(2, BOTTOM_ID)
    check("a scripted Bottom window ignores a forced responder commitment", [scripted.submit_decision().ok, scripted.last_report(), views(scripted._graph)], [true, scripted_expected.fields(), views(scripted_ref)])

    # A forced invalid value reaches the engine, which refuses it; the controller reports the engine's code and changes nothing.
    var bad := at_bottom_window()[0] as BjjMountPracticeController
    bad.select_action(BRIDGE)
    bad.select_response(POST)
    bad.selected_response_commitment = "BOGUS"
    var before := views(bad._graph)
    refused("the engine refuses an invalid responder commitment and the controller passes its code through", bad.submit_decision(), "invalid_response_commitment")
    check("the engine is unchanged and the selections are kept", [views(bad._graph), bad.selected_action, bad.selected_response, bad.selected_response_commitment], [before, BRIDGE, POST, "BOGUS"])


# --- 7. a recovery hold ----------------------------------------------------------------------------

func hold_pair() -> Array:
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
                    if c._graph.controller_fields().recovery_hold_mode:
                        return [c, ref]
                    c.select_action(NO_ACTION)
                    c.submit_decision()
                    ref.submit(window.window_id, BOTTOM_ID)
    return []


func _test_a_recovery_hold_reports_no_response_commitment() -> void:
    var pair := hold_pair()
    check("a recovery-hold Bottom window exists", pair.size(), 2)
    if pair.size() != 2:
        return
    var c: BjjMountPracticeController = pair[0]
    var ref: BjjPositionGraphMatch = pair[1]
    var window_id: int = c.view().window.window_id
    c.select_action(BRIDGE)
    c.select_response(POST)
    check("the responder control is ready in the hold window", c.view().commitment.responder.state, "ready")
    c.select_response_commitment("HIGH")
    var expected := ref.submit(window_id, BOTTOM_ID, BRIDGE, POST, "", "HIGH")
    check("the decision equals the reference", [c.submit_decision().ok, c.last_report(), views(c._graph)], [true, expected.fields(), views(ref)])
    check("the engine ran a recovery hold, so no responder commitment was settled", [c.last_report().detail.decision.kind, c.last_report().detail.settlement.has("response_requested_commitment")], ["LOCKOUT_HOLD", false])
    check("the text claims no settled responder commitment and says the choice was not used", [c.view().last_lines.any(func(l: String) -> bool: return l.begins_with("Top's response commitment")),
        c.view().last_lines.has("Your Top response commitment choice (HIGH) was not used.")], [false, true])


# --- 7b. the Top cannot always afford what it chose ----------------------------------------------------------

# The engine funds what the Top can afford; the effective commitment can be lower than the requested one, or empty (UNFUNDED).
func _test_an_underfunded_top_is_reported_honestly() -> void:
    var seen := {}
    for top_stamina: int in [0, 12, 16, 25]:  # unfunded, only LOW affordable, only MEDIUM affordable, fully funded (measured)
        for response_commitment: String in ["HIGH", ""]:
            var extra := {"top_stamina": top_stamina}
            var pair := at_bottom_window(extra)
            var c: BjjMountPracticeController = pair[0]
            var ref: BjjPositionGraphMatch = pair[1]
            c.select_action(BRIDGE)
            c.select_response(POST)
            c.select_response_commitment(response_commitment)
            var expected := ref.submit(2, BOTTOM_ID, BRIDGE, POST, "", response_commitment)
            if not c.submit_decision().ok:
                continue
            check("top_stamina %d / '%s': equals the reference" % [top_stamina, response_commitment], [c.last_report(), views(c._graph)], [expected.fields(), views(ref)])
            var settlement: Dictionary = c.last_report().detail.settlement
            if not settlement.has("response_requested_commitment"):
                continue
            var line: String = c.view().last_lines.filter(func(l: String) -> bool: return l.begins_with("Top's response commitment"))[0]
            var kind := "same" if settlement.response_effective_commitment == settlement.response_requested_commitment else ("unfunded" if settlement.response_effective_commitment.is_empty() else "lower")
            if not seen.has(kind):
                seen[kind] = line
            check("top_stamina %d / '%s': the text never shows an empty effective value" % [top_stamina, response_commitment], line.contains("effective )"), false)
    check("a case where the Top could not afford any response commitment exists", seen.has("unfunded"), true)
    if seen.has("unfunded"):
        check("and the text says UNFUNDED instead of repeating the request", seen["unfunded"].contains("could not afford any commitment, so the response was UNFUNDED"), true)
    check("a case where the Top could only afford a lower commitment exists", seen.has("lower"), true)
    if seen.has("lower"):
        check("and the text says what was affordable", seen["lower"].contains("the Top could only afford "), true)
    check("the ordinary case keeps the short text (the engine default, affordable at 16)", seen.get("same", ""), "Top's response commitment: MEDIUM (engine default)")
    check("the unfunded text, literally", seen.get("unfunded", ""), "Top's response commitment: HIGH (chosen; the Top could not afford any commitment, so the response was UNFUNDED)")
    check("the lower-commitment text, literally", seen.get("lower", ""), "Top's response commitment: HIGH (chosen; the Top could only afford LOW)")


# --- 8. blocked and terminal states ----------------------------------------------------------------------

func _test_blocked_and_terminal_states() -> void:
    # The documented two-window route to a blocked Half Guard exit, with the Top responding at LOW.
    var c := started("two_sided")
    var ref := reference()
    check("a Top window opens", [c.next_window().ok, ref.open_window().ok()], [true, true])
    c.select_action(CLIMB)
    c.select_response(TIGHT)
    check("the Top decision is accepted", [c.submit_decision().ok, ref.submit(1, TOP_ID, CLIMB, TIGHT).ok()], [true, true])
    c.next_window()
    ref.open_window()
    c.select_action(ELBOW)
    c.select_response(POST)
    check("LOW is selected for the responder", c.select_response_commitment("LOW").ok, true)
    var expected := ref.submit(2, BOTTOM_ID, ELBOW, POST, "", "LOW")
    check("the escape decision is accepted and equals the reference", [c.submit_decision().ok, c.last_report(), views(c._graph)], [true, expected.fields(), views(ref)])
    check("the engine halted at an unsupported exit, shown as blocked, not terminal", [c.view().status_kind, c.view().banner.contains("BLOCKED POSITION TRANSITION"), c.view().terminal_reason],
        ["blocked", true, ""])
    check("the responder control is inactive and every selection is refused with the graph's code", [c.view().commitment.responder.active, c.select_response_commitment("HIGH"), c.selected_response_commitment],
        [false, {"ok": false, "error": HALTED}, ""])

    # A timeout.
    var t := started("two_sided", {"clock": 10})
    for step: int in 200:
        if t.view().status_kind != "active":
            break
        t.next_window()
        var window: Dictionary = t.view().window
        if not window.open:
            break
        if window.role == "top":
            t.select_action(available_ids(t, "actions")[0])
            t.select_response(available_ids(t, "responses")[0])
        else:
            t.select_action(NO_ACTION)
        t.submit_decision()
    check("a two-sided match reaches a terminal outcome", [t.view().status_kind, t.view().terminal_reason], ["terminal", "timeout"])
    refused("a responder commitment after the match ended", t.select_response_commitment("HIGH"), "match_ended")
    check("nothing is selected", t.selected_response_commitment, "")


# --- 9. refreshes are inert -------------------------------------------------------------------------------

func _test_refreshes_are_inert() -> void:
    var pair := at_bottom_window()
    var c: BjjMountPracticeController = pair[0]
    c.select_action(BRIDGE)
    c.select_response(POST)
    c.select_response_commitment("HIGH")
    var before := views(c._graph)
    var model := c.view()
    for i: int in 50:
        c.view()
    check("50 reads of a ready responder control changed nothing", [views(c._graph), c.view()], [before, model])
    check("and the choice survived them", [c.selected_response_commitment, c.view().commitment.responder.selected], ["HIGH", "HIGH"])


# --- 10. source boundaries ------------------------------------------------------------------------------------

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
    check("the controller still sends only open_window and submit (three command lines)", code_lines(controller_path).filter(func(l: String) -> bool:
        return l.contains("_graph.open_window") or l.contains("_graph.submit(")).size(), 3)
    check("the responder commitment travels only in the existing submit call", code_lines(controller_path).filter(func(l: String) -> bool:
        return l.contains("_graph.submit(") and l.contains("responder_commitment")).size(), 1)
    check("the controller still avoids the low-level contract, match and D3-B", offenders(controller_path, ["bottom_decision", ".attempt(", "MountContract", "_contract", "reset_window", "recovery_hold", "d3b"]), [])
    check("the scene reaches the simulation through the controller only", offenders(scene_path, ["_graph", "open_window", ".submit(", "BjjPositionGraphMatch", "state_fields"]), [])
    check("the scene's own state is still the controller handle only", code_lines(scene_path).filter(func(l: String) -> bool: return l.begins_with("var ")),
        ["var controller: BjjMountPracticeController = BjjMountPracticeController.new()"])
    var scene_text := FileAccess.get_file_as_string("res://scenes/mount_practice.tscn")
    check("the scene file needs no new node: the existing commitment header, control and note are reused", [scene_text.count("name=\"CommitHeader\""), scene_text.count("name=\"CommitOption\""),
        scene_text.count("name=\"CommitNote\""), scene_text.count("[ext_resource")], [1, 1, 1, 1])


# --- 11. the scene ------------------------------------------------------------------------------------------

func label_text(scene: Node, node_name: String) -> String:
    return (scene.get_node("%" + node_name) as Label).text


func commit_texts(option: OptionButton) -> Array:
    var texts: Array = []
    for index: int in option.item_count:
        texts.append(option.get_item_text(index))
    return texts


func _test_scene() -> void:
    var scene: Control = (load("res://scenes/mount_practice.tscn") as PackedScene).instantiate()
    root.add_child(scene)
    await process_frame
    var c: BjjMountPracticeController = scene.controller
    var mode: OptionButton = scene.get_node("%ModeOption")
    var commit: OptionButton = scene.get_node("%CommitOption")
    var next_button: Button = scene.get_node("%NextWindowButton")
    var submit_button: Button = scene.get_node("%SubmitButton")
    var techniques: ItemList = scene.get_node("%TechniqueList")
    var responses: ItemList = scene.get_node("%ResponseList")
    check("scripted start: the control keeps its original meaning and items", [label_text(scene, "CommitHeader"), commit_texts(commit)], ["Commitment", ["LOW", "MEDIUM", "HIGH"]])

    mode.item_selected.emit(1)
    var ref := reference()
    next_button.pressed.emit()
    ref.open_window()
    check("a Top window: the Top's own commitment, named as such, three items, enabled", [label_text(scene, "CommitHeader"), commit_texts(commit), commit.disabled], ["Top's commitment", ["LOW", "MEDIUM", "HIGH"], false])
    techniques.item_selected.emit(0)
    responses.item_selected.emit(0)
    var ref_top := ref.submit(1, TOP_ID, CLIMB, FOREARM)
    submit_button.pressed.emit()
    check("the Top decision equals the reference", c.last_report(), ref_top.fields())

    next_button.pressed.emit()
    ref.open_window()
    check("the Bottom's window relabels the control as the Top's response commitment", label_text(scene, "CommitHeader"), "Top's response commitment")
    check("it offers the engine default and the three commitments", commit_texts(commit), LABELS)
    check("it is disabled until a technique and a response are chosen, and says so", [commit.disabled, label_text(scene, "CommitNote").begins_with("Sets the Top's commitment when it answers. Choose a technique and response first.")], [true, true])
    techniques.item_selected.emit(0)
    check("a technique alone does not enable it", commit.disabled, true)
    responses.item_selected.emit(0)
    check("a technique and a response enable it on the engine default", [commit.disabled, commit.selected, c.selected_response_commitment], [false, 0, ""])
    check("the note says what the default is and that the Bottom's own commitment is not editable", [label_text(scene, "CommitNote").contains("Default = MEDIUM"),
        label_text(scene, "CommitNote").contains("Bottom's own commitment: policy-selected")], [true, true])
    commit.item_selected.emit(3)
    check("choosing HIGH reaches the controller and shows as selected", [c.selected_response_commitment, commit.selected], ["HIGH", 3])
    techniques.item_selected.emit(1)
    check("choosing another technique resets the control and disables it", [c.selected_response_commitment, commit.disabled, commit.selected], ["", true, 0])
    techniques.item_selected.emit(0)
    responses.item_selected.emit(0)
    commit.item_selected.emit(1)
    check("LOW is chosen", [c.selected_response_commitment, commit.selected], ["LOW", 1])
    var ref_bottom := ref.submit(2, BOTTOM_ID, BRIDGE, POST, "", "LOW")
    var key := InputEventKey.new()
    key.keycode = KEY_S
    key.pressed = true
    scene._unhandled_key_input(key)
    check("the S hotkey submitted the Bottom decision with LOW, equal to the reference", [c.last_report(), views(c._graph)], [ref_bottom.fields(), views(ref)])
    check("the result panel shows what the engine used", label_text(scene, "ResultLabel").contains("Top's response commitment: LOW (chosen)"), true)
    check("after the decision the control is back to the Top's own meaning and disabled", [label_text(scene, "CommitHeader"), commit_texts(commit), commit.disabled], ["Commitment", ["LOW", "MEDIUM", "HIGH"], true])

    # No action: the control says there is nothing to choose.
    next_button.pressed.emit()
    techniques.item_selected.emit(0)
    responses.item_selected.emit(0)
    submit_button.pressed.emit()
    next_button.pressed.emit()
    check("a second Bottom window", [c.view().window.role, c.view().window.window_id], ["bottom", 4])
    techniques.item_selected.emit(3)
    check("No action disables the control and explains why", [c.selected_action, commit.disabled, label_text(scene, "CommitNote")], [NO_ACTION, true, "No response commitment: No action was chosen."])
    techniques.item_selected.emit(0)
    responses.item_selected.emit(0)
    commit.item_selected.emit(2)
    check("a choice is held before New Practice Match", c.selected_response_commitment, "MEDIUM")
    (scene.get_node("%NewMatchButton") as Button).pressed.emit()
    check("a stale choice is cleared when New Practice Match starts", [c.selected_response_commitment, c.match_serial], ["", 3])

    # Scripted mode never shows the responder control.
    mode.item_selected.emit(0)
    next_button.pressed.emit()
    techniques.item_selected.emit(0)
    responses.item_selected.emit(0)
    submit_button.pressed.emit()
    next_button.pressed.emit()
    check("scripted Bottom window: the original header, disabled, and the original note", [label_text(scene, "CommitHeader"), commit.disabled, label_text(scene, "CommitNote").begins_with("Selectable only for the Top fighter's window")],
        ["Commitment", true, true])
    root.remove_child(scene)
    scene.free()
    await process_frame
