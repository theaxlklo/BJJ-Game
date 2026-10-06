# CI Optimization

## Purpose

Reduce GitHub Actions wall-clock time without weakening qualification for executable changes.

Baseline evidence from run `37382027293` before this slice:

- Python 3.11 unit/regression suite: about 14.5 minutes.
- Python 3.13 unit/regression suite: about 18.2 minutes.
- Frozen digest + semantic checker + legacy entry point added several more minutes per Python version.
- Checkout and Python setup were only a few seconds, so dependency caching is not the bottleneck.

## Rules

### Documentation-only fast path

A change is eligible only when every changed path is:

- `docs/**`, except `docs/evidence/**`; or
- `README.md`.

`docs/evidence/**` deliberately triggers full qualification because committed evidence can be pinned by executable tests.

All other changes trigger full qualification. This includes source, tests, workflow/configuration files and packaging metadata.

The workflow still emits the stable final job `CI gate`. On a documentation-only change, the heavy jobs are skipped and the docs-only path must pass.

### Full qualification path

Executable or evidence-affecting changes preserve the existing qualification contract:

- Python 3.11 and Python 3.13.
- Complete unit/regression test suite.
- Frozen enumeration digest.
- Semantic checker.
- Legacy entry point.

The unit suite is loaded by Python's standard `unittest` discovery, flattened to individual test cases, sorted by stable test ID, then assigned deterministically round-robin across six independent shards per Python version. Every discovered test case belongs to exactly one shard for each Python version.

Test-case sharding is intentional: profiling the first file-sharded prototype showed that a few historical measurement methods dominate runtime, so file-level sharding left one shard carrying most of the wall clock.

Digest/checker/legacy verification runs in parallel with the unit-test shards instead of waiting for the whole unit suite.

### Historical git invariants

The unit-test shards use a shallow checkout. Tests that need older history skip there.

A small dedicated job, `historical verification (3.11 / 3.13)`, checks out full history (`fetch-depth: 0`) and runs only the history-dependent invariants, currently D3-B promotion PG8 (`test_pg8_nothing_bundled`). It sets `BJJ_REQUIRE_GIT_HISTORY=1`, so a missing history **fails** instead of skipping. `CI gate` requires this job on the full path. The docs-only fast path skips it.

Added by the PG8 maintenance slice (`docs/MAINTENANCE_PG8_ENDPOINT_PIN.md`).

### Superseded runs

The workflow uses GitHub Actions concurrency keyed by workflow + source branch, with `cancel-in-progress: true`.

A newer push to the same branch cancels obsolete work for the older SHA. Push and pull-request runs for the same source branch also share the concurrency key, avoiding duplicate long qualifications.

## Qualification

The optimized full path was exercised on exact head:

```text
00cc7934d2adf1c4d56b55a4678c38d8dbf85a5c
GitHub Actions run 37387768888
result: SUCCESS
```

That run exercised the workflow/configuration-change path, so it executed the full qualification rather than the documentation shortcut.

This documentation-only commit is the explicit fast-path probe. Its run must show:

- classifier = docs-only;
- `docs-only fast path` = success;
- all unit-test shards = skipped;
- both verification jobs = skipped;
- `CI gate` = success.

Do not merge the CI optimization until that probe passes.

## Invariants

- No gameplay, policy, settlement, stamina, submission or deterministic engine semantics are changed by this slice.
- No test is deleted or excluded from the full path.
- Both supported Python versions still execute every discovered test case exactly once on the full path.
- The frozen digest remains checked on both Python versions.
- The semantic checker and legacy entry point remain checked on both Python versions.
- `CI gate` fails if classification fails or if any applicable full-path job fails.
- History-dependent invariants run in the dedicated full-history job and cannot silently skip there.
- A zero-change/unknown classification is conservative: it takes the full path.

## Follow-up

Further test-runtime optimization should be based on measured test-case timings rather than removing coverage.
