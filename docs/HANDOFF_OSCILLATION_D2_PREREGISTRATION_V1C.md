# D2 Handoff-Oscillation Preregistration — Revision v1c (non-RESET recovery hold)

## Status

**PROPOSED PREREGISTRATION REVISION — FROZEN AT ITS COMMITTING SHA — HARD STOP FOR REVIEW.**

This revision selects **POST-CLEAR RESERVE-AWARE HANDOFF v1c (behavior-drain-aware, non-RESET RECOVERY HOLD)** as the D2 candidate. It becomes binding only after the user reviews this exact SHA and explicitly authorizes D2 implementation and measurement. No D2 candidate (v1, v1b or v1c) has been implemented or run.

It **supersedes v1b as the selected candidate**. It does not delete or rewrite earlier records:

```text
D1 evidence (unchanged):          cdb04a0c603dbfa1b2c9a41d66f877334a848869
v1 preregistration (unchanged):   62309599f955461fc29b60ee1c31b31eeb3008aa
v1b preregistration (unchanged):  f624db2cc3753f93b4f4f2bbc7d1e4d5b02057dc
adopted baseline (PR #10):        ee6cb6fcebb105e31224bead48a302811b27b59a
canonical policy:                 PRODUCTION_STAMINA_RECOVERY_POLICY (unchanged)
frozen digest:                    3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

Review record at `f624db2`: accepted as preregistration evidence. A v1b run was **not authorized**. The v1b ledger note predicted a closed block/LOW sawtooth (26..31, MEDIUM never returning) driven through the forced-RESET path, which structurally conflicts with mandatory criterion 5 (RESET-with-route exposure <=23; forced RESET precedent 983).

Design lineage, all decided before any candidate measurement:

```text
D1  cdb04a0  oscillation characterized: 35 -> 28 -> 27 -> 26 -> 19
v1  6230959  initiation-only reserve; predicted behavior-drain re-entry
v1b f624db2  + behavior reserve 2; predicted RESET-spam vs criterion 5
v1c (this)   + non-RESET recovery hold
```

## Changes versus v1b

| Item | v1b (`f624db2`) | v1c (this revision) |
|---|---|---|
| Reserve-safe rule | `stamina - cost(c) - 2 > 25` | **unchanged** |
| Unsafe fallback | RESERVE BLOCK through the forced-RESET path (`reset_window()`) | **RECOVERY HOLD**: a new non-RESET transition (below) |
| Engine surface | batch policy only | adds one opt-in engine transition, `MountMatch.recovery_hold()`, because no existing non-action, non-RESET transition exists (evidence below) |
| Criteria 1-14 | as frozen | unchanged; "RESERVE BLOCK" wording becomes "RECOVERY HOLD" |
| Criterion 15 | reserve-model diagnostics | unchanged, plus **hold diagnostics** (15b) |

---

# Engine inspection (evidence for the frozen semantics)

Inspected at `f624db2`:

1. **Initiative turnover exists in exactly two places.**
   - `MountMatch._apply_resolution()` (after `attempt()`, only when no exit): `self.initiator = self.initiator.opponent`.
   - `MountMatch.reset_window()`: `self.initiator = next_initiator`.

   No existing transition means "decline to initiate" without going through RESET machinery.
2. **`reset_window()` carries RESET semantics** a hold must not inherit: it records `stalling_progress_opportunity_history`, appends `stalling_reset_with_route_history` when a progress route exists, evaluates `StallingTracker.evaluate_reset()` (warnings, penalties, position resets, free initiative), and appends `reset_window_history`.
3. **The simulated clock moves only in `advance()`/`drift()`.** `attempt()` and `reset_window()` consume no simulated time.
4. **RNG ordering on the v0.2 setup path (used by E-PROD):** the initiation decision (`policy.choose` or the forced-recovery branch) is made **before** any Recognition rolls (`recognition_intent_rng`, `recognition_capability_rng`) or response-commitment RNG draws. A decision that ends without an attempt therefore consumes no RNG. The forced-RESET path already relies on this.
5. **The stalling clock** advances with simulated time in `advance()`. It is zeroed only by engagement (`engage`) or by an evaluated offense in `evaluate_reset`.
6. **Free initiative:** `consume_free_initiative_window()` runs at the top of the batch loop, before the decision, so a pending window is consumed whatever the initiator then does.

---

# Selected candidate: POST-CLEAR RESERVE-AWARE HANDOFF v1c

## Scope, arming, reserve and decision order (unchanged from v1b)

- Bottom only, and only when `bottom_behavior_mode=RECOVER` **and** v0.2 setup ordering is enabled (as on E-PROD). Any other configuration requesting v1c is rejected. Inactive on Surfaces A and B; Top is never affected.
- Rule 1 ON and Rule 2 OFF as adopted. Response selection, affordability, hold settlement, Recognition algorithms, costs, behavior rates, recovery amounts and the 25/35 hysteresis are unchanged. Adopted LOW_WHILE_EXHAUSTED is unchanged while Exhausted.
- **Armed** after Bottom's first Exhausted -> non-Exhausted clear in the match, for the rest of the match. Applies only at non-Exhausted Bottom decision windows.
- `behavior_reserve = 2` (frozen constant, same cadence rationale and rules as v1b, including violation reporting).
- `safe(c) = current_stamina - cost(c) - 2 > T_enter` (T_enter = 25).

```text
if safe(MEDIUM):   request MEDIUM (baseline)
elif safe(LOW):    request LOW
else:              RECOVERY HOLD
```

Implemented as a new opt-in **diagnostic** recovery-initiation mode. Raw defaults and the canonical production policy are unchanged.

## RECOVERY HOLD (frozen semantics)

At an armed, non-Exhausted Bottom decision window where neither MEDIUM nor LOW is reserve-safe, the batch replaces the initiation decision (the point where `policy.choose` or the forced-recovery branch would run) with a call to a **new engine transition**:

```text
MountMatch.recovery_hold()
```

Exactly:

| Aspect | Frozen behavior |
|---|---|
| Initiation / stamina | No action is selected or attempted. No initiator, responder or hold stamina is spent. No stamina is granted. |
| Clock | Consumes **no** simulated time, like `attempt()` and `reset_window()`. Time advances only at the next normal `advance()`. |
| Initiative turnover | **Passes initiative normally:** `initiator = initiator.opponent`. Bottom's opportunity is consumed and Top initiates next. Initiative is never retained. |
| RESET | **Not a RESET.** It does not call `reset_window()` and does not append `reset_window_history`. It does not count toward Bottom RESET totals or RESET-with-progress-route exposure. |
| v0.3b stalling | No stalling evaluation (`evaluate_reset` not called), no progress-opportunity record, no engagement. The stalling clock is **neither zeroed nor evaluated**: it keeps advancing with simulated time in later `advance()` calls, exactly as during any non-engaging interval. A later genuine RESET is evaluated with that accumulated clock. |
| Shadow stalling (OFF + shadow) | The recovery-policy collector's shadow tracker is **not** evaluated for a hold. Holds are recorded as hold events, never as shadow RESETs. |
| Behavior policy | One-shot CONSERVE override for the **next actual advance** (same as v1b): it replaces the RECOVER policy's pre-advance choice for the next normal-speed interval only. The existing post-advance re-choice then restores the baseline rule before resolution. Free-initiative windows (no advance) do not consume the pending override. |
| Free initiative | If the hold happens in a Bottom free-initiative window, that window is consumed (already done at loop start) and initiative passes to Top. No free-initiative state is created or altered. |
| Setup | No setup event: `setup_state` is not touched and no build, advance, Ready or consumption occurs. |
| Submission | No submission event; submission state untouched. |
| Recognition / responder | No Recognition read and no response selection. Because the hold replaces the decision before any RNG draw (v0.2 ordering), **no RNG is consumed**. |
| History | Appends one entry `"{side}@{elapsed}s:stamina={current}"` to a new `RunHistory.recovery_hold_history` list. The new field defaults to empty, so every non-v1c run is unchanged. |
| Observers | The A9 handoff observer samples after a hold, as after any engine operation. A hold mutates no stamina, so the Case-A sampling proof is unaffected. |
| Next Bottom decision | Re-evaluated from current stamina. No persistent recovery state beyond the one-shot CONSERVE override. |

Prohibited: timers, protected-action counters, a permanent LOW state, stamina grants, altered recovery amounts, any change to Top, any change to responder settlement, and any routing of holds through RESET or stalling machinery.

`MountMatch.recovery_hold()` is opt-in engine surface used only by the v1c diagnostic mode. Existing call paths never invoke it. The frozen digest, all historical replays and the canonical policy must be unchanged (criteria 6-8).

## Handoff definition for criterion 13 (unchanged from v1b)

A clear at 35 gives `35 - 7 - 2 = 26 > 25`, so MEDIUM is requested and baseline behavior is restored by the post-advance re-choice. **The policy handoff is the clear window.** Otherwise it is the first later Bottom decision window that both runs baseline behavior and requests MEDIUM. Any re-entry before that return counts as a failed handoff.

## Pre-registration ledger note (prediction, not a result)

Traced path (unfunded Top, alternating initiative), recorded before any run:

```text
+0   clear 33 -> 35; MEDIUM safe (26 > 25) -> MEDIUM -7 -> 28
+5   ESCAPE -1                                         -> 27
+10  ESCAPE -1                                         -> 26; HOLD (no spend, no RESET)
+15  CONSERVE +2 (one-shot)                            -> 28
+20  ESCAPE -1                                         -> 27; HOLD
...  while holding: +2 -1 = net +1 per 10 s
     at 31: LOW safe (26 > 25) -> LOW -3 -> 28 -> ... -> 26; HOLD
