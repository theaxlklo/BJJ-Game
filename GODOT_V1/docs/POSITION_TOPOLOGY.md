# Position topology and transition semantics (A3c — specification only)

**Status: specification and proposals. Nothing in this document is implemented, and nothing here
changes Mount, the graph owner, the A3b carry-over schema, Python, a fixture or a digest.** It adds no
executable position, no Mount exit, no catalog entry and no rule. It exists so that the three exit
labels the frozen Mount engine happens to emit today are not mistaken for the game's complete topology.

**Follow-up (owner clarification):** the finished game normally begins from Standing, not Mount. §18 adds a
proposed canonical position-family inventory, a registry recommendation and a match-start contract; §14, §15,
§16 and §17 are updated to match. The follow-up adds decision ids P-1 to P-12 and conflict ids C-9 to C-12 and
does not renumber any earlier T-n, C-n or section reference. (The §14 step list is replaced: old steps 3–7 are now steps 7, 4, 4, 4 and 8.)

Tags used throughout (claims that could be mistaken for decisions carry one; quoted evidence and table facts
that are plainly sourced do not):

| Tag | Meaning |
| --- | --- |
| **[APPROVED]** | The Guide §0A freeze register, `POSITION_GRAPH.md` D1–D6 (**direction only**: numerical and mechanical rules are not accepted) and Slice A, `POSITION_CONTRACT.md`, and the Half Guard-first owner direction recorded in `POSITION_GRAPH.md` §1 (Slice B itself, the Half Guard rules and oracle, is **not** approved and stays gated on Q1–Q8) |
| **[OWNER-CLARIFICATION]** | Direction the owner stated while reviewing this slice (normal matches begin Standing; an explicit canonical position inventory is wanted). It sets intent, not mechanics or numbers |
| **[GUIDE-DIRECTION]** | Master Guide sections that state design intent (🔵) but are not in the §0A freeze register (for example §10, §11, §58B). This document aligns with them and does not treat them as binding |
| **[CODE]** | Verified in source at `577cec2` (A3b head). Source and tests are authoritative |
| **[PROPOSAL]** | Suggested here; non-binding until the owner approves it |
| **[OPEN]** | Needs an owner decision; no default is chosen here |

Depends on: `POSITION_GRAPH.md` (D1–D6, Slice A), `POSITION_CONTRACT.md`, `CARRYOVER_EXPORT.md` (A3b),
`WINDOW_GATEWAY.md`, Master Guide v10.4 §§0A, 4, 7, 8, 9, 10, 11, 12, 14, 15, 16, 17, 28, 29, 30, 33, 40, 55, 58B.5, 58B.6, 58B.12, 58B.13, 63, 65, 68.

## 1. The risk this document addresses

**[CODE]** The frozen Mount catalog produces an exit from exactly two actions, and only when the action is
`escape_capable`, its final grade is successful **and** the proposed axis reaches the Mount floor
(`escape_threshold_reached` in `mount_resolver.gd`). The label is chosen by
`BjjMountCatalog.exit_destination(action_id, final_grade, band_before)`:

| Technique (stable id) | Final grade | Band before | Raw label | Declared destination id | Graph verdict today (A2/Slice A) |
| --- | --- | --- | --- | --- | --- |
| `mount.bottom.elbow_knee_escape` | SUCCESS | any | `Half Guard` | `half_guard` | blocked, `destination_not_implemented` |
| `mount.bottom.elbow_knee_escape` | STRONG_SUCCESS | STABLE | `Half Guard` | `half_guard` | blocked, `destination_not_implemented` |
| `mount.bottom.elbow_knee_escape` | STRONG_SUCCESS | not STABLE | `Open Guard` | `open_guard` | blocked, `destination_not_implemented` |
| `mount.bottom.trap_and_roll_escape` | SUCCESS or STRONG_SUCCESS | any | `Reversal` | none | blocked, `unresolved_destination` |

These are the **current producible outputs of the frozen v0 catalog**. They are an inventory of what one
engine can emit, not a statement of what Mount may eventually connect to. Two facts in the table already
matter for design: one technique yields several destinations depending on result and band, and two
different branches (SUCCESS, STRONG_SUCCESS at STABLE) converge on the same destination. A flat
`label -> destination` map cannot describe that; an edge must be keyed by technique and result branch.

**[GUIDE-DIRECTION]** The guide's own content list (§11) names no Mount destinations (§11.6 defers to code and
tests), yet lists Mount as a destination of Side Control, Half Guard, Closed Guard (after sweep/reversal) and
Back Control. The only Guide-level Mount outgoing example is the §14 Elbow Escape exit map (SUCCESS → Half Guard,
STRONG SUCCESS → Open Guard), which is the source of two of the three current exits. Mount's *incoming*
connections are therefore design direction; its *outgoing* connections beyond the three above are simply
undecided, not forbidden.

### 1.1 Statements that could be misread as complete topology (report only; nothing was edited)

| Where | Statement | Reading this document adopts |
| --- | --- | --- |
| `POSITION_GRAPH.md` §1 | "Mount can reach exactly Half Guard, Open Guard, or an unresolved Reversal"; Side Control, Standing, Closed Guard "cannot be entered from Mount" | True of the current executable engine only. It justified Half Guard being first (**[APPROVED]**) and is not a topology claim |
| `BjjMountContract.EXIT_DESTINATIONS`, `UNRESOLVED_EXITS`, `transition_destinations()` | Code comment: "Mount's own exit labels -> stable destination ids" | The set Mount can *produce*; together with `exit_destination` it is the authority for producible exits and stays so (§2, §4) |
| `CARRYOVER_EXPORT.md` (Validation) | "label must be a key of `BjjMountContract.EXIT_DESTINATIONS` or in `UNRESOLVED_EXITS`" | The accepted label set is derived from the Mount contract (`mount_carryover.gd`, `_exit_error`), so the three names are present contents, not a frozen set (§10) |
| `POSITION_GRAPH.md` §14 (classification table) | "`transition_blocked(reason=undeclared_exit_label)`; halt (fail closed; label never used as a position id)" for any other exit label | Correct and kept: an engine may never emit a label its contract did not declare |
| Guide §14 | "Every technique that can break a position must have explicit destinations" | Mount `Reversal` deliberately falls short of this under D5 (**[APPROVED]** explicit unresolved). Tracked as T-6 |

## 2. Recommendation and alternatives

**[PROPOSAL] Recommendation: a two-source model with a single authority per support status.**

1. **Producible exits** remain owned by the producing position and its contract. For Mount that is exactly two
   read-only pieces and nothing else: `BjjMountCatalog.exit_destination` (technique, result and band → raw
   label, called from `mount_resolver.gd`) and `BjjMountContract.transition_for()` (raw label → declared
   destination id).
2. **Cataloged possibilities** (design intent that no engine can emit yet) live in a separate, read-only
   topology catalog of data. The catalog never restates a producible mapping and can never widen what an
   engine produces.
3. **Promotion is a move, never a copy.** When an approved slice makes an edge producible, its record leaves
   the catalog and enters the owning position's code; a consistency test refuses any edge present in both. The
   frozen Mount has no slot for technique-level edge data, so promoting an edge *into Mount* is itself a
   change-control decision (§6.3 item 7, T-4).
4. The graph owner and match coordinator stay as approved: they classify and commit atomically; the catalog
   and the contracts perform no grading, costing, admission or resolution.
5. **Position identities come from one small registry that declares identity only** (§18): stable string ids,
   no roles, no authority, no actions, no exits, no implementation flags. Whether a position can start or
   receive a match is a separate, smaller roster; what a position does stays with its contract and engine.

| Alternative | Why it is not recommended |
| --- | --- |
| A. Extend per-position label whitelists only (status quo) | No cross-position view, incoming edges undiscoverable, no way to record intent that is not yet producible; every new family re-invents the shape |
| B. One global `label -> destination` table | Second authority beside `exit_destination` and `transition_for()`; couples positions; cannot express technique/result branching |
| C. The two-source model above | Keeps one authority per status, keeps Mount frozen, allows intent to be recorded and reviewed before any engine exists |
| D. Import a pose graph (GrappleMap) | Wrong granularity (continuous stick-figure poses), no outcomes/roles/stamina; see §8 |
| E. Family-level edges only, no variations | Cannot say "side control, knee-on-belly variation" without promoting variations to nodes; contradicts Guide §10 |

## 3. Vocabulary: eight distinctions that must not be conflated

| # | Pair | Definition used here | Current example | Forbidden conflation |
| --- | --- | --- | --- | --- |
| 1 | **Position family** vs **variation / microstate** | A family is one node of Guide §8's graph with its own contract (axis, catalog, roles). A variation is a named substate inside a family (Guide §10: Technical Mount, Knee-on-Belly, North-South, Butterfly) | `mount` is a family; Mount has no substate field today (**[CODE]**) | Creating an engine per variation; or letting a variation change role semantics silently |
| 2 | **Technique** vs **result** | A technique is a stable action id; a result is the branch the resolver settled (grade, plus conditions such as band or axis crossing) | `mount.bottom.elbow_knee_escape` vs its SUCCESS / STRONG_SUCCESS(STABLE) branches | Keying a destination on the technique alone, or on `ended` |
| 3 | **Raw outcome label** vs **declared destination id** | The label is the producing engine's own string; the id is a stable snake_case position id | `Half Guard` vs `half_guard`; `Reversal` has no id | Using a label as a position id (the graph already refuses this) |
| 4 | **Defined destination** vs **implemented receiving engine** | A destination id may be declared long before any engine can receive it | `half_guard` is declared, nothing receives it | Treating `resolved=true` as "can transition" |
| 5 | **Declared connection** vs **currently executable transition** | A connection may be cataloged, producible, or receivable (§4) | Three Mount edges are producible; zero are receivable | Listing a route in a document and claiming it plays |
| 6 | **Intermediate position** vs **committed position** | A transient (scramble, Guide §30) or a multi-hop route stop is not committed until the graph owner commits it | Slice A commits nothing | Letting a transient become a graph status or appear in history |
| 7 | **Position transition** vs **submission progression** | Submission stages are position-local state; a tap is a terminal outcome (`terminal_outcome`), not an edge | Americana tap is `terminal_outcome(tap)` | Making "submission" a destination node (Guide §9 says it is not a node) |
| 8 | **Connectivity** vs **automatic chaining** | An edge says a hop is possible; chaining decides whether a follow-up is offered or taken | None exists | Executing a second technique because an edge exists (§12) |

