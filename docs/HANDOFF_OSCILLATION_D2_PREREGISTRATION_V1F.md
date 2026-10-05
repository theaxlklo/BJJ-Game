# D2 Handoff-Oscillation Preregistration — Revision v1f (persistent-CONSERVE recovery mode with reserve-safe LOW; MEDIUM-only release)

## Status

**PROPOSED PREREGISTRATION REVISION — FROZEN AT ITS COMMITTING SHA — HARD STOP FOR REVIEW.**

This revision selects **POST-CLEAR RESERVE-AWARE HANDOFF v1f** as the next D2 candidate. It becomes binding only after the user reviews this exact SHA and explicitly authorizes D2 implementation and measurement. v1f has not been implemented or run.

It **supersedes v1e only as the selected future candidate**. The v1e measurement stays on record, unchanged, as a D2 FAIL:

```text
D1 evidence:                      cdb04a0c603dbfa1b2c9a41d66f877334a848869
v1 / v1b / v1c preregistrations:  62309599 / f624db2c / f30ace90
v1d preregistration:              8dcaabb5a633768a85005b1845132d78fc80d9a0
v1e preregistration (frozen):     c4a9c3369b53911eda4d47dd9d814d385470ba8a
v1e implementation (pre-run):     d00c48e5ecc7e1523924c26927119b2e3967fa59
v1e measured result: D2 FAIL:     fe229cbd28b2dbf7e430c2664637959f8dccd366
                                  docs/HANDOFF_OSCILLATION_D2_V1E_RESULT.md
adopted baseline (PR #10):        ee6cb6fcebb105e31224bead48a302811b27b59a
canonical policy:                 PRODUCTION_STAMINA_RECOVERY_POLICY (unchanged)
frozen digest:                    3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

Review record at `fe229cb`, accepted by the user:
- The v1e result is **FAIL on criterion 4 only**: original-100 escapes 17 (>=25 required; adopted 35) and timeouts 78 (<=70 required; adopted 60).
- v1e removed re-exhaustion completely (0/68 at 10 s, 0/59 at 30 s, against the adopted 64/69 and 64/64) and passed the post-hold return gate 44/44.
- Seed-matched attribution, 28 adopted escapes lost:

  | Adopted escaping attempt | Lost under v1e |
  |---|---|
  | The adopted +10 s MEDIUM after the clear | 18 |
  | Exhausted LOW at +20 to +50 s | 9 |
  | A later MEDIUM | 1 |

- Criterion 4 is not loosened, and v1e is not retuned.

Design lineage, all decided before the respective measurements:

```text
D1  cdb04a0  oscillation characterized: 35 -> 28 -> 27 -> 26 -> 19
v1  6230959  initiation-only reserve                         (not run)
v1b f624db2  + behavior reserve 2, RESET fallback            (not run)
v1c f30ace9  + non-RESET hold                                (not run)
v1d 8dcaabb  + hold mode, MEDIUM-only release, one-shot CONSERVE (not run)
v1e c4a9c33  + persistent CONSERVE in mode; + criterion 16   MEASURED fe229cb: FAIL (criterion 4)
v1f (this)   + reserve-safe LOW attempts inside the mode; LOW does not release
```

The question v1f tests: **can Bottom do reserve-safe LOW tactical work during recovery without giving up v1e's stable, timely return to MEDIUM?** v1e showed that the existing CONSERVE rate already gives a stable reserve and timely release. Its failure was that Bottom spent too many recovery windows doing nothing.

## Changes versus v1e

| Item | v1e (`c4a9c33`) | v1f (this revision) |
|---|---|---|
| Reserve-safe rule | `stamina - cost(c) - 2 > 25` | **unchanged** |
| Decision outside the mode | MEDIUM if safe, else LOW if safe, else ENTER + HOLD | **unchanged** |
| Decision inside the mode | RELEASE + MEDIUM if `safe(MEDIUM)`, else HOLD | RELEASE + MEDIUM if `safe(MEDIUM)`; **else LOW if `safe(LOW)`, staying in the mode**; else HOLD |
| A LOW-safe window in the mode where the policy picks no action | (not reachable) | **genuine RESET** through `reset_window()`; the mode stays active |
| Release | only `safe(MEDIUM)` | **unchanged**: only `safe(MEDIUM)`. LOW never releases |
| Mode termination | release, re-exhaustion, match end | **unchanged** |
| Persistent pre-advance CONSERVE in the mode | yes | **unchanged**, including after a LOW attempt or a genuine RESET in the mode |
| Post-advance behavior re-choice | unchanged | **unchanged** (CONSERVE is not forced through resolution) |
| `MountMatch.recovery_hold()` | v1c semantics | **unchanged** |
| Criteria 1-16 | as frozen | **unchanged** (two textual clarifications in 5 and 14 only) |
| Diagnostics | 15, 15b, 15c, 15d | kept; **15e (LOW-in-mode) and 15f (three-way seed-matched attribution) added** |

Frozen constants (unchanged; listed so that no silent change is possible):

```text
behavior_reserve           = 2
cost(LOW)                  = 3
cost(MEDIUM)               = 7
exhaustion_enter_threshold = 25   (StaminaPool, maximum 100)
exhaustion_clear_threshold = 35   (StaminaPool, maximum 100)
recovery amount            = Bottom CONSERVE +2 per 5 s behavior quantum
behavior drain             = Bottom ESCAPE -1 per 5 s behavior quantum
safe(LOW)    <=> stamina - 3 - 2 > 25 <=> stamina >= 31
safe(MEDIUM) <=> stamina - 7 - 2 > 25 <=> stamina >= 35   (the only release)
Rule 1 = ON, Rule 2 = OFF
```

---

# Selected candidate: POST-CLEAR RESERVE-AWARE HANDOFF v1f

## Scope and arming (unchanged from v1e)

- Bottom only, and only with `bottom_behavior_mode=RECOVER` (ESCAPE baseline), v0.2 setup ordering, v0.4a semantics, LOW_WHILE_EXHAUSTED, Rule 1 ON, Rule 2 OFF, no settlement umbrella, and baseline MEDIUM (E-PROD). Any other configuration requesting v1f is rejected. v1f is inactive on Surfaces A and B, and Top is never affected.
- **Armed** after Bottom's first Exhausted -> non-Exhausted latch clear in the match, for the rest of the match. v1f acts only at non-Exhausted Bottom decision windows of an armed match, plus the pre-advance behavior choice while the mode is active.
- **Before the first clear, gameplay is identical to the adopted policy** (and to v1e).
- Implemented as a new opt-in diagnostic mode value, alongside v1e. **v1e's mode, code path and pinned evidence must remain unchanged and reproducible.** Raw defaults and the canonical production policy are unchanged.

## State (unchanged from v1e)

```text
recovery_hold_mode : bool   per match, initially False
```

It is owned by the batch-side diagnostic controller. There is no timer and no counter, and it is discarded at match end.

## Decision at an armed Bottom decision window (frozen)

The safety rule is evaluated on current stamina at the Bottom decision window: after that window's advance (if any) and the post-advance re-choice, and before action selection.

```text
if Bottom is Exhausted:
    recovery_hold_mode := False          (if it was True: record CLEARED_BY_EXHAUSTION)
    adopted LOW_WHILE_EXHAUSTED decision, unchanged

