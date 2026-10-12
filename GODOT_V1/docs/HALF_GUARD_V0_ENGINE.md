# Half Guard v0 typed GDScript engine (B1b)

**Status: provisional v0 prototype baseline, not final game balance.** Implements [HALF_GUARD_V0_RULES.md](HALF_GUARD_V0_RULES.md) (C1 grades, decisions N-1 … N-11) in typed GDScript and is compared, cell for cell, with the independent Python oracle ([HALF_GUARD_V0_ORACLE.md](HALF_GUARD_V0_ORACLE.md)).
It is a headless, deterministic position implementation. The engine itself changes **no** Mount, F0 or F1 behavior. Two later slices connect it, both additive and neither enabling Half Guard in F1: the Mount edge adapter (B1c, `BjjHalfGuardMountEdge`, a pure Mount-record-to-entry-request converter) and the **opt-in** graph integration (B1d, see "Graph integration" below). `BjjPositionGraphMatch.create` still builds a Mount-only graph in which every Mount exit halts, F1 uses `create`, and nothing in F1 or F0 can start, enter or render Half Guard.

## Files (`GODOT_V1/scripts/positions/half_guard/`)

| Class | Role |
| --- | --- |
| `BjjHalfGuardRules` | Constants and pure axis/band rules (integer tenths, hysteresis, legal pairs, authority, shift tables) |
| `BjjHalfGuardCatalog` | Stable ids, the 15 C1 raw grades, governed responses, builders, exit destinations, the transition dictionary |
| `BjjHalfGuardResolver` | Pure grade pipeline, exit decision and readiness updates (no state) |
| `BjjHalfGuardEntry` | Pure fighter-id-keyed entry validation (first failing code) |
| `BjjHalfGuardMatch` | **The single mutable owner of simulation state**: axis, band, initiative, both stamina pools, both readiness integers, clock, window record, histories; `attempt`, `open_window_for`, `decide` |
| `BjjHalfGuardContract` | `BjjPositionContract` adapter (roles, authority, initiative, options, low-level `submit`, `Transition`) |
| `BjjHalfGuardWindowGateway` | Production-facing facade: reports (`BjjMatchWindowGateway.Report`), detached views, `snapshot()` |

Shared stamina and commitment primitives are reused **unchanged** (`BjjStaminaPool`, `BjjStaminaCostPolicy`, `BjjCommitment`, `BjjCommitmentSettlement`, `BjjExhaustionPolicy`, `BjjGrade`, the `Meter` type). There is no generic tactical framework and no shared preparation type: the two readiness tiers are two integers in the match.

## API

```gdscript
var created := BjjHalfGuardWindowGateway.create(entry)      # entry: the neutral fighter-id-keyed request (rules sheet section 4)
var gateway := created.gateway                               # created.error is a stable code; nothing is built on error
var opened := gateway.open_window()                          # BjjMatchWindowGateway.Report; open_window_for(duration) is the session-owner seam
var report := gateway.submit(window_id, fighter_id, action_id, response_id, commitment, response_commitment)   # empty action = pass
gateway.state_fields(); gateway.history_fields(); gateway.roles(); gateway.window_fields(); gateway.snapshot()
gateway.action_options(fighter_id); gateway.response_options(action_id); gateway.selected_commitment()
gateway.controller_fields()    # {}  (no D3-B)           gateway.behavior_fields()   # {"top": "", "bottom": ""} (no behaviors)
```

A successful submit report carries `kind` (`exchange` | `reset`), `detail.settlement`, `transition` (`BjjPositionContract.Transition.fields()` semantics: `none`, or `exit` with a resolved `side_control` / `open_guard` / `closed_guard`), `ended` and a detached `state`.
Every refusal is a stable code with no mutation of any kind. There is no `carryover_segment()` (the export envelope is a later schema decision).

## Qualification evidence

| Suite | Pin | What it proves |
| --- | --- | --- |
| `test_half_guard_boundaries.gd` | 4,006 assertions | Negative-first: entry refusals and precedence, Godot-measured fighter-id edges, latch restoration against a literal hysteresis model, context corruption, command refusal precedence, windows and timeouts, pipeline and readiness literals, Rule 1 / paid effort, exits and transitions, contract addressing, detached views, determinism, scope and hygiene scans |
| `test_half_guard_reference.gd` | 49,609 assertions | Replays the oracle fixture (16,858 rows: bands, entries, 13,365 exchange-grid and 2,916 break-grid rows rebuilt from full snapshots, 10 window trajectories replayed twice) with 0 mismatches |
| `test_half_guard_conformance.gd` | 151 assertions | Report shapes, shared view keys and shared admission codes agree with the Mount window gateway; time advances identically |

