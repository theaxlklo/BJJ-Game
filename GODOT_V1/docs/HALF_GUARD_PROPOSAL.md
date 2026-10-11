# Half Guard rules and architecture proposal (PROPOSED — nothing here is approved)

**Status: proposal for owner review. No gameplay, fixture, Python or workflow change.**
Q1–Q8 are NOT fully approved. §11 records the owner's review decisions (conceptual approvals only); all numerical
values in this document remain provisional.
Every number, name and default below is a *recommendation*; none is approved or frozen.
Scope: answers Q1–Q8 of `POSITION_GRAPH.md` §12 for the first Half Guard node (Mount →
Half Guard). Visual direction (Issue #40) is out of scope.

Built from: `POSITION_GRAPH.md` (PR #42, Slice A in PR #43 at `715a499`), `POSITION_CONTRACT.md`,
`WINDOW_GATEWAY.md`, Master Guide v10.4 §§7, 11.4, 12–17, and the Mount sources named below.

## 1. What is already decided, frozen, and new

### 1.1 Approved (D1–D6) — not reopened here
| ID | Decision |
|---|---|
| D1 | Escape preserves fighter IDs and physical `top`/`bottom` roles; Bottom recovers Half Guard (not a reversal). Half Guard has its **own** axis oriented *Top passing advantage vs Bottom retention/offence*; Mount's numeric axis is not reused. Initial values need reviewed rules (§3, Q2). |
| D2 | The exit-producing Mount window is consumed. No window is handed to either fighter; Half Guard decides the next eligible initiative event; no free windows, extra actions or clock changes. |
| D3 | A match-level graph owner holds persistent state and coordinates validated construction of position-specific gateways; new position is built and validated before commit; no partial mutation. |
| D4 | Shared stamina/exhaustion persists. Mount's Rule 1/2, Bottom RECOVER and D3-B are not automatically reused; primitives vs policies must be separated; D3-B must not grant tokens through transitions. |
| D5 | `Reversal` stays unresolved; unsupported transitions are explicit and not a normal terminal outcome; rejected commands are distinct from accepted exchanges reaching an unsupported destination. |
| D6 | Focused, independent, test-only Python oracle with frozen fixtures after the rules are accepted; no second production engine; Mount reference untouched. |

### 1.2 Frozen Mount behavior (must not change)
Mount catalog (12 entities, 18 raw grades), axis `0.10..4.00` with hysteresis bands, drift rates,
positional modifiers, exit maps, setup tiers, commitment semantics, production policy
(Rule 1 ON / Rule 2 OFF, Bottom RECOVER, LOW-while-Exhausted, baseline MEDIUM), D3-B
TOKEN/LOCKOUT_HOLD, `BjjMountContract`, `BjjMatchWindowGateway`, the 13 existing Godot suites,
the Python suite, and enumeration digest `3ee55429…59ff2`. **Any recommendation below that
would touch these is marked as a blocker, not silently assumed.**

### 1.3 New Half Guard rules needing approval
Everything in §§3–5 (Q1–Q5, Q8) plus the architectural items in §6–7 (Q7) and §8 blockers.

## 2. Design principles for the first node

1. **Small but two-sided.** 3 actions + 3 responses per side, like Mount, with *offence for
   Bottom* (an Underhook → Wrestle-Up progression and a guard-recovery exit) and *passing for
   Top* (a Flatten → Knee Slice progression).
2. **Mirror Mount's structure, not its numbers.** Same shapes (five-grade ordinal, response
   matrices, hysteresis bands, setup tiers gating "target" actions, success-at-boundary exits) so
   reviewers and tooling recognize them; every value is Half Guard's own.
3. **Integer arithmetic.** Axis in integer *centi-steps* (1 grade step = 100). Mount uses
   rounded floats (`round_ten`); a new position needs no float parity burden and the Python
   oracle can match bit-for-bit.
4. **Exits are declared, not assumed.** All three exits (`side_control`, `open_guard`,
   `standing`) are unimplemented today, so each ends at the Slice A unsupported-transition halt.
   No Half Guard → Mount route (POSITION_GRAPH §10).
5. **No new randomness, no free windows.** Every outcome is a function of state and command.

## 3. Axis, entry and authority (Q1, Q2)

### Q1 — Axis convention
Alternatives:

| Option | Description | Trade-offs | Determinism |
|---|---|---|---|
| **A (recommended)** | Signed integer axis; `+` = Top passing advantage, `−` = Bottom retention/offence advantage. Persisted range `−500..+500`. Five bands with hysteresis. | Matches D1 literally; two real exits; neutral is visible. Needs a position-local band table (new). | Pure integer compare. |
| B | Mount-like one-sided axis `10..400` (Top progress only; Bottom wins at floor) | Reuses a familiar shape. Cannot express Bottom *offence* (Underhook/Wrestle-Up) as progress; violates D1 orientation. | Same |
| C | Two independent meters (pass progress, retention progress) | Rich, but breaks the "single signed contest" model in Guide §12 and doubles bands/tests | Same, more state |

Recommended bands (centi-steps, enter / leave hysteresis ≥ one grade step apart):

| Band | Enter | Leave |
|---|---|---|
| `bottom_command` | ≤ −350 | > −250 |
| `bottom_edge` | ≤ −150 | > −50 |
| `contested` | (between) | |
| `top_edge` | ≥ +150 | < +50 |
| `top_command` | ≥ +350 | < +250 |

Positional modifier (mirrors the *role* of Mount's, not its table): an initiator acting while the
**opponent's** side is in `*_command` suffers `−1` grade (Bottom acting in `top_command`; Top acting
in `bottom_command`). No other modifier in v0. Exit crossing: an exit-capable action with a
successful final grade whose proposed axis reaches the outer bound on its own side
(`≥ +500` Top, `≤ −500` Bottom) leaves the position; the crossing value is exit data and is
never persisted (same idea as Mount's `crossing_axis`).

### Q2 — Entry value and control authority
| Option | Description | Trade-offs |
|---|---|---|
| **A (recommended)** | Fixed entry axis `0`, band `contested`, regardless of how Mount was left. | Zero coupling to Mount's exit grade; carry-over record stays minimal; easy to test. The recovered-but-not-secured feel is expressed by the opponent acting first (Q3), not by a bias. |
| B | Entry biased by the exit grade (e.g. `+100` for SUCCESS, `0` for STRONG_SUCCESS) | Rewards a clean escape. Needs the exit grade in the carry-over record and a Mount↔Half Guard calibration. |
| C | Fixed `+100` (Top-favoured) | Models Half Guard as the worse guard; a fixed bias to tune and justify. |

**Control authority** is *derived, never stored*: Top fighter in `top_edge`/`top_command`, Bottom
fighter in `bottom_edge`/`bottom_command`, none (`""`) in `contested`. This needs
`Roles.control_authority_id` to permit empty (a small contract clarification; Mount always sets it).
Alternative: always Top (Mount-like) — simpler but contradicts D1's "retention/offensive
advantage" meaning.

## 4. Initiative, windows, stamina and behavior (Q3, Q4, Q5)

### Q3 — First initiative and alternation
Constraint (D2): the consumed exit window is not handed on; no free window; zero seconds at transition.
The first Half Guard window opens only through the normal path (a time advance by the interval, then a window).

| Option | Description | Trade-offs |
|---|---|---|
| **A (recommended)** | **Strict alternation, Top first.** After every accepted decision *including a no-action (RESET)*, initiative flips. First holder after entry is the position-local `top`. | Same mechanism as frozen Mount (`initiator` flip), minimal new logic; Top first is rule-based, not derived from the consumed window, satisfying D2; matches "top-dominant established position, controlling top ordinarily acts first" (§15 authority rule) even though Half Guard is a contest. |
| B | Opening-triggered: Bottom holds the window when its Wrestle-Up is READY or band is `bottom_*`; else Top | Closer to Guide §15's triggered-initiative text; adds a state-dependent owner function and more edge cases (equal triggers, stall exploits). Defer until a measured need. |
| C | Sealed simultaneous choice (Guide §17) | Out of scope; changes the decision model. |

Setups gate **availability only** (target actions unlock when READY); they never change who holds
the window. Every non-initiating fighter always gets a legal response phase (existing model).
No-action windows are admitted for both sides (Mount's Top RESET precedent; still a rules decision
the owner may revisit).

### Q4 — Behaviors, drift, passive stamina
Mount's passive layer is fixed by configuration (`top_behavior`, `bottom_baseline`) and the
production RECOVER selector (Bottom becomes CONSERVE while Exhausted). It is not exposed to
players anywhere in the gateway today, so Half Guard has no player behavior choice to port.

| Option | Description | Trade-offs |
|---|---|---|
| **A (recommended)** | **No behavior layer and no axis drift in v0.** Passive stamina: a fighter whose band is `Exhausted` flows at the existing position-independent CONSERVE rate (`+2` per 5 s quantum via `BjjBehaviorStaminaPolicy`); any other fighter flows at the HOLD rate (`0`). | Avoids unmeasured drift numbers (Mount's drift came from pre-registered measurement). Gives both fighters a way out of exhaustion (no permanent-exhaustion trap). Symmetric. Without drift, stalling in `contested` is possible; the clock still ends the match and stalling controls remain a separate, later rule (consistent with the project's existing "stalling not ported"). |
| B | Port analogues of the three Mount behaviors per side + a drift table | Familiar, richer; but every drift/stamina number is a new, unmeasured policy. |
| C | No passive stamina at all | Simplest; exhaustion becomes absorbing once reached. |

The drift table exists as an all-zero slot so a measured table can be added later without an
interface change.

### Q5 — Stamina settlement inside Half Guard
Position-independent primitives that exist today and can be reused **unchanged**:
`BjjStaminaPool` (spend/recover/latch), `BjjStaminaCostPolicy` (LOW/MEDIUM/HIGH → 3/7/12 and funding
against available stamina), `BjjExhaustionPolicy.exchange` (initiator Exhausted `−1`, responder
Exhausted `+1`), `BjjCommitment`. Mount-specific *policy* is what is in question:

| Policy | Recommended for Half Guard v0 | Why |
|---|---|---|
| Commitment funding + magnitude modifier + response undercommitment modifier | **Adopt**, restated as Half Guard rules | Position-independent in meaning; omitting them makes Half Guard a different economy from the one the production policy was measured on |
| Exhaustion exchange modifier | **Adopt** | Pure function of bands |
| Rule 1 (initiator unfunded → responder cost waived) | **Adopt, explicitly re-validated by the Half Guard oracle** | Concerns funding, not position; Mount evidence supports the intent |
| Rule 2 / supplemental hold charge | **Not applicable** | Belongs to Mount submission holds; v0 has none |
| Bottom RECOVER / LOW-while-Exhausted baseline | **Not adopted**; replaced by the exhaustion-gated passive recovery in Q4-A, with baseline commitment MEDIUM for both sides | RECOVER fixes a Mount-specific bottom stalemate |
| D3-B TOKEN / LOCKOUT_HOLD | **Frozen, not observed** (Q6) | Mount-measured |

Alternative: adopt *none* of the settlement modifiers (cost only). Cleaner, but changes the economic
meaning of commitments across the graph. **The settlement code currently lives privately inside
`BjjMountExchange.attempt` (see blocker B1).**

## 5. D3-B, catalog and exits (Q6, Q8)

### Q6 — D3-B
Confirm the Slice-A-consistent default: **frozen and never observed in Half Guard.** The graph owner keeps
the Mount-segment controller record read-only; Half Guard receives none and calls neither
`observe_advance` nor `decide`; transitions cannot arm, re-arm or consume a token. Return to Mount is
unsupported; if ever added, reconciliation (rebase `previous_exhausted` without arming vs discard)
needs a separate decision and a controller operation that does not exist today.
Alternative: give Half Guard its own D3-B-style lockout — rejected for v0 (no measurement; "no extra tokens").

### Q8 — First-node catalog (PROPOSED, illustrative grades)
IDs follow the existing convention (`half_guard.<side>.<name>`, responses `half_guard.<side>_response.<name>`).

| Side | Action (id suffix) | Role | Exit (if successful at the bound) |
|---|---|---|---|
| Top | `crossface_pressure` | builds control, free | none |
| Top | `flatten_hips` | **setup** (tiers 0–2) for Knee Slice | none |
| Top | `knee_slice_pass` | **target** (needs READY), pass-capable | `Side Control` (SUCCESS and STRONG_SUCCESS) |
| Bottom | `underhook_fight` | **setup** (tiers 0–2) for Wrestle-Up | none |
| Bottom | `recover_guard` | free, exit-capable | `Open Guard` (SUCCESS and STRONG_SUCCESS) |
| Bottom | `wrestle_up` | **target** (needs READY), exit-capable | `Standing` (SUCCESS and STRONG_SUCCESS) |

Responses — Top responds to Bottom actions: `heavy_crossface`, `whizzer_base`, `knee_line_cut`.
Bottom responds to Top actions: `knee_shield_frame`, `underhook_turn_in`, `hip_escape_hide_knee`.

Raw grades (−2 strong failure … +2 strong success for the **initiator**; one clear counter per row):

| Top action \ Bottom response | knee_shield_frame | underhook_turn_in | hip_escape_hide_knee |
|---|---|---|---|
| crossface_pressure | −1 | +1 | +2 |
| flatten_hips | +1 | −1 | 0 |
| knee_slice_pass | 0 | −2 | +2 |

| Bottom action \ Top response | heavy_crossface | whizzer_base | knee_line_cut |
|---|---|---|---|
| underhook_fight | −2 | −1 | +1 |
| recover_guard | +1 | +2 | −2 |
| wrestle_up | −1 | −2 | +2 |

Axis effect (same convention as Mount): Top-initiated grade `g` → `+100·g`; Bottom-initiated → `−100·g`.
Setup tiers (0 → READY at 2): `flatten_hips`/`underhook_fight` advance their tier by one when the exchange moves
the axis (not absorbed by a clamp) and tier < 2; using the target consumes the tier (set 0). The two Mount
"ready override" pairs have no Half Guard analogue in v0 (setup only unlocks the target).

Alternatives considered for Bottom offence: (1) include a **Sweep** that ends in "Top Half Guard" with swapped
roles — *deferred*: it needs a same-position role-swap rule that Guide §12 allows only as a deliberate
transition and that no contract expresses yet; (2) `Wrestle-Up → Standing` (recommended above) halts at the
boundary but keeps a real offensive route; (3) `Wrestle-Up` as an unresolved exit like Reversal — unnecessary since
`standing` is a declared id.

Open Guard is reachable from both Mount and Half Guard; no new label.

## 6. Carry-over construction and graph ownership (Q7)

### 6.1 Carry-over record (detached, validated, typed)
`BjjCarryOver` (name provisional): `from_position_id`, `to_position_id`, `fighter_ids` (top, bottom),
per-fighter `{current, maximum, latch}` for both pools, per-fighter behavior-flow `remainder_units`,
`initial_clock`, `remaining_clock`, `window_counter`, `event_count`, the frozen Mount controller
record (read-only, not given to Half Guard), and `exit` data (label, optionally the exit grade only
if Q2-B is chosen). `validate()` repeats the Mount context checks that are position-independent
(non-aliased pools, latches consistent with thresholds, clock bounds, identities). It is a value, not a
live object: no reference into the Mount segment survives.

### 6.2 Construction seam (alternatives)
| Option | Description | Trade-offs |
|---|---|---|
| **A (recommended)** | A position-agnostic **segment interface** at the graph boundary (fail-closed virtuals, like `BjjPositionContract`): `open_window`, `submit`, detached views, `carry_over()` export. Mount's gateway implements it by an *additive* wrapper/method; a new `BjjHalfGuardWindowGateway` implements it natively and is built by `create_from(carry_over)`. The graph owner builds the new segment in isolation, validates, then swaps. | No change to frozen Mount logic; one shared admission idea instead of one global rewrite. Requires either a small shared window-ledger helper or accepting ~50 lines of window-admission duplication until Mount is refactored (see B3). |
| B | Generalize `BjjMatchWindowGateway` over `BjjPositionContract` | One gateway, but it must absorb Mount-only `next_window`/`bottom_decision` semantics; large blast radius on a qualified file. |
| C | Graph owner calls positions directly, bypassing gateways | Rejects the qualified admission layer; duplicates window identity. Not recommended. |

### 6.3 Single source of truth after commit
At commit the Half Guard segment owns **newly constructed** pools and meters copied from the record (never aliased
to Mount's objects). The Mount segment is sealed read-only history (it is terminal by exit). Never two live
mutable owners. Tests assert non-aliasing and that no Mount mutator is reachable after commit.

## 7. Testing and verification requirements (negative-first)

Specification gate (before code): owner decisions on Q1–Q8 recorded; a Half Guard rules document (this
proposal, edited); D6 oracle plan accepted.

**Oracle (D6).** Test-only, integer arithmetic, written from the accepted tables rather than from the Godot code,
under `GODOT_V1/tests/` (not `src/`, not the Python shard set) with its own generator and a gitignored generated
fixture, as the repository already does. A small self-check run in the Godot workflow step validates fixture
invariants. *Independence caveat:* if the same author writes both implementations the oracle is not truly independent;
mitigation is that the oracle is derived only from the tables here and reviewed separately.

**Native negative tests (each with whole-state equality before/after rejection):** wrong side, unknown ids, gated
target without READY, response for the wrong action, invalid commitments, terminal state, stale/duplicate windows,
wrong fighter, wrong initiative, invalid carry-over (every field, aliasing, latch inconsistency, clock out of range,
identity mismatch), construction failure leaving Mount and graph untouched.

**Transition tests:** Mount exit → Half Guard commit happens exactly once; zero seconds and zero charge at the
swap; pools/meters/clock/identities bit-identical; first window only via the normal path; no token granted or
consumed; event order `decision_accepted → transition_committed`; old Mount ids rejected afterwards; halts at
Half Guard's own exits (`side_control`, `open_guard`, `standing`) reuse the Slice A boundary.

**Replay:** identical command sequences reproduce identical states and event logs twice over a seed × axis ×
stamina grid; lockstep against the oracle per operation (grade, axis, band, tiers, stamina, exit, histories).

**Regression:** all 13 existing Godot suites, Python 3.11/3.13 suite, digest and checks unchanged; CI routing
requires both Godot and Python because the workflow changes.

**Measurement gate (before freezing numbers).** Mount's numbers came from pre-registered measurement. The grades,
bounds and thresholds above are *provisional v0*. Recommended pre-registered, test-only criteria (no tuning during
measurement): every declared exit reachable by legal play; no single action dominant across responses; both sides
can reach their own exit; expected exchanges-to-exit within a stated range. Failed measurements are recorded, not
edited away.

## 8. Architectural blockers

| ID | Blocker | Impact | Proposed resolution (needs approval) |
|---|---|---|---|
| **B1** | Commitment settlement (funding order, magnitude and undercommitment modifiers `_magnitude`/`_rank`, Rule 1 waiver) is private inside `BjjMountExchange.attempt` | Half Guard cannot reuse it without copying or touching frozen code | Prefer a **behavior-neutral extraction slice** of those primitives (guarded by the 13 suites + exchange oracle) *before* Half Guard; alternative: duplicate ~15 lines in Half Guard and prove equality with the oracle |
| **B2** | `BjjPositionGraphMatch.classify_exit` is hard-wired to Mount's exit table | Half Guard's labels would classify as "undeclared" | Make classification position-aware (active position's declared exit map), backward compatible; its own small slice with Slice A tests unchanged |
| **B3** | `BjjMatchWindowGateway` is Mount-specific (composes `BjjMountMatch`, uses `next_window`/`bottom_decision`) | No gateway exists for another position | Segment interface + new Half Guard gateway (Q7-A); decide shared ledger vs temporary duplication |
| **B4** | Mount segment has no detached carry-over export (meter remainders, controller record) | Cannot build the record | Additive read-only export on `BjjMountMatch`/gateway; no behavior change |
| **B5** | Window ids are a per-gateway counter | Ids must be monotonic across segments with no skipped or reused id | The Mount gateway's `_window_id` is the *last issued* id (incremented before use). The record carries it as `window_counter`; the new segment is seeded with `_window_id = window_counter`, so its first window is `window_counter + 1`. (Seeding with `window_counter + 1` would skip an id; seeding with a lower value would reuse one.) See §11 |
| **B6** | CORRECTED: an empty `Roles.control_authority_id` already exists (`position_contract.gd` declares `""` as the default; Mount always sets the top id) | `contested` needs an empty authority | No type change. Documentation-only: state that empty is legal and means "contested", and that consumers must not assume a non-empty id. Mount unchanged. See §11 |
| **B7** | Oracle independence and placement | Parity claims weaker if not independent | Place under `GODOT_V1/tests/`, derive from tables, separate reviewer |
| **B8** | Provisional numbers without a measurement | Risk of freezing untested balance | Measurement gate (§7) before freeze |

None of B1–B8 requires changing frozen Mount behavior if resolved as proposed; B1 and B4 touch Mount *files*
(extraction/additive export) and must be reviewed as behavior-neutral changes with the full suites.

## 9. Proposed slice order (after approval)

1. **A2 — contract clarifications + graph classification generalization** (B2, B6): no gameplay.
2. **A3 — behavior-neutral settlement extraction + Mount carry-over export** (B1, B4) with the 13 suites.
3. **HG-1 — Half Guard rules document accepted, oracle + fixture (test-only).**
4. **HG-2 — Half Guard position, gateway, carry-over construction, transition commit** (B3, B5), negative-first.
5. Measurement gate; then freeze numbers.

## 10. Decisions requested

| ID | Recommended default | Needs your decision |
|---|---|---|
| Q1 | Signed integer axis ±500, five hysteresis bands (A) | yes |
| Q2 | Fixed entry `0`, `contested`; authority derived from band, empty when contested (A) | yes |
| Q3 | Strict alternation, Top first, RESET admitted for both (A) | yes |
| Q4 | No behavior layer, no drift; Exhausted fighter recovers at CONSERVE rate (A) | yes |
| Q5 | Adopt commitment funding/modifiers, exhaustion modifier and Rule 1; no Rule 2; no RECOVER | yes |
| Q6 | D3-B frozen, never observed in Half Guard | confirm |
| Q7 | Segment interface + additive carry-over (A) | yes |
| Q8 | 3+3 catalog above; Sweep deferred; exits `Side Control`/`Open Guard`/`Standing` | yes |
| B1 | Extraction slice before Half Guard | yes |

## 11. Review decisions recorded (owner review of PR #44)

These are review outcomes, not a blanket approval. Nothing here freezes a number, and no implementation is authorized.

| ID | Recorded decision | Still provisional / open |
|---|---|---|
| Q1 | A signed fixed-point axis is approved **conceptually**. | Numerical bounds (±500), the five bands and their enter/leave thresholds. |
| Q2 | Contested entry at axis zero with **empty** control authority is approved. | Nothing numeric beyond the zero entry value. |
| Q3 | Compare **Bottom-first** against Top-first. Bottom-first is the preferred *proposed* default, **not frozen**. | See §11.1. |
| Q4 | No drift in v0. The Half Guard recovery rate is **defined separately** and explicitly, not inherited implicitly from Mount's CONSERVE rate. | The rate value and its specification. |
| Q5 | Reusable funding primitives are approved. Half Guard modifiers and Rule 1 settlement require **explicit specification and validation** (not assumed to carry over). | Modifier values; Rule 1 restatement and its oracle validation. |
| Q6 | D3-B stays frozen across Half Guard (never observed, never grants a token). | — |
| Q7 | Detached, validated carry-over is approved. Window-counter seeding is corrected (B5, §11.2). | Record schema details and the segment interface. |
| Q8 | A small three-action-per-fighter catalog is approved as a **starting scope**. | Grade tables, thresholds, exit gating; Sweep stays deferred. |
| B1 | Approved as a **future, separately tested, behavior-neutral extraction slice**. Not implemented in this PR. | Slice design and its parity evidence. |

### 11.1 Q3 comparison: Bottom-first vs Top-first
| | Top-first (earlier proposal) | Bottom-first (preferred proposed default) |
|---|---|---|
| Rationale | Top is the established dominant fighter; matches the Guide's authority text. | Bottom has just escaped Mount and is the fighter acting to improve; gives Bottom's offensive options (Wrestle-Up, Recover Guard) the first opening and avoids Top acting immediately on a position it has just lost. |
| D2 compliance | Yes: a rule-based owner, not derived from the consumed window. | Yes, provided the rule is position-local (`bottom` always opens) and never derived from who initiated the exit window. |
| Determinism | Fixed rule. | Fixed rule; no state-dependent owner function. |
| Risks | Top opens against a freshly recovered Bottom, which may feel punishing. | Bottom could be seen as rewarded for escaping; the measurement gate must check Bottom's first-action advantage and that Top's pass is still reachable. |
| Alternation | Strict thereafter in both variants (RESET admitted for both, still the owner's to revisit). | Same. |

The choice is settled only after the measurement criteria are pre-registered and the rules are accepted.

### 11.2 Window counter seeding (correction)
`_window_id` in the Mount gateway is the id of the last window issued, incremented before a window opens. The
carry-over `window_counter` is that value. The consumed exit window therefore holds id `window_counter`, and the first Half
Guard window must be `window_counter + 1`. The new segment is seeded with `_window_id = window_counter`. Tests must assert
no skipped id, no reused id, and that the old Mount window id is rejected after commit.

### 11.3 Empty control authority
`Roles.control_authority_id` is a plain string defaulting to `""`, so an empty authority is already representable. No
contract change is needed. The documentation clarification (empty means contested) is the only change, and Mount's
non-empty authority stays as is.

### 11.4 Measurement and oracle ordering
Measurement criteria must be **pre-registered before any numerical tuning**; failed measurements are recorded, not
edited away. Final oracle fixtures are generated and frozen **only after the rules are accepted**, never from provisional
numbers.
