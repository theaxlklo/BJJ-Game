# Side Control v0 — canonical rules sheet (B2b-1)

**Status: provisional v0 prototype baseline, owner-approved for B2b only (2026-10-13, `SIDE_CONTROL_V0_PROPOSAL.md` §11A.6, ledger E-022). Not final game balance.** Every number below is a **provisional prototype constant**: it exists so an independent oracle can be built and tested. It may change only through an explicit, versioned and measured rules revision (§13), never silently.

Side Control v0 is a **transition prototype, not a finishing position**: it has no submissions, so a match can leave it only by an exit to a position that does not exist yet, or by the clock.

This sheet restates the approved rules as one self-contained, ordered specification. An independent implementer needs this file and nothing else (no GDScript, no existing oracle). The test-only Python oracle (`tests/oracles/side_control_v0.py`) is written from **this sheet**; the later typed GDScript engine (B2c, **not authorized yet**) will implement the same sheet. No Python-to-Godot parity claim exists for Side Control until B2c.

Mount, Half Guard, the graph, the frozen Python reference, production defaults and every existing fixture are untouched. Where this sheet reuses a number that Half Guard also uses, the number is **stated again here as an independently approved Side Control value** (`SC-N*`); no Half Guard table or constant is imported by reference.

## 0. Approved constants versus deferred systems

| Approved provisional constants (this sheet specifies them) | Deferred or excluded (this sheet does **not** specify them) |
| --- | --- |
| Identity and role mapping (§1), reported authority by axis sign (SC-D3) | Fighter proficiency (`G`, `R`), initiative numerical thresholds, the future opening priority calculation (the entry request only carries an explicit `initiator`) |
| 3 Top actions and 3 Bottom actions, 3 responses per side (§3) | Submissions: the ids `side_control.top.kimura_route` and `.armbar_route` are **reserved only** (no setup, finish, tap or submission-defense mechanics) |
| Both 3×3 raw-grade matrices (§3.3), the exit map (§3.4) | Any receiver for Mount, Back Control, Half Guard or Turtle; return routes; Mount and Side Control `Reversal` landings (unresolved) |
| Axis range, step, entry value, bands, hysteresis, exit lines (§2) | Behaviors, drift, recovery, REST, feints, the sealed protocol, D3-B |
| Readiness tracks, entry tiers, consume/wear/build (§5.7) | Stalling, Momentum, Heart of a Lion, scoring (the position owns none of their state) |
| The existing shared commitment, funding and exhaustion mechanics, restated (§2, §5) | Half Guard preparation carry-over (it does **not** carry), the Half Guard snapshot adapter (a later pure boundary), the graph constructor, UI |
| PASS (§6) and its clock semantics (§7) | North-South and Knee-on-Belly variations, Standing |

## 1. Identity, roles, authority and initiative

Four concepts are never inferred from one another.

| Concept | Rule |
| --- | --- |
| Fighter identity | Two stable string ids supplied by the entry request (§4). They never change for the life of the position. All stamina state belongs to the **fighter id**; roles are labels over the role map. After a Knee Slice the Half Guard Top is the Side Control Top (identity role map, SC-D1); the oracle receives the map as data. |
| Physical role | `top` (the pinning fighter) and `bottom`. |
| Control authority | **Reported only, no mechanical effect** (SC-D3): the Top fighter's id if `axis_tenths > 0`, the Bottom fighter's id if `axis_tenths < 0`, the empty string if `axis_tenths == 0`. |
| Initiative | The role (and therefore the fighter id) that may submit in the current decision window. The first initiator is the entry request's explicit, validated `initiator` (SC-D2; prototype fixtures use `"top"`). After every accepted non-exit exchange and every accepted PASS the initiator flips; an exit leaves it unchanged. Initiative is never derived from role, axis or authority. |

The entry request carries `initiator` because the later opening policy (General Technique `G`, separately earned position-role proficiency `R` starting at 0 for a new career fighter, and the positional advantage that ordinarily favors Top) belongs to a later authorized slice. v0 neither implements proficiency nor chooses a threshold; it only validates the value it is given.

## 2. Constants

