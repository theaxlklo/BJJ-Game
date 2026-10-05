# D3 — Bounded Burst / Exhausted Recovery Lockout: Research and Preregistration

## Status

**PROPOSED PREREGISTRATION — FROZEN AT ITS COMMITTING SHA — HARD STOP FOR REVIEW.**

This is a new experiment family, D3. It is documentation only: no gameplay, engine, batch, policy or test code is changed. It becomes binding only after the user reviews this exact SHA and explicitly authorizes D3 implementation and measurement.

```text
branch:                         review/burst-recovery-lockout-d3   (created from 88a01e9)
adopted baseline (PR #10):      ee6cb6fcebb105e31224bead48a302811b27b59a
canonical policy:               PRODUCTION_STAMINA_RECOVERY_POLICY (unchanged)
frozen digest:                  3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2

D1 characterization:            cdb04a0c603dbfa1b2c9a41d66f877334a848869
D2 v1 / v1b / v1c / v1d prereg: 62309599 / f624db2c / f30ace90 / 8dcaabb5
D2 v1e preregistration:         c4a9c3369b53911eda4d47dd9d814d385470ba8a
D2 v1e implementation:          d00c48e5ecc7e1523924c26927119b2e3967fa59
D2 v1e measured result:         fe229cbd28b2dbf7e430c2664637959f8dccd366   D2 FAIL (criterion 4)
D2 v1f preregistration:         88a01e9a30f66a50d1d2d3114557df0924785980   never implemented or run
```

D2 stays historically as recorded: **v1e = stability PASS, tactical preservation FAIL, overall FAIL.** v1f stays preregistered and never run. Nothing in D2 is edited or reinterpreted here.

---

# 1. Historical evidence

**D1 (adopted policy).** The traced ledger was:

```text
33 -> CONSERVE +2 -> 35 (Exhausted clears) -> MEDIUM -7 -> 28
+5 ESCAPE -> 27; +10 ESCAPE -> 26 -> MEDIUM -7 -> 19 (Exhausted again)
```

The adopted A9 result was 64/69 admissible clears re-exhausted within 10 s (p = 0.927536231884058).

**D2 v1e** (persistent-CONSERVE recovery hold until MEDIUM is reserve-safe; `fe229cb`):

| Original-100 E-PROD | Adopted | v1e | Frozen bound |
|---|---|---|---|
| Escapes | 35 | 17 | >= 25 |
| Timeouts | 60 | 78 | <= 70 |

- **Stability:** re-exhaustion within 10 s went from 64/69 to 0/68; the post-hold return gate passed 44/44.
- **Seed-matched attribution:** 28 adopted escapes were lost. 18 were the adopted +10 s MEDIUM after the clear, 9 were Exhausted LOW attempts at +20 to +50 s, and 1 was a later MEDIUM.

# 2. Why D2 failed

D2 took "rapid post-clear re-exhaustion" as the defect and gated on it (criteria 9-10: re-exhaustion within 10 s <= 0.20). Satisfying that gate means the +10 s MEDIUM at stamina 26 must not happen, because that is the spend that re-exhausts Bottom.

v1e's attribution shows that this same MEDIUM was the escaping attempt in 18 matches. **D2's stability objective and the adopted policy's most productive post-clear attack were the same event.** Any D2 candidate that passes criteria 9-10 on the traced path must remove that attack. v1f, preregistered and never run, keeps the +10 s hold and therefore inherits the same loss.

# 3. New problem definition

D3 separates two things D2 treated as one:

```text
INTENTIONAL BURST RE-EXHAUSTION   clear -> MEDIUM -> +10 MEDIUM -> Exhausted      (valuable; keep)
UNBOUNDED EXHAUSTED-SPEND         Exhausted -> LOW -> LOW -> LOW ... (recovery barely
                                  keeps up; the latch practically never clears)    (the debt)
```

New evidence from the adopted control logs: `docs/evidence/handoff_d2_v1e_evidence.json.gz`, adopted runs, both seeds, OFF + shadow. This is existing evidence; no new run was made.

- In all **63/63** matches where Bottom becomes Exhausted again after its first clear, the re-entry happens **exactly 10 s after the clear**, at **stamina 19**, caused by **Bottom's own MEDIUM initiation**.
- After that re-entry, the adopted Bottom **re-clears in only 1/63 matches** within the match (once, after 130 s). It keeps spending Exhausted LOW (3 per Bottom window) while CONSERVE recovers 4 per 10 s, a net +1 per 10 s. From 19 the latch would need about 160 s to clear, longer than the time left in almost every match.
- The real "oscillation" is therefore not a fast cycle. It is **one productive burst, followed by a long Exhausted LOW grind** (-1 initiator grade modifier, and Bottom is an Exhausted responder giving Top +1) that rarely ends.

