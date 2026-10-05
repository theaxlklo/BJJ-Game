# D3-B Production Promotion — Preregistration and Definition of Done

## Status

**PROPOSED PROMOTION PREREGISTRATION — FROZEN AT ITS COMMITTING SHA — HARD STOP FOR REVIEW.**

Documentation only. Nothing here is implemented. This document becomes binding only after the user reviews this exact SHA and explicitly authorizes the promotion implementation and its verification run.

```text
D3-B frozen preregistration:      dc4fc16947546dc3277d75dc1fbbd2e3d7a88310
D3-B implementation checkpoint:   f92dc6e65653e4accbf30aec12b5b6c3d7ba9203  (includes 31a6bb9)
D3-B result (DESIGN PASS):        1b96ffc4ae60307e1c7842ca1d46fea540457c69  (CI run 37339943583 green)
branch (this slice):              review/d3b-production-promotion  (from 1b96ffc)
adopted baseline / PR #10:        ee6cb6fcebb105e31224bead48a302811b27b59a  (OPEN, frozen, untouched)
canonical policy today:           PRODUCTION_STAMINA_RECOVERY_POLICY = Gate-G policy (unchanged)
frozen digest:                    3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

**Purpose.** Promote the measured D3-B semantics from an opt-in diagnostic mode into the canonical production stamina/recovery policy **without changing the measured gameplay**. This slice is an equivalence-and-wiring slice, analogous to Gate G of `docs/STAMINA_PRODUCTION_POLICY_ADOPTION_DEFINITION_OF_DONE.md`. It is not a new candidate, a new measurement, or a tuning opportunity.

**Carried-forward caveat (must stay prominent).** D3-B passed with two gates exactly at their floors: **P3 original-100 Bottom final median = 29 (>= 29)** and **G7 = 5/25 (>= 5)**. D3-B has no tactical margin on those gates. Promotion must reproduce these values exactly and must not be described as improving them.

**Status entering this slice.**

```text
D2 v1e                      FAIL (fe229cb)
D2 v1f                      preregistered, never run
D3-A                        preregistered, superseded, never run
D3-B                        DESIGN PASS (1b96ffc)
D3-B production integration NOT YET AUTHORIZED (this document proposes its DoD)
PR #10                      OPEN at ee6cb6f, unchanged
canonical production policy unchanged
```

---

# 1. What is promoted (frozen)

The canonical production stamina/recovery policy becomes:

```text
Rule 1 = ON    (unchanged)
Rule 2 = OFF   (unchanged; no Rule-2 fix bundled)
Bottom RECOVER + Exhausted initiation = LOW            (unchanged)
Initiation after Exhausted clears     = baseline MEDIUM (unchanged)
NEW: Bottom RECOVER post-clear handoff = D3-B
     (PostClearHandoffMode.D3B_EXHAUSTED_TOKEN_LOCKOUT, exactly as measured:
      armed on Bottom's first latch clear; one Exhausted LOW token per armed
      Exhausted episode; then LOCKOUT_HOLD via MountMatch.recovery_hold()
      until the latch clears)
