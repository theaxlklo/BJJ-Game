# Joint Tactical Evaluator — G1 Post-Failure Characterization (read-only)

## Status

**CHARACTERIZATION COMPLETE — READ-ONLY — HARD STOP FOR REVIEW.**

The Stage 1B result (`27ef5e5`, DESIGN FAIL on G1) is unchanged. There was no re-run, no new G1 verdict, no TE-1 change and no TE-2 implementation.

```text
preregistration (binding):  ab50f7ef908f1f174aba3c5fad331f8b3ff2c060
                            docs/TACTICAL_EVALUATOR_G1_CHARACTERIZATION_PREREGISTRATION.md
Stage 1B result (input):    27ef5e54095b2915f776cb6287dba73bbe28d026
branch:                     review/tactical-evaluator-g1-characterization
diagnostics:                src/bjj_game/diagnostics/tactical_evaluator_g1_characterization.py
tests:                      tests/test_tactical_evaluator_g1_characterization.py (9)
evidence:                   docs/evidence/tactical_evaluator_g1_characterization.json
```

The characterization was run once, on Python 3.13.15 under Windows with 20 worker processes, in 50 s. Inside that run, every analysis was computed twice to check determinism.

## Integrity

| Check | Result |
|---|---|
| Frozen Stage 1B and Stage 1A-v2 evidence hashes, before and after | unchanged |
| Paths changed relative to `27ef5e5` outside this slice | none |
| Baseline reconstruction (frozen row; every decision and attempt vs Stage 1A-v2 records) | exact on A-PROD and PROTECT |
| Candidate reconstruction (inertness replay from committed Stage 1B records; summary and events) | exact on A-PROD and PROTECT |
| State identical in both trajectories at every first divergence | yes, 200 of 200 |
| RNG draws during route search and analyses | 0 |
| Deterministic re-run of every analysis | identical |
| Route-search cells over budget (INFEASIBLE) | none |

---

# 1. First divergence

**Every A-PROD match diverges at its first window, from a single state.** That covers all 100 matches, including the 78 baseline Threat matches. PROTECT is the same: all 100 matches diverge at window 0 from one state.

| | A-PROD | PROTECT |
|---|---|---|
| Clock, initiative | 295 s, Top | 295 s, Top |
| Axis, band | 2.0, Stable | 2.25, Strong |
| Top / Bottom stamina | 99 / 99, both Fresh | 99 / 100, both Fresh |
| Setup, Ready, stage | all tiers 0, none Ready, no stage | the same |
| Baseline decision | High Mount Climb, MEDIUM (setup) | High Mount Climb, MEDIUM (setup) |
| TE-1 decision | RESET | RESET |

**TE-1 candidates at the A-PROD state.** There are 2 legal actions × 3 commitments:

| Candidate | terminal | progress | setup_future | setup_advance | axis (realized, raw) | ready_mass |
|---|---|---|---|---|---|---|
| High Mount Climb LOW / MEDIUM | 0 | 0 | 0 | 1 | −1, −1 | 1/3 |
| High Mount Climb HIGH | 0 | 0 | 0 | 1 | −1.9, −2 | 1/9 |
| Crossface Pressure LOW / MEDIUM / HIGH | 0 | 0 | 0 | 0 | −1 to −1.9, −1 to −2 | n/a |

Every candidate fails every tier: terminal ≤ 0, progress ≤ 0, setup_future ≤ 0, and both axis values ≤ 0. No candidate was removed by the stamina guard.

The builder reaches Ready in the projection with probability 1/3. But at the projected use state Bottom is still fresh, so the informed defender defeats the Ready use at every commitment. With no tier qualifying, RESET is chosen as the fallback.

---

# 2. Route reachability and the horizon

**Route value** `V_N` is the exact maximum over Top policies of P(Threat within N decision windows), against a frozen opponent. Ready reachability is computed the same way. TE-1's own horizon is N0 = 5 windows at these states.

**A-PROD first-divergence state:**

| Horizon | O-TE1: V | O-TE1: RESET Q / best action Q | O-EF: V | O-EF: RESET Q / best action Q | Ready reachable |
|---|---|---|---|---|---|
| N0 = 5 | 0 | 0 / 0 | 0 | 0 / 0 | yes |
| N0+2 = 7 | 0 | 0 / 0 | 0 | 0 / 0 | yes |
| N0+4 = 9 | 0 | 0 / 0 | 0 | 0 / 0 | yes |
| **N0+8 = 13** | **1/3** | **1/9 / 1/3** | **1** | **1 / 673/729** | yes |

**PROTECT first-divergence state:** V = 0 at every horizon under both opponents, and every action and RESET has Q = 0. Ready is still reachable.

**Candidate trajectory states (S3, 30 distinct Top states per surface, from the all-RESET loop):**

