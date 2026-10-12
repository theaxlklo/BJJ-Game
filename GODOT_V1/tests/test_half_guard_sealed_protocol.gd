extends SceneTree

# Negative-first tests for the Half Guard sealed-intent protocol (B1g, TACTICAL_PREPARATION_AND_FEINTS.md section 7-8).
# B1h REVISED THIS SUITE ON PURPOSE (owner decisions GP-2, GP-3 and the published timeout fallback): the requested commitment and the list of
# eligible real techniques are now PUBLIC view fields; the sealed secret of B1g (the commitment) is public, so the secrecy checks moved to the
# real technique, the feint flag and the funding results (see test_half_guard_feint_protocol.gd); executor events gained `real_action_id` /
# `apparent_action_id` / `feint`; `apply_response_timeout` accepts only the published fallback; the gateway gained three feint methods.
# Everything that is not one of those is unchanged.
# Expected values are literals, come from a TWIN driven through the unchanged one-call BjjHalfGuardWindowGateway.submit with the
# same inputs, or come from the independent Python oracle fixture; the protocol is never compared with itself except for the
# deliberate replay and indistinguishability checks. Refusals are checked by whole executor-state equality (gateway snapshot, the
# sealed store, the serial counter, the event log and the closed flag). The only private reads are test seams: `_gateway._match`
# (plain-field state injection, as the existing Half Guard tests do) and source scans.
const FIXTURE: String = "res://tests/generated/half_guard_reference.jsonl"
const PROTOCOL_PATH: String = "res://scripts/positions/half_guard/half_guard_sealed_protocol.gd"
const TOP_ID: String = "fighter_alpha"
const BOTTOM_ID: String = "fighter_bravo"
const CF: String = BjjHalfGuardCatalog.TOP_CROSSFACE
const FL: String = BjjHalfGuardCatalog.TOP_FLATTEN
const KS: String = BjjHalfGuardCatalog.TOP_KNEE_SLICE
const UH: String = BjjHalfGuardCatalog.BOTTOM_UNDERHOOK
const RG: String = BjjHalfGuardCatalog.BOTTOM_RECOVER_GUARD
const HF: String = BjjHalfGuardCatalog.BOTTOM_HIP_FRAME
const UF: String = BjjHalfGuardCatalog.BOTTOM_UNDERHOOK_FIGHT
const KSH: String = BjjHalfGuardCatalog.BOTTOM_KNEE_SHIELD
const HC: String = BjjHalfGuardCatalog.TOP_HEAD_CONTROL
const HP: String = BjjHalfGuardCatalog.TOP_HIP_PRESSURE
const KP: String = BjjHalfGuardCatalog.TOP_KNEE_PIN
const VIEW_KEYS: Array = ["apparent_technique_id", "apparent_technique_name", "commitment_requested", "eligible_real_ids", "initiator_id",
    "intent_serial", "position_id", "responder_id", "response_ids", "window_id"]
const COMMITMENTS: Array = ["LOW", "MEDIUM", "HIGH"]

var checks: int = 0
var failures: int = 0
var oracle_rows: int = 0
var leaves: int = 0


func check(label: String, actual: Variant, expected: Variant) -> void:
    checks += 1
    if typeof(actual) != typeof(expected) or JSON.stringify(actual, "", true, true) != JSON.stringify(expected, "", true, true):
        failures += 1
        if failures <= 40:
            push_error("%s: got %s expected %s" % [label, JSON.stringify(actual).left(600), JSON.stringify(expected).left(600)])


# Numeric comparison for the oracle fixture (JSON has one number type); everything else is strict.
func same_loose(actual: Variant, expected: Variant) -> bool:
    var a := typeof(actual)
    var e := typeof(expected)
    if (a == TYPE_INT or a == TYPE_FLOAT) and (e == TYPE_INT or e == TYPE_FLOAT):
        return absf(float(actual) - float(expected)) < 1e-9
    if a != e:
        return false
    if a == TYPE_DICTIONARY:
        var da: Dictionary = actual
        var de: Dictionary = expected
        if da.size() != de.size():
            return false
        for key: Variant in de:
            if not da.has(key) or not same_loose(da[key], de[key]):
                return false
        return true
    if a == TYPE_ARRAY:
        var aa: Array = actual
        var ae: Array = expected
        if aa.size() != ae.size():
            return false
        for i in range(aa.size()):
            if not same_loose(aa[i], ae[i]):
                return false
        return true
    return actual == expected


func check_loose(label: String, actual: Variant, expected: Variant) -> void:
    checks += 1
    leaves += 1
    if not same_loose(actual, expected):
        failures += 1
        if failures <= 40:
            push_error("%s: got %s expected %s" % [label, JSON.stringify(actual).left(600), JSON.stringify(expected).left(600)])


func _initialize() -> void:
    _test_creation()
    _test_seal_refusals()
    _test_respond_refusals()
    _test_retry_after_refusal()
    _test_timeout_refusals_and_fallback()
    _test_closed_public_view()
    _test_probing_controller()
    _test_defender_indistinguishability()
    _test_events_and_redaction()
    _test_detached_values()
    _test_lockstep_against_the_direct_path()
    _test_accounting_literals()
    _test_exits_and_terminal()
    _test_stale_and_duplicate_delivery()
    _test_session_end()
    _test_deterministic_replay()
    _test_oracle_trajectories()
    _test_oracle_grids()
    _test_unchanged_surfaces()
    _test_scope_and_hygiene()
    if failures > 0:
        push_error("Half Guard sealed protocol: %d / %d assertions failed" % [failures, checks])
        quit(1)
        return
    print("Half Guard sealed protocol PASS: %d assertions" % checks)
    quit(0)


# ---- Builders -----------------------------------------------------------------------------------------------------------

func fighter(current: int = 100, maximum: int = 100) -> Dictionary:
    var enter := int(floor(float(maximum) * 0.25))
    return {"stamina_current": current, "stamina_maximum": maximum, "exhaustion_latched": current <= enter, "behavior_remainder_units": 0}


func entry(top_current: int = 100, bottom_current: int = 100, clock: int = 300, interval: int = 5, last_issued: int = 0) -> Dictionary:
    return {"role_map": {"top": TOP_ID, "bottom": BOTTOM_ID}, "fighters": {TOP_ID: fighter(top_current), BOTTOM_ID: fighter(bottom_current)},
        "clock": {"initial_seconds": clock, "remaining_seconds": clock}, "window": {"last_issued_id": last_issued}, "interval_seconds": interval}


func fresh(request: Dictionary = {}) -> BjjHalfGuardSealedProtocol:
    return BjjHalfGuardSealedProtocol.create(entry() if request.is_empty() else request).protocol


func twin(request: Dictionary = {}) -> BjjHalfGuardWindowGateway:
    return BjjHalfGuardWindowGateway.create(entry() if request.is_empty() else request).gateway


func rep(report: BjjMatchWindowGateway.Report) -> Dictionary:
    if not report.ok():
        return {"error": report.error}
    var values := report.values.duplicate(true)
    values["error"] = ""
    return values


# An opened window for the initiator: {window_id, fighter_id, role}.
func opened(p: BjjHalfGuardSealedProtocol) -> Dictionary:
    return p.open_window().values


# A protocol with one open window and one sealed intent (Top, Crossface, the given commitment).
func sealed(commitment: String = "HIGH", action: String = CF) -> BjjHalfGuardSealedProtocol:
    var p := fresh()
    var w := opened(p)
    p.seal_intent(int(w.window_id), str(w.fighter_id), action, commitment)
    return p


func expect_refused(label: String, p: BjjHalfGuardSealedProtocol, before: Dictionary, report: BjjMatchWindowGateway.Report, code: String) -> void:
    check(label + " is refused", report.ok(), false)
    check(label + " code", report.error, code)
    check(label + " carries no values", report.values.is_empty(), true)
    check(label + " leaves the whole executor state unchanged", p.executor_snapshot(), before)


# ---- 1. Creation ----------------------------------------------------------------------------------------------------------

func _test_creation() -> void:
    var bad := entry()
    bad["interval_seconds"] = 0
    var created := BjjHalfGuardSealedProtocol.create(bad)
    check("an invalid entry builds nothing", created.ok(), false)
    check("the entry error is the engine's", created.error, BjjHalfGuardEntry.validate(bad))
    check("no protocol object leaks", created.protocol == null, true)
    check("a non-dictionary entry is refused", BjjHalfGuardSealedProtocol.create(5).ok(), false)
    var p := fresh()
    check("a valid entry builds", p != null, true)
    check("nothing pending", p.has_pending_intent(), false)
    check("not closed", p.is_closed(), false)
    check("initial executor state", p.executor_snapshot(),
        {"gateway": twin().snapshot(), "pending": {}, "serial": 0, "events": [], "closed": false})
    check("the simulation snapshot equals the unchanged gateway's", p.snapshot(), twin().snapshot())
    check("no public view without a seal", p.public_intent_view().error, "no_sealed_intent")
    check("no sealed view without a seal", p.sealed_intent_view(TOP_ID).error, "no_sealed_intent")
    check("no public events yet", p.public_events(), [])


# ---- 2. Seal refusals (negative first, whole-state equality) -----------------------------------------------------------------

