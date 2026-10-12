class_name BjjExchangeRules
extends RefCounted

# MountMatch constructor prerequisites. Raw defaults stay OFF. No implicit opt-in.
const FLAGS: Array[String] = ["enable_v02_setup", "enable_v03_submissions", "enable_v03b_stalling",
    "enable_v04_commitment_semantics", "enable_v04b_recognition", "enable_stamina_settlement_rules",
    "enable_unfunded_responder_cost_waiver", "enable_supplemental_hold_settlement"]
var _setup: bool = false
var _submissions: bool = false
var _v04: bool = false
var _rule1: bool = false
var _rule2: bool = false
var setup: bool:
    get: return _setup
var submissions: bool:
    get: return _submissions
var v04: bool:
    get: return _v04
var rule1: bool:
    get: return _rule1
var rule2: bool:
    get: return _rule2

class BuildResult extends RefCounted:
    var rules: BjjExchangeRules
    var error: String = ""
    func ok() -> bool:
        return error.is_empty()

static func build(settings: Dictionary) -> BuildResult:
    var r := BuildResult.new()
    for key: Variant in settings:
        if not (key is String or key is StringName) or not FLAGS.has(str(key)):
            r.error = "unknown_feature_flag"
            return r
        if not settings[key] is bool:
            r.error = "feature_flag_must_be_boolean"
            return r
    var setup_enabled: bool = settings.get("enable_v02_setup", false)
    var submissions_enabled: bool = settings.get("enable_v03_submissions", false)
    var stalling: bool = settings.get("enable_v03b_stalling", false)
    var commitment_enabled: bool = settings.get("enable_v04_commitment_semantics", false)
    var recognition: bool = settings.get("enable_v04b_recognition", false)
    var umbrella: bool = settings.get("enable_stamina_settlement_rules", false)
    var waiver: bool = settings.get("enable_unfunded_responder_cost_waiver", false)
    var supplemental: bool = settings.get("enable_supplemental_hold_settlement", false)
    if submissions_enabled and not setup_enabled:
        r.error = "submissions_require_setup"
        return r
    if stalling and not submissions_enabled:
        r.error = "stalling_requires_submissions"
        return r
    if (recognition or umbrella or waiver or supplemental) and not commitment_enabled:
        r.error = "settlement_or_recognition_requires_v04"
        return r
    if stalling or recognition:
        r.error = "unsupported_controller"
        return r
    r.rules = BjjExchangeRules.new()
    r.rules._setup = setup_enabled
    r.rules._submissions = submissions_enabled
    r.rules._v04 = commitment_enabled
    r.rules._rule1 = umbrella or waiver
    r.rules._rule2 = umbrella or supplemental
    return r
