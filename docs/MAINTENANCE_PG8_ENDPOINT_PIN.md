# Maintenance — Pin D3-B Promotion PG8 to Its Historical Interval

## Status

**MAINTENANCE SLICE — HARD STOP FOR REVIEW.** Authorized after review of the late-recovery characterization `683e830`. No gameplay, policy, settlement or evidence change.

```text
branch:  maintenance/pin-d3b-pg8-endpoint
base:    f4b9c9e1ee24c648c14d584bcfc377f234bd851f (main)
```

## Defect

`d3b_promotion.pg8()` ran `git diff --name-only 1b96ffc HEAD`. PG8 is the promotion-time "nothing bundled" gate (`docs/BURST_RECOVERY_LOCKOUT_D3B_PROMOTION_PREREGISTRATION.md`). Its question is what changed between the measured D3-B result and the qualified promotion, not what has changed in the repository since then. Because the endpoint was `HEAD`, every later legitimate change became "unexpected".

- `test_pg8_nothing_bundled` has failed on full-history checkouts since the R1 merge `cfdb08c` (and on `f4b9c9e`).
- CI never ran it: the shallow checkout lacks `1b96ffc`, so the test skipped.

## Change

1. `PROMOTION_HEAD_SHA = 0aa23db5089476982eb6eaf94d91b316d857cee1` (qualified promotion head, PR #11) is an explicit constant. PG8 now diffs `1b96ffc -> 0aa23db`. `HEAD` is no longer part of the comparison.
2. `test_pg8_nothing_bundled`:
   - requires status PASS with forbidden = unexpected = [];
   - requires PG8's file list to equal the pinned interval diff;
   - requires the committed historical PG8 record (taken mid-promotion at `33a9718`) to lie inside that interval.
   Without the history it skips, unless `BJJ_REQUIRE_GIT_HISTORY=1`, in which case it fails.
3. CI: a dedicated `historical verification (3.11 / 3.13)` job with a full-history checkout runs only that test with `BJJ_REQUIRE_GIT_HISTORY=1`. `CI gate` requires it on the full path. The 12 unit-test shards stay shallow. The docs-only fast path skips the job.

**Not changed:** `ALLOWED_PATHS` / `FORBIDDEN_PATHS`; the frozen promotion evidence (`docs/evidence/d3b_promotion/*`, including the committed PG8 PASS record); gameplay; policy; defaults.

## Evidence

Pinned PG8: **PASS**, forbidden [], unexpected [], 17 files in `1b96ffc..0aa23db`.

**HEAD independence.** The new `pg8()` was run in throwaway worktrees at each HEAD below. Output hash:

| HEAD | PG8 | Output hash |
|---|---|---|
| `f4b9c9e` (current `main`) | PASS [] [] | `8d519df2f99854b1` |
| `683e830` (late-recovery branch) | PASS [] [] | `8d519df2f99854b1` |
| local docs-only commit on `main` (not pushed) | PASS [] [] | `8d519df2f99854b1` |
| this branch | PASS [] [] | `8d519df2f99854b1` |

**Fail-not-skip.** With history forced unavailable:
- `BJJ_REQUIRE_GIT_HISTORY=1` gives 1 failure, 0 skips;
- unset gives 0 failures, 1 skip.

## Acceptance

PG8 PASS on the pinned interval; historical evidence unchanged; gameplay unchanged; digest exact; normal full suite PASS; historical verification PASS on 3.11 and 3.13; CI gate PASS. Exact-head results are reported at review.

**HARD STOP.**
