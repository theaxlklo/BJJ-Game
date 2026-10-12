#!/usr/bin/env python3
"""Half Guard v0 feint tactical measurements (B1h). Evidence only -- NOT a gate, NOT a balance claim.

Everything is computed with the independent test-only oracle (``tests/oracles/half_guard_v0.py``); no GDScript is run. The Godot engine
reproduces the oracle exactly (``test_half_guard_feint_reference.gd``), so these numbers describe the engine too. Deterministic: no clock, no
Python ``random`` (a fixed linear congruential generator drives the seeded populations), stable ordering, stable output.

Two kinds of evidence are kept apart on purpose:
  * STRUCTURAL: exact facts about the rules (one-exchange grade tables, exact funding arithmetic, forced searches, reachability).
  * POPULATION: counts over seeded policy populations. They describe what a stated policy does; they say nothing about balance or fun.

Usage:  python GODOT_V1/tests/measure_half_guard_feints.py
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "tests"))

from oracles import half_guard_v0 as O  # noqa: E402
from oracles import half_guard_v0_scenarios as S  # noqa: E402

A, R = S.ACTION, S.RESPONSE
TOP, BOT = S.TOP_ID, S.BOTTOM_ID
PAIRS = {"top": (A["cf"], A["ks"], R["uf"], R["ks"]), "bottom": (A["uh"], A["rg"], R["hc"], R["kp"])}  # apparent, real, bite, call
RESPONSES = {"top": (R["hf"], R["uf"], R["ks"]), "bottom": (R["hc"], R["hp"], R["kp"])}


def short(identifier):
    return identifier.rsplit(".", 1)[1]


def state(side="top", axis=5, band=0, top_base=1, bottom_frame=1, initiator_stamina=100, responder_stamina=100):
    top_current, bottom_current = (initiator_stamina, responder_stamina) if side == "top" else (responder_stamina, initiator_stamina)
    return S.state_with(initiator=side, axis_tenths=axis, band=band, top_base=top_base, bottom_frame=bottom_frame, top_current=top_current, bottom_current=bottom_current)


def final(snapshot, apparent, response, commitment, response_commitment, real=""):
    result = O.HalfGuard.from_snapshot(snapshot).attempt(apparent, response, commitment, response_commitment, real)
    return None if result["error"] else result["final_grade"]


def table(rows):
    widths = [max(len(str(r[i])) for r in rows) for i in range(len(rows[0]))]
    return "\n".join("| " + " | ".join(str(c).ljust(widths[i]) for i, c in enumerate(r)) + " |" for r in rows)


class Lcg:
    def __init__(self, seed):
        self.x = (seed * 6364136223846793005 + 1442695040888963407) % (1 << 64)

    def below(self, n):
        self.x = (self.x * 6364136223846793005 + 1442695040888963407) % (1 << 64)
        return (self.x >> 33) % n


# ---- 1. One-exchange grade tables (structural) ---------------------------------------------------------------------------------
def one_exchange_tables():
    out = []
    for side in ("top", "bottom"):
        apparent, real, bite, call = PAIRS[side]
        out.append("\n**%s: %s -> %s (bite = %s, call = %s), defender answers MEDIUM, attacker at 100 stamina, neutral axis**" %
                   (side.title(), short(apparent), short(real), short(bite), short(call)))
        rows = [["tiers (own/other)", "attacker commitment", "defender response", "direct apparent", "direct real", "feint", "feint exits?"]]
        for own in (1, 2):
            for commitment in O.COMMITMENTS:
                for response in RESPONSES[side]:
                    snap = state(side, top_base=own if side == "top" else 1, bottom_frame=own if side == "bottom" else 1)
                    d_app = final(snap, apparent, response, commitment, "MEDIUM")
                    d_real = final(snap, real, response, commitment, "MEDIUM")
                    f = O.HalfGuard.from_snapshot(snap).attempt(apparent, response, commitment, "MEDIUM", real)
                    rows.append(["%s/1" % ("Ready" if own == 2 else "Partial"), commitment, short(response), d_app, d_real, f["final_grade"], f["exit_destination"] or "-"])
        out.append(table(rows))
    return "\n".join(out)


# ---- 2. Does preparation create opportunities? (structural) -------------------------------------------------------------------------
def opportunity_counts():
    rows = [["pair", "own tier", "cells (response x commitment x defender commitment)", "feint strictly beats BOTH direct options", "feint equals the better direct option", "feint strictly worse than the better direct option"]]
    for side in ("top", "bottom"):
        apparent, real, _, _ = PAIRS[side]
        for own in (0, 1, 2):
            snap = state(side, top_base=own if side == "top" else 1, bottom_frame=own if side == "bottom" else 1)
            cells = better = equal = worse = 0
            for response in RESPONSES[side]:
                for commitment in O.COMMITMENTS:
                    for defender in ("LOW", "MEDIUM", "HIGH"):
                        f = final(snap, apparent, response, commitment, defender, real)
                        if f is None:
                            continue
                        best_direct = max(final(snap, apparent, response, commitment, defender), final(snap, real, response, commitment, defender))
                        cells += 1
                        better += f > best_direct
                        equal += f == best_direct
                        worse += f < best_direct
            rows.append(["%s -> %s" % (short(apparent), short(real)), ["None (not eligible)", "Partial", "Ready"][own], cells, better, equal, worse])
    return table(rows)


# ---- 3. Defender policies: worst cases ---------------------------------------------------------------------------------------------
def policy_table():
    rows = [["pair", "defender policy", "response", "direct apparent", "feint (MEDIUM/MEDIUM)", "feint (HIGH/MEDIUM)", "attacker's worst case across {direct apparent, feint}"]]
    for side in ("top", "bottom"):
        apparent, real, bite, call = PAIRS[side]
        snap = state(side)
        balanced = min(RESPONSES[side], key=lambda r: (max(final(snap, apparent, r, "MEDIUM", "MEDIUM"), final(snap, apparent, r, "MEDIUM", "MEDIUM", real)), RESPONSES[side].index(r)))
        policies = (("fixed best counter to the APPARENT technique (bites)", bite), ("calls the bluff (best counter to the REAL technique)", call),
                    ("balanced (minimises the attacker's worst case)", balanced), ("timeout fallback (published, LOW)", O.TIMEOUT_FALLBACK["bottom" if side == "top" else "top"][0]))
        for name, response in policies:
            commitment = "LOW" if "fallback" in name else "MEDIUM"
            d = final(snap, apparent, response, "MEDIUM", commitment)
            f = final(snap, apparent, response, "MEDIUM", commitment, real)
            fh = final(snap, apparent, response, "HIGH", commitment, real)
            rows.append(["%s -> %s" % (short(apparent), short(real)), name, short(response), d, f, fh, max(d, f)])
    return table(rows)


# ---- 4. Stamina: how fast do feints deplete the attacker? (structural arithmetic + a driven sequence) ---------------------------------------
def depletion():
    rows = [["attack", "cost per attack", "attacks until the attacker is latched (<= 25) from 100", "attacker stamina then", "defender stamina then (answers MEDIUM)"]]
    for label, real, commitment in (("direct MEDIUM", "", "MEDIUM"), ("direct HIGH", "", "HIGH"), ("feint LOW (+3)", "x", "LOW"), ("feint MEDIUM (+3)", "x", "MEDIUM"), ("feint HIGH (+3)", "x", "HIGH")):
        attacker, defender, attacks = 100, 100, 0
        while attacker > 25:
            if real:
                _, total = O.feint_funding(attacker, commitment)
            else:
                total = O.determine(commitment, attacker)[1]
            attacker -= total
            defender -= O.determine("MEDIUM", defender)[1]
            attacks += 1
        rows.append([label, {"direct MEDIUM": 7, "direct HIGH": 12, "feint LOW (+3)": 6, "feint MEDIUM (+3)": 10, "feint HIGH (+3)": 15}[label], attacks, attacker, defender])
    return table(rows)


def repeated_feints(response_for, commitment, defender_commitment, windows=40, side="top"):
    """The attacker feints at every one of its windows; the defender answers by `response_for`; the other fighter's own windows are passes."""
    apparent, real, _, _ = PAIRS[side]
    match, _ = O.HalfGuard.from_entry(S.entry())
    history = []
    for _ in range(windows):
        report = match.open_window()
        if report.get("closed") or report["error"]:
            break
        if report["role"] == side:
            if match.s["top_base" if side == "top" else "bottom_frame"] < 1 or O.feint_funding(match.s["fighters"][match.s["role_map"][side]]["stamina_current"], commitment)[0] == "":
                history.append(("stop", match.s["axis_tenths"]))
                break
            r = match.submit(report["window_id"], report["fighter_id"], apparent, response_for(match), commitment, defender_commitment, real)
            history.append((short(r["detail"]["settlement"]["response_id"]), r["detail"]["settlement"]["final_grade"], match.s["axis_tenths"]))
        else:
            match.submit(report["window_id"], report["fighter_id"])
        if match.s["exit_destination"]:
            history.append(("EXIT " + match.s["exit_destination"], match.s["axis_tenths"]))
            break
    return match, history