Fighter identity, physical role, control authority and initiative stay four separate fields
(**[APPROVED]**: Guide §0A Initiative and Axis rows, `POSITION_CONTRACT.md`; detailed in Guide §7 v10.4 requirement, §12 axis clarification, §15 authority rule).

## 4. Separating executable exits from cataloged possibilities

**[PROPOSAL]** Four support statuses, one authority each. They are lifecycle labels for a *connection*; they do
not rename or replace any existing code field or error string.

| Status | Meaning | Authority of record | Can the engine emit it? | Graph behavior |
| --- | --- | --- | --- | --- |
| `undeclared` | Not mentioned anywhere | none | An engine that emits it is wrong | Existing `undeclared_exit_label`, fail closed (**[CODE]**) |
| `cataloged` | Design possibility, no engine produces it | topology catalog (data) | No | Cannot occur at run time; queryable only |
| `producible` | An engine can emit it; destination not implemented (and possibly unresolved) | the owning position contract | Yes | Existing halt: `destination_not_implemented`, or `unresolved_destination` when the destination is unknown (**[CODE]**) |
| `receivable` | A destination engine exists and validates the entry | the owning contract plus the receiver's entry validator | Yes | A future commit path (not built) |

Mapping to existing code **[CODE]**: `Transition.resolved == true` means "producible with a declared
destination id"; `resolved == false` means "producible, destination unknown". No field today means
`receivable`, and the graph never commits. Today all three Mount edges are `producible`; the catalog does not
exist.

Rules **[PROPOSAL]**:

* A catalog entry may not carry a label an engine emits. If it does, promotion has happened and the entry is
  removed from the catalog in the same change.
* The catalog never decides a result, a grade, a cost, an admission or an applicability. Applicability is a
  *name* of a predicate the owning engine evaluates.
* `unresolved` is an attribute of a producible edge, not a status. Reversal stays here until the owner decides
  (§6.3).
* A cataloged edge must cite a provenance (Guide section, or an explicit owner decision). Edges that are not in
  Guide §11 are marked `proposed` and need owner approval before they are even cataloged (T-2).

## 5. Conceptual directed graph and example routes

Edges are directed and may be parallel (same two families, different technique or branch). Nodes are
families; variations are attributes of a node reference. **Every edge below is `cataloged` or `proposed`
unless marked `producible`; none is executable.**

### 5.1 Guide-listed destinations (Guide §11, **[GUIDE-DIRECTION]**, none implemented)

```
Standing        -> Standing, Closed Guard, Open Guard, Half Guard, Turtle, Front Headlock, Side Control
Closed Guard    -> Open Guard, Half Guard, Side Control, Mount (after sweep/reversal), Back Control
Open Guard      -> Standing, Half Guard, Side Control, Back Control, Leg Entanglement
Half Guard      -> Guard, Side Control, Mount, Turtle, Back Control, Front Headlock
Side Control    -> Guard, Half Guard, Turtle, Mount, Back Control
Mount           -> (none listed; §11.6 defers to the catalog in code)  producible today: half_guard, open_guard, Reversal(unresolved)
Back Control    -> Mount, Guard, Turtle
Turtle          -> Standing, Guard, Back Control, Front Headlock, Side Control
Front Headlock  -> Turtle, Back Control, Side Control, Standing
Leg Entanglement-> Open Guard, Standing, top position
```
(Guide §11 also lists "submission" under Closed Guard, Back Control, Front Headlock and Leg Entanglement. "Guard",
"top position" and "submission" are not stable ids and are not resolved here; see C-5.)

### 5.2 Mount examples (all outgoing additions are **[PROPOSAL]**, T-2/T-4 gate)

| Example | Shape | Hops | Status today | What it would need (not decided) |
| --- | --- | --- | --- | --- |
| Elbow-Knee Escape → half guard | Mount→Half Guard, roles preserved (D1) | 1 | `producible`, halts | Half Guard engine (Q1–Q8, D6 oracle) |
| Elbow-Knee Escape → open guard | Mount→Open Guard | 1 | `producible`, halts | Open Guard engine and its own role/authority rules |
| Trap-and-Roll → Reversal | Mount→? with roles swapped | 1 | `producible`, unresolved | Landing rule (§6.3) |
| Top takes the back via technical mount | Mount→(mount, technical_mount)→Back Control, or Mount→Back Control directly | 1–2 | not producible | A Top exit-capable action; owner choice of variation vs node (T-1); Back Control engine with attacker/defender roles |
| Top moves to side control | Mount→Side Control (variation `standard` or `knee_on_belly`) | 1 | not producible | A Top positional-advance action; destination variation (Guide §10) |
| Top reaches north-south | Mount→Side Control→(side_control, north_south) | 2 hops, or 1 edge to the variation | not producible | Owner choice: route vs direct edge; each hop is a separate decision and commit |
| Top voluntarily repositions instead of maintaining | A deliberate action (Guide §12: drift "should not automatically choose a new position"; "deliberate action causes major transitions") | 1 | not producible | Is it graded and defended (T-5)? The responder must still get a legal response phase (Guide §15) |
| Bottom recovers closed guard | Mount→Closed Guard | 1 | not producible | Whether the frozen catalog's replacement or an additive catalog may emit it (T-4) |
| Bottom reaches turtle / scramble | Mount→Turtle; scramble is a transient (Guide §30), not a node | 1 | not producible | A mechanical justification and a destination role map; a scramble resolves into a real position or stays unresolved |

A **route** is a path of separately committed hops. A route is never executed as a unit: each hop needs its
own decision window, its own resolution by the owning engine and its own atomic commit. A route in this
document is a way to talk about reachability, not an action.

## 6. Identity, roles and control across transitions

Every row keeps fighter identity stable; the other three fields are decided by the destination, never inferred
from the source.

### 6.1 Examples

| Transition | Physical roles before → after | Control authority at entry | Initiative at entry | Status |
| --- | --- | --- | --- | --- |
| Mount → Half Guard (D1) | A top→top, B bottom→bottom (preserved; not a reversal, not a score) | Half Guard rule (Q2); Mount's authority does not carry over | None granted (D2); next event per Q3 | **[APPROVED]** direction, rules **[OPEN]** |
| Mount → Back Control via Top advance | A top→back attacker, B bottom→back defender | Back attacker ordinarily holds the positive side (Guide §12, §15 v10.4); defined by the Back Control contract | Back attacker ordinarily acts first (Guide §15) | Role vocabulary **[APPROVED]** (§0A, §7 v10.4); edge **[PROPOSAL]** |
| Mount → Side Control / north-south | A top→top, B bottom→bottom | Side Control contract | Side Control contract | Edge **[PROPOSAL]** |
| Mount → Turtle (bottom turns) | A top→turtle attacker, B bottom→turtle defender | Turtle contract (Guide §11.8) | Turtle contract | Edge **[PROPOSAL]** |
| Hypothetical guard-bottom landing for Mount Reversal (illustration only; landing and role map are **[OPEN]** per D5) | If such a landing were approved: A top→bottom (inside own closed guard), B bottom→top | Closed Guard contract; physical top is **not** authority | **[OPEN]**: D2 is approved for the Mount→Half Guard exit window; extending it to a reversal landing needs approval (T-6) | Landing **[OPEN]** |

### 6.2 Illustration (a hypothetical landing, not a chosen one): A is Mount Top, B is Mount Bottom, B reverses and ends on top inside A's closed guard

* **Fighter identity:** unchanged. A is still A; B is still B.
* **Physical roles:** if a landing placed B on top, they would be swapped relative to the Mount segment. In Mount
  `fighter_by_role = {top: A, bottom: B}`; in that landing it would be `{top: B, bottom: A}`. The role map
  belongs to the *edge/resolved transition*, not to the carry-over record.
* **Control authority:** B being physically on top would not give B Mount Top's authority, and A being on the
  bottom would not by itself remove A's attacking options (the Guide says a guard bottom is "often offensively
  dangerous" and "a qualifying setup/counter may transfer initiative without a physical reversal", §7). The Closed Guard contract decides authority at entry; the existing
  `BjjPositionContract.Roles` already carries `control_authority_id` and `initiative_id` as separate fields.
  Mount sets authority to its Top permanently (**[CODE]**); a guard contract must not copy that default.
* **Initiative:** **[OPEN]** for a reversal landing. D2 (approved for the Mount→Half Guard exit) says the
  exit-producing window is consumed and the Mount `initiator` field must not be read as a handoff
  (`POSITION_GRAPH.md` §4); applying that to a reversal landing is an extension that needs approval (T-6).
* **Hazard in the A3b record [CODE]:** `fighters.top` means *source* Top (A), `fighters.bottom` means source
  Bottom (B), keyed by Mount role. A receiver that indexes `fighters[destination_role]` would hand A's stamina
  to B. A consumer must re-key by fighter id using the record's own `fighter_by_role`. That is a consumer rule;
  the A3b schema needs no change.
