extends SceneTree

# Negative-first tests for BjjPositionGraphMatch (Slice A). Rejected commands must leave the
# whole graph unchanged; an accepted exchange that reaches an unsupported destination must be
# kept (settled state equals a bare gateway's after the same operations) and halt the graph.
# The twin is a bare BjjMatchWindowGateway driven with identical operations. Nothing here
# injects state into production objects.
const C = preload("res://scripts/positions/mount/mount_catalog.gd")
const TOP_ID: String = "fighter_alpha"
const BOTTOM_ID: String = "fighter_bravo"
const HALTED: String = "halted_unsupported_transition"

var checks: int = 0
var failures: int = 0
var lockstep_operations: int = 0
var tally: Dictionary = {}

func check(label: String, actual: Variant, expected: Variant) -> void:
    checks += 1
    if actual != expected:
        failures += 1
        if failures <= 25:
            push_error("%s: got %s expected %s" % [label, actual, expected])

func same(label: String, actual: Variant, expected: Variant) -> void:
    checks += 1
    if JSON.stringify(actual, "", true, true) != JSON.stringify(expected, "", true, true):
        failures += 1
        if failures <= 25:
            push_error("%s: structures differ" % label)

func modern_rules() -> Dictionary:
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

func config(rules: Dictionary, extra: Dictionary = {}) -> Dictionary:
    var c := {"rules": rules}
    c.merge(extra, true)
    return c

func graph_of(settings: Dictionary) -> BjjPositionGraphMatch:
    return BjjPositionGraphMatch.create(settings, TOP_ID, BOTTOM_ID).graph

func twin_of(settings: Dictionary) -> BjjMatchWindowGateway:
    return BjjMatchWindowGateway.create(settings, TOP_ID, BOTTOM_ID).gateway

func everything(g: BjjPositionGraphMatch) -> Dictionary:
    return {"state": g.state_fields(), "history": g.history_fields(), "controller": g.controller_fields(),
        "window": g.window_fields(), "status": g.status(), "events": g.events(), "blocked": g.blocked_transition()}

func underlying(g: Variant) -> Dictionary:
    return {"state": g.state_fields(), "history": g.history_fields(), "controller": g.controller_fields(),
        "window": g.window_fields()}

func plain(report: BjjMatchWindowGateway.Report) -> Dictionary:
    var values := report.fields()
    values.erase("graph")
    return values

func kinds(g: BjjPositionGraphMatch) -> Array:
    var result: Array = []
    for event: Dictionary in g.events():
        result.append(event.kind)
    return result

func count_kind(g: BjjPositionGraphMatch, kind: String) -> int:
    return kinds(g).count(kind)

func rejected_submit(label: String, g: BjjPositionGraphMatch, expected_error: String, window_id: int, fighter: String,
        action: String = "", response: String = "", commitment: String = "") -> void:
    var before := everything(g)
    var r := g.submit(window_id, fighter, action, response, commitment)
    check(label + " rejected", r.ok(), false)
    check(label + " error", r.error, expected_error)
    same(label + " graph unchanged", everything(g), before)

func rejected_open(label: String, g: BjjPositionGraphMatch, expected_error: String, duration: Variant = null) -> void:
    var before := everything(g)
    var r := g.open_window_for(duration)
    check(label + " rejected", r.ok(), false)
    check(label + " error", r.error, expected_error)
    same(label + " graph unchanged", everything(g), before)

# Top window -> Top RESET -> Bottom window (zero simulated time), on graph and twin alike.
func to_bottom(g: BjjPositionGraphMatch, t: BjjMatchWindowGateway) -> void:
    var o := g.open_window_for(0)
    var to := t.open_window_for(0)
    check("to_bottom open top", o.ok() and to.ok(), true)
    var r := g.submit(o.values.window_id, TOP_ID)
    var tr := t.submit(to.values.window_id, TOP_ID)
    check("to_bottom reset", r.ok() and tr.ok(), true)
    var b := g.open_window_for(0)
    var tb := t.open_window_for(0)
    check("to_bottom open bottom", b.ok() and tb.ok() and b.values.role == "bottom", true)