func _test_seal_refusals() -> void:
    var p := fresh()
    var b := p.executor_snapshot()
    expect_refused("seal before any window", p, b, p.seal_intent(1, TOP_ID, CF, "LOW"), "no_open_window")
    expect_refused("seal for window 0 before any window", p, b, p.seal_intent(0, TOP_ID, CF, "LOW"), "no_open_window")
    var w := opened(p)
    var id := int(w.window_id)
    b = p.executor_snapshot()
    check("the opened window is the initiator's", [id, w.fighter_id, w.role], [1, TOP_ID, "top"])
    for stale: int in [0, id + 1, -1, 99]:
        expect_refused("stale window %d" % stale, p, b, p.seal_intent(stale, TOP_ID, CF, "LOW"), "stale_window")
    expect_refused("missing fighter", p, b, p.seal_intent(id, "", CF, "LOW"), "missing_fighter_id")
    expect_refused("unknown fighter", p, b, p.seal_intent(id, "stranger", CF, "LOW"), "unknown_fighter")
    expect_refused("the responder cannot seal", p, b, p.seal_intent(id, BOTTOM_ID, UH, "LOW"), "not_initiator")
    expect_refused("the responder cannot seal even with the initiator's technique", p, b, p.seal_intent(id, BOTTOM_ID, CF, "LOW"), "not_initiator")
    for bad_action: String in ["", "nonsense", UH, RG, HF, HC, "half_guard.top"]:
        expect_refused("unknown or foreign technique '%s'" % bad_action, p, b, p.seal_intent(id, TOP_ID, bad_action, "LOW"), "unknown_action")
    for bad_commitment: String in ["EXTREME", "low", "Medium", " ", "NONE"]:
        expect_refused("invalid commitment '%s'" % bad_commitment, p, b, p.seal_intent(id, TOP_ID, CF, bad_commitment), "invalid_commitment")
    # precedence: window identity, addressing, initiator, duplicate, technique, commitment
    expect_refused("stale beats unknown fighter", p, b, p.seal_intent(id + 1, "stranger", "x", "x"), "stale_window")
    expect_refused("unknown fighter beats a bad technique", p, b, p.seal_intent(id, "stranger", "x", "x"), "unknown_fighter")
    expect_refused("not initiator beats a bad technique", p, b, p.seal_intent(id, BOTTOM_ID, "x", "x"), "not_initiator")
    expect_refused("technique beats commitment", p, b, p.seal_intent(id, TOP_ID, "x", "x"), "unknown_action")
    # a pass is not a seal, and the legacy and time paths are unaffected while nothing is sealed
    check("nothing was sealed by any refusal", p.has_pending_intent(), false)
    var sealed_ok := p.seal_intent(id, TOP_ID, CF, "HIGH")
    check("the valid seal is accepted", sealed_ok.ok(), true)
    check("the seal is pending", p.has_pending_intent(), true)
    b = p.executor_snapshot()
    expect_refused("a second seal", p, b, p.seal_intent(id, TOP_ID, CF, "HIGH"), "intent_already_sealed")
    expect_refused("a second seal with a different technique", p, b, p.seal_intent(id, TOP_ID, FL, "LOW"), "intent_already_sealed")
    expect_refused("a second seal with a bad commitment still reports the duplicate", p, b, p.seal_intent(id, TOP_ID, "x", "x"), "intent_already_sealed")
    expect_refused("the responder cannot seal over a pending intent", p, b, p.seal_intent(id, BOTTOM_ID, UH, "LOW"), "not_initiator")
    expect_refused("a stale seal over a pending intent", p, b, p.seal_intent(id + 1, TOP_ID, CF, "LOW"), "stale_window")
    check("the original sealed content survives every refusal", p.sealed_intent_view(TOP_ID).values,
        {"window_id": id, "intent_serial": 1, "action_id": CF, "real_action_id": CF, "commitment_requested": "HIGH"})
    expect_refused("the legacy submit is refused while sealed", p, b, p.submit(id, TOP_ID, FL, HF, "LOW", "LOW"), "intent_pending")
    expect_refused("a pass is refused while sealed (a seal is irrevocable)", p, b, p.submit(id, TOP_ID), "intent_pending")
    expect_refused("a responder pass is refused while sealed", p, b, p.submit(id, BOTTOM_ID), "intent_pending")
    expect_refused("a second window cannot be opened over a seal", p, b, p.open_window(), "window_already_open")
    expect_refused("a timed window cannot be opened over a seal", p, b, p.open_window_for(0), "window_already_open")
    # a default commitment is the gateway's selected commitment
    var d := fresh()
    var dw := opened(d)
    d.seal_intent(int(dw.window_id), TOP_ID, KS)
    check("an empty commitment seals the selected commitment", d.sealed_intent_view(TOP_ID).values.commitment_requested, "MEDIUM")
    # context errors come from the gateway, never invented here
    var corrupt := fresh()
    var cw := opened(corrupt)
    corrupt._gateway._match.initiator = "nobody"
    b = corrupt.executor_snapshot()
    expect_refused("a corrupt initiator is the gateway's own context error", corrupt, b, corrupt.seal_intent(int(cw.window_id), TOP_ID, CF, "LOW"), "invalid_initiator")


# ---- 3. Respond refusals ---------------------------------------------------------------------------------------------------

func _test_respond_refusals() -> void:
    var p := fresh()
    var b := p.executor_snapshot()
    expect_refused("respond with no window", p, b, p.respond(1, BOTTOM_ID, 1, HF, "LOW"), "no_open_window")
    var w := opened(p)
    var id := int(w.window_id)
    b = p.executor_snapshot()
    expect_refused("respond with a window but no seal", p, b, p.respond(id, BOTTOM_ID, 1, HF, "LOW"), "no_sealed_intent")
    expect_refused("respond to a stale window with no seal", p, b, p.respond(id + 1, BOTTOM_ID, 1, HF, "LOW"), "stale_window")
    p.seal_intent(id, TOP_ID, KS, "HIGH")
    b = p.executor_snapshot()
    for stale: int in [0, id + 1, 99]:
        expect_refused("respond stale window %d" % stale, p, b, p.respond(stale, BOTTOM_ID, 1, HF, "LOW"), "stale_window")
    for serial: int in [0, 2, -1, 99]:
        expect_refused("respond serial %d" % serial, p, b, p.respond(id, BOTTOM_ID, serial, HF, "LOW"), "intent_serial_mismatch")
    expect_refused("respond without a fighter", p, b, p.respond(id, "", 1, HF, "LOW"), "missing_fighter_id")
    expect_refused("respond by a stranger", p, b, p.respond(id, "stranger", 1, HF, "LOW"), "unknown_fighter")
    expect_refused("the initiator cannot respond to itself", p, b, p.respond(id, TOP_ID, 1, HF, "LOW"), "not_responder")
    expect_refused("the initiator cannot respond to itself with its own response", p, b, p.respond(id, TOP_ID, 1, HC, "LOW"), "not_responder")
    for bad_response: String in ["", "nonsense", HC, HP, KP, CF, UH, "half_guard.bottom_response"]:
        expect_refused("unknown or foreign response '%s'" % bad_response, p, b, p.respond(id, BOTTOM_ID, 1, bad_response, "LOW"), "unknown_response")
    for bad_commitment: String in ["EXTREME", "low", " ", "NONE"]:
        expect_refused("invalid response commitment '%s'" % bad_commitment, p, b, p.respond(id, BOTTOM_ID, 1, HF, bad_commitment), "invalid_response_commitment")
    # precedence: window, seal, serial, responder identity, response, response commitment
    expect_refused("stale beats serial", p, b, p.respond(id + 1, "stranger", 9, "x", "x"), "stale_window")
    expect_refused("serial beats the responder identity", p, b, p.respond(id, "stranger", 9, "x", "x"), "intent_serial_mismatch")
    expect_refused("responder identity beats the response", p, b, p.respond(id, TOP_ID, 1, "x", "x"), "not_responder")
    expect_refused("unknown fighter beats the response", p, b, p.respond(id, "stranger", 1, "x", "x"), "unknown_fighter")
    expect_refused("response beats its commitment", p, b, p.respond(id, BOTTOM_ID, 1, "x", "x"), "unknown_response")
    check("every refusal kept the sealed intent", p.has_pending_intent(), true)
    check("and its window", p.window_fields().open, true)


# ---- 4. A refused response keeps the seal and allows a valid retry ---------------------------------------------------------------

func _test_retry_after_refusal() -> void:
    var p := sealed("HIGH", KS)
    var t := twin()
    var tw := t.open_window().values
    var w := p.window_fields()
    var view_before := p.public_intent_view().values
    var refused := p.respond(int(w.window_id), BOTTOM_ID, 1, "nonsense", "LOW")
    check("the first response is refused", refused.error, "unknown_response")
    check("the public view is unchanged by the refusal", p.public_intent_view().values, view_before)
    check("the sealed content is unchanged by the refusal", p.sealed_intent_view(TOP_ID).values,
        {"window_id": 1, "intent_serial": 1, "action_id": KS, "real_action_id": KS, "commitment_requested": "HIGH"})
    var refused_again := p.respond(int(w.window_id), BOTTOM_ID, 1, KSH, "bad")
    check("a second invalid response is refused", refused_again.error, "invalid_response_commitment")
    var retry := p.respond(int(w.window_id), BOTTOM_ID, 1, KSH, "LOW")
    var direct := t.submit(int(tw.window_id), TOP_ID, KS, KSH, "HIGH", "LOW")
    check("the retry is accepted", retry.ok(), true)
    check("the retry equals the direct one-call exchange with the sealed technique and commitment", rep(retry), rep(direct))
    check("the seal is consumed", p.has_pending_intent(), false)
    check("the simulation equals the direct path", p.snapshot(), t.snapshot())
    var again := p.respond(int(w.window_id), BOTTOM_ID, 1, KSH, "LOW")
    check("a second response to the consumed seal is refused", again.error, "no_open_window")
    check("and changes nothing", p.snapshot(), t.snapshot())


