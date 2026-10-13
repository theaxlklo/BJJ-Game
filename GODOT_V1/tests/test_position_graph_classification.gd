extends SceneTree

# Negative-first tests for position-aware exit classification (A2). Classification is a pure,
# read-only decision: Mount keeps its authoritative mapping (BjjMountContract), unknown or
# malformed inputs fail closed, and synthetic declarations are isolated from Mount. Nothing
# here registers a production position or a transition commit.
const TOP_ID: String = "fighter_alpha"
const BOTTOM_ID: String = "fighter_bravo"
const MOUNT: String = "mount"

var checks: int = 0
var failures: int = 0

func check(label: String, actual: Variant, expected: Variant) -> void:
    checks += 1
    if JSON.stringify(actual, "", true, true) != JSON.stringify(expected, "", true, true):
        failures += 1
        if failures <= 25:
            push_error("%s: got %s expected %s" % [label, actual, expected])

func blocked(reason: String, destination: String = "") -> Dictionary:
    return {"kind": "blocked", "reason": reason, "destination_position_id": destination}

func synthetic() -> Dictionary:
    return {
        "synthetic_a": {"exits": {"Alpha Exit": "synthetic_b", "Half Guard": "synthetic_c"}, "unresolved": ["Scramble"]},
        "synthetic_b": {"exits": {"Beta Exit": "synthetic_a"}, "unresolved": []},
    }

func malformed_declarations() -> Dictionary:
    return {
        "not a dictionary": "x",
        "null": null,
        "empty dictionary": {},
        "missing exits": {"unresolved": []},
        "missing unresolved": {"exits": {"A": "b"}},
        "extra key": {"exits": {"A": "b"}, "unresolved": [], "implemented": true},
        "exits not a dictionary": {"exits": ["A"], "unresolved": []},
        "empty exit label": {"exits": {"": "b"}, "unresolved": []},
        "non-string exit label": {"exits": {1: "b"}, "unresolved": []},
        "empty destination": {"exits": {"A": ""}, "unresolved": []},
        "non-string destination": {"exits": {"A": 3}, "unresolved": []},
        "self destination": {"exits": {"A": "synthetic_m"}, "unresolved": []},
        "unresolved not an array": {"exits": {"A": "b"}, "unresolved": "Scramble"},
        "unresolved empty label": {"exits": {"A": "b"}, "unresolved": [""]},
        "unresolved non-string": {"exits": {"A": "b"}, "unresolved": [4]},
        "unresolved duplicate": {"exits": {"A": "b"}, "unresolved": ["S", "S"]},
        "unresolved overlaps exits": {"exits": {"A": "b"}, "unresolved": ["A"]},
    }

