extends SceneTree

var checked: int = 0
var failures: int = 0
const MAX_INT: int = 9223372036854775807

func _initialize() -> void:
    # Invalid configurations must not become permissive defaults.
    var bad_costs: Array[Dictionary] = [
        {"LOW": 0.0, "MEDIUM": 7, "HIGH": 12},
        {"LOW": 3, "MEDIUM": "7", "HIGH": 12},
        {"LOW": 12, "MEDIUM": 7, "HIGH": 3},
        {"LOW": 3, "MEDIUM": 7},
        {"LOW": 3, "MEDIUM": 7, "INVALID": 12}]
    for config: Dictionary in bad_costs:
        check("invalid costs %s" % config, not BjjStaminaCostPolicy.build(config).ok())
    var rates: Dictionary = {"PRESSURE": -1, "HOLD": 0, "ESCAPE": -1, "PROTECT": 0, "CONSERVE": 2}
    for bad: Variant in [0.0, "0", null, -MAX_INT - 1]:
        var invalid := rates.duplicate()
        invalid["HOLD"] = bad
        check("invalid rate %s" % str(bad), not BjjBehaviorStaminaPolicy.build(5, invalid).ok())
    var bool_cost := BjjStaminaCostPolicy.build({"LOW": true, "MEDIUM": 7, "HIGH": 12})
    check("Python boolean integer cost", bool_cost.ok() and bool_cost.policy.determine("LOW", 1).effective_cost == 1)
    check("Python boolean cost serialization", bool_cost.policy.determine("LOW", 1).fields().effective_cost is bool)
    var bool_rates := rates.duplicate()
    bool_rates["HOLD"] = true
    check("Python boolean integer rate", BjjBehaviorStaminaPolicy.build(5, bool_rates).ok())
    check("unrepresentable capacity", not BjjStaminaPool.create(0, BjjStaminaPool.MAXIMUM_EXACT + 1).ok())
    var pool := BjjStaminaPool.create(10).pool
    var flow := BjjBehaviorStaminaPolicy.defaults()
    for carry: int in [MAX_INT, -MAX_INT, -MAX_INT - 1]:
        var meter := BjjBehaviorStaminaPolicy.Meter.new(carry)
        var previous: int = pool.current
        var previous_band: String = pool.band
        var behavior: String = "CONSERVE" if carry > 0 else "PRESSURE"
        var rejected := flow.apply(pool, behavior, 5, meter)
        check("sum overflow rejected %s" % carry, not rejected.ok())
        check("sum overflow pool unchanged", pool.current == previous and pool.band == previous_band)
        check("sum overflow carry unchanged", meter.remainder_units == carry)
    # The safe int64 endpoints remain usable without wrapping.
    var meter := BjjBehaviorStaminaPolicy.Meter.new()
    var large := flow.apply(pool, "PRESSURE", MAX_INT, meter)
    check("large safe expenditure", large.ok() and large.spent == 10 and pool.current == 0)
    check("large negative carry", meter.remainder_units == -2)
    check("huge pool expenditure", pool.spend_up_to(MAX_INT).shortfall == MAX_INT)
    check("huge recovery", pool.recover_up_to(MAX_INT).overflow == MAX_INT - 100)
    # Copied configuration must not retain mutable caller dictionaries.
    var costs: Dictionary = {"LOW": 3, "MEDIUM": 7, "HIGH": 12}
    var policy := BjjStaminaCostPolicy.build(costs).policy
    costs["HIGH"] = 0
    check("cost snapshot", policy.determine("HIGH", 12).effective_cost == 12)
    var custom := BjjBehaviorStaminaPolicy.build(5, rates).policy
    rates["CONSERVE"] = -100
    var custom_pool := BjjStaminaPool.create(50).pool
    check("rate snapshot", custom.apply(custom_pool, "CONSERVE", 5,
        BjjBehaviorStaminaPolicy.Meter.new()).recovered == 2)
    var free := BjjStaminaCostPolicy.build({"LOW": 0, "MEDIUM": 1, "HIGH": 2}).policy
    check("legal zero cost LOW", free.determine("HIGH", 0).effective == "LOW")
    check("negative availability preserves Python None", free.determine("LOW", -1).effective == "")
    # Same monotone behavior: total bookkeeping, carry, band and pool agree.
    for initial: int in [0, 1, 25, 26, 34, 35, 99, 100]:
        for behavior: String in BjjBehaviorStaminaPolicy.BEHAVIORS:
            for carry: int in [-4, 0, 4]:
                var split := BjjStaminaPool.create(initial).pool
                var combined := BjjStaminaPool.create(initial).pool
                var split_meter := BjjBehaviorStaminaPolicy.Meter.new(carry)
                var combined_meter := BjjBehaviorStaminaPolicy.Meter.new(carry)
                var spent: int = 0
                var recovered: int = 0
                var shortfall: int = 0
                var overflow: int = 0
                for i in range(5):
                    var r := flow.apply(split, behavior, 1, split_meter)
                    spent += r.spent
                    recovered += r.recovered
                    shortfall += r.spend_shortfall
                    overflow += r.recovery_overflow
                var single := flow.apply(combined, behavior, 5, combined_meter)
                check("partition %d %s carry=%d" % [initial, behavior, carry],
                    split.current == combined.current and split.band == combined.band
                    and split_meter.remainder_units == combined_meter.remainder_units
                    and spent == single.spent and recovered == single.recovered
                    and shortfall == single.spend_shortfall and overflow == single.recovery_overflow)
    # Both fighters crossing entry after charging cannot alter captured modifiers.
    var top := BjjStaminaPool.create(26).pool
    var bottom := BjjStaminaPool.create(26).pool
    var history := BjjExhaustionPolicy.exchange(top.band, bottom.band)
    top.spend_up_to(3)
    bottom.spend_up_to(3)
    check("simultaneous historical bands", history.modifier == 0
        and history.initiator == "Tired" and history.responder == "Tired"
        and top.band == "Exhausted" and bottom.band == "Exhausted")
    print("Stamina native boundaries: %d checks, %d failures" % [checked, failures])
    quit(0 if failures == 0 else 1)

func check(label: String, passed: bool) -> void:
    checked += 1
    if not passed:
        failures += 1
        print("FAIL " + label)
