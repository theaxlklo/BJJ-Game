# Late Recovery / Match Pacing — Characterization and Proposed Decision

## Status

**CHARACTERIZATION ONLY — FROZEN AT ITS COMMITTING SHA — HARD STOP FOR REVIEW.**

Observer-only. Recovery rates, stamina costs, commitment behavior, D3-B, settlement, policy and defaults are all unchanged. No candidate has been designed, implemented or run, and nothing has been tuned.

```text
branch:              review/late-recovery-characterization
base (main):         f4b9c9e1ee24c648c14d584bcfc377f234bd851f
canonical policy:    PRODUCTION_STAMINA_RECOVERY_POLICY (unchanged; Rule 1 ON, Rule 2 OFF,
                     LOW while Exhausted, D3-B after the first clear)
frozen digest:       3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
observer:            src/bjj_game/diagnostics/late_recovery.py
evidence:            docs/evidence/late_recovery_characterization.json (per-match records included)
pinning tests:       tests/test_late_recovery_characterization.py
```

Reproduce:

```bash
PYTHONPATH=src python3 -m bjj_game.diagnostics.late_recovery
PYTHONPATH=src python3 -m unittest tests.test_late_recovery_characterization
```

**Population.** Canonical E-PROD (`canonical_kwargs`), seeds 42 and 142, 100 matches each, stalling OFF + shadow and ON. **OFF and ON are identical in every reported value**, so the tables show OFF.

**Integrity.**
- Every Bottom stamina change is attributed to a source (unexplained delta = 0 on all four runs).
- The observer is inert: full `BatchSummary` identity with an unobserved run, replay identity, and wrappers restored after normal exit and exceptions.
- It reproduces the frozen D3-B result (`1b96ffc`) for seed 42: 30 escapes, 65 timeouts, Tap 5, 45 clearing matches, first-clear median 240 s.

---

# 1. The four requested measures

| Measure | Seed 42 | Seed 142 |
|---|---|---|
| Matches where Bottom becomes Exhausted | 91 | 90 |
| Bottom first Exhausted entry (median; range) | **50 s** (40-60) | **50 s** (40-55) |
| Top first Exhausted entry (median; range) | 50 s (40-65) | 50 s (40-65) |
| Bottom stamina at first entry (median; range) | 23 (15-25) | 23 (16-25) |
| Matches with a first clear | 45 | 37 |
| **Time to first clear** (median; p10-p90; range) | **240 s**; 180-300; 140-300 | **240 s**; 190-290; 140-300 |
| First Exhausted episode length, clearing matches (median; range) | 185 s (80-255) | 195 s (85-255) |
| **Bottom time Exhausted**, share of all match time | **79.0%** | **79.5%** |
| **Match time left after first clear** (median; p90; max) | **20 s**; 110; 160 | **20 s**; 70; 120 |
| Bottom attempts after first clear: non-Exhausted MEDIUM / Exhausted LOW token | 97 / 33 | 78 / 20 |

**Terminal outcome by first-clear time:**

| First clear | Seed 42: escape / timeout / Tap | Seed 142: escape / timeout / Tap |
|---|---|---|
| Never Exhausted | 8 / 0 / 1 | 10 / 0 / 0 |
| Exhausted, never cleared | 8 / 34 / 4 | 5 / 44 / 4 |
| Cleared <= 150 s | 0 / 1 / 0 | 2 / 0 / 0 |
| Cleared 151-200 s | 7 / 4 / 0 | 4 / 1 / 0 |
| Cleared 201-250 s | 6 / 8 / 0 | 7 / 7 / 0 |
| Cleared 251-300 s | 1 / 18 / 0 | 3 / 13 / 0 |
| **Total** | **30 / 65 / 5** | **31 / 65 / 4** |

**Escapes by phase** (pooled, both seeds):
- 20 before the first Exhausted entry;
- 11 during the first Exhausted episode (all Exhausted LOW);
- 30 after the first clear (most of them non-Exhausted MEDIUM).

By commitment and state: MEDIUM / non-Exhausted 46; LOW / Exhausted 15.

---

# 2. Mechanism (exact accounting)

## 2.1 Opening sprint: 100 -> Exhausted in about 50 s

Bottom stamina spent from match start to the first Exhausted entry. Matches that become Exhausted; per 10 s of simulated time.