**D3 hypothesis:** keep the burst, including the +10 s MEDIUM that re-exhausts. Once that burst has made Bottom Exhausted, stop Bottom-initiated spending until the existing latch genuinely clears. The intended invariant is:

> Once an armed Bottom is Exhausted, Bottom makes no initiation (and spends no initiation stamina) until the Exhausted latch clears.

# 4. External references

**NONE.** No external project was consulted for this preregistration. The design rests only on this engine and its measured evidence. (Research into external stamina systems was optional in the brief, and was skipped so that no outside precedent shapes the frozen semantics.)

---

# 5. Engine audit (inspected at `88a01e9`)

## A. Initiation spends while Exhausted (adopted policy)

- **Requested commitment.** In `run_escape_first_batch`, `bottom_recovery_exhausted_turn = side is BOTTOM and bottom_behavior_mode is RECOVER and bottom band is EXHAUSTED`. With `LOW_WHILE_EXHAUSTED` the requested commitment is LOW; otherwise it is the baseline MEDIUM. This applies to every Exhausted Bottom decision window: before the first clear and after it alike, normal or free.
- **Action selection** is unchanged: `EscapeFirstInitiatorPolicy.choose(match)` (escape, then submission progress, then setup builder with value, then positive position attack, else RESET). It does not take the commitment as input.
- **Effective commitment.** `StaminaCostPolicy.effective_commitment` returns the highest commitment at or below the requested one whose full cost is no more than current stamina (LOW 3, MEDIUM 7, HIGH 12). LOW is **unaffordable only below 3 stamina**, which gives effective commitment `None` (UNFUNDED) and cost 0.
- **Actual spend.** In `MountMatch.attempt`, after resolution, setup and submission updates: `spend = pool.spend_up_to(effective_cost)`. **Every resolved attempt spends its effective cost, whatever the outcome**, including failed, partial and escaping attempts. RESET and holds spend nothing.
- **Exhaustion grade effects:** -1 for an Exhausted initiator and +1 for the attacker when the responder is Exhausted (`ExhaustionPolicy`).
- **Setup builders while Exhausted:** yes. Adoption Gate D recorded 1,227 Exhausted setup-builder attempts.
- **Submissions** belong to Top only (Americana). Bottom never progresses a submission. Top's submission track can progress while Bottom is Exhausted, and the Exhausted-responder +1 helps it.
- **Can a LOW initiation escape immediately?** Yes. 9 adopted escapes lost under v1e came from Exhausted LOW attempts.

## B. Responder spends while locked

- **Responder commitment.** When Top initiates, Bottom's response commitment is charged `responder_pool.spend_up_to(response_effective_cost)`, unless Rule 1 applies (Top UNFUNDED, `effective_commitment is None`): then the response cost is waived (`spend_up_to(0)`).
- **Provisional submission hold** (Americana finish CONTESTED, or Ready arm isolation CONTESTED): nominal 3 (LOW cost).
  - Under Rule 1 with an UNFUNDED Top it is waived.
  - With Rule 2 OFF and a funded Top, the legacy full hold is charged in addition to the response commitment. This is the known double-charge debt, out of scope here.
- **Can Bottom lose stamina while locked?** Yes, from a funded Top. That lowers Bottom's stamina and delays the clear, but Bottom is already Exhausted, so it cannot "re-enter" while locked.
- **Observed exposure.** In the adopted control logs, Top made 204 attempts during the post-clear Exhausted windows of the 63 matches, and **0 stamina** was charged to Bottom as responder. Post-clear, Top is UNFUNDED, so Rule 1 waives both charges.
- **Blocking responses would alter separate mechanics:** responder affordability, Rule 1/Rule 2 settlement, and responder grade and Recognition response selection. **Frozen decision: the lockout blocks only Bottom-initiated spending. Defensive responses are unchanged.**

## C. Behavior stamina

- `DEFAULT_BEHAVIOR_STAMINA_POLICY`, per 5 s quantum: Bottom CONSERVE +2, ESCAPE -1, PROTECT 0.
- `AdaptiveBehaviorPolicy` (RECOVER) already chooses **CONSERVE whenever Bottom is Exhausted**, and the baseline ESCAPE otherwise. That covers both the pre-advance choice and the post-advance re-choice.
- **Drift:** CONSERVE is aliased to PROTECT for drift. Against Top PRESSURE that is +0.15/s (+0.75 per 5 s), against ESCAPE's +0.10/s (+0.50 per 5 s), clamped at axis 4.00.
- **The existing Exhausted behavior already supplies all the recovery D3 needs.** D3 needs **no forced CONSERVE** and no non-Exhausted CONSERVE. v1e's structural side effect (forced CONSERVE while non-Exhausted) does not exist in D3.

