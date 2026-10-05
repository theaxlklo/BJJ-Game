# D2 Handoff-Oscillation — v1e Measurement Result

## Status

**D2 DESIGN RESULT: FAIL (criterion 4). HARD STOP.**

v1e was implemented exactly as preregistered and measured once on the frozen experiment. Every mandatory criterion passes except criterion 4 (original-100 escapes and timeouts). Under the preregistration, one failed mandatory criterion makes the D2 design result FAIL. Unit, checker and CI PASS do not soften this.

Nothing was tuned or rerun to change an outcome, and no extra batch was run. The canonical production policy, defaults and PR #10 are unchanged.

```text
preregistration (frozen):       c4a9c3369b53911eda4d47dd9d814d385470ba8a
implementation (pre-run):       d00c48e5ecc7e1523924c26927119b2e3967fa59
adopted baseline (PR #10):      ee6cb6fcebb105e31224bead48a302811b27b59a
frozen digest:                  3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2

candidate code:   src/bjj_game/interfaces/handoff_policy.py
                  MountMatch.recovery_hold() (src/bjj_game/engine/match.py)
                  run_escape_first_batch(post_clear_handoff_mode=V1E_PERSISTENT_CONSERVE_HOLD)
measurement:      src/bjj_game/diagnostics/handoff_d2_v1e.py
generated data:   docs/HANDOFF_OSCILLATION_D2_V1E_MEASUREMENT_DATA.md
raw evidence:     docs/evidence/handoff_d2_v1e_evidence.json.gz  (every event of every match, v1e and controls)
tests:            tests/test_handoff_d2_v1e.py              (synthetic; committed in d00c48e before the run)
                  tests/test_handoff_d2_v1e_measurement.py  (pins the recorded results)
```

## Run record

- **Frozen experiment:** E-PROD; base seeds 42 and 142, 100 matches each, 300 s; stalling OFF + shadow and ON; v1e enabled.
- **Adopted controls:** the same four runs through `PRODUCTION_STAMINA_RECOVERY_POLICY`.
- **Surfaces A and B:** run with the adopted settings. v1e cannot be requested there and is rejected.
- **One scoring-code fix, recorded for transparency.** The first scoring pass stopped with an internal alignment assertion. The shadow-stalling-clock lookup assumed one trajectory snapshot per decision window, but the trajectory also holds a start and a finish snapshot.
  - The alignment was fixed in the scoring code and the scoring was rerun.
  - The criteria code was unchanged.
  - Gameplay is deterministic, and the replay identity checks below confirm the gameplay was identical.
  - The same scoring pass also fixed three reporting labels: post-clear re-entries were separated from all exhaustion entries, the pooled mode-time share was computed instead of left None, and histograms now sort numerically.
- No gameplay code changed after `d00c48e`.

---

# Criteria

The full evidence strings are in the generated data document. OFF + shadow and ON produced identical gameplay (criterion 5), so one value is shown where both agree.

| # | Criterion | Result | Key evidence |
|---|---|---|---|
| 1 | Surface A 78/1950/Tap 0; B Tap 9; v1e inactive elsewhere | **PASS** | A 78/1950/0; B Tap 9/100; v1e rejected on A and B; 0 `recovery_hold` calls |
| 2 | Rule 1 exact; Rule 2 OFF | **PASS** | All 4 runs: unfunded responder spend 0, unfunded hold charged 0, hold covered 0 |
| 3 | Stamina bounds; no fabricated recovery; final median >=29 | **PASS** | All samples in [0,100]; 0 non-CONSERVE stamina increases; 0 negative costs; original-100 Bottom final median 31.0 |
| 4 | **Original-100 escapes / exits / timeouts / Tap** | **FAIL** | **escapes 17 (>=25 required); timeouts 78 (<=70 required)**; Half/Open/Reversal 7/5/5 (each within +/-10 of 16/10/9); Tap 5 (<=9) |
| 5 | RESET-with-route <=23; no real offense; OFF/ON divergence 0 | **PASS** | Exposure 13 (seed-142 batch: 19); real W/P/PR 0/0/0 on both batches; 0/100 diverged on both batches |
| 6 | Digest/suite/checkers; replay; observer identity; hold isolation | **PASS** | Replay identical on all 4 runs; observers ON/OFF identical; 0 hold calls on controls, A and B; `recovery_hold_history` empty on controls; digest/suite/checkers below |
| 7 | Entry-point equivalence; canonical unchanged | **PASS** | Explicit v1e kwargs equal to canonical + v1e: settings, summary, 0 diverged; canonical control equals the adoption diagnostic |
| 8 | Historical evidence preserved | **PASS** | D1, v1, v1b, v1c, v1d, v1e preregistrations, adoption verification and D1 trace unchanged |
| 9 | Re-exhaustion within 10 s <=0.20 | **PASS** | Episodes 0/68; first clear 0/68 (adopted control: 64/69) |
| 10 | Re-exhaustion within 30 s <=0.35 | **PASS** | Episodes 0/59; first clear 0/59 (adopted control: 64/64) |
| 11 | Denominators >=43 | **PASS** | 68 / 59 at 10 s / 30 s, both denominators |
| 12 | Anti-removal floors | **PASS** | Clearing matches 45 / 82; first-clear median 240 / 240 s (identical to adopted, as predicted) |
| 13 | Clear-window handoff | **PASS** | 71 matches return at the clear window (delay 0); 0 failed handoffs; 11 clear at timeout; +10 s 0/68, +30 s 0/59 |
| 14 | Hold diagnostics | REPORTED | Below |
| 16 | Post-hold return gate | **PASS** | Eligible 44 (>=35); timely 44/44 = 1.00 (>=0.80); late 0; re-exhausted before release 0; pending 0; release delay median/p90 30/30 s |

