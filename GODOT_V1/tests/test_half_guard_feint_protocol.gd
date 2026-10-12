extends SceneTree

# Negative-first tests for the Half Guard feints through the sealed-intent protocol (B1h, HALF_GUARD_V0_RULES.md section 13).
# Expected values are literals computed by hand from the rules sheet (the arithmetic is in the comments), come from a TWIN driven through the
# unchanged one-call gateway paths (`submit`, `submit_feint`), or come from the independent Python oracle fixture; the protocol is never compared
# with itself except for the deliberate direct-versus-feint indistinguishability and replay checks. Refusals are checked by whole executor-state
# equality (gateway snapshot, sealed store, serial, events, closed flag). The only private reads are the test seams: `_gateway._match` (plain-field
# state injection, as the other Half Guard suites do) and source scans.
const FIXTURE: String = "res://tests/generated/half_guard_feint_reference.jsonl"
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
const COMMITMENTS: Array = ["LOW", "MEDIUM", "HIGH"]

var checks: int = 0
var failures: int = 0
var oracle_rows: int = 0


func check(label: String, actual: Variant, expected: Variant) -> void:
    checks += 1
    if typeof(actual) != typeof(expected) or JSON.stringify(actual, "", true, true) != JSON.stringify(expected, "", true, true):
        failures += 1
        if failures <= 40:
            push_error("%s: got %s expected %s" % [label, JSON.stringify(actual).left(700), JSON.stringify(expected).left(700)])


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
    if not same_loose(actual, expected):
        failures += 1
        if failures <= 40:
            push_error("%s: got %s expected %s" % [label, JSON.stringify(actual).left(700), JSON.stringify(expected).left(700)])


func _initialize() -> void:
    _test_seal_refusals()
    _test_feint_resolution_literals()
    _test_lockstep_against_the_gateway_feint_path()
    _test_exit_cap_and_exits()
    _test_funding_through_the_protocol()
    _test_public_information_equivalence()
    _test_probing_controller()
    _test_refusals_do_not_depend_on_the_hidden_command()
    _test_events_and_reveal()
    _test_published_timeout_fallback()
    _test_session_end_with_a_pending_feint()
    _test_deterministic_replay()
    _test_oracle_trajectories_through_the_protocol()
    _test_oracle_grid_through_the_protocol()
    _test_unchanged_surfaces()
    _test_scope_and_hygiene()
    if failures > 0:
        push_error("Half Guard feint protocol: %d / %d assertions failed" % [failures, checks])
        quit(1)
        return
    print("Half Guard feint protocol PASS: %d assertions" % checks)
    quit(0)


# ---- Builders -----------------------------------------------------------------------------------------------------------

func fighter(current: int = 100, maximum: int = 100) -> Dictionary:
    var enter := int(floor(float(maximum) * 0.25))
    return {"stamina_current": current, "stamina_maximum": maximum, "exhaustion_latched": current <= enter, "behavior_remainder_units": 0}


func entry(top_current: int = 100, bottom_current: int = 100, clock: int = 300, interval: int = 5) -> Dictionary:
    return {"role_map": {"top": TOP_ID, "bottom": BOTTOM_ID}, "fighters": {TOP_ID: fighter(top_current), BOTTOM_ID: fighter(bottom_current)},
        "clock": {"initial_seconds": clock, "remaining_seconds": clock}, "window": {"last_issued_id": 0}, "interval_seconds": interval}


# A protocol in an arbitrary legal state: the public entry path, then plain-field assignment on the match (the test seam).
func at(initiator: String = "top", axis: int = 5, band: int = 0, top_base: int = 1, bottom_frame: int = 1, top_current: int = 100, bottom_current: int = 100) -> BjjHalfGuardSealedProtocol:
    var p := BjjHalfGuardSealedProtocol.create(entry(top_current, bottom_current)).protocol
    _poke(p._gateway._match, initiator, axis, band, top_base, bottom_frame)
    return p


func twin_at(initiator: String = "top", axis: int = 5, band: int = 0, top_base: int = 1, bottom_frame: int = 1, top_current: int = 100, bottom_current: int = 100) -> BjjHalfGuardWindowGateway:
    var g := BjjHalfGuardWindowGateway.create(entry(top_current, bottom_current)).gateway
    _poke(g._match, initiator, axis, band, top_base, bottom_frame)
    return g


func _poke(state: BjjHalfGuardMatch, initiator: String, axis: int, band: int, top_base: int, bottom_frame: int) -> void:
    state.initiator = initiator
    state.axis_tenths = axis
    state.band = band
    state.top_base = top_base
    state.bottom_frame = bottom_frame


func rep(report: BjjMatchWindowGateway.Report) -> Dictionary:
    if not report.ok():
        return {"error": report.error}
    var values := report.values.duplicate(true)
    values["error"] = ""
    return values


func opened(p: BjjHalfGuardSealedProtocol) -> Dictionary:
    return p.open_window().values


func expect_refused(label: String, p: BjjHalfGuardSealedProtocol, before: Dictionary, report: BjjMatchWindowGateway.Report, code: String) -> void:
    check(label + " is refused", report.ok(), false)
    check(label + " code", report.error, code)
    check(label + " carries no values", report.values.is_empty(), true)
    check(label + " leaves the whole executor state unchanged", p.executor_snapshot(), before)


func pair_of(initiator: String) -> Array:
    return [CF, KS] if initiator == "top" else [UH, RG]


func responses_of(initiator: String) -> Array:
    return [HF, UF, KSH] if initiator == "top" else [HC, HP, KP]


func fighter_of(initiator: String) -> String:
    return TOP_ID if initiator == "top" else BOTTOM_ID


func responder_of(initiator: String) -> String:
    return BOTTOM_ID if initiator == "top" else TOP_ID


# ---- 1. Seal refusals for feints (negative first, whole-state equality) --------------------------------------------------------------

func _test_seal_refusals() -> void:
    var p := at()
    var w := opened(p)
    var id := int(w.window_id)
    var b := p.executor_snapshot()
    check("the window is the Top's", [id, w.fighter_id], [1, TOP_ID])
    expect_refused("real equals apparent", p, b, p.seal_intent(id, TOP_ID, CF, "MEDIUM", CF), "feint_real_equals_apparent")
    expect_refused("real equals apparent (knee slice)", p, b, p.seal_intent(id, TOP_ID, KS, "MEDIUM", KS), "feint_real_equals_apparent")
    expect_refused("Flatten to Knee Slice is excluded", p, b, p.seal_intent(id, TOP_ID, FL, "MEDIUM", KS), "feint_not_supported")
    expect_refused("Knee Slice to Crossface is not a pair", p, b, p.seal_intent(id, TOP_ID, KS, "MEDIUM", CF), "feint_not_supported")
    expect_refused("Crossface to Flatten (not break-capable) is not a pair", p, b, p.seal_intent(id, TOP_ID, CF, "MEDIUM", FL), "feint_not_supported")
    expect_refused("a bottom technique as the real of a top apparent", p, b, p.seal_intent(id, TOP_ID, CF, "MEDIUM", RG), "incorrect_action_side_or_kind")
    expect_refused("a response id as the real", p, b, p.seal_intent(id, TOP_ID, CF, "MEDIUM", HF), "incorrect_action_side_or_kind")
    expect_refused("an unknown real", p, b, p.seal_intent(id, TOP_ID, CF, "MEDIUM", "nonsense"), "unknown_action")
    # precedence: window identity, addressing, initiator, duplicate, apparent technique, commitment, then the feint checks
    expect_refused("stale beats the feint checks", p, b, p.seal_intent(id + 1, TOP_ID, CF, "MEDIUM", CF), "stale_window")
    expect_refused("the responder cannot feint", p, b, p.seal_intent(id, BOTTOM_ID, UH, "MEDIUM", RG), "not_initiator")
    expect_refused("an unknown apparent beats the feint checks", p, b, p.seal_intent(id, TOP_ID, "nonsense", "MEDIUM", KS), "unknown_action")
    expect_refused("a foreign apparent beats the feint checks", p, b, p.seal_intent(id, TOP_ID, UH, "MEDIUM", RG), "unknown_action")
    expect_refused("an invalid commitment beats the feint checks", p, b, p.seal_intent(id, TOP_ID, CF, "EXTREME", CF), "invalid_commitment")
    expect_refused("not supported beats not eligible", p, b, p.seal_intent(id, TOP_ID, FL, "MEDIUM", KS), "feint_not_supported")
    check("nothing was sealed by any refusal", [p.has_pending_intent(), p.protocol_events()], [false, []])
    # a duplicate: a feint cannot be sealed over a direct seal, nor the other way round
    check("the direct seal is accepted", p.seal_intent(id, TOP_ID, CF, "MEDIUM").ok(), true)
    b = p.executor_snapshot()
    expect_refused("a feint over a pending direct seal", p, b, p.seal_intent(id, TOP_ID, CF, "MEDIUM", KS), "intent_already_sealed")
    expect_refused("a feint over a pending direct seal even with a bad real", p, b, p.seal_intent(id, TOP_ID, CF, "MEDIUM", "nonsense"), "intent_already_sealed")
    var q := at()
    var qw := opened(q)
    check("the feint seal is accepted", q.seal_intent(int(qw.window_id), TOP_ID, CF, "MEDIUM", KS).ok(), true)
    var qb := q.executor_snapshot()
    expect_refused("a direct seal over a pending feint", q, qb, q.seal_intent(int(qw.window_id), TOP_ID, CF, "MEDIUM"), "intent_already_sealed")
    expect_refused("a second feint over a pending feint", q, qb, q.seal_intent(int(qw.window_id), TOP_ID, CF, "LOW", KS), "intent_already_sealed")
    # a closed session refuses a feint
    var r := at()
    var rw := opened(r)
    r.end_session()
    var rb := r.executor_snapshot()
    expect_refused("a feint after the session ended", r, rb, r.seal_intent(int(rw.window_id), TOP_ID, CF, "MEDIUM", KS), "session_closed")
    # no window
    var n := at()
    var nb := n.executor_snapshot()
    expect_refused("a feint with no open window", n, nb, n.seal_intent(1, TOP_ID, CF, "MEDIUM", KS), "no_open_window")


