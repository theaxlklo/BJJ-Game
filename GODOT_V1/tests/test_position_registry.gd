extends SceneTree

# Negative-first tests for the canonical position registry (A3e). The registry is identity
# only: it must reject malformed and undeclared ids with stable codes, never normalize,
# return detached copies, and stay unrelated to Mount behavior. Expected values below are
# literals, never read back from the registry. Declared does not mean implemented: nothing
# here starts, enters or plays any position.
const EXPECTED_IDS: Array[String] = [
    "back_control", "closed_guard", "front_headlock", "half_guard", "leg_entanglement",
    "mount", "open_guard", "side_control", "standing", "turtle",
]
const INVALID: String = "invalid_position_id"
const UNKNOWN: String = "unknown_position_id"

var checks: int = 0
var failures: int = 0


func check(label: String, actual: Variant, expected: Variant) -> void:
    checks += 1
    if typeof(actual) != typeof(expected) or JSON.stringify(actual, "", true, true) != JSON.stringify(expected, "", true, true):
        failures += 1
        if failures <= 25:
            push_error("%s: got %s expected %s" % [label, actual, expected])


func _initialize() -> void:
    _test_invalid_ids()
    _test_casing_and_whitespace_never_normalized()
    _test_unknown_but_well_formed_ids()
    _test_declared_inventory()
    _test_duplicates_and_mutation_attempts()
    _test_identity_only_surface()
    _test_mount_integration()
    _test_existing_graph_behavior_preserved()
    # Same completion contract as the Mount slice: one PASS line with the exact count. CI also
    # validates the whole log, because a script error can abort one test function and still
    # end here with exit 0 and a smaller count.
    if failures > 0:
        push_error("Position registry: %d / %d assertions failed" % [failures, checks])
        quit(1)
        return
    print("Position registry PASS: %d assertions" % checks)
    quit(0)


func _test_invalid_ids() -> void:
    var not_strings: Array = [null, 0, 1, 1.5, true, false, [], ["mount"], {}, {"mount": "mount"}, Vector2.ZERO,
        &"mount", PackedStringArray(["mount"]), NodePath("mount")]
    for value: Variant in not_strings:
        check("non-String is invalid: %s" % [var_to_str(value)], BjjPositionRegistry.error_for(value), INVALID)
        check("non-String is not declared: %s" % [var_to_str(value)], BjjPositionRegistry.is_declared(value), false)
    var malformed: Array[String] = ["", " ", "_", "__", "_mount", "mount_", "mo__unt", "mount__", "1mount", "9", "0_mount",
        "mount-", "mount-control", "side control", "side.control", "side/control", "mount!", "mount?",
        "mount\u00e9",  # accented e
        "m\u00f6unt",  # o with diaeresis
        "mo\u0430nt",  # Cyrillic a lookalike
        "\u30de\u30a6\u30f3\u30c8",  # katakana
        "mount\u200b", "\u200bmount",  # zero-width space
        "mount{", "mount`", "mount:", "mount^", "mount~", "mount|", "mount@", "mount[",  # just outside a-z, 0-9, _
        "mount\u0001", "mount\u007f", "mount\u0080"]  # control, DEL and C1 characters
    for text: String in malformed:
        check("malformed is invalid: %s" % [text.c_escape()], BjjPositionRegistry.error_for(text), INVALID)
        check("malformed is not declared: %s" % [text.c_escape()], BjjPositionRegistry.is_declared(text), false)


func _test_casing_and_whitespace_never_normalized() -> void:
    for id: String in EXPECTED_IDS:
        var variants: Array[String] = [id.to_upper(), id.capitalize(), id.capitalize().replace(" ", ""),
            id.substr(0, 1).to_upper() + id.substr(1), " " + id, id + " ", " " + id + " ", "\t" + id, id + "\t",
            id + "\n", "\n" + id, id + "\r\n", id.replace("_", "-"), id.replace("_", " ")]
        for variant: String in variants:
            if variant == id:
                continue
            check("variant of %s is never normalized: %s" % [id, variant.c_escape()], BjjPositionRegistry.error_for(variant), INVALID)
    # Single-word ids have no underscore; capitalized and upper forms must still differ.
    check("Mount is invalid", BjjPositionRegistry.error_for("Mount"), INVALID)
    check("MOUNT is invalid", BjjPositionRegistry.error_for("MOUNT"), INVALID)
    check("Half Guard (the exit label) is invalid as an id", BjjPositionRegistry.error_for("Half Guard"), INVALID)
    check("Open Guard (the exit label) is invalid as an id", BjjPositionRegistry.error_for("Open Guard"), INVALID)
    check("Reversal (the exit label) is invalid as an id", BjjPositionRegistry.error_for("Reversal"), INVALID)


