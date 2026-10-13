extends SceneTree

# Negative-first tests for F0: BjjFighterDefinition (reusable content Resource), the additive
# read-only BjjMatchWindowGateway.behavior_fields() and BjjFighterSnapshotAdapter. The Mount
# match stays the only owner of stamina, exhaustion, behavior, roles and time; every check here
# compares a snapshot with the gateway's own views or with the match (test-side private access
# is used ONLY as the authoritative oracle, exactly as test_window_gateway_boundaries.gd does).
# Expected values are literals or come from a different source than the code under test.
const TOP_ID: String = "fighter_alpha"
const BOTTOM_ID: String = "fighter_bravo"
const ALPHA_RES: String = "res://tests/resources/fighter_test_alpha.tres"
const BRAVO_RES: String = "res://tests/resources/fighter_test_bravo.tres"

var checks: int = 0
var failures: int = 0


func check(label: String, actual: Variant, expected: Variant) -> void:
    checks += 1
    if typeof(actual) != typeof(expected) or JSON.stringify(actual, "", true, true) != JSON.stringify(expected, "", true, true):
        failures += 1
        if failures <= 25:
            push_error("%s: got %s expected %s" % [label, actual, expected])


func _initialize() -> void:
    _test_definition_negatives()
    _test_definition_resources_and_inspector()
    _test_adapter_creation_negatives()
    _test_adapter_creation_accepts()
    _test_behavior_accessor()
    _test_snapshots_across_phases()
    _test_terminal_match()
    _test_detached_and_inert_reads()
    _test_role_resolution_by_identity()
    _test_synthetic_role_mapping()
    _test_reused_definition_has_no_shared_runtime_state()
    _test_surface_and_source_boundaries()
    # Same completion contract as the Mount slice: one PASS line with the exact count. CI also
    # validates the whole log, because a script error can abort one test function and still
    # end here with exit 0 and a smaller count.
    if failures > 0:
        push_error("Fighter foundation: %d / %d assertions failed" % [failures, checks])
        quit(1)
        return
    print("Fighter foundation PASS: %d assertions" % checks)
    quit(0)


# --- helpers ---------------------------------------------------------------------------

func rules() -> Dictionary:
    var s := BjjProductionStaminaPolicy.settings()
    s["enable_v02_setup"] = true
    s["enable_v03_submissions"] = true
    s["enable_v04_commitment_semantics"] = true
    return s


func make(top_id: String = TOP_ID, bottom_id: String = BOTTOM_ID, top_stamina: int = 80, bottom_stamina: int = 35) -> BjjMatchWindowGateway:
    return BjjMatchWindowGateway.create({"rules": rules(), "top_stamina": top_stamina, "bottom_stamina": bottom_stamina,
        "capacity": 100}, top_id, bottom_id).gateway


func definition(id: String, display: String) -> BjjFighterDefinition:
    var d := BjjFighterDefinition.new()
    d.definition_id = id
    d.display_name = display
    return d


func alpha() -> BjjFighterDefinition:
    return definition("test_template_alpha", "Test Alpha")


func bravo() -> BjjFighterDefinition:
    return definition("test_template_bravo", "Test Bravo")


func views(g: BjjMatchWindowGateway) -> Dictionary:
    var carry := g.carryover_segment()
    return {"state": g.state_fields(), "history": g.history_fields(), "controller": g.controller_fields(),
        "window": g.window_fields(), "behaviors": g.behavior_fields(), "roles": g.roles().fields(),
        "terminal": g.is_terminal(), "commitment": g.selected_commitment(),
        "carryover": {"error": carry.error, "record": carry.record},
        "lifecycle": g._match.lifecycle_fields()}


func rejected(label: String, gateway: Variant, definitions: Variant, expected_error: String) -> void:
    var before: Dictionary = views(gateway) if gateway is BjjMatchWindowGateway else {}
    var created := BjjFighterSnapshotAdapter.create(gateway, definitions)
    check(label + ": rejected", created.ok(), false)
    check(label + ": code", created.error, expected_error)
    check(label + ": no adapter", created.adapter == null, true)
    if gateway is BjjMatchWindowGateway:
        check(label + ": gateway untouched", views(gateway), before)


func pair(top_definition: Variant, bottom_definition: Variant) -> Dictionary:
    return {TOP_ID: top_definition, BOTTOM_ID: bottom_definition}


# --- 1. definitions: negatives first ---------------------------------------------------