# ---- 2. Hand-computed settlement literals through seal + respond ---------------------------------------------------------------------

# Seals and answers one exchange; returns {seal, done, protocol}.
func play(p: BjjHalfGuardSealedProtocol, apparent: String, real: String, response: String, commitment: String = "MEDIUM", response_commitment: String = "MEDIUM") -> Dictionary:
    var w := opened(p)
    var fighter_id := str(w.fighter_id)
    var seal := p.seal_intent(int(w.window_id), fighter_id, apparent, commitment, real)
    var done := p.respond(int(w.window_id), responder_of("top" if fighter_id == TOP_ID else "bottom"), int(seal.values.get("intent_serial", 0)), response, response_commitment)
    return {"seal": seal, "done": done, "protocol": p}


func settlement_of(played: Dictionary) -> Dictionary:
    return (played.done as BjjMatchWindowGateway.Report).values.detail.settlement


func _test_feint_resolution_literals() -> void:
    # FP-1 at the neutral state, both MEDIUM. Hip Frame: raw 1, no shifts, not a bite -1 -> 0, no exhaustion, MEDIUM magnitude 0, no
    # undercommitment: final 0, axis 5; charges 3 + 7 = 10 and 7. Underhook Fight (the bite): raw 2, +1 saturates at 2, final 2, axis 25.
    # Knee Shield (a call): raw -2, defense (MEDIUM, bottom_frame Partial) shift 0, -1 saturates at -2, axis -15, band -1, the governed MEDIUM
    # defense wears bottom_frame because final != 0.
    var played := play(at(), CF, KS, HF)
    var settled := settlement_of(played)
    check("FP-1 vs Hip Frame", [settled.action_id, settled.raw_grade, settled.grade_after_defense, settled.final_grade, settled.axis_after, settled.initiator_charged,
        settled.responder_charged, settled.exit_destination], [KS, 1, 1, 0, 5, 10, 7, ""])
    check("FP-1 vs Hip Frame feint record", settled.feint, {"apparent_action_id": CF, "real_action_id": KS, "bite_response_id": UF, "bit": false, "modifier": -1,
        "grade_before": 1, "grade_after": 0, "surcharge": 3, "surcharge_charged": 3, "total_cost": 10, "exit_capped": false})
    check("FP-1 vs Hip Frame stamina and initiative", [(played.protocol as BjjHalfGuardSealedProtocol).state_fields().top_stamina,
        (played.protocol as BjjHalfGuardSealedProtocol).state_fields().bottom_stamina, (played.protocol as BjjHalfGuardSealedProtocol).roles().initiative_id], [90, 93, BOTTOM_ID])
    settled = settlement_of(play(at(), CF, KS, UF))
    check("FP-1 vs Underhook Fight (the bite)", [settled.raw_grade, settled.final_grade, settled.axis_after, settled.band_after, settled.feint.bit, settled.feint.modifier,
        settled.readiness_changes], [2, 2, 25, 1, true, 1, []])
    settled = settlement_of(play(at(), CF, KS, KSH))
    check("FP-1 vs Knee Shield (a call)", [settled.raw_grade, settled.defense_strength_tier, settled.final_grade, settled.axis_after, settled.band_after, settled.readiness_changes],
        [-2, 1, -2, -15, -1, ["bottom_frame:Partial->None:knee_slice"]])
    # FP-2 (Bottom): Head Control (the bite): raw 2, final 2, Bottom axis 5 - 20 = -15; Recover Guard builds: top_base -1.
    settled = settlement_of(play(at("bottom"), UH, RG, HC))
    check("FP-2 vs Head Control (the bite)", [settled.action_id, settled.final_grade, settled.axis_after, settled.band_after, settled.readiness_changes, settled.feint.bit],
        [RG, 2, -15, -1, ["top_base:Partial->None:recover_guard"], true])
    settled = settlement_of(play(at("bottom"), UH, RG, HP))
    check("FP-2 vs Hip Pressure (not a bite)", [settled.raw_grade, settled.final_grade, settled.axis_after, settled.readiness_changes], [1, 0, 5, []])
    settled = settlement_of(play(at("bottom"), UH, RG, KP))
    check("FP-2 vs Knee Pin (a call)", [settled.raw_grade, settled.final_grade, settled.axis_after, settled.band_after, settled.readiness_changes],
        [-2, -2, 25, 1, ["top_base:Partial->None:recover_guard"]])
    # sequential saturation: an Exhausted (20) attacker at Ready (top_base 2) feints into the bite: raw 2 -> attack +1 saturates 2 -> feint +1 saturates 2
    # -> exhaustion -1 gives 1; one combined modifier (+1 +1 -1 on raw 2 = 3 -> 2) would give 2.
    var exhausted := play(at("top", 5, 0, 2, 1, 20, 100), CF, KS, UF)
    settled = settlement_of(exhausted)
    check("sequential saturation", [settled.raw_grade, settled.grade_after_attack, settled.grade_after_defense, settled.feint.grade_after, settled.exhaustion_modifier,
        settled.grade_after_exhaustion, settled.final_grade], [2, 2, 2, 2, -1, 1, 1])
    check("the exhausted feinter's consumption and settlement", [settled.readiness_changes, settled.axis_after, settled.initiator_charged],
        [["top_base:Ready->Partial:knee_slice"], 15, 10])
    # the apparent technique never resolves: history holds the real id once, and Crossface's builder (bottom_frame -1) never ran
    var history := (played.protocol as BjjHalfGuardSealedProtocol).history_fields()
    check("history holds the real technique once", [history.initiated_action_history, history.raw_grade_history, history.top_initiation_count], [[KS], ["Success"], 1])
    var bite := play(at(), CF, KS, UF)
    check("the apparent technique built nothing", [(bite.protocol as BjjHalfGuardSealedProtocol).state_fields().top_base,
        (bite.protocol as BjjHalfGuardSealedProtocol).state_fields().bottom_frame], [1, 1])


# ---- 3. Lockstep against the unchanged gateway feint path --------------------------------------------------------------------------------

func _same_views(tag: String, p: BjjHalfGuardSealedProtocol, t: BjjHalfGuardWindowGateway) -> void:
    check(tag + " snapshot", p.snapshot(), t.snapshot())
    check(tag + " window", p.window_fields(), t.window_fields())
    check(tag + " state", p.state_fields(), t.state_fields())
    check(tag + " history", p.history_fields(), t.history_fields())