# ---- 5. The session timeout seam --------------------------------------------------------------------------------------------

func _test_timeout_refusals_and_fallback() -> void:
    var p := fresh()
    var b := p.executor_snapshot()
    expect_refused("timeout with no window", p, b, p.apply_response_timeout(1, 1, HF, "LOW"), "no_open_window")
    var w := opened(p)
    var id := int(w.window_id)
    b = p.executor_snapshot()
    expect_refused("timeout with no seal", p, b, p.apply_response_timeout(id, 1, HF, "LOW"), "no_sealed_intent")
    expect_refused("timeout with a stale window and no seal", p, b, p.apply_response_timeout(id + 1, 1, HF, "LOW"), "stale_window")
    p.seal_intent(id, TOP_ID, FL, "LOW")
    b = p.executor_snapshot()
    expect_refused("timeout stale window", p, b, p.apply_response_timeout(id + 1, 1, HF, "LOW"), "stale_window")
    expect_refused("timeout serial", p, b, p.apply_response_timeout(id, 2, HF, "LOW"), "intent_serial_mismatch")
    # B1h: only the PUBLISHED fallback of the defender's role is accepted (Bottom: Hip Frame LOW). Anything else, including a legal response
    # at another commitment or another side's response, is `fallback_not_published`; the code depends only on the defender's role.
    for wrong: Array in [["nonsense", "LOW"], [HC, "LOW"], [HF, "bad"], [HF, ""], [HF, "MEDIUM"], [HF, "HIGH"], [UF, "LOW"], [KSH, "LOW"], ["", ""]]:
        expect_refused("timeout fallback %s is not the published one" % [wrong], p, b, p.apply_response_timeout(id, 1, str(wrong[0]), str(wrong[1])), "fallback_not_published")
    check("a refused timeout keeps the seal", p.has_pending_intent(), true)
    # an accepted timeout resolves exactly like the responder's own identical response, flagged as defaulted
    var t := twin()
    var tw := t.open_window().values
    var applied := p.apply_response_timeout(id, 1, HF, "LOW")
    var direct := t.submit(int(tw.window_id), TOP_ID, FL, HF, "LOW", "LOW")
    check("the timeout resolves", applied.ok(), true)
    check("the timeout equals the direct exchange", rep(applied), rep(direct))
    check("the simulation equals the direct path", p.snapshot(), t.snapshot())
    check("the seal is gone", p.has_pending_intent(), false)
    var events := p.protocol_events()
    check("the timeout is flagged on the response event", events[1].defaulted, true)
    check("and on the reveal event", events[2].defaulted, true)
    var normal := sealed("LOW", FL)
    normal.respond(1, BOTTOM_ID, 1, HF, "LOW")
    check("a responder's own response is not flagged", normal.protocol_events()[1].defaulted, false)
    check("the simulation is identical whether the response was the responder's or the session's fallback", normal.snapshot(), p.snapshot())
    # nothing carries into the next window
    var next := p.open_window()
    check("the next window opens normally", next.ok(), true)
    check("the next window is the next id", next.values.window_id, 2)
    check("with no pending intent", p.has_pending_intent(), false)
    check("and the public view is empty", p.public_intent_view().error, "no_sealed_intent")


# ---- 6. Closed public-view schema -------------------------------------------------------------------------------------------

func _test_closed_public_view() -> void:
    check("the allow-list literal", BjjHalfGuardSealedProtocol.PUBLIC_VIEW_KEYS, ["position_id", "window_id", "intent_serial", "initiator_id", "responder_id",
        "apparent_technique_id", "apparent_technique_name", "commitment_requested", "eligible_real_ids", "response_ids"])
    for action: String in [CF, FL, KS]:
        for commitment: String in ["", "LOW", "MEDIUM", "HIGH"]:
            var p := fresh()
            var w := opened(p)
            var seal := p.seal_intent(int(w.window_id), TOP_ID, action, commitment)
            var view := p.public_intent_view().values
            var keys := view.keys()
            keys.sort()
            check("the closed key set (%s %s)" % [action, commitment], keys, VIEW_KEYS)
            check("the seal call returns exactly the public view (%s %s)" % [action, commitment], seal.values, view)
            check("literal view (%s %s)" % [action, commitment], view, {"position_id": "half_guard", "window_id": 1, "intent_serial": 1,
                "initiator_id": TOP_ID, "responder_id": BOTTOM_ID, "apparent_technique_id": action,
                "apparent_technique_name": BjjHalfGuardCatalog.technique_name(action), "commitment_requested": "MEDIUM" if commitment.is_empty() else commitment,
                "eligible_real_ids": [KS] if action == CF else [], "response_ids": [HF, UF, KSH]})
            # GP-3: the REQUESTED commitment is public and is the only thing the commitment changes in the view
            var other := _view_for(action, "LOW" if commitment != "LOW" else "HIGH")
            other["commitment_requested"] = view.commitment_requested
            check("the view differs by the requested commitment only (%s %s)" % [action, commitment], view, other)
            for key: String in view:
                for fragment: String in ["feint", "sealed", "effective", "funded", "downgrade", "surcharge", "total", "real_action", "real_technique"]:
                    check("no hidden vocabulary '%s' in key %s" % [fragment, key], key.contains(fragment), false)
    # the bottom's seal presents Bottom's technique and Top's responses
    var q := fresh()
    var qw := opened(q)
    q.submit(int(qw.window_id), TOP_ID)
    var qw2 := opened(q)
    check("the second window is Bottom's", [qw2.fighter_id, qw2.role], [BOTTOM_ID, "bottom"])
    q.seal_intent(int(qw2.window_id), BOTTOM_ID, RG, "LOW")
    check("Bottom's public view", q.public_intent_view().values, {"position_id": "half_guard", "window_id": 2, "intent_serial": 1,
        "initiator_id": BOTTOM_ID, "responder_id": TOP_ID, "apparent_technique_id": RG, "apparent_technique_name": "Recover Guard",
        "commitment_requested": "LOW", "eligible_real_ids": [], "response_ids": [HC, HP, KP]})
    check("only the owner reads the sealed view", [q.sealed_intent_view(TOP_ID).error, q.sealed_intent_view("").error, q.sealed_intent_view("stranger").error],
        ["not_intent_owner", "not_intent_owner", "not_intent_owner"])
    check("the owner reads it", q.sealed_intent_view(BOTTOM_ID).values, {"window_id": 2, "intent_serial": 1, "action_id": RG, "real_action_id": RG,
        "commitment_requested": "LOW"})


func _view_for(action: String, commitment: String) -> Dictionary:
    var p := fresh()
    var w := opened(p)
    p.seal_intent(int(w.window_id), TOP_ID, action, commitment)
    return p.public_intent_view().values


# ---- 7. The probing controller double (and its mutation-sensitivity control) ---------------------------------------------------------

class LeakyObject extends RefCounted:
    var innocent: String = "ok"
    var carried: Array = []

# BEGIN controller double (it is handed ONLY detached dictionaries; the scan below proves it never names executor internals)
func probe_leaks(value: Variant, secrets: Array, depth: int = 0) -> int:
    if depth > 10:
        return 0
    var found := 0
    match typeof(value):
        TYPE_STRING, TYPE_STRING_NAME:
            for secret: String in secrets:
                if str(value).contains(secret):
                    found += 1
        TYPE_DICTIONARY:
            var dictionary: Dictionary = value
            for key: Variant in dictionary:
                found += probe_leaks(key, secrets, depth + 1) + probe_leaks(dictionary[key], secrets, depth + 1)
        TYPE_ARRAY:
            for item: Variant in value:
                found += probe_leaks(item, secrets, depth + 1)
        TYPE_OBJECT:
            if value != null:
                for property: Dictionary in value.get_property_list():
                    found += probe_leaks(value.get(str(property.name)), secrets, depth + 1)
    return found
# END controller double


func _test_probing_controller() -> void:
    var secrets: Array = ["LOW", "MEDIUM", "HIGH"]
    # control: the probe really detects leaks of every shape, so a clean result below is meaningful
    var clean := {"a": "x", "b": ["y", {"c": "z"}]}
    check("the probe sees nothing in a clean structure", probe_leaks(clean, secrets), 0)
    check("the probe sees a leaked value", probe_leaks({"a": "HIGH"}, secrets), 1)
    check("the probe sees a leaked key", probe_leaks({"HIGH": 1}, secrets), 1)
    check("the probe sees a leak in a nested array", probe_leaks({"a": [1, ["x", {"b": "MEDIUM"}]]}, secrets), 1)
    check("the probe sees a leak embedded in a longer string", probe_leaks({"a": "commitment=LOW"}, secrets), 1)
    var leaky := LeakyObject.new()
    leaky.carried = [{"inner": "HIGH"}]
    check("the probe walks object properties", probe_leaks({"obj": leaky}, secrets), 1)
    # B1h: the REQUESTED commitment is public (GP-3). What stays executor-only, even for a direct command, is the sealed-store vocabulary: the real
    # technique's key, the feint flag and the surcharge. The very same probe must find none of it on any public surface before the reveal.
    var hidden: Array = ["real_action_id", "feint", "surcharge"]
    for action: String in [CF, FL, KS]:
        for commitment: String in COMMITMENTS:
            var p := fresh()
            var w := opened(p)
            var seal := p.seal_intent(int(w.window_id), TOP_ID, action, commitment)
            var view := p.public_intent_view().values
            check("the public view carries the requested commitment (%s %s)" % [action, commitment], view.commitment_requested, commitment)
            check("the public view leaks no sealed-store vocabulary (%s %s)" % [action, commitment], probe_leaks(view, hidden), 0)
            check("the seal report leaks none", probe_leaks(seal.values, hidden), 0)
            check("the public events leak none", probe_leaks(p.public_events(), hidden), 0)
            check("the public views of the gateway leak none", probe_leaks([p.window_fields(), p.state_fields(), p.history_fields(), p.snapshot()], hidden), 0)
            check("the responder's option menus leak none", probe_leaks([p.response_options(action).options.map(func(o: BjjPositionContract.Option) -> Dictionary: return o.fields()),
                p.action_options(BOTTOM_ID).options.map(func(o: BjjPositionContract.Option) -> Dictionary: return o.fields())], hidden), 0)
            # the executor surface DOES hold it, which is exactly why a controller must never be handed it
            check("control: the executor surface holds the sealed store", probe_leaks(p.executor_snapshot(), hidden) > 0, true)
            # injected leak: a view that adds a sealed-store key is caught by the very same probe
            var mutated := view.duplicate(true)
            mutated["real_action_id"] = action
            check("mutation control: a leaky view fails the probe", probe_leaks(mutated, hidden), 1)