func _test_definition_negatives() -> void:
    var fresh := BjjFighterDefinition.new()
    check("a fresh definition is invalid until filled in", fresh.validation_error(), "invalid_definition_id")
    var bad_ids: Array[String] = ["", "Alpha", "ALPHA", "1alpha", "_alpha", "alpha beta", "alpha-beta", "alpha!", "alpha.beta",
        "alpha\n", "alpha ", " alpha", "alph" + String.chr(0xe9), "a".repeat(65), String.chr(0x200b) + "alpha"]
    for text: String in bad_ids:
        var d := definition(text, "Name")
        check("bad definition id: " + text.c_escape(), d.validation_error(), "invalid_definition_id")
    for text: String in ["a`", "a{", "a/", "a:", "a@", "a[", "a" + String.chr(31), "a" + String.chr(127)]:
        check("bad id at a character boundary: " + text.c_escape(), definition(text, "Name").validation_error(), "invalid_definition_id")
    for text: String in ["a", "z", "a0", "a9", "alpha_1", "test_template_alpha", "a".repeat(64), "a__b", "a_"]:
        check("good definition id: " + text, definition(text, "Name").validation_error(), "")
    var bad_names: Array[String] = ["", " ", "  x", "x  ", "line\nbreak", "tab\tx", "x" + String.chr(7), "x" + String.chr(127),
        "x" + String.chr(0x85), "x" + String.chr(31), "x" + String.chr(0x9f), "a" + String.chr(31) + "b", "a" + String.chr(127) + "b",
        "a" + String.chr(0x9f) + "b", "a".repeat(65), "\n"]
    for text: String in bad_names:
        check("bad display name: " + text.c_escape(), definition("good_id", text).validation_error(), "invalid_display_name")
    for text: String in ["A", "Test Alpha", "Jos" + String.chr(0xe9) + " Silva", "a".repeat(64), "O'Brien", "Two  Spaces"]:
        check("good display name: " + text, definition("good_id", text).validation_error(), "")
    check("id is checked before name", definition("", "").validation_error(), "invalid_definition_id")
    check("valid id with an invalid name", definition("good_id", "").validation_error(), "invalid_display_name")
    # Validation never normalizes or mutates the content.
    var d := definition("good_id", " padded ")
    d.validation_error()
    check("validation leaves the name untouched", d.display_name, " padded ")


# --- 2. definitions: reusable, Inspector-editable content ------------------------------

func _test_definition_resources_and_inspector() -> void:
    var a: Resource = load(ALPHA_RES)
    var b: Resource = load(BRAVO_RES)
    check("alpha loads as a fighter definition", a is BjjFighterDefinition, true)
    check("bravo loads as a fighter definition", b is BjjFighterDefinition, true)
    check("alpha content", [a.definition_id, a.display_name, a.validation_error()], ["test_template_alpha", "Test Alpha", ""])
    check("bravo content", [b.definition_id, b.display_name, b.validation_error()], ["test_template_bravo", "Test Bravo", ""])
    check("the two test definitions differ", a.definition_id != b.definition_id and a.display_name != b.display_name, true)
    # An uncached load is an independent object; editing one never reaches the other.
    var fresh: Resource = ResourceLoader.load(ALPHA_RES, "", ResourceLoader.CACHE_MODE_IGNORE)
    check("an uncached load is a distinct object", fresh != a, true)
    fresh.display_name = "Edited"
    fresh.definition_id = "edited_id"
    check("editing one copy leaves the cached resource alone", [a.definition_id, a.display_name], ["test_template_alpha", "Test Alpha"])
    var copy: BjjFighterDefinition = a.duplicate()
    copy.display_name = "Copy"
    check("duplicate() is independent", [a.display_name, copy.display_name], ["Test Alpha", "Copy"])
    # Inspector editing: both fields are exported, editor-visible and stored; nothing else is.
    var exported: Array = []
    var script_variables: Array = []
    for property: Dictionary in a.get_property_list():
        var usage: int = int(property.usage)
        if (usage & PROPERTY_USAGE_SCRIPT_VARIABLE) != 0:
            script_variables.append(str(property.name))
            if (usage & PROPERTY_USAGE_EDITOR) != 0 and (usage & PROPERTY_USAGE_STORAGE) != 0 and int(property.type) == TYPE_STRING:
                exported.append(str(property.name))
    script_variables.sort()
    exported.sort()
    check("only two script variables exist", script_variables, ["definition_id", "display_name"])
    check("both are String properties editable in the Inspector and saved with the resource", exported, ["definition_id", "display_name"])


# --- 3. adapter creation: reject everything wrong before anything is stored -------------