func _test_lockstep_against_the_gateway_feint_path() -> void:
    var count := 0
    for initiator: String in ["top", "bottom"]:
        var pair := pair_of(initiator)
        for own_tier: int in [1, 2]:
            for stamina: int in [100, 31, 20, 14, 8, 6]:
                for response: String in responses_of(initiator):
                    for commitment: String in COMMITMENTS:
                        for response_commitment: String in ["", "LOW", "HIGH"]:
                            var top_base := own_tier if initiator == "top" else 1
                            var bottom_frame := own_tier if initiator == "bottom" else 1
                            var top_current := stamina if initiator == "top" else 100
                            var bottom_current := stamina if initiator == "bottom" else 100
                            var p := at(initiator, 5, 0, top_base, bottom_frame, top_current, bottom_current)
                            var t := twin_at(initiator, 5, 0, top_base, bottom_frame, top_current, bottom_current)
                            var tag := "lockstep %s tier %d S=%d %s %s/%s" % [initiator, own_tier, stamina, response.get_slice(".", 2), commitment, response_commitment]
                            var wp := p.open_window()
                            var wt := t.open_window()
                            check(tag + " open", rep(wp), rep(wt))
                            var seal := p.seal_intent(int(wp.values.window_id), fighter_of(initiator), pair[0], commitment, pair[1])
                            var admissible := t.feint_error(pair[0], pair[1], commitment)
                            check(tag + " the seal is admitted exactly when the gateway's pure check says so", seal.error, admissible)
                            _same_views(tag + " after the seal (a seal changes nothing)", p, t)
                            if not seal.ok():
                                continue
                            var done := p.respond(int(wp.values.window_id), responder_of(initiator), int(seal.values.intent_serial), response, response_commitment)
                            var direct := t.submit_feint(int(wt.values.window_id), fighter_of(initiator), pair[0], pair[1], response, commitment, response_commitment)
                            check(tag + " resolved report equals the gateway's feint exchange", rep(done), rep(direct))
                            _same_views(tag + " after", p, t)
                            check(tag + " the window is closed and no other opened", [p.window_fields().open, p.window_fields().window_id], [false, 1])
                            check(tag + " the seal is consumed", p.has_pending_intent(), false)
                            check(tag + " one exchange is three events", p.protocol_events().size(), 3)
                            count += 1
    check("a measured number of lockstep feints was exercised", count > 600, true)


# ---- 4. Exit cap and exits ---------------------------------------------------------------------------------------------------------------------

func _test_exit_cap_and_exits() -> void:
    # At axis 20 (band 1) Knee Slice vs Underhook Fight: raw 2, bite keeps 2. LOW magnitude on Strong Success -1 -> 1, final 1, proposed 30 reaches the pass
    # line but the LOW-effective cap removes the exit; the axis clamps at 30 (band 2) and initiative flips. MEDIUM/HIGH exit with Strong Success.
    var low := play(at("top", 20, 1), CF, KS, UF, "LOW", "MEDIUM")
    var settled := settlement_of(low)
    check("a LOW feint resolves but cannot exit", [settled.initiator_effective, settled.final_grade, settled.axis_proposed, settled.axis_after, settled.band_after,
        settled.exit_destination, settled.feint.exit_capped, settled.initiator_charged], ["LOW", 1, 30, 30, 2, "", true, 6])
    var low_p := low.protocol as BjjHalfGuardSealedProtocol
    check("the segment continues with initiative flipped", [low_p.is_terminal(), low_p.roles().initiative_id, low_p.state_fields().exit_destination], [false, BOTTOM_ID, ""])
    check("the next window opens", low_p.open_window().ok(), true)
    for commitment: Array in [["MEDIUM", 10], ["HIGH", 15]]:
        var played := play(at("top", 20, 1), CF, KS, UF, str(commitment[0]), "MEDIUM")
        var s := settlement_of(played)
        var report: BjjMatchWindowGateway.Report = played.done
        check("a %s feint exits to Side Control" % commitment[0], [s.final_grade, s.axis_after, s.exit_destination, s.feint.exit_capped, s.initiator_charged,
            report.values.transition, report.values.ended], [2, 40, "Side Control", false, int(commitment[1]),
            {"kind": "exit", "raw_destination": "Side Control", "destination_position_id": "side_control", "resolved": true}, true])
        var played_p := played.protocol as BjjHalfGuardSealedProtocol
        check("an exit is terminal, keeps initiative and refuses later commands", [played_p.is_terminal(), played_p.roles().initiative_id,
            played_p.state_fields().exit_reason, played_p.open_window().error], [true, TOP_ID, "Knee Slice reached the pass line with final grade Strong Success", "terminal_exchange"])
    # a downgraded feint is capped by its effective commitment: requested HIGH from stamina 8 is funded LOW (8 - 3 = 5)
    var downgraded := settlement_of(play(at("top", 20, 1, 1, 1, 8, 100), CF, KS, UF, "HIGH", "MEDIUM"))
    check("requested HIGH funded as LOW is capped", [downgraded.commitment_requested, downgraded.initiator_effective, downgraded.exit_destination, downgraded.feint.exit_capped],
        ["HIGH", "LOW", "", true])
    # the bottom pair: Recover Guard vs Head Control (bite) at axis -20: MEDIUM escapes (Closed Guard at Strong Success); LOW is capped
    var medium := settlement_of(play(at("bottom", -20, -1), UH, RG, HC, "MEDIUM", "MEDIUM"))
    check("the bottom MEDIUM feint escapes", [medium.final_grade, medium.exit_destination], [2, "Closed Guard"])
    var capped := settlement_of(play(at("bottom", -20, -1), UH, RG, HC, "LOW", "MEDIUM"))
    check("the bottom LOW feint is capped", [capped.final_grade, capped.axis_proposed, capped.exit_destination, capped.feint.exit_capped], [1, -30, "", true])
    # a direct LOW Knee Slice from the same state still exits: the cap is feint-only
    var p := at("top", 20, 1)
    var w := opened(p)
    p.seal_intent(int(w.window_id), TOP_ID, KS, "LOW")
    var direct_exit := p.respond(int(w.window_id), BOTTOM_ID, 1, UF, "MEDIUM")
    check("a direct LOW technique is not capped", [direct_exit.values.detail.settlement.final_grade, direct_exit.values.detail.settlement.exit_destination], [1, "Side Control"])
    check("a direct record carries no feint key", direct_exit.values.detail.settlement.has("feint"), false)


# ---- 5. Funding through the protocol ------------------------------------------------------------------------------------------------------------

func _test_funding_through_the_protocol() -> void:
    # stamina -> {requested: [effective, total]} hand-written from the specification; [] is a refusal at seal time.
    var table := {0: [[], [], []], 2: [[], [], []], 3: [[], [], []], 5: [[], [], []],
        6: [["LOW", 6], ["LOW", 6], ["LOW", 6]], 8: [["LOW", 6], ["LOW", 6], ["LOW", 6]], 9: [["LOW", 6], ["LOW", 6], ["LOW", 6]],
        10: [["MEDIUM", 10], ["MEDIUM", 10], ["LOW", 6]], 12: [["MEDIUM", 10], ["MEDIUM", 10], ["LOW", 6]], 14: [["MEDIUM", 10], ["MEDIUM", 10], ["LOW", 6]],
        15: [["HIGH", 15], ["MEDIUM", 10], ["LOW", 6]], 16: [["HIGH", 15], ["MEDIUM", 10], ["LOW", 6]]}
    for initiator: String in ["top", "bottom"]:
        var pair := pair_of(initiator)
        for stamina: int in table:
            var row: Array = table[stamina]
            for index in range(3):
                var requested: String = ["HIGH", "MEDIUM", "LOW"][index]
                var p := at(initiator, 5, 0, 1, 1, stamina if initiator == "top" else 100, stamina if initiator == "bottom" else 100)
                var w := opened(p)
                var before := p.executor_snapshot()
                var seal := p.seal_intent(int(w.window_id), fighter_of(initiator), pair[0], requested, pair[1])
                var tag := "%s S=%d requested %s" % [initiator, stamina, requested]
                if (row[index] as Array).is_empty():
                    check(tag + " is refused for funding", seal.error, "feint_requires_funding")
                    check(tag + " leaves the whole state unchanged (no surcharge reserved, nothing sealed)", p.executor_snapshot(), before)
                    continue
                check(tag + " is accepted", seal.error, "")
                var done := p.respond(int(w.window_id), responder_of(initiator), 1, responses_of(initiator)[0], "MEDIUM")
                var settled := settlement_of({"done": done})
                check(tag + " funded effective and total", [settled.initiator_effective, settled.initiator_charged, settled.initiator_effective_cost], [row[index][0], row[index][1], row[index][1] - 3])
                var pool_after: int = int(p.state_fields().top_stamina) if initiator == "top" else int(p.state_fields().bottom_stamina)
                check(tag + " charged exactly once", pool_after, stamina - int(row[index][1]))
                check(tag + " the responder pays the normal 7 and never a surcharge", [settled.responder_charged, settled.responder_waived], [7, 0])
    # an unfunded attacker may attack directly (S=3..5 funds LOW; S=2 is unfunded and Rule 1 waives the responder's charge) but cannot feint
    for stamina: int in [2, 3, 5]:
        var p := at("top", 5, 0, 1, 1, stamina, 100)
        var w := opened(p)
        check("S=%d: the feint is refused" % stamina, p.seal_intent(int(w.window_id), TOP_ID, CF, "HIGH", KS).error, "feint_requires_funding")
        check("S=%d: the direct technique is accepted in the same window" % stamina, p.seal_intent(int(w.window_id), TOP_ID, CF, "HIGH").ok(), true)
        var s := settlement_of({"done": p.respond(int(w.window_id), BOTTOM_ID, 1, HF, "MEDIUM")})
        check("S=%d: direct funding and the Rule 1 waiver" % stamina, [s.initiator_effective, s.initiator_charged, s.responder_waived], ["LOW", 3, 0] if stamina >= 3 else ["", 0, 7])
    # the latch edges: a LOW feint costs 6: from 31 the attacker lands on 25 (latched), from 32 on 26 (not latched)
    for edge: Array in [[31, 25, true], [32, 26, false]]:
        var p := at("top", 5, 0, 1, 1, int(edge[0]), 100)
        var w := opened(p)
        p.seal_intent(int(w.window_id), TOP_ID, CF, "LOW", KS)
        p.respond(int(w.window_id), BOTTOM_ID, 1, HF, "MEDIUM")
        check("latch edge from S=%d" % int(edge[0]), [p.state_fields().top_stamina, p.state_fields().top_latched], [edge[1], edge[2]])


