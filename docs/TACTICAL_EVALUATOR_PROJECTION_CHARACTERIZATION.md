# Tactical Evaluator — Projection-Error Characterization (read-only)

## Status

**CHARACTERIZATION ONLY — NO EVALUATOR, GATE OR GAMEPLAY CHANGE — HARD STOP FOR REVIEW.**

Stage 1A stays **FAIL** (C1 PASS, C2 PASS, **C3 FAIL**, C4 PASS). This slice does not revise, rerun or re-score it. It answers one question from the frozen evidence:

> Between a baseline Top builder decision and its Ready use, which state changes did the frozen section 2.4 projection omit, and which of them decide C3?

```text
branch:              review/tactical-evaluator-projection-v2
base (Stage 1A FAIL): 2d2778d88205874e30aeda37579dc45d5d9f885e  (immutable, reachable)
preregistration:     4e61bada3998e1d97bdeaba975e92aa282c92bfb  (unchanged)
evaluator:           src/bjj_game/interfaces/tactical_evaluator.py  (unchanged)
instrument:          src/bjj_game/diagnostics/projection_characterization.py
evidence:            docs/evidence/tactical_evaluator_projection_characterization.json
tests:               tests/test_projection_characterization.py (mechanics, closure)
                     tests/test_projection_characterization_evidence.py (evidence pin,
                     Stage 1A evidence sha256 unchanged)
command:             PYTHONPATH=src python3.13 -m bjj_game.diagnostics.projection_characterization
```

**Not done:** projection v2 implementation, any TE-1 change, rerunning C1-C4 under a revised evaluator, `TACTICAL_V1` wiring, Stage 1B, any threshold change.

---

# 1. Method

## 1.1 Re-observation of the frozen populations (not a new population)

The Stage 1A per-event records carry outcomes and projection traces, but **no per-window state** (stamina, latches, axis between windows). The frozen surfaces were therefore re-run under the **unchanged baseline** with a read-only state recorder. Scoped wrappers on `advance`, `attempt`, `reset_window`, `recovery_hold` and the real policy decision log state before and after each step. No evaluator runs during play. Each original call is made exactly once, and every wrapper is restored on exit.

It is the same population, verified on every surface:

| Check | Result (all 7 runs) |
|---|---|
| Every decision (t, side, action, reason) equals the committed Stage 1A record | exact (A-PROD alone: 4,690 decisions, 4,612 exchanges) |
| Every exchange (t, side, action, requested/effective commitment, response, realized grade, Ready use, Threat entry, setup advance, exit) equals the record | exact |
| `BatchSummary` vs uninstrumented run | identical |
| Per-match gameplay signatures vs evaluator-free reference | identical |
| Baseline RNG sequence (count + sha256 over every draw) | identical |
| RNG draws by the recorder | 0 |
| Builder-decision order and chain assignment vs Stage 1A C3 rows | identical |
| Stage 1A evidence files | unchanged (sha256 pinned in tests) |

## 1.2 Exact decomposition

For every Top builder decision whose chain reached a Ready use, the change from the decision state (pre-attempt) to the Ready-use state (pre-attempt) splits into:

| Stamina, Top (builder) | Stamina, Bottom (defender) | Axis |
|---|---|---|
| passive behavior flow | passive behavior flow | builder exchange movement |
| commitment spend on its builder exchanges | response (+hold) spend on Top builder exchanges | ordinary drift |
| commitment spend on non-builder exchanges | response (+hold) spend on Top non-builder exchanges | Bottom-initiated exchange movement |
| response spend during Bottom initiations | commitment spend on its own initiations | Top non-builder exchange movement |
| | | stalling penalty / position reset movement |

The components **sum exactly** to the realized change. `attempt` changes stamina only through the initiator, response and hold charges, which is asserted per exchange. Resets and holds change no stamina, also asserted.

## 1.3 Layered attribution (historical substitution, attribution only)

Actual future values are substituted into the frozen projection one group at a time. The **frozen** use valuation is then re-applied: section 2.4 step 6, the same `outcome_distribution`, at the projected state. Chain probability stays the frozen `p_adv^r`. The C3 reading stays Stage 1A's: maximum over the builder's deduplicated candidate commitments.

| Layer | Adds (cumulative) |
|---|---|
| **P0** | frozen projection |
| **P1** | + builder settlement: actual Top builder spend; Bottom's actual response/hold spend on those builders |
| **P2** | + intervening stamina: Bottom's own initiation spend, Top's response spend, Top non-builder exchanges |
| **P3** | + ordinary drift |
| **P4** | + intervening exchange axis movement (Bottom-initiated, Top non-builder) |
| **P5** | + actual passive flow (replaces rate × Δ), actual builder movement (replaces r × E[realized]), stalling movement |
| **P6** | + path: actual stamina latches, axis-band hysteresis and behaviors at use |

