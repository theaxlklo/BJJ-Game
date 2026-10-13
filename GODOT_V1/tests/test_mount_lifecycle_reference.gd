extends SceneTree
var scenarios: int = 0
var operations: int = 0
func _initialize() -> void:
    var verifier: SceneTree = load("res://tests/test_exchange_reference.gd").new()
    var fixture := FileAccess.open("res://tests/generated/mount_lifecycle_reference.jsonl", FileAccess.READ)
    if fixture == null:
        push_error("Generate Mount lifecycle oracle first")
        verifier.free()
        quit(1)
        return
    while not fixture.eof_reached():
        var line := fixture.get_line()
        if line.is_empty():
            continue
        var c: Dictionary = JSON.parse_string(line)
        scenarios += 1
        operations += c.steps.size()
        for replay_pass in range(2):
            var m := BjjMountMatch.new()
            m.initial_clock = int(c.initial.initial_clock)
            m.clock_seconds = int(c.initial.clock_seconds)
            m.top = BjjStaminaPool.create(int(c.initial.top_stamina), int(c.initial.top_maximum)).pool
            m.bottom = BjjStaminaPool.create(int(c.initial.bottom_stamina), int(c.initial.bottom_maximum)).pool
            m.top_behavior = str(c.initial.top_behavior)
            m.bottom_behavior = str(c.initial.bottom_behavior)
            m.configure_recover(bool(c.recover), str(c.baseline))
            verifier.compare(c.label + " initial", m.lifecycle_fields(), c.initial)
            for i in range(c.steps.size()):
                var step: Dictionary = c.steps[i]
                var label := "%s pass %d step %d" % [c.label, replay_pass, i]
                var before := m.lifecycle_fields()
                var result := m.recovery_advance(int(step.duration)) if c.recover else m.advance(int(step.duration))
                verifier.compare(label + " rejection", not result.ok(), step.rejected)
                if not result.ok():
                    verifier.compare(label + " unchanged", m.lifecycle_fields(), before)
                else:
                    verifier.compare(label + " result", result.fields(), step.result)
                verifier.compare(label + " state", m.lifecycle_fields(), step.state)
    print("Mount advancement: %d scenarios, %d operations, replayed twice, %d comparisons, %d mismatches" % [scenarios, operations, verifier.checks, verifier.mismatches])
    var mismatches: int = verifier.mismatches
    verifier.free()
    quit(0 if mismatches == 0 else 1)