## D. Reusing `MountMatch.recovery_hold()`

- **Semantics:** Bottom-only. No stamina spend or grant, no simulated time, no stalling evaluation, progress-opportunity record or engagement, no setup, submission or Recognition change, and no RNG. Initiative passes to Top, and one entry is appended to `RunHistory.recovery_hold_history`.
- **It has no stamina-band precondition, so it is valid while Exhausted.** It raises only for a Top initiator, at timeout, or when Mount is broken.
- **Generic enough:** it means "Bottom declines this decision window without RESET semantics", which is exactly the lockout's opportunity consumption.
- **History name:** keep `recovery_hold_history`. The D3 collector distinguishes lockout holds by decision kind (`LOCKOUT_HOLD`). A distinct transition would duplicate identical engine semantics and add engine surface for no behavioral difference. **Frozen: reuse `recovery_hold()` unchanged. D3 adds no engine code.** Updating its docstring to mention D3 is the only engine-file change permitted at implementation, and it is not a behavior change.
- **Initiative, clock, RNG, stalling, setup and submission:** as above. A lockout hold is never a RESET, never stalling-evaluated, and never shadow-evaluated.

## E. Free initiative

`consume_free_initiative_window()` runs at the top of the loop (stalling ON only), before the decision, and with no advance. If Bottom is the beneficiary while armed and Exhausted:

```text
the free window is consumed (already at loop start)
-> Bottom is locked -> LOCKOUT_HOLD via recovery_hold()
-> initiative passes to Top
-> no time advance and no behavior applied
-> the lockout persists (the latch is unchanged)
```

This matches current mechanics: the free window only requires the beneficiary to own the initiative when it is consumed.

---

# 6. Candidate families

All traces below assume Top PRESSURE and UNFUNDED post-clear (as observed in 63/63 matches), alternating initiative, no free windows, and stamina 19 at lockout entry. T is the lockout-entry window (clear + 10 s). Values are Bottom stamina at Bottom decision windows. Exhausted Bottom recovers +4 per 10 s through CONSERVE.

| Family | Rule while armed and Exhausted | Trace from T | Lockout length | Notes |
|---|---|---|---|---|
| **A. Strict Exhausted initiation lockout** | no initiation; hold | T+10 23 H, T+20 27 H, T+30 31 H, T+40 35 clear -> MEDIUM | **40 s** | Uses the existing latch only; no new state |
| A' (variant) | as A, but also before the first clear | — | — | **Rejected.** Changes pre-clear play and first-clear timing (criterion 12), removes adoption's Exhausted LOW activity (Gate D: 1,227 builders), and changes the context of the 31 pre-clear escapes |
| B. One Exhausted LOW token per episode | one LOW, then hold until clear | T+10 23 LOW -> 20, T+20 24 H, T+30 28 H, T+40 32 H, T+50 36 clear -> MEDIUM | 50 s | Adds one boolean per episode. **The T+10 LOW is identical to the adopted T+10 attempt, so its 4 adopted escapes would be preserved by construction** (see section 10) |
| C. Reserve-safe Exhausted LOW | LOW only if a frozen rule says the clear is not delayed | Any Exhausted LOW nets +1 instead of +4 per 10 s, so every LOW delays the clear. A "does not delay" rule would allow none and collapse to A; a looser rule needs a recovery forecast | — | **Rejected.** It recreates D2's forecasting complexity with no gain over A or B |
| D. Explicit stamina debt / burst credit | one overdraw, then debt blocks spending until repaid | — | — | **Equivalent to A.** The engine's hysteresis latch already is the debt (enter <= 25, repay to >= 35). An explicit debt variable would duplicate it. **Rejected; A uses the existing state** |

**Selected: Family A — STRICT EXHAUSTED INITIATION LOCKOUT (D3-A).** It is the simplest, adds no state beyond the existing latch and the existing "armed" notion, no timer, no counter and no stamina grant, and it directly removes the unbounded Exhausted-spend grind.

Family B is recorded as the strongest alternative: one more boolean of state, a 10 s longer lockout, and 4 extra preserved escapes by construction. **Choosing B instead of A is a user decision before implementation authorization**, and would need its own preregistration revision. It is not selected here.

---

# 7. Selected candidate: D3-A STRICT EXHAUSTED INITIATION LOCKOUT

## Scope

- Bottom only, on the E-PROD configuration only: `bottom_behavior_mode=RECOVER` (ESCAPE baseline), v0.2 setup ordering, v0.4a semantics, `LOW_WHILE_EXHAUSTED`, Rule 1 ON, Rule 2 OFF, no settlement umbrella, baseline MEDIUM. Any other configuration requesting D3 is rejected. D3 is inactive on Surfaces A and B, and Top is never affected.
- Implemented as a **new opt-in diagnostic mode**, separate from v1e and v1f. v1e's code path and pinned evidence must stay unchanged and reproducible.
- No change to costs, recovery amounts, behavior rates, drift rates, the 25/35 hysteresis, Recognition, response selection, settlement, setup or submission rules, stalling rules, or the canonical production policy.

