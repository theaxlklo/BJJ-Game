# Side Control v0 — proposal and Half Guard Knee Slice receiver boundary (B2a)

**Status: DOCUMENTATION ONLY. Nothing here is implemented, and nothing here is approved.** This is a proposal for the project owner to review. It changes no engine, test, fixture, oracle, workflow, default, frozen Python reference or number. Every combat value below is a **proposal**, not an accepted rule, and none is a balance claim. Executable Side Control mechanics need a separate, explicit authorization (see §12 for the recommended B2b boundary).

Stacked on draft PR #63 (`docs/match-incentives-heart-of-lion-spec`, head `650e7e1b9c6ba138a931c2805ce661e2268431b2`). Written against that exact revision; the open PR stack is **not** merged to `main`. **Update 2026-10-13:** the PR stack was integrated into `main` by #66 and development is now local-first; PR-specific wording below (PRs, stacking, "separate PR") is historical and superseded by independent local commit phases (§11A.4). §11A is a recommendation-only owner-decision review; nothing in it is approved.

## 0. How to read the labels

| Label | Meaning |
| --- | --- |
| **[OBSERVED]** | A fact verified in code, tests or a document at the stack head above, with a file reference. |
| **[GUIDE]** | Content listed in the Master Development Guide v10.4 (names and direction only; not numbers, not approval). |
| **[OWNER-APPROVED]** | Direction the owner recorded in an existing document (cited). The approval covers only what the cited text states. |
| **[PROPOSAL]** | New content in this document. Not authorized. Every number carries this label, explicitly or through its table. |
| **[OPEN]** | A decision only the owner can make. Collected in §11. |

Reuse of a Half Guard or Mount **number** below is a proposal for oracle simplicity. It is never an acceptance of that number for Side Control, and no Half Guard or Mount table, constant or class is imported or shared (`bjj-position-slice`: no cloned match with string switches or global rule tables masquerading as reuse).

## 1. Scope contract (`bjj-scope-plan`)

* **Goal.** Specify a second pin position, Side Control, and exactly how a real Half Guard Knee Slice would hand the match to it, so the owner can accept, amend or reject the rules before any code exists.
* **Current implemented behavior [OBSERVED].** Half Guard Knee Slice with final grade ≥ Success and proposed axis ≥ +30 sets `exit_destination = "Side Control"` (`half_guard_resolver.gd:81-83`, `half_guard_catalog.gd:62`, rules sheet `HALF_GUARD_V0_RULES.md:60,79`). The graph then **halts** with `transition_blocked` (`from_position_id = "half_guard"`) because no receiver exists (`HALF_GUARD_V0_ENGINE.md` §"Graph integration"; `test_half_guard_graph.gd`). `side_control` is a declared id in `BjjPositionRegistry` (`position_registry.gd:24,32`) and nothing more.
* **Desired diff of this slice.** One new Markdown file. Excluded: any `.gd`, `.uid`, `.py`, fixture, workflow, `project.godot`, edit of the Master Guide, `PORT_STATUS.md`, `POSITION_GRAPH.md`, `POSITION_TOPOLOGY.md`, `HALF_GUARD_V0_RULES.md` (parsed by `tests/test_half_guard_oracle.py`) or `MATCH_FLOW_DIAGNOSTICS.md`.
* **Single authoritative command path (for the later implementation).** The Side Control gateway would own its own mechanics; the position graph would own only the active-position choice, status and the global event log, through the existing single `_settle_accepted` path (`graph_match.gd:385`). No second simulation, no second settlement.
* **Not changed and not previewed as changed.** Mount and Half Guard mechanics, stamina costs and recovery, scoring, the sealed protocol and feints, production defaults, F0/F1, PR #63's future stalling / Momentum / Heart of a Lion / REST / zero-stamina LOW-memory rules, UI, artwork, careers and AI. The Mount `Reversal` destination stays unresolved (§5.4).

## 2. Sources

Read for this proposal: `AGENTS.md`, `CLAUDE.md`, the skills `bjj-scope-plan`, `bjj-position-slice`, `bjj-pr-handoff`, `bjj-parity-gate`; Master Guide §§7–15, 21–22, 40, 11.4–11.5; `POSITION_CONTRACT.md`, `POSITION_GRAPH.md` (incl. §15), `POSITION_TOPOLOGY.md` (§§5.2, 6, 9.3, 10, 11, 19), `HALF_GUARD_V0_RULES.md`, `HALF_GUARD_V0_ENGINE.md`, `HALF_GUARD_V0_ORACLE.md`, `MATCH_FLOW_DIAGNOSTICS.md`, `MATCH_INCENTIVES_HEART_OF_A_LION.md`; `graph_match.gd`, `half_guard_{catalog,resolver,match,entry,mount_edge,contract,window_gateway}.gd`, `position_registry.gd`. Three read-only specialist reviews are summarized in §13.

## 3. Identity, roles, authority, axis and initiative

### 3.1 Observed contract vocabulary

