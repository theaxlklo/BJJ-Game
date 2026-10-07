# Joint Tactical Evaluator — TE-2 Preregistration (TE-2E exact route-value tier, Top only)

## Status

**PROPOSED PREREGISTRATION — DOCUMENTATION ONLY — HARD STOP FOR REVIEW.**

Nothing is implemented or run. This document freezes the TE-2 candidate, its supported configurations, its integrity checks and its scoring **before any implementation**.

**Authorization language.** Approval of this document at the SHA that carries it makes **the document** binding. It does **not** authorize implementation, wiring or any measurement. TE-2 implementation and the TE-2 candidate measurement each need a separate, explicit authorization.

```text
branch:                       review/tactical-evaluator-te2-preregistration
base:                         3b08cea9f79aeec22b6f9708be53ab62ee1af12b  (G1 characterization, CI 37679571180)
evidence this design rests on: docs/TACTICAL_EVALUATOR_G1_CHARACTERIZATION.md (3b08cea)
binding inputs (unchanged):   4e61bad (TE-1, P1-P6, G1-G6); 5b57017 (projection v2, O-3);
                              ae786af (Stage 1B scoring, G4 amendment, G6 denominator, integrity)
historical results:           Stage 1A FAIL 2d2778d; Stage 1A-v2 PASS 750ffe8;
                              Stage 1B DESIGN FAIL (G1) 27ef5e5 — all unchanged
canonical policy:             PRODUCTION_STAMINA_RECOVERY_POLICY (unchanged)
frozen digest:                3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

**Scope.** One candidate, **TACTICAL_V2**:
- **Top** initiates with **TE-2E**: TE-1 tiers A and B unchanged, then an exact route-value tier, then TE-1's position tier, then RESET.
- **Bottom** initiates with **TE-1 exactly as in Stage 1B**.

It is run once on the frozen Stage 1B surfaces and once on a fresh holdout set, and scored on P1-P6, G1-G6 and the holdout gates HG1-HG6.

---

# 1. Why this design (from the accepted characterization)

- **Primary mechanism: horizon truncation.** From the A-PROD opening, the exact Threat-route value is 0 at 5, 7 and 9 windows, and positive at 13 (1/3 against the O-3 TE-1 opponent). 25 of 30 candidate-trajectory states have a route at 13 windows, and 0 of 30 at 9 or fewer.
- **Secondary mechanisms.** First, the fixed "repeat builder, then use" projection gives setup_future = 0 to builders whose adaptive route value is positive at the same horizon. Second, acting-policy feedback: TE-1's all-RESET trajectory never drains Bottom by exchanges.
- **Discriminator.** Exact Threat-route value separates A-PROD from PROTECT completely. Ready or setup reachability does not, because PROTECT reaches Ready as easily.
- **Selective extension.** The QB definition recovered every uniform route against the O-3 TE-1 opponent at about 30 times lower cost, and created no PROTECT route. QA recovered none.

---

# 2. Evidence classes (frozen)

| Class | Surfaces / seeds | Role |
|---|---|---|
| **Development** | A-PROD seed 42 and the PROTECT probe seed 42, including every state the characterization analyzed | The 5 / 13-window finding was derived here. Regression evidence only; **not** evidence of generalization. |
| **Regression gates** | The Stage 1B gated surfaces: A-PROD, B-PROD, E-PROD 42 and 142 (OFF + shadow, ON), PROTECT probe | Scored on P1-P6 and G1-G6, unchanged. Their Stage 1B candidate outcomes are known, so they are not fresh. |
| **Seen holdouts** | Stage 1B holdouts at 4242 and 4342 | Their Stage 1B outcomes are known. Reported only. |
| **Fresh holdouts (generalization)** | Section 7 seeds 685800 and 23316 | Never run under any tactical policy before the TE-2 measurement. Scored on HG1-HG6. |

---

# 3. Decision rule TE-2E (Top initiator windows only)

Precedence, D3-B and force-RESET rules run first, exactly as in Stage 1B. Under every modeled configuration they never force a Top commitment. If a configuration ever forced one, the route tier's options would be restricted to that commitment, as in Stage 1B section 2.1.

**Candidate set C(s).** C(s) is every legal Top action × commitment, with funding duplicates dropped exactly as `te.candidates` and `v2.candidates`. **Option set O(s)** is C(s) ∪ {RESET}.

1. **Tier A, terminal.** Identical to TE-1 (4e61bad 2.5): the frozen immediate evaluator, the stamina guard and the tie-breaks.
2. **Tier B, progress.** Identical to TE-1.
3. **Tier R, route.** This tier replaces TE-1's tier C (the setup projection) and the RESET fallback for Top.
   - **R1.** Compute `Q(s, o)` for every o ∈ O(s) (section 4).
   - **R2, stamina guard.** This is TE-1's existing guard rule, applied to the metric Q. An option whose commitment `enters_exhausted` is admissible only if its Q strictly exceeds the Q of every non-entering commitment of the same action. RESET never enters Exhausted.
   - **R3.** If the maximum admissible Q is 0, Tier R is empty. Go to Tier D.
   - **R4.** Otherwise choose the admissible option with the highest Q. Ties are broken, in order, by:
     1. lower stamina cost, where RESET costs 0;
     2. higher axis_realized, with RESET counted as 0;
     3. higher axis_raw, with RESET counted as 0;
     4. catalog order, with RESET last;
     5. LOW < MEDIUM < HIGH.

     This is TE-1's ordering with cost moved ahead of the axis, so that at an exactly equal route value the cheapest commitment and waiting are preferred.
4. **Tier D, position.** Identical to TE-1: reduce to the cheapest qualifying commitment, with axis_raw > 0 and axis_realized > 0.
5. **RESET.**

**Commitment.** The chosen option's commitment is the requested commitment. TE-2E chooses LOW, MEDIUM or HIGH only through the rule above. There is no separate commitment heuristic.

**Decision-reason mapping** (used by the batch's existing counters; G4 is reason-independent):

| TE-2E tier | Top reason |
|---|---|
| A terminal, B progress | `submission` |
| R, a designated setup builder | `setup` |
| R, any other action | `position` |
| R, RESET chosen | `reset` |
| D position | `position` |
| RESET | `reset` |

**Bottom initiator windows** use TE-1 with projection v2 exactly as Stage 1B (fd19dd0). This includes LOW_WHILE_EXHAUSTED, D3-B TOKEN and LOCKOUT_HOLD precedence, and the reason mapping.

---

# 4. Route value Q (frozen; the instrument of the characterization, made normative)

**Normative reference.** The algorithm is `RouteSearch`, `Solver` and `unresolved_qb` in `src/bjj_game/diagnostics/tactical_evaluator_g1_characterization.py` at `3b08cea`. The gameplay implementation must equal it exactly on the characterization states, and a test must pin that equality.

- **Top windows (OR).** Max over O(s'), using the same option construction as section 3.
- **Chance (exact).** Every exchange expands through `exchange_cases`: the Recognition read, the response commitment and the response, with exact `Fraction` weights.
- **Bottom windows.** The **O-3 TE-1 contract** of Stage 1B: `Continuation.opponent` under a TACTICAL_V1 context. That means TE-1 tiers whose nested setup valuation is the frozen single-chain projection, with precedence and a copied D3-B controller. The depth is exactly 1, and a Bottom window never starts a route search or a projection-v2 continuation.
- **Between windows.** `Continuation.advance`: behavior choice, `advance()`, D3-B observation, post-advance re-choice.
- **RESET in the search.** It passes the initiative, then advances. This is exact when v0.3b stalling is off. With stalling on, the stalling consequences of a reset are not modeled. This is the same declared omission as projection v2 (5b57017, section 2 step 1), and its incidence is reported (section 9).
- **Success.** The submission stage becomes non-None (Threat entry) or the match taps, checked after every exchange and every advance. **Failure terminals:** exit and timeout.
- **Horizon: QB-quiescent search.** **Base B = 5** decision windows, **bound M = 13** decision windows, both absolute and counted from the decision being made. A node at depth d (windows taken) is:
  - a **success** leaf, valued 1, if the goal holds;
  - valued 0 if d = M;
  - valued 0 if B ≤ d < M and the node is not unresolved;
  - expanded otherwise.
- **Unresolved (QB, frozen exactly).** A node is unresolved if any of these hold:
  - Top's Americana target is Ready;
  - Top's Americana target has setup tier > 0;
  - **Bottom's stamina pool is latched Exhausted;**
  - Top is to move, and some legal Top action at some fully funded commitment (`funded(c) is c`) has immediate terminal > 0 or progress > 0 under the frozen evaluator.
- **Q(s, o)** is the exact value of choosing o first, then optimal Top play within the search.
- **Optimism (declared).** Q assumes adaptive optimal Top play and an opponent that follows the O-3 contract exactly. It is a route value, not a prediction of TE-2E's own play.

**Exactness and caching.** The memo is keyed on (Branch, d), where d is root-relative. Values depend only on the branch and d, so the memo is exact and may be shared across decisions within a match. The Continuation caches are exact as in Stage 1B. No sampling, pruning, beam, averaging, random cutoff or depth reduction is allowed.

**Budget (frozen).** Exceeding any budget makes the run **OPEN**. It never changes a decision and is never approximated.

| Budget | Limit |
|---|---|
| New memo entries per Top decision | ≤ 3,000,000 (deterministic) |
| Memo entries held per match | ≤ 20,000,000 |
| Resident memory per measurement process | ≤ 24 GB |
| Wall time per surface for the authoritative run, on the measurement machine | ≤ 48 h |

The node budget is deterministic. The memory and wall-time limits decide only feasibility (OPEN), never a decision.

**Purity.** The route search draws no RNG and never mutates the live match or the live D3-B controller. It runs on sandboxes only and does no I/O, as in Stage 1B section 2.3.

---

# 5. Supported configurations

These are the same as TACTICAL_V1 (ae786af section 2.1 and section 9.1): v0.2 setup, v0.3a submissions, v0.4a semantics, the informed Bottom responder, handoff NONE or D3-B, and an interval that is a whole number of quanta. There is no fallback, and unsupported configurations raise `ValueError`.

**v0.4a-off exception.** The frozen PROTECT probe envelope is admitted exactly. It is admitted at base_seed 42 and at the fresh PROTECT holdout seed 685800 (section 7), with every other argument equal. This is the already-qualified valuation envelope; the seed changes no configuration. Every other v0.4a-off configuration raises `ValueError`.

---

# 6. Gates

## 6.1 Preservation P1-P6 and design gates G1-G6 (unchanged)

These are exactly as frozen in 4e61bad and scored as in ae786af sections 4-5:
- the same surfaces, baselines and floors;
- the G4 reason-independent amendment;
- the G6 denominator: commitments chosen by the policy, with precedence-forced exchanges excluded and both sides pooled;
- per-stalling-mode pooling.

"TE-1-chosen" in G6 reads "policy-chosen". It counts Top commitments chosen by TE-2E and Bottom commitments chosen by TE-1.

P3 additionally counts 0 TE-2E route searches started from a Bottom window.

## 6.2 Fresh-holdout gates HG1-HG6 (new; required for PASS)

The fresh-holdout surfaces of section 7 are scored with the G-gate principles, against **their own ESCAPE_FIRST baselines**. Those baselines are measured on the head under test **before** the candidate run and recorded. Floors round as in 4e61bad: 80% floors up, the 50% cap down.

| ID | Gate |
|---|---|
| HG1 | A-PROD-H Threat ≥ ⌈0.8 × baseline⌉; and, per stalling mode, B-PROD-H + E-PROD-H1 + E-PROD-H2 pooled Threat ≥ ⌈0.8 × pooled baseline⌉ |
| HG2 | Tap ≤ 20 on every fresh-holdout run |
| HG3 | E-PROD-H1 + E-PROD-H2 pooled escapes ≥ ⌈0.8 × pooled baseline⌉ per stalling mode; B-PROD-H escapes ≥ ⌈0.8 × baseline⌉ |
| HG4 | PROTECT-H reason-independent count ≤ ⌊0.5 × its baseline⌋ |
| HG5 | E-PROD-H Bottom first-Exhausted median ≥ 50 s and Bottom Exhausted share ≤ 80%, each seed and each stalling mode |
| HG6 | E-PROD-H pooled HIGH share among policy-chosen initiations ≤ 50% per stalling mode |

**Why gated.** The regression surfaces and the development states are no longer fresh. A design fitted to the 13-window finding could pass G1 there and fail elsewhere. The holdout gates are the generalization check.

## 6.3 Decision rule

- **DESIGN PASS:** P1-P6, G1-G6 and HG1-HG6 all pass, and every integrity check holds.
- **DESIGN FAIL:** any gate fails with valid evidence. Record it and STOP. No tuning, no re-run, no change to B, M, QB, the tie-breaks or any gate.
- **OPEN:** an integrity failure, a baseline that does not reproduce, a budget exceeded, or missing evidence. OPEN is never relabeled.

---

# 7. Fresh holdout set (mechanically chosen; fixed here)

**Rule.** For k = 0, 1, 2, …, compute:

```text
s_k = 10_000 + int(sha256("3b08cea9f79aeec22b6f9708be53ab62ee1af12b:te2-holdout:k").hexdigest(), 16) mod 880_000
```

Accept s_k if its match-seed range [s_k, s_k + 99] is disjoint from every base-seed range already used in the repository and from the ranges of previously accepted seeds. The used base seeds are 0, 7, 42, 142, 4242, 4342, and the synthetic range from 900000 up. Take the first two accepted seeds.

**Result:** k = 0 gives **H1 = 685800** and k = 1 gives **H2 = 23316**. Both were accepted on the first draw.

**Surfaces** (each with the same kwargs as its Stage 1B gated counterpart, only `base_seed` changed):

| Holdout | Counterpart | Seed |
|---|---|---|
| A-PROD-H | A-PROD | H1 |
| B-PROD-H | B-PROD | H1 |
| E-PROD-H1 OFF + shadow / ON | E-PROD | H1 |
| E-PROD-H2 OFF + shadow / ON | E-PROD | H2 |
| PROTECT-H | PROTECT probe | H1 |

**Discipline.** No tactical policy (TE-1 or TE-2) may be run on these seeds before the authoritative TE-2 measurement. Synthetic tests keep to seeds 910000 and above.

---

# 8. Integrity checks (any failure = OPEN)

These carry over from ae786af section 5, applied to TACTICAL_V2:
- the ESCAPE_FIRST baseline reproduces the frozen table exactly, and the fresh-holdout baselines are recorded before the candidate run;
- G4 equivalence holds on every baseline run;
- evaluator RNG draws are 0, including every route search;
- a second candidate run is identical;
- the **inertness replay** from a tape covering every `policy.choose` call, executed and counterfactual, is identical;
- an **uninstrumented candidate run** is identical to the observed run on every gated surface (now required);
- the Stage 1B window-ordering pins stay green.

Also new for TE-2:
- the **route-search equivalence pin**: the implementation's Q equals the 3b08cea diagnostic instrument on every characterization state, at B = 5 and M = 13, under QB;
- a budget-overflow test showing OPEN, not approximation;
- purity tests.

---

# 9. Reported (not gated)

- Everything Stage 1B reported (ae786af section 6).
- **TE-2E route tier.** Choices by option type (builder, other action, RESET) and by commitment. The distribution of Q at choices. How often Tier R was empty, and how often RESET won Tier R. Route-search nodes, frontier, wall time and memory per decision.
- **O-3 fidelity, both directions.** First, Top's route search models Bottom by the O-3 TE-1 surrogate, while the real Bottom uses TE-1 with projection v2. Second, Bottom's projection models Top by the TE-1 surrogate, while the real Top uses TE-2E. Both are reported by side and tier.
- **Stalling-ON incidence.** Real Top RESETs whose stalling consequence the route search did not model.
- **Calibration.** Σ Q at Tier-R choices against realized Threat entries within the next 13 windows (±3σ, reported).
- **Holdouts.** The seen holdouts (4242, 4342) as ratios to their committed ESCAPE_FIRST baselines.

---

# 10. Predictions (recorded before implementation)

- **G1 is expected to recover substantially on A-PROD,** because routes exist at 13 windows from the opening. Whether it reaches ≥ 63 is uncertain. Q is optimistic, and Bottom (TE-1) also changes its play once Top exchanges.
- **G4 is expected to pass.** PROTECT had no route at any horizon in the characterization.
- **G5 and G6 are the main risks.** Route-seeking Top play drains Bottom through exchanges. The commitment mix it selects was measured only at the opening state, where LOW was best or tied.
- **G3 is a risk on Recognition surfaces.** More Top exchanges give Bottom more terminal windows; the direction is uncertain.
- **Runtime.** Feasible on A-PROD and PROTECT (≤ 0.4 s per decision under QB in the characterization). Recognition surfaces were not characterized and could exceed the budget, which would be OPEN.
- **The HG gates are the real test** of whether the 13-window finding generalizes.

---

# 11. Decisions for review

| # | Decision | Proposed |
|---|---|---|
| T1 | Top TE-2E; Bottom frozen TE-1 | as the review required |
| T2 | B = 5, M = 13, absolute windows; QB exactly as in section 4 | as the review required |
| T3 | Tier R tie-breaks: Q, then cost (RESET = 0), then axis_realized, axis_raw, catalog order, commitment rank | proposed here |
| T4 | Stamina guard applied to Q in Tier R (the TE-1 rule with the Tier-R metric) | proposed here |
| T5 | RESET's stalling consequence not modeled in the route search under stalling ON (the projection-v2 omission), with incidence reported | proposed here |
| T6 | HG1-HG6 gated and required for PASS | proposed here; it could instead be report-only |
| T7 | The PROTECT envelope also admitted at the fresh seed H1 | proposed here |
| T8 | Budgets: 3M nodes per decision; 20M per match; 24 GB; 48 h per surface | proposed here |
| T9 | Uninstrumented-run identity becomes a required integrity check | proposed here |

---

# 12. Not authorized by this document

- any implementation or wiring, and any TE-2 or TE-1 run;
- any run of any tactical policy on the fresh holdout seeds;
- any change to TE-1, projection v2, the engine, the domain, positions, D3-B, the production policy, the defaults or the frozen digest;
- any change to P1-P6, G1-G6, thresholds, the G4 amendment or the G6 denominator;
- modification of any historical evidence;
- promotion, merge, squash or force-push.

**HARD STOP.**