func _init() -> void:
    # ---- 1. Mount classification is identical and still authoritative -----------------------
    var labels: Array[String] = ["", "Half Guard", "Open Guard", "Reversal", "Bogus", "half_guard", "mount", "Mount",
        "Side Control", " Half Guard", "half guard", "Half Guard ", "REVERSAL"]
    for label: String in labels:
        check("legacy equals position-aware for " + label, BjjPositionGraphMatch.classify_exit_from(MOUNT, label),
            BjjPositionGraphMatch.classify_exit(label))
    check("Mount none", BjjPositionGraphMatch.classify_exit_from(MOUNT, ""), {"kind": "none"})
    check("Mount Half Guard", BjjPositionGraphMatch.classify_exit_from(MOUNT, "Half Guard"), blocked("destination_not_implemented", "half_guard"))
    check("Mount Open Guard", BjjPositionGraphMatch.classify_exit_from(MOUNT, "Open Guard"), blocked("destination_not_implemented", "open_guard"))
    check("Mount Reversal", BjjPositionGraphMatch.classify_exit_from(MOUNT, "Reversal"), blocked("unresolved_destination"))
    for label: String in ["Bogus", "half_guard", "Side Control", " Half Guard"]:
        check("Mount undeclared " + label, BjjPositionGraphMatch.classify_exit_from(MOUNT, label), blocked("undeclared_exit_label"))
    # Mount's mapping is read from BjjMountContract, not copied: every declared label agrees with it.
    for label: String in BjjMountContract.EXIT_DESTINATIONS.keys():
        check("authoritative destination " + label, BjjPositionGraphMatch.classify_exit_from(MOUNT, label).destination_position_id,
            BjjMountContract.transition_for(label).destination_position_id)
    for label: String in BjjMountContract.UNRESOLVED_EXITS:
        check("authoritative unresolved " + label, BjjPositionGraphMatch.classify_exit_from(MOUNT, label).reason, "unresolved_destination")

    # ---- 2. Unknown sources are never interpreted as Mount ----------------------------------
    for source: String in ["", "Mount", "MOUNT", " mount", "mount ", "half_guard", "open_guard", "side_control", "standing", "unknown"]:
        for label: String in ["", "Half Guard", "Open Guard", "Reversal", "Bogus"]:
            check("unknown source '%s' label '%s'" % [source, label], BjjPositionGraphMatch.classify_exit_from(source, label),
                blocked("unknown_source_position"))
            check("unknown source with unrelated declarations '%s' '%s'" % [source, label],
                BjjPositionGraphMatch.classify_exit_from(source, label, synthetic()), blocked("unknown_source_position"))

    # ---- 3. Synthetic declarations are isolated from Mount ----------------------------------
    var decl := synthetic()
    check("synthetic none", BjjPositionGraphMatch.classify_exit_from("synthetic_a", "", decl), {"kind": "none"})
    check("synthetic declared", BjjPositionGraphMatch.classify_exit_from("synthetic_a", "Alpha Exit", decl), blocked("destination_not_implemented", "synthetic_b"))
    check("synthetic unresolved", BjjPositionGraphMatch.classify_exit_from("synthetic_a", "Scramble", decl), blocked("unresolved_destination"))
    check("synthetic undeclared", BjjPositionGraphMatch.classify_exit_from("synthetic_a", "Beta Exit", decl), blocked("undeclared_exit_label"))
    check("synthetic does not know Mount Open Guard", BjjPositionGraphMatch.classify_exit_from("synthetic_a", "Open Guard", decl), blocked("undeclared_exit_label"))
    check("synthetic does not know Mount Reversal", BjjPositionGraphMatch.classify_exit_from("synthetic_a", "Reversal", decl), blocked("undeclared_exit_label"))
    check("synthetic reuses a Mount label name", BjjPositionGraphMatch.classify_exit_from("synthetic_a", "Half Guard", decl), blocked("destination_not_implemented", "synthetic_c"))
    check("Mount unaffected by that reuse", BjjPositionGraphMatch.classify_exit_from(MOUNT, "Half Guard", decl), blocked("destination_not_implemented", "half_guard"))
    check("Mount does not know synthetic labels", BjjPositionGraphMatch.classify_exit_from(MOUNT, "Alpha Exit", decl), blocked("undeclared_exit_label"))
    check("second synthetic position isolated", BjjPositionGraphMatch.classify_exit_from("synthetic_b", "Alpha Exit", decl), blocked("undeclared_exit_label"))
    check("second synthetic declared", BjjPositionGraphMatch.classify_exit_from("synthetic_b", "Beta Exit", decl), blocked("destination_not_implemented", "synthetic_a"))
    check("without declarations synthetic is unknown", BjjPositionGraphMatch.classify_exit_from("synthetic_a", "Alpha Exit"), blocked("unknown_source_position"))
    check("no synthetic result is ever a transition", BjjPositionGraphMatch.classify_exit_from("synthetic_a", "Alpha Exit", decl).kind, "blocked")
    for production: String in ["half_guard", "open_guard", "side_control", "standing"]:
        check("no production registration for " + production, BjjPositionGraphMatch.classify_exit_from(production, "Side Control"), blocked("unknown_source_position"))

    # ---- 4. Malformed declarations fail closed ----------------------------------------------
    var bad := malformed_declarations()
    for name: String in bad:
        var declaration: Variant = bad[name]
        var holder := {"synthetic_m": declaration}
        for label: String in ["", "A", "S", "Scramble", "Half Guard"]:
            check("malformed '%s' label '%s'" % [name, label], BjjPositionGraphMatch.classify_exit_from("synthetic_m", label, holder),
                blocked("malformed_declaration"))
    check("declaration may not shadow Mount (Mount query)", BjjPositionGraphMatch.classify_exit_from(MOUNT, "Half Guard",
        {MOUNT: {"exits": {"Half Guard": "somewhere"}, "unresolved": []}}), blocked("malformed_declaration"))
    check("declaration may not shadow Mount (other query)", BjjPositionGraphMatch.classify_exit_from("synthetic_a", "Alpha Exit",
        {MOUNT: {"exits": {}, "unresolved": []}, "synthetic_a": decl.synthetic_a}), blocked("malformed_declaration"))
    check("empty-string key is never a source", BjjPositionGraphMatch.classify_exit_from("", "Alpha Exit",
        {"": {"exits": {"Alpha Exit": "b"}, "unresolved": []}}), blocked("unknown_source_position"))
    var good_and_bad := {"synthetic_a": decl.synthetic_a, "synthetic_bad": "oops"}
    check("a malformed neighbour does not poison a valid declaration", BjjPositionGraphMatch.classify_exit_from("synthetic_a", "Alpha Exit", good_and_bad),
        blocked("destination_not_implemented", "synthetic_b"))
    check("the malformed neighbour itself fails closed", BjjPositionGraphMatch.classify_exit_from("synthetic_bad", "Alpha Exit", good_and_bad),
        blocked("malformed_declaration"))

    # ---- 5. Deterministic and read-only -----------------------------------------------------
    var before := synthetic()
    var shared := synthetic()
    var first: Array = []
    var second: Array = []
    for label: String in ["", "Alpha Exit", "Scramble", "Bogus", "Half Guard"]:
        first.append(BjjPositionGraphMatch.classify_exit_from("synthetic_a", label, shared))
        second.append(BjjPositionGraphMatch.classify_exit_from("synthetic_a", label, shared))
    check("deterministic across calls", first, second)
    check("declarations are not mutated", shared, before)
    var result := BjjPositionGraphMatch.classify_exit_from(MOUNT, "Half Guard")
    result["reason"] = "tampered"
    result["destination_position_id"] = "tampered"
    check("a returned result is detached (Mount)", BjjPositionGraphMatch.classify_exit_from(MOUNT, "Half Guard"), blocked("destination_not_implemented", "half_guard"))
    var detached := BjjPositionGraphMatch.classify_exit_from("synthetic_a", "Alpha Exit", shared)
    detached["reason"] = "tampered"
    check("a returned result is detached (synthetic)", BjjPositionGraphMatch.classify_exit_from("synthetic_a", "Alpha Exit", shared),
        blocked("destination_not_implemented", "synthetic_b"))
    check("declarations still untouched after tampering", shared, before)
    check("Mount tables untouched", [BjjMountContract.EXIT_DESTINATIONS, BjjMountContract.UNRESOLVED_EXITS],
        [{"Half Guard": "half_guard", "Open Guard": "open_guard"}, ["Reversal"]])

    # ---- 5b. Strictness, ordering and extra read-only evidence --------------------------------
    check("a synthetic exit to mount is still only a blocked classification", BjjPositionGraphMatch.classify_exit_from("synthetic_x", "X",
        {"synthetic_x": {"exits": {"X": "mount"}, "unresolved": []}}), blocked("destination_not_implemented", "mount"))
    for name: String in ["null destination", "bool label", "null in unresolved", "float destination", "StringName label", "StringName destination", "PackedStringArray unresolved"]:
        var odd: Dictionary = {}
        match name:
            "null destination": odd = {"exits": {"A": null}, "unresolved": []}
            "bool label": odd = {"exits": {true: "b"}, "unresolved": []}
            "null in unresolved": odd = {"exits": {"A": "b"}, "unresolved": [null]}
            "float destination": odd = {"exits": {"A": 1.5}, "unresolved": []}
            "StringName label": odd = {"exits": {&"A": "b"}, "unresolved": []}
            "StringName destination": odd = {"exits": {"A": &"b"}, "unresolved": []}
            "PackedStringArray unresolved": odd = {"exits": {"A": "b"}, "unresolved": PackedStringArray(["S"])}
        check("fails closed: " + name, BjjPositionGraphMatch.classify_exit_from("synthetic_o", "A", {"synthetic_o": odd}), blocked("malformed_declaration"))
    var typed_exits: Dictionary[String, String] = {"A": "synthetic_b"}
    var typed_unresolved: Array[String] = ["S"]
    check("typed containers are accepted (declared)", BjjPositionGraphMatch.classify_exit_from("synthetic_t", "A",
        {"synthetic_t": {"exits": typed_exits, "unresolved": typed_unresolved}}), blocked("destination_not_implemented", "synthetic_b"))
    check("typed containers are accepted (unresolved)", BjjPositionGraphMatch.classify_exit_from("synthetic_t", "S",
        {"synthetic_t": {"exits": typed_exits, "unresolved": typed_unresolved}}), blocked("unresolved_destination"))
    var ordered := {"synthetic_a": {"exits": {"Alpha Exit": "synthetic_b", "Other": "synthetic_c"}, "unresolved": ["S1", "S2"]}, "synthetic_bad": 1}
    var reordered := {"synthetic_bad": 1, "synthetic_a": {"unresolved": ["S2", "S1"], "exits": {"Other": "synthetic_c", "Alpha Exit": "synthetic_b"}}}
    for label: String in ["", "Alpha Exit", "Other", "S1", "S2", "Bogus"]:
        for source: String in ["synthetic_a", "synthetic_bad", "mount", "unknown"]:
            check("order independent %s/%s" % [source, label], BjjPositionGraphMatch.classify_exit_from(source, label, ordered),
                BjjPositionGraphMatch.classify_exit_from(source, label, reordered))
    var bad_before := malformed_declarations().duplicate(true)
    var bad_holder := malformed_declarations()
    for name: String in bad_holder:
        BjjPositionGraphMatch.classify_exit_from("synthetic_m", "A", {"synthetic_m": bad_holder[name]})
    BjjPositionGraphMatch.classify_exit_from("synthetic_a", "Alpha Exit", good_and_bad)
    check("malformed declarations are not mutated", bad_holder, bad_before)
    check("neighbour map is not mutated", good_and_bad, {"synthetic_a": decl.synthetic_a, "synthetic_bad": "oops"})
    for label: String in ["", "Half Guard", "Reversal", "Bogus"]:
        var typed := BjjPositionGraphMatch.classify_exit_from(MOUNT, label)
        for key: String in typed:
            check("string typed result field %s/%s" % [label, key], typeof(typed[key]), TYPE_STRING)

    # ---- 6. Graph atomicity is unchanged and classification never touches a graph -----------
    var rules := BjjProductionStaminaPolicy.settings()
    rules["enable_v02_setup"] = true
    rules["enable_v04_commitment_semantics"] = true
    var created := BjjPositionGraphMatch.create({"rules": rules}, TOP_ID, BOTTOM_ID)
    check("graph created", created.ok(), true)
    if not created.ok():
        print("position graph classification failures: ", failures)
        quit(1)
        return
    var graph := created.graph
    var snapshot := graph_snapshot(graph)
    check("a rejected submit leaves the graph unchanged", graph.submit(1, TOP_ID).ok(), false)
    check("graph unchanged after rejected submit", graph_snapshot(graph), snapshot)
    BjjPositionGraphMatch.classify_exit_from(MOUNT, "Half Guard")
    BjjPositionGraphMatch.classify_exit_from("synthetic_a", "Alpha Exit", synthetic())
    BjjPositionGraphMatch.classify_exit_from("unknown", "Half Guard")
    check("classification does not touch the graph", graph_snapshot(graph), snapshot)
    check("graph source position is still Mount", BjjPositionGraphMatch.POSITION_ID, MOUNT)
    check("graph status active", graph.status(), "active")

    print("position graph classification checks: ", checks)
    print("position graph classification failures: ", failures)
    quit(1 if failures > 0 else 0)

func graph_snapshot(g: BjjPositionGraphMatch) -> Dictionary:
    return {"state": g.state_fields(), "history": g.history_fields(), "controller": g.controller_fields(),
        "window": g.window_fields(), "status": g.status(), "events": g.events(), "blocked": g.blocked_transition()}
