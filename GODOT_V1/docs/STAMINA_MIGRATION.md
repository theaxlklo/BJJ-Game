# Stamina and commitment migration contract

This slice ports the integer stamina primitives from `domain/stamina.py`,
`domain/action.py::Commitment`, and `engine/stamina.py`. It does **not** port
`MountMatch`, action attempts, submission settlement, or the production batch
controller. It depends on PR #17 (`feat/godot-v1-reference-parity`,
`1de58ef97c4a0a4342f6a80a36c352926620be6e`); Mount sources and tests are unchanged.
The master design guide remains v10.4.

## Implemented APIs

| Component | Contract |
|---|---|
| `BjjStaminaPool.create(current, maximum)` | Validated creation result (`pool`, `error`, `ok()`). `new()` also creates a valid 100/100 default. |
| Pool properties | Current/maximum, ratio, band, floor(25%) entry and ceil(35%) clear thresholds. |
| `set_current(value)` | Empty error string on success; specific nonempty error on rejection. |
| `spend_up_to` / `recover_up_to` | Typed change result, including before/after, requested, charged/shortfall/fully-paid or recovered/overflow. |
| `BjjCommitment` | Stable LOW/MEDIUM/HIGH strings; empty effective identifier means UNFUNDED and is never a valid request. |
| `BjjStaminaCostPolicy.build` / `defaults` | Copied policy configuration; strictly increasing nonnegative integer costs, defaults 3/7/12. |
| `determine(requested, available)` | Pure typed funding result: requested/effective IDs, both costs, funding gap, explicit error. Does not charge stamina. |
| `BjjBehaviorStaminaPolicy.build` / `defaults` | Copied integer rates for all five distinct IDs; default quantum 5, rates -1/0/-1/0/+2. CONSERVE is shared by both sides in Python. |
| `apply(pool, behavior, duration, meter)` | Explicit flow result and controlled pool/meter mutation; signed integer carry, saturation, spend shortfall and recovery overflow. |
| `BjjExhaustionPolicy.exchange` | Default -1 initiator and +1 responder effects, typed historical-band result; invalid bands rejected. Both Exhausted cancel. |

Policies and pool internals use underscore members; GDScript has no private
member enforcement. Callers must use the controlled methods, not those members.
Public properties read authoritative internal values and reject writes with an
explicit Godot error diagnostic (Python raises AttributeError). Getter-only
GDScript properties otherwise silently accept writes to unused backing storage;
the explicit setters prevent that misleading behavior. Normal recoverable pool
operations return errors, rather than log diagnostics. Dictionaries appear only
at configuration/serialization boundaries; simulation returns typed objects.
No autoload, rendering dependency, frame delta, random draw, or third-party code
was introduced. Result objects are caller-owned snapshots, not live pool views.

## Non-obvious reference behavior

- The Exhausted latch retains history within the entry/clear interval. Setting,
  spending or recovering zero still refreshes the latch exactly as Python does.
  Construction initializes the latch from entry alone.
- Negative available stamina in `effective_commitment` is accepted by Python and
  produces UNFUNDED. It is preserved in `determine`; actual pools cannot be negative.
- Zero-cost LOW is legal if the other costs strictly increase. Zero available
  stamina can fund that LOW; it is distinguishable from UNFUNDED.
- A meter can be preloaded outside one quantum. A **zero-duration** apply still
  processes that carry. A normal zero-duration update with fractional carry does
  nothing. HOLD and PROTECT preserve fractional carry, rather than resetting it.
- Saturation consumes whole-point requests even when charged/recovered is zero.
  The remaining signed fractional units survive behavior changes. Opposing rates
  first cancel the shared signed carry; separate positive/negative meters would
  change the game.
- Split/combined equivalence applies to the same monotone behavior over an interval,
  including cumulative overflow and shortfall. Do not collapse a trace containing
  different behaviors or intervening costs into a net rate.
- `MountMatch.attempt` captures **both** stamina bands before resolving and charging
  action/response costs (`engine/match.py`, around line 1360). Pass these captured
  bands to `exchange`, and keep the returned snapshot in history. A later depleted
  or recovered pool must never redefine that exchange's exhaustion modifier.

## Portable numeric/type boundary and remaining differences

Gameplay parity is verified for integer requests/configuration and the default
exhaustion modifiers. Capacity is explicitly restricted to `1..2^53-1` so JSON
numbers and double threshold calculations retain exact integer input values.
Requests and signed flow arithmetic use Godot int64. Before mutation, apply
rejects an overflowing product, overflowing carry sum, or -2^63 units (whose
negation cannot be represented). Python has unbounded integers; these rejection
boundaries are portability restrictions, not new gameplay costs or clamps.

