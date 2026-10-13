extends SceneTree

# Negative-first match-flow tests for the opt-in sealed Half Guard graph (B1i). The graph COORDINATES match flow; it never prescribes a sequence
# of positions: a match stays in its current position through any number of accepted exchanges, can end there (tap or clock expiry), and only a
# legal, accepted positional exit transitions. Mount and Half Guard keep their own combat mechanics; the sealed protocol (B1g/B1h) owns the Half
# Guard seal / respond / reveal workflow and operates on the graph's OWN Half Guard gateway (adopted, never a second simulation).
# Every Mount run here is a REAL run through the public gateway API (no injected state). Expected values are literals, come from a twin driven
# through the bare Mount gateway / an independently created qualified protocol with the same entry and commands, or come from the oracle
# fixtures; the graph is never compared with itself except for the deliberate replay checks. The only private reads are read-only (the retained
# Mount gateway, the Half Guard slot, the adopted protocol slot), which is how the single-owner invariants are observed.
const C = preload("res://scripts/positions/mount/mount_catalog.gd")
const TOP: String = "fighter_alpha"
const BOTTOM: String = "fighter_bravo"
const HALTED: String = "halted_unsupported_transition"
const STATUS_HALTED: String = "halted_at_unsupported_transition"
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
const DIRECT_FIXTURE: String = "res://tests/generated/half_guard_reference.jsonl"
const FEINT_FIXTURE: String = "res://tests/generated/half_guard_feint_reference.jsonl"
# The digests the generators print (the file bytes ARE the digested bytes): B1g's direct fixture and B1h's feint fixture.
const DIRECT_FIXTURE_SHA256: String = "62da68057bcb427fb4d356a4af95907d39e1e4394529779b9373da01c3a517fb"
const FEINT_FIXTURE_SHA256: String = "4842c85d905aa6efce45e4698759cde3e9e7f145cd805b77c67a343d3a8f5bc7"

var checks: int = 0
var failures: int = 0
var plans: Array = []            # real Mount -> Half Guard exit plans
var open_guard_plan: Dictionary = {}


func check(label: String, actual: Variant, expected: Variant) -> void:
    checks += 1
    if typeof(actual) != typeof(expected) or JSON.stringify(actual, "", true, true) != JSON.stringify(expected, "", true, true):
        failures += 1
        if failures <= 40:
            push_error("%s: got %s expected %s" % [label, JSON.stringify(actual).left(500), JSON.stringify(expected).left(500)])


# ---- Construction ---------------------------------------------------------------------------------------------------------------------

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


func config_of(plan: Dictionary) -> Dictionary:
    var configuration := {"rules": plain_rules() if plan.rule_set == "plain" else rules()}
    configuration.merge(plan.config, true)
    return configuration


func make_sealed(plan: Dictionary, receivers: Variant = null) -> BjjPositionGraphMatch:
    var created := BjjPositionGraphMatch.create_with_sealed_half_guard(config_of(plan), TOP, BOTTOM, receivers)
    check("sealed graph built", [created.ok(), created.error], [true, ""])
    return created.graph


func make_default(plan: Dictionary) -> BjjPositionGraphMatch:
    return BjjPositionGraphMatch.create(config_of(plan), TOP, BOTTOM).graph


func make_b1d(plan: Dictionary) -> BjjPositionGraphMatch:
    return BjjPositionGraphMatch.create_with_receivers(config_of(plan), TOP, BOTTOM, BjjPositionGraphMatch.default_receivers()).graph


func make_bare(plan: Dictionary) -> BjjMatchWindowGateway:
    return BjjMatchWindowGateway.create(config_of(plan), TOP, BOTTOM).gateway


# ---- Views and fingerprints ------------------------------------------------------------------------------------------------------------

func mount_views(gateway: BjjMatchWindowGateway) -> Dictionary:
    return {"state": gateway.state_fields(), "history": gateway.history_fields(), "controller": gateway.controller_fields(), "window": gateway.window_fields(),
        "behavior": gateway.behavior_fields(), "roles": gateway.roles().fields(), "terminal": gateway.is_terminal(), "commitment": gateway.selected_commitment(),
        "segment": gateway.carryover_segment().record}


func graph_views(g: BjjPositionGraphMatch) -> Dictionary:
    return {"status": g.status(), "events": g.events(), "blocked": g.blocked_transition(), "active": g.active_position_id(), "state": g.state_fields(),
        "history": g.history_fields(), "controller": g.controller_fields(), "window": g.window_fields(), "behavior": g.behavior_fields(),
        "roles": g.roles().fields(), "commitment": g.selected_commitment(), "export_error": g.carryover_export().error,
        "public_events": g.sealed_public_events()}


# Everything authoritative: the graph, the retained Mount segment, the Half Guard gateway and the adopted protocol's executor state.
func everything(g: BjjPositionGraphMatch) -> Dictionary:
    var all := graph_views(g)
    all["mount"] = mount_views(g._gateway)
    all["half_guard"] = g._half_guard.snapshot() if g._half_guard != null else {}
    all["protocol"] = g._sealed.executor_snapshot() if g._sealed != null else {}
    return all


func strip(report: BjjMatchWindowGateway.Report) -> Dictionary:
    var values := report.values.duplicate(true)
    values.erase("graph")
    return {"error": report.error, "values": values}


func event_kinds(g: BjjPositionGraphMatch) -> Array:
    return g.events().map(func(e: Dictionary) -> String: return str(e.kind))


func refused(label: String, g: BjjPositionGraphMatch, report: BjjMatchWindowGateway.Report, code: String, before: Dictionary) -> void:
    check(label + " is refused", report.ok(), false)
    check(label + " code", report.error, code)
    check(label + " carries no values", report.values.is_empty(), true)
    check(label + " leaves the whole authoritative graph and protocol state unchanged", everything(g), before)


# Exactly one active position and exactly one simulation owner; the adopted protocol drives THE graph's gateway (same object), never a copy.
func single_owner(label: String, g: BjjPositionGraphMatch) -> void:
    var active := g.active_position_id()
    check(label + ": the active position is one of the two", ["mount", "half_guard"].has(active), true)
    check(label + ": the active position agrees with the Half Guard slot", g._half_guard != null, active == "half_guard")
    check(label + ": the protocol slot is set exactly when Half Guard is active on a sealed graph", g._sealed != null, active == "half_guard" and g._sealed_enabled)
    if g._sealed != null:
        check(label + ": the protocol drives the graph's own gateway object", g._sealed._gateway == g._half_guard, true)
        check(label + ": the protocol's simulation snapshot is the gateway's", g._sealed.snapshot(), g._half_guard.snapshot())
        check(label + ": the gateway is claimed by exactly that protocol", [g._half_guard._protocol_claimed, g._sealed.is_adopted()], [true, true])
        check(label + ": no second protocol can adopt the gateway", BjjHalfGuardSealedProtocol.adopt(g._half_guard).error in ["gateway_already_attached", "gateway_not_idle"], true)
    if g._half_guard != null:
        check(label + ": the retained Mount segment is terminal history, never a second owner", [g._gateway.is_terminal(), g._gateway.window_fields().open], [true, false])
        check(label + ": a frozen Mount segment accepts no window", g._gateway.open_window_for(0).ok(), false)


# ---- Directed real Mount runs (the B1d plan builder) ----------------------------------------------------------------------------------------

func run_plan(target: Variant, plan: Dictionary) -> Dictionary:
    var trace: Array = []
    var out := {"trace": trace, "exited": false}
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
    var exit_report: BjjMatchWindowGateway.Report = target.submit(target.window_fields().window_id, BOTTOM, plan.action, plan.response)
    trace.append(strip(exit_report))
    out.exited = exit_report.ok() and str(exit_report.values.transition.raw_destination) == plan.label
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
                                    if plans.size() >= 5 and not open_guard_plan.is_empty():
                                        return
                                    var plan := {"rule_set": rule_set, "config": {"axis": axis, "top_stamina": top_stamina, "bottom_stamina": bottom_stamina, "interval": interval},
                                        "action": action_id, "response": response_id, "rounds": rounds, "label": "Half Guard"}
                                    var bare := make_bare(plan)
                                    run_plan(bare, plan)
                                    var label: String = bare.state_fields().exit_destination
                                    if label.is_empty():
                                        continue
                                    plan.label = label
                                    var signature := JSON.stringify(bare.carryover_segment().record) + label
                                    if seen.has(signature):
                                        continue
                                    seen[signature] = true
                                    if label == "Half Guard" and plans.size() < 5:
                                        plans.append(plan)
                                    elif label == "Open Guard" and open_guard_plan.is_empty():
                                        open_guard_plan = plan


# A sealed graph taken through the real Mount exit into Half Guard; also returns the bare twin's Mount record for the continuity checks.
func entered(plan: Dictionary) -> Dictionary:
    var g := make_sealed(plan)
    var bare := make_bare(plan)
    run_plan(bare, plan)
    var run := run_plan(g, plan)
    check("the real Mount run exits to Half Guard", [run.exited, g.active_position_id()], [true, "half_guard"])
    return {"graph": g, "bare": bare, "record": bare.carryover_segment().record, "interval": int(plan.config.interval)}


# The independently driven qualified B1h protocol receiving the same entry the edge adapter builds from the same Mount record.
func twin_protocol(record: Dictionary, interval: int) -> BjjHalfGuardSealedProtocol:
    var edge := BjjHalfGuardMountEdge.entry_from_record(record.duplicate(true), interval)
    check("the edge accepts the real record", edge.ok(), true)
    return BjjHalfGuardSealedProtocol.create(edge.request).protocol