Closure, verified on every used chain of every surface:
- **P0 reproduces the committed Stage 1A projection exactly** (own/opponent stamina and band, axis, band, use value per commitment, setup_future);
- **P6 equals the realized use state exactly** (stamina, latches, axis, band);
- **the P6 use value equals a direct valuation of the realized use state**.

Because the layer order affects attribution, every group is also scored alone (`only:`), removed from the full substitution (`without:`), and in composites.

**Historical future values are used here only to attribute the error. They are never a candidate evaluator.** No candidate continuation model is scored against C3 or C4 in this slice (section 5).

---

# 2. Results — layered attribution (C3 population)

Share of C3-population decisions (Top builder decisions whose chain ended in a Threat entry) with setup_future > 0. The floor is 80%.

| Layer | A-PROD | B-PROD | E-PROD 42 | E-PROD 142 |
|---|---|---|---|---|
| **P0** (frozen, = Stage 1A) | **0/156 (0%)** | 69/118 (58%) | 68/122 (56%) | 67/114 (59%) |
| P1 + builder settlement | 78/156 (50%) | 69/118 (58%) | 69/122 (57%) | 66/114 (58%) |
| P2 + intervening stamina | 123/156 (79%) | 73/118 (62%) | 73/122 (60%) | 71/114 (62%) |
| P3 + drift | **156/156 (100%)** | 96/118 (81%) | 100/122 (82%) | 93/114 (82%) |
| P4 + intervening axis | 156/156 | **118/118 (100%)** | **122/122 (100%)** | 112/114 (98%) |
| P5 + flow, builder axis, stalling | 156/156 | 118/118 | 112/122 (92%) | 110/114 (96%) |
| P6 + path (= realized state) | 156/156 | 118/118 | 122/122 | 114/114 |

E-PROD stalling OFF + shadow and ON are identical in every value.

**P0 reproduces the C3 failure exactly.** The P0 zero classes equal the Stage 1A result section 4: A-PROD 33 Loose/Stable + 123 Strong/Locked-but-Bottom-not-Exhausted; B 45 + 4; E-42 49 + 5; E-142 43 + 4.

## 2.1 Order-independent views

| Variant | A-PROD | B-PROD | E-PROD 42 | E-PROD 142 |
|---|---|---|---|---|
| only builder settlement | 50% | 58% | 57% | 58% |
| only intervening stamina | 0% | 54% | 51% | 56% |
| only drift | 0% | 78% | 78% | 78% |
| only intervening axis | 0% | 72% | 68% | 71% |
| only passive flow / only builder axis / only stalling | 0% / 0% / 0% | 58% / 55% / 58% | 56% / 52% / 56% | 57% / 55% / 59% |
| **stamina only** (settlement + intervening + flow) | **79%** | 62% | 52% | 59% |
| **axis only** (drift + intervening + builder + stalling) | **0%** | **97%** | **96%** | **96%** |
| without builder settlement (from P6) | 50% | 98% | 92% | 96% |
| without intervening stamina (from P6) | 100% | 97% | 94% | 96% |
| without drift / intervening axis / flow / builder axis / stalling (from P6) | 100% each | 100% each | 100% each | 100% each |

From P6 (full substitution), removing any single axis group still leaves 100%. The axis groups overlap: drift alone or intervening movement alone moves most chains into Strong/Locked, and any one of them suffices once the others are actual. Only the stamina groups are individually necessary on A-PROD.

## 2.2 Does the opponent's own window need modeling?

| Composite | A-PROD | B-PROD | E-PROD 42 | E-PROD 142 |
|---|---|---|---|---|
| Top's windows + advances only (settlement, flow, drift, builder movement); one-shot latch | 50% | 75% | 75% | 75% |
| + opponent-window stamina | 100% | 79% | 72% | 76% |
| Top's windows + advances, actual path | 100% | 97% | 94% | 96% |
| + opponent-window stamina, actual path | 100% | 100% | 100% | 100% |

**Yes.** Without the opponent's window, A-PROD stays at 50% and the Recognition surfaces stay at 75%.

The "actual path" rows need a caveat. The realized latches already contain the opponent's spends, so they are not separable from the opponent window. A real continuation must produce the latch itself, by stepping the windows.

