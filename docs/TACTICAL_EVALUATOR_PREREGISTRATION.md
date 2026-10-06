# Joint Tactical Evaluator (Debts 4 + 5) — Preregistration / DoD

## Status

**PROPOSED PREREGISTRATION — DOCUMENTATION ONLY — FROZEN AT ITS COMMITTING SHA — HARD STOP FOR REVIEW.**

Nothing is implemented or run. This document becomes binding only after the user reviews this exact SHA and explicitly authorizes **Stage 1A**. Each later stage needs its own authorization.

```text
branch:              review/tactical-evaluator-preregistration
base (main):         e273bae235f9e68275d3a5874dd510229bd56c9a
inputs (frozen):     docs/SETUP_POLICY_RESULT.md — E1-E6, A1-A6 (SP-JOINT, 9908235)
                     docs/LATE_RECOVERY_RESULT.md — debt-3 re-evaluation contract (683e830)
canonical policy:    PRODUCTION_STAMINA_RECOVERY_POLICY (unchanged)
frozen digest:       3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

**Scope.** One deterministic, bounded evaluator, `TacticalValue`, used by the batch **initiator** for both:
- the **action** choice, including setup builders (debt 4);
- the **initiator commitment** choice, LOW / MEDIUM / HIGH (debt 5).

**Out of scope:** responder response-id policy; response-commitment modes; Recognition rules; settlement (Rule 1 ON, Rule 2 OFF, best-effort additive hold); stamina costs and rates; thresholds; D3-B; scoring; frontend.

---

# 1. Mechanics the evaluator must model exactly (read from code)

| Mechanic | Source | Semantics |
|---|---|---|
| Base resolution | `MountMatch._resolve_attempt_resolution` | Matchup grade, then the exhaustion modifier (initiator Exhausted −1, responder Exhausted +1), then the v0.4a commitment transform. |
| Initiator commitment magnitude | `_initiator_commitment_modifier` | HIGH: Success→Strong Success, Failure→Strong Failure. LOW: Strong Success→Success, Strong Failure→Failure. MEDIUM: none. UNFUNDED behaves as LOW. |
| Responder undercommitment | `_response_undercommitment_modifier` | +1 grade to the initiator if the responder's effective rank < the initiator's effective rank. |
| Funding | `StaminaCostPolicy.effective_commitment` | Highest requested-or-lower level fully payable. Costs LOW 3, MEDIUM 7, HIGH 12. |
| Settlement | `MountMatch.attempt` | Resolution first, then stamina. Rule 1 waives the responder's charge when the initiator is UNFUNDED. Hold LOW = 3 is additive and best-effort. |
| Recognition | `CommitmentRecognitionPolicy.read` | Independent d6 rolls for intent and capability: roll 1 = one level down, roll 6 = one level up, 2-5 exact. Exactly enumerable as 3 × 3 weighted cases (1/6, 4/6, 1/6 each). |
| Response commitment | `_response_commitment_for_exchange` | Surface mode (MATCH / RECOGNITION / ...), a function of the initiator's request or the Recognition read. |
| Response id | Bottom: `_informed_bottom_response_id` (minimum predicted grade under the perceived effective commitment). Top: `RandomBlindResponder` weighted policy. | |
| Setup | `MountSetupPolicy` | A builder advances unless the Mount cap fully absorbs it. Two advances reach Ready. Use consumes Ready. |

**Characterized defect being fixed.** The current helpers (`exact_escape_probability`, `expected_*_axis_delta`, `_submission_entry_probability`) apply the exhaustion modifier but **not** the commitment transform. They also use random-blind weights even where Bottom defends informed. `9908235` showed that both errors matter: random-blind valuation causes about 4x overestimation, and a current-state, commitment-blind informed gate (S1) collapses access.

---

# 2. Evaluator contract (A1-A6 made concrete)

## 2.1 Knowledge model (A6)

**Public state**, known to the initiator:
- axis and band;
- both stamina values and latch bands;
- both behaviors;
- setup tiers;
- submission stage;
- clock;
- the initiator's own requested and effective commitment.

**Not known:** future RNG draws.
- Recognition rolls and Top's random-blind response are **enumerated with their exact probabilities**. The evaluator never reads RNG state and never draws.
- The opponent's future discretionary choices are not projected (see 2.4).

## 2.2 Opponent model (E1)

`OpponentModel` is declared per surface and side. It equals the responder that surface actually uses:

| Initiator | Responder model used for valuation |
|---|---|
| Top | **Informed Bottom.** For each of the 9 Recognition cases (or 1 without Recognition): response commitment from the surface mode; response id = minimum predicted grade under the *perceived* effective commitment; actual grade from true commitments. |
| Bottom | **Random-blind Top** weights (unchanged), each response with the response commitment from the surface mode (Recognition enumerated where enabled). |

Every probability is an exact finite weighted sum.

## 2.3 `TacticalValue` (A2, A3)

Each candidate `(action, requested commitment)` gets a frozen tuple, computed exactly under 2.2 with the full v0.4a commitment transform:

```text
TacticalValue(
  terminal      = P(initiator terminal success now)   # Bottom: escape; Top: Tap
  progress      = P(submission progress now)          # Top: stage advance or Ready-isolation Threat entry; Bottom: 0
  setup_future  = projected setup value (2.4)         # builders only; else 0
  axis_realized = E[realized axis delta], initiator-signed
  axis_raw      = E[raw axis delta], initiator-signed
  stamina_cost  = effective commitment cost
  enters_exhausted = own post-spend stamina <= enter threshold while currently not Exhausted
)
```

There are no weighted sums or coefficients. Candidates whose requested commitment funds to the same effective level as a lower request are dropped, keeping the lowest request.

## 2.4 Bounded setup projection (A5, E2)

For a builder candidate targeting T at tier t (None = 0, Partial = 1):

1. **Builds remaining** r = 2 − t. **Horizon** = r builder windows plus 1 use window. **Elapsed to use** Δ = 2 · r · `interval_seconds` (strict initiative alternation assumed; free windows ignored).
2. **Own stamina at use** = current − r · cost(c) + behavior rate(own current behavior) · Δ. Builds are projected at the candidate's own commitment c.
3. **Opponent stamina at use** = current + behavior rate(opponent current behavior) · Δ. The opponent's discretionary spends (its initiations and responses) are **not projected**: a declared lower bound on opponent drain.
4. **Bands at use** come from the existing hysteresis latch applied to each projected value from its current latched state. Values are clamped to [0, 100].
5. **Axis at use** = current + r · E[realized axis of this builder at c], clamped to the Mount range. The band is derived from it.
6. **Use value** V = max over c' ∈ {LOW, MEDIUM, HIGH} fundable at the projected own stamina of P(success of T at the projected state) under 2.2, where success means Top Threat entry or Bottom escape.
7. **Chain probability** P = p_adv(builder, c)^r, with p_adv exact at the current state.
8. **`setup_future`** = P · V.

The projection never simulates opponent decisions, never recurses beyond the single setup chain, and never consumes RNG.

## 2.5 Decision rule TE-1 (tiers kept; values corrected; commitment added)

Applied at every initiator window where 2.6 leaves a choice:

| Tier | Admits | Selects | Commitment within the tier |
|---|---|---|---|
| A — terminal | candidates with terminal > 0 | max terminal | **highest-value**: max terminal (stamina guard applies) |
| B — progress | progress > 0 | max progress | highest-value: max progress (stamina guard applies) |
| C — setup | builders with setup_future > 0 | max setup_future | **cheapest** c with setup_future > 0 |
| D — position | axis_raw > 0 and axis_realized > 0 | max axis_realized | **cheapest** c keeping both > 0 |
| E — RESET | otherwise | RESET | — |

- **Stamina guard** (tiers A and B): a commitment with `enters_exhausted` is admissible only if its tier metric is **strictly greater** than every admissible non-entering commitment of the same action. No tolerance.
- **Tie-breaks, in order:** tier metric; then axis_realized; then axis_raw; then lower stamina_cost; then catalog order; then LOW < MEDIUM < HIGH. Every comparison is exact on floats produced by identical code paths; no epsilon.
- **Principle** (no coefficients): pay more only for terminal or submission outcomes. Spend the minimum that keeps a setup or positional action worthwhile.

TE-1 deliberately **keeps today's tier order** (setup above position). `9908235` showed that order displaces only 6-28% / 0-5% better positional attacks. Changing it is a separate, later question. TE-1 isolates the two characterized defects (opponent model and use-time valuation) plus the commitment dimension.

## 2.6 Precedence (production constraints win)

- `PRODUCTION_STAMINA_RECOVERY_POLICY` is unchanged.
- In Bottom RECOVER windows while Exhausted, the commitment stays **LOW** (LOW_WHILE_EXHAUSTED). D3-B token and lockout decisions are taken first and unchanged; a LOCKOUT_HOLD replaces the window as today. TE-1 picks only the **action** in an Exhausted window, at LOW.
- Response commitment, response id, Recognition, settlement and D3-B are untouched.
- TE-1 is **opt-in**: a new batch option, `initiator_policy=TACTICAL_V1`. The default stays `ESCAPE_FIRST`, so raw defaults and the frozen digest are unchanged.

---

# 3. Stages

| Stage | Content | Ends with |
|---|---|---|
| **1A — evaluator in shadow** | Pure `TacticalValue` module + observer. The batch policy is **unchanged**. Evaluate TE-1's values and choices on baseline states, and gate calibration (section 4.2). | HARD STOP |
| **1B — candidate run** | Wire TE-1 behind `initiator_policy=TACTICAL_V1`. Run once on the frozen surfaces. Score sections 4.1 and 4.3. | HARD STOP; DESIGN PASS / FAIL / OPEN |
| 2 — promotion | Separate preregistration (canonical policy entry point). | — |
| 3 — debt-3 re-evaluation | Re-run `bjj_game.diagnostics.late_recovery` under the promoted policy. | — |

FAIL means record it and STOP, with no tuning and no gate change. Missing or inadequate evidence means OPEN.

---

# 4. Gates (frozen)

**Surfaces** (100 matches each):
- A-PROD, B-PROD;
- E-PROD seeds 42 and 142, each with stalling OFF + shadow and ON;
- the v0.3a PROTECT probe.

Baselines are the committed characterization evidence:

| Surface | Threat matches | Tap | Escapes | Timeouts | Top completed builds |
|---|---|---|---|---|---|
| A-PROD | 78 | 0 | 22 | 78 | 312 |
| B-PROD | 59 | 9 | 12 | 79 | 880 |
| E-PROD 42 / 142 | 61 / 57 | 5 / 4 | 30 / 31 | 65 / 65 | 844 / 841 |
| PROTECT probe | 0 | 0 | 2 | 98 | 1,768 |

## 4.1 Preservation (mandatory, Stage 1B)

| ID | Gate |
|---|---|
| P1 | Raw `MountMatch` / batch defaults and `PRODUCTION_STAMINA_RECOVERY_POLICY` unchanged; frozen digest exact; with `ESCAPE_FIRST`, every existing pinned surface reproduces exactly (full suite green). |
| P2 | Rule 1 exact, Rule 2 OFF, best-effort additive hold, costs, rates and thresholds unchanged. |
| P3 | Precedence (2.6): 0 Bottom RECOVER Exhausted initiations at a commitment other than LOW. Every D3-B token and lockout decision is produced by the unchanged D3-B controller. TE-1 never overrides a token or a LOCKOUT_HOLD, and no TE-1 action executes in a LOCKOUT_HOLD window. |
| P4 | **No RNG consumed by the evaluator** (instrumented: 0 draws from any batch RNG during evaluation). Deterministic replay: full gameplay identity across two runs. |
| P5 | Stamina guard: 0 tier-A/B choices with `enters_exhausted` that are not strictly better. Tiers C/D: 0 choices above the cheapest qualifying commitment. |
| P6 | Exact-head CI on Python 3.11 and 3.13, including full-history PG8. All historical evidence preserved. |

## 4.2 Stage-1A calibration gates (mandatory before 1B)

| ID | Gate |
|---|---|
| C1 | **Deterministic exactness.** Where 2.2 is deterministic (Top initiator, no Recognition: A-PROD), TE-1's predicted grade at the baseline's actual commitment equals the realized grade in **100%** of Top exchanges. |
| C2 | **Stochastic calibration.** On every surface and for each of terminal / progress / setup-advance, sum of predicted probabilities versus realized count over the baseline's actual (action, commitment) exchanges: within **±3 binomial standard deviations** (σ = √Σp(1−p)). |
| C3 | **No S1-style collapse.** Population: baseline Top builder decisions whose chain ended in a Threat entry at the next Ready use (pooled per surface). TE-1 `setup_future` > 0 for **≥ 80%** of them on A-PROD, B-PROD and each E-PROD seed. S1 scored 0% here. |
| C4 | **Churn recognition (E3).** On the PROTECT probe, TE-1 `setup_future` = 0 for **≥ 50%** of baseline Top builder decisions. Baseline realized conversion is 0. |

C1-C4 run against the **unchanged** baseline policy. A failure stops the slice before any candidate run.

## 4.3 Design gates (mandatory, Stage 1B)

| ID | Gate | Rationale |
|---|---|---|
| G1 | **Submission access:** A-PROD Threat matches **≥ 63** (80% of 78 = 62.4, rounded up); B-PROD + E-PROD pooled (B, 42, 142) **≥ 142** (80% of 177). | A-PROD 78 is the prominent control. Rule 2 and S1 both went to about 0; an 80% floor catches collapse with a wide margin and still allows movement. |
| G2 | **Submission not dominant:** Tap ≤ 20 on every surface. | Keeps submission a threat rather than the default ending. |
| G3 | **Escapes:** E-PROD pooled (42 + 142) **≥ 49** (80% of 61); B-PROD **≥ 10**. | Same 80% preservation principle on the defender's terminal route. |
| G4 | **Churn:** PROTECT Top completed builds **≤ 884** (50% of 1,768). | E3 design property as a ratio, not an attempt count k. |
| G5 | **Pacing no-regression:** E-PROD Bottom first-Exhausted median **≥ 50 s**; Bottom Exhausted share **≤ 80%** (each seed, stalling OFF + shadow and ON). | Debt 3 must not get worse. Improvement is reported, not required. |
| G6 | **Commitment sanity:** E-PROD pooled share of HIGH among TE-1-chosen initiations **≤ 50%**. | Guards against a HIGH-spam burn. |

Each E-PROD gate must pass in **both** stalling modes. Percentage floors round up to the next integer.

## 4.4 Reported (not gated)

- Commitment distribution by side, tier and surface.
- Tier distribution versus baseline.
- Setup decisions and builds per Threat entry.
- Forgone-better-position counts.
- Ready conversion predicted versus actual (`9908235` section 2.4 format).
- Full outcome tables, timeouts, stamina finals.
- All late-recovery measures (`LATE_RECOVERY_CHARACTERIZATION.md` section 1).
- Calibration tables per component.

---

# 5. Predictions (recorded before any implementation)

- **Commitment shifts heavily to LOW.** Tiers C and D (setup and position: most decisions on every surface) take the cheapest qualifying commitment. HIGH appears mainly in tier A (Bottom escape, where Success→Strong Success can cross) and tier B (Top submission, where Bottom cannot fund a matching HIGH response, so undercommitment gives +1).
- **Pacing improves sharply.** Bottom's own opening initiation spend (about 42% of its burn) falls from 7 to about 3 per window. Under MATCH, Top's responses follow. Expect a later first exhaustion and a lower Exhausted share (G5 is expected to pass with margin).
- **Submission access is the main risk.** Conversions on production depend largely on Bottom being drained or unable to fund a matching response. Less burn means fewer such states. Tier-B HIGH isolation partly offsets this. **G1 is the gate most likely to fail.** Its outcome cannot be derived from the existing evidence. C3 in Stage 1A is designed to reveal a projection that undervalues production chains before any candidate run.
- **PROTECT churn falls.** The informed model gives 0 use value against PROTECT in most states (calibration exact there today), so C4 and G4 are expected to pass.
- **Projection bias.** Ignoring opponent discretionary spends under-predicts opponent drain, so `setup_future` is conservative. If C3 fails for that reason, the remedy is a new preregistration revision, never a tolerance change.

---

# 6. Planned implementation surface (for review; not implemented)

- `src/bjj_game/interfaces/tactical_evaluator.py` (new):
  - `TacticalValue` (frozen dataclass);
  - `OpponentModel` (informed / random-blind, with exact Recognition enumeration);
  - `evaluate(match, action_id, commitment)` (pure);
  - `project_setup(...)` (pure);
  - `TacticalV1Policy.choose(match) -> (BatchDecision, Commitment)`.
- `interfaces/batch.py`: `initiator_policy` option (default `ESCAPE_FIRST`), wired after the existing recovery/D3-B precedence.
- `diagnostics/tactical_evaluator.py`: Stage-1A shadow observer and C1-C4 scoring; Stage-1B scoring of P1-P6 and G1-G6.
- Tests: purity/no-RNG, exact enumeration (hand-computed cases for each commitment transform and the Recognition branches), precedence, determinism, pinned evidence.
- No external dependency (E6). No change to engine, domain, settlement or production policy modules.

---

# 7. Hard-stop rules

Done in this slice: this document only.

**Not authorized:** any implementation (Stage 1A or later), any candidate run, any change to gates after authorization, any change to gameplay, policy, settlement, costs, D3-B or defaults; merge; squash; force-push.

**HARD STOP.**