| Horizon | A-PROD route, O-TE1 | A-PROD route, O-EF | PROTECT route (both) | Ready (both surfaces) |
|---|---|---|---|---|
| N0 to N0+4 | 0 / 30 | 0 / 30 | 0 / 30 | 28 / 30 |
| N0+8 | **25 / 30** | **22 / 30** | **0 / 30** | 28 / 30 |

At N0+8 under O-TE1, RESET still preserves a route in 24 of the 25 A-PROD states with a route, and destroys one. Under O-EF it preserves 19 of 22, destroys 3, and is strictly best in 1.

**Baseline route states (S2: the first builder of each converting chain).** A-PROD has 4 distinct states covering the 78 matches, all at 265 s with Top 51 and Bottom 48 stamina. PROTECT's S2 is its opening state.

| Horizon | A-PROD route, O-TE1 | A-PROD route, O-EF | PROTECT |
|---|---|---|---|
| N0 | 2 / 4 | 4 / 4 | 0 / 1 |
| N0+2 and beyond | 4 / 4 | 4 / 4 | 0 / 1 |

On those 4 baseline states, TE-1 itself would still choose RESET on 3 and setup on 1.

**Cost.** The largest cell was 18,115 nodes in 7.5 s, A-PROD at N0+8 under O-EF. No cell came near the budget of 3,000,000 nodes or 30 minutes.

---

# 3. Reset forensics

The single A-PROD first-divergence state carries codes **R1, R2, R3, R4 and R6**:
- no terminal (R1), progress (R2) or position (R4) value;
- the builders have setup_future = 0 but Q > 0 beyond the horizon (R3);
- the best non-RESET Q is 0 at N0 and positive at N0+8 (**R6, horizon**).

It does **not** carry R5 (stamina guard), R7 (opponent kills the route) or R8 (no route).

The PROTECT state carries **R1, R2, R4 and R8**: no route at any horizon under either opponent.

**RESET comparison at the A-PROD state:**
- At N0 to N0+4, RESET and every action are **equivalent at 0**. Pricing RESET at TE-1's own horizon changes nothing.
- At N0+8 under O-TE1, RESET (1/9) is worse than any action (1/3).
- At N0+8 under O-EF, RESET (1) is strictly best. Against ESCAPE_FIRST, Bottom drains itself by attacking.

---

# 4. setup_future = 0 decomposition

| Surface | Builder candidates with setup_future = 0 | Primary cause | Beyond the horizon |
|---|---|---|---|
| A-PROD | 14 | **Z3b in all 14:** Ready is reached, but the informed defender defeats the use at every commitment | **Z4 in all 14:** Q > 0 at a larger horizon (horizon-truncated) |
| PROTECT | 6 | Z3b in all 6 | **Z5 in all 6:** Q = 0 at every horizon under both opponents (dead) |

On A-PROD, the zero means "not visible within the projection". On PROTECT, it means "dead within the characterization".

**TE-1 projection vs route value at the same horizon N0 (A-PROD S1 and S2 builders):**
- 12 builders have setup_future = 0 and Q_N0 = 0;
- **2 builders have setup_future = 0 but Q_N0 > 0;**
- 1 builder has both positive;
- none has setup_future > 0 with Q_N0 = 0.

So at the same horizon, the fixed-chain projection also misses routes that adaptive play finds. It assumes "repeat this builder at this commitment, then the best use".

---

# 5. Quiescence

The search runs at the base horizon N0, extends unresolved nodes up to N0+8, and values quiet nodes at 0. It is compared with uniform search at N0+8.

| Set, opponent | Uniform N0+8 routes | QA routes (QA misses) | QB routes (QB misses) | Nodes: uniform / QB |
|---|---|---|---|---|
| A-PROD S1, O-TE1 | 1 / 1 | 0 (1) | 1 (0) | 4,358 / 1,893 |
| A-PROD S1, O-EF | 1 / 1 | 0 (1) | 1 (0) | 18,115 / 8,613 |
| A-PROD S2, both | 4 / 4 | 4 (0) | 4 (0) | about 10-11k / 8.7-10.5k |
| A-PROD S3, O-TE1 | 25 / 30 | **0 (25)** | **25 (0)** | 78,991 / 40,935 |
| A-PROD S3, O-EF | 22 / 30 | 0 (22) | 18 (4) | 192,292 / 117,216 |
| PROTECT (all sets, both) | 0 | 0 | 0 | 2,073-197,080 / 847-76,906 |

- **QA**, the prompt's conditions (chain in progress, Ready, immediate terminal or progress), recovers **none** of the A-PROD opening and trajectory routes.
- **QB** adds "Bottom is Exhausted". It recovers every uniform route under O-TE1 and 18 of 22 under O-EF. It never creates a PROTECT route. Its wall time was about 30 times lower than uniform on S3 (1.4 s vs 41 s under O-TE1).
- **No quiescent route appeared that uniform search lacked.** QA and QB never disagree with uniform in that direction.

