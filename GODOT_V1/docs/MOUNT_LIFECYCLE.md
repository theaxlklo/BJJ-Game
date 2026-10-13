# Headless Mount lifecycle — incremental port

## Advancement and Bottom RECOVER (Issue #20)

`BjjMountMatch` extends the existing exchange implementation; it does not
introduce a second stamina or action resolver. `advance(integer_seconds)` uses
`MountMatch.advance()` ordering: drift/clock, behavior history, Top flow, Bottom
flow, flow histories. Its default interval is five simulated seconds. Both flows
are preflighted on detached pools/meters so overflow cannot partially commit.
`Advance` stores detached results, not references to mutable fighter state.

`configure_recover` selects batch-style Bottom RECOVER independently of raw
match rules. `recovery_advance` chooses CONSERVE before advance while latched
Exhausted and restores its baseline immediately after a clear, before action
resolution. `selected_commitment` requests LOW for Exhausted Bottom and the
baseline commitment otherwise. RECOVER remains outside the five primitive
behaviors. `configure_production_recover` requires caller-selected setup,
v0.4a, Rule 1 ON and Rule 2 OFF; it selects ESCAPE/MEDIUM. It does not silently
turn match features on. D3-B is a subsequent controller milestone.

Source mapping: `engine/match.py::{advance,drift}`, `engine/stamina.py`,
`interfaces/batch.py::{AdaptiveBehaviorPolicy,run_batch}` and
`interfaces/production_policy.py`. Shared admission invariants now have one
`validate_context` implementation, used by exchanges and advancement.

The unchanged Python APIs generate 756 independent trajectories / 5,418
operations over all nine behavior pairs, capacities 7/100/101, resource and
latch thresholds, recovery on/off, negative/zero/truncated intervals and split
intervals. Two replays produce 1,658,052 comparisons with zero mismatches.
Negative RECOVER duration is a Godot admission test, not a Python batch trace:
batch never admits a negative interval, and externally mutating Python's
interval after changing behavior is outside that policy boundary.

Frozen `advance()` can run at timeout with zero elapsed duration and can still
advance after Tap; this is preserved, including history records. A normal
frontend loop stops on `ended`. Broken-position advancement rejects without
mutation. Exchanges keep the previously approved atomic terminal rejection.

## Scope boundary

Stalling and Recognition feature flags remain explicitly unsupported, rather
than being silently downgraded. This milestone is advancement/RECOVER, not
complete MountMatch or full production policy parity. D3-B, decision-window
handoff and integrated match trajectories remain to be qualified separately.
No Python source or frozen expectations changed; no third-party code adopted.

## D3-B and integrated lifecycle (Issue #21)

`BjjD3BController` ports the frozen Python controller's armed flag, consumed
flag and previous Bottom exhaustion. Successful advance observes the latch
before post-advance RECOVER re-choice. A clear arms/reset tokens; subsequent
Exhausted windows use TOKEN then LOCKOUT_HOLD. It never overrides behavior.
`bottom_decision` validates a supplied command before changing controller state;
TOKEN runs the adopted LOW attempt or a genuine RESET when no action is chosen.
LOCKOUT_HOLD performs a distinct recovery hold with no time/stamina/setup change.
No deduplication protocol, timer or random policy was introduced.

`BjjMountMatch.create(configuration)` validates construction and returns a typed
creation result. Explicit operations are `advance`, `recovery_advance`,
`next_window`, `attempt` (inherited), `bottom_decision`, `reset_window`,
`recovery_hold`, `consume_free_window`, `legal_actions`, `legal_responses`, and
`decide_legacy`. `next_window` advances normal windows but consumes free windows
without advancement. Free-window ownership is an honest integration boundary:
this core does not generate stalling penalties/free windows itself.

`configure_production` requires the measured E-PROD configuration, then selects
RECOVER and D3-B. Repeated selection preserves controller state and cannot refill
a token. Raw construction remains opt-out. The controller can also be tested
separately without selecting production. Result dictionaries are detached
serialization records; funding, pools, meters, resolutions and controller state
remain typed objects. Lifecycle state is independent of SceneTree/Node/rendering.

The Python generator executes 72 independent scenarios / 1,550 operations,
including complete builder → Ready → Americana Threat → Control → Finish → Tap
sequences with naturally alternating RESET windows, successful Open Guard
exits, timeout, legacy decisions, production on/off, all resource thresholds,
initial exhaustion, re-exhaustion, clears, token RESETs and free-window ownership.
Positive Tap traces assert completion and zero rejected operations at generation.
Two replays compare 596,644 values/structures with zero mismatches, including
legal menus and complete histories. 61 native assertions cover factory admission,
Top/terminal/invalid command rejection, unchanged state, hold versus RESET,
free windows, configuration idempotence and zero-time behavior.

### Exact completion boundary

The **headless Mount core lifecycle** supports frozen v0 actions and drift,
modern setup/Americana submissions, commitment semantics, generic stamina,
production settlement, RECOVER, D3-B, initiative, normal timing and terminal
outcomes. It is usable without graphics. This is not all-optional-feature
`MountMatch` parity: v0.3b stalling, v0.4b Recognition, scoring/diagnostic collectors,
random batch AI and custom setup/exhaustion/catalog policies remain unported.
Their enabling flags are rejected. Generated free windows require a future
stalling port; consuming a valid externally supplied free window is covered.
The existing three approved exchange terminal differences remain documented in
`EXCHANGE_SETTLEMENT.md`; four older boundary operations are excluded there.
The new D3-B corpus has no excluded terminal operations. Menu/window entry points
reject ended match state; no equivalence is claimed for Python queries that
continue returning legal menus after a match ends.

Principal review checked pre-charge history, sequential clamping, charge order,
production opt-in, latch observation, repeated configuration and alias isolation.
The repeated-configuration token refill was corrected before submission. No
reproducible mismatch remains in the supported slice. No third-party dependencies
or copied code were introduced. Python reference source/tests remain untouched.
