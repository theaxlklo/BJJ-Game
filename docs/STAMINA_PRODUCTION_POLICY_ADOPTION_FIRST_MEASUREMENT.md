# Stamina Production-Policy Adoption — First Measurement

## Status

**STAGE 2 MEASURED — GATES A-F AND H PASS — GATE G NOT EVALUATED — HARD STOP BEFORE PROMOTION.**

This is the first, untuned Rule1-only + LOW production-candidate measurement required by
`docs/STAMINA_PRODUCTION_POLICY_ADOPTION_DEFINITION_OF_DONE.md` (Stage 2, steps 13-19), scored against
`docs/STAMINA_PRODUCTION_POLICY_ADOPTION_PREREGISTRATION.md` (frozen at `985002d82c785d8f90604a06adc6a516245f4e81`).

No default changed. No canonical production entry point was added. Nothing was tuned.

The slice is **not yet ADOPTED**. Gate G can only be evaluated after the canonical production entry point is added (DoD steps 20-21), which needs separate user authorization.

```text
measurement code: src/bjj_game/diagnostics/stamina_adoption_candidate.py
rubric tests:     tests/test_stamina_adoption_candidate_rules.py (synthetic; written before the run)
pinned results:   tests/test_stamina_adoption_candidate_measurement.py
frozen digest:    3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

---

# 1. Exact candidate configuration

`PROPOSED_PRODUCTION_DIAGNOSTIC`: a diagnostic configuration only, not canonical.

```text
enable_unfunded_responder_cost_waiver = True    (Rule 1 ON)
enable_supplemental_hold_settlement   = False   (Rule 2 OFF)
enable_stamina_settlement_rules       = False   (umbrella BOTH not used)
recovery_initiation_mode = LOW_WHILE_EXHAUSTED  (Surface E-PROD only)
```

Surfaces, all 100 matched seeds `42..141`:

```text
A       existing Surface A public MATCH + Rule1 ON / Rule2 OFF
B       existing Surface B trust-read  + Rule1 ON / Rule2 OFF
E-PROD  existing Surface E (Bottom RECOVER) + Rule1 ON / Rule2 OFF
        + LOW_WHILE_EXHAUSTED
        run: stalling OFF + shadow v0.3b; stalling ON (frozen v0.3b);
             stalling OFF plain (shadow nonperturbation check)