func _initialize() -> void:
    find_plans()
    check("several real Half Guard exit plans were found", plans.size() >= 4, true)
    check("a real Open Guard exit plan was found", open_guard_plan.is_empty(), false)
    if plans.size() < 4 or open_guard_plan.is_empty():
        push_error("Half Guard graph sealed flow: required real Mount exits were not reached")
        quit(1)
        return
    _test_construction()
    _test_admission_refusals()
    _test_mount_stays_active()
    _test_mount_ends_without_a_transition()
    _test_mount_to_half_guard_entry()
    _test_half_guard_direct_flow()
    _test_half_guard_feints()
    _test_half_guard_timeout_fallback()
    _test_half_guard_exits_unsupported_and_terminal()
    _test_sealed_refusals_and_adversarial_boundaries()
    _test_attachment_failures_halt_without_partial_activation()
    _test_replay_determinism()
    _test_fixtures_and_unchanged_surfaces()
    _test_scope_and_hygiene()
    if failures > 0:
        push_error("Half Guard graph sealed flow: %d / %d assertions failed" % [failures, checks])
        quit(1)
        return
    print("Half Guard graph sealed flow PASS: %d assertions" % checks)
    quit(0)


# ---- 1. Construction and admission (negative first) --------------------------------------------------------------------------------------

func _test_construction() -> void:
    var plan: Dictionary = plans[0]
    var good := Callable(self, "_receiver_two_arguments")
    for table: Array in [["empty table (no way into Half Guard)", {}], ["int", 5], ["string", "half_guard"], ["array", [good]], ["unknown key", {"open_guard": good}],
            ["valid plus unknown key", {"half_guard": good, "open_guard": good}], ["null value", {"half_guard": null}], ["one argument", {"half_guard": Callable(self, "_receiver_one_argument")}],
            ["empty callable", {"half_guard": Callable()}]]:
        var created := BjjPositionGraphMatch.create_with_sealed_half_guard(config_of(plan), TOP, BOTTOM, table[1])
        check("%s builds no sealed graph" % table[0], [created.ok(), created.error, created.graph == null], [false, "invalid_receivers", true])
    for configuration: Dictionary in [{}, {"rules": rules(), "production": false}, {"rules": rules(), "clock": 0}, {"rules": rules(), "unknown": 1}]:
        var plain := BjjPositionGraphMatch.create(configuration, TOP, BOTTOM)
        var sealed := BjjPositionGraphMatch.create_with_sealed_half_guard(configuration, TOP, BOTTOM)
        check("configuration error equals create's for %s" % [configuration.keys()], [sealed.error, sealed.graph == null], [plain.error, plain.graph == null])
    var g := make_sealed(plan)
    check("a sealed graph starts Mount-active with no Half Guard and no protocol", [g.active_position_id(), g._half_guard == null, g._sealed == null, g.sealed_protocol_enabled(),
        g.status()], ["mount", true, true, true, "active"])
    check("a custom valid table is accepted", BjjPositionGraphMatch.create_with_sealed_half_guard(config_of(plan), TOP, BOTTOM, {"half_guard": good}).ok(), true)
    for builder: Array in [["default", make_default(plan)], ["B1d opt-in", make_b1d(plan)]]:
        check("%s graph did not opt in to the sealed protocol" % builder[0], (builder[1] as BjjPositionGraphMatch).sealed_protocol_enabled(), false)


func _receiver_two_arguments(record: Dictionary, interval_seconds: int) -> BjjHalfGuardWindowGateway.Creation:
    return BjjPositionGraphMatch.default_receivers()["half_guard"].call(record, interval_seconds)


func _receiver_one_argument(record: Dictionary) -> BjjHalfGuardWindowGateway.Creation:
    return null


# Every sealed graph method refuses before anything is forwarded; the code names why; the whole authoritative state is unchanged.
func _sealed_calls(g: BjjPositionGraphMatch) -> Array:
    return [["seal_intent", g.seal_intent(1, TOP, CF, "MEDIUM")], ["seal_intent (feint)", g.seal_intent(1, TOP, CF, "MEDIUM", KS)], ["public_intent_view", g.public_intent_view()],
        ["sealed_intent_view", g.sealed_intent_view(TOP)], ["respond", g.respond(1, BOTTOM, 1, HF, "MEDIUM")], ["apply_response_timeout", g.apply_response_timeout(1, 1, HF, "LOW")]]


func _test_admission_refusals() -> void:
    var plan: Dictionary = plans[0]
    # Mount active: wrong position on a sealed graph, not enabled on the others
    var sealed_mount := make_sealed(plan)
    var before := everything(sealed_mount)
    for call: Array in _sealed_calls(sealed_mount):
        refused("Mount active, sealed graph: %s" % call[0], sealed_mount, call[1], "wrong_active_position", before)
    check("Mount active, sealed graph: the public protocol events are empty", sealed_mount.sealed_public_events(), [])
    for builder: Array in [["default", make_default(plan)], ["B1d opt-in", make_b1d(plan)]]:
        var g: BjjPositionGraphMatch = builder[1]
        var snapshot := everything(g)
        for call: Array in _sealed_calls(g):
            refused("%s graph: %s" % [builder[0], call[0]], g, call[1], "sealed_protocol_not_enabled", snapshot)
    # a B1d opt-in graph that REACHED Half Guard still has no sealed methods enabled
    var b1d := make_b1d(plan)
    run_plan(b1d, plan)
    check("the B1d opt-in graph reached Half Guard", b1d.active_position_id(), "half_guard")
    var b1d_before := everything(b1d)
    for call: Array in _sealed_calls(b1d):
        refused("B1d opt-in graph in Half Guard: %s" % call[0], b1d, call[1], "sealed_protocol_not_enabled", b1d_before)
    check("and has no protocol slot", [b1d._sealed == null, b1d.sealed_public_events()], [true, []])
    # halted (the default graph halts at the first Mount exit; so does a sealed graph at an unsupported Mount exit)
    var halted_default := make_default(plan)
    run_plan(halted_default, plan)
    var halted_before := everything(halted_default)
    for call: Array in _sealed_calls(halted_default):
        refused("a halted graph: %s" % call[0], halted_default, call[1], HALTED, halted_before)
    var halted_sealed := make_sealed(open_guard_plan)
    run_plan(halted_sealed, open_guard_plan)
    check("a sealed graph halts at an unsupported Mount exit (Open Guard has no receiver)", [halted_sealed.status(), halted_sealed.active_position_id(), halted_sealed._sealed == null],
        [STATUS_HALTED, "mount", true])
    var halted_sealed_before := everything(halted_sealed)
    for call: Array in _sealed_calls(halted_sealed):
        refused("a halted sealed graph: %s" % call[0], halted_sealed, call[1], HALTED, halted_sealed_before)
    # ended: a Mount clock expiry
    var ended := BjjPositionGraphMatch.create_with_sealed_half_guard({"rules": rules(), "clock": 5, "interval": 5}, TOP, BOTTOM).graph
    check("the Mount clock ends the match", [ended.open_window_for(5).values.closed, ended.status()], [true, "ended"])
    var ended_before := everything(ended)
    for call: Array in _sealed_calls(ended):
        refused("an ended match: %s" % call[0], ended, call[1], "match_ended", ended_before)
    # precedence: halted beats ended beats not-enabled beats wrong-position (a halted sealed graph is also Mount-active)
    check("halted outranks wrong position", halted_sealed.seal_intent(1, TOP, CF).error, HALTED)
    check("ended outranks wrong position", ended.seal_intent(1, TOP, CF).error, "match_ended")
    check("not enabled outranks wrong position", make_default(plan).seal_intent(1, TOP, CF).error, "sealed_protocol_not_enabled")
    check("the sealed methods never revealed a protocol event", [ended.sealed_public_events(), halted_sealed.sealed_public_events()], [[], []])


# ---- 2. A. Staying in Mount: no position is forced ---------------------------------------------------------------------------------------

func _test_mount_stays_active() -> void:
    var plan := {"rule_set": "modern", "config": {"axis": 1.5}, "label": "", "rounds": 0, "action": "", "response": ""}
    var g := make_sealed(plan)
    var twin := make_bare(plan)
    var windows := 0
    var accepted := 0
    var checkpoints := [10, 20, 30, 40, 50]
    for index in range(50):
        var opened := g.open_window_for(0)
        var opened_twin := twin.open_window_for(0)
        check("window %d report equals the bare gateway's" % index, strip(opened), strip(opened_twin))
        if not opened.ok() or opened.values.get("closed", false):
            break
        windows += 1
        var role := str(opened.values.role)
        var fighter_id := str(opened.values.fighter_id)
        var report: BjjMatchWindowGateway.Report
        var report_twin: BjjMatchWindowGateway.Report
        if role == "top" and index % 3 == 0:
            # a REAL exchange: Top's first available non-finishing technique against its first available response
            var ids := g.action_options(TOP).available_ids().filter(func(id: String) -> bool: return not id.contains("finish"))
            var pick: String = ids[0]
            var response: String = g.response_options(pick).available_ids()[0]
            report = g.submit(int(opened.values.window_id), fighter_id, pick, response, "MEDIUM", "MEDIUM")
            report_twin = twin.submit(int(opened.values.window_id), fighter_id, pick, response, "MEDIUM", "MEDIUM")
        else:
            report = g.submit(int(opened.values.window_id), fighter_id)
            report_twin = twin.submit(int(opened.values.window_id), fighter_id)
        check("decision %d report equals the bare gateway's" % index, strip(report), strip(report_twin))
        if not report.ok() or str(report.values.transition.raw_destination) != "":
            check("the straight run never exited (it is a stay-in-Mount scenario)", [report.ok(), report.values.get("transition", {})], [true, {}])
            break
        accepted += 1
        check("window %d: Mount is still the active position" % index, [g.active_position_id(), g.status(), g._half_guard == null, g._sealed == null], ["mount", "active", true, true])
        if checkpoints.has(index + 1):
            check("after %d windows no transition appeared" % (index + 1), event_kinds(g).filter(func(k: String) -> bool: return k.begins_with("transition")), [])
    check("a long run of accepted exchanges was driven", windows >= 40 and accepted == windows, true)
    # each exchange settled exactly once: one window_opened and one decision_accepted per window, nothing else
    var kinds := event_kinds(g)
    var expected_kinds: Array = []
    for i in range(windows):
        expected_kinds.append("window_opened")
        expected_kinds.append("decision_accepted")
    check("exactly one window and one accepted decision per exchange, no transition, no terminal", kinds, expected_kinds)
    check("event indices are monotonic from 1", g.events().map(func(e: Dictionary) -> int: return int(e.index)), range(1, expected_kinds.size() + 1))
    check("state, history, controller, window and behavior equal the bare gateway's", [g.state_fields(), g.history_fields(), g.controller_fields(), g.window_fields(), g.behavior_fields()],
        [twin.state_fields(), twin.history_fields(), twin.controller_fields(), twin.window_fields(), twin.behavior_fields()])
    check("roles and the carry-over segment equal the bare gateway's", [g.roles().fields(), g._gateway.carryover_segment().record], [twin.roles().fields(), twin.carryover_segment().record])
    check("no Half Guard receiver or protocol was activated", [g._half_guard == null, g._sealed == null, g.sealed_public_events()], [true, true, []])
    check("the match is still playable", [g.status(), g.state_fields().ended], ["active", false])