func _test_adapter_creation_negatives() -> void:
    var g := make()
    for bad_gateway: Variant in [null, 5, "gateway", [], {}, RefCounted.new(), BjjMountMatch.create({}).match_state]:
        var created := BjjFighterSnapshotAdapter.create(bad_gateway, pair(alpha(), bravo()))
        check("not a gateway: " + var_to_str(bad_gateway).substr(0, 24), [created.ok(), created.error], [false, "missing_gateway"])
    for bad_map: Variant in [null, 5, "map", [alpha(), bravo()], alpha()]:
        rejected("definitions not a Dictionary: " + var_to_str(bad_map).substr(0, 24), g, bad_map, "invalid_definitions")
    rejected("empty mapping", g, {}, "missing_fighter_definition")
    rejected("only the top fighter", g, {TOP_ID: alpha()}, "missing_fighter_definition")
    rejected("only the bottom fighter", g, {BOTTOM_ID: bravo()}, "missing_fighter_definition")
    rejected("a third, unknown fighter", g, {TOP_ID: alpha(), BOTTOM_ID: bravo(), "fighter_charlie": alpha()}, "unknown_fighter_id")
    rejected("one unknown id instead of a known one", g, {TOP_ID: alpha(), "fighter_charlie": bravo()}, "unknown_fighter_id")
    rejected("two unknown ids", g, {"x": alpha(), "y": bravo()}, "unknown_fighter_id")
    rejected("case mismatch", g, {"Fighter_alpha": alpha(), BOTTOM_ID: bravo()}, "unknown_fighter_id")
    rejected("whitespace mismatch", g, {TOP_ID + " ": alpha(), BOTTOM_ID: bravo()}, "unknown_fighter_id")
    rejected("empty-string id", g, {"": alpha(), BOTTOM_ID: bravo()}, "unknown_fighter_id")
    rejected("definition ids used as fighter ids", g, {"test_template_alpha": alpha(), "test_template_bravo": bravo()}, "unknown_fighter_id")
    rejected("integer keys", g, {1: alpha(), 2: bravo()}, "invalid_fighter_id_key")
    rejected("a non-String key among valid ones", g, {TOP_ID: alpha(), BOTTOM_ID: bravo(), 3: alpha()}, "invalid_fighter_id_key")
    rejected("StringName keys are not Strings", g, {&"fighter_alpha": alpha(), &"fighter_bravo": bravo()}, "invalid_fighter_id_key")
    rejected("null definition", g, pair(null, bravo()), "invalid_fighter_definition")
    rejected("null definition for the bottom fighter", g, pair(alpha(), null), "invalid_fighter_definition")
    for wrong: Variant in ["alpha", 5, {}, [], Resource.new(), RefCounted.new()]:
        rejected("wrong value type: " + var_to_str(wrong).substr(0, 24), g, pair(wrong, bravo()), "invalid_fighter_definition")
    rejected("a fresh definition", g, pair(BjjFighterDefinition.new(), bravo()), "invalid_definition_id")
    rejected("a definition with no name", g, pair(alpha(), definition("test_template_bravo", "")), "invalid_display_name")
    var padded := definition("test_template_bravo", " Bravo ")
    rejected("a padded name is rejected, never trimmed", g, pair(alpha(), padded), "invalid_display_name")
    check("and the rejected definition keeps its padding", padded.display_name, " Bravo ")
    var shouting := definition("Test_Template", "Bravo")
    rejected("an upper-case id is rejected, never lowered", g, pair(alpha(), shouting), "invalid_definition_id")
    check("and the rejected definition keeps its id", shouting.definition_id, "Test_Template")
    rejected("the first failing fighter (sorted by id) decides", g, pair(definition("Bad Id", "X"), definition("ok_id", "")), "invalid_definition_id")
    rejected("the bottom fighter's own error is reported", g, pair(alpha(), definition("Bad Id", "X")), "invalid_definition_id")
    # No adapter can exist for fighter ids the gateway itself rejects.
    for ids: Array in [["same", "same"], ["", "b"], ["a", ""], [" a", "b"], ["a ", "b"]]:
        var made := BjjMatchWindowGateway.create({"rules": rules()}, ids[0], ids[1])
        check("gateway refuses ids " + str(ids), [made.ok(), made.error], [false, "invalid_fighter_id"])
        check("so no adapter for ids " + str(ids), BjjFighterSnapshotAdapter.create(made.gateway, pair(alpha(), bravo())).error, "missing_gateway")
    # Mid-match rejection leaves the match exactly as it was, too.
    g.open_window()
    rejected("while a window is open", g, {TOP_ID: alpha()}, "missing_fighter_definition")


# --- 4. adapter creation: what is accepted -----------------------------------------------

func _test_adapter_creation_accepts() -> void:
    var g := make()
    var before := views(g)
    var created := BjjFighterSnapshotAdapter.create(g, pair(alpha(), bravo()))
    check("exactly the two gateway fighters are accepted", [created.ok(), created.error], [true, ""])
    check("creating an adapter changes nothing", views(g), before)
    check("fighter ids are sorted and role-independent", created.adapter.fighter_ids(), [TOP_ID, BOTTOM_ID])
    # Keys are matched by value, so insertion order is irrelevant.
    var reversed := BjjFighterSnapshotAdapter.create(g, {BOTTOM_ID: bravo(), TOP_ID: alpha()})
    check("insertion order does not matter", reversed.ok(), true)
    check("both adapters agree", reversed.adapter.snapshots(), created.adapter.snapshots())
    # One reusable definition may back both participants.
    var shared := alpha()
    check("the same definition can back both fighters", BjjFighterSnapshotAdapter.create(g, pair(shared, shared)).ok(), true)
    # Swapping which definition a fighter gets is just data.
    check("definitions can be assigned either way round", BjjFighterSnapshotAdapter.create(g, pair(bravo(), alpha())).ok(), true)
    # The definition id is content, never a fighter id: a definition may even reuse a fighter id string.
    var confusing := BjjFighterSnapshotAdapter.create(g, pair(definition(BOTTOM_ID, "Looks like the bottom fighter"), alpha()))
    check("a definition whose id equals another fighter's id is only content", confusing.ok(), true)
    var snaps := confusing.adapter.snapshots()
    check("match identity still comes from the gateway", [snaps[TOP_ID].fighter_id, snaps[TOP_ID].definition_id, snaps[TOP_ID].role],
        [TOP_ID, BOTTOM_ID, "top"])
    check("and the other fighter is untouched", [snaps[BOTTOM_ID].fighter_id, snaps[BOTTOM_ID].definition_id, snaps[BOTTOM_ID].role],
        [BOTTOM_ID, "test_template_alpha", "bottom"])
    check("the gateway's roles are unchanged", g.roles().fighter_by_role, {"top": TOP_ID, "bottom": BOTTOM_ID})