## Exact state machine

```text
                     (match start; adopted policy unchanged)
UNARMED ─────────────────────────────────────────────────────────┐
   │ first Exhausted -> non-Exhausted latch clear of Bottom       │
   v                                                              │
ARMED_NORMAL  ── Bottom latch enters Exhausted (any cause) ──>  ARMED_LOCKOUT
     ^                                                            │
     └────────── Bottom latch clears (recover_up_to reaches >= 35) ┘
```

- **Lockout is not a stored flag:** `lockout_active ≡ armed ∧ bottom.stamina.band is EXHAUSTED`. `armed` is the only new per-match bit, and it is equivalent to "Bottom has been Exhausted earlier in this match and has since cleared". Both are discarded at match end.

Answers to the required questions:

| Question | Frozen answer |
|---|---|
| Is the lockout active for every Exhausted state? | **No: only after arming.** It applies to every Exhausted state after the first clear. |
| Pre-clear (initial) exhaustion? | **Adopted policy unchanged:** Exhausted LOW initiations continue until the first clear. |
| Is the match armed after the first clear? | **Yes,** for the rest of the match. |
| Does the lockout reset at match end? | **Yes.** All state is per match. A match ending while locked is recorded as `PENDING_AT_END`. |
| Does another exhaustion create a new episode? | **Yes.** Each ARMED_NORMAL -> ARMED_LOCKOUT transition is a new lockout episode. |
| Exhausted clears during an advance before a Top window? | The lockout ends with the latch. Top's window is normal (Top is never affected). Bottom's next window is ordinary adopted play. |
| At what exact point does the lockout end? | At the latch clear. Clears happen only inside `advance()` (behavior recovery). D3 decisions read the latch at the Bottom decision window: after that window's advance and the post-advance behavior re-choice, before action selection. |
| Can Bottom act in the same window that records the clear? | **Yes.** If the advance immediately before a Bottom decision window clears the latch, that window is ordinary: adopted RECOVER re-choice gives ESCAPE, and the request is baseline MEDIUM, exactly as the adopted policy does today. |

## Decision at a Bottom decision window (normal or free)

```text
if armed and Bottom is Exhausted:
    LOCKOUT_HOLD: MountMatch.recovery_hold()      # no initiation, no spend, initiative -> Top
else:
    adopted decision unchanged:
        Exhausted (unarmed)  -> LOW_WHILE_EXHAUSTED
        non-Exhausted        -> baseline MEDIUM
        policy.choose -> no action -> genuine RESET (unchanged)
```

- **The lockout begins only after the spend that makes Bottom Exhausted.** The decision that leads to it is made while Bottom is non-Exhausted (stamina 26) and is the ordinary MEDIUM.
- **Behavior is untouched.** While Exhausted, adopted RECOVER already selects CONSERVE. D3 adds no override.
- **Top windows and Bottom's defensive responses are unchanged.** That includes response commitment, provisional holds, Rule 1 waivers, Recognition and response selection.
- **No timer, no cooldown, no counter, no stamina grant, no new rate or threshold.**

---

# 8. Hand-traced ledger (traced path)

Offsets from the first clear:

```text
+0    advance: CONSERVE 33 -> 35, latch clears (armed)    Bottom window: MEDIUM -7    -> 28
+5    advance ESCAPE -1 (Top window; Top UNFUNDED, response waived)                   -> 27
+10   advance ESCAPE -1                                   Bottom window 26: MEDIUM -7 -> 19
      latch enters Exhausted  => LOCKOUT episode 1 begins (after the spend)
+15   advance CONSERVE +2 (Top window)                                                -> 21
+20   advance CONSERVE +2   Bottom window 23 (Exhausted): LOCKOUT_HOLD
+25   advance CONSERVE +2 (Top window)                                                -> 25
+30   advance CONSERVE +2   Bottom window 27: LOCKOUT_HOLD
+35   advance CONSERVE +2 (Top window)                                                -> 29
+40   advance CONSERVE +2   Bottom window 31: LOCKOUT_HOLD
+45   advance CONSERVE +2 (Top window)                                                -> 33
+50   advance CONSERVE +2 -> 35, latch CLEARS (lockout ends)
      re-choice ESCAPE; Bottom window 35: baseline MEDIUM -7                          -> 28
+55   ESCAPE -1 -> 27;  +60 ESCAPE -1 -> 26: MEDIUM -7 -> 19 => LOCKOUT episode 2
...   steady cycle of 50 s
```