def self_defeating():
    out = []
    for side in ("top", "bottom"):
        apparent, real, bite, call = PAIRS[side]
        for name, picker in (("always calls (best counter to the real technique)", lambda m, c=call: c), ("always bites", lambda m, b=bite: b)):
            match, history = repeated_feints(picker, "MEDIUM", "MEDIUM", windows=24, side=side)
            s = match.s
            own = "top" if side == "top" else "bottom"
            out.append("%s feinting %s -> %s every window, defender %s: %d feints, final axis %+d, attacker stamina %d, defender stamina %d, exit '%s'; exchanges (response, final grade, axis): %s" % (
                side, short(apparent), short(real), name, len([h for h in history if h[0] not in ("stop",) and not str(h[0]).startswith("EXIT")]), s["axis_tenths"],
                s["fighters"][s["role_map"][own]]["stamina_current"], s["fighters"][s["role_map"]["bottom" if own == "top" else "top"]]["stamina_current"],
                s["exit_destination"] or "none", history[:6]))
    return "\n".join("* " + line for line in out)


# ---- 5. Reachability of exits (structural search) and seeded population evidence ---------------------------------------------------------------
def key(snapshot):
    f = snapshot["fighters"]
    return (snapshot["axis_tenths"], snapshot["band"], snapshot["initiator"], snapshot["top_base"], snapshot["bottom_frame"], snapshot["exit_destination"],
            tuple((k, v["stamina_current"], v["exhaustion_latched"]) for k, v in sorted(f.items())))


