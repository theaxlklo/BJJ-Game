extends SceneTree

# Negative-first tests for the typed Half Guard v0 engine (BjjHalfGuardRules / Catalog / Resolver / Entry / Match /
# Contract / WindowGateway). Every rejected call must leave the whole segment (state, histories, window record) exactly as it
# was. Expected values are literals hand-computed from HALF_GUARD_V0_RULES.md (the same worked examples the independent Python
# oracle tests use); nothing is read back from the engine. The oracle replay lives in test_half_guard_reference.gd.
const TOP_ID: String = "fighter_a"
const BOTTOM_ID: String = "fighter_b"
const CF: String = BjjHalfGuardCatalog.TOP_CROSSFACE
const FL: String = BjjHalfGuardCatalog.TOP_FLATTEN
const KS: String = BjjHalfGuardCatalog.TOP_KNEE_SLICE
const UH: String = BjjHalfGuardCatalog.BOTTOM_UNDERHOOK
const RG: String = BjjHalfGuardCatalog.BOTTOM_RECOVER_GUARD
const HF: String = BjjHalfGuardCatalog.BOTTOM_HIP_FRAME
const UF: String = BjjHalfGuardCatalog.BOTTOM_UNDERHOOK_FIGHT
const KSH: String = BjjHalfGuardCatalog.BOTTOM_KNEE_SHIELD
const HC: String = BjjHalfGuardCatalog.TOP_HEAD_CONTROL
const HP: String = BjjHalfGuardCatalog.TOP_HIP_PRESSURE
const KP: String = BjjHalfGuardCatalog.TOP_KNEE_PIN
const SOURCES: Array[String] = [
    "res://scripts/positions/half_guard/half_guard_rules.gd", "res://scripts/positions/half_guard/half_guard_catalog.gd",
    "res://scripts/positions/half_guard/half_guard_resolver.gd", "res://scripts/positions/half_guard/half_guard_entry.gd",
    "res://scripts/positions/half_guard/half_guard_match.gd", "res://scripts/positions/half_guard/half_guard_contract.gd",
    "res://scripts/positions/half_guard/half_guard_window_gateway.gd",
]

var checks: int = 0
var failures: int = 0


func check(label: String, actual: Variant, expected: Variant) -> void:
    checks += 1
    if typeof(actual) != typeof(expected) or JSON.stringify(actual, "", true, true) != JSON.stringify(expected, "", true, true):
        failures += 1
        if failures <= 25:
            push_error("%s: got %s expected %s" % [label, JSON.stringify(actual), JSON.stringify(expected)])


func _initialize() -> void:
    _test_rejected_entries()
    _test_fighter_id_edges()
    _test_entry_state_by_fighter_id()
    _test_latch_restoration()
    _test_context_corruption()
    _test_command_refusals_and_precedence()
    _test_window_lifecycle()
    _test_rules_tables_and_bands()
    _test_catalog()
    _test_grade_pipeline_literals()
    _test_readiness_and_wear()
    _test_rule_one_and_paid_effort()
    _test_exits_and_transitions()
    _test_contract_and_options()
    _test_views_are_detached()
    _test_determinism()
    _test_scope_and_hygiene()
    if failures > 0:
        push_error("Half Guard boundaries: %d / %d assertions failed" % [failures, checks])
        quit(1)
        return
    print("Half Guard boundaries PASS: %d assertions" % checks)
    quit(0)


# --- Builders -------------------------------------------------------------------------------

func fighter(current: int = 100, maximum: int = 100, remainder: int = 0) -> Dictionary:
    var enter := int(floor(float(maximum) * 0.25))
    return {"stamina_current": current, "stamina_maximum": maximum, "exhaustion_latched": current <= enter,
        "behavior_remainder_units": remainder}


func entry(top_current: int = 100, bottom_current: int = 100, swap: bool = false, clock: int = 300, interval: int = 5, last_issued: int = 0) -> Dictionary:
    return {"role_map": {"top": BOTTOM_ID if swap else TOP_ID, "bottom": TOP_ID if swap else BOTTOM_ID},
        "fighters": {TOP_ID: fighter(top_current), BOTTOM_ID: fighter(bottom_current)},
        "clock": {"initial_seconds": clock, "remaining_seconds": clock}, "window": {"last_issued_id": last_issued},
        "interval_seconds": interval}


func gateway(request: Dictionary = {}) -> BjjHalfGuardWindowGateway:
    return BjjHalfGuardWindowGateway.create(entry() if request.is_empty() else request).gateway


# A gateway in an arbitrary legal state: public entry path, then plain-field assignment on the match (the test seam).
func at(axis: int, band_value: int, base: int, frame: int, side: String = "top", top_current: int = 100, bottom_current: int = 100) -> BjjHalfGuardWindowGateway:
    var g := gateway(entry(top_current, bottom_current))
    g._match.axis_tenths = axis
    g._match.band = band_value
    g._match.top_base = base
    g._match.bottom_frame = frame
    g._match.initiator = side
    return g


func attempt(g: BjjHalfGuardWindowGateway, action: String, response: String, commitment: String = "MEDIUM", response_commitment: String = "MEDIUM") -> Dictionary:
    var r := g._match.attempt(action, response, commitment, response_commitment)
    if not r.ok():
        return {"error": r.error}
    var values := r.values.duplicate(true)
    values["error"] = ""
    return values


func refused_submit(label: String, g: BjjHalfGuardWindowGateway, expected_error: String, window_id: int, fighter_id: String,
        action: String = "", response: String = "", commitment: String = "", response_commitment: String = "") -> void:
    var before := g.snapshot()
    var r := g.submit(window_id, fighter_id, action, response, commitment, response_commitment)
    check(label + " rejected", r.ok(), false)
    check(label + " error", r.error, expected_error)
    check(label + " no values", r.values.is_empty(), true)
    check(label + " whole segment unchanged", g.snapshot(), before)


func mutated(change: Callable) -> Dictionary:
    var request := entry()
    change.call(request)
    return request


# --- Entry ----------------------------------------------------------------------------------

