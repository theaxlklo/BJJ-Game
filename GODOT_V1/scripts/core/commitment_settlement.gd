class_name BjjCommitmentSettlement
extends RefCounted

# Pure commitment-settlement calculations shared by any position. Stateless static functions:
# they read only their arguments and return plain values. Callers keep the ordering, mutation,
# stamina spending and history recording. "Effective" commitment is what funding granted:
# one of BjjCommitment.ORDER, or BjjCommitment.UNFUNDED ("") when nothing could be afforded.

# 0 for unfunded (and, as before, for any unrecognized identifier); 1..3 for LOW..HIGH.
static func rank(effective: String) -> int:
    return BjjCommitment.ORDER.find(effective) + 1

# Grade shift earned by the initiator's effective commitment: HIGH presses a Success up or a
# Failure down; LOW or unfunded softens a Strong Success or lifts a Strong Failure.
static func magnitude_modifier(effective: String, grade: int) -> int:
    if effective == BjjCommitment.HIGH:
        if grade == BjjGrade.SUCCESS:
            return 1
        if grade == BjjGrade.FAILURE:
            return -1
    if effective == BjjCommitment.LOW or effective == BjjCommitment.UNFUNDED:
        if grade == BjjGrade.STRONG_SUCCESS:
            return -1
        if grade == BjjGrade.STRONG_FAILURE:
            return 1
    return 0

# 1 when the responder is funded strictly below the initiator, else 0.
static func undercommitment_modifier(initiator_effective: String, responder_effective: String) -> int:
    return 1 if rank(responder_effective) < rank(initiator_effective) else 0

# Applies the two modifiers one after the other, saturating after each (never as one summed shift).
static func sequential_grade(grade: int, magnitude: int, undercommitment: int) -> int:
    return BjjGrade.shift(BjjGrade.shift(grade, magnitude), undercommitment)

# Rule 1: an unfunded initiator waives the responder's commitment cost.
static func waives_response_cost(rule1: bool, initiator_effective: String) -> bool:
    return rule1 and initiator_effective == BjjCommitment.UNFUNDED
