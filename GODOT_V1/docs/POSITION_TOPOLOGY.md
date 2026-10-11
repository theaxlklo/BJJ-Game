# Position topology and transition semantics (A3c — specification only)

**Status: specification and proposals. Nothing in this document is implemented, and nothing here
changes Mount, the graph owner, the A3b carry-over schema, Python, a fixture or a digest.** It adds no
executable position, no Mount exit, no catalog entry and no rule. It exists so that the three exit
labels the frozen Mount engine happens to emit today are not mistaken for the game's complete topology.

Tags used throughout (claims that could be mistaken for decisions carry one; quoted evidence and table facts
that are plainly sourced do not):

| Tag | Meaning |
| --- | --- |
| **[APPROVED]** | The Guide §0A freeze register, `POSITION_GRAPH.md` D1–D6 (**direction only**: numerical and mechanical rules are not accepted) and Slice A, and `POSITION_CONTRACT.md` |
| **[GUIDE-DIRECTION]** | Master Guide sections that state design intent (🔵) but are not in the §0A freeze register (for example §10, §11, §58B). This document aligns with them and does not treat them as binding |
| **[CODE]** | Verified in source at `577cec2` (A3b head). Source and tests are authoritative |
| **[PROPOSAL]** | Suggested here; non-binding until the owner approves it |
| **[OPEN]** | Needs an owner decision; no default is chosen here |

Depends on: `POSITION_GRAPH.md` (D1–D6, Slice A), `POSITION_CONTRACT.md`, `CARRYOVER_EXPORT.md` (A3b),
`WINDOW_GATEWAY.md`, Master Guide v10.4 §§0A, 7, 9, 10, 11, 12, 14, 15, 16, 17, 28, 30, 33, 40, 58B.5, 58B.6, 58B.12, 58B.13.

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

**[PROPOSAL]** A second Mount segment is a *new* segment built from carry-over, never the first gateway
resurrected. It needs a graph-owned segment index, continuing (never reused) window ids and one continuing
event log. Mount's D3-B record must not grant a second token on re-entry (the `POSITION_GRAPH.md` §6 risk).
Alternatives: (a) keep re-entry unsupported (current, recommended until a second position exists);
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
| Half Guard first; Open Guard declared-but-unimplemented at the unsupported boundary | §14 sequence keeps the Half Guard gate unchanged |
| Slice A halt semantics and `halted_at_unsupported_transition` | Unchanged; v1 halted exports stay valid as v1 (§10) |
| A3b schema, `destination_not_implemented` / `unresolved_destination` distinction | Unchanged; no file under `scripts/` or `tests/` touched |
| Frozen Mount, Python oracle, fixtures, digest | Untouched; any Mount extension is additive and separately approved (T-4) |

## 14. Smallest safe implementation sequence after A3c

**[PROPOSAL]** Each step is a separate, reviewable, explicitly authorized slice. None is started here.

1. **Owner decisions** T-1 to T-3 (family/variation vocabulary, catalog provenance, support-status vocabulary). Documentation only.
2. **"A3d" (proposed name; test-only): pin the producible-exit inventory.** Enumerate (technique x grade x band) through the
   existing catalog function and assert the producible set equals today's three labels. No production edit.
   This turns "the engine can emit exactly these" from a belief into a tested fact and makes any future Mount
   exit a visible, deliberate diff. Recommended next slice.
3. **Topology catalog data and validator** (conditional): only if the owner approves T-1 to T-3 *and* a second
   engine or other consumer exists to prove it, in line with `bjj-scope-plan` ("no generalized framework without
   proof from a second use case"). Pure and read-only, no executable edge, with the consistency checks of §9.2
   and negative-first tests. It may reasonably wait until after step 4.
4. **Half Guard rules and test-only oracle** (Slice B gate; Q1–Q8, D6), unchanged from `POSITION_GRAPH.md`.
5. **Receiver seams**, each additive and parity-tested, only after T-7: a verified latch-restoration method
   (existing public API per §11.1 option e, else a new factory), meter restore check, window-counter seed.
6. **Graph commit path and v2 carry-over**, with `transition_committed`, Mount→Half Guard.
7. Later: Open Guard, then the Reversal slice (needs the landing rule), then re-entry.

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

## 17. What A3c did and did not do

Added this specification and one-line pointers from `PORT_STATUS.md`, `POSITION_GRAPH.md`,
`POSITION_CONTRACT.md` and `CARRYOVER_EXPORT.md`. It changed no GDScript, no Python, no test, no workflow, no
fixture, no digest and no earlier PR. It created no executable position, receiver, catalog, grade, stamina,
D3-B, clock or policy rule, and it chose no Reversal landing.