| Source | Seed 42 | Seed 142 | Share |
|---|---|---|---|
| Own MEDIUM initiations | 6.68 | 6.57 | ~42% |
| Responses to Top's MEDIUM attacks | 6.48 | 6.84 | ~42% |
| Provisional holds | 0.67 | 0.64 | ~4% |
| ESCAPE behavior | 2.00 | 2.00 | ~13% |
| **Total drain** | **15.8** | **16.0** | |

Top follows the same pattern (fixed MEDIUM attacks plus PRESSURE) and exhausts at the same median of 50 s. **From about 50 s onward the match is a mutually Exhausted state for most of its length.** The opening burn rate is about four times the best possible recovery rate (CONSERVE +4 per 10 s).

## 2.2 Recovery while Exhausted: about +0.45 per 10 s

First Exhausted episode (entry to clear, or to match end), per 10 s:

| Source | Seed 42 | Seed 142 |
|---|---|---|
| CONSERVE gain | **+4.00** | **+4.00** |
| Own LOW initiations (LOW_WHILE_EXHAUSTED, one per Bottom window) | **−2.85** | **−2.84** |
| Responses to funded Top attacks | −0.57 | −0.61 |
| Provisional holds | −0.13 | −0.13 |
| **Net** | **+0.45** | **+0.42** |

- **Bottom's own LOW initiations take back 71% of CONSERVE recovery.** This is the arithmetic of the adopted policy: +2 per 5 s versus −3 per 10 s Bottom window gives the +1 per 10 s sawtooth already recorded in the D2 history, before Top costs.
- Top is UNFUNDED on about 90% of its attacks during Bottom's episode (funded: 179/1,817 and 184/1,839). Rule 1 therefore makes most Top attacks free for Bottom; only about 10% cost anything.
- Entry is at a median of 23 stamina, and clearing needs 35. Twelve points at about +0.45 per 10 s takes about 270 s. That is why only about 41% of matches clear at all, and why the clearing median lands at 240 s.

## 2.3 What happens after the clear

The median match has **20 s** left after the first clear. That is about two Bottom decision windows. The post-clear MEDIUM windows are productive: 30 of 61 pooled escapes happen after the first clear. But a clear after 250 s almost never converts (4 escapes / 31 timeouts pooled).

## 2.4 Historical context (frozen evidence, not re-run)

The recovery-policy amendment (`docs/STAMINA_RECOVERY_POLICY_AMENDMENT_FIRST_MEASUREMENT.md`, BOTH settlement, Surface E) already showed this trade-off:

| Recovery initiation | Latch clears | Escapes | Timeouts |
|---|---|---|---|
| CURRENT (MEDIUM) | 0 | 20 | 75 |
| RESET_WHILE_EXHAUSTED | 234 | 72 | 23 |
| LOW_WHILE_EXHAUSTED | 67 | 51 | 44 |

LOW was adopted as the production answer. Slow recovery is its known price for keeping Bottom tactically active while Exhausted. RESET's alternative price is stalling exposure.

---

# 3. Findings

- **L1 — "Late recovery" is mostly "early exhaustion".** Both fighters exhaust at about 50 s because fixed MEDIUM commitment at a 10 s cadence burns about 16 stamina per 10 s against a maximum recovery of +4. The 240 s clear follows from a 50 s entry plus a slow, positive net recovery rate.
- **L2 — The slow recovery is the adopted LOW_WHILE_EXHAUSTED policy working as designed.** 71% of recovery is reinvested in LOW initiations, which produce 15 of 61 escapes (all LOW / Exhausted). Rule 1 already removes about 90% of Top-attack costs. Responder costs are not the bottleneck.
- **L3 — The game spends about 79% of match time with Bottom Exhausted.** Pacing is dominated by one long mutually Exhausted phase rather than repeated cycles.
- **L4 — Clear timing strongly predicts outcome.** Clears by 250 s convert to escapes about half the time; later clears almost never do.
- **L5 — The root driver is a placeholder.** Fixed MEDIUM initiation for both sides is the batch harness's baseline, not a tactical policy. Debt 5 (initiator tactical commitment selection) will replace exactly the input that sets the opening burn rate (about 42% of Bottom's opening spend is its own MEDIUM initiations, and another 42% answers Top's). Debt 4 (setup policy) also changes how many attacks are made.