---

# 6. Opponent-policy ablation

The route **exists under both opponents** wherever it exists, and R7 never fires. That makes **TE-1-versus-TE-1 feedback not the cause of route absence**. The TE-1 opponent even leaves more A-PROD trajectory states with a route (25 vs 22).

The opponent model does change the **relative value of RESET**. Against ESCAPE_FIRST, waiting is strong, because Bottom spends its own stamina attacking. Against the TE-1 opponent, which also waits, waiting is weak (1/9 vs 1/3), because only Top's exchanges drain Bottom.

---

# 7. A-PROD vs PROTECT separation

| Signal (at N0+8 unless stated) | A-PROD | PROTECT |
|---|---|---|
| setup_future > 0 (TE-1) at the opening state | 0 / 1 | 0 / 1 |
| Ready reachable (any horizon) | S1 1/1; S3 28/30 | S1 1/1; S3 28/30 |
| **Threat route V > 0, O-TE1** | **S1 1/1; S2 4/4; S3 25/30** | **0/1; 0/1; 0/30** |
| **Threat route V > 0, O-EF** | **S1 1/1; S2 4/4; S3 22/30** | **0/1; 0/1; 0/30** |
| Threat route at TE-1's own horizon N0 | S1 0/1; S3 0/30 | 0 |
| QB-quiescent route, O-TE1 | S1 1/1; S3 25/30 | 0 |

- **Threat-route viability at a sufficient horizon separates the two surfaces completely** on every set.
- setup_future does not separate them at the opening, because it is zero on both.
- **Ready reachability does not separate them.** PROTECT churn reaches Ready as easily as A-PROD. Rewarding Ready, setup progress or builder chains, rather than Threat reachability, would reopen G4.

---

# 8. Backward-reachability feasibility

Every analyzed cell is a bounded backward reachability from the success states over the forward-reachable set, computed as an exact AND-OR expectimax. The forward-reachable (state, remaining) cardinality was at most 18,115 nodes at 13 windows (sum over all 30 S3 states about 192,000), with peak frontiers in the low thousands.

A full retrograde table over the whole state space was not built. It would span the clock (60 windows), both stamina pools (0-100 each), axis, band, setup tiers, Ready and behaviors. The bounded per-decision search is already cheap, so a global table is not needed to obtain the signal.

---

# 9. Architecture comparison

