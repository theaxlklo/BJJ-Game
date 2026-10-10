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
