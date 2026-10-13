extends SceneTree

# CI-gated STRUCTURAL invariants of the connected Mount + Half Guard match flow (B1e). A fixed, deterministic set of REAL games (named scripted policies, fixed
# seeds, explicit maximum windows) is driven through the real opt-in sealed graph by the shared harness (tests/match_flow_harness.gd). An observer checks the
# invariants LIVE at every step and probes rejected commands (whole-state equality). Exploratory population measurements live in measure_match_flow.gd and are
# NOT gated; only exact properties are asserted here. No rule is changed or tuned and nothing is fabricated: every transition below happened through the gateway.
const H = preload("res://tests/match_flow_harness.gd")
const TOP: String = H.TOP
const BOTTOM: String = H.BOTTOM
const HALTED: String = "halted_unsupported_transition"
const MAX_WINDOWS: int = 80

var checks: int = 0
var failures: int = 0
var coverage := {"games": 0, "windows": 0, "probes": 0, "transitions": 0, "halts": 0, "ended": 0, "taps": 0, "feints_accepted": 0, "fallbacks": 0, "exchanges": 0,
    "mount_replays": 0, "mount_windows_replayed": 0, "terminal_batteries": 0}


func check(label: String, actual: Variant, expected: Variant) -> void:
    checks += 1
    if typeof(actual) != typeof(expected) or JSON.stringify(actual, "", true, true) != JSON.stringify(expected, "", true, true):
        failures += 1
        if failures <= 40:
            push_error("%s: got %s expected %s" % [label, JSON.stringify(actual).left(400), JSON.stringify(expected).left(400)])


