# D2 Handoff-Oscillation Preregistration — Revision v1d (recovery hold until MEDIUM is reserve-safe)

## Status

**PROPOSED PREREGISTRATION REVISION — FROZEN AT ITS COMMITTING SHA — HARD STOP FOR REVIEW.**

This revision selects **POST-CLEAR RESERVE-AWARE HANDOFF v1d (recovery hold until MEDIUM is reserve-safe)** as the D2 candidate. It becomes binding only after the user reviews this exact SHA and explicitly authorizes D2 implementation and measurement. No D2 candidate (v1, v1b, v1c or v1d) has been implemented or run.

It **supersedes v1c only as the selected future candidate**. v1c stays on record, unchanged, as historical preregistration evidence, and so do all earlier records:

```text
D1 evidence (unchanged):          cdb04a0c603dbfa1b2c9a41d66f877334a848869
v1 preregistration (unchanged):   62309599f955461fc29b60ee1c31b31eeb3008aa
v1b preregistration (unchanged):  f624db2cc3753f93b4f4f2bbc7d1e4d5b02057dc
v1c preregistration (unchanged):  f30ace90c20df9d901ca6370e0acd4c3a8caa2c5
                                  docs/HANDOFF_OSCILLATION_D2_PREREGISTRATION_V1C.md
plan/status at v1c review:        9c7d2f8ef4a997fbfd9bd5a0bc1ab9cf1a0c8383
adopted baseline (PR #10):        ee6cb6fcebb105e31224bead48a302811b27b59a
canonical policy:                 PRODUCTION_STAMINA_RECOVERY_POLICY (unchanged)
frozen digest:                    3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

Review record at `9c7d2f8`: v1c accepted as preregistration evidence. A v1c run was **not authorized**. The v1c ledger note predicted a closed 26..31 sawtooth: the hold recovers +1 per 10 s, LOW becomes reserve-safe at 31, LOW costs 3 and two ESCAPE quanta return Bottom to 26. On that path v1c never returns to MEDIUM after its first hold.

Design lineage, all decided before any candidate measurement:

```text
D1  cdb04a0  oscillation characterized: 35 -> 28 -> 27 -> 26 -> 19
v1  6230959  initiation-only reserve; predicted behavior-drain re-entry
v1b f624db2  + behavior reserve 2; predicted RESET spam vs criterion 5
v1c f30ace9  + non-RESET recovery hold; predicted 26..31 LOW sawtooth, no MEDIUM return
v1d (this)   + hold persists as a mode; only reserve-safe MEDIUM releases it
```

## Changes versus v1c

| Item | v1c (`f30ace9`) | v1d (this revision) |
|---|---|---|
| Reserve-safe rule | `stamina - cost(c) - 2 > 25` | **unchanged** |
| Decision outside recovery-hold mode | MEDIUM if safe, else LOW if safe, else HOLD | **unchanged**; the HOLD branch also **enters recovery-hold mode** |
| Decision inside recovery-hold mode | (no mode; every window re-evaluated) | **HOLD unless `safe(MEDIUM)`**. LOW is never requested in mode, even when LOW is reserve-safe |
| Release | none; LOW at 31 ends each hold run | **only `safe(MEDIUM)`** (stamina >= 35 at current values), or re-exhaustion, or match end |
| Hold transition | `MountMatch.recovery_hold()` | **identical semantics**, unchanged |
| CONSERVE override | one-shot per hold | **unchanged**: one-shot per hold, re-armed by each hold |
| Persistent state | none beyond the one-shot override | one per-match boolean, `recovery_hold_mode`, owned by the batch-side diagnostic mode |
| Criteria 1-14 | as frozen | unchanged in substance; textual clarifications only (listed below) |
| Diagnostics | 15 and 15b | 15 and 15b kept; **15c (release diagnostics) added**; 15 attribution extended to v1c |

Frozen constants (unchanged; listed so that no silent change is possible):

```text
behavior_reserve           = 2
cost(LOW)                  = 3
cost(MEDIUM)               = 7
exhaustion_enter_threshold = 25   (StaminaPool, maximum 100)
exhaustion_clear_threshold = 35   (StaminaPool, maximum 100)
recovery amount            = CONSERVE +2 per 5 s behavior quantum (unchanged)
behavior drain             = Bottom ESCAPE -1 per 5 s behavior quantum (unchanged)
Rule 1                     = ON
Rule 2                     = OFF
```

---

# Engine inspection (inherited from v1c; re-confirmed at `9c7d2f8`)

1. Initiative turns over only in `MountMatch._apply_resolution()` (after an attempt with no exit) and `MountMatch.reset_window()`. There is no existing "decline without RESET" transition, so v1d reuses the v1c-specified `MountMatch.recovery_hold()`.
2. `reset_window()` carries RESET and stalling semantics a hold must not inherit.
3. The simulated clock moves only in `advance()`/`drift()`.
4. On the v0.2 setup path (E-PROD), the initiation decision happens before any Recognition or response-commitment RNG draw. A window that ends without an attempt consumes no RNG.
5. `StallingTracker` keeps per-side clocks. They advance with simulated time in `advance()`. A side's clock is zeroed when that side engages, and when the opponent's attempt marks it as an engaged defender (`_record_engagement(..., defender_engaged=True)`). It is also zeroed by an evaluated offense in `evaluate_reset()`.
6. The batch loop consumes a pending free-initiative window before the decision. On a normal window it chooses behavior, runs `advance()`, then re-chooses behavior (`AdaptiveBehaviorPolicy.choose`) before resolution. Non-Exhausted RECOVER Bottom re-chooses its baseline ESCAPE. Exhausted Bottom chooses CONSERVE.

---

# Selected candidate: POST-CLEAR RESERVE-AWARE HANDOFF v1d

## Scope and arming (unchanged from v1c)

- Bottom only, and only when `bottom_behavior_mode=RECOVER` **and** v0.2 setup ordering is enabled (as on E-PROD). Any other configuration that requests v1d is rejected. v1d is inactive on Surfaces A and B, and Top is never affected.
- Rule 1 ON and Rule 2 OFF, as adopted. Response selection, affordability, provisional-hold settlement, Recognition algorithms, costs, behavior rates, recovery amounts and the 25/35 hysteresis are unchanged. Adopted LOW_WHILE_EXHAUSTED is unchanged while Bottom is Exhausted.
- **Armed** after Bottom's first Exhausted -> non-Exhausted latch clear in the match, for the rest of the match. v1d acts only at **non-Exhausted Bottom decision windows** of an armed match.
- **Before the first clear, gameplay is identical to the adopted policy.** v1d holds no state and makes no decision there.
- Implemented as a new opt-in **diagnostic** recovery-initiation mode. Raw defaults and the canonical production policy are unchanged.

## Reserve-safe rule (unchanged)

```text
safe(c) = current_stamina - cost(c) - behavior_reserve > exhaustion_enter_threshold
```

It is evaluated on current stamina at the Bottom decision window: after that window's advance (if any) and the post-advance behavior re-choice, and before action selection. The same timing applies to entry and release.

Current values:

```text
safe(MEDIUM) <=> stamina - 7 - 2 > 25 <=> stamina >= 35
safe(LOW)    <=> stamina - 3 - 2 > 25 <=> stamina >= 31
```

The release threshold of 35 equals the latch clear threshold for these values. **This equality is arithmetic, not a rule.** The release is defined by `safe(MEDIUM)`, never by the latch.

## State

Per match, owned by the batch-side v1d diagnostic mode (not by `MountMatch`, `StaminaPool` or `AdaptiveBehaviorPolicy`):

```text
recovery_hold_mode : bool   initially False
pending_conserve   : bool   initially False   (the v1c one-shot override)
```

Both are created False at match start and discarded at match end. Neither is a timer or a counter. Neither carries over between matches.

## Decision at an armed Bottom decision window

```text
if Bottom is Exhausted:
    recovery_hold_mode := False          (if it was True: record CLEARED_BY_EXHAUSTION)
    adopted LOW_WHILE_EXHAUSTED decision, unchanged