- **Lockout entry to clear:** 19 -> 23 -> 27 -> 31 -> 35 at Bottom windows: **40 s exactly**, 8 CONSERVE advances, 3 Bottom opportunities held, 4 Top windows.
- **Steady cycle:** 50 s with 2 MEDIUM bursts (clear window and +10 s), 3 lockout holds and 10 advances (8 CONSERVE, 2 ESCAPE).
- **The +10 s MEDIUM remains available: YES.** Both the clear-window MEDIUM and the +10 s MEDIUM at 26 are ordinary adopted decisions made while non-Exhausted. The lockout starts only after the +10 s spend.

**Parity.** From entry 19, Bottom windows see odd values and the clear lands exactly on a Bottom window. If an entry stamina gives an odd value at Top windows reaching 35 or 36 (for example entry 21: Bottom windows 25, 29, 33 and Top window 35), the latch clears before a Top window. Bottom's next window is then ordinary at 34 (MEDIUM -> 27). That is an adopted decision and is reported, not specially handled.

**Comparison with the adopted policy over the same 50 s from lockout entry T:**

| Window | Adopted | D3-A |
|---|---|---|
| T+10 .. T+40 | Exhausted LOW at 23, 24, 25, 26 (net +1 per 10 s) | holds at 23, 27, 31; clear at T+40 |
| T+40 | still Exhausted | MEDIUM at 35 (clear window) |
| T+50 | still Exhausted | MEDIUM at 26 (next burst) |
| Typical outcome | stays Exhausted roughly 160 s (observed 62/63 never re-clear) | — |

**Positional drift, predicted (measured only after authorization).** During the lockout D3 and the adopted policy both use CONSERVE (Bottom is Exhausted in both), so D3 introduces **no forced-CONSERVE drift**. After D3 clears at T+40, its advances are ESCAPE (+0.50) while the adopted Bottom is still Exhausted on CONSERVE (+0.75). Per 50 s cycle that is about **-0.50 axis toward Top relative to adopted**, before clamping and before the axis effects of the different attempts. Compare v1e: +0.25 per forced advance, 120.5 axis units realized.

# 9. Expected tactical effects (from existing adopted evidence; no candidate run)

D3 changes **nothing before the first armed lockout entry**: every decision up to and including the +10 s MEDIUM is the adopted decision, from the same state with the same RNG streams. So gameplay up to and including that attempt is **identical to the adopted control** in every match.

From the adopted control logs:

| | Original-100 (seed 42) | Seed 142 |
|---|---|---|
| Matches with a post-clear Exhausted entry | 33 | 30 |
| ... of which the entry attempt itself ended the match (escape) | 8 | 11 |
| **Affected matches** (continue past lockout entry) | **25** | **19** |
| Adopted outcomes in affected matches | 10 escapes (Reversal 4, Open 5, Half 1), 15 timeouts, **0 Tap** | 1 escape (Open), 18 timeouts, 0 Tap |
| Adopted escapes preserved by construction (prefix identical) | **25** (Half 15, Open 5, Reversal 5) | 28 |
| Adopted escapes at risk | 10: Exhausted LOW at T+10 (3 Reversal), T+20 (3 Open), T+30 (1 Open, 1 Reversal), T+40 (1 Open); non-Exhausted MEDIUM at T+140 (1 Half) | 1: Exhausted LOW at T+10 (Open) |
| Adopted timeouts in unaffected matches | 45 | 49 |
| Adopted Taps in unaffected matches | 5 | 4 |

Consequences for criterion 4 (original-100), assuming the prefix identity holds:

- **Escapes >= 25: met by construction** (25 preserved). It needs no recovery from the at-risk 10.
- **Timeouts <= 70: met in the worst case.** 45 unaffected + at most 25 affected = 70, since each affected match can contribute at most one timeout.
- **Tap <= 9:** the 5 unaffected Taps are fixed. It fails only if at least 5 of the 25 affected matches become Taps. The adopted policy kept Bottom Exhausted (Top +1) through all of them with 0 Taps; D3 keeps Bottom Exhausted for less time.
- **Half 16 / Open 10 / Reversal 9, +/-10:** the preserved split is 15/5/5, all within tolerance. It fails only if D3 adds at least 12 Half Guard escapes, or at least 16 Open, or at least 15 Reversal, in 25 affected matches.

**Important honesty note:** under the prefix-identity property, the frozen criterion-4 floors are satisfied in the worst case for escapes and timeouts. **Criterion 4 therefore cannot discriminate D3's tactical quality.** The tactical judgment rests on the mandatory prefix-identity gate (G6) and on the attribution reporting. If the user wants a non-vacuous tactical gate for the affected matches, it must be added **before** implementation authorization. This preregistration does not invent one.

