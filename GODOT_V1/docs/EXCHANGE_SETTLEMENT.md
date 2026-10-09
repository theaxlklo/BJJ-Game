# Phase 19 — validated Mount exchange settlement

This is an exchange-only migration of the supported portions of
`src/bjj_game/engine/match.py::MountMatch.attempt()`. It is not complete
MountMatch parity or complete production stamina/recovery parity. It is stacked
on PR #18 (`9c4166cef43d367786bbb24b76bccef6624779ba`), which is stacked on #17.
Python source and frozen tests remain unchanged.

## Public interfaces and source mapping

| Godot component | Responsibility | Unchanged Python authority |
|---|---|---|
| `BjjExchangeRules.build(settings)` | Validated flags, immutable public getters; raw defaults OFF | `MountMatch.__post_init__`, settlement flag properties |
| `BjjProductionStaminaPolicy.settings()` | Rule 1 ON, Rule 2 OFF; no implicit v0.4a | `PRODUCTION_STAMINA_RECOVERY_POLICY.match_settings()` |
| `BjjMountExchange.attempt(request)` / `process(state, request)` | Admission, historical capture, funding, resolution, outcomes, ordered charges | `MountMatch.attempt`, `_resolve_attempt_resolution`, `_apply_resolution` |
| `BjjExchangeResult.Request` | Action/response and requested commitments; empty response effort means omitted | `ActionAttempt`, `MountMatch.attempt` |
| `BjjExchangeResult` | Typed funding/spends, historical exhaustion, both resolutions and detached outcome | `domain/action.py::AttemptResult` |
| `BjjExchangeResult.Resolution` | Typed adapter for the unchanged frozen resolver | `ResolutionResult`, `MountResolutionEngine.resolve_action` |
| `BjjExchangeHistory` | Typed append-only-by-convention value arrays, detached serialization | `RunHistory`, attempt bookkeeping |
| Minimal setup and Americana transitions inside `BjjMountExchange` | Default builders, Ready legality/override/consumption, Threat→Control→Finish→Tap and defense/feint histories | Default setup policy, `_apply_setup_after_attempt`, `_resolve_submission_stage`, `_apply_submission_after_attempt` |

The exchange owns two existing `BjjStaminaPool` references and uses the existing
cost and exhaustion policies. It does not duplicate pool, funding, or latch rules.
The existing Mount catalog/resolver and all predecessor tests are unchanged.
The modern finish uses the frozen Americana row as Python does; it does not add
matchup entries or fake a new resolution table.

```gdscript
var settings := BjjProductionStaminaPolicy.settings()
settings["enable_v04_commitment_semantics"] = true # Explicit caller opt-in.
var configured := BjjExchangeRules.build(settings)
if not configured.ok():
    return configured.error
var exchange := BjjMountExchange.new()
exchange.rules = configured.rules
var request := BjjExchangeResult.Request.new(
    BjjMountCatalog.TOP_HIGH_MOUNT_CLIMB,
    BjjMountCatalog.BOTTOM_RESPONSE_FOREARM_FRAME, "HIGH", "MEDIUM")
var result := exchange.attempt(request)
if not result.ok():
    return result.error # Rejection occurs before authoritative mutations.
```

The owning simulation supplies validated axis/band, initiative, behaviors,
clock context, tiers, stage and pools. These context fields are typed and mutable
for integration, not an unvalidated save/load API. Missing/aliased pools, invalid
state/configuration and invalid requests produce specific error identifiers.
Underscore policy storage follows the existing GDScript privacy convention;
callers must not write implementation fields. Histories and results are mutable
value objects by convention, but never share mutable arrays or state objects with
one another. `fields()` is the serialization boundary and returns fresh data.

## Frozen operation order

1. Validate admission before changing either pool, position, initiative, track or history.
2. Capture the original initiator, both stamina amounts and both historical bands.
3. Determine initiator funding; under v0.4a determine response funding (omitted→MEDIUM).
4. Resolve raw/behavior/position/Ready override, then historical exhaustion.
5. Apply commitment magnitude, saturate, then responder undercommitment and saturate again.
6. If either commitment step applies, re-resolve using the actual final grade minus the base grade. A sum of modifier steps is incorrect across clamps. Otherwise preserve the exhausted resolution including its external modifier field.
7. Apply position/history and initiative (exits retain initiative), then default setup/submission effects.
8. Charge initiator, response commitment, and finally the narrowly defined Contested Americana hold.
9. Record charges, funding gaps, waivers and historical modifiers; return a detached outcome.