# ---- 8. The defender cannot learn the sealed commitment from refusals, menus or any public surface -----------------------------------------

func _defender_transcript(action: String, commitment: String) -> Dictionary:
    var p := fresh()
    var w := opened(p)
    var id := int(w.window_id)
    var seal := p.seal_intent(id, TOP_ID, action, commitment)
    var codes: Array = []
    codes.append(p.respond(id, BOTTOM_ID, 2, HF, "LOW").error)
    codes.append(p.respond(id + 1, BOTTOM_ID, 1, HF, "LOW").error)
    codes.append(p.respond(id, TOP_ID, 1, HF, "LOW").error)
    codes.append(p.respond(id, BOTTOM_ID, 1, "nonsense", "LOW").error)
    codes.append(p.respond(id, BOTTOM_ID, 1, HF, "bad").error)
    codes.append(p.seal_intent(id, BOTTOM_ID, UH, "LOW").error)
    codes.append(p.seal_intent(id, TOP_ID, CF, "LOW").error)
    codes.append(p.submit(id, BOTTOM_ID).error)
    codes.append(p.open_window().error)
    codes.append(p.sealed_intent_view(BOTTOM_ID).error)
    codes.append(p.apply_response_timeout(id, 1, "nonsense", "LOW").error)
    return {"seal": seal.values, "view": p.public_intent_view().values, "codes": codes, "window": p.window_fields(),
        "state": p.state_fields(), "history": p.history_fields(), "simulation": p.snapshot(), "public_events": p.public_events(),
        "responses": p.response_options(action).options.map(func(o: BjjPositionContract.Option) -> Dictionary: return o.fields()),
        "own_menu": p.action_options(BOTTOM_ID).options.map(func(o: BjjPositionContract.Option) -> Dictionary: return o.fields())}


# GP-3: the requested commitment is public, so it is the ONE thing a defender transcript may differ by; blank it before comparing.
func _normalized(transcript: Dictionary) -> Dictionary:
    var copy := transcript.duplicate(true)
    copy.seal["commitment_requested"] = ""
    copy.view["commitment_requested"] = ""
    for event: Dictionary in copy.public_events:
        if event.has("commitment_requested"):
            event["commitment_requested"] = ""
    return copy


func _test_defender_indistinguishability() -> void:
    for action: String in [CF, FL, KS]:
        var reference := _defender_transcript(action, "MEDIUM")
        for commitment: String in ["", "LOW", "HIGH"]:
            var transcript := _defender_transcript(action, commitment)
            check("the requested commitment is what the defender sees (%s '%s')" % [action, commitment], [transcript.view.commitment_requested, transcript.seal.commitment_requested,
                transcript.public_events[0].commitment_requested], ["MEDIUM" if commitment.is_empty() else commitment, "MEDIUM" if commitment.is_empty() else commitment,
                "MEDIUM" if commitment.is_empty() else commitment])
            check("everything else the defender can observe is identical for %s sealed at '%s' versus MEDIUM" % [action, commitment],
                _normalized(transcript), _normalized(reference))
        check("the refusal codes are the expected literals", reference.codes, ["intent_serial_mismatch", "stale_window", "not_responder",
            "unknown_response", "invalid_response_commitment", "not_initiator", "intent_already_sealed", "intent_pending", "window_already_open",
            "not_intent_owner", "fallback_not_published"])
    # the refusal codes do not depend on the sealed technique either
    var codes_cf: Array = _defender_transcript(CF, "LOW").codes
    check("refusal codes are the same for Flatten", _defender_transcript(FL, "LOW").codes, codes_cf)
    check("refusal codes are the same for Knee Slice", _defender_transcript(KS, "HIGH").codes, codes_cf)
    # and no refusal is a probe of whether a commitment would fund: stamina is never charged by a refusal or a seal
    var poor := fresh(entry(2, 100))
    var w := opened(poor)
    var before := poor.snapshot()
    poor.seal_intent(int(w.window_id), TOP_ID, CF, "HIGH")
    check("a seal never charges stamina or moves any state, even when the commitment is unaffordable", poor.snapshot(), before)


# ---- 9. Events and redaction -------------------------------------------------------------------------------------------------------

func _event_names(events: Array) -> Array:
    return events.map(func(e: Dictionary) -> String: return str(e.event))


func _test_events_and_redaction() -> void:
    var p := fresh()
    var w := opened(p)
    var id := int(w.window_id)
    p.seal_intent(id, TOP_ID, KS, "HIGH")
    check("the seal appends exactly one executor event", p.protocol_events(), [{"event": "intent_sealed", "index": 1, "window_id": 1,
        "intent_serial": 1, "initiator_id": TOP_ID, "apparent_technique_id": KS, "commitment_requested": "HIGH", "real_action_id": KS}])
    check("the public stream carries the requested commitment (GP-3) and never the real technique's key", p.public_events(), [{"event": "intent_sealed",
        "index": 1, "window_id": 1, "intent_serial": 1, "initiator_id": TOP_ID, "apparent_technique_id": KS, "commitment_requested": "HIGH"}])
    var report := p.respond(id, BOTTOM_ID, 1, KSH, "LOW")
    var executor := p.protocol_events()
    check("one exchange appends exactly three events in order", _event_names(executor), ["intent_sealed", "response_committed", "exchange_revealed"])
    check("event indices are contiguous", executor.map(func(e: Dictionary) -> int: return int(e.index)), [1, 2, 3])
    check("the response event", executor[1], {"event": "response_committed", "index": 2, "window_id": 1, "intent_serial": 1,
        "responder_id": BOTTOM_ID, "response_id": KSH, "response_commitment_requested": "LOW", "defaulted": false})
    var revealed: Dictionary = executor[2]
    check("the reveal carries the resolved intent", [revealed.action_id, revealed.commitment_requested, revealed.initiator_id, revealed.responder_id],
        [KS, "HIGH", TOP_ID, BOTTOM_ID])
    check("the reveal carries the resolved outcome", revealed.settlement, report.values.detail.settlement)
    check("the reveal carries the transition and end flag", [revealed.transition, revealed.ended], [report.values.transition, report.values.ended])
    var public_stream := p.public_events()
    check("the public stream after the reveal still omits the sealed event's real-technique key", public_stream[0].has("real_action_id"), false)
    check("the reveal publishes the resolved intent", [public_stream[2].commitment_requested, public_stream[2].apparent_action_id, public_stream[2].action_id,
        public_stream[2].feint], ["HIGH", KS, KS, false])
    # refusals append nothing and a pass appends nothing
    var n := p.protocol_events().size()
    p.respond(id, BOTTOM_ID, 1, KSH, "LOW")
    p.seal_intent(id, TOP_ID, CF, "LOW")
    check("refusals append no event", p.protocol_events().size(), n)
    var w2 := opened(p)
    p.submit(int(w2.window_id), BOTTOM_ID)
    check("a pass appends no protocol event", p.protocol_events().size(), n)


# ---- 10. Every returned value is detached ----------------------------------------------------------------------------------------------

func _test_detached_values() -> void:
    var p := sealed("HIGH", CF)
    var before := p.executor_snapshot()
    var view := p.public_intent_view().values
    view["apparent_technique_id"] = "tampered"
    (view["response_ids"] as Array).append("tampered")
    var own := p.sealed_intent_view(TOP_ID).values
    own["commitment_requested"] = "LOW"
    var events := p.protocol_events()
    events[0]["commitment_requested"] = "LOW"
    events.clear()
    var public_events := p.public_events()
    public_events[0]["apparent_technique_id"] = "tampered"
    var snapshot := p.executor_snapshot()
    snapshot.pending["action_id"] = "tampered"
    snapshot.gateway["axis_tenths"] = 999
    var window := p.window_fields()
    window["open"] = false
    var state := p.state_fields()
    state["axis_tenths"] = 999
    var simulation := p.snapshot()
    simulation["axis_tenths"] = 999
    check("mutating any returned value changes nothing", p.executor_snapshot(), before)
    var resolved := p.respond(1, BOTTOM_ID, 1, HF, "LOW")
    var settlement: Dictionary = resolved.values.detail.settlement
    settlement["final_grade"] = 99
    var revealed: Dictionary = p.protocol_events()[2]
    check("a returned report does not alias the revealed event", revealed.settlement.final_grade != 99, true)
    var stream: Array = p.protocol_events()
    stream[2]["settlement"]["final_grade"] = 77
    check("the event log does not alias a returned copy", p.protocol_events()[2].settlement.final_grade != 77, true)
    var log_before := p.protocol_events()
    var public_stream := p.public_events()
    public_stream[1]["response_id"] = "tampered"
    public_stream[2]["settlement"]["final_grade"] = 55
    public_stream[2]["transition"]["kind"] = "tampered"
    check("mutating the public stream (resolved events) changes nothing in the executor log", p.protocol_events(), log_before)
    check("and the next public stream is clean", p.public_events()[1].response_id, HF)


