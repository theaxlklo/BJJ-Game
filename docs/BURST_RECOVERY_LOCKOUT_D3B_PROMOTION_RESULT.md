# D3-B Production Promotion — Result

```text
D3-B PROMOTION RESULT:  PASS
```

**The canonical `PRODUCTION_STAMINA_RECOVERY_POLICY` now selects D3-B on Bottom RECOVER, and the canonical route reproduces the measured diagnostic D3-B of `1b96ffc` exactly.** Every promotion gate PG1-PG11 passed in the one frozen equivalence verification. Promotion proves identity; it adds no confidence and no margin. The measured D3-B result stands with two values **exactly at their floors**:

```text
P3  original-100 Bottom final median = 29    (required >= 29)
G7  frozen affected population       = 5/25  (required >= 5/25)
```

Nothing is merged. PR #10 stays OPEN at `ee6cb6f`, unchanged. No frontend wiring. **HARD STOP.**

```text
promotion preregistration (authorized):  1eb0a30ad2896dad53f9248e218c3da9a48ab557
step 1, historical freeze:               7a290d0ba1085020e198b44ab0e269f7d1ef8e59
promotion implementation checkpoint:     fdfc39e384c327b37ca7d561c25d40a26ea9fc7f
reproduced D3-B result:                  1b96ffc4ae60307e1c7842ca1d46fea540457c69
branch:                                  review/d3b-production-promotion
PR #10:                                  OPEN at ee6cb6fcebb105e31224bead48a302811b27b59a (unchanged)
frozen digest:                           3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2 (exact)
verification run:                        ONE, from fdfc39e, Python 3.13.16
```

