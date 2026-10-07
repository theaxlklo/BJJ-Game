# Joint Tactical Evaluator — G1 Post-Failure Characterization: Preregistration

## Status

**PREREGISTRATION — READ-ONLY CHARACTERIZATION — NO NEW AGGREGATE RESULT EXISTS YET.**

This document freezes how the Stage 1B G1 failure will be characterized, **before** any new aggregate diagnostic is computed. It is committed first. The characterization code, its evidence and the architecture recommendation come in a later commit on the same branch.

```text
branch:                       review/tactical-evaluator-g1-characterization
base (Stage 1B result):       27ef5e54095b2915f776cb6287dba73bbe28d026  (DESIGN FAIL, G1; CI 37667846293)
Stage 1B preregistration:     ae786af483d109785f172cb10a17170ece2ed241
Stage 1B implementation:      fd19dd0f6220753d4e135e98db2abd1f03963a3b
historical:                   Stage 1A FAIL 2d2778d; Stage 1A-v2 PASS 750ffe8 (unchanged)
```

**What this slice is not:** it is not a Stage 1B re-run, and it produces no second G1 result. It does not modify TE-1, `tactical_evaluator.py`, `tactical_policy.py`, projection v2, the engine, the domain, positions, D3-B or the production policy. It does not implement TE-2, run any changed acting policy in gameplay, tune anything against G1, promote or merge.

**Frozen inputs (sha256 at `27ef5e5`; verified unchanged before and after the characterization):**

```text
docs/evidence/tactical_evaluator_stage1b.json             d5ee3c8c8101c09a14a4a6524317ad6d44ba3deebd111b9c0e35d47def87b750
docs/evidence/tactical_evaluator_stage1b_records.json.gz  9775a2f4b42d8b7b60d9f2b3d860630290e3697429ca0b1057209f22b8649c72
docs/TACTICAL_EVALUATOR_STAGE1B_RESULT.md                 c58ae09e9a2f337f82fb13164167d469e803658da7f96cbc0c24e19d4611107e
docs/evidence/tactical_evaluator_stage1a_v2.json          c0394a27bbf4faa031a8a530d792167ee5f1ffaba777af6168ca5e83176691e3
docs/evidence/tactical_evaluator_stage1a_v2_records.json.gz eba5dd73d2ee91b483caff95b51565d53c6662b1b0f63ec03b87f44edde69bc9
```

**Already known before this document (from committed Stage 1B evidence, disclosed so it cannot be presented as a finding of this slice):**
- On A-PROD and on the PROTECT probe, the Stage 1B candidate chose RESET at every window on both sides, with 0 exchanges.
- In the Stage 1A-v2 shadow, every A-PROD baseline conversion happened against an Exhausted Bottom (78 of 78).

---

# 1. Questions

1. **Q1.** Where do the A-PROD baseline Threat trajectories and the Stage 1B candidate trajectories first diverge, and why did TE-1 not prefer a non-RESET action there?
2. **Q2.** At those states, does a route to Threat exist at all under the frozen mechanics and opponent model? Does it exist within TE-1's own horizon, or only beyond it?
3. **Q3.** Is the collapse caused by the current player's free RESET fallback, by the horizon, by the binary setup tier, by the acting-policy trajectory, by TE-1 against TE-1 opponent feedback, or by a missing route-viability value? Hypotheses H1-H6 are in section 2.
4. **Q4.** Which diagnostic signals separate A-PROD (productive chains exist) from PROTECT (builder churn is worthless)?
5. **Q5.** Which evaluator architecture is the smallest principled change that addresses the demonstrated mechanism and preserves the Stage 1B properties?

---

# 2. Hypotheses (frozen)

| ID | Hypothesis | Primary evidence that would support it | Evidence that would weaken it |
|---|---|---|---|
| H1 | **Free-RESET fallback.** RESET wins whenever no action passes a tier, without its own forward value. | At the reset states, some non-RESET first action has route value Q > RESET's Q (section 5). | RESET's Q ≥ every non-RESET Q at the reset states. |
| H2 | **Horizon effect.** Routes exist, but beyond TE-1's horizon. | Q of the best non-RESET action is 0 at N0 and > 0 at a larger characterization horizon. | Q > 0 already at N0, or 0 at every feasible horizon. |
| H3 | **Binary setup eligibility.** Builders that preserve or advance a viable route get setup_future = 0. | A builder with setup_future = 0 has Q > 0 as a first action, at N0 or beyond. | Every setup_future = 0 builder also has Q = 0 at all feasible horizons. |
| H4 | **Acting-policy feedback.** TE-1 is locally sensible on baseline states, but its own RESETs keep the trajectory away from states where routes exist. | Route value is positive on the baseline route states (S2) but zero on the candidate trajectory states (S3) at the same horizon. | Route value is similar on S2 and S3, or zero on both. |
| H5 | **Opponent-policy feedback.** The TE-1 opponent removes routes that the ESCAPE_FIRST opponent leaves open. | V under the ESCAPE_FIRST opponent > 0 where V under the TE-1 opponent = 0, at the same states and horizon. | V is equal or similarly zero under both opponents. |
| H6 | **Missing route viability.** A route-viability value separates A-PROD from PROTECT better than setup_future. | Viability (V > 0 at some horizon) is positive on A-PROD states and zero on PROTECT states, while setup_future is zero on both. | Viability does not separate the two surfaces, or setup_future already does. |