# --- 5. the one additive gateway accessor ----------------------------------------------

func _test_behavior_accessor() -> void:
    var g := make()
    check("initial behaviors (literal)", g.behavior_fields(), {"top": "PRESSURE", "bottom": "ESCAPE"})
    check("agrees with the authoritative match", g.behavior_fields(), {"top": g._match.top_behavior, "bottom": g._match.bottom_behavior})
    check("the history cannot say: it is empty before the first window", [g.history_fields().top_behavior_history, g.history_fields().bottom_behavior_history], [[], []])
    # Detached.
    var fields := g.behavior_fields()
    fields["top"] = "tampered"
    fields["extra"] = true
    fields.erase("bottom")
    check("a returned dictionary is detached", g.behavior_fields(), {"top": "PRESSURE", "bottom": "ESCAPE"})
    check("tampering never reached the match", [g._match.top_behavior, g._match.bottom_behavior], ["PRESSURE", "ESCAPE"])
    # Pure read: nothing else moves.
    var before := views(g)
    for i: int in 20:
        g.behavior_fields()
    check("reading behaviors is inert", views(g), before)
    # An exhausted bottom fighter: the accessor tracks the match while history lags or is empty.
    var tired := make(TOP_ID, BOTTOM_ID, 80, 10)
    # The accessor reports the behavior the match currently HOLDS (set by the last advance); it is not
    # re-derived from the exhaustion band, which the next advance may do. Before any window the
    # exhausted bottom fighter still holds the baseline, so this pins the held semantics.
    check("exhausted bottom, before any window: the held baseline, not a re-derived CONSERVE", [tired.state_fields().bottom_band, tired.behavior_fields()],
        ["Exhausted", {"top": "PRESSURE", "bottom": "ESCAPE"}])
    check("and history is empty", tired.history_fields().bottom_behavior_history, [])
    tired.open_window()
    check("after the first window the bottom conserves", tired.behavior_fields(), {"top": "PRESSURE", "bottom": "CONSERVE"})
    check("agrees with the match", tired.behavior_fields(), {"top": tired._match.top_behavior, "bottom": tired._match.bottom_behavior})
    # Never changes through rejected commands.
    var before_rejected := views(tired)
    check("a rejected decision is refused", tired.submit(99, TOP_ID, "mount.top.high_mount_climb").ok(), false)
    check("and leaves behaviors alone", tired.behavior_fields(), before_rejected.behaviors)


# --- 6. snapshots before a window, while one is open, and after each decision ----------

func agreement(label: String, g: BjjMatchWindowGateway, adapter: BjjFighterSnapshotAdapter, names: Dictionary) -> Dictionary:
    var snaps := adapter.snapshots()
    var state := g.state_fields()
    var roles: Dictionary = g.roles().fighter_by_role
    var lifecycle: Dictionary = g._match.lifecycle_fields()
    var keys: Array = snaps.keys()
    keys.sort()
    check(label + ": keyed by exactly the two fighters", keys, [TOP_ID, BOTTOM_ID])
    check(label + ": exactly two snapshots", snaps.size(), 2)
    for role: String in ["top", "bottom"]:
        var id: String = roles[role]
        var s: Dictionary = snaps[id]
        check(label + ": " + role + " fighter id", s.fighter_id, id)
        check(label + ": " + role + " role", s.role, role)
        check(label + ": " + role + " stamina agrees with state_fields()", s.stamina_current, state[role + "_stamina"])
        check(label + ": " + role + " maximum agrees with state_fields()", s.stamina_maximum, state[role + "_maximum"])
        check(label + ": " + role + " band agrees with state_fields()", s.exhaustion_band, state[role + "_band"])
        var pool: BjjStaminaPool = g._match.top if role == "top" else g._match.bottom
        check(label + ": " + role + " stamina agrees with the authoritative pool", [s.stamina_current, s.stamina_maximum, s.exhaustion_band],
            [pool.current, pool.maximum, pool.band])
        check(label + ": " + role + " behavior agrees with the match", s.behavior, lifecycle[role + "_behavior"])
        check(label + ": " + role + " display name", s.display_name, names[id].display)
        check(label + ": " + role + " definition id", s.definition_id, names[id].definition)
        check(label + ": " + role + " field set", s.keys(), ["fighter_id", "definition_id", "display_name", "role", "stamina_current",
            "stamina_maximum", "exhaustion_band", "behavior"])
    return snaps