**[OBSERVED]** Four concepts are never inferred from one another: fighter identity (stable ids supplied once by the graph owner), physical role (position-local), control authority (the fighter on the positive side of the position's signed axis) and initiative (the fighter holding the current decision window) (`POSITION_CONTRACT.md` §Contract). The signed axis is a **position-local contest**, not universally vertical (Guide v10.4 §12 clarification; `bjj-position-slice` step 1). Half Guard reports authority by axis sign with no mechanical effect (`HALF_GUARD_V0_RULES.md` §2); Mount fixes authority on the Top.

### 3.2 Proposed Side Control identity

| Item | Proposal |
| --- | --- |
| Position id | **[OBSERVED]** `side_control` (already declared; `position_registry.gd:24`). Subpositions North-South and Knee-on-Belly stay **variations**, not nodes (Guide §10; T-1 **[OWNER-APPROVED]**), and are not modeled in v0. |
| Fighter ids | Two stable ids that never change across positions (`BjjPositionContract.fighter_ids_error` rules). |
| Roles **[GUIDE]/[PROPOSAL]** | `top` and `bottom` (Guide §11.5 uses Top/Bottom). Physical meaning: `top` is the pinning fighter. |
| Role map at the Knee Slice boundary **[PROPOSAL]** | Identity map: Half Guard `top` → Side Control `top`; Half Guard `bottom` → Side Control `bottom`. Knee Slice is a Top-side technique (`half_guard_catalog.gd:25`), so the fighter who passes is the Top in Side Control. This mirrors the approved Mount→Half Guard D1 precedent (roles preserved, not a reversal, not a score). **[OPEN]** SC-D1. |
| Control axis **[PROPOSAL]** | A Side Control-**own** signed integer in tenths, positive = Top pin/advance control, negative = Bottom recovery/escape advantage. It is never derived from or converted from the Half Guard axis (`POSITION_GRAPH.md` §4 states the same rule for Half Guard versus Mount). |
| Authority **[PROPOSAL]** | Reported only, by axis sign: Top id if axis > 0, Bottom id if axis < 0, empty at 0 (Half Guard convention), with no mechanical effect. Alternative: fixed to the Top for the life of the position (Mount convention). **[OPEN]** SC-D3. |
| Initiative **[PROPOSAL]** | Explicit fighter id, never inferred from physical role (Guide §15 v10.4). In the established position the controlling Top ordinarily acts first. Initiative alternates strictly after every accepted non-exit exchange and every pass, as Half Guard does. The boundary rule for the **first** window is §6.4. |
| Window ownership | Each window is owned by the receiving position's own gateway; the non-initiating fighter always has a legal response phase (Guide §15). |

Hypothetical field names in this document (`top_pin`, `bottom_space`, entry error codes, technique names) are **[PROPOSAL]** names only.

## 4. Compact catalog

The Guide §11.5 lists (Top) Stabilize, Transition to Mount, Expose Back, Kimura route, Armbar route; (Bottom) Shrimp, Recover Guard, Recover Half Guard, Underhook Escape, Bridge, Turn to Knees, Reversal. **[GUIDE]**. The first playable proof should be smaller than the Guide's eventual target (`bjj-position-slice` step 2), so this proposal selects three actions and three responses per side, in the shape of the Half Guard v0 catalog. Technique and response **names** below come from the Guide's lists where possible; the three response names per side are **[PROPOSAL]** and no technique description is invented.

### 4.1 Actions

| Id (**[PROPOSAL]**) | Side | Kind | Break-capable | Guide name |
| --- | --- | --- | --- | --- |
| `side_control.top.stabilize` | top | action | no (builds pin) | Stabilize |
| `side_control.top.advance_to_mount` | top | action | **yes** → `Mount` | Transition to Mount |
| `side_control.top.expose_back` | top | action | **yes** → `Back Control` | Expose Back (meaning not specified by the Guide; this reading is **[OPEN]** SC-D5) |
| `side_control.bottom.shrimp` | bottom | action | no (builds space) | Shrimp |
| `side_control.bottom.recover_half_guard` | bottom | action | **yes** → `Half Guard` | Recover Half Guard |
| `side_control.bottom.turn_to_knees` | bottom | action | **yes** → `Turtle` | Turn to Knees |

### 4.2 Responses (owned by the responding side)

| Id (**[PROPOSAL]**) | Owner | Governed by readiness |
| --- | --- | --- |
| `side_control.bottom_response.forearm_frame` | bottom | no |
| `side_control.bottom_response.hip_escape` | bottom | yes (`bottom_space`) |
| `side_control.bottom_response.bridge_defense` | bottom | no |
| `side_control.top_response.shoulder_pressure` | top | no |
| `side_control.top_response.hip_block` | top | yes (`top_pin`) |
| `side_control.top_response.follow_the_hips` | top | no |

Governed responses are the best counter to a break-capable technique, as Knee Shield and Knee Pin are in Half Guard v0 (`HALF_GUARD_V0_RULES.md` N-2). **[PROPOSAL]**

### 4.3 Proposed raw grades (initiator's point of view; −2 … +2)

**[PROPOSAL]** — values chosen to satisfy the Guide §16 rule "every defense should close some routes while leaving others open", and checked structurally (see below). They are not a balance claim.

| Top action \ Bottom response | Forearm Frame | Hip Escape | Bridge Defense |
| --- | --- | --- | --- |
| Stabilize | −1 | +1 | 0 |
| Advance to Mount | +1 | −2 | +1 |
| Expose Back | +1 | 0 | −2 |

| Bottom action \ Top response | Shoulder Pressure | Hip Block | Follow the Hips |
| --- | --- | --- | --- |
| Shrimp | −1 | +1 | 0 |
| Recover Half Guard | +2 | −1 | +1 |
| Turn to Knees | 0 | +2 | −2 |

*Structural check run for this proposal (disposable script, not committed, not an oracle).* In both grids every response holds (≤ 0) at least one action and loses (≥ +1) to at least one; every action is neutralized by at least one response and succeeds against at least one; the best counter to each action is a different response; and no response is strictly dominated by another. This verifies the table's shape only. It says nothing about reachability, frequency or fairness. An earlier draft of the Top grid failed this check (one response dominated by another; two actions sharing a best counter) and was corrected before this text was written. A real oracle checkpoint would repeat the check independently (§8).

*Observation worth the owner's attention.* Bottom `recover_half_guard` succeeds against two of three Top responses, and only the governed Hip Block holds it; a measurement slice should look at this before the numbers are accepted. **[OPEN]** SC-D6.

### 4.4 Potential submissions (not in the v0 catalog)

**[GUIDE]** lists a Kimura route and an Armbar route for the Top. **[PROPOSAL]** Neither is in the v0 catalog: a "route" with no finish stage would be a meaningless threat builder, and a real finish needs setup tiers, a submission stage, a tap terminal and the emergency submission-defense rule that Half Guard v0 deliberately lacks (`HALF_GUARD_V0_ENGINE.md`, "three timeout systems"). The id namespace `side_control.top.kimura_route` / `.armbar_route` is reserved for a later slice, which would also need T-8 (is a finish always a terminal outcome rather than a destination) answered. Mount's existing Americana chain is the precedent for stage mechanics; nothing is reused or copied. **[OPEN]** SC-D4.

### 4.5 Deliberately excluded Guide techniques

Underhook Escape, Bridge (as an action), Recover Guard (the Guide's generic "Guard" destination needs a closed/open split rule, as Half Guard needed one), and **Reversal**. Side Control `Reversal` has the same unresolved-landing problem as Mount `Reversal` and is **not** silently resolved; it is simply absent from v0. **[PROPOSAL]**

## 5. Outcomes, exits and potential return routes

### 5.1 Legal outcomes of an accepted exchange **[PROPOSAL]**

1. Continue in Side Control (no exit).
2. A **declared exit** (the four break-capable techniques of §4.1).
3. A terminal timeout (clock reaches zero) — a normal terminal outcome of the current position, never an exit, and still without scoring or a winner (`POSITION_GRAPH.md` §15).

There is no submission outcome in v0 (§4.4) and no automatic transition: a match stays in Side Control through any number of exchanges and may end there. The graph must never force a position change to make progress (`POSITION_GRAPH.md` §15 **[OWNER-APPROVED]**).

### 5.2 Exit map **[PROPOSAL]** (mirrors the Half Guard exit-map shape; lines are proposals)

| Technique | Condition | Raw label | Destination id |
| --- | --- | --- | --- |
| Advance to Mount | final ≥ Success and proposed ≥ +30 | `Mount` | `mount` |
| Expose Back | final ≥ Success and proposed ≥ +30 | `Back Control` | `back_control` |
| Recover Half Guard | final ≥ Success and proposed ≤ −30 | `Half Guard` | `half_guard` |
| Turn to Knees | final ≥ Success and proposed ≤ −30 | `Turtle` | `turtle` |

Every destination id is already declared (`position_registry.gd:17-32`). No label is unresolved; no exit is invented for Reversal.

### 5.3 All Side Control exits halt in v0

**[PROPOSAL]** As Half Guard's own three exits did until B1d, every Side Control exit lands at the honest unsupported-transition boundary (`halted_at_unsupported_transition`, `transition_blocked`, `destination_not_implemented`): the exchange stays accepted and settled, nothing is activated, no winner or score is produced. Mount, Back Control and Turtle have no receiver for a Side Control source. Mount and Half Guard **do** exist as positions, but re-entering an earlier position is exactly the unresolved problem P-11 (**[OWNER-APPROVED]** direction: segment identity and re-entry are designed before the first return route; `POSITION_TOPOLOGY.md` §19.1, `POSITION_GRAPH.md` §10: "Return to Mount is unsupported"). So `Recover Half Guard` and `Advance to Mount` are *declared exits that halt*, not return routes.

### 5.4 Potential return routes (design notes only; none authorized)

| Route | Source of the idea | What it would need first |
| --- | --- | --- |
| Side Control → Half Guard (Bottom recovers) | Guide §11.5 | P-11 segment identity; a Half Guard receiver that accepts a **non-Mount** source (P-10 **[OWNER-APPROVED]** direction: "validated role maps from non-Mount sources"); a decision whether prior Half Guard readiness carries (§6.6) |
| Side Control → Mount (Top advances) | Guide §11.5 | A Mount receiver (none exists), D3-B reconciliation (`POSITION_GRAPH.md` §6, Q6) and a Mount re-entry initial state |
| Side Control → Guard | Guide §11.5 | The closed/open split rule and the Closed/Open Guard engines |
| Side Control → Turtle / Back Control | Guide §11.5 | The Turtle and Back Control engines and their attacker/defender role vocabularies (T-9) |
| Mount `Reversal` landing | — | **Unresolved by D5. Nothing in this proposal resolves, approximates or routes it** |

## 6. The Half Guard Knee Slice → Side Control receiver boundary

### 6.1 What the engine does today **[OBSERVED]**

* `half_guard.top.knee_slice` is Top-side and break-capable (`half_guard_catalog.gd:8,25`). Its exit needs final grade ≥ Success and proposed axis ≥ `PASS_LINE` (30) (`half_guard_resolver.gd:81-83`); a feint whose **funded effective** commitment is LOW cannot exit (`half_guard_resolver.gd:86-89`; rules sheet §13.4); a direct LOW Knee Slice can.
* The exit exchange settles through the normal pipeline (stamina charges, readiness, axis clamp and band update **also on an exit**, histories). Initiative is **not** flipped on an exit and the position is then `ended` (`half_guard_match.gd:354-363`; rules sheet §5.4, §6).
* `BjjHalfGuardWindowGateway.snapshot()` is a canonical detached dictionary (`half_guard_window_gateway.gd:101`, `half_guard_match.gd:138`) containing the role map, per-fighter-id stamina, maximum, latch and behavior remainder, both clocks, cadence, `window_id`, the exit destination and reason and histories. **There is no Half Guard `carryover_segment()`** and no carry-over schema other than Mount's v1; `carryover_export()` is refused while Half Guard is active (`graph_match.gd:230-233`, `carryover_unsupported_position`).
* The graph classifies a Half Guard exit with the **static** classifier and halts (`graph_match.gd:402-408`): `classify_exit_from("half_guard", "Side Control")` returns a blocked verdict; production registers no Side Control source.
* The receiver path is **Mount-only**: `RECEIVER_IDS = [half_guard]` (`graph_match.gd:36`); `_commit_or_halt`/`_build_half_guard` read `_gateway.carryover_segment()` (the retained **Mount** gateway) and hard-code `POSITION_ID` (Mount) as the source of `transition_blocked` and `transition_committed` (`graph_match.gd:420-438,440-470`).
* Tests that currently pin this boundary and would be touched, deliberately and visibly, by an implementation: `test_half_guard_graph.gd:253,904` (unknown receiver key `side_control`; static classifier), `test_position_graph_classification.gd:62,95`, `test_carryover_export.gd:208`, `test_position_registry.gd:226`, and the B1e structural suite (`test_match_flow_invariants.gd`, which treats every Half Guard exit as a halt).

### 6.2 What Side Control would need to receive **[PROPOSAL]**

A pure, static **edge adapter** (the role `BjjHalfGuardMountEdge` plays for Mount → Half Guard) that turns a detached Half Guard snapshot into a neutral Side Control **entry request** and a pure Side Control entry validator that is the only construction path of the position. The request is source-agnostic (like Half Guard's, so a later source may reuse it):

```
{"role_map": {"top": id, "bottom": id},
 "fighters": {id: {"stamina_current", "stamina_maximum", "exhaustion_latched", "behavior_remainder_units"}, ...},
 "clock": {"initial_seconds", "remaining_seconds"},
 "window": {"last_issued_id"},
 "interval_seconds"}
```

* **Where the source data comes from [OPEN] SC-D10.** Option (a), recommended: read the existing detached Half Guard `snapshot()` through a pure edge adapter, validating strictly (below); no new carry-over schema, no change to the Half Guard engine, and `carryover_export()` stays refused for non-Mount segments. Option (b): design a Half Guard carry-over segment schema first (a v2 envelope; `POSITION_TOPOLOGY.md` §10 requires versioning rather than in-place edits). Option (b) is larger, touches the A3b validator family and is not needed to prove the second receiver.
* **The edge declares the role map** (identity, §3.2); the receiving position declares its own entry axis, tiers, authority and initiative (`POSITION_TOPOLOGY.md` §11.2). Nothing is derived from physical top/bottom or from Half Guard's `initiator`, axis, band or tiers.

### 6.3 Strict edge validation (all before anything is built; first failing code wins) **[PROPOSAL]**

The snapshot must be a Half Guard snapshot whose exit is exactly the Knee Slice pass: `position_id == "half_guard"`, `exit_destination == "Side Control"`, a resolved declared destination `side_control`, **no window open**, `clock_seconds ≥ 1` (an exit always leaves time, because a window only opens with time left and the exchange moves no clock; a zero-clock record is refused as inconsistent), a valid role map and fighter ids, and per-fighter stamina, latch, remainder, clock, window id and cadence that pass the entry validator. Error codes are provisional (`hg_edge_not_an_exit`, `hg_edge_wrong_destination`, `hg_edge_window_open`, `hg_edge_clock_exhausted`, plus the entry validator's own). Refusals return the stable code and **build nothing**.

### 6.4 First initiative at entry **[OPEN] SC-D2 (a real risk, not a formality)**

Half Guard entry precedent **[OBSERVED]**: after Mount → Half Guard the *escaping* fighter (Mount Bottom) produced the exit, and the Half Guard Top (the former Mount Top) opens the first window; the exit window is consumed and no window or time is granted by the transition (D2 **[OWNER-APPROVED]**).

Here the situation differs: the fighter who produces the exit (the passing **Top**) is also the fighter who would hold the first Side Control window if the Guide §15 v10.4 authority rule ("the controlling top player ordinarily acts first") is applied. That fighter would have acted in the last Half Guard window and be first in the next Side Control window, which is not the strict alternation seen across the existing boundary. The window is **not free**: it opens only on a later caller request and spends the cadence from the clock like every window; there is no extra action or clock change. The proposal is therefore:

* **[PROPOSAL]** entry `initiator = top`, no window open, zero seconds, no charge, window ids continuing (§6.5);
* **[OPEN]** the owner decides between the Guide §15 authority rule (Top first) and an alternation rule (Bottom first, because Top just acted). Either is expressible without extra turns. This slice neither adds nor models a free-initiative priority; that belongs to the stalling/priority rule family of PR #63.

**Note (2026-10-13):** the owner-agreed direction in `POSITION_AWARE_INITIATIVE_PROPOSAL.md` (B2a.1) supersedes this binary framing: Side Control would be a position-biased opening (Top favored) that a sufficiently skilled or specialized fighter can override. That document is a proposal; none of its numerical thresholds is approved, and until fighter proficiency data exists an identical provisional profile makes the favored role open.

### 6.5 What is preserved **[PROPOSAL; continuity facts OBSERVED for Half Guard]**

| Quantity | Rule at the boundary | Observed precedent / source |
| --- | --- | --- |
| Fighter identities | Unchanged; two distinct ids, never re-keyed by role | `half_guard_mount_edge.gd` re-keys by id; `POSITION_GRAPH.md` §2 |
| Physical roles | Identity map (§3.2) | D1 |
| Stamina current / maximum | Copied exactly, per fighter id, from the **post-exchange** snapshot; the transition charges **nothing** | D4 |
| Exhaustion latch | Restored with the public pool API only: a latched fighter is built at zero and moved to its current value, so hysteresis between the enter and recover thresholds is remembered; never `create(current, max)` for a latched pool (option (e) of `POSITION_TOPOLOGY.md` §11.1) | `half_guard_match.gd:88-97` |
| Behavior remainders | Carried per fighter id and **never changed** by Side Control v0 (no behaviors) | rules sheet A-13 |
| Clock | `initial` and `remaining` copied; zero seconds pass in the transition | D2 |
| Global window identity | `last_issued_id` copied; the first Side Control window id is `last_issued_id + 1`; ids are never reused | `POSITION_GRAPH.md` §7 |
| Global event log | Continues with one new `transition_committed` after the already appended `decision_accepted` | `POSITION_GRAPH.md` §5 |
| Half Guard-local state | **Not carried:** axis, band, `top_base`, `bottom_frame`, histories, exit reason, any feint record, the sealed protocol | `half_guard_match.gd:138` |
| D3-B | Never observed or granted by Side Control; Mount's frozen record is not touched | `POSITION_GRAPH.md` §6 |

Preparation earned in Half Guard does **not** carry in v0. The Guide's example run (Run A, "a prepared Knee Slice … preserves a bounded amount of preparation toward a Mount advance") describes a future chain/technique-memory system, which is not authorized; v0 enters with fresh Side Control tiers. **[OPEN]** SC-D7.

### 6.6 Atomic receiver validation, frozen previous segment, unsupported handling **[PROPOSAL]**

The accepted Knee Slice exchange is already settled; there is no rollback (HG-18 **[OWNER-APPROVED]**). The transition therefore follows the existing protocol, generalized only in its source:

1. **Detect/classify** from the accepted report's transition, never from `ended` alone: a Knee Slice exit → destination `side_control`; a timeout is a terminal outcome, never an exit.
2. **Validate** (§6.3), computing the graph's **own** expected request and fresh reference state.
3. **Construct** the Side Control gateway completely in isolation from detached values; the retained Half Guard segment, clock, pools, meters and log are untouched.
4. **Compare** the receiver's detached views with the expected request and the fresh snapshot (roles, per-id stamina, latch, remainder, both clocks, cadence, window counter, entry axis/band/tiers/initiator, empty history, no open window), and confirm the retained Half Guard segment's public views and snapshot are unchanged (a faulty receiver may not touch it; the Half Guard fingerprint is new work, R9).
5. **Commit**: set one typed slot and append exactly one `transition_committed(from = half_guard, to = side_control, label = "Side Control")`. No window opens, nothing is charged, no clock moves.
6. **On any failure at steps 2–4**: the exchange stays settled; the graph appends `transition_blocked` with reason `transition_entry_invalid`, halts, and activates nothing (HG-18 semantics).
7. **Previous position frozen**: the Half Guard gateway (and its adopted sealed protocol) is retained only as history, is never advanced, submitted to or exported again, and every command for `half_guard` or an old window id is refused with zero mutation.
8. **Side Control exits** halt as in §5.3. `carryover_export()` stays refused (`carryover_unsupported_position`); no v2 schema is created by this proposal.

### 6.7 Architecture risks the later implementation must handle **[OBSERVED code; risk statements are inference, flagged as such]**

| # | Risk | Evidence | Safest handling **[PROPOSAL]** |
| --- | --- | --- | --- |
| R1 | **Receiver keyed by destination only could fabricate a transition.** `_classify` turns a static "not implemented" verdict into a transition if the destination id is a registered receiver (`graph_match.gd:402-408`). If Side Control later exits to `half_guard` and a `half_guard` receiver is registered, a destination-only lookup would build Half Guard from the **retained Mount segment** (`_build_half_guard` reads `_gateway.carryover_segment()`), resurrecting stale state | inference from `graph_match.gd:402-408,440-470` | Key receivers by **(source position, destination)**; a Side Control source has no registered receivers in B2b; add a test that Side Control → Half Guard halts and never constructs |
| R2 | **Hard-coded Mount source.** `_commit_or_halt` and `_halt(POSITION_ID, …)` name Mount as the source of both `transition_blocked` and `transition_committed` | `graph_match.gd:420-438` | Pass the real source; Mount → Half Guard events stay byte-identical (the current pins) |
| R3 | **Active-owner dispatch by null checks.** At least 17 sites decide "which position is active" from `_half_guard != null` / `_sealed != null` (`graph_match.gd:225-381`). Adding a third position by another null check invites two owners at once | `graph_match.gd` | One explicit, typed active-owner indicator updated at the single commit point, with an invariant test "exactly one owner" (B1e already pins this) |
| R4 | **Stale sealed protocol.** `_sealed_admission` refuses with `wrong_active_position` only when `_sealed == null` (`graph_match.gd:362-370`). After Half Guard → Side Control the Half Guard protocol must not remain reachable, or `seal_intent`/`respond` could drive the frozen Half Guard simulation | inference | The commit retires the sealed slot; sealed methods are refused (`wrong_active_position`) while Side Control is active; a mutation test must catch a stale slot |
| R5 | **Tripwire tests** assert today's halt (§6.1 list) | listed above | Update deliberately in the implementing slice, visibly, never weaken; default and `create_with_*` graphs keep every existing pin |
| R6 | **Feint-originated exit.** A Knee Slice exit can come from an FP-1 feint (the real technique settles through the same pipeline) and from the published LOW fallback path | `HALF_GUARD_V0_ENGINE.md` §"Feint behavior" | The edge reads only the settled snapshot; it carries no feint or apparent-technique information, so the receiver cannot learn a concealed intent |
| R7 | **Double settlement.** The snapshot is read **after** the exit exchange's charges; re-charging, re-advancing time or re-issuing a window id at the boundary would be a second settlement | `half_guard_match.gd:343-347` | Boundary tests assert exactly one `decision_accepted`, zero added charge, zero added seconds, and `last_issued_id + 1` for the first window (§9) |
| R8 | **Silent activation through the default receiver table.** `create_with_sealed_half_guard` uses `default_receivers()` when no table is given (`graph_match.gd:96-109`), and the B1e harness builds its graphs that way (`match_flow_harness.gd`). If Side Control were added to those defaults, every existing sealed graph would start committing exits that currently halt, changing the B1e baseline (the Half Guard → Side Control halt is its largest destination bucket in `MATCH_FLOW_DIAGNOSTICS.md`) | inference from the cited lines | `default_receivers()`, `create`, `create_with_receivers` and `create_with_sealed_half_guard` keep exact behavior; Side Control is reachable only through its own explicit opt-in constructor (SC-D12); the existing `invalid_receivers` pin for `side_control` (`test_half_guard_graph.gd:253`) is revised deliberately, not weakened |
| R9 | **Frozen-segment proof is Mount-specific.** The graph proves a faulty receiver did not touch the retained segment with `_mount_fingerprint()` (`graph_match.gd:507-510`); nothing equivalent exists for a Half Guard segment | observed | A Half Guard fingerprint (public views plus `snapshot()`) is part of the implementing slice, and a test must fail if a receiver mutates the retained Half Guard gateway |
| R10 | **F1 and the fighter adapter are Mount-only.** `BjjFighterSnapshotAdapter` reads `top_stamina`/`top_maximum`/`top_band` and `behavior_fields()[role]` from the active segment (`fighter_snapshot_adapter.gd`), and F1's controller assumes Mount | observed (Half Guard already satisfies the adapter's keys; Side Control would have to as well) | Side Control exposes the same view keys; F0/F1 never enable the opt-in graph; no UI work |
| R11 | **Export and terminal fall-through.** `carryover_export()` refuses only while `_half_guard != null` (`graph_match.gd:230-233`): a refactor that nulls or repurposes that slot would silently export the frozen **Mount** segment while Side Control is active. `terminal_reason` reads `clock_seconds` and `submission_tapped` from `state_fields()` (`graph_match.gd:206`); a Side Control state view that omitted or renamed them would classify a clock end as `unclassified_terminal` | inference from the cited lines | Tests: the export on a Side Control-active graph is refused with `carryover_unsupported_position`; a Side Control clock end (including an exit that leaves exactly one interval of clock) records `reason == "timeout"`; Side Control exposes the same state-view keys |
| R12 | **Existing source scans fail on innocent naming.** `test_half_guard_graph.gd:926-930` pins that `_gateway = ` is assigned only in `create`, that `_half_guard = ` appears exactly once, and that no public graph name contains "gateway"; `test_half_guard_graph_sealed_flow.gd:1098-1105` pins exactly one `_half_guard = `, one `_sealed = `, one `BjjHalfGuardWindowGateway.create(` and exactly three `_settle_accepted(source, report)` call sites | observed | Decide slot names up front (proposed: a typed `_side_control`, one new source-keyed receiver path), keep the three-call-site single settlement (a fourth call site is a design smell), and list in the implementing slice every scan it deliberately amends, with a reason |

## 7. Setup/readiness, stamina and commitment (proposed values vs accepted mechanics)

### 7.1 Accepted, position-independent mechanics **[OBSERVED]**

Commitment costs LOW 3 / MEDIUM 7 / HIGH 12; funding `determine(requested, available)`; exhaustion latch enter `floor(0.25·max)`, recover `ceil(0.35·max)`; stamina bands; `BjjExhaustionPolicy` modifier; `BjjCommitmentSettlement` magnitude and undercommitment steps; Rule 1 (an unfunded initiator waives the responder's charge) (`HALF_GUARD_V0_RULES.md` §2, §5). These are the existing shared primitives and are not changed.

### 7.2 Proposed Side Control settlement **[PROPOSAL]** (each row is an acceptance item for the owner)

| # | Proposal | Precedent (not an acceptance) |
| --- | --- | --- |
| SC-N1 | Two readiness tracks, `top_pin` and `bottom_space`, tiers `0 None`, `1 Partial`, `2 Ready`; entry Partial/Partial; no decay | HG N-1 |
| SC-N2 | Governed responses: Hip Escape (reads `bottom_space`) and Hip Block (reads `top_pin`) | HG N-2 |
| SC-N3 | Attack readiness: a break-capable action reads its own track: `advance_to_mount`, `expose_back` read `top_pin`; `recover_half_guard`, `turn_to_knees` read `bottom_space`; shift Ready +1 / Partial 0 / None −1 | HG N-3 |
| SC-N4 | Defense readiness for governed responses: Ready −1 / Partial 0 / None +2; a LOW or unfunded defender is evaluated at None | HG N-4, A-10 |
| SC-N5 | Build: a successful `stabilize` raises `top_pin` by one; a successful `shrimp` raises `bottom_space` by one; at Ready a break-capable attempt spends one tier whatever the result; governed responses wear by effective commitment as in the Half Guard wear table; no cross-track weakening in v0 | HG N-5, N-6, N-8 |
| SC-N6 | Pipeline order: raw → positional (−1 facing the opposing CONTROL band) → attack readiness → defense readiness → exhaustion → magnitude → undercommitment; each step saturates at ±2; the clamp and band update also happen on an exit | HG §5.3, N-7 |
| SC-N7 | Axis: integer tenths in −40…+40; step 10 per final grade; entry axis **+10** (band +1, `TOP_EDGE`); exit lines ±30; band hysteresis table identical in shape to Half Guard's but defined independently in the Side Control rules sheet | HG §2 |
| SC-N8 | A pass costs nothing, spends no clock and flips initiative (as Half Guard); there are **no behaviors, no drift, no recovery action, no D3-B** in v0 | HG v0 |
| SC-N9 | Timeout: `TIMEOUT — Side Control retained`, terminal, no exit | HG A-9 |

Entry axis +10 reflects that the Top has just completed a pass; it is a placeholder for the owner's choice, not a balance result. **[OPEN]** SC-D6, SC-D7, SC-D8.

### 7.3 Inherited properties the owner should expect, not hide

Because SC-N8 copies Half Guard's economy, Side Control v0 would inherit what B1e measured for Half Guard and recorded as design questions, not defects: no stamina recovery (depleted fighters can freeze into no-progress), free passes (both fighters can pass to the clock), and called-bluff coupling effects (`MATCH_FLOW_DIAGNOSTICS.md`). This proposal does not fix them, and PR #63's rules (custom three-turn stalling, Momentum, Heart of a Lion, REST, zero-stamina LOW memories) are **future, unimplemented, opt-in** policies.

### 7.4 Room left for PR #63 **[PROPOSAL]**

Side Control must not hard-code anything that blocks those rules: every accepted exchange and pass is recorded with fighter id, technique and response ids, grades, axis before/after and exit (so a later activity classifier can derive "meaningful activity" per fighter); the engine owns no inactivity counter, no momentum, no recovery and no penalty; funding refusal at very low stamina stays an explicit, testable admission rule that a later "zero-stamina LOW memory" exception can amend through its own reviewed change; and none of those policy states belongs in the position (they live at the match owner and survive position changes).

## 8. Independent oracle plan and typed Godot sequence

Follows `bjj-parity-gate` and the Half Guard precedent (B1b, B1c, B1d, B1h). The frozen Python reference, its fixtures and the enumeration digest are **never** edited. Every path named in this section is **proposed and does not exist yet**.

1. **Rules sheet first.** `GODOT_V1/docs/SIDE_CONTROL_V0_RULES.md`, self-contained, with every number the owner accepted, written by the implementing slice after the owner decisions in §11. (This proposal is not that sheet.)
2. **Test-only Python oracle**, `tests/oracles/side_control_v0.py` (plus scenario and generator modules), written **from the rules sheet only**, never by reading GDScript, and run by `tests/test_side_control_oracle.py` on the existing Python CI route. It exposes: entry validation, a canonical `snapshot()`, `attempt`, `open_window`, `submit`, bands, exits, readiness and replay. A table-consistency test parses the rules sheet's tables and compares them to the oracle's constants (the Half Guard sheet is parsed the same way by `tests/test_half_guard_oracle.py`).
3. **Checkpoint.** Oracle tests and a mutation-sensitivity run (disposable edits, restored, verified byte-identical) are pushed **before any GDScript**, as B1b and B1h did.
4. **Typed Godot position** under `scripts/positions/side_control/` mirroring the Half Guard structure by **composition** (rules, catalog, resolver, entry, match, contract, window gateway), implementing the same rules sheet. No shared rule table with Mount or Half Guard.
5. **Fixture and reference test.** `GODOT_V1/tests/generate_side_control_reference.py` writes the git-ignored fixture under `GODOT_V1/tests/generated/`; `test_side_control_reference.gd` compares the engine with the oracle field by field. Assertion counts are measured, pinned in `godot-v1.yml` and in `tools/ci/test_validate_mount_slice_log.py`, and change only by reviewed edit.
6. **Edge and graph (separate slice, §12).** `side_control_half_guard_edge.gd` (pure), the generalized receiver table keyed by (source, destination) behind a **new explicit opt-in constructor** (a graph built by `create`, `create_with_receivers` or `create_with_sealed_half_guard` keeps its exact behavior), the typed Side Control slot and the single settlement path.
7. **Match-flow harness extension** for Side Control flow, as a separate measurement slice (no gate on frequencies).
8. **Oracle for the edge.** The Python oracle also builds the expected Side Control entry request from a Half Guard **snapshot fixture** produced by the existing, unchanged Half Guard oracle, so that the edge is checked against an independent construction rather than against the GDScript adapter.

Contamination and independence controls **[PROPOSAL]**:

* The oracle imports no GDScript-derived data and is **stdlib-only**; it must not import `half_guard_v0`, and the four or five position-independent helpers it needs are re-implemented. A test-only differential check compares them with the Half Guard oracle helpers and, when `PYTHONPATH=src` is set, the frozen reference (a skipped differential is reported as skipped, never as passed). An AST test forbids I/O, clock, randomness and the Half Guard import, as the Half Guard oracle's own test does.
* The Half Guard oracle was written before any GDScript existed; Side Control has a Half Guard engine as its template. So the oracle checkpoint is a **separate, earlier commit phase** than the typed engine, written from the rules sheet only, with hand-computed literals and the arithmetic in comments for each rule, and with the sheet's own tables parsed into a consistency test. It is not a search-and-replace copy of the Half Guard oracle (shared constants such as the 30 pass line would carry shared bugs).
* Fixtures are generated, never hand-copied; a strict integer comparator is used in the Godot reference test (a float where an integer is expected must fail; the Half Guard reference comparator treats int and float as equal within 1e-9, `test_half_guard_reference.gd:30-34`), the fixture SHA-256 and the per-family minimum counts are pinned inside each reference test, and the Python side pins exact scenario, operation and comparison counts.
* Byte-identical generation is proven under at least three `PYTHONHASHSEED` values in subprocesses, and an AST check forbids iterating a `set` into output. (The Half Guard test of that name generates twice under one seed, so it does not by itself prove hash-seed independence.)
* Oracle-measured structural searches are labelled "not parity evidence".
* A continuity family is generated from the **unchanged** Half Guard oracle (an exit trajectory to a Side Control entry), labelled "continuity, not combat", without editing any Half Guard fixture.
* Every slice handoff includes a path allowlist command, for example `git diff --name-only <base>...<head>` showing nothing under `src/`, `docs/evidence/`, `tests/oracles/half_guard_*`, `tests/test_half_guard_*`, `GODOT_V1/tests/generate_half_guard_*`, `MATCH_FLOW_MEASUREMENTS.md`, or an existing `test_half_guard_*.gd` unless a per-line reason is given. The existing digest tripwires (the direct fixture SHA-256 at `test_half_guard_feint_oracle.py:31` and `test_half_guard_graph_sealed_flow.gd:30`) keep running.
* Mutation-sensitivity runs record, per mutation: id, file, before/after, killing test and exit status; survivors are counted; "not run" is stated when not run. Boundary mutations to include: re-applying the exit charge; advancing the clock at commit; not carrying or resetting the window counter; leaving routing on Half Guard; a hard-coded Mount `from_position_id`; advancing the frozen Half Guard segment; `_receiver_matches` replaced by true; swapped role map or resources; latch not carried; remainder dropped; `transition_committed` appended twice or before `decision_accepted`; export falling through to the Mount segment; a sealed command forwarded to the frozen protocol.

## 9. Negative-first test plan

Every rejected command leaves the **whole** state unchanged: position state, both pools and latches, meters, clock, window record, histories and the graph's event log and status (compared by full-state fingerprints, as `test_match_flow_invariants.gd` does).

| Area | Cases (each with before/after equality) |
| --- | --- |
| Entry | not a dictionary; malformed / extra / missing key at every level; wrong types (bool is not int, float is not int); invalid or padded or equal fighter ids; stamina maximum/current out of range; inconsistent latch; remainder out of range; invalid clock; invalid window id; invalid interval; a tier key supplied (refused as extra); each with first-failing-code precedence |
| Commands | unknown action; wrong side or kind; unknown response; wrong-side response; response without action; commitment without action; invalid commitment and response commitment; missing / unknown fighter; **wrong role** (a Top fighter submitting a Bottom technique, a Bottom fighter acting out of turn); not the initiator; no open window; **stale** and **duplicate** window id; wrong-position id; a Mount or Half Guard technique id in Side Control |
| Windows | window already open; negative or non-integer duration; zero-time window legal; clock reaching zero closes without opening; window id unchanged on close; ids strictly monotonic |
| Terminal | command after an exit; command after a timeout; command after a halt; refusal precedes any tier read |
| Boundary | edge refusals (§6.3: not an exit, wrong destination, open window, zero clock, malformed snapshot, each snapshot field); **mismatched roles** (an edge input whose role map disagrees with the receiver's expected map); a receiver that returns the wrong object, wrong ids, wrong stamina, wrong latch, a non-fresh state, an open window, a changed retained segment (HG-18 failure injection through the receiver seam); each leaves the exchange settled, appends exactly one `transition_blocked(transition_entry_invalid)`, activates nothing and halts |
| Transition failure | the previous position stays frozen and byte-identical; later commands refused `halted_unsupported_transition`; the graph's carry-over export stays refused |
| Single settlement | exactly one `decision_accepted` per exchange; zero stamina change by the transition; zero seconds; first window id = `last_issued_id + 1`; no duplicate event; sealed or direct path produces the same event stream |
| Receiver keying | Side Control → Half Guard halts and never constructs a Half Guard (R1); default graphs unchanged; Mount → Half Guard events byte-identical to today |
| Stale protocol | sealed methods refused while Side Control is active (R4) |
| Identity / carried-versus-reset | stamina follows the **fighter id** under swapped role maps; one negative test per dropped Half Guard field (axis, band, tiers, histories, exit reason, feint record, protocol state) proving no leakage; latch and remainder restored exactly at the enter and recover thresholds and at large capacities; a carried-versus-reset table in the rules sheet |
| Exit routes | direct `submit`, sealed `respond` and the published-fallback timeout produce **identical** Side Control entries for identical settlements; an FP-1 feint exit and a plain Knee Slice exit carry no concealed-intent information; Open Guard and Closed Guard exits from Half Guard still halt exactly as before with `from_position_id = half_guard` on a Side Control-enabled graph |
| Duplicate delivery | re-sending the exit command (direct, sealed, timeout) after commit is refused with no new event; submitting the consumed Half Guard window id to Side Control is refused; cross-position id refusals in both directions (Side Control ids into Half Guard, Half Guard and Mount ids into Side Control); a global property that `window_opened` ids across Mount, Half Guard and Side Control are strictly +1 |
| Adapter independence | the Half Guard → Side Control edge adapter is tested **directly** with literals and single-field mutations of real Half Guard records (the graph computes its own expected request with the same adapter, so graph tests alone are circular), with refusal precedence and interval validation |
| Faulty-receiver battery | malformed outputs; single-field mutations (stamina or maximum off by one, remainder, clock, initial clock, window counter, cadence, swapped resources, swapped role map, renamed ids); stale, open and decided gateways; a receiver tampering with the frozen Half Guard segment and protocol; a receiver mutating its own record argument; no retry after a halt; receiver-table negatives (a `side_control` key without a `half_guard` key, wrong arity, padded or StringName keys, table copy semantics) |
| Whole-state fingerprints | the three existing `everything()` copies (`test_half_guard_graph.gd`, `test_half_guard_graph_sealed_flow.gd`, `match_flow_harness.gd`) cover two positions only, so a non-mutation test using them would pass vacuously for a third; new tests use a fresh three-position fingerprint, with a meta-test that every instance variable of the graph is covered; the B1e observer tracks a **list** of frozen segments, and the B1e coverage floors gain lower bounds for Half Guard → Side Control transitions, Side Control exchanges, halts and timeouts (today they would pass if none ever occurred) |
| Terminal matrix | after a Side Control clock end: sealed commands `match_ended`, `open_window` `terminal_exchange`, `submit` `no_open_window`; an exit report carries `ended: true` while the graph stays active and `_record_terminal` is never called for an exit |
| Determinism | each scenario replayed twice with identical states, event logs and halt indices; with and without an observer; no dictionary-order, RNG, float or wall-clock dependence (all arithmetic in integer tenths) |
| Scope | source scans: no Mount/Half Guard internals referenced; no `randi`/time APIs; no forbidden names |

Checks that must be **stated as not run** in any later report unless run: the full mutation matrix, Python 3.11/3.13 shards, skipped differential tests (a skip is not a pass), and anything in this list not observed on the exact head. Each new test states its expected assertion-count delta, and conditional `check` calls guarded by `if` are avoided (a pinned count catches shrinkage, not a check that never executes). A green documentation-only check, such as this slice's, proves nothing about Side Control behavior.

**Hard gate for the graph slice.** The default and existing opt-in graphs stay byte-identical: the pinned counts 2,133 (Half Guard graph), 2,433 (graph sealed flow) and 73,606 (match-flow invariants) must be unchanged unless a listed, justified pin amendment says otherwise; the committed B1e measurements and digests are never rewritten (a new measurement document is added instead).

## 10. Verification for this documentation slice

Only this Markdown file changed. The checks are `git diff --check` (including the CI whitespace configuration, before and after staging), a read-through for label consistency, and a link and file-reference check (every repository path and `file:line` citation was opened at the stack head). No Godot or Python suite applies to a documentation-only change and none was run; a green documentation-only CI result proves nothing about Side Control behavior. The exact CI routing and results are reported in the handoff.

## 11. Owner decisions required before implementation

| ID | Decision | Recommendation (not a decision) |
| --- | --- | --- |
| SC-D1 | Role map at the Knee Slice boundary: identity (Half Guard Top stays Top) | Identity |
| SC-D2 | Who holds the first Side Control window: Top (Guide §15 authority rule) or Bottom (alternation after the Top's exit) | Top, with the consecutive-initiative effect recorded as a known property. **Reframed 2026-10-13:** no longer a binary; see §11A and `POSITION_AWARE_INITIATIVE_PROPOSAL.md` |
| SC-D3 | Authority: by axis sign (reported only) or fixed to the Top | By axis sign |
| SC-D4 | v0 catalog scope: 3+3 as proposed, the Guide's full list, or a different subset; submissions (Kimura/Armbar routes) in v0 or deferred | 3+3, no submissions |
| SC-D5 | Meaning of "Expose Back" and whether `back_control` is a v0 exit at all | Keep as an honest-halt exit |
| SC-D6 | Grade tables, exit lines, entry axis, step, bands (§4.3, §7.2) | Accept only after an oracle checkpoint and a separate measurement. **Sequencing amended in §11A.2:** accept as provisional prototype constants for B2b |
| SC-D7 | Readiness tracks, entry tiers, consume/wear/build rules; whether Half Guard preparation carries (v0: it does not) | Fresh tiers, no carry |
| SC-D8 | Economy: free passes, no recovery, no behaviors (inherits Half Guard) versus any change | Inherit; leave economy to the PR #63 family |
| SC-D9 | Feints and the sealed protocol in Side Control (v0: none; sealed methods refused while Side Control is active) | None in v0 |
| SC-D10 | Edge source: Half Guard `snapshot()` through a pure adapter, or a new Half Guard carry-over schema | Snapshot adapter |
| SC-D11 | Destination set and label resolution (the Guide's generic "Guard"), and whether any of the four v0 exits may become a receiver, which requires P-11 | All four halt |
| SC-D12 | Graph exposure: a new explicit opt-in constructor (recommended) versus extending an existing one | New constructor; defaults unchanged |
| SC-D13 | Variations (North-South, Knee-on-Belly) and Knee-on-Belly's Guide §40.1 scoring hook | Out of v0; scoring remains a policy over events |
| SC-D14 | Mount `Reversal`, Side Control `Reversal` landings | Remain unresolved |
| SC-D15 | Slicing under local-first development: oracle-only B2b then engine B2c as independent local commit phases on `main` (recommended), or the Half Guard precedent of one slice with an earlier oracle checkpoint (§11A.4) | Separate oracle phase: its own commits, on `main` before any GDScript |

## 11A. Owner-decision review of SC-D1 to SC-D15 (2026-10-13)

**Documentation only. Everything below is a recommendation until the owner approves it. No number, rule or threshold is approved by this section, nothing is implemented, and Mount and Half Guard are untouched.** The recommended scope in §11 is the starting point; where this review disagrees it says so and why. Sources: this proposal, `POSITION_AWARE_INITIATIVE_PROPOSAL.md` (B2a.1), `MATCH_INCENTIVES_HEART_OF_A_LION.md`, Master Guide §§11.5, 15–17, 40–42, the Engineering Roadmap and the Oversight Ledger.

**Preserved direction.** Initiative combines General Technique `G`, separate earned position-role proficiency `R` (a new career fighter starts at `R = 0`, never derived from `G`) and the position's tactical advantage. Side Control v0 grades, costs and readiness use **neither** `G` nor `R`; the opening contest uses them once (B2a.1 §4.3). So nothing is counted twice and no B2a.1 number is needed to build the position.

### 11A.1 Classification

Each decision is tagged by its dominant nature: **A** architecture consistent with the current engine; **B** small v0 scope or implementation boundary; **C** gameplay with a meaningful player-facing consequence; **N** numerical balance needing future measurement. A decision can carry a second tag.

### 11A.2 Review table

| ID | Decision (short) | Tag | Existing recommendation | Review | Why |
|---|---|---|---|---|---|
| SC-D1 | Role map at the Knee Slice boundary | **A** | Identity (Top stays Top) | **Agree** | Knee Slice is a Top technique; matches the approved Mount→Half Guard D1 precedent; roles are not a reversal or a score |
| SC-D2 | First Side Control window | **C** (+A) | Top | **Reframed** | No longer a Top/Bottom binary. B2a.1: Side Control is a position-biased opening (Top favored) that skill may override. The v0 position only needs an explicit, validated **entry `initiator` input**; a provisional identical profile makes it Top. No B2a.1 threshold is needed for B2b |
| SC-D3 | Authority | **A** | By axis sign (reported only) | **Agree** | No mechanical effect, same convention as Half Guard, and independent of the B2a.1 "favored role" (a policy declaration, not authority) |
| SC-D4 | Catalog scope and submissions | **B** (+C) | 3+3, no submissions | **Agree, with the consequence stated** | See concern 1. A real finish needs setup tiers, a stage, a tap terminal and the emergency-defense rule |
| SC-D5 | "Expose Back" and `back_control` as an exit | **B** (+C) | Keep as an honest-halt exit | **Agree, with a meaning caveat** | See concern 2 |
| SC-D6 | Grade tables, exit lines, entry axis, step, bands | **N** (+C) | Accept only after an oracle checkpoint and a separate measurement | **Disagree with the sequencing** | That order is circular: the oracle must freeze values first and measurement needs an engine. Accept the values as **provisional prototype constants** for B2b, as Half Guard's GP-2/3/4 were; B2e measurement may then justify a versioned amendment through the oracle. See concern 5 |
| SC-D7 | Readiness tracks, tiers, wear, no carry | **N** (+A) | Fresh tiers, no carry | **Agree** | "No carry" is also the engine-consistent choice (no Half Guard field beyond the carry-over list crosses the boundary); the cost is that Half Guard preparation is lost at the pass, a player-visible consequence worth recording |
| SC-D8 | Economy: free pass, no recovery, no behaviors | **C** (+N) | Inherit; leave to the stalling family | **Agree, with one added requirement** | See concern 4: record a pass as its own decision kind |
| SC-D9 | Feints and the sealed protocol | **B** | None in v0 | **Agree** | Sealed methods must be refused while Side Control is active (risk R4); simultaneous-sealed (B2a.1 §6.2) is a different, later protocol |
| SC-D10 | Edge source | **A** | Half Guard `snapshot()` through a pure adapter | **Agree** | The oracle builds the expected entry from a Half Guard snapshot fixture, so the edge is checked independently |
| SC-D11 | Destinations; do the four exits halt | **B** (+C) | All four halt | **Agree for B2b/B2c; flag for B2d** | See concern 3 |
| SC-D12 | Graph exposure | **A** | New explicit opt-in constructor, defaults unchanged | **Agree** | Same pattern as `create_with_receivers` and `create_with_sealed_half_guard`; belongs to B2d, not B2b |
| SC-D13 | North-South, Knee-on-Belly, scoring hook | **B** | Out of v0 | **Agree** | Variations stay variations (Guide §10); scoring remains a policy over recorded events |
| SC-D14 | Mount `Reversal` and Side Control `Reversal` landings | **B** | Remain unresolved | **Agree** | Nothing here resolves or approximates a landing |
| SC-D15 | Slicing | **A** (process) | Separate oracle PR | **Reframed** | Obsolete under local-first development; see 11A.4 |

### 11A.3 The six concerns

**1. No submissions in v0 (SC-D4).** With no Kimura or Armbar route, a Top fighter in Side Control has no finishing threat: the position can end only by clock, or by an exit that halts the prototype. That also means the opening advantage (B2a.1) has little at stake in v0, and a match in Side Control cannot be *won*. This is the same state Half Guard v0 has. I **agree to defer** because a real finish needs setup tiers, a submission stage, a tap terminal, the emergency submission-defense rule and an answer to T-8; a "route" with no finish would be a meaningless threat builder. Two cautions: (a) call v0 a **transition prototype, not a complete position**, in the rules sheet; (b) reserve `side_control.top.kimura_route` / `.armbar_route` and schedule submissions as their own later slice, using Mount's Americana chain only as precedent. Owner-visible consequence: Side Control v0 will not deliver a finish.

**2. "Expose Back" and the Back Control destination (SC-D5, SC-D11).** The Guide lists "Expose Back" under Top and `Back Control` as a destination but defines neither. The proposal reads it as a break-capable Top technique that lands in `back_control`. Two risks: the name is a Guide word whose intended meaning (exposing the opponent's back versus taking it) is unstated, and Back Control will need its own attacker/defender role vocabulary (T-9) at receive time, which a halt-only v0 never exercises. I **agree to keep it**, because the 3×3 response grid's structural properties (every response holds one action and loses to another, no dominated response) depend on three actions per side, and removing it would force a new grid. Keep the exit label `Back Control` and the id `side_control.top.expose_back` as **provisional names**, state that the meaning is open, and treat the first real use as the moment T-9 is decided. **Alternative for the owner:** drop it from v0 and keep two Top actions, accepting a redesigned grid.

**3. Does a halt-only v0 feel like a dead end (SC-D11).** Four of the six actions are break-capable exits (`advance_to_mount`, `expose_back`, `recover_half_guard`, `turn_to_knees`), and every successful one ends the prototype at `halted_at_unsupported_transition`. From the proposed entry axis +10 (step 10 per final grade), the Top reaches the +30 line in as few as **one** accepted exchange (a final +2) and the Bottom needs at least **two** to reach −30. That is arithmetic on proposed numbers, **not a measured frequency** (SC-D6). Precedent: §5.3 cites the same honest-halt behavior, as Mount's exit toward Half Guard halted before the B1d edge existed. The honest-halt behavior is correct and consistent with the engine; the player-facing risk is that the first playable Mount→Half Guard→Side Control path ends abruptly, against the project invariant of human-play breadth over endless Mount tuning. **Recommendation:** accept all-halt for B2b and B2c (they are standalone); make **the first return route (Side Control → Half Guard, which needs the P-11 segment-identity and re-entry design)** an explicit roadmap item to be decided before B2e measurement, instead of silently leaving the loop open. No mechanic is added here.

**4. Free PASS without recovery, and future inactivity penalties (SC-D8).** In v0 (as in Half Guard) a pass charges no stamina, produces no grades and flips initiative; the window it closes already advanced the clock when it opened, so two fighters passing still run the match to the clock. There are no behaviors, no recovery and no REST. B1e measured the Half Guard consequences (no-progress freezes, pass-to-the-clock). Under the approved custom stalling rule (`MATCH_INCENTIVES_HEART_OF_A_LION.md` §1) an accepted normal PASS is an **inactive personal turn**, and the third consecutive one triggers the stalling penalty, keyed by fighter ID across positions. So free passes are exactly what that future rule polices, but **nothing in v0 punishes them**. Two interactions the owner should know: a fighter who cannot afford any action (funding refusal at very low stamina) has PASS as the only non-engaging choice, which is the "no legal defense must not be automatically punished" exemption that is still undefined; and v0 has no REST, so the REST/LOW-memory direction after Heart of a Lion has no home in Side Control yet. I **agree to inherit** with one added v0 requirement: **a pass is recorded as its own decision kind with the fighter ID**, the position owns no inactivity or Heart-of-a-Lion state, and a test asserts both (§7.4 already requires the record). Classification stays at the match owner. This answers none of the open accounting questions (B2a.1 §11.2).

**5. Grade tables and their independence from the oracle (SC-D6).** The §4.3 tables were chosen to satisfy Guide §16 and checked by a disposable structural script; that verifies shape only (no dominated response, no shared best counter), not reachability, frequency or fairness, and an earlier draft failed it. The independence risk is that the same author writes the rules sheet, the oracle and the engine, so a conceptual error could be shared (Half Guard had no template; Side Control has one). Existing controls are sound and should all be required: oracle written from the **sheet only**, stdlib-only, no import of the Half Guard oracle, hand-computed literals with the arithmetic in comments, a test that parses the sheet's tables and compares them with the oracle's constants, strict integer comparators, byte-identical generation under at least three hash seeds, a mutation-sensitivity record, and the engine written from the sheet (never from the oracle) and compared against a generated fixture. Under local-first development there is no PR boundary, so independence must be **enforced by order and a checkable rule**: no GDScript may be committed to `main` before the oracle commit, verified by the path-allowlist command in §8. I **disagree only with the sequencing in SC-D6** (see the table): accept the tables as provisional prototype constants now, keep the sheet versioned, and let measurement amend them through a new sheet version and oracle change rather than a silent edit. Because the grade tables use neither `G` nor `R`, they stay independent of the initiative contract.

**6. SC-D15's obsolete PR language.** Replaced in 11A.4.

### 11A.4 SC-D15 under local-first development

The original wording ("separate oracle PR", "a separate, earlier commit and PR") assumed a PR review boundary that no longer exists. **Recommended replacement:** independent **local commit phases on `main`**, each tested locally before it is pushed, with no PRs and no automatic CI:

1. **B2b-1: rules sheet** (`SIDE_CONTROL_V0_RULES.md`): documentation only, containing exactly the owner-approved values and a "provisional prototype constants" label.
2. **B2b-2: test-only Python oracle** (`tests/oracles/side_control_v0.py`, its generator and tests) with the mutation-sensitivity record. Python and documentation only; **no GDScript**.
3. **B2c: standalone typed Godot position** and its reference test against the oracle fixture, committed only after B2b-2 is on `main`.
4. **B2d: Half Guard → Side Control edge, opt-in graph constructor**; **B2e: measurement and a new diagnostics document.**

Independence is preserved by commit order, the path-allowlist check, and the rule that the engine commit reads the sheet and fixture, not oracle code. Local gates replace CI: the oracle's own tests, the existing parity and pinned-count steps through `tools/ci/run_godot_steps.py`, and an optional manual workflow run on the exact SHA.

### 11A.5 Recommended minimal v0 set (recommendation, not approval)

- **Architecture:** identity role map (SC-D1); authority by axis sign, reported only (SC-D3); Half Guard `snapshot()` through a pure adapter (SC-D10); new explicit opt-in graph constructor, defaults unchanged (SC-D12, B2d); local commit phases (SC-D15).
- **Scope:** three actions and three responses per side, no submissions, no feints, no variations (SC-D4, SC-D9, SC-D13); keep `expose_back` as a provisional-name halting exit (SC-D5); all four exits halt (SC-D11); both `Reversal` landings stay unresolved (SC-D14).
- **Gameplay:** entry initiator is an explicit validated input supplied by the receiving rule, Top under the provisional identical profile (SC-D2); economy inherited from Half Guard with passes recorded as their own decision kind (SC-D8); fresh readiness tiers, no carry (SC-D7).
- **Numbers:** the §4.3 and §7.2 values accepted **only as provisional prototype constants** (SC-D6), versioned, with measurement allowed to amend them.

### 11A.6 Smallest owner-approval package to start B2b

B2b builds only the rules sheet and the Python oracle, so it needs no B2a.1 threshold, no `R` data and no graph decision. The owner needs to approve, in one message:

1. **SC-D1, D3, D4, D5, D7, D8, D9, D10, D11, D14** as recommended in 11A.5 (or amend named items).
2. **SC-D2 reduced to one sentence:** the Side Control entry request carries an explicit, validated `initiator`, supplied by the receiving rule; fixtures use Top.
3. **SC-D6 values as provisional prototype constants** (or list the changes). This is the **only** numerical acceptance.
4. **SC-D15 as the local commit phases of 11A.4.**

**Not needed for B2b:** SC-D12 and SC-D13 (B2d and out of scope), and the B2a.1 decisions OD-2a, OD-4, OD-9 and OD-12. B2a.1 OD-1, OD-3, OD-5, OD-6 and OD-7 are needed by **B2d**, when the graph supplies the first window.

## 12. Recommended implementation boundary

* **B2b (recommended): the accepted Side Control rules sheet and the test-only Python oracle, with its mutation-sensitivity checkpoint. Python and documentation only; no GDScript.** The oracle is written from the sheet alone, and keeping it a separate, earlier commit phase than the engine (no GDScript before the oracle commit is on `main`) preserves its independence (a Side Control engine template already exists, unlike when the Half Guard oracle was written). Alternative for the owner: the Half Guard precedent of one slice whose oracle checkpoint is pushed before any GDScript (**[OPEN]** SC-D15).
* **B2c:** the standalone typed Godot position (rules, catalog, resolver, entry, match, contract, window gateway) and its reference tests against the oracle fixture. No graph, no edge, no receiver; the only existing files touched are workflow and pin wiring.
* **B2d:** the pure Half Guard → Side Control edge adapter, the (source, destination)-keyed receiver generalization behind a **new explicit opt-in constructor**, the typed slot, the Half Guard frozen-segment fingerprint and the HG-18 failure tests, with every amended pin (§6.1, R12) listed with a reason and Mount → Half Guard behavior proved byte-identical.
* **B2e:** match-flow harness extension and a new diagnostics document for Mount → Half Guard → Side Control (measurement only; no gating of frequencies; the committed B1e documents and digests are never rewritten).
* **Not before the owner decides the items in §11, and not combined with** stalling, Momentum, Heart of a Lion, REST, scoring, return routes or any additional position.

## 13. Review record for this slice

Three read-only specialist reviews (repository PR/CI verifier, position architect and replay auditor) informed this text; their findings are folded into §6.7 (R1-R12), §8 (independence controls) and §9 (negative tests), and are listed with the CI evidence in the PR description and handoff report so that this proposal never claims evidence CI has not produced. Neither reviewer approved any rule, and no number here has been reviewed for balance.
