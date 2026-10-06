# Joint Tactical Evaluator — Projection v2 Revised Preregistration

## Status

**REVIEWED REVISION — DECISIONS RECORDED (section 6) — DOCUMENTATION ONLY.**

Proposed at `afa8259`. The user reviewed it and recorded D1-D5 (section 6). This clarification commit applies the review's corrections:
- the O-3 wording;
- the exact state-merge rule and its no-approximation clause;
- the C5 population;
- the frozen runtime ordering.

Per the review, this document is **binding at the SHA of this clarification commit once that commit passes exact-head CI**. That pass authorizes **Stage 1A-v2 only**. `afa8259` and all Stage 1A failure evidence stay unchanged.

```text
branch:              review/tactical-evaluator-projection-v2
base (Stage 1A FAIL): 2d2778d88205874e30aeda37579dc45d5d9f885e  (immutable)
revises:             docs/TACTICAL_EVALUATOR_PREREGISTRATION.md (frozen at 4e61bad)
evidence basis:      docs/TACTICAL_EVALUATOR_PROJECTION_CHARACTERIZATION.md (this branch)
historical result:   docs/TACTICAL_EVALUATOR_STAGE1A_RESULT.md — C1 PASS, C2 PASS,
                     C3 FAIL, C4 PASS, STAGE 1A FAIL (unchanged, stays historical)
```

**Scope of the revision.** Only the forward-state projection changes: section 2.4 of 4e61bad, plus the matching sentences in 2.1 and A6. Everything else in 4e61bad stays binding as written:
- the mechanics table (section 1);
- the opponent model (2.2);
- the `TacticalValue` tuple (2.3);
- TE-1 tiers, reduce-then-compare, the stamina guard and tie-breaks (2.5);
- precedence (2.6);
- the stages (3);
- P1-P6, C1-C4 and G1-G6, with their surfaces, baselines and floors (4);
- the hard-stop rules (7).

The immediate-exchange and Ready-use layer of `24e8591` is **reused unchanged**. It is calibrated: C1 2,384/2,384 exact; C2 21/21; Ready conversion predicted 59.1 vs 61 actual.

---

# 1. What the characterization established (binding inputs)

From the read-only re-analysis of the frozen Stage 1A populations, with identity verified against the committed records:

1. **Horizon is right.** Every converted chain reached its Ready use exactly 2r windows after the builder decision. No Top non-builder actions, holds, free windows or stalling movement occurred inside a converted chain.
2. **The window contents were wrong.**
   - The projection omitted the defender's response spend on builders, the defender's own initiation spend, the builder's response spend, ordinary drift, and the axis movement of the opponent's exchanges.
   - The bias is one-signed: the defender is projected 14-19 stamina too fresh, and the axis 1.6-1.7 too low.
3. **Genuinely both stamina and axis.**
   - A-PROD needs stamina (stamina only: 79%; axis only: 0%) plus drift.
   - The Recognition surfaces need axis (axis only: 96-97%; stamina only: 52-62%).
4. **The opponent's window matters.** With Top's windows and the advances only, A-PROD reaches 50% and the Recognition surfaces 75%.
5. **Latches must be stepped.** A single hysteresis application loses 10 / 4 E-PROD chains.
6. **Drain must come from mechanics.** Over-projecting the defender's drain turns PROTECT from 0% to 33% positive.

---

# 2. Revised section 2.4 — bounded alternating-window continuation (replaces 4e61bad 2.4)

For a builder candidate (a, c) targeting T at tier t (None = 0, Partial = 1):

1. **Horizon (unchanged).** r = 2 − t builds remain. The continuation advances exactly the windows of strict initiative alternation from the decision state:

   ```text
   W1  initiator builder (a, c)      ← the candidate itself
   A   advance
   W2  opponent window
   A   advance
   W3  initiator builder (a, c)      ← only if r = 2
   A   advance
   W4  opponent window               ← only if r = 2
   A   advance
   U   Ready use of T
   ```

   That is 2r exchange windows, 2r advances, then the use. Free initiative windows, stalling evaluation and position resets are not modeled (0 occurrences inside converted chains). If the clock reaches 0 before U, that branch's use value is 0.

