# Position graph: Mount → Half Guard (specification — direction approved, numbers open)

**Status: owner direction D1–D6 approved; numerical and mechanical rules NOT yet accepted;
nothing implemented.** No Half Guard mechanics, grades, axis values, catalog entries or tests
exist. This document fixes the architecture, the transition boundary and the Definition of Done
for a later implementation slice, and lists what is still undecided. It changes no Mount
behavior, no Python source and no fixture.

Depends on: `POSITION_CONTRACT.md` (PR #39), `WINDOW_GATEWAY.md` (PR #41), `MOUNT_LIFECYCLE.md`,
Master Guide v10.4 §§7, 8, 9, 11.4, 12, 14, 63.

See also: [POSITION_TOPOLOGY.md](POSITION_TOPOLOGY.md) (A3c, proposal) for the wider position topology, which
treats the three Mount exit labels in §1 as the current producible inventory, not the complete topology.

## 1. Why Half Guard first (deviation from Guide §63)

Guide §63 Phase 2 recommends: Standing, Closed Guard, Side Control, Half Guard, Back Control,
Turtle, Open Guard, Front Headlock, Leg Entanglement, "Mount integration/regression throughout".

| Fact (verified in source) | Consequence |
|---|---|
| Mount's only exits come from Elbow-Knee Escape (SUCCESS → `Half Guard`; STRONG_SUCCESS → `Open Guard`, or `Half Guard` at Stable band) and Trap-and-Roll (→ `Reversal`) | Mount can reach exactly Half Guard, Open Guard, or an unresolved Reversal |
| Mount declares no Side Control, Standing or Closed Guard destination | Those positions cannot be entered from Mount |
| Guide §11.4 lists Half Guard destinations Guard, Side Control, Mount, Turtle, Back Control; §11.5 lists Side Control destinations Guard, Half Guard, Turtle, Mount, Back Control | Side Control connects to Mount only through Half Guard (or Guard/Back, also unbuilt) |
| No Python reference exists for any non-Mount position | Any second position needs rules and a test-only oracle first |

Deviation: Half Guard moves ahead of Standing, Closed Guard and Side Control because it is the
only unbuilt position reachable from the one built position, and Phase 1's exit criterion ("a
second position can use the same architecture") needs a real connection. Standing and Closed
Guard keep their §63 priority for the full graph. Open Guard (the other Mount exit) stays
declared-but-unimplemented and is handled at the unsupported boundary (§9).

## 2. Stable identifiers

- Position IDs (lowercase snake case, as in `EXIT_DESTINATIONS`): `mount`, `half_guard`, `open_guard`.
- Mount's raw exit labels (`Half Guard`, `Open Guard`, `Reversal`) remain exit *labels*, never
  position IDs. `BjjMountContract.transition_for` stays the only label→ID mapping.
- Fighter IDs are supplied once by the graph owner (`BjjPositionContract.fighter_ids_error`
  rules) and never change across positions.
- Roles are position-local. Half Guard uses `top` and `bottom` (D1).

## 3. D3 — a match-level graph owner

`BjjPositionGraphMatch` (name provisional) is the only holder of persistent match state:
fighter identity, the active position segment, the simulated clock, both stamina pools and
their behavior-flow meters, the global window counter and the global event log.

- It coordinates **validated construction of position-specific gateways**. Each position keeps
  its own gateway/state and its own rules; the graph owner performs no grading, costing or
  resolution.
- Because `BjjMatchWindowGateway` currently builds and owns its own `BjjMountMatch`, the
  graph owner needs a construction path that accepts a validated carry-over record. That path
  must be additive: `BjjMountMatch.create` defaults, Mount rules and existing gateway behavior
  must not change. The exact seam is an implementation-slice design item (§12, Q7).
- Positions never instantiate other positions, never read another position's internals and never
  decide that a transition happened. They report an exit; the graph owner validates and commits.
- The graph owner's event sequence is global and monotonic across segments, and no wall-clock,
  frame or UI input reaches it.

## 4. D1 and D2 — roles, axis and initiative

**D1 (approved).** A successful Mount Elbow-Knee Escape into Half Guard preserves fighter IDs
and physical roles: the fighter who was Mount Top is Half Guard `top`; the fighter who was
Mount Bottom is Half Guard `bottom` and has recovered Half Guard. This is **not** a reversal and
not a score.

- Half Guard has its **own** control axis, oriented toward *Top passing advantage* versus
  *Bottom retention / offensive advantage*. Mount's numeric axis, bands, clamps, thresholds and
  drift rates are never reused, converted or derived from Mount's `crossing_axis` overshoot.
- Sign convention, range, bands, hysteresis and initial value are Half Guard design items that
  require their own reviewed rules (§12, Q1–Q2). Until accepted, no number appears in code.
- Control authority at entry is a Half Guard rule, not inferred from Mount. Mount's
  authority (Top for all of Mount) does not carry over by itself.

**D2 (approved).** The exit-producing Mount decision window is **consumed**. Verified in
`mount_exchange.gd` (`_apply_resolution`): an exit exchange does not alternate initiative; Mount
leaves `initiator` unchanged. The graph owner must therefore not read `initiator` as a handoff.

- The transition does not hand a window to either fighter, grants no free window, no extra
  action and no clock change.
- The Half Guard controller decides the next eligible initiative event under its own rules
  (§12, Q3). Until it does, no window exists after the transition; a window opens only through
  the receiving position's normal path.
- Zero seconds are consumed by the transition itself. Any time that passes later passes through
  the receiving position's advance path.

## 5. Transition protocol and event ordering

One atomic graph-owner step, run only after an accepted decision whose outcome is an exit:

1. **Detect** (read-only): classify by the decision's `transition` and Mount's
   `exit_destination`, never by `ended` alone (timeout and tap are not exits; an exit also sets
   `ended`).
2. **Classify**: resolved + implemented destination → continue; `resolved=false` (Reversal) or
   declared-but-unimplemented (Open Guard until built) → unsupported boundary (§9).
3. **Validate** the entry: destination implemented, identities unchanged, role mapping valid,
   carry-over record valid (§6), event log consistent.
4. **Construct** the receiving gateway and position completely in isolation. The active segment,
   clock, pools, meters, controller snapshot and log are untouched.
5. **Commit** by swapping the active segment reference and appending one
   `transition_committed(from, to, label)` event. This step performs no validation and cannot fail.
6. **Open no window** automatically.

Event order (fixed, replay-checked): `decision_accepted` (the exit exchange, already settled by
Mount) → `transition_committed` → later, caller-driven `window_opened`. Events are never
reordered, merged or duplicated. Any failure in steps 1–4 leaves the whole graph state
bit-identical and appends nothing.

## 6. D4 — shared state versus position-specific policy

Shared stamina and exhaustion state persists across the transition and the transition charges
nothing. Mount's policies are **not** automatically reused.

**Position-independent primitives (carried, reusable as-is)**
- `BjjStaminaPool`: `current`, `maximum` and the exhaustion latch (enter/recover thresholds).
- `BjjBehaviorStaminaPolicy.Meter.remainder_units` for each fighter. These sub-unit remainders
  are real state; dropping or resetting them silently changes stamina after the transition, so
  they are part of the carry-over record.
- `BjjExhaustionPolicy.exchange(attacker_band, defender_band)`: pure function of stamina bands.
- `BjjStaminaCostPolicy` / `BjjCommitment`: commitment funding as a function of requested level
  and available stamina.
- Remaining simulated clock and `initial_clock`.

**Mount-specific policies (require separate Half Guard validation; NOT applied until accepted)**
- Rule 1 ON / Rule 2 OFF settlement and the unfunded-responder waiver (they are exchange
  settlement rules read from Mount's `rules` object).
- Behavior names and rates: `BEHAVIORS` mixes Top (`PRESSURE`, `HOLD`, `CONSERVE`) and Bottom
  (`ESCAPE`, `PROTECT`, `CONSERVE`) Mount behaviors. Whether Half Guard has behaviors, which
  names, and which stamina rates apply is a Half Guard rule (Q4).
- Bottom RECOVER, selected-commitment policy (LOW while Exhausted, MEDIUM after clear) and the
  Mount drift. Whether any analogue exists in Half Guard is Q5.
- D3-B TOKEN / LOCKOUT_HOLD (see below).

**D3-B episode state: preserve or suspend without granting tokens**

`BjjD3BController` holds `armed`, `token_consumed`, `previous_exhausted`, `initialized`. Its
only state changes are in `observe_advance` (the sole place `armed` becomes true and
`token_consumed` resets, on an Exhausted→clear edge of Bottom) and `decide` (consumes the token).
A token is therefore granted only by an Exhausted→clear edge seen by `observe_advance`.

Risk: if the controller kept observing Half Guard time, or were resumed on a later return to
Mount with a stale `previous_exhausted`, an episode that straddled the transition could present
a fresh edge and grant a second token.

Specified behavior (proposed, subject to Q6):
1. The controller is **frozen**, not copied or reset: the graph owner keeps the Mount-segment
   controller record read-only at the moment of exit. Half Guard receives no controller, never
   calls `observe_advance` or `decide`, and is not given any token/hold behavior.
2. Entering Half Guard neither arms nor re-arms nor consumes anything, regardless of Bottom's
   band at that instant (including Exhausted with `token_consumed` already true).
3. A transition can only produce a token if some code path calls `observe_advance`; the
   graph owner never does so across a boundary. A test must prove token counts are identical
   before and after any transition sequence.
4. Return to Mount is **unsupported** (§10). Should it ever be added, it needs its own decision
   on how the frozen episode is reconciled with stamina changes made in Half Guard (options:
   resume from the frozen record with `previous_exhausted` rebased to the current band without
   arming, or discard the episode). Rebasing needs a controller operation that does not exist;
   it must not be improvised in the transition code and does not change D3-B evidence.

Histories: Mount's histories stay with the Mount segment (read-only). The graph event log is the
cross-position record. Commitment baseline is not recomputed by the transition.

## 7. Action admission after a transition

- Admission is position-local: the active gateway validates window id, fighter, initiative and
  action against its own catalog.
- Commands for `mount` or an old window id after commit are rejected with zero mutation.
  Window ids come from the graph owner's monotonic counter and are never reused.
- No chained technique or inherited "next move" is created by a transition. A Half Guard command
  may not use a Mount technique id.

## 8. Error handling and rejection atomicity

Two situations are kept apart and must never be conflated:

- **A rejected command** (invalid, stale, duplicate, unknown fighter, wrong initiative, command
  after a halt, failed construction validation) leaves the **entire graph state unchanged**:
  Mount state, clock, pools, histories, controller record, window record, event log and status.
- **An accepted exchange whose destination is unavailable** (`Reversal`, unimplemented
  `Half Guard` / `Open Guard`) is **not** rolled back. The exchange stays accepted and settled:
  its stamina, clock, positional and history changes remain. The graph then appends
  `transition_blocked`, enters `halted_at_unsupported_transition`, instantiates no destination
  and invents no winner, score or terminal result; later commands are rejected without mutation.

The exit-producing exchange is atomic through the existing owners. The deferred gateway hardening (an unreachable
post-mutation settlement guard) is a separate maintenance task; this specification neither
depends on it nor relaxes it, and transitions run only after a fully accepted decision.

## 9. D5 — unsupported transitions are explicit, not terminal

Mount `Reversal` stays unresolved. It must not be assigned a landing, mapped to a nearby
position, scored or reported as a normal match outcome (timeout, tap or "exit complete").

Three outcomes are kept distinct:

| Case | Meaning | State effect | Report |
|---|---|---|---|
| **Rejected command** | The command was invalid or stale | None | existing error code |
| **Valid exchange, supported transition** | Destination declared and implemented | Atomic commit (§5) | `transition_committed` |
| **Valid exchange, unsupported destination** | The exchange was legal and fully settled, but its destination is unresolved (`Reversal`) or unimplemented (`Open Guard`) | The exchange stands; the graph does **not** transition | `transition_blocked(from, label, reason)` |

On the third case the exchange is accepted and settled and is never rolled back; the graph status becomes `halted_at_unsupported_transition`. This is
neither an error return nor a match end: no result, winner or score is produced. The Mount
segment, clock, pools, meters, controller record and histories stay exactly as the settled
exchange left them; reads are allowed; every further decision is rejected `halted_unsupported_transition`
before any mutation. Replaying the same commands halts at the same event index with identical
state. Existing Mount tests and the contract's `resolved=false` report are unchanged.
When a destination later becomes supported, resuming a halted graph is a separate decision.

## 10. Return routes

Half Guard → Mount appears in the Guide's destination list but has no mechanics, exit map or
oracle. No return route is declared. Half Guard's `transition_destinations()` must not include
`mount` until an approved definition of done defines the action, grades, exit map and the Mount
re-entry initial state. Do not assume it works.

## 11. Definition of Done (for the later implementation slices)

Gates are separate. **Slice A (§14) has its own acceptance criteria and is not blocked by
Q1–Q8**, which concern Half Guard mechanics and completed position-to-position integration.
The gate below applies to the later Half Guard implementation, not to Slice A.

Half Guard specification gate (before any Half Guard code):
1. Questions Q1–Q8 below answered and recorded here.
2. A Half Guard rules document: roles, axis sign/range/bands/initial values, action and response
   catalog, commitment/stamina treatment, exit map, terminal rules.
3. D6: a **focused, test-only Python oracle** (e.g. under `tests/`, no new production engine, no
   edit of `src/` Mount modules, fixtures or the enumeration digest) with its own generator and
   frozen fixture, accepted after the rules, before the Godot port.
4. Digest `3ee55429…` and all existing Mount fixtures unchanged.

Implementation gate (negative-first):
5. Transition tests: wrong destination, unresolved Reversal halt, Open Guard halt, undeclared
   label, timeout/tap not treated as exit, stale/duplicate commands after commit and after halt,
   invalid carry-over (each field), identity mismatch — each with whole-graph equality before/after.
6. Continuity tests: clock, pools, latches, meter remainders, controller record and histories are
   identical across the swap; zero charge; token count unchanged.
7. Replay: identical command sequences give identical states, event logs and halt indices, twice,
   over the existing seed/axis/stamina grid.
8. Mount regression: all 13 Godot suites and the Python suite unchanged and green.
9. Half Guard oracle replay: independent scenarios compared field-by-field with counts.
10. CI: Godot, Python 3.11 and 3.13 jobs and the `CI gate` green on the exact PR head.

Non-goals: Side Control, Standing, Closed Guard, Open Guard mechanics, scoring, stalling,
Recognition, a human timer, memory cards and any presentation (Issue #40 stays deferred).

## 12. Remaining design questions (Half Guard gate only; not a Slice A prerequisite)

| ID | Question |
|---|---|
| Q1 | Half Guard axis: sign convention, range, bands, hysteresis |
| Q2 | Half Guard entry values (initial axis/band) and who holds control authority at entry |
| Q3 | Which event gives the first Half Guard initiative, and how initiative alternates inside it |
| Q4 | Does Half Guard use behaviors, and which stamina rates apply (new names vs Mount's) |
| Q5 | Stamina settlement inside Half Guard: Rule 1/2 analogue, RECOVER analogue, commitment baseline |
| Q6 | D3-B: confirm "frozen, never observed in Half Guard"; decide reconciliation if Mount return is ever added |
| Q7 | Gateway construction seam for carry-over (additive factory vs per-position constructor) |
| Q8 | Half Guard action/response catalog and exit map, including the entry to Open Guard on STRONG_SUCCESS and whether it stays a halt |

## 13. First implementation slice (Slice A; approved, independent of Q1–Q8)

**Slice A — graph owner with an explicit halt boundary, no Half Guard mechanics.**
A `BjjPositionGraphMatch` that wraps the existing Mount gateway, owns the event log and the
carry-over record, and can *only* commit nothing yet: every exit, resolved or not, is
classified, and because no destination is implemented it ends in `transition_blocked`
(`Reversal`, `Open Guard`, `Half Guard` all reported as unsupported). This proves the owner,
event ordering, halt semantics and atomicity against the real Mount without inventing Half
Guard. Mount and gateway behavior are unchanged (lockstep against the bare gateway).

Negative-first tests: exit classification table for all three labels; timeout and tap are not
exits; rejected command vs blocked exchange are distinct, with whole-graph equality; command
after halt rejected with zero mutation; stale ids; unknown fighter; replay twice reaches the same
halt index; controller token count unchanged; construction-validation failures leave state intact.

**Slice B — Half Guard rules + test-only oracle, then Godot Half Guard.** Only after Slice A and
acceptance of Q1–Q8. Expected files for A: `scripts/positions/graph_match.gd` (new),
`tests/test_position_graph_boundaries.gd` (+ `.uid`), a workflow step, docs. No Mount file changes.

## 14. Slice A — acceptance criteria and boundaries

`BjjPositionGraphMatch` (`scripts/positions/graph_match.gd`) is a **thin coordinator** around
exactly one `BjjMatchWindowGateway`. Mount is the only implemented position. It never enters
`half_guard`, `open_guard` or the unresolved `Reversal`.

**Single source of truth.** The gateway (and the `BjjMountMatch` it owns) remains the only
owner of stamina, meters, clock, D3-B, fighter identity, histories and window state. The graph
holds no copy of any of them; every view it exposes is a fresh detached read through the gateway.
The graph owns only what is new: its status, its global event log and the recorded blocked
transition. Window ids are the gateway's single monotonic counter, passed through unchanged
(one segment exists, so a separate graph counter would be a second source of truth).

**Behavior.** `open_window` / `open_window_for` and `submit` delegate to the gateway unchanged.
After an accepted decision the graph classifies the settled outcome:

| Settled outcome | Graph action |
|---|---|
| Exchange without exit | `decision_accepted` only |
| Exit to `Half Guard` / `Open Guard` (declared, not implemented) | `decision_accepted`, then `transition_blocked(reason=destination_not_implemented)`; halt |
| Exit to `Reversal` (unresolved) | `decision_accepted`, then `transition_blocked(reason=unresolved_destination)`; halt |
| Exit with any other label | `transition_blocked(reason=undeclared_exit_label)`; halt (fail closed; label never used as a position id) |
| Timeout (clock reached 0) or tap | `terminal_outcome(reason=timeout|tap)`; status `ended`; **not** a positional exit |

Statuses: `active`, `ended`, `halted_at_unsupported_transition`. Events are numbered 1.. in a
single global order. Exactly one `transition_blocked` is recorded per accepted exit, and after
it every `open_window*` and `submit` returns `halted_unsupported_transition` before reaching the
gateway. Reads stay available. No winner, score or terminal result is produced by a halt.

**Acceptance criteria**
1. Half Guard exit, Open Guard exit and Reversal exit each produce an accepted-exchange halt.
2. The settled underlying Mount state equals a bare gateway's after the same operations (never
   compared against the pre-exchange state).
3. Timeout and tap are not classified as positional exits.
4. Rejected commands (invalid action, stale or duplicate window, unknown fighter, wrong
   initiative, after a halt, after a terminal) leave the whole graph unchanged.
5. One `transition_blocked` per exit; stable global event order; identical double replay.
6. D3-B controller fields are identical to the bare gateway's at the transition boundary.
7. Lockstep against a bare gateway over the existing trajectory grid.
8. Undeclared labels are classified fail-closed by the pure classifier.
9. Existing suites, Python checks and CI routing are unchanged and green. No Python production
   code, fixture or Mount behavior is modified.

**Future carry-over construction interface (documented only; not implemented in Slice A).**
When a destination is implemented, the graph owner will need to construct the receiving
position from a validated, detached *carry-over record* instead of from fresh defaults:
fighter ids; both stamina pools (`current`, `maximum`, latch); both behavior-flow meter
remainders; remaining and initial clock; the frozen Mount-segment controller record; the global
window counter; and the event-log length. The construction call must validate the record,
build the receiving position in isolation and return it without touching the active segment
(§5). In that later slice persistent match-wide state moves to the graph owner as one move, never
as a duplicate. Slice A deliberately adds no such interface, setter or constructor.