Categories may overlap; more than one hypothesis may hold.

---

# 3. Surfaces, matching and state sets

**Surfaces:** A-PROD and the PROTECT probe. Their kwargs are the frozen Stage 1A surfaces, identical to those Stage 1B ran. Other surfaces are out of scope for this slice.

**Trajectory reconstruction (no TE-1 evaluation in gameplay):**
- **Baseline.** Run the unchanged ESCAPE_FIRST batch. It must reproduce the frozen section 3 baseline row exactly, and every per-match decision and attempt sequence (side, action or RESET, reason, requested commitment, realized grade, response) must equal the committed Stage 1A-v2 records.
- **Candidate.** Run an inertness replay from the committed Stage 1B records. A recorded-decision policy returns each recorded decision (tier, action, reason, requested commitment) in call order without evaluating anything, and fails on any desynchronization. The reconstructed per-match timelines must equal the committed Stage 1B records, and the summary must equal the committed Stage 1B summary fields.
- Either mismatch makes the whole slice **OPEN**. No other trajectory is substituted.

**Matching:** baseline match i is paired with candidate match i (the same `base_seed + i`).

**First divergence:** the first decision window, counted in order from the start of the match over both sides, at which the two trajectories' decisions differ in side, action (RESET counts as an action) or requested commitment. The window state at that point is identical in both trajectories by construction; this is checked, not assumed. The state is the projection-v2 `Branch` (te.State plus clock plus D3-B fields).

**State sets** (deduplicated by `Branch` equality; multiplicities reported):
- **S1 first-divergence states.** A-PROD: the 78 baseline Threat matches (the primary set), and all 100 matches reported separately. PROTECT: all 100 matches.
- **S2 baseline route states.** A-PROD: in each of the 78 Threat matches, the state at the first Top builder decision of the first chain that converted. PROTECT: in each of the 100 matches, the state at the first Top builder decision of the first chain. A chain is the reason-independent chain of Stage 1B section 5.2.
- **S3 candidate trajectory states.** Every distinct Top decision-window state on the reconstructed candidate trajectories of A-PROD and PROTECT.

**Recorded fields at every S1 state:** match index, seed, clock, initiative, axis, band, both stamina pools (current, band, latch), both behaviors, setup tiers and Ready set, submission stage, D3-B fields (None on both surfaces), the baseline action and commitment, the TE-1 tier, action or RESET and requested commitment (from the committed Stage 1B record), every legal action and every allowed commitment. For every TE-1 candidate (the Stage 1B candidate set: legal actions × allowed commitments, funding duplicates dropped exactly as `v2.candidates`): terminal, progress, setup_future, setup_advance, axis_realized, axis_raw, stamina_cost, enters_exhausted, projection availability and its fields (r, ready_mass, setup_future_requested, terminal mass). For every candidate, the reason it fails to outrank RESET is stated as the first TE-1 tier condition it fails (terminal ≤ 0; progress ≤ 0; setup_future ≤ 0; not (axis_raw > 0 and axis_realized > 0); removed by the stamina guard).

---

# 4. Exact route search (the shared diagnostic instrument)

A read-only diagnostic. It does not change any acting policy and is never used in gameplay. It reuses projection v2's engine-native steps (`Continuation.exchange`, `Continuation.advance`, `Continuation.opponent`, `Sandbox`) and its exact `Fraction` branch merging. No second simulation engine is written.