| Design | G1 relevance (evidence) | G4 risk | G5 / G6 risk | Complexity | Runtime per decision (this machine, Python) | Testability, explainability |
|---|---|---|---|---|---|---|
| **TE-2A evaluated RESET** (at TE-1's horizon) | **None alone.** RESET and every action tie at 0 at N0 to N0+4 on all A-PROD S1 and S3 states. | low | low | small | as TE-1 | high |
| **TE-2B quiescent extension, QA** | **Fails:** recovers 0 of 26 A-PROD S1+S3 routes | low | low | medium | low | medium |
| **TE-2B quiescent extension, QB** | Recovers 26 of 26 A-PROD S1+S3 routes under O-TE1, 19 of 23 under O-EF | none observed (PROTECT 0) | unmeasured; opponent exhaustion becomes a search driver | medium | about 0.05 s per state | medium; the definition must be frozen |
| **TE-2C route-viability tier** (V_N > 0 before RESET) | Separates A-PROD / PROTECT completely at N0+8 | none observed | binary viability treats V = 1/9 like V = 1; ordering by value is needed | medium | ≤ 7.5 s uniform, ≤ 0.4 s with QB | high |
| **TE-2D SRQR** (evaluated RESET + quiescence + viability leaf) | Its components that the evidence supports are the route value and QB; RESET is valued inside the search | as TE-2B / TE-2C | as TE-2C | highest | as TE-2B | medium |
| **Backward reachability, full table** | Same signal as the bounded search | none observed | as TE-2C | high | precompute-heavy | high once built |
| **TE-2E (proposed): exact route-value tier** | See below | none observed | must be measured | medium | about 0.05-7.5 s | high |

**TE-2E, proposed.** Keep TE-1 tiers A and B unchanged, along with precedence, the stamina guard and D3-B. Replace the tier-C projection (setup_future) and the free RESET fallback with **one exact route value**: `Q_N(s, a)` over every candidate **including RESET**, computed by the instrument used here (OR over own options, exact chance and declared-opponent AND, Fraction, memoized), with QB-quiescent extension to a fixed bound.

The decision rule:
- if max Q > 0, choose by Q, then by the existing commitment-cost tie-breaks;
- otherwise fall through to position, then RESET.

This prices RESET and actions on the same footing. It replaces the fixed-chain projection, which misses routes even at its own horizon (section 4), and it reads the signal that separates A-PROD from PROTECT (Threat reachability, not Ready).

---

# 10. Recommendation

```text
PRIMARY FAILURE MECHANISM:
  Horizon truncation (H2) of a route that runs through draining the
  defender. From the opening state, Threat is reachable only at 13 windows
  (V = 1/3 vs the TE-1 opponent, 1 vs ESCAPE_FIRST) and is invisible at
  TE-1's 5 windows, and at 7 and 9. Every candidate then values 0 and the
  RESET fallback wins.

SECONDARY MECHANISMS:
  - Projection restriction (H3): the fixed "repeat builder, then use" chain
    gives setup_future = 0 to 2 builders whose adaptive route value at the
    same horizon is positive.
  - Acting-policy feedback (H4): the baseline reached drained-defender states
    by 265 s (Bottom 48), where routes are visible at N0 on 2 of 4 states
    under O-TE1 and 4 of 4 under O-EF. TE-1's all-RESET trajectory never
    drains Bottom by exchanges and stays where routes need 13 windows
    (0 of 30 at ≤ 9 windows).
  - H1, free RESET, matters only as the tie-break consequence of H2: at
    TE-1's horizon RESET and every action are exactly equal at 0.

NOT SUPPORTED:
  - H5 (TE-1 vs TE-1 opponent feedback) as the cause: routes exist under both
    opponents wherever they exist; R7 never fires. The opponent changes
    RESET's relative value, not route existence.
  - R5 (stamina guard): never involved.
  - "Ready / setup progress as the missing value": Ready is reachable on
    PROTECT as on A-PROD, so it does not discriminate.
  - QA quiescence: recovers no route.

BEST NEXT EVALUATOR ARCHITECTURE:
  TE-2E, an exact route-value tier: Q_N over all candidates including RESET,
  exact AND-OR expectimax against the declared opponent contract, with
  QB-quiescent extension (opponent exhaustion is an unresolved condition)
  up to a fixed preregistered bound. TE-1 tiers A/B, precedence, the stamina
  guard and D3-B are unchanged.

WHY:
  - It is the only tested signal that is positive on every A-PROD set and zero
    on every PROTECT set (25/30 vs 0/30 on trajectory states).
  - It subsumes evaluated RESET without the zero-tie failure of TE-2A.
  - It replaces the fixed-chain projection that misses routes at its own
    horizon.
  - QB makes it cheap: about 30x less wall time than uniform depth for the
    same answers under O-TE1.
  - It is deterministic, draws no RNG and is exact (pinned by tests here).

WHY NOT THE ALTERNATIVES:
  - TE-2A alone ties at zero: no effect.
  - QA quiescence finds nothing.
  - A binary viability tier (TE-2C) discards the value ordering (1/9 vs 1/3)
    that distinguishes RESET from attacking against the TE-1 opponent.
  - SRQR is TE-2E plus a RESET-only trigger. Restricting the search to "would
    RESET" states would leave the projection-restriction misses (H3) of
    tier C in place.
  - A full backward-reachability table is unnecessary at the measured cost.

EXPECTED RISKS:
  - G5 / G6: route-maximizing Top play drains Bottom by exchanges; the
    commitment mix it selects is unmeasured beyond the opening state, where
    LOW was best or tied.
  - G3 / Bottom: TE-1's Bottom also reset everywhere on A-PROD. Bottom's
    escape route needs the symmetric route value, which this slice did not
    characterize.
  - The route value is optimistic: it assumes adaptive Top play and an
    opponent following its declared contract exactly.
  - Runtime: uniform N0+8 costs up to 7.5 s per decision. QB is required in
    practice, and its definition must be frozen before any candidate run.
  - The horizon and quiescence bound are new free choices. They must be fixed
    from this characterization, not tuned on G1.

WHAT MUST BE PREREGISTERED BEFORE IMPLEMENTATION:
  1. The route-value definition (success = Threat entry or Tap; the option set
     including RESET; the opponent contract = O-3 TE-1; exact chance).
  2. The fixed base horizon and quiescence bound, and the QB unresolved
     conditions, unchanged after results.
  3. The tier placement and tie-breaks (after A/B, before position; cheapest
     commitment; the stamina guard).
  4. Bottom's symmetric escape-route value, or an explicit statement that
     Bottom keeps TE-1, with its own characterization.
  5. A budget and the infeasibility rule: no approximation.
  6. Gates: G1-G6 and P1-P6 unchanged, plus a new holdout set never used in
     this characterization.
  7. Integrity: purity, inertness replay, the RNG trace, determinism.
```

**HARD STOP.** TE-2 needs its own preregistration and a separate authorization.
