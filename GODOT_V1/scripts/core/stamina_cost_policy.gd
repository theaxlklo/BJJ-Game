class_name BjjStaminaCostPolicy
extends RefCounted

# Pure funding decision, no stamina charge or match settlement.
var _costs: Array[int] = [3, 7, 12]
# Python bool is an int: retain the original JSON type while computing with ints.
var _boolean_costs: Array[bool] = [false, false, false]

class BuildResult extends RefCounted:
    var policy: BjjStaminaCostPolicy
    var error: String = ""
    func ok() -> bool:
        return error.is_empty()

class Funding extends RefCounted:
    var error: String = ""
    var requested: String = ""
    var effective: String = ""
    var requested_cost: int = 0
    var effective_cost: int = 0
    var funding_gap: int = 0
    var _requested_is_boolean: bool = false
    var _effective_is_boolean: bool = false
    func ok() -> bool:
        return error.is_empty()
    func fields() -> Dictionary:
        return {"requested": requested, "effective": effective,
            "requested_cost": bool(requested_cost) if _requested_is_boolean else requested_cost,
            "effective_cost": bool(effective_cost) if _effective_is_boolean else effective_cost,
            "funding_gap": funding_gap}

static func defaults() -> BjjStaminaCostPolicy:
    return BjjStaminaCostPolicy.new()

static func build(costs: Dictionary) -> BuildResult:
    var r := BuildResult.new()
    if costs.size() != BjjCommitment.ORDER.size():
        r.error = "commitment_keys_mismatch"
        return r
    var copied: Array[int] = []
    var boolean_costs: Array[bool] = []
    for id: String in BjjCommitment.ORDER:
        if not costs.has(id):
            r.error = "commitment_keys_mismatch"
            return r
        if not (costs[id] is int or costs[id] is bool) or int(costs[id]) < 0:
            r.error = "cost_must_be_nonnegative_integer"
            return r
        copied.append(int(costs[id]))
        boolean_costs.append(costs[id] is bool)
    if not (copied[0] < copied[1] and copied[1] < copied[2]):
        r.error = "costs_must_strictly_increase"
        return r
    r.policy = BjjStaminaCostPolicy.new()
    r.policy._costs = copied
    r.policy._boolean_costs = boolean_costs
    return r

func determine(requested: String, available_stamina: int) -> Funding:
    var r := Funding.new()
    r.requested = requested
    var index: int = BjjCommitment.ORDER.find(requested)
    if index < 0:
        r.error = "invalid_commitment"
        return r
    r.requested_cost = _costs[index]
    r._requested_is_boolean = _boolean_costs[index]
    # Python accepts negative availability and returns None, including zero-cost LOW.
    for i in range(index, -1, -1):
        if _costs[i] <= available_stamina:
            r.effective = BjjCommitment.ORDER[i]
            r.effective_cost = _costs[i]
            r._effective_is_boolean = _boolean_costs[i]
            break
    r.funding_gap = r.requested_cost - r.effective_cost
    return r