Typed scalar APIs accept integers. Policy dictionary values must be native Godot
integers: floats and strings are rejected. Python's `isinstance(x, int)`
also accepts booleans. Policy builds preserve that surprising accepted case:
boolean rates compute as 0/1, and boolean costs compute as 0/1 while retaining
boolean type in serialized funding cost fields. Typed funding numeric properties
remain native ints. Godot JSON parses all numbers as floats; only the test adapter
restores integral fixture configuration values to native ints. Runtime validation
has no permissive numeric coercion. Future save/load requires an explicit typed,
versioned decoder, including exhaustion latch and meter carry; this PR implements
neither save/load nor a replay command schema.

The public Python presentation `display`, pacing projections, custom exhaustion
modifier configuration, `AdvanceResult` drift orchestration, and v0.4a commitment
grade/magnitude semantics are outside this primitive slice. No full MountMatch,
production recovery, terminal-match, duplicate-command, or full-engine parity is
claimed. Primitives permit repeated calls by design; command identity/terminal
checks belong to the future aggregate.

## Production recovery boundary: focused follow-up tasks

Source: `interfaces/production_policy.py`, `interfaces/recovery_policy.py`,
`interfaces/handoff_policy.py::D3BTokenLockoutController`, `interfaces/batch.py`,
and the settlement sections of `engine/match.py`.

1. **Port validated exchange/attempt settlement and v0.4a opt-in.** Required inputs:
   initiator/responder identity, legal technique/response, requested commitments,
   historical pre-cost bands, submission stage/setup and resolution. Required
   outputs: both funding/spend records, waiver, nominal/covered/supplemental hold
   charge, historical modifiers, resulting state. Freeze resolution before
   charging. Rule 1 ON must waive response **and** submission hold charges when
   the initiator is UNFUNDED. Rule 2 OFF keeps legacy hold settlement. Raw Mount
   defaults remain unchanged; compose a separate explicit production preset.
   Verify opt-in/off controls and atomic rejected attempts against Python before
   connecting this to presentation.
2. **Port advance and Bottom RECOVER decisions.** Advance must update both meters,
   pools, drift and clock in reference order. Supply post-advance latch observations
   and normal/free Bottom decision windows. RECOVER chooses LOW initiation while
   Exhausted, baseline MEDIUM after clear. RECOVER is a batch policy, not a sixth
   primitive behavior. Preserve measured E-PROD configuration validation; reject
   unsupported production configuration instead of falling back.
3. **Port D3-B only after those interfaces exist.** Controller state: `armed`,
   `token_consumed`, previous Bottom exhaustion. First observed Exhausted→clear
   after advance arms it and resets the token. An armed exhausted Bottom window
   consumes one token (adopted LOW attempt or a genuine RESET if no action chosen).
   Subsequent exhausted windows return LOCKOUT_HOLD until a clear is observed.
   `recovery_hold()` must consume no simulated time/stamina, pass initiative, and
   differ from RESET. Observe every advance, include free windows, reject Top
   decision calls, and never override chosen behavior. Generate full controller
   trajectories from Python before claiming production policy parity.

## Verification and self-review

Negative/reference tests were committed before the core modules (commit
`e47d37e`), with an initial missing-class failure recorded during development.
`generate_stamina_reference.py` invokes the unchanged Python APIs; it does not
reimplement the expected formulas. The runner checks every result field and pool
state after each operation, verifies unchanged state after rejection, and executes
the corpus twice from identical initial states. JSON expected integer outputs
must correspond to native Godot ints. Native tests additionally cover float/string
configuration rejection, Python boolean configuration compatibility, missing objects, overflow, copied configuration,
zero-cost funding, read-only property rejection, split/combined cumulative accounting and historical bands.
The native CI step verifies exactly two expected read-only error diagnostics and
rejects any unexpected script/engine errors; those two are deliberate negative
cases, not hidden test failures.
Fixtures are generated during CI, not checked in.

Principal self-review: a rejected spend cannot report fully paid; all validation precedes pool/meter mutations; policy builds
copy input; safe arithmetic guards precede multiplication/addition/negation; no
catch-all success or frame-time dependency exists; histories store bands rather
than recalculate them; no Match defaults changed. Side Control can reuse these
primitives without extracting a speculative engine framework. GDScript underscore
privacy and caller-owned mutable result objects remain language-level conventions.
