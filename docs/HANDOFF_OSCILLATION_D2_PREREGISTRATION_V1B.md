# D2 Handoff-Oscillation Preregistration — Revision v1b (behavior-drain-aware)

## Status

**PROPOSED PREREGISTRATION REVISION — FROZEN AT ITS COMMITTING SHA — HARD STOP FOR REVIEW.**

This revision selects **POST-CLEAR RESERVE-AWARE HANDOFF v1b (behavior-drain-aware)** as the D2 candidate. It becomes binding only after the user reviews this exact SHA and explicitly authorizes D2 implementation and measurement. No D2 candidate, v1 or v1b, has been implemented or run.

It **supersedes v1 as the selected candidate**. It does not delete or rewrite earlier records:

```text
D1 evidence (unchanged):           cdb04a0c603dbfa1b2c9a41d66f877334a848869
v1 preregistration (unchanged):    62309599f955461fc29b60ee1c31b31eeb3008aa
                                   docs/HANDOFF_OSCILLATION_D2_PREREGISTRATION.md
adopted baseline (PR #10):         ee6cb6fcebb105e31224bead48a302811b27b59a
canonical policy:                  PRODUCTION_STAMINA_RECOVERY_POLICY (unchanged)
frozen digest:                     3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

Review record at `62309599`: accepted as D1 + v1 prereg evidence. v1 was **not selected**, because its own ledger note shows initiation-only reserve leaves a behavior-drain re-entry path:

```text
29 -> LOW (-3)    -> 26 -> ESCAPE (-1) -> 25 Exhausted
33 -> MEDIUM (-7) -> 26 -> ESCAPE (-1) -> 25 Exhausted
```

## Changes versus the v1 preregistration

| Item | v1 (`62309599`) | v1b (this revision) |
|---|---|---|
| Reserve-safe rule | `current - cost(c) > 25` | `current - cost(c) - behavior_reserve > 25`, with `behavior_reserve = 2` |
| Reserve-model integrity | — | Violations reported when actual intervening drain exceeds the reserved drain (criterion 15) |
| v1 vs v1b attribution | — | Every armed decision classified against the counterfactual v1 decision (criterion 15) |
| Criteria 1-14 | as frozen | Unchanged, except that wording now names v1b where it named v1 |

Scope, arming, decision order, RESERVE BLOCK semantics, sampling and all thresholds are identical to `62309599`.

---

# Selected candidate: POST-CLEAR RESERVE-AWARE HANDOFF v1b

## Scope (unchanged from v1)

- Bottom only, and only when `bottom_behavior_mode=RECOVER`. Inactive on Surfaces A and B, and Top is never affected.
- Rule 1 ON and Rule 2 OFF, as adopted. Response commitment selection, affordability, hold settlement and Recognition algorithms are unchanged.
- `StaminaPool` hysteresis (enter <=25, clear >=35), costs (LOW 3 / MEDIUM 7 / HIGH 12), behavior rates and recovery amounts are unchanged.
- While Bottom is Exhausted, adopted LOW_WHILE_EXHAUSTED is unchanged.
- Implemented as a new opt-in **diagnostic** recovery-initiation mode. Raw defaults and the canonical production policy are unchanged.

## Arming (unchanged from v1)

```text
post-clear armed = Bottom has made at least one
                   Exhausted -> non-Exhausted latch transition
                   earlier in the current match
