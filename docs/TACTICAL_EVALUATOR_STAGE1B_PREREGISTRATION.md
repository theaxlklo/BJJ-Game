# Joint Tactical Evaluator — Stage 1B Preregistration (candidate run under real TACTICAL_V1 execution)

## Status

**PROPOSED PREREGISTRATION — DOCUMENTATION ONLY — REVIEW RULINGS RECORDED (section 9) — HARD STOP FOR FINAL REVIEW.**

Nothing is implemented or run. This document freezes how Stage 1B will be scored **before any wiring**. It was proposed at `0fcae3e`; the user's rulings on B1-B8 are recorded in section 9, and this clarification commit applies the two corrections and three wording fixes they required.

**Pre-implementation contract clarification (section 9.1).** `3494fa5` was made binding and an implementation authorization was issued against it. Before any implementation was committed, that attempt stopped on a conflict inside this document: section 2.1 requires v0.4a semantics for `TACTICAL_V1`, but G4's only surface, the frozen PROTECT probe, runs with v0.4a off. The user ruled a hard stop, and this docs-only commit records the narrow exception that resolves it. It is **not** a gate or threshold change and **not** a broadening of supported configurations. No Stage 1B code was committed and `TACTICAL_V1` was never run.

**Authorization language.** The user's approval of the corrected preregistration, at the SHA that carries this text, makes **the document** binding. It does **not** authorize implementation, wiring or any measurement. Stage 1B implementation and the candidate run require a **separate, explicit authorization**.