elif recovery_hold_mode:
    if safe(MEDIUM):
        recovery_hold_mode := False      (record RELEASE)
        request MEDIUM; normal action selection
    elif safe(LOW):
        request LOW; normal action selection          (record MODE_LOW)
        recovery_hold_mode stays True
        if policy.choose returns no action:
            genuine RESET via reset_window()          (record MODE_LOW_RESET)
            recovery_hold_mode stays True
    else:
        RECOVERY HOLD

else:                                    (ordinary decision; unchanged)
    if safe(MEDIUM):   request MEDIUM, normal action selection
    elif safe(LOW):    request LOW, normal action selection
    else:
        recovery_hold_mode := True       (record ENTER)
        RECOVERY HOLD
```

### LOW inside the mode (NEW, frozen)

- **Pipeline:** LOW is the requested commitment and feeds the unchanged pipeline: effective-commitment funding, Recognition read of the actual request, response selection, settlement (Rule 1 ON, Rule 2 OFF), setup, submission and exit resolution. Nothing about an in-mode LOW attempt differs from an ordinary LOW attempt.
- **The mode stays active after a LOW attempt.** The next normal advance is still forced CONSERVE.
- **LOW never releases the mode.** Release happens only at a Bottom window where `safe(MEDIUM)` holds.
- **Exits:** if the LOW attempt ends the match (escape or reversal), the mode ends with the match (`PENDING_AT_END` with terminal type exit). That is not a release.
- **Re-exhaustion:** if the LOW attempt, or any later spend, makes Bottom Exhausted, the mode ends at Bottom's next decision window (`CLEARED_BY_EXHAUSTION`), as in v1e.

### Genuine RESET at a LOW-safe window in the mode (option (a), frozen)

```text
LOW is the requested commitment
-> normal policy.choose() runs
-> policy returns no action
-> genuine RESET: reset_window()
-> normal v0.3b stalling / progress-route / warning / penalty / position-reset /
   free-initiative semantics apply (real on ON; shadow-evaluated on OFF + shadow)