```

On A and B, recovery LOW is not set. The batch rejects non-CURRENT recovery modes without Bottom RECOVER, and the DoD states that LOW is irrelevant on Surface A.

---

# 2. Gates A-H

| Gate | Status | Evidence |
|---|---|---|
| A — Rule 1 remains exact | **PASS** | UNFUNDED exchanges / responder spend: A 3588/0, B 3638/0, E-PROD OFF 1790/0, E-PROD ON 1790/0. A and B are identical to the isolated Rule1-only cells. |
| B — Rule 2 absent | **PASS** | Effective Rule 2 OFF. Hold covered by response = 0 on every surface. Surface A Threat matches/entries = 78/1950. |
| C — LOW fixes the deadlock + A9 | **PASS** | Latch clears 46, CONSERVE->ESCAPE 38, State2->State1 46. A9: N=10s, admissible 69, R(N) 64, p=0.927536231884058 <= X=0.975034786099515, EXT-100 triggered. |
| D — tactical activity preserved | **PASS** | Exhausted setup builders 1227, Bridge 1227, completed builds 1107 (prior CURRENT/RESET/LOW+BOTH builders 1326/0/1114). |
| E — competent-defender Tap | **PASS** | Surface B Tap 9/100 (legacy / Rule1-only / BOTH = 6/9/7). |
| F — frozen v0.3b observational | **PASS** | Shadow nonperturbation True. Stalling threshold 20 s unchanged. Counters populated. Real W/P/PR/free 0/0/0/0. Matched divergence 0/100. |
| G — canonical equals measured | **NOT EVALUATED** | No canonical entry point added; evaluated only after promotion is authorized. |
| H — historical replay/defaults | **PASS** | Raw defaults unchanged. NONE attribution equals merged legacy. BOTH equals PR8 BOTH. CURRENT/RESET/LOW still callable. Rule1-only identity is shown in Gate A. Rule2-only remains covered by the existing settlement tests. |

---

# 3. A1-A10 preregistration comparison

The scoring rubric was fixed in code and tested on synthetic inputs before the candidate run (`tests/test_stamina_adoption_candidate_rules.py`). For ranges with a hard floor (A2, A3): inside the expected range is CONFIRMED; at or above the floor but outside the range is PARTIAL; below the floor is NOT CONFIRMED.

| Prediction | Result | Measured | Frozen expectation |
|---|---|---|---|
| A1 public-MATCH Threat | CONFIRMED | 78 / 1950 / Tap 0 | exact 78 / 1950 / 0 |
| A2 latch clears | CONFIRMED | 46 | floor >=34; expected 40-120 (LOW+BOTH 67) |
| A3 exhausted setup builders | CONFIRMED | 1227 | floor >=557; expected 800-1400 (LOW+BOTH 1114) |
| A4 Bottom final median | CONFIRMED | 29.0 | 20-35 (LOW+BOTH 26) |
| A5 timeouts | CONFIRMED | 60 | 30-75 (LOW+BOTH 44; CURRENT+BOTH 75) |
| A6 LOW stalling exposure | CONFIRMED | RESET-with-route 13; real W/P/PR 0/0/0 | <=15; 0/0/0 |
| A7 OFF+shadow vs ON | CONFIRMED | no real offense; identical; 0/100 diverged | identical; 0/100 |
| A8 exit split | CONFIRMED | Half/Open/Reversal 16/10/9 | Half largest; Reversal <15% (LOW+BOTH 31/15/5) |
| A9 handoff | CONFIRMED (gate PASS) | p_candidate 0.927536231884058 on 69 admissible | p <= 0.975034786099515 with >=43 admissible |
| A10 trust-read Tap | CONFIRMED | 9/100 | 0% < Tap < 50% |

No prediction missed, so no miss explanations are required. A1-A8 and A10 are scored on the original 100 seeds only.

---

# 4. A / B / E-PROD outcome tables

| Surface | Tap | Half | Open | Reversal | Escapes | Timeouts | Top / Bottom final median | Threat matches | Threat / Control / Finish entries |
|---|---|---|---|---|---|---|---|---|---|
| A public MATCH | 0 | 22 | 0 | 0 | 22 | 78 | 0.0 / 0.0 | 78 | 1950 / 0 / 0 |
| B trust-read | 9 | 8 | 2 | 2 | 12 | 79 | 0.0 / 0.0 | 59 | 533 / 355 / 372 |
| E-PROD OFF+shadow | 5 | 16 | 10 | 9 | 35 | 60 | 0.0 / 29.0 | 61 | 683 / 408 / 168 |
| E-PROD ON | 5 | 16 | 10 | 9 | 35 | 60 | 0.0 / 29.0 | 61 | 683 / 408 / 168 |

# 5. Half / Open / Reversal exit split (E-PROD)

```text
E-PROD Rule1-only + LOW: Half=16  Open=10  Reversal=9   (escapes 35)
LOW+BOTH anchor:         Half=31  Open=15  Reversal=5   (escapes 51)
```

Half Guard is still the largest category and Reversal is still under 15%, so A8 is CONFIRMED. Compared with LOW+BOTH, though, there are 16 fewer escapes, 16 more timeouts, and Reversal is a larger share of the escapes. This is a **configuration effect** (Rule1-only versus BOTH, with the legacy response+hold double charge active again). It should not be attributed to LOW alone.

---

# 6. Recovery / stamina budget (Bottom, E-PROD stalling OFF)

```text
behavior recovery=7786            behavior spend=1012
defensive response commitment spend=4084
hold spend=537
total defensive spend=4621
own-attack commitment spend=9151  own initiated actions=2359
RESET count=31
requested commitments while Exhausted={LOW: 1839}
latch clears=46   CONSERVE->ESCAPE=38   State2->State1=46
State1 / State2 / State3 shares=0.2230 / 0.7768 / 0.0002
spend per recovery own / defensive / total=1.175 / 0.594 / 1.769
```

Every Exhausted-state initiation requested LOW (1839/1839).

---

# 7. LOW -> MEDIUM re-exhaustion / handoff analysis

## Original 100 seeds (42..141)

```text
clear events=46
eventual re-exhaustions after a clear=34
clears remaining non-Exhausted through match end=12
time-to-re-exhaustion: all 34 observed at exactly 10 s (median=p25=p75=10)
first-clear time per match (45 matches with a clear): median 240 s, range 140-300 s
Bottom stamina at every clear: 35 (46/46)
```

| h | R(h) | survived | censored | admissible |
|---|---|---|---|---|
| 5 s | 0 | 37 | 9 | 37 |
| 10 s | 34 | 3 | 9 | 37 |
| 15 s | 34 | 0 | 12 | 34 |
| 20 s | 34 | 0 | 12 | 34 |

## Frozen A9 verdict

```text
N=10 s, X=0.975034786099515 (display 0.98), M=43