# ---- 3. B. A match may END in Mount without transitioning -------------------------------------------------------------------------------------

func tap_run(g: BjjPositionGraphMatch) -> bool:
    for index in range(60):
        var opened := g.open_window_for(0)
        if not opened.ok() or g.status() != "active" or opened.values.get("closed", false):
            return false
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
            return false
        if g.state_fields().submission_tapped:
            return true
    return false


func _test_mount_ends_without_a_transition() -> void:
    var tap_plan := {"rule_set": "modern", "config": {"axis": 1.5}, "label": "", "rounds": 0, "action": "", "response": ""}
    # (i) a genuine legal submission: the existing engine taps and the graph reports the existing terminal reason
    var sealed := make_sealed(tap_plan)
    var default := make_default(tap_plan)
    check("a real tap was reached on the sealed graph", tap_run(sealed), true)
    check("and on the default graph with the same commands", tap_run(default), true)
    check("the match ended in Mount by the tap", [sealed.status(), sealed.active_position_id(), sealed.state_fields().submission_tapped], ["ended", "mount", true])
    check("the sealed graph's whole record equals the default graph's (events, state, history, controller)", graph_views(sealed), graph_views(default))
    check("the terminal outcome is the existing reason, not an exit", [sealed.events().back().kind, sealed.events().back().reason], ["terminal_outcome", "tap"])
    check("the terminal report carries no winner, score or adjudication field", sealed.events().back().keys(), ["kind", "reason", "index"])
    check("no transition event and nothing blocked", [event_kinds(sealed).filter(func(k: String) -> bool: return k.begins_with("transition")), sealed.blocked_transition()], [[], {}])
    check("no Half Guard simulation or protocol was activated by the end of the match", [sealed._half_guard == null, sealed._sealed == null], [true, true])
    var tapped_before := everything(sealed)
    for call: Array in _sealed_calls(sealed):
        refused("after the Mount tap: %s" % call[0], sealed, call[1], "match_ended", tapped_before)
    refused("a legacy submit after the Mount tap", sealed, sealed.submit(1, TOP, CF, HF), "no_open_window", tapped_before)
    refused("a legacy pass after the Mount tap", sealed, sealed.submit(1, TOP), "no_open_window", tapped_before)
    # (ii) the match clock expires in Mount (real open_window_for on a short clock)
    var timed := BjjPositionGraphMatch.create_with_sealed_half_guard({"rules": rules(), "clock": 20, "interval": 5}, TOP, BOTTOM).graph
    var twin := BjjMatchWindowGateway.create({"rules": rules(), "clock": 20, "interval": 5}, TOP, BOTTOM).gateway
    for index in range(3):
        var opened := timed.open_window()
        check("window %d of the short clock opens like the bare gateway's" % index, strip(opened), strip(twin.open_window()))
        check("window %d: pass settles like the bare gateway's" % index, strip(timed.submit(int(opened.values.window_id), str(opened.values.fighter_id))),
            strip(twin.submit(int(opened.values.window_id), str(opened.values.fighter_id))))
        check("window %d: still Mount, still active" % index, [timed.active_position_id(), timed.status()], ["mount", "active"])
    var closing := timed.open_window()
    var closing_twin := twin.open_window()
    check("the closing window equals the bare gateway's", strip(closing), strip(closing_twin))
    check("the clock ended the match in Mount", [closing.values.closed, timed.status(), timed.active_position_id(), timed._half_guard == null, timed._sealed == null],
        [true, "ended", "mount", true, true])
    check("the existing terminal outcome is a timeout, not an exit", [timed.events().back().kind, timed.events().back().reason, timed.events().back().keys()],
        ["terminal_outcome", "timeout", ["kind", "reason", "index"]])
    check("the clock end produced no positional transition", [event_kinds(timed).filter(func(k: String) -> bool: return k.begins_with("transition")), timed.blocked_transition()], [[], {}])
    var timed_before := everything(timed)
    for call: Array in _sealed_calls(timed):
        refused("after the Mount clock expiry: %s" % call[0], timed, call[1], "match_ended", timed_before)
    check("the legacy path after the end is the gateway's own refusal and appends nothing", [timed.open_window().error, timed.events().size()], ["terminal_exchange", timed_before.events.size()])
    refused("a legacy submit after the Mount clock expiry", timed, timed.submit(1, TOP, CF, HF), "no_open_window", timed_before)


# ---- 4. C. Mount -> Half Guard: entry and continuity --------------------------------------------------------------------------------------

func _test_mount_to_half_guard_entry() -> void:
    for plan: Dictionary in plans:
        var run := entered(plan)
        var g: BjjPositionGraphMatch = run.graph
        var record: Dictionary = run.record
        var bare: BjjMatchWindowGateway = run.bare
        var kinds := event_kinds(g)
        var tail := kinds.slice(kinds.size() - 3)
        check("the transition sequence is window_opened, decision_accepted, transition_committed (nothing in between or after)", tail, ["window_opened", "decision_accepted", "transition_committed"])
        check("exactly one transition event and no halt", [kinds.count("transition_committed"), kinds.count("transition_blocked"), g.status(), g.blocked_transition()], [1, 0, "active", {}])
        check("the committed event names the real exit", g.events().back(), {"kind": "transition_committed", "from_position_id": "mount", "to_position_id": "half_guard", "label": "Half Guard",
            "index": kinds.size()})
        check("global event indices are monotonic from 1", g.events().map(func(e: Dictionary) -> int: return int(e.index)), range(1, kinds.size() + 1))
        single_owner("after entry", g)
        # the sealed protocol is fresh and idle on THE graph's own gateway; nothing was settled by attaching it
        var executor := g._sealed.executor_snapshot()
        check("the protocol starts idle: no pending seal, no serial, no events, not closed", [executor.pending, executor.serial, executor.events, executor.closed], [{}, 0, [], false])
        check("the public protocol events are empty", g.sealed_public_events(), [])
        # identity, resources, clock and window continuity against the Mount record (the bare twin of the same real run)
        var snapshot := g._half_guard.snapshot()
        check("fighter identity and roles are preserved", [snapshot.role_map, g.roles().fields().fighter_by_role], [{"top": TOP, "bottom": BOTTOM}, {"top": TOP, "bottom": BOTTOM}])
        for id: String in [TOP, BOTTOM]:
            var role := "top" if id == TOP else "bottom"
            var carried: Dictionary = record.fighters[role]
            check("%s: stamina, exhaustion latch and behavior meter are carried exactly" % id, snapshot.fighters[id], {"stamina_current": carried.stamina_current,
                "stamina_maximum": carried.stamina_maximum, "exhaustion_latched": carried.exhaustion_latched, "behavior_remainder_units": carried.behavior_remainder_units})
        check("the match clock and the window counter continue (no second advance, no new window)", [snapshot.clock_seconds, snapshot.initial_clock, snapshot.window_id, snapshot.window_open],
            [record.clock.remaining_seconds, record.clock.initial_seconds, record.window.last_issued_id, false])
        check("Half Guard has its own entry axis, band, readiness and initiative", [snapshot.axis_tenths, snapshot.band, snapshot.top_base, snapshot.bottom_frame, snapshot.initiator,
            snapshot.history == BjjHalfGuardMatch.empty_history()], [5, 0, 1, 1, "top", true])
        check("nothing was charged or granted by the transition: the first Half Guard window is still to be opened", [g.window_fields().open, g.window_fields().fighter_id], [false, ""])
        # the retained Mount segment equals the bare twin's final Mount state and is frozen from now on
        var frozen := mount_views(g._gateway)
        check("the retained Mount segment equals the bare gateway's after the same real run", frozen, mount_views(bare))
        check("the legacy export is refused (no v2 envelope exists)", g.carryover_export().error, "carryover_unsupported_position")
        # the first window opens only on an explicit call, with the next id, for the Top
        var opened := g.open_window()
        check("the first Half Guard window opens on request with the next window id for the Top", [opened.ok(), opened.values.window_id, opened.values.fighter_id, opened.values.role],
            [true, int(record.window.last_issued_id) + 1, TOP, "top"])
        check("opening it appended exactly one window_opened", event_kinds(g).slice(kinds.size()), ["window_opened"])
        check("the retained Mount segment did not change when Half Guard opened a window", mount_views(g._gateway), frozen)
        single_owner("after the first Half Guard window", g)