LOW and UNFUNDED have the same magnitude ceiling but different funding ranks and
settlement rules. HIGH only magnifies Success/Failure. An affordable zero-cost
LOW is funded. Funding gaps compare requested and effective costs; stamina
shortfall compares actual expenditure request and charge. These are distinct.
Raw Mount ignores even an invalid optional response commitment; v0.4a validates
it and defaults an omitted response to MEDIUM. Preserve that surprising legacy
behavior rather than replacing it with a new rule.

A submission hold occurs only for Contested active Americana finish, or
Contested Ready isolation with submissions enabled. Rule 1 waives both response
commitment and hold expenditure only for an UNFUNDED initiator. Rule 2 credits
actual response charge against nominal LOW hold cost only for a funded
initiator. Rule 2-only plus UNFUNDED retains legacy hold settlement. The production
preset selects Rule 1 ON / Rule 2 OFF; umbrella ON selects both and is a control,
not the production default. Holds still report nominal cost and a zero-request
spend when waived. Requested LOW caps successful stage advancement; a MEDIUM/HIGH
request downgraded to LOW is not a LOW feint.

## Approved terminal differences — excluded from exact parity

The user explicitly approved atomic terminal rejection on 2026-10-09 after these
unchanged Python behaviors were reproduced:

- An active Americana finish after timeout can succeed and charge stamina.
- An ordinary action after `submission_tapped=True` can succeed and append history.
- A finish against broken Mount raises after appending resolution/action history.

Godot rejects timeout, Tap and exited Mount before mutation. The fixture retains
Python's observed results/state for these probes, labels them `terminal_override`,
and checks Godot rejection plus unchanged pre-state separately. Those operations
are counted separately and are not successful parity comparisons. No Python
repair or redesign was included. Other supported source rejections compare both
observable rejection and complete unchanged state/history. Textual errors need
not match Python exceptions.

## Admission boundaries and unported dependencies

- Exchange costs are nonnegative, strictly ordered **integer** costs. Default
  3/7/12, zero-cost LOW and custom integer policies are covered. Python also
  permits boolean cost values because bool subclasses int. PR #18 preserves that
  primitive funding quirk. This exchange entry explicitly rejects such policies
  before mutation (`unsupported_cost_policy`); boolean spend/history serialization
  is unported and is not in the parity claim. No primitive behavior was changed.
- Strict typed flag validation rejects misspelled keys/non-booleans. Python's
  dataclass accepts some non-boolean truthy flag values; these are outside the
  typed configuration contract. JSON is not accepted as a permissive runtime decoder.
- Default setup, default exhaustion and frozen Mount resolution only. Custom
  setup/exhaustion/resolution policies, Recognition and stalling are not ported.
  Valid Python configurations enabling Recognition/stalling are rejected explicitly
  as unsupported; prerequisites are still checked first.
- Clock context may be supplied with a positive initial clock and current time in
  its range; no time advancement occurs. Numeric capacity/clock values use the
  predecessor exact-integer boundary (`2^53-1`). No frame delta or random draw is used.
- No full match aggregate, recovery/reset/free initiative controller, D3-B,
  progression, scoring, new positions, save/load, networking or presentation wiring.
- No command identity or deduplication protocol. Repeated commands are evaluated
  against current context; an initiative change can make the repeated action illegal.
- Result snapshots contain relevant exchange state; complete histories are exposed
  separately as detached fields. Reserved histories for unported controllers stay empty.

## Verification

