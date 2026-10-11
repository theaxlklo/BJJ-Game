# Mount carry-over export (A3b)

Status: additive, read-only, validated, detached record of Mount state that a future position
transition may need. **No receiver exists.** Nothing here creates a Half Guard, commits a graph
transition, re-arms D3-B, changes stamina policy or defines a combat rule. Python is untouched.
See [POSITION_TOPOLOGY.md](POSITION_TOPOLOGY.md) (A3c, proposal) for how this v1 record relates to a wider
topology and how it would be versioned when a destination becomes executable.

## Ownership boundaries

The gateway and graph each build their own block from state they already own; a pure validator class
(`BjjMountCarryover`) reads no production state. No outside class reads an underscore member.

| Fact | Owner (unchanged) | Read by |
| --- | --- | --- |
| Fighter ids by physical role | gateway (`_top_id`/`_bottom_id`) | `BjjMatchWindowGateway.carryover_segment()` |
| Stamina current/maximum, latch | `BjjStaminaPool` | `current`, `maximum`, `band == "Exhausted"` (the band IS the latch) |
| Behavior-meter remainders | `BjjMountMatch.top_meter/bottom_meter` | `remainder_units`, via the gateway's own `_match` |
| Initial / remaining simulated clock, ended, tapped | `BjjMountExchange.snapshot()` | snapshot |
| Last issued window id | gateway `_window_id` | read only, never incremented |
| D3-B | `BjjD3BController` | `armed`, `token_consumed`, `previous_exhausted` |
| Exit label and declared destination | `BjjMountContract.transition_for()` | single mapping, not re-implemented |
| Graph status, global event count, blocked transition | `BjjPositionGraphMatch` | `BjjPositionGraphMatch.carryover_export()` |

The gateway exports **segment** facts only and owns no event count. The graph adds its own block
beside (never inside) the segment. Mount history stays Mount history and is not copied: the record
invents no cross-position history or event. `BjjD3BController.initialized` is a constant `true` for
every gateway-built match, so it is not exported.

Export never calls `validate_context()` (it returns `terminal_exchange` after an exit, timeout or tap);
export must work in those states. It is refused only while a window is open (`window_open`): a pending
window is not a transition point and a receiver cannot inherit it. Export after `open_window` closes the
match at timeout leaves `last_issued_id` at its previous value (nothing was issued).

## Segment record, `mount_carryover` version 1

All values are `int`, `bool` or `String`; no floats and no shared containers.

```
{
  "schema": "mount_carryover", "version": 1, "source_position_id": "mount",
  "fighter_by_role": {"top": <id>, "bottom": <id>},      # source Mount roles; no authority/initiative
  "fighters": {
    "top":    {"stamina_current": int, "stamina_maximum": int,
               "exhaustion_latched": bool, "behavior_remainder_units": int},
    "bottom": {...same...}},
  "clock":    {"initial_seconds": int, "remaining_seconds": int},
  "window":   {"last_issued_id": int},                   # last ISSUED id, not next
  "d3b":      {"armed": bool, "token_consumed": bool, "previous_exhausted": bool},
  "terminal": {"ended": bool, "submission_tapped": bool},
  "exit":     {"kind": "none"|"exit", "raw_destination": String,
               "destination_position_id": String, "resolved": bool}   # = Transition.fields()
}
```

## Graph envelope, `position_graph_carryover` version 1

`{"schema", "version": 1, "segment": <mount_carryover>, "graph": {"status", "event_count", "blocked_transition"}}`
`blocked_transition` is `{}` or exactly `{from_position_id, label, reason, destination_position_id}`.
Cross-checks: halted <=> non-empty blocked <=> `segment.exit.kind == "exit"`, and the blocked label and
destination equal the segment exit; `ended` status requires `segment.terminal.ended` and no exit; `active`
requires neither. The blocked transition stays recorded graph data, never an executed transition.
The blocked `reason` is validated against the segment exit: a resolved exit (`Half Guard`, `Open Guard`) requires
`destination_not_implemented`, an unresolved one (`Reversal`) requires `unresolved_destination`. It is derived from the
validated exit's `resolved` flag, not from a second label mapping. **This is a v1 assumption** that no destination
position is implemented: when one is, halted-export validation (reasons, and the `ended`-with-exit rejection)
must be updated deliberately, together with a schema version decision.

## Validation (exact keys, exact types, no side effects, never calls validate_context)

* Exact key sets at every level; `int` is not accepted for `bool` or the reverse; no floats.
* Fighter ids pass `BjjPositionContract.fighter_ids_error`.
* Stamina: `maximum` in 1..`BjjStaminaPool.MAXIMUM_EXACT`, `current` in 0..maximum; the latch uses the
  pool's own thresholds (`BjjStaminaPool.create(...)`): `current <= enter` => latched, `current >= recover`
  => not latched, between => either (hysteresis). Remainders are ints within +/-`MAXIMUM_EXACT`.
* Clock: initial 1..`MAXIMUM_EXACT`, remaining 0..initial. `last_issued_id` >= 0.
* D3-B: `token_consumed` => `armed` (the controller consumes only while armed). `previous_exhausted` is
  NOT cross-checked with the current latch: stamina can change after the last D3-B observation.
* Terminal: `ended == (remaining == 0 or tapped or exit.kind == "exit")`; an exit requires remaining >= 1
  (the clock does not move during a decision).
* Exit: label must be a key of `BjjMountContract.EXIT_DESTINATIONS` or in `UNRESOLVED_EXITS`; fields must
  equal `BjjMountContract.transition_for(label).fields()`. `Reversal` stays unresolved, destination empty.

Export is `validate(build(...))`: an inconsistent source yields an error code and no record.

## Deliberately NOT exported (decision gates, not invented here)

* Mount-local control (axis, band), setup tiers, submission stage, behaviors: meaningless to a receiver
  without a new rule.
* Initiative and control authority, in Mount or in a receiver: not exported; the receiving position decides.
* Clock interval, behavior-rate policy, RECOVER/baseline configuration, rules flags.
* A receiver-side pool factory that accepts a hysteresis latch: `BjjStaminaPool.create` derives the latch
  from `current` only, so importing a latched-between-thresholds pool needs a separate decision.
* D3-B re-arming or applicability in another position.

## Notes and known limits

* `missing_carryover_source` / `missing_d3b_controller` guard code paths that no public API can reach
  (a gateway always builds its match, meters and D3-B); they are untested by design.
* Records hold only `int`, `bool` and `String`. A JSON round trip turns ints into floats, which the
  validator rejects on purpose; a future serializer must restore ints before validating.
* A graph status of `ended` together with an exit record fails validation. Today every Mount exit label
  classifies as blocked and halts, so this cannot occur; if a future receiver makes an exit non-blocked,
  the envelope contract must be revisited deliberately (fail-closed).
* The Mount layer does not depend on the graph class: the graph status names are repeated as literals in
  `BjjMountCarryover` and pinned to the graph's constants by the test.
* Behavior-meter remainders are checked against the meters the exporter reads and against role swaps; no
  independent literal expectation exists for a nonzero remainder value. Exact remainder arithmetic stays
  covered by the existing stamina/lifecycle parity suites, not by this export.
* A real Americana tap, a timeout and all three exits are exercised through the public commands.