# A reusable lockstep driver: the graph and an independently created qualified protocol receive the same commands; every observable surface is
# compared after each step. `steps` use window roles from the opened window; the twin never sees the graph.
func drive(g: BjjPositionGraphMatch, twin: BjjHalfGuardSealedProtocol, steps: Array, tag: String) -> void:
    for index in range(steps.size()):
        var step: Dictionary = steps[index]
        var label := "%s step %d (%s)" % [tag, index, step.k]
        var events_before := g.events().size()
        var opened := g.open_window()
        var opened_twin := twin.open_window()
        check(label + " open report equals the twin's", strip(opened), strip(opened_twin))
        if not opened.ok() or opened.values.get("closed", false):
            return
        var window_id := int(opened.values.window_id)
        var fighter_id := str(opened.values.fighter_id)
        var responder_id := BOTTOM if fighter_id == TOP else TOP
        var clock_after_open := int(g.state_fields().clock_seconds)
        var accepted := 0
        match str(step.k):
            "direct":
                var report := g.submit(window_id, fighter_id, str(step.a), str(step.r), str(step.c), str(step.rc))
                var twin_report := twin.submit(window_id, fighter_id, str(step.a), str(step.r), str(step.c), str(step.rc))
                check(label + " report equals the twin's", strip(report), strip(twin_report))
                accepted = 1 if report.ok() else 0
            "pass":
                check(label + " report equals the twin's", strip(g.submit(window_id, fighter_id)), strip(twin.submit(window_id, fighter_id)))
                accepted = 1
            "feint", "sealed", "timeout":
                var real := str(step.get("real", ""))
                var seal := g.seal_intent(window_id, fighter_id, str(step.a), str(step.c), real)
                var twin_seal := twin.seal_intent(window_id, fighter_id, str(step.a), str(step.c), real)
                check(label + " the seal report (the public view) equals the twin's", strip(seal), strip(twin_seal))
                check(label + " the seal was accepted", seal.error, "")
                if not seal.ok():
                    return
                check(label + " a seal is not a combat exchange: no graph event, no state change", [g.events().size(), g.window_fields().open], [events_before + 1, true])
                check(label + " the graph's public view equals the twin's", strip(g.public_intent_view()), strip(twin.public_intent_view()))
                check(label + " the public protocol events equal the twin's and carry no real technique", [g.sealed_public_events(), g.sealed_public_events().filter(
                    func(e: Dictionary) -> bool: return e.has("real_action_id"))], [twin.public_events(), []])
                check(label + " the initiator reads its own seal", strip(g.sealed_intent_view(fighter_id)), strip(twin.sealed_intent_view(fighter_id)))
                var serial := int(seal.values.intent_serial)
                var done: BjjMatchWindowGateway.Report
                var twin_done: BjjMatchWindowGateway.Report
                if str(step.k) == "timeout":
                    var published := BjjHalfGuardCatalog.timeout_fallback("bottom" if responder_id == BOTTOM else "top")
                    done = g.apply_response_timeout(window_id, serial, str(published.response_id), str(published.commitment))
                    twin_done = twin.apply_response_timeout(window_id, serial, str(published.response_id), str(published.commitment))
                else:
                    done = g.respond(window_id, responder_id, serial, str(step.r), str(step.rc))
                    twin_done = twin.respond(window_id, responder_id, serial, str(step.r), str(step.rc))
                check(label + " the resolved report equals the twin's", strip(done), strip(twin_done))
                accepted = 1 if done.ok() else 0
        # exactly one accepted graph decision, one window, no extra clock advance, the same simulation as the twin
        var new_kinds := event_kinds(g).slice(events_before)
        check(label + " the graph recorded one window and one accepted decision (plus at most one transition event)", new_kinds.slice(0, 2), ["window_opened", "decision_accepted"] if accepted == 1 else ["window_opened"])
        check(label + " the clock did not advance after the window opened", g.state_fields().clock_seconds, clock_after_open)
        check(label + " the graph's Half Guard simulation equals the twin's", g._half_guard.snapshot(), twin.snapshot())
        check(label + " the graph's views equal the twin's", [g.state_fields(), g.history_fields(), g.window_fields(), g.roles().fields()],
            [twin.state_fields(), twin.history_fields(), twin.window_fields(), twin.roles().fields()])
        check(label + " the protocol executor state equals the twin's", g._sealed.executor_snapshot(), twin.executor_snapshot())
        if g.status() == "active":
            single_owner(label, g)
        else:
            return


func _test_half_guard_direct_flow() -> void:
    # direct Half Guard exchanges through the graph's legacy submit (routed through the adopted protocol), compared with the independent twin;
    # the position is kept through many exchanges (no automatic transition); the retained Mount segment never changes
    for plan: Dictionary in plans.slice(0, 3):
        var run := entered(plan)
        var g: BjjPositionGraphMatch = run.graph
        var twin := twin_protocol(run.record, int(run.interval))
        var frozen := mount_views(g._gateway)
        drive(g, twin, [
            {"k": "direct", "a": CF, "r": HF, "c": "MEDIUM", "rc": "MEDIUM"},     # Top
            {"k": "direct", "a": UH, "r": HC, "c": "LOW", "rc": "LOW"},          # Bottom
            {"k": "direct", "a": FL, "r": UF, "c": "MEDIUM", "rc": "HIGH"},      # Top
            {"k": "direct", "a": UH, "r": HP, "c": "MEDIUM", "rc": "MEDIUM"},    # Bottom
            {"k": "pass"},                                                        # Top
        ], "direct flow")
        check("many direct exchanges kept Half Guard active (no forced position change)", [g.active_position_id(), g.status()], ["half_guard", "active"])
        check("history holds exactly the four accepted exchanges and the one pass, once each", [g.history_fields().initiated_action_history, g.history_fields().reset_window_history],
            [[CF, UH, FL, UH], ["top"]])
        check("the retained Mount segment never changed during Half Guard play", mount_views(g._gateway), frozen)
        var after_entry := event_kinds(g).slice(event_kinds(g).find("transition_committed") + 1)
        check("since entry: exactly one window and one accepted graph decision per exchange or pass, nothing else", after_entry, ["window_opened", "decision_accepted", "window_opened", "decision_accepted",
            "window_opened", "decision_accepted", "window_opened", "decision_accepted", "window_opened", "decision_accepted"])
    # the legacy path cannot bypass a pending seal, and the pending seal survives the attempt
    var run2 := entered(plans[0])
    var g2: BjjPositionGraphMatch = run2.graph
    var opened := g2.open_window()
    var wid := int(opened.values.window_id)
    check("a seal is accepted", g2.seal_intent(wid, TOP, CF, "HIGH", KS).ok(), true)
    var before := everything(g2)
    refused("legacy submit with a pending seal", g2, g2.submit(wid, TOP, CF, HF, "MEDIUM", "MEDIUM"), "intent_pending", before)
    refused("a legacy pass with a pending seal", g2, g2.submit(wid, TOP), "intent_pending", before)
    refused("a legacy pass by the responder with a pending seal", g2, g2.submit(wid, BOTTOM), "intent_pending", before)
    refused("a second window over a pending seal", g2, g2.open_window(), "window_already_open", before)
    refused("a timed window over a pending seal", g2, g2.open_window_for(0), "window_already_open", before)
    check("the sealed feint survived every bypass attempt", g2.sealed_intent_view(TOP).values.real_action_id, KS)


# ---- 6. D. Mount -> Half Guard -> feints (both qualified pairs) ------------------------------------------------------------------------------

func _test_half_guard_feints() -> void:
    for plan: Dictionary in plans.slice(0, 3):
        # FP-1: Top Crossface -> Knee Slice, answered by every response, compared with the independent protocol
        for response: String in [HF, UF, KSH]:
            var run := entered(plan)
            var g: BjjPositionGraphMatch = run.graph
            var twin := twin_protocol(run.record, int(run.interval))
            drive(g, twin, [{"k": "feint", "a": CF, "real": KS, "c": "MEDIUM", "r": response, "rc": "MEDIUM"}], "FP-1 vs %s" % response.get_slice(".", 2))
            check("FP-1: the settled exchange is the real technique", g.history_fields().initiated_action_history, [KS])
            check("FP-1: one history exchange, one accepted graph decision since entry", [g.history_fields().top_initiation_count, event_kinds(g).count("decision_accepted")],
                [1, event_kinds(g).count("decision_accepted")])
        # FP-2: Bottom Underhook -> Recover Guard (the Bottom's window follows one Top exchange)
        for response: String in [HC, HP, KP]:
            var run2 := entered(plan)
            var g2: BjjPositionGraphMatch = run2.graph
            var twin2 := twin_protocol(run2.record, int(run2.interval))
            # the Top passes first: a successful Crossface would weaken the Bottom's frame and (correctly) make FP-2 ineligible
            drive(g2, twin2, [{"k": "pass"}, {"k": "feint", "a": UH, "real": RG, "c": "MEDIUM", "r": response, "rc": "MEDIUM"}], "FP-2 vs %s" % response.get_slice(".", 2))
            check("FP-2: the settled exchange is the real technique", g2.history_fields().initiated_action_history, [RG])
    # the graph-level view of a sealed feint, step by step (literal expectations)
    var run3 := entered(plans[0])
    var g3: BjjPositionGraphMatch = run3.graph
    var opened := g3.open_window()
    var wid := int(opened.values.window_id)
    var seal := g3.seal_intent(wid, TOP, CF, "HIGH", KS)
    check("the seal report is exactly the public view", seal.values, {"position_id": "half_guard", "window_id": wid, "intent_serial": 1, "initiator_id": TOP, "responder_id": BOTTOM,
        "apparent_technique_id": CF, "apparent_technique_name": "Crossface", "commitment_requested": "HIGH", "eligible_real_ids": [KS], "response_ids": [HF, UF, KSH]})
    check("the public view equals the seal report", g3.public_intent_view().values, seal.values)
    check("only the initiator reads the sealed intent", [g3.sealed_intent_view(BOTTOM).error, g3.sealed_intent_view("").error, g3.sealed_intent_view("stranger").error,
        g3.sealed_intent_view(TOP).values], ["not_intent_owner", "not_intent_owner", "not_intent_owner",
        {"window_id": wid, "intent_serial": 1, "action_id": CF, "real_action_id": KS, "commitment_requested": "HIGH"}])
    check("a seal appended no graph decision and no transition", event_kinds(g3).slice(-1), ["window_opened"])
    var done := g3.respond(wid, BOTTOM, 1, UF, "MEDIUM")
    check("one resolved feint: one accepted graph decision and nothing else", [event_kinds(g3).slice(-2), done.ok(), done.values.graph.status], [["window_opened", "decision_accepted"], true, "active"])
    check("the real technique appears in the public stream only at the reveal", g3.sealed_public_events().map(func(e: Dictionary) -> bool: return e.has("real_action_id")), [false, false, false])
    check("the reveal discloses the apparent and the real technique", [g3.sealed_public_events()[2].apparent_action_id, g3.sealed_public_events()[2].action_id, g3.sealed_public_events()[2].feint],
        [CF, KS, true])