func _test_rejected_entries() -> void:
    var cases: Array = [
        ["not a dictionary", "text", "entry_not_a_dictionary"], ["null", null, "entry_not_a_dictionary"], ["array", [], "entry_not_a_dictionary"],
        ["missing interval", mutated(func(r: Dictionary) -> void: r.erase("interval_seconds")), "entry_malformed"],
        ["extra top-level key", mutated(func(r: Dictionary) -> void: r["extra"] = 1), "entry_malformed"],
        ["extra role", mutated(func(r: Dictionary) -> void: r.role_map["middle"] = "x"), "entry_malformed"],
        ["float clock", mutated(func(r: Dictionary) -> void: r.clock["initial_seconds"] = 300.0), "entry_malformed"],
        ["bool stamina", mutated(func(r: Dictionary) -> void: r.fighters[TOP_ID]["stamina_current"] = true), "entry_malformed"],
        ["readiness key is not accepted", mutated(func(r: Dictionary) -> void: r.fighters[TOP_ID]["top_base"] = 2), "entry_malformed"],
        ["missing latch", mutated(func(r: Dictionary) -> void: r.fighters[BOTTOM_ID].erase("exhaustion_latched")), "entry_malformed"],
        ["string window id", mutated(func(r: Dictionary) -> void: r.window["last_issued_id"] = "1"), "entry_malformed"],
        ["empty top id", mutated(func(r: Dictionary) -> void: r.role_map["top"] = ""), "invalid_fighter_id"],
        ["padded top id", mutated(func(r: Dictionary) -> void: r.role_map["top"] = " padded"), "invalid_fighter_id"],
        ["trailing newline id", mutated(func(r: Dictionary) -> void: r.role_map["bottom"] = "id\n"), "invalid_fighter_id"],
        ["same fighter in both roles", mutated(func(r: Dictionary) -> void: r.role_map["bottom"] = TOP_ID), "invalid_fighter_id"],
        ["fighters keyed by other ids", mutated(func(r: Dictionary) -> void: r["fighters"] = {TOP_ID: fighter(), "stranger": fighter()}), "fighters_mismatch"],
        ["zero maximum", mutated(func(r: Dictionary) -> void: r.fighters[TOP_ID]["stamina_maximum"] = 0), "invalid_stamina_maximum"],
        ["maximum above 2^53-1", mutated(func(r: Dictionary) -> void: r.fighters[TOP_ID]["stamina_maximum"] = 9007199254740992), "invalid_stamina_maximum"],
        ["current above maximum", mutated(func(r: Dictionary) -> void: r.fighters[BOTTOM_ID]["stamina_current"] = 101), "invalid_stamina_current"],
        ["negative current", mutated(func(r: Dictionary) -> void: r.fighters[BOTTOM_ID]["stamina_current"] = -1), "invalid_stamina_current"],
        ["unlatched at the enter threshold", mutated(func(r: Dictionary) -> void: r.fighters[TOP_ID].merge({"stamina_current": 25, "exhaustion_latched": false}, true)), "inconsistent_exhaustion_latch"],
        ["latched at the recover threshold", mutated(func(r: Dictionary) -> void: r.fighters[TOP_ID].merge({"stamina_current": 35, "exhaustion_latched": true}, true)), "inconsistent_exhaustion_latch"],
        ["remainder out of range", mutated(func(r: Dictionary) -> void: r.fighters[BOTTOM_ID]["behavior_remainder_units"] = 9007199254740992), "invalid_behavior_remainder"],
        ["remaining clock zero", mutated(func(r: Dictionary) -> void: r.clock["remaining_seconds"] = 0), "invalid_clock"],
        ["remaining above initial", mutated(func(r: Dictionary) -> void: r.clock["remaining_seconds"] = 301), "invalid_clock"],
        ["zero initial clock", mutated(func(r: Dictionary) -> void: r.clock.merge({"initial_seconds": 0, "remaining_seconds": 0}, true)), "invalid_clock"],
        ["negative window id", mutated(func(r: Dictionary) -> void: r.window["last_issued_id"] = -1), "invalid_window_id"],
        ["zero interval", mutated(func(r: Dictionary) -> void: r["interval_seconds"] = 0), "invalid_interval"],
        ["negative interval", mutated(func(r: Dictionary) -> void: r["interval_seconds"] = -5), "invalid_interval"],
        ["precedence: clock before window id before interval", mutated(func(r: Dictionary) -> void:
            r["interval_seconds"] = 0
            r.window["last_issued_id"] = -1
            r.clock["remaining_seconds"] = 0), "invalid_clock"],
        ["precedence: fighter ids before stamina", mutated(func(r: Dictionary) -> void:
            r.role_map["bottom"] = TOP_ID
            r.fighters[TOP_ID]["stamina_maximum"] = 0), "invalid_fighter_id"],
        ["precedence: shape before identity", mutated(func(r: Dictionary) -> void:
            r.role_map["top"] = ""
            r.clock["initial_seconds"] = 3.0), "entry_malformed"],
    ]
    for c: Array in cases:
        var request: Variant = c[1]
        var before := JSON.stringify(request)
        check("%s: validate" % c[0], BjjHalfGuardEntry.validate(request), c[2])
        var created := BjjHalfGuardMatch.from_entry(request)
        check("%s: creation error" % c[0], created.error, c[2])
        check("%s: nothing built" % c[0], created.match_state == null, true)
        check("%s: the gateway refuses too" % c[0], BjjHalfGuardWindowGateway.create(request).error, c[2])
        check("%s: request untouched" % c[0], JSON.stringify(request), before)


# Godot's String.strip_edges strips exactly the code points 0x01..0x20 at either end (measured with Godot 4.7.2).
func _test_fighter_id_edges() -> void:
    for code in range(1, 33):
        var ch := String.chr(code)
        for id: String in [ch + "x", "x" + ch]:
            var request := entry()
            request.role_map["top"] = id
            request["fighters"] = {id: fighter(), BOTTOM_ID: fighter()}
            check("id with code 0x%x refused" % code, BjjHalfGuardEntry.validate(request), "invalid_fighter_id")
    for code: int in [0x7f, 0x80, 0x85, 0x9f, 0xa0, 0xad, 0x1680, 0x180e, 0x2000, 0x2003, 0x200a, 0x200b, 0x2028, 0x2029, 0x202f, 0x205f, 0x2060, 0x3000, 0xfeff]:
        var ch := String.chr(code)
        for id: String in [ch + "x", "x" + ch]:
            var request := entry()
            request.role_map["bottom"] = id
            request["fighters"] = {TOP_ID: fighter(), id: fighter()}
            check("id with code 0x%x accepted" % code, BjjHalfGuardEntry.validate(request), "")
    var interior := entry()
    interior.role_map["top"] = "inner space"
    interior["fighters"] = {"inner space": fighter(), BOTTOM_ID: fighter()}
    check("interior whitespace accepted", BjjHalfGuardEntry.validate(interior), "")


func _test_entry_state_by_fighter_id() -> void:
    var request := entry(40, 20)
    request.fighters[TOP_ID]["behavior_remainder_units"] = -3
    request.fighters[BOTTOM_ID]["behavior_remainder_units"] = 11
    request.window["last_issued_id"] = 7
    request["clock"] = {"initial_seconds": 123, "remaining_seconds": 123}
    request["interval_seconds"] = 9
    var built := BjjHalfGuardMatch.from_entry(request)
    check("valid entry builds", built.ok(), true)
    var snapshot := built.match_state.snapshot()
    check("fighter a state", snapshot.fighters[TOP_ID], {"stamina_current": 40, "stamina_maximum": 100, "exhaustion_latched": false, "behavior_remainder_units": -3})
    check("fighter b state", snapshot.fighters[BOTTOM_ID], {"stamina_current": 20, "stamina_maximum": 100, "exhaustion_latched": true, "behavior_remainder_units": 11})
    check("entry values", [snapshot.axis_tenths, snapshot.band, snapshot.initiator, snapshot.top_base, snapshot.bottom_frame, snapshot.window_id,
        snapshot.window_open, snapshot.clock_seconds, snapshot.initial_clock, snapshot.interval_seconds, snapshot.exit_destination],
        [5, 0, "top", 1, 1, 7, false, 123, 123, 9, ""])
    check("empty histories", snapshot.history, BjjHalfGuardMatch.empty_history())
    # Swapped role map: the same two fighters, opposite roles; state follows the fighter id.
    var swapped := BjjHalfGuardMatch.from_entry(entry(40, 20, true)).match_state
    check("swapped fighters keyed by id", swapped.snapshot().fighters, BjjHalfGuardMatch.from_entry(entry(40, 20)).match_state.snapshot().fighters)
    check("swapped role map", swapped.snapshot().role_map, {"top": BOTTOM_ID, "bottom": TOP_ID})
    var fields := swapped.state_fields()
    check("swapped top view is fighter b", [fields.top_stamina, fields.bottom_stamina, fields.top_latched, fields.bottom_latched], [20, 40, true, false])
    check("swapped authority follows the Top role", fields.authority, BOTTOM_ID)
    check("entry axis view", fields.axis, 0.5)


func _enter(maximum: int) -> int:
    return int(floor(float(maximum) * 0.25))


func _recover(maximum: int) -> int:
    return int(ceil(float(maximum) * 0.35))