# ---- 6. Direct and feint commands are indistinguishable to the defender ------------------------------------------------------------------------------

# Everything a defender (a controller handed the session's public surfaces) can observe after the seal and after a battery of faulty commands.
func _defender_transcript(initiator: String, top_base: int, bottom_frame: int, top_current: int, bottom_current: int, commitment: String, real: String) -> Dictionary:
    var p := at(initiator, 5, 0, top_base, bottom_frame, top_current, bottom_current)
    var w := opened(p)
    var id := int(w.window_id)
    var apparent: String = pair_of(initiator)[0]
    var attacker := fighter_of(initiator)
    var defender := responder_of(initiator)
    var seal := p.seal_intent(id, attacker, apparent, commitment, real)
    if not seal.ok():
        return {"refused": seal.error}
    var codes: Array = []
    codes.append(p.respond(id, defender, 2, responses_of(initiator)[0], "LOW").error)
    codes.append(p.respond(id + 1, defender, 1, responses_of(initiator)[0], "LOW").error)
    codes.append(p.respond(id, attacker, 1, responses_of(initiator)[0], "LOW").error)
    codes.append(p.respond(id, defender, 1, "nonsense", "LOW").error)
    codes.append(p.respond(id, defender, 1, responses_of(initiator)[0], "bad").error)
    codes.append(p.seal_intent(id, defender, apparent, "LOW", real).error)
    codes.append(p.seal_intent(id, attacker, apparent, "LOW", real).error)
    codes.append(p.seal_intent(id, attacker, apparent, "LOW").error)
    codes.append(p.submit(id, defender).error)
    codes.append(p.open_window().error)
    codes.append(p.sealed_intent_view(defender).error)
    codes.append(p.apply_response_timeout(id, 1, "nonsense", "LOW").error)
    codes.append(p.apply_response_timeout(id, 1, responses_of(initiator)[2], "LOW").error)
    return {"seal": seal.values, "view": p.public_intent_view().values, "codes": codes, "window": p.window_fields(), "state": p.state_fields(),
        "history": p.history_fields(), "simulation": p.snapshot(), "public_events": p.public_events(), "roles": [p.roles().initiative_id, p.roles().control_authority_id],
        "responses": p.response_options(apparent).options.map(func(o: BjjPositionContract.Option) -> Dictionary: return o.fields()),
        "defender_menu": p.action_options(defender).options.map(func(o: BjjPositionContract.Option) -> Dictionary: return o.fields())}


func _test_public_information_equivalence() -> void:
    var compared := 0
    for initiator: String in ["top", "bottom"]:
        var pair := pair_of(initiator)
        for top_base: int in [0, 1, 2]:
            for bottom_frame: int in [0, 1, 2]:
                for stamina: int in [100, 31, 14, 8, 6]:
                    for commitment: String in ["", "LOW", "MEDIUM", "HIGH"]:
                        var top_current := stamina if initiator == "top" else 100
                        var bottom_current := stamina if initiator == "bottom" else 100
                        var as_direct := _defender_transcript(initiator, top_base, bottom_frame, top_current, bottom_current, commitment, "")
                        var as_feint := _defender_transcript(initiator, top_base, bottom_frame, top_current, bottom_current, commitment, pair[1])
                        var tag := "%s tiers %d/%d S=%d '%s'" % [initiator, top_base, bottom_frame, stamina, commitment]
                        if as_feint.has("refused"):
                            # the feint is not admissible here (tier None or unfunded): only the attacker ever learns that; the direct seal still works
                            var own := top_base if initiator == "top" else bottom_frame
                            check(tag + " the feint refusal is the match's own code", as_feint.refused, "feint_not_eligible" if own == 0 else "feint_requires_funding")
                            check(tag + " the direct seal is unaffected", as_direct.has("refused"), false)
                            continue
                        compared += 1
                        check(tag + " every defender-observable surface is identical for the direct and the feint command", as_feint, as_direct)
                        check(tag + " the eligible list reflects the possible choices, not the sealed one", as_feint.view.eligible_real_ids, [pair[1]])
    check("a measured number of direct/feint pairs was compared", compared > 150, true)
    # eligibility is public and independent of stamina and funding: an attacker who could never fund the feint still shows the eligible list
    var poor := at("top", 5, 0, 1, 1, 2, 100)
    var w := opened(poor)
    poor.seal_intent(int(w.window_id), TOP_ID, CF, "MEDIUM")
    check("an unfundable attacker's direct seal still shows the eligible list", poor.public_intent_view().values.eligible_real_ids, [KS])
    var none := at("top", 5, 0, 0, 1)
    var nw := opened(none)
    none.seal_intent(int(nw.window_id), TOP_ID, CF, "MEDIUM")
    check("at top_base None the eligible list is empty", none.public_intent_view().values.eligible_real_ids, [])
    var flatten := at()
    var fw := opened(flatten)
    flatten.seal_intent(int(fw.window_id), TOP_ID, FL, "MEDIUM")
    check("Flatten conceals nothing", flatten.public_intent_view().values.eligible_real_ids, [])


# BEGIN controller double (it is handed ONLY detached dictionaries and arrays; the scan below proves it never names executor internals)
class ProbingController extends RefCounted:
    var seen_objects: int = 0
    var seen_strings: Array = []
    var attempts: int = 0

    # Recursively enumerates everything it was handed: counts objects (there must be none), records every string and key.
    func inspect(value: Variant, depth: int = 0) -> void:
        if depth > 10:
            return
        match typeof(value):
            TYPE_STRING, TYPE_STRING_NAME:
                seen_strings.append(str(value))
            TYPE_DICTIONARY:
                var dictionary: Dictionary = value
                for key: Variant in dictionary:
                    inspect(key, depth + 1)
                    inspect(dictionary[key], depth + 1)
            TYPE_ARRAY:
                for item: Variant in value:
                    inspect(item, depth + 1)
            TYPE_OBJECT:
                seen_objects += 1

    # A hostile controller tries every private-looking key of what it received.
    func poke(value: Variant) -> int:
        var found := 0
        if typeof(value) == TYPE_DICTIONARY:
            for key_name: String in ["_pending", "_gateway", "real_action_id", "feint", "effective", "surcharge", "total_cost", "funding", "sealed"]:
                attempts += 1
                if (value as Dictionary).has(key_name):
                    found += 1
        return found
# END controller double