original-100 admissible clears at N=37 < 43  -> EXT-100 mechanically triggered
EXT-100 (142..241) at N: R=30, survived=2, censored=5, admissible=32
pooled at N:             R=64, survived=5, censored=14, admissible=69

p_candidate (pooled, unrounded)=64/69=0.927536231884058
p_baseline=59/63=0.9365079365079365
p_candidate - p_baseline=-0.00897170462387853

69 >= 43 and 0.927536231884058 <= 0.975034786099515  -> A9 PASS
```

**Descriptive reading, kept separate from PASS/FAIL:** A9 passes only as the frozen *relative* gate. The candidate's handoff oscillates almost exactly like the baseline. 92.8% of admissible clears re-exhaust within 10 s, every observed re-exhaustion takes exactly 10 s, and every clear happens at exactly the 35-stamina recovery threshold. A9 PASS does **not** show that the LOW -> MEDIUM handoff is stable. The oscillation debt remains open.

# 8. EXT-100

Triggered **mechanically, on sample adequacy only**: the original-100 admissible clears at N were 37, below 43. Exactly one EXT-100 batch was run, with the same code and frozen digest. EXT-100 is used for A9 only. No second extension was run.

| Population | clears | R(N) | survived@N | censored@N | admissible@N |
|---|---|---|---|---|---|
| original 100 | 46 | 34 | 3 | 9 | 37 |
| EXT-100 | 37 | 30 | 2 | 5 | 32 |
| pooled | 83 | 64 | 5 | 14 | 69 |

The EXT-100 clears do not count toward A2 or any other gate. A2 uses the original 46.

# 9. A9 match-level sensitivity (advisory, non-gating)

| | episode admissible | R(N) | p_episode | matches with admissible clear | matches with rapid re-exhaustion | p_match | gap |
|---|---|---|---|---|---|---|---|
| LOW+BOTH baseline | 63 | 59 | 0.9365079365079365 | 61 | 58 | 0.9508196721311475 | 0.0143 |
| candidate (pooled) | 69 | 64 | 0.927536231884058 | 68 | 63 | 0.9264705882352942 | 0.0011 |

```text
episode-level sign(p_candidate - p_baseline) = negative
match-level   sign(p_candidate - p_baseline) = negative
ordering flip = False
both gaps <= 0.05
```

No clustering explanation is mandated. Nearly every match contributes one admissible clear (69 episodes from 68 matches).

# 10. Setup interaction while Exhausted (E-PROD)

```text
Bridge attempts=1227
setup-builder attempts=1227
setup advances=1182
Ready transitions=593
completed setup builds=1107
escapes after measured setup builds=5
RESETs forgoing setup opportunity=31   (Exhausted RESETs=31)
```

Compared with LOW+BOTH (1114 builders), setup activity is preserved and slightly higher.

# 11. Shadow / real stalling comparison (E-PROD)

```text
stalling OFF + shadow:
  RESET-with-progress-route exposure=13
  shadow threshold reaches=0
  shadow Warnings/Penalties/Position Resets/free initiative=0/0/0/0