# Directed Bottom scenario on a fresh graph and twin. A Trap-and-Roll first needs two Bridge setups
# (Mount's own setup tiers); everything runs through public commands on both sides.
func escape_attempt(rules: Dictionary, axis: float, stamina: int, action: String, response: String) -> Array:
    var settings := config(rules, {"axis": axis, "bottom_stamina": stamina})
    var g := graph_of(settings)
    var t := twin_of(settings)
    to_bottom(g, t)
    var tries := 0
    while action == C.BOTTOM_TRAP_AND_ROLL_ESCAPE and not g.action_options(BOTTOM_ID).available_ids().has(action) and tries < 6:
        tries += 1
        var bridge_response: String = response
        var prep := g.submit(g.window_fields().window_id, BOTTOM_ID, C.BOTTOM_BRIDGE, bridge_response)
        var twin_prep := t.submit(t.window_fields().window_id, BOTTOM_ID, C.BOTTOM_BRIDGE, bridge_response)
        check("prep parity", prep.ok(), twin_prep.ok())
        if not prep.ok() or g.status() != "active":
            return [g, t, prep]
        to_bottom(g, t)
    if not g.action_options(BOTTOM_ID).available_ids().has(action):
        return [g, t, null]
    var report := g.submit(g.window_fields().window_id, BOTTOM_ID, action, response)
    var twin_report := t.submit(t.window_fields().window_id, BOTTOM_ID, action, response)
    check("attempt parity ok", report.ok(), twin_report.ok())
    if report.ok():
        same("attempt report parity", plain(report), plain(twin_report))
    return [g, t, report]