# ---- 11. Lockstep against the unchanged one-call path ------------------------------------------------------------------------------------

func _step_plans() -> Array:
    var plans: Array = []
    var kinds: Array = ["exchange", "exchange", "timeout", "legacy", "pass", "exchange"]
    var index := 0
    for stamina: Array in [[100, 100], [60, 45], [14, 9], [3, 2], [0, 0]]:
        for commitment: String in ["", "LOW", "MEDIUM", "HIGH"]:
            for response_commitment: String in ["", "LOW", "MEDIUM", "HIGH"]:
                var steps: Array = []
                for round_index in range(6):
                    steps.append({"kind": kinds[(round_index + index) % kinds.size()], "a": index + round_index, "r": index + 2 * round_index,
                        "c": commitment, "rc": response_commitment})
                plans.append({"label": "stamina %s c=%s rc=%s" % [stamina, commitment, response_commitment], "entry": entry(stamina[0], stamina[1]), "steps": steps})
                index += 1
    return plans


func _test_lockstep_against_the_direct_path() -> void:
    for plan: Dictionary in _step_plans():
        _lockstep(str(plan.label), plan.entry, plan.steps)


func _same_views(tag: String, p: BjjHalfGuardSealedProtocol, t: BjjHalfGuardWindowGateway) -> void:
    check(tag + " snapshot", p.snapshot(), t.snapshot())
    check(tag + " window", p.window_fields(), t.window_fields())
    check(tag + " state", p.state_fields(), t.state_fields())
    check(tag + " history", p.history_fields(), t.history_fields())
    check(tag + " roles", [p.roles().initiative_id, p.roles().control_authority_id], [t.roles().initiative_id, t.roles().control_authority_id])
    check(tag + " terminal", p.is_terminal(), t.is_terminal())


func _lockstep(label: String, request: Dictionary, steps: Array) -> void:
    var p := fresh(request)
    var t := twin(request)
    for index in range(steps.size()):
        var step: Dictionary = steps[index]
        var tag := "%s step %d %s" % [label, index, step.kind]
        var open_p := p.open_window()
        var open_t := t.open_window()
        check(tag + " open", rep(open_p), rep(open_t))
        if not open_p.ok() or bool(open_p.values.closed):
            _same_views(tag + " after the closing open", p, t)
            check(tag + " nothing can be sealed without a window", p.seal_intent(int(open_p.values.get("window_id", 0)) + 1, TOP_ID, CF, "LOW").ok(), false)
            break
        var role := str(open_p.values.role)
        var other := "bottom" if role == "top" else "top"
        var fighter_id := str(open_p.values.fighter_id)
        var responder_id := BOTTOM_ID if fighter_id == TOP_ID else TOP_ID
        var window_id := int(open_p.values.window_id)
        var actions := BjjHalfGuardCatalog.actions_of(role)
        var responses := BjjHalfGuardCatalog.responses_of(other)
        var action: String = actions[int(step.a) % actions.size()]
        var response: String = responses[int(step.r) % responses.size()]
        if step.kind == "pass":
            check(tag + " pass", rep(p.submit(window_id, fighter_id)), rep(t.submit(window_id, fighter_id)))
        elif step.kind == "legacy":
            check(tag + " legacy exchange", rep(p.submit(window_id, fighter_id, action, response, step.c, step.rc)),
                rep(t.submit(window_id, fighter_id, action, response, step.c, step.rc)))
        else:
            var seal := p.seal_intent(window_id, fighter_id, action, step.c)
            check(tag + " seal accepted", seal.ok(), true)
            _same_views(tag + " after the seal (a seal changes nothing)", p, t)
            var events_before := p.protocol_events().size()
            var done: BjjMatchWindowGateway.Report
            var direct: BjjMatchWindowGateway.Report
            if step.kind == "timeout":
                # B1h: a timeout accepts only the published fallback of the defender's role (Bottom Hip Frame LOW, Top Hip Pressure LOW).
                var published := BjjHalfGuardCatalog.timeout_fallback(other)
                done = p.apply_response_timeout(window_id, int(seal.values.intent_serial), str(published.response_id), str(published.commitment))
                direct = t.submit(window_id, fighter_id, action, str(published.response_id), step.c, str(published.commitment))
            else:
                done = p.respond(window_id, responder_id, int(seal.values.intent_serial), response, step.rc)
                direct = t.submit(window_id, fighter_id, action, response, step.c, step.rc)
            check(tag + " resolved report equals the direct path", rep(done), rep(direct))
            check(tag + " the seal is consumed", p.has_pending_intent(), false)
            check(tag + " the resolution appends two events after the seal's one", p.protocol_events().size() - events_before, 2)
        _same_views(tag + " after", p, t)
        check(tag + " the window is closed (no hidden extra window)", p.window_fields().open, false)
        check(tag + " window id unchanged by resolution", p.window_fields().window_id, window_id)
    check(label + " final snapshot", p.snapshot(), t.snapshot())
    check(label + " nothing left pending", p.has_pending_intent(), false)


# ---- 12. One settlement, one clock advance, one initiative change (literal arithmetic) ----------------------------------------------------------

func _test_accounting_literals() -> void:
    var p := fresh()
    var w := opened(p)
    check("opening advances the clock once", p.state_fields().clock_seconds, 295)
    var seal := p.seal_intent(int(w.window_id), TOP_ID, CF, "MEDIUM")
    check("the seal charges nothing", [p.state_fields().top_stamina, p.state_fields().bottom_stamina], [100, 100])
    check("the seal does not move the clock", p.state_fields().clock_seconds, 295)
    check("the seal does not change initiative", p.roles().initiative_id, TOP_ID)
    check("the seal opens no window", p.window_fields(), {"open": true, "window_id": 1, "fighter_id": TOP_ID, "role": "top"})
    check("the seal writes no history", p.history_fields(), BjjHalfGuardMatch.empty_history())
    var refused := p.respond(1, BOTTOM_ID, 1, "nonsense", "MEDIUM")
    check("a refused response charges nothing", [refused.ok(), p.state_fields().top_stamina, p.state_fields().bottom_stamina], [false, 100, 100])
    var done := p.respond(1, BOTTOM_ID, int(seal.values.intent_serial), HF, "MEDIUM")
    check("the exchange is accepted", done.ok(), true)
    check("each side is charged exactly once (MEDIUM costs 7)", [p.state_fields().top_stamina, p.state_fields().bottom_stamina], [93, 93])
    check("the clock did not move again", p.state_fields().clock_seconds, 295)
    check("initiative changed exactly once", p.roles().initiative_id, BOTTOM_ID)
    check("exactly one exchange was recorded", [p.history_fields().initiated_action_history, p.history_fields().response_history,
        p.history_fields().top_initiation_count, p.history_fields().bottom_initiation_count], [[CF], [HF], 1, 0])
    check("the window is closed and no other window exists", [p.window_fields().open, p.window_fields().window_id], [false, 1])
    var next := p.open_window()
    check("the next window is the very next id, for the new initiative", [next.values.window_id, next.values.fighter_id], [2, BOTTOM_ID])
    check("the next window advances the clock once", p.state_fields().clock_seconds, 290)
    check("the next window starts with no carried intent", [p.has_pending_intent(), p.public_intent_view().error], [false, "no_sealed_intent"])
    # a pass still costs nothing and flips initiative once
    p.submit(2, BOTTOM_ID)
    check("a pass flips initiative once and charges nothing", [p.roles().initiative_id, p.state_fields().top_stamina, p.state_fields().bottom_stamina], [TOP_ID, 93, 93])


# ---- 13. Exits, terminal states and timeout of the match clock -----------------------------------------------------------------------------------

func _poke(p: BjjHalfGuardSealedProtocol, t: BjjHalfGuardWindowGateway, axis: int, band: int, initiator: String) -> void:
    for state: BjjHalfGuardMatch in [p._gateway._match, t._match]:
        state.axis_tenths = axis
        state.band = band
        state.initiator = initiator