# Latch restoration is checked against a literal two-state model, never against another pool built the same way.
func _test_latch_restoration() -> void:
    var literal: Dictionary = {1: [0, 1], 2: [0, 1], 3: [0, 2], 4: [1, 2], 7: [1, 3], 20: [5, 7], 37: [9, 13], 64: [16, 23], 100: [25, 35]}
    for maximum: int in literal:
        check("thresholds %d" % maximum, [_enter(maximum), _recover(maximum)], literal[maximum])
        for current in range(0, mini(maximum, 100) + 1):
            for latched: bool in [false, true]:
                var accepted: bool = not ((current <= literal[maximum][0] and not latched) or (current >= literal[maximum][1] and latched))
                var request := entry()
                request.fighters[TOP_ID] = {"stamina_current": current, "stamina_maximum": maximum, "exhaustion_latched": latched, "behavior_remainder_units": 0}
                request.fighters[BOTTOM_ID] = fighter()
                var built := BjjHalfGuardMatch.from_entry(request)
                check("entry accepted %d/%d latched %s" % [current, maximum, latched], built.ok(), accepted)
                if not accepted:
                    continue
                var pool := built.match_state.top
                check("restored current %d/%d" % [current, maximum], pool.current, current)
                check("restored latch %d/%d latched %s" % [current, maximum, latched], pool.band == "Exhausted", latched)
                # continuity after spending: the literal hysteresis model
                var state := latched
                var amount := current
                for spend: int in [1, 3, 7, 12]:
                    var charged := pool.spend_up_to(spend).charged
                    amount -= charged
                    state = not (amount >= literal[maximum][1]) if state else amount <= literal[maximum][0]
                    check("latch after spending %d (%d/%d)" % [spend, current, maximum], pool.band == "Exhausted", state)
    # a capacity at the exact-integer limit keeps the frozen float thresholds
    var huge := 9007199254740991
    for current: int in [0, 1, _enter(huge) - 1, _enter(huge), _enter(huge) + 1, _recover(huge) - 1, _recover(huge), _recover(huge) + 1, huge - 1, huge]:
        for latched: bool in [false, true]:
            var request := entry()
            request.fighters[TOP_ID] = {"stamina_current": current, "stamina_maximum": huge, "exhaustion_latched": latched, "behavior_remainder_units": 0}
            var accepted: bool = not ((current <= _enter(huge) and not latched) or (current >= _recover(huge) and latched))
            var built := BjjHalfGuardMatch.from_entry(request)
            check("huge entry %d latched %s" % [current, latched], built.ok(), accepted)
            if accepted:
                check("huge restored latch %d" % current, built.match_state.top.band == "Exhausted", latched)


# --- Context and command refusals -----------------------------------------------------------

func _test_context_corruption() -> void:
    var corruptions: Array = [
        ["missing top pool", "invalid_stamina_state", func(m: BjjHalfGuardMatch) -> void: m.top = null],
        ["aliased pools", "invalid_stamina_state", func(m: BjjHalfGuardMatch) -> void: m.bottom = m.top],
        ["missing meter", "invalid_stamina_state", func(m: BjjHalfGuardMatch) -> void: m.top_meter = null],
        ["invalid initiator", "invalid_initiator", func(m: BjjHalfGuardMatch) -> void: m.initiator = "middle"],
        ["clock above initial", "invalid_clock_context", func(m: BjjHalfGuardMatch) -> void: m.clock_seconds = 301],
        ["negative clock", "invalid_clock_context", func(m: BjjHalfGuardMatch) -> void: m.clock_seconds = -1],
        ["zero interval", "invalid_clock_context", func(m: BjjHalfGuardMatch) -> void: m.interval_seconds = 0],
        ["clock at zero", "terminal_exchange", func(m: BjjHalfGuardMatch) -> void: m.clock_seconds = 0],
        ["exit recorded", "terminal_exchange", func(m: BjjHalfGuardMatch) -> void: m.exit_destination = "Side Control"],
        ["axis out of range", "invalid_half_guard_context", func(m: BjjHalfGuardMatch) -> void: m.axis_tenths = 41],
        ["illegal axis and band", "invalid_half_guard_context", func(m: BjjHalfGuardMatch) -> void: m.band = 1],
        ["unknown band", "invalid_half_guard_context", func(m: BjjHalfGuardMatch) -> void: m.band = 3],
        ["tier above ready", "invalid_half_guard_context", func(m: BjjHalfGuardMatch) -> void: m.top_base = 3],
        ["negative tier", "invalid_half_guard_context", func(m: BjjHalfGuardMatch) -> void: m.bottom_frame = -1],
        ["precedence: stamina before initiator", "invalid_stamina_state", func(m: BjjHalfGuardMatch) -> void:
            m.initiator = "x"
            m.top = null],
        ["precedence: clock before terminal", "invalid_clock_context", func(m: BjjHalfGuardMatch) -> void:
            m.interval_seconds = 0
            m.clock_seconds = 0],
        ["precedence: terminal before Half Guard context", "terminal_exchange", func(m: BjjHalfGuardMatch) -> void:
            m.clock_seconds = 0
            m.axis_tenths = 41],
    ]
    for c: Array in corruptions:
        var g := gateway()
        (c[2] as Callable).call(g._match)
        check("%s: context" % c[0], g._match.validate_context(), c[1])
        if g._match.top == null or g._match.top == g._match.bottom or g._match.top_meter == null:
            continue  # a missing pool cannot be snapshotted; the code above is the evidence
        var before := g.snapshot()
        check("%s: attempt refused" % c[0], g._match.attempt(CF, HF, "MEDIUM").error, c[1])
        check("%s: open_window refused" % c[0], g.open_window().error, c[1])
        check("%s: unchanged" % c[0], g.snapshot(), before)
    var corrupted := gateway()
    corrupted.open_window()
    corrupted._match.initiator = "bottom"
    var before := corrupted.snapshot()
    check("window initiator changed", corrupted.submit(1, TOP_ID, CF, HF).error, "window_initiator_changed")
    check("window initiator changed: unchanged", corrupted.snapshot(), before)


func _test_command_refusals_and_precedence() -> void:
    var opened := gateway()
    var cases: Array = [
        # [label, setup opens a window?, window id, fighter, action, response, commitment, response commitment, code]
        ["no window yet", false, 1, TOP_ID, CF, HF, "", "", "no_open_window"],
        ["stale id", true, 9, TOP_ID, CF, HF, "", "", "stale_window"],
        ["id zero", true, 0, TOP_ID, CF, HF, "", "", "stale_window"],
        ["missing fighter", true, 1, "", CF, HF, "", "", "missing_fighter_id"],
        ["unknown fighter", true, 1, "ghost", CF, HF, "", "", "unknown_fighter"],
        ["not the initiator", true, 1, BOTTOM_ID, UH, HC, "", "", "not_initiator"],
        ["response without action", true, 1, TOP_ID, "", HF, "", "", "response_without_action"],
        ["commitment on a pass", true, 1, TOP_ID, "", "", "LOW", "", "commitment_without_action"],
        ["response commitment on a pass", true, 1, TOP_ID, "", "", "", "LOW", "commitment_without_action"],
        ["invalid commitment", true, 1, TOP_ID, CF, HF, "EXTREME", "", "invalid_commitment"],
        ["invalid response commitment", true, 1, TOP_ID, CF, HF, "", "EXTREME", "invalid_response_commitment"],
        ["unknown action", true, 1, TOP_ID, "nope", HF, "", "", "unknown_action"],
        ["other side's action", true, 1, TOP_ID, UH, HF, "", "", "incorrect_action_side_or_kind"],
        ["a response used as the action", true, 1, TOP_ID, HF, HF, "", "", "incorrect_action_side_or_kind"],
        ["unknown response", true, 1, TOP_ID, CF, "nope", "", "", "unknown_response"],
        ["empty response with an action", true, 1, TOP_ID, CF, "", "", "", "unknown_response"],
        ["own side's response", true, 1, TOP_ID, CF, HC, "", "", "incorrect_response_side_or_kind"],
        ["an action used as the response", true, 1, TOP_ID, CF, UH, "", "", "incorrect_response_side_or_kind"],
        # simultaneous faults: the earliest documented code wins
        ["stale beats everything", true, 9, "ghost", "nope", "nope", "EXTREME", "EXTREME", "stale_window"],
        ["missing fighter beats shape faults", true, 1, "", "nope", "nope", "EXTREME", "EXTREME", "missing_fighter_id"],
        ["unknown fighter beats shape faults", true, 1, "ghost", "nope", "nope", "EXTREME", "EXTREME", "unknown_fighter"],
        ["not initiator beats shape faults", true, 1, BOTTOM_ID, "nope", "nope", "EXTREME", "EXTREME", "not_initiator"],
        ["response without action beats commitments", true, 1, TOP_ID, "", HF, "LOW", "LOW", "response_without_action"],
        ["commitment beats response commitment and ids", true, 1, TOP_ID, CF, "nope", "EXTREME", "EXTREME", "invalid_commitment"],
        ["response commitment beats ids", true, 1, TOP_ID, CF, "nope", "", "EXTREME", "invalid_response_commitment"],
        ["unknown action beats response faults", true, 1, TOP_ID, "nope", "nope", "", "", "unknown_action"],
        ["incorrect action beats response faults", true, 1, TOP_ID, UH, "nope", "", "", "incorrect_action_side_or_kind"],
        ["unknown response beats incorrect response", true, 1, TOP_ID, CF, "nope", "", "", "unknown_response"],
    ]
    for c: Array in cases:
        var g := gateway()
        if bool(c[1]):
            g.open_window()
        refused_submit(c[0], g, c[8], c[2], c[3], c[4], c[5], c[6], c[7])
    opened.open_window()
    check("a valid exchange is accepted after all refusals", opened.submit(1, TOP_ID, CF, HF).ok(), true)
    # terminal outranks command-shape faults
    var terminal := at(25, 1, 1, 1)
    terminal._match.attempt(KS, HF, "MEDIUM")
    refused_submit("terminal, window closed", terminal, "no_open_window", 1, "ghost", "nope")
    terminal._match.window_open = true
    terminal._match.window_side = "top"
    terminal._match.window_id = 1
    refused_submit("terminal context outranks command shape", terminal, "terminal_exchange", 1, "ghost", "nope")
    # match-level attempt
    var g2 := gateway()
    var before := g2.snapshot()
    check("attempt: empty commitment", g2._match.attempt(CF, HF, "").error, "invalid_commitment")
    check("attempt: bad response commitment", g2._match.attempt(CF, HF, "MEDIUM", "bogus").error, "invalid_response_commitment")
    check("attempt: unknown action", g2._match.attempt("", HF, "MEDIUM").error, "unknown_action")
    check("attempt: refusals leave state", g2.snapshot(), before)
    check("attempt: empty response commitment is MEDIUM", g2._match.attempt(CF, HF, "MEDIUM", "").ok(), true)
    check("attempt: charged 7 as MEDIUM", g2.snapshot().history.response_charge_history, [7])


