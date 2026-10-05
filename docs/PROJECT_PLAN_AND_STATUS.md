# BJJ-Game — Plan and Status

_Last updated: 2026-10-05. A living overview of where the project stands and what is still missing before the engine is final and frontend work can start._

The authoritative details always live in the per-slice DoD, preregistration and measurement documents linked below. If anything here conflicts with them, they win.

---

## 1. The goal

A **deterministic tactical BJJ roguelike/simulation**. The current engine scope is **Mount-v0**: Top-vs-Bottom exchanges with stamina, commitment levels, setup/Ready, the Americana submission track, v0.3b stalling, and v0.4b Recognition.

Before any frontend work, every remaining engine/design debt must be either **closed** or **explicitly deferred**.

## 2. How work is done (change control)

Every gameplay or mechanics change follows this sequence:

```text
branch -> freeze DoD -> HARD STOP -> review -> explicit authorization
-> implement -> evidence -> review exact SHA -> explicit merge authorization -> squash merge
```

- Criteria are frozen before measurement and never edited afterwards to make gates pass. Failed measurements stay on record.
- Unit/checker PASS is not the same thing as a design-gate PASS or OPEN.
- Required qualification: exact-head GitHub CI on **Python 3.11 and 3.13** (unit suite, frozen enumeration digest, semantic checker, legacy entry point). Local runs on system Python are supplementary.
- Frozen Mount-v0 enumeration digest: `3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2`.

## 3. Where things are

| Branch / PR | Head | Contents | State |
|---|---|---|---|
| `main` | `51ada9c` | everything through PR #9 (recovery-policy amendment) | stable |
| `review/stamina-production-policy-adoption-dod` / **PR #10** | `ee6cb6f` | stamina production-policy adoption | **ADOPTED, awaiting merge authorization** |
| `review/handoff-oscillation-d1` (no PR yet) | this branch | D1 characterization + D2 preregistrations + this plan | **D2 not yet authorized** |

## 4. Completed: stamina production-policy adoption (PR #10)

Canonical production policy, `bjj_game.interfaces.production_policy.PRODUCTION_STAMINA_RECOVERY_POLICY`:

```text
Rule 1 ON   (UNFUNDED initiator cannot drain the responder)
Rule 2 OFF  (deferred)
Bottom RECOVER + Exhausted initiation = LOW; after clear = baseline MEDIUM
```

It is explicit opt-in. Raw defaults are unchanged.

| Stage | SHA | Result |
|---|---|---|
| Frozen DoD | `6068bc9` | reviewed |
| Stage 1A: read-only A9 observer + inertness | `9a70335` | green |
| Stage 1B: A9 preregistration | `985002d` | N=10 s, X=0.975034786099515, M=43 |
| Stage 2: Rule1-only + LOW measurement | `17e2e68` | Gates A-F, H PASS; A1-A10 all CONFIRMED |
| Canonical promotion + Gate G | `ee6cb6f` | Gates A-H all PASS: **ADOPTED** |

Docs: `docs/STAMINA_PRODUCTION_POLICY_ADOPTION_*` (DoD, preregistration, first measurement, verification).

## 5. In progress: D1/D2, the LOW -> MEDIUM handoff oscillation (debt 1)

**Problem (D1, `cdb04a0`):** after Bottom clears Exhausted at 35, it immediately spends MEDIUM (-7). ESCAPE then drains 2 over 10 s, and the next MEDIUM re-enters Exhausted:

```text
35 -> 28 -> 27 -> 26 -> 19
```

About 93% of admissible clears re-exhaust at exactly 10 s. A9 passed only as a *relative* gate; absolute stability was never established.

**Candidate lineage (all decided before any candidate run):**

| Rev | SHA | Candidate | Outcome of review |
|---|---|---|---|
| D1 | `cdb04a0` | characterization + first proposed D2 DoD | accepted as evidence |
| v1 | `6230959` | initiation-only reserve: `stamina - cost > 25` | not selected; ledger shows a behavior-drain re-entry path |
| v1b | `f624db2` | + behavior reserve 2, fallback = forced RESET | not selected; predicted RESET spam vs criterion 5 (<=23) |
| v1c | `f30ace9` | + behavior reserve 2, fallback = non-RESET RECOVERY HOLD | not selected; predicted 26..31 LOW sawtooth, MEDIUM never returns |
| v1d | `8dcaabb` | + hold persists as a mode; only reserve-safe MEDIUM (stamina >= 35) releases it; LOW never releases | not selected; one-shot CONSERVE gives ~90 s holds, ~66/82 predicted never to release, and no gate caught it |
| v1e | `c4a9c33` (impl. `d00c48e`) | + CONSERVE on every normal advance while the mode is active (not through resolution); + post-hold return gate (criterion 16) | **measured: D2 FAIL on criterion 4** (escapes 17 < 25, timeouts 78 > 70). Stability 0/68 at 10 s, return gate 44/44. See `docs/HANDOFF_OSCILLATION_D2_V1E_RESULT.md` |
| v1f | this branch | + reserve-safe LOW inside the mode (LOW never releases; LOW-safe + no action = genuine RESET, mode stays on); persistent CONSERVE; MEDIUM-only release | **awaiting review**; criterion 4 predicted at risk (the +10 s hold remains), entry-27 cycles predicted to release late (50 s) |

