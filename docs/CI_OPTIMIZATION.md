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

The unit suite is split deterministically across four independent shards per Python version. Test files are sorted and assigned round-robin by file index. Every `tests/test_*.py` file belongs to exactly one shard for each Python version.

Digest/checker/legacy verification runs in parallel with the unit-test shards instead of waiting for the whole unit suite.

### Superseded runs

The workflow uses GitHub Actions concurrency keyed by workflow + source branch, with `cancel-in-progress: true`.

A newer push to the same branch cancels obsolete work for the older SHA. Push and pull-request runs for the same source branch also share the concurrency key, avoiding duplicate long qualifications.

## Invariants

- No gameplay, policy, settlement, stamina, submission or deterministic engine semantics are changed by this slice.
- No test is deleted or excluded from the full path.
- Both supported Python versions still execute every test file on the full path.
- The frozen digest remains checked on both Python versions.
- The semantic checker and legacy entry point remain checked on both Python versions.
- `CI gate` fails if classification fails or if any applicable full-path job fails.
- A zero-change/unknown classification is conservative: it takes the full path.

## Follow-up

After this workflow is qualified, a later ordinary docs-only commit can be used to verify the fast path in seconds. Further test-runtime optimization should be based on measured per-file timings rather than removing coverage.
