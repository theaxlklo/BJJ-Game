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
    for config: Dictionary in [{"unknown":1}, {"clock":0}, {"interval":0}, {"axis":NAN}, {"axis":INF}, {"axis":0.0}, {"top_stamina":-1}, {"bottom_stamina":101}, {"capacity":0}, {"clock":1.5}, {"production":true}]:
        check("factory rejects " + str(config), BjjMountMatch.create(config).ok(), false)
    check("factory default", BjjMountMatch.create({}).ok(), true)
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
    var production := BjjMountMatch.new()
    var flags := BjjProductionStaminaPolicy.settings()
    flags.enable_v02_setup = true
    flags.enable_v04_commitment_semantics = true
    production.rules = BjjExchangeRules.build(flags).rules
    production.bottom.set_current(25)
    check("production full opt-in", production.configure_production().ok(), true)
    production.bottom_behavior = "CONSERVE"
    production.advance(25)
    production.bottom.set_current(25)
    production.initiator = "bottom"
    production.d3b.decide(production)
    var token_before := production.d3b.fields()
    check("production repeated opt-in", production.configure_production().ok(), true)
    check("reconfiguration cannot refill token", production.d3b.fields(), token_before)
    check("production cannot silently disable RECOVER", production.configure_recover(false).ok(), false)
    var state_before := production.lifecycle_fields()
    check("invalid combined decision", production.bottom_decision("INVALID", "INVALID").ok(), false)
    check("combined rejection preserves match", production.lifecycle_fields(), state_before)
    check("combined rejection preserves token", production.d3b.fields(), token_before)
    var window := production.next_window(0)
    check("zero-time normal window", window.ok(), true)
    check("normal window is not free", window.values.free, false)
    production.free_initiative_pending = true
    production.free_initiative_beneficiary = "bottom"
    state_before = production.lifecycle_fields()
    window = production.next_window(5)
    check("free window succeeds", window.ok(), true)
    check("free window flag", window.values.free, true)
    check("free window no clock", production.clock_seconds, state_before.clock_seconds)
    check("free window no flow", production.bottom.current, state_before.bottom_stamina)
    check("free window locks", production.bottom_decision().values.decision.kind, "LOCKOUT_HOLD")
    print("D3-B native: %d assertions, %d failures" % [checks, failures])
    quit(0 if failures == 0 else 1)
