# PositionContract and the Mount adapter

Implements the minimum of guide v10.4 section 7 needed to expose the existing,
parity-qualified headless Mount through a reusable, position-independent interface.
Stacked on PR #30 (`feat/godot-v1-d3b-mount-lifecycle`, head
`a5ed9b97bff10a3f78b61f002de93386852a1b5e`). No Python source, frozen fixture or
Mount rule changed. Side Control is **not** implemented.

## Files

| File | Role |
|---|---|
| `scripts/core/position_contract.gd` (`BjjPositionContract`) | Interface and detached value types; every virtual fails closed |
| `scripts/positions/mount/mount_contract.gd` (`BjjMountContract`) | Thin adapter wrapping a `BjjMountMatch` by composition |
| `scripts/positions/mount/mount_exchange.gd` | One additive, read-only method: `admission_error(request)` (returns the result of the unchanged `_validate`) |
| `tests/test_position_contract_boundaries.gd` | Negative-first native tests, direct-vs-contract equivalence, exit semantics, replayed trajectories |
| `tests/test_position_contract_reference.gd` | The frozen Python exchange oracle replayed through the contract |

## Contract

Four concepts are separate and never inferred from one another:

- **Fighter identity**: stable ids supplied by the owner (`BjjMountContract.create(match, top_id, bottom_id)`); two distinct, non-empty ids without surrounding whitespace.
- **Physical role**: position-local (`"top"`, `"bottom"` for Mount). `Roles.fighter_by_role` maps role to fighter id.
- **Control authority**: the fighter on the positive/control side of the position's signed axis (`Roles.control_authority_id`).
- **Initiative**: the fighter holding the current decision window (`Roles.initiative_id`).

Mount's authority is the Top fighter for the life of the position (its axis convention is
unchanged), while initiative alternates exactly as the existing match decides. A physically
Top fighter without initiative is rejected (`not_initiator`); a Bottom fighter with initiative
may act. Initiative moving is not a reversal, position change or score.

| Member | Purpose |
|---|---|
| `position_id()`, `fighter_ids()`, `roles()` | Identity, roles, authority, initiative |
| `state_fields()`, `history_fields()` | Detached position state and histories (same data as `snapshot()` / `history.fields()`) |
| `setup_state()`, `submission_state()` | Setup tiers keyed by stable technique id; submission stage and finisher id. Empty when the rule set has none |
| `is_terminal()` | Timeout, tap or exit |
| `action_options(fighter_id)`, `response_options(action_id)` | Menus of stable technique ids; unavailable options carry a reason code |
| `commitment_options()` | `LOW`, `MEDIUM`, `HIGH` |
| `transition_destinations()`, `validate_transition(id)` | Declared stable destination ids and their validation |
| `submit(command)` | One atomic decision |

`Command` carries `position_id`, `fighter_id`, `action_id`, `response_id`, `commitment`,
`response_commitment`. `Outcome` carries `error`, the detached exchange record, a `Transition`
and the detached post-state. All returned data is a fresh copy.

### Rejection order (all before any mutation)

`missing_command` → `missing_position` / `unknown_position` → `missing_position_state` →
existing context errors (including `terminal_exchange`) → `missing_fighter_id` /
`unknown_fighter` → `not_initiator` → the existing Mount admission codes unchanged
(`unknown_action`, `incorrect_action_side_or_kind`, `setup_not_ready`, `inactive_submission`,
`incorrect_finish_initiator`, `unknown_response`, `incorrect_response_side_or_kind`,
`incompatible_ready_response`, `invalid_commitment`, `invalid_response_commitment`, ...).

Option reason codes: `not_initiator`, `setup_not_ready`, `inactive_submission`, plus any
existing admission code for responses.

## How Mount uses it, and why behavior is unchanged