The single-latch application from the decision state also loses chains on its own. On E-PROD, P5 (every value actual, single latch application from the decision state, decision-time behaviors) → P6 (actual latches, band and behaviors) recovers 10 / 4 chains (seeds 42 / 142). E-PROD is the only surface with a latch-dependent behavior (Bottom RECOVER → CONSERVE while Exhausted). Which of latch, band hysteresis or behavior carries each chain is not split further here.

---

# 3. Results — what the error is made of

## 3.1 Horizon: exact

In **every** converted chain on every surface, the Ready use came exactly **2r windows** after the builder decision (elapsed − 2·r·interval = 0). There were no Top non-builder actions, no stalling movement, no D3-B holds and no free windows inside a converted chain.

The frozen strict-alternation horizon (r builder windows, r opponent windows, then the use) is **correct**. The error is in what happens inside those windows, not in how many there are.

## 3.2 Components (C3 population, mean per chain; r averages 1.5)

| Component | A-PROD | B-PROD | E-PROD 42 | E-PROD 142 | In frozen projection? |
|---|---|---|---|---|---|
| Top passive flow | −3.0 | −3.0 | −3.0 | −3.0 | yes (exact) |
| Top builder spend | −10.5 | −10.5 | −10.5 | −10.5 | yes (exact) |
| **Top response spend** (Bottom windows) | −3.5 | −9.1 | −8.6 | −7.7 | **no** |
| Bottom passive flow | −3.0 | −3.0 | −0.6 | −0.3 | yes (current behavior; E-PROD RECOVER switches) |
| **Bottom response spend on builders** | **−10.5** | −9.8 | −9.9 | −10.8 | **no** |
| **Bottom initiation spend** | −3.5 | −9.3 | −9.0 | −8.1 | **no** |
| Top non-builder spend / Bottom response to them | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | n/a |
| Builder axis movement | −1.50 | −1.05 | −1.10 | −1.19 | expectation (≈ actual) |
| **Ordinary drift** | **+1.35** | **+1.05** | **+1.15** | **+1.28** | **no** |
| **Bottom-initiated movement** | +0.23 | **+0.66** | **+0.58** | **+0.63** | **no** |
| Stalling movement | 0 | 0 | 0 | 0 | n/a |

