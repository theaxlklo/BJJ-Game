class_name BjjHalfGuardResolver
extends RefCounted

# Pure Half Guard exchange resolution (HALF_GUARD_V0_RULES.md sections 5.3, 5.4 and 5.7). It reads plain values and
# returns a value object; it mutates nothing and owns no state. The ordered grade pipeline (each step saturating):
#   raw -> positional -> attack readiness -> defense readiness -> exhaustion -> magnitude -> undercommitment.
# Shared stamina and commitment primitives are reused unchanged (BjjGrade, BjjExhaustionPolicy, BjjCommitmentSettlement).

class Inputs extends RefCounted:
    var side: String = ""
    var action_id: String = ""
    var response_id: String = ""
    var axis_tenths: int = 0
    var band: int = 0
    var top_base: int = 1
    var bottom_frame: int = 1
    var initiator_band: String = ""
    var responder_band: String = ""
    var initiator_effective: String = ""
    var responder_effective: String = ""

class Resolution extends RefCounted:
    var raw_grade: int = 0
    var positional_modifier: int = 0
    var attack_readiness_shift: int = 0
    # -1 stands for "no governed response" (the oracle reports null for it).
    var defense_strength_tier: int = -1
    var defense_readiness_shift: int = 0
    var exhaustion_modifier: int = 0
    var grade_after_positional: int = 0
    var grade_after_attack: int = 0
    var grade_after_defense: int = 0
    var grade_after_exhaustion: int = 0
    var magnitude_modifier: int = 0
    var grade_after_magnitude: int = 0
    var undercommitment_modifier: int = 0
    var final_grade: int = 0
    var axis_proposed: int = 0
    var axis_after: int = 0
    var band_after: int = 0
    var exit_destination: String = ""

static func resolve(input: Inputs) -> Resolution:
    var r := Resolution.new()
    r.raw_grade = int(BjjHalfGuardCatalog.RAW[input.side][input.action_id][input.response_id])
    var against_control := (input.side == "top" and input.band == -2) or (input.side == "bottom" and input.band == 2)
    r.positional_modifier = -1 if against_control else 0
    r.grade_after_positional = BjjGrade.shift(r.raw_grade, r.positional_modifier)
    var own_tier := input.top_base if input.side == "top" else input.bottom_frame
    if BjjHalfGuardCatalog.is_break_capable(input.action_id):
        r.attack_readiness_shift = int(BjjHalfGuardRules.ATTACK_SHIFT[own_tier])
    r.grade_after_attack = BjjGrade.shift(r.grade_after_positional, r.attack_readiness_shift)
    if BjjHalfGuardCatalog.GOVERNED.has(input.response_id):
        var track_tier := input.bottom_frame if str(BjjHalfGuardCatalog.GOVERNED[input.response_id]) == BjjHalfGuardCatalog.BOTTOM_FRAME else input.top_base
        # A LOW or unfunded defense was not made with real effort: it is evaluated as tier None (N-8, N-9).
        var unmade := input.responder_effective == BjjCommitment.LOW or input.responder_effective == BjjCommitment.UNFUNDED
        r.defense_strength_tier = 0 if unmade else track_tier
        r.defense_readiness_shift = int(BjjHalfGuardRules.DEFENSE_SHIFT[r.defense_strength_tier])
    r.grade_after_defense = BjjGrade.shift(r.grade_after_attack, r.defense_readiness_shift)
    r.exhaustion_modifier = BjjExhaustionPolicy.exchange(input.initiator_band, input.responder_band).modifier
    r.grade_after_exhaustion = BjjGrade.shift(r.grade_after_defense, r.exhaustion_modifier)
    r.magnitude_modifier = BjjCommitmentSettlement.magnitude_modifier(input.initiator_effective, r.grade_after_exhaustion)
    r.grade_after_magnitude = BjjGrade.shift(r.grade_after_exhaustion, r.magnitude_modifier)
    r.undercommitment_modifier = BjjCommitmentSettlement.undercommitment_modifier(input.initiator_effective, input.responder_effective)
    r.final_grade = BjjGrade.shift(r.grade_after_magnitude, r.undercommitment_modifier)
    var delta := BjjHalfGuardRules.STEP_TENTHS * r.final_grade
    r.axis_proposed = input.axis_tenths + (delta if input.side == "top" else -delta)
    if r.final_grade >= BjjGrade.SUCCESS:
        if input.action_id == BjjHalfGuardCatalog.TOP_KNEE_SLICE and r.axis_proposed >= BjjHalfGuardRules.PASS_LINE:
            r.exit_destination = "Side Control"
        elif input.action_id == BjjHalfGuardCatalog.BOTTOM_RECOVER_GUARD and r.axis_proposed <= BjjHalfGuardRules.ESCAPE_LINE:
            r.exit_destination = "Open Guard" if r.final_grade == BjjGrade.SUCCESS else "Closed Guard"
    # The clamp and the band update also happen on an exit (N-7).
    r.axis_after = clampi(r.axis_proposed, BjjHalfGuardRules.AXIS_MIN, BjjHalfGuardRules.AXIS_MAX)
    r.band_after = BjjHalfGuardRules.band_update(r.axis_after, input.band)
    return r