# ---- 7. The ordinary defender timeout (published LOW fallback) through the graph -----------------------------------------------------------------

func _test_half_guard_timeout_fallback() -> void:
    for plan: Dictionary in plans.slice(0, 2):
        var run := entered(plan)
        var g: BjjPositionGraphMatch = run.graph
        var twin := twin_protocol(run.record, int(run.interval))
        drive(g, twin, [
            {"k": "timeout", "a": CF, "real": KS, "c": "LOW"},       # Top feint FP-1 (Knee Slice builds nothing)
            {"k": "timeout", "a": UH, "real": RG, "c": "HIGH"},      # Bottom feint FP-2 (its success weakens the Top's base)
            {"k": "timeout", "a": FL, "real": "", "c": "MEDIUM"},    # Top direct Flatten
        ], "timeout")
        check("a defaulted decision is an ordinary accepted decision for the graph (no stalling, no extra window)", [event_kinds(g).count("window_opened"), event_kinds(g).count("decision_accepted") >= 3,
            g.status()], [event_kinds(g).count("window_opened"), true, "active"])
        var defaulted: Array = g._sealed.protocol_events().filter(func(e: Dictionary) -> bool: return e.event == "response_committed").map(func(e: Dictionary) -> bool: return bool(e.defaulted))
        check("the protocol flagged each timeout as defaulted", defaulted, [true, true, true])
    # the graph refuses a fallback that is not the published one, without mutation
    var run2 := entered(plans[0])
    var g2: BjjPositionGraphMatch = run2.graph
    var wid := int(g2.open_window().values.window_id)
    g2.seal_intent(wid, TOP, CF, "MEDIUM", KS)
    var before := everything(g2)
    for wrong: Array in [[HF, "MEDIUM"], [HF, ""], [UF, "LOW"], [KSH, "LOW"], [HC, "LOW"], ["nonsense", "LOW"]]:
        refused("a fallback that is not published %s" % [wrong], g2, g2.apply_response_timeout(wid, 1, str(wrong[0]), str(wrong[1])), "fallback_not_published", before)
    check("the published fallback resolves it", g2.apply_response_timeout(wid, 1, HF, "LOW").ok(), true)


# ---- 8. E. Exiting or ending Half Guard through the graph's sealed protocol ----------------------------------------------------------------------

func _test_half_guard_exits_unsupported_and_terminal() -> void:
    var plan: Dictionary = plans[0]
    # (1) a genuine Half Guard exit by a MEDIUM feint that bites twice (axis 5 -> 25 -> exit): Side Control has no receiver, so the graph HALTS
    var run := entered(plan)
    var g: BjjPositionGraphMatch = run.graph
    var twin := twin_protocol(run.record, int(run.interval))
    drive(g, twin, [{"k": "feint", "a": CF, "real": KS, "c": "MEDIUM", "r": UF, "rc": "MEDIUM"}, {"k": "pass"},
        {"k": "feint", "a": CF, "real": KS, "c": "MEDIUM", "r": UF, "rc": "MEDIUM"}], "Side Control exit")
    check("the accepted exit exchange stays settled and the graph halts (an incomplete-engine boundary, not a victory)", [g.status(), g.active_position_id()], [STATUS_HALTED, "half_guard"])
    check("the sequence is window, accepted decision, one blocked transition", event_kinds(g).slice(-3), ["window_opened", "decision_accepted", "transition_blocked"])
    check("the block names Half Guard as the source and the unimplemented destination", g.blocked_transition(), {"from_position_id": "half_guard", "label": "Side Control",
        "reason": "destination_not_implemented", "destination_position_id": "side_control"})
    check("a halt is not a terminal outcome: no terminal event, no winner, no score", [event_kinds(g).has("terminal_outcome"), g._terminal_reason], [false, ""])
    check("exactly one transition_blocked and no transition_committed after the entry", [event_kinds(g).count("transition_blocked"), event_kinds(g).count("transition_committed")], [1, 1])
    check("the settled exit is recorded once: the real technique, ended, one exit", [g.history_fields().initiated_action_history.back(), g.state_fields().exit_destination, g.state_fields().ended],
        [KS, "Side Control", true])
    var halted_before := everything(g)
    for call: Array in _sealed_calls(g):
        refused("after the Half Guard exit halt: %s" % call[0], g, call[1], HALTED, halted_before)
    refused("legacy submit after the Half Guard halt", g, g.submit(1, TOP, CF, HF), HALTED, halted_before)
    refused("opening a window after the Half Guard halt", g, g.open_window(), HALTED, halted_before)
    # (2) the Bottom's escape: Underhook -> Recover Guard bites twice and exits to Closed Guard (no receiver either)
    var run2 := entered(plan)
    var g2: BjjPositionGraphMatch = run2.graph
    var twin2 := twin_protocol(run2.record, int(run2.interval))
    drive(g2, twin2, [{"k": "pass"}, {"k": "feint", "a": UH, "real": RG, "c": "MEDIUM", "r": HC, "rc": "MEDIUM"}, {"k": "pass"},
        {"k": "feint", "a": UH, "real": RG, "c": "MEDIUM", "r": HC, "rc": "MEDIUM"}], "Closed Guard exit")
    check("the Bottom's escape halts with the Half Guard source and its own label", [g2.status(), g2.blocked_transition()], [STATUS_HALTED, {"from_position_id": "half_guard",
        "label": "Closed Guard", "reason": "destination_not_implemented", "destination_position_id": "closed_guard"}])
    check("the escape was one accepted exchange of the real technique", g2.history_fields().initiated_action_history, [RG, RG])
    # (3) a direct (legacy submit) exit takes the same path
    var run3 := entered(plan)
    var g3: BjjPositionGraphMatch = run3.graph
    var twin3 := twin_protocol(run3.record, int(run3.interval))
    drive(g3, twin3, [{"k": "direct", "a": KS, "r": UF, "c": "HIGH", "rc": "MEDIUM"}, {"k": "pass"}, {"k": "direct", "a": KS, "r": UF, "c": "HIGH", "rc": "MEDIUM"}], "direct exit")
    check("a direct Half Guard exit halts exactly like a sealed one", [g3.status(), g3.blocked_transition().from_position_id, event_kinds(g3).slice(-1)], [STATUS_HALTED, "half_guard", ["transition_blocked"]])
    # (4) the match clock ends Half Guard: a genuine terminal outcome from the CURRENT position, not an exit
    var run4 := entered(plan)
    var g4: BjjPositionGraphMatch = run4.graph
    var twin4 := twin_protocol(run4.record, int(run4.interval))
    var remaining := int(g4.state_fields().clock_seconds)
    var closing := g4.open_window_for(remaining)
    check("the closing window equals the independent protocol's", strip(closing), strip(twin4.open_window_for(remaining)))
    check("the clock ended the match in Half Guard", [closing.values.closed, g4.status(), g4.active_position_id()], [true, "ended", "half_guard"])
    check("the terminal outcome is a timeout, not an exit: no blocked transition, no new transition", [event_kinds(g4).slice(-1), g4.events().back().reason, g4.blocked_transition(),
        event_kinds(g4).count("transition_committed"), event_kinds(g4).count("transition_blocked")], [["terminal_outcome"], "timeout", {}, 1, 0])
    check("no winner, score or adjudication was produced", g4.events().back().keys(), ["kind", "reason", "index"])
    var ended_before := everything(g4)
    for call: Array in _sealed_calls(g4):
        refused("after the Half Guard clock expiry: %s" % call[0], g4, call[1], "match_ended", ended_before)
    check("the legacy path after the end is the gateway's own refusal and appends nothing", [g4.open_window().error, g4.events().size()], ["terminal_exchange", ended_before.events.size()])
    refused("a legacy submit after the Half Guard clock expiry", g4, g4.submit(1, TOP, CF, HF), "no_open_window", ended_before)
    check("the Half Guard segment equals the independent protocol's after the end", g4._half_guard.snapshot(), twin4.snapshot())


# ---- 9. F. Refusals and adversarial boundaries ---------------------------------------------------------------------------------------------------

func _hg_window(plan: Dictionary) -> Dictionary:
    var run := entered(plan)
    var g: BjjPositionGraphMatch = run.graph
    var opened := g.open_window()
    return {"graph": g, "window_id": int(opened.values.window_id), "run": run}