-> recovery_hold_mode remains active
```

- This RESET is **not** a RECOVERY HOLD. It is never reinterpreted as one, and it appears in `reset_window_history`.
- It counts toward Bottom RESET totals and toward criterion-5 RESET-with-progress-route exposure, with **no carve-out**.
- It does not release or end the mode.
- No RNG is consumed before it beyond what an ordinary RESET consumes. Under v0.2 ordering, `policy.choose` runs before any Recognition or response draw.

The same rule already applies, unchanged from v1e, to a RELEASE window where `policy.choose` returns no action: it is a genuine RESET, and the mode stays released.

### Hold, persistence, clock, stalling, history (unchanged from v1e)

- **RECOVERY HOLD:** exactly the v1c/v1e `MountMatch.recovery_hold()`. No stamina spend or grant, no simulated time, initiative passes to Top, no RESET semantics, no stalling evaluation, no setup/submission/Recognition change, no RNG, recorded only in `recovery_hold_history`.
- **Persistence:** the mode persists across initiative changes, Top windows, free-initiative windows, in-mode LOW attempts and in-mode genuine RESETs.
- **Free initiative:** a Bottom free-initiative window in the mode is evaluated by the same in-mode decision (release, LOW or hold). It has no advance, so it applies no behavior.
- **Persistent CONSERVE:** on every normal advance while `recovery_hold_mode` is True, Bottom's pre-advance behavior is CONSERVE. The post-advance re-choice is unchanged, so resolution, previews, Recognition inputs and progress-route detection see the baseline behavior (ESCAPE while non-Exhausted). CONSERVE keeps its existing stamina effect (+2 per quantum) and its existing positional-drift effect (aliased to PROTECT: +0.75 instead of +0.50 per 5 s interval against Top PRESSURE). Neither is special-cased.
- **History and observers:**
  - Holds append to `recovery_hold_history`.
  - The batch-side collector records mode transitions (`ENTER`, `RELEASE`, `CLEARED_BY_EXHAUSTION`, `PENDING_AT_END`) and the in-mode decision kinds (`MODE_LOW`, `MODE_LOW_RESET`).
  - Collectors are read-only, consume no RNG and mutate no engine state.
- **Match end:** any terminal event ends the mode. Pending is never a release.

Prohibited:
- timers, protected-action counters and stamina grants;
- altered recovery amounts, drains, drift rates or behavior modifiers;
- LOW releasing the mode;
- reinterpreting a LOW-safe no-action window as a hold;
- forcing CONSERVE through resolution;
- any change to Top, or to responder or provisional-hold settlement;
- routing holds through RESET or stalling machinery.

## Handoff definition for criterion 13 (unchanged)

A clear at 35 gives `35 - 7 - 2 = 26 > 25`, so MEDIUM is requested at the clear window. **The criterion-13 handoff is the clear window.** Post-hold release is gated separately by criterion 16.

---

# Pre-registration ledger note (prediction, not a result)

Traced path: Top PRESSURE and unfunded, alternating initiative, no free windows. The values are Bottom stamina at Bottom decision windows, 10 s apart. Between consecutive Bottom windows in the mode there are two forced-CONSERVE advances (+4). An in-mode LOW spends 3, so each LOW window nets **+1** to the next Bottom window. A hold nets **+4**.

```text
+0    clear 33 -> 35; MEDIUM safe (26 > 25) -> MEDIUM -7          -> 28
+5    ESCAPE -1                                     (Top window)  -> 27
+10   ESCAPE -1   26: ENTER mode, HOLD                             26
+20   CONSERVE x2                     30: HOLD     (LOW 25, unsafe)     30
+30   CONSERVE x2                     34: LOW -3 (stay in mode)    34 -> 31
+40   CONSERVE x2                     35: RELEASE, MEDIUM -7       35 -> 28
+45   ESCAPE -1                                     (Top window)  -> 27
+50   ESCAPE -1   26: ENTER mode, HOLD (cycle 2)                    26
```

**Release delay depends on entry stamina.** Because each in-mode LOW nets +1 and release needs exactly 35, a cycle's shape is fixed by its entry stamina (entry <= 30 by definition):

| Entry stamina | Bottom windows in the cycle | Entry -> release | Criterion 16 (<= 40 s) |
|---|---|---|---|
| 26 | H(26), H(30), L(34), M(35) | **30 s** | timely |
| 27 | H(27), L(31), L(32), L(33), L(34), M(35) | **50 s** | **late: criterion-16 failure if it is a first cycle with >= 40 s left** |
| 28 | H(28), L(32), L(33), L(34), M(35) | **40 s** | timely (boundary, inclusive) |
| 29 | H(29), L(33), L(34), M(35) | **30 s** | timely |
| 30 | H(30), L(34), M(35) | **20 s** | timely |

- On the traced path, release always lands on exactly 35. MEDIUM then gives 28, and two ESCAPE drains give 26. **The steady-state cycle is therefore entry 26: H, H, L, M, every 40 s.** That is 2 Bottom initiations (1 LOW, 1 MEDIUM) per 4 Bottom windows, with 50% of Bottom windows held.
- For comparison:
  - v1e had 1 MEDIUM per 3-4 windows, about 69-77% held.
  - The adopted policy initiated at every Bottom window after re-exhausting at +10 s.

Predictions recorded for later checking, not as results:

1. **Criterion 4 remains materially at risk.** v1f still removes the adopted +10 s MEDIUM, because the +10 s window is at 26 and is a hold. That attempt produced **18 of v1e's 28 lost escapes**, and v1f cannot restore it. To pass, v1f must recover enough later escape production, from in-mode LOW at about +30 s, from the release MEDIUM at about +40 s, and from later cycles, to move original-100 escapes from 17 to at least 25 (+8) and timeouts from 78 to at most 70. With a median first clear at 240 s of 300 s, typically only one or two cycles fit after the first clear. **This warning stays visible whatever the eventual result.**
2. **Criterion 16 has a specific predicted failure mode.** A first cycle that enters at 27 releases after 50 s, a late release and a failure.
   - Entry at 27 needs a clear above 35 (for example 34 + 2 = 36, giving MEDIUM 29 -> 28 -> 27), or a responder/provisional-hold charge before entry.
   - D1 and v1e observed every clear at exactly 35, and every v1e first cycle entered at 26. So entry-27 first cycles are expected to be rare but are possible.
   - Entry 28 releases exactly at the 40 s boundary (timely).
   - Re-exhaustion before release and match end before release remain failures, as frozen.
3. **Criteria 9-10 are expected to remain closed on the traced path.**
   - An in-mode LOW leaves Bottom at 31 (from 34) or at 28-31 (from 31-34). The next two advances are CONSERVE, so behavior drain cannot re-exhaust Bottom.
   - The remaining re-entry path is a Top-funded exchange: a responder or provisional-hold charge of at least 3 at stamina 28.
4. **Criterion 5 exposure returns partly.** Genuine RESETs at LOW-safe in-mode windows count with no carve-out. v1e's exposure was 13 (original 100) against the bound of 23. v1f adds every LOW-safe window where the policy picks no action and a progress route exists. Every v1e hold window (304/304) had a progress-capable action available. That suggests, but does not guarantee, that most LOW-safe windows will be attempts rather than RESETs: the policy's own selection rule decides.
5. **Criterion 12 is predicted to PASS by construction** (pre-clear gameplay identical: 45 / 82 / 240 s).
6. **Positional drift is unchanged in kind** (persistent CONSERVE in the mode). The mode now also contains LOW attempts, so post-release and in-mode LOW attempts will often start in STRONG/LOCKED (-1 positional modifier for Bottom). This may limit how many escapes in-mode LOW recovers.
7. **Mode-induced behavior-switch bookkeeping** continues (two flips per forced advance) and is reported separately.

v1f is frozen as specified. Any change to the release threshold, the in-mode LOW rule, the RESET semantics, the CONSERVE scope, the reserve or the gate tolerances would be a different candidate needing its own preregistration.

---

# Sampling and denominators (unchanged from v1e)

Run the exact two E-PROD batches, 100 each, base seeds 42 and 142, 300 s, with E-PROD settings and v1f enabled, both OFF + shadow and ON.

**Comparators**, all on the same seeds and stalling modes:
- the adopted canonical controls (`PRODUCTION_STAMINA_RECOVERY_POLICY`);
- **the v1e candidate as frozen**, reproduced from the unchanged v1e code path, which must equal the recorded `fe229cb` evidence.

No adaptive extensions, seed replacement, tuning, or outcome exclusions.

All admissibility, censoring and denominator rules are unchanged from v1e. That includes criterion 16's eligibility rule (>= 40 s remaining at entry), under which an eligible cycle that does not release in time is a failure.

---

# Criteria (1-16 unchanged)

Criteria 1-14 and 16 are **identical to `docs/HANDOFF_OSCILLATION_D2_PREREGISTRATION_V1E.md`**, with "v1e" read as "v1f" wherever a criterion names the candidate. That covers their thresholds, denominators, OPEN/FAIL rules and wording.

In summary:

```text
A. Preservation (all mandatory)
 1  Surface A 78 / 1,950 / Tap 0; Surface B Tap 9; v1f inactive on non-RECOVER surfaces
 2  Rule 1 exact (no responder commitment or provisional hold charged on unfunded exchanges); Rule 2 OFF
 3  Bottom stamina in [0,100]; no fabricated recovery or negative cost; original-100 final median >= 29
 4  Original-100: escapes >= 25; Half 16 / Open 10 / Reversal 9 each +/-10; timeouts <= 70; Tap <= 9
 5  RESET-with-progress-route <= 23/100; no real W/P/PR; OFF/ON divergence 0/100 per batch
 6  Digest exact; suite / checker / legacy PASS; exact-head CI 3.11 + 3.13; deterministic replay;
    observer ON/OFF identity; recovery_hold() never invoked outside v1e/v1f;
    recovery_hold_history empty on every non-candidate surface
 7  Effective-settings and gameplay equivalence across v1f's diagnostic entry points;
    canonical production entry point unchanged
 8  All historical evidence preserved, including the v1e FAIL record