func _test_probing_controller() -> void:
    for initiator: String in ["top", "bottom"]:
        var pair := pair_of(initiator)
        for real: String in ["", pair[1]]:
            for commitment: String in COMMITMENTS:
                var p := at(initiator)
                var w := opened(p)
                var seal := p.seal_intent(int(w.window_id), fighter_of(initiator), pair[0], commitment, real)
                var controller := ProbingController.new()
                # everything a controller is ever handed: the seal report, the public view, the public events, the gateway views and the option menus
                var handed: Array = [seal.values, p.public_intent_view().values, p.public_events(), p.window_fields(), p.state_fields(), p.history_fields(), p.snapshot(),
                    p.response_options(pair[0]).options.map(func(o: BjjPositionContract.Option) -> Dictionary: return o.fields()),
                    p.action_options(responder_of(initiator)).options.map(func(o: BjjPositionContract.Option) -> Dictionary: return o.fields())]
                var found := 0
                for item: Variant in handed:
                    controller.inspect(item)
                    found += controller.poke(item)
                    if typeof(item) == TYPE_ARRAY:
                        for inner: Variant in item:
                            found += controller.poke(inner)
                var tag := "%s as '%s' at %s" % [pair[0], real, commitment]
                check(tag + ": the controller received no object, so there is no private member to read", controller.seen_objects, 0)
                check(tag + ": it found no sealed-store key on any public surface", found, 0)
                check(tag + ": the surfaces name no hidden vocabulary", controller.seen_strings.any(func(text: String) -> bool:
                    return text.contains("real_action_id") or text.contains("surcharge") or text.contains("total_cost") or text == "feint"), false)
                check(tag + ": the only real technique it can see is the public possibility list", controller.seen_strings.count(pair[1]) >= 1, true)
    # control: the probe really sees a leak (so a clean result above means something); also a leaky view injected into a public surface is caught
    var leaky := ProbingController.new()
    var p2 := at()
    var w2 := opened(p2)
    p2.seal_intent(int(w2.window_id), TOP_ID, CF, "MEDIUM", KS)
    var injected := p2.public_intent_view().values.duplicate(true)
    injected["real_action_id"] = KS
    leaky.inspect(injected)
    check("mutation control: a view carrying the real technique's key is detected", leaky.poke(injected), 1)
    check("mutation control: the executor surface is detected as holding sealed-store keys", leaky.poke(p2.executor_snapshot().pending), 1)


# ---- 7. Refusals available to the defender do not depend on the hidden command --------------------------------------------------------------------------

func _test_refusals_do_not_depend_on_the_hidden_command() -> void:
    for initiator: String in ["top", "bottom"]:
        var pair := pair_of(initiator)
        var codes := {}
        for real: String in ["", pair[1]]:
            var transcript := _defender_transcript(initiator, 1, 1, 100, 100, "MEDIUM", real)
            codes[real] = transcript.codes
        check("%s: the defender's refusal codes are identical for a direct and a feint command" % initiator, codes[pair[1]], codes[""])
        check("%s: the refusal codes are the expected literals" % initiator, codes[""], ["intent_serial_mismatch", "stale_window", "not_responder", "unknown_response",
            "invalid_response_commitment", "not_initiator", "intent_already_sealed", "intent_already_sealed", "intent_pending", "window_already_open", "not_intent_owner",
            "fallback_not_published", "fallback_not_published"])
    # the response menu for the apparent technique is the full legal menu whatever was sealed
    for real: String in ["", KS]:
        var p := at()
        var w := opened(p)
        p.seal_intent(int(w.window_id), TOP_ID, CF, "MEDIUM", real)
        check("the response ids are the three legal responses (sealed '%s')" % real, p.public_intent_view().values.response_ids, [HF, UF, KSH])
        for response: String in [HF, UF, KSH]:
            var probe := at()
            var pw := opened(probe)
            probe.seal_intent(int(pw.window_id), TOP_ID, CF, "MEDIUM", real)
            check("every public response is accepted against '%s'" % real, probe.respond(int(pw.window_id), BOTTOM_ID, 1, response, "MEDIUM").ok(), true)


# ---- 8. Events and the reveal -------------------------------------------------------------------------------------------------------------------------

func _test_events_and_reveal() -> void:
    var p := at()
    var w := opened(p)
    var id := int(w.window_id)
    p.seal_intent(id, TOP_ID, CF, "HIGH", KS)
    check("the executor event holds the real technique", p.protocol_events(), [{"event": "intent_sealed", "index": 1, "window_id": 1, "intent_serial": 1,
        "initiator_id": TOP_ID, "apparent_technique_id": CF, "commitment_requested": "HIGH", "real_action_id": KS}])
    check("the public event is the direct seal's event (GP-3 commitment, no real technique)", p.public_events(), [{"event": "intent_sealed", "index": 1, "window_id": 1,
        "intent_serial": 1, "initiator_id": TOP_ID, "apparent_technique_id": CF, "commitment_requested": "HIGH"}])
    var direct := at()
    var dw := opened(direct)
    direct.seal_intent(int(dw.window_id), TOP_ID, CF, "HIGH")
    check("before the reveal the public stream is identical for the direct and the feint command", p.public_events(), direct.public_events())
    var done := p.respond(id, BOTTOM_ID, 1, HF, "LOW")
    var events := p.protocol_events()
    check("one feint is three events in order", events.map(func(e: Dictionary) -> String: return str(e.event)), ["intent_sealed", "response_committed", "exchange_revealed"])
    var revealed: Dictionary = events[2]
    check("the reveal discloses the apparent and the real technique and the feint flag", [revealed.apparent_action_id, revealed.action_id, revealed.feint], [CF, KS, true])
    check("the reveal carries the settlement with the feint record", [revealed.settlement.action_id, revealed.settlement.feint.apparent_action_id,
        revealed.settlement.feint.total_cost], [KS, CF, 15])
    check("the reveal equals the report's settlement", revealed.settlement, done.values.detail.settlement)
    check("a direct exchange's reveal is not a feint", _reveal_flags(KS, ""), [KS, KS, false])
    check("the public stream after the reveal now shows the whole intent", [p.public_events()[2].apparent_action_id, p.public_events()[2].action_id, p.public_events()[2].feint],
        [CF, KS, true])


func _reveal_flags(apparent: String, real: String) -> Array:
    var p := at()
    var w := opened(p)
    p.seal_intent(int(w.window_id), TOP_ID, apparent, "MEDIUM", real)
    p.respond(int(w.window_id), BOTTOM_ID, 1, HF, "MEDIUM")
    var revealed: Dictionary = p.protocol_events()[2]
    return [revealed.apparent_action_id, revealed.action_id, revealed.feint]


# ---- 9. The published timeout fallback ----------------------------------------------------------------------------------------------------------------------