func _initialize() -> void:
    # ---- 1. Creation and delegated admission --------------------------------------------------
    for pair: Array in [["", BOTTOM_ID], [TOP_ID, ""], [TOP_ID, TOP_ID], [" a", "b"]]:
        check("fighter ids %s" % [pair], BjjPositionGraphMatch.create(config(modern_rules()), pair[0], pair[1]).error, "invalid_fighter_id")
    check("production cannot be disabled", BjjPositionGraphMatch.create(config(modern_rules(), {"production": false}), TOP_ID, BOTTOM_ID).error, "production_configuration_required")
    check("raw rules rejected", BjjPositionGraphMatch.create({}, TOP_ID, BOTTOM_ID).ok(), false)
    var fresh := graph_of(config(modern_rules()))
    check("fresh status", fresh.status(), "active")
    check("fresh events empty", fresh.events().size(), 0)
    check("fresh blocked empty", fresh.blocked_transition().is_empty(), true)
    check("one Mount gateway; the Half Guard slot is empty on a default graph (HG-16)", [fresh._gateway is BjjMatchWindowGateway, fresh._half_guard == null, fresh.active_position_id()], [true, true, "mount"])
    var own_properties: Array[String] = []
    for p: Dictionary in fresh.get_property_list():
        if (int(p.usage) & PROPERTY_USAGE_SCRIPT_VARIABLE) != 0:
            own_properties.append(str(p.name))
    own_properties.sort()
    # HG-16 revises this pin: the retained Mount gateway is still the only Mount owner; the typed nullable Half Guard slot, the
    # opt-in receiver table and the cadence are the only additions. B1i revises it again for the opt-in sealed protocol: one typed nullable
    # protocol slot (it adopts the SAME Half Guard gateway) and its opt-in flag.
    check("graph holds gateway, Half Guard slot, sealed protocol slot and flag, receivers, cadence, status, events, blocked, terminal reason", own_properties,
        ["_blocked", "_events", "_gateway", "_half_guard", "_interval_seconds", "_receivers", "_sealed", "_sealed_enabled", "_status", "_terminal_reason"])

    # ---- 2. Rejections leave the whole graph unchanged ---------------------------------------
    var g := graph_of(config(modern_rules()))
    var twin := twin_of(config(modern_rules()))
    rejected_submit("submit before any window", g, "no_open_window", 1, TOP_ID)
    var opened := g.open_window_for(5)
    var twin_opened := twin.open_window_for(5)
    same("open parity", plain(opened), plain(twin_opened))
    check("window_opened event", kinds(g), ["window_opened"])
    rejected_open("duplicate open", g, "window_already_open", 5)
    rejected_open("invalid duration on fresh graph", graph_of(config(modern_rules())), "invalid_duration", "x")
    var id: int = opened.values.window_id
    rejected_submit("stale window", g, "stale_window", id + 1, TOP_ID)
    rejected_submit("unknown fighter", g, "unknown_fighter", id, "fighter_zzz")
    rejected_submit("missing fighter", g, "missing_fighter_id", id, "")
    rejected_submit("wrong initiator", g, "not_initiator", id, BOTTOM_ID)
    rejected_submit("unknown action", g, "unknown_action", id, TOP_ID, "not.an.action", C.TOP_RESPONSE_POST_AND_BASE)
    rejected_submit("bottom action in top window", g, "incorrect_action_side_or_kind", id, TOP_ID, C.BOTTOM_BRIDGE, C.TOP_RESPONSE_POST_AND_BASE)
    var menu := g.action_options(TOP_ID).available_ids()
    var action: String = menu[0]
    var response: String = g.response_options(action).available_ids()[0]
    var accepted := g.submit(id, TOP_ID, action, response)
    var twin_accepted := twin.submit(twin_opened.values.window_id, TOP_ID, action, response)
    check("accepted", accepted.ok(), true)
    same("accepted parity", plain(accepted), plain(twin_accepted))
    check("decision event", kinds(g), ["window_opened", "decision_accepted"])
    rejected_submit("duplicate decision", g, "no_open_window", id, TOP_ID, action, response)
    rejected_submit("replayed old id", g, "no_open_window", id, TOP_ID)
    same("underlying parity after accept", underlying(g), underlying(twin))

    # ---- 3. Accepted exits halt the graph without rolling the exchange back -------------------
    var found: Dictionary = {}
    var rule_sets: Array = [plain_rules(), modern_rules()]
    for rules: Dictionary in rule_sets:
        for axis: float in [0.2, 0.4, 0.8, 1.5, 3.0]:
            for stamina: int in [100, 60]:
                for action_id: String in [C.BOTTOM_ELBOW_KNEE_ESCAPE, C.BOTTOM_TRAP_AND_ROLL_ESCAPE]:
                    for response_id: String in [C.TOP_RESPONSE_POST_AND_BASE, C.TOP_RESPONSE_WIDE_MOUNT_BASE, C.TOP_RESPONSE_HIP_FOLLOW_REPUMMEL]:
                        var run := escape_attempt(rules, axis, stamina, action_id, response_id)
                        var gg: BjjPositionGraphMatch = run[0]
                        if run[2] == null or gg.status() != "halted_at_unsupported_transition":
                            continue
                        var label: String = gg.blocked_transition().label
                        if not found.has(label):
                            found[label] = run
    for label: String in ["Half Guard", "Open Guard", "Reversal"]:
        check("exit scenario found: " + label, found.has(label), true)
    check("no other exit labels reachable", found.size(), 3)
    for label: String in found:
        var gg: BjjPositionGraphMatch = found[label][0]
        var tw: BjjMatchWindowGateway = found[label][1]
        var rep: BjjMatchWindowGateway.Report = found[label][2]
        check(label + " exchange accepted", rep.ok(), true)
        check(label + " status halted", gg.status(), "halted_at_unsupported_transition")
        check(label + " one blocked event", count_kind(gg, "transition_blocked"), 1)
        check(label + " blocked is last", kinds(gg).back(), "transition_blocked")
        check(label + " accepted precedes blocked", kinds(gg).slice(-2), ["decision_accepted", "transition_blocked"])
        var index := 0
        for event: Dictionary in gg.events():
            index += 1
            check(label + " global order %d" % index, event.index, index)
        var blocked := gg.blocked_transition()
        check(label + " blocked from mount", blocked.from_position_id, "mount")
        check(label + " reason", blocked.reason, "unresolved_destination" if label == "Reversal" else "destination_not_implemented")
        check(label + " destination id", blocked.destination_position_id, "" if label == "Reversal" else label.to_snake_case())
        check(label + " no winner or score", blocked.has("winner") or blocked.has("score"), false)
        check(label + " not a terminal outcome", count_kind(gg, "terminal_outcome"), 0)
        # Settled exchange state is kept and equals the bare gateway's after the same operations.
        same(label + " settled state equals bare gateway", underlying(gg), underlying(tw))
        check(label + " exchange not rolled back", gg.history_fields().initiated_action_history.size() > 0, true)
        check(label + " mount settled as exit", gg.state_fields().exit_destination, label)
        # Commands after the halt are rejected without any mutation; reads still work.
        rejected_open(label + " open after halt", gg, HALTED)
        rejected_open(label + " open_for after halt", gg, HALTED, 0)
        rejected_submit(label + " submit after halt", gg, HALTED, gg.window_fields().window_id, BOTTOM_ID, C.BOTTOM_BRIDGE, C.TOP_RESPONSE_POST_AND_BASE)
        rejected_submit(label + " reset after halt", gg, HALTED, 0, TOP_ID)
        check(label + " reads available", gg.state_fields().is_empty(), false)
        # The graph, like the gateway, produces no destination and no outcome.
        check(label + " controller untouched by classification", gg.controller_fields(), tw.controller_fields())

    # ---- 4. Timeout and tap are not positional exits ------------------------------------------
    var timed := graph_of(config(modern_rules(), {"clock": 5, "interval": 5}))
    var last := timed.open_window_for(5)
    check("timeout open ok", last.ok() and last.values.closed, true)
    check("timeout status ended", timed.status(), "ended")
    check("timeout event", kinds(timed), ["terminal_outcome"])
    check("timeout reason", timed.events()[0].reason, "timeout")
    check("timeout is not blocked", timed.blocked_transition().is_empty(), true)
    rejected_open("open after timeout", timed, "terminal_exchange", 0)
    rejected_submit("submit after timeout", timed, "no_open_window", 1, TOP_ID)
    check("terminal reason timeout", BjjPositionGraphMatch.terminal_reason({"clock_seconds": 0, "submission_tapped": false}), "timeout")
    check("terminal reason tap", BjjPositionGraphMatch.terminal_reason({"clock_seconds": 30, "submission_tapped": true}), "tap")
    check("terminal reason none", BjjPositionGraphMatch.terminal_reason({"clock_seconds": 30, "submission_tapped": false}), "")

    # ---- 5. Fail-closed exit classification ---------------------------------------------------
    check("no exit", BjjPositionGraphMatch.classify_exit("").kind, "none")
    check("Half Guard", BjjPositionGraphMatch.classify_exit("Half Guard"), {"kind": "blocked", "reason": "destination_not_implemented", "destination_position_id": "half_guard"})
    check("Open Guard", BjjPositionGraphMatch.classify_exit("Open Guard"), {"kind": "blocked", "reason": "destination_not_implemented", "destination_position_id": "open_guard"})
    check("Reversal", BjjPositionGraphMatch.classify_exit("Reversal"), {"kind": "blocked", "reason": "unresolved_destination", "destination_position_id": ""})
    for label: String in ["Bogus", "half_guard", "mount", "Mount", "Side Control", " Half Guard", "half guard"]:
        check("undeclared label " + label, BjjPositionGraphMatch.classify_exit(label), {"kind": "blocked", "reason": "undeclared_exit_label", "destination_position_id": ""})

    # ---- 5b. Exit while D3-B is armed (reached through real recovery time) --------------------
    var armed_exits := 0
    for start: float in [0.2, 0.4, 0.8]:
        for response_id: String in [C.TOP_RESPONSE_POST_AND_BASE, C.TOP_RESPONSE_WIDE_MOUNT_BASE, C.TOP_RESPONSE_HIP_FOLLOW_REPUMMEL]:
            armed_exits += 1 if armed_exit(response_id, start) else 0
    check("an exit was reached with D3-B armed", armed_exits > 0, true)
    print("armed exits reached: ", armed_exits)

    # ---- 6. Lockstep trajectories against a bare gateway ---------------------------------------
    var signatures: Array[String] = []
    for replay_pass in range(2):
        var run_signature := ""
        for rules: Dictionary in rule_sets:
            for bottom_start: int in [100, 40, 25, 0]:
                for axis: float in [0.4, 1.5, 3.0]:
                    for seed_base in range(1, 4):
                        run_signature += trajectory(rules, bottom_start, axis, seed_base, replay_pass)
        signatures.append(run_signature.sha256_text())
    check("two replays identical", signatures[0], signatures[1])
    check("lockstep saw an exit halt", int(tally.get("halt", 0)) > 0, true)
    check("lockstep saw a timeout", int(tally.get("ended", 0)) > 0, true)
    check("lockstep saw armed and token decisions", int(tally.get("ARMED_NORMAL", 0)) > 0 and int(tally.get("TOKEN", 0)) > 0, true)

    print("lockstep coverage: ", tally)
    print("Position graph native: %d assertions, %d failures; %d lockstep operations" % [checks, failures, lockstep_operations])
    quit(0 if failures == 0 else 1)

