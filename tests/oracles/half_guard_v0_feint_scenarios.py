"""Bounded, deterministic feint scenario families for the Half Guard v0 oracle (B1h checkpoint).

Shared by the focused unit tests and the fixture generator. Expected values always come from ``half_guard_v0`` (the oracle);
the *hand-computed literals* live in ``tests/test_half_guard_feint_oracle.py`` and are checked against the oracle there, so the
fixture is anchored by literals and is never a self-generated expectation alone. Counts are measured by running the families,
never asserted from documentation. Nothing here imports GDScript, Mount or the frozen engine.
"""
import copy
import functools

from . import half_guard_v0 as O
from . import half_guard_v0_scenarios as S

A, R = S.ACTION, S.RESPONSE
TOP_ID, BOTTOM_ID = S.TOP_ID, S.BOTTOM_ID
# (initiator side, apparent, real, own track, bite response id)
PAIRS = (("top", A["cf"], A["ks"], "top_base", R["uf"]), ("bottom", A["uh"], A["rg"], "bottom_frame", R["hc"]))
RESPONSES_FOR = {"top": (R["hf"], R["uf"], R["ks"]), "bottom": (R["hc"], R["hp"], R["kp"])}
# Legal (axis_tenths, band) boundary states per acting side: neutral, edges, one step before / at / past a break line, control bands.
AXES = {"top": ((5, 0), (15, 1), (20, 1), (26, 1), (28, 2), (-15, -1), (-30, -2)),
        "bottom": ((5, 0), (-15, -1), (-20, -1), (-26, -1), (-28, -2), (15, 1), (30, 2))}
# Initiator stamina profiles (maximum 100): refused (0-5), LOW-only (6-9), MEDIUM-reachable (10-14), HIGH-reachable (15+) and the
# latch edges: a LOW feint (6) from 31 lands on 25 (latched), from 32 on 26 (not latched).
FUNDING_STAMINA = (0, 2, 3, 5, 6, 8, 9, 10, 12, 14, 15, 16, 20, 25, 31, 32, 100)
COMMITMENTS = ("LOW", "MEDIUM", "HIGH")
RESPONSE_COMMITMENTS = ("", "LOW", "MEDIUM", "HIGH")


def _state(side, axis, band, top_base, bottom_frame, initiator_stamina=100, responder_stamina=100):
    top_current, bottom_current = (initiator_stamina, responder_stamina) if side == "top" else (responder_stamina, initiator_stamina)
    return S.state_with(initiator=side, axis_tenths=axis, band=band, top_base=top_base, bottom_frame=bottom_frame,
                        top_current=top_current, bottom_current=bottom_current)


def _row(family, state, command):
    match = O.HalfGuard.from_snapshot(state)
    result = match.attempt(command["action_id"], command["response_id"], command["commitment"], command["response_commitment"],
                           command.get("real_action_id", ""))
    return {"family": family, "snapshot": copy.deepcopy(state), "command": {"op": "attempt", **command}, "expected": result,
            "final": match.snapshot()}


@functools.lru_cache(maxsize=None)
def grid_rows():
    """Feint grid: both pairs x own tier x other tier x boundary states x every response x commitments x response commitments."""
    rows = []
    for side, apparent, real, track, _ in PAIRS:
        other_track = "bottom_frame" if track == "top_base" else "top_base"
        for own in (0, 1, 2):
            for other in (0, 1, 2):
                for axis, band in AXES[side]:
                    tiers = {track: own, other_track: other}
                    state = _state(side, axis, band, tiers["top_base"], tiers["bottom_frame"])
                    for response in RESPONSES_FOR[side]:
                        for commitment in COMMITMENTS:
                            for response_commitment in RESPONSE_COMMITMENTS:
                                rows.append(_row("feint_grid", state, {"action_id": apparent, "real_action_id": real, "response_id": response,
                                                                       "commitment": commitment, "response_commitment": response_commitment}))
    return rows