elif recovery_hold_mode:
    if safe(MEDIUM):
        recovery_hold_mode := False      (record RELEASE)
        ordinary decision in this same window (see below)
    else:
        RECOVERY HOLD                    (LOW is not considered)

else:                                    (ordinary decision)
    if safe(MEDIUM):   request MEDIUM, normal action selection
    elif safe(LOW):    request LOW, normal action selection
    else:
        recovery_hold_mode := True       (record ENTER)
        RECOVERY HOLD
```

"Normal action selection" means the existing `policy.choose(match)` with the requested commitment fed into the unchanged pipeline (effective-commitment funding, Recognition read of the actual request, response selection). If `policy.choose` returns no action, that is a **genuine policy RESET** through `reset_window()`. It is counted and stalling-evaluated like any RESET, and it does **not** enter recovery-hold mode. Only the reserve rule enters the mode.

### Entry (frozen)

Recovery-hold mode is entered exactly when all of the following hold at a Bottom decision window:

- Bottom side, RECOVER mode, v0.2 setup ordering, Rule 1 ON, Rule 2 OFF;
- the match is armed (Bottom has cleared Exhausted earlier in this match);
- Bottom is not Exhausted;
- recovery-hold mode is not already active;
- the ordinary reserve-aware decision finds **neither MEDIUM nor LOW reserve-safe** (current values: stamina <= 30).

The entry window itself is a hold.

The ordinary decision outside the mode is exactly the v1c decision. A reserve-rule LOW request (MEDIUM unsafe, LOW safe, mode inactive) therefore stays possible at stamina 31-34. It is reported separately (15c). It does not enter the mode.

### Recovery-hold state (frozen)

| Aspect | Frozen behavior |
|---|---|
| Persistence across initiative changes | **Persists.** Top windows neither read nor change the mode. Each hold passes initiative to Top, and the mode is still active at Bottom's next window. |
| Persistence across free initiative | **Persists.** A Bottom free-initiative window in mode is evaluated exactly like a normal Bottom window (release check, otherwise hold). The free window is consumed (already done at loop start), and initiative passes to Top. A Top free-initiative window does not touch the mode. |
| Clock | A hold consumes **no** simulated time. The mode has **no timer**. Simulated time advances only in normal `advance()` calls. |
| Initiative turnover | Every hold passes initiative normally: `initiator = initiator.opponent`. Initiative is never retained. |
| CONSERVE behavior | **One-shot per hold** (v1c semantics, unchanged). A hold sets `pending_conserve := True`. The next actual `advance()` uses Bottom CONSERVE in place of the RECOVER pre-advance choice, then clears `pending_conserve`. The existing post-advance re-choice then restores the baseline rule (ESCAPE while non-Exhausted). The following advance, before Bottom's next window, uses the unchanged RECOVER choice. `pending_conserve` is a boolean: holds do not stack, and a second hold before an advance leaves it True. Free-initiative windows (no advance) do not consume it. **CONSERVE is not persistent across the whole mode.** A persistent-CONSERVE variant would be a different candidate (see predictions). |
| `AdaptiveBehaviorPolicy` | Unchanged and not subclassed. The v1d mode applies the one-shot override around it, at the pre-advance choice only. When Bottom is Exhausted, the latch-keyed CONSERVE applies as adopted. A pending override that coincides with Exhausted is behaviorally identical, and it is still consumed by that advance. |
| v0.3b stalling | A hold calls neither `reset_window()` nor `evaluate_reset()`, records no progress opportunity, and engages no side. The stalling clocks are neither zeroed nor evaluated by a hold. They advance with simulated time and are zeroed only by the existing engagement and offense rules (inspection item 5). A later genuine RESET is evaluated with whatever clock has accumulated. |
| Shadow stalling (OFF + shadow) | The recovery-policy collector's shadow tracker is **not** evaluated for a hold. Holds are recorded as hold events, never as shadow RESETs. |
| RESET | **No RESET semantics.** A hold does not append `reset_window_history` and does not count toward Bottom RESET totals or RESET-with-progress-route exposure. |
| Setup | No setup event: `setup_state` is untouched, with no build, advance, Ready or consumption. |
| Submission | No submission event; submission state untouched. |
| Recognition / responder | No Recognition read and no response selection on a hold. Under v0.2 ordering, the hold replaces the decision before any RNG draw, so **no RNG is consumed**. Top's own windows during the mode are unchanged. Bottom responds to Top's attempts exactly as adopted, including any funded response or provisional-hold charge. |
| Stamina | A hold spends and grants nothing. The mode changes stamina only through the one-shot CONSERVE behavior choice, whose recovery amount is unchanged. |
| History | Each hold appends `"{side}@{elapsed}s:stamina={current}"` to `RunHistory.recovery_hold_history` (v1c field, unchanged). Mode transitions (`ENTER`, `RELEASE`, `CLEARED_BY_EXHAUSTION`, `PENDING_AT_END`, each with elapsed seconds and stamina) are recorded by the batch-side v1d collector. Neither appears on any non-v1d run. |
| Observers | The A9 handoff observer samples exactly as adopted. A hold mutates no stamina and no latch, so the Case-A sampling proof is unaffected. Any v1d collector is read-only, consumes no RNG and mutates no engine state. Observer ON/OFF full-summary identity is required (criterion 6). |
| Match end / exit | Any terminal event (escape/exit, submission, timeout) ends the mode. If the mode was active, `PENDING_AT_END` is recorded and the episode is reported as pending, never as a release. Both state booleans are discarded with the match. |

### Release (frozen)

```text
release only when safe(MEDIUM):
    current_stamina - cost(MEDIUM) - behavior_reserve > exhaustion_enter_threshold
    current values: stamina - 7 - 2 > 25  <=>  stamina >= 35