# --- Windows --------------------------------------------------------------------------------

func _test_window_lifecycle() -> void:
    var g := gateway(entry(100, 100, false, 300, 5, 9))
    var opened := g.open_window()
    check("first window id continues the entry counter", [opened.values.window_id, opened.values.fighter_id, opened.values.role, opened.values.commitment], [10, TOP_ID, "top", "MEDIUM"])
    check("advance", opened.values.advance, {"elapsed_seconds": 5, "clock_seconds": 295})
    check("window view", g.window_fields(), {"open": true, "window_id": 10, "fighter_id": TOP_ID, "role": "top"})
    check("second open refused", g.open_window().error, "window_already_open")
    check("exchange accepted", g.submit(10, TOP_ID, CF, UF).values.kind, "exchange")
    check("window closed", g.window_fields(), {"open": false, "window_id": 10, "fighter_id": "", "role": ""})
    var second := g.open_window()
    check("alternation: bottom window", [second.values.window_id, second.values.fighter_id, second.values.role], [11, BOTTOM_ID, "bottom"])
    check("bottom may pass", g.submit(11, BOTTOM_ID).values.kind, "reset")
    check("then top again", g.open_window().values.role, "top")
    check("pass history", [g.history_fields().reset_window_history, g.history_fields().top_initiation_count, g.history_fields().bottom_initiation_count], [["bottom"], 1, 0])
    # a pass changes only initiative
    var p := gateway()
    p.open_window()
    var before := p.snapshot()
    p.submit(1, TOP_ID)
    var after := p.snapshot()
    check("pass flips initiative", after.initiator, "bottom")
    for key: String in ["fighters", "axis_tenths", "band", "top_base", "bottom_frame", "exit_destination"]:
        check("pass leaves %s" % key, after[key], before[key])
    # replayed and stale commands
    var q := gateway()
    q.open_window()
    q.submit(1, TOP_ID, CF, HF)
    var settled := q.snapshot()
    check("replayed command", q.submit(1, TOP_ID, CF, HF).error, "no_open_window")
    check("replay leaves state", q.snapshot(), settled)
    q.open_window()
    check("old window id", q.submit(1, BOTTOM_ID, UH, HC).error, "stale_window")
    check("current id accepted", q.submit(2, BOTTOM_ID, UH, HC).ok(), true)
    # durations
    var d := gateway(entry(100, 100, false, 10, 5, 0))
    for case: Array in [[-1, "invalid_window_request"], [true, "invalid_duration"], ["5", "invalid_duration"], [2.5, "invalid_duration"], [[], "invalid_duration"]]:
        var snapshot := d.snapshot()
        check("duration %s" % JSON.stringify(case[0]), d.open_window_for(case[0]).error, case[1])
        check("duration refusal leaves state", d.snapshot(), snapshot)
    var zero := d.open_window_for(0)
    check("zero-time window", [zero.values.window_open, zero.values.advance.elapsed_seconds, zero.values.advance.clock_seconds], [true, 0, 10])
    d.submit(1, TOP_ID, CF, HF)
    var clamped := d.open_window_for(99)
    check("clamped to the remaining clock", [clamped.values.closed, clamped.values.window_open, clamped.values.window_id], [true, false, 1])
    check("clamped advance", clamped.values.advance, {"elapsed_seconds": 10, "clock_seconds": 0})
    check("timeout reason", d.state_fields().exit_reason, "TIMEOUT — Half Guard retained")
    check("timeout leaves no exit", [d.state_fields().exit_destination, d.state_fields().ended], ["", true])
    # exact interval boundary
    var b := gateway(entry(100, 100, false, 10, 5, 0))
    b.open_window()
    b.submit(1, TOP_ID)
    check("closing report", b.open_window().values.closed, true)
    check("open after the end", b.open_window().error, "terminal_exchange")
    check("submit after the end", b.submit(1, BOTTOM_ID, UH, HC).error, "no_open_window")
    check("attempt after the end", b._match.attempt(UH, HC, "MEDIUM").error, "terminal_exchange")
    # an exit leaves the clock alone
    var e := at(25, 1, 1, 1)
    e.open_window()
    var clock: int = e.state_fields().clock_seconds
    e.submit(1, TOP_ID, KS, HF)
    check("exit leaves the clock", e.state_fields().clock_seconds, clock)
    check("no window after an exit", e.open_window().error, "terminal_exchange")


# --- Pure rules ----------------------------------------------------------------------------------

func _test_rules_tables_and_bands() -> void:
    for axis in range(-40, 41):
        var expected := 0
        if axis >= 10 and axis <= 24:
            expected = 1
        elif axis >= 25:
            expected = 2
        elif axis <= -10 and axis >= -24:
            expected = -1
        elif axis <= -25:
            expected = -2
        check("initial band %d" % axis, BjjHalfGuardRules.initial_band(axis), expected)
    var hysteresis: Array = [[0, 12, 1], [0, 11, 0], [1, 27, 2], [1, 26, 1], [-1, -8, 0], [-1, -9, -1], [-2, -23, -1], [-2, -24, -2],
        [2, 23, 1], [2, 24, 2], [1, 8, 0], [1, 9, 1], [0, -12, -1], [0, -11, 0], [-1, -27, -2], [-1, -26, -1],
        [0, 30, 2], [0, 40, 2], [2, -30, -2], [-2, 40, 2], [1, -40, -2], [-1, 12, 1], [2, 0, 0], [-2, 0, 0],
        [1, 10, 1], [0, 10, 0], [2, 25, 2], [1, 25, 1], [-1, -10, -1], [0, -10, 0]]
    for h: Array in hysteresis:
        check("band %d at %d" % [h[0], h[1]], BjjHalfGuardRules.band_update(h[1], h[0]), h[2])
    for axis in range(-40, 41):
        var legal: Dictionary = {0: axis >= -11 and axis <= 11, 1: axis >= 9 and axis <= 26, 2: axis >= 24, -1: axis >= -26 and axis <= -9, -2: axis <= -24}
        for band_value: int in [-2, -1, 0, 1, 2]:
            check("legal pair %d/%d" % [axis, band_value], BjjHalfGuardRules.legal_pair(axis, band_value), legal[band_value])
            check("update lands legal %d/%d" % [axis, band_value], BjjHalfGuardRules.legal_pair(axis, BjjHalfGuardRules.band_update(axis, band_value)), true)
    check("unknown bands are never legal", [BjjHalfGuardRules.legal_pair(5, 3), BjjHalfGuardRules.legal_pair(5, -3)], [false, false])
    check("authority", [BjjHalfGuardRules.authority_id(0, "t", "b"), BjjHalfGuardRules.authority_id(1, "t", "b"), BjjHalfGuardRules.authority_id(-1, "t", "b"),
        BjjHalfGuardRules.authority_id(40, "t", "b"), BjjHalfGuardRules.authority_id(-40, "t", "b")], ["", "t", "b", "t", "b"])
    check("shift tables", [BjjHalfGuardRules.ATTACK_SHIFT, BjjHalfGuardRules.DEFENSE_SHIFT], [{2: 1, 1: 0, 0: -1}, {2: -1, 1: 0, 0: 2}])
    check("tier names", [BjjHalfGuardRules.tier_name(0), BjjHalfGuardRules.tier_name(1), BjjHalfGuardRules.tier_name(2), BjjHalfGuardRules.tier_name(3)], ["None", "Partial", "Ready", ""])
    check("band names", BjjHalfGuardRules.BAND_NAMES, {-2: "BOTTOM_CONTROL", -1: "BOTTOM_EDGE", 0: "CONTESTED", 1: "TOP_EDGE", 2: "TOP_CONTROL"})
    check("constants", [BjjHalfGuardRules.ENTRY_AXIS, BjjHalfGuardRules.PASS_LINE, BjjHalfGuardRules.ESCAPE_LINE, BjjHalfGuardRules.STEP_TENTHS,
        BjjHalfGuardRules.AXIS_MIN, BjjHalfGuardRules.AXIS_MAX], [5, 30, -30, 10, -40, 40])