Generated data: `docs/BURST_RECOVERY_LOCKOUT_D3B_PROMOTION_VERIFICATION_DATA.md`. Raw evidence: `docs/evidence/d3b_promotion/verification.json.gz`, `docs/evidence/d3b_promotion/reference_1b96ffc.json` (fingerprints computed by `d3b_promotion_reference.py` against a temporary detached `1b96ffc` worktree, since removed), `docs/evidence/d3b_promotion/pre_promotion_canonical_policy_outputs.txt` (the canonical policy's outputs at `1eb0a30`, before any change).

---

## 1. What changed

```text
GATE_G_STAMINA_RECOVERY_POLICY        Rule 1 ON, Rule 2 OFF, LOW while Exhausted, no post-clear handoff
PRODUCTION_STAMINA_RECOVERY_POLICY    Rule 1 ON, Rule 2 OFF, LOW while Exhausted, post-clear D3-B
```

- `ProductionStaminaRecoveryPolicy` is a frozen dataclass with one immutable field, `post_clear_handoff_mode` (default NONE). Each output depends only on that instance state. The two constants are independent instances; the historical one cannot be changed by the canonical one.
- `match_settings()`: identical for both.
- `batch_settings(RECOVER)`: canonical = Gate-G output + `post_clear_handoff_mode = D3B_EXHAUSTED_TOKEN_LOCKOUT`. `batch_settings(any other mode)`: identical to Gate-G, no handoff key.
- An unmeasured RECOVER configuration requested through the canonical policy **raises `ValueError`** (existing batch validation; tested), never a silent fallback.
- Historical consumers (Gate-G verification, D1 characterization, the D2/D3-B adopted comparator, one v1e test) reference `GATE_G_STAMINA_RECOVERY_POLICY`. The Gate-G policy spec tests target the historical constant; new tests cover the promoted policy.
- Chronology as preregistered: step 1 (`7a290d0`) froze the historical policy alone, with the canonical object still NONE, and proved its outputs equal the pre-promotion snapshot and the full suite (485) passed, including Gate G, D1, `fe229cb` and D3-B evidence reproduction. Only then did `fdfc39e` promote the canonical policy.
- **No gameplay code changed**: `engine/`, `interfaces/batch.py`, `interfaces/handoff_policy.py`, `domain/` and `diagnostics/handoff_d3b.py` are untouched since `1b96ffc` (PG8).

## 2. Gates

| Gate | Requirement | Measured | Status |
|---|---|---|---|
| PG1 | effective settings: canonical E-PROD == diagnostic D3-B | equal in 42/OFF+shadow, 42/ON, 142/OFF+shadow, 142/ON | **PASS** |
| PG2 | full gameplay identity, 0 divergent matches | every run: `BatchSummary` equal; 100 matches; divergent 0 by captured gameplay signature, 0 by post-clear event log, 0 by per-match op trace (actions, RNG draw order, clock, axis, band, staminas, exit, setup, submission, stalling state) | **PASS** |
| PG3 | every frozen D3-B value reproduced exactly from the canonical route | see section 3; the committed D3-B evidence file regenerates **byte-identically** and the D3-B data report **identically**; all 14 D3-B gates PASS | **PASS** |
| PG4 | negative control | hook removed: diverges from diagnostic D3-B in every run (see note); equals the Gate-G adopted control exactly (summary, captured matches, and the stored `fe229cb` control event logs) in all four runs; original-100 35 escapes (16 / 10 / 9) / 60 timeouts / Tap 5, seed 142 29 / 67 / 4 | **PASS** |
| PG5 | raw defaults unchanged | batch and `MountMatch` defaults equal to `1b96ffc`; `post_clear_handoff_mode` default NONE; raw-default batch gameplay fingerprint equal to `1b96ffc` | **PASS** |
| PG6 | Surfaces A and B unchanged | canonical settings equal Gate-G; canonical A and B gameplay fingerprints equal `1b96ffc`; 0 `recovery_hold` calls; A 78 / 1,950 / Tap 0; B Tap 9 | **PASS** |
| PG7 | Rule 1 ON, Rule 2 OFF | canonical: waiver True, supplemental hold False, umbrella False, LOW while Exhausted, D3-B; Rule 1 exact on all four canonical runs (responder spend 0, hold charged 0, covered 0) | **PASS** |
| PG8 | nothing bundled | changed since `1b96ffc`: `production_policy.py`, the three historical-reference diagnostics, the two promotion diagnostics, tests, docs/evidence; 0 forbidden paths, 0 unexpected | **PASS** |
| PG9 | historical reproduction | Gate-G constant outputs == pre-promotion canonical snapshot; independent instance; `fe229cb` evidence regenerated == stored; Gate-G, D1, v1e and D3-B pinned tests pass | **PASS** |
| PG10 | digest, checker, legacy | digest exact; semantic checker PASS; legacy entry point PASS (3.11, 3.13, 3.14) | **PASS** |
| PG11 | local suites + exact-head CI | local full suite PASS on 3.11 / 3.13 / 3.14; exact-head CI on the result SHA: see the final report | **PASS** (local); CI recorded at hard stop |
| PG12 | hard stop | — | stopped |

**PG4 note.** The checker's "divergent" count is 100/100 in every run because D3-B event logs carry D3-only metadata (`kind`, `armed`) on every Bottom window, which the hook-removed run lacks. PG4(a) as preregistered (the PG2 checker reports >= 1 divergent match in every run) is met. The gameplay divergence is real and shown separately: the hook-removed run's outcomes differ from D3-B's (original-100 35 / 60 / 5 vs 30 / 65 / 5), and `tests/test_d3b_promotion_verification.py` additionally requires, per run, unequal summaries and >= 1 divergence at the captured-gameplay and op-trace levels.

## 3. PG3 — measured D3-B values reproduced by the canonical route

Identical in OFF + shadow and ON.

```text
original-100 (seed 42):  30 escapes   Half Guard 17 / Open Guard 5 / Reversal 8   65 timeouts   Tap 5
                         Bottom final median 29   (at threshold, >= 29)
seed 142:                31 escapes   Half Guard 24 / Open Guard 6 / Reversal 1   65 timeouts   Tap 4
P5:                      RESET-with-route exposure 13; real offenses 0; OFF/ON divergence 0
G1/G2:                   53 tokens, 97 lockout holds, 0 G1 violations, 0 G2 violations
G3:                      25/25
G6:                      0 prefix mismatches (100 matches x 4 runs); 18/18 +10 s MEDIUM escapes; 4/4 token-window escapes
G7:                      5/25  — matches 12, 24, 38, 48, 76   (at threshold, >= 5)
```

Any differing value would have been PROMOTION FAIL. None differed.

## 4. Verification integrity

- One verification run from the committed checkpoint `fdfc39e`, frozen seeds 42 and 142, 100 matches, 300 s, OFF + shadow and ON. No new seeds, settings, thresholds or candidates. No scoring fix was needed.
- The `1b96ffc` reference was computed by running the same reference script against a detached `1b96ffc` worktree (HEAD verified), then the worktree was removed.
- `tests/test_d3b_promotion_verification.py` re-executes the verification and requires PG1-PG7 and PG9 to equal the committed evidence. PG8 depends on git history and the growing file list, so it is re-checked (0 forbidden, 0 unexpected) only where `1b96ffc` history exists (skipped in CI's shallow checkout).

## 5. Still not done / not authorized

- Merging the promotion branch, merging or modifying PR #10, frontend wiring (a frontend must construct the same `D3BTokenLockoutController` via the policy's `post_clear_handoff_mode`), Rule 2, setup-policy or commitment-selection debt, raw-default changes, D3-C, further D3-B tuning, squash, force-push.

**HARD STOP.**