* **Back Control:** attacker/defender, not top/bottom, is the right vocabulary (Guide §7 v10.4, §11.7). Role
  names are local to a position contract. The destination contract declares its role names; the edge's
  `role_map` maps source role names to them. `ROLES = ["top","bottom"]` in `BjjMountCarryover` is correct for a
  Mount segment and must not be reused for a Back Control segment (§10, T-9).

### 6.3 Reversal: do not assign a landing; what is missing

**[CODE]** Mount emits the label `Reversal` and nothing else; `BjjMountContract` reports `resolved=false`
(`POSITION_CONTRACT.md`). **[APPROVED]** D5: it must not be assigned a landing, mapped to a nearby position,
scored, or reported as a normal outcome. The Guide classes reversal as an overlay, not a node (§9).

The inputs a landing rule could use are **already present** in the accepted exchange record
(`BjjExchangeResult.fields()`: `attempt.action_id`, and under `resolution`: `response_id`, `raw_grade`,
`final_grade`, `band_before`, `axis_before/after`, `exit_destination`) and in the carry-over record. What does not exist is the **rule**.
Note that `exit_destination()` currently receives `(action_id, final_grade, band_before)`: the Top's chosen
response is folded into the grade and is not a separate input. A future exit map may need it.

Information a future approved slice must supply before `Reversal` can resolve **[OPEN]**:

1. **A landing rule**: a deterministic table from (technique, response, grade, band or axis) to a landing
   family and variation. Different techniques and different opponent responses can land differently. A single
   fixed landing per technique is the simplest form; whether it fits depends on the unresolved rule, and it
   must not default to closed guard or any other position.
2. **Role map** for the landing (who is physically top).
3. **Entry state for the landing**: initial control value or band, authority and initiative (Mount has no leg
   or guard configuration state, so "inside closed guard" cannot be derived from Mount data; it must be a rule).
4. Whether a **transient** (scramble) sits between the roll and the landing, and if so how it resolves
   (Guide §17, §30) and what happens when it does not resolve (T-11).
5. **Technique granularity**: one Trap-and-Roll action with response-dependent landing, or several action
   variants with fixed landings.
6. **Scoring hooks**: a sweep or reversal may score (Guide §40.1); the policy layer interprets domain events,
   the graph credits nothing (T-12).
7. **Change control for the frozen Mount**: any new field on the Mount exchange result or any change to
   `exit_destination()` alters the frozen oracle surface. The rule must be delivered additively (new code path
   or versioned catalog) and must leave raw `Reversal` and all existing fixtures untouched (T-4).

Until then `Reversal` stays `producible`, `unresolved`, and halts with `unresolved_destination`.

## 7. Position family versus variation

* **[GUIDE-DIRECTION]** Guide §10: represent configurations as substates first; promote a variation to a node only
  when human play shows it needs significantly different mechanics. Listed substates: Open Guard (Butterfly,
  De La Riva, Reverse De La Riva, Single-Leg X), Side Control (Standard, North-South, Knee-on-Belly), Mount
  (Low, High, Technical), Leg Entanglement (Ashi, 50/50).
* **[PROPOSAL]** Address a destination as two fields, never one parsed string: `position_id` (the family, the
  existing meaning of `destination_position_id`) and an optional `variation_id`. Existing records keep the
  family id only.
* **[PROPOSAL]** A variation may change the legal action set, exits and camera of its family; it may not change
  role vocabulary, axis sign convention or the engine. A change that needs those is a promotion decision.
