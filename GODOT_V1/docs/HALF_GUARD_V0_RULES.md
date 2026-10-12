# Half Guard v0 — canonical rules sheet (B1b oracle baseline)

**Status: provisional v0 prototype baseline for the independent oracle. This is a qualified-prototype target, not final game balance.** The owner selected
the implementation-baseline decisions N-1 … N-11 of `HALF_GUARD_V0_PROPOSAL.md` §12.13.1 with the selections recorded in §1. This sheet restates the accepted rules as one
self-contained, ordered specification; the Python oracle (`tests/oracles/half_guard_v0.py`) is written from **this sheet**, not from any GDScript. No GDScript Half Guard class exists yet.

**Provenance of earlier evidence.** The B1a proposal (`HALF_GUARD_V0_PROPOSAL.md`) and its prototype measurements (Appendices A–E: reachability counts, random-play splits, horizon values,
exit windows) were computed for the **proposal-stage grades ("C0": Knee Slice vs Hip Frame = 0)**. They are historical proposal evidence. They are **not** measurements of this C1 baseline, and no
number from them is restated here as a property of C1. Every count reported for this baseline comes from the oracle checkpoint's own tests (§9).

Mount, the graph, F0/F1, the frozen Python engine, existing fixtures, the digest and CI routing are untouched by this baseline.

## 1. Selected decisions (N-1 … N-11)

| # | Selection |
| --- | --- |
| N-1 | Two readiness tracks, `top_base` and `bottom_frame`; tiers `0 None`, `1 Partial`, `2 Ready`; entry `Partial/Partial` (1/1); no decay |
| N-2 | Option M: only **Knee Shield** and **Knee Pin** are readiness-governed counters |
| N-3 | Attack readiness shift for Knee Slice (reads `top_base`) and Recover Guard (reads `bottom_frame`): Ready `+1`, Partial `0`, None `−1` |
| N-4 | Defense readiness shift (toward the initiator) for Knee Shield (reads `bottom_frame`) and Knee Pin (reads `top_base`): Ready `−1`, Partial `0`, None `+2` |
| N-5 | Preparation changes by ±1 tier on a successful accepted exchange (final grade ≥ Success), per the table of §5.4 |
| N-6 | Attempting a prepared (break-capable) technique while the initiator's own track is Ready spends one tier, whatever the result |
| N-7 | Uniform update order for every accepted exchange, **including exits** (§6) |
| N-8 | LOW / MEDIUM / HIGH defensive wear table (§5.5) |
| N-9 | HIGH preservation only if the HIGH charge was actually paid; the Rule 1 waiver is applied without changing the frozen Mount rules (§5.6) |
| N-10 | **C1**: Knee Slice vs Hip Frame raw grade is **+1** (not 0); the other 14 grades are as proposed |
| N-11 | Axis, band, hysteresis, exit-map, initiative and positional-modifier values of §2 as provisional v0 constants |

## 2. Axis, bands and constants

* Axis: signed **integer tenths**, `−40 … +40`; positive = Top passing advantage; entry axis `+5`, entry band `0`. The decimal `axis / 10` is a view only.
* Bands are ordinals: `−2 BOTTOM_CONTROL`, `−1 BOTTOM_EDGE`, `0 CONTESTED`, `+1 TOP_EDGE`, `+2 TOP_CONTROL`.
* Initial band of an axis `a`: `|a| < 10 → 0`; `10 ≤ |a| < 25 → ±1`; `|a| ≥ 25 → ±2` (sign of `a`).
* Band update (applied repeatedly until no rule matches; rules are mutually exclusive per band):

| From band | Rule | To band |
| --- | --- | --- |
| 0 | `a ≥ 12` | +1 |
| +1 | `a ≥ 27` | +2 |
| −1 | `a ≥ −8` | 0 |
| −2 | `a ≥ −23` | −1 |
| +2 | `a ≤ 23` | +1 |
| +1 | `a ≤ 8` | 0 |
| 0 | `a ≤ −12` | −1 |
| −1 | `a ≤ −27` | −2 |

