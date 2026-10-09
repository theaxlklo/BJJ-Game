class_name BjjExhaustionPolicy
extends RefCounted

# engine/stamina.py::ExhaustionPolicy default modifiers. Supply historical bands
# captured BEFORE action costs, not live pools. This never recomputes history.
class Exchange extends RefCounted:
    var error: String = ""
    var initiator: String = ""
    var responder: String = ""
    var initiator_modifier: int = 0
    var responder_modifier: int = 0
    var modifier: int = 0
    func ok() -> bool:
        return error.is_empty()
    func fields() -> Dictionary:
        return {"initiator": initiator, "responder": responder,
            "initiator_modifier": initiator_modifier,
            "responder_modifier": responder_modifier, "modifier": modifier}

static func exchange(initiator_band: String, responder_band: String) -> Exchange:
    var r := Exchange.new()
    if not BjjStaminaPool.BANDS.has(initiator_band) or not BjjStaminaPool.BANDS.has(responder_band):
        r.error = "invalid_stamina_band"
        return r
    r.initiator = initiator_band
    r.responder = responder_band
    if initiator_band == "Exhausted":
        r.initiator_modifier = -1
    if responder_band == "Exhausted":
        r.responder_modifier = 1
    r.modifier = r.initiator_modifier + r.responder_modifier
    return r