func _test_catalog() -> void:
    var literal: Dictionary = {
        "top": {CF: {HF: 1, UF: -1, KSH: 0}, FL: {HF: -1, UF: 1, KSH: 1}, KS: {HF: 1, UF: 2, KSH: -2}},
        "bottom": {UH: {HC: -1, HP: 0, KP: 1}, RG: {HC: 2, HP: 1, KP: -2}},
    }
    check("the 15 C1 raw grades", BjjHalfGuardCatalog.RAW, literal)
    check("C1: Knee Slice vs Hip Frame is +1", BjjHalfGuardCatalog.RAW["top"][KS][HF], 1)
    check("entities", BjjHalfGuardCatalog.ENTITIES.size(), 11)
    check("break-capable set", [BjjHalfGuardCatalog.is_break_capable(CF), BjjHalfGuardCatalog.is_break_capable(FL), BjjHalfGuardCatalog.is_break_capable(KS),
        BjjHalfGuardCatalog.is_break_capable(UH), BjjHalfGuardCatalog.is_break_capable(RG), BjjHalfGuardCatalog.is_break_capable(HF)], [false, false, true, false, true, false])
    check("governed responses (option M)", BjjHalfGuardCatalog.GOVERNED, {KSH: "bottom_frame", KP: "top_base"})
    check("builders", BjjHalfGuardCatalog.BUILD, {CF: ["bottom_frame", -1], FL: ["top_base", 1], UH: ["bottom_frame", 1], RG: ["top_base", -1]})
    check("exit destinations", BjjHalfGuardCatalog.EXIT_DESTINATIONS, {"Side Control": "side_control", "Open Guard": "open_guard", "Closed Guard": "closed_guard"})
    check("short names", [BjjHalfGuardCatalog.short_name(KS), BjjHalfGuardCatalog.short_name(RG)], ["knee_slice", "recover_guard"])
    check("sides own their actions and responses", [BjjHalfGuardCatalog.actions_of("top"), BjjHalfGuardCatalog.actions_of("bottom"),
        BjjHalfGuardCatalog.responses_of("top"), BjjHalfGuardCatalog.responses_of("bottom"), BjjHalfGuardCatalog.actions_of("middle")],
        [[CF, FL, KS], [UH, RG], [HC, HP, KP], [HF, UF, KSH], []])
    for side: String in ["top", "bottom"]:
        for action: String in literal[side]:
            var row: Dictionary = literal[side][action]
            var lowest := 9
            var highest := -9
            for response: String in row:
                lowest = mini(lowest, int(row[response]))
                highest = maxi(highest, int(row[response]))
            check("%s has a counter" % action, lowest <= -1, true)
            check("%s has a favorable response" % action, highest >= 1, true)
    # every matchup at the neutral entry state resolves to its raw grade
    for side: String in ["top", "bottom"]:
        for action: String in literal[side]:
            for response: String in literal[side][action]:
                var g := at(5, 0, 1, 1, side)
                var r := attempt(g, action, response)
                var raw: int = literal[side][action][response]
                check("neutral %s vs %s" % [action, response], [r.error, r.raw_grade, r.final_grade], ["", raw, raw])
                check("neutral axis %s vs %s" % [action, response], r.axis_proposed, 5 + (10 * raw if side == "top" else -10 * raw))


# --- Grade pipeline and readiness ---------------------------------------------------------------

func _test_grade_pipeline_literals() -> void:
    var r := attempt(at(5, 0, 0, 0), KS, KSH)
    check("saturation order: raw -2, attacker None, defender None -> 0", [r.grade_after_attack, r.grade_after_defense, r.final_grade, r.attack_readiness_shift, r.defense_readiness_shift, r.defense_strength_tier], [-2, 0, 0, -1, 2, 0])
    r = attempt(at(5, 0, 2, 0), KS, KSH)
    check("prepared attacker beats an unprepared defender", [r.grade_after_attack, r.grade_after_defense, r.final_grade, r.axis_after, r.tiers_after, r.readiness_changes],
        [-1, 1, 1, 15, {"top_base": 1, "bottom_frame": 0}, ["top_base:Ready->Partial:knee_slice"]])
    check("Ready defender is stronger below the floor", [attempt(at(5, 0, 1, 2), CF, KSH).final_grade, attempt(at(5, 0, 1, 2), FL, KSH).final_grade, attempt(at(5, 0, 1, 2), KS, KSH).final_grade], [-1, 0, -2])
    for tier in range(3):
        check("non-governed ignores readiness", attempt(at(5, 0, 1, tier), CF, HF).defense_readiness_shift, 0)
        check("non-governed has no strength tier", attempt(at(5, 0, tier, 1, "bottom"), UH, HC).defense_strength_tier, null)
    for tier in range(3):
        var shift: int = [-1, 0, 1][tier]
        check("attack shift top tier %d" % tier, attempt(at(5, 0, tier, 1), KS, HF).attack_readiness_shift, shift)
        check("attack shift bottom tier %d" % tier, attempt(at(5, 0, 1, tier, "bottom"), RG, HP).attack_readiness_shift, shift)
        check("non-break attack unshifted", attempt(at(5, 0, tier, 1), CF, HF).attack_readiness_shift, 0)
    check("attacker reads its own track", attempt(at(5, 0, 2, 0), KS, HF).attack_readiness_shift, 1)
    # positional modifier
    r = attempt(at(-30, -2, 1, 1), CF, HF)
    check("top against bottom control", [r.positional_modifier, r.final_grade], [-1, 0])
    r = attempt(at(30, 2, 1, 1, "bottom"), UH, KP)
    check("bottom against top control", [r.positional_modifier, r.final_grade], [-1, 0])
    check("no modifier against its own band", [attempt(at(30, 2, 1, 1), CF, HF).positional_modifier, attempt(at(-15, -1, 1, 1), CF, HF).positional_modifier], [0, 0])
    # exhaustion
    check("exhausted attacker", attempt(at(5, 0, 1, 1, "top", 20, 100), CF, HF).final_grade, 0)
    check("exhausted responder", attempt(at(5, 0, 1, 1, "top", 100, 20), CF, UF).final_grade, 0)
    r = attempt(at(5, 0, 1, 1, "top", 20, 20), CF, HF)
    check("both exhausted cancel", [r.exhaustion_modifier, r.final_grade, r.initiator_band, r.responder_band], [0, 1, "Exhausted", "Exhausted"])
    # magnitude and undercommitment in sequence
    check("HIGH presses a Success", attempt(at(5, 0, 1, 1), CF, HF, "HIGH", "MEDIUM").final_grade, 2)
    r = attempt(at(5, 0, 1, 1), FL, HF, "HIGH", "MEDIUM")
    check("HIGH presses a Failure then undercommitment", [r.magnitude_modifier, r.undercommitment_modifier, r.final_grade], [-1, 1, -1])
    check("LOW softens a Strong Success", attempt(at(5, 0, 1, 1), KS, UF, "LOW", "LOW").final_grade, 1)
    check("a LOW defender is unprepared (strength None)", attempt(at(5, 0, 1, 1), KS, KSH, "LOW", "LOW").final_grade, 0)
    check("undercommitment only when strictly below", [attempt(at(5, 0, 1, 1), CF, UF, "MEDIUM", "LOW").undercommitment_modifier,
        attempt(at(5, 0, 1, 1), CF, UF, "MEDIUM", "HIGH").undercommitment_modifier, attempt(at(5, 0, 1, 1), CF, UF, "MEDIUM", "MEDIUM").undercommitment_modifier], [1, 0, 0])
    r = attempt(at(5, 0, 1, 1, "top", 2, 100), KS, UF)
    check("unfunded initiator", [r.initiator_effective, r.exhaustion_modifier, r.grade_after_exhaustion, r.final_grade], ["", -1, 1, 1])
    r = attempt(at(5, 0, 0, 2), KS, KSH, "MEDIUM", "LOW")
    check("a LOW answer defeats a Ready structure", [r.defense_strength_tier, r.defense_readiness_shift, r.final_grade], [0, 2, 1])
    r = attempt(at(5, 0, 0, 2), KS, KSH, "MEDIUM", "MEDIUM")
    check("the same defender at MEDIUM keeps the Ready shift", [r.defense_strength_tier, r.defense_readiness_shift, r.final_grade], [2, -1, -2])
    # funding
    for requested: String in BjjCommitment.ORDER:
        for current in range(0, 16):
            var expected := ""
            if requested == "HIGH" and current >= 12:
                expected = "HIGH"
            elif requested != "LOW" and current >= 7:
                expected = "MEDIUM"
            elif current >= 3:
                expected = "LOW"
            check("funding %s at %d" % [requested, current], BjjStaminaCostPolicy.defaults().determine(requested, current).effective, expected)