func _test_published_timeout_fallback() -> void:
    check("the published fallback table", [BjjHalfGuardCatalog.timeout_fallback("bottom"), BjjHalfGuardCatalog.timeout_fallback("top"), BjjHalfGuardCatalog.timeout_fallback("nobody")],
        [{"response_id": HF, "commitment": "LOW"}, {"response_id": HP, "commitment": "LOW"}, {}])
    # Direct Crossface, defender (Bottom) times out into Hip Frame LOW: raw 1. LOW vs LOW: no bonus -> 1; MEDIUM vs LOW: +1 -> 2; HIGH vs LOW: magnitude +1 then +1 -> 2.
    var expected := {"LOW": [0, 1, 3], "MEDIUM": [1, 2, 7], "HIGH": [1, 2, 12]}
    for commitment: String in expected:
        var p := at()
        var w := opened(p)
        var seal := p.seal_intent(int(w.window_id), TOP_ID, CF, commitment)
        var clock := int(p.state_fields().clock_seconds)
        var done := p.apply_response_timeout(int(w.window_id), int(seal.values.intent_serial), HF, "LOW")
        var s := settlement_of({"done": done})
        check("timeout vs %s Crossface" % commitment, [s.undercommitment_modifier, s.final_grade, s.initiator_charged, s.responder_charged], [expected[commitment][0], expected[commitment][1], expected[commitment][2], 3])
        check("timeout %s changes no clock, opens no window, flips initiative once" % commitment, [p.state_fields().clock_seconds, p.window_fields().open, p.roles().initiative_id], [clock, false, BOTTOM_ID])
        check("the events flag it as defaulted", [p.protocol_events()[1].defaulted, p.protocol_events()[2].defaulted], [true, true])
        # no duplicate penalty: the identical ACTIVE response gives the identical settlement
        var active := at()
        var aw := opened(active)
        active.seal_intent(int(aw.window_id), TOP_ID, CF, commitment)
        var answered := active.respond(int(aw.window_id), BOTTOM_ID, 1, HF, "LOW")
        check("a defaulted LOW response settles exactly like an active LOW response (%s)" % commitment, rep(done), rep(answered))
        check("the simulations are identical", p.snapshot(), active.snapshot())
        # and the only difference from a MEDIUM response is the existing undercommitment step
        var medium := at()
        var mw := opened(medium)
        medium.seal_intent(int(mw.window_id), TOP_ID, CF, commitment)
        var against_medium := settlement_of({"done": medium.respond(int(mw.window_id), BOTTOM_ID, 1, HF, "MEDIUM")})
        check("the fallback gained %s only through the undercommitment modifier (never a second bonus)" % commitment,
            [s.final_grade - against_medium.final_grade <= 1, s.undercommitment_modifier - against_medium.undercommitment_modifier <= 1], [true, true])
    # Top defender: Bottom attacks Underhook MEDIUM; the defender times out into Hip Pressure LOW: raw 0 + undercommitment 1 -> 1
    var q := at("bottom")
    var qw := opened(q)
    var qs := q.seal_intent(int(qw.window_id), BOTTOM_ID, UH, "MEDIUM")
    var top_done := q.apply_response_timeout(int(qw.window_id), int(qs.values.intent_serial), HP, "LOW")
    var ts := settlement_of({"done": top_done})
    check("timeout of the Top defender", [ts.response_id, ts.raw_grade, ts.undercommitment_modifier, ts.final_grade, ts.responder_charged], [HP, 0, 1, 1, 3])
    # the Top's fallback is not the Bottom's and vice versa
    var wrong := at("bottom")
    var ww := opened(wrong)
    wrong.seal_intent(int(ww.window_id), BOTTOM_ID, UH, "MEDIUM")
    var wb := wrong.executor_snapshot()
    expect_refused("the Bottom's fallback is not published for the Top defender", wrong, wb, wrong.apply_response_timeout(int(ww.window_id), 1, HF, "LOW"), "fallback_not_published")
    expect_refused("Head Control LOW is not the Top's published fallback", wrong, wb, wrong.apply_response_timeout(int(ww.window_id), 1, HC, "LOW"), "fallback_not_published")
    expect_refused("Hip Pressure at MEDIUM is not the published commitment", wrong, wb, wrong.apply_response_timeout(int(ww.window_id), 1, HP, "MEDIUM"), "fallback_not_published")
    expect_refused("Hip Pressure with an empty commitment is not the published commitment", wrong, wb, wrong.apply_response_timeout(int(ww.window_id), 1, HP, ""), "fallback_not_published")
    # the fallback against a feint follows the same bite rules: FP-1 vs Hip Frame (not a bite) at MEDIUM: raw 1 -1 -> 0, +1 (MEDIUM vs LOW) -> 1; charges 10 / 3
    var f := at()
    var fw := opened(f)
    var fs := f.seal_intent(int(fw.window_id), TOP_ID, CF, "MEDIUM", KS)
    var fd := settlement_of({"done": f.apply_response_timeout(int(fw.window_id), int(fs.values.intent_serial), HF, "LOW")})
    check("the fallback against FP-1", [fd.feint.bit, fd.feint.modifier, fd.undercommitment_modifier, fd.final_grade, fd.initiator_charged, fd.responder_charged], [false, -1, 1, 1, 10, 3])
    var g := at("bottom")
    var gw := opened(g)
    var gs := g.seal_intent(int(gw.window_id), BOTTOM_ID, UH, "MEDIUM", RG)
    var gd := settlement_of({"done": g.apply_response_timeout(int(gw.window_id), int(gs.values.intent_serial), HP, "LOW")})
    check("the fallback against FP-2", [gd.feint.bit, gd.feint.modifier, gd.undercommitment_modifier, gd.final_grade], [false, -1, 1, 1])
    # the fallback can never bite: Hip Frame is not the FP-1 bite (Underhook Fight) and Hip Pressure is not the FP-2 bite (Head Control)
    for bite: Array in [[CF, BjjHalfGuardCatalog.FEINT_PAIRS[CF].bite, HF], [UH, BjjHalfGuardCatalog.FEINT_PAIRS[UH].bite, HP]]:
        check("the published fallback is not the bite of %s" % bite[0], bite[1] != bite[2], true)
    # an unfundable fallback follows the existing unfunded handling: the defender has 2 stamina, LOW (3) is unaffordable -> charged 0, undercommitment +1 once
    var broke := at("top", 5, 0, 1, 1, 100, 2)
    var bw := opened(broke)
    broke.seal_intent(int(bw.window_id), TOP_ID, CF, "MEDIUM")
    var bs := settlement_of({"done": broke.apply_response_timeout(int(bw.window_id), 1, HF, "LOW")})
    check("an unfundable fallback is unfunded, charged nothing and gives no free stamina", [bs.responder_effective, bs.responder_effective_cost, bs.responder_charged, bs.responder_waived,
        bs.undercommitment_modifier], ["", 0, 0, 0, 1])
    check("the defender kept its 2 stamina", broke.state_fields().bottom_stamina, 2)
    # a timeout resolves nothing without a seal, in a stale window, with a stale serial
    var empty := at()
    var ew := opened(empty)
    var eb := empty.executor_snapshot()
    expect_refused("a timeout with no seal", empty, eb, empty.apply_response_timeout(int(ew.window_id), 1, HF, "LOW"), "no_sealed_intent")
    empty.seal_intent(int(ew.window_id), TOP_ID, CF, "MEDIUM", KS)
    eb = empty.executor_snapshot()
    expect_refused("a timeout in a stale window", empty, eb, empty.apply_response_timeout(int(ew.window_id) + 1, 1, HF, "LOW"), "stale_window")
    expect_refused("a timeout with a stale serial", empty, eb, empty.apply_response_timeout(int(ew.window_id), 2, HF, "LOW"), "intent_serial_mismatch")
    check("a refused timeout keeps the sealed feint", empty.sealed_intent_view(TOP_ID).values.real_action_id, KS)


# ---- 10. A session end discards a pending feint --------------------------------------------------------------------------------------------------------------

func _test_session_end_with_a_pending_feint() -> void:
    var p := at()
    var w := opened(p)
    p.seal_intent(int(w.window_id), TOP_ID, CF, "HIGH", KS)
    var simulation := p.snapshot()
    var ended := p.end_session()
    check("the pending feint is discarded, reporting only its serial", ended.values, {"discarded_intent_serial": 1})
    check("nothing was resolved: no charge, no history, no clock change, no initiative change", [p.snapshot() == simulation, p.state_fields().top_stamina, p.history_fields().initiated_action_history,
        p.roles().initiative_id], [true, 100, [], TOP_ID])
    check("the discarded feint's surcharge was never reserved or paid", [p.state_fields().top_stamina, p.state_fields().bottom_stamina], [100, 100])
    var b := p.executor_snapshot()
    expect_refused("the discarded intent cannot be answered", p, b, p.respond(int(w.window_id), BOTTOM_ID, 1, HF, "LOW"), "session_closed")
    expect_refused("the discarded intent cannot be timed out", p, b, p.apply_response_timeout(int(w.window_id), 1, HF, "LOW"), "session_closed")
    expect_refused("the discarded intent cannot be resealed", p, b, p.seal_intent(int(w.window_id), TOP_ID, CF, "HIGH", KS), "session_closed")
    check("the public events never carried the real technique", p.public_events().filter(func(e: Dictionary) -> bool: return e.has("real_action_id")), [])
    # a fresh session starts clean: nothing of the discarded intent leaks into it
    var fresh_p := at()
    check("a new session has no pending intent and serial 0", [fresh_p.has_pending_intent(), fresh_p.executor_snapshot().serial], [false, 0])


# ---- 11. Deterministic replay -----------------------------------------------------------------------------------------------------------------------------------------

func _scenario_log() -> Array:
    return [
        {"op": "open"},
        {"op": "seal", "w": 1, "f": TOP_ID, "a": CF, "c": "MEDIUM", "r": KS},
        {"op": "seal", "w": 1, "f": TOP_ID, "a": CF, "c": "MEDIUM", "r": ""},
        {"op": "respond", "w": 1, "f": TOP_ID, "s": 1, "x": HF, "xc": "LOW"},
        {"op": "respond", "w": 1, "f": BOTTOM_ID, "s": 1, "x": "nonsense", "xc": "LOW"},
        {"op": "timeout", "w": 1, "s": 1, "x": UF, "xc": "LOW"},
        {"op": "timeout", "w": 1, "s": 1, "x": HF, "xc": "LOW"},
        {"op": "open"},
        {"op": "seal", "w": 2, "f": BOTTOM_ID, "a": UH, "c": "HIGH", "r": RG},
        {"op": "respond", "w": 2, "f": TOP_ID, "s": 2, "x": HC, "xc": "HIGH"},
        {"op": "open"},
        {"op": "seal", "w": 3, "f": TOP_ID, "a": CF, "c": "LOW", "r": ""},
        {"op": "respond", "w": 3, "f": BOTTOM_ID, "s": 3, "x": KSH, "xc": ""},
        {"op": "open"},
        {"op": "seal", "w": 4, "f": BOTTOM_ID, "a": UH, "c": "LOW", "r": RG},
        {"op": "end"},
        {"op": "respond", "w": 4, "f": TOP_ID, "s": 4, "x": HP, "xc": "LOW"},
    ]


