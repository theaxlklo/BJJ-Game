extends SceneTree

var checked: int = 0
var failures: int = 0

func _initialize() -> void:
    var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string("res://tests/generated/stamina_reference.json"))
    if not parsed is Dictionary or int(parsed.get("schema", 0)) != 1:
        push_error("Generate schema-1 Python stamina fixtures first")
        quit(1)
        return
    var data: Dictionary = parsed
    for x: Dictionary in data.constructors:
        var created := BjjStaminaPool.create(int(x.current), int(x.maximum))
        compare("constructor %s" % x, not created.ok(), x.rejected)
    for c: Dictionary in data.costs:
        var built := BjjStaminaCostPolicy.build(integer_config(c.config))
        compare("cost config %s" % c.config, not built.ok(), c.rejected)
        if not built.ok():
            continue
        for x: Dictionary in c.cases:
            var funding := built.policy.determine(str(x.requested), int(x.available))
            compare("funding %s" % x, not funding.ok(), x.rejected)
            if funding.ok():
                compare("funding result %s" % x, funding.fields(), x.result)
    for c: Dictionary in data.flow_configs:
        var built := BjjBehaviorStaminaPolicy.build(int(c.quantum), integer_config(c.rates))
        compare("flow config %s" % c, not built.ok(), c.rejected)
    var flow := BjjBehaviorStaminaPolicy.defaults()
    for replay_pass in range(2):
        for index in range(data.traces.size()):
            var t: Dictionary = data.traces[index]
            var trace_flow: BjjBehaviorStaminaPolicy = flow
            if t.has("policy"):
                trace_flow = BjjBehaviorStaminaPolicy.build(int(t.policy.quantum), integer_config(t.policy.rates)).policy
            var pool := BjjStaminaPool.create(int(t.current), int(t.maximum)).pool
            var meter := BjjBehaviorStaminaPolicy.Meter.new(int(t.remainder))
            for step_index in range(t.steps.size()):
                var x: Dictionary = t.steps[step_index]
                var op: Dictionary = x.operation
                var label := "replay[%d] trace[%d] step[%d] %s" % [replay_pass, index, step_index, op]
                var before := snapshot(pool, meter)
                var error := ""
                var result: Dictionary = {}
                match str(op.kind):
                    "set":
                        error = pool.set_current(int(op.value))
                    "spend":
                        var r := pool.spend_up_to(int(op.value))
                        error = r.error
                        result = r.spend_fields()
                    "recover":
                        var r := pool.recover_up_to(int(op.value))
                        error = r.error
                        result = r.recovery_fields()
                    "flow":
                        var r := trace_flow.apply(pool, str(op.behavior), int(op.value), meter)
                        error = r.error
                        result = r.fields()
                    _:
                        push_error("Unknown fixture operation")
                        quit(1)
                        return
                compare(label + " rejected", not error.is_empty(), x.rejected)
                if bool(x.rejected):
                    compare(label + " unchanged", snapshot(pool, meter), before)
                else:
                    compare(label + " result", result, x.result)
                compare(label + " state", snapshot(pool, meter), x.state)
    for x: Dictionary in data.exhaustion:
        var r := BjjExhaustionPolicy.exchange(str(x.initiator), str(x.responder))
        compare("exhaustion %s" % x, r.fields(), x)
    # Historical snapshot is independent of later spending/recovery.
    var a := BjjStaminaPool.create(26).pool
    var b := BjjStaminaPool.create(25).pool
    var captured := BjjExhaustionPolicy.exchange(a.band, b.band)
    a.spend_up_to(12)
    b.recover_up_to(75)
    compare("historical initiator", captured.initiator_modifier, 0)
    compare("historical responder", captured.responder_modifier, 1)
    compare("historical net", captured.modifier, 1)
    compare("invalid initiator band", BjjExhaustionPolicy.exchange("INVALID", b.band).ok(), false)
    compare("invalid responder band", BjjExhaustionPolicy.exchange(a.band, "INVALID").ok(), false)
    # Native integer boundary failures must leave both mutable objects untouched.
    var meter := BjjBehaviorStaminaPolicy.Meter.new(4)
    var initial := snapshot(a, meter)
    compare("duration product overflow", flow.apply(a, "CONSERVE", 9223372036854775807, meter).ok(), false)
    compare("overflow unchanged", snapshot(a, meter), initial)
    compare("missing pool", flow.apply(null, "HOLD", 1, meter).ok(), false)
    compare("missing meter", flow.apply(a, "HOLD", 1, null).ok(), false)
    print("Stamina parity: %d checks, %d failures" % [checked, failures])
    quit(0 if failures == 0 else 1)

func snapshot(pool: BjjStaminaPool, meter: BjjBehaviorStaminaPolicy.Meter) -> Dictionary:
    return {"current": pool.current, "maximum": pool.maximum, "band": pool.band,
        "enter": pool.exhaustion_enter_threshold, "clear": pool.exhaustion_recover_threshold,
        "remainder": meter.remainder_units}

func compare(label: String, actual: Variant, expected: Variant) -> void:
    checked += 1
    if actual is Dictionary and expected is Dictionary:
        if actual.size() != expected.size():
            fail(label + " keys", actual.keys(), expected.keys())
        for key: String in expected:
            if not actual.has(key):
                fail(label + "." + key, "missing", expected[key])
            else:
                compare(label + "." + key, actual[key], expected[key])
        return
    # JSON numbers are floats; the authoritative outputs must remain native ints.
    if expected is float:
        if not actual is int or actual != int(expected):
            fail(label + " (integer expected)", actual, expected)
        return
    if actual != expected:
        fail(label, actual, expected)

func fail(label: String, actual: Variant, expected: Variant) -> void:
    failures += 1
    if failures <= 20:
        print("FAIL %s actual=%s expected=%s" % [label, actual, expected])

# JSON loses integer tags. Restore integral fixture values only at the test boundary.
func integer_config(values: Dictionary) -> Dictionary:
    var restored: Dictionary = {}
    for key: String in values:
        var value: Variant = values[key]
        restored[key] = int(value) if value is float and value == floor(value) else value
    return restored