---

# 4. Proposed decision (for review)

## LR-DEFER-TO-POLICY (recommended)

Record late recovery as **characterized, cause identified, decision deferred** until debts 4 and 5 (setup policy and tactical commitment selection) exist. Then re-measure with the same observer and the same frozen measures. No mechanics change now.

Reason: any pacing fix made today (recovery rate, LOW cost, CONSERVE rate, thresholds) would be tuned against the fixed-MEDIUM placeholder, which debt 5 is meant to replace. Tuning against it risks double-correcting once tactical commitment selection lowers the opening burn rate.

**Re-evaluation contract (frozen now, applied after debt 5):**

1. Re-run `late_recovery.characterize` on the then-canonical E-PROD (both seeds, OFF + shadow and ON).
2. Report the same table set as section 1, plus the opening and episode decompositions of section 2.
3. **Pacing questions to answer then** (thresholds deliberately not set now):
   - Bottom first-Exhausted median versus 50 s today.
   - Bottom Exhausted share versus 79% today.
   - Time left after the first clear versus 20 s today.
   - Escape/timeout split by first-clear bin.
4. If pacing still looks wrong at that point, a candidate slice gets its own preregistration, with gates fixed before any run.

**Closure gates for this outcome:**

| ID | Gate |
|---|---|
| LR-1 | Characterization reproduces exactly: the pinning test equals the committed evidence on all four runs; observer inert; unexplained delta 0. |
| LR-2 | No gameplay change: the only `src/` addition is the observer module; frozen digest exact; full suite, semantic checker and legacy entry point PASS; exact-head CI on Python 3.11 and 3.13. |
| LR-3 | `docs/PROJECT_PLAN_AND_STATUS.md` records debt 3 as characterized and deferred behind debts 4 and 5, with the re-evaluation contract. |

## LR-ACCEPT

Declare the current pacing intended as it is: a long mutually Exhausted mid-match with a late recovery window. Not recommended now, for the same placeholder reason.

## LR-CANDIDATE

Preregister a mechanics candidate now (for example, the LOW_WHILE_EXHAUSTED cadence or CONSERVE rate). Not recommended: it tunes against the fixed-MEDIUM baseline and would stack with debt 5 changes.

---

# 5. Known pre-existing test defect (blocks LR-2; not caused by this slice)

`tests/test_d3b_promotion_verification.py::test_pg8_nothing_bundled` fails on any full-history checkout of current `main`.

**Cause.** `d3b_promotion.pg8()` diffs the D3-B result `1b96ffc` against **`HEAD`**. It was meant as a one-time "nothing bundled into the promotion" check, but it now treats every later legitimate change as bundled. CI does not catch this, because its shallow checkout lacks `1b96ffc` and the test is skipped.

| PG8 endpoint | Unexpected paths |
|---|---|
| `0aa23db` (qualified promotion head) | none: PASS |
| `b59fc7f`, `1e2b5e3` | none: PASS |
| `cfdb08c` (R1 merge) | `src/bjj_game/diagnostics/r1_affordability.py` |
| `f4b9c9e` (current `main`) | + `.github/workflows/test.yml` |

The R1 slice's local full-suite run did not catch this, because it ran before the R1 files were committed (`HEAD` was still `1e2b5e3`).

This slice will add `src/bjj_game/diagnostics/late_recovery.py` to the list. The promotion evidence itself is unaffected: PG8 is exact at the promotion head.

**Proposed fix (separate maintenance slice, not done here):** pin PG8's endpoint to the qualified promotion head `0aa23db` instead of `HEAD`. Optionally, make CI fetch enough history that history-dependent tests run instead of being skipped. This changes a frozen promotion-verification test, so it needs its own authorization.

# 6. Hard-stop rules

Done in this slice: branch, observer-only module, pinning tests, evidence JSON, this document.

**Not authorized:** any outcome (DEFER-TO-POLICY, ACCEPT, CANDIDATE) until the user selects one at this exact SHA; any change to recovery rates, stamina costs, commitment behavior, D3-B, settlement, policy or defaults; any candidate implementation or run; tuning; merge; squash; force-push.

The status document is not edited in this slice. LR-3 is applied only after an outcome is selected.

**HARD STOP.**