func _run_log(p: BjjHalfGuardSealedProtocol, log: Array) -> Array:
    var outcomes: Array = []
    for step: Dictionary in log:
        match str(step.op):
            "open":
                outcomes.append(rep(p.open_window()))
            "seal":
                outcomes.append(rep(p.seal_intent(int(step.w), str(step.f), str(step.a), str(step.c), str(step.r))))
            "respond":
                outcomes.append(rep(p.respond(int(step.w), str(step.f), int(step.s), str(step.x), str(step.xc))))
            "timeout":
                outcomes.append(rep(p.apply_response_timeout(int(step.w), int(step.s), str(step.x), str(step.xc))))
            "end":
                outcomes.append(rep(p.end_session()))
    return outcomes


func _test_deterministic_replay() -> void:
    var log := _scenario_log()
    var first := at()
    var second := at()
    var out_first := _run_log(first, log)
    var out_second := _run_log(second, log)
    check("every outcome replays identically", out_first, out_second)
    check("the whole executor state replays identically", first.executor_snapshot(), second.executor_snapshot())
    check("the public stream replays identically", first.public_events(), second.public_events())
    var errors: Array = out_first.map(func(o: Dictionary) -> String: return str(o.error))
    check("the scenario's refusals and acceptances are as designed", errors, ["", "", "intent_already_sealed", "not_responder", "unknown_response", "fallback_not_published", "",
        "", "", "", "", "", "", "", "", "", "session_closed"])
    check("two exchanges resolved: a feint (timed out) and a bottom feint then a direct one", first.history_fields().initiated_action_history, [KS, RG, CF])
    # the executor's own event log is a replayable command log (including the sealed real technique)
    var original := at()
    original.open_window()
    original.seal_intent(1, TOP_ID, CF, "MEDIUM", KS)
    original.apply_response_timeout(1, 1, HF, "LOW")
    original.open_window()
    original.seal_intent(2, BOTTOM_ID, UH, "HIGH", RG)
    original.respond(2, TOP_ID, 2, HC, "HIGH")
    original.open_window()
    original.seal_intent(3, TOP_ID, CF, "LOW")
    original.respond(3, BOTTOM_ID, 3, KSH, "")
    var rebuilt := at()
    for event: Dictionary in original.protocol_events():
        match str(event.event):
            "intent_sealed":
                rebuilt.open_window()
                var real := str(event.real_action_id)
                rebuilt.seal_intent(int(event.window_id), str(event.initiator_id), str(event.apparent_technique_id), str(event.commitment_requested), "" if real == str(event.apparent_technique_id) else real)
            "response_committed":
                if bool(event.defaulted):
                    rebuilt.apply_response_timeout(int(event.window_id), int(event.intent_serial), str(event.response_id), str(event.response_commitment_requested))
                else:
                    rebuilt.respond(int(event.window_id), str(event.responder_id), int(event.intent_serial), str(event.response_id), str(event.response_commitment_requested))
    check("replaying the resolved command log reproduces the whole executor state", rebuilt.executor_snapshot(), original.executor_snapshot())
    check("and the public stream", rebuilt.public_events(), original.public_events())


# ---- 12. The independent oracle through the protocol ----------------------------------------------------------------------------------------------------------------------

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
        push_error("Generate the Half Guard feint oracle fixture first")
        return rows
    while not fixture.eof_reached():
        var line := fixture.get_line()
        if line.is_empty():
            continue
        var row: Dictionary = JSON.parse_string(line)
        if family_names.has(str(row.family)):
            rows.append(row)
    return rows


func _seal_and_respond(p: BjjHalfGuardSealedProtocol, command: Dictionary) -> BjjMatchWindowGateway.Report:
    var fighter_id := str(command.fighter_id)
    var seal := p.seal_intent(int(command.window_id), fighter_id, str(command.action_id), str(command.commitment), str(command.get("real_action_id", "")))
    if not seal.ok():
        return seal
    var responder_id := ""
    for role: Variant in p.roles().fighter_by_role:
        if str(p.roles().fighter_by_role[role]) != fighter_id:
            responder_id = str(p.roles().fighter_by_role[role])
    return p.respond(int(command.window_id), responder_id, int(seal.values.intent_serial), str(command.response_id), str(command.response_commitment))


func _rebuild(request: Variant, applied: Array) -> BjjHalfGuardSealedProtocol:
    var p := BjjHalfGuardSealedProtocol.create(request).protocol
    for command: Dictionary in applied:
        if str(command.op) == "open":
            p.open_window_for(command.duration)
        elif str(command.action_id).is_empty():
            p.submit(int(command.window_id), str(command.fighter_id))
        else:
            _seal_and_respond(p, command)
    return p


func _test_oracle_trajectories_through_the_protocol() -> void:
    var trajectories := 0
    var accepted := 0
    var refused := 0
    var feints_accepted := 0
    for row: Dictionary in _rows(["feint_trajectory"]):
        trajectories += 1
        oracle_rows += 1
        var request: Variant = _decode(row.entry)
        var commands: Array = _decode(row.commands)
        var expected: Array = row.expected.results
        var main := BjjHalfGuardSealedProtocol.create(request).protocol
        var applied: Array = []
        for index in range(commands.size()):
            var command: Dictionary = commands[index]
            var want: Dictionary = expected[index]
            var tag := "oracle %s command %d" % [row.name, index]
            if str(command.op) == "open":
                check_loose(tag + " open", rep(main.open_window_for(command.duration)), want)
                applied.append(command)
            elif str(command.action_id).is_empty():
                var pass_report := main.submit(int(command.window_id), str(command.fighter_id), "", str(command.response_id), str(command.commitment), str(command.response_commitment))
                if str(command.get("real_action_id", "")).is_empty():
                    check_loose(tag + " pass", rep(pass_report), want)
                    if str(want.error).is_empty():
                        applied.append(command)
                else:
                    # a pass carrying a real technique is the oracle's feint_without_action; the protocol has no such input (its seal needs an apparent technique)
                    check(tag + " the oracle refuses a pass that carries a real technique", want.error, "feint_without_action")
                    check(tag + " the protocol's pass without a real technique is a plain pass", pass_report.ok(), true)
                    main = _rebuild(request, applied)
            else:
                var probe := _rebuild(request, applied)
                var probe_before := probe.snapshot()
                var outcome := _seal_and_respond(probe, command)
                if outcome.ok():
                    accepted += 1
                    if not str(command.get("real_action_id", "")).is_empty():
                        feints_accepted += 1
                    check(tag + " the protocol accepts exactly what the oracle accepts", str(want.error).is_empty(), true)
                    check_loose(tag + " exchange report", rep(outcome), want)
                    check_loose(tag + " exchange report on the main protocol", rep(_seal_and_respond(main, command)), want)
                    applied.append(command)
                else:
                    refused += 1
                    check(tag + " the protocol refuses exactly what the oracle refuses", str(want.error).is_empty(), false)
                    check(tag + " the refusal changed no simulation state", probe.snapshot(), probe_before)
                    # the seal's own code equals the oracle's for every feint-specific refusal and for addressing / window refusals
                    if str(want.error).begins_with("feint_") or str(want.error) in ["not_initiator", "stale_window", "no_open_window"]:
                        check(tag + " refusal code", outcome.error, want.error)
        check_loose("oracle %s final snapshot" % row.name, main.snapshot(), row.expected.final)
        check("oracle %s leaves nothing pending" % row.name, main.has_pending_intent(), false)
    check("all ten feint trajectories were replayed", trajectories, 10)
    check("feint exchanges were accepted through the protocol", feints_accepted >= 8, true)
    check("and refusals were exercised", refused >= 4, true)
    check("accepted exchanges include direct ones", accepted > feints_accepted, true)


