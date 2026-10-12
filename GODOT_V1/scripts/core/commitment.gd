class_name BjjCommitment
extends RefCounted

# Stable identifiers mirror domain/action.py, not ordinal arithmetic.
const LOW: String = "LOW"
const MEDIUM: String = "MEDIUM"
const HIGH: String = "HIGH"
const ORDER: Array[String] = [LOW, MEDIUM, HIGH]
# Empty effective identifier means UNFUNDED; it is not a valid request.
const UNFUNDED: String = ""

static func valid(identifier: String) -> bool:
    return ORDER.has(identifier)