* **[OPEN] T-1, a gap between the Guide and the frozen engine:** Mount has no substate (`substate` appears in
  Guide §7's contract list but not in `BjjMountMatch`). A *Technical Mount* variation inside Mount would add
  state to a frozen position. Options: (i) variation inside Mount (changes frozen Mount — not allowed without
  approval); (ii) a separate position id with its own contract (consistent with Guide §10 promotion when
  mechanics differ: back-take and armbar routes); (iii) a transient. No choice is made here.
* Scoring distinctions (knee-on-belly, mount, back) are policy over events (Guide §40.1: three simulated
  seconds of stabilization). A variation id may be *read* by a ruleset policy; an edge never credits points.

## 8. GrappleMap evaluation

Evaluated 2026-10-11 against upstream `master` at commit
`032c8f91809786b7b784852abd07cf3e10c0ea35` (committed 2020-03-14; 752 commits on `master`, the only branch; pull-request refs exist but no other branches). Repository:
<https://github.com/Eelis/GrappleMap>. **Nothing was cloned, vendored, imported, generated or executed in this
repository.** To verify the claims below, the upstream text files (including the 2.6 MB data file, to compute
the tallies in §8.1) were read over HTTPS into a session scratch directory outside the repository; nothing was
committed and the scratch copies were deleted at the end of the slice. This read-only evaluation is disclosed so
the owner can accept it explicitly (T-10); no data was used in any project.

### 8.1 What upstream actually shows

| Topic | Evidence (upstream file at the commit above) |
| --- | --- |
| Model | README: "Techniques are modeled in a big directed graph, where each vertex is a concrete pose of the two stick figure players, and each edge is a transition from one such position to another." |
| Nodes and edges | `src/graph.hpp`: `Graph::Node` (a `NamedPosition` with `in`, `out`, `in_out` transition lists) and `Graph::Edge : Sequence` with `ReorientedNode from, to` and the stated invariant `*from != *to` ("no identity transitions"). Edges are stored as a list, so parallel edges are representable (not verified to occur in the data) |
| Reorientation | `doc/web-editor.md`: a "mere reorientation" is "a mirror operation, a player swap, or a rotation or horizontal translation" of all joints. *Our inference:* node identity is pose identity modulo player swap, **not** fighter identity |
| Intermediate frames | `doc/web-editor.md`: edits to frames other than the first and last "are always local"; the first and last frames are "at a connecting position". *Our inference:* an intermediate pose is not a node |
| Metadata | `doc/web-editor.md`: first line is the name; `tags:` and `properties:` lines. Documented properties: `top`/`bottom`, `bidirectional`, `detailed`. Data also contains `ref:` (source citation), `todo:` lines, and the undocumented properties `sweep` and `transitive` |
| Tags | README: tags give "categorization into domains (e.g. deep_half, side_control)", "detailed information about poses (e.g. bottom_supine, top_posture_broken)" and "specific grips or controls (e.g. lockdown, kimura, crossface, arm_drag)" in a single unscoped tag list (our observation of the data, not an upstream statement) |
| Fidelity | README: "The graph structure itself is obviously a gross simplification"; techniques appear "in their bare textbook form"; "The timing of techniques is also not really captured at all"; animations "are really just schematics" |
| Scope | README: "(no-gi) grappling"; MMA-applicable techniques from several arts; "there are no [gi-specific] techniques in the database" |
| Data format | One plain-text file `GrappleMap.txt` (2,674,097 bytes, SHA-256 `734c5af03958f7384af1c09b18bf06500748a8c505573e5be9a48174ddcfb74e`). A position is name, tags and one frame of joint coordinates (four 69-character base-64-like lines); a transition is two or more frames. README: "pretty ad-hoc and minimalistic ... I fully expect that the format will evolve into something different" |

Approximate tallies from a heuristic parse of that file (own tally, not an upstream claim): about 2,086
entries, of which about 601 single-frame (positions) and 1,485 multi-frame (transitions); 161 distinct tags;
`properties`: top 616, bottom 558, detailed 159, bidirectional 38; 1,208 `ref:` lines. Family tags sit
mostly on positions: `half_guard` 55, `full_guard` 52 (token occurrences; 51 distinct entries), `side_control` 46, `turtle` 30, `back` 28,
`closed_guard` 22, `mount` 15, `three_quarter_mount` 7, `s_mount` 2, `north_south` 6, `knee_on_belly` 6;
`open_guard`, `front_headlock` and `technical_mount` do not occur as tags (`headlock` once).

### 8.2 Licensing and provenance

* `LICENSE` (147 bytes), verbatim: "All authors involved in the creation of the contents of this package have
  agreed to release their respective contributions into the Public Domain."
* README FAQ: "What license is the code and data under? None; the GrappleMap code and data is released into the
  public domain."
* GitHub's license detector reports `NOASSERTION` / "Other" (no recognized SPDX license).
* Contributors per the GitHub API: two accounts, 751 and 1 commits (merged history only; other people have opened
  pull requests that were never merged).
* **Reading:** the public-domain intent is stated twice and consistently. It is an informal dedication, not a
  recognized instrument with a fallback license (as CC0 or the Unlicense provide), and it asserts the agreement
  of "all authors" without evidence this repository can check. The pose data cites third-party instructional
  materials in `ref:` lines; those are citations, not copied content, but the poses are the author's
  interpretation of that material. `grappleman.mhm` is a MakeHuman 1.1.0 export ("Written by MakeHuman 1.1.0") with no license or author
  metadata; the license of that asset and of the hosted website <http://eel.is/GrappleMap/> was **not** reviewed.
* **Conclusion:** the repository states that code and data are public domain, but reuse of actual data would
  need an owner and, if desired, legal sign-off first (T-10). This is not legal advice.
* Activity: master has no commits after 2020-03-14. GitHub's `pushed_at` (2023-02-06) coincides with the creation of closed,
  unmerged pull request #2 from a fork, i.e. a push to a PR ref. Eight PRs exist (six open, two closed); none has been merged.
  Treat the project as effectively static with an explicitly unstable format.

### 8.3 Value and limits for BJJ-Game

| Idea | Verdict |
| --- | --- |
| A graph as a *possibility structure* with no execution semantics: traversal is a query, never a result | **Adopt the concept** (original text, §12). Matches our Part 6 separation and Guide §58B.6 |
| A family is a classification over many concrete states, not a node identity | **Adopt the concept** as family vs variation (§7) |
| Node identity modulo player swap | **Adopt the caution**: it reinforces keeping fighter identity separate from pose or role (`POSITION_CONTRACT.md`) |
| No identity (self) edges | **Adopt** for the edge model: a transition with the same source and destination is not an edge |
| Reverse direction is the exception (38 of about 1,485 transitions carry `bidirectional`) | **Adopt**: model each direction as its own edge (the technique differs: escape vs pass) |
| `ref:` provenance on every edge | **Adopt**: each cataloged edge cites a Guide section or owner decision |
| Flat, unscoped tag namespace mixing family, posture, grips, techniques | **Do not adopt**: scope any classification by facet; never let tags carry rules |
| Joint-coordinate poses, keyframe transitions, stick-figure animation | **Not adopted**: presentation material; 2D stylized art is the approved v1 direction (Issue #40), deferred |
| Data import, a dependency, generated content | **Not adopted** in A3c and not proposed. A later, owner-approved *offline* vocabulary cross-check (pinned commit and hash, human review, no runtime path) is the only reuse worth considering |

Practical limits: no outcomes, grades, responses, stamina, roles, initiative or rulesets; no-gi and
MMA-oriented; includes techniques whose legality depends on belt and ruleset (our ruleset policy owns that);
granularity is one textbook path per transition, while ours must branch by result.

## 9. Proposed future transition contract

**[PROPOSAL, candidate fields only; not a schema to freeze.]** Avoid one universal object. Three small
records, each field with a named writer. Later stages *read* earlier records and never modify them, so no field
is written by two stages:

| Record | Writer of its fields | Lifetime | Purpose |
| --- | --- | --- | --- |
| **Declared edge** | the catalog author for `cataloged` edges; for `producible` edges the producing position's code (nothing is stored in the catalog) | static data | A possible connection and what it needs |
| **Resolved transition** | the producing position's contract only (an extension of today's `Transition`) | one per accepted exit | What actually happened, in the producing engine's terms |
| **Entry request** | the graph owner only | built at commit time, discarded after | What the receiver validates to construct itself |

### 9.1 Candidate fields

| Field | Record | Writer | Notes |
| --- | --- | --- | --- |
| `source_position_id`, optional `source_variation_id` | edge, resolved | catalog / producer | Stable ids; `mount` today |
| `technique_id` | edge, resolved | catalog / producer | Stable action id (`mount.bottom.elbow_knee_escape`); never a label |
| `result_branch` | edge, resolved | catalog names it; producer settles it | Grade plus the conditions the engine used (band, axis crossing); named, never computed by the catalog |
| `applicability` | edge | catalog (a predicate *name*) | The owning engine evaluates it; the catalog never does |
| `edge_id` | edge; referenced by resolved | catalog | Stable, composed from the parts above, never parsed. Legacy label exits have none |
| `raw_destination` | resolved | producer | Today's `Transition.raw_destination` |
| `destination` = `{position_id, variation_id?}` | edge; resolved | catalog (cataloged) / producer (producible) | Today's `destination_position_id` is the family id |
| `destination_resolved` | resolved | producer | Today's `resolved` (unchanged meaning) |
| `support_status` | edge | catalog (`cataloged`) / owning position (`producible`, `receivable`) | `cataloged`, `producible`, `receivable` (§4) |
| `role_map` | edge | catalog (cataloged) / producer (producible) | Source role -> destination role names; identity map for Half Guard (D1). The entry request carries a read-only snapshot |
| `entry_authority`, `entry_initiative` | entry request | graph owner, from the **receiver's declared rule** | Never copied from the source; `entry_initiative` may be "none" (D2, Q3) |
| `entry_state_requirements` | edge | receiver declares | Names of fields the receiver needs, no values |
| `carryover_requirements` | edge | graph owner | Which carry-over blocks are required (the A3b blocks are the baseline) |
| `transition_id`, `event_index` | entry request | graph owner | Deterministic: the graph's global monotonic event index; no wall clock, frame or UI input |
| `source_window_id` | entry request | graph owner, read from the carry-over `last_issued_id` | Equals the id of the exit-producing window |
| `provenance` | edge | catalog author | Guide section or owner decision |

### 9.2 Cataloging without duplicating `transition_for()`

* One catalog module **per source position**, kept beside that position's contract, so adding Side Control's
  outgoing edges does not edit Mount files. A single read-only aggregator answers outgoing/incoming queries
  (incoming is computed by inversion, never stored).
* Producible edges are **not stored in the catalog**, so the label mapping exists once. No contract member lists
  technique-level producible edges today (`transition_destinations()` returns destination ids only). Until a
  separately approved API exists (for example a contract-level `producible_edges()`), the aggregator would obtain
  Mount's by read-only enumeration of `exit_destination` × `transition_for`, as proposed for A3d (§14).
* Technique content stays in the technique catalog (Guide §28: `start_positions`, per-grade exits,
  `chain_tags`). The topology catalog records connections between positions, keyed by technique id, and never
  copies grades, costs or setup effects.
* A validator (future, negative-first) rejects: an edge present as cataloged and producible; a cataloged edge
  whose source equals its destination; a destination or technique id that does not resolve; a variation not
  declared by its family; a `receivable` edge whose destination contract is absent.

### 9.3 What changes, deliberately and version-safely, when a destination becomes executable

**[PROPOSAL]** Required order, each step its own reviewed change:

1. Destination rules accepted and a test-only oracle in place (D6; for Half Guard, Q1–Q8 in `POSITION_GRAPH.md`).
2. The receiving contract and an additive entry factory exist and pass their own negative-first tests.
3. The edge moves from `producible` to `receivable` (single owner, no duplicate).
4. The graph classifier gains a third verdict, a commit, beside `none` and `blocked`; today it cannot return one
   (`classify_exit_from` comment). Commit appends exactly one `transition_committed` and swaps the active
   segment atomically (`POSITION_GRAPH.md` §5).
5. **Carry-over validation is versioned, not edited in place** (§10): only the `position_graph_carryover`
   envelope carries the halted-export assumptions, so it needs a v2; a build that can commit stops producing v1
   halted envelopes for that exit. The `mount_carryover` v1 *segment* stays consumable unchanged.
6. Mount's declared exits, the three halted-export assumptions and the tests that use `Side Control` as an
   invalid example are updated in the same reviewed change as the engine that makes them true.

## 10. Impact on the existing A3b carry-over validation

Verified in `mount_carryover.gd` and `test_carryover_export.gd` at `577cec2`. **A3c changes none of it.**

| A3b element | Impact now | Impact when topology grows |
| --- | --- | --- |
| Segment schema `mount_carryover` v1 | None | A back-control or other source needs its own segment schema (different roles); records stay per source family. No giant universal record |
| Accepted exit-label set | None. It is derived from `BjjMountContract.EXIT_DESTINATIONS` / `UNRESOLVED_EXITS`, not literal | A new Mount-producible but unimplemented exit would pass the v1 segment and the derived reason check without a schema change, which is the intended extensibility. It also silently widens v1, so adding any Mount exit must be a visible, reviewed change |
| Tripwires | The A2 classification test and A3b tests use `Side Control` and `Mount` as example *invalid* labels (`test_position_graph_classification.gd`, `test_carryover_export.gd`) | A future Mount exit to Side Control makes those assertions fail by design; they must be updated deliberately, not weakened |
| Envelope v1 halted-export assumption (`validate_envelope` only: reason is `destination_not_implemented` iff resolved, else `unresolved_destination`; halted <=> exit; `ended` with an exit is rejected) | Correct: no destination is implemented | The first implemented destination breaks "halted <=> exit". Envelope v1 keeps describing the world where nothing is implemented; a committing build must emit an envelope v2 and must not label such records v1. `validate_segment` v1 would still accept the same Mount segment |
| Exact-key validation (both schemas) | None | Any new key (edge id, technique id, role map, landing in the segment; segment index, transition record in the envelope) fails v1 by design, which forces a version bump instead of a silent extension |
| Role-keyed fighter blocks | None | Re-key by fighter id for any swap landing (§6.2) |
| `window.last_issued_id` | None | Receiver continues from `last_issued_id + 1`; ids are never reused (`POSITION_GRAPH.md` §7) |
| D3-B block | None | It is the Mount Bottom's episode; the record's own `fighter_by_role.bottom` identifies whose it is. Applicability in a receiver is §11 item 3 |
| Graph block `{status, event_count, blocked_transition}` | None | A committed graph needs a segment index and a transition record; both are envelope v2 additions |
| Segment `exit` block = `Transition.fields()` | None | Cannot express technique, branch, role map or landing detail; a richer resolved transition implies a new *segment* schema version |

**Version constants.** `BjjMountCarryover.VERSION = 1` is a single constant checked by both `validate_segment`
and `validate_envelope`. An envelope v2 must therefore not be introduced by bumping it, which would reject
segment v1 records; separate segment and envelope version constants are needed. This is a prerequisite note for
that future slice, not a change here.

## 11. Receiver-state decision matrix

Current ownership **[CODE]**: the gateway owns window state; the `BjjMountMatch` it owns holds both stamina
pools, both behavior meters, the clock and the D3-B controller; the graph owns only status, the global event
log and the recorded blocked transition (`POSITION_GRAPH.md` §14). The earlier D3 text describing a graph owner
that holds pools and meters is the *end state*; `POSITION_GRAPH.md` §14 states it moves "as one move, never as a
duplicate".

| # | Question | Approved today | A3b actual | Unresolved |
| --- | --- | --- | --- | --- |
| 1 | Latches inside hysteresis | D4: shared stamina and the exhaustion latch persist; the transition charges nothing | Record carries `exhaustion_latched`; validator allows either value between thresholds (both exercised in `test_carryover_export.gd`) | How a receiver restores a latch that `create` does not derive from `current` |
| 2 | Ids, roles, authority, initiative | D1, D2; Guide §7/§12/§15; four separate fields | Record carries ids and source roles only | Role map and entry authority/initiative per destination |
| 3 | D3-B episode | Freeze, never observe in the receiver is **proposed, subject to Q6** (`POSITION_GRAPH.md` §6), not approved | Three fields exported | Applicability in each receiver, and re-entry reconciliation |
| 4 | Reversal landing | D5: stays unresolved | Exported as unresolved | §6.3 |
| 5 | Time, meters, window ids, history | D2 zero seconds; D4 meters carried; D3 monotonic global event log and window ids | Clock, remainders, `last_issued_id` exported; event count in the graph block | Seeding window counter and meters in the receiver |
| 6 | Re-entry into an earlier position | "Return to Mount is unsupported" (`POSITION_GRAPH.md` §10) | Nothing | Segment identity, history, D3-B |

### 11.1 Latches inside hysteresis

Facts **[CODE]**: `BjjStaminaPool.create(start, capacity)` sets the latch from `start` alone
(`start <= exhaustion_enter_threshold`). There is no dedicated restore API, and `_exhausted_latched` is an
implementation-only field (GDScript has no private members). The latch only changes in `_refresh_latch`: a
latched pool stays latched until `current >= exhaustion_recover_threshold`. The public `set_current` and
`recover_up_to` both call it. A fighter latched at 30 and one unlatched at 30 both occur (exercised by the
A3b tests), so rebuilding a pool from `current` alone can silently flip a latch and change later behavior.

| Option | Description | Risk |
| --- | --- | --- |
| a | Receiver rebuilds each pool with `create(current, maximum)` | Silently drops hysteresis; a stamina-policy change nobody approved |
| b | Add a validated pool factory that accepts the latch (rejecting values the thresholds forbid) | New production API in a parity-covered module; needs a restore-then-advance equivalence test over the hysteresis grid |
| c | Refuse transitions while any latch is between thresholds | Arbitrary, gameplay-visible, hard to explain |
| d | Hand the same pool objects to the receiver (graph owner holds them, per D3 end state) | Moves ownership out of `BjjMountMatch`, which is a larger refactor of a frozen position |
| e | Reconstruct through the existing public API: unlatched → `create(current, maximum)`; latched → `create(0, maximum)` then `set_current(current)` (the latched pool stays latched while `current` is below the recover threshold) | No production change, but unproven: needs the same restore-then-advance equivalence test and a check of every (current, latch) pair the validator accepts |

**[PROPOSAL]** Direction: prove (e) first, because it needs no new production API; fall back to (b) only if the
equivalence test fails; (d) is the end state and can follow. Never (a). Requires owner approval (T-7).

### 11.2 Identity, role, authority and initiative

**[PROPOSAL]** The edge declares `role_map`; the destination contract declares role names, `entry_authority`
and `entry_initiative` by its own rule; the carry-over record is re-keyed by fighter id. Nothing is derived
from physical top/bottom or from Mount's `initiator`. Alternative (derive authority and initiative from the
carry-over) invents rules and is rejected.