* **Axis:** signed integer **tenths**, `-40 … +40`. Positive favors the Top (advance/pin control); negative favors the Bottom (recovery/escape). Entry axis **`+10`**, entry band **`+1`**. The decimal `axis / 10` is a view only. The axis belongs to Side Control; it is never converted from another position's axis.
* **Bands** (ordinals): `-2 BOTTOM_CONTROL`, `-1 BOTTOM_EDGE`, `0 CONTESTED`, `+1 TOP_EDGE`, `+2 TOP_CONTROL`.
* **Band update** (SC-N7), applied repeatedly until no rule matches. Each band has at most one applicable rule at a time, so the order below is only for reading:

| From band | Rule (`a` = axis tenths) | To band |
| --- | --- | --- |
| 0 | `a >= 12` | +1 |
| +1 | `a >= 27` | +2 |
| -1 | `a >= -8` | 0 |
| -2 | `a >= -23` | -1 |
| +2 | `a <= 23` | +1 |
| +1 | `a <= 8` | 0 |
| 0 | `a <= -12` | -1 |
| -1 | `a <= -27` | -2 |

  The legal `(axis, band)` pairs are: band 0 `-12 < a < 12`; +1 `8 < a < 27`; +2 `a > 23`; -1 `-27 < a < -8`; -2 `a < -23`. The entry pair `(10, +1)` is legal. The overlaps are deliberate hysteresis: a band is kept until the axis leaves it by a margin.
* **Exit lines:** Top `proposed >= +30`; Bottom `proposed <= -30`. **Step:** `10` tenths per final-grade step. **Positional modifier:** `-1` for an initiator facing the opposing CONTROL band (Top while the band is `-2`; Bottom while the band is `+2`), else `0`.
* **Grades:** `-2 Strong Failure`, `-1 Failure`, `0 Contested`, `+1 Success`, `+2 Strong Success`, always from the **initiator's** point of view. `shift(g, k) = clamp(g + k, -2, +2)`: every step saturates **before** the next step, so the order of §5.3 is part of the rule.
* **Commitment:** `LOW`, `MEDIUM`, `HIGH`; costs `LOW 3 / MEDIUM 7 / HIGH 12`; ranks `unfunded 0, LOW 1, MEDIUM 2, HIGH 3`. `determine(requested, available)` is the highest tier not above `requested` whose cost is `<= available`, or **unfunded** (the empty string) if none fits.
* **Stamina pool** (existing shared policy, restated): per fighter `current` (`0 … maximum`), `maximum`, and the **Exhausted latch**. Enter threshold `floor(maximum * 0.25)`, recover threshold `ceil(maximum * 0.35)`, both computed as an IEEE-754 binary64 product then rounded (the frozen formulas; they differ from exact integer forms only at capacities above about 2^52). After any change of `current`: if latched and `current >= recover` the latch clears; otherwise if not latched and `current <= enter` the latch sets. `spend_up_to(cost)` removes `min(current, cost)`.
* **Stamina band:** `Exhausted` if latched; else `Fresh` if `current / maximum > 0.75`, `Working` if `> 0.50`, else `Tired` (binary64 division). Only `Exhausted` has a grading effect in v0.
* **Exhaustion modifier:** `(-1 if the initiator's band is Exhausted) + (+1 if the responder's band is Exhausted)`, with both bands captured before any charge.

## 3. Catalog

### 3.1 Actions and responses (stable ids)

| Id | Side | Kind | Break-capable | Readiness track | Exit label |
| --- | --- | --- | --- | --- | --- |
| `side_control.top.stabilize` | top | action | no | none (builds `top_pin`) | — |
| `side_control.top.advance_to_mount` | top | action | **yes** | `top_pin` | `Mount` |
| `side_control.top.expose_back` | top | action | **yes** | `top_pin` | `Back Control` |
| `side_control.bottom.shrimp` | bottom | action | no | none (builds `bottom_space`) | — |
| `side_control.bottom.recover_half_guard` | bottom | action | **yes** | `bottom_space` | `Half Guard` |
| `side_control.bottom.turn_to_knees` | bottom | action | **yes** | `bottom_space` | `Turtle` |
| `side_control.bottom_response.forearm_frame` | bottom | response | — | none | — |
| `side_control.bottom_response.hip_escape` | bottom | response | — | **governed**, reads `bottom_space` | — |
| `side_control.bottom_response.bridge_defense` | bottom | response | — | none | — |
| `side_control.top_response.shoulder_pressure` | top | response | — | none | — |
| `side_control.top_response.hip_block` | top | response | — | **governed**, reads `top_pin` | — |
| `side_control.top_response.follow_the_hips` | top | response | — | none | — |