func _test_exits_and_terminal() -> void:
    var cases: Array = [
        {"label": "Side Control exit", "axis": 25, "band": 1, "initiator": "top", "action": KS, "response": HF, "c": "HIGH", "rc": "LOW"},
        {"label": "Side Control exit at Strong Success", "axis": 25, "band": 1, "initiator": "top", "action": KS, "response": UF, "c": "MEDIUM", "rc": "MEDIUM"},
        {"label": "Open Guard exit", "axis": -25, "band": -2, "initiator": "bottom", "action": RG, "response": HP, "c": "MEDIUM", "rc": "HIGH"},
        {"label": "Closed Guard exit", "axis": -15, "band": -1, "initiator": "bottom", "action": RG, "response": HC, "c": "MEDIUM", "rc": "MEDIUM"},
        {"label": "a break attempt that does not exit", "axis": 19, "band": 1, "initiator": "top", "action": KS, "response": HF, "c": "MEDIUM", "rc": "MEDIUM"},
        {"label": "an ordinary exchange", "axis": 5, "band": 0, "initiator": "top", "action": CF, "response": HF, "c": "LOW", "rc": "LOW"},
    ]
    var exits := 0
    for case: Dictionary in cases:
        var p := fresh()
        var t := twin()
        _poke(p, t, int(case.axis), int(case.band), str(case.initiator))
        var wp := p.open_window()
        var wt := t.open_window()
        check(case.label + " open", rep(wp), rep(wt))
        var fighter_id := str(wp.values.fighter_id)
        var responder_id := BOTTOM_ID if fighter_id == TOP_ID else TOP_ID
        var seal := p.seal_intent(int(wp.values.window_id), fighter_id, str(case.action), str(case.c))
        var done := p.respond(int(wp.values.window_id), responder_id, int(seal.values.intent_serial), str(case.response), str(case.rc))
        var direct := t.submit(int(wt.values.window_id), fighter_id, str(case.action), str(case.response), str(case.c), str(case.rc))
        check(case.label + " report equals the direct path", rep(done), rep(direct))
        _same_views(case.label, p, t)
        var event: Dictionary = p.protocol_events()[2]
        check(case.label + " the reveal reports the transition and end flag of the direct path", [event.transition, event.ended],
            [direct.values.transition, direct.values.ended])
        if bool(direct.values.ended):
            exits += 1
            check(case.label + " is terminal", p.is_terminal(), true)
            var b := p.executor_snapshot()
            expect_refused(case.label + ": the ended segment opens no window", p, b, p.open_window(), rep(t.open_window()).error)
            expect_refused(case.label + ": nothing can be sealed after the end", p, b, p.seal_intent(int(wp.values.window_id), fighter_id, str(case.action), "LOW"), "no_open_window")
            expect_refused(case.label + ": nothing can be answered after the end", p, b, p.respond(int(wp.values.window_id), responder_id, 1, str(case.response), "LOW"), "no_open_window")
            check(case.label + " the unchanged gateway agrees that it ended", t.is_terminal(), true)
    check("all four exits were exercised, and the two non-exits were not exits", exits, 4)
    # a real transition destination is reported, and nothing is invented for it
    var q := fresh()
    var u := twin()
    _poke(q, u, 25, 1, "top")
    var wq := q.open_window().values
    u.open_window()
    q.seal_intent(int(wq.window_id), TOP_ID, KS, "HIGH")
    q.respond(int(wq.window_id), BOTTOM_ID, 1, UF, "LOW")
    check("the exit is Side Control with a resolved declared destination", q.protocol_events()[2].transition,
        {"kind": "exit", "raw_destination": "Side Control", "destination_position_id": "side_control", "resolved": true})
    # the match clock ending is terminal and nothing is sealable (timeout is a terminal outcome, not an exit)
    var timed := fresh(entry(100, 100, 12, 5))
    var first := opened(timed)
    timed.seal_intent(int(first.window_id), TOP_ID, CF, "LOW")
    timed.respond(int(first.window_id), BOTTOM_ID, 1, HF, "LOW")
    var second := timed.open_window()
    check("the second window opens with the clock still running", [second.values.window_id, timed.state_fields().clock_seconds], [2, 2])
    timed.submit(2, BOTTOM_ID)
    var closing := timed.open_window()
    check("the clock reaches zero and no window opens", [closing.values.closed, closing.values.window_open], [true, false])
    check("the segment ended by the clock", [timed.is_terminal(), timed.state_fields().exit_destination, timed.state_fields().clock_seconds], [true, "", 0])
    var tb := timed.executor_snapshot()
    expect_refused("nothing can be sealed after the timeout", timed, tb, timed.seal_intent(2, TOP_ID, CF, "LOW"), "no_open_window")
    expect_refused("nothing can be answered after the timeout", timed, tb, timed.respond(2, BOTTOM_ID, 1, HF, "LOW"), "no_open_window")


# ---- 14. Stale and duplicate delivery ------------------------------------------------------------------------------------------------------------

func _test_stale_and_duplicate_delivery() -> void:
    var p := fresh()
    var t := twin()
    var w := opened(p)
    t.open_window()
    p.seal_intent(1, TOP_ID, CF, "LOW")
    p.respond(1, BOTTOM_ID, 1, HF, "LOW")
    t.submit(1, TOP_ID, CF, HF, "LOW", "LOW")
    var settled := p.executor_snapshot()
    # a duplicated delivery of the consumed commands cannot double-spend
    expect_refused("a replayed seal for the consumed window", p, settled, p.seal_intent(1, TOP_ID, CF, "LOW"), "no_open_window")
    expect_refused("a replayed response for the consumed window", p, settled, p.respond(1, BOTTOM_ID, 1, HF, "LOW"), "no_open_window")
    expect_refused("a replayed timeout for the consumed window", p, settled, p.apply_response_timeout(1, 1, HF, "LOW"), "no_open_window")
    check("the simulation still equals the single direct exchange", p.snapshot(), t.snapshot())
    # in the next window the old identifiers are stale
    var w2 := p.open_window().values
    t.open_window()
    var next := p.executor_snapshot()
    expect_refused("old window id, no seal yet", p, next, p.seal_intent(1, BOTTOM_ID, UH, "LOW"), "stale_window")
    expect_refused("old response, no seal yet", p, next, p.respond(2, TOP_ID, 1, HC, "LOW"), "no_sealed_intent")
    var seal := p.seal_intent(2, BOTTOM_ID, UH, "LOW")
    check("the new seal gets the next serial", seal.values.intent_serial, 2)
    var pending := p.executor_snapshot()
    expect_refused("the old serial cannot answer the new seal", p, pending, p.respond(2, TOP_ID, 1, HC, "LOW"), "intent_serial_mismatch")
    expect_refused("the old window cannot answer the new seal", p, pending, p.respond(1, TOP_ID, 2, HC, "LOW"), "stale_window")
    expect_refused("the old seal command cannot reseal", p, pending, p.seal_intent(1, TOP_ID, CF, "LOW"), "stale_window")
    check("the new window id was issued exactly once", w2.window_id, 2)
    p.respond(2, TOP_ID, 2, HC, "LOW")
    t.submit(2, BOTTOM_ID, UH, HC, "LOW", "LOW")
    check("two exchanges equal two direct exchanges", p.snapshot(), t.snapshot())


# ---- 15. Ending the session with an unresolved seal ---------------------------------------------------------------------------------------------

func _test_session_end() -> void:
    var p := sealed("HIGH", KS)
    var simulation := p.snapshot()
    var ended := p.end_session()
    check("the session ends", ended.ok(), true)
    check("the discarded serial is reported", ended.values, {"discarded_intent_serial": 1})
    check("the seal is discarded, never resolved: the simulation is exactly as before", p.snapshot(), simulation)
    check("no stamina, history, clock or initiative change", [p.state_fields().top_stamina, p.state_fields().bottom_stamina,
        p.state_fields().clock_seconds, p.history_fields(), p.roles().initiative_id], [100, 100, 295, BjjHalfGuardMatch.empty_history(), TOP_ID])
    check("nothing is pending", [p.has_pending_intent(), p.is_closed()], [false, true])
    check("the end is recorded as an event", p.protocol_events().back(), {"event": "session_closed", "index": 2, "discarded_intent_serial": 1})
    var b := p.executor_snapshot()
    expect_refused("seal after the end", p, b, p.seal_intent(1, TOP_ID, CF, "LOW"), "session_closed")
    expect_refused("respond after the end", p, b, p.respond(1, BOTTOM_ID, 1, HF, "LOW"), "session_closed")
    expect_refused("timeout after the end", p, b, p.apply_response_timeout(1, 1, HF, "LOW"), "session_closed")
    expect_refused("legacy submit after the end", p, b, p.submit(1, TOP_ID), "session_closed")
    expect_refused("open after the end", p, b, p.open_window(), "session_closed")
    expect_refused("timed open after the end", p, b, p.open_window_for(0), "session_closed")
    expect_refused("a second end", p, b, p.end_session(), "session_closed")
    expect_refused("the public view after the end", p, b, p.public_intent_view(), "session_closed")
    expect_refused("the sealed view after the end", p, b, p.sealed_intent_view(TOP_ID), "session_closed")
    check("read-only views still work after the end", [p.state_fields().clock_seconds, p.snapshot() == simulation], [295, true])
    var clean := fresh()
    check("ending a session with nothing pending discards serial 0", clean.end_session().values, {"discarded_intent_serial": 0})
    var open_window := fresh()
    opened(open_window)
    check("ending with an open window and no seal discards nothing", open_window.end_session().values, {"discarded_intent_serial": 0})
    # a resolved exchange leaves nothing for the end to discard
    var done := sealed("LOW", CF)
    done.respond(1, BOTTOM_ID, 1, HF, "LOW")
    check("a resolved seal is not discarded again", done.end_session().values, {"discarded_intent_serial": 0})


# ---- 16. Deterministic replay ---------------------------------------------------------------------------------------------------------------------

