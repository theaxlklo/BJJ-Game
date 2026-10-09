extends SceneTree

var checks: int = 0
var failures: int = 0
const C = preload("res://scripts/positions/mount/mount_catalog.gd")

func check(label: String, actual: Variant, expected: Variant) -> void:
    checks += 1
    if actual != expected:
        failures += 1
        push_error("%s: got %s expected %s" % [label, actual, expected])

func request(action: String = C.TOP_HIGH_MOUNT_CLIMB, response: String = C.BOTTOM_RESPONSE_FOREARM_FRAME,
        commitment: String = "MEDIUM", response_commitment: String = "") -> BjjExchangeResult.Request:
    return BjjExchangeResult.Request.new(action, response, commitment, response_commitment)

func rejected(label: String, state: BjjMountExchange, command: BjjExchangeResult.Request) -> void:
    var before := state.snapshot().fields()
    var result := state.attempt(command)
    check(label + " rejection", result.ok(), false)
    check(label + " unchanged", state.snapshot().fields(), before)

func _initialize() -> void:
    check("missing state", BjjMountExchange.process(null, request()).ok(), false)
    for flag: String in ["enable_v03_submissions", "enable_stamina_settlement_rules",
            "enable_unfunded_responder_cost_waiver", "enable_supplemental_hold_settlement", "enable_v04b_recognition"]:
        check("prerequisite " + flag, BjjExchangeRules.build({flag: true}).ok(), false)
    check("unknown configuration", BjjExchangeRules.build({"typo": false}).ok(), false)
    check("nonboolean configuration", BjjExchangeRules.build({"enable_v02_setup": 1}).ok(), false)
    check("Recognition unsupported", BjjExchangeRules.build({"enable_v04_commitment_semantics":true,
        "enable_v04b_recognition":true}).ok(), false)
    check("stalling unsupported", BjjExchangeRules.build({"enable_v02_setup":true,
        "enable_v03_submissions":true, "enable_v03b_stalling":true}).ok(), false)
    check("production needs explicit v04", BjjExchangeRules.build(BjjProductionStaminaPolicy.settings()).ok(), false)
    var settings := BjjProductionStaminaPolicy.settings()
    settings.enable_v04_commitment_semantics = true
    var rules := BjjExchangeRules.build(settings).rules
    check("production Rule 1", rules.rule1, true)
    check("production Rule 2", rules.rule2, false)
    check("raw Rule 1", BjjExchangeRules.new().rule1, false)
    check("raw v04", BjjExchangeRules.new().v04, false)
    var s := BjjMountExchange.new()
    s.rules = rules
    rejected("missing request", s, null)
    for command: BjjExchangeResult.Request in [request(""), request(C.TOP_HIGH_MOUNT_CLIMB,""),
        request("unknown"), request(C.TOP_HIGH_MOUNT_CLIMB,"unknown"), request(C.BOTTOM_BRIDGE,C.TOP_RESPONSE_POST_AND_BASE),
        request(C.TOP_HIGH_MOUNT_CLIMB,C.TOP_RESPONSE_POST_AND_BASE), request(C.TOP_HIGH_MOUNT_CLIMB,C.BOTTOM_RESPONSE_FOREARM_FRAME,"INVALID"),
        request(C.TOP_HIGH_MOUNT_CLIMB,C.BOTTOM_RESPONSE_FOREARM_FRAME,"MEDIUM","INVALID"),
        request(BjjMountExchange.FINISH), request(C.TOP_AMERICANA_ARM_ISOLATION)]:
        if command.action_id == C.TOP_AMERICANA_ARM_ISOLATION:
            s.rules = BjjExchangeRules.build({"enable_v02_setup":true}).rules
        rejected("invalid command " + str(command.fields()), s, command)
    s.rules = rules
    s.initiator = "INVALID"
    rejected("invalid initiator", s, request())
    s.initiator = "top"
    s.position.axis = NAN
    rejected("nonfinite axis", s, request())
    s.position.axis = 1.5
    s.position.band = 3
    rejected("inconsistent axis/band", s, request())
    s.position.band = 1
    s.top_behavior = "ESCAPE"
    rejected("wrong behavior side", s, request())
    s.top_behavior = "PRESSURE"
    s.americana_tier = 3
    rejected("invalid setup tier", s, request())
    s.americana_tier = 0
    s.submission_stage = "INVALID"
    rejected("invalid stage", s, request())
    s.submission_stage = ""
    s.clock_seconds = 0
    rejected("timeout", s, request())
    s.clock_seconds = -1
    rejected("invalid clock", s, request())
    s.clock_seconds = 300
    s.submission_tapped = true
    rejected("Tap", s, request())
    s.submission_tapped = false
    s.position.break_mount(-0.5)
    rejected("exit", s, request())
    rejected("repeated exit", s, request())
    # Rejected commands cannot poison subsequent replay; results cannot alias live history/state.
    var a := BjjMountExchange.new()
    var b := BjjMountExchange.new()
    a.rules = rules
    b.rules = rules
    rejected("before replay", a, request("bad"))
    var captured: Dictionary = {}
    for command: BjjExchangeResult.Request in [request(), request(C.BOTTOM_BRIDGE,C.TOP_RESPONSE_HIP_FOLLOW_REPUMMEL), request()]:
        var ar := a.attempt(command)
        var br := b.attempt(command)
        check("deterministic result", ar.fields(), br.fields())
        check("deterministic state", a.snapshot().fields(), b.snapshot().fields())
        if captured.is_empty():
            captured = ar.fields()
            ar.outcome.top_stamina = 999
            ar.initiator_funding.requested_cost = 999
    check("result mutation does not touch state", a.snapshot().fields(), b.snapshot().fields())
    var hist := a.history.fields()
    hist.commitment_history.append("corruption")
    check("serialized history detached", a.history.fields(), b.history.fields())
    for available in [0,2,3,6,7,11,12,25,26,34,35,100]:
        var boundary := BjjMountExchange.new()
        boundary.rules = rules
        boundary.top.set_current(available)
        boundary.bottom.set_current(available)
        var ib := boundary.top.band
        var rb := boundary.bottom.band
        var r := boundary.attempt(request(C.TOP_HIGH_MOUNT_CLIMB,C.BOTTOM_RESPONSE_FOREARM_FRAME,"HIGH","HIGH"))
        check("boundary accepted %d" % available, r.ok(), true)
        check("historical bands %d" % available, [r.exhaustion.initiator,r.exhaustion.responder], [ib,rb])
        check("nonnegative resources %d" % available, boundary.top.current >= 0 and boundary.bottom.current >= 0, true)
        check("funding charged %d" % available, r.stamina.charged, r.initiator_funding.effective_cost)
    var shared := BjjMountExchange.new()
    shared.bottom = shared.top
    rejected("aliased fighters", shared, request())
    var missing := BjjMountExchange.new()
    missing.top = null
    check("missing pool", missing.attempt(request()).ok(), false)
    missing = BjjMountExchange.new()
    missing.position = null
    check("missing position", missing.attempt(request()).ok(), false)
    missing = BjjMountExchange.new()
    missing.rules = null
    rejected("missing rules", missing, request())
    missing.rules = rules
    missing.cost_policy = null
    rejected("missing costs", missing, request())
    print("Exchange native: %d assertions, %d failures" % [checks, failures])
    quit(0 if failures == 0 else 1)