class Observer extends RefCounted:
    var t: Object
    var label: String = ""
    var last_clock: int = 0
    var last_events: int = 0
    var last_window_id: int = 0
    var stamina_before: Array = [0, 0]
    var hg_open_snapshot: Dictionary = {}
    var events_at_open: int = 0
    var protocol_events_at_open: int = 0
    var mount_frozen: Dictionary = {}
    var position_before: String = "mount"
    var windows_seen: int = 0

    func begin(g: BjjPositionGraphMatch, game_label: String) -> void:
        label = game_label
        last_clock = int(g.state_fields().clock_seconds)
        last_events = g.events().size()
        last_window_id = int(g.window_fields().window_id)
        var state := g.state_fields()
        stamina_before = [int(state.top_stamina), int(state.bottom_stamina)]
        position_before = g.active_position_id()
        mount_frozen = {}
        windows_seen = 0

    # Exactly one active owner and a consistent slot picture; fighter identity and roles never change.
    func owner(g: BjjPositionGraphMatch) -> void:
        var active := g.active_position_id()
        t.check(label + ": one active owner agrees with the slots", [active, g._half_guard != null, g._sealed != null], [active, active == "half_guard", active == "half_guard"])
        t.check(label + ": identity and roles are preserved", g.roles().fields().fighter_by_role, {"top": TOP, "bottom": BOTTOM})
        if g._sealed != null:
            t.check(label + ": the protocol drives the graph's own gateway", [g._sealed._gateway == g._half_guard, g._half_guard._protocol_claimed], [true, true])
        if g._half_guard != null and g.status() == "active":
            t.check(label + ": the retained Mount segment is terminal and never a second owner", [g._gateway.is_terminal(), g._gateway.window_fields().open], [true, false])

    func on_event(event: String, g: BjjPositionGraphMatch, info: Dictionary) -> void:
        match event:
            "game_start":
                begin(g, str(info.get("label", label)))
            "after_open":
                _after_open(g, info)
            "after_seal":
                _after_seal(g, info)
            "after_command":
                _after_command(g, info)
            "game_end":
                _game_end(g)

    func _after_open(g: BjjPositionGraphMatch, info: Dictionary) -> void:
        var interval := int(g._interval_seconds)
        var new_events := g.events().slice(last_events)
        if bool(info.closed):
            t.check(label + ": a closing window is a terminal outcome of the current position, not an exit", [g.status(), new_events.map(func(e: Dictionary) -> String: return str(e.kind))],
                ["ended", ["terminal_outcome"]])
            t.check(label + ": a closing window consumed only the remaining clock", [int(g.state_fields().clock_seconds), last_clock - mini(interval, last_clock)], [0, last_clock - mini(interval, last_clock)])
            return
        windows_seen += 1
        t.coverage.windows += 1
        t.check(label + ": opening appends exactly one window_opened and nothing else", new_events.map(func(e: Dictionary) -> String: return str(e.kind)), ["window_opened"])
        t.check(label + ": the clock advanced exactly once by the interval", int(g.state_fields().clock_seconds), last_clock - mini(interval, last_clock))
        t.check(label + ": window ids are issued one at a time", int(g.window_fields().window_id), last_window_id + 1)
        var state := g.state_fields()
        if str(info.position) == "half_guard":
            # Half Guard v0 has no behavior flow, no drift and no recovery: opening a window moves the clock and nothing else. (Mount applies its own, existing
            # time-advance behavior effects when a window opens; that is measured, not gated.)
            t.check(label + ": opening a Half Guard window charged no stamina", [int(state.top_stamina), int(state.bottom_stamina)], stamina_before)
        owner(g)
        if not mount_frozen.is_empty():
            t.check(label + ": the previous position is frozen history", H.mount_views(g._gateway), mount_frozen)
        last_clock = int(state.clock_seconds)
        last_window_id = int(info.window_id)
        events_at_open = g.events().size()
        last_events = events_at_open
        if g._half_guard != null:
            hg_open_snapshot = g._half_guard.snapshot()
            protocol_events_at_open = g._sealed.protocol_events().size()
        if windows_seen <= 12 or windows_seen % 4 == 0:
            _probe_open(g, info)

    # Rejected commands must be refused with their codes and change the WHOLE authoritative state not at all.
    func _probes(g: BjjPositionGraphMatch, before: Dictionary, calls: Array) -> void:
        for call: Array in calls:
            var report: BjjMatchWindowGateway.Report = call[1]
            t.check(label + ": %s is refused" % call[0], [report.ok(), report.error], [false, call[2]])
            t.coverage.probes += 1
        t.check(label + ": the rejected battery changed nothing", H.everything(g), before)

    func _probe_open(g: BjjPositionGraphMatch, info: Dictionary) -> void:
        var wid := int(info.window_id)
        var fighter_id := str(info.fighter_id)
        var other := BOTTOM if fighter_id == TOP else TOP
        var role := str(info.role)
        var apparent := H.CF if role == "top" else H.UH
        var before := H.everything(g)
        if str(info.position) == "mount":
            _probes(g, before, [["a stale submit", g.submit(wid + 1, fighter_id), "stale_window"], ["an unknown fighter", g.submit(wid, "stranger"), "unknown_fighter"],
                ["the responder", g.submit(wid, other), "not_initiator"], ["a sealed seal in Mount", g.seal_intent(wid, fighter_id, apparent, "MEDIUM"), "wrong_active_position"],
                ["a sealed response in Mount", g.respond(wid, other, 1, H.HF, "MEDIUM"), "wrong_active_position"],
                ["a sealed timeout in Mount", g.apply_response_timeout(wid, 1, H.HF, "LOW"), "wrong_active_position"],
                ["a second window over the open one", g.open_window(), "window_already_open"]])
        else:
            _probes(g, before, [["a stale seal", g.seal_intent(wid + 1, fighter_id, apparent, "MEDIUM"), "stale_window"],
                ["a seal by the responder", g.seal_intent(wid, other, apparent, "MEDIUM"), "not_initiator"],
                ["an unknown technique", g.seal_intent(wid, fighter_id, "nonsense", "MEDIUM"), "unknown_action"],
                ["real equals apparent", g.seal_intent(wid, fighter_id, apparent, "MEDIUM", apparent), "feint_real_equals_apparent"],
                ["a response with no seal", g.respond(wid, other, 1, H.HF, "MEDIUM"), "no_sealed_intent"],
                ["a timeout with no seal", g.apply_response_timeout(wid, 1, H.HF, "LOW"), "no_sealed_intent"],
                ["a stale legacy submit", g.submit(wid + 1, fighter_id), "stale_window"], ["an unknown fighter", g.submit(wid, "stranger"), "unknown_fighter"],
                ["a second window over the open one", g.open_window(), "window_already_open"]])

    func _after_seal(g: BjjPositionGraphMatch, info: Dictionary) -> void:
        t.check(label + ": sealing changed no simulation state", g._half_guard.snapshot(), hg_open_snapshot)
        t.check(label + ": sealing advanced no clock and opened no window", [int(g.state_fields().clock_seconds), g.events().size()], [last_clock, events_at_open])
        t.check(label + ": a seal adds exactly one protocol event", g._sealed.protocol_events().size(), protocol_events_at_open + 1)
        var wid := int(info.window_id)
        var fighter_id := str(info.fighter_id)
        var other := BOTTOM if fighter_id == TOP else TOP
        var serial := int(g._sealed.executor_snapshot().serial)
        var apparent := str(g._sealed.executor_snapshot().pending.action_id)
        if windows_seen <= 12 or windows_seen % 4 == 0:
            var before := H.everything(g)
            _probes(g, before, [["a duplicate seal", g.seal_intent(wid, fighter_id, apparent, "MEDIUM"), "intent_already_sealed"], ["a bypassing legacy submit", g.submit(wid, fighter_id), "intent_pending"],
                ["a wrong serial", g.respond(wid, other, serial + 1, H.HF, "MEDIUM"), "intent_serial_mismatch"], ["the initiator answering itself", g.respond(wid, fighter_id, serial, H.HF, "MEDIUM"), "not_responder"],
                ["a stale response", g.respond(wid + 1, other, serial, H.HF, "MEDIUM"), "stale_window"],
                ["a wrong fallback", g.apply_response_timeout(wid, serial, "nonsense", "LOW"), "fallback_not_published"],
                ["a second window over the pending seal", g.open_window(), "window_already_open"]])

    func _after_command(g: BjjPositionGraphMatch, info: Dictionary) -> void:
        var report: BjjMatchWindowGateway.Report = info.report
        var new_events := g.events().slice(last_events)
        var kinds: Array = new_events.map(func(e: Dictionary) -> String: return str(e.kind))
        var label_exit := str(report.values.transition.raw_destination)
        t.check(label + ": exactly one accepted decision per resolution", kinds[0], "decision_accepted")
        t.check(label + ": at most one outcome event follows", kinds.size() <= 2, true)
        var after_position := g.active_position_id()
        if label_exit.is_empty():
            t.check(label + ": no exit means NO transition and the position is unchanged", [after_position, kinds.filter(func(k: String) -> bool: return k.begins_with("transition"))], [position_before, []])
        else:
            t.check(label + ": an exit produces exactly one transition outcome", kinds.slice(1).size(), 1)
            t.check(label + ": the position changes only through a committed transition", after_position != position_before, kinds.slice(1) == ["transition_committed"])
        if bool(report.values.ended) and label_exit.is_empty():
            t.check(label + ": a normal terminal ends the match from its current position", [g.status(), kinds.slice(1), after_position], ["ended", ["terminal_outcome"], position_before])
            if g.state_fields().get("submission_tapped", false):
                t.coverage.taps += 1
        if after_position != position_before:
            t.coverage.transitions += 1
            mount_frozen = H.mount_views(g._gateway)
            t.check(label + ": a transition opens no window and charges no stamina in the same step", [g.window_fields().open, int(g.state_fields().clock_seconds)], [false, last_clock])
        if g.status() == "halted_at_unsupported_transition":
            t.coverage.halts += 1
        t.check(label + ": the decision opened no additional window and did not move the clock", [int(g.window_fields().window_id), int(g.state_fields().clock_seconds)], [last_window_id, last_clock])
        # Half Guard exchange: each fighter is charged exactly what the settlement says, once
        if str(info.position) == "half_guard" and str(report.values.kind) == "exchange":
            var s: Dictionary = report.values.detail.settlement
            var initiator_top := str(s.initiator) == "top"
            var after := g.state_fields()
            var expected_top: int = int(stamina_before[0]) - (int(s.initiator_charged) if initiator_top else int(s.responder_charged))
            var expected_bottom: int = int(stamina_before[1]) - (int(s.responder_charged) if initiator_top else int(s.initiator_charged))
            t.check(label + ": stamina is settled exactly once per fighter (surcharge included)", [int(after.top_stamina), int(after.bottom_stamina)], [expected_top, expected_bottom])
            t.coverage.exchanges += 1
            if s.has("feint"):
                t.coverage.feints_accepted += 1
                t.check(label + ": a feint is one exchange: the real technique settled once", g.history_fields().initiated_action_history.back(), s.action_id)
        var state := g.state_fields()
        stamina_before = [int(state.top_stamina), int(state.bottom_stamina)]
        last_events = g.events().size()
        position_before = after_position
        owner(g)

    func _game_end(g: BjjPositionGraphMatch) -> void:
        if g.status() == "active":
            return
        t.coverage.ended += 1 if g.status() == "ended" else 0
        t.coverage.terminal_batteries += 1
        var halted := g.status() == "halted_at_unsupported_transition"
        var sealed_code := HALTED if halted else "match_ended"
        var before := H.everything(g)
        var calls: Array = [["open_window", g.open_window(), HALTED if halted else "terminal_exchange"], ["a timed window", g.open_window_for(0), HALTED if halted else "terminal_exchange"],
            ["a direct submit", g.submit(1, TOP, H.CF, H.HF, "MEDIUM", "MEDIUM"), HALTED if halted else "no_open_window"], ["a pass", g.submit(1, TOP), HALTED if halted else "no_open_window"],
            ["a seal", g.seal_intent(1, TOP, H.CF, "MEDIUM"), sealed_code], ["a feint seal", g.seal_intent(1, TOP, H.CF, "MEDIUM", H.KS), sealed_code], ["the public view", g.public_intent_view(), sealed_code],
            ["the sealed view", g.sealed_intent_view(TOP), sealed_code], ["a response", g.respond(1, BOTTOM, 1, H.HF, "MEDIUM"), sealed_code],
            ["a timeout", g.apply_response_timeout(1, 1, H.HF, "LOW"), sealed_code]]
        for call: Array in calls:
            var report: BjjMatchWindowGateway.Report = call[1]
            t.check(label + ": after the end, %s is refused" % call[0], [report.ok(), report.error], [false, call[2]])
        t.check(label + ": nothing was accepted after the end and the whole state is unchanged", H.everything(g), before)