func _scenario_log() -> Array:
    return [
        {"op": "seal", "w": 1, "f": TOP_ID, "a": CF, "c": "LOW"},
        {"op": "open"},
        {"op": "seal", "w": 1, "f": TOP_ID, "a": CF, "c": "bad"},
        {"op": "seal", "w": 1, "f": TOP_ID, "a": CF, "c": "HIGH"},
        {"op": "seal", "w": 1, "f": TOP_ID, "a": FL, "c": "LOW"},
        {"op": "respond", "w": 1, "f": TOP_ID, "s": 1, "r": HF, "rc": "LOW"},
        {"op": "respond", "w": 1, "f": BOTTOM_ID, "s": 1, "r": "nonsense", "rc": "LOW"},
        {"op": "respond", "w": 1, "f": BOTTOM_ID, "s": 1, "r": UF, "rc": "HIGH"},
        {"op": "open"},
        {"op": "seal", "w": 2, "f": BOTTOM_ID, "a": UH, "c": "MEDIUM"},
        {"op": "timeout", "w": 2, "s": 2, "r": HP, "rc": "LOW"},
        {"op": "open"},
        {"op": "submit", "w": 3, "f": TOP_ID},
        {"op": "open"},
        {"op": "seal", "w": 4, "f": BOTTOM_ID, "a": UH, "c": ""},
        {"op": "end"},
        {"op": "seal", "w": 4, "f": BOTTOM_ID, "a": UH, "c": ""},
    ]


func _run_log(p: BjjHalfGuardSealedProtocol, log: Array) -> Array:
    var outcomes: Array = []
    for step: Dictionary in log:
        match str(step.op):
            "open":
                outcomes.append(rep(p.open_window()))
            "seal":
                outcomes.append(rep(p.seal_intent(int(step.w), str(step.f), str(step.a), str(step.c))))
            "respond":
                outcomes.append(rep(p.respond(int(step.w), str(step.f), int(step.s), str(step.r), str(step.rc))))
            "timeout":
                outcomes.append(rep(p.apply_response_timeout(int(step.w), int(step.s), str(step.r), str(step.rc))))
            "submit":
                outcomes.append(rep(p.submit(int(step.w), str(step.f))))
            "end":
                outcomes.append(rep(p.end_session()))
    return outcomes


func _test_deterministic_replay() -> void:
    var log := _scenario_log()
    var first := fresh()
    var second := fresh()
    var out_first := _run_log(first, log)
    var out_second := _run_log(second, log)
    check("every outcome replays identically", out_first, out_second)
    check("the whole executor state replays identically", first.executor_snapshot(), second.executor_snapshot())
    check("the public stream replays identically", first.public_events(), second.public_events())
    var errors: Array = out_first.map(func(o: Dictionary) -> String: return str(o.error))
    check("the scenario's refusals and acceptances are as designed", errors, ["no_open_window", "", "invalid_commitment", "", "intent_already_sealed",
        "not_responder", "unknown_response", "", "", "", "", "", "", "", "", "", "session_closed"])
    check("the seeded history is exactly the two resolved exchanges", first.history_fields().initiated_action_history, [CF, UH])
    check("and the resolved responses, the second one defaulted by the session", [first.history_fields().response_history, first.protocol_events()[4].defaulted], [[UF, HP], true])
    # the executor's own event log is a replayable command log: windows are session-side, so the replay opens one per seal
    var original := fresh()
    original.open_window()
    original.seal_intent(1, TOP_ID, CF, "HIGH")
    original.respond(1, BOTTOM_ID, 1, UF, "LOW")
    original.open_window()
    original.seal_intent(2, BOTTOM_ID, UH, "MEDIUM")
    original.apply_response_timeout(2, 2, HP, "LOW")
    var rebuilt := fresh()
    for event: Dictionary in original.protocol_events():
        match str(event.event):
            "intent_sealed":
                rebuilt.open_window()
                rebuilt.seal_intent(int(event.window_id), str(event.initiator_id), str(event.apparent_technique_id), str(event.commitment_requested))
            "response_committed":
                if bool(event.defaulted):
                    rebuilt.apply_response_timeout(int(event.window_id), int(event.intent_serial), str(event.response_id), str(event.response_commitment_requested))
                else:
                    rebuilt.respond(int(event.window_id), str(event.responder_id), int(event.intent_serial), str(event.response_id), str(event.response_commitment_requested))
    check("replaying the resolved command log reproduces the whole executor state", rebuilt.executor_snapshot(), original.executor_snapshot())
    check("and the public stream", rebuilt.public_events(), original.public_events())


# ---- 17. Compatibility with the independent oracle -----------------------------------------------------------------------------------------------------

func _decode(value: Variant) -> Variant:
    match typeof(value):
        TYPE_DICTIONARY:
            var dictionary: Dictionary = value
            if dictionary.size() == 1 and dictionary.has("$float"):
                return float(dictionary["$float"])
            var out := {}
            for key: Variant in dictionary:
                out[key] = _decode(dictionary[key])
            return out
        TYPE_ARRAY:
            var out_array: Array = []
            for item: Variant in value:
                out_array.append(_decode(item))
            return out_array
        TYPE_FLOAT:
            var number: float = value
            if number == floorf(number) and absf(number) <= 9007199254740992.0:
                return int(number)
            return number
    return value


func _rows(family_names: Array) -> Array:
    var rows: Array = []
    var fixture := FileAccess.open(FIXTURE, FileAccess.READ)
    if fixture == null:
        failures += 1
        push_error("Generate the Half Guard Python oracle fixture first")
        return rows
    while not fixture.eof_reached():
        var line := fixture.get_line()
        if line.is_empty():
            continue
        var row: Dictionary = JSON.parse_string(line)
        if family_names.has(str(row.family)):
            rows.append(row)
    return rows


# The oracle's codes for the two shape errors the seal/respond menus express as "not in the menu".
func _oracle_code(code: String) -> String:
    return {"incorrect_action_side_or_kind": "unknown_action", "incorrect_response_side_or_kind": "unknown_response"}.get(code, code)


func _rebuild(request: Variant, applied: Array) -> BjjHalfGuardSealedProtocol:
    var p := fresh(request)
    for command: Dictionary in applied:
        if str(command.op) == "open":
            p.open_window_for(command.duration)
        elif str(command.action_id).is_empty():
            p.submit(int(command.window_id), str(command.fighter_id), "", str(command.response_id), str(command.commitment), str(command.response_commitment))
        else:
            _seal_and_respond(p, command)
    return p


func _seal_and_respond(p: BjjHalfGuardSealedProtocol, command: Dictionary) -> BjjMatchWindowGateway.Report:
    var fighter_id := str(command.fighter_id)
    var seal := p.seal_intent(int(command.window_id), fighter_id, str(command.action_id), str(command.commitment))
    if not seal.ok():
        return seal
    var responder_id := ""
    for role: Variant in p.roles().fighter_by_role:
        if str(p.roles().fighter_by_role[role]) != fighter_id:
            responder_id = str(p.roles().fighter_by_role[role])
    return p.respond(int(command.window_id), responder_id, int(seal.values.intent_serial), str(command.response_id), str(command.response_commitment))


func _test_oracle_trajectories() -> void:
    var trajectories := 0
    var driven := 0
    var refused_exchanges := 0
    var accepted_exchanges := 0
    var transitions := 0
    var terminals := 0
    for row: Dictionary in _rows(["trajectory"]):
        trajectories += 1
        oracle_rows += 1
        var request: Variant = _decode(row.entry)
        var commands: Array = _decode(row.commands)
        var expected: Array = row.expected.results
        var main := fresh(request)
        var applied: Array = []
        for index in range(commands.size()):
            var command: Dictionary = commands[index]
            var want: Dictionary = expected[index]
            var tag := "oracle %s command %d" % [row.name, index]
            match str(command.op):
                "open":
                    check_loose(tag + " open", rep(main.open_window_for(command.duration)), want)
                    applied.append(command)
                    driven += 1
                "attempt":
                    # a match-level attempt is not a protocol operation; the oracle refuses it (terminal) and nothing may change
                    var before := main.executor_snapshot()
                    check(tag + " is a refusal in the oracle", str(want.error).is_empty(), false)
                    check(tag + " has no protocol equivalent and the ended segment cannot be sealed", main.seal_intent(int(main.window_fields().window_id), TOP_ID, CF, "LOW").ok(), false)
                    check(tag + " leaves the executor unchanged", main.executor_snapshot(), before)
                "submit":
                    driven += 1
                    if str(command.action_id).is_empty():
                        check_loose(tag + " pass or refused pass", rep(main.submit(int(command.window_id), str(command.fighter_id), "",
                            str(command.response_id), str(command.commitment), str(command.response_commitment))), want)
                        if str(want.error).is_empty():
                            applied.append(command)
                    else:
                        var probe := _rebuild(request, applied)
                        var probe_before := probe.snapshot()
                        var outcome := _seal_and_respond(probe, command)
                        if outcome.ok():
                            accepted_exchanges += 1
                            check(tag + " the protocol accepts exactly what the oracle accepts", str(want.error).is_empty(), true)
                            check_loose(tag + " exchange report", rep(outcome), want)
                            var applied_main := _seal_and_respond(main, command)
                            check_loose(tag + " exchange report on the main protocol", rep(applied_main), want)
                            applied.append(command)
                            if bool(want.transition.get("resolved", false)) or str(want.transition.get("kind", "none")) == "exit":
                                transitions += 1
                            if bool(want.ended):
                                terminals += 1
                        else:
                            refused_exchanges += 1
                            check(tag + " the protocol refuses exactly what the oracle refuses", str(want.error).is_empty(), false)
                            check(tag + " refusal code (mapped)", outcome.error, _oracle_code(str(want.error)))
                            check(tag + " the refusal changed no simulation state", probe.snapshot(), probe_before)
        check_loose("oracle %s final snapshot" % row.name, main.snapshot(), row.expected.final)
        check("oracle %s leaves nothing pending" % row.name, main.has_pending_intent(), false)
    check("all ten oracle trajectories were replayed", trajectories, 10)
    check("the oracle trajectories exercise accepted exchanges", accepted_exchanges, 12)
    check("and refused exchanges", refused_exchanges, 20)
    check("including an exit transition", transitions >= 1, true)
    check("including terminal exchanges", terminals >= 1, true)
    check("most trajectory operations were driven through the protocol", driven > 60, true)