def attacker_moves(side, allow_feint):
    moves = [(a, "") for a in O.ACTIONS[side]]
    if allow_feint:
        apparent, real = PAIRS[side][0], PAIRS[side][1]
        moves.append((apparent, real))
    return moves


def earliest_exits(allow_feint, defender, max_windows=5, commitments=("MEDIUM",)):
    """Breadth-first over windows. defender: 'any' (cooperative: every response at MEDIUM) | 'bite' | 'call' | 'balanced'."""
    start = O.HalfGuard.from_entry(S.entry())[0].snapshot()
    frontier, seen, found = [start], {key(start)}, {}
    for window in range(1, max_windows + 1):
        nxt = []
        for snap in frontier:
            side = snap["initiator"]
            base = O.HalfGuard.from_snapshot(snap)
            opened = base.open_window()
            if opened.get("closed") or opened["error"]:
                continue
            after_open = base.snapshot()
            # a pass
            m = O.HalfGuard.from_snapshot(after_open)
            m.submit(opened["window_id"], opened["fighter_id"])
            k = key(m.snapshot())
            if k not in seen:
                seen.add(k)
                nxt.append(m.snapshot())
            for apparent, real in attacker_moves(side, allow_feint):
                for commitment in commitments:
                    responses = RESPONSES[side]
                    if defender == "bite" and real:
                        responses = (PAIRS[side][2],)
                    elif defender == "bite":
                        responses = (PAIRS[side][2],) if apparent == PAIRS[side][0] else responses
                    elif defender == "call":
                        responses = (PAIRS[side][3],)
                    for response in responses:
                        m = O.HalfGuard.from_snapshot(after_open)
                        r = m.submit(opened["window_id"], opened["fighter_id"], apparent, response, commitment, "MEDIUM", real)
                        if r["error"]:
                            continue
                        if m.s["exit_destination"]:
                            found.setdefault(m.s["exit_destination"], window)
                            continue
                        k = key(m.snapshot())
                        if k not in seen:
                            seen.add(k)
                            nxt.append(m.snapshot())
        frontier = nxt
    return found


