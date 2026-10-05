# D2 Handoff-Oscillation Preregistration — Revision v1e (persistent-CONSERVE recovery hold until MEDIUM is reserve-safe)

## Status

**PROPOSED PREREGISTRATION REVISION — FROZEN AT ITS COMMITTING SHA — HARD STOP FOR REVIEW.**

This revision selects **POST-CLEAR RESERVE-AWARE HANDOFF v1e (persistent-CONSERVE recovery hold until MEDIUM is reserve-safe)** as the D2 candidate. It becomes binding only after the user reviews this exact SHA and explicitly authorizes D2 implementation and measurement. No D2 candidate (v1, v1b, v1c, v1d or v1e) has been implemented or run.

It **supersedes v1d only as the selected future candidate**. v1d stays on record, unchanged, as historical preregistration evidence, and so do all earlier records:

```text
D1 evidence (unchanged):          cdb04a0c603dbfa1b2c9a41d66f877334a848869
v1 preregistration (unchanged):   62309599f955461fc29b60ee1c31b31eeb3008aa
v1b preregistration (unchanged):  f624db2cc3753f93b4f4f2bbc7d1e4d5b02057dc
v1c preregistration (unchanged):  f30ace90c20df9d901ca6370e0acd4c3a8caa2c5
v1d preregistration (unchanged):  8dcaabb5a633768a85005b1845132d78fc80d9a0
                                  docs/HANDOFF_OSCILLATION_D2_PREREGISTRATION_V1D.md
adopted baseline (PR #10):        ee6cb6fcebb105e31224bead48a302811b27b59a
canonical policy:                 PRODUCTION_STAMINA_RECOVERY_POLICY (unchanged)
frozen digest:                    3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

Review record at `8dcaabb`: v1d accepted as preregistration evidence. A v1d run was **not authorized**. The reason: the mandatory gates did not prevent post-clear pass-by-passivity. One-shot CONSERVE recovers only +1 per 10 s, so a hold cycle lasts about 90 s. v1d's own prediction was that about 66/82 clearing matches would never release to MEDIUM, while criterion 13 would still be met at the clear window.

Design lineage, all decided before any candidate measurement:

```text
D1  cdb04a0  oscillation characterized: 35 -> 28 -> 27 -> 26 -> 19
v1  6230959  initiation-only reserve; predicted behavior-drain re-entry
v1b f624db2  + behavior reserve 2; predicted RESET spam vs criterion 5
v1c f30ace9  + non-RESET recovery hold; predicted 26..31 LOW sawtooth, no MEDIUM return
v1d 8dcaabb  + hold mode released only by safe(MEDIUM); predicted ~90 s holds, ~66/82 never release
v1e (this)   + CONSERVE on every normal advance while the mode is active; + post-hold return gate (16)
```

## Changes versus v1d

| Item | v1d (`8dcaabb`) | v1e (this revision) |
|---|---|---|
| Reserve-safe rule | `stamina - cost(c) - 2 > 25` | **unchanged** |
| Entry, mode decision, release | as frozen in v1d | **unchanged** |
| Hold transition `MountMatch.recovery_hold()` | v1c semantics | **unchanged** |
| Pre-advance Bottom behavior while the mode is active | CONSERVE for the one advance after each hold (`pending_conserve`) | **CONSERVE on every normal advance while `recovery_hold_mode` is True** |
| Post-advance behavior re-choice | unchanged | **unchanged** (CONSERVE is not forced through resolution) |
| State | `recovery_hold_mode`, `pending_conserve` | `recovery_hold_mode` only |
| Criteria 1-15 | as frozen | **unchanged** |
| New mandatory gate | — | **16. Post-hold return gate** |
| Diagnostics | 15, 15b, 15c | kept; 15c extended (15d) |

Frozen constants (unchanged; listed so that no silent change is possible):

```text
behavior_reserve           = 2
cost(LOW)                  = 3
cost(MEDIUM)               = 7
exhaustion_enter_threshold = 25   (StaminaPool, maximum 100)
exhaustion_clear_threshold = 35   (StaminaPool, maximum 100)
recovery amount            = Bottom CONSERVE +2 per 5 s behavior quantum (unchanged)
behavior drain             = Bottom ESCAPE -1 per 5 s behavior quantum (unchanged)
release threshold          = safe(MEDIUM): stamina - 7 - 2 > 25  <=>  stamina >= 35
Rule 1                     = ON
Rule 2                     = OFF
```

---

# Engine inspection: what reads the behavior state (inspected at `8dcaabb`)

Required before freezing: does exchange resolution read the behavior state that the post-advance re-choice leaves in place? **Yes.** The mechanics are documented here and are **not modified** by v1e.

1. **Exchange resolution reads the opposing side's current behavior.** `MountMatch._resolve()` and `_resolve_submission_stage()` pass `match.top.behavior` / `match.bottom.behavior` (via `_behaviors()`) to `MountEngine.resolve_action()`. That function applies `MountRuleSet.behavior_modifier(action, opposing_behavior)`, which is `action.behavior_modifiers.get(opposing_behavior, 0)`, as a grade shift. The current catalog entries are:
   - Top Americana arm isolation and Top Americana finish: `BottomBehavior.PROTECT: -1`;
   - Bottom Bridge and Bottom Trap-and-Roll: `TopBehavior.HOLD: -1`.

   **No catalog entry keys `BottomBehavior.CONSERVE`**, so Bottom CONSERVE would give modifier 0, the same as ESCAPE. The modifier lookup does not alias CONSERVE to PROTECT.
2. **Decision previews read the same state.** `preview_attempt_resolution()`, `preview_attempt_resolution_from_effective()` (used by the batch's informed Bottom response choice) and `_progress_preview()` (used by `action_is_progress_capable()` for stalling progress routes) all call `_behaviors()`. They therefore see the post-re-choice behavior.
3. **`advance()` reads the pre-advance behavior for two things,** both governed by the behavior set before the advance:
   - **behavior stamina** (`BehaviorStaminaPolicy.apply`: CONSERVE +2, ESCAPE -1 per 5 s quantum);
   - **positional drift** (`MountRuleSet.drift_rate`). For drift, CONSERVE is aliased to PROTECT. With Top PRESSURE (E-PROD): `(PRESSURE, ESCAPE) = +0.10/s` and `(PRESSURE, PROTECT) = +0.15/s`. Over a 5 s interval that is +0.50 versus +0.75 toward Top, clamped at `MAX_AXIS = 4.00`.

   `drift()` also appends the pre-advance behavior to `bottom_behavior_history`.
4. **Consequence for v1e (frozen):** with the unchanged post-advance re-choice, a non-Exhausted Bottom in the mode is back on baseline ESCAPE at every decision window. Resolution, previews, Recognition inputs and progress-route detection therefore see exactly the behavior they see under the adopted policy. **v1e changes only what happens inside each advance in the mode: stamina (+2 instead of -1 per quantum) and positional drift (+0.75 instead of +0.50 per 5 s interval).** The drift effect is inseparable from CONSERVE as the engine defines it. It is not a change to exchange mechanics, but it means v1e is **not a pure stamina-ledger change**. It is recorded here before any run and reported in 15d. Adopted Exhausted-latch CONSERVE and v1c/v1d one-shot CONSERVE carry the same drift effect.

Other engine facts (inherited from v1c/v1d inspection, re-confirmed): initiative turns over only in `_apply_resolution()` and `reset_window()`. The clock moves only in `advance()`/`drift()`. Under v0.2 ordering, the decision precedes all Recognition and response RNG draws. Stalling clocks are per side, advance with simulated time, and are zeroed by own engagement, by being an engaged defender of the opponent's attempt, or by an evaluated offense.

---

# Selected candidate: POST-CLEAR RESERVE-AWARE HANDOFF v1e

## Scope and arming (unchanged from v1d)

- Bottom only, and only when `bottom_behavior_mode=RECOVER` **and** v0.2 setup ordering is enabled (as on E-PROD). Any other configuration that requests v1e is rejected. v1e is inactive on Surfaces A and B, and Top is never affected.
- Rule 1 ON and Rule 2 OFF, as adopted. Response selection, affordability, provisional-hold settlement, Recognition algorithms, costs, behavior rates, recovery amounts, drift rates, behavior modifiers and the 25/35 hysteresis are unchanged. Adopted LOW_WHILE_EXHAUSTED is unchanged while Bottom is Exhausted.
- **Armed** after Bottom's first Exhausted -> non-Exhausted latch clear in the match, for the rest of the match. v1e acts only at non-Exhausted Bottom decision windows of an armed match, plus the pre-advance behavior choice while the mode is active.
- **Before the first clear, gameplay is identical to the adopted policy.**
- Implemented as a new opt-in **diagnostic** recovery-initiation mode. Raw defaults and the canonical production policy are unchanged.

## Reserve-safe rule (unchanged)

```text
safe(c) = current_stamina - cost(c) - behavior_reserve > exhaustion_enter_threshold
safe(MEDIUM) <=> stamina >= 35        safe(LOW) <=> stamina >= 31
```

It is evaluated on current stamina at the Bottom decision window: after that window's advance (if any) and the post-advance re-choice, and before action selection. The same timing applies to entry and release. The release threshold equals the latch clear threshold for these values by arithmetic only. Release is defined by `safe(MEDIUM)`, never by the latch.

## State

```text
recovery_hold_mode : bool   per match, initially False
```

It is owned by the batch-side v1e diagnostic mode, not by `MountMatch`, `StaminaPool` or `AdaptiveBehaviorPolicy`. It is created False at match start and discarded at match end. There is no timer and no counter. v1d's `pending_conserve` does not exist in v1e.

## Decision at an armed Bottom decision window (unchanged from v1d)

```text
if Bottom is Exhausted:
    recovery_hold_mode := False          (if it was True: record CLEARED_BY_EXHAUSTION)
    adopted LOW_WHILE_EXHAUSTED decision, unchanged