**Decision: FAIL** (criterion 4). Criteria 15a-15d are descriptive and are reported below.

---

# Criterion 4: why it fails

| Original-100 (seed 42) | v1e | Adopted control | Frozen bound |
|---|---|---|---|
| Escapes | **17** | 35 | >=25 |
| Half / Open / Reversal | 7 / 5 / 5 | 16 / 10 / 9 | each +/-10 |
| Timeouts | **78** | 60 | <=70 |
| Tap | 5 | 5 | <=9 |

The seed-142 batch shows the same direction: escapes 20 versus 29, timeouts 76 versus 67.

**Seed-matched attribution (pooled, 200 matches).** v1e is inactive before the first clear, so every outcome change comes after it. 30 matches changed outcome:
- 28 escapes were lost, and all 28 became timeouts;
- 1 escape was gained (timeout to Half Guard);
- 1 changed escape type (Open to Half).

For each lost escape, the control's escaping attempt was:

| Control's escaping attempt | Lost escapes |
|---|---|
| **The +10 s MEDIUM after the clear** (non-Exhausted, almost all in the Stable band) | **18** |
| A later non-Exhausted MEDIUM (+150 s) | 1 |
| Exhausted LOW at +20 to +50 s (Loose/Stable band) | 9 |

**The dominant mechanism is the very initiation the candidate removes.** On the adopted path, the +10 s MEDIUM is the attempt that re-exhausts Bottom (26 → 19), the oscillation D1 characterized. In 18 matches that same attempt was the escape. v1e replaces it with a hold. The adopted policy's Exhausted LOW attempts after re-exhaustion produced the other 9 escapes, and v1e removes those windows too.

**Bottom initiates less after the first clear.** Pooled OFF + shadow, Bottom initiations after the first clear numbered 163 under v1e against 306 in the control.

**The positional drift side effect is real and adds to the loss, but it is secondary in this data:**
- **Theoretical versus realized drift:** 608 forced-CONSERVE advances. Theory gives 608 × 0.25 = 152 axis units of extra drift toward Top. Realized was **120.5** (actual 406.0 against an ESCAPE counterfactual of 285.5 from the same starts), with band limits and clamping absorbing the rest. In 84 forced advances the resulting band differed from the ESCAPE counterfactual.
- **More time in STRONG/LOCKED:** after the first clear, 83.6% of decision windows were in STRONG/LOCKED under v1e, against 80.8% in the control.
- **Release attempts start tight:** the first post-release Bottom initiation started in Locked 56 times, Strong 30 and Stable 6 (92 releases). STRONG/LOCKED carry the existing −1 positional modifier for Bottom. Most control escaping attempts started in Stable or Loose.
- **Escape-loss matches were tighter under v1e:** in the 28 matches, the median post-clear STRONG/LOCKED share was 0.85 under v1e against 0.67 in the control.
- **Why the drift is not the main cause:** the drift pushes post-release attempts into worse bands. But 19 of the 28 lost escapes came from windows v1e replaced with a hold, which leaves no attempt for the band to affect. The drift cannot be cleanly separated from the removed initiations with this design, and no counterfactual run was made.

The late first clear makes all of this worse (median 240 s of 300 s). After the clear, a typical match has only a few Bottom windows left. Holding 20-30 s out of about 60 s gives up most of the remaining exit chances.

---

# Stability and return: the targeted problem is fixed

- **No re-exhaustion after a clear at any horizon:**
  - 0/68 at 10 s and 0/59 at 30 s, against 64/69 and 64/64 for the adopted control.
  - No post-clear re-entry of any cause occurred in any match.
  - No reserve-model violation: the drain to Bottom's next window was 0 or 2.