`submit` performs only addressing, identity and initiative checks, then builds the same
`BjjExchangeResult.Request` and calls the same `BjjMountMatch.attempt`. Resolution grades,
stamina and commitment settlement, exhaustion, setup/Americana progression, initiative flip,
histories, exit semantics and terminal admission are executed by that unchanged code. The
adapter never writes to match state. Equivalence is checked, not assumed:

- 40,320 requests across four rule sets plus production, three axes, both initiators, setup/stage/stamina variants, accepted and rejected, compared field-for-field (result, outcome state, full lifecycle state and histories) against `attempt` on an identical twin.
- 108 full trajectories (3 configurations x 9 behavior pairs x 4 seeds) driven in lockstep through both entry points, each replayed twice.
- The frozen Python exchange oracle (14,631 scenarios / 14,780 operations, two replays) routed through the contract with the oracle's expectations untouched.

## Supported boundary

Covered: command execution equivalent to `attempt`; menus; roles; setup and submission views;
declared exits; terminal reporting.

Not covered here (unchanged on `BjjMountMatch`): `advance`, `recovery_advance`, `next_window`,
RECOVER, D3-B windows and `bottom_decision`, `reset_window`, `recovery_hold`, free windows,
`decide_legacy`. These are match orchestration, not position responsibilities. A human
Bottom decision in production mode still goes through `bottom_decision`; a future
match-level window controller should own that. Stalling, Recognition, scoring collectors
and custom policy providers remain unported, as before. The three approved exchange terminal
differences in `EXCHANGE_SETTLEMENT.md` apply unchanged; the contract rejects terminal
exchanges atomically with `terminal_exchange`.

### Exits and one unresolved rule

Mount's frozen catalog emits three exit labels. `Half Guard` and `Open Guard` map to
`half_guard` and `open_guard`. `Reversal` is an action overlay, not a position node (guide
section 9), and the specification does not say where a Trap-and-Roll reversal lands. The
contract therefore reports it as an exit with `resolved = false` and no destination id. This
needs an owner decision before a position graph can route it; nothing was invented.

## Architecture comparison

Reference: the Architecture guide of the community reconstruction of Slay the Spire 2
(decompiled proprietary code, not verified open source). Used for comparison only; nothing
was copied, and the repository was not cloned or audited.

| Pattern | Already equivalent in BJJ-Game | Immediate gap | Needed for PositionContract |
|---|---|---|---|
| Canonical definitions vs mutable state | `BjjMountCatalog` (stable ids, frozen grades) vs `BjjMountExchange`/pools/history | None for Mount | Menus return stable ids, never copies of definitions |
| Explicit commands, deterministic execution | `BjjExchangeResult.Request` + `attempt`: validate, then atomic mutation, no RNG | Callers use Mount-specific types and `"top"`/`"bottom"` strings | `Command` addressed by position id and fighter id; initiative check |
| Separate combat, run and presentation | Headless lifecycle independent of `SceneTree`; presentation is a separate script | No run state yet (roguelike is future) | Detached return data so presentation cannot alias authority |

Also needed, from the gap analysis against guide section 7: stable fighter identity,
authority-versus-initiative, availability reasons, and declared validated exits.

Deliberately rejected: a general command queue/executor (our decisions are synchronous and
atomic; the queue serves their undo and networking), reflection or auto-discovered content
registries (explicit `class_name` types and `preload` suffice), per-category RNG streams
(Mount has no randomness), network message wrappers, C#, and any new framework. The source
document also describes its own state objects inconsistently as both immutable and mutated
in place; that is not a pattern to import.

## Verification commands

```bash
godot --headless --path GODOT_V1 --editor --import --quit
godot --headless --path GODOT_V1 --script res://tests/test_position_contract_boundaries.gd
PYTHONPATH=src python GODOT_V1/tests/generate_exchange_reference.py
godot --headless --path GODOT_V1 --script res://tests/test_position_contract_reference.gd
```

The exchange oracle fixture is generated by the unchanged Python engine and is gitignored.
The contract tests are wired into `godot-v1.yml` after the D3-B steps.
