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

## Intelligent routing (supersedes the earlier all-executable full path)

`tools/ci/route.py` is dependency-free and independently tested outside gameplay
unittest discovery. Precedence: UNKNOWN, CI_INFRASTRUCTURE, PYTHON_OR_SHARED,
GODOT_ONLY, DOCUMENTATION_ONLY. Unknown/empty/failed diffs run both qualifications.

| Changes | Python matrix | Godot parity |
| --- | --- | --- |
| Godot scripts, scenes, assets, tests, Python fixture generators | skipped | required |
| Ordinary Markdown documentation / README | skipped | skipped |
| Python source/tests/packaging, shared policy/semantic/design documents, evidence | required | required |
| CI workflows/classifier, unknown paths, mixed changes | required | required |
| Main integration / explicit full qualification | required | required |

All workflow edits conservatively require both routes: file-level routing cannot
infer whether a YAML edit changes security permissions. `docs/evidence/**` and
shared contract documents and pinned measurement/preregistration Markdown outside
that directory cannot use the documentation shortcut. Markdown in
`GODOT_V1/docs/` is documentation; executable fixtures elsewhere under Godot are not.

The always-created `CI gate` requires successful routing, lightweight whitespace
validation (allowing intentional Markdown hard breaks), and **every selected job**. It directly depends on the reusable Godot
qualification; skipped, cancelled or failed required Godot jobs cannot produce a
passing gate. Existing test commands, matrices, shard assignment and digest remain
unchanged. The Godot workflow now runs through the caller, not independent path
filters. Shared Python changes also receive Godot reference comparisons.

### Events and exact revisions

Automatic qualification runs for every PR (including non-main stacked bases), and
for every push/merge to `main`. Base retargets trigger qualification even without
a new head commit. Recognized title/body-only edits with complete PR refs are
ignored in isolated concurrency groups and publish no automatic CI gate; missing
event fields conservatively enter qualification. Feature pushes without a PR do not launch CI: open
a draft PR or dispatch full qualification. This intentionally removes duplicate
push/PR work. PR ranges use actual event base...head; push ranges use before..head,
including all commits. Rename records include both old and new paths. Missing or
unusable ranges conservatively select both routes. Missing/incorrect head SHAs
fail admission, rather than testing a guessed revision. Jobs check out the event
head, not an implicit merge ref. Main integration checks test the resulting tree.

Automatic concurrency includes event and PR number/ref; newer PR commits cancel
obsolete PR runs, not main or manual qualification. Manual runs have unique run
IDs and cannot cancel automatic checks.

### Full qualification of a final head

Get the current head, then dispatch the routing workflow with an exact SHA:

```sh
branch=feat/godot-v1-exchange-settlement
sha=$(gh api repos/theaxlklo/BJJ-Game/commits/$branch --jq .sha)
gh workflow run test.yml --ref "$branch" -f target_sha="$sha" -f full_qualification=true
```

Use a branch containing the updated workflow. The requested SHA must equal that
branch's SHA at dispatch time; stale pins fail before launching tests. All jobs use
that immutable SHA. Verify the completed run's `head_sha` and re-run after any new
commit. Dispatch without an available diff also runs full qualification, including
when the input is false: ambiguity never authorizes skipping. Manual dispatch publishes **Manual qualification gate** and **Manual admission**,
separate from automatic **CI gate**. Invalid dispatch requests therefore cannot
publish a failed required CI gate on an otherwise qualified PR SHA. Manual evidence
does not satisfy an automatic CI gate requirement; verify both where appropriate.
Major migration heads should receive a final successful full run before merging.

### Repository protection limitation

Inspection reported `main.protected=false` and no rulesets. The detailed protection
endpoint returned HTTP 403 (`Resource not accessible by integration`). This change
cannot claim enforced merge protection. A maintainer must configure branch
protection/rulesets to require the stable **CI gate**, disallow bypasses/direct
pushes, and enforce the chosen up-to-date-branch policy. If an old standalone Godot
job name is required, update it to the new caller context or use CI gate (which
already requires Godot when applicable). Do not leave an obsolete check pending.
Routing cannot protect against a PR deliberately deleting its own required gate;
workflow/routing changes need maintainer review under protected repository rules.

### Dependencies and review

No runtime dependency or copied external code was added. Local workflow linting
uses the MIT-licensed `rhysd/actionlint` v1.7.7 executable as a verification tool;
it is not bundled or required by CI. See `docs/ci/PR22_REVIEW.md` for the separate,
read-only settlement review. Issue #20 remains outside this change.