func _test_unknown_but_well_formed_ids() -> void:
    # Well formed, not declared. A retired-id policy is not decided (POSITION_TOPOLOGY 19.2 a);
    # none exists, so nothing here claims one.
    var unknown: Array[String] = ["reversal", "scramble", "technical_mount", "north_south", "knee_on_belly", "butterfly",
        "deep_half", "guard", "top", "bottom", "submission", "tap", "timeout", "mount_2", "mount2", "mount_top",
        "half_guard_top", "standing_neutral", "a", "z9", "x_y_z", "closed", "side", "back", "leg", "front", "synthetic_a"]
    for text: String in unknown:
        check("well-formed undeclared id is unknown: %s" % text, BjjPositionRegistry.error_for(text), UNKNOWN)
        check("undeclared id is not declared: %s" % text, BjjPositionRegistry.is_declared(text), false)
    check("reversal is an outcome label, not a position id", BjjPositionRegistry.is_declared("reversal"), false)
    var very_long: String = "a".repeat(10000)
    check("a very long well-formed id is unknown, not invalid", BjjPositionRegistry.error_for(very_long), UNKNOWN)
    check("a very long id is not declared", BjjPositionRegistry.is_declared(very_long), false)


func _test_declared_inventory() -> void:
    check("exactly ten ids, sorted, no more", BjjPositionRegistry.declared_ids(), EXPECTED_IDS)
    check("ten declared ids", BjjPositionRegistry.declared_ids().size(), 10)
    var sorted_copy: Array[String] = EXPECTED_IDS.duplicate()
    sorted_copy.sort()
    check("literal inventory is itself sorted", EXPECTED_IDS, sorted_copy)
    for id: String in EXPECTED_IDS:
        check("declared: " + id, BjjPositionRegistry.is_declared(id), true)
        check("no error for declared: " + id, BjjPositionRegistry.error_for(id), "")
    # Name-checked constants carry the literal values (the strings are the persisted values).
    check("constant values", [BjjPositionRegistry.BACK_CONTROL, BjjPositionRegistry.CLOSED_GUARD, BjjPositionRegistry.FRONT_HEADLOCK,
        BjjPositionRegistry.HALF_GUARD, BjjPositionRegistry.LEG_ENTANGLEMENT, BjjPositionRegistry.MOUNT, BjjPositionRegistry.OPEN_GUARD,
        BjjPositionRegistry.SIDE_CONTROL, BjjPositionRegistry.STANDING, BjjPositionRegistry.TURTLE], EXPECTED_IDS)
    check("registry codes", [BjjPositionRegistry.INVALID_POSITION_ID, BjjPositionRegistry.UNKNOWN_POSITION_ID], [INVALID, UNKNOWN])
    # The inventory is not a roster: nothing but Mount is implemented, and the registry says nothing about it.
    check("Standing is declared identity only", BjjPositionRegistry.is_declared("standing"), true)


