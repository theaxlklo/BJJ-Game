# F0 — Fighter definitions and read-only fighter state views

**Status:** implemented, headless, additive. Stacked on A3e (PR #52). No simulation ownership moved.

F0 adds the smallest fighter foundation the future 2D practice UI and later positions can build on:

* `BjjFighterDefinition` (`scripts/core/fighter_definition.gd`) — a `Resource` for reusable, Inspector-editable fighter
  **content**. It is not a match participant.
* `BjjFighterSnapshotAdapter` (`scripts/positions/mount/fighter_snapshot_adapter.gd`) — a `RefCounted` adapter that
  returns fresh, detached, fighter-keyed views of a live Mount gateway.
* `BjjMatchWindowGateway.behavior_fields()` — one additive, read-only accessor (the only change to existing code).

The Mount match remains the **only** owner of stamina, exhaustion, behavior, meter remainders, initiative, roles, time
and D3-B state. F0 holds no second copy of any of it. Nothing in this slice is a Node or depends on the scene tree.

## 1. Source-field inventory (checked against the code at the F0 parent)

"Open window" means the state after `open_window()` and before the decision that closes it.

| Fact | Authoritative owner (private) | Public read path | Exposed while a window is open? |
| --- | --- | --- | --- |
| Fighter identity | `BjjMatchWindowGateway._top_id` / `_bottom_id`; `BjjMountContract._top_id` / `_bottom_id` | `gateway.roles().fighter_by_role` (`{top, bottom}`); `window_fields().fighter_id` (the id holding the window) | Yes |
| Role of a fighter | Mount's fixed `top` / `bottom` roles | `roles().fighter_by_role`; `window_fields().role` | Yes |
| Stamina current / maximum | `BjjMountMatch.top` / `.bottom` (`BjjStaminaPool`) | `state_fields()` → `top_stamina`, `bottom_stamina`, `top_maximum`, `bottom_maximum` (`BjjExchangeResult.Snapshot`) | Yes (live) |
| Exhaustion band (`Fresh`/`Working`/`Tired`/`Exhausted`) | `BjjStaminaPool.band` | `state_fields()` → `top_band`, `bottom_band` | Yes (live) |
| D3-B latch / token | `BjjD3BController` | `controller_fields()` | Yes (not used by F0) |
| **Held behavior** (`top`: PRESSURE/HOLD/CONSERVE; `bottom`: ESCAPE/PROTECT/CONSERVE) | `BjjMountExchange.top_behavior` / `.bottom_behavior`; `recovery_advance()` sets the bottom's before an advance and re-chooses it afterwards unless the match ended, so the field is the value last *set*, which the next advance may re-derive from the exhaustion band | **None before F0.** `history_fields()` holds only the behavior *used by past advances* (empty before the first window); `BjjMountMatch.lifecycle_fields()` is not reachable through the gateway | **No** (not recoverable) |
| Behavior-meter remainder | `BjjMountMatch.top_meter` / `.bottom_meter` (`remainder_units`) | Only `carryover_segment()`, which refuses an open window by design | **No** |
| Clock, position, initiative | match / contract | `state_fields()`, `roles().initiative_id` | Yes (not used by F0) |

`behavior_fields()` therefore reports the behavior the match **currently holds**, not a recomputed one: before the first
window an exhausted bottom fighter still holds `ESCAPE` (pinned by a test), and it becomes `CONSERVE` once the match has advanced.

Observed facts that justify the one accessor (probe of the real gateway, `top_stamina 80`, `bottom_stamina 10`): before the
first window the match holds `bottom_behavior = ESCAPE` while history is empty; after `open_window()` it is `CONSERVE`.
History therefore cannot tell a UI what a fighter is currently doing before the first window, or if the exhaustion state
flips inside an advance.

## 2. Public API

```gdscript
# Resource (Inspector-editable; two exported String fields, nothing else)
BjjFighterDefinition.definition_id   # stable content/template id, lowercase snake case, <= 64 chars
BjjFighterDefinition.display_name    # non-empty, trimmed, no control characters, <= 64 chars
BjjFighterDefinition.validation_error() -> String   # "" | invalid_definition_id | invalid_display_name

# RefCounted adapter over the Mount gateway
BjjFighterSnapshotAdapter.create(source: Variant, definitions: Variant) -> Creation   # source: a gateway (F0) or a BjjPositionGraphMatch (F1); .ok(), .error, .adapter
BjjFighterSnapshotAdapter.fighter_ids() -> Array[String]       # the two ids, sorted, role-independent
BjjFighterSnapshotAdapter.snapshots() -> Dictionary            # fighter_id -> fresh, detached Dictionary

# Additive gateway accessor
BjjMatchWindowGateway.behavior_fields() -> Dictionary          # {"top": ..., "bottom": ...}, behaviors the match currently holds
```

`create()` error codes, in order: `missing_gateway`, `invalid_definitions`, `invalid_fighter_id_key` (a key that is not a
`String`), `unknown_fighter_id`, `missing_fighter_definition`, `invalid_fighter_definition`, then the definition's own
`validation_error()`. The keys must equal the gateway's two fighter ids exactly; the match owner supplies the ids and the
existing fighter-id validation is untouched. One definition may back both fighters.

`snapshots()` returns an empty `{}` (a refusal) if the gateway's roles ever fail to name exactly the known fighters; that cannot
happen with today's Mount gateway and is covered by synthetic tests. Each snapshot value contains only plain data: `fighter_id`, `definition_id`, `display_name`, `role`, `stamina_current`,
`stamina_maximum`, `exhaustion_band`, `behavior`. Identity metadata is copied from the definitions at creation, so editing
a shared `Resource` afterwards never changes an existing view (a new adapter picks the edit up). Roles resolve by fighter
id through `roles().fighter_by_role`, never by array order or display name.

## 3. Feasibility record (transferable to the owner's HTML feasibility matrix)

Gate applied to each candidate: concrete need, smallest existing alternative, benefit, cost, deterministic regression
risk, whether we can live with the current design, decision.

| # | Candidate | Concrete need | Smallest existing alternative | Benefit | Change / maintenance cost | Regression risk | Live with current? | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `BjjFighterDefinition` Resource, two fields | Reusable, editable content for tests now and the practice UI next; owner asked for Resource-based definitions | Plain dictionaries or strings in tests | Inspector editing, a validated, typed place for content, reuse across participants | ~60 lines, 2 fields | None: no simulation code involved | Partially (dictionaries work, but are unvalidated and not editable) | **Implement** |
| 2 | Optional visual/style identifier on the Resource | None yet: no UI consumer exists | None needed | Hypothetical | Freezes a content taxonomy without a user | None | Yes | **Defer** to F1 if the UI needs it |
| 3 | Power/speed/stamina/belt fields on the Resource | None; would invent rules | The frozen Mount rules | None | Rules and parity risk | High (new gameplay) | Yes | **Reject** |
| 4 | Resource owns runtime stamina/exhaustion/behavior | None; would duplicate authoritative state | Mount pools | None | Two sources of truth | High | Yes | **Reject** |
| 5 | `BjjFighterSnapshotAdapter` | The UI needs fighter-keyed views; the gateway exposes role-keyed (`top_`/`bottom_`) fields | The UI reading `state_fields()` and `roles()` itself, repeating the role mapping | One tested identity mapping, detached values, stable fighter-keyed API | ~110 lines, one class | None: reads public views only | Yes, for a single call site; a second consumer (UI) is imminent | **Implement** (adapter, read-only) |
| 6 | Copy identity metadata at creation vs reading the Resource live | Stable, deterministic views while content Resources stay editable | Live reads | Edits to a shared Resource cannot silently change a match view | 2 dictionary copies | None | n/a | **Adapt**: copy at creation |
| 7 | Gateway `behavior_fields()` (option **B**) | Behavior is part of the fighter state the UI shows, and it is not recoverable from any public view (see §1) | Omit behavior (**A**); derive from `history_fields()` (wrong before the first window); read `_match` privately (forbidden) | Accurate current behavior with a 3-line, non-mutating, detached accessor | One method on a qualified file; no behavior change | Very low (pure read); guarded by tests that compare with the match and by an inertness check | No: the data is otherwise unreachable | **Implement** (smallest of A/B/C) |
| 8 | Meter remainder in snapshots | None: it is internal bookkeeping with no UI use | `carryover_segment()` between windows when a hand-off needs it | None for the UI | Another public surface on the gateway | Very low | Yes | **Defer** (additive later if a consumer appears) |
| 9 | Ownership refactor of state (option **C**) | None | Existing owners | None | Large, touches parity-qualified code | High | Yes | **Reject** |
| 10 | `carryover_segment()` as a live-window getter | None | `state_fields()` | None | It correctly refuses an open window | n/a | Yes | **Reject** |
| 11 | `FighterMatchState` / shared mutable fighter state | None | The adapter's detached views | None | Second authority | High | Yes | **Reject** (non-goal) |
| 12 | Position-agnostic adapter interface | None until a second position has a gateway | The Mount-specific adapter | Hypothetical | Speculative abstraction | None | Yes | **Defer** until a second position |
| 13 | Make `BjjMountContract.POSITION_ID` derive from the registry | None | Equality test (A3e) | None | Touches frozen-adjacent code | Low | Yes | **Defer** (carried from A3e) |
| 14 | Two committed `.tres` sample definitions | Proves the Inspector/Resource path end to end and gives the UI sample content | Constructing definitions in code only | Real load/duplicate/cache behavior is exercised | 2 tiny files generated by Godot | None | Yes, but weaker proof | **Implement** |

## 4. Verification summary

* `tests/test_fighter_foundation.gd` — 750 assertions, negative-first, wired into `godot-v1.yml` through the existing log
  validator (`--name "Fighter foundation"`, exact pin 750, fail-closed on any diagnostic or premature PASS).
* Frozen Mount suite (256,992 assertions) and position registry suite (431 assertions) are unchanged and re-run.
* Reads are inert (time, stamina, window, D3-B, histories, position and carry-over unchanged across 30 repeated reads at each phase);
  snapshots agree literally with `state_fields()` and with the match's behaviors before a window, while one is open and after
  every accepted decision over an 8-window sequence, and an independent twin match reproduces every snapshot.
* Synthetic role-mapping tests show that a future top/bottom role change would keep fighter identity, metadata and ids stable.
  They do **not** claim that the current Mount engine can execute a completed reversal into another position.

## 5. Godot UID policy and historical UIDs

F0 commits the `.gd.uid` files of the three `.gd` files it creates. It stages no other UID file.

Historical, not repaired here: 17 tracked scripts have no tracked `.gd.uid` (Godot regenerates them locally as untracked
files): `scripts/core/{grade,position_contract,position_registry}.gd`,
`scripts/positions/mount/{mount_catalog,mount_contract,mount_drift,mount_position,mount_resolver,mount_rules}.gd`,
`scripts/presentation/mount_debug_view.gd`, and the tests `test_d3b_reference`, `test_mount_lifecycle_reference`,
`test_mount_reference`, `test_mount_slice`, `test_position_contract_boundaries`, `test_position_contract_reference`,
`test_position_registry`. Fixing that is a separate owner decision.

## 6. Remaining risks

* The adapter is Mount-specific (role-prefixed state fields); the second position will need its own mapping (candidate 12).
* `behavior_fields()` adds one public method to a qualified gateway file; the A3d/H1 suites and parity steps pass unchanged,
  but any future gateway surface pin must include it.
* Definition validation limits (64 characters, lowercase snake case) are new content rules for UI data only; they affect no simulation.
  Display names allow any Unicode except control characters (U+0000-U+001F, U+007F-U+009F) and leading/trailing whitespace; stricter Unicode
  policy (bidi controls, zero-width characters) is a content decision left to the UI slice.
* `create()` trusts a gateway built by `BjjMatchWindowGateway.create()`. A bare `BjjMatchWindowGateway.new()` has no match and would
  raise a script error on `roles()`, like every other gateway method; CI's log validator would flag it. It is unreachable through the supported constructor.
* **Resolved in F1:** the adapter now also accepts a `BjjPositionGraphMatch` (the graph gained a read-only `behavior_fields()` pass-through
  and still keeps its gateway private); see `F1_MOUNT_PRACTICE.md`. Originally: the adapter was bound to the bare Mount gateway. A `BjjPositionGraphMatch` keeps its gateway private and had no `behavior_fields()`
  pass-through, so a graph-owned match could not be viewed through this adapter. Holding the raw gateway beside a graph would let a caller
  bypass the graph's halt and classification, so F0 deliberately adds no pass-through. Whether F1 uses a graph pass-through or a source
  interface is a follow-up decision.
* Terminal matches are covered (a 12-second match is driven to its end and read); snapshots and `behavior_fields()` stay correct and inert.
