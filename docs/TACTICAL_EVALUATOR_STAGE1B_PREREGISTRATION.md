# Joint Tactical Evaluator — Stage 1B Preregistration (candidate run under real TACTICAL_V1 execution)

## Status

**PROPOSED PREREGISTRATION — DOCUMENTATION ONLY — NOT BINDING — HARD STOP FOR REVIEW.**

Nothing is implemented or run. This document freezes how Stage 1B will be scored **before any wiring**. It becomes binding only after the user reviews this exact SHA, **resolves the decisions in section 9**, and explicitly authorizes Stage 1B. Authorization of this document is not authorization of implementation; Stage 1B is authorized as its own step.

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

**P1-P6 and G1-G6 keep their frozen definitions, surfaces, baselines and floors. No gate or threshold changes.** This document adds no gate. It adds only measurement definitions, integrity checks, reported (not gated) measures, and decision rules that 4e61bad left implicit, each marked in section 9 where it needs a ruling.

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

- The default (`ESCAPE_FIRST`) path must be **byte-identical** to today: same code path, same RNG draws, same summaries. This is P1, and it includes every existing pinned surface and both the Stage 1A and Stage 1A-v2 evidence pins.
- `TACTICAL_V1` is selected only by the explicit option. It requires the configuration of 4e61bad (v0.2 setup, v0.3a submissions, v0.4a semantics, informed Bottom responder) and raises `ValueError` on any configuration projection v2 does not model (for example handoff modes other than `NONE` and D3-B). There is **no silent fallback to `ESCAPE_FIRST`**.
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
- Threat matches = `summary.matches_reached_submission_threat`; Tap = outcome `TAP — Americana`; timeouts = outcome `TIMEOUT — Mount retained`; escapes = matches − Tap − timeouts; Top completed builds = `summary.top_completed_setup_build_count` (as in `diagnostics/tactical_evaluator.py` baseline reproduction).
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
| G4 | PROTECT Top completed builds **≤ 884** | **Both** the frozen counter and the engine-derived count (section 5.2) must be ≤ 884 |
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

After the candidate run, re-run each gated surface with a **replay policy** that returns the recorded TE-1 decisions (action and requested commitment, in order) **without evaluating anything**. The summary, per-match gameplay signatures and RNG digest must be identical to the candidate run. This proves that the evaluator has no side effect on the match, the controller or the RNG under real execution. The evaluator-free baseline comparison of Stage 1A no longer applies, because the gameplay legitimately differs.

## 5.2 G4 guard against a labeling loophole

The frozen counter credits a Top build only when the decision reason is `"setup"` (`batch.py`: `pending_setup_builds` is incremented only then). A builder chosen through the position tier (reason `position`) would advance the setup tier without being counted, so the frozen counter alone could understate churn under a new policy.

Therefore G4 is also computed **from the engine**: the number of Top builder exchanges that advanced the setup state (`setup_change_history`) and belong to chains closed by a Ready use (the Stage 1A C3 chain definition). Both counts must be ≤ 884. This tightens measurement; it does not change the floor. It is flagged for ruling as decision B3.

## 5.3 G6 denominator

"TE-1-chosen initiations" = every initiator **exchange** (not resets or holds) on the E-PROD 42 and 142 runs of one stalling mode, **both sides pooled**, whose commitment TE-1 selected. Exchanges whose commitment was **forced by precedence** (LOW while Exhausted in a Bottom RECOVER window, and the D3-B token path) are excluded from the denominator. The numerator is requested commitment HIGH. Excluding forced LOW exchanges is the stricter reading (the share is higher). The count of excluded exchanges is reported. Flagged as decision B4.

## 5.4 Baseline reproduction

The ESCAPE_FIRST baseline is re-run on the head under test and must reproduce the section 3 table exactly (as in Stage 1A and 1A-v2) before any candidate comparison is read.

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
- **G4 is expected to pass** by a wide margin: setup_future was 0 on all 1,964 PROTECT builder decisions, so TE-1 should not build there, and the engine-derived count should be near 0.
- **G2 and G3 are expected to pass** (baseline Tap ≤ 9; HIGH on Bottom terminal windows should raise escape probability).
- **O-3 fidelity:** expected to be high but not exact; no number is predicted.
- **P1-P6** are expected to pass if the wiring is default-off by construction.

---

# 9. Decisions required at review

| # | Decision | Recommendation |
|---|---|---|
| B1 | Both initiators use TE-1 under `TACTICAL_V1`, with unsupported configurations rejected and no fallback (2.1) | Yes (4e61bad scope) |
| B2 | O-3 under `TACTICAL_V1`: opponent windows run TE-1 with the frozen projection as the depth-1 surrogate; fidelity reported, not gated (2.2, 6.3) | Yes (D1 as approved) |
| B3 | G4 scored on both the frozen counter and the engine-derived count (5.2). This is a measurement guard, not a floor change | **Yes** |
| B4 | G6 denominator excludes precedence-forced commitments and pools both sides (5.3) | **Yes** (stricter) |
| B5 | G1 and G3 pooled sums taken per stalling mode (4.2) | Yes (4e61bad: each E-PROD gate must pass in both modes) |
| B6 | Run the six holdout surfaces once and report ratios only (6.4) | Yes (no verdict, so no new gate and no new risk of a gate change) |
| B7 | Setup calibration and O-3 fidelity under `TACTICAL_V1` are reported, not gated (6.3) | Yes. Gating them would add gates after seeing Stage 1A-v2 |
| B8 | Inertness replay (5.1) is a mandatory integrity check | **Yes** |

---

# 10. Stage 1B deliverables and hard-stop rules (when authorized)

Implementation of section 2; the candidate run (once); scoring of P1-P6 and G1-G6 and the section 5 checks; the section 6 reports; a result document and evidence (summary plus per-event records, pinned by tests); exact-head CI on 3.11 and 3.13; then **HARD STOP** with DESIGN PASS / FAIL / OPEN.

**Not authorized by this document:**
- any implementation or wiring;
- any candidate run;
- any change to C1-C5, C3-H, P1-P6, G1-G6 or any threshold;
- production-policy changes;
- Stage 2 (promotion) or Stage 3 (debt-3 re-evaluation);
- merge, squash or force-push.

**HARD STOP.**