func _test_duplicates_and_mutation_attempts() -> void:
    var seen: Dictionary = {}
    for id: String in BjjPositionRegistry.declared_ids():
        check("no duplicate declaration: " + id, seen.has(id), false)
        seen[id] = true
    check("declared ids are unique", seen.size(), BjjPositionRegistry.declared_ids().size())
    # Mutating a returned list, in every way, must never reach the registry or later results.
    var returned := BjjPositionRegistry.declared_ids()
    returned.append("standing")
    returned.append("not_a_position")
    returned[0] = "tampered"
    returned.sort()
    returned.reverse()
    returned.erase("mount")
    check("later enumeration unaffected by tampering", BjjPositionRegistry.declared_ids(), EXPECTED_IDS)
    check("tampered value is still not declared", BjjPositionRegistry.is_declared("not_a_position"), false)
    check("tampered-away value is still declared", BjjPositionRegistry.is_declared("mount"), true)
    returned.clear()
    check("clearing a copy does not clear the registry", BjjPositionRegistry.declared_ids().size(), 10)
    var first := BjjPositionRegistry.declared_ids()
    var second := BjjPositionRegistry.declared_ids()
    first.append("x")
    check("independent copies on each call", second, EXPECTED_IDS)
    # Queries are pure and repeatable, in any order and number of calls.
    for pass_index: int in 3:
        for id: String in ["mount", "Mount", "reversal", "standing", "", "turtle"]:
            check("repeatable %s pass %d" % [id, pass_index], BjjPositionRegistry.error_for(id),
                {"mount": "", "Mount": INVALID, "reversal": UNKNOWN, "standing": "", "": INVALID, "turtle": ""}[id])
    check("queries leave the inventory intact", BjjPositionRegistry.declared_ids(), EXPECTED_IDS)
    check("declared_ids returns a writable copy, never the read-only constant", BjjPositionRegistry.declared_ids().is_read_only(), false)


func _test_identity_only_surface() -> void:
    # The registry must stay identity only: its whole public surface is pinned here so adding
    # grading, techniques, stamina, exits or implementation flags is a visible, reviewed change.
    var registry_script: Script = BjjPositionRegistry
    var constants: Array = []
    for key: Variant in registry_script.get_script_constant_map().keys():
        constants.append(str(key))
    constants.sort()
    check("exact constant surface", constants, ["BACK_CONTROL", "CLOSED_GUARD", "DECLARED", "FRONT_HEADLOCK", "HALF_GUARD",
        "INVALID_POSITION_ID", "LEG_ENTANGLEMENT", "MOUNT", "OPEN_GUARD", "SIDE_CONTROL", "STANDING", "TURTLE", "UNKNOWN_POSITION_ID"])
    var methods: Array = []
    for method: Dictionary in registry_script.get_script_method_list():
        if not str(method.name).begins_with("_") and not str(method.name).begins_with("@"):
            methods.append(str(method.name))
    methods.sort()
    check("exact public static surface", methods, ["declared_ids", "error_for", "is_declared"])
    check("no mutable script variables", registry_script.get_script_property_list().filter(
        func(p: Dictionary) -> bool: return (int(p.usage) & PROPERTY_USAGE_SCRIPT_VARIABLE) != 0).size(), 0)
    # Reflection does not list static variables, so also scan the source: the registry must declare
    # no variable of any kind (no cache, no mutable state) and must stay a plain RefCounted.
    var source: String = FileAccess.get_file_as_string("res://scripts/core/position_registry.gd")
    check("registry source is readable", source.is_empty(), false)
    var variable_lines: Array[String] = []
    var extends_lines: Array[String] = []
    for line: String in source.split("\n"):
        # Only column-0 declarations are class level; indented `var` lines are function locals.
        if line.begins_with("var ") or line.begins_with("static var ") or line.begins_with("@export") or line.begins_with("@onready"):
            variable_lines.append(line)
        if line.begins_with("extends "):
            extends_lines.append(line)
    check("no variables declared anywhere in the registry (no mutable state)", variable_lines, [])
    check("registry extends RefCounted only (no Node or scene-tree dependency)", extends_lines, ["extends RefCounted"])


