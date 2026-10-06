# BJJ-Game — Plan and Status

_Last updated: 2026-10-05. A living overview of where the project stands and what is still missing before the engine is final and frontend work can start._

The authoritative details always live in the per-slice DoD, preregistration, measurement, result and promotion documents linked below. If anything here conflicts with them, they win.

---

## 1. The goal

A **deterministic tactical BJJ roguelike/simulation**. The current engine scope is **Mount-v0**: Top-vs-Bottom exchanges with stamina, commitment levels, setup/Ready, the Americana submission track, v0.3b stalling, and v0.4b Recognition.

Before frontend work starts, every remaining engine/design debt must be either **closed** or **explicitly deferred**.

## 2. How work is done (change control)

Every gameplay or mechanics change follows this sequence:

```text
branch -> freeze DoD / preregistration -> HARD STOP -> review
-> explicit implementation authorization -> implement -> evidence
-> exact-head qualification -> review exact SHA -> explicit merge authorization
-> merge -> final-main verification -> HARD STOP
```

- Criteria are frozen before measurement and never edited afterwards to make gates pass. Failed measurements stay on record.
- Unit/checker PASS is not the same thing as a design-gate PASS or OPEN.
- Required qualification is exact-head GitHub CI on **Python 3.11 and 3.13** with the unit/regression suite, frozen enumeration digest, semantic checker, and legacy entry point. Local runs are supplementary.
- When frozen evidence documents cite exact checkpoint SHAs, the merge strategy must preserve those commits in reachable history unless a different method is explicitly reviewed and authorized.
- No gameplay change goes directly to `main`.
- Frozen Mount-v0 enumeration digest: `3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2`.

## 3. Current repository state

| Item | SHA / PR | State |
|---|---|---|
| R1 base main | `1e2b5e3ffbf6f8a8051775d48c20063cc3abdedd` | stable; CI `37374129845` PASS |
| Stamina production adoption | PR #10, head `ee6cb6fcebb105e31224bead48a302811b27b59a`, merge `2149925e684d49cea66915495efffec496ef54a5` | **MERGED** |
| D3-B production promotion | PR #11, head `0aa23db5089476982eb6eaf94d91b316d857cee1`, merge `b59fc7f046d5420e3edc05f3300ad9699473776d` | **MERGED** |
| D3-B final-main qualification (`b59fc7f`) | CI `37370017411` | **PASS** on Python 3.11 and 3.13; 504 tests, 1 skipped; digest exact |
| LOW -> MEDIUM handoff oscillation | D3-B design + promotion lineage | **CLOSED IN PRODUCTION** |
| R1 — response commitment / provisional-hold affordability | branch `review/r1-hold-inclusive-affordability`; DoD `a2e2887` (CI `37382027293`) | **CLOSED BY CHARACTERIZATION — no gameplay change** |

The review branches and historical checkpoint commits are intentionally preserved. The final integration kept the full evidence chain reachable from `main`.

## 4. Completed: stamina production-policy adoption

The original production-adoption slice established the baseline policy:

```text
Rule 1 ON   (UNFUNDED initiator cannot drain the responder)
Rule 2 OFF  (deferred)
Bottom RECOVER + Exhausted initiation = LOW
After an Exhausted clear = baseline MEDIUM
```

Key checkpoints:

| Stage | SHA | Result |
|---|---|---|
| Frozen DoD | `6068bc9` | reviewed |
| Stage 1A | `9a70335` | read-only A9 observer + inertness |
| Stage 1B | `985002d` | A9 preregistration |
| Stage 2 | `17e2e68` | Gates A-F, H PASS; A1-A10 CONFIRMED |
| Canonical promotion + Gate G | `ee6cb6f` | Gates A-H PASS: **ADOPTED** |
| Merge to `main` | `2149925` | PR #10 merged with a merge commit |

Historical Gate-G behavior is now frozen separately as:

`GATE_G_STAMINA_RECOVERY_POLICY`

so the original adoption evidence remains reproducible after D3-B promotion.

Docs: `docs/STAMINA_PRODUCTION_POLICY_ADOPTION_*`.

## 5. Completed: debt 1 — LOW -> MEDIUM handoff oscillation

### 5.1 Original problem

D1 characterization (`cdb04a0`) showed that after Bottom cleared Exhausted at 35, the adopted handoff commonly followed:

```text
35 -> MEDIUM spend -> 28
ESCAPE drain -> 27 -> 26
next MEDIUM -> 19 -> Exhausted
```

About 93% of admissible clears re-entered Exhausted at exactly +10 s. The earlier A9 result was only a relative gate and did not establish absolute stability.

### 5.2 Candidate history

The failed and superseded candidates remain historical evidence:

| Candidate | Key checkpoint | Status |
|---|---|---|
| D2 v1-v1d | `6230959` / `f624db2` / `f30ace9` / `8dcaabb` | preregistered/reviewed, not selected for measurement |
| D2 v1e | prereg `c4a9c33`, impl `d00c48e`, result `fe229cb` | **DESIGN FAIL**: escapes 17 < 25; timeouts 78 > 70 |
| D2 v1f | `88a01e9` | preregistered only; never implemented or run |
| D3-A | `2fb24d5` | preregistered, superseded before implementation/run |
| D3-B | prereg `dc4fc16`, implementation `f92dc6e`, result `1b96ffc` | **DESIGN PASS** |
| D3-B promotion | prereg `1eb0a30`, implementation `fdfc39e`, qualified head `0aa23db` | **PROMOTION PASS** |
| Production integration | PR #11 -> `b59fc7f` | **MERGED; debt closed** |

### 5.3 Current canonical behavior

`PRODUCTION_STAMINA_RECOVERY_POLICY` now selects:

```text
Rule 1 ON
Rule 2 OFF
LOW while Exhausted under Bottom RECOVER

After the first Exhausted clear:
- arm D3-B
- each armed Exhausted episode gets exactly one Exhausted LOW token decision
- after that token, Bottom initiation is locked out with LOCKOUT_HOLD
- lockout ends only when the existing Exhausted latch clears
- clear-window / ordinary non-Exhausted play returns to baseline MEDIUM
```

Raw `MountMatch` and batch defaults remain unchanged. D3-B is selected only through the canonical RECOVER production policy. An unmeasured RECOVER configuration is rejected rather than silently falling back.

### 5.4 Frozen D3-B result

Important measured values from `1b96ffc`:

```text
original-100:
30 escapes
Half Guard 17
Open Guard 5
Reversal 8
65 timeouts
Tap 5
Bottom final median 29

seed 142:
31 escapes
65 timeouts
Tap 4

G3:
25/25 bounded-recovery successes

G6:
0 prefix mismatches
18/18 +10 s MEDIUM escapes preserved
4/4 token-window escapes preserved

G7:
5/25 affected-region Bottom escapes
```

Two values passed exactly at their floors and must remain described that way:

- P3 Bottom final median = **29**, required >=29.
- G7 = **5/25**, required >=5/25.

The result proves the frozen acceptance contract, not excess tactical margin.

Docs:

- `docs/BURST_RECOVERY_LOCKOUT_D3B_PREREGISTRATION.md`
- `docs/BURST_RECOVERY_LOCKOUT_D3B_RESULT.md`
- `docs/BURST_RECOVERY_LOCKOUT_D3B_PROMOTION_PREREGISTRATION.md`
- `docs/BURST_RECOVERY_LOCKOUT_D3B_PROMOTION_RESULT.md`

## 6. Next actions

### 6.1 Completed: R1 — response commitment / provisional-hold affordability