**+10 s MEDIUM restoration.** All 18 escapes v1e lost from the adopted +10 s MEDIUM lie inside the identical prefix. **D3-A restores all 18 by construction.** Of the 10 at-risk original-100 escapes, the 9 Exhausted LOW escapes fall in T+10..T+40. At T+10..T+30 D3-A holds, and T+40 is D3's clear-window MEDIUM from a different state. These escapes are expected to be lost unless D3's post-lockout MEDIUM bursts produce replacements.

# 10. Known risks and predicted failure modes

1. **Lost Exhausted LOW escapes.** Up to 10 original-100 escapes are at risk (9 of them Exhausted LOW). Under Family B the 4 at T+10 would be preserved by construction. D3-A forfeits them unless its own bursts replace them.
2. **Burst cadence.** D3-A re-enters Exhausted 10 s after every lockout clear: two MEDIUMs, then 40 s locked. This is by design (intentional burst re-exhaustion) and is not gated. The adopted policy re-cleared once in 63 matches; D3-A is expected to produce roughly `floor(remaining / 50)` further cycles per affected match.
3. **Lockout recovery delayed by funded Top exchanges** (response commitment or provisional hold, Rule 2 OFF double charge). None was observed post-clear in adopted logs (204 Top attempts, 0 charged), but funded Top windows remain possible.
4. **Fewer Bottom initiations while Exhausted:** fewer Exhausted setup builders after the first clear. Pre-clear Exhausted activity (adoption Gate D) is unchanged.
5. **Stalling.** Lockout holds are invisible to v0.3b (as v1e holds were). Bottom's clock is zeroed when it is the engaged defender of Top attempts. A genuine RESET after a lockout could be evaluated with a clock that includes lockout time. This is reported, never hidden.
6. **G3 sample is small.** Only **26** pooled first lockouts have >= 50 s remaining at entry (see section 11). The number is fixed in advance by the identical prefix.
7. **Criterion-4 vacuity** (section 9) is a measurement-design limitation, recorded up front.

---

# 11. Proposed D3 gates (frozen)

## Preservation (mandatory; carried over from adoption/D2 where they still make sense)

| ID | Gate |
|---|---|
| P1 | Surface A exactly 78 Threat matches / 1,950 Threat entries / Tap 0; Surface B Tap 9/100; D3 rejected (inactive) on non-RECOVER surfaces. |
| P2 | Rule 1: zero responder commitment and zero provisional hold charged on unfunded-initiator exchanges. Rule 2 OFF: hold covered by response = 0. |
| P3 | Bottom stamina in [0,100]; no fabricated recovery (every increase is a CONSERVE behavior gain); no negative cost; original-100 Bottom final median >= 29. |
| P4 | Original-100 E-PROD: escapes >= 25; Half Guard 16 +/-10, Open Guard 10 +/-10, Reversal 9 +/-10; timeouts <= 70; Tap <= 9. Evaluated on OFF + shadow and ON; both must pass. |
| P5 | Original-100 RESET-with-progress-route exposure <= 23/100. Real v0.3b warning, penalty or position reset: any that occur are **reported, never hidden**, with cause. A lockout hold can never cause one (structural). An offense caused by a genuine RESET under the existing rules does not by itself fail P5. OFF/ON gameplay divergence must be 0/100 per batch whenever no real offense fires; divergence after a real offense is reported with its first-divergence time. |
| P6 | Frozen digest exact; full unit suite, semantic checker and legacy entry point PASS; exact-head CI on Python 3.11 and 3.13; deterministic replay (full gameplay identity); observer ON/OFF identity; `recovery_hold()` invoked only by v1e and D3 modes; `recovery_hold_history` empty on every non-candidate surface; **v1e reproduces its recorded `fe229cb` evidence exactly** (existing pinned tests unchanged). |
| P7 | Explicit D3 diagnostic entry points are equivalent (effective settings and gameplay); the canonical production entry point equals the adopted controls and is unchanged; `PRODUCTION_STAMINA_RECOVERY_POLICY` unchanged. |
| P8 | All historical evidence preserved (D1, D2 v1-v1f, the v1e FAIL record, adoption records). |
| P9 | Anti-removal floors (D2 criterion 12): clearing matches original >= 40 and pooled >= 75; first-clear median <= 250 s, original and pooled. Expected identical to adopted (45 / 82 / 240 s) by construction. |

D2 criteria 9-10 (re-exhaustion within 10/30 s), 11 and 13 are **not** D3 gates: the candidate intentionally re-exhausts at +10 s. D2 criterion 16 does not apply (D3 has no recovery-hold mode).

## New D3 bounded-burst gates