The counts are measured by the suites and pinned in `.github/workflows/godot-v1.yml` and `tools/ci/test_validate_mount_slice_log.py`; they change only with a reviewed change to the suite or the oracle. A development-time mutation control (disposable edits, not committed) confirmed that ten engine mutations — the C0 grade, the defense shift, paid-effort preservation, the Rule 1 waiver, latch restoration, initiative on an exit, the pass line, a hysteresis threshold, LOW-defense strength and readiness consumption — are each detected by these suites.

## Known limitations

* Reachable only through an opt-in graph (`create_with_receivers`) or directly through the gateway; F0 and F1 do not use it and there is no UI. There is no Half Guard carry-over export (the graph refuses one) and no return route.
* No feints, behaviors, drift, recovery or D3-B (all explicitly later work). Direct techniques only. The match itself has no sealed intent; the two-phase sealed-intent protocol (B1g) is a separate, explicit opt-in object that wraps the unchanged gateway (see the last section).
* Stamina-state corruption (an out-of-range pool value) is not representable (the pool refuses it); context corruption is exercised through plain field assignment on the match.
* `BjjHalfGuardMatch.new()` is not a supported construction path; a match is built only from an entry request.
* The oracle fixture is large (tens of megabytes) and generated at test time; it is git-ignored.

## Graph integration (B1d, opt-in)

`BjjPositionGraphMatch.create_with_receivers(configuration, top_id, bottom_id, receivers)` builds the Mount graph with a receiver table; `create` is unchanged and builds none.
`receivers` must be a `Dictionary` whose keys are a subset of `{"half_guard"}` and whose values are valid two-argument `Callable`s `(record, interval_seconds) -> BjjHalfGuardWindowGateway.Creation`; anything else builds no graph and returns `invalid_receivers`. An empty table is observably identical to `create`. `BjjPositionGraphMatch.default_receivers()` returns the Half Guard edge for future callers and tests (no production caller exists). The cadence handed to a receiver is the graph's own `configuration.interval` (default: `BjjMountRules.DEFAULT_INTERVAL_SECONDS`).

The graph owns the **choice of the active position** (`active_position_id()`: `"mount"` or `"half_guard"`); each position owns its own mechanics. At every moment of an active match exactly one position accepts commands. A transition replaces that owner in one step and the previous segment is retained as frozen history.

After an accepted Mount decision whose exit label is registered, the graph (1) takes the validated A3b record from the retained Mount gateway, (2) computes its **own** expected entry request and fresh reference snapshot with the edge adapter and the Half Guard entry, (3) calls the receiver with a detached record copy, (4) checks the returned object is a `BjjHalfGuardWindowGateway.Creation` with a gateway and compares the gateway's detached views with the expected request (roles, per-fighter-id stamina, maximum, latch and meter, both clocks, window counter, cadence, entry axis, band, readiness, initiative, empty history, no open window) and with the fresh snapshot, (5) confirms the retained Mount segment's public views and export are unchanged, and only then (6) sets the typed `_half_guard` slot and appends exactly one `transition_committed`. It opens no window, charges nothing and moves no clock; the first Half Guard window opens on a later caller request, with window ids continuing from the Mount counter.

If step 2-5 fails after the exchange was accepted, the exchange stays settled (there is no rollback; see the `POSITION_GRAPH.md` §5/§8 amendment): the graph appends `transition_blocked` with reason `transition_entry_invalid`, halts, and activates nothing. Open Guard and Reversal (and Mount exits on a graph with no receiver) halt exactly as before. A Half Guard exit (`Side Control`, `Open Guard`, `Closed Guard`) halts with `transition_blocked` and `from_position_id = "half_guard"`; a Half Guard timeout is a terminal outcome, never an exit. While Half Guard is active `carryover_export()` is refused with `carryover_unsupported_position`; no v2 schema exists, and the unchanged v1 validator refuses a graph halted with `transition_entry_invalid` (`inconsistent_graph_segment`).

A halt at an unsupported transition is an **incomplete-engine boundary**, not a state of a finished playable game. `test_half_guard_graph.gd` pins this slice (see the CI step); two private-property pins in `test_position_graph_boundaries.gd` and `test_carryover_export.gd` were revised on purpose (HG-16).

## Sealed-intent protocol (B1g, explicit opt-in)