func _test_sealed_refusals_and_adversarial_boundaries() -> void:
    var plan: Dictionary = plans[1]
    var ctx := _hg_window(plan)
    var g: BjjPositionGraphMatch = ctx.graph
    var wid: int = ctx.window_id
    var before := everything(g)
    # nothing sealed yet
    refused("respond with no seal", g, g.respond(wid, BOTTOM, 1, HF, "MEDIUM"), "no_sealed_intent", before)
    refused("timeout with no seal", g, g.apply_response_timeout(wid, 1, HF, "LOW"), "no_sealed_intent", before)
    refused("the initiator's view with no seal", g, g.sealed_intent_view(TOP), "no_sealed_intent", before)
    refused("the public view with no seal", g, g.public_intent_view(), "no_sealed_intent", before)
    for stale: int in [0, wid - 1, wid + 1, 99999]:
        refused("seal for stale window %d" % stale, g, g.seal_intent(stale, TOP, CF, "MEDIUM"), "stale_window", before)
    refused("the responder cannot seal", g, g.seal_intent(wid, BOTTOM, UH, "MEDIUM"), "not_initiator", before)
    refused("an unknown fighter cannot seal", g, g.seal_intent(wid, "stranger", CF, "MEDIUM"), "unknown_fighter", before)
    refused("a missing fighter cannot seal", g, g.seal_intent(wid, "", CF, "MEDIUM"), "missing_fighter_id", before)
    refused("an unknown technique", g, g.seal_intent(wid, TOP, "nonsense", "MEDIUM"), "unknown_action", before)
    refused("the other side's technique", g, g.seal_intent(wid, TOP, UH, "MEDIUM"), "unknown_action", before)
    refused("an invalid commitment", g, g.seal_intent(wid, TOP, CF, "EXTREME"), "invalid_commitment", before)
    refused("real equals apparent", g, g.seal_intent(wid, TOP, CF, "MEDIUM", CF), "feint_real_equals_apparent", before)
    refused("Flatten to Knee Slice is not a pair", g, g.seal_intent(wid, TOP, FL, "MEDIUM", KS), "feint_not_supported", before)
    refused("a bottom technique as the real", g, g.seal_intent(wid, TOP, CF, "MEDIUM", RG), "incorrect_action_side_or_kind", before)
    refused("an unknown real", g, g.seal_intent(wid, TOP, CF, "MEDIUM", "nonsense"), "unknown_action", before)
    # a seal, then every refusal of the seal / respond / timeout path leaves the sealed intent intact
    check("a valid feint seal is accepted", g.seal_intent(wid, TOP, CF, "HIGH", KS).ok(), true)
    var sealed := everything(g)
    check("the seal changed no simulation state and appended no graph event", [g._half_guard.snapshot(), g.events().size()], [before.half_guard, before.events.size()])
    refused("a duplicate seal", g, g.seal_intent(wid, TOP, CF, "HIGH", KS), "intent_already_sealed", sealed)
    refused("a duplicate seal with a different technique", g, g.seal_intent(wid, TOP, FL, "LOW"), "intent_already_sealed", sealed)
    refused("a duplicate seal as the responder", g, g.seal_intent(wid, BOTTOM, UH, "LOW"), "not_initiator", sealed)
    refused("a stale response", g, g.respond(wid + 1, BOTTOM, 1, HF, "MEDIUM"), "stale_window", sealed)
    for serial: int in [0, 2, -1]:
        refused("response serial %d" % serial, g, g.respond(wid, BOTTOM, serial, HF, "MEDIUM"), "intent_serial_mismatch", sealed)
    refused("the initiator cannot answer itself", g, g.respond(wid, TOP, 1, HF, "MEDIUM"), "not_responder", sealed)
    refused("an unknown fighter cannot respond", g, g.respond(wid, "stranger", 1, HF, "MEDIUM"), "unknown_fighter", sealed)
    refused("an invalid response", g, g.respond(wid, BOTTOM, 1, "nonsense", "MEDIUM"), "unknown_response", sealed)
    refused("the other side's response", g, g.respond(wid, BOTTOM, 1, HC, "MEDIUM"), "unknown_response", sealed)
    refused("an invalid response commitment", g, g.respond(wid, BOTTOM, 1, HF, "bad"), "invalid_response_commitment", sealed)
    refused("an incorrect timeout fallback", g, g.apply_response_timeout(wid, 1, UF, "LOW"), "fallback_not_published", sealed)
    refused("a stale timeout", g, g.apply_response_timeout(wid + 1, 1, HF, "LOW"), "stale_window", sealed)
    refused("legacy submit bypassing the pending seal", g, g.submit(wid, TOP, CF, HF, "MEDIUM", "MEDIUM"), "intent_pending", sealed)
    check("the sealed feint survived every refusal and a valid retry resolves it", [g.sealed_intent_view(TOP).values.real_action_id, g.respond(wid, BOTTOM, 1, UF, "MEDIUM").ok()], [KS, true])
    var settled := everything(g)
    # replayed and duplicated deliveries cannot double-spend
    refused("a replayed response", g, g.respond(wid, BOTTOM, 1, UF, "MEDIUM"), "no_open_window", settled)
    refused("a replayed timeout", g, g.apply_response_timeout(wid, 1, HF, "LOW"), "no_open_window", settled)
    refused("a replayed seal", g, g.seal_intent(wid, TOP, CF, "HIGH", KS), "no_open_window", settled)
    check("exactly one exchange and one accepted decision since entry", [g.history_fields().initiated_action_history.size(),
        event_kinds(g).slice(event_kinds(g).find("transition_committed") + 1).count("decision_accepted")], [1, 1])
    # the same battery on a Bottom window (the other role)
    var ctx2 := _hg_window(plan)
    var g2: BjjPositionGraphMatch = ctx2.graph
    g2.submit(ctx2.window_id, TOP)
    var wid2 := int(g2.open_window().values.window_id)
    var before2 := everything(g2)
    refused("the Top cannot seal in the Bottom's window", g2, g2.seal_intent(wid2, TOP, CF, "MEDIUM"), "not_initiator", before2)
    refused("a Top technique cannot be sealed by the Bottom", g2, g2.seal_intent(wid2, BOTTOM, CF, "MEDIUM"), "unknown_action", before2)
    refused("Recover Guard is not an apparent feint technique", g2, g2.seal_intent(wid2, BOTTOM, RG, "MEDIUM", UH), "feint_not_supported", before2)
    check("the Bottom's feint seal is accepted", g2.seal_intent(wid2, BOTTOM, UH, "LOW", RG).ok(), true)
    var sealed2 := everything(g2)
    refused("the Bottom cannot answer itself", g2, g2.respond(wid2, BOTTOM, 1, HC, "MEDIUM"), "not_responder", sealed2)
    refused("the Top cannot answer with a Bottom response", g2, g2.respond(wid2, TOP, 1, HF, "MEDIUM"), "unknown_response", sealed2)
    refused("the Bottom's wrong fallback", g2, g2.apply_response_timeout(wid2, 1, HF, "LOW"), "fallback_not_published", sealed2)
    check("the published Top fallback resolves it", g2.apply_response_timeout(wid2, 1, HP, "LOW").ok(), true)

    # --- malformed attachment (the adoption seam itself) ---
    var idle_entry := BjjHalfGuardMountEdge.entry_from_record(ctx.run.record.duplicate(true), int(ctx.run.interval)).request
    for bad: Array in [["null", null], ["int", 5], ["string", "x"], ["dictionary", {}], ["array", []], ["a Mount gateway", g._gateway], ["a graph", g], ["a protocol", g._sealed], ["a node", RefCounted.new()]]:
        var adopted := BjjHalfGuardSealedProtocol.adopt(bad[1])
        check("adopting %s is refused" % bad[0], [adopted.ok(), adopted.error, adopted.protocol == null], [false, "invalid_gateway", true])
    var fresh_gateway := BjjHalfGuardWindowGateway.create(idle_entry).gateway
    var fresh_before := fresh_gateway.snapshot()
    var open_gateway := BjjHalfGuardWindowGateway.create(idle_entry).gateway
    open_gateway.open_window()
    var open_before := open_gateway.snapshot()
    var open_attempt := BjjHalfGuardSealedProtocol.adopt(open_gateway)
    check("a gateway with an open window is refused and left untouched and unclaimed", [open_attempt.error, open_gateway.snapshot() == open_before, open_gateway._protocol_claimed], ["gateway_not_idle", true, false])
    var terminal_gateway := BjjHalfGuardWindowGateway.create(idle_entry).gateway
    terminal_gateway.open_window_for(int(terminal_gateway.state_fields().clock_seconds))
    check("a terminal gateway is refused", [BjjHalfGuardSealedProtocol.adopt(terminal_gateway).error, terminal_gateway._protocol_claimed], ["gateway_not_idle", false])
    var owned := BjjHalfGuardSealedProtocol.create(idle_entry).protocol
    check("a gateway already owned by create() cannot be adopted", [BjjHalfGuardSealedProtocol.adopt(owned._gateway).error, owned.is_adopted()], ["gateway_already_attached", false])
    var first := BjjHalfGuardSealedProtocol.adopt(fresh_gateway)
    check("an idle, unclaimed gateway is adopted", [first.ok(), first.protocol.is_adopted(), fresh_gateway._protocol_claimed, fresh_gateway.snapshot() == fresh_before], [true, true, true, true])
    var second := BjjHalfGuardSealedProtocol.adopt(fresh_gateway)
    check("a second adoption of the same gateway is refused (duplicate state ownership)", [second.ok(), second.error, second.protocol == null], [false, "gateway_already_attached", true])
    check("the adopted protocol shares the gateway, it does not copy it", [first.protocol._gateway == fresh_gateway, first.protocol.snapshot() == fresh_gateway.snapshot()], [true, true])
    # create(entry) keeps its own gateway and its own seams: it is NOT an adopted protocol and has no divergence guard
    check("create(entry) is unchanged: owned, not adopted", [owned.is_adopted(), owned._gateway._protocol_claimed], [false, true])
    owned._gateway._match.axis_tenths = 15   # the test seam the earlier suites use: state injection before the first command
    owned._gateway._match.band = 1
    check("an owned protocol still works after a seam injection (no divergence refusal)", owned.open_window().ok(), true)

    # --- attempted aliasing: another holder of the gateway changes it behind the protocol's back ---
    var ctx3 := _hg_window(plan)
    var g3: BjjPositionGraphMatch = ctx3.graph
    var alias: BjjHalfGuardWindowGateway = g3._half_guard
    check("the test holds an alias to the graph's gateway (read through the seam)", alias == g3._sealed._gateway, true)
    alias.submit(ctx3.window_id, TOP, CF, HF, "MEDIUM", "MEDIUM")   # a direct bypass of the protocol and the graph
    var diverged := everything(g3)
    refused("a seal after an outside mutation", g3, g3.seal_intent(ctx3.window_id, TOP, CF, "MEDIUM"), "gateway_diverged", diverged)
    refused("a response after an outside mutation", g3, g3.respond(ctx3.window_id, BOTTOM, 1, HF, "MEDIUM"), "gateway_diverged", diverged)
    refused("a timeout after an outside mutation", g3, g3.apply_response_timeout(ctx3.window_id, 1, HF, "LOW"), "gateway_diverged", diverged)
    refused("a legacy submit after an outside mutation", g3, g3.submit(ctx3.window_id, TOP), "gateway_diverged", diverged)
    refused("opening a window after an outside mutation", g3, g3.open_window(), "gateway_diverged", diverged)
    check("the graph never recorded the bypassed exchange as an accepted decision", event_kinds(g3).slice(-1), ["window_opened"])

    # --- direct versus feint are indistinguishable at the graph level ---
    for commitment: String in ["LOW", "MEDIUM", "HIGH"]:
        var direct_ctx := _hg_window(plan)
        var feint_ctx := _hg_window(plan)
        var gd: BjjPositionGraphMatch = direct_ctx.graph
        var gf: BjjPositionGraphMatch = feint_ctx.graph
        var seal_d := gd.seal_intent(direct_ctx.window_id, TOP, CF, commitment)
        var seal_f := gf.seal_intent(feint_ctx.window_id, TOP, CF, commitment, KS)
        check("%s: the seal reports are identical" % commitment, strip(seal_d), strip(seal_f))
        var battery: Callable = Callable(self, "_defender_battery")
        check("%s: every defender-observable graph surface is identical (views, events, refusals, menus)" % commitment, battery.call(gf), battery.call(gd))