| ID | Gate | Status |
|---|---|---|
| **G1** | **No Bottom initiation spend during lockout.** For every lockout episode, Bottom initiation stamina spend is exactly 0 from entry until the latch clears or the match ends. This includes LOW, MEDIUM, HIGH, setup-builder initiations, UNFUNDED initiations and any Bottom-initiated action. No exception. | MANDATORY |
| **G2** | **Lockout exactness.** At every armed Bottom decision window (normal or free): Bottom Exhausted ⇔ `LOCKOUT_HOLD`. That means 0 Bottom attempts and 0 Bottom RESETs while armed and Exhausted, and 0 lockout holds while non-Exhausted or unarmed. Defensive responses are reported separately and are not part of G2. | MANDATORY |
| **G3** | **Recovery success.** Population: each match's first lockout episode where the match continues past entry, pooled over both seeds and evaluated separately for OFF + shadow and ON (both must pass). Eligible if at least **50 s** remain at entry (`300 - entry_elapsed >= 50`). Adequacy: at least **25** eligible pooled matches, otherwise OPEN. Success: at least **80%** of eligible episodes see the latch clear within **50 s** of entry (inclusive), with Bottom not at match end. Re-entry is impossible while locked. Match end before the clear despite >= 50 s remaining at entry is a failure. | MANDATORY |
| G4 | Lockout clear to next lockout entry: full distribution, plus the share of clears followed by an entry within 10 s (the intentional burst). | REPORTED |
| G5 | Lockout cycling: episodes per match (distribution, median, p90, max); lockout durations (minimum, median, maximum). The minimum possible completed duration is 25 s (from 25: five +2 advances), so zero-time churn is structurally impossible. Every completed episode below 25 s, or ending without a latch clear, is listed. | REPORTED (sanity-checked) |
| **G6** | **Prefix identity and burst preservation.** For every match and both stalling modes, the D3 event log, including the outcome when the match ends earlier, is identical to the adopted control up to and including the attempt that causes the first armed lockout entry. Every adopted escape occurring at or before that attempt is present in D3. In particular, **all 18 adopted +10 s MEDIUM escapes that v1e lost are present in D3**. | MANDATORY |
| G6r | Seed-matched attribution, adopted vs D3 and v1e vs D3 (section 13). | REPORTED |

**G3 threshold rationale.** The values were checked against existing evidence before freezing, and the brief's suggested adequacy of 35 was **rejected**:

- **The lockout entries are known in advance.** The D3 prefix is identical to the adopted control, so the first-lockout entry times are already determined by the adopted logs.
- **Matches still running at lockout entry, by time remaining** (pooled, both seeds):

  | Remaining at entry | >= 30 s | >= 40 s | >= 50 s | >= 60 s | >= 70 s |
  |---|---|---|---|---|---|
  | Matches | 35 | 29 | **26** | 25 | 20 |

- **Why not the suggested floor of 35:** only 35 matches have even 30 s remaining. A floor of 35 would force eligibility down to 30 s, below the traced 40 s recovery, so G3 would be mechanically OPEN or unfair.
- **Why eligibility at 50 s:** the traced recovery is 40 s. A 50 s eligibility and 50 s clearing window allow one extra 10 s cycle of slack (one Top-funded charge, or a parity shift).
- **Why 25:** it is the largest floor below the known eligible population (26) that still requires near-complete exposure.
- **Why 80%:** it is kept from D2's criterion 16 as the timeliness tolerance.

These values are normative and frozen here, before implementation.

**Decision rule.** All mandatory gates (P1-P9, G1, G2, G3, G6) must pass for a D3 design-gate PASS. Any failure means FAIL: record it and STOP, with no tuning and no gate change. Missing or inadequate evidence means OPEN. Unit, checker and CI PASS never soften a FAIL or an OPEN.

# 12. Sampling and denominators

- **Candidate runs:** E-PROD, base seeds 42 and 142, 100 matches each, 300 s, stalling OFF + shadow and ON, with D3-A enabled.
- **Comparators** on the same seeds and stalling modes:
  - the adopted canonical controls;
  - **v1e as frozen**, reproduced from its unchanged code path and checked equal to `fe229cb`.
- **No:** exploratory seeds, extensions, seed replacement, tuning, outcome exclusions, or reruns because a result looks unfortunate. A scoring-code bug may be fixed and rescored only if gameplay identity is re-verified, and the fix must be recorded.
- **Original-100** means base seed 42. **Pooled** means both seeds, 200 matches, with seed-142 match indices offset by 100.

# 13. Required diagnostics (mandatory reporting; descriptive)

**Lockout episode,** for each one:
- entry timestamp, entry stamina and cause of the Exhausted entry (initiation spend, behavior drain, responder commitment, provisional hold);
- the initiating action that caused the entry, with requested and effective commitment;
- axis and band at entry;
- setup state (Bottom tiers, Ready targets) and submission stage;
- remaining match time;
- end type: `CLEARED`, `PENDING_AT_END` by terminal type.

