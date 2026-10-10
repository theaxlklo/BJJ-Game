extends SceneTree
var checks: int = 0
var failures: int = 0
const C = preload("res://scripts/positions/mount/mount_catalog.gd")
func check(label: String, actual: Variant, expected: Variant) -> void:
    checks += 1
    if actual != expected:
        failures += 1
        push_error("%s: %s != %s" % [label, actual, expected])
func _initialize() -> void:
    var m := BjjMountMatch.new()
    m.bottom.set_current(25)
    var controller := BjjD3BController.create(m).controller
    var before := controller.fields()
    check("Top rejects", controller.decide(m).ok(), false)
    check("Top rejection preserves token", controller.fields(), before)
    m.initiator = "bottom"
    check("initial Exhausted is unarmed", controller.decide(m).kind, "UNARMED")
    m.bottom.set_current(35)
    controller.observe_advance(m)
    check("clear arms", controller.armed, true)
    check("clear resets token", controller.token_consumed, false)
    check("armed clear window", controller.decide(m).kind, "ARMED_NORMAL")
    m.bottom.set_current(25)
    check("first Exhausted window token", controller.decide(m).kind, "TOKEN")
    check("token consumed", controller.token_consumed, true)
    check("next Exhausted window locks", controller.decide(m).kind, "LOCKOUT_HOLD")
    before = m.lifecycle_fields()
    var hold := m.recovery_hold()
    check("hold succeeds", hold.ok(), true)
    check("hold initiative", m.initiator, "top")
    for key: String in ["clock_seconds", "axis", "top_stamina", "bottom_stamina", "top_remainder", "bottom_remainder", "submission_stage", "americana_tier", "trap_tier"]:
        check("hold preserves " + key, m.lifecycle_fields()[key], before[key])
    check("hold differs from RESET", m.history.reset_window_history.size(), 0)
    check("hold recorded", m.history.recovery_hold_history.size(), 1)
    before = m.lifecycle_fields()
    check("Top hold rejects", m.recovery_hold().ok(), false)
    check("Top hold unchanged", m.lifecycle_fields(), before)
    m.initiator = "bottom"
    check("genuine RESET", m.reset_window().ok(), true)
    check("RESET recorded", m.history.reset_window_history, ["bottom"])
    m.bottom.set_current(35)
    controller.observe_advance(m)
    m.initiator = "bottom"
    check("clear unlocks", controller.decide(m).kind, "ARMED_NORMAL")
    m.bottom.set_current(25)
    check("new episode token", controller.decide(m).kind, "TOKEN")
    m.free_initiative_pending = true
    m.free_initiative_beneficiary = "top"
    before = m.lifecycle_fields()
    check("mismatched free beneficiary", m.consume_free_window().ok(), false)
    check("free rejection unchanged", m.lifecycle_fields(), before)
    m.free_initiative_beneficiary = "bottom"
    check("free window consumed", m.consume_free_window().ok(), true)
    check("free flag cleared", m.free_initiative_pending, false)
    m.clock_seconds = 0
    before = m.lifecycle_fields()
    check("terminal RESET rejects", m.reset_window().ok(), false)
    check("terminal hold rejects", m.recovery_hold().ok(), false)
    check("terminal handoff unchanged", m.lifecycle_fields(), before)
    print("D3-B native: %d assertions, %d failures" % [checks, failures])
    quit(0 if failures == 0 else 1)
