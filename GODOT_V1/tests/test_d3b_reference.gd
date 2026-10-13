extends SceneTree
const C = preload("res://scripts/positions/mount/mount_catalog.gd")
var scenarios: int = 0
var operations: int = 0
var excluded: int = 0
func full_state(m: BjjMountMatch) -> Dictionary:
    var values := m.lifecycle_fields()
    values["controller"] = m.d3b.fields() if m.d3b != null else null
    if not m.ended:
        values["legal_actions"] = m.legal_actions().ids
        var responses: Dictionary = {}
        for action: String in m.legal_actions().ids:
            responses[action] = m.legal_responses(action).ids
        values["legal_responses"] = responses
    return values
func _initialize() -> void:
    var verifier: SceneTree = load("res://tests/test_exchange_reference.gd").new()
    var fixture := FileAccess.open("res://tests/generated/d3b_reference.jsonl", FileAccess.READ)
    if fixture == null:
        push_error("Generate D3-B oracle first")
        verifier.free()
        quit(1)
        return
    while not fixture.eof_reached():
        var line := fixture.get_line()
        if line.is_empty(): continue
        var c: Dictionary = JSON.parse_string(line)
        scenarios += 1
        operations += c.steps.size()
        for replay_pass in range(2):
            var m := BjjMountMatch.new()
            m.rules = BjjExchangeRules.build(c.settings).rules
            m.initial_clock = int(c.initial.initial_clock)
            m.clock_seconds = int(c.initial.clock_seconds)
            m.position = BjjMountPosition.new(float(c.initial.control_axis))
            m.top = BjjStaminaPool.create(int(c.initial.top_stamina), int(c.initial.top_maximum)).pool
            m.bottom = BjjStaminaPool.create(int(c.initial.bottom_stamina), int(c.initial.bottom_maximum)).pool
            m.submission_stage = str(c.stage)
            m.configure_recover(true)
            if c.production:
                m.d3b = BjjD3BController.create(m).controller
            verifier.compare(c.label + " initial", full_state(m), c.initial)
            for i in range(c.steps.size()):
                var step: Dictionary = c.steps[i]
                var command: Dictionary = step.command
                var label := "%s pass %d step %d %s" % [c.label, replay_pass, i, command.op]
                var before := full_state(m)
                var error: String = ""
                var expected_fields: Variant = null
                match str(command.op):
                    "set":
                        var pool := m.top if command.side == "top" else m.bottom
                        error = pool.set_current(int(command.value))
                    "side": m.initiator = str(command.value)
                    "free":
                        m.free_initiative_pending = true
                        m.free_initiative_beneficiary = str(command.side)
                    "consume":
                        var r := m.consume_free_window()
                        error = r.error
                        expected_fields = r.fields()
                    "advance":
                        var r := m.recovery_advance(int(command.duration))
                        error = r.error
                        expected_fields = r.fields()
                    "controller":
                        var r := m.d3b.decide(m)
                        error = r.error
                        expected_fields = r.fields()
                    "hold":
                        var r := m.recovery_hold()
                        error = r.error
                        expected_fields = r.fields()
                    "reset":
                        var r := m.reset_window()
                        error = r.error
                        expected_fields = r.fields()
                    "attempt":
                        var r := m.attempt(BjjExchangeResult.Request.new(str(command.action), str(command.response), str(command.commitment), "MEDIUM"))
                        error = r.error
                        expected_fields = r.fields()
                    "legacy":
                        var r := m.decide_legacy(str(command.action), str(command.response))
                        error = r.error
                        expected_fields = r.fields()
                    "bottom":
                        var r := m.bottom_decision(str(command.get("action", "")), str(command.get("response", "")), "MEDIUM")
                        error = r.error
                        expected_fields = r.fields()
                    _:
                        push_error("Unknown oracle command")
                        quit(1)
                        return
                if step.terminal_override:
                    verifier.compare(label + " approved terminal rejection", not error.is_empty(), true)
                    verifier.compare(label + " unchanged", full_state(m), before)
                    if replay_pass == 0: excluded += 1
                    continue
                verifier.compare(label + " rejected", not error.is_empty(), step.rejected)
                if step.rejected:
                    verifier.compare(label + " rejected unchanged", full_state(m), before)
                else:
                    verifier.compare(label + " result", expected_fields, step.expected)
                verifier.compare(label + " state", full_state(m), step.state)
    print("D3-B/lifecycle: %d scenarios, %d operations, two replays, %d comparisons, %d mismatches, %d excluded terminal operations" % [scenarios, operations, verifier.checks, verifier.mismatches, excluded])
    var failures: int = verifier.mismatches
    verifier.free()
    quit(0 if failures == 0 else 1)