func _test_readiness_and_wear() -> void:
    var neutral: Array = [
        ["top", CF, HF, [1, 1], [1, 0], ["bottom_frame:Partial->None:crossface"]], ["top", CF, UF, [1, 1], [1, 1], []], ["top", CF, KSH, [1, 1], [1, 1], []],
        ["top", FL, UF, [1, 1], [2, 1], ["top_base:Partial->Ready:flatten"]],
        ["top", FL, KSH, [1, 1], [2, 0], ["bottom_frame:Partial->None:flatten", "top_base:Partial->Ready:flatten"]],
        ["top", FL, HF, [1, 1], [1, 1], []], ["top", KS, HF, [1, 1], [1, 1], []], ["top", KS, KSH, [1, 1], [1, 0], ["bottom_frame:Partial->None:knee_slice"]],
        ["bottom", UH, KP, [1, 1], [0, 2], ["top_base:Partial->None:underhook", "bottom_frame:Partial->Ready:underhook"]], ["bottom", UH, HC, [1, 1], [1, 1], []],
        ["bottom", RG, HP, [1, 1], [0, 1], ["top_base:Partial->None:recover_guard"]], ["bottom", RG, HC, [1, 1], [0, 1], ["top_base:Partial->None:recover_guard"]],
        ["bottom", RG, KP, [1, 1], [0, 1], ["top_base:Partial->None:recover_guard"]],
    ]
    for c: Array in neutral:
        var g := at(5, 0, c[3][0], c[3][1], c[0])
        var r := attempt(g, c[1], c[2])
        check("readiness %s vs %s" % [c[1], c[2]], [[r.tiers_after.top_base, r.tiers_after.bottom_frame], r.readiness_changes], [c[4], c[5]])
        check("history agrees %s vs %s" % [c[1], c[2]], g.history_fields().readiness_change_history, c[5])
        check("state view agrees %s vs %s" % [c[1], c[2]], [g.state_fields().top_base, g.state_fields().bottom_frame], c[4])
    # floors and ceilings
    var r := attempt(at(5, 0, 2, 1), FL, UF)
    check("ceiling records no change", [r.tiers_after.top_base, r.readiness_changes], [2, []])
    r = attempt(at(5, 0, 1, 0), CF, HF)
    check("floor records no change", [r.tiers_after.bottom_frame, r.readiness_changes], [0, []])
    # consumption of a prepared technique at Ready, whatever the result
    for c: Array in [[KS, HF, "top_base", "top"], [KS, KSH, "top_base", "top"], [RG, HC, "bottom_frame", "bottom"], [RG, KP, "bottom_frame", "bottom"]]:
        var base: int = 2 if c[2] == "top_base" else 1
        var frame: int = 2 if c[2] == "bottom_frame" else 1
        var ready := attempt(at(5, 0, base, frame, c[3]), c[0], c[1])
        check("Ready is consumed %s" % c[0], ready.readiness_changes.any(func(s: String) -> bool: return s.begins_with(c[2] + ":Ready->Partial")), true)
        var partial_base: int = 1
        var partial := attempt(at(5, 0, partial_base, partial_base, c[3]), c[0], c[1])
        check("Partial is not consumed %s" % c[0], partial.readiness_changes.any(func(s: String) -> bool: return s.begins_with(c[2] + ":Ready->")), false)
    for c: Array in [[CF, UF, "top_base", "top"], [FL, HF, "top_base", "top"], [UH, HC, "bottom_frame", "bottom"]]:
        var base: int = 2 if c[2] == "top_base" else 1
        var frame: int = 2 if c[2] == "bottom_frame" else 1
        var unprepared := attempt(at(5, 0, base, frame, c[3]), c[0], c[1])
        check("non-prepared %s never consumes" % c[0], [unprepared.readiness_changes, unprepared.tiers_after[c[2]]], [[], 2])
    # double touch: the update order is wear then build
    var g2 := at(5, 0, 1, 2, "top", 100, 20)
    r = attempt(g2, CF, KSH, "HIGH", "MEDIUM")
    check("double touch final", r.final_grade, 1)
    check("double touch order", [r.readiness_changes, r.tiers_after.bottom_frame], [["bottom_frame:Ready->Partial:crossface", "bottom_frame:Partial->None:crossface"], 0])
    # wear depends on commitment and outcome
    check("MEDIUM wears on a decisive defense", attempt(at(5, 0, 1, 1), KS, KSH, "MEDIUM", "MEDIUM").tiers_after.bottom_frame, 0)
    check("HIGH paid preserves a successful defense", attempt(at(5, 0, 1, 1), KS, KSH, "MEDIUM", "HIGH").tiers_after.bottom_frame, 1)
    check("LOW never wears", attempt(at(5, 0, 1, 1), KS, KSH, "MEDIUM", "LOW").tiers_after.bottom_frame, 1)
    check("HIGH funded down to LOW never wears", attempt(at(5, 0, 1, 1, "top", 100, 6), KS, KSH, "MEDIUM", "HIGH").tiers_after.bottom_frame, 1)
    check("an unfunded defender never wears", attempt(at(5, 0, 1, 1, "top", 100, 2), KS, KSH, "MEDIUM", "HIGH").tiers_after.bottom_frame, 1)
    r = attempt(at(5, 0, 1, 1), FL, KSH, "MEDIUM", "HIGH")
    check("a failed HIGH defense wears", [r.final_grade, r.tiers_after.bottom_frame], [1, 0])
    for commitment: String in ["MEDIUM", "HIGH"]:
        check("a contested defense never wears (%s)" % commitment, attempt(at(5, 0, 1, 1), CF, KSH, "MEDIUM", commitment).tiers_after.bottom_frame, 1)
    r = attempt(at(5, 0, 1, 1), CF, KSH, "MEDIUM", "LOW")
    check("LOW defense is unprepared: the Crossface succeeds and weakens as a builder", [r.final_grade, r.tiers_after.bottom_frame, r.readiness_changes], [2, 0, ["bottom_frame:Partial->None:crossface"]])