@functools.lru_cache(maxsize=None)
def funding_rows():
    """The funding boundary grid: initiator stamina x requested x pair x tiers x response x responder stamina."""
    rows = []
    for side, apparent, real, track, _ in PAIRS:
        for tiers in ((1, 1), (2, 2)):
            for initiator_stamina in FUNDING_STAMINA:
                for responder_stamina in (100, 7, 2):
                    state = _state(side, 5, 0, tiers[0], tiers[1], initiator_stamina, responder_stamina)
                    for response in RESPONSES_FOR[side]:
                        for commitment in COMMITMENTS:
                            rows.append(_row("feint_funding", state, {"action_id": apparent, "real_action_id": real, "response_id": response,
                                                                      "commitment": commitment, "response_commitment": ""}))
    return rows


@functools.lru_cache(maxsize=None)
def timeout_rows():
    """The published fallback (defender role -> response, LOW) against direct and feint attackers at every requested commitment."""
    rows = []
    for side, apparent, real, track, _ in PAIRS:
        defender = "bottom" if side == "top" else "top"
        fallback, fallback_commitment = O.TIMEOUT_FALLBACK[defender]
        direct_actions = O.ACTIONS[side]
        state = _state(side, 5, 0, 1, 1)
        for commitment in COMMITMENTS:
            for action in direct_actions:
                rows.append(_row("timeout_fallback", state, {"action_id": action, "real_action_id": "", "response_id": fallback,
                                                             "commitment": commitment, "response_commitment": fallback_commitment}))
            rows.append(_row("timeout_fallback", state, {"action_id": apparent, "real_action_id": real, "response_id": fallback,
                                                         "commitment": commitment, "response_commitment": fallback_commitment}))
    return rows


def refusal_cases():
    """(label, state, command) where the expected result is a refusal. Hand-listed; every code and the precedence pairs."""
    top = _state("top", 5, 0, 1, 1)
    bottom = _state("bottom", 5, 0, 1, 1)

    def top_cmd(**kw):
        base = {"action_id": A["cf"], "real_action_id": A["ks"], "response_id": R["hf"], "commitment": "MEDIUM", "response_commitment": ""}
        base.update(kw)
        return base

    def bottom_cmd(**kw):
        base = {"action_id": A["uh"], "real_action_id": A["rg"], "response_id": R["hc"], "commitment": "MEDIUM", "response_commitment": ""}
        base.update(kw)
        return base

    return [
        ("real equals apparent (top)", top, top_cmd(action_id=A["ks"], real_action_id=A["ks"])),
        ("real equals apparent (crossface)", top, top_cmd(real_action_id=A["cf"])),
        ("flatten to knee slice is excluded", top, top_cmd(action_id=A["fl"])),
        ("knee slice to crossface is not a pair", top, top_cmd(action_id=A["ks"], real_action_id=A["cf"])),
        ("crossface to flatten (not break-capable) is not a pair", top, top_cmd(real_action_id=A["fl"])),
        ("bottom real from the top side", top, top_cmd(real_action_id=A["rg"])),
        ("unknown real", top, top_cmd(real_action_id="nonsense")),
        ("a response id as the real", top, top_cmd(real_action_id=R["hf"])),
        ("underhook to knee slice crosses sides", bottom, bottom_cmd(real_action_id=A["ks"])),
        ("underhook to recover guard eligible but recover to underhook is not", bottom, bottom_cmd(action_id=A["rg"], real_action_id=A["uh"])),
        ("top apparent with None track", _state("top", 5, 0, 0, 1), top_cmd()),
        ("bottom apparent with None track", _state("bottom", 5, 0, 1, 0), bottom_cmd()),
        ("the other side's track does not help (top)", _state("top", 5, 0, 0, 2), top_cmd()),
        ("the other side's track does not help (bottom)", _state("bottom", 5, 0, 2, 0), bottom_cmd()),
        ("unfunded below the surcharge (top, 2)", _state("top", 5, 0, 1, 1, 2), top_cmd()),
        ("unfunded below the surcharge (top, 0)", _state("top", 5, 0, 1, 1, 0), top_cmd(commitment="LOW")),
        ("unfunded: commitment unaffordable after the surcharge (top, 5)", _state("top", 5, 0, 1, 1, 5), top_cmd(commitment="HIGH")),
        ("unfunded: commitment unaffordable after the surcharge (bottom, 5)", _state("bottom", 5, 0, 1, 1, 5), bottom_cmd(commitment="LOW")),
        ("invalid commitment still reported first", top, top_cmd(commitment="EXTREME", real_action_id="nonsense")),
        ("invalid response commitment before the feint checks", top, top_cmd(response_commitment="bad", real_action_id="nonsense")),
        ("unknown apparent before the feint checks", top, top_cmd(action_id="nonsense", real_action_id=A["ks"])),
        ("foreign apparent before the feint checks", top, top_cmd(action_id=A["uh"], real_action_id=A["rg"])),
        ("unknown response before the feint checks", top, top_cmd(response_id="nonsense", real_action_id="nonsense")),
        ("foreign response before the feint checks", top, top_cmd(response_id=R["hc"], real_action_id="nonsense")),
        ("equality before the real id's own shape", top, top_cmd(action_id="half_guard.top.crossface", real_action_id=A["cf"], response_id=R["hf"])),
        ("not supported before not eligible", _state("top", 5, 0, 0, 1), top_cmd(action_id=A["fl"])),
        ("not eligible before funding", _state("top", 5, 0, 0, 1, 2), top_cmd()),
        ("a terminal state refuses a feint", S.state_with(exit_destination="Side Control", initiator="top"), top_cmd()),
    ]


