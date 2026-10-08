# Joint Tactical Evaluator — TE-2 Preregistration (TE-2E exact route-value tier, Top only)

## Status

**BINDING AT `218f1c0` — PROPOSED PRE-MEASUREMENT AMENDMENT A1 PENDING REVIEW (section 4.3) — HARD STOP FOR REVIEW.**

**Binding text: `218f1c0`.** Sections 1-12 as approved at `218f1c0` are binding.

**Proposed pre-measurement amendment A1 (this commit, section 4.3): exact cross-match transposition cache.** It is not binding until reviewed. It changes no value, decision, gate, seed, horizon, QB definition or limit. It was proposed after the qualified harness preflight (`eae5780`, synthetic only) projected that E-PROD stalling-ON surfaces would exceed the frozen 48 h limit. No G or HG outcome has been seen.

**Earlier review amendment (`218f1c0`, a direct child of `6df192f`).** The review accepted the architecture in principle. It approved T1, T2, T4, T6, T7 (with pins) and T9, and required amendments to T3, T5 and T8. This commit applies exactly those rulings, plus the consistency edits they need:
- **T3:** RESET wins Tier R only with strictly greater Q (section 3);
- **T5:** exact stalling-aware RESET and window steps on a full route branch (section 4.1);
- **T8:** one TACTICAL_V2 surface process at a time and a 16 GB RSS cap (section 4.2).

The rulings are recorded in section 11. No gate, threshold, seed, horizon or QB definition changed.

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
   - **R3.** If the maximum admissible Q over O(s), RESET included, is 0, Tier R is empty. Go to Tier D.
   - **R4, RESET against actions (amended, T3).** Let `Q*` be the highest Q among admissible **non-RESET** options.
     - If `Q(RESET) > Q*`, Top chooses **RESET**. RESET wins only with a **strictly** greater route value.
     - Otherwise, including the tie `Q(RESET) = Q* > 0`, Top chooses a **non-RESET** option with `Q = Q*`.

     This prevents receding-horizon procrastination. Without it, the search could prefer "wait now, attack later" at every window, because a tied RESET would keep moving the planned attack into the future horizon.
   - **R5, ties among non-RESET options with `Q = Q*`.** TE-1's existing ordering, in this order:
     1. higher axis_realized;
     2. higher axis_raw;
     3. lower stamina cost;
     4. catalog order;
     5. LOW < MEDIUM < HIGH.
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

**Normative reference.** The algorithm is `RouteSearch`, `Solver` and `unresolved_qb` in `src/bjj_game/diagnostics/tactical_evaluator_g1_characterization.py` at `3b08cea`.
- **With v0.3b stalling off**, the gameplay implementation must equal it exactly on every characterization state, and a test must pin that equality.
- **With stalling on**, the transitions are the exact stalling-aware steps of section 4.1. That instrument models a RESET as an initiative swap, which is exact only with stalling off, so it is not the reference there. The option set, the opponent's decision contract, QB, success, the horizon and the tie rules are unchanged.