**Model.** A finite-horizon decision process for Top (the submission route owner):
- **Top windows (OR).** The options are RESET and every candidate (action, commitment) of the Stage 1B candidate set at that state. RESET passes the initiative; this is exact here, because stalling is off on both surfaces and `reset_window` then only swaps the initiator.
- **Chance (AND / expectation).** Every exchange is expanded through the exact enumerated cases of `exchange_cases` (Recognition read, response commitment, response). There is no sampling.
- **Bottom windows.** Bottom acts by a **frozen opponent contract**, deterministic per state:
  - **O-TE1:** the Stage 1B O-3 opponent (TE-1 with the frozen single-chain projection, with precedence);
  - **O-EF:** the frozen ESCAPE_FIRST policy at the batch commitment, with precedence (Stage 1A-v2 O-3).
- **Between windows:** `Continuation.advance` (behavior choice, `advance()`, post-advance re-choice), exactly as projection v2.
- **Success:** the submission stage becomes non-None (Threat entry) or the match taps, checked after every exchange and every advance. **Failure terminals:** exit (escape) and timeout. Exhausting the horizon counts as 0.

**Values (exact `Fraction`):**
- `V_N(s)`: the maximum over Top policies of P(success within N decision windows from s).
- `Q_N(s, a)`: the same value with Top's first option fixed to a.
- `Ready_N(s)`: the maximum over Top policies of P(Top's Americana target is Ready, or success, within N windows).
- **Route exists** means `V_N > 0`. This is exactly bounded backward reachability from the success states, restricted to the forward-reachable bounded state set (an AND-OR search with exact probabilities).

**Horizons (characterization only; not gameplay parameters).** N0(s) is TE-1's own horizon: 2r + 1 windows, with r = 2 − tier(Arm Isolation), or 1 if the target is Ready. The horizons are **N0, N0 + 2, N0 + 4, N0 + 8**. One tactical exchange is one Top window plus one Bottom window, which is 2 windows. The full curve is reported, and no horizon is selected.

**Exactness and infeasibility.** Memoization is keyed on (Branch, windows remaining), with exact merging. There is no Monte Carlo, sampling, pruning, beam, averaging or random cutoff. The budget per (state, opponent, horizon) is **3,000,000 memo entries or 30 minutes of wall time**. If it is exceeded, that cell and every larger horizon for that state and opponent are recorded as **INFEASIBLE (OPEN)** and are not approximated.

**Cost reported per cell:** wall time, memo entries (distinct (state, remaining) nodes), the largest per-depth frontier, and exchange-cache hits and misses.

---

# 5. Analyses

## 5.1 Reset forensics (S1 states where TE-1 chose RESET)

Overlapping categories, each with an exact rule:

| Code | Rule |
|---|---|
| R1 | no candidate has terminal > 0 |
| R2 | no candidate has progress > 0 |
| R3 | some builder candidate has setup_future = 0 but `Q_N > 0` at some feasible horizon under O-TE1 |
| R4 | no candidate qualifies for the position tier |
| R5 | some candidate with terminal or progress > 0 was removed by the stamina guard |
| R6 | the best non-RESET `Q_{N0}` = 0, but the best non-RESET `Q_N > 0` at a larger feasible horizon (O-TE1) |
| R7 | `V_N = 0` under O-TE1 but `> 0` under O-EF at the same horizon |
| R8 | `V_N = 0` at every feasible horizon under both opponents (no credible route found) |
| R9 | none of the above |

New categories may be added only if a state fits none; any addition is disclosed.

**RESET comparison**, per horizon and opponent:
- RESET better: `Q(RESET) > max non-RESET Q`.
- RESET destroys a route: `Q(RESET) = 0 < max non-RESET Q`.
- Equivalent: `Q(RESET) = max non-RESET Q`.
- RESET preserves a route: `Q(RESET) > 0`.

## 5.2 Route reachability and horizon (S1, S2, S3; both surfaces; both opponents)

For each horizon: the number of states analyzed; Threat reachable (`V > 0`); Ready reachable (`Ready > 0`); RESET preserves a route; RESET destroys a route; some non-RESET action preserves a route; and cost.

TE-1's own setup_future at N0 is compared with `Q_{N0}` of the same builder. The difference measures the restriction of TE-1's projection to "repeat this builder at this commitment, then the best use".

## 5.3 Quiescence (S1, S2; both surfaces; O-TE1, plus O-EF reported)

Base horizon N0, safety bound N0 + 8. A search node at depth d (windows used) is expanded if d < N0, or if N0 ≤ d < N0 + 8 and the state is **unresolved**. Quiet nodes beyond N0 are valued 0.

**Unresolved, variant QA** (the prompt's conditions, made computable):
- Top's Americana target has tier > 0 and is not Ready (a chain is in progress; this includes "one builder can complete Ready");
- the target is Ready (one exchange from a target use);
- Top is to move and some legal Top action has immediate terminal > 0 or progress > 0 at a fundable commitment.

An active submission stage is already a success terminal, so it is not a separate condition.

**Variant QB** is QA plus one more condition: Bottom is latched Exhausted. This is added because the base rates in this document's status record every A-PROD conversion against an Exhausted Bottom. It is stated here, before any aggregate is computed.

Both variants are compared with uniform search at N0 + 8 on: agreement of `V > 0`, value differences, nodes expanded, wall time, and A-PROD / PROTECT discrimination. Neither definition is changed after its results are seen.

## 5.4 Opponent-policy ablation

All of 5.2 and 5.3 is computed under both O-TE1 and O-EF on the same states. This is report-only and does not claim any candidate result.

## 5.5 setup_future = 0 decomposition (every Top builder candidate with setup_future = 0 at S1 and S2)

Rules are applied in order; the first match is the primary cause, and all matches are reported:

| Code | Rule |
|---|---|
| Z1 | setup_advance = 0: the builder cannot advance now |
| Z2 | ready_mass = 0: the chain does not reach Ready within the projection |
| Z3a | Ready is reached, every fundable use value is 0, and some unfundable commitment has use value > 0: stamina makes the use unfundable |
| Z3b | Ready is reached and the use value is 0 at every commitment: the informed defender defeats the use |
| Z4 | (any of the above, and) `Q_N(builder) > 0` at a larger feasible horizon under O-TE1: horizon-truncated |
| Z5 | `Q_N(builder) = 0` at every feasible horizon under both opponents: dead within the characterization |

## 5.6 A-PROD vs PROTECT

Every metric of 5.2-5.5 is reported per surface as a distribution: Threat reachable within N, Ready reachable within N, `V > 0`, RESET destroys a route, the cheapest-action route preserved, and the first horizon at which value appears.

**Separation** is reported as: the fraction of A-PROD states with the signal positive, against the fraction of PROTECT states with it positive. A useful signal is positive on A-PROD route states and zero on PROTECT states.

## 5.7 Backward-reachability feasibility

For each surface, the number of distinct forward-reachable (Branch, remaining) nodes per horizon from the analyzed states is reported. This is the cardinality any retrograde or solved-state table would need. No full-state-space solver is built in this slice.

---

# 6. Integrity (any failure = OPEN)

- The frozen inputs above have unchanged hashes before and after the characterization run.
- `git diff 27ef5e5` shows no change outside the new diagnostics module, its tests and the new docs or evidence.
- Both trajectory reconstructions match the committed evidence exactly (section 3).
- The window state is identical in both trajectories at every first-divergence point.
- Zero RNG draws during the route search and the analyses (the Stage 1A `RngTrace`).
- The same input gives the same output: the whole characterization is run twice, and the outputs are compared.
- Unit tests pin the route search on hand-checkable cases: a state with an immediate Ready use, a terminal state, horizon 0, RESET semantics, and agreement with `Continuation` steps.

---

# 7. Deliverables

- `src/bjj_game/diagnostics/tactical_evaluator_g1_characterization.py` (read-only diagnostics);
- `tests/test_tactical_evaluator_g1_characterization.py`;
- `docs/evidence/tactical_evaluator_g1_characterization.json` (summary) and a records file if needed;
- `docs/TACTICAL_EVALUATOR_G1_CHARACTERIZATION.md`, containing:
  - the first-divergence report and the reset cause distribution;
  - the route reachability table and the horizon analysis;
  - the quiescence analysis and the opponent ablation;
  - the setup_future decomposition and the A-PROD / PROTECT separation;
  - the backward-reachability feasibility;
  - an architecture comparison of TE-2A (evaluated RESET), TE-2B (quiescent extension), TE-2C (viability tier), TE-2D (SRQR), backward reachability and any alternative, on G1 relevance, G4 / G5 / G6 risk, complexity, determinism, runtime, memory, testability and explainability;
  - the recommendation in the format: primary mechanism / secondary / not supported / best next architecture / why / why not the alternatives / risks / what must be preregistered next.

Then **HARD STOP** for human review. TE-2 needs its own preregistration and separate authorization.

---

# 8. Hard-stop rules

Not authorized by this document or by the characterization:
- any change to TE-1, `tactical_evaluator.py`, `tactical_policy.py`, projection v2, the engine, the domain, positions, D3-B or the production policy;
- any TE-2 implementation, any changed-policy gameplay run, or any new G1 verdict;
- any threshold or gate change, any tuning against G1, any change to these definitions after aggregate results are seen;
- modification of Stage 1B or any historical evidence;
- promotion, merge, squash or force-push.

**HARD STOP after the characterization and recommendation.**
