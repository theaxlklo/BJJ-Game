extends SceneTree

var checks: int = 0
var mismatches: int = 0
var scenarios: int = 0
var operations: int = 0
var terminal_boundaries: int = 0

func _initialize() -> void:
    var fixture := FileAccess.open("res://tests/generated/exchange_reference.jsonl", FileAccess.READ)
    if fixture == null:
        push_error("Generate exchange Python oracle first")
        quit(1)
        return
    var header: Dictionary = JSON.parse_string(fixture.get_line())
    compare("schema", header.schema, 1)
    compare("production selection", BjjProductionStaminaPolicy.settings(), header.production_settings)
    for c: Dictionary in header.config_cases:
        compare("config %s" % c.settings, not BjjExchangeRules.build(c.settings).ok(), bool(c.rejected) or bool(c.unsupported))
    while not fixture.eof_reached():
        var line := fixture.get_line()
        if line.is_empty():
            continue
        var c: Dictionary = JSON.parse_string(line)
        scenarios += 1
        operations += c.steps.size()
        for replay_pass in range(2):
            var state := create_state(c)
            compare(c.label + " initial", full_state(state), c.initial)
            for index in range(c.steps.size()):
                var x: Dictionary = c.steps[index]
                var command := BjjExchangeResult.Request.new(str(x.request.action_id), str(x.request.response_id),
                    str(x.request.commitment), str(x.request.response_commitment))
                var label := "%s replay %d op %d" % [c.label, replay_pass, index]
                var before := full_state(state)
                var r := state.attempt(command)
                if bool(x.terminal_override):
                    compare(label + " approved atomic terminal rejection", r.ok(), false)
                    compare(label + " terminal unchanged", full_state(state), before)
                    if replay_pass == 0:
                        terminal_boundaries += 1
                    continue
                compare(label + " rejected", not r.ok(), x.rejected)
                if bool(x.rejected):
                    compare(label + " unchanged", full_state(state), before)
                elif r.ok():
                    compare(label + " result", r.fields(), x.expected)
                compare(label + " state", full_state(state), x.state)
    print("Exchange oracle: %d independent scenarios, %d operations; replayed twice; %d field comparisons, %d mismatches; %d approved terminal boundary operations" % [
        scenarios, operations, checks, mismatches, terminal_boundaries])
    quit(0 if mismatches == 0 else 1)

func create_state(c: Dictionary) -> BjjMountExchange:
    var s := BjjMountExchange.new()
    s.rules = BjjExchangeRules.build(c.settings).rules
    var costs: Dictionary = {}
    for key: String in c.costs:
        costs[key] = int(c.costs[key])
    s.cost_policy = BjjStaminaCostPolicy.build(costs).policy
    s.top.set_current(int(c.top_initial))
    s.bottom.set_current(int(c.bottom_initial))
    for value: Variant in c.top_history:
        s.top.set_current(int(value))
    for value: Variant in c.bottom_history:
        s.bottom.set_current(int(value))
    s.position.axis = float(c.initial.control_axis)
    s.position.band = int(c.initial.band)
    s.position.broken = bool(c.initial.broken)
    if s.position.broken:
        s.position.crossing_axis = float(c.initial.crossing_axis)
    s.initiator = str(c.initial.initiator)
    s.clock_seconds = int(c.initial.clock_seconds)
    s.americana_tier = int(c.initial.americana_tier)
    s.trap_tier = int(c.initial.trap_tier)
    s.submission_stage = str(c.initial.submission_stage)
    s.submission_tapped = bool(c.initial.submission_tapped)
    s.exit_destination = str(c.initial.exit_destination)
    s.exit_reason = str(c.initial.exit_reason)
    s.top_behavior = str(c.top_behavior)
    s.bottom_behavior = str(c.bottom_behavior)
    return s

func full_state(s: BjjMountExchange) -> Dictionary:
    var values := s.snapshot().fields()
    values["history"] = s.history.fields()
    return values

func compare(label: String, actual: Variant, expected: Variant) -> void:
    if actual is Dictionary and expected is Dictionary:
        compare(label + " keys", actual.keys().size(), expected.keys().size())
        for key: Variant in expected:
            if not actual.has(key):
                fail(label + "." + str(key), "missing", expected[key])
            else:
                compare(label + "." + str(key), actual[key], expected[key])
        return
    if actual is Array and expected is Array:
        compare(label + " length", actual.size(), expected.size())
        for i in range(mini(actual.size(), expected.size())):
            compare(label + "[%d]" % i, actual[i], expected[i])
        return
    checks += 1
    if expected is bool:
        if not actual is bool or actual != expected:
            fail(label, actual, expected)
    elif expected is float or expected is int:
        # JSON parses numbers as double. Integers must remain typed integers at runtime;
        # float axis values have the same 1e-10 contract as the frozen Mount corpus.
        if not (actual is int or actual is float) or absf(float(actual)-float(expected)) > 0.0000000001:
            fail(label, actual, expected)
        if float(expected) == floorf(float(expected)) and not label.contains("axis"):
            if not actual is int:
                fail(label + " integer type", actual, "int")
    elif actual != expected:
        fail(label, actual, expected)

func fail(label: String, actual: Variant, expected: Variant) -> void:
    mismatches += 1
    if mismatches <= 20:
        push_error("%s: got %s expected %s" % [label, actual, expected])