func _test_snapshots_across_phases() -> void:
    var names := {TOP_ID: {"display": "Test Alpha", "definition": "test_template_alpha"},
        BOTTOM_ID: {"display": "Test Bravo", "definition": "test_template_bravo"}}
    var g := make()
    var adapter := BjjFighterSnapshotAdapter.create(g, pair(alpha(), bravo())).adapter
    # Before any window: literal configuration.
    var start := agreement("before a window", g, adapter, names)
    check("top starts at 80/100, Fresh, PRESSURE", [start[TOP_ID].stamina_current, start[TOP_ID].stamina_maximum, start[TOP_ID].exhaustion_band, start[TOP_ID].behavior],
        [80, 100, "Fresh", "PRESSURE"])
    check("bottom starts at 35/100, Tired, ESCAPE", [start[BOTTOM_ID].stamina_current, start[BOTTOM_ID].stamina_maximum, start[BOTTOM_ID].exhaustion_band, start[BOTTOM_ID].behavior],
        [35, 100, "Tired", "ESCAPE"])
    var trace: Array = []
    for step: int in 8:
        var opened := g.open_window()
        check("step %d: window opens" % step, opened.ok(), true)
        var window := g.window_fields()
        check("step %d: a window is open" % step, window.open, true)
        var during := agreement("step %d, window open" % step, g, adapter, names)
        var before_decision := views(g)
        if window.role == "top":
            var action: String = g.action_options(window.fighter_id).available_ids()[0]
            var response: String = g.response_options(action).available_ids()[0]
            check("step %d: top decision accepted" % step, g.submit(window.window_id, window.fighter_id, action, response).ok(), true)
        else:
            check("step %d: bottom decision accepted" % step, g.submit(window.window_id, window.fighter_id).ok(), true)
        check("step %d: the decision changed the match" % step, views(g) != before_decision, true)
        var after := agreement("step %d, after the decision" % step, g, adapter, names)
        trace.append([during, after])
        if step == 0:
            check("after the first accepted exchange: literal values", [after[TOP_ID].stamina_current, after[BOTTOM_ID].stamina_current,
                after[TOP_ID].exhaustion_band, after[BOTTOM_ID].exhaustion_band], [72, 27, "Working", "Tired"])
        if step == 2:
            check("after the third window the bottom is Exhausted and conserving", [after[BOTTOM_ID].stamina_current, after[BOTTOM_ID].exhaustion_band,
                after[BOTTOM_ID].behavior, after[TOP_ID].behavior], [18, "Exhausted", "CONSERVE", "PRESSURE"])
    # Determinism: a second, independent match reproduces every snapshot.
    var twin := make()
    var twin_adapter := BjjFighterSnapshotAdapter.create(twin, pair(alpha(), bravo())).adapter
    var twin_trace: Array = []
    for step: int in 8:
        twin.open_window()
        var window := twin.window_fields()
        var during := twin_adapter.snapshots()
        if window.role == "top":
            var action: String = twin.action_options(window.fighter_id).available_ids()[0]
            twin.submit(window.window_id, window.fighter_id, action, twin.response_options(action).available_ids()[0])
        else:
            twin.submit(window.window_id, window.fighter_id)
        twin_trace.append([during, twin_adapter.snapshots()])
    check("an independent twin match produces identical snapshots at every step", twin_trace, trace)


# --- 6b. a finished match -------------------------------------------------------------

func _test_terminal_match() -> void:
    var names := {TOP_ID: {"display": "Test Alpha", "definition": "test_template_alpha"},
        BOTTOM_ID: {"display": "Test Bravo", "definition": "test_template_bravo"}}
    var g := BjjMatchWindowGateway.create({"rules": rules(), "top_stamina": 80, "bottom_stamina": 35, "capacity": 100, "clock": 12},
        TOP_ID, BOTTOM_ID).gateway
    var adapter := BjjFighterSnapshotAdapter.create(g, pair(alpha(), bravo())).adapter
    var decisions: int = 0
    for step: int in 10:
        g.open_window()
        var window := g.window_fields()
        if not window.open:
            break
        if window.role == "top":
            var action: String = g.action_options(window.fighter_id).available_ids()[0]
            check("terminal run: top decision accepted", g.submit(window.window_id, window.fighter_id, action,
                g.response_options(action).available_ids()[0]).ok(), true)
        else:
            check("terminal run: bottom decision accepted", g.submit(window.window_id, window.fighter_id).ok(), true)
        decisions += 1
    check("the short match took exactly two decisions", decisions, 2)
    check("the match is terminal with no clock left", [g.is_terminal(), g.state_fields().ended, g.state_fields().clock_seconds], [true, true, 0])
    check("no window is open once it has ended", g.window_fields().open, false)
    var final := agreement("terminal match", g, adapter, names)
    check("a finished match still reports the fighters", [final[TOP_ID].role, final[BOTTOM_ID].role], ["top", "bottom"])
    check("behaviors agree with the match after the end", g.behavior_fields(), {"top": g._match.top_behavior, "bottom": g._match.bottom_behavior})
    var before := views(g)
    for i: int in 30:
        adapter.snapshots()
        g.behavior_fields()
    check("reads on a finished match are inert", views(g), before)
    check("and snapshots stay stable", adapter.snapshots(), final)


# --- 7. detached results and inert reads -----------------------------------------------