```

Nothing else changes: costs, recovery amounts, behavior and drift rates, the 25/35 hysteresis, Recognition, response selection, settlement, setup, submission and stalling rules, and every raw `MountMatch` / batch default.

---

# 2. Frozen design decisions

## 2.1 Historical policy is frozen under its own name (required before the canonical change)

Today three diagnostic modules build the "adopted" control from `PRODUCTION_STAMINA_RECOVERY_POLICY`:

```text
src/bjj_game/diagnostics/stamina_adoption_verification.py   (Gate G verification)
src/bjj_game/diagnostics/handoff_characterization.py        (D1 characterization)
src/bjj_game/diagnostics/handoff_d2_v1e.py                  (D2 / D3-B adopted comparator; fe229cb evidence)
```

If the canonical object changed in place, every historical comparator would silently become D3-B and the recorded evidence (Gate G, D1, `fe229cb`, and D3-B's own adopted comparator) would stop reproducing. Therefore:

- The current policy is preserved as a fixed, named historical constant, e.g. `GATE_G_STAMINA_RECOVERY_POLICY` (Rule 1 ON, Rule 2 OFF, LOW while Exhausted, no post-clear handoff), with byte-for-byte identical `match_settings()` / `batch_settings()` output to today's canonical policy.
- Those three diagnostic modules (and the tests that construct the adopted control) reference the historical constant instead of the canonical one. This is a reference change only; their outputs must be unchanged (PG9).
- `PRODUCTION_STAMINA_RECOVERY_POLICY` / `production_stamina_recovery_policy()` keep their names and become the D3-B-promoted policy. A frontend that already requests the canonical policy receives D3-B without a new name.

## 2.2 Eligibility: selected only where D3-B was measured; never a silent fallback

- `batch_settings(bottom_behavior_mode=RECOVER)` adds `post_clear_handoff_mode = D3B_EXHAUSTED_TOKEN_LOCKOUT` to the existing settings.
- `batch_settings(bottom_behavior_mode != RECOVER)` is unchanged from the Gate-G policy (no handoff mode). Surfaces A and B therefore receive identical settings and identical gameplay (PG6).
- The existing batch validation is reused unchanged: a RECOVER configuration outside the measured E-PROD shape (ESCAPE baseline, v0.2 setup, v0.4a, `LOW_WHILE_EXHAUSTED`, Rule 1 ON, Rule 2 OFF, no settlement umbrella, baseline MEDIUM) **raises `ValueError`**. The canonical policy never silently runs a RECOVER configuration without D3-B, and never runs D3-B on an unmeasured configuration.
- `match_settings()` is unchanged. D3-B is a decision-window controller, not a `MountMatch` setting. The policy additionally exposes the selected mode (e.g. a `post_clear_handoff_mode` property) so a future frontend can construct the same `D3BTokenLockoutController`; wiring a frontend to it is out of scope here.

## 2.3 No gameplay code changes

The promotion implementation may change only:

```text
src/bjj_game/interfaces/production_policy.py          (historical constant + promoted canonical policy)
the three diagnostic modules in 2.1                    (reference the historical constant)
tests                                                  (new promotion tests; adopted-control references)
a new promotion verification diagnostic + its docs/evidence
```

It must **not** change `engine/match.py`, `interfaces/batch.py`, `interfaces/handoff_policy.py`, `domain/*`, or any D3-B / v1e semantics. If the implementation appears to require such a change: **STOP and report**; do not adapt the gates.

## 2.4 Relationship to PR #10 and branches

- PR #10 stays OPEN at `ee6cb6f`, unmodified. It is not merged, rebased or extended.
- `ee6cb6f` is an ancestor of `1b96ffc`, so this branch contains PR #10's commits. Any future merge order (PR #10 first, or a stacked promotion PR) is a separate user decision; this slice opens no PR unless asked.

---

# 3. Promotion gates (definition of done)

All gates must PASS. Any FAIL means **PROMOTION FAIL**: record and STOP, with no tuning and no gate change. Missing evidence means **OPEN**. Unit, checker or CI PASS never substitutes for a promotion gate.

| ID | Gate | Requirement |
|---|---|---|
| **PG1** | Effective settings | For seeds 42 and 142, OFF + shadow and ON: `effective_settings(canonical E-PROD kwargs)` == `effective_settings(d3b_kwargs)` exactly (the measured diagnostic D3-B configuration of `1b96ffc`). |
| **PG2** | Full gameplay identity | Same seeds and modes, 100 matches, 300 s: canonical-D3B vs measured diagnostic-D3B. `BatchSummary` equal; captured per-match records equal; post-clear event logs equal; per-match op traces (fixed tracer) equal, including RNG draw order, setup, submission and stalling state. **0 divergent matches in all four runs.** |
| **PG3** | Frozen D3-B values reproduced from the canonical route | Every gate value of `1b96ffc` reproduces exactly, including: P3 median **29**; P4 original-100 **30 escapes (Half 17 / Open 5 / Reversal 8) / 65 timeouts / Tap 5** and seed 142 **31 / 65 / 4**; P5 exposure **13**, real offenses **0**, OFF/ON divergence **0**; G1/G2 **53 tokens / 97 lockout holds / 0 violations**; G3 **25/25**; G6 **0 prefix mismatches, 18/18 and 4/4**; G7 **5/25** (matches 12, 24, 38, 48, 76). The committed D3-B evidence file and data report regenerate byte-identically. |
| **PG4** | Negative control | With the canonical D3-B hook intentionally disabled (canonical policy with the post-clear handoff forced to NONE, test-only): (a) the PG2 checker reports **>= 1 divergent match in every run** against diagnostic-D3B, and (b) that disabled run equals the Gate-G adopted control exactly (the `fe229cb` control evidence, e.g. original-100 35 escapes / 60 timeouts / Tap 5). This proves the checker can detect a missing hook and that the hook is the only difference. |
| **PG5** | Raw defaults unchanged | `run_escape_first_batch` and `MountMatch` defaults are unchanged (`post_clear_handoff_mode` default NONE; all stamina flags default as before). Raw-default construction is gameplay-identical to `1b96ffc`. |
| **PG6** | Surfaces A and B unchanged | Canonical `batch_settings` on A and B equals the Gate-G policy's output; A = 78 Threat matches / 1,950 entries / Tap 0; B Tap 9/100; 0 `recovery_hold` calls; gameplay identical to `1b96ffc`. |
| **PG7** | Rule 1 ON, Rule 2 OFF | Canonical policy: `unfunded_responder_cost_waiver` True, `supplemental_hold_settlement` False, settlement umbrella off. Rule 1 exact on all four E-PROD runs (responder spend 0, hold charged 0 on unfunded-initiator exchanges); hold covered by response 0. |
| **PG8** | Nothing bundled | Diff review: no Rule-2 fix, no setup-policy change, no commitment-selection change, no frontend code, no change outside 2.3. |
| **PG9** | Historical reproduction | Unchanged pinned tests pass: Gate G / adoption verification, D1 characterization, v1e `fe229cb` evidence reproduction, D3-B measurement pins. The historical constant's settings equal today's canonical output. v1e and diagnostic D3-B modes remain callable. Historical documents and evidence preserved. |
| **PG10** | Frozen digest | `3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2` exact; semantic checker PASS; legacy entry point PASS. |
| **PG11** | Verification | Full local suite on Python 3.11, 3.13 and 3.14 (if available); exact-head CI on 3.11 and 3.13 green on the final promotion SHA. |
| **PG12** | Hard stop | After the promotion evidence is recorded and exact-head CI is known: HARD STOP. No merge, no PR #10 change, no frontend work, no next candidate. |

---

# 4. Verification run (not a measurement)

- Seeds 42 and 142, 100 matches, 300 s, OFF + shadow and ON — the same frozen configuration as D3-B. These runs exist only to prove equivalence and reproduction (PG2-PG4, PG6). They are not a new candidate measurement.
- No new seeds, extensions, settings or thresholds. Values are compared for exact equality with `1b96ffc`; there is nothing to tune.
- If any equivalence fails, the promotion wiring is wrong: record the divergence (first divergent match and operation) and STOP for review. Do not adjust D3-B, the gates or the evidence.

# 5. Required chronology after authorization

1. Implement 2.1 (historical constant + reference switch) first, alone. Show PG9 before touching the canonical policy.
2. Implement 2.2 (promoted canonical policy) and the promotion tests, including the PG4 negative control.
3. Commit an **implementation checkpoint** before the verification run; push normally.
4. Run the verification once; record `docs/BURST_RECOVERY_LOCKOUT_D3B_PROMOTION_RESULT.md` with PROMOTION RESULT: PASS / FAIL / OPEN, plus raw evidence.
5. Pin the equivalence results in tests; full local verification; commit the **result separately**; push; exact-head CI.
6. HARD STOP (PG12).

# 6. Not authorized by this document

- any implementation (this document is preregistration only);
- merging or modifying PR #10; squash; force-push;
- changing D3-B semantics, the frozen D3-B evidence, or any gate value;
- raw default changes; Rule-2 work; setup-policy or commitment-selection debt; frontend work;
- running D3-A, v1f, or any new candidate.