```

- The release check runs only at **Bottom decision windows** (normal or free). It does not run at Top windows or inside an advance.
- **LOW never releases the mode**, including when `safe(LOW)` holds (31-34).
- On release, the same window runs the ordinary decision. Since `safe(MEDIUM)` holds, it requests MEDIUM with normal action selection. If `policy.choose` returns no action, that is a genuine policy RESET (counted, stalling-evaluated, no carve-out), and the mode stays released.
- The mode also ends, without release, on re-exhaustion (`CLEARED_BY_EXHAUSTION`) or match end (`PENDING_AT_END`). After a re-exhaustion and a later clear, a new entry needs a new unsafe ordinary decision. Each entry starts a new **recovery-hold cycle**.

Prohibited: timers, protected-action counters, a permanent LOW state, LOW requests in the mode, stamina grants, altered recovery amounts or drains, persistent CONSERVE, any change to Top, any change to responder or provisional-hold settlement, and any routing of holds through RESET or stalling machinery.

`MountMatch.recovery_hold()` is opt-in engine surface used only by the v1d diagnostic mode, with exactly the v1c semantics. Existing call paths never invoke it.

## Handoff definition for criterion 13 (unchanged)

A clear at 35 gives `35 - 7 - 2 = 26 > 25`, so MEDIUM is requested at the clear window and baseline behavior is restored by the post-advance re-choice. **The policy handoff is the clear window.** Otherwise it is the first later Bottom decision window that both runs baseline behavior and requests MEDIUM. Any re-entry before that return counts as a failed handoff.

A post-hold **release** is a separate event, reported in 15c. It does not redefine the criterion-13 handoff.

## Pre-registration ledger note (prediction, not a result)

Traced path (unfunded Top, alternating initiative, no free windows), recorded before any run:

```text
+0    clear 33 -> 35; MEDIUM safe (26 > 25) -> MEDIUM -7      -> 28
+5    ESCAPE -1                                               -> 27   (Top window)
+10   ESCAPE -1                                               -> 26   MEDIUM 17, LOW 21: ENTER mode, HOLD 1
+15   CONSERVE +2 (one-shot)                                  -> 28   (Top window)
+20   ESCAPE -1                                               -> 27   HOLD 2
+30                                                           -> 28   HOLD 3
+40                                                           -> 29   HOLD 4
+50                                                           -> 30   HOLD 5
+60                                                           -> 31   HOLD 6  (v1c would play LOW here)
+70                                                           -> 32   HOLD 7
+80                                                           -> 33   HOLD 8
+90                                                           -> 34   HOLD 9  (34 - 9 = 25, not > 25)
+100                                                          -> 35   RELEASE; MEDIUM -7 -> 28
+105  ESCAPE -1                                               -> 27
+110  ESCAPE -1                                               -> 26   ENTER mode (cycle 2), HOLD
```

Per 100 s cycle on this path: 1 MEDIUM initiation, 9 holds, 90 s in mode, 18 normal advances in mode, stamina floor 26 and peak 35 at Bottom windows, and no re-exhaustion.

Predictions recorded for later checking, not as results:

1. **Re-exhaustion is closed on the traced path,** both after the clear and after each release (28 -> 27 -> 26 -> HOLD). Criteria 9-10 are plausible. The remaining re-entry path is any **Top-funded exchange during the mode**. At 26-28, even a funded LOW response (3) or a provisional-hold charge re-exhausts Bottom, and the reserve deliberately does not cover it (v1b rule 3). The mode keeps Bottom at 26-35 for about 90 s per cycle, longer than v1c's 26-31 band, so this exposure is larger per cycle. D1 observed no funded Top response post-clear, but D1 never observed 90 s non-Exhausted runs.
2. **MEDIUM release is slow, and most armed matches will probably never reach it.** On the traced path the first release comes 100 s after the clear. The match ends at 300 s, and a clear at timeout has no later window, so a release needs a clear at <=190 s. v1d is inactive before the first clear, so first-clear times equal the adopted controls exactly. The D1 adopted first-clear histograms give 5/37 (seed 142 batch) + 11/45 (seed 42 batch) = **16 of 82 pooled clearing matches** with a first clear <=190 s. Predicted: **roughly 66/82 armed matches never release to MEDIUM**, with typical post-clear hold-time share above 80%. v1d is designed to give a deterministic *path* back to MEDIUM. The 300 s horizon is predicted to truncate that path in most matches.
3. **v1d is more passive than v1c after the first hold.** On this path it makes 1 MEDIUM per 100 s, against v1c's 1 LOW per 60 s and the adopted policy's MEDIUM at +10 followed by Exhausted LOW initiations every 10 s. Escape attempts from Bottom after +10 s are mostly removed. **Criterion 4 is at risk** (escapes >=25, timeouts <=70). Tap direction is uncertain: Top's attempt rate is unchanged, matches may last longer, but Bottom stays non-Exhausted instead of re-exhausting, which changes exhausted-responder grades.
4. **Criterion 12 is predicted to PASS by construction,** with identical numbers to the adopted controls (pre-clear gameplay is identical): original-100 clearing matches 45, pooled 82, first-clear median 240 s.
5. **Criteria 11 and 13 sample sizes look adequate but are not guaranteed.** Admissible 30 s exposure needs clears at <=270 s: 28 + 34 = 62 pooled first clears in D1, before exit censoring. The criterion-13 handoff happens at the clear window, so the return counts track the clear counts.
6. **Criterion 5 should be relieved,** as in v1c. Holds add no RESET exposure, and in the mode they replace windows where the baseline policy might have RESET.
7. **Pass-by-passivity is not gated.** Criterion 13 is satisfied at the clear window. Release frequency, time in hold and never-release matches (15c) are descriptive. v1d could pass every A and B criterion while most armed matches never return to MEDIUM after their first hold. This revision does not add or tune a gate for that. **Whether post-hold release should be gated is a review decision to take before D2 authorization, not after results.**
8. **Stalling exposure from the mode is bounded by Top's engagement.** Holds do not zero Bottom's clock, but each Top attempt that marks Bottom as an engaged defender does. Accumulation is possible only across Top RESET runs. This is reported (15b), not gated.
9. **Rejected alternative, recorded so it is not adopted silently:** persistent CONSERVE for every advance in the mode would net +4 per 10 s (26 -> 30 -> 34 -> 38, release about 30 s after entry, at 38). It changes the recovery ledger and would be a different candidate needing its own preregistration.

v1d is frozen as specified.

---

# Sampling and denominators (unchanged)

Run the exact two E-PROD batches, 100 each, base seeds 42 and 142, 300 s, with E-PROD settings and v1d enabled, both OFF + shadow and ON. Also run adopted-policy controls at the canonical checkpoint/settings. No adaptive extensions, seed replacement, tuning, or outcome exclusions.

- Evaluate both pooled episode results and first-clear-per-match results.
- A horizon admits an episode if re-entry occurs within the inclusive horizon or the episode is observed through the horizon. Otherwise it is right-censored.
- A successful escape before the horizon is censored for stamina survival and reported separately.
- No-clear matches and clears at timeout are never survival successes.
- Report each batch and pooled results, every failure, censored counts, all 5/10/15/20/30 s horizons, complete 10/20/30 spend/recovery histograms, first actions, first-clear times and repeated cycles.
- Keep the original adoption numbers beside the new results.
- The same admissibility and censoring rules apply to the post-release horizons in 15c.

---

# A. Preservation (all mandatory; unchanged except naming and the clarifications marked)

1. Surface A (original 100 seeds/settings) exactly preserves 78 Threat matches, 1,950 Threat entries and Tap 0. Surface B exactly preserves Tap 9/100. v1d must be inactive on non-RECOVER surfaces.
2. Rule 1: zero responder commitment **or provisional hold** charged on unfunded initiator exchanges. Rule 2 stays OFF; charges, refunds and their semantics are unchanged. *(Clarification: "hold" in this criterion has always meant the provisional stamina hold of response settlement, not a RECOVERY HOLD. A RECOVERY HOLD charges nothing.)*
3. Bottom stamina stays within [0,100], with no fabricated recovery and no negative costs. E-PROD original-100 final median >=29. Setup-builder availability is retained; report attempts, advances, completions and post-clear action distributions.
4. Original-100 E-PROD:
   - escapes >=25 (adopted 35 - 10);
   - Half Guard 16, Open Guard 10 and Reversal 9 each within +/-10;
   - timeouts <=70 (adopted 60 + 10);
   - **Tap <=9/100 (adopted E-PROD 5/100 + 4)**.

   These are pragmatic tolerances, not statistical equivalence claims.
5. RESET-with-progress-route exposure <=23/100 (adopted 13 + 10). No real warning, penalty or position reset in E-PROD. OFF/ON gameplay divergence 0/100 for both seed batches when no offense fires, using full gameplay identity. RECOVERY HOLDs are not RESETs and add no exposure. Genuine RESETs, including a policy RESET at a release window, count with no carve-out.
6. Frozen Mount-v0 digest exactly `3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2`. Full unit suite, semantic checker and legacy entry point PASS. Supported-lane qualification comes from exact-head CI on Python 3.11 and 3.13; local runs are supplementary. Deterministic replay of full gameplay traces (including `recovery_hold_history` and the v1d mode-transition record), and observer ON/OFF full summary identity. `recovery_hold()` is never invoked outside v1d, and `recovery_hold_history` is empty on every non-v1d surface.
7. v1d settings must show effective-settings and full gameplay equivalence across their explicit diagnostic entry points. The existing canonical production entry point stays identical to the adopted controls and unchanged. Canonical integration needs separate authorization, and candidate equivalence must not be described as equality to unchanged adopted gameplay.
8. Preserve all historical evidence, including the failed first Gate G, old Rule 2, and the v1/v1b/v1c preregistrations. Report adoption A1-A10 and Gates A-H as historical results, not as proof that D2 passes.

# B. Absolute handoff stability (all mandatory; unchanged)

9. Rate of re-exhaustion within 10 s <=0.20, for both pooled episodes and the first-clear-per-match admissible sample.
10. Rate within 30 s <=0.35, for both denominators.
11. Each pooled denominator at both 10 s and 30 s must be >=43, including first-clear-per-match. Wilson bounds are reported descriptively only; no confidence-bound substitution for the frozen rates.
12. Anti-removal floors:
    - original-100 matches with >=1 clear: >=40 (adopted 45);
    - pooled matches with >=1 clear: >=75 (adopted 82);
    - first-clear median: <=250 s for original-100 and for pooled (adopted 240 s).

    Rates with inadequate samples remain OPEN, not PASS. Gate failures remain FAIL even if checker or unit tests PASS. No additional batch may rescue this experiment.
13. Policy handoff is the first post-clear decision window that actually restores both baseline behavior and a baseline MEDIUM request (see the handoff definition above).
    - Require >=43 distinct pooled matches with such a return.
    - Require >=43 admissible first-return-per-match observations at both +10 s and +30 s.
    - Apply the same <=0.20 / <=0.35 re-entry limits from the return timestamp as well as from the latch clear.
    - A clear-to-return re-entry counts as a failed handoff and is never dropped in favor of healthier later returns.
    - Report return delays, pending-at-end states and all pre-return re-entries.
    - Inadequate return exposure is OPEN.
14. Hold diagnostics (mandatory reporting; descriptive):
    - RECOVERY HOLD opportunities (total, per match, and per armed match);
    - longest and distribution of consecutive holds;
    - time in reserve recovery: simulated seconds from each hold until the next funded Bottom initiation (or match end, reported as pending);
    - Bottom stamina at the first decision window where `safe(MEDIUM)` holds again after a hold;
    - matches never returning to a MEDIUM request after their first hold;
    - LOW requests made by the reserve rule (MEDIUM unsafe, LOW safe, mode inactive), separately from Exhausted LOW;
    - re-entries classified by cause (initiation spend, behavior drain, responder/provisional-hold spend).

# C. Reserve-model, hold and release diagnostics (mandatory reporting; descriptive, not gates)

15. Reserve model (unchanged from v1b/v1c). For every armed, non-Exhausted Bottom decision window:
    - the predicted behavior reserve used (always 2);
    - the actual Bottom behavior drain before Bottom's next decision (or truncated at match end);
    - reserve-model violations (actual drain > 2) with their control-flow sequence;
    - classification against the counterfactual decisions of **v1** (reserve 0, no mode) and **v1c** (reserve 2, no mode) at the same state: same, MEDIUM -> LOW, MEDIUM -> HOLD, LOW -> HOLD, and the v1d-only class **LOW-safe held by mode** (v1c LOW -> v1d HOLD). Counts per batch and pooled.
    - For hold windows in the mode: the predicted net change to Bottom's next window (+2 CONSERVE, -1 ESCAPE = +1 on the traced cadence) against the actual net change, with every window where Bottom's stamina at its next window is lower than at the hold listed with its cause.

15b. Recovery-hold diagnostics (v1c list, kept):
    - total holds, and holds per match (distribution);
    - consecutive holds (longest; distribution);
    - simulated seconds in hold state: from a hold to Bottom's next funded initiation or match end (pending);
    - initiative transitions caused by holds, plus any free-initiative windows consumed by a hold;
    - setup/submission/progression opportunities forgone: holds where Bottom had a legal setup-builder or progress-capable action available;
    - holds with a progress route available (would have been RESET-with-route under v1b), reported as an explicit counterfactual and never added to criterion-5 exposure;
    - Bottom stalling clock at each hold, the stalling-clock accumulation across each mode episode, and any later genuine-RESET offense whose clock includes time spent in the mode;
    - matches where more than 50% of post-clear Bottom opportunities were holds;
    - confirmation that no hold consumed RNG, spent or granted stamina, touched setup/submission/Recognition state, or appeared in `reset_window_history` (**no RESET exposure from holds**), and that no hold was evaluated by the shadow stalling tracker.

15c. **NEW, recovery-hold mode and release diagnostics:**
    - recovery-hold cycles (mode entries) per match: total and distribution;
    - per cycle: time from entry (first hold) to MEDIUM release, in simulated seconds, with pending-at-end cycles reported separately and never as releases;
    - Bottom stamina at release (expected 35 or 36 at current values);
    - number of hold opportunities before release, per cycle;
    - number of normal advances before release, per cycle;
    - armed matches never releasing to MEDIUM after their first hold (count and list), split into ended-by-exit, ended-by-timeout and cleared-by-exhaustion;
    - percentage of post-clear simulated time spent in the mode, per armed match and pooled. Numerator: seconds from each entry to its release, exhaustion or match end. Denominator: seconds from the first clear to match end. Also reported over non-Exhausted post-clear time only;
    - first funded Bottom action after each release (action id, requested and effective commitment, exchange outcome), and whether the release window itself was a policy RESET;
    - first requested Bottom commitment after each release;
    - re-exhaustion within 10 s and within 30 s after each release, using the frozen admissibility and censoring rules, per cycle and first-release-per-match;
    - re-exhaustions while the mode is active (`CLEARED_BY_EXHAUSTION`), with cause (responder/provisional-hold spend, behavior drain, other);
    - reserve-rule LOW requests outside the mode (stamina 31-34), with the preceding event;
    - Bottom free-initiative windows evaluated in the mode (hold or release).

    These diagnostics are descriptive. They cannot PASS or FAIL D2, alter `behavior_reserve`, the release rule or hold semantics, or authorize retuning.

# Compatibility review of the existing gates

Each A and B criterion was checked against the v1d semantics before freezing. None is logically incompatible, and no threshold is changed:

- 1, 6, 7, 8: v1d is opt-in and RECOVER-only; surfaces, digest and canonical entry point are untouched.
- 2: textual clarification only ("provisional hold" versus RECOVERY HOLD).
- 3, 4, 5: computable unchanged. Criterion 4 is predicted to be at risk (prediction 3), which is a risk, not an incompatibility.
- 9-11: the clear-anchored rates are well defined. Post-release rates are added only as descriptive 15c data.
- 12: unaffected by design (pre-clear gameplay identical).
- 13: the handoff stays at the clear window, as in v1b/v1c. It does not measure post-hold release (prediction 7). That is a coverage gap, not a contradiction, and is flagged for review rather than changed here.

# Decision and hard stops

All A and B criteria must pass for a D2 design-gate PASS. A candidate failing any criterion is recorded with exact SHA/settings, then STOP: no tuning and no silent criteria change. Missing evidence gives OPEN.

After this commit: HARD STOP for review of this exact SHA and explicit D2 authorization. After D2 evidence: HARD STOP again. Not authorized here: v1d implementation, `MountMatch.recovery_hold()` implementation, candidate measurement, main changes, merges, squash, PR #10 changes, force-push, frontend work, canonical production-policy changes, Rule 2 work, or default changes.