2. **State.** The state is the public snapshot of section 2.1: axis, band, both pools with latch, behaviors, setup tiers / Ready set, submission stage, clock. The continuation carries an **exact finite distribution** over such states (weights are `Fraction`s). No sampling, no RNG, no averaging of states.

   **Merge rule (frozen at review).** Two branches merge, adding their weights, only when **every continuation-relevant field is equal**:
   - axis and band;
   - both stamina values and both latches;
   - both behaviors;
   - setup tiers and the Ready set;
   - submission stage;
   - clock;
   - initiative;
   - every copied controller state that can affect a later window: the D3-B armed / token / latch-history fields, and the behavior-meter remainders.

   Nothing else merges.

   **No approximation.** There is no pruning, probability cutoff, Monte Carlo, float-state averaging, branch cap or any other silent approximation. If branch growth makes Stage 1A-v2 impractical, the result is **STAGE 1A-v2 = OPEN**.

3. **Initiator builder window (W1, W3).**
   - Resolve (a, c) at each branch state with the existing `outcome_distribution`: Recognition enumerated, and the responder from 2.2.
   - Each outcome branch settles exactly as `MountMatch.attempt`: initiator effective cost; responder effective cost from the response commitment of that Recognition case (Rule 1 waiver when the initiator is UNFUNDED); hold where `attempt` charges one; axis_after.
   - Each branch then applies the setup advance of that outcome (`setup_advances_from`).
   - Later builds are projected at the candidate's own commitment c (unchanged from 4e61bad).

4. **Opponent window (W2, W4).** The opponent's choice is resolved by the **opponent initiator model** of section 3: O-3, the declared opponent policy with a depth-1 bounded surrogate for nested setup valuation (D1). The resulting exchange is enumerated and settled exactly as in step 3, with the roles swapped:
   - the opponent pays its initiation;
   - the projecting side pays its response under its surface response model and response-commitment mode;
   - axis movement is applied.

   A reset moves no stamina. A recovery/LOCKOUT hold changes nothing.

5. **Advance (A).** Apply the engine's own `simulate_drift`: `rules.drift_rate` of the branch behaviors, one interval, existing band hysteresis. Apply the behavior stamina flow (`behavior_stamina_policy`, horizon aligned to the quantum as in 4e61bad). Step each pool through the **existing `StaminaPool` hysteresis** at every change, so latches follow the path. Each side's behavior for the next interval comes from that side's surface behavior policy (`AdaptiveBehaviorPolicy`: FIXED, or RECOVER = CONSERVE while Exhausted).

6. **Use value (unchanged rule, new states).** In each branch where T is Ready at U:
   - V = max over c′ ∈ {LOW, MEDIUM, HIGH} fully fundable at that branch's own stamina of P(success of T), computed by the existing exact use valuation;
   - success means Top Threat entry or Bottom escape.

   In a branch where T is not Ready at U (a build failed to advance), V = 0.