**D2 acceptance contract** (criteria 1-16 in `docs/HANDOFF_OSCILLATION_D2_PREREGISTRATION_V1E.md`; 1-15 unchanged in substance since v1c, 16 new in v1e):

- Preservation: Surface A 78/1950/0, Surface B Tap 9, Rule 1 exact, Rule 2 OFF, escapes/exits/timeouts/Tap tolerances, stalling exposure, digest.
- Absolute stability: re-exhaustion **<=20% within 10 s** and **<=35% within 30 s**, with sample size >=43.
- Anti-gaming: clearing-match floors, first-clear timing, a real return to MEDIUM at the clear window (13) and after recovery hold (16: >=35 eligible first cycles, >=80% release within 40 s).
- Mandatory diagnostics: holds, passivity, reserve-model violations, v1-vs-candidate attribution.

**Important prediction already recorded for v1c:** the hold changes *how* Bottom declines an unsafe initiation, but not the stamina ledger. The same 26..31 sawtooth (+1 per 10 s, LOW at 31 back to 26) is predicted, so MEDIUM may still never return after the first hold. The gain is removing the RESET/stalling exposure. Expect the experiment to be decided by the passivity and return criteria (12-15).

**Predictions recorded for v1d:** on the traced path, Bottom holds from 26 up to 35 (+1 per 10 s, 9 holds, about 90 s), then releases to MEDIUM (35 -> 28 -> 26) and holds again. No re-exhaustion on that path. But a release needs a first clear at <=190 s, so only about 16 of 82 pooled clearing matches are predicted to ever release. Criterion 4 (escapes, timeouts) is at risk from fewer post-clear Bottom initiations, and Top-funded responder spend during the long 26-35 band is the remaining re-entry path.

**Predictions recorded for v1e:** persistent CONSERVE recovers +4 per 10 s. The traced path is a 130 s period of 4 cycles (entry 26/29/28/27, release 38/37/36/35, 20-30 s from entry to release), so recovery is cyclic, not a cure. Criterion 16 is expected to pass on the traced path. Its failure sources are Top-funded responder spend at 26-30 and terminal events during the mode. About 47 pooled matches have a first clear early enough to be eligible (floor 35). CONSERVE also drifts the axis faster toward Top during advances (+0.75 instead of +0.50 per interval). That is inherent to the engine and reported, not changed.

## 6. What is missing to finalize

### Next actions (in order)

1. **Review the D3-B promotion result** (`docs/BURST_RECOVERY_LOCKOUT_D3B_PROMOTION_RESULT.md`, branch `review/d3b-production-promotion`). **D3-B PROMOTION RESULT = PASS** (PG1-PG11): `PRODUCTION_STAMINA_RECOVERY_POLICY` now selects D3-B on RECOVER and reproduces the measured D3-B (`1b96ffc`) exactly; the Gate-G policy is frozen as `GATE_G_STAMINA_RECOVERY_POLICY`. D3-B's P3 median 29 and G7 5/25 remain exactly at their floors. Nothing merged; PR #10 stays open at `ee6cb6f`; no frontend wiring. Decide what, if anything, is authorized next (e.g. merge strategy for PR #10 and the promotion branch).
2. **D2 implementation + measurement** (only after explicit authorization):
   - implement the v1e diagnostic mode and `MountMatch.recovery_hold()` (opt-in);
   - run seeds 42 and 142, OFF + shadow and ON, plus adopted controls;
   - score criteria 1-16, record the results document, CI on 3.11/3.13, HARD STOP.
3. **D2 outcome:**
   - PASS -> a separate authorization to integrate into the canonical production policy;
   - FAIL/OPEN -> record it, no tuning, and decide the next candidate or an explicit deferral.
4. **PR #10 merge decision:** squash-merge the adoption checkpoint `ee6cb6f` into `main` when authorized. This is independent of D2 by design.

### Remaining engine/design debt before frontend

| # | Debt | Status |
|---|---|---|
| 1 | LOW -> MEDIUM handoff oscillation | **D2 in preregistration** (this branch) |
| 2 | **R1:** Rule 2 response + provisional-hold double charge (179 cases on E-PROD); Rule 2 redesign vs permanent deferral | open; not started (a separate slice after D2) |
| 3 | Late recovery: median first clear at 240 s of 300 s; fewer escapes and more timeouts than LOW+BOTH | open; partly addressed by D2 criteria |
| 4 | Setup-policy debt | open |
| 5 | Initiator tactical commitment-selection policy | open |
| 6 | Scoring / timeout meaning for the first playable ruleset | open |
| 7 | Final player-facing state/input contract | open |
| 8 | v0.3b stalling visibility of non-RESET holds (raised by v1c, kept by v1d) | design consideration; decide if a hold candidate is ever made player-facing |

### Definition of "ready for frontend"

- PR #10 merged.
- Debt 1 closed (D2 PASS and integrated) or explicitly deferred.
- Debt 2 (R1) closed or explicitly deferred.
- Debts 4-7 closed or explicitly deferred, each through its own controlled slice.
- `main` green on Python 3.11/3.13, with the frozen digest exact.

## 7. Resuming work (checklist)

```bash
cd ~/Projects/BJJ-Game
git fetch origin
git checkout review/handoff-oscillation-d1
git log --oneline -6
PYTHONPATH=src python3 -m unittest discover -s tests
```

Then read `docs/HANDOFF_OSCILLATION_D2_PREREGISTRATION_V1E.md` and make the step-1 decision above.