func _test_oracle_grid_through_the_protocol() -> void:
    var rows := 0
    var accepted := 0
    var refused := 0
    for row: Dictionary in _rows(["feint_grid", "feint_funding"]):
        rows += 1
        oracle_rows += 1
        var snapshot: Dictionary = _decode(row.snapshot)
        var command: Dictionary = _decode(row.command)
        var request := {"role_map": snapshot.role_map.duplicate(true), "fighters": snapshot.fighters.duplicate(true),
            "clock": {"initial_seconds": snapshot.initial_clock, "remaining_seconds": snapshot.clock_seconds},
            "window": {"last_issued_id": snapshot.window_id}, "interval_seconds": snapshot.interval_seconds}
        var p := BjjHalfGuardSealedProtocol.create(request).protocol
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
        var before := p.snapshot()
        var seal := p.seal_intent(int(snapshot.window_id), initiator_id, str(command.action_id), str(command.commitment), str(command.real_action_id))
        if not str(row.expected.error).is_empty():
            refused += 1
            check_loose("grid row %d the seal is refused with the oracle's code" % rows, seal.error, row.expected.error)
            check("grid row %d the refusal changed nothing" % rows, p.snapshot(), before)
            continue
        accepted += 1
        check("grid row %d the seal is accepted" % rows, seal.error, "")
        var done := p.respond(int(snapshot.window_id), responder_id, 1, str(command.response_id), str(command.response_commitment))
        check("grid row %d the response is accepted" % rows, done.error, "")
        if not done.ok():
            continue
        var settlement: Dictionary = done.values.detail.settlement.duplicate(true)
        settlement["error"] = ""
        check_loose("grid row %d settlement" % rows, settlement, row.expected)
        var final: Dictionary = _decode(row.final)
        final["window_open"] = false
        final["window_side"] = ""
        check_loose("grid row %d final snapshot" % rows, p.snapshot(), final)
    check("every feint grid and funding row was replayed", rows, 6372)
    check("both accepted and refused rows exist", [accepted > 0, refused > 0], [true, true])


# ---- 13. Other surfaces are unchanged -----------------------------------------------------------------------------------------------------------------------------------

func _method_names(script: GDScript) -> Array:
    var names: Array = []
    for method: Dictionary in script.get_script_method_list():
        names.append(str(method.name))
    names.sort()
    return names


func _test_unchanged_surfaces() -> void:
    for method_name: String in ["seal_intent", "respond", "apply_response_timeout", "public_intent_view", "submit_feint", "feint_error"]:
        check("the Mount gateway has no %s" % method_name, _method_names(BjjMatchWindowGateway).has(method_name), false)
        # B1i: the graph has the sealed coordinator methods (seal_intent, respond, apply_response_timeout, public_intent_view) but never the feint rules
        check("the position graph has %s only if it is a B1i coordinator method" % method_name, _method_names(BjjPositionGraphMatch).has(method_name),
            method_name in ["seal_intent", "respond", "apply_response_timeout", "public_intent_view"])
        check("the position contract has no %s" % method_name, _method_names(BjjPositionContract).has(method_name), false)
    check("the Half Guard contract has no feint method", _method_names(BjjHalfGuardContract).has("submit_feint"), false)
    # the existing one-call gateway path still behaves exactly as before and a direct command never takes the feint path
    var g := twin_at()
    var w := g.open_window().values
    var direct := g.submit(int(w.window_id), TOP_ID, KS, HF, "MEDIUM", "MEDIUM")
    check("the one-call direct path resolves and has no feint record", [direct.ok(), direct.values.detail.settlement.has("feint")], [true, false])
    check("and charges once", [g.state_fields().top_stamina, g.state_fields().bottom_stamina], [93, 93])
    var h := twin_at()
    var hw := h.open_window().values
    var before := h.snapshot()
    check("the gateway's pure admission check says a funded FP-1 is admissible", h.feint_error(CF, KS, "MEDIUM"), "")
    check("and mutates nothing", h.snapshot(), before)
    check("a feint with an empty real technique through the gateway is exactly the direct exchange", rep(h.submit_feint(int(hw.window_id), TOP_ID, KS, "", HF, "MEDIUM", "MEDIUM")),
        rep(direct))


# ---- 14. Scope and hygiene ----------------------------------------------------------------------------------------------------------------------------------------------------

func _code_text(path: String) -> String:
    var file := FileAccess.open(path, FileAccess.READ)
    if file == null:
        return ""
    var code_lines: Array[String] = []
    for source_line: String in file.get_as_text().split("\n"):
        code_lines.append(source_line.split("#")[0])
    return "\n".join(code_lines)


func _test_scope_and_hygiene() -> void:
    var base := "res://scripts/positions/half_guard/"
    for path: String in ["half_guard_rules", "half_guard_catalog", "half_guard_resolver", "half_guard_entry", "half_guard_match", "half_guard_contract", "half_guard_window_gateway"]:
        var text := _code_text(base + path + ".gd")
        check("%s is readable" % path, text.is_empty(), false)
        for token: String in ["randi", "randf", "RandomNumberGenerator", "Time.", "OS.get_ticks", "await", "get_tree", "Engine.get_frames", "FileAccess", "preload(",
                "SealedProtocol", "seal_intent", "defaulted", "BjjMount", "BjjPositionGraphMatch"]:
            check("%s has no %s" % [path, token], text.contains(token), false)
    # the feint rules live in one place each
    var match_text := _code_text(base + "half_guard_match.gd")
    var resolver_text := _code_text(base + "half_guard_resolver.gd")
    check("the match builds the feint funding once", match_text.count("func _feint_funding("), 1)
    check("the surcharge constant is read only where it is charged and funded", [match_text.count("BjjHalfGuardRules.FEINT_SURCHARGE")], [5])
    check("the bite table is read only by the resolver (grade) and the match (record)", [resolver_text.count("FEINT_PAIRS"), match_text.count("FEINT_PAIRS")], [1, 3])
    check("there is exactly one place that applies the feint grade modifier", resolver_text.count("grade_after_feint = BjjGrade.shift("), 1)
    check("and one place that removes the LOW-feint exit", resolver_text.count("r.exit_capped = true"), 1)
    # nobody outside the Half Guard files knows feints: Mount, the graph, F0 and F1
    for path: String in ["res://scripts/positions/graph_match.gd", "res://scripts/positions/mount/mount_window_gateway.gd", "res://scripts/positions/mount/mount_match.gd",
            "res://scripts/presentation/mount_debug_view.gd"]:
        var other := _code_text(path)
        if other.is_empty():
            continue
        for token: String in ["submit_feint", "seal_intent", "FEINT_PAIRS", "SealedProtocol", "timeout_fallback", "feint_error"]:
            # B1i: the graph names the protocol (slot, adoption, forwarding) but never the feint rules, the pair table, the fallback table or the admission check
            check("%s references %s only as the B1i opt-in" % [path, token], other.contains(token),
                path.ends_with("graph_match.gd") and token in ["seal_intent", "SealedProtocol"])
    var referencing: Array = []
    for directory: String in ["res://scripts/core", "res://scripts/positions", "res://scripts/positions/mount", "res://scripts/presentation", "res://scripts/ui"]:
        var dir := DirAccess.open(directory)
        if dir == null:
            continue
        for file_name: String in dir.get_files():
            if file_name.ends_with(".gd") and _code_text(directory + "/" + file_name).contains("BjjHalfGuardSealedProtocol"):
                referencing.append(directory + "/" + file_name)
    check("only the graph's explicit opt-in references the protocol (B1i); no other production source does", referencing, ["res://scripts/positions/graph_match.gd"])
    # the controller double above never names executor internals
    var own := FileAccess.open("res://tests/test_half_guard_feint_protocol.gd", FileAccess.READ).get_as_text()
    var begin := own.find("# BEGIN controller double")
    var finish := own.find("# END controller double")
    check("the controller double is delimited", begin >= 0 and finish > begin, true)
    var controller := own.substr(begin, finish - begin)
    for token: String in ["executor_snapshot", "protocol_events", "sealed_intent_view", "_events", "_serial", "has_pending_intent", "BjjHalfGuardSealedProtocol", "_match"]:
        check("the controller double never names %s" % token, controller.contains(token), false)
    var protocol_text := _code_text(PROTOCOL_PATH)
    check("the protocol still calls no resolver and no match", [protocol_text.contains("BjjHalfGuardResolver"), protocol_text.contains(".attempt("), protocol_text.contains(".decide(")],
        [false, false, false])