7. **`setup_future`** = Σ over branches of P(branch) · V(branch). This replaces the separate chain factor p_adv^r: advancement is now evaluated per branch, at that branch's state.
8. **Runtime ordering (frozen at review; read from code at `2d2778d`).** The continuation applies the steps in exactly the baseline runtime order (`run_escape_first_batch` / `MountMatch`). Tests pin the order window by window against a real match.

   **Exchange window** (`MountMatch.attempt`):
   1. Exhaustion bands are read before the action.
   2. Funding.
   3. Resolution: matchup / Ready / submission, then exhaustion, then the commitment transform.
   4. `_apply_resolution`: axis and band, then initiative passes (or the exit).
   5. Setup advancement or Ready consumption (`_apply_setup_after_attempt`).
   6. Submission state (`_apply_submission_after_attempt`).
   7. Settlement: initiator charge, then responder charge (with the Rule 1 waiver), then the hold charge. Each charge refreshes that pool's latch.

   **Between exchange windows** (non-free window, batch loop):
   1. Pre-advance behavior choice from each side's behavior policy at the current latch (Bottom's passes the handoff controller's pre-advance hook).
   2. `advance()`:
      - drift, second by second: axis clamp and band hysteresis each tick, clock decrement;
      - the stalling-tracker advance;
      - Top behavior stamina flow, then Bottom behavior stamina flow, each refreshing its latch.
   3. Controller `observe_advance` (D3-B arming from the latch transition).
   4. Post-advance behavior re-choice.
   5. At a Bottom window, the controller decision (D3-B token / lockout / hold), then the initiator policy.

   **Disclosed difference from the review's list:** settlement comes **after** setup advancement and submission state, not before. That is the code's order, and it is the order frozen here.

   The continuation reads behavior only at steps 1 and 4 of the between-window sequence, exactly as the runtime does. A latch that changes during a settlement or advance affects behavior only at the next re-choice.

9. **Bounds.**
   - At most 2r ≤ 4 exchange windows and one target.
   - No search over the projecting side's own future actions: later builds are fixed to (a, c).
   - Opponent windows nest at **depth 1** (section 3).
   - The evaluator never draws RNG.

## 2.1′ Knowledge model (revises the last bullet of 4e61bad 2.1 and A6)

Replace "The opponent's future discretionary choices are not projected (see 2.4)" with:

> Inside the bounded continuation, the opponent's initiator choices are given by the declared opponent initiator model (section 3), in the same way the opponent's response choices are given by the declared responder model (2.2). Chance (Recognition rolls, random-blind responses) is enumerated with exact weights. The evaluator never reads RNG state and never draws.

---

# 3. Opponent initiator model (the open architectural choice)

This is the only part of v2 that the characterization could not settle. Attribution shows that the opponent's window must carry its spend and movement. It cannot pick the model without scoring candidates against C3, which was deliberately not done.

| Option | Opponent window | Bounded / non-recursive | Assessment |
|---|---|---|---|
| **O-0 Null** | Opponent always resets | yes | Rejected by evidence: equivalent to "Top's windows + advances only" (A-PROD 50%, Recognition surfaces 75%) |
| **O-1 Declared commitment, no action** | Opponent always initiates at its declared commitment policy (MEDIUM; LOW while Exhausted under RECOVER); stamina only, no movement | yes | Wrong in both directions. It omits opponent movement, which the Recognition surfaces need. It also over-drains on A-PROD, where Bottom resets 67% of its windows, so it risks the PROTECT churn of characterization section 4 |
| **O-2 Average drain / movement constants** | Fixed per-window deltas | yes | **Not allowed:** arbitrary constants (A3/A5), fitted to the failed dataset, and shown to break PROTECT if they over-drain |
| **O-3 — declared opponent policy with depth-1 bounded surrogate for nested setup valuation** (**selected, D1**) | The opponent's action and commitment are chosen by **the opponent's declared initiator policy contract** on that surface, evaluated on the branch state. Every nested setup valuation is replaced by **the frozen single-chain 4e61bad 2.4 projection** as a bounded surrogate (no continuation inside a continuation). Production precedence (2.6, D3-B) applies inside the window as in play | yes: nesting depth is exactly 1, and the surrogate never recurses | Mirrors E1. Uses no constants. Under the baseline (Stage 1A-v2 shadow), the opponent policy is ESCAPE_FIRST, which has no setup projection, so there the model is the exact actual policy. Under TACTICAL_V1 (Stage 1B), the action/commitment contract is TE-1, but its nested setup valuation is **deliberately approximated** by the frozen projection. It is therefore not the exact actual opponent policy. That approximation is declared, and its calibration is reported (E1, E5) |
| O-3′ Actual policy, setup disabled | As O-3, but the nested evaluation drops tier C (opponent builders are never chosen for setup value) | yes | Simpler. In Stage 1B it would misstate an opponent TE-1 that does build (Bottom Trap-and-Roll chains) |