var harness: RefCounted
var observer: Observer


func _initialize() -> void:
    harness = H.new()
    observer = Observer.new()
    observer.t = self
    var plans: Array = harness.find_plans(3)
    check("three real Mount entries into Half Guard were found", plans.size(), 3)
    var specs: Array = _specs(plans)
    for spec: Dictionary in specs:
        _run_and_verify(spec)
    _test_coverage_and_aggregates()
    if failures > 0:
        push_error("Match-flow invariants: %d / %d assertions failed" % [failures, checks])
        quit(1)
        return
    print("Match-flow invariants PASS: %d assertions" % checks)
    print("coverage: ", JSON.stringify(coverage))
    quit(0)


func _specs(plans: Array) -> Array:
    var specs: Array = []
    # Mount-only flows: repeated passes for the whole clock, a direct attacker, a submission chase (a real tap), and the legal-random walk (entries, halts)
    for mount: String in ["pass_only", "top_direct", "top_finish", "bottom_escape", "bottom_trap_roll"]:
        specs.append({"name": "mount %s" % mount, "mount": mount, "mount_defender": "first_available", "commit": "MEDIUM", "hg": "hg_pass", "defender": "bite", "seed": 0})
    for seed_value in range(6):
        specs.append({"name": "mount seeded_legal #%d" % seed_value, "mount": "seeded_legal", "mount_defender": "seeded", "commit": "HIGH" if seed_value % 2 == 1 else "MEDIUM",
            "hg": "hg_seeded_legal", "defender": "seeded", "seed": seed_value})
    # Full flows: a Mount escape, then every Half Guard attacker against the named defenders
    for attacker: String in ["hg_feint_when_eligible", "hg_prep_oriented", "hg_direct_cycle"]:
        for defender: String in ["bite", "call", "balanced", "fallback"]:
            specs.append({"name": "mount bottom_escape -> %s / %s" % [attacker, defender], "mount": "bottom_escape", "mount_defender": "first_available", "commit": "MEDIUM",
                "hg": attacker, "defender": defender, "seed": 0})
    # Half Guard from real entries
    var index := 0
    for plan: Dictionary in plans:
        for attacker: String in H.HG_ATTACKERS:
            for defender: String in ["bite", "call", "fallback", "seeded"]:
                var seeds := 2 if attacker == "hg_seeded_legal" or defender == "seeded" else 1
                for seed_value in range(seeds):
                    specs.append({"name": "entry %d %s / %s #%d" % [index, attacker.trim_prefix("hg_"), defender, seed_value], "plan": plan, "hg": attacker, "defender": defender,
                        "commit": "HIGH" if seed_value == 1 else "MEDIUM", "seed": seed_value})
        index += 1
    return specs