```

It stays armed for the rest of the match and applies only at Bottom decision windows where Bottom is non-Exhausted. Before the first clear, Bottom behaves exactly as adopted. There is no timer and no counter.

## Behavior reserve (frozen constant)

```text
behavior_reserve = 2   (stamina points; fixed for this experiment)
```

Cadence rationale on the frozen E-PROD surface (interval 5 s, behavior quantum 5 s, Bottom ESCAPE -1 per quantum, initiative alternating Top/Bottom with one normal-speed advance before each normal decision window):

> Between the current Bottom initiation decision and Bottom's next normal initiation decision, two normal-speed advances can occur: one before Top's window and one before Bottom's next window. Each drains at most one ESCAPE quantum (-1). The maximum deterministic behavior drain before Bottom's next normal decision is therefore 2.

Frozen rules for the reserve:

1. The constant is **2**. Implementation code must not infer, compute or adapt a future drain.
2. A free-initiative Bottom decision (no advance before it) adds **no** extra reserve quantum; the reserve stays 2.
3. The reserve covers **behavior drain only**. It does not reserve responder commitment or hold liability. Rule 1 and Rule 2 are untouched.
4. If actual control flow produces more drain before Bottom's next decision than was reserved (for example more than two draining advances), instrumentation must report it as a **reserve-model violation** (criterion 15). The reserve must never be raised after seeing results.

## Reserve-safe rule (integer, deterministic)

```text
T_enter = pool.exhaustion_enter_threshold                (25 for maximum 100)
safe(c) = current_stamina - cost(c) - behavior_reserve > T_enter
```

The check uses current stamina at the Bottom decision, after that window's advance and the post-advance behavior re-choice, and before action selection.

## Bottom initiation decision while armed and non-Exhausted

```text
if safe(MEDIUM):   request MEDIUM (baseline), normal action selection
elif safe(LOW):    request LOW, normal action selection
else:              RESERVE BLOCK
```

The requested commitment feeds the existing pipeline unchanged: effective-commitment funding, Recognition read of the actual request, and response selection.

Worked boundaries (maximum 100):

```text
35 - 7 - 2 = 26 > 25  -> MEDIUM safe   (a clear at 35 returns MEDIUM immediately)
34 - 7 - 2 = 25       -> MEDIUM unsafe; 34 - 3 - 2 = 29 -> LOW
33 - 7 - 2 = 24       -> MEDIUM unsafe; 33 - 3 - 2 = 28 -> LOW
31 - 3 - 2 = 26 > 25  -> LOW safe
30 - 3 - 2 = 25       -> LOW unsafe -> RESERVE BLOCK
29 - 3 - 2 = 24       -> LOW unsafe -> RESERVE BLOCK
```

So MEDIUM requires stamina >=35, LOW (when MEDIUM is unsafe) requires >=31, and stamina <=30 blocks.

## RESERVE BLOCK (unchanged from v1)

When neither MEDIUM nor LOW is reserve-safe:

1. Bottom takes **no initiation spend** in that decision window. It uses the existing forced-recovery RESET path (`decision.action_id = None` -> `match.reset_window()`), the same mechanism RESET_WHILE_EXHAUSTED uses. It counts as a Bottom RESET and is evaluated by v0.3b stalling exactly as any RESET is.
2. Bottom uses **CONSERVE for the next actual advance**: a one-shot override of the RECOVER policy's pre-advance behavior choice for the next normal-speed interval only. After that advance, the existing post-advance re-choice applies the unchanged baseline rule before resolution. Free-initiative windows (no advance) do not consume the pending override.
3. The next Bottom decision window is re-evaluated from current stamina, with no persistent recovery state beyond the one-shot override.

Prohibited: timers, protected-action counters, a permanent LOW state, stamina grants, altered recovery amounts, any change to Top, and any change to responder settlement.

## Handoff definition for criterion 13

v1b has no separate recovery state. A clear at 35 gives `35 - 7 - 2 = 26 > 25`, so MEDIUM is safe, and the existing post-advance re-choice restores baseline behavior. **The policy handoff is the clear window.** If a clear window does not request MEDIUM, the handoff is the first later Bottom decision window that both runs baseline behavior and requests MEDIUM. Any re-entry before that return counts as a failed handoff.

## Pre-registration ledger note (prediction, not a result)

Hand ledger on the D1-traced path (unfunded Top, so no responder charge; alternating initiative), recorded before any run:

```text
+0   clear 33 -> 35; MEDIUM safe (26 > 25)  -> MEDIUM -7      -> 28
+5   ESCAPE -1                                                -> 27
+10  ESCAPE -1                                                -> 26
     decision: MEDIUM 17, LOW 21 -> RESERVE BLOCK (RESET)
+15  CONSERVE +2 (one-shot)                                   -> 28
+20  ESCAPE -1                                                -> 27; BLOCK
...  while blocked: +2 -1 = net +1 per 10 s; stamina rises 26 -> 31
     at 31 -> LOW (-3) -> 28 -> ESCAPE, ESCAPE -> 26 -> BLOCK again
     (closed cycle 26..31; 35 is never reached on this path)
