# Match Window Gateway

`BjjMatchWindowGateway` (`scripts/positions/mount/mount_window_gateway.gd`) is the narrow,
match-level owner of production decision windows for the headless Mount. It adds only
**window identity and admission**. It owns no grade, cost, recovery or token logic.

Built on branch `feat/godot-v1-match-window-gateway` from commit `d548358` (PositionContract + D3-B lifecycle stack). No Python source, frozen
fixture, D3-B controller, Mount rule or `project.godot` changed. Side Control, a human decision
timer, stalling, Recognition and any presentation layer are **not** part of this slice.

## Authorities it calls (unchanged)

| Intent | Executed by |
|---|---|
| Advance simulated time / consume an external free window | `BjjMountMatch.next_window()` (only place time moves) |
| Bottom decision (action, RESET, TOKEN, LOCKOUT_HOLD, selected commitment) | `BjjMountMatch.bottom_decision()` |
| Top exchange | `BjjMountContract.submit()` (== `attempt()`) |
| Top no-action | `BjjMountMatch.reset_window()` |

`create(configuration, top_id, bottom_id)` builds and owns a production match
(`production` is forced on and cannot be disabled; raw/unsupported rules are rejected by
`BjjMountMatch.create`). Because the gateway owns the match, no caller holds a mutable
reference. Views (`state_fields`, `history_fields`, `controller_fields`, `window_fields`,
menus, `roles`) and every `Report` are detached copies.

## Window lifecycle

`open_window()` advances the match's own interval; `open_window_for(seconds)` is an explicit
session-owner/test seam (trusted simulated seconds, never exposed to a human UI) and
each opens **at most one** window with a monotonically increasing `window_id`. `submit(window_id,
fighter_id, action, response, commitment, response_commitment)` closes it with exactly one
accepted decision. Free windows consume the external beneficiary flag without advancing time.
A match that ends on advance or decision opens no window.

Rejection order, all before any mutation: `window_already_open` / match context errors
(`terminal_exchange`, ...) / `invalid_duration` / `invalid_window_request` for opening;
`no_open_window` → `stale_window` → context errors → `window_initiator_changed` →
`missing_fighter_id` / `unknown_fighter` → `not_initiator` → `response_without_action` →
`commitment_is_policy_selected` (Bottom) → `commitment_without_action` (no-action) → the owners' own admission codes unchanged.

Bottom cannot supply a commitment: `bottom_decision` applies the selected policy (LOW while
Exhausted, baseline MEDIUM after clear). Top may request LOW/MEDIUM/HIGH, defaulting to the
selected baseline.

## Evidence

`tests/test_window_gateway_boundaries.gd`: negative-first admission with whole-state
(match, histories, D3-B, window record) equality after every rejection; D3-B sequences
(clear → ARMED_NORMAL → TOKEN → LOCKOUT_HOLD with zero time/stamina → new episode RESET);
free-window ownership; timeout and exit terminals; detachment; and 36 configured lockstep trajectories
(4 Bottom stamina starts × 3 axes × 3 seeds, each replayed twice; each runs up to 160 steps and stops early on a terminal) against a twin driven only by
`next_window`/`bottom_decision`/`attempt`/`reset_window`, comparing results, lifecycle state,
controller state and histories after every operation. The twin entry points are covered by the existing D3-B, lifecycle and exchange Python-oracle suites,
so the gateway inherits that parity by inference; it has no Python-oracle comparison of its own and
this slice adds no new Python generator.

```bash
godot --headless --path GODOT_V1 --script res://tests/test_window_gateway_boundaries.gd
```

## Known limits

- Top RESET is admitted through the existing `reset_window()`; whether human Top may RESET is a rules decision that was not made here.
- Mount `Reversal` still has no declared landing; it surfaces as an unresolved exit.
- A decision timer, stalling-generated free windows and non-Mount positions are future work.
- `transition.resolved` means the destination id is *declared* (`half_guard`, `open_guard`), not that a receiving position exists. The gateway creates no new position; the Mount match ends at the exit.
- `role` in a window/report is the position-local side holding that window, not control authority. Control authority stays with the Top fighter (`roles().control_authority_id`).
- Production cadence is the match interval via `open_window()`. Zero-time windows occur only through the D3-B HOLD/free-window paths or the explicit `open_window_for` seam.