A Top action is answered by a Bottom response and a Bottom action by a Top response. `Expose Back` is a **provisional technique name and interpretation**; its detailed meaning is not approved. The ids `side_control.top.kimura_route` and `side_control.top.armbar_route` are reserved and are **not** part of the catalog: they are `unknown_action`.

### 3.2 Technique names

`Stabilize`, `Advance to Mount`, `Expose Back`, `Shrimp`, `Recover Half Guard`, `Turn to Knees` (used in exit reasons, §5.4).

### 3.3 Raw grades (initiator's point of view)

| Top action \ Bottom response | `side_control.bottom_response.forearm_frame` | `side_control.bottom_response.hip_escape` | `side_control.bottom_response.bridge_defense` |
| --- | --- | --- | --- |
| `side_control.top.stabilize` | -1 | +1 | 0 |
| `side_control.top.advance_to_mount` | +1 | -2 | +1 |
| `side_control.top.expose_back` | +1 | 0 | -2 |

| Bottom action \ Top response | `side_control.top_response.shoulder_pressure` | `side_control.top_response.hip_block` | `side_control.top_response.follow_the_hips` |
| --- | --- | --- | --- |
| `side_control.bottom.shrimp` | -1 | +1 | 0 |
| `side_control.bottom.recover_half_guard` | +2 | -1 | +1 |
| `side_control.bottom.turn_to_knees` | 0 | +2 | -2 |

