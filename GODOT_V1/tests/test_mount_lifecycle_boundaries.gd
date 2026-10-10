extends SceneTree
var checks: int = 0
var failures: int = 0
func check(label: String, actual: Variant, expected: Variant) -> void:
    checks += 1
    if actual != expected:
        failures += 1
        push_error("%s: %s != %s" % [label, actual, expected])
func _initialize() -> void:
    var m := BjjMountMatch.new()
    for duration: int in [-1, -20]:
        var before := m.lifecycle_fields()
        check("negative advancement", m.advance(duration).ok(), false)
        check("rejected advancement unchanged", m.lifecycle_fields(), before)
    m.bottom_meter.remainder_units = BjjBehaviorStaminaPolicy.INT_MAX
    var before := m.lifecycle_fields()
    m.bottom_behavior = "CONSERVE"
    before = m.lifecycle_fields()
    check("second fighter overflow", m.advance(5).ok(), false)
    check("second fighter error rolls back first", m.lifecycle_fields(), before)
    m.bottom_meter.remainder_units = 0
    check("zero interval", m.advance(0).ok(), true)
    check("zero interval clock", m.clock_seconds, 300)
    m.position.axis = NAN
    check("nonfinite drift rejection", m.advance(1).ok(), false)
    m.position.axis = 1.5
    m.top_behavior = "ESCAPE"
    check("wrong side behavior", m.advance(5).ok(), false)
    m.top_behavior = "HOLD"
    m.bottom_behavior = "PROTECT"
    check("advance succeeds", m.advance(5).ok(), true)
    check("clock advances", m.clock_seconds, 295)
    check("raw advance stamina", m.bottom.current, 100)
    check("raw policy unchanged", m.recover_enabled, false)
    check("raw commitment", m.selected_commitment(), "MEDIUM")
    m.initiator = "bottom"
    m.bottom.set_current(25)
    check("RECOVER selection", m.configure_recover(true).ok(), true)
    check("exhausted behavior", m.recovery_behavior(), "CONSERVE")
    check("exhausted commitment", m.selected_commitment(), "LOW")
    m.bottom.set_current(34)
    check("hysteresis retains recovery", m.recovery_behavior(), "CONSERVE")
    m.bottom.set_current(35)
    check("clear restores baseline", m.recovery_behavior(), "ESCAPE")
    check("clear commitment", m.selected_commitment(), "MEDIUM")
    m.initiator = "top"
    check("Top baseline commitment", m.selected_commitment(), "MEDIUM")
    print("Mount lifecycle native: %d assertions, %d failures" % [checks, failures])
    quit(0 if failures == 0 else 1)