func _run_and_verify(spec: Dictionary) -> void:
    var run := spec.duplicate()
    run["max_windows"] = MAX_WINDOWS
    var label := str(spec.name)
    # with the observer (live invariants), then without it: the digests and the final authoritative state must be identical (observing and probing change nothing)
    harness.observer = Callable()
    var plain: Dictionary = harness.play(run)
    var probe_graph: BjjPositionGraphMatch = plain.graph
    var plain_state := H.everything(probe_graph)
    coverage.games += 1
    var observed_graph: BjjPositionGraphMatch
    harness.observer = Callable(self, "_dispatch")
    # the observer needs a begin() on the very graph the harness builds: the harness announces it through the first event
    _pending_label = label
    var observed: Dictionary = harness.play(run)
    observed_graph = observed.graph
    harness.observer = Callable()
    check(label + ": the observer and its rejected probes changed nothing (identical trace)", [observed.digest, observed.outcome], [plain.digest, plain.outcome])
    check(label + ": the final authoritative state is identical", H.everything(observed_graph), plain_state)
    check(label + ": no policy error (a refused command the harness did not intend)", observed.policy_errors, [])
    check(label + ": a finished game ends from its CURRENT position, never by a forced transition", [observed.outcome.begins_with("max_windows") or observed.status != "active", observed.windows <= MAX_WINDOWS], [true, true])
    check(label + ": transitions preserved identity, stamina and match time", observed.continuity_violations, 0)
    check(label + ": Half Guard v0 has no recovery rule: its stamina never rose", observed.stamina_increases_half_guard, 0)
    # histories: one history exchange per resolved exchange of the ACTIVE segment
    if not spec.has("plan"):
        var window_events: int = observed_graph.events().filter(func(e: Dictionary) -> bool: return e.kind == "window_opened").size()
        check(label + ": exactly one window per harness window (no hidden window)", window_events, observed.windows)
    var active_exchanges: int = observed.half_guard_exchanges if observed.position_end == "half_guard" else observed.mount_exchanges
    check(label + ": one history exchange per resolved exchange of the active segment", observed_graph.history_fields().initiated_action_history.size(), active_exchanges)
    check(label + ": every accepted feint is counted once and classified once", [observed.feints_accepted, observed.feints_accepted], [observed.feints_bit + observed.feints_not_bit,
        observed.feints_effective + observed.feints_neutral + observed.feints_punished])
    check(label + ": the published fallback's only consequence is the existing undercommitment step", observed.timeout_other_modifiers, 0)
    coverage.fallbacks += int(observed.timeouts)
    if not spec.has("plan"):
        _replay_mount_phase(label, observed, observed_graph)