- **Top windows (OR).** Max over O(s'), using the same option construction as section 3.
- **Chance (exact).** Every exchange expands through `exchange_cases`: the Recognition read, the response commitment and the response, with exact `Fraction` weights.
- **Bottom windows.** The **decision** is the **O-3 TE-1 contract** of Stage 1B (`Continuation.opponent_decision` under a TACTICAL_V1 context). That means TE-1 tiers whose nested setup valuation is the frozen single-chain projection, with precedence and a copied D3-B controller. The **transition** that follows the decision (exchange, RESET or hold) is taken by the section 4.1 steps. The depth is exactly 1, and a Bottom window never starts a route search or a projection-v2 continuation.
- **Between windows.** The batch's own window loop (section 4.1): a pending free-initiative window first; otherwise behavior choice, `advance()`, D3-B observation and post-advance re-choice. With stalling off, this is exactly `Continuation.advance`.
- **RESET in the search (amended, T5).** Every RESET, both Top's RESET option and an opponent RESET, executes the engine's own `reset_window()` on a sandbox loaded with the full route branch. That includes, under stalling, its stalling evaluation, warnings, penalties, axis changes, position resets and free-initiative grants. The window loop then follows. With stalling off, this reduces exactly to an initiative swap.
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

## 4.1 Exact stalling-aware route steps (amended, T5)

**Route branch.** TE-2 uses its own route branch: the projection-v2 `Branch` plus every piece of match state that `reset_window`, `attempt`, `advance`, `recovery_hold` or `consume_free_initiative_window` reads or writes under v0.3b stalling. That includes:
- both sides' stalling-tracker state, such as advancement clocks and the offense and consequence-ladder position;
- the free-initiative pending flag and beneficiary;
- any other mutable field those methods touch.

The implementation must enumerate these fields from the engine code. With stalling off they are constant, and the route branch reduces to `Branch`. **Projection v2, its `Branch` and its pins are not modified.** These are TE-2's own steps in its own module.

**Steps.** Every step runs the engine's own method on a fresh sandbox loaded with the full route branch, and reads the full route branch back:
- `attempt()` for each exact chance case;
- `reset_window()` for every RESET;
- `recovery_hold()` for D3-B LOCKOUT_HOLD;
- the window loop of `run_batch` at `fd19dd0`. `consume_free_initiative_window()` is called first. If it returns a side, that window has no behavior choice and no advance. Otherwise: behavior choice, `advance()`, D3-B observation, re-choice.

Caches are keyed on the full route branch, never on `te.State` alone, because under stalling an attempt can change stalling state.

**Determinism.** Every stalling path must draw no RNG given the route branch. A test pins zero draws. If any stalling path drew RNG, that configuration is unsupported, and a gated stalling-ON run would be **OPEN**, never approximated.

**Required exactness tests (before any measurement):**
- **Field coverage and successor equality.** These run on synthetic stalling-ON matches (seeds 910000 and above). At every real window, load the real pre-window route branch into a fresh sandbox and apply the real decision. A deterministic step must reproduce the real post-window route branch exactly. A chance step must contain the real successor in its exact support.
- **Coverage of reset consequences.** At least one test each for a reset producing a warning, a penalty, a position reset and a free-initiative window.
- **Stalling-off equivalence.** Q equals the `3b08cea` instrument on every characterization state.

**Scope of the old omission.** Bottom's frozen TE-1 still values setup through projection v2, and that projection keeps its historical stalling omission (5b57017, section 2 step 1). This is unchanged frozen TE-1 behavior. **TE-2E's Q has no stalling omission.**

**Exactness and caching.** The memo is keyed on (route branch, d), where d is root-relative. Values depend only on the route branch and d, so the memo is exact and may be shared across decisions within a match. Section 4.3 proposes sharing it across matches within one evaluated surface run (amendment A1, not yet binding). No sampling, pruning, beam, averaging, random cutoff or depth reduction is allowed.

## 4.2 Budget, machine safety and purity (amended, T8)

**Budget (frozen).** Whichever limit trips first makes the run **OPEN**. A limit never changes a decision and never leads to an approximation.

| Budget | Limit |
|---|---|
| New memo entries per Top decision | ≤ 3,000,000 (deterministic) |
| Memo entries held per match | ≤ 20,000,000 (deterministic) |
| Resident memory (RSS) of the route-search process | **≤ 16 GB** (on the 32 GB measurement machine) |
| Wall time per surface for the authoritative run, on the measurement machine | ≤ 48 h |

**Concurrency (frozen).** The authoritative measurement runs **one TACTICAL_V2 surface process at a time**. This covers the candidate run, the second run, the inertness replay and the uninstrumented run of every gated and fresh-holdout surface. ESCAPE_FIRST baseline runs perform no route search and may run separately.

The node limits are deterministic. The memory and wall-time limits decide only feasibility (OPEN), never a decision. The RSS cap is enforced by the measurement driver's own monitor, which stops the run and records OPEN.

**Purity.** The route search draws no RNG and never mutates the live match or the live D3-B controller. It runs on sandboxes only and does no I/O, as in Stage 1B section 2.3.

## 4.3 Pre-measurement amendment A1: exact cross-match transposition cache (PROPOSED)

**Status.** Proposed, documentation only, not yet binding. It is an engineering amendment made **before any authoritative measurement and before any G or HG outcome was seen**.

**Why.** The qualified measurement-harness preflight (`eae5780`, CI 37740238263, synthetic seeds only) measured about **88 s per Top decision** on the synthetic E-PROD stalling-ON role. Applying the Stage 1B count of about 820 Top decisions per surface and three evaluated passes per surface gives about 60 h per surface. That is past the frozen **48 h** limit, so those surfaces would be OPEN. The break-even mean is 48 h / (820 × 3), about 70 s per decision.

This amendment changes **only where an already-exact value may be looked up**. Q, every decision and every gate are unchanged by construction, and section A1.5 requires a proof of that before measurement.

### A1.1 What may be shared

- **Only the solved-value transposition memo**, the memo of `value(route branch, depth)` of section 4, may persist **across matches within one evaluated run of one surface**.
- The step caches stay **per match** exactly as now: exchange, reset, window loop, opponent decision, options and QB. This amendment does not broaden them.

### A1.2 Key

The shared memo is keyed on:

```text
(static fingerprint, full route branch, root-relative depth)
```

- **Static fingerprint.** This binds every immutable input that can affect Q:
  - every `init=True` field of the live `MountMatch` configuration, compared by value;
  - every field of the O-3 projection-v2 `Context`: opponent model, commitment, behavior policies, behavior and recovery modes, D3-B flag and initiator contract;
  - B, M and the QB definition (by the preregistration SHA);
  - the route budget class.
- **Full route branch.** This is the projection-v2 `Branch` plus every v0.3b stalling field (section 4.1).
- **Never `te.State` alone.**

### A1.3 Lifetime

- **One shared memo per evaluated run of one surface:**
  - the candidate run's memo starts empty;
  - the second deterministic run's memo starts **empty**;
  - the uninstrumented run's memo starts **empty**;
  - the inertness replay evaluates nothing.
- **Never shared** between those runs, between surfaces, between processes, or through disk. It is never persisted.
- Each run records a memo generation identifier. The integrity checks verify that no two runs share one.

### A1.4 Budgets under sharing

Every frozen limit stays: B, M, the 16 GB RSS cap, 48 h per surface, and one TACTICAL_V2 surface process at a time. Proposed accounting:
- **New memo entries per Top decision ≤ 3,000,000.** This counts only entries newly computed during that decision; hits on the shared memo are not counted. As a consequence, a decision that would exceed the limit from an empty memo may stay within it when the memo is warm. That is accepted, because the limit is a feasibility ceiling and never changes a value.
- **Entries computed per match ≤ 20,000,000.** This keeps the per-match meaning of the frozen limit.
- **Deterministic exact clearing (proposed).** If the shared memo holds more than 20,000,000 entries at a **match boundary**, it is cleared before the next match. Clearing only affects runtime: values are recomputed exactly. The RSS cap remains the memory backstop, and overflow = OPEN.

### A1.5 Required proof before acceptance (synthetic seeds 910000 and above only)

**Cache OFF against cache ON** must be exactly equal on every synthetic preflight role shape: A-PROD, B-PROD, E-PROD stalling OFF, E-PROD stalling ON with D3-B, and the PROTECT substitute. Each role runs with **at least 3 matches**, so that cross-match hits actually occur. Required equal:
- every decision, and every Q value of every route record;
- the complete replay tape, and every match summary;
- every timeline record and gameplay signature;
- the synthetic P / G / HG-shaped scoring and its PASS / FAIL / OPEN label;
- the inertness-replay output and the uninstrumented-run result.

Also required:
- zero evaluator RNG draws, both ways;
- **cross-match hits > 0** on at least the E-PROD roles, so the test is not vacuous;
- distinct memo generations across the candidate, second and uninstrumented runs, and across surfaces;
- no frozen, regression or fresh-holdout seed executed, enforced by the preflight guard.

Only timing, cache-hit and size counters and RSS may differ.

**Mutation tests** must be caught by the equivalence or unit tests:
- dropping the depth from the key;
- dropping the stalling fields from the key;
- dropping a fingerprint component. This is caught by a test that deliberately offers one memo object to two configurations that differ only in that component.

### A1.6 Feasibility target (not a gate)

On the synthetic E-PROD stalling-ON preflight role, with at least 3 matches, the mean seconds per Top decision with the cache ON should be **≤ 60 s**. That is about 15% headroom under the 70 s break-even. The cache-OFF figure is reported alongside.

This is an engineering target, not a gameplay gate and not a G or HG threshold. If it is not met, the slice stops (**HARD STOP**) for a decision. The options then are another semantics-preserving optimization, or accepting OPEN. The 48 h limit is **not** raised.

### A1.7 Authoritative driver requirement

When authoritative mode is implemented (separately authorized), a worker that exceeds the 48 h subprocess timeout, the RSS cap or a node limit must be **recorded as that surface OPEN**, and the driver continues with the remaining surfaces. It must not crash the whole run.

### A1.8 Unchanged

B = 5, M = 13, QB, Tier R, the RESET rules, the stamina guard, the opponent contract, G1-G6, HG1-HG6, the fresh seeds, the 16 GB RSS cap, 48 h per surface, and one TACTICAL_V2 surface process at a time are all unchanged.

A cache-OFF switch exists only for the A1.5 proof. The authoritative measurement runs with the cache ON, as frozen here once binding.

---

# 5. Supported configurations

These are the same as TACTICAL_V1 (ae786af section 2.1 and section 9.1): v0.2 setup, v0.3a submissions, v0.4a semantics, the informed Bottom responder, handoff NONE or D3-B, and an interval that is a whole number of quanta. There is no fallback, and unsupported configurations raise `ValueError`.

**v0.4a-off exception.** The frozen PROTECT probe envelope is admitted exactly, at **base_seed 42 and base_seed 685800 only** (the fresh PROTECT holdout seed of section 7), with every other argument equal. This is the already-qualified valuation envelope; the seed changes no configuration. Every other v0.4a-off configuration raises `ValueError`.

**Required pins (T7):**
- positive tests for exactly those two seeds;
- negative tests for every single-argument perturbation of the envelope;
- a negative test for a third, arbitrary base_seed.

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
- **DESIGN FAIL:** any gate fails with valid evidence. Record it and STOP. No tuning, no re-run, no change to B, M, QB, the Tier R rules or any gate.
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
- the **route-search equivalence pin**: with stalling off, the implementation's Q equals the 3b08cea diagnostic instrument on every characterization state, at B = 5 and M = 13, under QB;
- the **stalling exactness tests** of section 4.1 (field coverage and successor equality, coverage of reset consequences, zero RNG on stalling paths);
- the **Tier R tie tests** (T3): a positive tie between RESET and an action chooses the action, and RESET with strictly greater Q than every action chooses RESET;
- the **PROTECT envelope pins** (T7, section 5);
- budget-overflow tests (node limits and the RSS monitor) showing OPEN, not approximation;
- purity tests.

---

# 9. Reported (not gated)

- Everything Stage 1B reported (ae786af section 6).
- **TE-2E route tier.** Choices by option type (builder, other action, RESET) and by commitment. The distribution of Q at choices. How often Tier R was empty, and how often RESET won Tier R. Route-search nodes, frontier, wall time and memory per decision.
- **O-3 fidelity, both directions.** First, Top's route search models Bottom by the O-3 TE-1 surrogate, while the real Bottom uses TE-1 with projection v2. Second, Bottom's projection models Top by the TE-1 surrogate, while the real Top uses TE-2E. Both are reported by side and tier.
- **Stalling-ON resets.** The stalling consequences produced by real Top RESETs: warnings, penalties, position resets and free windows. All are modeled by the route search.
- **Calibration.** Σ Q at Tier-R choices against realized Threat entries within the next 13 windows (±3σ, reported).
- **Holdouts.** The seen holdouts (4242, 4342) as ratios to their committed ESCAPE_FIRST baselines.

---

# 10. Predictions (recorded before implementation)

- **G1 is expected to recover substantially on A-PROD,** because routes exist at 13 windows from the opening. Whether it reaches ≥ 63 is uncertain. Q is optimistic, and Bottom (TE-1) also changes its play once Top exchanges.
- **G4 is expected to pass.** PROTECT had no route at any horizon in the characterization.
- **G5 and G6 are the main risks.** Route-seeking Top play drains Bottom through exchanges. The commitment mix it selects was measured only at the opening state, where LOW was best or tied.
- **G3 is a risk on Recognition surfaces.** More Top exchanges give Bottom more terminal windows; the direction is uncertain.
- **Runtime.** Feasible on A-PROD and PROTECT (≤ 0.4 s per decision under QB in the characterization). The Recognition surfaces were not characterized. On stalling-ON surfaces the route branch also carries stalling state, which reduces merging. Either could exceed the budget, which would be OPEN. Running one surface at a time (T8) lengthens the measurement.
- **The HG gates are the real test** of whether the 13-window finding generalizes.

---

# 11. Decisions and review rulings

| # | Decision | Ruling |
|---|---|---|
| T1 | Top TE-2E; Bottom frozen TE-1 | **APPROVED** |
| T2 | B = 5, M = 13, absolute windows; QB exactly as in section 4 | **APPROVED**; no tuning after measurement |
| T3 | Tier R choice between RESET and actions | **AMENDED (section 3, R4-R5).** RESET wins only with strictly greater Q. A positive tie goes to the non-RESET option. Among tied non-RESET options: axis_realized, axis_raw, cost, catalog order, commitment rank. Tie tests are required. |
| T4 | Stamina guard applied to Q in Tier R | **APPROVED**; RESET stays outside commitment guarding |
| T5 | RESET semantics in the route search under stalling ON | **AMENDED (section 4.1).** The engine's real `reset_window()` runs on a route branch that carries every stalling field, with exactness tests. The proposed omission is withdrawn. |
| T6 | HG1-HG6 gated and required for PASS | **APPROVED** |
| T7 | PROTECT envelope at seeds 42 and 685800 only | **APPROVED WITH PINS (section 5)** |
| T8 | Budgets and machine safety | **AMENDED (section 4.2).** One TACTICAL_V2 surface process at a time; RSS ≤ 16 GB; deterministic node limits and 48 h kept; first limit tripped = OPEN. |
| T9 | Uninstrumented-run identity required | **APPROVED** |

**Amendment A1 (section 4.3): decisions for review (PROPOSED).**

| # | Decision | Proposed |
|---|---|---|
| C1 | Scope: only the solved-value memo is shared; the step caches stay per match | A1.1 |
| C2 | Key: (static fingerprint, full route branch, depth); never `te.State` alone | A1.2 |
| C3 | Lifetime: one evaluated run of one surface; the candidate, second and uninstrumented runs each start empty; never across surfaces, processes or disk | A1.3 |
| C4 | Budgets: 3M counts newly computed entries per decision; 20M counts entries computed per match; deterministic exact clearing above 20M held at a match boundary | A1.4 |
| C5 | Proof: cache OFF vs ON exact on all role shapes with at least 3 matches; non-vacuous hits; mutations caught | A1.5 |
| C6 | Feasibility target ≤ 60 s mean per Top decision on synthetic E-PROD stalling ON (not a gate); HARD STOP if missed; 48 h not raised | A1.6 |
| C7 | Authoritative driver records a timeout, RSS or node overflow as that surface OPEN and continues | A1.7 |

---

# 12. Not authorized by this document

- any implementation or wiring, and any TE-2 or TE-1 run;
- any run of any tactical policy on the fresh holdout seeds;
- any change to TE-1, projection v2, the engine, the domain, positions, D3-B, the production policy, the defaults or the frozen digest;
- any change to P1-P6, G1-G6, thresholds, the G4 amendment or the G6 denominator;
- modification of any historical evidence;
- promotion, merge, squash or force-push.

**HARD STOP.**