func _test_detached_and_inert_reads() -> void:
    var d_alpha := alpha()
    var d_bravo := bravo()
    var g := make()
    var adapter := BjjFighterSnapshotAdapter.create(g, pair(d_alpha, d_bravo)).adapter
    for phase: String in ["before a window", "window open", "after a decision"]:
        if phase == "window open":
            g.open_window()
        elif phase == "after a decision":
            var window := g.window_fields()
            var action: String = g.action_options(window.fighter_id).available_ids()[0]
            check("the decision used by the after-a-decision phase is accepted", g.submit(window.window_id, window.fighter_id, action,
                g.response_options(action).available_ids()[0]).ok(), true)
            check("and it closed the window", g.window_fields().open, false)
        var before := views(g)
        var expected := adapter.snapshots()
        # Many repeated reads never advance time, spend stamina, move a window, touch D3-B,
        # histories, behaviors, positions or carry-over.
        for i: int in 30:
            adapter.snapshots()
            adapter.fighter_ids()
        check(phase + ": repeated reads are inert", views(g), before)
        check(phase + ": repeated reads agree", adapter.snapshots(), expected)
        # Tamper with everything that was returned.
        var tampered := adapter.snapshots()
        tampered[TOP_ID].stamina_current = 99999
        tampered[TOP_ID].display_name = "Tampered"
        tampered[TOP_ID]["extra"] = true
        tampered[BOTTOM_ID].erase("role")
        tampered.erase(BOTTOM_ID)
        tampered["intruder"] = {}
        var ids := adapter.fighter_ids()
        ids.append("intruder")
        ids[0] = "tampered"
        check(phase + ": tampering with a snapshot leaves the gateway alone", views(g), before)
        check(phase + ": tampering with a snapshot leaves later snapshots alone", adapter.snapshots(), expected)
        check(phase + ": tampering with the id list leaves it alone", adapter.fighter_ids(), [TOP_ID, BOTTOM_ID])
        check(phase + ": definitions untouched by tampering", [d_alpha.definition_id, d_alpha.display_name, d_bravo.definition_id, d_bravo.display_name],
            ["test_template_alpha", "Test Alpha", "test_template_bravo", "Test Bravo"])
    # Editing a shared Resource after creation never changes an existing view.
    var before_edit := adapter.snapshots()
    d_alpha.display_name = "Edited Later"
    d_alpha.definition_id = "edited_later"
    check("later edits to a definition do not leak into snapshots", adapter.snapshots(), before_edit)
    check("and the definition keeps what was written to it", [d_alpha.definition_id, d_alpha.display_name], ["edited_later", "Edited Later"])
    var fresh_adapter := BjjFighterSnapshotAdapter.create(g, pair(d_alpha, d_bravo)).adapter
    check("a new adapter picks the edit up", fresh_adapter.snapshots()[TOP_ID].display_name, "Edited Later")


# --- 8. roles resolve by fighter identity ----------------------------------------------

func _test_role_resolution_by_identity() -> void:
    # Misleading display names and reversed insertion order must not decide roles.
    var misleading := {BOTTOM_ID: definition("sparring_partner", "Top Dog"), TOP_ID: definition("sparring_dummy", "Bottom Feeder")}
    var g := make()
    var snaps := BjjFighterSnapshotAdapter.create(g, misleading).adapter.snapshots()
    check("the top fighter keeps its role despite its name", [snaps[TOP_ID].role, snaps[TOP_ID].display_name], ["top", "Bottom Feeder"])
    check("the bottom fighter keeps its role despite its name", [snaps[BOTTOM_ID].role, snaps[BOTTOM_ID].display_name], ["bottom", "Top Dog"])
    # The same ids with the roles the other way round: roles follow identity.
    var swapped := make(BOTTOM_ID, TOP_ID, 80, 35)
    check("the gateway maps roles to ids", swapped.roles().fighter_by_role, {"top": BOTTOM_ID, "bottom": TOP_ID})
    var swapped_snaps := BjjFighterSnapshotAdapter.create(swapped, misleading).adapter.snapshots()
    check("fighter_bravo is now the top fighter", [swapped_snaps[BOTTOM_ID].role, swapped_snaps[BOTTOM_ID].stamina_current,
        swapped_snaps[BOTTOM_ID].behavior], ["top", 80, "PRESSURE"])
    check("fighter_alpha is now the bottom fighter", [swapped_snaps[TOP_ID].role, swapped_snaps[TOP_ID].stamina_current,
        swapped_snaps[TOP_ID].behavior], ["bottom", 35, "ESCAPE"])
    check("identity metadata followed the id, not the role", [swapped_snaps[BOTTOM_ID].display_name, swapped_snaps[TOP_ID].display_name],
        ["Top Dog", "Bottom Feeder"])
    check("sorted fighter ids do not depend on roles", BjjFighterSnapshotAdapter.create(swapped, misleading).adapter.fighter_ids(), [TOP_ID, BOTTOM_ID])
    # Exactly the ids that were used: unrelated ids are refused for this gateway.
    rejected("ids from a different gateway", swapped, {"other_one": alpha(), "other_two": bravo()}, "unknown_fighter_id")


# --- 9. synthetic role mapping (no claim that Mount can complete a reversal) -----------

