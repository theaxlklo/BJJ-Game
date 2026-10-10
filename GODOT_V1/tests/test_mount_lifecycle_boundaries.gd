extends SceneTree
const C = preload("res://scripts/positions/mount/mount_catalog.gd")
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
    var raw := BjjMountMatch.new()
    var raw_before := raw.lifecycle_fields()
    check("production prerequisites rejected", raw.configure_production_recover().ok(), false)
    check("configuration rejection unchanged", raw.lifecycle_fields(), raw_before)
    var settings := BjjProductionStaminaPolicy.settings()
    settings.enable_v02_setup = true
    settings.enable_v04_commitment_semantics = true
    raw.rules = BjjExchangeRules.build(settings).rules
    check("production configured explicitly", raw.configure_production_recover().ok(), true)
    check("production Rule 1", raw.rules.rule1, true)
    check("production Rule 2", raw.rules.rule2, false)
    var split := BjjMountMatch.new()
    var combined := BjjMountMatch.new()
    for state: BjjMountMatch in [split, combined]:
        state.top.set_current(50)
        state.bottom.set_current(50)
        state.top_behavior = "CONSERVE"
        state.bottom_behavior = "ESCAPE"
    for i in range(5):
        split.advance(1)
    combined.advance(5)
    for key: String in ["axis", "control_axis", "clock_seconds", "top_stamina", "bottom_stamina", "top_remainder", "bottom_remainder", "top_band", "bottom_band"]:
        check("split/combined " + key, split.lifecycle_fields()[key], combined.lifecycle_fields()[key])
    raw.clock_seconds = 1
    check("truncated terminal advance", raw.advance(5).ok(), true)
    check("terminal clock", raw.clock_seconds, 0)
    check("reference zero-time timeout advance", raw.advance(0).ok(), true)
    var terminal_before := raw.lifecycle_fields()
    check("timeout exchange still rejected", raw.attempt(BjjExchangeResult.Request.new(C.TOP_HIGH_MOUNT_CLIMB, C.BOTTOM_RESPONSE_FOREARM_FRAME, "MEDIUM")).ok(), false)
    check("timeout exchange unchanged", raw.lifecycle_fields(), terminal_before)
    print("Mount lifecycle native: %d assertions, %d failures" % [checks, failures])
    quit(0 if failures == 0 else 1)