```text
branch:                    review/tactical-evaluator-stage1b-preregistration
base:                      750ffe859d59f969db334ba73daa038a6e181bd0  (Stage 1A-v2 PASS, CI 37519099015)
binding inputs (unchanged): docs/TACTICAL_EVALUATOR_PREREGISTRATION.md            (4e61bad: P1-P6, G1-G6, TE-1)
                            docs/TACTICAL_EVALUATOR_PROJECTION_V2_PREREGISTRATION.md (5b57017: projection v2, O-3)
historical results:         Stage 1A  FAIL (C3) at 2d2778d  — unchanged
                            Stage 1A-v2 PASS at 750ffe8     — unchanged
canonical policy:           PRODUCTION_STAMINA_RECOVERY_POLICY (unchanged)
frozen digest:              3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

**Scope.** Stage 1B of 4e61bad section 3: wire TE-1 (with projection v2) behind an opt-in batch option, run it **once** on the frozen surfaces, and score the preservation gates P1-P6 and the design gates G1-G6.

**P1-P6 and G1-G6 keep their frozen surfaces, baselines and numerical floors. No threshold changes and no gate is added.** This document adds measurement definitions, integrity checks, reported (not gated) measures, and decision rules that 4e61bad left implicit.

**One of them is an explicit pre-measurement amendment to G4's measurement definition** (section 5.2). It changes how a G4 verdict is obtained, so it is disclosed as an amendment and not described as "not a gate change". The floor (≤ 884) and the PROTECT baseline (1,768) are unchanged.

---

# 1. What Stage 1B measures, and what Stage 1A-v2 did not

Stage 1A-v2 qualified the **valuation**: on states reached by the **baseline** policy, projection v2 predicts conversions (C5, C3-H) and never revalues PROTECT churn (C4). It did not run TE-1 as the acting policy.

Under real execution, three things change that no shadow gate could test:

1. **State distribution shifts.** TE-1 declines builds the baseline made (A-PROD shadow: 156 setup choices and about 2,150 Top resets, against 356 baseline setup decisions), so initiative, time, drain and axis evolve differently. The calibration was measured on the baseline's trajectories.
2. **The opponent window changes meaning.** In Stage 1A-v2 the modeled opponent was the real `ESCAPE_FIRST`, and the surrogate matched every real Bottom decision. Under TACTICAL_V1 the opponent is TE-1, and its nested setup valuation is the frozen single-chain projection, a deliberate depth-1 approximation (5b57017 section 3, O-3). Its fidelity can be measured only here.
3. **Commitment becomes a choice.** Stage 1A-v2 scored builders at the baseline commitment (MEDIUM). TE-1 chooses LOW / MEDIUM / HIGH, which changes drain, pacing and the Recognition game.

G1 (submission access) is the gate most likely to fail and the one no existing evidence can predict (4e61bad section 5). It is the first thing this stage answers.

---

# 2. Wiring contract (what Stage 1B may implement)

**Authorized to change** (at Stage 1B, not now):
- `interfaces/batch.py`: a new option `initiator_policy` (`ESCAPE_FIRST` default, `TACTICAL_V1`), wired **after** the existing recovery / D3-B precedence;
- `interfaces/tactical_evaluator.py` / `tactical_projection_v2.py`: `TacticalV1Policy` and the opponent-window mode below;
- new diagnostics and tests.

**Not to change:** engine, domain, settlement, costs, rates, thresholds, D3-B, production policy, response policy, Recognition, scoring, defaults, the frozen digest.

## 2.1 Seam and invariants

- The default `ESCAPE_FIRST` path must be **behaviorally and RNG-identical to the frozen baseline**: same decisions, same RNG draws in the same order, same summaries. The existing decision path remains unchanged apart from the opt-in selection seam. (Adding an option necessarily changes source and bytecode, so literal byte identity is not required.) This is P1, and it includes every existing pinned surface and both the Stage 1A and Stage 1A-v2 evidence pins.
- `TACTICAL_V1` is selected only by the explicit option. It requires the configuration of 4e61bad (v0.2 setup, v0.3a submissions, v0.4a semantics, informed Bottom responder) and raises `ValueError` on any configuration projection v2 does not model (for example handoff modes other than `NONE` and D3-B). There is **no silent fallback to `ESCAPE_FIRST`**.
  - **Single exception (section 9.1):** the exact frozen G4 PROTECT probe is admitted with v0.4a off. Every other configuration with v0.4a off still raises `ValueError`.
- Both initiators use TE-1 under `TACTICAL_V1` (Top and Bottom), as in 4e61bad section 2.
- **Order of decisions at a window (unchanged from the runtime):** D3-B controller decision (TOKEN / LOCKOUT_HOLD / unarmed), then force-RESET rules, then the initiator policy. In a LOCKOUT_HOLD window `recovery_hold()` replaces the initiation, and TE-1 never executes. In a Bottom RECOVER window while Exhausted, the commitment stays **LOW** (`LOW_WHILE_EXHAUSTED`) and TE-1 picks only the action (4e61bad 2.6).
- The D3-B collector calls `policy.choose(match)` at LOCKOUT_HOLD windows as a **counterfactual**. Under `TACTICAL_V1` that call must be pure: it may not change match state, controller state or any RNG, and its result is recorded only.
- **Decision-reason mapping** (the batch's existing summary counters read the reason):

  | TE-1 tier | Top reason | Bottom reason |
  |---|---|---|
  | A terminal | `submission` | `escape` |
  | B progress | `submission` | n/a |
  | C setup | `setup` | `setup` |
  | D position | `position` | `position` |
  | E reset | `reset` | `reset` |

## 2.2 Opponent windows under TACTICAL_V1 (O-3, as approved at D1)

Inside a continuation, an opponent window is chosen by **the opponent's declared policy contract** on the branch state. Under `TACTICAL_V1` that contract is TE-1 (tiers, tie-breaks, stamina guard, precedence). Its **nested setup valuation is the frozen 4e61bad section 2.4 single-chain projection** (the surrogate). Depth is exactly 1: the surrogate never recurses and never starts another continuation. A required guard test pins this: the surrogate path never calls the continuation. (Stage 1A-v2 pinned the stricter "no nested TE-1", which cannot hold here because the opponent window itself is a TE-1 evaluation.)

This is a declared approximation, not "the actual opponent policy". It is reported, not gated (section 6.3).

## 2.3 Purity

The evaluator remains pure: no RNG draw, no mutation of the live match or of the live D3-B controller, no I/O. Sandbox matches are fresh instances (as in Stage 1A-v2).

---

# 3. Surfaces, baselines and the run

**Gated surfaces** (100 matches each; the frozen Stage 1A surfaces, unchanged): A-PROD, B-PROD, E-PROD seeds 42 and 142 each with stalling OFF + shadow and ON, and the PROTECT probe. The authoritative candidate run is made **once**.

**Baselines** (committed evidence; the 4e61bad section 4 table, reproduced exactly by the Stage 1A and Stage 1A-v2 runs):

| Surface | Threat matches | Tap | Escapes | Timeouts | Top completed builds |
|---|---|---|---|---|---|
| A-PROD | 78 | 0 | 22 | 78 | 312 |
| B-PROD | 59 | 9 | 12 | 79 | 880 |
| E-PROD 42 / 142 | 61 / 57 | 5 / 4 | 30 / 31 | 65 / 65 | 844 / 841 |
| PROTECT probe | 0 | 0 | 2 | 98 | 1,768 |

**Metric definitions (frozen by reference to existing code; no new definitions):**
- Threat matches = `summary.matches_reached_submission_threat`; Tap = outcome `TAP — Americana`; timeouts = outcome `TIMEOUT — Mount retained`; escapes = matches − Tap − timeouts; Top completed builds (historical counter) = `summary.top_completed_setup_build_count` (as in `diagnostics/tactical_evaluator.py` baseline reproduction). G4's authoritative measure is the reason-independent count of section 5.2.
- Bottom first-Exhausted median = `summary.bottom_first_exhausted_time_median`.
- Bottom Exhausted share = `bottom_exhausted_share_of_match_time` of `diagnostics/late_recovery.py` (Bottom advance-time while Exhausted over total match time; baseline 79.0% seed 42, 79.5% seed 142), computed by the unchanged observer on the candidate run.

**Reported-only holdout runs** (not gated; section 6.4): the six Stage 1A-v2 C3-H surfaces (A-PROD 4242, B-PROD 4242, E-PROD 4242 and 4342, both stalling modes), whose ESCAPE_FIRST baselines are committed in the Stage 1A-v2 evidence (Threat / Tap / escapes / timeouts / builds: 77, 0, 23, 77, 308; 49, 8, 21, 71, 824; 49, 2, 42, 56, 790; 57, 1, 42, 57, 725).

---

# 4. Gates (frozen; scoring made explicit)

## 4.1 Preservation P1-P6 (mandatory)

| ID | Gate (4e61bad 4.1) | How it is scored in Stage 1B |
|---|---|---|
| P1 | Raw defaults, canonical policy and frozen digest unchanged; with `ESCAPE_FIRST` every pinned surface reproduces | Full suite green on 3.11 and 3.13, **including the Stage 1A and Stage 1A-v2 evidence pins** (those wrap `EscapeFirstInitiatorPolicy.choose` and must still reproduce); digest exact; both checkers PASS |
| P2 | Rule 1 exact, Rule 2 OFF, best-effort hold, costs / rates / thresholds unchanged | Unchanged by construction; scored by the full suite and by `git diff` showing no change to engine, domain, settlement, stamina or production-policy files |
| P3 | Precedence | 0 Bottom RECOVER Exhausted initiations at a commitment other than LOW; every D3-B decision is produced by the unchanged controller; 0 TE-1 actions in a LOCKOUT_HOLD window (counted from the engine's `recovery_hold_history` and the controller log) |
| P4 | No RNG consumed by the evaluator; deterministic replay | (a) 0 draws from any `random.Random` while the evaluator runs (the Stage 1A `RngTrace`, now around the real policy call); (b) two runs are identical (summary, signatures, every record, RNG digest); (c) **inertness replay** (section 5.1) |
| P5 | Stamina guard | Recorded per decision: 0 tier A/B choices with `enters_exhausted` that are not strictly better than every admissible non-entering commitment of the same action; 0 tier C/D choices above the cheapest qualifying commitment |
| P6 | Exact-head CI on 3.11 and 3.13 including full-history PG8 | CI on the exact head of the Stage 1B result commit |

## 4.2 Design gates G1-G6 (mandatory; floors unchanged)

| ID | Gate | Scoring |
|---|---|---|
| G1 | A-PROD Threat matches **≥ 63**; B-PROD + E-PROD 42 + E-PROD 142 pooled Threat matches **≥ 142** | Pooled sum is taken **per stalling mode** (the B-PROD run counts in both); each of OFF + shadow and ON must reach 142 |
| G2 | Tap **≤ 20** on every surface | Every gated run |
| G3 | E-PROD pooled (42 + 142) escapes **≥ 49**; B-PROD escapes **≥ 10** | E-PROD pooled per stalling mode |
| G4 | PROTECT Top completed builds **≤ 884** | The **reason-independent completed-chain builder-attempt count** (section 5.2, a pre-measurement amendment to the measurement definition) must be ≤ 884. The historical counter is reported alongside |
| G5 | E-PROD Bottom first-Exhausted median **≥ 50 s**; Bottom Exhausted share **≤ 80%** | Each seed, each stalling mode (4 runs); metrics as in section 3 |
| G6 | E-PROD pooled share of HIGH among TE-1-chosen initiations **≤ 50%** | Section 5.3 |

Each E-PROD gate must pass in **both** stalling modes. Percentage floors round up to the next integer, as frozen.

## 4.3 Decision rule

- **DESIGN PASS:** P1-P6 and G1-G6 all pass, and no integrity check in section 5 fails.
- **DESIGN FAIL:** any of P1-P6 or G1-G6 fails with valid evidence. Record it and **STOP**: no tuning, no gate change, no re-run under the same preregistration, no wiring tweak. Section 7 lists the read-only diagnostics that may follow a FAIL.
- **OPEN:** missing or inadequate evidence, any integrity failure (section 5), a baseline that does not reproduce, or infeasible cost. OPEN is never relabeled PASS or FAIL, and approximation is not an allowed way to make a run feasible.

---

# 5. Integrity checks and measurement guards (mandatory; any failure = OPEN)

## 5.1 Inertness replay (P4c)

After the candidate run, re-run each gated surface with a **replay policy** that returns the recorded TE-1 results **without evaluating anything**. The summary, per-match gameplay signatures and RNG digest must be identical to the candidate run. This proves that the evaluator has no side effect on the match, the controller or the RNG under real execution. The evaluator-free baseline comparison of Stage 1A no longer applies, because the gameplay legitimately differs.

**The replay tape covers every `policy.choose` invocation, in order.** That includes the D3-B collector's **counterfactual** calls at LOCKOUT_HOLD windows. Each tape entry records the match, the call index, the returned decision (action, reason) and requested commitment, and a flag **`executed` vs `counterfactual`**, so the two kinds are distinguishable. The replay policy consumes the next entry for every call, whichever kind it is. A tape that holds only executed decisions could consume the wrong entry at a collector-only call and desynchronize even though gameplay is pure. A replay that desynchronizes, runs out of entries, or finds an `executed` flag that does not match the call is an integrity failure (OPEN), not a PASS.

## 5.2 G4 measurement amendment (pre-measurement)

**What the frozen counter does** (`batch.py`, read at `750ffe8`). `top_completed_setup_build_count` is built from `pending_setup_builds`:
- it is incremented at **decision time**, before the attempt resolves, for every Top decision whose **reason is `"setup"`** and whose action is a designated builder;
- the increment does not depend on whether that attempt later advances setup, so failed and cap-absorbed attempts are counted;
- the accumulated pending attempts are **credited** when Top next attempts the target while it is Ready, and a chain that never completes is never credited.

**The loophole.** The increment depends on the reason **label**. Under TE-1 a builder chosen through the position tier carries reason `position`, so it can advance the chain without being counted, and the frozen counter alone could understate churn.

**The amendment.** G4 is scored on a **reason-independent completed-chain builder-attempt count**:
- whenever Top attempts a designated setup builder for a target that is **not yet Ready**, the attempt is added to that target's pending chain **regardless of TE-1 tier or reason, and regardless of whether that attempt advances setup**;
- when Top next attempts the target while it is Ready, the pending attempts are credited **exactly as the frozen counter credits them**;
- a chain that never completes is not credited.

Counting only attempts that advanced setup is **not** the amendment: it would drop the failed attempts the frozen counter includes, and so measure something different.

**What does not change:** the floor (≤ 884), the PROTECT baseline (1,768) and the surface.

**Equivalence at baseline (premise of the amendment).** Under `ESCAPE_FIRST` the two counts coincide, because every Top builder attempt carries reason `setup`. This was checked read-only on the committed baseline at `750ffe8`: A-PROD 312 = 312, B-PROD 880 = 880, PROTECT 1,768 = 1,768. Stage 1B re-checks it on every baseline run (section 5.4). A difference on any baseline run makes the amendment's premise false and the result **OPEN** pending a ruling.

**Reporting.** The historical counter is reported on every run for continuity. Under TE-1 it counts a subset of the reason-independent count (a `setup`-reason builder always targets a not-yet-Ready target), so the reason-independent count is the authoritative loophole guard and the historical counter cannot exceed it. Flagged and ruled at B3.

## 5.3 G6 denominator

"TE-1-chosen initiations" = every initiator **exchange** (not resets or holds) on the E-PROD 42 and 142 runs of one stalling mode, **both sides pooled**, whose commitment TE-1 selected. Exchanges whose commitment was **forced by precedence** (LOW while Exhausted in a Bottom RECOVER window, and the D3-B token path) are excluded from the denominator. The numerator is requested commitment HIGH. Excluding forced LOW exchanges is the stricter reading (the share is higher), and it is the logical one: TE-1 did not choose those commitments. Pooling both sides matches the fact that `TACTICAL_V1` controls both initiators. The count of excluded exchanges is reported. This interpretation is frozen here, before any candidate result is seen (ruled at B4).

## 5.4 Baseline reproduction

The ESCAPE_FIRST baseline is re-run on the head under test and must reproduce the section 3 table exactly (as in Stage 1A and 1A-v2) before any candidate comparison is read. On the same runs the reason-independent count of section 5.2 must equal the historical counter exactly.

## 5.5 Window-ordering regression pins

The Stage 1A-v2 ordering tests (advance, exchange support, opponent-window support against real matches) stay green after wiring, and a new pin covers TE-1 as the opponent inside a continuation.

---

# 6. Reported, not gated

## 6.1 Required by 4e61bad section 4.4

Commitment distribution by side, tier and surface; tier distribution versus baseline; setup decisions and builds per Threat entry; forgone-better-position counts; Ready conversion predicted vs actual (9908235 format); full outcome tables, timeouts and stamina finals; all late-recovery measures (`LATE_RECOVERY_CHARACTERIZATION.md` section 1); calibration tables per component.

## 6.2 Real-play shift (the state-distribution question of section 1)

- Per surface: Top windows by TE-1 tier, resets per match, time in each (initiative, band) cell, and the mean time to first Ready.
- **Counterfactual of declined builds** (from the shadow evidence, not a new run): baseline builds TE-1 declines (A-PROD: 200 of 356 setup decisions had setup_future = 0).
- Free initiative windows and projection-horizon mismatches (chains whose real horizon differs from 2r). Stalling ON creates free windows that the continuation does not model (5b57017 section 2 step 1); this reports how often it matters.

## 6.3 Calibration under TACTICAL_V1

- **Setup calibration (C5-style).** For every chain begun in the candidate run: Σ setup_future at the builder's chosen commitment vs realized Threat entries, with the exact ±3σ test **reported only**, as calibration evidence under the shifted state distribution.
- **O-3 surrogate fidelity.** At every real opponent window: whether the surrogate decision (TE-1 with the frozen projection) equals the real decision (TE-1 with projection v2), by side and tier. This is the only place the depth-1 approximation is measured.

## 6.4 Holdouts

The six holdout surfaces are run once under `TACTICAL_V1` and reported against their committed ESCAPE_FIRST baselines using the G-gate metrics as **ratios only**, with no pass/fail. They carry no verdict. If the gated surfaces pass and a holdout is materially worse, that is reported, not acted on.

---

# 7. After a FAIL: allowed read-only diagnostics

A FAIL stops the slice. The following are permitted **only** as a new, separately authorized characterization slice, never as a re-run of Stage 1B:

- decomposition of the failing gate (for G1: where Threat entries were lost relative to baseline, by builder, chain, state and window);
- the section 6.2 and 6.3 reports;
- shadow re-analysis on the candidate trajectories.

No change to TE-1, projection v2, commitment tiers or any gate follows from a FAIL under this document. Any change requires a new preregistration.

---

# 8. Predictions (recorded before any implementation)

- **G1 is the gate I am least able to predict, and the one most likely to fail.** Two mechanisms push opposite ways.
  - *Against:* TE-1 declines the 200 of 356 A-PROD builds that had no value at the baseline's states and resets about 2,150 Top windows. Fewer builds mean fewer Ready states.
  - *For:* resets pass initiative to a Bottom that spends stamina on each initiation, and every A-PROD conversion happened against an Exhausted Bottom (Stage 1A-v2: 78 of 78). More Bottom windows may mean more drained Bottoms by the time a chain completes.

  The shadow evidence cannot separate these, because it holds the baseline's trajectory fixed.
- **G5's first-Exhausted floor is a second real risk.** The floor (≥ 50 s) equals the baseline median (50 s). The shadow shows Bottom choosing HIGH on most terminal-tier windows (A-PROD 127 of 127; E-PROD 42: 88 HIGH, 79 LOW). HIGH costs 12 against MEDIUM's 7, so HIGH-heavy Bottom play can pull the first Exhausted entry earlier and fail G5, and also push G6 toward its 50% cap.
- **G1 and G5 pull against each other.** The shadow also shows tier C/D choices overwhelmingly LOW, which lowers drain and the Exhausted share. Less drain is what G5 wants and what the conversion mechanism above may not.
- **G4 is expected to pass** by a wide margin: setup_future was 0 on all 1,964 PROTECT builder decisions, so TE-1 should not choose builders there, and the reason-independent count should be near 0.
- **G2 and G3 are expected to pass** (baseline Tap ≤ 9; HIGH on Bottom terminal windows should raise escape probability).
- **O-3 fidelity:** expected to be high but not exact; no number is predicted.
- **P1-P6** are expected to pass if the wiring is default-off by construction.

---

# 9. Decisions and review rulings

The user's rulings on the decisions proposed at `0fcae3e`:

| # | Decision | Ruling |
|---|---|---|
| B1 | Both initiators use TE-1 under `TACTICAL_V1`; unsupported configurations rejected, no fallback (2.1) | **APPROVED** |
| B2 | O-3 under `TACTICAL_V1`: opponent windows run TE-1 with the frozen projection as the depth-1 surrogate; fidelity reported, not gated (2.2, 6.3) | **APPROVED** |
| B3 | G4 loophole guard (5.2) | **APPROVED WITH CORRECTION.** The guard is the reason-independent completed-chain builder-attempt count, not the count of successful setup advances. It is disclosed as a **pre-measurement amendment to G4's measurement definition**. The historical counter is still reported. Floor and baseline unchanged |
| B4 | G6 denominator excludes precedence-forced commitments and pools both sides (5.3) | **APPROVED.** Frozen before any candidate result |
| B5 | G1 and G3 pooled sums taken per stalling mode (4.2) | **APPROVED** |
| B6 | Run the six holdout surfaces once; report ratios only (6.4) | **APPROVED** |
| B7 | Setup calibration and O-3 fidelity under `TACTICAL_V1` are reported, not gated (6.3) | **APPROVED** |
| B8 | Inertness replay is a mandatory integrity check (5.1) | **APPROVED WITH CLARIFICATION.** The replay tape covers every `policy.choose` call in order, including collector counterfactual calls, with executed and counterfactual calls distinguishable |

**Wording fixes required by the review, applied here:**
- "byte-identical" replaced by behaviorally and RNG-identical (2.1);
- authorization language clarified (Status): approval makes the document binding and does not authorize implementation or measurement;
- G4 is described as carrying a measurement amendment, not as unchanged.

## 9.1 Pre-implementation contract clarification: PROTECT probe and v0.4a

**The conflict (found before any implementation was committed).** Section 2.1 says `TACTICAL_V1` requires v0.4a semantics and raises `ValueError` otherwise. Sections 3 and 4.2 score G4 on the frozen PROTECT probe, whose kwargs run with v0.4a **off**. Read literally, `TACTICAL_V1` would raise on G4's only surface, and G4 could never be measured. The user ruled a hard stop and asked for this clarification before implementation resumes.

**The rule.**
- `TACTICAL_V1` still requires v0.4a commitment semantics, as written in section 2.1.
- **One exception:** the exact frozen G4 PROTECT probe is admitted with v0.4a off. "Exact" means every keyword argument of the batch call equals the frozen probe, apart from `initiator_policy=TACTICAL_V1`. The frozen probe is `diagnostics/setup_policy.py: historical_protect_probe_kwargs()` at `3494fa5`:

  ```text
  matches=100, base_seed=42,
  top_behavior=PRESSURE, bottom_behavior=PROTECT, commitment=MEDIUM,
  initial_clock=300, starting_axis=1.50, interval_seconds=5,
  top_stamina=100, bottom_stamina=100,
  bottom_behavior_mode=FIXED, bottom_responder_mode=INFORMED,
  enable_v02_setup=True, enable_v03_submissions=True
  ```

  Every other batch option keeps its default: v0.3b stalling off, v0.4a off, v0.4b Recognition off, response commitment `FIXED_MEDIUM`, Rule 1 waiver off, settlement rules and supplemental hold off, recovery initiation `CURRENT`, Top behavior mode `FIXED`, post-clear handoff `NONE`, shadow stalling off, and every `measure_*` flag off.
- **Every other configuration with v0.4a off raises `ValueError`**, including the PROTECT probe with any single argument changed (seed, match count, behavior, responder, clock, stamina or any other flag). There is no fallback to `ESCAPE_FIRST`. Tests must pin both sides of this: the exact envelope is accepted, and a perturbation of each argument is rejected.

**Why this envelope is admissible.** Projection v2 and TE-1 were already qualified on exactly this configuration in Stage 1A-v2 (`750ffe8`): C4 1,964 / 1,964, C5 exact (Σp 0.00, observed 0), C0 5,696 / 5,696, and O-3 2,848 / 2,848. With v0.4a off, the engine applies no commitment grade transform and still charges the initiator's funded commitment cost. The frozen evaluator models it the same way (`tactical_evaluator.resolve` returns the post-exhaustion grade, and `evaluate` costs the funded commitment). The exception admits a configuration that is already modeled and qualified. It adds nothing new.

**What this is not.**
- It is not a gate or threshold change. The G4 baseline (1,768), the floor (≤ 884), the G4 measurement amendment (section 5.2), the PROTECT surface and its seed are unchanged, and so are P1-P6, G1-G6, every other surface, baseline, seed and floor.
- It is not a broadening of supported configurations. Section 2.1 still rejects everything it rejected, apart from this one already-qualified envelope.
- It does not change TE-1, projection v2, precedence, D3-B, production policy or any gameplay default.
- It does not authorize implementation or any run. Stage 1B implementation needs a fresh authorization against the SHA that carries this text, and the candidate measurement needs its own separate authorization after that.

---

# 10. Stage 1B deliverables and hard-stop rules (when authorized)

Implementation of section 2; the candidate run (once); scoring of P1-P6 and G1-G6 and the section 5 checks; the section 6 reports; a result document and evidence (summary plus per-event records, pinned by tests); exact-head CI on 3.11 and 3.13; then **HARD STOP** with DESIGN PASS / FAIL / OPEN.

**Stage 1B itself is NOT authorized by this document.** Its implementation and the candidate run each require a separate explicit authorization.

**Not authorized by this document:**
- any implementation or wiring;
- any candidate run;
- any change to C1-C5, C3-H, P1-P6, G1-G6 or any threshold (the G4 measurement amendment of 5.2 is the only measurement-definition change, and it leaves the floor unchanged);
- production-policy changes;
- Stage 2 (promotion) or Stage 3 (debt-3 re-evaluation);
- merge, squash or force-push.

**HARD STOP.**