```

Predictions recorded for later checking, not as results:

- **The same 26..31 sawtooth as v1b is likely.** Changing the fallback does not change the stamina ledger: a hold gains the same net +1 per 10 s as a RESET block, and LOW at 31 still returns to 26. **v1c may still never return to MEDIUM after its first hold on this path.** v1c's advantage over v1b is that it removes RESET/stalling exposure, not that it adds recovery speed.
- **Criterion 5 is expected to be relieved,** because holds add no RESET-with-route exposure. The remaining exposure comes only from genuine policy RESETs.
- **The passivity risk moves to criteria 12-15.** Expect many holds per armed match, long hold runs, and many matches never requesting MEDIUM again after their first hold. Criterion 13 is likely still satisfied at the clear window.
- **New stalling-design consideration:** holds are invisible to v0.3b. A reserve-limited hold cannot draw a stalling consequence, but the stalling clock keeps accumulating, so a later genuine RESET may be evaluated with a larger clock. This is recorded as a design consideration for any future player-facing use; it is not a D2 gate.

v1c is frozen as specified. A variant that changes recovery speed (for example, holding until a higher reserve before LOW) would be a different candidate and need its own preregistration.

---

# Sampling and denominators (unchanged)

Run the exact two E-PROD batches, 100 each, base seeds 42 and 142, 300 s, with E-PROD settings and v1c enabled, both OFF + shadow and ON. Also run adopted-policy controls at the canonical checkpoint/settings. No adaptive extensions, seed replacement, tuning, or outcome exclusions.

- Evaluate both pooled episode results and first-clear-per-match results.
- A horizon admits an episode if re-entry occurs within the inclusive horizon or the episode is observed through the horizon. Otherwise it is right-censored.
- A successful escape before the horizon is censored for stamina survival and reported separately.
- No-clear matches and clears at timeout are never survival successes.
- Report each batch and pooled results, every failure, censored counts, all 5/10/15/20/30 s horizons, complete 10/20/30 spend/recovery histograms, first actions, first-clear times and repeated cycles.
- Keep the original adoption numbers beside the new results.

---

# A. Preservation (all mandatory; unchanged except candidate naming)

1. Surface A (original 100 seeds/settings) exactly preserves 78 Threat matches, 1,950 Threat entries and Tap 0. Surface B exactly preserves Tap 9/100. v1c must be inactive on non-RECOVER surfaces.
2. Rule 1: zero responder commitment **or hold** charged on unfunded initiator exchanges. Rule 2 stays OFF; charges, refunds and their semantics are unchanged.
3. Bottom stamina stays within [0,100], with no fabricated recovery and no negative costs. E-PROD original-100 final median >=29. Setup-builder availability is retained; report attempts, advances, completions and post-clear action distributions.
4. Original-100 E-PROD:
   - escapes >=25 (adopted 35 - 10);
   - Half Guard 16, Open Guard 10 and Reversal 9 each within +/-10;
   - timeouts <=70 (adopted 60 + 10);
   - **Tap <=9/100 (adopted E-PROD 5/100 + 4)**.

   These are pragmatic tolerances, not statistical equivalence claims.
5. RESET-with-progress-route exposure <=23/100 (adopted 13 + 10). No real warning, penalty or position reset in E-PROD. OFF/ON gameplay divergence 0/100 for both seed batches when no offense fires, using full gameplay identity. RECOVERY HOLDs are not RESETs and add no exposure; genuine RESETs count with no carve-out.
6. Frozen Mount-v0 digest exactly `3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2`. Full unit suite, semantic checker and legacy entry point PASS. Supported-lane qualification comes from exact-head CI on Python 3.11 and 3.13; local system Python runs are supplementary. Deterministic replay of full gameplay traces, and observer ON/OFF full summary identity. Additionally, `recovery_hold()` is never invoked outside v1c, and `recovery_hold_history` is empty on every non-v1c surface.
7. v1c settings must show effective-settings and full gameplay equivalence across their explicit diagnostic entry points. The existing canonical production entry point stays identical to the adopted controls and unchanged. Canonical integration needs separate authorization, and candidate equivalence must not be described as equality to unchanged adopted gameplay.
8. Preserve all historical evidence, including the failed first Gate G, old Rule 2, and the v1/v1b preregistrations. Report adoption A1-A10 and Gates A-H as historical results, not as proof that D2 passes.

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
14. Hold diagnostics, formerly reserve-block diagnostics (mandatory reporting; descriptive):
    - RECOVERY HOLD opportunities (total, per match, and per armed match);
    - longest and distribution of consecutive holds;
    - time in reserve recovery: simulated seconds from each hold until the next funded Bottom initiation (or match end, reported as pending);
    - Bottom stamina at the first decision window where `safe(MEDIUM)` holds again after a hold;
    - matches never returning to a MEDIUM request after their first hold;
    - LOW requests made by the reserve rule (MEDIUM unsafe, LOW safe), separately from Exhausted LOW;
    - re-entries classified by cause (initiation spend, behavior drain, responder/hold spend).

# C. Reserve-model and hold diagnostics (mandatory reporting; descriptive, not gates)

15. Reserve model (unchanged from v1b). For every armed, non-Exhausted Bottom decision window:
    - the predicted behavior reserve used (always 2);
    - the actual Bottom behavior drain before Bottom's next decision (or truncated at match end);
    - reserve-model violations (actual drain > 2) with their control-flow sequence;
    - v1-versus-v1c classification of the counterfactual decision v1 (reserve 0) would have made: same, MEDIUM -> LOW, MEDIUM -> HOLD, or LOW -> HOLD, with counts per batch and pooled.

15b. **NEW, recovery-hold diagnostics:**
    - total holds, and holds per match (distribution);
    - consecutive holds (longest; distribution);
    - simulated seconds in hold state: from a hold to Bottom's next funded initiation or match end (pending);
    - initiative transitions caused by holds (each hold passes initiative to Top), plus any free-initiative windows consumed by a hold;
    - setup/submission opportunities forgone: holds where Bottom had a legal setup-builder or progress-capable action available;
    - holds with a progress route available ("would have been RESET-with-route" under v1b), reported as an explicit counterfactual and never added to criterion-5 exposure;
    - Bottom stalling clock at each hold, and any later genuine-RESET offense whose clock includes hold-time accumulation;
    - matches where more than 50% of post-clear Bottom opportunities were holds (descriptive; not a gate);
    - confirmation that no hold consumed RNG, spent or granted stamina, touched setup/submission state, or appeared in `reset_window_history`.

    These diagnostics are descriptive. They cannot PASS or FAIL D2, alter `behavior_reserve` or hold semantics, or authorize retuning.

# Decision and hard stops

All A and B criteria must pass for a D2 design-gate PASS. A candidate failing any criterion is recorded with exact SHA/settings, then STOP: no tuning and no silent criteria change. Missing evidence gives OPEN.

After this commit: HARD STOP for review of this exact SHA and explicit D2 authorization. After D2 evidence: HARD STOP again. Not authorized here: main changes, merges into main, squash, frontend work, canonical production-policy changes, Rule 2 work, or default changes.