```

Predictions recorded for later checking, not as results:

- **Initiation-driven and drain-driven re-entry are closed on this path.** Stamina floors at 26 between decisions, so criteria 9-10 are plausible.
- **v1b is likely to produce many RESERVE BLOCK RESETs.** After the clear-window MEDIUM, Bottom enters a closed block / LOW cycle: blocks at 26, 27, 28, 29 and 30 (net +1 per 10 s), LOW at 31, then two ESCAPE drains back to 26. That is five blocks per LOW, about 60 s per cycle. **On this path stamina never reaches 35, so MEDIUM never returns after the first block** unless something outside the traced path adds stamina.
- **Criterion 5 is at risk.** RESERVE BLOCK uses the same forced-RESET path as RESET_WHILE_EXHAUSTED, which produced **983** RESET-with-progress-route events under BOTH. The criterion-5 bound is **<=23** (adopted 13 + 10). Real v0.3b warnings are less likely, because interleaved LOW initiations engage progress (RESET+BOTH reached no warning), but this is not guaranteed.
- **Criterion 13 is likely satisfied at the clear window,** but criterion 14 will probably show long reserve-recovery times and many matches never requesting MEDIUM again after their first block.

This is recorded so that a v1b failure on criterion 5, or a pass-by-passivity pattern, cannot be reinterpreted afterwards. v1b is frozen as specified. A different fallback (one that does not RESET) would be a different candidate and need its own preregistration.

---

# Sampling and denominators (unchanged)

Run the exact two E-PROD batches, 100 each, base seeds 42 and 142, 300 s, with E-PROD settings and v1b enabled, both OFF + shadow and ON. Also run adopted-policy controls at the canonical checkpoint/settings. No adaptive extensions, seed replacement, tuning, or outcome exclusions.

- Evaluate both pooled episode results and first-clear-per-match results.
- A horizon admits an episode if re-entry occurs within the inclusive horizon or the episode is observed through the horizon. Otherwise it is right-censored.
- A successful escape before the horizon is censored for stamina survival and reported separately.
- No-clear matches and clears at timeout are never survival successes.
- Report each batch and pooled results, every failure, censored counts, all 5/10/15/20/30 s horizons, complete 10/20/30 spend/recovery histograms, first actions, first-clear times and repeated cycles.
- Keep the original adoption numbers beside the new results.

---

# A. Preservation (all mandatory; unchanged except the candidate name)

1. Surface A (original 100 seeds/settings) exactly preserves 78 Threat matches, 1,950 Threat entries and Tap 0. Surface B exactly preserves Tap 9/100. v1b must be inactive on non-RECOVER surfaces.
2. Rule 1: zero responder commitment **or hold** charged on unfunded initiator exchanges. Rule 2 stays OFF; charges, refunds and their semantics are unchanged.
3. Bottom stamina stays within [0,100], with no fabricated recovery and no negative costs. E-PROD original-100 final median >=29. Setup-builder availability is retained; report attempts, advances, completions and post-clear action distributions.
4. Original-100 E-PROD:
   - escapes >=25 (adopted 35 - 10);
   - Half Guard 16, Open Guard 10 and Reversal 9 each within +/-10;
   - timeouts <=70 (adopted 60 + 10);
   - **Tap <=9/100 (adopted E-PROD 5/100 + 4)**.

   These are pragmatic tolerances, not statistical equivalence claims.
5. RESET-with-progress-route exposure <=23/100 (adopted 13 + 10). No real warning, penalty or position reset in E-PROD. OFF/ON gameplay divergence 0/100 for both seed batches when no offense fires, using full gameplay identity. RESERVE BLOCK resets count toward this exposure; there is no carve-out.
6. Frozen Mount-v0 digest exactly `3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2`. Full unit suite, semantic checker and legacy entry point PASS. Supported-lane qualification comes from exact-head CI on Python 3.11 and 3.13; local system Python runs are supplementary. Deterministic replay of full gameplay traces, and observer ON/OFF full summary identity.
7. v1b settings must show effective-settings and full gameplay equivalence across their explicit diagnostic entry points. The existing canonical production entry point stays identical to the adopted controls and unchanged. Canonical integration needs separate authorization, and candidate equivalence must not be described as equality to unchanged adopted gameplay.
8. Preserve all historical evidence, including the failed first Gate G, old Rule 2, and the v1 preregistration. Report adoption A1-A10 and Gates A-H as historical results, not as proof that D2 passes.

# B. Absolute handoff stability (all mandatory; unchanged)

9. Rate of re-exhaustion within 10 s <=0.20, for both pooled episodes and the first-clear-per-match admissible sample.
10. Rate within 30 s <=0.35, for both denominators.
11. Each pooled denominator at both 10 s and 30 s must be >=43, including first-clear-per-match. Wilson bounds are reported descriptively only; no confidence-bound substitution for the frozen rates.
12. Anti-removal floors:
    - original-100 matches with >=1 clear: >=40 (adopted 45);
    - pooled matches with >=1 clear: >=75 (adopted 82);
    - first-clear median: <=250 s for original-100 and for pooled (adopted 240 s).

    Rates with inadequate samples remain OPEN, not PASS. Gate failures remain FAIL even if checker or unit tests PASS. No additional batch may rescue this experiment.
13. Policy handoff is the first post-clear decision window that actually restores both baseline behavior and a baseline MEDIUM request (see the v1b handoff definition above).
    - Require >=43 distinct pooled matches with such a return.
    - Require >=43 admissible first-return-per-match observations at both +10 s and +30 s.
    - Apply the same <=0.20 / <=0.35 re-entry limits from the return timestamp as well as from the latch clear.
    - A clear-to-return re-entry counts as a failed handoff and is never dropped in favor of healthier later returns.
    - Report return delays, pending-at-end states and all pre-return re-entries.
    - Inadequate return exposure is OPEN.
14. Reserve-block diagnostics (mandatory reporting; descriptive):
    - reserve-blocked Bottom decision opportunities (total, per match, and per armed match);
    - longest and distribution of consecutive blocked opportunities;
    - time in reserve recovery: simulated seconds from each block until the next funded Bottom initiation (or match end, reported as pending);
    - Bottom stamina at the first decision window where `safe(MEDIUM)` holds again after a block;
    - matches never returning to a MEDIUM request after their first block;
    - LOW requests made by the reserve rule (MEDIUM unsafe, LOW safe), separately from Exhausted LOW;
    - re-entries classified by cause (initiation spend, behavior drain, responder/hold spend).

# C. NEW reserve-model diagnostics (mandatory reporting; descriptive, not gates)

15. For every armed, non-Exhausted Bottom decision window, report:
    - **predicted behavior reserve** used (always 2);
    - **actual Bottom behavior drain** (sum of negative behavior stamina changes) between that decision and Bottom's next decision window, or match end, reported as truncated;
    - **reserve-model violations:** count and list of decisions where actual drain > reserved drain (2), with the control-flow sequence that produced them. Zero violations supports the cadence model; any violation is reported, not absorbed.
    - **v1-versus-v1b classification** of the counterfactual decision v1 would have made at the same state (reserve 0):

      ```text
      same decision
      v1 MEDIUM -> v1b LOW     (downgraded by behavior reserve)
      v1 MEDIUM -> v1b BLOCK   (blocked by behavior reserve)
      v1 LOW    -> v1b BLOCK   (blocked by behavior reserve)
      ```

      with counts per batch and pooled.

    These diagnostics are descriptive. They cannot PASS or FAIL D2, alter `behavior_reserve`, or authorize retuning.

# Decision and hard stops

All A and B criteria must pass for a D2 design-gate PASS. A candidate failing any criterion is recorded with exact SHA/settings, then STOP: no tuning and no silent criteria change. Missing evidence gives OPEN.

After this commit: HARD STOP for review of this exact SHA and explicit D2 authorization. After D2 evidence: HARD STOP again. Not authorized here: main changes, merges into main, squash, frontend work, canonical production-policy changes, Rule 2 work, or default changes.