* Legal (axis, band) pairs: band 0 `−12 < a < 12`; +1 `8 < a < 27`; +2 `a > 23`; −1 `−27 < a < −8`; −2 `a < −23`.
* Authority (reported only; no mechanical effect): the Top fighter id if `a > 0`, the Bottom fighter id if `a < 0`, `""` if `a == 0`.
* Break lines: Top `proposed ≥ +30`; Bottom `proposed ≤ −30`. Step: `10` tenths per final-grade step. Positional modifier `−1` for an initiator facing the opposing CONTROL band (Top vs band −2; Bottom vs band +2), else `0`.
* Grades: `−2 Strong Failure`, `−1 Failure`, `0 Contested`, `+1 Success`, `+2 Strong Success`; shifts saturate at ±2 **after every step**.
* Stamina (frozen position-independent policy, restated): costs LOW 3 / MEDIUM 7 / HIGH 12; enter threshold `floor(0.25·max)` (latch when `current ≤`), recover threshold `ceil(0.35·max)` (unlatch when `current ≥`); both computed with the frozen float formulas.
  Stamina band: `Exhausted` if latched, else `Fresh` if `current/max > 0.75`, `Working` if `> 0.50`, else `Tired` (float division, as the frozen engine).

## 3. Catalog and the 15 raw grades (C1)

| Id | Side | Kind | Break-capable |
| --- | --- | --- | --- |
| `half_guard.top.crossface` | top | action | no |
| `half_guard.top.flatten` | top | action | no |
| `half_guard.top.knee_slice` | top | action | **yes** (pass → Side Control) |
| `half_guard.bottom.underhook` | bottom | action | no |
| `half_guard.bottom.recover_guard` | bottom | action | **yes** (→ Open Guard / Closed Guard) |
| `half_guard.bottom_response.hip_frame` / `.underhook_fight` / `.knee_shield` | bottom | response | — (Knee Shield is governed) |
| `half_guard.top_response.head_control` / `.hip_pressure` / `.knee_pin` | top | response | — (Knee Pin is governed) |

Raw grade from the initiator's point of view (all 15 cells; **bold = changed by C1**):

| Top initiator \ Bottom response | Hip Frame | Underhook Fight | Knee Shield |
| --- | --- | --- | --- |
| Crossface | +1 | −1 | 0 |
| Flatten | −1 | +1 | +1 |
| Knee Slice | **+1** | +2 | −2 |

| Bottom initiator \ Top response | Head Control | Hip Pressure | Knee Pin |
| --- | --- | --- | --- |
| Underhook | −1 | 0 | +1 |
| Recover Guard | +2 | +1 | −2 |

Exit map (the only exits): Knee Slice with `final ≥ Success` and `proposed ≥ +30` → `Side Control`; Recover Guard with `proposed ≤ −30` → `Open Guard` if `final == Success`, `Closed Guard` if `final == Strong Success`.
Destination ids: `side_control`, `open_guard`, `closed_guard`. No unresolved label, no return to Mount.

## 4. State, entry and identity

State: `axis_tenths`, `band`, `initiator` (`top` | `bottom`), per fighter id: stamina current, maximum, latched flag and a carried behavior remainder (never changed), the role map (`top`/`bottom` → fighter id), `top_base`, `bottom_frame`,
`initial_clock`, `clock_seconds`, `interval_seconds`, `window_id` (last issued), `window_open`, `window_side`, `exit_destination`, `exit_reason`, histories. `ended = clock_seconds == 0 or exit_destination != ""`.
State belongs to the **fighter id**; roles are labels over the role map.

**Entry request** (the only way to build a match):

```
{"role_map": {"top": id, "bottom": id},
 "fighters": {id: {"stamina_current": int, "stamina_maximum": int, "exhaustion_latched": bool, "behavior_remainder_units": int}, ...},
 "clock": {"initial_seconds": int, "remaining_seconds": int},
 "window": {"last_issued_id": int},
 "interval_seconds": int}
```