**Implementation requirements for O-3 (Stage 1A-v2):**
- On the baseline shadow, the opponent window must reproduce the real `ESCAPE_FIRST` choice exactly. Stage 1A-v2 checks the surrogate call against every real Bottom decision (`action`, `reason`) of the shadow runs. Any mismatch is an integrity failure (OPEN).
- The opponent policy must be callable on a branch snapshot without touching the live match or any RNG. This is the same purity standard as the C0 / no-RNG instrumentation of Stage 1A.
- D3-B controller state at the decision is copied, never advanced, by the evaluator.
- If the opponent policy cannot be evaluated purely on a snapshot, Stage 1A-v2 stops as **OPEN**. It does not fall back to another option.

---

# 4. Gates

## 4.1 Unchanged (reused exactly)

- **C1, C2, C3, C4** as in 4e61bad 4.2: same surfaces, populations, floors (C3 ≥ 80% on A-PROD, B-PROD and each E-PROD seed in both stalling modes; C4 ≥ 50%) and scoring code paths. **C3's 80% floor is not lowered.**
- **P1-P6** (Stage 1B preservation) and **G1-G6** (Stage 1B design gates), as written.
- FAIL means record and STOP; inadequate evidence means OPEN.

## 4.2 Why C3 alone is no longer enough (disclosed)

Under O-3 on the baseline shadow, the opponent model is the opponent's actual policy, and chance is enumerated exactly. So the realized trajectory of every converted chain is one of the enumerated branches whenever the builder's candidate c equals the baseline's actual commitment. It has positive weight and positive use value, so **C3 passes nearly by construction**.

Two things follow:
- C3 still guards against the S1-style collapse it was designed for.
- It no longer tests whether `setup_future` is **calibrated**, and C4 tests only one surface.

The C3 populations also informed this design, so they are in-sample. Both are strong reasons to add gates. They were accepted at review (section 6, D3 and D4).

## 4.3 Additional gates (accepted at review: D3, D4)

| ID | Gate | Rationale |
|---|---|---|
| **C5 — setup_future calibration (unconditional)** | See the definition below. | Makes v2's continuation falsifiable rather than tautological under O-3. It tests the unconditional probability that setup_future claims to predict (corrected at review: conditioning on reaching Ready would compare different probability spaces). One decision per chain. The same ±3σ rule as C2 adds no new tolerance |
| **C3-H — holdout** | C3, unchanged (≥ 80%), on surfaces not used in the characterization: A-PROD and B-PROD at `base_seed` 4242, and E-PROD at seeds 4242 and 4342, each in both stalling modes. All other kwargs are identical to the frozen surfaces. Baselines are recorded at Stage 1A-v2 before scoring. | The 4e61bad C3 populations shaped this design. A fresh population guards against fitting it |

**C5 definition (frozen at review).**

- **Surfaces:** A-PROD, B-PROD, E-PROD 42 and 142 in both stalling modes, and the PROTECT probe (the frozen Stage 1A surfaces).
- **Population:** the **first builder decision of every setup chain begun** on the surface. A chain is the Stage 1A C3 chain: the run of Top setup decisions closed by the next Top Ready use of its target, or by the end of the match. This includes chains that never reach Ready and chains never used.
- **Predicted p:** setup_future from that decision under section 2, with two scoring settings:
  - the builder at the baseline's actual builder commitment;
  - the Ready use valued at the baseline's use commitment, instead of TE-1's max over c′. That is the baseline policy's fixed Top commitment on the surface. Where a use exists, it is asserted equal to the actual use commitment; a mismatch is an integrity failure.
- **Observed:** 1 if that chain ultimately produces a Threat entry at its corresponding Ready use; 0 otherwise, including chains that never reach Ready or are never used.
- **Test:** (observed − Σp)² ≤ 9 · Σp(1−p) on each surface, exactly as C2.
- **Disclosed property (not a tolerance):**
  - "Observed" counts conversions at any later use of the chain.
  - setup_future counts only uses within the 2r-window horizon.
  - On the frozen populations, every converted chain used exactly 2r windows (characterization 3.1), so the two coincide there.
  - On other populations, a retried build that later converts would count as observed but not predicted. C5 is scored as defined, without adjustment.