Tests/fixtures were committed first (`c5f8bcd`); native execution initially failed
on missing exchange types. The generator invokes unchanged `MountMatch.attempt()`
and serializes its dataclasses, properties and final state, without implementing
expected funding/grade/settlement calculations. It records all 18 frozen pairs,
requested effort combinations, thresholds, exhausted histories, Ready/active
submission contexts, default and custom integer costs, custom pool capacity and
clock contexts, rejections and consecutive operations. Six explicitly named
policy controls are raw, v0.4a, production, Rule 1-only, Rule 2-only and umbrella-both.
The generated JSONL corpus is streamed one scenario at a time to avoid retaining
its roughly 123 MB payload in Godot memory. Fixtures are generated in CI, not committed.

The runner replays each scenario twice from the same initial state, checks every
result/state/history field, checks rejection preservation, and requires integer
runtime types for serialized integer outputs. Axis comparison uses the unchanged
Mount corpus's `1e-10` precision contract; no tolerance was widened. JSON numeric
configuration is restored to native integer types only inside the fixture adapter.

```bash
PYTHONPATH=src python GODOT_V1/tests/generate_exchange_reference.py
godot --headless --path GODOT_V1 --script res://tests/test_exchange_boundaries.gd
godot --headless --path GODOT_V1 --script res://tests/test_exchange_reference.gd
```

Local final qualification with pinned Godot 4.7.2:

| Category | Measured result |
|---|---|
| Source-generated exchange scenarios | 14,631 (includes explicit terminal-boundary probes) |
| Exchange operations | 14,780; each trace replayed twice |
| Scalar/shape comparisons across oracle, rejection and boundary checks | 8,851,698; zero mismatches |
| User-approved terminal boundary operations | 4, separately identified; source outcomes excluded from exact equivalence |
| Native exchange negative/boundary/positive assertions | 231; zero failures |
| Hold operations by policy | raw 416; v0.4a, production, Rule 1-only, Rule 2-only, both: 325 each |
| Existing Mount native / oracle | 40 assertions; 4,140 action cases + 300 drift sequences; 92,939 field checks |
| Existing stamina oracle / native | 1,752 traces, 13,433 operations; 410,192 checks; 154 native assertions |
| Corrected targeted Python qualification | 68 tests passed |
| Import and 3D scene startup | Passed |

Comparison counts include structural keys/array lengths and rejection/boundary
preservation checks, not just successful result scalars; they are not independent
test counts. The four terminal operations include an after-Tap step in a replay
plus the three standalone anomaly probes. Ordinary successful parity operations:
14,686; reference-equivalent rejections: 90; approved terminal guards: 4.

The extended Godot workflow retains import, 40 Mount assertions, both predecessor
corpora, 154 stamina adversarial checks and scene startup. New native/parity steps
reject unexpected engine/script errors and warnings. The predecessor native step
continues to require exactly its two deliberate read-only diagnostics. Python CI
is unchanged: full 3.11/3.13 shards, semantic/frozen enumerate digest and historical
qualification. See the PR checks for CI outcomes at the final commit.

## Adversarial self-review and next milestone

Review specifically checked pre-validation mutations, aliasing fighter pools,
result/history aliasing, charging after initiative flips, sequential grade clamps,
Rule 1 on both hold triggers, Rule 2 actual-charge coverage, requested LOW versus
effective LOW feint caps, setup consumption on exits and persisted-versus-crossing
axis. Native guards and independent field comparisons cover these concerns. Review
found that clock context initially assumed 300 seconds; it now carries the source
initial clock, with custom-clock fixtures and correct feint timestamps. A helper
that interpreted any non-Americana identifier as the Trap tier now handles only
the two explicit targets. No reproducible unresolved defect remains within the
claimed integer/default-policy slice; the admission boundaries above are limitations.

No third-party source, package or dependency was adopted. Consulted the official
[Godot GDScript documentation](https://docs.godotengine.org/en/stable/tutorials/scripting/gdscript/gdscript_basics.html)
for typed inner classes, RefCounted data and property behavior; implementation is
original project-specific code porting the repository's own reference.

Issue #20 should port `MountMatch.advance()` and Bottom RECOVER decisions next:
update both behavior meters/pools, drift and clock in frozen order, expose
post-advance exhaustion observations and normal/free Bottom windows, and preserve
E-PROD configuration validation. Reuse this settlement entry for chosen attempts.
D3-B token arming/lockout and `recovery_hold()` remain Issue #21; do not fold them
into the pool or this exchange controller.