func synthetic_roles(top_id: String, bottom_id: String) -> BjjPositionContract.Roles:
    var roles := BjjPositionContract.Roles.new()
    roles.position_id = "synthetic"
    roles.fighter_by_role = {"top": top_id, "bottom": bottom_id}
    return roles


func synthetic_state() -> Dictionary:
    return {"top_stamina": 61, "top_maximum": 90, "top_band": "Working", "bottom_stamina": 7, "bottom_maximum": 95, "bottom_band": "Exhausted"}


func _test_synthetic_role_mapping() -> void:
    # The current Mount engine never swaps roles and cannot execute a completed reversal into another
    # position; these tests only show that the mapping layer keys identity by fighter id.
    var identity := {"fighter_a": {"definition_id": "def_a", "display_name": "Alice"},
        "fighter_b": {"definition_id": "def_b", "display_name": "Bruno"}}
    var behaviors := {"top": "PRESSURE", "bottom": "CONSERVE"}
    var before := BjjFighterSnapshotAdapter._build(synthetic_roles("fighter_a", "fighter_b"), synthetic_state(), behaviors, identity)
    check("A on top: A's role and role-keyed fields", [before.fighter_a.role, before.fighter_a.stamina_current, before.fighter_a.exhaustion_band, before.fighter_a.behavior],
        ["top", 61, "Working", "PRESSURE"])
    check("A on top: B's role and role-keyed fields", [before.fighter_b.role, before.fighter_b.stamina_maximum, before.fighter_b.exhaustion_band, before.fighter_b.behavior],
        ["bottom", 95, "Exhausted", "CONSERVE"])
    # A hypothetical future change of roles: the same ids, the roles reversed.
    var after := BjjFighterSnapshotAdapter._build(synthetic_roles("fighter_b", "fighter_a"), synthetic_state(), behaviors, identity)
    check("after a role change: A is the bottom fighter", [after.fighter_a.role, after.fighter_a.stamina_current, after.fighter_a.behavior],
        ["bottom", 7, "CONSERVE"])
    check("after a role change: B is the top fighter", [after.fighter_b.role, after.fighter_b.stamina_current, after.fighter_b.behavior],
        ["top", 61, "PRESSURE"])
    check("identity metadata never moves with the role", [after.fighter_a.display_name, after.fighter_a.definition_id, after.fighter_b.display_name, after.fighter_b.definition_id],
        ["Alice", "def_a", "Bruno", "def_b"])
    var after_keys: Array = after.keys()
    var before_keys: Array = before.keys()
    after_keys.sort()
    before_keys.sort()
    check("the same two fighter ids key both views", [after_keys, before_keys], [["fighter_a", "fighter_b"], ["fighter_a", "fighter_b"]])
    check("each snapshot names its own fighter", [after.fighter_a.fighter_id, after.fighter_b.fighter_id], ["fighter_a", "fighter_b"])
    # Refusals: roles that do not name exactly the known fighters produce nothing at all.
    check("the same fighter in both roles", BjjFighterSnapshotAdapter._build(synthetic_roles("fighter_a", "fighter_a"), synthetic_state(), behaviors, identity), {})
    check("an unknown fighter in a role", BjjFighterSnapshotAdapter._build(synthetic_roles("fighter_a", "fighter_z"), synthetic_state(), behaviors, identity), {})
    check("an empty role", BjjFighterSnapshotAdapter._build(synthetic_roles("fighter_a", ""), synthetic_state(), behaviors, identity), {})
    var partial := BjjPositionContract.Roles.new()
    partial.fighter_by_role = {"top": "fighter_a"}
    check("a missing role", BjjFighterSnapshotAdapter._build(partial, synthetic_state(), behaviors, identity), {})
    var three := identity.duplicate(true)
    three["fighter_c"] = {"definition_id": "def_c", "display_name": "Carla"}
    check("a third known fighter that no role names", BjjFighterSnapshotAdapter._build(synthetic_roles("fighter_a", "fighter_b"), synthetic_state(), behaviors, three), {})
    # The inputs are never modified.
    check("identity input untouched", identity, {"fighter_a": {"definition_id": "def_a", "display_name": "Alice"},
        "fighter_b": {"definition_id": "def_b", "display_name": "Bruno"}})
    check("state input untouched", synthetic_state(), {"top_stamina": 61, "top_maximum": 90, "top_band": "Working", "bottom_stamina": 7, "bottom_maximum": 95, "bottom_band": "Exhausted"})


# --- 10. one reusable definition, two participants, no shared runtime state ------------