func _test_oracle_grids() -> void:
    var rows := 0
    var exits := 0
    var attempts_ended := 0
    for row: Dictionary in _rows(["exchange_grid", "break_grid"]):
        rows += 1
        oracle_rows += 1
        var snapshot: Dictionary = _decode(row.snapshot)
        var command: Dictionary = _decode(row.command)
        var request := {"role_map": snapshot.role_map.duplicate(true), "fighters": snapshot.fighters.duplicate(true),
            "clock": {"initial_seconds": snapshot.initial_clock, "remaining_seconds": snapshot.clock_seconds},
            "window": {"last_issued_id": snapshot.window_id}, "interval_seconds": snapshot.interval_seconds}
        var p := fresh(request)
        var state := p._gateway._match
        state.axis_tenths = snapshot.axis_tenths
        state.band = snapshot.band
        state.initiator = snapshot.initiator
        state.top_base = snapshot.top_base
        state.bottom_frame = snapshot.bottom_frame
        state.exit_destination = snapshot.exit_destination
        state.exit_reason = snapshot.exit_reason
        state.history = snapshot.history.duplicate(true)
        state.window_open = true
        state.window_side = snapshot.initiator
        var initiator_id: String = snapshot.role_map[snapshot.initiator]
        var responder_id: String = snapshot.role_map["bottom" if snapshot.initiator == "top" else "top"]
        var seal := p.seal_intent(int(snapshot.window_id), initiator_id, str(command.action_id), str(command.commitment))
        var done := p.respond(int(snapshot.window_id), responder_id, 1, str(command.response_id), str(command.response_commitment))
        if not (seal.ok() and done.ok()):
            check("grid row %d is accepted by the protocol" % rows, [seal.error, done.error], ["", ""])
            continue
        var settlement: Dictionary = done.values.detail.settlement.duplicate(true)
        settlement["error"] = ""
        check_loose("grid row %d settlement" % rows, settlement, row.expected)
        var final: Dictionary = _decode(row.final)
        final["window_open"] = false
        final["window_side"] = ""
        check_loose("grid row %d final snapshot" % rows, p.snapshot(), final)
        if not str(row.expected.exit_destination).is_empty():
            exits += 1
            check("grid row %d the exit is reported by the reveal" % rows, p.protocol_events()[2].transition.raw_destination, row.expected.exit_destination)
        if bool(done.values.ended):
            attempts_ended += 1
    check("every grid row was replayed", rows, 16281)
    check("the grid includes exchanges that exit", exits > 0, true)
    check("and ended exchanges are reported as ended", attempts_ended, exits)


# ---- 18. Other surfaces are unchanged -----------------------------------------------------------------------------------------------------------------

func _method_names(script: GDScript) -> Array:
    var names: Array = []
    for method: Dictionary in script.get_script_method_list():
        names.append(str(method.name))
    names.sort()
    return names


func _test_unchanged_surfaces() -> void:
    var gateway_methods := _method_names(BjjHalfGuardWindowGateway)
    check("the Half Guard gateway's method set is exactly the qualified one", gateway_methods, ["_report", "action_options", "behavior_fields", "controller_fields",
        "create", "eligible_real_ids", "feint_error", "history_fields", "is_terminal", "open_window", "open_window_for", "response_options", "roles",
        "selected_commitment", "snapshot", "state_fields", "submit", "submit_feint", "window_fields"])
    for method_name: String in ["seal_intent", "respond", "apply_response_timeout", "end_session", "public_intent_view", "sealed_intent_view"]:
        check("the Half Guard gateway has no %s" % method_name, gateway_methods.has(method_name), false)
        check("the Mount gateway has no %s" % method_name, _method_names(BjjMatchWindowGateway).has(method_name), false)
        check("the position graph has no %s" % method_name, _method_names(BjjPositionGraphMatch).has(method_name), false)
        check("the Half Guard match has no %s" % method_name, _method_names(BjjHalfGuardMatch).has(method_name), false)
        check("the Half Guard contract has no %s" % method_name, _method_names(BjjHalfGuardContract).has(method_name), false)
        check("the protocol has %s" % method_name, _method_names(BjjHalfGuardSealedProtocol).has(method_name), true)
    # the existing one-call path still behaves exactly as before on the unchanged gateway
    var g := twin()
    var w := g.open_window().values
    check("the one-call gateway path still resolves an exchange", g.submit(int(w.window_id), TOP_ID, CF, HF, "MEDIUM", "MEDIUM").ok(), true)
    check("and still charges once", [g.state_fields().top_stamina, g.state_fields().bottom_stamina], [93, 93])


# ---- 19. Scope and hygiene --------------------------------------------------------------------------------------------------------------------------------

func _code_text(path: String) -> String:
    var file := FileAccess.open(path, FileAccess.READ)
    if file == null:
        return ""
    var code_lines: Array[String] = []
    for source_line: String in file.get_as_text().split("\n"):
        code_lines.append(source_line.split("#")[0])
    return "\n".join(code_lines)


func _test_scope_and_hygiene() -> void:
    var text := _code_text(PROTOCOL_PATH)
    check("the protocol source is readable", text.is_empty(), false)
    for token: String in ["randi", "randf", "RandomNumberGenerator", "Time.", "OS.get_ticks", "await", "get_tree", "Engine.get_frames", "FileAccess", "preload(",
            "BjjMount", "BjjMatchWindowGateway.create", "BjjPositionGraphMatch", "BjjHalfGuardMatch", "BjjHalfGuardResolver", "BjjHalfGuardEntry", "BjjStaminaPool",
            "BjjStaminaCostPolicy", "BjjCommitmentSettlement", "spend", "set_current", "_match", "FEINT_PAIRS", "FEINT_SURCHARGE", "BjjGrade", "grade_after", "BjjD3B", "BjjBehaviorStaminaPolicy"]:
        check("the protocol has no %s" % token, text.contains(token), false)
    check("it reaches the gateway's submit only in the gated pass-through and the single resolution", text.count("_gateway.submit("), 2)
    check("and never through the match or contract", [text.contains(".attempt("), text.contains(".decide(")], [false, false])
    var rules_uses: Array = []
    for code_line: String in text.split("\n"):
        if code_line.contains("BjjHalfGuardRules"):
            rules_uses.append(code_line.contains("BjjHalfGuardRules.POSITION_ID"))
    check("the rules file is read only for the position id (no rule constant is copied)", rules_uses, [true])
    # B1h: the catalog is read only for the public technique name and the published fallback; every rule lives in the match
    var catalog_uses: Array = []
    for code_line: String in text.split("\n"):
        if code_line.contains("BjjHalfGuardCatalog"):
            catalog_uses.append(code_line.contains("BjjHalfGuardCatalog.technique_name(") or code_line.contains("BjjHalfGuardCatalog.timeout_fallback("))
    check("the catalog is used only for the technique name and the published fallback", catalog_uses, [true, true])
    check("a feint resolves through the gateway's submit_feint exactly once", text.count("_gateway.submit_feint("), 1)
    # no other source knows the protocol: dependency direction is protocol -> gateway only
    for path: String in ["half_guard_rules", "half_guard_catalog", "half_guard_resolver", "half_guard_entry", "half_guard_match", "half_guard_contract",
            "half_guard_window_gateway", "half_guard_mount_edge"]:
        var engine := _code_text("res://scripts/positions/half_guard/%s.gd" % path)
        check("%s is readable" % path, engine.is_empty(), false)
        check("%s never references the protocol" % path, engine.contains("SealedProtocol"), false)
    for path: String in ["res://scripts/positions/graph_match.gd", "res://scripts/positions/mount/mount_window_gateway.gd",
            "res://scripts/presentation/mount_debug_view.gd"]:
        var other := _code_text(path)
        check("%s is readable" % path, other.is_empty(), false)
        check("%s never references the protocol" % path, other.contains("SealedProtocol") or other.contains("seal_intent"), false)
    var seen := {}
    for directory: String in ["res://scripts/core", "res://scripts/positions", "res://scripts/positions/mount", "res://scripts/positions/half_guard",
            "res://scripts/presentation", "res://scripts/ui"]:
        var dir := DirAccess.open(directory)
        if dir == null:
            continue
        for file_name: String in dir.get_files():
            if file_name.ends_with(".gd") and not file_name.ends_with("half_guard_sealed_protocol.gd"):
                seen[directory + "/" + file_name] = _code_text(directory + "/" + file_name).contains("BjjHalfGuardSealedProtocol")
    var referencing: Array = []
    for path: String in seen:
        if seen[path]:
            referencing.append(path)
    check("no production source references the protocol yet (it is an explicit opt-in path)", referencing, [])
    # the controller double above never names executor internals
    var own := FileAccess.open("res://tests/test_half_guard_sealed_protocol.gd", FileAccess.READ).get_as_text()
    var begin := own.find("# BEGIN controller double")
    var finish := own.find("# END controller double")
    check("the controller double is delimited", begin >= 0 and finish > begin, true)
    var controller := own.substr(begin, finish - begin)
    for token: String in ["_pending", "_gateway", "executor_snapshot", "protocol_events", "sealed_intent_view", "_events", "_serial", "has_pending_intent"]:
        check("the controller double never names %s" % token, controller.contains(token), false)
