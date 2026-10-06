# Joint Tactical Evaluator — Projection v2 Revised Preregistration

## Status

**PROPOSED REVISION — DOCUMENTATION ONLY — NOT BINDING — HARD STOP FOR REVIEW.**

Nothing here is implemented or run. This revision becomes binding only after the user reviews this exact SHA, **resolves the decisions in section 6**, and explicitly authorizes **Stage 1A-v2**.

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

2. **State.** The state is the public snapshot of section 2.1: axis, band, both pools with latch, behaviors, setup tiers / Ready set, submission stage, clock. The continuation carries an **exact finite distribution** over such states (weights are `Fraction`s), merging identical states. No sampling, no RNG, no averaging of states.

3. **Initiator builder window (W1, W3).**
   - Resolve (a, c) at each branch state with the existing `outcome_distribution`: Recognition enumerated, and the responder from 2.2.
   - Each outcome branch settles exactly as `MountMatch.attempt`: initiator effective cost; responder effective cost from the response commitment of that Recognition case (Rule 1 waiver when the initiator is UNFUNDED); hold where `attempt` charges one; axis_after.
   - Each branch then applies the setup advance of that outcome (`setup_advances_from`).
   - Later builds are projected at the candidate's own commitment c (unchanged from 4e61bad).

4. **Opponent window (W2, W4).** The opponent's choice is resolved by the **opponent initiator model** of section 3 (decision D1). The resulting exchange is enumerated and settled exactly as in step 3, with the roles swapped:
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
8. **Bounds.**
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
| **O-3 Actual opponent policy, depth 1** (recommended) | The opponent's action and commitment are chosen by **the initiator policy that surface actually uses for the opponent**, evaluated on the branch state, with every nested setup projection replaced by **the frozen single-chain 4e61bad 2.4 projection** (no continuation inside a continuation). Production precedence (2.6, D3-B) applies inside the window as in play | yes: nesting depth is exactly 1, and the frozen projection never recurses | Mirrors E1 (the responder model equals the responder actually used). Uses no constants. Under the baseline (Stage 1A-v2 shadow), the opponent policy is ESCAPE_FIRST, which has no projection at all. Under TACTICAL_V1 (Stage 1B), it is TE-1 with the frozen 2.4 projection: a declared approximation whose calibration is reported (E1, E5) |
| O-3′ Actual policy, setup disabled | As O-3, but the nested evaluation drops tier C (opponent builders are never chosen for setup value) | yes | Simpler. In Stage 1B it would misstate an opponent TE-1 that does build (Bottom Trap-and-Roll chains) |

**Implementation requirements for O-3 (Stage 1A-v2):**
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

The C3 populations also informed this design, so they are in-sample. Both are strong reasons to add gates. They are proposed below and need an explicit decision (section 6, D3 and D4).

## 4.3 Proposed additional gates (require decision; not binding until accepted)

| ID | Gate | Rationale |
|---|---|---|
| **C5 — setup_future calibration** | On every C3 surface and the PROTECT probe, take the first builder decision of each chain that reached a Ready use. At the baseline's actual builder commitment, and with the use valued at the baseline's actual use commitment (a scoring variant of step 6, not TE-1's max), compare Σ setup_future with the realized Threat-entry count. It must be within **±3 binomial σ** (σ = √Σp(1−p)), the same exact test as C2. | Makes v2's continuation falsifiable rather than tautological under O-3. One decision per chain keeps the outcomes independent. The same ±3σ rule as C2 adds no new tolerance |
| **C3-H — holdout** | C3, unchanged (≥ 80%), on surfaces not used in the characterization: A-PROD and B-PROD at `base_seed` 4242, and E-PROD at seeds 4242 and 4342, each in both stalling modes. All other kwargs are identical to the frozen surfaces. Baselines are recorded at Stage 1A-v2 before scoring. | The 4e61bad C3 populations shaped this design. A fresh population guards against fitting it |

**Reported, not gated:**
- the projected-vs-realized use-state fidelity of v2 on the C3 populations (band agreement, defender latch agreement, stamina and axis errors; characterization section 3.2 format);
- the drain sensitivity of characterization section 4;
- branch counts and evaluation cost per decision.

---

# 5. Stages (revised)

| Stage | Content | Ends with |
|---|---|---|
| **1A-v2: projection v2 in shadow** | Implement section 2 (+ the D1 choice) as a replacement for `project_setup` only. Rerun the Stage 1A shadow on the frozen surfaces (+ C3-H if accepted) with the batch policy **unchanged**. Score C1-C4 (+ C5 / C3-H if accepted). The Stage 1A observer, integrity checks (0 evaluator RNG draws, RNG-sequence, summary and replay identity, C0) and evidence format are reused. | HARD STOP |
| 1B, 2, 3 | As 4e61bad section 3; each needs its own authorization. | — |

The Stage 1A FAIL record (`2d2778d`) is never rewritten. Stage 1A-v2 is a new result document.

---

# 6. Decisions required at review

| # | Decision | Recommendation |
|---|---|---|
| D1 | Opponent initiator model | **O-3** (actual opponent policy, depth 1, nested setup valued by the frozen 4e61bad 2.4 projection) |
| D2 | Continuation arithmetic | **Exact branch distribution with state merging** (section 2 step 2). Cost is measured in 1A-v2. If it is infeasible, 1A-v2 stops OPEN; no silent approximation (mean-field state averaging is not allowed: latch thresholds make averaged states meaningless) |
| D3 | Add **C5** (setup_future calibration) | **Yes** (see 4.2) |
| D4 | Add **C3-H** (holdout) | **Yes** (see 4.2) |
| D5 | Confirm that a 2r-window, depth-1 continuation is within A5 ("never by recursively playing the match") | Within A5. It never plays the match: no search over own actions, fixed horizon ≤ 4 windows, one target, depth 1. Recorded here so the reading is explicit |

---

# 7. Predictions (recorded before any implementation)

- **C1, C2:** unchanged. The immediate-exchange layer is not modified.
- **C3:** PASS on every surface, largely by construction under O-3 (4.2).
- **C4: the real risk.** On PROTECT, Bottom is often Exhausted while Top is drained too. Branches in which Bottom's chance outcomes drain it while Top stays fundable could value Ready > 0. Expect C4 to pass (realized-state use value is 0 in 1,768/1,768 used chains) but with less margin than Stage 1A's 100%.
- **C5:** expected to pass on A-PROD (deterministic). The Recognition surfaces are the test: any opponent-model or settlement mismatch shows up here first.
- **G1** remains the most likely Stage 1B failure (4e61bad section 5), unchanged by this revision.

---

# 8. Not authorized by this document

- Projection-v2 implementation used by TE-1;
- rerunning C1-C4 under a revised evaluator;
- `TACTICAL_V1` wiring;
- Stage 1B or any candidate gameplay run;
- any change to C3, C4, G1-G6 or other thresholds (C5 and C3-H are proposals pending D3 / D4);
- merge, squash or force-push.

**HARD STOP.**