func _test_reused_definition_has_no_shared_runtime_state() -> void:
    var shared := alpha()
    var g := make()
    var adapter := BjjFighterSnapshotAdapter.create(g, pair(shared, shared)).adapter
    var snaps := adapter.snapshots()
    check("both participants show the shared content", [snaps[TOP_ID].display_name, snaps[BOTTOM_ID].display_name,
        snaps[TOP_ID].definition_id, snaps[BOTTOM_ID].definition_id], ["Test Alpha", "Test Alpha", "test_template_alpha", "test_template_alpha"])
    check("but each keeps its own match identity", [snaps[TOP_ID].fighter_id, snaps[BOTTOM_ID].fighter_id], [TOP_ID, BOTTOM_ID])
    check("and its own runtime values", [snaps[TOP_ID].stamina_current, snaps[BOTTOM_ID].stamina_current, snaps[TOP_ID].exhaustion_band,
        snaps[BOTTOM_ID].exhaustion_band, snaps[TOP_ID].role, snaps[BOTTOM_ID].role], [80, 35, "Fresh", "Tired", "top", "bottom"])
    g.open_window()
    var window := g.window_fields()
    var action: String = g.action_options(window.fighter_id).available_ids()[0]
    g.submit(window.window_id, window.fighter_id, action, g.response_options(action).available_ids()[0])
    var after := adapter.snapshots()
    check("a decision moves each participant's own values independently", [after[TOP_ID].stamina_current, after[BOTTOM_ID].stamina_current], [72, 27])
    check("the shared definition holds no runtime state", [shared.definition_id, shared.display_name, shared.validation_error()], ["test_template_alpha", "Test Alpha", ""])
    # A second match backed by the very same Resource instance is unaffected by the first.
    var other := make()
    var other_snaps := BjjFighterSnapshotAdapter.create(other, pair(shared, shared)).adapter.snapshots()
    check("a second match using the same Resource starts fresh", [other_snaps[TOP_ID].stamina_current, other_snaps[BOTTOM_ID].stamina_current,
        other.window_fields().window_id], [80, 35, 0])
    check("and the first match is unaffected by the second", [adapter.snapshots()[TOP_ID].stamina_current, g.window_fields().window_id], [72, 1])


# --- 11. surfaces and source boundaries ------------------------------------------------

func method_names(script: Script) -> Array:
    var names: Array = []
    for method: Dictionary in script.get_script_method_list():
        var name: String = str(method.name)
        if not name.begins_with("_") and not name.begins_with("@"):
            names.append(name)
    names.sort()
    return names


func constant_names(script: Script) -> Array:
    var names: Array = []
    for key: Variant in script.get_script_constant_map().keys():
        names.append(str(key))
    names.sort()
    return names


func class_level_lines(path: String, prefixes: Array) -> Array:
    var found: Array = []
    for line: String in FileAccess.get_file_as_string(path).split("\n"):
        for prefix: String in prefixes:
            if line.begins_with(prefix):
                found.append(line)
    return found


func _test_surface_and_source_boundaries() -> void:
    var definition_script: Script = BjjFighterDefinition
    var adapter_script: Script = BjjFighterSnapshotAdapter
    check("definition public methods", method_names(definition_script), ["validation_error"])
    check("definition constants", constant_names(definition_script), ["INVALID_DEFINITION_ID", "INVALID_DISPLAY_NAME", "MAX_LENGTH"])
    check("definition declares exactly two exported variables and nothing else",
        class_level_lines("res://scripts/core/fighter_definition.gd", ["var ", "static var ", "@export", "@onready", "signal "]),
        ["@export var definition_id: String = \"\"", "@export var display_name: String = \"\""])
    check("definition is a plain Resource", class_level_lines("res://scripts/core/fighter_definition.gd", ["extends "]), ["extends Resource"])
    check("adapter public methods", method_names(adapter_script), ["create", "fighter_ids", "snapshots"])
    check("adapter constants (the inner Creation class counts)", constant_names(adapter_script), ["Creation", "ROLES"])
    check("adapter is a RefCounted", class_level_lines("res://scripts/positions/mount/fighter_snapshot_adapter.gd", ["extends "]), ["extends RefCounted"])
    check("adapter keeps exactly three private members: the source handle (gateway or graph) and plain identity data",
        class_level_lines("res://scripts/positions/mount/fighter_snapshot_adapter.gd", ["var ", "static var ", "@export", "@onready"]),
        ["var _source: Variant", "var _identity: Dictionary = {}", "var _fighter_ids: Array[String] = []"])
    # The adapter reads public gateway views only: no private match, id, pool, controller or carry-over access.
    var forbidden: Array[String] = ["._match", "._contract", "._top_id", "._bottom_id", "._window", ".top_meter", ".bottom_meter",
        ".d3b", ".top.", ".bottom.", "carryover_segment", "lifecycle_fields", "snapshot()",
        "open_window", ".submit(", "reset_window", "next_window", "recovery_hold", "bottom_decision"]
    var offenders: Array = []
    for line: String in FileAccess.get_file_as_string("res://scripts/positions/mount/fighter_snapshot_adapter.gd").split("\n"):
        if line.strip_edges().begins_with("#"):
            continue
        for token: String in forbidden:
            if line.contains(token):
                offenders.append("%s :: %s" % [token, line.strip_edges()])
    check("adapter code (comments aside) reads public gateway views only", offenders, [])
    # The additive read-only accessor exists (the gateway's full surface is not pinned here).
    check("the gateway exposes behavior_fields()", method_names(BjjMatchWindowGateway).has("behavior_fields"), true)
    check("neither class names a Node or scene-tree type", FileAccess.get_file_as_string("res://scripts/positions/mount/fighter_snapshot_adapter.gd").contains("Node")
        or FileAccess.get_file_as_string("res://scripts/core/fighter_definition.gd").contains("Node"), false)