elif recovery_hold_mode:
    if safe(MEDIUM):
        recovery_hold_mode := False      (record RELEASE)
        ordinary decision in this same window
    else:
        RECOVERY HOLD                    (LOW is not considered)

else:                                    (ordinary decision = v1c decision)
    if safe(MEDIUM):   request MEDIUM, normal action selection
    elif safe(LOW):    request LOW, normal action selection
    else:
        recovery_hold_mode := True       (record ENTER)
        RECOVERY HOLD
```

If `policy.choose` returns no action in an ordinary decision, that is a **genuine policy RESET**. It is counted and stalling-evaluated like any RESET, and it does not enter the mode. Only the reserve rule enters the mode.

### Entry (unchanged from v1d)

Entry happens at a Bottom decision window with: Bottom, RECOVER, v0.2 setup ordering, Rule 1 ON, Rule 2 OFF; the match armed; Bottom not Exhausted; the mode inactive; and neither MEDIUM nor LOW reserve-safe (stamina <= 30). The entry window itself is a hold.

### Behavior while the mode is active (NEW, frozen)

```text
PRE-ADVANCE (each normal-speed advance, i.e. each loop iteration without a free window):
    if recovery_hold_mode:  Bottom behavior := CONSERVE
    else:                   Bottom behavior := AdaptiveBehaviorPolicy.choose(match)   (unchanged)