func _defender_battery(g: BjjPositionGraphMatch) -> Dictionary:
    var wid := int(g.window_fields().window_id)
    var codes: Array = [g.respond(wid, BOTTOM, 2, HF, "LOW").error, g.respond(wid + 1, BOTTOM, 1, HF, "LOW").error, g.respond(wid, TOP, 1, HF, "LOW").error,
        g.respond(wid, BOTTOM, 1, "nonsense", "LOW").error, g.respond(wid, BOTTOM, 1, HF, "bad").error, g.seal_intent(wid, BOTTOM, UH, "LOW").error,
        g.seal_intent(wid, TOP, CF, "LOW").error, g.submit(wid, BOTTOM).error, g.open_window().error, g.sealed_intent_view(BOTTOM).error,
        g.apply_response_timeout(wid, 1, UF, "LOW").error, g.apply_response_timeout(wid, 1, HF, "MEDIUM").error]
    return {"view": strip(g.public_intent_view()), "public_events": g.sealed_public_events(), "graph_events": g.events(), "codes": codes, "state": g.state_fields(), "history": g.history_fields(),
        "window": g.window_fields(), "roles": g.roles().fields(), "responses": g.response_options(CF).available_ids(), "defender_menu": g.action_options(BOTTOM).available_ids()}


# ---- 10. Failure injection during recipient construction and attachment ---------------------------------------------------------------------------

var _foreign_protocol: BjjHalfGuardSealedProtocol
var _receiver_calls: int = 0


func _receiver_pre_claimed(record: Dictionary, interval_seconds: int) -> BjjHalfGuardWindowGateway.Creation:
    _receiver_calls += 1
    var creation := BjjPositionGraphMatch.default_receivers()["half_guard"].call(record, interval_seconds) as BjjHalfGuardWindowGateway.Creation
    _foreign_protocol = BjjHalfGuardSealedProtocol.adopt(creation.gateway).protocol   # somebody else already owns this simulation
    return creation


func _receiver_window_open(record: Dictionary, interval_seconds: int) -> BjjHalfGuardWindowGateway.Creation:
    _receiver_calls += 1
    var creation := BjjPositionGraphMatch.default_receivers()["half_guard"].call(record, interval_seconds) as BjjHalfGuardWindowGateway.Creation
    creation.gateway.open_window()
    return creation


func _receiver_not_a_creation(record: Dictionary, interval_seconds: int) -> Variant:
    _receiver_calls += 1
    return 5


func _receiver_failed_creation(record: Dictionary, interval_seconds: int) -> BjjHalfGuardWindowGateway.Creation:
    _receiver_calls += 1
    var failed := BjjHalfGuardWindowGateway.Creation.new()
    failed.error = "injected"
    return failed


func _receiver_tampered(record: Dictionary, interval_seconds: int) -> BjjHalfGuardWindowGateway.Creation:
    _receiver_calls += 1
    var creation := BjjPositionGraphMatch.default_receivers()["half_guard"].call(record, interval_seconds) as BjjHalfGuardWindowGateway.Creation
    creation.gateway._match.clock_seconds -= 1
    return creation


func _test_attachment_failures_halt_without_partial_activation() -> void:
    var plan: Dictionary = plans[0]
    for injection: Array in [["a gateway another protocol already owns", "_receiver_pre_claimed"], ["a gateway with a window already open", "_receiver_window_open"],
            ["a non-Creation answer", "_receiver_not_a_creation"], ["a failed Creation", "_receiver_failed_creation"], ["a tampered clock", "_receiver_tampered"]]:
        _receiver_calls = 0
        _foreign_protocol = null
        var g := make_sealed(plan, {"half_guard": Callable(self, str(injection[1]))})
        var bare := make_bare(plan)
        run_plan(bare, plan)
        run_plan(g, plan)
        var label := str(injection[0])
        check("%s: the receiver was asked exactly once" % label, _receiver_calls, 1)
        check("%s: the graph halted with transition_entry_invalid (HG-18: no rollback, no partial activation)" % label, [g.status(), g.blocked_transition()],
            [STATUS_HALTED, {"from_position_id": "mount", "label": "Half Guard", "reason": "transition_entry_invalid", "destination_position_id": "half_guard"}])
        check("%s: no Half Guard slot, no protocol, no committed transition" % label, [g._half_guard == null, g._sealed == null, event_kinds(g).count("transition_committed"),
            event_kinds(g).count("transition_blocked"), g.active_position_id()], [true, true, 0, 1, "mount"])
        check("%s: the accepted Mount exchange stays settled exactly as the bare gateway's" % label, mount_views(g._gateway), mount_views(bare))
        check("%s: the event sequence ends window, accepted decision, blocked" % label, event_kinds(g).slice(-3), ["window_opened", "decision_accepted", "transition_blocked"])
        var halted_before := everything(g)
        for call: Array in _sealed_calls(g):
            refused("%s, then %s" % [label, call[0]], g, call[1], HALTED, halted_before)
        if _foreign_protocol != null:
            check("%s: the foreign owner keeps its simulation untouched" % label, [_foreign_protocol.is_adopted(), _foreign_protocol.has_pending_intent(), _foreign_protocol.executor_snapshot().serial], [true, false, 0])


# ---- 11. Determinism: complete match-flow sequences replay identically -----------------------------------------------------------------------------

func _record(g: BjjPositionGraphMatch, reports: Array) -> Dictionary:
    var all := everything(g)
    all["reports"] = reports
    return all


func scenario_mount_only() -> Dictionary:
    var plan := {"rule_set": "modern", "config": {"axis": 1.5}, "label": "", "rounds": 0, "action": "", "response": ""}
    var g := make_sealed(plan)
    var reports: Array = []
    for index in range(14):
        var opened := g.open_window_for(0)
        reports.append(strip(opened))
        reports.append(strip(g.submit(int(opened.values.window_id), str(opened.values.fighter_id))))
    return _record(g, reports)


func scenario_mount_terminal() -> Dictionary:
    var g := BjjPositionGraphMatch.create_with_sealed_half_guard({"rules": rules(), "clock": 15, "interval": 5}, TOP, BOTTOM).graph
    var reports: Array = []
    for index in range(4):
        var opened := g.open_window()
        reports.append(strip(opened))
        if opened.values.get("closed", false):
            break
        reports.append(strip(g.submit(int(opened.values.window_id), str(opened.values.fighter_id))))
    return _record(g, reports)


func scenario_mount_to_half_guard() -> Dictionary:
    var plan: Dictionary = plans[0]
    var g := make_sealed(plan)
    var run := run_plan(g, plan)
    return _record(g, run.trace)