Validation (pure, nothing is built on error), first failing code wins, in this order:
1. `entry_not_a_dictionary`; 2. `entry_malformed` (any missing or extra key at any level; a wrong type — `bool` is not an `int`, a float is not an `int`);
3. `invalid_fighter_id` (a role-map id that is empty, is padded at either end by any code point `0x01 … 0x20`, or the two ids are equal — exactly Godot's `String.strip_edges` set, measured with Godot 4.7.2; `0x7f`, `0x85`, `0xa0`, the Unicode spaces and `0xfeff` are **not** stripped and are accepted; interior whitespace is accepted); 4. `fighters_mismatch` (the `fighters` keys differ from the two role-map ids);
5. `invalid_stamina_maximum` (`1 … 9007199254740991`); 6. `invalid_stamina_current` (`0 … maximum`); 7. `inconsistent_exhaustion_latch` (`current ≤ enter` requires latched; `current ≥ recover` requires not latched; between: either);
8. `invalid_behavior_remainder` (`|r| ≤ 9007199254740991`); 9. `invalid_clock` (`initial ∈ 1 … 9007199254740991`, `remaining ∈ 1 … initial`); 10. `invalid_window_id` (`0 … 9007199254740991`); 11. `invalid_interval` (`1 … 9007199254740991`).
Fighters are checked in role order (top, then bottom) within steps 5–8.

Built state: axis `+5`, band `0`, `top_base = bottom_frame = 1`, initiator `top`, `window_id = last_issued_id`, no window open, empty histories, `exit_destination = ""`. **No tier key is accepted in the request** (it is an extra key → `entry_malformed`).

## 5. The exchange

An exchange is one accepted request by the current initiator (`attempt`, §7). The ordered settlement:

**5.1 Admission** — all before any mutation (§8). **5.2 Capture** (before any charge): the initiator's and responder's stamina bands; the pre-exchange tiers; axis and band.

**5.3 Funding and grading.**
1. `initiator_effective = determine(commitment, initiator.current)`; `responder_effective = determine(response_commitment or MEDIUM, responder.current)`, where `determine(requested, current)` is the highest tier ≤ `requested` whose cost ≤ `current`, or unfunded (`""`).
2. `raw = RAW[action][response]`; `g1 = shift(raw, positional)`.
3. **Attack readiness** (Knee Slice reads `top_base`, Recover Guard reads `bottom_frame`, tier of the initiator's own track): `g2 = shift(g1, tier − 1)`; other actions `g2 = g1`.
4. **Defense readiness** (response Knee Shield reads `bottom_frame`, Knee Pin reads `top_base`): the *strength tier* is `0` (None) if `responder_effective` is LOW or unfunded, else the responder's track tier; `g3 = shift(g2, {2: −1, 1: 0, 0: +2}[strength tier])`; other responses `g3 = g2`.
5. **Exhaustion**: `modifier = (−1 if initiator band == Exhausted) + (+1 if responder band == Exhausted)`; `g4 = shift(g3, modifier)`.
6. **Magnitude** on `g4`: initiator effective HIGH: Success → `+1`, Failure → `−1`; LOW or unfunded: Strong Success → `−1`, Strong Failure → `+1`; otherwise `0`. `g5 = shift(g4, magnitude)`.
7. **Undercommitment**: ranks unfunded 0, LOW 1, MEDIUM 2, HIGH 3; `+1` if `rank(responder_effective) < rank(initiator_effective)`; `final = shift(g5, undercommitment)`.

**5.4 Axis, exit, initiative.** `delta = +10·final` (Top) or `−10·final` (Bottom); `proposed = axis + delta`. Exit per §3. Then `axis = clamp(proposed, −40, +40)`, `band = band_update(axis, band)`
(**the clamp and band update also happen on an exit**). Initiative flips unless the exchange exited. On an exit: `exit_destination` is the label, `exit_reason` is
`"<Technique name> reached the pass line with final grade <Grade name>"` (Knee Slice) or `"<Technique name> reached the escape line with final grade <Grade name>"` (Recover Guard).

**5.5 Stamina charges** (after grading, initiator then responder, each `spend_up_to`): the initiator pays its effective cost; the responder pays its effective cost **unless Rule 1 waives it**
(the initiator's effective commitment is unfunded), in which case the charge is `0` and the waived amount is recorded. Rule 1 is ON, Rule 2 (supplemental hold) does not exist. Pools latch and unlatch by the thresholds of §2.

**5.6 Paid effort.** `paid_effort = (responder effective cost > 0) and (charged ≥ responder effective cost)`. Requested, funded-effective and charged commitment are three distinct recorded quantities.

**5.7 Readiness updates** (after the charges; each step saturates at `0 … 2`; this is the only place tiers change):
1. *Consume*: if the action is break-capable and the initiator's own track tier is Ready (2) → that track `−1`.
2. *Wear* of the responder's governed track (only if the response is Knee Shield or Knee Pin): by `responder_effective` —
   LOW or unfunded: none; MEDIUM: `−1` if `final != 0`; HIGH and paid: `−1` only if `final ≥ +1` (the defense failed); HIGH and **not paid** (waived): as MEDIUM, `−1` if `final != 0`.
3. *Build / weaken*, only if `final ≥ +1`: Crossface `bottom_frame −1`; Flatten `top_base +1`; Underhook `bottom_frame +1`; Recover Guard `top_base −1`; Knee Slice none.

## 6. Uniform processing (N-7)

Every accepted exchange, exit or not, is processed in this order: admission → capture → grade (from pre-exchange tiers) → axis/band/exit/initiative → stamina charges → readiness updates (consume, wear, build) → histories → terminal fields.
There is no exit special case: terminal tiers are the post-exchange values; the exit grants no extra action or window; initiative stays as is; later commands are refused `terminal_exchange` before any tier is read.

## 7. Windows, clock and passes

* `open_window(duration = None)`: `window_already_open` → context errors → `invalid_duration` (not `None` and not an `int`; a `bool` is not an `int`) → `invalid_window_request` (`duration < 0`). `None` means `interval_seconds`; `0` is a legal zero-time window.
  `elapsed = min(duration, clock_seconds)`; `clock_seconds −= elapsed`. If the clock is now `0` the report is `closed`, **no window opens**, the window id is unchanged and, if no exit occurred, `exit_reason = "TIMEOUT — Half Guard retained"`.
  Otherwise the window id increments, the window opens for the current initiator.
* A successful `submit` report carries `transition`, semantically `BjjPositionContract.Transition.fields()`: `{"kind": "none", "raw_destination": "", "destination_position_id": "", "resolved": false}` for a non-exit exchange or a pass, and for an exit
  `{"kind": "exit", "raw_destination": <label>, "destination_position_id": "side_control" | "open_guard" | "closed_guard", "resolved": true}`. A label that is not one of the three declared destinations would be `kind: "exit"`, `resolved: false` with an empty destination id (never silently mapped). Window-open reports carry no `transition`.
* `submit(window_id, fighter_id, action_id, response_id, commitment, response_commitment)` (§8) closes the window on success. An empty `action_id` is a **pass** (no stamina, no clock, no grades): the initiator flips and `reset_window_history` records the side; either side may pass.
  An exchange with an empty `commitment` uses `MEDIUM`.
* Strict alternation: the Top opens at entry; after every accepted non-exit exchange and every pass the initiator flips.
* The match-level `attempt` (used by exchange grids) acts for the current initiator without a window; its `commitment` must be non-empty and valid; an empty `response_commitment` is `MEDIUM`.

## 8. Admission and refusal precedence (nothing mutates on any refusal)

**Context** (`validate_context`, in this order): `missing_state`; `invalid_stamina_state` (a pool's current/maximum out of range); `invalid_exhaustion_latch` (latch inconsistent with the thresholds);
`invalid_initiator`; `invalid_clock_context` (`clock_seconds`, `initial_clock`, `interval_seconds` out of range); `terminal_exchange` (`ended`); `invalid_half_guard_context` (axis out of range, illegal (axis, band), a tier outside `0 … 2`, an unknown `exit_destination`).

**`submit`**: `no_open_window` → `stale_window` → context → `window_initiator_changed` → `missing_fighter_id` → `unknown_fighter` → `not_initiator` → `response_without_action` → `commitment_without_action` (a pass carrying a commitment or response commitment) →
`invalid_commitment` → `invalid_response_commitment` → `unknown_action` → `incorrect_action_side_or_kind` → `unknown_response` → `incorrect_response_side_or_kind`.
**`attempt`** (match level): context → `invalid_commitment` → `invalid_response_commitment` → `unknown_action` → `incorrect_action_side_or_kind` → `unknown_response` → `incorrect_response_side_or_kind`.
An empty response id with an action is `unknown_response`. The cost policy is fixed (3/7/12), so `unsupported_cost_policy` has no oracle case. `unsupported_matchup` is unreachable because all 15 cells exist.

## 9. Histories, records and replay

Histories (per accepted exchange unless noted): `initiated_action_history`, `response_history`, `raw_grade_history`, `modified_grade_history` (grade names), `initiator_effective_commitment_history`, `responder_effective_commitment_history` (`""` for unfunded),
`response_charge_history`, `response_waived_history`, `band_change_history` (`"<before>-><after>"`, one net entry when the band changed), `readiness_change_history` (`"<track>:<before name>-><after name>:<action short name>"`, one entry per tier that changed, in §5.7 order),
`reset_window_history` (per pass), `top_initiation_count`, `bottom_initiation_count`. A snapshot (`snapshot()`) is a canonical JSON-able dictionary of the whole state; refusals leave it byte-identical. Replay of the same entry and command list is deterministic and bit-identical.

## 10. Resolved non-numeric details (owner-accepted with the B1b continuation; none changes a number)

| # | Resolution | Note |
| --- | --- | --- |
| A-1 | `band_change_history` records **one net `before->after` entry per accepted exchange** whose band changed (a multi-band jump is one entry) | resolved |
| A-2 | `readiness_change_history` uses tier **names** (`None`/`Partial`/`Ready`) and the initiator's action short name; the cause (consume / wear / build) is implied by the §5.7 order | resolved |
| A-3 | `top_initiation_count` / `bottom_initiation_count` count **accepted exchanges only**; a pass is recorded in `reset_window_history` and is not an initiation | resolved |
| A-4 | A fighter id is padded if it differs from itself stripped of the code points `0x01 … 0x20` — the exact `String.strip_edges` set of Godot 4.7.2, which `BjjPositionContract.fighter_ids_error` uses. Godot does **not** strip `0x7f`, `0x85`, `0xa0`, `0x1680`, `0x2000–0x200b`, `0x2028/9`, `0x202f`, `0x205f`, `0x3000`, `0xfeff`; those ids are valid. A Godot `String` cannot hold NUL, so NUL is outside the contract | measured, not assumed |
| A-5 | Stamina bands and thresholds use the **frozen float formulas** (`current / max > 0.75`, `floor(0.25·max)`, `ceil(0.35·max)`); exact-integer forms differ at capacities above about 2^52 | resolved |
| A-6 | A refused exchange never charges anything; a pass never charges anything | resolved |
| A-7 | `terminal_exchange` is a context error and precedes every command-shape error | resolved |
| A-8 | `window_initiator_changed` is unreachable through the public API; the oracle exercises it only through a corrupted snapshot | defensive guard |
| A-9 | Timeout `exit_reason` is `"TIMEOUT — Half Guard retained"`; `exit_destination` stays `""` | resolved |
| A-10 | Defense **strength** and **wear** use the responder's *funded effective* commitment; only HIGH *preservation* uses the charge actually paid. A LOW or unfunded defender is evaluated at tier **None** whatever its track | resolved |
| A-11 | The effective-commitment test for wear uses the value granted by funding **before** the Rule 1 waiver | resolved |
| A-12 | An exchange by an unfunded initiator (stamina < 3) is legal; Rule 1 then waives the responder's charge | resolved |
| A-13 | `behavior_remainder_units` are carried in the snapshot and never changed | resolved |
| A-14 | Contract-level addressing codes (`missing_command`, `unknown_position`, …) are not part of the oracle; they belong to the Godot contract layer | resolved |
| A-15 | **HIGH preservation on Contested:** a paid HIGH defense is preserved on a Contested result (`final == 0`) and on a defense success; it wears only when the defense failed (`final ≥ +1`) | resolved |

## 11. Known properties (measured on this C1 baseline; recorded, not failures, not a balance claim)

All numbers below come from the oracle checkpoint's own tests (`tests/test_half_guard_oracle.py`, `StructuralSearchTests`); re-run to refresh. Stamina, exhaustion, commitment settlement and readiness are all **included** (these are searches over the real oracle, not prototypes).

* **Cooperative reachability** (both fighters choose freely, MEDIUM commitments, passes allowed, horizon 8 windows): Side Control is first reachable in **3** windows, Closed Guard in **4**, Open Guard in **4** (1,480 distinct states explored).
* **Best-counter stalemate (known property).** Against a responder that always plays the lowest-raw-grade counter to the visible action, while the attacker may choose any action, any pass and one fixed commitment:
  with **matched** commitment (attacker and responder both LOW, both MEDIUM, or both HIGH) **no exit is reachable within 12 windows** (279 / 826 / 119 states explored).
  The stalemate is **not robust to a commitment mismatch**: attacker HIGH vs a fixed-MEDIUM responder reaches Side Control at window 5, Open Guard at 6 and Closed Guard at 10; attacker MEDIUM vs a fixed-LOW responder reaches Side Control at 5 and Open Guard at 8; attacker LOW vs a fixed-MEDIUM responder reaches none.
  The mechanism is the existing undercommitment (+1) and defensive wear; it is a property of the *direct-technique baseline with a constant-commitment responder*, not of the rules in general. It is a reachability fact, not a statement about fairness or fun.
* **Decisive counters under the full pipeline** (best final grade a Knee Slice can reach from raw −2 against Knee Shield, band 0, defender making the MEDIUM/HIGH effort; "plain" = no stamina effect, "lifted" = best over every coherent exhaustion, magnitude and commitment combination):

| Attacker tier \ defender tier | Ready | Partial | None |
| --- | --- | --- | --- |
| None | −2 / −1 | −2 / −1 | 0 / +2 |
| Partial | −2 / −1 | −2 / −1 | 0 / +2 |
| Ready | −2 / −1 | −1 / +1 | +1 / +2 |

  The proposal-stage table (B1a §12.1.4) listed 0 in some "lifted" cells because it combined stamina lifts that cannot co-occur (for example an unfunded attacker who is not Exhausted). This coherent table supersedes it. **Defensive effort matters:** a defender answering at LOW (or unfunded) is evaluated at tier None whatever its track, so a Ready defender who answers LOW against an unprepared attacker concedes `+1` (test `test_a_low_response_is_unprepared_even_against_a_ready_structure`).
* **C1 effect on holds.** Only Knee Shield holds Knee Slice to `≤ 0`, and only Knee Pin holds Recover Guard to `≤ 0` (the proposal-stage table also let Hip Frame hold Knee Slice at no wear).
* **Reachable axis values** (cooperative, all commitments, 10 windows, exits included): every multiple of 5 from −40 to +40, including 0 (reached after clamping).
* Reachability (can each label be reached?) and balance (is play fair or fun?) are separate questions; these tests establish only the former.
* The baseline has no behaviors, drift, recovery, feints, scoring or Standing.

## 12. Remaining non-numeric limitations (none blocks the engine)

| # | Item |
| --- | --- |
| L-1 | The exchange fixture embeds full pre/post snapshots (tens of megabytes); a compact encoding may be preferable later. The Godot parity suite reads it as generated, git-ignored data |
| L-2 | `window_initiator_changed` and the context-error codes other than `terminal_exchange` are reachable only through a corrupted state, so the Godot suite exercises them through its test seam |
| L-3 | Contract-level addressing codes belong to the Godot contract layer and are tested there, not in the oracle |