func _test_rule_one_and_paid_effort() -> void:
    # [attacker stamina, attacker request, defender stamina, defender request] -> [responder effective, charged, waived, paid, frame after]
    var cases: Array = [
        [[2, "HIGH", 100, "HIGH"], ["HIGH", 0, 12, false, 0]], [[5, "LOW", 100, "HIGH"], ["HIGH", 12, 0, true, 1]],
        [[100, "MEDIUM", 100, "HIGH"], ["HIGH", 12, 0, true, 1]], [[100, "MEDIUM", 11, "HIGH"], ["MEDIUM", 7, 0, true, 0]],
        [[100, "MEDIUM", 7, "HIGH"], ["MEDIUM", 7, 0, true, 0]], [[100, "MEDIUM", 6, "HIGH"], ["LOW", 3, 0, true, 1]],
        [[100, "MEDIUM", 2, "HIGH"], ["", 0, 0, false, 1]], [[2, "MEDIUM", 100, "MEDIUM"], ["MEDIUM", 0, 7, false, 0]],
        [[2, "HIGH", 100, "LOW"], ["LOW", 0, 3, false, 1]],
    ]
    for c: Array in cases:
        var a: Array = c[0]
        var g := at(5, 0, 1, 1, "top", a[0], a[2])
        var r := attempt(g, KS, KSH, a[1], a[3])
        check("Rule 1 case %s" % [a], [r.responder_effective, r.responder_charged, r.responder_waived, r.paid_effort, r.tiers_after.bottom_frame], c[1])
        check("defender stamina after %s" % [a], g.snapshot().fighters[BOTTOM_ID].stamina_current, int(a[2]) - int(c[1][1]))
        check("waived history %s" % [a], g.history_fields().response_waived_history, [c[1][2]])
    var waived := attempt(at(5, 0, 1, 1, "top", 2, 100), KS, KSH, "HIGH", "HIGH")
    var paid := attempt(at(5, 0, 1, 1, "top", 5, 100), KS, KSH, "LOW", "HIGH")
    for key: String in ["grade_after_exhaustion", "grade_after_magnitude", "final_grade", "responder_effective", "undercommitment_modifier"]:
        check("a waiver never changes %s" % key, waived[key], paid[key])
    check("waived HIGH is not preserved, paid HIGH is", [waived.paid_effort, paid.paid_effort, waived.tiers_after.bottom_frame, paid.tiers_after.bottom_frame], [false, true, 0, 1])
    # pass and refusal charge nothing
    var g := gateway()
    g.open_window()
    g.submit(1, TOP_ID)
    check("a pass charges nothing", [g.state_fields().top_stamina, g.state_fields().bottom_stamina], [100, 100])


func _test_exits_and_transitions() -> void:
    var none := {"kind": "none", "raw_destination": "", "destination_position_id": "", "resolved": false}
    for case: Array in [["Side Control", "side_control", 25, 1, "top", KS, HF], ["Open Guard", "open_guard", -25, -2, "bottom", RG, HP], ["Closed Guard", "closed_guard", -15, -1, "bottom", RG, HC]]:
        var g := at(case[2], case[3], 1, 1, case[4])
        var window := g.open_window()
        var report := g.submit(window.values.window_id, window.values.fighter_id, case[5], case[6])
        check("%s exit report" % case[0], report.values.transition, {"kind": "exit", "raw_destination": case[0], "destination_position_id": case[1], "resolved": true})
        check("%s ended" % case[0], [report.values.ended, report.values.state.exit_destination, g.is_terminal()], [true, case[0], true])
        check("%s transition mapping" % case[0], BjjHalfGuardContract.transition_for(case[0]).fields(), report.values.transition)
    var g2 := gateway()
    g2.open_window()
    check("normal exchange transition", g2.submit(1, TOP_ID, CF, HF).values.transition, none)
    g2.open_window()
    check("pass transition", g2.submit(2, BOTTOM_ID).values.transition, none)
    check("window-open report has no transition", g2.open_window().values.has("transition"), false)
    check("an undeclared label would be unresolved", BjjHalfGuardCatalog.transition_fields("Mount"), {"kind": "exit", "raw_destination": "Mount", "destination_position_id": "", "resolved": false})
    # reasons, thresholds and the exit grade
    var r := attempt(at(25, 1, 1, 1), KS, UF)
    check("Strong Success exit reason", [r.final_grade, r.exit_destination], [2, "Side Control"])
    var m := at(25, 1, 1, 1)
    attempt(m, KS, UF)
    check("pass reason text", m.state_fields().exit_reason, "Knee Slice reached the pass line with final grade Strong Success")
    m = at(-25, -2, 1, 1, "bottom")
    attempt(m, RG, HP)
    check("escape reason text", m.state_fields().exit_reason, "Recover Guard reached the escape line with final grade Success")
    check("Open Guard needs exactly Success", [attempt(at(-25, -2, 1, 1, "bottom"), RG, HP).exit_destination, attempt(at(-15, -1, 1, 1, "bottom"), RG, HC).exit_destination], ["Open Guard", "Closed Guard"])
    check("pass line is inclusive", [attempt(at(20, 1, 1, 1), KS, HF).exit_destination, attempt(at(19, 1, 1, 1), KS, HF).exit_destination], ["Side Control", ""])
    check("escape line is inclusive", [attempt(at(-20, -1, 1, 1, "bottom"), RG, HP).exit_destination, attempt(at(-19, -1, 1, 1, "bottom"), RG, HP).exit_destination], ["Open Guard", ""])
    check("a contested or failed break never exits", attempt(at(35, 2, 1, 1), KS, KSH).exit_destination, "")
    check("a non-break success past the line does not exit", attempt(at(35, 2, 1, 1), CF, HF).exit_destination, "")
    r = attempt(at(30, 2, 1, 1), KS, UF)
    check("exit clamps the axis", [r.axis_proposed, r.axis_after, r.band_after], [50, 40, 2])
    r = attempt(at(-20, -1, 1, 1, "bottom"), RG, HC)
    check("exit updates the band", [r.axis_after, r.band_before, r.band_after], [-40, -1, -2])
    # initiative: a normal exchange flips, an exit does not
    var n := at(5, 0, 1, 1)
    attempt(n, KS, HF)
    check("non-exit flips initiative", n._match.initiator, "bottom")
    var x := at(25, 1, 1, 1)
    attempt(x, KS, HF)
    check("exit keeps initiative", x._match.initiator, "top")
    # uniform readiness processing on exits
    r = attempt(at(25, 1, 2, 1), KS, KSH, "HIGH", "LOW")
    check("exit processes consumption", [r.final_grade, r.exit_destination, r.tiers_after, r.readiness_changes], [2, "Side Control", {"top_base": 1, "bottom_frame": 1}, ["top_base:Ready->Partial:knee_slice"]])
    r = attempt(at(-25, -2, 1, 2, "bottom"), RG, HP)
    check("exit processes consumption and weakening", [r.final_grade, r.exit_destination, r.tiers_after, r.readiness_changes],
        [2, "Closed Guard", {"top_base": 0, "bottom_frame": 1}, ["bottom_frame:Ready->Partial:recover_guard", "top_base:Partial->None:recover_guard"]])
    # a finished segment refuses everything and changes nothing
    var t := at(25, 1, 1, 1)
    attempt(t, KS, HF)
    var snapshot := t.snapshot()
    check("terminal attempt", t._match.attempt(CF, HF, "MEDIUM").error, "terminal_exchange")
    check("terminal open", t.open_window().error, "terminal_exchange")
    check("terminal submit", t.submit(1, TOP_ID, CF, HF).error, "no_open_window")
    check("terminal leaves everything", t.snapshot(), snapshot)


# --- Contract, options and views ------------------------------------------------------------------