All 18 cells exist, so no matchup is unsupported. (The proposal's structural check of these tables — every response holds one action and loses to another, the best counters differ, no response is dominated — verifies their shape only, not fairness or reachability.)

### 3.4 Exit map (the only exits)

An exchange exits only if the action is break-capable **and** `final >= +1` **and** the line is crossed:

| Technique | Line | Label | Destination id |
| --- | --- | --- | --- |
| Advance to Mount | `proposed >= +30` | `Mount` | `mount` |
| Expose Back | `proposed >= +30` | `Back Control` | `back_control` |
| Recover Half Guard | `proposed <= -30` | `Half Guard` | `half_guard` |
| Turn to Knees | `proposed <= -30` | `Turtle` | `turtle` |

Every destination id is a declared position id. **All four destinations are unsupported in v0** (§10).

## 4. State, entry and validation

**State:** `axis_tenths`, `band`, `initiator`, per fighter id `stamina_current`, `stamina_maximum`, `exhaustion_latched`, `behavior_remainder_units`, the role map, `top_pin`, `bottom_space` (tiers `0 None`, `1 Partial`, `2 Ready`), `initial_seconds`, `clock_seconds`, `interval_seconds`, `window_id` (last issued), `window_open`, `window_initiator`, `exit_destination`, `exit_reason`, `decision_history`. `ended = (clock_seconds == 0) or (exit_destination != "")`.

**Entry request** (the only way to build a position):

```
{"role_map": {"top": id, "bottom": id},
 "initiator": "top" | "bottom",
 "fighters": {id: {"stamina_current": int, "stamina_maximum": int, "exhaustion_latched": bool, "behavior_remainder_units": int}, ...},
 "clock": {"initial_seconds": int, "remaining_seconds": int},
 "window": {"last_issued_id": int},
 "interval_seconds": int}
```

**Validation** is pure; nothing is built on error; the first failing code wins, in this order:

1. `entry_not_a_dictionary`.
2. `entry_malformed`: any missing or extra key at any level, or a wrong type (a `bool` is not an `int`; a float is not an `int`; `initiator` and ids must be strings). **No tier, axis or band key is accepted**; one is an extra key.
3. `invalid_fighter_id`: a role-map id that is empty, is padded at either end by any code point `0x01 … 0x20`, or the two ids are equal. (This is exactly Godot 4.7.2's `String.strip_edges` set: `0x7f`, `0x85`, `0xa0`, the Unicode spaces and `0xfeff` are **not** stripped and are accepted; interior whitespace is accepted.)
4. `fighters_mismatch`: the `fighters` keys differ from the two role-map ids.
5. `invalid_initiator`: `initiator` is neither `"top"` nor `"bottom"`.
6. `invalid_stamina_maximum` (`1 … 9007199254740991`); 7. `invalid_stamina_current` (`0 … maximum`); 8. `inconsistent_exhaustion_latch` (`current <= enter` requires latched; `current >= recover` requires not latched; strictly between the thresholds either value is accepted and is **carried**, which preserves hysteresis across a boundary).
9. `invalid_behavior_remainder` (`|r| <= 9007199254740991`); 10. `invalid_clock` (`initial` in `1 … 9007199254740991`, `remaining` in `1 … initial`: an entry with no time left is refused as inconsistent); 11. `invalid_window_id` (`0 … 9007199254740991`); 12. `invalid_interval` (`1 … 9007199254740991`).

Fighters are checked in role order (top, then bottom) within steps 6–9.

**Built state:** axis `+10`, band `+1`, `top_pin = bottom_space = 1` (Partial/Partial, **fresh**: nothing from a previous position carries), `initiator` as requested, `window_id = last_issued_id`, no window open, `exit_destination = exit_reason = ""`, empty `decision_history`, stamina/latch/remainder/clock exactly as supplied. Behavior remainders are carried and **never changed** by v0.

## 5. The exchange

An exchange is one accepted request by the current initiator.

**5.1 Admission** — all checks of §8 pass before anything mutates. **5.2 Capture** (before any charge): both stamina bands; the pre-exchange tiers, axis and band.

**5.3 Funding and grading** (each step saturates at ±2):

1. Requested commitment and response commitment each default to `MEDIUM` when empty. `initiator_effective = determine(commitment, initiator.current)`; `responder_effective = determine(response_commitment, responder.current)`.
2. `raw = RAW[action][response]` (§3.3). `g1 = shift(raw, positional)`.
3. **Attack readiness** (break-capable actions only; the tier of the initiator's own track named in §3.1): `g2 = shift(g1, tier - 1)` (Ready `+1`, Partial `0`, None `-1`). Other actions: `g2 = g1`.
4. **Defense readiness** (responses `hip_escape` reading `bottom_space` and `hip_block` reading `top_pin`): the *strength tier* is `0` (None) if `responder_effective` is LOW or unfunded, else the responder's own track tier; `g3 = shift(g2, {2: -1, 1: 0, 0: +2}[strength tier])`. Other responses: `g3 = g2`.
5. **Exhaustion:** `g4 = shift(g3, exhaustion modifier)` (§2).
6. **Magnitude** (evaluated on `g4`): initiator effective HIGH: `+1` when `g4 == +1`, `-1` when `g4 == -1`; initiator effective LOW or unfunded: `-1` when `g4 == +2`, `+1` when `g4 == -2`; otherwise `0`. `g5 = shift(g4, magnitude)`.
7. **Undercommitment:** `+1` if `rank(responder_effective) < rank(initiator_effective)`, else `0`. `final = shift(g5, undercommitment)`.

**5.4 Axis, exit, initiative.** `delta = +10 * final` for a Top initiator, `-10 * final` for a Bottom initiator; `proposed = axis + delta`. Exit per §3.4. Then `axis = clamp(proposed, -40, +40)` and `band` is updated from the **clamped** axis (§2); the clamp and band update happen **also on an exit**. The initiator flips unless the exchange exited. On an exit `exit_destination` is the label and `exit_reason` is `"<Technique name> reached the advance line with final grade <Grade name>"` (Top actions) or `"<Technique name> reached the escape line with final grade <Grade name>"` (Bottom actions).

**5.5 Stamina charges** (after grading; initiator, then responder; each `spend_up_to`). The initiator pays the cost of its effective commitment (an unfunded initiator pays `0`). The responder pays the cost of its effective commitment **unless Rule 1 waives it**: Rule 1 is ON, and when the initiator's effective commitment is unfunded the responder's charge is `0` and the waived amount (the cost it would have paid) is recorded. Rule 2 (a supplemental hold) does not exist. Latches update as in §2.

**5.6 Paid effort.** `responder_paid = (responder_effective is funded) and not waived`. Requested, funded-effective and charged commitment are three distinct recorded quantities.

**5.7 Readiness updates** (after the charges; each step saturates at `0 … 2`; this is the only place tiers change):

1. *Consume:* if the action is break-capable and the initiator's own track is Ready (`2`), that track `-1`, whatever the result.
2. *Wear* of the responder's governed track (only if the response is `hip_escape` → `bottom_space` or `hip_block` → `top_pin`), by `responder_effective` (the value granted by funding **before** the Rule 1 waiver):

| Responder effective commitment | Wear |
| --- | --- |
| LOW or unfunded | none |
| MEDIUM | `-1` if `final != 0` |
| HIGH and paid | `-1` only if `final >= +1` (the defense failed); preserved on `0` and on a defense success |
| HIGH and not paid (waived) | as MEDIUM: `-1` if `final != 0` |

3. *Build:* only if `final >= +1`: `stabilize` → `top_pin +1`; `shrimp` → `bottom_space +1`. **No cross-track weakening** exists in v0.

Consume applies to the initiator's own track, wear to the responder's other track, and build to a non-break-capable action, so no track is touched twice in one exchange.

## 6. PASS

A PASS is a submitted decision with an **empty** action id (and empty response id and commitments). Either role may pass when it is the initiator. An accepted PASS:

* costs **no stamina** and produces **no grade**; the axis, band, tiers, latches and remainders are untouched;
* flips the initiator;
* advances the clock by **nothing**. The simulated clock is consumed only by opening a normal decision window (§7); PASS is never a way to freeze simulated time, and two passing fighters still run the match to the clock;
* is recorded as its own decision kind (`"pass"`) with the stable fighter id, so a later match owner can classify activity (§9). The position owns **no** inactivity counter, no stalling penalty, no Momentum and no Heart of a Lion state.

A refused PASS (any code of §8) changes nothing.

## 7. Windows, clock, timeout and terminal states

* `open_window(duration = None)`, in this precedence: `window_already_open`; context errors (§8); `invalid_duration` (neither `None` nor an `int`; a `bool` is not an `int`); `invalid_window_request` (`duration < 0`). `None` means `interval_seconds`; `0` is a legal zero-time window. `elapsed = min(duration, clock_seconds)`, `clock_seconds -= elapsed`.
  * If the clock is now `0`, the report is `closed`: **no window opens**, the window id is unchanged and, if no exit occurred, `exit_reason = "TIMEOUT — Side Control retained"` (an em dash, U+2014). `exit_destination` stays empty. This is a terminal outcome, never an exit, and has no winner or score.
  * Otherwise `window_id += 1` and the window opens for the **current initiator** (`window_open = true`, `window_initiator = initiator`).
* `submit(...)` closes the window on success. `attempt(...)` is the window-less path used by exchange grids: it acts for the current initiator, is refused `window_already_open` while a window is open, requires an action (it cannot pass), and records the last issued `window_id`.
* A successful `submit` or `attempt` report carries `transition`: `{"kind": "none", "raw_destination": "", "destination_position_id": "", "resolved": false}` for a non-exit exchange or a PASS, and for an exit `{"kind": "exit", "raw_destination": <label>, "destination_position_id": <id of §3.4>, "resolved": true}` (`resolved` means the label maps to a declared position id; it does **not** mean a receiver exists). Window-open reports carry no `transition`.
* An exit grants no extra action, window or time; after any exit or timeout every command is refused (§8) before any tier is read.

## 8. Admission and refusal precedence (nothing mutates on any refusal)

**Context** (`context_error`, in this order): `missing_state` (a required key or nested shape absent or of the wrong type); `invalid_stamina_state` (a pool's current/maximum out of range); `invalid_exhaustion_latch` (latch inconsistent with the thresholds); `invalid_initiator`; `invalid_clock_context` (`clock_seconds`, `initial_seconds`, `interval_seconds` out of range, `clock_seconds > initial_seconds`); `terminal_exchange` (`ended`); `invalid_side_control_context` (axis outside `-40 … +40`, an illegal `(axis, band)` pair, a tier outside `0 … 2`, an unknown `exit_destination`, a window id outside range).

**`submit(window_id, fighter_id, action_id, response_id, commitment, response_commitment)`:** `malformed_command` (`window_id` not an `int`, or any other argument not a string; a `bool` is not an `int`) → `no_open_window` → `stale_window` (`window_id` differs from the issued id) → context → `window_initiator_changed` → `missing_fighter_id` (empty) → `unknown_fighter` → `not_initiator` → `response_without_action` → `commitment_without_action` (a PASS carrying a commitment or a response commitment) → `invalid_commitment` → `invalid_response_commitment` (a non-empty value outside `LOW`/`MEDIUM`/`HIGH`) → `unknown_action` → `incorrect_action_side_or_kind` → `unknown_response` (an empty response with an action is `unknown_response`) → `incorrect_response_side_or_kind`.

**`attempt(action_id, response_id, commitment, response_commitment)`:** `malformed_command` → `window_already_open` → context → `invalid_commitment` → `invalid_response_commitment` → `unknown_action` → `incorrect_action_side_or_kind` → `unknown_response` → `incorrect_response_side_or_kind`.

*Unknown* means the id is not one of the 12 catalog ids. *Incorrect side or kind* means a catalog id of the wrong kind (a response given as an action) or the wrong side (an action not owned by the initiator's role; a response not owned by the opposite role). A foreign id (a Mount or Half Guard technique) is `unknown_action` or `unknown_response`. Contract-level addressing codes (`missing_command`, `unknown_position`, …) belong to the later contract layer and are not part of this sheet. The cost policy is fixed (3/7/12); `unsupported_matchup` is unreachable because all 18 cells exist.

## 9. Decisions, snapshots and replay

**`decision_history`** is one ordered list with one record per accepted decision (exchange or PASS); a refusal appends nothing. Common fields: `kind` (`"exchange"` or `"pass"`), `window_id` (the window it closed, or the last issued id for `attempt`), `fighter_id` and `role` of the initiator.

An exchange record adds: `responder_id`; `action_id`; `response_id`; `commitment_requested`, `response_commitment_requested` (after the MEDIUM default); `initiator_effective`, `responder_effective` (`""` when unfunded); `initiator_charged`; `responder_charged`; `responder_waived`; `raw_grade`; `final_grade` (integers `-2 … +2`); `axis_before`, `axis_after`, `band_before`, `band_after`; `exit_destination` (`""` if none); `readiness_changes`, a list in §5.7 order with one `{"track", "before", "after", "cause"}` entry per tier that actually changed (`cause` is `consume`, `wear` or `build`). A PASS record has only the common fields. Together with the decision kind and fighter id this is enough for a later classifier to derive meaningful activity per fighter.

**`snapshot()`** is a canonical, detached, JSON-able dictionary of the whole state: `position_id` (`"side_control"`), `role_map`, `initiator`, `axis_tenths`, `band`, `top_pin`, `bottom_space`, `fighters` (per id: `stamina_current`, `stamina_maximum`, `exhaustion_latched`, `behavior_remainder_units`), `initial_seconds`, `clock_seconds`, `interval_seconds`, `window_id`, `window_open`, `window_initiator`, `exit_destination`, `exit_reason`, `decision_history`. Authority, `ended` and the transition view are derived and are **not** stored. Mutating a returned snapshot never affects the position. The canonical byte form is the JSON text with sorted keys, separators `(",", ":")` and ASCII escaping; a refusal leaves it byte-identical.

**Replay:** the same entry and the same operation list always reproduce the same results and the same final snapshot byte for byte. Nothing reads a clock, randomness, the environment or dictionary iteration order into a result.

## 10. Exits are honestly unsupported

The four exits of §3.4 end the prototype with the destination recorded. v0 builds **no** receiving position, activates nothing, resolves no return route and derives no score or winner. `Side Control → Half Guard` is a future return-route target that needs its own approved design (segment identity and re-entry); it is not implemented here. The `Reversal` landings of Mount and Side Control remain unresolved and have no id here.

## 11. Explicit exclusions

No submissions, tap or submission-defense rules; no feints, behaviors, drift, recovery or REST; no sealed protocol; no D3-B; no stalling, Momentum or Heart of a Lion state; no scoring; no fighter proficiency or initiative threshold; no Half Guard carry-over; no graph, receiver, snapshot adapter or UI. The entry request cannot supply tiers, an axis or a band.

## 12. Resolved non-numeric details (none changes an approved number)

| # | Resolution |
| --- | --- |
| R-1 | The band-update thresholds of §2 are the SC-N7 hysteresis table, stated independently here with the same numeric values as the shape the proposal approves; the entry axis `+10` yields band `+1` under them. |
| R-2 | The wear table (§5.7) and the funding, magnitude and undercommitment rules (§5.3) are the shared, existing mechanics SC-N5/SC-N6 name; they are restated here so no other document is needed. |
| R-3 | `decision_history` replaces per-quantity parallel arrays and records PASS as a distinguishable kind with the fighter id (SC-D8). Passes are not counted as initiations. |
| R-4 | Empty `commitment` and `response_commitment` default to `MEDIUM` for every exchange, in both `submit` and `attempt`. |
| R-5 | `attempt` is refused while a window is open, so the window-less path cannot desynchronize a window from the initiator. |
| R-6 | `malformed_command` is a typed fail-closed boundary; contract-level addressing is excluded. |
| R-7 | A refused exchange never charges anything; a PASS never charges anything. `terminal_exchange` is a context error and precedes every command-shape error that follows context. |
| R-8 | `window_initiator_changed` is unreachable through the public API and is exercised only through a corrupted snapshot. |
| R-9 | Defense strength and wear use the responder's **funded effective** commitment; only HIGH *preservation* uses the charge actually paid. A LOW or unfunded defender is evaluated at tier None whatever its track. |
| R-10 | An exchange by an unfunded initiator (stamina below 3) is legal; Rule 1 then waives the responder's charge. |
| R-11 | Exit reason strings are descriptive text only and carry no rule. |

## 13. Versioning and worked examples

This is rules version `side_control_v0`. A change to any approved constant needs a new sheet version, owner approval and a measured justification; the oracle's table-consistency test parses §2–§3 of this sheet and fails when the two disagree.

Worked examples (every arithmetic step; `T` = Top, `B` = Bottom, 100/100 stamina, tiers 1/1, entry state unless stated):

1. **Plain exchange.** `T` Advance to Mount vs `forearm_frame`, MEDIUM/MEDIUM. `raw = +1`; positional 0 (band +1); attack readiness `1 - 1 = 0`; the response is not governed; exhaustion 0; magnitude 0 (MEDIUM); undercommitment 0 (ranks equal). `final = +1`; `proposed = 10 + 10 = 20 < 30` → no exit. Axis `20`, band stays `+1` (`20 < 27`, `20 > 8`). The initiator flips to `B`. Charges 7 and 7 → both at 93. No tier changes (not Ready; no governed response; Advance does not build).
2. **Exit.** Axis `20`, band `+1`, `top_pin = 2`. `T` Advance to Mount at HIGH vs `bridge_defense` at MEDIUM. `raw = +1`; attack readiness `2 - 1 = +1` → `+2`; not governed; exhaustion 0; magnitude 0 (HIGH acts only on `±1`, and `g4 = +2`); undercommitment `+1` (MEDIUM rank 2 `<` HIGH rank 3) → saturates at `+2`. `final = +2`; `proposed = 20 + 20 = 40 >= 30` and `final >= +1` → exit `Mount` (`mount`). Axis clamps to `40` (already 40), band `+1 → +2` (`40 >= 27`). The initiator does **not** flip. Consume: break-capable at Ready → `top_pin = 1`. Charges 12 and 7.
3. **Defense readiness.** `T` Advance to Mount vs `hip_escape`, both MEDIUM, `bottom_space = 0`. `raw = -2`; attack readiness `1 - 1 = 0` → `-2`; defense: strength tier 0 (None) → shift `+2` → `0`. `final = 0` (Contested), axis unchanged. MEDIUM wear: `final == 0` → none.
4. **Unfunded initiator.** `B` has stamina 2 of 100 (latched, so Exhausted) and requests MEDIUM Turn to Knees vs `shoulder_pressure` (MEDIUM, `T` at 100). `determine(MEDIUM, 2)` → unfunded. `raw = 0`; positional 0; attack readiness `1 - 1 = 0`; not governed; exhaustion `-1` (initiator Exhausted) → `-1`; magnitude on `g4 = -1` for an unfunded initiator → 0; undercommitment: responder rank 2 `<` initiator rank 0 is false → 0. `final = -1`; Bottom `delta = -10 * -1 = +10` → axis `20`. Rule 1 waives `T`'s charge (waived `7`, charged `0`); `B` pays `0`. No readiness change.