@functools.lru_cache(maxsize=None)
def refusal_rows():
    rows = []
    for label, state, command in refusal_cases():
        row = _row("feint_refusal", state, command)
        row["label"] = label
        rows.append(row)
    return rows


def _open(duration=None):
    return {"op": "open", "duration": duration}


def _submit(window_id, fighter_id, action="", response="", commitment="", response_commitment="", real=""):
    command = {"op": "submit", "window_id": window_id, "fighter_id": fighter_id, "action_id": action, "response_id": response,
               "commitment": commitment, "response_commitment": response_commitment}
    if real:
        command["real_action_id"] = real
    return command


def trajectories():
    cf, ks, uh, rg = A["cf"], A["ks"], A["uh"], A["rg"]
    hf, uf, ksh, hc, hp, kp = R["hf"], R["uf"], R["ks"], R["hc"], R["hp"], R["kp"]
    return [
        # a feint, then a direct technique, then a bottom feint: one window and one exchange each, strict alternation
        ("feint_then_direct_then_bottom_feint", S.entry(), [
            _open(), _submit(1, TOP_ID, cf, hf, "MEDIUM", "MEDIUM", ks),
            _open(), _submit(2, BOTTOM_ID, uh, hc, "MEDIUM", "MEDIUM", rg),
            _open(), _submit(3, TOP_ID, cf, uf, "HIGH", "LOW"),
        ]),
        ("pass_and_refused_feint_keep_the_window", S.entry(), [
            _open(), _submit(1, TOP_ID, "", "", "", "", ks),
            _submit(1, TOP_ID, cf, hf, "MEDIUM", "MEDIUM", cf),
            _submit(1, TOP_ID, fl_pair(), hf, "MEDIUM", "MEDIUM", ks),
            _submit(1, BOTTOM_ID, cf, hf, "MEDIUM", "MEDIUM", ks),
            _submit(1, TOP_ID, cf, hf, "MEDIUM", "MEDIUM", ks),
        ]),
        ("unfunded_attacker_cannot_feint_but_can_attack_directly", S.entry(top_current=4), [
            _open(), _submit(1, TOP_ID, cf, hf, "HIGH", "MEDIUM", ks), _submit(1, TOP_ID, cf, hf, "HIGH", "MEDIUM"),
        ]),
        ("rule_one_waiver_only_for_an_unfunded_direct_attack", S.entry(top_current=2), [
            _open(), _submit(1, TOP_ID, cf, hf, "MEDIUM", "MEDIUM", ks), _submit(1, TOP_ID, ks, hf, "MEDIUM", "MEDIUM"),
        ]),
        ("medium_feint_exits_to_side_control_from_a_prepared_edge", S.entry(), _exit_script(ks_commitment="MEDIUM")),
        ("low_feint_cannot_exit", S.entry(), _exit_script(ks_commitment="LOW")),
        ("bottom_feint_exits_by_escape", S.entry(), _bottom_escape_script()),
        ("published_fallback_after_a_feint_and_a_direct_attack", S.entry(), [
            _open(), _submit(1, TOP_ID, cf, hf, "MEDIUM", "LOW", ks),
            _open(), _submit(2, BOTTOM_ID, uh, hp, "HIGH", "LOW"),
            _open(), _submit(3, TOP_ID, cf, hf, "LOW", "LOW", ks),
        ]),
        ("repeated_called_feints_are_self_defeating", S.entry(), [
            _open(), _submit(1, TOP_ID, cf, ksh, "MEDIUM", "MEDIUM", ks),
            _open(), _submit(2, BOTTOM_ID, "", ""),
            _open(), _submit(3, TOP_ID, cf, ksh, "MEDIUM", "MEDIUM", ks),
            _open(), _submit(4, BOTTOM_ID, "", ""),
            _open(), _submit(5, TOP_ID, cf, ksh, "MEDIUM", "MEDIUM", ks),
        ]),
        ("clock_advances_only_when_a_window_opens", S.entry(clock=12), [
            _open(), _submit(1, TOP_ID, cf, uf, "MEDIUM", "MEDIUM", ks),
            _open(), _submit(2, BOTTOM_ID, uh, hc, "MEDIUM", "MEDIUM", rg),
            _open(), _open(),
        ]),
    ]