func _test_contract_and_options() -> void:
    var g := gateway()
    var roles := g.roles()
    check("roles", roles.fields(), {"position_id": "half_guard", "fighter_by_role": {"top": TOP_ID, "bottom": BOTTOM_ID}, "control_authority_id": TOP_ID, "initiative_id": TOP_ID})
    var swapped := BjjHalfGuardWindowGateway.create(entry(100, 100, true)).gateway.roles()
    check("swapped roles", [swapped.fighter_by_role, swapped.control_authority_id, swapped.initiative_id], [{"top": BOTTOM_ID, "bottom": TOP_ID}, BOTTOM_ID, BOTTOM_ID])
    var even := at(0, 0, 1, 1).roles()
    check("no authority at axis 0", even.control_authority_id, "")
    check("negative axis favors the Bottom role", at(-15, -1, 1, 1).roles().control_authority_id, BOTTOM_ID)
    var options := g.action_options(TOP_ID)
    check("top actions", options.fields(), {"options": [{"id": CF, "available": true, "reason": ""}, {"id": FL, "available": true, "reason": ""}, {"id": KS, "available": true, "reason": ""}]})
    check("bottom actions are listed but not available", g.action_options(BOTTOM_ID).fields(), {"options": [
        {"id": UH, "available": false, "reason": "not_initiator"}, {"id": RG, "available": false, "reason": "not_initiator"}]})
    check("menu errors", [g.action_options("").error, g.action_options("ghost").error], ["missing_fighter_id", "unknown_fighter"])
    check("responses for a legal action", g.response_options(CF).available_ids(), [HF, UF, KSH])
    check("responses for an illegal action", [g.response_options(UH).error, g.response_options("nope").error, g.response_options("").error], ["illegal_action", "illegal_action", "illegal_action"])
    check("selected commitment", g.selected_commitment(), "MEDIUM")
    check("commitment options", BjjHalfGuardContract.create(g._match).contract.commitment_options(), ["LOW", "MEDIUM", "HIGH"])
    var contract := BjjHalfGuardContract.create(g._match).contract
    check("declared destinations", contract.transition_destinations(), ["side_control", "open_guard", "closed_guard"])
    check("destination validation", [contract.validate_transition("side_control"), contract.validate_transition("mount"), contract.validate_transition("")],
        ["", "undeclared_transition_destination", "missing_transition_destination"])
    check("identity", [contract.position_id(), contract.fighter_ids()], ["half_guard", [TOP_ID, BOTTOM_ID]])
    # contract addressing precedes the match's own admission
    var before := g.snapshot()
    var command := BjjPositionContract.Command.new
    check("missing command", contract.submit(null).error, "missing_command")
    check("missing position", contract.submit(command.call("", TOP_ID, CF, HF, "MEDIUM", "MEDIUM")).error, "missing_position")
    check("unknown position", contract.submit(command.call("mount", TOP_ID, CF, HF, "MEDIUM", "MEDIUM")).error, "unknown_position")
    check("missing fighter", contract.submit(command.call("half_guard", "", CF, HF, "MEDIUM", "MEDIUM")).error, "missing_fighter_id")
    check("unknown fighter", contract.submit(command.call("half_guard", "ghost", CF, HF, "MEDIUM", "MEDIUM")).error, "unknown_fighter")
    check("not initiator", contract.submit(command.call("half_guard", BOTTOM_ID, UH, HC, "MEDIUM", "MEDIUM")).error, "not_initiator")
    check("addressing precedes shape", contract.submit(command.call("half_guard", BOTTOM_ID, "nope", "nope", "EXTREME", "EXTREME")).error, "not_initiator")
    check("match admission after addressing", contract.submit(command.call("half_guard", TOP_ID, CF, HF, "", "")).error, "invalid_commitment")
    check("contract refusals leave state", g.snapshot(), before)
    var outcome := contract.submit(command.call("half_guard", TOP_ID, CF, HF, "MEDIUM", "MEDIUM"))
    check("contract exchange accepted", [outcome.ok(), outcome.position_id, outcome.exchange.final_grade, outcome.transition.kind, outcome.state.axis_tenths], [true, "half_guard", 1, "none", 15])
    check("missing state", BjjHalfGuardContract.create(null).error, "missing_position_state")
    check("contract identity rule", BjjHalfGuardContract.create(BjjHalfGuardMatch.new()).error, "invalid_fighter_id")


func _test_views_are_detached() -> void:
    var g := gateway()
    g.open_window()
    g.submit(1, TOP_ID, CF, HF)
    var before := g.snapshot()
    var state := g.state_fields()
    state["axis_tenths"] = 999
    state["top_stamina"] = -1
    var history := g.history_fields()
    history["initiated_action_history"].append("tampered")
    history["top_initiation_count"] = 99
    var roles := g.roles()
    roles.fighter_by_role["top"] = "tampered"
    var snapshot := g.snapshot()
    snapshot.fighters[TOP_ID]["stamina_current"] = 0
    snapshot.history["response_history"].clear()
    var report := g.open_window()
    report.values["state"]["axis_tenths"] = 123
    report.values["advance"]["clock_seconds"] = -1
    var window := g.window_fields()
    window["open"] = false
    check("mutating returned views never reaches the match", g.snapshot().duplicate(true).fighters, before.fighters)
    check("history detached", g.history_fields().initiated_action_history, [CF])
    check("roles detached", g.roles().fighter_by_role, {"top": TOP_ID, "bottom": BOTTOM_ID})
    check("window detached", g.window_fields().open, true)
    check("state detached", g.state_fields().axis_tenths, 15)
    var settled := g.submit(2, BOTTOM_ID, UH, HC)
    settled.values.detail.settlement["final_grade"] = 99
    check("report detached", g.history_fields().modified_grade_history, ["Success", "Failure"])
    check("behavior view is constant", g.behavior_fields(), {"top": "", "bottom": ""})
    check("no controller", g.controller_fields(), {})
    check("no carry-over export exists for this position yet", g.has_method("carryover_segment"), false)


func _test_determinism() -> void:
    var plan: Array = [[CF, UF], [UH, HC], [KS, HF], [RG, HP], [FL, KSH], [UH, KP], [CF, HF], [RG, HC]]
    var runs: Array = []
    for pass_index in range(2):
        var g := gateway(entry(60, 45))
        for step: Array in plan:
            var window := g.open_window()
            if window.values.closed:
                break
            var report := g.submit(window.values.window_id, window.values.fighter_id, step[0], step[1], "MEDIUM", "MEDIUM")
            if not report.ok():
                # an action of the other side is refused; pass instead (still deterministic)
                g.submit(window.values.window_id, window.values.fighter_id)
        runs.append(g.snapshot())
    check("the same sequence replays identically", runs[0], runs[1])
    check("the sequence did something", (runs[0].history.initiated_action_history as Array).size() > 3, true)


func _test_scope_and_hygiene() -> void:
    # B1h revised this pin on purpose: the engine sources now contain the explicit feint rules, so "feint" / "Feint" / "surcharge" are no longer
    # forbidden. The sealed-intent protocol and its timeout metadata stay OUTSIDE the engine: "sealed", "seal_intent", "SealedProtocol" and
    # "defaulted" remain forbidden in every engine source.
    var forbidden: Array[String] = ["sealed", "seal_intent", "SealedProtocol", "defaulted", "BjjBehaviorStaminaPolicy.Flow", "BjjD3B", "BjjMount", "BjjMatchWindowGateway.create",
        "randi", "randf", "RandomNumberGenerator", "Time.", "OS.get_ticks", "await", "get_tree", "Engine.get_frames", "FileAccess", "preload("]
    for path: String in SOURCES:
        var file := FileAccess.open(path, FileAccess.READ)
        check("source readable %s" % path, file != null, true)
        var code_lines: Array[String] = []
        for source_line: String in file.get_as_text().split("\n"):
            code_lines.append(source_line.split("#")[0])  # comments may name what the code must not use
        var text := "\n".join(code_lines)
        for token: String in forbidden:
            if token == "BjjMatchWindowGateway.create":
                check("%s does not build a Mount gateway" % path, text.contains(token), false)
            elif token == "BjjMount":
                check("%s never references Mount" % path, text.contains(token), false)
            else:
                check("%s has no %s" % [path, token], text.contains(token), false)
        # the only use of the behavior policy file is the carried Meter type
        for code_line: String in code_lines:
            if code_line.contains("BjjBehaviorStaminaPolicy") and not code_line.contains("BjjBehaviorStaminaPolicy.Meter"):
                check("only the Meter type is used: %s" % code_line.strip_edges(), false, true)
    # reports use the shared Mount-gateway Report type
    check("shared report type", gateway().open_window() is BjjMatchWindowGateway.Report, true)