stalling ON (frozen v0.3b):
  real Warnings/Penalties/Position Resets/free initiative=0/0/0/0
  stalling penalty axis movement signed/absolute=0.0/0.0
  real resets-with-route=13

shadow nonperturbation (OFF+shadow vs OFF plain gameplay)=True
matched OFF/ON divergence=0/100
```

No real offense was reached, so OFF and ON gameplay are identical.

# 12. Canonical-production equivalence

**Not performed.** Promotion has not happened. DoD steps 20-21 (add the canonical entry point, prove deterministic equivalence with this diagnostic) need explicit user authorization. Gate G is evaluated only then.

# 13. Rule 2 deferred status and named additive-hold debt

Rule 2 stays **deferred, not solved**. With Rule 2 OFF, the legacy response + provisional-hold additive charge is active in the candidate:

| Surface | hold exchanges | hold stamina charged | additive double-charge cases (funded response >=3 and hold charged) |
|---|---|---|---|
| A | 1950 | 234 | 78 |
| B | 1434 | 408 | 137 |
| E-PROD | 1422 | 537 | 179 |

As the DoD names it, commitment-only affordability can still overstate hold-inclusive affordability. Differences from LOW+BOTH (A2 46 vs 67; escapes 35 vs 51; timeouts 60 vs 44) are therefore **configuration effects** of Rule1-only versus BOTH, not pure LOW effects.

# 14. Residual RESET / stalling risk

RESET-with-progress-route exposure rose from 7 (LOW+BOTH) to 13. That is within the A6 bound of 15, and no real v0.3b offense fired. RESET is not the proposed production policy, so RESET+BOTH's exposure of 983 is still a documented residual risk of that mode only. v0.3b was not changed.

# 15. Facts versus remaining design debt

**Facts (measured, deterministic, first untuned run):**

- Gates A, B, C, D, E, F and H PASS. Gate G is not evaluated.
- A1-A10 are all CONFIRMED.
- EXT-100 was mechanically triggered. Pooled A9 PASS: 64/69 <= X.
- Rule 1 is exact. Rule 2 is absent. Surface A is 78/1950/0. Surface B Tap is 9/100.
- No default changed, nothing was tuned, and v0.3b is unchanged.

**Remaining design debt (not resolved by this measurement):**

- **LOW -> MEDIUM handoff oscillation.** About 93% of admissible clears re-exhaust at exactly 10 s, and clears happen only at the 35 threshold. This passes the frozen relative gate but is an open absolute-stability design question.
- **Rule 2 redesign versus permanent deferral.** The additive response+hold debt is active: 179 cases on E-PROD.
- **Late recovery.** The median first clear is at 240 s of 300 s, and 8 of the 45 first clears happen at match end.
- Fewer escapes and more timeouts than LOW+BOTH: a configuration effect.
- Setup-policy debt, initiator commitment-selection policy, scoring/timeout meaning, and the player-facing contract: all out of scope here, per the DoD.

---

# HARD STOP

The next DoD steps (20-26) are: add the canonical production stamina/recovery entry point, prove equivalence (Gate G), full regression, record adoption verification, update the PR, then a HARD STOP for review.

None of these are started. They need explicit user authorization after review of this measurement commit. No merge without explicit authorization.