func lcg(state: int) -> int:
    return (state * 1103515245 + 12345) & 0x7fffffff

func trajectory(rules: Dictionary, bottom_start: int, axis: float, seed_base: int, replay_pass: int) -> String:
    var label := "traj %d/%s/%d/p%d" % [bottom_start, axis, seed_base, replay_pass]
    var settings := config(rules, {"bottom_stamina": bottom_start, "axis": axis, "clock": 120})
    var g := graph_of(settings)
    var t := twin_of(settings)
    var durations: Array[int] = [0, 1, 5, 7, 30, 5]
    var rng := seed_base * 977 + (1 if rules.has("enable_v02_setup") else 0)
    var log := ""
    for step in range(160):
        rng = lcg(rng)
        var duration: int = durations[rng % durations.size()]
        var opened := g.open_window_for(duration)
        var expected := t.open_window_for(duration)
        check(label + " open parity", opened.ok(), expected.ok())
        if not expected.ok():
            check(label + " open error parity", opened.error, expected.error)
            break
        same(label + " open report parity", plain(opened), plain(expected))
        same(label + " underlying after open", underlying(g), underlying(t))
        lockstep_operations += 1
        if opened.values.closed:
            check(label + " ended status", g.status(), "ended")
            tally["ended"] = int(tally.get("ended", 0)) + 1
            break
        var side: String = opened.values.role
        var fighter := TOP_ID if side == "top" else BOTTOM_ID
        var window_id: int = opened.values.window_id
        rng = lcg(rng)
        var actions := t.action_options(fighter).available_ids()
        var pick_action := rng % 5 != 0
        var action: String = ""
        var response: String = ""
        if pick_action and not actions.is_empty():
            # Bias Bottom toward escape-capable actions so exits are exercised.
            var escapes := actions.filter(func(id: String) -> bool: return id == C.BOTTOM_ELBOW_KNEE_ESCAPE or id == C.BOTTOM_TRAP_AND_ROLL_ESCAPE)
            var pool: Array = escapes if side == "bottom" and not escapes.is_empty() and (rng / 3) % 2 == 0 else actions
            action = pool[(rng / 11) % pool.size()]
            var responses := t.response_options(action).available_ids()
            response = responses[(rng / 7) % responses.size()]
        var report := g.submit(window_id, fighter, action, response)
        var baseline := t.submit(window_id, fighter, action, response)
        check(label + " submit parity", report.ok(), baseline.ok())
        if not baseline.ok():
            check(label + " submit error parity", report.error, baseline.error)
            break
        same(label + " submit report parity", plain(report), plain(baseline))
        same(label + " underlying after submit", underlying(g), underlying(t))
        lockstep_operations += 1
        if side == "bottom":
            var kind: String = str(report.values.detail.decision.kind) + ("/reset" if action == "" else "")
            tally[kind.get_slice("/", 0)] = int(tally.get(kind.get_slice("/", 0), 0)) + 1
        log += "%s|%s|%s;" % [side, action, g.state_fields().clock_seconds]
        if g.status() != "active":
            tally["halt" if g.status() == "halted_at_unsupported_transition" else "ended"] = int(tally.get("halt" if g.status() == "halted_at_unsupported_transition" else "ended", 0)) + 1
            check(label + " halted only on exit", baseline.values.transition.kind, "exit")
            same(label + " controller equals bare gateway at the boundary", g.controller_fields(), t.controller_fields())

            check(label + " one blocked", count_kind(g, "transition_blocked"), 1)
            var blocked_label: String = g.blocked_transition().label
            check(label + " blocked label is the settled exit", blocked_label, g.state_fields().exit_destination)
            var before := everything(g)
            var after := g.submit(window_id, fighter, action, response)
            check(label + " post-halt rejected", after.error, HALTED)
            same(label + " post-halt unchanged", everything(g), before)
            break
    var index := 0
    for event: Dictionary in g.events():
        index += 1
        check(label + " event order", event.index, index)
    log += JSON.stringify(everything(g), "", true, true)
    return log