def reachability():
    rows = [["attacker options", "defender", "earliest window to Side Control", "to Open Guard", "to Closed Guard"]]
    for allow in (False, True):
        for defender in ("any", "bite", "call"):
            found = earliest_exits(allow, defender, 5, O.COMMITMENTS)
            rows.append(["direct + feint" if allow else "direct only", {"any": "cooperative (any response)", "bite": "always the bite response", "call": "always the call response"}[defender],
                         found.get("Side Control", "not within 5"), found.get("Open Guard", "not within 5"), found.get("Closed Guard", "not within 5")])
    return table(rows)


def population(seeds=500, windows=60):
    """Seeded uniform-random attackers (direct vs feint mixes) against fixed defender policies. Counts only; a description of the policies, not of balance."""
    results = {}
    attackers = (("direct only", 0), ("feints 50% of the time when eligible", 50), ("feints whenever eligible", 100))
    defenders = ("random response", "always bites", "always calls", "published fallback (LOW) every time")
    for aname, feint_percent in attackers:
        for dname in defenders:
            tally = {"Side Control": 0, "Open Guard": 0, "Closed Guard": 0, "timeout": 0}
            total_windows = feints = exits_by_feint = 0
            for seed in range(seeds):
                rng = Lcg(seed)
                match, _ = O.HalfGuard.from_entry(S.entry())
                for w in range(windows):
                    opened = match.open_window()
                    if opened.get("closed") or opened["error"]:
                        break
                    total_windows += 1
                    side = opened["role"]
                    apparent_choices = O.ACTIONS[side]
                    if rng.below(5) == 0:
                        match.submit(opened["window_id"], opened["fighter_id"])
                        continue
                    action = apparent_choices[rng.below(len(apparent_choices))]
                    real = ""
                    if action == PAIRS[side][0] and match.s["top_base" if side == "top" else "bottom_frame"] >= 1 and rng.below(100) < feint_percent:
                        stamina = match.s["fighters"][match.s["role_map"][side]]["stamina_current"]
                        if O.feint_funding(stamina, "MEDIUM")[0]:
                            real = PAIRS[side][1]
                    commitment = O.COMMITMENTS[rng.below(3)]
                    responses = RESPONSES[side]
                    if dname == "random response":
                        response, rc = responses[rng.below(3)], O.COMMITMENTS[rng.below(3)]
                    elif dname == "always bites":
                        response, rc = PAIRS[side][2], "MEDIUM"
                    elif dname == "always calls":
                        response, rc = PAIRS[side][3], "MEDIUM"
                    else:
                        response, rc = (O.TIMEOUT_FALLBACK["bottom" if side == "top" else "top"]), None
                        response, rc = response[0], response[1]
                    r = match.submit(opened["window_id"], opened["fighter_id"], action, response, commitment, rc, real)
                    feints += bool(real) and not r["error"]
                    if match.s["exit_destination"]:
                        exits_by_feint += bool(real) and not r["error"]
                        break
                label = match.s["exit_destination"] or "timeout"
                tally[label] += 1
            results[(aname, dname)] = (tally, feints, exits_by_feint, total_windows)
    rows = [["attacker", "defender", "games", "Side Control", "Open Guard", "Closed Guard", "timeout (60 windows)", "accepted feints", "exits ended by a feint"]]
    for (aname, dname), (tally, feints, by_feint, _) in results.items():
        rows.append([aname, dname, seeds, tally["Side Control"], tally["Open Guard"], tally["Closed Guard"], tally["timeout"], feints, by_feint])
    return table(rows)


def main():
    print("# Half Guard v0 feint measurements (oracle-computed; evidence only, not a balance claim)\n")
    print("## 1. One-exchange final grades (STRUCTURAL)\n" + one_exchange_tables())
    print("\n## 2. Does preparation create feint opportunities? (STRUCTURAL; 27 cells per row)\n" + opportunity_counts())
    print("\n## 3. Defender policies at the neutral state (STRUCTURAL)\n" + policy_table())
    print("\n## 4. Attacker stamina depletion (STRUCTURAL arithmetic)\n" + depletion())
    print("\n### Repeated feints driven through the oracle (STRUCTURAL sequence)\n" + self_defeating())
    print("\n## 5. Earliest exit windows over every attacker choice and commitment (STRUCTURAL breadth-first search over every attacker action, feint and commitment, 5 windows (the state space grows too fast for more), defender answers MEDIUM)\n" + reachability())
    print("\n## 6. Seeded policy populations (POPULATION evidence; 500 games x 60 windows per cell)\n" + population())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