**Frozen-projection use-state error** (projected − realized, at the baseline's commitment):

| | A-PROD | B-PROD | E-PROD 42 | E-PROD 142 |
|---|---|---|---|---|
| Top stamina (mean / median) | +3.5 / +3.5 | +9.1 / +7 | +8.6 / +7 | +7.7 / +7 |
| Bottom stamina (mean / median) | **+14.0 / +14** | **+19.1 / +19** | **+16.5 / +15** | **+16.5 / +14.5** |
| Axis (mean / median) | −1.58 / −1.00 | −1.69 / −1.39 | −1.68 / −1.39 | −1.73 / −1.69 |
| Bottom Exhausted, projected → realized | notE→E 156 | notE→E 57, E→E 7, notE→notE 54 | notE→E 63, E→E 5, notE→notE 54 | notE→E 49, E→E 11, notE→notE 54 |

The bias is one-signed on every component that was omitted. The projection keeps Bottom too fresh (+14 to +19 stamina) and Top a little too fresh. It places the axis 1.6 to 1.7 too low.

- On A-PROD, **every** conversion faced a Bottom who was Exhausted at use. The projection never had one.
- **Every** chain the projection placed in Loose/Stable was realized in Strong or Locked: A-PROD 33/33, B-PROD 45/45, E-PROD 42 49/49, E-PROD 142 43/43.

## 3.3 Opponent windows inside converted chains

| | A-PROD | B-PROD | E-PROD 42 | E-PROD 142 |
|---|---|---|---|---|
| Bottom windows | 234 | 177 | 183 | 171 |
| Bottom initiations (MEDIUM / LOW / UNFUNDED) | 78 (78 / 0 / 0) | 159 (156 / 1 / 2) | 161 (153 / 8 / 0) | 136 (130 / 6 / 0) |
| Bottom resets | **156 (67%)** | 18 (10%) | 22 (12%) | 35 (20%) |
| D3-B holds / free windows | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

Bottom's commitment inside these windows is the surface's declared commitment policy. MEDIUM is the baseline; LOW appears only under RECOVER while Exhausted; UNFUNDED only when stamina is short. Its initiate-or-reset choice varies strongly by surface. This choice is the part a continuation model must decide how to model (section 5).

---

# 4. Churn (C4 / E3) under the attribution

**PROTECT probe:** 1,964 Top builder decisions; 1,768 with a used chain; 0 conversions. setup_future > 0 in **0 / 1,768** under **every** layer and variant, including P6 (the realized use state).

**Non-converted production chains** (reported): the share with setup_future > 0 rises with substitution. For example, B-PROD goes from 89/762 at P0 to 152/762 at P6. These are real Ready uses with positive conversion probability at the realized state, not churn.

**The PROTECT zero is state-dependent, not structural.** Reported sensitivity of the use value at the realized use state, over used chains:

| Use state | A-PROD | B-PROD | E-PROD 42 | E-PROD 142 | PROTECT probe |
|---|---|---|---|---|---|
| realized | 156/312 | 270/880 | 278/844 | 277/841 | **0/1,768** |
| Bottom over-drained (Exhausted at 0) | 312/312 | 282/880 | 288/844 | 289/841 | **582/1,768 (33%)** |
| Top under-drained (decision-time stamina) | 156/312 | 303/880 | 305/844 | 307/841 | 0/1,768 |
| both | 312/312 | 303/880 | 314/844 | 314/841 | 582/1,768 |

On PROTECT, Bottom does reach Exhaustion (stamina 0 in 98 of 100 matches). Ready isolation still has 0 value at every realized use, because Top is drained too and v0.4 semantics (undercommitment) are off on that surface. A continuation that **over-projects Bottom drain** turns 0% into 33% positive.

So C4 holds only if the continuation produces drain from the actual mechanics for both sides. **Average drain constants, learned coefficients or "assume the defender is drained" would reintroduce PROTECT churn.** This is direct evidence for the exclusions in the authorization.

---

# 5. Answer to the key question

> What is the smallest bounded, deterministic, non-oracular continuation model that would have predicted the historically successful setup chains without reintroducing PROTECT churn?

**Genuinely both stamina and axis continuation are needed, through the opponent's window, with window-stepped latches.**

| Requirement (from the evidence) | Why |
|---|---|
| Keep the frozen horizon: r builder windows, r opponent windows, then the use (strict alternation) | Exact in 100% of converted chains (3.1) |
| Builder windows: settle the **responder's** spend (response commitment, plus hold where applicable), not just the builder's own cost | Largest single omitted term on A-PROD; necessary for A-PROD (2.1, "without builder settlement" 50%) |
| Advances: apply **drift** (`rules.drift_rate` of the behaviors) and behavior flow per window | Drift alone takes the Recognition surfaces 56-59% → 78%; P0 ignored drift entirely |
| Opponent windows: settle the opponent's **initiation spend**, the initiator's **response spend**, and the **axis movement** of that exchange | Without them: A-PROD 50%, Recognition surfaces 75% (2.2) |
| **Step latches, band and behaviors window by window** (existing hysteresis; RECOVER behavior as a function of the latch) | Single application with decision-time behaviors loses 10 / 4 E-PROD chains (2.2) |
| Drain only from mechanics, for both sides | Over-projected Bottom drain alone: PROTECT 0% → 33% (4) |
| Builder movement may stay an expectation or become an exact distribution | Expected ≈ actual (3.2); "without builder axis" from P6 = 100% |
| No horizon extension, no Top position-attack modeling, no stalling modeling | 0 occurrences inside converted chains (3.1) |

This is the bounded alternating-window continuation sketched in the authorization, and the evidence now pins down what each window must contain. **The one unresolved choice is how the opponent's window is chosen** (initiate vs reset, which action). Attribution can show that the window matters. It cannot choose the model without scoring candidates against C3, which this slice does not do. The candidates and a recommendation are in `docs/TACTICAL_EVALUATOR_PROJECTION_V2_PREREGISTRATION.md` section 3.

---

# 6. Verification

| Check | Result |
|---|---|
| `tests.test_projection_characterization` | recorder inert; identity with Stage 1A records; identity check detects a changed exchange; components sum exactly; P0 = frozen projection and P6 = realized use state |
| `tests.test_projection_characterization_evidence` | re-measurement equals the committed summary on all 7 runs; Stage 1A evidence sha256 unchanged |
| Full local suite, frozen digest, both checkers | see the final report for this head |

---

# 7. Hard stop

Done: read-only characterization of the frozen Stage 1A populations, plus a proposed revised preregistration (separate document, not binding until reviewed).

**Not done, and not authorized:** projection-v2 implementation used by TE-1; rerunning C1-C4 under a revised evaluator; `TACTICAL_V1` wiring; Stage 1B; any candidate gameplay run; any change to C3, C4, G1-G6 or other thresholds; merge.

**HARD STOP.**
