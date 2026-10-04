# D2 Handoff-Oscillation Preregistration (amended)

## Status

**PROPOSED PREREGISTRATION — FROZEN AT ITS COMMITTING SHA — HARD STOP FOR REVIEW.**

This document is the D2 experiment contract. Once the user reviews this exact SHA and explicitly authorizes D2, it becomes binding. Until then, no D2 candidate may be implemented or measured.

It **supersedes** the "Proposed frozen D2 DoD" section of
`docs/HANDOFF_OSCILLATION_CHARACTERIZATION_AND_DOD.md` at `cdb04a0c603dbfa1b2c9a41d66f877334a848869`. That document stays unchanged as D1 evidence. No D2 candidate has been implemented or run, so these amendments are preregistration work and not a post-measurement change.

```text
D1 evidence:          cdb04a0c603dbfa1b2c9a41d66f877334a848869 (branch review/handoff-oscillation-d1)
adopted baseline:     ee6cb6fcebb105e31224bead48a302811b27b59a (PR #10, unmerged)
canonical policy:     PRODUCTION_STAMINA_RECOVERY_POLICY (unchanged by D2)
frozen digest:        3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

## Amendments versus the cdb04a0 proposal

| # | cdb04a0 proposal | This preregistration |
|---|---|---|
| 1 | No candidate family selected | **Selected:** POST-CLEAR RESERVE-AWARE HANDOFF v1 (exact semantics below) |
| 2 | Criterion 4: "Tap <=9/100" (provenance ambiguous) | E-PROD original-100 Tap <=9/100, defined as **adopted E-PROD 5/100 + 4**. Surface B Tap stays exactly 9/100 under criterion 1. |
| 3 | Criterion 12: clearing matches >=45 / >=82; first-clear median <=240 s (zero margin) | Clearing matches **>=40** original-100 / **>=75** pooled; first-clear median **<=250 s** original-100 and pooled |
| 4 | — | **New criterion 14:** reserve-block diagnostics (mandatory reporting) |
| 5 | Criterion 13 | Retained unchanged in substance. Its application to v1 is made explicit. |

Not selected: reserve-to-60. Under CONSERVE + LOW, the D1 ledger nets about +1 per 10 s, so refilling 35 -> 60 takes about 250 s. With the adopted median first clear at 240 s of 300 s, that family would very likely fail criterion 13's return exposure by construction.

---

# Selected candidate: POST-CLEAR RESERVE-AWARE HANDOFF v1

## Scope

- Bottom only, and only when `bottom_behavior_mode=RECOVER`. It is inactive on every other surface (A, B), and Top is never affected.
- Rule 1 ON and Rule 2 OFF, exactly as adopted. Response commitment selection, affordability, hold settlement and Recognition algorithms are unchanged.
- `StaminaPool` hysteresis (enter <=25, clear >=35), all costs (LOW 3 / MEDIUM 7 / HIGH 12), behavior rates and recovery amounts are unchanged.
- While Bottom is Exhausted, the adopted LOW_WHILE_EXHAUSTED behavior is unchanged (CONSERVE + LOW initiation).
- It is implemented as a new opt-in **diagnostic** recovery-initiation mode. Raw defaults and the canonical production policy are unchanged. Canonical integration would need separate authorization.

## Arming

```text
post-clear armed = Bottom has made at least one
                   Exhausted -> non-Exhausted latch transition
                   earlier in the current match