C5 is scored on the frozen surfaces only; the holdout surfaces carry C3-H.

**Reported, not gated:**
- the projected-vs-realized use-state fidelity of v2 on the C3 populations (band agreement, defender latch agreement, stamina and axis errors; characterization section 3.2 format);
- the drain sensitivity of characterization section 4;
- branch counts and evaluation cost per decision.

---

# 5. Stages (revised)

| Stage | Content | Ends with |
|---|---|---|
| **1A-v2: projection v2 in shadow** | Implement section 2 with O-3 as a replacement for `project_setup` only; the immediate evaluator is unchanged. Rerun the Stage 1A shadow on the frozen surfaces and run the C3-H holdout surfaces, with the batch policy **unchanged**. Score C1-C5 and C3-H. The Stage 1A observer, integrity checks (0 evaluator RNG draws, RNG-sequence, summary and replay identity, C0) and evidence format are reused. | HARD STOP |
| 1B, 2, 3 | As 4e61bad section 3; each needs its own authorization. | — |

The Stage 1A FAIL record (`2d2778d`) is never rewritten. Stage 1A-v2 is a new result document.

---

# 6. Decisions required at review

| # | Decision | Recommendation |
|---|---|---|
| D1 | Opponent initiator model | **APPROVED: O-3**, worded as a declared opponent policy with a depth-1 bounded surrogate for nested setup valuation (section 3) |
| D2 | Continuation arithmetic | **APPROVED: exact branch distribution with exact state merging** (section 2 step 2: merge only on equality of every continuation-relevant field; impractical growth means OPEN; no pruning, cutoff, Monte Carlo, averaging or silent approximation) |
| D3 | Add **C5** | **APPROVED subject to the population correction**, now applied: unconditional setup_future over every chain start (4.3) |
| D4 | Add **C3-H** | **APPROVED:** A-PROD 4242, B-PROD 4242, E-PROD 4242 and 4342, both stalling modes where applicable. No peeking, seed replacement or additional seeds if one fails. The 80% floor is unchanged |
| D5 | A 2r-window, depth-1 continuation is within A5 | **APPROVED:** fixed target; horizon ≤ 4 exchange windows; the projecting side's future builder actions fixed; only opponent windows evaluate a policy; nesting depth exactly 1; no recursion beyond the frozen single-chain projection; no RNG |
| — | Additional rule (review) | **Runtime ordering frozen** and pinned by window-by-window tests (section 2 step 8) |

**Stage 1A-v2 failure rule (review).** If any of C1-C5 or C3-H fails, the failure is recorded and the slice stops. Projection v2 is not iterated under this preregistration.

---

# 7. Predictions (recorded before any implementation)

- **C1, C2:** unchanged. The immediate-exchange layer is not modified.
- **C3:** PASS on every surface, largely by construction under O-3 (4.2).
- **C4: the real risk.** On PROTECT, Bottom is often Exhausted while Top is drained too. Branches in which Bottom's chance outcomes drain it while Top stays fundable could value Ready > 0. Expect C4 to pass (realized-state use value is 0 in 1,768/1,768 used chains) but with less margin than Stage 1A's 100%.
- **C5:** expected to pass on A-PROD (deterministic). The Recognition surfaces are the test: any opponent-model or settlement mismatch shows up here first.
- **G1** remains the most likely Stage 1B failure (4e61bad section 5), unchanged by this revision.

---

# 8. Not authorized by this document

- `TACTICAL_V1` wiring;
- Stage 1B or any candidate gameplay run;
- any change to C3, C4, G1-G6 or other thresholds;
- G1-G6 candidate scoring; production-policy changes.

Stage 1A-v2 (section 5) is authorized only once this clarification commit passes exact-head CI.
- merge, squash or force-push.

**HARD STOP.**