class Readiness extends RefCounted:
    var top_base: int = 1
    var bottom_frame: int = 1
    var changes: Array[String] = []

# Readiness updates after the stamina charges (the paid-effort test needs the charge), in the fixed uniform order:
# consume the initiator's prepared-technique tier, wear the responder's governed tier, then build / weaken. Every step saturates at 0..2.
static func update_readiness(input: Inputs, final_grade: int, responder_paid_effort: bool) -> Readiness:
    var result := Readiness.new()
    result.top_base = input.top_base
    result.bottom_frame = input.bottom_frame
    var tiers := {BjjHalfGuardCatalog.TOP_BASE: input.top_base, BjjHalfGuardCatalog.BOTTOM_FRAME: input.bottom_frame}
    var short := BjjHalfGuardCatalog.short_name(input.action_id)
    var own := BjjHalfGuardCatalog.own_track(input.side)
    if BjjHalfGuardCatalog.is_break_capable(input.action_id) and int(tiers[own]) == BjjHalfGuardRules.TIER_MAX:
        _change(tiers, own, -1, short, result.changes)
    var effective := input.responder_effective
    if BjjHalfGuardCatalog.GOVERNED.has(input.response_id) and effective != BjjCommitment.LOW and effective != BjjCommitment.UNFUNDED:
        var wears := final_grade != BjjGrade.CONTESTED
        if effective == BjjCommitment.HIGH and responder_paid_effort:
            wears = final_grade >= BjjGrade.SUCCESS  # a paid HIGH defense is preserved unless it failed
        if wears:
            _change(tiers, str(BjjHalfGuardCatalog.GOVERNED[input.response_id]), -1, short, result.changes)
    if final_grade >= BjjGrade.SUCCESS and BjjHalfGuardCatalog.BUILD.has(input.action_id):
        var build: Array = BjjHalfGuardCatalog.BUILD[input.action_id]
        _change(tiers, str(build[0]), int(build[1]), short, result.changes)
    result.top_base = int(tiers[BjjHalfGuardCatalog.TOP_BASE])
    result.bottom_frame = int(tiers[BjjHalfGuardCatalog.BOTTOM_FRAME])
    return result

static func _change(tiers: Dictionary, track: String, delta: int, short: String, changes: Array[String]) -> void:
    var before: int = int(tiers[track])
    var after := clampi(before + delta, 0, BjjHalfGuardRules.TIER_MAX)
    tiers[track] = after
    if after != before:
        changes.append("%s:%s->%s:%s" % [track, BjjHalfGuardRules.tier_name(before), BjjHalfGuardRules.tier_name(after), short])
