# Joint Tactical Evaluator — Stage 1A-v2 Result (projection v2, shadow only)

## Status

**STAGE 1A-v2 = PASS.**

| C1 | C2 | C3 | C4 | C5 | C3-H |
|---|---|---|---|---|---|
| PASS | PASS | PASS | PASS | PASS | PASS |

The evidence is valid and complete. Integrity holds on all 13 runs, and every frozen baseline reproduces exactly.

**HARD STOP.** `TACTICAL_V1` is not wired. Stage 1B was not run. No gate, threshold, production policy or gameplay changed. Stage 1A (`2d2778d`, FAIL) stays historical and unchanged.

```text
preregistration (binding):  5b57017434514e75bee005834d6b04884e17194f
                            docs/TACTICAL_EVALUATOR_PROJECTION_V2_PREREGISTRATION.md
                            (revising 4e61bad section 2.4; review decisions D1-D5 recorded)
Stage 1A (FAIL, unchanged): 2d2778d88205874e30aeda37579dc45d5d9f885e
branch:                     review/tactical-evaluator-projection-v2
projection v2 (pure):       src/bjj_game/interfaces/tactical_projection_v2.py
immediate evaluator:        src/bjj_game/interfaces/tactical_evaluator.py (unchanged since 24e8591)
observer + scoring:         src/bjj_game/diagnostics/tactical_evaluator_v2.py
evidence (summary):         docs/evidence/tactical_evaluator_stage1a_v2.json
evidence (per event):       docs/evidence/tactical_evaluator_stage1a_v2_records.json.gz
tests:                      tests/test_tactical_projection_v2.py (window ordering, mechanics)
                            tests/test_tactical_evaluator_stage1a_v2_evidence.py (evidence pin)
frozen digest:              3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

The authoritative measurement was run **once**. It ran after the mechanics and ordering tests, the full suite, the digest and both checkers had passed. Python 3.13.16 was used on the working tree of this commit. Each surface ran in its own fresh interpreter, and the parts were merged in surface order:

```bash
PYTHONPATH=src python3.13 -m bjj_game.diagnostics.tactical_evaluator_v2 --jobs 13
```

**Disclosed execution history:**
- Two earlier launches used a forked process pool. Both aborted when pool workers crashed with SIGSEGV inside CPython (`subtype_dealloc`, core dumps at 14:58 and 15:02) before any surface finished. No results were produced, read or kept.
- The driver was then changed to one fresh interpreter per surface. The measurement code did not change.
- Debug smoke runs (2-4 matches) were used only to check instrumentation and speed. They are not evidence and were not scored.

---

# 1. What was built (Stage 1A-v2 scope only)

**Projection v2** replaces only `project_setup`. It is the bounded alternating-window continuation of preregistration section 2:

- **Horizon.** r builder windows and r opponent windows in strict alternation, with an advance before each later window and before the Ready use.
- **Exact distribution.** Branch weights are exact `Fraction`s. Branches merge only on equality of every continuation-relevant field: the `te.State` fields, the clock, and the copied D3-B fields. Behavior-meter remainders are asserted to stay 0. There is no pruning, cutoff, sampling or averaging. Branch growth stayed small: at most 270 live branches, a mean of about 23 on the Recognition surfaces, and 4 on A-PROD.
- **Engine-native steps.** Each step runs the engine's own code on a sandbox `MountMatch`, a fresh instance with the live configuration, loaded with the branch state:
  - `attempt()` for every enumerated chance case of an exchange (Recognition read, response commitment, response id: the frozen enumeration, pinned equal to `outcome_distribution`);
  - between windows, the batch behavior choice, then `advance()`, then D3-B `observe_advance`, then the post-advance re-choice;
  - `recovery_hold()` for D3-B LOCKOUT_HOLD.

  The runtime ordering frozen at review (preregistration 2 step 8) therefore holds by construction. `MountMatch` holds no RNG, and the live match is never touched.
- **Opponent windows (O-3).** The real `EscapeFirstInitiatorPolicy.choose` runs on the branch state. Around it sit the batch's commitment selection (LOW while Exhausted under RECOVER), recovery precedence and a copied D3-B controller.
  - Depth is exactly 1. When the observer sees a policy call on a sandbox, it passes the call straight through and never starts a nested TE-1 evaluation.
  - Stalling evaluation at opponent resets is not modeled (preregistration 2 step 1).
- **Use window.** The frozen use valuation runs at each branch where T is Ready. `setup_future` is Σ P(branch) · max over fully fundable c′ of V. The C5 scoring variant values the use at the baseline's requested commitment instead.

**Unchanged:**
- the immediate evaluator (C1 and C2 equal the committed Stage 1A values exactly, checked per surface);
- TE-1 selection;
- the engine, domain, batch policy, response policy, Recognition, settlement, stamina, D3-B, production policy and defaults.

---

# 2. Integrity (all 13 runs)

| Check | Result |
|---|---|
| Evaluator RNG draws, including every sandbox step | **0** on every run |
| Baseline RNG sequence (count + sha256 over every draw) vs evaluator-free run | identical |
| `BatchSummary` vs uninstrumented run; per-match gameplay signatures | identical |
| Deterministic replay: second observed run (summary, signatures, every record including v2 values, RNG digest) | identical |
| C0: pure path vs real exchange | exact on every exchange (for example A-PROD 4,612/4,612; PROTECT 5,696/5,696) |
| **O-3 surrogate vs every real Bottom decision** (action, D3-B kind) | exact on every run (for example A-PROD 2,306/2,306; E-PROD 42 2,351/2,351; PROTECT 2,848/2,848) |
| D3-B counterfactual exclusion | E-PROD 42: 63 = 63; E-PROD 142: 34 = 34; holdouts: 4242 26 = 26, 4342 41 = 41 |
| C1 / C2 equal to committed Stage 1A values | exact on all 7 frozen runs |
| Frozen baseline reproduction (Threat, Tap, escapes, timeouts, Top builds) | exact on all 7 frozen runs; holdout baselines recorded before scoring |

**Window ordering** (`tests/test_tactical_projection_v2.py`) was checked on real baseline matches of A-PROD, B-PROD, E-PROD 42 OFF/ON and PROTECT:
- every continuation `advance` from a recorded real post-window state equals the recorded real start of the next window exactly;
- every real exchange's successor is in the exact support of the continuation exchange;
- every real Bottom window's successor is in the support of the O-3 opponent window.

Scratch mutations, not committed, are each caught by these tests: skipping the pre-advance behavior choice; observing D3-B before `advance()`; skipping the post-advance re-choice; ignoring LOW-while-Exhausted; dropping the controller copy.

---

# 3. Gates (scored exactly as preregistered)

## C1 — deterministic exactness (A-PROD): **PASS**

2,384 / 2,384. Identical to Stage 1A; the immediate layer is unchanged.

## C2 — stochastic calibration: **PASS** (21 / 21)

Identical to Stage 1A on every surface and component.

## C3 — no S1-style collapse (≥ 80%): **PASS**

| Surface | Stage 1A (frozen projection) | **Stage 1A-v2** |
|---|---|---|
| A-PROD | 0 / 156 (0%) | **156 / 156 (100%)** |
| B-PROD | 69 / 118 (58%) | **118 / 118 (100%)** |
| E-PROD 42 (OFF + shadow / ON) | 68 / 122 (56%) | **122 / 122 (100%)** each |
| E-PROD 142 (OFF + shadow / ON) | 67 / 114 (59%) | **114 / 114 (100%)** each |

As disclosed in preregistration 4.2, C3 passes nearly by construction under O-3 on the baseline. This is why C5 and C3-H were added.

## C4 — churn recognition (PROTECT, ≥ 50%): **PASS**

**1,964 / 1,964** baseline Top builder decisions have setup_future = 0 (100%), the same as Stage 1A. The prediction that C4 would pass with less margin did not hold. The continuation reproduces PROTECT's mutual drain, so no branch reaches a positive Ready value.

## C5 — setup_future calibration (unconditional, every chain start): **PASS**

The test is (observed − Σp)² ≤ 9 · Σp(1−p), with p = setup_future at the baseline builder commitment and the use at the baseline commitment (MEDIUM).

| Surface | Chain starts | Predicted Σp | Observed | σ | z | Result |
|---|---|---|---|---|---|---|
| A-PROD | 178 | **78.00** | **78** | 0 | exact | PASS |
| B-PROD | 451 | 55.68 | 59 | 5.51 | +0.60 | PASS |
| E-PROD 42 (each mode) | 454 | 56.32 | 61 | 5.49 | +0.85 | PASS |
| E-PROD 142 (each mode) | 447 | 57.28 | 57 | 5.42 | −0.05 | PASS |
| PROTECT probe | 982 | **0.00** | **0** | 0 | exact | PASS |

On the two deterministic surfaces (σ = 0), the continuation predicts the realized conversion count **exactly**. The Recognition surfaces are within 1σ.

The C5 assertion that the actual use commitment equals the baseline's (MEDIUM) held on every used chain. Every builder decision used the batch commitment.

## C3-H — holdout (C3 on fresh seeds, ≥ 80%): **PASS**

| Holdout surface | setup_future > 0 / converted-chain decisions | Holdout baseline (Threat, Tap, escapes, timeouts, Top builds) |
|---|---|---|
| A-PROD 4242 | 154 / 154 (100%) | 77, 0, 23, 77, 308 |
| B-PROD 4242 | 99 / 99 (100%) | 49, 8, 21, 71, 824 |
| E-PROD 4242 (OFF + shadow / ON) | 99 / 99 (100%) each | 49, 2, 42, 56, 790 |
| E-PROD 4342 (OFF + shadow / ON) | 114 / 114 (100%) each | 57, 1, 42, 57, 725 |

The seeds and kwargs are exactly those frozen at D4. No seed was replaced or added.

---

# 4. Reported (not gated)

**C5 on the holdouts** (not gated; C5 is scored on the frozen surfaces only):

| Surface | Σp | Observed | z |
|---|---|---|---|
| A-PROD 4242 | 77.00 | 77 | exact |
| B-PROD 4242 | 56.09 | 49 | −1.27 |
| E-PROD 4242 | 55.33 | 49 | −1.15 |
| E-PROD 4342 | 53.59 | 57 | +0.64 |

All are within 2σ.

**Use-state fidelity at converted chain starts** (projection at the baseline commitment vs realized use state):

| Surface | P(Bottom Exhausted): predicted Σ / realized | P(Strong/Locked): predicted Σ / realized | Mean axis error |
|---|---|---|---|
| A-PROD | 78.0 / 78 | 78.0 / 78 | +0.013 |
| B-PROD | 29.1 / 32 | 52.9 / 59 | −0.20 |
| E-PROD 42 | 30.7 / 34 | 56.0 / 61 | −0.11 |
| E-PROD 142 | 27.9 / 30 | 52.4 / 57 | −0.14 |

Compare the frozen projection on the same chains (characterization section 3.2): Bottom stamina was off by +14 to +19, axis by −1.6 to −1.7, and the projection never had a Bottom Exhausted on A-PROD. These rows are conditioned on conversion, so the predictions are expected to fall slightly below realized. They are reported only.

**TE-1 shadow tiers, Top** (for later stages; not gated):

| Surface | setup | progress | terminal | position | reset |
|---|---|---|---|---|---|
| A-PROD | 156 | 78 | 0 | 0 | 2,150 |
| B-PROD | 336 | 242 | 10 | 17 | 1,883 |
| E-PROD 42 | 331 | 255 | 9 | 13 | 1,876 |
| E-PROD 142 | 336 | 246 | 10 | 10 | 1,833 |
| PROTECT | 0 | 0 | 0 | 0 | 2,946 |

On A-PROD, TE-1 now picks setup only from states where the continuation reaches a Ready use with value. Under Stage 1A it never picked setup. It still resets in most Top windows of the baseline trajectory. Whether that preserves submission access in play (G1) is a Stage 1B question and was not measured.

**Cost.** The authoritative run took 14 m 22 s wall time and 124 CPU-minutes across 13 processes.

---

# 5. Interpretations fixed before the measurement (disclosed)

| Item | Reading used |
|---|---|
| Stalling at opponent resets / free windows | Not modeled (preregistration 2 step 1). A reset only passes initiative |
| Projecting side's later builds | Fixed to (a, c), with no own D3-B or recovery precedence (preregistration 2 step 3) |
| Clock reaching 0 / exit / Tap inside the continuation | Terminal branch, use value 0 |
| C5 chain | Stage 1A C3 chain: Top setup decisions closed by the next Top Ready use, or open at match end; first decision = chain start |
| C5 use commitment | The batch's Top commitment (MEDIUM), requested and funded as the engine funds it; asserted equal to the actual use commitment |
| E-PROD stalling modes | Each mode scored as its own run; OFF + shadow and ON are identical in every value |
| D3-B controller in branches | Copied (armed, token_consumed, last observed Exhausted); the live controller is never touched |

---

# 6. Verification

| Check | Result |
|---|---|
| `tests.test_tactical_projection_v2` | 9 tests OK (ordering pins, exact enumeration, purity / depth 1, merge key, C5 population, holdout surfaces) |
| `tests.test_tactical_evaluator_stage1a_v2_evidence` | re-measurement (without the replay run) equals the committed summary on all 13 runs |
| Full local suite, frozen digest, both checkers | see the final report for this head |

---

# 7. Hard stop

**Not done, and not authorized:**
- `TACTICAL_V1` gameplay wiring;
- Stage 1B, or any G1-G6 candidate scoring;
- any change to C1-C5, C3-H, G1-G6 or thresholds;
- production-policy changes;
- merge to main.

Stage 1B requires its own authorization.

**HARD STOP.**