```

Once armed, it stays armed for the rest of the match. It applies only at Bottom decision windows where Bottom is **non-Exhausted**. Before the first clear, Bottom behaves exactly as adopted. There is no timer and no action counter.

## Reserve-safe rule (integer, deterministic)

```text
T_enter = pool.exhaustion_enter_threshold        (25 for maximum 100)
safe(c) = current_stamina - cost(c) > T_enter
```

An initiation is unsafe if paying its cost would leave Bottom at or below 25. The check uses current stamina at the moment of the Bottom decision, after that window's advance and the post-advance behavior re-choice, and before action selection.

## Bottom initiation decision while armed and non-Exhausted

```text
if safe(MEDIUM):   request MEDIUM (baseline), normal action selection
elif safe(LOW):    request LOW, normal action selection
else:              RESERVE BLOCK
```

The requested commitment feeds the existing pipeline unchanged: effective-commitment funding, Recognition read of the actual request, and response selection.

## RESERVE BLOCK (frozen fallback)

When neither MEDIUM nor LOW is reserve-safe:

1. Bottom takes **no initiation spend** in that decision window. It uses the existing forced-recovery RESET path (`decision.action_id = None` -> `match.reset_window()`), the same mechanism RESET_WHILE_EXHAUSTED uses. The RESET is counted as a Bottom RESET and evaluated by v0.3b stalling exactly as any RESET is (real offenses possible when stalling is ON; shadow-evaluated when OFF + shadow).
2. Bottom uses **CONSERVE for the next advance**. A one-shot override replaces the RECOVER policy's pre-advance behavior choice for the next normal-speed interval only. After that advance, the existing post-advance re-choice applies the unchanged baseline rule (ESCAPE when non-Exhausted, CONSERVE when Exhausted) before resolution. If the next window is a free-initiative window (no advance), the override stays pending until the next advance.
3. At the next Bottom decision window, everything is re-evaluated from current stamina. There is no persistent recovery state beyond the one-shot override.

Prohibited by construction: timers, protected-action counters, a permanent LOW state, stamina grants, altered recovery amounts, any change to Top, and any change to responder settlement.

## Handoff definition for criterion 13

v1 has no separate recovery state. At the clear window the baseline behavior is restored (by the existing post-advance re-choice) and MEDIUM is requested whenever `safe(MEDIUM)` holds. A clear at 35 gives 35 - 7 = 28 > 25, so it is safe. **The policy handoff is the clear window**, as criterion 13 already specifies for policies without a separate recovery state. If a clear window does not request MEDIUM (unsafe, or no Bottom decision before the next advance), the handoff is the first later Bottom decision window that both runs baseline behavior and requests MEDIUM. Any re-entry before that return counts as a failed handoff.

## Pre-registration ledger note (prediction, not a result)

From the D1 ledger, the reserve-safe check covers the **initiation** cost only. It does not reserve the ESCAPE drain before the next Bottom decision (-1 per advance; two advances separate Bottom decisions when initiative alternates). The traced paths below therefore still re-enter through behavior drain, not initiation:

```text
29 -> LOW (-3)    -> 26 -> ESCAPE (-1) -> 25  Exhausted
33 -> MEDIUM (-7) -> 26 -> ESCAPE (-1) -> 25  Exhausted
```

This is recorded before any candidate run so that a possible v1 failure on criteria 9-10 cannot be reinterpreted afterwards. v1 is frozen as specified. A variant that reserves the expected drain would be a different candidate and need its own preregistration.

---

# Sampling and denominators (unchanged from cdb04a0)

Run the exact two E-PROD batches, 100 each, base seeds 42 and 142, 300 s, with E-PROD settings and v1 enabled, both OFF + shadow and ON. Also run adopted-policy controls at the canonical checkpoint/settings. No adaptive extensions, seed replacement, tuning, or outcome exclusions.

- Evaluate both pooled episode results and first-clear-per-match results.
- A horizon admits an episode if re-entry occurs within the inclusive horizon or the episode is observed through the horizon. Otherwise it is right-censored.
- A successful escape before the horizon is censored for stamina survival and reported separately.
- No-clear matches and clears at timeout are never survival successes.
- Report each batch and pooled results, every failure, censored counts, all 5/10/15/20/30 s horizons, complete 10/20/30 spend/recovery histograms, first actions, first-clear times and repeated cycles.
- Keep the original adoption numbers beside the new results.

---

# A. Preservation (all mandatory)

1. Surface A (original 100 seeds/settings) exactly preserves 78 Threat matches, 1,950 Threat entries and Tap 0. Surface B exactly preserves Tap 9/100. v1 must be inactive on non-RECOVER surfaces.
2. Rule 1: zero responder commitment **or hold** charged on unfunded initiator exchanges. Rule 2 stays OFF; charges, refunds and their semantics are unchanged.
3. Bottom stamina stays within [0,100], with no fabricated recovery and no negative costs. E-PROD original-100 final median >=29. Setup-builder availability is retained; report attempts, advances, completions and post-clear action distributions.
4. Original-100 E-PROD:
   - escapes >=25 (adopted 35 - 10);
   - Half Guard 16, Open Guard 10 and Reversal 9 each within +/-10;
   - timeouts <=70 (adopted 60 + 10);
   - **Tap <=9/100 (adopted E-PROD 5/100 + 4)**.

   These are pragmatic tolerances, not statistical equivalence claims.
5. RESET-with-progress-route exposure <=23/100 (adopted 13 + 10). No real warning, penalty or position reset in E-PROD. OFF/ON gameplay divergence 0/100 for both seed batches when no offense fires, using full gameplay identity. RESET BLOCK resets count toward this exposure; there is no carve-out.
6. Frozen Mount-v0 digest exactly `3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2`. Full unit suite, semantic checker and legacy entry point PASS. Supported-lane qualification comes from exact-head CI on Python 3.11 and 3.13; local system Python runs are supplementary. Deterministic replay of full gameplay traces, and observer ON/OFF full summary identity.
7. v1 settings must show effective-settings and full gameplay equivalence across their explicit diagnostic entry points. The existing canonical production entry point stays identical to the adopted controls and unchanged. Canonical integration needs separate authorization, and candidate equivalence must not be described as equality to unchanged adopted gameplay.
8. Preserve all historical evidence, including the failed first Gate G and old Rule 2. Report adoption A1-A10 and Gates A-H as historical results, not as proof that D2 passes.

# B. Absolute handoff stability (all mandatory)

9. **NEW:** rate of re-exhaustion within 10 s <=0.20, for both pooled episodes and the first-clear-per-match admissible sample.
10. **NEW:** rate within 30 s <=0.35, for both denominators.
11. Each pooled denominator at both 10 s and 30 s must be >=43, including first-clear-per-match. Wilson bounds are reported descriptively only; no confidence-bound substitution for the frozen rates.
12. **AMENDED anti-removal floors:**
    - original-100 matches with >=1 clear: **>=40** (adopted 45);
    - pooled matches with >=1 clear: **>=75** (adopted 45 + 37 = 82);
    - first-clear time median: **<=250 s** for original-100 and for pooled (adopted 240 s).

    Rates with inadequate samples remain OPEN, not PASS. Gate failures remain FAIL even if checker or unit tests PASS. No additional batch may rescue this experiment.
13. Policy handoff is the first post-clear decision window that actually restores both baseline behavior and a baseline MEDIUM request (see the v1 handoff definition above).
    - Require >=43 distinct pooled matches with such a return.
    - Require >=43 admissible first-return-per-match observations at both +10 s and +30 s.
    - Apply the same <=0.20 / <=0.35 re-entry limits from the return timestamp as well as from the latch clear.
    - A clear-to-return re-entry counts as a failed handoff and is never dropped in favor of healthier later returns.
    - Report return delays, pending-at-end states and all pre-return re-entries.
    - Inadequate return exposure is OPEN.
14. **NEW, reserve-block diagnostics (mandatory reporting; descriptive, not separate pass/fail):**
    - reserve-blocked Bottom decision opportunities (total, per match, and per armed match);
    - longest and distribution of consecutive blocked opportunities;
    - time in reserve recovery: simulated seconds from each block until the next funded Bottom initiation (or match end, reported as pending);
    - Bottom stamina at the first decision window where `safe(MEDIUM)` holds again after a block;
    - matches never returning to a MEDIUM request after their first block;
    - LOW requests made by the reserve rule (MEDIUM unsafe, LOW safe), separately from Exhausted LOW;
    - re-entries classified by cause (initiation spend, behavior drain, responder/hold spend), so the ledger-note prediction can be checked.

    A candidate that stabilizes stamina by becoming excessively passive will show it here, and criterion 13 will make it OPEN/FAIL.

# Decision and hard stops

All A and B criteria must pass for a D2 design-gate PASS. A candidate failing any criterion is recorded with exact SHA/settings, then STOP: no tuning and no silent criteria change. Missing evidence gives OPEN.

After this commit: HARD STOP for review of this exact SHA and explicit D2 authorization. After D2 evidence: HARD STOP again. Not authorized here: main changes, merges into main, squash, frontend work, canonical production-policy changes, or default changes.
