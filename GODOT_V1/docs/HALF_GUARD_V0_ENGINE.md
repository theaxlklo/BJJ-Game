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
* No behaviors, drift, recovery or D3-B (all explicitly later work). Direct techniques plus (B1h) the two explicit feint pairs of `HALF_GUARD_V0_RULES.md` §13, which are an optional input to the same settlement path (an empty real technique is the unchanged direct path). The match itself has no sealed intent; the two-phase sealed-intent protocol (B1g/B1h) is a separate, explicit opt-in object that wraps the gateway (see the last section).
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

## Sealed-intent protocol and feints (B1g protocol, B1h feints; explicit opt-in)

`BjjHalfGuardSealedProtocol` (`half_guard_sealed_protocol.gd`) is the Half Guard-only commit-and-reveal path of `TACTICAL_PREPARATION_AND_FEINTS.md` §7. B1g added the protocol for direct techniques; **B1h** adds the two explicit feint pairs on top of it (rules: `HALF_GUARD_V0_RULES.md` §13, oracle: `HALF_GUARD_V0_ORACLE.md`). It wraps a `BjjHalfGuardWindowGateway` (`create(entry)` builds and owns its own; B1i `adopt(gateway)` attaches to the position graph's already-constructed one), so the positional simulator stays the single authority for grades, stamina charges, readiness, axis, initiative and exits; the protocol contains no resolver, copies no rule table and reaches the gateway's `submit` / `submit_feint` only in its gated pass-through and its one resolution call. Mount, F0 and F1 do not reference it. Since B1i the position graph can adopt it **only through its explicit opt-in constructor** (`create_with_sealed_half_guard`, see the B1i section below); every other graph (`create`, `create_with_receivers`) is unchanged and routes nothing through it.

### What B1h added to the engine (minimum, one pipeline)

* `BjjHalfGuardMatch.attempt(..., real_action_id = "")` / `decide(..., real_action_id = "")`: a non-empty real technique makes the command a feint; **the real technique settles through the same pipeline** (admission → capture → grade → axis/exit/initiative → charges → readiness → histories). `feint_error(apparent, real, commitment)` is the pure admission/funding check (also used by the protocol at seal time).
* `BjjHalfGuardResolver`: one extra step between the defense readiness shift and exhaustion (`grade_after_feint`, `feint_modifier` ±1, saturating on its own) and the LOW-effective exit cap (`exit_capped`). Direct inputs leave both at zero.
* `BjjHalfGuardCatalog`: `FEINT_PAIRS` (FP-1, FP-2), `TIMEOUT_FALLBACK`, `eligible_real_ids`, `timeout_fallback`. `BjjHalfGuardRules.FEINT_SURCHARGE = 3`.
* `BjjHalfGuardWindowGateway`: `submit_feint(...)`, and the pure reads `feint_error(...)` / `eligible_real_ids(apparent)`. `submit` and every other qualified method are unchanged.
* Records: a feint record carries every key of the direct record plus one `feint` sub-record (`apparent_action_id`, `real_action_id`, `bite_response_id`, `bit`, `modifier`, `grade_before`, `grade_after`, `surcharge`, `surcharge_charged`, `total_cost`, `exit_capped`). **No direct record, history or snapshot gained a key**; `initiated_action_history` holds the real id. `initiator_effective_cost` is the cost of the effective commitment and `initiator_charged` is the total (including the 3 surcharge).

### Feint behavior in one place

| Item | Rule |
| --- | --- |
| Pairs | FP-1 Top Crossface → Knee Slice (`top_base ≥ Partial`, bite = Underhook Fight); FP-2 Bottom Underhook → Recover Guard (`bottom_frame ≥ Partial`, bite = Head Control). Flatten → Knee Slice is excluded. The real technique must differ, share the side, be listed, be break-capable and meet the condition |
| Grade | `raw[real][response]` → positional → attack readiness (real) → defense readiness → **bite `+1` / otherwise `−1`** → exhaustion → magnitude → undercommitment, each step saturating at ±2 |
| Funding | `S < 3` refused; `determine(requested, S − 3)`; unfunded refused; total `3 + cost(effective)` charged once. Needs `S ≥ 6`. HIGH: 0–5 refused, 6–9 LOW (6), 10–14 MEDIUM (10), 15+ HIGH (15). The responder pays the normal cost and never a surcharge; a funded feint never triggers Rule 1's waiver |
| Exit cap | A feint whose **funded effective** commitment is LOW may resolve, move the axis and build tiers but cannot exit; MEDIUM/HIGH follow the real technique's exit rule |
| Refusals | after the direct checks: `feint_real_equals_apparent`, `unknown_action` / `incorrect_action_side_or_kind` (real id), `feint_not_supported`, `feint_not_eligible`, `feint_requires_funding`; `feint_without_action` at `submit` |

### Protocol API

`BjjHalfGuardSealedProtocol.create(entry) -> Creation{error, protocol}` takes the same entry request as the gateway. Commands return the shared `BjjMatchWindowGateway.Report`; every returned value is detached.

| Call | Meaning |
| --- | --- |
| `open_window()`, `open_window_for(duration)` | The gateway's own time seam (unchanged); a window can never open over another, so a seal cannot be overtaken |
| `seal_intent(window_id, fighter_id, action_id, commitment = "", real_action_id = "")` | The initiator seals the apparent technique, its requested commitment (empty = the selected commitment) and, privately, no real technique (a direct command) or the real technique of an explicit pair. A feint is admitted and funded by the match's own rules at seal time. Nothing in the simulation changes (no surcharge is reserved). The report is the public view. GP-4: irrevocable |
| `respond(window_id, fighter_id, intent_serial, response_id, response_commitment = "")` | The responder commits a response chosen from `public_intent_view()`. The same call hands the resolved command to the gateway: one window, one accepted exchange, one initiative advancement, no clock movement |
| `apply_response_timeout(window_id, intent_serial, fallback_response_id, fallback_response_commitment = "")` | Session-layer ordinary-decision timeout. The session supplies the **published fallback of the defender's role** (`BjjHalfGuardCatalog.timeout_fallback`: Bottom Hip Frame LOW, Top Hip Pressure LOW); anything else is `fallback_not_published`. It resolves exactly like `respond` and is flagged `defaulted` in the protocol events only |
| `submit(...)` | The existing one-call decision (an exchange or a pass), unchanged semantics, refused with `intent_pending` while a seal is pending |
| `end_session()` | Discards an unresolved seal (never resolves it, never reserves or charges anything) and refuses every later command |
| `public_intent_view()` | Closed schema, exactly: `position_id, window_id, intent_serial, initiator_id, responder_id, apparent_technique_id, apparent_technique_name, commitment_requested, eligible_real_ids, response_ids` |
| `sealed_intent_view(fighter_id)` | The initiator's own seal (`real_action_id` included); anyone else gets `not_intent_owner` |
| `public_events()` / `protocol_events()` | Redacted public stream / executor log: `intent_sealed` → `response_committed` → `exchange_revealed` (+ `session_closed`). The public `intent_sealed` carries the requested commitment but never the real technique; `exchange_revealed` discloses `apparent_action_id`, `action_id` (the real one), `feint` and the settlement |
| `executor_snapshot()` | Gateway snapshot + sealed store + serial + events + closed flag, for replay and parity tests; never hand it to a controller |

**Public information (GP-2, GP-3, accepted provisionally).** The defender sees the apparent technique, the **requested** commitment, and `eligible_real_ids`: the real techniques the apparent technique may conceal in the visible state (the pair table crossed with the public tier; it ignores stamina and funding and is the same whatever was sealed). It never sees the real technique, whether the command is a feint, the funded effective commitment or a downgrade, a surcharge or a funding result. For a given visible state, apparent technique and requested commitment, a direct command and an eligible feint produce identical public views, events, menus and refusal codes (tested field by field). If the list is empty the defender can infer the command is direct; that is the published consequence of GP-2.

Refusals (all leave the **whole executor state** unchanged and depend only on public state and the caller's own command): seal — `session_closed`, `no_open_window`, `stale_window`, the gateway's addressing/context codes, `not_initiator`, `intent_already_sealed`, `unknown_action`, `invalid_commitment`, then (a feint) `feint_real_equals_apparent`, `incorrect_action_side_or_kind`, `feint_not_supported`, `feint_not_eligible`, `feint_requires_funding`; respond — `session_closed`, `no_open_window`, `stale_window`, `no_sealed_intent`, `intent_serial_mismatch`, `missing_fighter_id`, `unknown_fighter`, `not_responder`, `unknown_response`, `invalid_response_commitment`; timeout — the same window/seal/serial codes, then `fallback_not_published`. A refused response keeps the seal and the window, so a valid retry is possible.

**The three timeout systems stay separate.** (1) The ordinary missed defender deadline is the published LOW fallback above: the only tactical consequence is the existing undercommitment step (+1 for an attacker whose funded effective commitment outranks the defender's LOW), no timeout-specific modifier, no free window, no second clock advance, no attacker-timeout policy. (2) Positional stalling (Guide §§41–42: lack of progress, priority/free-initiative windows, resets) is a future match-rule mechanic and is **not** implemented or approximated here. (3) The emergency submission-defense expiry is a separate frozen rule that Half Guard v0 does not have and this slice does not touch.

**Unresolved seals.** A window cannot close without resolving: a pending seal blocks `open_window`, the legacy `submit` and a pass, and the match clock cannot move while the window is open. A timeout resolves through the published fallback; a session end discards the seal. After either, nothing is pending, so nothing half-committed can reach the next window. A pending seal is not persisted across processes.

**Information isolation (accurate scope).** The responder's controller is handed only detached dictionaries built from an allow-list; none contains the sealed store. GDScript has no private members: any in-process code that holds the protocol object can read `_pending`. This is architectural discipline plus tests, **not** a security boundary and not cryptographic protection. The probing-controller double receives only detached dictionaries (no objects, so no private members), and a source scan pins that it never names executor internals.

**Intentionally revised earlier pins (B1h).** `test_half_guard_boundaries.gd` 4,006 → 3,999 (the engine scope scan no longer forbids `feint` / `surcharge`, and now also forbids `SealedProtocol` and `defaulted` in every engine source); `test_half_guard_sealed_protocol.gd` 41,231 → 42,309 (GP-2/GP-3 public fields, the published-fallback rule, executor event fields and the gateway's three new methods). Every other qualified pin, including the 49,609-assertion direct oracle replay (16,858 rows) and the byte-identical direct fixture, is unchanged. New suites: `test_half_guard_feint_reference.gd` (26,415) and `test_half_guard_feint_protocol.gd` (32,222).

**Measurements.** Structural and seeded-population evidence about the feints (grade tables, funding arithmetic, reachability, policy populations; explicitly not a balance claim) is in [HALF_GUARD_V0_FEINT_MEASUREMENTS.md](HALF_GUARD_V0_FEINT_MEASUREMENTS.md), produced by `GODOT_V1/tests/measure_half_guard_feints.py` (not wired into CI).

**Not in this slice.** (B1i has since added the opt-in graph exposure; see below.) Positional stalling and priority tokens, attacker timeouts, emergency submission defense, behaviors, recovery, new positions, technique memories and any UI.

## Sealed decisions through the position graph (B1i, explicit opt-in)

`BjjPositionGraphMatch.create_with_sealed_half_guard(configuration, top_id, bottom_id, receivers = default)` builds the B1d graph (same receiver table, same validation, same activation; `receivers` must contain `half_guard`, otherwise `invalid_receivers`) and additionally enables the sealed workflow **for Half Guard only**. `create` and `create_with_receivers` are unchanged; F0 and F1 still use `create`. Nothing changes while Mount is active: the Mount gateway handles every decision exactly as before, no protocol is required, and a match that ends in Mount never constructs a Half Guard simulation or a protocol.

**The graph coordinates match flow; it does not prescribe a sequence of positions.** A match stays in its current position through any number of accepted exchanges and may end there (a tap, or the match clock reaching zero); only a legal, accepted positional exit triggers a transition; an unsupported exit halts at the existing incomplete-engine boundary and is not a victory. This holds for every position added later. Each position owns its own mechanics (Mount and Half Guard have position-local combat rules); the graph owns only the active-position choice, its status and its global event log. No scoring, winner or points adjudication exists: a clock expiry keeps the existing `terminal_outcome` (`timeout`) record.

**Typed ownership (the adoption seam).** `BjjHalfGuardSealedProtocol.adopt(gateway)` attaches a protocol to an **already constructed** `BjjHalfGuardWindowGateway`; it never builds a second simulation (`create(entry)` is unchanged and still builds its own). Adoption validates the gateway before anything is claimed: a typed non-null `BjjHalfGuardWindowGateway` (`invalid_gateway`), not terminal and no window open (`gateway_not_idle`), and not already claimed (`gateway_already_attached`). The claim is one-way (`BjjHalfGuardWindowGateway.claim_for_protocol()`), so at most one protocol can ever drive a gateway. An adopted protocol remembers the gateway snapshot after each of its own operations and refuses to act (`gateway_diverged`) if anything else changed the gateway since, so a stray alias or a bypass cannot silently create two mutators. The graph keeps its typed nullable Half Guard slot (the gateway, used for detached reads) and one more typed nullable slot for the adopted protocol (the same object's driver); while the protocol slot is set, every Half Guard command that can change the simulation goes through it, so a pending seal cannot be bypassed by the legacy `submit`.

**Atomic activation.** The accepted Mount exchange stays settled (HG-18, no rollback). The graph validates the Mount carry-over record, builds the Half Guard gateway through the B1d receiver and checks it (identity, resources, clock, window continuity, fresh state), adopts the protocol onto that exact gateway, checks the attachment (an adopted, unclosed protocol whose snapshot equals the gateway's, nothing pending, serial 0, no events), and only then sets both slots and appends exactly one `transition_committed`. Any failure, including a protocol attachment refusal, appends `transition_blocked` with `transition_entry_invalid`, halts and activates nothing. The transition opens no window, spends nothing and moves no clock; the Mount segment stays frozen history.

**Graph-level sealed methods** (`seal_intent`, `public_intent_view`, `sealed_intent_view`, `respond`, `apply_response_timeout`, `sealed_public_events`; window opening and the legacy `submit` keep their names) forward to the protocol after the graph's own admission, in this order: `halted_unsupported_transition`, `match_ended`, `sealed_protocol_not_enabled`, `wrong_active_position` (Mount active). A rejected call changes nothing. A seal appends no graph event; a resolved response or a published-fallback timeout is **one accepted exchange** that feeds the **same** `_settle_accepted` function as a direct `submit`: one `decision_accepted`, then continue (no exit), transition or halt (an exit), or terminal (not an exit). There is no separate transition logic for feints. Half Guard exits halt with `from_position_id = "half_guard"`; a clock end is a terminal outcome of the current position.

**Unchanged and still excluded.** The ordinary defender timeout is the published LOW fallback (Bottom Hip Frame, Top Hip Pressure) and nothing else; positional stalling, free-initiative rewards, attacker timeouts, emergency submission defense, scoring and match adjudication are not implemented. There is no Standing, no further position, no return route and no multi-position UI: current F1 remains Mount-only. This is not a complete BJJ match experience; it connects two qualified positions through one coordinator.

**Intentionally revised pins (B1i).** The two private-property pins in `test_position_graph_boundaries.gd` and `test_carryover_export.gd` gained `_sealed` and `_sealed_enabled` (assertion counts unchanged); `test_half_guard_graph.gd` 2,125 → 2,133 (its public-name scan now also checks the eight new graph method names, each "does not mention a gateway"); the B1g and B1h protocol suites keep their counts (42,309 and 32,222) but now state that the graph is the one production source that names the protocol and that the gateway has the one-way claim method. The new suite `test_half_guard_graph_sealed_flow.gd` is pinned in CI.