POST-ADVANCE:
    existing re-choice, unchanged: Bottom behavior := AdaptiveBehaviorPolicy.choose(match)
    (non-Exhausted -> baseline ESCAPE; Exhausted -> CONSERVE)

RESOLUTION:
    uses the post-advance behavior, as adopted
```

- **Persistent across the whole mode.** CONSERVE is forced on every normal advance from the one after the entry window up to and including the advance before the release window. That covers advances before Top windows and before Bottom windows.
- **Not forced through resolution.** The unchanged post-advance re-choice governs resolution, previews, Recognition inputs and progress-route detection.
- **Free-initiative windows** have no advance, so they apply no behavior and change no stamina. The mode persists through them.
- **The release window:** the advance before it was forced CONSERVE (the mode was still active). After release, the next advance uses the unchanged RECOVER pre-advance choice.
- **Exhaustion:** if Bottom becomes Exhausted while the mode is active, the mode ends at Bottom's next decision window (`CLEARED_BY_EXHAUSTION`). Until then, the forced CONSERVE coincides with the latch-keyed CONSERVE, so behavior is identical either way.
- **`AdaptiveBehaviorPolicy` is unchanged and not subclassed.** The override wraps only the pre-advance call site.
- **Bookkeeping consequence (descriptive):** in the mode, Bottom's behavior flips CONSERVE -> ESCAPE at every post-advance re-choice and ESCAPE -> CONSERVE at every pre-advance choice. The existing `bottom_behavior_switches` counter and the stamina-economy collector's switch events therefore record two switches per advance in the mode. These are counters, not gameplay. They are reported separately so they are not read as policy instability.

### Recovery-hold state (unchanged from v1d except CONSERVE)

| Aspect | Frozen behavior |
|---|---|
| Persistence across initiative changes | Persists. Top windows neither read nor change the mode. |
| Persistence across free initiative | Persists. A Bottom free window in the mode is evaluated exactly like a normal Bottom window (release check, otherwise hold). Initiative passes to Top. A Top free window does not touch the mode. |
| Clock | A hold consumes no simulated time. The mode has no timer. |
| Initiative turnover | Every hold passes initiative normally: `initiator = initiator.opponent`. |
| CONSERVE | **Persistent pre-advance CONSERVE while the mode is active (above).** No one-shot flag. |
| v0.3b stalling | A hold calls neither `reset_window()` nor `evaluate_reset()`, records no progress opportunity and engages no side. Stalling clocks keep advancing with simulated time and are zeroed only by the existing engagement and offense rules. |
| Shadow stalling | Not evaluated for holds. Holds are never shadow RESETs. |
| RESET | No RESET semantics. Holds are not in `reset_window_history`, Bottom RESET totals or RESET-with-route exposure. |
| Setup / submission | Untouched by holds. |
| Recognition / responder | No Recognition read or response selection on a hold, and **no RNG consumed**. Top's windows are unchanged, and Bottom responds exactly as adopted, including any funded response or provisional-hold charge. |
| Stamina | A hold spends and grants nothing. The mode changes stamina only through the CONSERVE behavior during advances, at the unchanged rate. |
| History | Each hold appends `"{side}@{elapsed}s:stamina={current}"` to `RunHistory.recovery_hold_history`. Mode transitions (`ENTER`, `RELEASE`, `CLEARED_BY_EXHAUSTION`, `PENDING_AT_END`, each with elapsed seconds, remaining seconds and stamina) are recorded by the batch-side v1e collector. Neither appears on any non-v1e run. |
| Observers | The A9 observer samples as adopted. v1e collectors are read-only, consume no RNG and mutate no engine state. Observer ON/OFF full-summary identity is required. |
| Match end / exit | Any terminal event ends the mode. `PENDING_AT_END` is recorded if it was active. Pending is never a release. |

### Release (unchanged from v1d)

```text
release only when safe(MEDIUM):  stamina - 7 - 2 > 25  <=>  stamina >= 35
```

The check runs only at Bottom decision windows (normal or free). **LOW never releases the mode.** On release, the same window runs the ordinary decision, which requests MEDIUM. If `policy.choose` returns no action, that is a genuine, counted policy RESET. The mode also ends on re-exhaustion or match end, both without release. Each entry starts a new **recovery-hold cycle**.

Prohibited: timers, protected-action counters, a permanent LOW state, LOW requests in the mode, stamina grants, altered recovery amounts, drains, drift rates or behavior modifiers, forcing CONSERVE through resolution, any change to Top, any change to responder or provisional-hold settlement, and any routing of holds through RESET or stalling machinery.

`MountMatch.recovery_hold()` is opt-in engine surface used only by the v1e diagnostic mode, with exactly the v1c semantics. Existing call paths never invoke it.

## Handoff definition for criterion 13 (unchanged)

A clear at 35 gives `35 - 7 - 2 = 26 > 25`, so MEDIUM is requested at the clear window. **The criterion-13 handoff is the clear window.** Post-hold release is gated separately by criterion 16.

## Pre-registration ledger note (prediction, not a result)

Traced path (Top PRESSURE and unfunded, alternating initiative, no free windows), recorded before any run. Each line is the stamina after the advance ending at that offset:

```text
+0    clear 33 -> 35; MEDIUM safe (26 > 25) -> MEDIUM -7          -> 28
+5    ESCAPE -1                                     (Top window)  -> 27
+10   ESCAPE -1   MEDIUM 17, LOW 21 unsafe: ENTER cycle 1, HOLD   -> 26
+15   CONSERVE +2                                   (Top window)  -> 28
+20   CONSERVE +2                       HOLD   (30 - 9 = 21)      -> 30
+25   CONSERVE +2                                   (Top window)  -> 32
+30   CONSERVE +2                       HOLD   (34 - 9 = 25)      -> 34
+35   CONSERVE +2                                   (Top window)  -> 36
+40   CONSERVE +2   RELEASE (38 - 9 = 29 > 25); MEDIUM -7        -> 38 -> 31
+45   ESCAPE -1                                     (Top window)  -> 30
+50   ESCAPE -1   MEDIUM 20, LOW 24 unsafe: ENTER cycle 2, HOLD   -> 29
```

**v1e is expected to be cyclic recovery, not a permanent cure for stamina pressure.** Continuing the same arithmetic, entry stamina is `release - 9`, and each 10 s in the mode adds +4 at Bottom windows:

| Cycle | Entry | Bottom-window stamina in mode | Release at | Holds | Entry -> release | Release -> next entry |
|---|---|---|---|---|---|---|
| 1 | 26 | 26, 30, 34 | 38 | 3 | 30 s | 10 s |
| 2 | 29 | 29, 33 | 37 | 2 | 20 s | 10 s |
| 3 | 28 | 28, 32 | 36 | 2 | 20 s | 10 s |
| 4 | 27 | 27, 31 | 35 | 2 | 20 s | 10 s |
| 5 | 26 | (repeats cycle 1) | | | | |

Period: 130 s, with 4 MEDIUM initiations and 9 holds (9 of 13 Bottom windows are holds, about 69%). Bottom stays between 26 and 38 at its windows and never re-exhausts on this path. Time from a hold to the next funded Bottom initiation is at most 30 s.

Predictions recorded for later checking, not as results:

1. **Criteria 9-10 and post-release re-exhaustion are closed on the traced path.** The remaining re-entry path is a **Top-funded exchange while Bottom sits at 26-30**. Even a funded LOW response (3) or a provisional-hold charge re-exhausts Bottom, and the reserve does not cover it. The low band now lasts about 10-20 s per cycle instead of v1d's about 90 s.
2. **Criterion 16 timely release is expected to PASS on the traced path** (maximum 30 s against the 40 s limit). The predicted failure sources are re-exhaustion before release (prediction 1) and terminal events during the mode, such as Top's Tap or exit attempts. Eligibility needs entry at <=260 s elapsed. With entry at clear +10 s, that means a first clear at <=250 s. v1e is inactive before the first clear, so first-clear times equal the adopted controls exactly. The D1 adopted histograms give 21 (seed 142 batch) + 26 (seed 42 batch) = **about 47 pooled matches with a first clear <=250 s**, before removing matches that end at the clear window or re-exhaust first. The >=35 adequacy floor is expected to be met but is not guaranteed.
3. **Criterion 12 is predicted to PASS by construction,** with numbers identical to the adopted controls (45 / 82 / 240 s).
4. **Criterion 4 risk is reduced compared with v1d but not removed.** On this path Bottom makes about one MEDIUM initiation per 32.5 s after the first hold, against v1d's one per 100 s. The adopted post-clear path made a MEDIUM at +10 and then Exhausted LOW initiations every 10 s. Escapes may still fall and timeouts rise.
5. **The positional drift side effect (inspection item 4):** each advance in the mode drifts +0.75 instead of +0.50 toward Top. That is +0.25 extra per forced advance: +1.5 axis in traced cycle 1 (6 forced advances) and +1.0 in later cycles (4 forced advances), before clamping at 4.00. Baseline PRESSURE/ESCAPE already drifts +0.50 per interval, so the axis may often already be at the clamp, and the realized difference is an empirical question. If the axis is not already at the clamp, this can push the band toward STRONG/LOCKED, where Bottom initiations take the existing -1 positional modifier. That could lower escape success after release (criterion 4) and change Tap exposure (Tap direction uncertain). This is inherent to CONSERVE as defined and is reported, not corrected.
6. **Criterion 5 should be relieved.** Holds add no RESET exposure, and release windows can produce genuine policy RESETs, which count.
7. **Behavior-switch counters will inflate** (two per advance in the mode). This is bookkeeping only (see above).
8. **Criteria 11 and 13 sample sizes look adequate** (about 62 pooled first clears at <=270 s for 30 s exposure), but are not guaranteed.

v1e is frozen as specified. Any change to the release threshold, CONSERVE scope, reserve or gate tolerances would be a different candidate needing its own preregistration.

---

# Sampling and denominators (unchanged)

Run the exact two E-PROD batches, 100 each, base seeds 42 and 142, 300 s, with E-PROD settings and v1e enabled, both OFF + shadow and ON. Also run adopted-policy controls at the canonical checkpoint/settings. No adaptive extensions, seed replacement, tuning, or outcome exclusions.

- Evaluate both pooled episode results and first-clear-per-match results.
- A horizon admits an episode if re-entry occurs within the inclusive horizon or the episode is observed through the horizon. Otherwise it is right-censored.
- A successful escape before the horizon is censored for stamina survival and reported separately.
- No-clear matches and clears at timeout are never survival successes.
- Report each batch and pooled results, every failure, censored counts, all 5/10/15/20/30 s horizons, complete 10/20/30 spend/recovery histograms, first actions, first-clear times and repeated cycles.
- Keep the original adoption numbers beside the new results.
- Criterion 16 uses its own eligibility rule (below), **not** right-censoring: an eligible cycle that does not release in time is a failure.

---

# A. Preservation (all mandatory; unchanged from v1d)

1. Surface A (original 100 seeds/settings) exactly preserves 78 Threat matches, 1,950 Threat entries and Tap 0. Surface B exactly preserves Tap 9/100. v1e must be inactive on non-RECOVER surfaces.
2. Rule 1: zero responder commitment **or provisional hold** charged on unfunded initiator exchanges. Rule 2 stays OFF; charges, refunds and their semantics are unchanged. ("Hold" here is the provisional stamina hold of response settlement, not a RECOVERY HOLD. A RECOVERY HOLD charges nothing.)
3. Bottom stamina stays within [0,100], with no fabricated recovery and no negative costs. E-PROD original-100 final median >=29. Setup-builder availability is retained; report attempts, advances, completions and post-clear action distributions.
4. Original-100 E-PROD:
   - escapes >=25 (adopted 35 - 10);
   - Half Guard 16, Open Guard 10 and Reversal 9 each within +/-10;
   - timeouts <=70 (adopted 60 + 10);
   - **Tap <=9/100 (adopted E-PROD 5/100 + 4)**.

   These are pragmatic tolerances, not statistical equivalence claims.
5. RESET-with-progress-route exposure <=23/100 (adopted 13 + 10). No real warning, penalty or position reset in E-PROD. OFF/ON gameplay divergence 0/100 for both seed batches when no offense fires, using full gameplay identity. RECOVERY HOLDs are not RESETs and add no exposure. Genuine RESETs, including a policy RESET at a release window, count with no carve-out.
6. Frozen Mount-v0 digest exactly `3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2`. Full unit suite, semantic checker and legacy entry point PASS. Supported-lane qualification comes from exact-head CI on Python 3.11 and 3.13; local runs are supplementary. Deterministic replay of full gameplay traces (including `recovery_hold_history` and the v1e mode-transition record), and observer ON/OFF full summary identity. `recovery_hold()` is never invoked outside v1e, and `recovery_hold_history` is empty on every non-v1e surface.
7. v1e settings must show effective-settings and full gameplay equivalence across their explicit diagnostic entry points. The existing canonical production entry point stays identical to the adopted controls and unchanged. Canonical integration needs separate authorization, and candidate equivalence must not be described as equality to unchanged adopted gameplay.
8. Preserve all historical evidence, including the failed first Gate G, old Rule 2, and the v1/v1b/v1c/v1d preregistrations. Report adoption A1-A10 and Gates A-H as historical results, not as proof that D2 passes.

# B. Absolute handoff stability (all mandatory; 9-14 unchanged, 16 NEW)

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

16. **NEW — POST-HOLD RETURN GATE (mandatory).** Population: each match's **first recovery-hold cycle** (its first mode entry), pooled over both seed batches (200 matches), evaluated separately for OFF + shadow and ON. Both must pass.

    ```text
    entry_elapsed     = elapsed simulated seconds at the entry window
    remaining_at_entry = initial_clock (300) - entry_elapsed
    eligible          <=> remaining_at_entry >= 40          (entry_elapsed <= 260)
    release_delay     = elapsed at the RELEASE window - entry_elapsed
    timely release    <=> the cycle ends by RELEASE and release_delay <= 40   (inclusive)
    ```

    - **Sample adequacy:** at least **35** distinct pooled matches must have an eligible first cycle. Fewer gives **OPEN**, never PASS.
    - **Timely release:** at least **80%** of eligible first cycles must be timely releases (`timely / eligible >= 0.80`, computed unrounded).
    - **Failures (counted in the denominator, never censored or dropped):**
      - re-exhaustion before release (`CLEARED_BY_EXHAUSTION`);
      - match end before release (any terminal event, such as timeout, escape/exit or submission, while the mode is active), despite >=40 s remaining at entry;
      - release with `release_delay > 40` (late release).
    - **Pending-at-end is never a successful release.**
    - Ineligible first cycles (entry with < 40 s remaining) are excluded from the gate and reported.
    - The 35 / 80% / 40 s values are frozen here, before implementation. They are normative tolerances, not statistical claims, and cannot be changed after results.
    - **Mandatory report:** eligible denominator; timely releases; late releases; re-exhausted-before-release; pending-at-end, by terminal type; ineligible first cycles; median and p90 `release_delay` over all releasing first cycles (eligible and all); total matches ever releasing after a hold; recovery-hold cycles per match (distribution); all per batch and pooled.

    Criterion 16 answers a different question from 9-13: whether a match that enters recovery hold actually returns to MEDIUM play. It does not replace or relax the clear-anchored stability criteria.

# C. Reserve-model, hold and release diagnostics (mandatory reporting; descriptive, not gates)

15. Reserve model (unchanged). For every armed, non-Exhausted Bottom decision window:
    - the predicted behavior reserve used (always 2);
    - the actual Bottom behavior drain before Bottom's next decision (or truncated at match end);
    - reserve-model violations (actual drain > 2) with their control-flow sequence;
    - classification against the counterfactual decisions of **v1** (reserve 0, no mode) and **v1c** (reserve 2, no mode) at the same state: same, MEDIUM -> LOW, MEDIUM -> HOLD, LOW -> HOLD, and **LOW-safe held by mode** (v1c LOW -> v1e HOLD). Counts per batch and pooled.
    - For hold windows in the mode: the predicted net change to Bottom's next window (+4 with two CONSERVE advances on the traced cadence) against the actual net change, with every window where Bottom's stamina at its next window is lower than at the hold listed with its cause.

15b. Recovery-hold diagnostics (unchanged from v1c/v1d):
    - total holds, and holds per match (distribution);
    - consecutive holds (longest; distribution);
    - simulated seconds in hold state: from a hold to Bottom's next funded initiation or match end (pending);
    - initiative transitions caused by holds, plus any free-initiative windows consumed by a hold;
    - setup/submission/progression opportunities forgone: holds where Bottom had a legal setup-builder or progress-capable action available;
    - holds with a progress route available (would have been RESET-with-route under v1b), reported as an explicit counterfactual and never added to criterion-5 exposure;
    - Bottom stalling clock at each hold, the stalling-clock accumulation across each mode episode, and any later genuine-RESET offense whose clock includes time spent in the mode;
    - matches where more than 50% of post-clear Bottom opportunities were holds;
    - confirmation that no hold consumed RNG, spent or granted stamina, touched setup/submission/Recognition state, appeared in `reset_window_history` (no RESET exposure from holds), or was evaluated by the shadow stalling tracker.

15c. Recovery-hold mode and release diagnostics (unchanged from v1d; these are all cycles, while criterion 16 gates first cycles):
    - recovery-hold cycles (mode entries) per match: total and distribution;
    - per cycle: time from entry to MEDIUM release, with pending-at-end cycles reported separately and never as releases;
    - Bottom stamina at entry and at release (traced expectation: entry 26-29, release 35-38);
    - number of hold opportunities and of normal advances before release, per cycle;
    - armed matches never releasing to MEDIUM after their first hold, split into ended-by-exit, ended-by-timeout and cleared-by-exhaustion;
    - percentage of post-clear simulated time in the mode, per armed match and pooled. Numerator: seconds from each entry to its release, exhaustion or match end. Denominator: seconds from the first clear to match end. Also reported over non-Exhausted post-clear time only;
    - first funded Bottom action after each release (action id, requested and effective commitment, exchange outcome), and whether the release window was a policy RESET;
    - first requested Bottom commitment after each release;
    - re-exhaustion within 10 s and within 30 s after each release, using the frozen admissibility and censoring rules, per cycle and first-release-per-match;
    - re-exhaustions while the mode is active, with cause;
    - reserve-rule LOW requests outside the mode (stamina 31-34), with the preceding event;
    - Bottom free-initiative windows evaluated in the mode.

15d. **NEW, persistent-CONSERVE diagnostics:**
    - number of normal advances run under forced CONSERVE, per match and pooled, and Bottom stamina gained in them;
    - positional drift accumulated during forced-CONSERVE advances, against the counterfactual ESCAPE drift for the same advances (the +0.25 per advance difference, after clamping); band at each entry and each release; band changes that occurred during forced-CONSERVE advances;
    - Bottom initiations after release by band (to expose the STRONG/LOCKED -1 positional modifier);
    - behavior-switch counts, split into mode-induced pre/post-advance flips and all other switches;
    - confirmation that at every Bottom and Top decision window in the mode, the behavior seen by resolution and previews equals the unchanged post-advance re-choice.

    These diagnostics are descriptive. They cannot PASS or FAIL D2, alter `behavior_reserve`, the release rule, the CONSERVE scope or hold semantics, or authorize retuning.

# Compatibility review of the existing gates

Each criterion was checked against the v1e semantics before freezing. None is logically incompatible, and no threshold is changed:

- 1, 6, 7, 8: v1e is opt-in and RECOVER-only; surfaces, digest and canonical entry point are untouched.
- 2, 3, 4, 5: computable unchanged. Criterion 4 is at risk (predictions 4-5), which is a risk, not an incompatibility.
- 9-11: clear-anchored rates are unchanged and well defined.
- 12: unaffected by design.
- 13: still the clear-window handoff. The post-hold return coverage gap noted in v1d is closed by the new criterion 16, not by changing 13.
- 16: new. It uses eligibility (>=40 s remaining at entry) instead of right-censoring. Within eligible cycles, every non-timely outcome is a failure.

# Decision and hard stops

All A and B criteria (1-14 and 16) must pass for a D2 design-gate PASS. A candidate failing any criterion is recorded with exact SHA/settings, then STOP: no tuning and no silent criteria change. Missing evidence gives OPEN.

After this commit: HARD STOP for review of this exact SHA and explicit D2 authorization. After D2 evidence: HARD STOP again. Not authorized here: v1e implementation, `MountMatch.recovery_hold()` implementation, candidate measurement, main changes, merges, squash, PR #10 changes, force-push, frontend work, canonical production-policy changes, Rule 2 work, or default changes.