func _hg_scenario(steps: Array) -> Dictionary:
    var plan: Dictionary = plans[0]
    var g := make_sealed(plan)
    var run := run_plan(g, plan)
    var reports: Array = run.trace.duplicate()
    for step: Dictionary in steps:
        var opened := g.open_window()
        reports.append(strip(opened))
        if not opened.ok() or opened.values.get("closed", false):
            break
        var wid := int(opened.values.window_id)
        var fighter_id := str(opened.values.fighter_id)
        var responder_id := BOTTOM if fighter_id == TOP else TOP
        if str(step.k) == "direct":
            reports.append(strip(g.submit(wid, fighter_id, str(step.a), str(step.r), str(step.c), str(step.rc))))
        elif str(step.k) == "pass":
            reports.append(strip(g.submit(wid, fighter_id)))
        else:
            reports.append(strip(g.seal_intent(wid, fighter_id, str(step.a), str(step.c), str(step.get("real", "")))))
            reports.append(strip(g.public_intent_view()))
            if str(step.k) == "timeout":
                var published := BjjHalfGuardCatalog.timeout_fallback("bottom" if responder_id == BOTTOM else "top")
                reports.append(strip(g.apply_response_timeout(wid, int(g._sealed.executor_snapshot().serial), str(published.response_id), str(published.commitment))))
            else:
                reports.append(strip(g.respond(wid, responder_id, int(g._sealed.executor_snapshot().serial), str(step.r), str(step.rc))))
        if g.status() != "active":
            break
    return _record(g, reports)


func scenario_half_guard_direct() -> Dictionary:
    return _hg_scenario([{"k": "direct", "a": CF, "r": HF, "c": "MEDIUM", "rc": "MEDIUM"}, {"k": "direct", "a": UH, "r": HC, "c": "LOW", "rc": "LOW"}, {"k": "pass"}])


func scenario_half_guard_feint() -> Dictionary:
    return _hg_scenario([{"k": "feint", "a": CF, "real": KS, "c": "MEDIUM", "r": KSH, "rc": "MEDIUM"}, {"k": "pass"}, {"k": "feint", "a": CF, "real": KS, "c": "HIGH", "r": UF, "rc": "LOW"}])


func scenario_half_guard_timeout() -> Dictionary:
    return _hg_scenario([{"k": "timeout", "a": CF, "real": KS, "c": "MEDIUM"}, {"k": "timeout", "a": UH, "real": RG, "c": "LOW"}])


func scenario_half_guard_unsupported_exit() -> Dictionary:
    return _hg_scenario([{"k": "feint", "a": CF, "real": KS, "c": "MEDIUM", "r": UF, "rc": "MEDIUM"}, {"k": "pass"}, {"k": "feint", "a": CF, "real": KS, "c": "MEDIUM", "r": UF, "rc": "MEDIUM"}])


func _test_replay_determinism() -> void:
    var expected_ends := {"scenario_mount_only": ["active", "mount"], "scenario_mount_terminal": ["ended", "mount"], "scenario_mount_to_half_guard": ["active", "half_guard"],
        "scenario_half_guard_direct": ["active", "half_guard"], "scenario_half_guard_feint": ["active", "half_guard"], "scenario_half_guard_timeout": ["active", "half_guard"],
        "scenario_half_guard_unsupported_exit": [STATUS_HALTED, "half_guard"]}
    for name: String in expected_ends:
        var first: Dictionary = call(name)
        var second: Dictionary = call(name)
        check("%s: the whole record (states, histories, graph events, protocol outputs) replays identically" % name, first, second)
        check("%s: the scenario ends as designed" % name, [first.status, first.active], expected_ends[name])
        check("%s: the scenario produced real reports" % name, first.reports.size() > 3, true)


# ---- 12. Oracle fixtures and unchanged surfaces ---------------------------------------------------------------------------------------------------------

func _test_fixtures_and_unchanged_surfaces() -> void:
    check("the B1g direct oracle fixture is byte-identical to the qualified one", FileAccess.get_sha256(DIRECT_FIXTURE), DIRECT_FIXTURE_SHA256)
    check("the B1h feint oracle fixture is byte-identical to the qualified one", FileAccess.get_sha256(FEINT_FIXTURE), FEINT_FIXTURE_SHA256)
    var plan: Dictionary = plans[0]
    # the default graph, the B1d opt-in graph and the sealed graph are the SAME Mount-only graph until Half Guard is reached
    var default := make_default(plan)
    var b1d := make_b1d(plan)
    var sealed := make_sealed(plan)
    var bare := make_bare(plan)
    var runs := [run_plan(default, plan).trace, run_plan(b1d, plan).trace, run_plan(sealed, plan).trace, run_plan(bare, plan).trace]
    check("the B1d opt-in graph's Mount run equals the default graph's, command for command", runs[1], runs[0])
    check("the sealed graph's Mount run equals the default graph's, command for command", runs[2], runs[0])
    check("and equals the bare gateway's", runs[3], runs[0])
    check("the default graph still halts at the Half Guard exit", [default.status(), default.blocked_transition().reason], [STATUS_HALTED, "destination_not_implemented"])
    check("the B1d opt-in graph still enters Half Guard directly, with no protocol", [b1d.active_position_id(), b1d._sealed == null], ["half_guard", true])
    check("the sealed graph entered Half Guard with the protocol adopted", [sealed.active_position_id(), sealed._sealed != null], ["half_guard", true])
    check("the Mount history, state and event kinds before the transition are identical across the three graphs", [mount_views(sealed._gateway), event_kinds(sealed).slice(0, -1)],
        [mount_views(b1d._gateway), event_kinds(b1d).slice(0, -1)])
    check("the transition event is identical across the B1d and sealed graphs", sealed.events().back(), b1d.events().back())
    # the opt-in graph's static classification is unchanged
    check("static classification is unchanged", [BjjPositionGraphMatch.classify_exit("Half Guard"), BjjPositionGraphMatch.classify_exit("Open Guard").reason,
        BjjPositionGraphMatch.classify_exit("Reversal").reason], [{"kind": "blocked", "reason": "destination_not_implemented", "destination_position_id": "half_guard"},
        "destination_not_implemented", "unresolved_destination"])


# ---- 13. Scope and hygiene ------------------------------------------------------------------------------------------------------------------------------------

func _code_text(path: String) -> String:
    var file := FileAccess.open(path, FileAccess.READ)
    if file == null:
        return ""
    var code_lines: Array[String] = []
    for source_line: String in file.get_as_text().split("\n"):
        code_lines.append(source_line.split("#")[0])
    return "\n".join(code_lines)


func _test_scope_and_hygiene() -> void:
    var graph := _code_text("res://scripts/positions/graph_match.gd")
    check("the graph source is readable", graph.is_empty(), false)
    for token: String in ["randi", "randf", "RandomNumberGenerator", "Time.", "OS.get_ticks", "await", "get_tree", "Engine.get_frames", "FileAccess", "preload(", "._match", "set_current",
            "BjjMountMatch", "BjjStaminaPool", "BjjBehaviorStaminaPolicy", "BjjD3B", "BjjHalfGuardResolver", "FEINT_PAIRS", "FEINT_SURCHARGE", "submit_feint", "feint_error",
            "timeout_fallback", "eligible_real_ids", "BjjHalfGuardCatalog.TIMEOUT", "attempt(", ".decide("]:
        check("the graph has no %s (no combat rule or second owner lives in the coordinator)" % token, graph.contains(token), false)
    check("exactly one place assigns the Half Guard slot and one the protocol slot (the commit)", [graph.count("_half_guard = "), graph.count("_sealed = ")], [1, 1])
    check("the graph adopts the protocol exactly once and never builds a second simulation for it", [graph.count("BjjHalfGuardSealedProtocol.adopt("), graph.count("BjjHalfGuardSealedProtocol.create(")], [1, 0])
    check("the graph never claims or constructs a gateway itself beyond the receiver edge", [graph.contains("claim_for_protocol"), graph.count("BjjHalfGuardWindowGateway.create(")], [false, 1])
    check("the settlement path is a single function used by submit, respond and timeout", [graph.count("func _settle_accepted("), graph.count("_settle_accepted(source, report)")], [1, 3])
    check("no other source constructs the sealed graph (F0 and F1 stay Mount-only)", _referencing("create_with_sealed_half_guard"), ["res://scripts/positions/graph_match.gd"])
    check("no Mount source references the protocol or the sealed graph", ["SealedProtocol", "create_with_sealed_half_guard", "seal_intent"].map(
        func(token: String) -> bool: return _code_text("res://scripts/positions/mount/mount_window_gateway.gd").contains(token)), [false, false, false])
    for path: String in ["half_guard_rules", "half_guard_catalog", "half_guard_resolver", "half_guard_entry", "half_guard_match", "half_guard_contract", "half_guard_mount_edge"]:
        check("%s knows neither the graph nor the adoption" % path, ["BjjPositionGraphMatch", "SealedProtocol", "adopt("].map(
            func(token: String) -> bool: return _code_text("res://scripts/positions/half_guard/%s.gd" % path).contains(token)), [false, false, false])
    check("the protocol still holds no combat rule", ["FEINT_PAIRS", "BjjHalfGuardResolver", ".attempt(", ".decide("].map(
        func(token: String) -> bool: return _code_text("res://scripts/positions/half_guard/half_guard_sealed_protocol.gd").contains(token)), [false, false, false, false])
    check("no graph public name mentions a gateway", (BjjPositionGraphMatch as GDScript).get_script_method_list().filter(func(m: Dictionary) -> bool:
        return not str(m.name).begins_with("_") and str(m.name).to_lower().contains("gateway")).size(), 0)


func _referencing(token: String) -> Array:
    var found: Array = []
    for directory: String in ["res://scripts/core", "res://scripts/positions", "res://scripts/positions/mount", "res://scripts/positions/half_guard", "res://scripts/presentation", "res://scripts/ui"]:
        var dir := DirAccess.open(directory)
        if dir == null:
            continue
        for file_name: String in dir.get_files():
            if file_name.ends_with(".gd") and _code_text(directory + "/" + file_name).contains(token):
                found.append(directory + "/" + file_name)
    found.sort()
    return found
