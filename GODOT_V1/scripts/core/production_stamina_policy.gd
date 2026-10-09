class_name BjjProductionStaminaPolicy
extends RefCounted

# interfaces/production_policy.py::PRODUCTION_STAMINA_RECOVERY_POLICY.
# Caller must explicitly enable v0.4a. RECOVER/D3-B are separate milestones.
static func settings() -> Dictionary:
    return {"enable_stamina_settlement_rules": false,
        "enable_unfunded_responder_cost_waiver": true,
        "enable_supplemental_hold_settlement": false}
