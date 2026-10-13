class_name BjjSideControlResolver
extends RefCounted

# Pure Side Control exchange resolution (SIDE_CONTROL_V0_RULES.md sections 5.3, 5.4 and 5.7). It reads plain values and returns a value
# object; it mutates nothing and owns no state. The ordered grade pipeline (every step saturates at +-2 BEFORE the next, so the order is
# part of the rule):
#   raw -> positional -> attack readiness -> defense readiness -> exhaustion -> magnitude -> undercommitment.
# Shared grade, funding, exhaustion and commitment primitives are reused unchanged.

class Inputs extends RefCounted:
    var side: String = ""
    var action_id: String = ""
    var response_id: String = ""
    var axis_tenths: int = 0
    var band: int = 0
    var top_pin: int = 1
    var bottom_space: int = 1
    # Stamina bands captured BEFORE any charge, so a charge can never change its own exchange's grade.
    var initiator_band: String = ""
    var responder_band: String = ""
    var initiator_effective: String = ""
    var responder_effective: String = ""

class Resolution extends RefCounted:
    var raw_grade: int = 0
    var final_grade: int = 0
    var axis_proposed: int = 0
    var axis_after: int = 0
    var band_after: int = 0
    # "" when the exchange does not exit; otherwise the exit label of section 3.4.
    var exit_label: String = ""

static func tier_of(track: String, top_pin: int, bottom_space: int) -> int:
    return top_pin if track == BjjSideControlCatalog.TOP_PIN else bottom_space

static func resolve(input: Inputs) -> Resolution:
    var r := Resolution.new()
    var action: Dictionary = BjjSideControlCatalog.ENTITIES[input.action_id]
    var response: Dictionary = BjjSideControlCatalog.ENTITIES[input.response_id]
    r.raw_grade = int(BjjSideControlCatalog.RAW[input.action_id][input.response_id])
    # An initiator facing the opposing CONTROL band acts uphill.
    var against_control := (input.side == "top" and input.band == -2) or (input.side == "bottom" and input.band == 2)
    var grade := BjjGrade.shift(r.raw_grade, -1 if against_control else 0)
    if bool(action.break_capable):
        # Ready +1 / Partial 0 / None -1: the initiator's OWN track.
        grade = BjjGrade.shift(grade, tier_of(str(action.track), input.top_pin, input.bottom_space) - 1)
    if not str(response.track).is_empty():
        # A LOW or unfunded defense was not made with real effort: it is evaluated as tier None whatever its track (R-9).
        var unmade := input.responder_effective == BjjCommitment.LOW or input.responder_effective == BjjCommitment.UNFUNDED
        var strength := 0 if unmade else tier_of(str(response.track), input.top_pin, input.bottom_space)
        grade = BjjGrade.shift(grade, int(BjjSideControlRules.DEFENSE_SHIFT[strength]))
    grade = BjjGrade.shift(grade, BjjExhaustionPolicy.exchange(input.initiator_band, input.responder_band).modifier)
    grade = BjjGrade.shift(grade, BjjCommitmentSettlement.magnitude_modifier(input.initiator_effective, grade))
    r.final_grade = BjjGrade.shift(grade, BjjCommitmentSettlement.undercommitment_modifier(input.initiator_effective, input.responder_effective))
    var delta := BjjSideControlRules.STEP_TENTHS * r.final_grade
    r.axis_proposed = input.axis_tenths + (delta if input.side == "top" else -delta)
    # An exit needs a break-capable technique, a Success or better AND the line crossed in the technique's own direction.
    var crossed := r.axis_proposed >= BjjSideControlRules.EXIT_LINE if input.side == "top" else r.axis_proposed <= -BjjSideControlRules.EXIT_LINE
    if bool(action.break_capable) and r.final_grade >= BjjGrade.SUCCESS and crossed:
        r.exit_label = str(action.exit)
    # The clamp and the band update also happen on an exit.
    r.axis_after = clampi(r.axis_proposed, BjjSideControlRules.AXIS_MIN, BjjSideControlRules.AXIS_MAX)
    r.band_after = BjjSideControlRules.band_update(r.axis_after, input.band)
    return r

class Readiness extends RefCounted:
    var top_pin: int = 1
    var bottom_space: int = 1
    # One {track, before, after, cause} per tier that actually changed, in the fixed consume -> wear -> build order.
    var changes: Array = []

# Readiness updates after the stamina charges (the paid-effort test needs the Rule 1 outcome). Each step saturates at 0..2 and records only
# real changes. Consume touches the initiator's own track, wear the responder's governed track and build a non-break-capable action's
# track, so no track is touched twice in one exchange.
static func update_readiness(input: Inputs, final_grade: int, responder_paid_effort: bool) -> Readiness:
    var result := Readiness.new()
    result.top_pin = input.top_pin
    result.bottom_space = input.bottom_space
    var tiers := {BjjSideControlCatalog.TOP_PIN: input.top_pin, BjjSideControlCatalog.BOTTOM_SPACE: input.bottom_space}
    var action: Dictionary = BjjSideControlCatalog.ENTITIES[input.action_id]
    var response: Dictionary = BjjSideControlCatalog.ENTITIES[input.response_id]
    if bool(action.break_capable) and int(tiers[str(action.track)]) == BjjSideControlRules.TIER_MAX:
        _change(tiers, str(action.track), -1, "consume", result.changes)
    var effective := input.responder_effective
    if not str(response.track).is_empty() and (effective == BjjCommitment.MEDIUM or effective == BjjCommitment.HIGH):
        var wears := final_grade != BjjGrade.CONTESTED
        if effective == BjjCommitment.HIGH and responder_paid_effort:
            wears = final_grade >= BjjGrade.SUCCESS  # a paid HIGH defense is preserved unless it failed
        if wears:
            _change(tiers, str(response.track), -1, "wear", result.changes)
    if final_grade >= BjjGrade.SUCCESS and not bool(action.break_capable):
        _change(tiers, BjjSideControlCatalog.TOP_PIN if input.side == "top" else BjjSideControlCatalog.BOTTOM_SPACE, 1, "build", result.changes)
    result.top_pin = int(tiers[BjjSideControlCatalog.TOP_PIN])
    result.bottom_space = int(tiers[BjjSideControlCatalog.BOTTOM_SPACE])
    return result

static func _change(tiers: Dictionary, track: String, delta: int, cause: String, changes: Array) -> void:
    var before: int = int(tiers[track])
    var after := clampi(before + delta, 0, BjjSideControlRules.TIER_MAX)
    tiers[track] = after
    if after != before:
        changes.append({"track": track, "before": before, "after": after, "cause": cause})