### 11.3 D3-B ownership and applicability

Facts **[CODE]**: the controller changes state only in `observe_advance` and `decide`; its mutable state is the
three exported booleans (`armed`, `token_consumed`, `previous_exhausted`) plus `initialized`, which is a constant
`true` for every gateway-built match and is not exported. The exported record identifies whose episode it is via
`fighter_by_role.bottom`, so a role-swapping landing does not orphan it.

Options **[OPEN]** (Q6 in `POSITION_GRAPH.md`; no recommendation is made here): (a) carry the frozen record
unchanged and apply it only if a Mount-lifecycle receiver exists; (b) discard it on exit (loses `token_consumed`
evidence needed on re-entry); (c) a per-position analogue (new rules, needs its own approval, Q5). A3b already
exports the three fields, which keeps (a) and (c) possible without deciding between them.

### 11.4 Reversal landings

See §6.3. Alternatives: (a) fixed landing per technique; (b) a landing function over (technique, response,
grade, band) in the owner-approved exit map (Guide §14, deterministic); (c) resolve through a transient with
simultaneous choices (Guide §17, §30, a new resolution path); (d) keep unresolved (current).
**[PROPOSAL]** Direction: (b) as the form, with content only after owner approval and after Half Guard; keep (d)
until then.

### 11.5 Continuity

* **Time:** zero seconds pass in the transition (D2); remaining/initial clock copy through the receiver factory.
* **Meters:** `BjjBehaviorStaminaPolicy.Meter` already accepts a remainder at construction (`_init(remainder)`),
  so restoring meters needs no new API; the receiver factory must still be tested.
* **Window ids:** the receiver is seeded so its first issued id is `last_issued_id + 1`. Seeding is a new
  additive parameter and does not exist today.
* **History:** Mount history stays Mount history; the graph's event log is the cross-position record, with one
  global monotonic index.

### 11.6 Re-entry into an earlier position

**[PROPOSAL]** *Revised by the A3c follow-up (C-11):* because a normal match starts in Standing and returns to it
(stand-ups, scrambles), re-entering a position is expected rather than exotic, so the segment identity below is
needed before the first route back to Standing, not only for a hypothetical second Mount visit. A second
segment of any position is a *new* segment built from carry-over, never the first gateway resurrected. It needs a graph-owned segment index, continuing (never reused) window
ids and one continuing event log. Mount's D3-B record must not grant a second token on re-entry (the `POSITION_GRAPH.md` §6 risk).
Alternatives: (a) keep re-entry unsupported (current for Mount; no longer sufficient once Standing is the start
position, see P-11);
(b) allow it with a fresh segment, the frozen D3-B record and an explicit rebase operation (needs a controller
operation that does not exist); (c) a fresh controller (risks a repeatable token).

## 12. Keeping chaining separate from topology

