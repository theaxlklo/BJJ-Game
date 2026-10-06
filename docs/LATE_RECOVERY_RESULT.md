# Late Recovery / Match Pacing — Result

## Status

**OUTCOME = LR-DEFER-TO-POLICY. CHARACTERIZED — CAUSE IDENTIFIED — MECHANICS DECISION DEFERRED.**

This is a docs-only closure record. There are no gameplay, policy, settlement, stamina or default changes.

```text
frozen characterization checkpoint:  683e8302d248550f0e818cb9b70b5250d590912a
                                     docs/LATE_RECOVERY_CHARACTERIZATION.md (unchanged)
exact-head CI on 683e830:            run 37405624229 — PASS on Python 3.11 and 3.13
branch:                              review/late-recovery-characterization
main merged in:                      cfb360387852dc3c3e3eb7a962a676d97d20636e (PG8 endpoint pin)
frozen digest:                       3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

## Decision record

| Item | Decision |
|---|---|
| Outcome | **LR-DEFER-TO-POLICY** (selected by the user after reviewing `683e830`) |
| LR-ACCEPT | Not selected. Current pacing is **not** declared intended. |
| LR-CANDIDATE | Not selected. No recovery candidate is designed. |
| Recovery rates, stamina costs, thresholds, LOW cadence, D3-B, commitment behavior | **UNCHANGED** |
| Tuning | **None** |

## Current observations (frozen at `683e830`, canonical E-PROD)

```text
Bottom first Exhausted median:      50 s
Bottom Exhausted share:             ~79% of match time
first-clear median:                 240 s
median time remaining after clear:  20 s
```

## Reason for deferral

Current pacing is substantially driven by **fixed-MEDIUM commitment selection** and the **existing setup/attack policy**:

- The opening burns about 16 stamina per 10 s against a maximum recovery of +4. Bottom's own MEDIUM initiations account for about 42% of that burn, and answering Top's MEDIUM attacks for another 42%.
- Fixed MEDIUM is the batch harness's placeholder, which debt 5 replaces. Debt 4 changes attack frequency.

Tuning recovery now would correct against the placeholder and risk overcorrecting once those policies land.

## Re-evaluation contract (frozen in DoD section 4, applied later)

Re-evaluate only after:

1. the **setup-policy** debt (debt 4), and
2. the **tactical commitment-selection** debt (debt 5).

Then re-run `bjj_game.diagnostics.late_recovery` on the then-canonical E-PROD (both seeds, OFF + shadow and ON). Report the same measures and decompositions, and answer the pacing questions listed in the DoD. Any mechanics candidate then needs its own preregistration, with gates fixed before any run.

## Closure gates

| ID | Gate | Result |
|---|---|---|
| LR-1 | Characterization reproduces exactly; observer inert; unexplained delta 0 | **PASS** (`tests/test_late_recovery_characterization.py`; CI `37405624229`) |
| LR-2 | No gameplay change; digest exact; full suite, checker and legacy entry point PASS; exact-head CI 3.11 / 3.13 | Blocked at `683e830` only by the pre-existing PG8 defect. That defect is fixed on `main` (`5714748`, merged `cfb3603`) and merged into this branch. Final evidence: this branch's combined-state CI, including the full-history PG8 job. |
| LR-3 | Status document records debt 3 as characterized and deferred behind debts 4 and 5, with the re-evaluation contract | **PASS** (`docs/PROJECT_PLAN_AND_STATUS.md`) |

## Next

The next design debt is **setup policy** (debt 4), followed by **tactical commitment selection** (debt 5). After both, re-run the frozen late-recovery characterization. None of these is authorized by this record.

**HARD STOP.**