- **Return to MEDIUM works as intended:**
  - Every eligible first hold cycle released to MEDIUM within 30 s: 44/44. Across all cycles, releases took 20 s (48) or 30 s (44).
  - Every release requested MEDIUM, and no release window became a policy RESET.
  - After a release, no match re-exhausted within 10 s or 30 s (3 and 33 episodes censored by match end).
- **The 19 matches that never released** all entered recovery with less than 40 s left (ineligible) and ended by timeout.

## Traced prediction versus reality

| | Predicted (preregistration) | Measured (pooled, OFF + shadow) |
|---|---|---|
| Cycle shape | 26→30→34→38 release; then entries 29, 28, 27 | Entries 26 (64), 29 (39), 28 (24), 27 (9); releases at 38 (44), 37 (30), 36 (16), 35 (2) |
| Holds per released cycle | 3, 2, 2, 2 | 3 (44), 2 (48) |
| Entry to next entry | 40 s, then 30 s | 40 s (39), 30 s (34) |
| MEDIUM initiations | 4 per 130 s ≈ 3.08 per 100 s | 2.34 per 100 s after first entry |
| Bottom windows held | ~69% | 76.8% after first entry |
| Stamina at Bottom windows | 26-38 | 26-38 |
| Time in recovery mode | (not predicted as a share) | 77.4% of time after first entry; post-clear median 66.7% (pooled 65.9%) |

The cycle arithmetic held exactly. MEDIUM frequency was lower and the held share higher than the steady-state prediction. The reason is that matches end mid-cycle: 44 cycles were pending at the end, almost all in a hold, and the 130 s period rarely completes after a late first clear.

## Hold and reserve diagnostics (14 / 15 / 15b / 15c / 15d; pooled OFF + shadow; ON identical)

- **Holds:**
  - 304 holds in 63 armed matches with at least one hold. 19 clearing matches never held: 11 cleared at timeout, 3 escaped to Half Guard in the clear window, and 5 timed out 10 s after the clear.
  - Consecutive holds were 1 (18 runs), 2 (68) or 3 (50); the longest run was 3.
  - Every hold had a progress route available, and 207 had a setup builder available. These are forgone opportunities, reported as counterfactuals only.
  - 0 free windows were consumed by holds, and no free Bottom window occurred in the mode.
- **Attribution:**
  - Against v1: same 260, LOW → HOLD 121, MEDIUM → HOLD 86.
  - Against v1c: same 359, "LOW-safe held by mode" 108.
  - Reserve-rule LOW requests outside the mode: 0.
- **Stalling:**
  - The shadow Bottom clock at holds was 5 s (300) or 10 s (4), and no hold was at or above the 20 s threshold.
  - Real W/P/PR: 0.
- **Persistent CONSERVE:**
  - 608 forced advances gained +1,216 stamina, exactly +2 each.
  - Behaviour switches totalled 1,422, of which 1,216 were mode-induced flips (bookkeeping) and 206 were other switches.
  - Resolution saw the unchanged re-choice at every non-free window.
- **Isolation proofs:**
  - All 608 holds (178 + 126 per batch, both stalling modes) consumed no RNG and changed no engine state.
  - No hold reached the RESET or shadow-stalling hooks: `reset_window` calls equal recovery-collector RESET hooks on every run.
  - Instrumented replays equal the uninstrumented runs.
  - The collector's episodes equal the A9 observer's episodes exactly.

---

# Verification

| Check | Result |
|---|---|
| Full unit suite, Python 3.11.17 / 3.13.16 / 3.14.8 (local) | see the commit report |
| Frozen digest | `3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2` (exact) |
| Semantic checker / legacy entry point | PASS / PASS |
| Exact-head CI (3.11, 3.13) | see the commit report |

# Interpretation (descriptive only; no action taken)

- **v1e meets its design goal.** It removes the LOW → MEDIUM oscillation completely and returns deterministically to MEDIUM within 20-30 s. Absolute stability and post-hold return both pass with margin.
- **The cost is the one preregistered as the main risk:** fewer post-clear Bottom initiations, and so fewer escapes and more timeouts, beyond the frozen criterion-4 tolerance.
- **The data shows why.** The adopted policy's oscillating MEDIUM at +10 s, and its Exhausted LOW attempts, were where most post-clear escapes came from. Stability and exit production pull against each other on this surface, because the first clear comes so late.

Per the preregistration, this FAIL is recorded with exact SHAs and settings, and work stops here. Any next step needs explicit user authorization and, for any new candidate, a new preregistration. That includes deferring debt 1, revisiting what criterion 4 should protect, or a different candidate.

**Not done and not authorized:** canonical integration, any change to `PRODUCTION_STAMINA_RECOVERY_POLICY`, PR #10 changes or merge, retuning v1e, v1f or any other candidate, Rule 2 work, default changes, frontend work, squash, force-push.