func _test_mount_integration() -> void:
    # Existing Mount identity and declared destinations stay valid registry ids, unchanged.
    check("Mount contract position id", BjjMountContract.POSITION_ID, "mount")
    check("Mount id is declared", BjjPositionRegistry.is_declared(BjjMountContract.POSITION_ID), true)
    check("registry Mount constant equals Mount contract id", BjjPositionRegistry.MOUNT, BjjMountContract.POSITION_ID)
    check("graph source position id", BjjPositionGraphMatch.POSITION_ID, "mount")
    check("graph source id is declared", BjjPositionRegistry.is_declared(BjjPositionGraphMatch.POSITION_ID), true)
    check("Mount exit declarations unchanged", [BjjMountContract.EXIT_DESTINATIONS, BjjMountContract.UNRESOLVED_EXITS],
        [{"Half Guard": "half_guard", "Open Guard": "open_guard"}, ["Reversal"]])
    for label: String in BjjMountContract.EXIT_DESTINATIONS:
        var destination: String = BjjMountContract.EXIT_DESTINATIONS[label]
        check("declared destination %s is a registry id" % label, BjjPositionRegistry.is_declared(destination), true)
    check("Half Guard destination", BjjPositionRegistry.HALF_GUARD, BjjMountContract.EXIT_DESTINATIONS["Half Guard"])
    check("Open Guard destination", BjjPositionRegistry.OPEN_GUARD, BjjMountContract.EXIT_DESTINATIONS["Open Guard"])
    # Reversal stays an unresolved outcome label: never a position id, in any spelling.
    check("Reversal is unresolved", BjjMountContract.UNRESOLVED_EXITS, ["Reversal"])
    for label: String in BjjMountContract.UNRESOLVED_EXITS:
        check("unresolved label is not a position id: " + label, BjjPositionRegistry.is_declared(label), false)
        check("lowercased unresolved label is not a position id: " + label, BjjPositionRegistry.is_declared(label.to_lower()), false)
        check("unresolved label is not a Mount destination", BjjMountContract.EXIT_DESTINATIONS.has(label), false)
    check("transition_for(Reversal) stays unresolved", BjjMountContract.transition_for("Reversal").fields(),
        {"kind": "exit", "raw_destination": "Reversal", "destination_position_id": "", "resolved": false})
    var contract := BjjMountContract.create(BjjMountMatch.create({}).match_state, "a", "b").contract
    var destinations := contract.transition_destinations()
    destinations.sort()
    check("contract destinations unchanged", destinations, ["half_guard", "open_guard"])
    for destination: String in destinations:
        check("contract destination is a registry id: " + destination, BjjPositionRegistry.is_declared(destination), true)
    check("contract roles use a declared id", BjjPositionRegistry.is_declared(contract.roles().position_id), true)
    # Declared ids that are not Mount destinations stay absent from the Mount contract.
    for id: String in BjjPositionRegistry.declared_ids():
        if id != "half_guard" and id != "open_guard":
            check("not a Mount destination: " + id, destinations.has(id), false)


func _test_existing_graph_behavior_preserved() -> void:
    # Declaring an id changes nothing: every declared non-Mount source is still an unknown
    # source for the graph, exactly as before the registry existed (POSITION_TOPOLOGY 18.8).
    for id: String in BjjPositionRegistry.declared_ids():
        if id == "mount":
            check("Mount classification unchanged: Half Guard", BjjPositionGraphMatch.classify_exit_from(id, "Half Guard"),
                {"kind": "blocked", "reason": "destination_not_implemented", "destination_position_id": "half_guard"})
            continue
        for label: String in ["Half Guard", "Open Guard", "Reversal", "Side Control"]:
            check("declared non-Mount source %s stays unknown for %s" % [id, label], BjjPositionGraphMatch.classify_exit_from(id, label),
                {"kind": "blocked", "reason": "unknown_source_position", "destination_position_id": ""})
    # The Mount-only constructors are unchanged and still ignore the registry.
    var bare := BjjPositionGraphMatch.create({}, "fighter_alpha", "fighter_bravo")
    check("a bare configuration is still refused by the Mount-only graph constructor", bare.error, "unsupported_production_recovery_configuration")
    var rules := BjjProductionStaminaPolicy.settings()
    rules["enable_v02_setup"] = true
    rules["enable_v04_commitment_semantics"] = true
    var created := BjjPositionGraphMatch.create({"rules": rules}, "fighter_alpha", "fighter_bravo")
    check("Mount-only graph constructor unchanged with the production configuration", created.ok(), true)
    if created.ok():
        check("graph still starts active in Mount", created.graph.status(), "active")
    var gateway := BjjMountContract.create(BjjMountMatch.create({}).match_state, "fighter_alpha", "fighter_bravo")
    check("Mount-only contract constructor unchanged", gateway.ok(), true)
    var same_ids := BjjMountContract.create(BjjMountMatch.create({}).match_state, "fighter_alpha", "fighter_alpha")
    check("source-fighter validation unchanged: duplicate fighter ids", same_ids.error, "invalid_fighter_id")