**During the lockout,** at every Bottom opportunity:
- timestamp, stamina, and whether it was a normal or free window;
- the commitment the adopted policy would have requested (LOW_WHILE_EXHAUSTED: deterministic, no RNG);
- **the action `EscapeFirstInitiatorPolicy.choose` would have selected.** This is computed inertly: the policy is deterministic preview arithmetic with no RNG, as audited. Inertness is proven by the observer ON/OFF identity gate (P6), and if that proof fails the counterfactual is omitted and reported as unavailable;
- whether a legal action existed, a progress route existed, and a setup builder (target not Ready) existed;
- the lockout action taken (`LOCKOUT_HOLD`) and the initiative transition.

**Stamina ledger** per advance and per exchange, by source: CONSERVE recovery, behavior drain, initiation spend, response commitment spend, provisional hold spend, other. Totals per lockout episode.

**Recovery,** per episode:
- entry stamina and clear stamina;
- entry-to-clear duration;
- number of advances;
- Bottom opportunities held;
- Top attempts during the lockout, with Bottom response spends, provisional-hold spends, and the extra lockout time those spends caused (measured against the +4 per 10 s trace);
- pending-at-end.

**Tactical effect,** D3 vs adopted vs v1e:
- Bottom attempts after the first clear, while Exhausted, and after each lockout clear;
- setup-builder attempts, setup advances and Ready completions;
- Top submission progression (Threat, Control, Finish entries);
- escapes by type, timeouts, Tap.

**Positional drift and band:**
- axis and band at every window after the first clear;
- the share of windows in STRONG/LOCKED;
- per-advance drift against the adopted control at matched times, and the realized drift difference;
- Bottom initiations by band, especially lockout-clear MEDIUMs.

**Seed-matched attribution (G6r):**
- complete match-by-match outcome transitions, adopted vs D3 and v1e vs D3;
- for every changed outcome: escape preserved, escape lost, timeout recovered, new timeout, Tap change, exit-type change;
- for each lost or gained escape, the escaping attempt (time from clear, time from lockout entry, decision kind, commitment, band);
- explicit confirmation of the 18 restored +10 s MEDIUM escapes;
- the fate of the 10 original-100 at-risk escapes;
- whether Family B's 4 T+10 escapes are among the losses.

**Traced prediction vs reality:**
- the entry-stamina distribution (predicted 19);
- the lockout duration distribution (predicted 40 s);
- cycle length (predicted 50 s);
- holds per lockout (predicted 3);
- MEDIUM bursts per cycle (predicted 2);
- the drift difference against adopted (predicted about -0.5 axis per cycle).

# 14. Planned implementation surface (for review; not implemented)

- A new opt-in batch mode value (for example `PostClearHandoffMode.D3_EXHAUSTED_INITIATION_LOCKOUT`) with the configuration validation in section 7. v1e's value and code path stay unchanged.
- **The decision hook:** at a Bottom window, `armed and Exhausted` → `match.recovery_hold()`. Otherwise the existing code path runs untouched.
- **No pre-advance override** and **no new engine transition or field.** `recovery_hold_history` is reused, and a docstring note is the only engine-file change.
- **A read-only collector extension:**
  - decision kind `LOCKOUT_HOLD`;
  - the counterfactual adopted request/action;
  - stamina-ledger sources;
  - episode records.
- **Synthetic unit tests, written before the frozen run,** pinning:
  - the 19 → 23 → 27 → 31 → 35 lockout, with the clear-window MEDIUM;
  - the +10 s MEDIUM still made at 26;
  - lockout only after arming;
  - free-window handling;
  - responses unchanged during the lockout;
  - no RNG and no RESET or stalling history from lockout holds;
  - prefix identity against the adopted policy;
  - inertness outside D3.

# 15. Hard-stop rules

After this commit: **HARD STOP** for review of this exact SHA and explicit D3 authorization.

Decisions the reviewer may take before authorizing:
- Family A vs Family B;
- whether to add a non-vacuous tactical gate for affected matches (section 9);
- confirmation of the G3 values (50 s / 25 / 80% / 50 s);
- confirmation of the P5 offense wording.

After any D3 evidence: HARD STOP again.

**Not authorized here:**
- D3 implementation or any D3 run, including exploratory seeds;
- any `MountMatch` or `handoff_policy.py` change;
- any change to v1e or its evidence;
- v1f implementation or measurement;
- D2 criteria changes;
- canonical production policy or raw default changes;
- PR #10 changes or merge, squash, force-push;
- Rule 2, setup-policy or commitment-selection work;
- frontend work.