**[GUIDE-DIRECTION]** Guide §58B.6 separates three graphs: the *position graph* (states and legal transitions
from Exit Maps), the *technique chain graph* (follow-ups conditioned by state, setup, responses and submission
state) and the *memory constellation* (a player's personal view, "not a second source of rules").
§58B.13: "A chain link never traverses an illegal transition." Guide §58B is a "Design baseline proposed for
owner approval" and `AGENTS.md` does not treat experimental memory or chain mechanics as approved, so this
document aligns with it without relying on it as binding. The topology catalog here is the first of those
graphs only.

**[PROPOSAL]** Rules:

1. An edge says a hop is possible. It never executes a technique, opens a window, spends stamina or advances a
   clock. A connected next technique is *offered* at the next decision window, never taken.
2. The topology API is read-only: `outgoing(position)`, `incoming(position)`, `edge(edge_id)` returning detached
   copies with `support_status`. It has no execute, advance or commit entry point.
3. A chain link stores its own predicates: applicability, the opponent response that keeps it open, the
   fighter's knowledge, stamina and the decision-window rule (Guide §16: follow-ups depend on setup, chain
   depth, position, stamina, technique knowledge and the opponent's response). It may reference topology edge
   ids and technique ids, but it never reads a topology edge as proof that the follow-up happens.
4. A chain link is enabled only if the topology edge exists **and** its support status allows the hop **and**
   the link's own predicates hold; otherwise it is disabled with a stable reason code, not a fabricated route.
5. Chain bonuses (Guide §58B.5 "Chain" memories) arrive as explicit deterministic inputs approved separately; the
   graph's event log is an audit record, not a modifier channel.
6. `transition_committed` is a "new position established" fact that Guide §33 lets Chain Depth policy consume.
   That is an event consumed by policy, not graph logic.
7. Submission switching and Chain Depth (Guide §33) are position-local submission rules and stay separate
   from positional edges.
8. Deterministic replay still depends only on resolved commands; chaining may reorder the *menu*, never the
   authoritative outcome (Guide §58B.12: filters never change legal action enumeration).

## 13. Approved decisions preserved

| Decision | How this document preserves it |
| --- | --- |
| D1: Mount→Half Guard preserves ids and roles; not a reversal or score | Used as the identity map example (§6.1) |
| D2: the exit-producing window is consumed; no initiative handoff, no extra window, zero seconds | Receiver gets no window; `initiator` is not read (§6.2) |
| D3: a match-level graph owner commits; positions report exits | Catalog and contracts never commit (§2, §12) |
| D4: shared stamina primitives carry; Mount policies do not automatically apply | Latch/meter carry stays; D3-B applicability left open (§11) |
| D5: Reversal stays unresolved and explicit | Never mapped (§6.3) |
| D6: a test-only Python oracle for any new position's rules | First step of §9.3 |
| Half Guard first (the first receiving-position integration target); Open Guard declared-but-unimplemented at the unsupported boundary | §14 keeps both unchanged. Standing as the future *entry* engine on a separate track is a **[PROPOSAL]** (P-10) built on the owner clarification; it does not replace Half Guard (§18.7) |
| Slice A halt semantics and `halted_at_unsupported_transition` | Unchanged; v1 halted exports stay valid as v1 (§10) |
| A3b schema, `destination_not_implemented` / `unresolved_destination` distinction | Unchanged; no file under `scripts/` or `tests/` touched |
| Frozen Mount, Python oracle, fixtures, digest | Untouched; any Mount extension is additive and separately approved (T-4) |

## 14. Smallest safe implementation sequence after A3c

**[PROPOSAL]** Each step is a separate, reviewable, explicitly authorized slice. None is started here. The A3c
follow-up replaces the earlier seven-step list with two tracks that share a registry (§18.7).

1. **Owner decisions** T-1 to T-3, P-1 to P-5 and P-10 (vocabulary, support statuses, registry representation,
   initial inventory, start contract, track ordering). P-6 to P-9, P-11 and P-12 are decided when the step that
   needs them is reached. Documentation only.
2. **"A3d" (proposed name; test-only): pin the producible-exit inventory.** Enumerate (technique x grade x band)
   through the existing catalog function and assert the producible set equals today's three labels. No
   production edit. Recommended next code-adjacent slice; unchanged by the follow-up.
3. **Position registry** (ids only): one pure class, negative-first tests, no behavior change; Mount's
   `POSITION_ID` keeps the value `"mount"`. Justified by the owner's explicit request for a canonical inventory
   (P-1, P-2) and by start-position validation. A second consumer (the catalog validator, graph source checks)
   is **not yet proven**: `bjj-scope-plan` asks for proof from a second use case before a generalized framework,
   so the owner may prefer only a pinned id list plus a test until Standing's factory (S1) lands. Only after P-1
   to P-3.
4. **Track A, receiving-position integration (unchanged except for the P-10 proposal below; Half Guard first):** Half Guard rules and test-only
   oracle (Q1–Q8, D6) -> receiver seams (T-7) -> graph commit path and envelope v2 -> Mount→Half Guard. Half Guard's
   entry must accept a role map and must not assume a Mount source (P-10).
5. **Track B, Standing as the normal-match entry engine:** Standing rules specification and test-only oracle
   (P-8, P-9, D6) -> a fresh-start entry factory and a start-position-aware constructor with default `standing`
   (P-5 to P-7) -> honest halts for destinations that are not yet receivers -> receivers added in the order
   Standing's exit map demands them (Half Guard first, shared with Track A).
6. **Re-entry and segment identity** before the first route back to Standing (P-11).
7. **Topology catalog data and validator** (conditional): only if T-1 to T-3 are approved and the registry
   plus a second consumer exist.
8. Later: Open Guard, the remaining families until all ten are reachable (Guide §63 Phase 2 exit), then the
   Reversal slice (needs the landing rule, T-6).

## 15. Open questions requiring owner approval

| ID | Question |
| --- | --- |
| T-1 | Adopt the family / variation vocabulary and promotion criteria; how is Technical Mount represented given Mount has no substate (options i–iii in §7) |
| T-2 | May the catalog list edges that are not in Guide §11 (for example Mount→Back Control, Mount→Side Control)? What provenance is required? |
| T-3 | Approve the support-status vocabulary (`cataloged`, `producible`, `receivable`) and the single-authority and promote-as-move rules |
| T-4 | How may the frozen Mount gain new outgoing techniques or a Reversal landing without changing frozen behavior: a versioned catalog, an opt-in ruleset flag, or a separate position id? |
| T-5 | Is a voluntary reposition a graded, defended action (consumes a window and stamina) or something else? |
| T-6 | Reversal: landing set, rule inputs (technique, response, grade, band), role map, entry authority and initiative, scoring hooks, transient or not (§6.3) |
| T-7 | Receiver state: latch restoration option (a–e), D3-B applicability and re-entry, window and meter seeding |
| T-8 | Is a submission finish always a terminal outcome rather than a destination ("submission" is listed as a destination in Guide §11 but §9 says it is not a node)? |
| T-9 | Role vocabularies and segment schemas per family (attacker/defender for Back Control, Turtle, Front Headlock, Leg Entanglement) |
| T-10 | Accept this evaluation's read-only reading of upstream files (§8)? May GrappleMap be used even as an offline vocabulary cross-check? Requires licensing sign-off first (§8.2) |
| T-11 | Is a transient (scramble) ever a committed, haltable state, or always resolved inside the exchange? |
| T-12 | Where do scoring hooks attach (events interpreted by a ruleset policy), and who owns the three-second stabilization clock? |

Decisions added by the A3c follow-up (§18); the T-n ids above are unchanged:

| ID | Question |
| --- | --- |
| P-1 | Registry representation: approve stable string ids behind one validated registry (recommended) instead of an integer enum or loose constants (§18.2) |
| P-2 | Approve the ten families of §18.1 as the *initial* registry inventory (not a claim to enumerate every position), and the rule for adding a family |
| P-3 | Id lifecycle: append-only, never renamed or reused; is a registry version recorded in persisted records, or is append-only enough? |
| P-4 | Variation registration: families only in the first registry, or variations declared per family now; promotion criteria (extends T-1; Technical Mount stays unresolved) |
| P-5 | Approve the default-start contract: normal matches start `standing`; an explicit start id is allowed for training and scenarios; explicit failure, never a fallback (§18.4) |
| P-6 | Interim constructors: keep today's Mount-only constructors as the explicit Mount scenario path, with `start="mount"` delegating to them (no second Mount path); the start-aware constructor fails explicitly for the default until Standing exists (§18.5) |
| P-7 | Two entry-factory kinds (`fresh_start`, `carryover_entry`) tracked in an implementation roster separate from the registry (§18.6) |
| P-8 | Standing neutral representation: role vocabulary (no top/bottom), no control authority, and how the contract expresses no initiative and sealed simultaneous choices (Guide §17), which today's `Roles` and `Command` cannot (C-12) |
| P-9 | Standing's first action set and exit-map policy: full exit maps with honest halts (recommended), a restricted catalog, or wait for receivers; how a remain-in-Standing result (the Guide's FAILURE → Standing) is expressed, since Standing→Standing is not a self-edge (§18.7) |
| P-10 | Confirm Half Guard remains the first receiving target, Standing is the parallel entry-engine track, and Half Guard's entry accepts a role map from non-Mount sources |
| P-11 | Re-entry and segment identity needed earlier because Standing is the start and is re-entered (revises the timing in §11.6) |
| P-12 | Scenario and training starts: who supplies roles and initial state for a non-Standing fresh start, and must the state be rule-legal for that position? |

## 16. Conflicts and inconsistencies found (reported, not silently resolved)

| ID | Observation | Disposition |
| --- | --- | --- |
| C-1 | `POSITION_GRAPH.md` §1 "exactly Half Guard, Open Guard, or Reversal" reads as topology; Guide §11.6 says Mount's destinations are defined by code | Treated as the current producible inventory (§1.1); the file is unchanged |
| C-2 | `POSITION_GRAPH.md` §3 (graph owner holds pools, meters, counter) differs from Slice A §14 and A3b actual ownership (gateway/match owns them) | §14 already reconciles it; this document follows A3b actual ownership and treats D3 as the end state |
| C-3 | Guide §14 requires explicit destinations for position-breaking techniques; Mount `Reversal` has none (D5) | Known and approved as an explicit gap; tracked as T-6 |
| C-4 | Guide §10 lists Technical Mount / Knee-on-Belly / North-South as substates; the request lists them as family examples; frozen Mount has no substate | Modeled as variations by default; T-1 |
| C-5 | Guide §11 lists "submission", "Guard" and "top position" as destinations; Guide §9 says submission is not a node; none is a stable id | Not resolved here; T-8 and a later id decision |
| C-6 | `POSITION_GRAPH.md` §6 D3-B "frozen" is labeled "proposed, subject to Q6" yet A3b already exports D3-B state | Consistent (export only); D3-B behavior in receivers remains open |
| C-7 | The test-only `declarations` argument of `classify_exit_from` is a flat `{label: destination}` map | Adequate as a test seam; it cannot express technique/result branching and must not become production topology |
| C-8 | Name `transition_destinations()` suggests "all destinations" but returns only Mount's producible set | Not renamed; documented in §1.1 |
| C-9 | Code and slice documents construct only Mount (`BjjMatchWindowGateway.create`, `BjjPositionGraphMatch.create`, `POSITION_GRAPH.md` Slice A) while the Guide's North-Star milestone, §55 and §68 begin matches in Standing | Not a rule conflict: Mount-only construction is a development artifact. Recorded so no one reads it as the intended default (§18.5); nothing changed |
| C-10 | `test_position_graph_classification.gd` pins `unknown_source_position` for `half_guard`, `open_guard`, `side_control` and `standing`; a registry would tempt a "declared but not implemented" reason for them | Keep the pinned reason until an owner-approved change; any new reason is a deliberate test update (§18.8) |
| C-11 | §11.6 above recommended keeping re-entry unsupported until a second position exists; with Standing as the start position that is no longer sufficient | This document's own recommendation is revised in place (§11.6, P-11); no approved specification is affected |
| C-12 | `BjjPositionContract.Roles` holds one `initiative_id` and `Command` names one submitting fighter, so Guide §17 sealed simultaneous choices (Standing) cannot be expressed | Reported as a design gap (P-8); the contract is not changed here |

## 17. What A3c did and did not do

Added this specification and one-line pointers from `PORT_STATUS.md`, `POSITION_GRAPH.md`,
`POSITION_CONTRACT.md` and `CARRYOVER_EXPORT.md`. The follow-up added §18 (canonical inventory, registry
representation, match-start contract) and updated §2, §11.6, §13, §14, §15, §16 and this section, plus the header, legend, "Depends on" list and one
sentence in `PORT_STATUS.md`. The only code executed was a throwaway enum check in a scratch project outside the
repository (§18.2). It changed no GDScript, no Python, no test, no workflow, no
fixture, no digest and no earlier PR. It created no executable position, receiver, catalog, grade, stamina,
D3-B, clock or policy rule, implemented no Standing, enum or registry module, and it chose no Reversal landing.
Mount remains the only constructed position and its three exits are unchanged.

## 18. Canonical position registry and match start (A3c follow-up)

**[OWNER-CLARIFICATION]** The finished game normally begins from Standing, not Mount. Mount is the first
implemented and parity-qualified position because it was the initial engineering prototype; it is not the
intended default start. The owner wants an explicit canonical inventory of position families, analogous to an
enum, from which definitions and implementations are organized, without adopting a rigid integer enum before
persistence, replay compatibility and the existing string ids are assessed.

