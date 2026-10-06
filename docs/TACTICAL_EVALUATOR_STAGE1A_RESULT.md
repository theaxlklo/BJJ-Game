# Joint Tactical Evaluator — Stage 1A Result (shadow only)

## Status

**STAGE 1A = FAIL.** C1 PASS, C2 PASS, **C3 FAIL**, C4 PASS. The evidence is valid and complete. Integrity holds on every surface, and every baseline reproduces exactly.

**HARD STOP.** Per preregistration section 3, a FAIL is recorded and the slice stops. There is no projection revision, no tuning and no gate or tolerance change. **Stage 1B was not run.** `TACTICAL_V1` is not wired into gameplay.

```text
preregistration (binding):  4e61bada3998e1d97bdeaba975e92aa282c92bfb
                            docs/TACTICAL_EVALUATOR_PREREGISTRATION.md (unchanged)
implementation + result:    the commit that adds this document
branch:                     review/tactical-evaluator-preregistration
evaluator (pure):           src/bjj_game/interfaces/tactical_evaluator.py
observer + C1-C4 scoring:   src/bjj_game/diagnostics/tactical_evaluator.py
evidence (summary):         docs/evidence/tactical_evaluator_stage1a.json
evidence (per event):       docs/evidence/tactical_evaluator_stage1a_records.json.gz
tests:                      tests/test_tactical_evaluator.py (mechanics, integrity)
                            tests/test_tactical_evaluator_stage1a_evidence.py (evidence pin)
frozen digest:              3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

The authoritative measurement was run **once**, after the mechanics tests, the inertness tests, the full suite, the digest and both checkers had passed. It ran under Python 3.13.16 on the working tree of this commit:

```bash
PYTHONPATH=src python3.13 -m bjj_game.diagnostics.tactical_evaluator
```

Debug smoke runs (2-6 matches) were used only to check the instrumentation. They are not evidence and were not scored.

---

# 1. What was built (Stage 1A scope only)

- **`TacticalValue`**: an exact tuple per `(action, requested commitment)`: terminal, progress, setup_future, axis_realized, axis_raw, stamina_cost and enters_exhausted. It also carries an auxiliary setup_advance (the chain input and the C2 component), which TE-1 does not rank. All probabilities and expectations are exact `Fraction`s, so TE-1 comparisons and C2 sums carry no rounding and use no epsilon.
- **Resolution** mirrors `MountMatch._resolve_attempt_resolution` on a state snapshot. The order is matchup/Ready/submission, then exhaustion, then the initiator magnitude, then responder undercommitment. It calls the engine's own `_commitment_grade_transform`, `resolve_action`, `effective_commitment`, `CommitmentRecognitionPolicy.read`, `RandomBlindResponder.weighted_policy`, `setup_advances_from` and `StaminaPool` latch code.
- **Opponent models** (E1):
  - Top initiator: informed Bottom. The 3 × 3 Recognition classes are enumerated with weights (1, 4, 1)/6 each. Each class gives a response commitment from the surface mode, and Bottom's response is the minimum grade under the perceived effective commitment. The actual grade comes from the true commitments.
  - Bottom initiator: random-blind Top weights.
- **Bounded projection** (section 2.4): r builds plus one use, Δ = 2·r·interval, and a single chain. Opponent stamina is projected by behavior flow only. There is no recursion and no search.
- **TE-1** (section 2.5):
  - Tiers A/B compare pairs directly, under the strict stamina guard.
  - Tiers C/D reduce each action to its cheapest qualifying commitment, then compare.
  - The frozen tie-breaks apply.
  - Section 2.6 precedence: Bottom RECOVER while Exhausted allows LOW only. D3-B LOCKOUT_HOLD windows are never evaluated.
- **Shadow observer**: scoped wrappers on `EscapeFirstInitiatorPolicy.choose`, `MountMatch.attempt` and `D3BTokenLockoutController.decide` (read-only), plus counting wrappers on `random.Random`. Each real call is delegated exactly once. Realized events are read from the engine's own history.

**Unchanged:** engine, domain, batch policy (ESCAPE_FIRST, fixed commitments), response policy, Recognition, settlement, stamina costs, rates and thresholds, D3-B, production policy, defaults.

---

# 2. Integrity (all surfaces)

| Check | Result |
|---|---|
| Evaluator RNG draws | **0** on every surface (every `random.Random` draw method counted while the evaluator runs) |
| Baseline RNG sequence | identical to an evaluator-free run: same draw count and same sha256 over every draw result, in order |
| `BatchSummary` | identical to an uninstrumented run and to the evaluator-free reference |
| Per-match gameplay signatures | identical to the evaluator-free reference |
| Deterministic replay | the second observed run is identical: summary, signatures, every event record, RNG digest |
| C0: pure path vs real exchange | 34,230 / 34,230 exchanges exact (grade, axis, exit) |
| D3-B counterfactual exclusion | E-PROD 42: 63 = 63 holds; E-PROD 142: 34 = 34 holds (each stalling mode) |
| Baseline reproduction (section 4 table) | exact on all 7 runs (Threat, Tap, escapes, timeouts, Top builds) |

---

# 3. Gates (frozen; scored exactly as preregistered)

## C1 — deterministic exactness (A-PROD): **PASS**

2,384 / 2,384 Top exchanges have a deterministic prediction at the baseline's actual commitment, and it equals the realized grade. There are 0 mismatches.

(The `C1` block of the other surfaces is reported only. There, `mismatches` counts stochastic Recognition predictions, not errors.)

## C2 — stochastic calibration: **PASS** (21 / 21 surface × component)

All baseline exchanges of each run, both sides pooled, at the baseline's actual `(action, commitment)`. The test is exact: (actual − Σp)² ≤ 9·Σp(1−p). The by-side breakdown is in the evidence.

| Surface | Component | n | Predicted Σp | Actual | σ | Deviation | z | Result |
|---|---|---|---|---|---|---|---|---|
| A-PROD | terminal | 4,612 | 18.00 | 22 | 2.45 | +4.00 | +1.63 | PASS |
| A-PROD | progress | 4,612 | 78.00 | 78 | 0.00 | +0.00 | — | PASS |
| A-PROD | setup-advance | 4,612 | 1138.67 | 1,133 | 18.83 | -5.67 | -0.30 | PASS |
| B-PROD | terminal | 4,860 | 18.50 | 21 | 2.25 | +2.50 | +1.11 | PASS |
| B-PROD | progress | 4,860 | 121.75 | 126 | 6.33 | +4.25 | +0.67 | PASS |
| B-PROD | setup-advance | 4,860 | 2045.98 | 2,053 | 15.21 | +7.02 | +0.46 | PASS |
| E-PROD 42 OFF | terminal | 4,804 | 30.78 | 35 | 3.52 | +4.22 | +1.20 | PASS |
| E-PROD 42 OFF | progress | 4,804 | 106.00 | 109 | 6.77 | +3.00 | +0.44 | PASS |
| E-PROD 42 OFF | setup-advance | 4,804 | 2383.31 | 2,386 | 5.78 | +2.69 | +0.46 | PASS |
| E-PROD 42 ON | terminal | 4,804 | 30.78 | 35 | 3.52 | +4.22 | +1.20 | PASS |
| E-PROD 42 ON | progress | 4,804 | 106.00 | 109 | 6.77 | +3.00 | +0.44 | PASS |
| E-PROD 42 ON | setup-advance | 4,804 | 2383.31 | 2,386 | 5.78 | +2.69 | +0.46 | PASS |
| E-PROD 142 OFF | terminal | 4,727 | 36.72 | 35 | 3.70 | -1.72 | -0.47 | PASS |
| E-PROD 142 OFF | progress | 4,727 | 102.25 | 108 | 6.63 | +5.75 | +0.87 | PASS |
| E-PROD 142 OFF | setup-advance | 4,727 | 2342.13 | 2,333 | 6.04 | -9.13 | -1.51 | PASS |
| E-PROD 142 ON | terminal | 4,727 | 36.72 | 35 | 3.70 | -1.72 | -0.47 | PASS |
| E-PROD 142 ON | progress | 4,727 | 102.25 | 108 | 6.63 | +5.75 | +0.87 | PASS |
| E-PROD 142 ON | setup-advance | 4,727 | 2342.13 | 2,333 | 6.04 | -9.13 | -1.51 | PASS |
| PROTECT probe | terminal | 5,696 | 1.67 | 2 | 1.05 | +0.33 | +0.32 | PASS |
| PROTECT probe | progress | 5,696 | 0.00 | 0 | 0.00 | +0.00 | — | PASS |
| PROTECT probe | setup-advance | 5,696 | 3828.67 | 3,830 | 5.75 | +1.33 | +0.23 | PASS |

## C3 — no S1-style collapse: **FAIL** (floor ≥ 80% on every applicable run)

Population: baseline Top setup decisions whose chain ended in a Threat entry at the next Ready use. The value is TE-1 `setup_future` at that decision, taken as the maximum over the builder's candidate commitments.

| Surface | setup_future > 0 / population | Share | Result |
|---|---|---|---|
| A-PROD | **0 / 156** | **0.0%** | FAIL |
| B-PROD | 69 / 118 | 58.5% | FAIL |
| E-PROD 42 (OFF + shadow) | 68 / 122 | 55.7% | FAIL |
| E-PROD 42 (ON) | 68 / 122 | 55.7% | FAIL |
| E-PROD 142 (OFF + shadow) | 67 / 114 | 58.8% | FAIL |
| E-PROD 142 (ON) | 67 / 114 | 58.8% | FAIL |

## C4 — churn recognition (PROTECT probe): **PASS**

1,964 / 1,964 baseline Top setup decisions get `setup_future` = 0 (100%; floor 50%).

---

# 4. Why C3 fails (read from the recorded projections; nothing changed)

Every converted-chain decision with `setup_future` = 0 falls into one of two classes:

| Surface | Zero: every projected use state is Loose/Stable (Threat entry impossible) | Zero: Strong/Locked projected, but projected Bottom not Exhausted |
|---|---|---|
| A-PROD | 33 | **123** |
| B-PROD | 45 | 4 |
| E-PROD 42 (each mode) | 49 | 5 |
| E-PROD 142 (each mode) | 43 | 4 |

1. **Opponent drain not projected (the declared section 2.4 / section 5 bias).** On A-PROD, every actual conversion happens against a Bottom who is drained, or cannot fund a matching response, at use time. The projection advances Bottom's stamina by behavior flow only. It deliberately omits Bottom's own initiations and responses, so the projected Bottom stays Tired rather than Exhausted. Against a non-Exhausted informed defender, Ready Arm Isolation is always answered with the Contested stalemate, so the use value is 0. Section 5 recorded this risk before any implementation: "If C3 fails for that reason, the remedy is a new preregistration revision, never a tolerance change."
2. **Axis projection lands outside Strong/Locked.** The climb's expected realized axis per build is negative in many states (9908235: about −0.85 to −1.0 per build). Step 5 projects axis + r × E[realized]. This often lands in Loose/Stable, where Threat entry is impossible. On production, the actual chains reached Strong/Locked through intervening drift, Bottom attempts and position changes. The bounded single-chain projection excludes those by design.

So the S1-style collapse is reproduced on A-PROD (0%, as S1). On the Recognition surfaces it is only partly avoided (about 56-59%).

**Interpretation check: use-time fundability.** At use, the evaluator counts a commitment c′ as fundable when cost(c′) ≤ projected own stamina, so UNFUNDED is excluded. This reading of "fundable at the projected own stamina" (step 6) was fixed before the measurement. It does not affect C3:

- no converted-chain projection on A-PROD or E-PROD has projected own stamina below 3;
- B-PROD has 2 such rows; even if both counted, the share would be 71/118 = 60.2%, still below 80%.

---

# 5. Reported (not gated)

**Ready conversion, predicted vs actual (section 2.4 format of 9908235):**

| Surface | Top Ready Arm Isolation: uses / predicted / actual | Bottom Ready Trap-and-Roll: uses / predicted / actual |
|---|---|---|
| A-PROD | 156 / 78.00 / 78 | 355 / 0.00 / 0 |
| B-PROD | 440 / 57.22 / 59 | 521 / 0.67 / 2 |
| E-PROD 42 | 422 / 59.14 / 61 | 701 / 4.67 / 8 |
| E-PROD 142 | 420 / 58.14 / 57 | 683 / 3.00 / 1 |
| PROTECT probe | 884 / 0.00 / 0 | 884 / 1.67 / 2 |

**The use-time valuation is now calibrated where it previously failed.** In 9908235, the policy's random-blind estimate was about 4× too high (for example 231.8 vs 61). Its static informed estimate was too low under Recognition (24 vs 61). Exact Recognition enumeration plus the commitment transform gives 59.1 vs 61. The failure is in the projection to the use state, not in the use-time model.

**TE-1 shadow choices.** Tier and commitment by side are recorded per run in the evidence (`te1_tier_distribution`, `te1_commitment_distribution`, `baseline_vs_te1`).

- On A-PROD, TE-1 never picks setup, because `setup_future` = 0 in all 356 Top setup decisions. It would RESET in 2,306 of 2,384 Top windows: the C3 collapse in action.
- Tier C/D commitments are overwhelmingly LOW. Bottom terminal choices are mostly HIGH (A-PROD 127/127; E-PROD 42: 88 HIGH / 79 LOW). Top progress choices are mostly MEDIUM on the Recognition surfaces.

**Other recorded data:**

- `setup_future` distributions:
  - PROTECT: 1,964 zero.
  - A-PROD: 356 zero.
  - B-PROD / E-PROD: about 82% zero, 9th decile 0.306, maximum 1.
- Calibration by side.
- Projection traces for every Top setup decision: projected own and opponent stamina and bands, axis, band, and use value per commitment.
- Per-event records with exact fractions.

---

# 6. Interpretations fixed before the measurement (disclosed)

| Item | Reading used |
|---|---|
| Use-time fundable commitments (2.4 step 6) | c′ with cost(c′) ≤ projected own stamina (UNFUNDED excluded). Shown immaterial to C3 in section 4. |
| Latch at use (2.4 step 4) | One application of the existing `StaminaPool` hysteresis to the projected value, from the current latched state (as written) |
| "Top builder decisions" (C3, C4) | Baseline Top decisions with reason `setup`. On every run, all High Mount Climb decisions had reason `setup`, so this equals all Top builder decisions. |
| TE-1 `setup_future` of a decision | Maximum over the builder's candidate commitments after the section 2.3 duplicate drop (TE-1 admits a builder with setup_future > 0 "at some commitment") |
| C2 population | All baseline exchanges of the run, both sides pooled; by-side reported |
| Realized progress / Threat entry | The engine's `submission_change_history`: an `entry:` event, or a Threat→Control / Control→Finish advance |
| E-PROD stalling modes | Each mode scored as its own run; OFF + shadow and ON are identical in every value |

---

# 7. Verification

| Check | Result |
|---|---|
| `tests.test_tactical_evaluator` | 48 tests OK |
| Full local suite | see the final report for this head |
| Mutation check (scratch only, not committed) | omniscient defender, reversed transform order, dropped exhaustion, skewed random-blind weights, reduce-to-highest and UNFUNDED-at-use: each caught by the tests |
| Frozen digest | exact |
| Semantic checker (`python -m bjj_game --check`) | PASS |
| Legacy checker (`python -m mount_v0 --check`) | PASS |
| Evidence pin | re-measurement equals the committed summary (RNG count and digest compared within the run, since they depend on the interpreter) |

---

# 8. Hard stop

**Not done, and not authorized:**

- `TACTICAL_V1` gameplay wiring;
- Stage 1B or any candidate run;
- any change to C1-C4, G1-G6, the projection, Recognition, response policy, settlement, stamina, D3-B or production policy;
- tuning;
- merge, squash or force-push.

Under the preregistration, the only route forward after a C3 failure is a **new preregistration revision**, reviewed before any implementation. Choosing whether and how is the user's decision.

**HARD STOP.**
