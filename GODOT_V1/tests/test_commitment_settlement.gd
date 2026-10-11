extends SceneTree

# Negative-first tests for BjjCommitmentSettlement (A3a): the pure, position-independent settlement
# calculations extracted from BjjMountExchange.attempt(). Expected values are written out literally
# here (not computed through production code) so a semantic change in the helper cannot hide.
const C = preload("res://scripts/positions/mount/mount_catalog.gd")
const LOW: String = "LOW"
const MEDIUM: String = "MEDIUM"
const HIGH: String = "HIGH"

var checks: int = 0
var failures: int = 0

func check(label: String, actual: Variant, expected: Variant) -> void:
    checks += 1
    if typeof(actual) != typeof(expected) or actual != expected:
        failures += 1
        if failures <= 25:
            push_error("%s: got %s expected %s" % [label, actual, expected])

func _initialize() -> void:
    # ---- rank -------------------------------------------------------------------------------
    var ranks := {"": 0, LOW: 1, MEDIUM: 2, HIGH: 3, "BOGUS": 0, "low": 0, " HIGH": 0, "Medium": 0}
    for key: String in ranks:
        check("rank '%s'" % key, BjjCommitmentSettlement.rank(key), ranks[key])

    # ---- magnitude modifier: literal table over grade -2..2 ----------------------------------
    # grades:                         -2  -1   0  +1  +2
    var magnitude := {
        HIGH:     [0, -1, 0, 1, 0],
        MEDIUM:   [0, 0, 0, 0, 0],
        LOW:      [1, 0, 0, 0, -1],
        "":       [1, 0, 0, 0, -1],
        "BOGUS":  [0, 0, 0, 0, 0],
        "high":   [0, 0, 0, 0, 0],
        "low":    [0, 0, 0, 0, 0],
        " ":      [0, 0, 0, 0, 0],
        "LOW ":   [0, 0, 0, 0, 0],
    }
    for effective: String in magnitude:
        for index in range(5):
            check("magnitude %s grade %d" % [effective, index - 2], BjjCommitmentSettlement.magnitude_modifier(effective, index - 2),
                magnitude[effective][index])
        for grade in [-3, 3, 99, -99]:
            check("magnitude %s out-of-range grade %d" % [effective, grade], BjjCommitmentSettlement.magnitude_modifier(effective, grade), 0)

    # ---- undercommitment: responder strictly below initiator --------------------------------
    var efforts: Array[String] = ["", LOW, MEDIUM, HIGH, "BOGUS"]
    var order := {"": 0, LOW: 1, MEDIUM: 2, HIGH: 3, "BOGUS": 0}
    for initiator in efforts:
        for responder in efforts:
            check("undercommitment %s vs %s" % [initiator, responder], BjjCommitmentSettlement.undercommitment_modifier(initiator, responder),
                1 if order[responder] < order[initiator] else 0)
    check("equal efforts do not undercommit", BjjCommitmentSettlement.undercommitment_modifier(HIGH, HIGH), 0)
    check("unfunded initiator is never undercommitted against", BjjCommitmentSettlement.undercommitment_modifier("", HIGH), 0)
    check("unfunded responder undercommits a funded initiator", BjjCommitmentSettlement.undercommitment_modifier(LOW, ""), 1)

    # ---- sequential grade: magnitude first, then undercommitment, clamped between -----------
    for grade in range(-2, 3):
        for step in [-1, 0, 1]:
            for under in [0, 1]:
                var middle: int = mini(2, maxi(-2, grade + step))
                var expected: int = mini(2, maxi(-2, middle + under))
                check("sequential %d %d %d" % [grade, step, under], BjjCommitmentSettlement.sequential_grade(grade, step, under), expected)
    check("clamping between the steps matters (not a summed shift)", BjjCommitmentSettlement.sequential_grade(-2, -1, 1), -1)
    check("upper clamp then no change", BjjCommitmentSettlement.sequential_grade(2, 1, 0), 2)
    check("neutral steps keep the grade", BjjCommitmentSettlement.sequential_grade(0, 0, 0), 0)

    # ---- saturation: sequential application is not the same as combining modifiers first -----
    # Literal cases at the clamp. Each pair is (sequential result, result of one summed shift).
    check("saturated +2: +1 then -1 is sequential +1", BjjCommitmentSettlement.sequential_grade(2, 1, -1), 1)
    check("saturated +2: summed shift (+1-1=0) would stay +2", BjjGrade.shift(2, 1 + -1), 2)
    check("saturated -2: -1 then +1 is sequential -1", BjjCommitmentSettlement.sequential_grade(-2, -1, 1), -1)
    check("saturated -2: summed shift (-1+1=0) would stay -2", BjjGrade.shift(-2, -1 + 1), -2)
    check("saturated +2: -1 then +1 returns to +2", BjjCommitmentSettlement.sequential_grade(2, -1, 1), 2)
    check("saturated +2: +1 then +1 stays +2", BjjCommitmentSettlement.sequential_grade(2, 1, 1), 2)
    check("saturated -2: -1 then -1 stays -2", BjjCommitmentSettlement.sequential_grade(-2, -1, -1), -2)
    # Both orders at every grade: the clamp between steps makes order observable only at the edges.
    var diverging := 0
    for grade in range(-2, 3):
        for first in [-1, 0, 1]:
            for second in [-1, 0, 1]:
                var sequential: int = BjjCommitmentSettlement.sequential_grade(grade, first, second)
                var summed: int = mini(2, maxi(-2, grade + first + second))
                if sequential != summed:
                    diverging += 1
                    check("divergence only at an edge (%d,%d,%d)" % [grade, first, second], absi(grade) == 2, true)
    check("exactly two edge cases diverge from a summed shift", diverging, 2)
    # Engine-reachable domain (magnitude in -1..1, undercommitment 0/+1): a nonzero modifier can leave
    # the grade unchanged. attempt() re-resolves on the modifiers being nonzero, not on a grade change,
    # so the helper must not be asked to signal "changed".
    check("nonzero undercommitment saturates unchanged at +2", BjjCommitmentSettlement.sequential_grade(2, 0, 1), 2)
    check("nonzero magnitude and undercommitment cancel back to +2", BjjCommitmentSettlement.sequential_grade(2, -1, 1), 2)
    check("nonzero magnitude saturates unchanged at +2", BjjCommitmentSettlement.sequential_grade(2, 1, 0), 2)
    check("nonzero magnitude saturates unchanged at -2", BjjCommitmentSettlement.sequential_grade(-2, -1, 0), -2)

    # ---- Rule 1 responder-cost waiver predicate ---------------------------------------------
    for rule1 in [false, true]:
        for effective: String in ["", LOW, MEDIUM, HIGH, "BOGUS", " ", "low"]:
            check("waives r1=%s '%s'" % [rule1, effective], BjjCommitmentSettlement.waives_response_cost(rule1, effective), rule1 and effective == "")
    check("Rule 1 off never waives an unfunded initiator", BjjCommitmentSettlement.waives_response_cost(false, ""), false)
    check("Rule 1 never waives a funded initiator", BjjCommitmentSettlement.waives_response_cost(true, LOW), false)
    check("Rule 1 waives for an unfunded initiator", BjjCommitmentSettlement.waives_response_cost(true, ""), true)

    # ---- purity: no instance state, detached results ----------------------------------------
    var holder := BjjCommitmentSettlement.new()
    var own_properties: Array = []
    for property: Dictionary in holder.get_property_list():
        if property.usage & PROPERTY_USAGE_SCRIPT_VARIABLE:
            own_properties.append(property.name)
    check("helper has no script variables", own_properties, [])
    # ---- wiring: BjjMountExchange.attempt() reports exactly the helper-table values ---------
    var wired := 0
    for rule1 in [false, true]:
        var rules := BjjExchangeRules.build({"enable_v02_setup": true, "enable_v04_commitment_semantics": true,
            "enable_unfunded_responder_cost_waiver": rule1}).rules
        for initiator_stamina in [0, 100]:
            for commitment in [LOW, MEDIUM, HIGH]:
                for response_commitment in ["", LOW, MEDIUM, HIGH]:
                    for response: String in [C.BOTTOM_RESPONSE_FOREARM_FRAME, C.BOTTOM_RESPONSE_TURN_IN_RECOVERY]:
                        var state := BjjMountExchange.new()
                        state.rules = rules
                        state.top.set_current(initiator_stamina)
                        var result := state.attempt(BjjExchangeResult.Request.new(C.TOP_HIGH_MOUNT_CLIMB, response, commitment, response_commitment))
                        if not result.ok():
                            check("wiring request accepted", result.ok(), true)
                            continue
                        wired += 1
                        var effective_initiator: String = result.initiator_funding.effective
                        var effective_responder: String = result.responder_funding.effective
                        var under: int = 1 if order[effective_responder] < order[effective_initiator] else 0
                        check("wired undercommitment", result.response_undercommitment_modifier, under)
                        # Rule 1 waiver wiring: waived exactly the responder's requested cost.
                        var waived: bool = rule1 and effective_initiator == ""
                        check("wired waiver", result.response_stamina_waived, result.responder_funding.effective_cost if waived else 0)
                        check("wired waiver leaves no response charge", result.response_stamina.charged == 0 if waived else true, true)
    check("wiring covered requests", wired > 0, true)

    print("commitment settlement checks: ", checks)
    print("commitment settlement failures: ", failures)
    quit(1 if failures > 0 else 0)