# Starts Exhausted, lets real simulated time clear the Bottom latch (which arms D3-B), then exits.
# Graph and bare gateway receive identical operations; their controllers must agree before,
# at and after the transition boundary, and the halt must not change either.
func armed_exit(response: String, axis: float) -> bool:
    var label := "armed exit %s/%s" % [axis, response.get_file()]
    var settings := config(modern_rules(), {"bottom_stamina": 0, "axis": axis, "clock": 300})
    var g := graph_of(settings)
    var t := twin_of(settings)
    var exited := false
    for step in range(80):
        if step == 0:
            # Same arrangement the gateway suite uses, applied identically to both sides: Bottom
            # starts Exhausted (observed at creation) and is then set clear, so the next advance
            # sees the Exhausted -> clear edge and arms D3-B. No production hook is involved.
            g._gateway._match.bottom.set_current(40)
            t._match.bottom.set_current(40)
        var seconds := 1 if step == 0 else 0
        var o := g.open_window_for(seconds)
        var to := t.open_window_for(seconds)
        check(label + " open parity", o.ok() == to.ok(), true)
        if not o.ok() or o.values.closed:
            break
        same(label + " controller after open", g.controller_fields(), t.controller_fields())
        var side: String = o.values.role
        var fighter := TOP_ID if side == "top" else BOTTOM_ID
        var id: int = o.values.window_id
        var action := ""
        var answer := ""
        if side == "bottom" and g.controller_fields().armed and not g.state_fields().bottom_band == "Exhausted":
            action = C.BOTTOM_ELBOW_KNEE_ESCAPE
            answer = response
        var r := g.submit(id, fighter, action, answer)
        var tr := t.submit(id, fighter, action, answer)
        check(label + " submit parity", r.ok() == tr.ok(), true)
        if not r.ok():
            break
        same(label + " report parity", plain(r), plain(tr))
        same(label + " controller after decision", g.controller_fields(), t.controller_fields())
        if g.status() != "active":
            exited = true
            check(label + " halted", g.status(), "halted_at_unsupported_transition")
            check(label + " armed at the boundary", g.controller_fields().armed, true)
            same(label + " underlying equals bare gateway", underlying(g), underlying(t))
            var before := g.controller_fields()
            rejected_open(label + " open after halt", g, HALTED, 5)
            same(label + " controller unchanged by halt", g.controller_fields(), before)
            break
    return exited