Supporting direction **[GUIDE-DIRECTION]** (none of it is in the §0A freeze register): §55 Definition of Done
("The player can: begin Standing"), §63 Phase 3 exit ("every normal match can begin Standing"), §63 Phase 6
North-Star Milestone #1 ("plays a complete BJJ match from Standing"), §68 ("Match starts Standing") and §4
("A full match must flow through Standing, takedown entries, ... Leg Entanglement"). Everything below is a
**[PROPOSAL]** unless tagged. **Nothing here is implemented: Standing is not executable, there is no registry or
enum module, and the runtime default and the three Mount exits are unchanged.**

### 18.1 Proposed canonical position-family inventory (initial registry)

Ten ids, taken from Guide §8 ("exactly ten top-level nodes"). The role, Guide and code columns are planning
context, **not registry fields** (§18.6).

| Proposed id | Guide | Role vocabulary the Guide uses | In code today **[CODE]** |
| --- | --- | --- | --- |
| `standing` | §8 #1, §11.1, §17, §29 | none stated; neutral, equal authority, sealed simultaneous choices (§17) | No engine. The id appears only as an *invalid-source* example in `test_position_graph_classification.gd` |
| `closed_guard` | §8 #2, §11.2 | Bottom / Top | Nowhere |
| `open_guard` | §8 #3, §11.3, §10 | Bottom / Top | `BjjMountContract.EXIT_DESTINATIONS` (a declared Mount destination, no engine) |
| `half_guard` | §8 #4, §11.4 | Bottom / Top | Same as `open_guard` |
| `side_control` | §8 #5, §11.5, §10 | Top / Bottom | Nowhere (tests use it as an invalid example) |
| `mount` | §8 #6, §11.6, §10 | Top / Bottom | Implemented: `BjjMountContract.POSITION_ID`, gateway and graph; **fresh-start only** (§18.6) |
| `back_control` | §8 #7, §11.7 | Attacker / Defender | Nowhere |
| `turtle` | §8 #8, §11.8 | Attacker / Defender | Nowhere |
| `front_headlock` | §8 #9, §11.9 | Attacker / Defender | Nowhere |
| `leg_entanglement` | §8 #10, §11.10, §10 | Attacker / Defender | Nowhere |

Format: lowercase snake case, the same style as the existing `mount`, `half_guard` and `open_guard`.

**Other top-level families the Guide requires:** none found. §8 fixes ten; §9 lists takedown, sweep, pass,
reversal, submission and scramble as *not* nodes; §30 calls scramble "a transient state, not an eleventh node".
Words in destination lists are not extra families: "Guard" must resolve to `closed_guard` or `open_guard` by an
exit map, "Top Half Guard" is `half_guard` with a role assignment, and "top position" and "submission" are
unresolved (C-5, T-8). Terminal outcomes (timeout, tap), halts and referee or mat-boundary resets (Guide §65,
open) are match events, not positions; whether a boundary reset re-enters `standing` is a ruleset question.

**What this inventory is not.** It is an initial registry of top-level families, not a claim to enumerate every
BJJ position. It does not list guard types, grips, seated or clinch states, variations or transients, and the
registry may add a family only by an owner-approved amendment (P-2). That does not exclude an eleventh id later,
for example through a T-1 promotion.

### 18.2 How stable ids are declared and validated

Facts **[CODE]**: every position-carrying shape already uses a **string** id: `BjjPositionContract.Command.position_id`,
`Roles.position_id`, `Transition.destination_position_id`, `transition_destinations()`, the A3b record's
`source_position_id`, the graph's `from_position_id` and `destination_position_id`. `BjjMountContract.POSITION_ID`
is a single constant reused by the gateway and graph. Nothing persists ids to disk yet (Guide save/load is
unchecked), but the Guide requires replays of resolved commands and save/load round trips that "preserve ... stable
IDs" (§58B.13), and A3b already documents that a JSON round trip turns ints into floats and is
rejected by design.

| Criterion | A. Godot integer enum | B. String constants only | C. Validated registry over string ids |
| --- | --- | --- | --- |
| Persistence and replay | Implicit values renumber if a member is inserted or reordered; a saved or replayed int silently changes meaning. JSON turns ints into floats | Stable if the string never changes | Same stability as B, plus a pinned id list so any change is a visible test diff |
| Fit with existing shapes | Changes every public shape above and the A3b schema (forbidden; breaks v1) | Matches today | Matches today; value of `mount` is unchanged |
| Readability of logs and events | Opaque numbers | Readable | Readable |
| Typo safety | Name-checked at parse time | None: a literal typo is a silent `undeclared` | Name-checked constants plus a runtime `is_declared` for external input |
| Unknown or out-of-range input | Any int is accepted unless separately range-checked | Any string accepted | Rejected with a stable code |
| Evolution | Append-only discipline is manual and easy to break | Ad hoc, scattered | One place; append-only enforced by a pinned-list test |
| Size of change | Large (breaks schemas) | None (already the status quo) | One small class |

Enum behavior was checked, not assumed, with a throwaway script in a scratch Godot project outside the repository
(deleted afterwards, never committed), run as `godot --headless --path <scratch> --script res://t.gd` on Godot
4.7.2. It declared `enum Position {STANDING, CLOSED_GUARD, MOUNT}` and a second enum with `OPEN_GUARD` inserted
before `CLOSED_GUARD`. Observed output:

```
implicit values: CLOSED_GUARD=1 MOUNT=2
after inserting a member: CLOSED_GUARD=2 MOUNT=3
out-of-range int accepted into enum-typed var: 99 keys=["STANDING", "CLOSED_GUARD", "MOUNT"]
json round-trip type of MOUNT: 3 is float=true value=2.0
```

So implicit values renumber on insertion, `99 as Position` is accepted into an enum-typed variable, and an enum
value that passed through `JSON.stringify` and `JSON.parse_string` came back as a float. It was not rerun in CI.

**[PROPOSAL] Recommendation: C, the smallest design that keeps replay and persistence safe.**

* **One class** (name provisional, `BjjPositionRegistry`): string constants for the ten ids, one declared list, and
  pure static functions: `is_declared(id)`, `error_for(id)` and a detached sorted `declared_ids()`. Two stable
  registry codes (proposed): `invalid_position_id` (missing, empty or ill-formed; format
  `^[a-z][a-z0-9]*(_[a-z0-9]+)*$`) and `unknown_position_id`. The existing codes are unchanged and keep their own
  meaning: `missing_position` and `unknown_position` (a `Command` addressed to the wrong contract) and the graph
  reason `unknown_source_position`; registry codes apply only to registry and start validation. No autoload, no
  resource files, no scanning or reflection (`POSITION_CONTRACT.md` already rejected auto-discovered registries),
  no mutable state.
* **The string is the persisted and replayed value.** An integer ordinal, if ever wanted for speed or arrays, is
  derived at run time from the sorted list and is never serialized.
* **Lifecycle:** append-only; an id is never renamed or reused; retirement is a tombstone, not a deletion (P-3).
  A test pins the exact id list so a change is deliberate. Unknown ids in a persisted record are rejected
  explicitly, never mapped to a default.
* **Migration is value-preserving:** `BjjMountContract.POSITION_ID` can later reference the registry constant with
  the identical value `"mount"`, so no record, event or test changes.
* **Not in the registry:** roles, control authority, actions, exits, edges, implementation flags, UI names.

### 18.3 Families versus variations (T-1 stays unresolved)

Guide §10 says to represent configurations as substates first and to promote one to a node only when human play
shows significantly different mechanics. **No classification below is approved;** the table records the Guide's
own default and what is unsettled.

| Candidate | Guide status | Guide §10 default (not adopted) | Unresolved |
| --- | --- | --- | --- |
| Technical Mount | §10 Mount substate (Low, High, Technical) | Variation of `mount` | T-1: the frozen Mount has no substate, so a variation inside Mount changes a frozen position; options (i)–(iii) in §7 are all still open |
| North-South | §10 Side Control substate | Variation of `side_control` | Whether its mechanics differ enough to promote |
| Knee-on-Belly | §10 Side Control substate; scored in §40.1 | Variation of `side_control` | Same; scoring is policy over events, not an edge |
| Butterfly | §10 Open Guard substate | Variation of `open_guard` | None beyond promotion criteria |
| Deep Half | Not in §10; §11.4 mentions "deeper half-guard entry later" | A later Half Guard entry or variation of `half_guard` | Whether it is a variation, an entry state or a family; the Guide does not say |
| Leg-entanglement variants (Ashi, 50/50, advanced entanglements) | §10 substates, "later advanced entanglements" | Variations of `leg_entanglement` | Which become nodes if their mechanics diverge |

The registry declares neither `technical_mount` as a family nor as a variation: T-1 options (i)–(iii) remain open,
and an append-only registry permits option (ii) later.

**[PROPOSAL]** The first registry declares **families only** (P-4). A variation is addressed later as
`(position_id, variation_id)` (§7), declared per family and reviewed with that family's rules. Declaring
variations now would freeze ids whose classification is open and would persist them before any engine can use
them. The A3b and graph shapes already carry only the family id, which stays valid.

### 18.4 Match-start contract

**[OWNER-CLARIFICATION]** Normal matches default to `standing`. **[PROPOSAL]** Contract:

1. **A start position is an explicit field of the match configuration**, owned by the graph owner or session
   layer, not by any position contract. Normal matches default to `"standing"`.
2. **Positional training or scenarios may request another declared start position** (for example `mount`),
   subject to rule 3.
