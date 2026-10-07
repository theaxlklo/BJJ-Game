# Joint Tactical Evaluator — Stage 1B Result (candidate run under real TACTICAL_V1 execution)

## Status

**STAGE 1B = DESIGN FAIL (G1).**

| P1 | P2 | P3 | P4 | P5 | P6 | G1 | G2 | G3 | G4 | G5 | G6 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| exact-head CI | PASS | PASS | PASS | PASS | exact-head CI | **FAIL** | PASS | PASS | PASS | PASS | PASS |

The evidence is valid. Every integrity check of section 5 holds on all 7 gated surfaces, every frozen ESCAPE_FIRST baseline reproduces exactly, and the G4 amendment premise holds on every baseline run. G1 fails with valid evidence, so by section 4.3 the result is **DESIGN FAIL**, whatever P1 and P6 return. P1 and P6 are scored by exact-head CI on this commit and are recorded in the checkpoint report.

**HARD STOP.** No tuning, no gate change, no re-run under this preregistration, no wiring change. Stage 1A (`2d2778d`, FAIL) and Stage 1A-v2 (`750ffe8`, PASS) stay historical and unchanged. No production promotion, no merge.

```text
preregistration (binding):  ae786af483d109785f172cb10a17170ece2ed241
                            docs/TACTICAL_EVALUATOR_STAGE1B_PREREGISTRATION.md
implementation (qualified): fd19dd0f6220753d4e135e98db2abd1f03963a3b  (CI 37653740212)
branch:                     review/tactical-evaluator-stage1b
measurement driver:         src/bjj_game/diagnostics/tactical_evaluator_stage1b.py
                            sha256 1d556526799da15e8f5c3e3b7ab8f051c1b7b7180c413bb52591a21f49dac96f
evidence (summary):         docs/evidence/tactical_evaluator_stage1b.json
evidence (per event):       docs/evidence/tactical_evaluator_stage1b_records.json.gz
tests:                      tests/test_tactical_evaluator_stage1b_driver.py   (integrity checks detect faults)
                            tests/test_tactical_evaluator_stage1b_evidence.py (evidence pin)
frozen digest:              3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

The authoritative measurement was run **once**, on 2026-10-07 from 17:44 to 17:53 UTC. Python 3.13.15 on Windows was used on the working tree of this commit, with each surface in its own fresh interpreter:

```bash
PYTHONPATH=src python3.13 -m bjj_game.diagnostics.tactical_evaluator_stage1b --jobs 13
```

It ran after the Stage 1B implementation and driver tests (63), both checkers and the canonical UTF-8/LF digest had passed.

**Disclosed execution history:**
- Before the authoritative run, the driver was smoke-tested only on synthetic fixtures (seeds 910000 and above, 1-2 matches, clocks of 120-200 s), to check instrumentation. Those runs are not evidence and their outcomes were not read.
- After the run, one integrity cross-check was added that the preregistration does not require: a plain, uninstrumented `run_batch(initiator_policy=TACTICAL_V1)` on each of the 7 gated surfaces. Outcomes, summary fields and the G6 tally were identical to the recorded candidate runs on all 7. It guards against an observer artifact; it is not a re-run and changes nothing.
- Nothing was re-run, tuned or replaced.

---

# 1. Integrity (section 5; any failure would be OPEN)

| Check | Result |
|---|---|
| 5.4 ESCAPE_FIRST baseline on this head vs the section 3 table | **exact** on all 7 gated surfaces |
| 5.2 premise: reason-independent count = historical counter on every baseline run | **equal** on all 7 (A-PROD 312, B-PROD 880, E-PROD 844 / 841, PROTECT 1,768) |
| P4a evaluator RNG draws (every `policy.choose`, including projection-v2 sandboxes and the O-3 surrogate) | **0** on all 13 runs |
| P4b second candidate run: summary, gameplay signatures, replay tape and exchanges, every record, RNG digest | **identical** on all 7 |
| P4c inertness replay from the tape (executed and counterfactual calls, flag-checked) | **identical** summary, signatures, tape and RNG digest on all 7; no desynchronization |
| Uninstrumented candidate run (disclosed cross-check) | identical on all 7 |
| Historical counter ≤ reason-independent count under TACTICAL_V1 | holds on all 13 |

The driver tests show these checks can fail. A flipped `executed` flag and a truncated tape each raise a replay desynchronization, an evaluator RNG draw is counted, and inconsistent P3 counts are rejected.

---

# 2. Preservation gates

| Gate | Result | Evidence |
|---|---|---|
| P1 | exact-head CI | Locally: all 7 ESCAPE_FIRST baselines exact, digest exact under canonical UTF-8/LF, both checkers PASS. The full suite, including the Stage 1A and 1A-v2 evidence pins, is scored on exact-head CI (3.11, 3.13). |
| P2 | **PASS** | `git diff ae786af` shows no change under engine, domain, positions, handoff, production, recovery, stamina-economy policy or the frozen evaluator. |
| P3 | **PASS** | 0 Bottom RECOVER Exhausted initiations above LOW (E-PROD 42: 367 and 366, E-PROD 142: 416 and 416, all LOW). Each LOCKOUT_HOLD decision equals one `recovery_hold_history` entry, one executed hold and one counterfactual tape entry (E-PROD 42: 25 and 23; 142: 19 and 18). 0 attempts in a LOCKOUT_HOLD window. `handoff_policy.py` unchanged. |
| P4 | **PASS** | Section 1. |
| P5 | **PASS** | 0 violations over every TE-1 call, executed and counterfactual (for example A-PROD 5,900, E-PROD 142 OFF 1,815), checked by an independent re-derivation of the guard and the cheapest-qualifying rule from the captured candidate values. |
| P6 | exact-head CI | This commit. |

---

# 3. Design gates (scored exactly as preregistered)

| Surface | Threat matches | Tap | Escapes | Timeouts | Top builds (historical / reason-independent) |
|---|---|---|---|---|---|
| A-PROD | **0** (78) | 0 (0) | 0 (22) | 100 (78) | 0 / 0 (312) |
| B-PROD | 27 (59) | 8 (9) | 73 (12) | 19 (79) | 130 / 130 (880) |
| E-PROD 42 OFF / ON | 25 / 25 (61) | 3 / 3 (5) | 74 / 75 (30) | 23 / 22 (65) | 130 / 130 (844) |
| E-PROD 142 OFF / ON | 28 / 28 (57) | 5 / 5 (4) | 69 / 70 (31) | 26 / 25 (65) | 152 / 152 (841) |
| PROTECT probe | 0 (0) | 0 (0) | 0 (2) | 100 (98) | 0 / 0 (1,768) |

Baselines in parentheses. One E-PROD ON match on each seed ended in a Reversal, counted as an escape.

## G1 — submission access: **FAIL**

| Measure | Value | Floor |
|---|---|---|
| A-PROD Threat matches | **0** | ≥ 63 |
| B + E-42 + E-142, stalling OFF | **80** | ≥ 142 |
| B + E-42 + E-142, stalling ON | **80** | ≥ 142 |

Both parts fail. On A-PROD, TE-1 chose **RESET at every window on both sides**: 3,000 Top and 2,900 Bottom resets, 0 exchanges, every match a timeout. The PROTECT probe shows the same pattern.

## G2 — Tap ≤ 20 on every surface: **PASS**

The maximum is 8 (B-PROD).

## G3 — escapes: **PASS**

E-PROD pooled escapes are 143 with stalling OFF and 145 with stalling ON, against a floor of 49. B-PROD has 73, against a floor of 10.

## G4 — PROTECT churn (reason-independent count ≤ 884): **PASS**

The reason-independent count is 0, and the historical counter is also 0. TE-1 never chose a builder on the PROTECT probe.

## G5 — pacing guard: **PASS**

| Run | Bottom first-Exhausted median (≥ 50 s) | Bottom Exhausted share (≤ 80%) |
|---|---|---|
| E-PROD 42 OFF | 75 s | 62.43% (5,110 / 8,185 s) |
| E-PROD 42 ON | 75 s | 62.44% (5,070 / 8,120 s) |
| E-PROD 142 OFF | 75 s | 62.25% (5,730 / 9,205 s) |
| E-PROD 142 ON | 75 s | 62.06% (5,685 / 9,160 s) |

The share is computed by the unchanged late-recovery observer, and the ≤ 80% test is applied on exact integers. Sandbox steps are routed past the observer. The observer's unexplained Bottom delta is 0 on all four runs.

## G6 — HIGH share among TE-1-chosen initiations (≤ 50%): **PASS**

| Stalling | TE-1-chosen | HIGH | Share | Excluded (forced) |
|---|---|---|---|---|
| OFF | 1,078 | 243 | 22.5% | LOW_WHILE_EXHAUSTED 758, D3-B token 25 |
| ON | 1,072 | 243 | 22.7% | LOW_WHILE_EXHAUSTED 758, D3-B token 24 |

By side, Bottom chose HIGH on 201 of 303 exchanges with stalling OFF, almost all of them terminal-tier escapes. Top chose HIGH on 42 of 775.

---

# 4. Reported (not gated)

## 4.1 Decisions and commitments (gated surfaces, executed windows)

| Surface | Top tiers (terminal / progress / setup / reset) | Bottom tiers (terminal / setup / position / reset) |
|---|---|---|
| A-PROD | 0 / 0 / 0 / 3,000 | 0 / 0 / 0 / 2,900 |
| B-PROD | 9 / 151 / 203 / 359 | 100 / 17 / 4 / 574 |
| E-PROD 42 OFF | 6 / 151 / 203 / 460 | 102 / 34 / 384 / 249 |
| E-PROD 142 OFF | 13 / 181 / 221 / 508 | 103 / 28 / 435 / 307 |
| PROTECT probe | 0 / 0 / 0 / 3,000 | 0 / 0 / 0 / 2,900 |

- **Commitments:** Top setup was always LOW, and Top progress was mostly MEDIUM (122-156 per surface, with 20-22 HIGH). Bottom terminal was HIGH on 100-101 per surface. Bottom position was LOW, with at most 1 MEDIUM.
- **No Top position-tier choice** occurred on any surface.
- **Setup per Threat entry:** Top setup-tier decisions per Threat match were 7.5 on B-PROD, 8.1 on E-PROD 42 and 7.9 on E-PROD 142.
- **Forgone better position** at setup choices was 1 on B-PROD, 17 on E-PROD 42 and 11-13 on E-PROD 142.
- **Mean time to first Top Ready** was 15 s on every surface where Ready was reached.

## 4.2 Calibration under TACTICAL_V1 (section 6.3)

- **Per component (C2 style, at the executed value).** Terminal, progress and setup-advance are within ±3σ on every surface. On B-PROD, predicted vs realized was 73.6 vs 81 for terminal, 82.3 vs 74 for progress, and 210.0 vs 208 for setup-advance.
- **Setup calibration over every chain begun.** Every surface is within ±3σ. Σ setup_future vs Threat entries was 29.6 vs 27 on B-PROD, 27.5 vs 25 on E-PROD 42, and 29.4 vs 28 on E-PROD 142.
- **Ready conversion at Top Ready uses.** Predicted vs actual was 27.5 vs 27 on B-PROD, 25.4 vs 25 on E-PROD 42, and 28.8 vs 28 on E-PROD 142.
- **Projection horizon.** Every closed chain's real horizon equalled 2r on every surface. Free initiative windows were 0-3 per run.

## 4.3 O-3 surrogate fidelity (depth-1 approximation)

The surrogate's decision equalled the real decision exactly on every terminal, progress and reset window, and on almost every position window. It diverged mainly at **setup**:

| Surface | Top setup windows: action exact | Bottom setup windows: action exact |
|---|---|---|
| B-PROD | 103 / 203 | 0 / 17 |
| E-PROD 42 OFF | 103 / 203 | 0 / 34 |
| E-PROD 142 OFF | 120 / 221 | 1 / 28 |

This is where the surrogate's frozen single-chain projection is expected to differ from projection v2.

## 4.4 Holdouts (run once; ratios to the committed ESCAPE_FIRST baselines; no verdict)

| Holdout | Threat | Tap | Escapes | Timeouts | Top builds |
|---|---|---|---|---|---|
| A-PROD 4242 | 0 / 77 | 0 / 0 | 0 / 23 | 100 / 77 | 0 / 308 |
| B-PROD 4242 | 34 / 49 | 15 / 8 | 65 / 21 | 20 / 71 | 152 / 824 |
| E-PROD 4242 OFF / ON | 31 / 49 | 10 / 2 | 65, 66 / 42 | 25, 24 / 56 | 152 / 790 |
| E-PROD 4342 OFF / ON | 28 / 57 | 7 / 1 | 68, 69 / 42 | 25, 24 / 57 | 162 / 725 |

The holdouts repeat the gated pattern. A-PROD collapses to all-RESET. Elsewhere Threat matches fall to about 50-70% of baseline and escapes rise sharply. The E-PROD holdouts' Bottom Exhausted share is 57-58%, and the HIGH share is 19%.

## 4.5 Against the section 8 predictions

- **G1 failed, as predicted to be the main risk.** The "against" mechanism dominated in its extreme form. On A-PROD and PROTECT, TE-1 found no positive terminal, progress, setup or position value at the opening state for either side, so every window was a RESET and the state never left it.
- **G5 passed with margin, against the stated risk.** The first-Exhausted median moved from 50 s to 75 s, and the share fell from about 79% to about 62%.
- **G4 passed as predicted.**
- **G6 passed.** Bottom's HIGH use is concentrated on terminal windows, as predicted.

Any decomposition of the G1 failure beyond these reported measures needs the separately authorized read-only slice of section 7.

---

# 5. Measurement interpretations fixed before the run (disclosed)

- **G1 and G3 pooling.** Pooling is per stalling mode, and the B-PROD run counts in both modes (B5).
- **G5 share.** The share is Bottom Exhausted seconds over total match seconds, from the late-recovery observer's per-match records, tested exactly as `5 · exhausted ≤ 4 · total`.
- **G6.** The tally comes from the implementation's exchange records (`g6_tally`), with E-PROD 42 and 142 pooled per stalling mode and precedence-forced exchanges excluded (B4).
- **P5.** It is checked at every `policy.choose` call, counterfactual calls included.
- **Section 6 reports.** Chains are the reason-independent chains of section 5.2. The real horizon counts executed windows and holds from a chain's first builder to its Ready use, against 2r. A free initiative window is a non-empty return of `consume_free_initiative_window`.

---

# 6. Hard stop

Stage 1B is complete: **DESIGN FAIL (G1)**, with valid evidence.

Not done and not authorized:
- any change to TE-1, projection v2, commitments, precedence, gates or thresholds;
- any re-run of Stage 1B;
- the section 7 read-only diagnostics, which need their own separately authorized slice;
- Stage 2 promotion, Stage 3, production-policy changes, merge or squash.

**HARD STOP.**
