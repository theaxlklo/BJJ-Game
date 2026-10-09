class_name BjjGrade
extends RefCounted

# Exact Grade/shift semantics of src/bjj_game/domain/model.py.
# Ordinal arithmetic is clamped at -2 .. 2.
const STRONG_FAILURE = -2
const FAILURE = -1
const CONTESTED = 0
const SUCCESS = 1
const STRONG_SUCCESS = 2


static func shift(grade: int, steps: int) -> int:
    return clampi(grade + steps, STRONG_FAILURE, STRONG_SUCCESS)


static func successful(grade: int) -> bool:
    return grade >= SUCCESS


static func failed(grade: int) -> bool:
    return grade <= FAILURE