def fl_pair():
    return A["fl"]


def _exit_script(ks_commitment):
    # Two Crossface->Knee Slice feints that bite (Underhook Fight) build axis; the third attack from the edge uses the requested commitment.
    cf, ks, uh = A["cf"], A["ks"], A["uh"]
    uf, hc, hf = R["uf"], R["hc"], R["hf"]
    return [
        _open(), _submit(1, TOP_ID, cf, uf, "MEDIUM", "MEDIUM", ks),   # +2 -> axis 25 (band 1)
        _open(), _submit(2, BOTTOM_ID, "", ""),                          # bottom passes
        _open(), _submit(3, TOP_ID, cf, uf, ks_commitment, "MEDIUM", ks),  # from 25: would reach the pass line
        _open(),
    ]


def _bottom_escape_script():
    uh, rg, cf = A["uh"], A["rg"], A["cf"]
    hc, hf = R["hc"], R["hf"]
    return [
        _open(), _submit(1, TOP_ID, ""),                                                # top passes, bottom initiates next
        _open(), _submit(2, BOTTOM_ID, uh, hc, "MEDIUM", "MEDIUM", rg),                 # bite: +2 for bottom -> axis -15
        _open(), _submit(3, TOP_ID, ""),
        _open(), _submit(4, BOTTOM_ID, uh, hc, "MEDIUM", "MEDIUM", rg),                 # again from -15: -35 -> clamp, escape
        _open(),
    ]


@functools.lru_cache(maxsize=None)
def trajectory_rows():
    rows = []
    for name, entry, commands in trajectories():
        rows.append({"family": "feint_trajectory", "name": name, "entry": entry, "commands": commands,
                     "expected": O.replay(entry, commands)})
    return rows


@functools.lru_cache(maxsize=None)
def public_view_rows():
    """The public intent view over tier pairs x actions of the initiating side x requested commitments (serial fixed)."""
    rows = []
    for side in ("top", "bottom"):
        for top_base in (0, 1, 2):
            for bottom_frame in (0, 1, 2):
                state = _state(side, 5, 0, top_base, bottom_frame)
                for apparent in O.ACTIONS[side]:
                    for commitment in ("",) + COMMITMENTS:
                        rows.append({"family": "public_view", "snapshot": state, "apparent_action_id": apparent, "commitment": commitment,
                                     "intent_serial": 7, "expected": O.public_intent_view(state, apparent, commitment, 7)})
    return rows


def fallback_rows():
    return [{"family": "published_fallback", "defender_role": role, "expected": {"response_id": O.TIMEOUT_FALLBACK[role][0],
                                                                                  "commitment": O.TIMEOUT_FALLBACK[role][1]}}
            for role in ("bottom", "top")]


def funding_table_rows():
    return [{"family": "funding_table", "stamina": stamina, "requested": requested,
             "expected": dict(zip(("effective", "total_cost"), O.feint_funding(stamina, requested)))}
            for stamina in FUNDING_STAMINA for requested in COMMITMENTS]


def all_rows():
    return (list(funding_table_rows()) + fallback_rows() + list(public_view_rows()) + list(refusal_rows()) + list(timeout_rows())
            + list(trajectory_rows()) + list(funding_rows()) + list(grid_rows()))