var _pending_label: String = ""


func _dispatch(event: String, g: BjjPositionGraphMatch, info: Dictionary) -> void:
    var enriched := info
    if event == "game_start":
        enriched = info.duplicate()
        enriched["label"] = _pending_label
    observer.on_event(event, g, enriched)


# The Mount phase of a game replayed on a BARE Mount gateway with the same commands: the graph adds no settlement of its own (no duplicate stamina settlement).
func _replay_mount_phase(label: String, rec: Dictionary, g: BjjPositionGraphMatch) -> void:
    var twin := BjjMatchWindowGateway.create({"rules": H.rules()}, TOP, BOTTOM).gateway
    var applied := 0
    for entry: Dictionary in rec.trace:
        var op := str(entry.op)
        if op == "open":
            var opened := twin.open_window()
            if not opened.ok() or opened.values.get("closed", false):
                break
        elif op == "pass" and str(entry.position) == "mount":
            check(label + ": a Mount pass settles like the bare gateway's", twin.submit(int(twin.window_fields().window_id), str(twin.window_fields().fighter_id)).ok(), true)
            applied += 1
        elif op == "mount_exchange":
            var fighter_id := str(twin.window_fields().fighter_id)
            var report := twin.submit(int(twin.window_fields().window_id), fighter_id, str(entry.action), str(entry.response), str(entry.commitment), "")
            check(label + ": a Mount exchange is accepted by the bare gateway too", report.ok(), true)
            applied += 1
        else:
            break
    check(label + ": the Mount segment equals the bare gateway's after the same commands (one settlement each)", H.mount_views(g._gateway), H.mount_views(twin))
    coverage.mount_replays += 1
    coverage.mount_windows_replayed += applied


func _test_coverage_and_aggregates() -> void:
    # The games must have exercised every property they claim to test (guards against a vacuous run).
    check("a meaningful number of games was driven", coverage.games >= 100, true)
    check("many windows were observed", coverage.windows >= 1500, true)
    check("rejected commands were probed in bulk", coverage.probes >= 2000, true)
    check("Mount -> Half Guard transitions happened for real", coverage.transitions >= 10, true)
    check("unsupported-destination halts happened for real", coverage.halts >= 10, true)
    check("matches ended from their current position (tap or clock)", coverage.ended >= 10, true)
    check("a real submission tap occurred", coverage.taps >= 1, true)
    check("Half Guard exchanges and feints were settled through the sealed protocol", [coverage.exchanges >= 100, coverage.feints_accepted >= 20], [true, true])
    check("published-fallback timeouts were exercised", coverage.fallbacks >= 20, true)
    check("Mount phases were replayed on a bare gateway", coverage.mount_replays >= 10, true)
    check("every ended or halted game received the full post-end command battery", coverage.terminal_batteries >= 20, true)
