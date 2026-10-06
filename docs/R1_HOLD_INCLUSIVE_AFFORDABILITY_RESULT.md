# R1 — Response Commitment / Provisional-Hold Affordability: Result

## Status

**R1 OUTCOME = CLOSE. R1 CLOSED BY CHARACTERIZATION.**

This is a docs-only closure record. There are no gameplay, test, policy, settlement or default changes.

```text
frozen characterization / DoD checkpoint:  a2e288742bd8763a5ce7f2323ab7493fe28c880d
                                           docs/R1_HOLD_INCLUSIVE_AFFORDABILITY_DOD.md (unchanged)
exact-head CI on a2e2887:                  run 37382027293 — PASS on Python 3.11 and 3.13
branch:                                    review/r1-hold-inclusive-affordability
base (main):                               1e2b5e3ffbf6f8a8051775d48c20063cc3abdedd
frozen digest:                             3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

## Decision record

| Item | Decision |
|---|---|
| R1 outcome | **CLOSE** (selected by the user after reviewing `a2e2887`) |
| H1 (downgrade only without defensive loss) | **NOT IMPLEMENTED.** Provably inert on the frozen production surfaces: 0 free downgrades on A-PROD, B-PROD and E-PROD 42 / 142. |
| H2 (downgrade at the cost of the hold) | **REJECTED FOR R1.** See below. |
| Settlement | **UNCHANGED.** Response commitment + provisional hold remain additive (semantics A). |
| Hold | **BEST-EFFORT LOW = 3.** |
| Rule 1 | **UNCHANGED / ON.** |
| Rule 2 | **OFF.** Semantics B remains rejected (public-MATCH Threat 78/100 -> 0/100). |
| Gameplay | **NO CHANGE.** |
| Hypothesis | **NOT ADDED** in this slice. The allowed and forbidden properties stay as frozen in DoD section 6. |
| `ResponderSettlementPlan` | **DEFERRED** (to debt 7 or a dedicated non-gameplay refactor slice). |

## Frozen production semantics

```text
The responder chooses a commitment for the exchange.
The exchange resolves.
If the result creates a provisional Contested hold:
    the responder pays the separate LOW = 3 hold burden on a best-effort basis.
If only 0, 1 or 2 stamina remain:
    the responder pays what remains;
    the already-earned Contested result is not revoked.
Rule 1 still overrides:
    UNFUNDED initiator -> zero response and hold burden.
```

This is a coherent mechanic, not an accounting bug. The E-PROD "179" counts how often semantics A applies. It is not a defect count.

## H2 — rejected for R1

```text
H2 intentionally converts some Contested defenses into attacker Success
when the responder cannot reserve enough stamina for the following hold.

That is a submission-pressure / balance mechanic, not an affordability
correctness fix.

It would alter the frozen A-PROD control: 78 affected decisions, one in
each of the existing 78 Threat matches.

No evidence currently justifies that balance change.
```

H2 is not forbidden permanently. If later playtesting concludes that a defender who spends all remaining stamina defending should not survive the lock without paying the full hold, that becomes a **new submission-design slice** with its own preregistration and gates. It is not part of R1.

## Evidence summary (from `a2e2887`; authoritative in the DoD and evidence JSON)

- The historical 1,366 mismatch reproduces exactly on the pre-change configuration. Rule 1 alone removes 1,362 of them.
- Canonical production mismatch: E-PROD 0 / 2, B-PROD 6, A-PROD 78 (A-PROD: one per Threat match, responder at exactly 7 stamina).
- A hold shortfall has no mechanical consequence. Resolution is fixed before stamina is charged.
- No free hold-aware downgrade exists. Every available lower commitment turns the predicted Contested into a Top Success.
- Recognition makes projected affordability noisy. About 170-180 FINISH decisions per Recognition surface perceive a funded initiator whose hold Rule 1 will actually waive.
- The observer is inert (full `BatchSummary` identity, replay identity, restored after normal exit and exceptions).

## Closure gates

| ID | Gate | Result |
|---|---|---|
| C1 | R-P1 to R-P6 | **PASS.** No settlement, policy or default change; Rule 1 exact; Rule 2 OFF; A-PROD 78 / 1,950 / Tap 0; B-PROD Tap 9; digest exact; exact-head CI 3.11 / 3.13 green; historical evidence preserved. |
| C2 | Characterization reproduces exactly; observer inert | **PASS** (`tests/test_r1_affordability_characterization.py`). |
| C3 | Production gameplay unchanged | **PASS.** The only `src/` addition is the observer module; all existing pinned tests green (508 tests). |
| C4 | Docs: debt renamed; best-effort semantics recorded; debt 7 carries the projected-burden requirement | **PASS** (this record + `docs/PROJECT_PLAN_AND_STATUS.md`, debt 7). |

## Requirement transferred to debt 7 (player-facing contract)

```text
The player-facing contract must expose the response-specific projected burden
on hold-eligible response windows:

    response effective commitment cost
    + 3 when the selected response is predicted Contested and the
      initiator appears funded from responder-visible information.

This is advisory and read-only.
Actual engine settlement remains authoritative and may differ, because
Recognition can be wrong and Rule 1 uses the true funding state.
The projected burden must never be presented as a guaranteed actual cost.
```

## Next

The next slice is **late recovery / match-pacing characterization**, as planned. It is not authorized by this record.

**HARD STOP.**