3. **Validation order, all before any state is created.** The existing creation checks run first and are unchanged
   (`fighter_ids_error` → `invalid_fighter_id`, then `production_configuration_required`, then the match
   configuration errors). Then the start id: (a) an *omitted* start means the default `standing`, whereas an
   explicit empty or ill-formed id fails `invalid_position_id`; (b) an id that is not declared fails
   `unknown_position_id`; (c) no registered **fresh-start entry factory** (§18.6) fails
   `start_position_not_implemented`; (d) the entry parameters are validated by a pure validator before anything is
   constructed, or the factory is construct-or-fail with no partial state, failing `invalid_start_entry`.
   `invalid_position_id` and `unknown_position_id` are the registry codes of §18.2; only (c) and (d) are
   start-specific. Existing addressing codes (`missing_position`, `unknown_position`) and
   `unknown_source_position` are unchanged.
4. **No silent fallback.** An unavailable start fails explicitly. In particular, an unspecified start while
   `standing` has no factory fails with `start_position_not_implemented`; it never falls back to Mount or to any
   other position.
5. **Fresh start is not carry-over.** The A3b record is a detached export of a *source* segment and cannot start a
   match. A fresh start is built from the match configuration (fighter ids, stamina, clock, ruleset) plus the
   start position's own entry parameters.
6. **Standing begins without Mount-style assumptions:**

| Concept | Mount today **[CODE]** | Standing start (equal authority and sealed simultaneous choices: **[GUIDE-DIRECTION]** §15, §17 and §0A Choices; no top/bottom or authority: **[OWNER-CLARIFICATION]**; vocabulary **[OPEN]** P-8) |
| --- | --- | --- |
| Fighter identity | Two distinct ids from the owner | Same: two distinct ids, supplied once |
| Physical role | `top` / `bottom` | Not top/bottom. Role vocabulary is a Standing contract decision (P-8); neither fighter is advantaged by order |
| Control authority | Top, for the life of Mount | None: neutral, equal authority |
| Initiative | One holder, alternates | None: sealed simultaneous choices (§17). Today's `Roles` and `Command` cannot express this (C-12) |

7. **Identity, role, authority and initiative stay four distinct fields** (**[APPROVED]**, `POSITION_CONTRACT.md`).
   Fighter order in an id pair or log is a diagnostic ordering, never an advantage.
8. **Replay safety.** The effective start id (after defaulting) and the ruleset are recorded in the match header or
   the first graph event. A replay supplies the recorded id explicitly and never re-resolves the default, so a later
   change of the default cannot change the meaning of an old recording.

### 18.5 Current behavior versus intended behavior

| Aspect | Current implementation **[CODE]** | Intended **[OWNER-CLARIFICATION]** |
| --- | --- | --- |
| Positions constructible | Mount only (`BjjMatchWindowGateway.create`, `BjjPositionGraphMatch.create` take `(configuration, top_id, bottom_id)`) | Standing for normal matches; any registered fresh-start position for training or scenarios |
| Start parameter | None | An explicit start id, default `standing` (§18.4) |
| Registry | None; `"mount"` is a constant | One validated registry (§18.2) |
| Standing | Not implemented (not executable) | The normal-match entry engine |
| Mount's role | The only engine; also the only start | One position among ten; a legitimate training start |
| Exits | `Half Guard`, `Open Guard`, `Reversal` halt (Slice A) | Unchanged until destinations exist |

**[PROPOSAL] Interim policy (P-6):** keep the existing Mount-only constructors untouched as the explicit *Mount
scenario* path (every current test depends on them). Add a start-aware constructor later, with default `standing`;
until Standing has a fresh-start factory it fails explicitly rather than choosing Mount. `start="mount"` through the
new constructor must delegate to the existing Mount constructors, so there is never a second path to Mount. The
new constructor must not reuse `top_fighter_id`/`bottom_fighter_id` for Standing: it takes a neutral pair of
fighter ids, and any role assignment is part of the start's own entry parameters (P-12). This avoids a silent
change of default and avoids pretending Standing exists. C-9 records that the Mount-only construction is a
development artifact.

### 18.6 Registry, implementation roster and authority are three different things

| Artifact | Answers | Owner | Contents |
| --- | --- | --- | --- |
| **Registry** | "Is this a declared position family?" | The registry class | Ids only (§18.2) |
| **Implementation roster** | "Can this position be *started* or *entered*?" | One explicit, static table owned by the start-aware constructor (id → factory); a consistency test | Per id: a `fresh_start` factory and/or a `carryover_entry` factory |
| **Authority** | "What happens in the position and where can it go?" | Position contracts and engines (outcomes); the graph owner (commit) | Techniques, grades, exits, transitions |

Rules: the roster may only name registered ids (roster ⊆ registry, tested); a registry entry never implies a
roster entry; nothing in the registry or roster decides an outcome, an edge or a transition. **Mount is
`fresh_start` only today:** its factory builds fresh pools, meters, clock and D3-B, so "Mount is implemented" does
not mean "Mount can receive" (a `carryover_entry` for Mount does not exist). The first `carryover_entry` is the
Half Guard integration target; the first `fresh_start` for normal matches is Standing, which will also need a
`carryover_entry` because routes back to Standing exist (S3, P-11). The roster is a plain table: no
self-registration, no scanning, no mutable state (§18.2). (P-7)

### 18.7 Ordering and the minimum for a Standing-started match

**[APPROVED]** Half Guard stays the first receiving-position integration target (owner direction recorded in
`POSITION_GRAPH.md` §1, which also says "Standing and Closed Guard keep their §63 priority for the full graph";
Slice B, the Half Guard rules and oracle, is not approved and stays gated on Q1–Q8) unless the owner separately
changes that. **[OWNER-CLARIFICATION]** Standing is the future normal-match
entry engine. These are different axes, so they run as two tracks (§14, P-10): **receiving integration** (Half
Guard first) proves graph commit, carry-over entry and role maps; **entry engine** (Standing) proves the start
contract and neutral play. They meet at Half Guard: Guide §29's Single Leg SUCCESS lands in Top Half Guard, so
Half Guard's entry should accept a role map from a non-Mount source (a takedown assigns roles by outcome, unlike
D1's identity map for Mount). Standing's rules also need D6 treatment (a test-only Python oracle) before any
Godot port, exactly as Half Guard does.

Minimum needed before a match can begin from Standing, in tiers:

| Tier | What it delivers | Minimum contents |
| --- | --- | --- |
| **S0** | Start validation, no engine | Registry; start-position checks of §18.4; `standing` fails with `start_position_not_implemented` |
| **S1** | A match starts in Standing | Standing contract and `fresh_start` factory; neutral roles with no authority (P-8); sealed simultaneous choices (§17) representable, including who owns a simultaneous window (today's gateway is single-initiator, C-12); Standing's own stamina and commitment settlement (LOW/MEDIUM/HIGH, Guide §22) and clock, with no Mount policy (Rule 1/2, RECOVER, D3-B) applied automatically (D4); each item of the Guide's "Missing design/implementation" list for Standing (§11.1: control or balance axis, grip/entry substates, takedown result grades, simultaneous neutral choices, guard-pull resolution, mat returns, counter-wrestling) is either specified or explicitly deferred by owner decision, and mat returns belong to S3; a first action and response set (Guide §29, §63 Phase 3: Single Leg, Double Leg, Body Lock, Snapdown, Guard Pull; Sprawl, Whizzer, Pummel/Frame, Counter-shot, Guillotine threat; §11.1 also lists Disengage / Reset) with an explicit destination for every grade (§14), including how a remain-in-Standing result is expressed (P-9). Every takedown that lands in a position without a receiver halts under the existing Slice A semantics, so S1 is **not** a full match |
| **S2** | Takedown outcomes do not halt | Receivers for each destination the first exit map names. Guide §11.1 lists six besides Standing: `closed_guard`, `open_guard`, `half_guard`, `turtle`, `front_headlock`, `side_control`; a scramble transient (CONTESTED) must resolve into a real position (§30, T-11). The actual set follows P-9 |
| **S3** | A full match | All ten families reachable by legitimate transitions (§63 Phase 2 exit), routes back to Standing (re-entry, P-11), a ruleset and terminal layer (§40), mat-boundary and stalling policy (open) and the Guide §68 checklist; beyond A3c |

Exit-map policy for S1 **[OPEN] P-9:** (A) full exit maps with honest halts for unimplemented destinations
(recommended: it matches Slice A and D5, keeps Guide §14's "explicit destinations", and the halt frequency is a
measurable signal for which receiver to build next); (B) a restricted catalog whose techniques only reach
implemented receivers (fewer techniques, still explicit); (C) wait for the receivers (delays the entry engine).
No numbers or mechanics are decided here.

### 18.8 Impact on existing artifacts

* **A3b:** unchanged. `validate_segment` requires `source_position_id == "mount"` and `ROLES` of `top`/`bottom`, so a
  Standing source needs its own segment schema (T-9 extended): no top/bottom, and whether any D3-B state applies is open (T-7).
  A fresh Standing start produces no A3b record (§18.4 rule 5).
* **Graph coordinator:** `classify_exit_from` returns `unknown_source_position` for any source other than Mount,
  including declared ids; tests pin this for `half_guard`, `open_guard`, `side_control` and `standing` (C-10). A
  registry does not change it by itself.
* **Contract:** `Roles`/`Command` assume a single initiative holder and one submitting fighter (C-12). Standing
  needs an owner-approved way to express no initiative and simultaneous choices; none is designed here.
* **Topology catalog (§9.2):** its endpoint check ("a destination or technique id that does not resolve") needs
  the registry, which is why the registry precedes the catalog in §14.
* **Python and fixtures:** untouched; the frozen oracle has no registry and none is proposed.