`BjjHalfGuardSealedProtocol` (`half_guard_sealed_protocol.gd`) is the Half Guard-only commit-and-reveal path of `TACTICAL_PREPARATION_AND_FEINTS.md` §7. It is a **protocol slice, not a feint slice**: the sealed technique is the direct technique (the real technique equals the apparent technique), and fake-to-real pairs, the surcharge, bite adjustments and counterplay gates are B1h. It **wraps an unchanged `BjjHalfGuardWindowGateway`** that it builds and owns, so the positional simulator stays the single authority for grades, stamina charges, readiness, axis, initiative and exits; the protocol contains no resolver and reaches `gateway.submit` only in its gated pass-through and in its one resolution call. No engine, gateway, graph, Mount, F0 or F1 source was edited, and none references the protocol (a scan test pins this). The existing one-call `BjjHalfGuardWindowGateway.submit` and the graph's Half Guard slot are unchanged: **the graph does not route through the protocol**, and a graph-held gateway cannot be reached from it (whether and how the graph should expose it is an owner decision, below).

`BjjHalfGuardSealedProtocol.create(entry) -> Creation{error, protocol}` takes the same entry request as the gateway. Commands return the shared `BjjMatchWindowGateway.Report`; every returned value is detached.

| Call | Meaning |
| --- | --- |
| `open_window()`, `open_window_for(duration)` | The gateway's own time seam (unchanged); a window can never open over another, so a seal cannot be overtaken |
| `seal_intent(window_id, fighter_id, action_id, commitment = "")` | The initiator seals ONE direct technique and its commitment (empty = the selected commitment) for the open window. Nothing in the simulation changes. The report is the public view |
| `respond(window_id, fighter_id, intent_serial, response_id, response_commitment = "")` | The responder commits a response chosen from `public_intent_view()`. The same call hands the resolved command to `gateway.submit`: one window, one accepted exchange, one initiative advancement, one clock (already advanced by the window) |
| `apply_response_timeout(window_id, intent_serial, fallback_response_id, fallback_response_commitment = "")` | Session-layer timeout seam (Guide §5.2a): the **session supplies** the published fallback; it is checked as a legal response for the sealed technique and resolved exactly like `respond`, flagged `defaulted` in the events. The protocol invents no fallback table |
| `submit(...)` | The existing one-call decision (an exchange or a pass), unchanged semantics, refused with `intent_pending` while a seal is pending |
| `end_session()` | Discards an unresolved seal (never resolves it) and refuses every later command |
| `public_intent_view()` | Closed schema, exactly: `position_id, window_id, intent_serial, initiator_id, responder_id, apparent_technique_id, apparent_technique_name, response_ids` |
| `sealed_intent_view(fighter_id)` | The initiator's own seal; anyone else gets `not_intent_owner` |
| `public_events()` / `protocol_events()` | Redacted public stream / executor log: `intent_sealed` → `response_committed` → `exchange_revealed` (+ `session_closed`); the sealed commitment is public only in `exchange_revealed` |
| `executor_snapshot()` | Gateway snapshot + sealed store + serial + events + closed flag, for replay and parity tests; never hand it to a controller |

Refusals (all leave the **whole executor state** unchanged, and depend only on public state and the caller's own command): seal — `session_closed`, `no_open_window`, `stale_window`, the gateway's addressing/context codes (`missing_fighter_id`, `unknown_fighter`, ...), `not_initiator`, `intent_already_sealed`, `unknown_action`, `invalid_commitment`; respond — `session_closed`, `no_open_window`, `stale_window`, `no_sealed_intent`, `intent_serial_mismatch`, `missing_fighter_id`, `unknown_fighter`, `not_responder`, `unknown_response`, `invalid_response_commitment`. A refused response keeps the seal and the window, so a valid retry is possible. A seal is irrevocable while the session lives.

**Unresolved seals.** A window cannot close without resolving: a pending seal blocks `open_window`, the legacy `submit` and a pass, and the match clock cannot move while the window is open. A timeout resolves through the session-supplied fallback; a session end discards the seal with no exchange, charge, history entry or clock change. After either, nothing is pending, so nothing half-committed can reach the next window. There is no persistence of a pending seal across processes.

**Information isolation (accurate scope).** The responder's controller is handed only detached dictionaries built from an allow-list; the sealed commitment is not in any of them, and refusal codes, option menus, the public view, the gateway views and the public event stream are byte-identical for any sealed commitment (tested). GDScript has no private members: any in-process code that holds the protocol object can read `_pending`. This is architectural discipline plus tests, **not** a security boundary and not cryptographic protection. In B1g the apparent and the real technique are the same, so the technique is public by design; only the commitment is hidden until the reveal.

Open owner decisions that shape B1h (none blocks B1g): GP-3 (is the requested commitment a public cue? — B1g omits it, which is the conservative reading and a one-line additive change), GP-5 (the published Half Guard fallback table for a timed-out responder), GP-4 (irrevocability is implemented but not yet accepted), GP-2 (publishing the list of eligible real techniques; no such list exists while real = apparent), and the graph exposure of the protocol. `test_half_guard_sealed_protocol.gd` pins this slice (see the CI step).