B. Absolute handoff stability (all mandatory)
 9  re-exhaustion within 10 s <= 0.20 (pooled episodes and first clear per match)
10  re-exhaustion within 30 s <= 0.35 (both denominators)
11  each pooled denominator >= 43 at 10 s and 30 s
12  clearing matches original >= 40, pooled >= 75; first-clear median <= 250 s (both)
13  clear-window handoff: >= 43 matches with return; >= 43 admissible at +10/+30 s;
    <= 0.20 / <= 0.35 from return; pre-return re-entries are failures
14  hold diagnostics (mandatory reporting)
16  post-hold return gate: first cycle eligible with >= 40 s remaining at entry;
    >= 35 eligible pooled matches; >= 80% release to MEDIUM within <= 40 s;
    re-exhaustion before release, match end before release and late release are failures;
    pending-at-end is never a success. Evaluated separately for OFF + shadow and ON; both must pass.
```

Textual clarifications only (no change in substance):

- **Criterion 5:** genuine RESETs at LOW-safe in-mode windows (`MODE_LOW_RESET`) count toward RESET-with-progress-route exposure and Bottom RESET totals with no carve-out. They are also reported separately in 15e.
- **Criterion 14:** "LOW requests made by the reserve rule" are reported in two classes: outside the mode (MEDIUM unsafe, LOW safe, mode inactive) and **inside the mode** (`MODE_LOW`). Both are separate from Exhausted LOW.

All A and B criteria (1-14 and 16) must pass for a D2 design-gate PASS. A candidate failing any criterion is recorded with exact SHA/settings, then STOP: no tuning and no silent criteria change. Missing evidence gives OPEN. Unit, checker and CI PASS never soften a FAIL or an OPEN.

# C. Diagnostics (mandatory reporting; descriptive, not gates)

**15, 15b, 15c, 15d:** unchanged from v1e. These cover the reserve model with v1/v1c attribution, hold diagnostics, mode/cycle/release diagnostics, and persistent-CONSERVE diagnostics including realized versus counterfactual drift, band exposure and the behavior-switch split. Two additions:
- The reserve-model check for in-mode windows predicts a net change to Bottom's next window of **+4 after a hold** and **+1 after a funded in-mode LOW**. Every window where the actual change is lower is listed with its cause.
- The decision-kind attribution against v1 and v1c gains the class **"LOW in mode"**, and is also reported **against v1e** at the same state.

**15e. NEW, LOW-in-mode diagnostics:**
- In-mode LOW windows, split into **attempts** (`MODE_LOW`) and **genuine RESETs** (`MODE_LOW_RESET`): total, per match, per cycle.
- In-mode LOW attempts: actions, effective commitment (funding), grade distribution, and immediate exits (escape / reversal) by type.
- In-mode LOW setup activity: setup-builder attempts, setup advances, Ready completions, and later consumption of setups built in the mode.
- `MODE_LOW_RESET` RESETs: count; how many had a progress route (criterion-5 contribution); real or shadow stalling clock at each; any warning, penalty, position reset or free-initiative window they produced.
- Number of in-mode LOW windows before each release; release delay by entry stamina (26 / 27 / 28 / 29 / 30), with every late release listed.
- Re-exhaustion following an in-mode LOW (within 10 s and 30 s, frozen censoring rules), with cause.
- Simulated seconds between consecutive funded Bottom initiations after the first clear (distribution), against v1e and adopted.
- Bottom-window decision shares after the first entry: hold / in-mode LOW / in-mode RESET / release MEDIUM / ordinary.
- Traced prediction versus reality: entry-stamina distribution, cycle shapes, steady-state H,H,L,M share, initiation rate, time in mode.

**15f. NEW, three-way seed-matched attribution (mandatory reporting).** Matches are paired by pooled index (same seeds, same stalling mode). All three runs are identical before the first clear, so every difference arises after it.
- **Adopted vs v1f** and **v1e vs v1f:** complete match-by-match outcome transition tables.
- **v1e's 28 lost escapes** (adopted escape -> v1e timeout), each listed with:
  - whether v1f restores an escape in that match;
  - the v1f escaping attempt (time from clear, decision kind such as `MODE_LOW`, release MEDIUM or ordinary, requested and effective commitment, band);
  - whether it matches the adopted escaping attempt's class (adopted +10 s MEDIUM, Exhausted LOW, or other).
- **Escapes v1e preserved or gained that v1f loses**, each listed with the cause.
- **New escapes in v1f** that neither adopted nor v1e produced.
- **Timeouts recovered relative to v1e,** and timeouts added relative to adopted.
- **Escapes restored by source:** in-mode LOW, release MEDIUM, ordinary decision, Exhausted LOW after a re-exhaustion.
- Tap transitions in both comparisons.

These diagnostics are descriptive. They cannot PASS or FAIL D2, alter `behavior_reserve`, the release rule, the in-mode LOW rule, the RESET semantics, the CONSERVE scope or hold semantics, or authorize retuning.

# Compatibility review of the existing gates

Each criterion was checked against the v1f semantics before freezing. None is logically incompatible, and no threshold is changed:

- 1, 6, 7, 8: v1f is opt-in and RECOVER-only. v1e stays reproducible, and the surfaces, digest and canonical entry point are untouched.
- 2, 3: computable unchanged. An in-mode LOW is an ordinary funded attempt under Rule 1 ON / Rule 2 OFF.
- 4: computable unchanged and **at material risk** (prediction 1). That is a risk, not an incompatibility.
- 5: computable unchanged. In-mode genuine RESETs count with no carve-out.
- 9-13: unchanged definitions. The criterion-13 handoff is still the clear window.
- 16: computable unchanged. The entry-27 late-release case (prediction 2) is a predicted failure mode, not an incompatibility.

# Decision and hard stops

After this commit: HARD STOP for review of this exact SHA and explicit D2 authorization. After any D2 evidence: HARD STOP again.

Not authorized here: v1f implementation, v1f measurement, any change to the recorded v1e evidence, canonical integration, any change to `PRODUCTION_STAMINA_RECOVERY_POLICY`, PR #10 changes or merge, Rule 2 work, default changes, frontend work, squash, force-push.