**R1 OUTCOME = CLOSE (closed by characterization).** Records: `docs/R1_HOLD_INCLUSIVE_AFFORDABILITY_DOD.md` (frozen at `a2e2887`) and `docs/R1_HOLD_INCLUSIVE_AFFORDABILITY_RESULT.md`.

Frozen production semantics: response commitment and the provisional Contested hold are additive. The LOW = 3 hold is charged on a best-effort basis. A responder with 0-2 stamina left pays what remains, and the Contested result is not revoked. Rule 1 still waives everything when the initiator is UNFUNDED. Rule 2 stays OFF; semantics B remains rejected (public-MATCH Threat 78/100 -> 0/100).

- H1 not implemented: provably inert on the production surfaces.
- H2 rejected for R1: it is a submission-balance change, not an affordability fix, and would alter the frozen A-PROD control (78 decisions). It may return later only as a new submission-design slice.
- Hypothesis not added; `ResponderSettlementPlan` deferred.
- The projected-burden display requirement moved to debt 7.

### 6.2 Remaining order after R1

R1 is closed. Next, in order:

1. **Late recovery / pacing (next slice; characterization first):** median first clear remains about 240 s of a 300 s match; decide whether this is intended game pacing or a separate mechanics debt.
2. **Setup-policy debt.**
3. **Initiator tactical commitment-selection policy:** player/AI choice among LOW / MEDIUM / HIGH rather than a fixed baseline.
4. **Scoring / timeout meaning** for the first playable ruleset.
5. **Final player-facing state/input contract.**
6. Resolve the player-facing meaning/visibility of non-RESET recovery holds if it is still relevant after the above slices.

## 7. Remaining engine/design debt before frontend

| # | Debt | Status |
|---|---|---|
| 1 | LOW -> MEDIUM handoff oscillation | **CLOSED IN PRODUCTION — D3-B** |
| 2 | **R1:** response commitment / provisional-hold affordability | **CLOSED BY CHARACTERIZATION** (`a2e2887`; result record) |
| 3 | Late recovery / match pacing | open |
| 4 | Setup-policy debt | open |
| 5 | Initiator tactical commitment-selection policy | open |
| 6 | Scoring / timeout meaning | open |
| 7 | Final player-facing state/input contract | open; **includes the R1 projected-burden requirement (below)** |
| 8 | Recovery-hold visibility / presentation | design consideration; resolve before exposing relevant state to players |

### Debt 7 requirement transferred from R1

The player-facing contract must expose the **response-specific projected burden** on hold-eligible response windows:

```text
response effective commitment cost
+ 3 when the selected response is predicted Contested and the
  initiator appears funded from responder-visible information
```

This is advisory and read-only. Actual engine settlement remains authoritative and may differ, because Recognition can be wrong and Rule 1 uses the true funding state. The projected burden must **never** be presented as a guaranteed actual cost.

## 8. Definition of "ready for frontend"

Frontend work may start only when:

- Debt 1 remains closed on `main`.
- Debt 2 (R1) is closed or explicitly deferred.
- Debts 3-7 are closed or explicitly deferred through their own controlled slices.
- Any player-visible recovery-hold semantics needed by the final contract are decided.
- The canonical production policy and player-facing state/input contract are stable.
- `main` is green on Python 3.11/3.13 with the frozen digest exact.

Current status: **NOT READY FOR FRONTEND.**

## 9. Resuming work

Start from final integrated `main`:

```bash
cd ~/Projects/BJJ-Game
git fetch origin
git switch main
git pull --ff-only origin main
git rev-parse HEAD
```

Expected: the latest merge commit on `main`. Every frozen checkpoint SHA cited in this document must be an ancestor of it (`git merge-base --is-ancestor <sha> HEAD`).

R1 is closed on `review/r1-hold-inclusive-affordability` (based on `1e2b5e3`; frozen DoD `a2e2887`). Merging that branch needs separate authorization. The next slice is late recovery / match-pacing characterization, starting on a fresh branch after explicit authorization.
