# BJJ Game — Engineering Roadmap & Overseer Ledger

**Audit date:** 2026-10-12 (living snapshot; update after each Claude handoff)  
**Roadmap revision:** 1.6 — record owner-directed three-slot blurry-memory learning queue, replacement choice and independent focus/recall constraints; no combat or progression implementation  
**Repository:** https://github.com/theaxlklo/BJJ-Game  
**Baseline audited:** `main` (`7aaf576e5fc01af4a5592dc544d632e9a3bf4fb1`) and draft PR #65 (`9942c5a53caf58d0d944bd7931ccc81bf86d0d07`), stacked on #63 (`650e7e1b9c6ba138a931c2805ce661e2268431b2`)  
**Decision authority:** The project owner approves new combat mechanics and any merge/integration. This document recommends; it does not change engine behavior or authorize a merge.

## Executive verdict

The deterministic Godot foundation is strong and the Mount→Half Guard graph is real, but the game cannot yet execute a complete scored match from Standing. Shift from engine polishing to **connected, human-playable matches**, without abandoning test coverage or frozen Python parity. Put integration discipline ahead of additional unbounded stacking.

**Observed repository facts:** 53 total PRs as of the B2a review: 16 merged (#1–#16), four closed CI probes without merge (#24–#27), 33 open. Thirty-one open PRs form the active sequential, SHA-checked Godot branch stack from #17 through #65 (with expected numbering gaps). #44 is an additional divergent Half Guard proposal. #64 is a separate **main-based** documentation-only oversight PR and is not in the gameplay stack. Compared with `main`, draft #65's head is 75 commits ahead, 0 behind, with 199 changed paths. Neither the 31 active-stack PRs nor #44 nor #64 is merged to `main`. Some early Godot PRs are not drafts, but their open state is not approval to merge.

**Functional evidence at the stacked tip:** typed Godot Mount parity and stamina/commitment systems, production-safe window gateway, PositionContract, graph, validated Mount→Half Guard transition, Half Guard independent oracle, preparation/feints/sealed-intent, F0 fighter read views, F1 interactive **Mount-only** 2D practice, B1e structural and exploratory match-flow harness. F1 has a scripted non-acting Bottom path and player-selected opposition responses; it is not a true computer opponent or cross-position match UI. B1e measured 2,534 games/74,490 windows, including 1,438 unsupported exits, 907 clock endings with no adjudication and 189 taps; the outcomes are scripted-policy evidence, **not** balanced player tests.

**Critical management risk:** CI tests and PR qualification measure the exact tested branches. They are not proof of playable game completion and not proof that `main` contains the work. PR #62 and PR #63 each had **21/21 successful exact-head jobs** (`cd87bf21` and `650e7e1`). B2a PR #65's doc-only exact-head workflow (`9942c5a`) concluded successfully: **4 successful jobs, 4 expected skipped jobs**. Draft PR #64, the independent oversight-doc branch, also has a successful exact-head workflow on `e15b7ee`. All these PRs remain unmerged.

## Visual roadmap

```mermaid
flowchart TD
  I[0. Audit and integration readiness] --> S[1. Side Control slice]
  S --> G[2. Open + Closed Guard slices]
  G --> ST[3. Standing / takedown start]
  ST --> LOOPS[4. Legal return routes + reversals]
  LOOPS --> RULES[5. Scoring + adjudication + custom stalling]
  RULES --> UI[6. Multi-position human UI + simple opponent]
  UI --> MVP{{Gate A: full match from Standing}}
  MVP --> DEPTH[7. Back, Turtle, Front Headlock, Leg Entanglement]
  MVP --> ENERGY[8. Heart of a Lion / REST / LOW / Momentum]
  DEPTH --> MEM[9. Memory, career, roguelike and richer 2D presentation]
  ENERGY --> MEM
```

This is **a dependency-oriented sequence, not a requirement to finish every position before scoring**. Adjacent tasks may overlap if the feature gates are separate and no shared engine state is mutated concurrently. In particular, the minimal zero-stamina safety path may need to move **before Gate A** if a playtest demonstrates a deadlock. The full BJJ ten-family graph remains a long-term scope target, not a condition for the first playable match.

## Position connectivity snapshot

```mermaid
flowchart LR
  M[Mount — implemented] -->|Elbow-Knee Success| H[Half Guard — implemented, opt-in]
  M -.->|Strong Elbow-Knee| OG[Open Guard — unimplemented]
  M -.->|Trap-and-Roll| R[Reversal — destination unresolved]
  H -.->|Knee Slice| SC[Side Control — unimplemented]
  H -.->|Recover Guard| OG
  H -.->|Recover Guard| CG[Closed Guard — unimplemented]
  ST[Standing — normal start intended, unimplemented] -.-> M
  ST -.-> H
```

Dotted connections are **not runnable** in the current graph; Standing arrows show future integration intent, **not approved transition mechanics**. Some additional possible edges exist in topology proposals and must not be mistaken for executable transitions.

## Ordered backlog with gates

| Priority | Work package | First artifacts / PR boundary | Exit gate and overseer evidence | Current status |
|---|---|---|---|---|
| P0 | **Integration-readiness checkpoint** | Inventory the 30-PR stack, independent #44, all exact heads, CI and dependent commits; explicitly plan safe bottom-up integration. | Owner-approved merge train, no silently changed bases or SHA, full composite CI; branch/PR reconciled with `main`. | **Needed**. No merges authorized. |
| P1 | **B2a Side Control spec** | [Draft #65](https://github.com/theaxlklo/BJJ-Game/pull/65): `GODOT_V1/docs/SIDE_CONTROL_V0_PROPOSAL.md` (346 lines); 3 actions and 3 responses per side, proposed grade tables, four proposed exits, Knee Slice receiver, R1–R12 risks and SC-D1–SC-D15. | Owner accepts or amends exact mechanics and architecture before any oracle is frozen. | **DOC-QUALIFIED; awaiting owner approval**. |
| P1.1 | **B2a.1 Position-aware initiative contract** | New documentation-only checkpoint stacked on qualified B2a #65. Compare current Mount/Half Guard windows against Side Control, Closed Guard, Open Guard and Standing needs; define first-window, ongoing-initiative and neutral simultaneous-choice semantics, with impact on personal turn accounting. | Report design alternatives and owner decisions, no code/fixture/default changes; preserve SC-D2 as open. | **NEXT · approved to investigate only**. |
| P2 | **Side Control executable** | **B2b** accepted canonical rules sheet and independent test-only Python oracle (checkpoint PR), **B2c** typed Godot engine, **B2d** source→destination keyed receiver/opt-in graph seam, **B2e** measurement (separate slices). | After owner approval: independent oracle prior to GDScript, negative-first and replay parity, real Knee Slice→Side entry, no leaked Half Guard protocol or Mount replay, honest unsupported exit halts. | **Blocked on SC-D1–SC-D15; not started**. |
| P3 | **Open Guard** | Spec/oracle/engine plus legal receiving routes from Mount and Half Guard. | Unblocked real exits; no illegal role/axis conversion or fabricated window. | Not started. |
| P4 | **Closed Guard** | Spec/oracle/engine receiving Half Guard recovery; deliberate guard initiative/defense and realistic return paths. | Legal entry/exit, rejection atomicity, replay. | Not started. |
| P5 | **Standing and takedown opening** | Fresh-start factory; takedowns, guard pulls, defenses, start roster, legitimate receiver paths. | A normal match can actually start Standing; Mount-only practice constructors still unchanged. | Architectural direction approved; mechanics absent. |
| P6 | **Return routes, reversals and graph traversal** | Side→Half/Mount, guard escapes/sweeps, role swaps, Mount re-entry D3-B rebase decision, unresolved Mount `Reversal`. | Multi-hop, cyclic deterministic trace; no duplicate score/stamina/clock settlement or repeated exhaustion token. | Open design/implementation. |
| P7 | **Scoring, 3s holds, time expiry and stalling** | Separate ruleset ledger and event interpreter; minimum positional scoring (takedown/sweep/pass/mount); custom 3-consecutive-inactive-personal-turn penalty; IBJJF-inspired penalty effects; winner/decision handling. | 5-minute (prototype) clock-end produces a lawful result rather than `timeout` with no adjudication; non-stalling defense and failed genuine efforts protected. | Game rules partly specified; code absent. |
| P8 | **Human multi-position play + baseline opponent** | Extend F1 to real graph traversal; choices for both physical roles, valid counters, sealed intents; separate deterministic rule-based opponent (no advanced AI); legible HUD. | One human can start Standing, choose legal actions, face an independently responding opponent, traverse ≥3 positions, and win/lose by legitimate tap/points/decision. | F1 Mount-only practice exists. |
| **Gate A** | **First complete playable match** | End-to-end human-in-loop acceptance transcript and regression suite. | No reachable unsupported exit in the supported match scenario menu; gameplay doesn't deadlock at zero stamina; playable on lightweight laptop; state/log determinism. | **Not reached**. |
| P9 | **Further graph breadth** | Back Control, Turtle, Front Headlock, Leg Entanglement, appropriate submissions and the remaining ten-family coverage. | All intended family nodes reachable through correct grappling transitions, no surprise fallthrough halts. | Not started. |
| P10 | **Distinctive tactical mechanics** | Heart of a Lion (once, mutual zero, 50%; five *personal* turns each; 100%), zero-stamina LOW memories, REST with 2-turn stalling allowance, Momentum with capped owner-approved modifier. | Exact normal-turn accounting, no infinite refills/extra windows, no double penalties, deterministic tests and per-ruleset opt-in. | **Design direction recorded in #63; not coded.** Bring essential anti-deadlock minimum forward to P8 if required. |
| P11 | **Game identity and campaign** | F0 expanded with belts/styles/loadouts; Memory Constellation and **three-slot blurry-memory learning queue**, clutch/never-forget, persistent belt career, three-win runs, rewards, injuries, 2D anime/arcade UI. | First complete short roguelike run changes player choices meaningfully; no unearned belt loss. | Mostly approved/open design, not engine. |

### Why this order

- **Side Control** is the highest-value near connection: B1e Population B recorded 910 Side Control blocked exits vs 353 Closed Guard and 155 Open Guard, under scripted test policies. This is *coverage evidence*, not real player play rates.
- **Standing** is mandatory before the project's North-Star complete-match gate. It can move ahead of Guard details if full-match implementation is otherwise blocked; preserving realistic legal receivers is the constraint.
- **Scoring and active play** should start as soon as enough connected positions are executable; not all ten positions must be built first.
- **The F1 UI** is not multi-position nor a real opponent; extend it only after the engine supports legal traversal. The controller must never force engine decisions.
- **The zero-stamina escape hatch** is a gameplay liveness concern; whether it can wait until after Gate A must be validated. Do not assume that every match can end without it.

## Latest engineering checkpoint — B2a qualified (2026-10-12)

- **Verified:** [PR #65](https://github.com/theaxlklo/BJJ-Game/pull/65), base `docs/match-incentives-heart-of-lion-spec` at `650e7e1b9c6ba138a931c2805ce661e2268431b2`, head `9942c5a53caf58d0d944bd7931ccc81bf86d0d07`. Exactly one new `GODOT_V1/docs/SIDE_CONTROL_V0_PROPOSAL.md`, 346 lines, one commit, no production behavior. Docs-only CI: 4 PASS / 4 SKIP. All unchanged engine functionality remains **unmerged**.
- **B2a deliverable:** identity-role proposal, Side Control local axis and initiative, 3 Top + 3 Bottom proposed actions, three responses per defending side, a grade matrix, setup/readiness/economy, four exits all **unsupported in v0**, a Half Guard Knee Slice→Side Control receiver contract, oracle plan, negative-first tests, 12 architectural risks, 15 owner decisions.
- **Primary architecture risks:** existing graph keys receivers only by destination, hard-codes Mount→Half Guard building and source reporting, uses 17+ nullable routing sites, exposes stale sealed-protocol/export fallthrough hazards, and has Mount-only retained-segment fingerprint tests. B2d must address these without changing default graph behavior or fabricating a return route. The B1e measurement file and digest remain frozen.
- **Recommendation (not authorization):** accept the compact v0 *scope* and tested approach first; review SC-D1–D15, especially first Side Control initiative (Top-first after Top's Knee Slice means consecutive **personal** decisions across positions) and the tentative raw grades/axis/entry thresholds. Treat all proposed combat numbers as provisional test baselines until measured. After owner sign-off, proceed **B2b docs+test-only Python oracle**, then **B2c standalone typed engine**, then **B2d graph/edge**, then **B2e measured population**.
- **Overseer action:** update `OVERSIGHT_LEDGER.md` with this evidence. Do not advance B2b, merge or retarget any PR without the relevant owner decision.

## New design checkpoint — B2a.1 position-aware initiative (owner direction, 2026-10-12)

The owner deliberately **declined to freeze** a universal initiative rule or the Top-first Side Control choice (SC-D2). Design must accommodate position-specific tactical rights:
- Side Control: Top may have priority because of pinning control; Bottom still has meaningful, initiated escape opportunities.
- Closed Guard: the Bottom can sometimes own initiative despite physical Bottom role.
- Open Guard and Standing: neutral exchanges may use genuinely simultaneous committed choices.
- Mount and Half Guard: preserve all existing implemented decision-window and role behavior; do not retrofit universal simultaneous choices.

Separate three dimensions: **positional control / authority**, **initiative ownership / eligibility**, and **decision-timing protocol** (sequential with response, or simultaneous sealed choices). Assess entrance initiative separately from ongoing initiative and from cross-position exchange fairness. Top-first after a Knee Slice would give that fighter consecutive **personal opportunities** across positions, even without a free clock/window; treat this as an **open game-balance decision** rather than a technical inevitability.

**B2a.1 deliverable:** one docs-only `GODOT_V1/docs/POSITION_AWARE_INITIATIVE_PROPOSAL.md` (name itself provisional), proposed state-machine/contract, position matrix and explicit compatibility/test plan covering actor eligibility, real simultaneous commitment secrecy, responder rights, `window_id` and simulated clock once per bounded exchange, and **per-fighter** completed-turn tracking for future 3-turn stalling and 5-turn-per-fighter Heart of a Lion. No executable engine/refactor, no proposed numeric buffs, no changes to #65, and no B2b authorization. Prefer conditional design variants to premature universal abstractions.

### Technical proficiency as a possible initiative modifier (owner idea; PROPOSAL ONLY, 2026-10-12)

The owner proposed adding a fighter **Technique proficiency stat** with **overlapping typical distributions by belt** (White, Blue, Purple, Brown, Black) and meaningful within-belt fighter variance. The idea is to let exceptional technical proficiency sometimes overcome a position's default opening initiative. This is not approval of values, dynamic turn theft or new fighter schema. Distinguish:

- **Belt** = progression/rank and a possible *distribution for initial proficiency*, never an automatic initiative win or a hard cap on later learning.
- **General technique proficiency** = fighter characteristic; **position-specific proficiency** = expertise in the relevant position; **individual memory mastery** = proficiency with a named move/variant. Avoid double counting one learned technique both as a priority modifier and a resolution/grade boost without explicit balance approval.
- **Position policy** = ordinary opening initiative and sequential-vs-simultaneous timing. **Technical differential** = possible *bounded exception* to that policy if one fighter's relevant proficiency greatly exceeds the other's. Control axis, authority, and legality of defenses remain separate; even a priority loss must not eliminate legal responses.
- **Determinism** = any within-belt variation is assigned reproducibly at fighter creation/career progression and stored in fighter state, never randomly rerolled during a decision window. Re-evaluate only at explicit match-owner boundaries. Avoid extra windows, time advances, repeated initiative theft, sealed-intent leaks or opportunity inflation.

**Illustrative candidate ranges only (NOT ACCEPTED, 0–100):** White 10–35, Blue 25–50, Purple 40–65, Brown 55–80, Black 70–95. These represent overlapping starting distributions, not the real BJJ belt system or proven game balance; exceptional positional specialists may differ substantially. An equally provisional Side Control +12 bias for Top is useful solely as a paper test of whether an opposing proficiency gap could reverse opening priority. Do not freeze any bonus, formula, threshold, range, tie rule, or simultaneous protocol from this example.

**B2a.1 proposal must evaluate:** how to represent general vs positional vs move-level skill without feature bloat; whether fighter definitions currently expose enough skill data; when skill may override *opening priority* vs ongoing turn eligibility; per-position policy table including neutral simultaneous entry; how belts and persistent career affect stable stats; no deadlock or passive runaway advantage; and a deterministic test matrix for equal ratings, adjacent belts, underdogs, high-skill Bottom in Side Control/Closed Guard, and low-technique Top in Open Guard. This is docs-only and does **not** expand the approved B2a.1 into implementation.

### Selectable positional training focus — role-specific fighter strategy (OWNER PROPOSAL, 2026-10-12)

The owner wants a player to **choose the positions they actively train**, instead of having every fighter improve equally everywhere. Example at White Belt: choose **two focus slots**, such as `mount/top` and `side_control/top`; as the persistent fighter wins, improves and advances belts, the number of available focuses may expand. **Two starting slots is the owner's example/provisional direction; no higher-belt slot ladder, XP rates, unlock schedule or numeric modifier has yet been decided.**

**Role-aware focus keys are essential:** `mount/top`, `mount/bottom`, `side_control/top`, `side_control/bottom`, `closed_guard/bottom`, `closed_guard/top` are distinct specializations. Neutral positions such as Standing require position-specific roles rather than fictitious top/bottom assignments. Track the stable family ID and that family's physical role vocabulary, not the fighter's identity, axis sign or control authority. Whether each pair consumes exactly one slot needs owner review.

**Proposed three-factor composition** (not three independent permanent bonuses to one outcome):
1. **General Technique**: baseline competence, potentially initialized from overlapping belt ranges with reproducible fighter variance; never use belt as a universal priority trump.
2. **Positional proficiency**: accumulated role-specific experience. Player-chosen **training focuses** accelerate growth or direct investment for their matching position/role; previously earned proficiency remains persistent when a focus changes.
3. **Individual memory mastery**: progress with a particular named technique/variant (blurry discovery → clarified/learned → mastered); focus may improve discovery/clarification and training, but it should not auto-grant mastery or block observation-based learning elsewhere. The Never Forget/clutch selection is a separate, limited overlay.

**Safeguards and progression questions:**
- **No legal move or defense locked solely for lack of focus.** Focus changes the fighter's preparation, growth and possibly familiarity, not the basic legality of positional survival. Non-focus techniques may still be learned or performed under the game's existing knowledge/belt gating.
- **No XP farming through pass/no-op/REST.** Growth events require legitimate accepted attempts, defenses, focused training or reviewed match/career rewards; failed legitimate effort can count while repeated meaningless spam should not.
- **No automatic promotion or automatic focus deletion.** The persistent fighter retains earned belt and historical positional proficiency across runs under existing career rules. The focus slot unlock path can be linked to promotion or specific milestone wins, but no exact threshold is chosen here.
- **Avoid triple dipping.** General Technique, relevant positional expertise and memory mastery must have clearly separated responsibilities (opening priority versus execution/grading versus learning speed), with bounded contributions and explicit balance tests; no hidden stat double-count or passive initiative monopoly.
- **Training selection is between matches or explicit career opportunities**, not a free priority rebalance mid-exchange. Determine how reassignment works, whether choices persist across matches, and whether unused training focuses are allowed.
- **Stable deterministic representation** when implemented: fighter ID, belt, general Technique, role-specific proficiency per stable position ID, active focus-slot list, unlocked slot count, and named move mastery; assign any variance once and persist it. Current F0/fighter snapshots are not claimed to support this model.
- **Sealed neutral decisions remain sealed.** Even an exceptional specialist doesn't get to see the opponent's committed technique before choosing, and all legal emergency defenses remain available.

**Design gate / tests for B2a.1:** Compare two White Belts with different 2-focus selections; Bottom Closed Guard specialist against high-general-Technique opponent; Top Side Control specialist against high-general-Technique Bottom escape specialist; identical belt/general Technique with different focus histories; a respec retaining earned proficiency; off-focus legitimate moves; fighter promotion unlocking an additional active focus; replay determinism across career load/save and matches. These are **test cases to specify**, not authorization to implement the underlying career or serialization system.

**Scheduling:** B2a.1 may define the *interfaces and meaning* of role-specific proficiency and show how future priorities use them, but **must not implement focus selection, memory XP, fighter data migrations, belt advancement or combat modification**. Implement selectable focuses when fighter identity/career/memory infrastructure is ready; do not make its full implementation a blocker for the next Side Control oracle. Until the subsystem exists, use explicit stable test inputs or a provisional fixed initiative rule approved by the owner.


**Gate:** project owner reviews B2a.1 and the Side Control SC-D2 choice together. Only then can B2b freeze a self-contained Side Control rules sheet and independent Python oracle. Any new 2-fighter simultaneous action protocol is a later independently qualified slice, not assumed to exist because Half Guard has a sealed feint/response protocol.

### Blurry memory learning queue — three unfinished techniques maximum (OWNER DIRECTION, 2026-10-12)

The user proposes an **exactly three-slot capacity for active blurry / unfinished technique memories** at a time. This is a constraint on **concurrent learning projects**, **not** the lifetime total of learned techniques, currently equipped match techniques, positional training focuses, or the limited `Never Forget` / clutch recall pool.

**Proposed state machine for later memory-system implementation:**

```text
Opponent uses a technique not yet learned
      │
      ├─ available blurry slot ──> add fuzzy observation to open slot
      │                              │
      │                         repetition / practice
      │                              │
      │                         learned / clarified ──> learned repertoire
      │                                                      │
      │                                                   free slot
      │
      └─ all 3 occupied ───────> prompt non-authoritative player choice:
                                  keep 3 current blur memories
                                  OR deliberately replace ONE with the new encounter
```

**Owner-defined principles:** at most three unresolved blurry memories concurrently; the player may **grind/practice until one becomes learned** (then its slot is freed) or **discard one and acquire a newly encountered technique**. A new encounter must **never automatically evict** an existing blurry memory. Reject or defer admission of a fourth active blurry record if no player replacement choice has been committed. Do not lose learned/mastered techniques when clearing a blurry slot. These mechanics do not narrow the future total memory/technique collection.

**Proposed interactions (not frozen implementation):**
- A White Belt's illustrative **two positional-focus slots** (`mount/top` etc.) are unrelated to the **three blurry-memory slots**; active positional focus may speed learning matching move memories but does not change the concurrency cap absent a later explicit rule.
- General `Technique`, role-specific positional proficiency and memory mastery have distinct effects. A blurred memory is **not fully learned**. Whether it can be attempted weakly or as a LOW-memory variant before clarity, and how near-learned techniques graduate into deeper mastery, require a separate rule gate.
- If the three slots are occupied and an opponent reveals a new move during a real exchange, record a deterministic `technique_observed` fact and offer a choice in safe UI flow; **do not add an unauthorized combat decision window, extra clock, automatic reveal of sealed intent or another action**. The player may continue with current memories without swapping.
- Store active slots in stable order with stable technique/variant IDs, deterministic clarity progress, optional pending encounter reference and explicit `keep` / `replace(slot_id)` selection. Replay/load must reproduce the same choices and queue. Treat distinct technique variants consistently, and do not count the same technique twice.
- No pass/REST spam or scripted opponent repetition should award unlimited mastery. Progress triggers and anti-farming policy require independent measurement; previously mastered / Never Forget techniques are not forcibly displaced by slot replacement.

**Open implementation decisions:** what exact events add clarity (observation, using an incomplete memory, practice, defeat/training), whether discarded partial clarity is fully lost or leaves a retrievable trace, what counts as `learned` versus `mastered`, whether pending observations expire, timing/UX for replacement prompts in five-minute matches, duplicate-variant semantics, career/run persistence boundaries, and whether the 3-slot cap ever upgrades. Do not fill missing numerical XP thresholds or game-balance rules without owner approval.

**Milestone placement:** include this in the **memory/career design** phase and in a later bounded memory learning specification, not the current B2a.1 initiative contract or B2b Side Control oracle. B2a.1 may reference how positional focus would accelerate memory progress, but it must not implement this queue or change initiative.

## Open PR inventory — status snapshot

**Merged foundation:** #1–#16 are merged on main (Python stamina, stalling groundwork, submission track, commitment, production policy, CI experiments).  
**Closed disposable probes:** #24–#27 are closed and not merged.  
**Active, continuous Godot integration stack (31 PRs, oldest to newest):**

| Layer | PRs | Delivered on stack (not necessarily on main) |
|---|---|---|
| Base parity / stamina / CI | [#17](https://github.com/theaxlklo/BJJ-Game/pull/17), [#18](https://github.com/theaxlklo/BJJ-Game/pull/18), [#22](https://github.com/theaxlklo/BJJ-Game/pull/22), [#23](https://github.com/theaxlklo/BJJ-Game/pull/23) | Mount Python comparison, typed stamina, settlement, targeted CI. |
| Mount lifecycle | [#28](https://github.com/theaxlklo/BJJ-Game/pull/28), [#29](https://github.com/theaxlklo/BJJ-Game/pull/29), [#30](https://github.com/theaxlklo/BJJ-Game/pull/30) | Hardening, advancement/RECOVER, D3-B and production lifecycle. |
| Contracts and first graph | [#39](https://github.com/theaxlklo/BJJ-Game/pull/39), [#41](https://github.com/theaxlklo/BJJ-Game/pull/41), [#42](https://github.com/theaxlklo/BJJ-Game/pull/42), [#43](https://github.com/theaxlklo/BJJ-Game/pull/43), [#45](https://github.com/theaxlklo/BJJ-Game/pull/45) | PositionContract, window gateway, graph rules, unsupported exits, classified outcomes. |
| Quality/architecture | [#46](https://github.com/theaxlklo/BJJ-Game/pull/46), [#47](https://github.com/theaxlklo/BJJ-Game/pull/47), [#48](https://github.com/theaxlklo/BJJ-Game/pull/48), [#49](https://github.com/theaxlklo/BJJ-Game/pull/49), [#50](https://github.com/theaxlklo/BJJ-Game/pull/50), [#51](https://github.com/theaxlklo/BJJ-Game/pull/51), [#52](https://github.com/theaxlklo/BJJ-Game/pull/52) | Agent workflow, settlement extraction, carryover, topology, frozen exit inventory, fail-closed CI, identity-only registry. |
| Fighter/player vertical prototype | [#53](https://github.com/theaxlklo/BJJ-Game/pull/53), [#54](https://github.com/theaxlklo/BJJ-Game/pull/54) | Fighter definitions and snapshots, Mount-only F1 interactive 2D scene. |
| Half Guard executable pipeline | [#55](https://github.com/theaxlklo/BJJ-Game/pull/55), [#56](https://github.com/theaxlklo/BJJ-Game/pull/56), [#57](https://github.com/theaxlklo/BJJ-Game/pull/57), [#58](https://github.com/theaxlklo/BJJ-Game/pull/58), [#59](https://github.com/theaxlklo/BJJ-Game/pull/59), [#60](https://github.com/theaxlklo/BJJ-Game/pull/60), [#61](https://github.com/theaxlklo/BJJ-Game/pull/61) | Rules, oracle, Mount→Half edge, graph receiver, sealed protocol, feints/fallback, connected sealed flow. |
| Evidence / owner rulebook | [#62](https://github.com/theaxlklo/BJJ-Game/pull/62), [#63](https://github.com/theaxlklo/BJJ-Game/pull/63) | Match diagnostics and separately documented future stalling/Momentum/Heart/LOW/REST. |

**Parallel divergence:** [#44](https://github.com/theaxlklo/BJJ-Game/pull/44) is a separate, open draft Half Guard proposal based on #43, NOT an ancestor of #63. Compared with #63, it is a three-commit divergent branch and needs explicit reconcile/close/retain review; never blindly merge it into the mainline. The current proposal #55 and rules #56 are the active successor lineage.

## Overseer's living dashboard specification

Maintain one canonical file on the integrated repo branch, e.g. `docs/project/OVERSIGHT_LEDGER.md`, updated **on every qualified slice**. This snapshot can initialize it but **do not** mark an unmerged PR as integrated.

| Field | Meaning | Current snapshot |
|---|---|---|
| `main_sha` | Integrated baseline | `7aaf576e5fc01af4a5592dc544d632e9a3bf4fb1` |
| `stack_tip` | Latest tested/observed development head | PR #63, `650e7e1` (21/21 exact-head CI; unmerged draft) |
| `connected_executable_families` | Real interconnected nodes on development tip | 2: Mount, Half Guard (latter opt-in) |
| `normal_start_standing` | Normal match can start Standing | NO |
| `run_to_result` | Full match with legal scoring/adjudication | NO |
| `human_control` | Human can control multi-position fight | Mount practice only |
| `opponent` | Autonomous opponent policy | No production opponent, only scripted practice/harness |
| `special_mechanics` | Momentum/Lion/REST/zero-LOW implemented | No, documented only |
| `open_merge_work` | Main-stack, divergent and oversight branches | 31-stack + independent #44 + independent docs #64 |
| `next_gate` | Near-term objective | B2a.1 initiative design checkpoint before SC-D1–SC-D15 approval and B2b |

For each new slice, record these fields **even if unchanged**:

```
Slice ID / short title:
Owner-approved scope and exclusions:
Base PR / base SHA:
Head PR / exact head SHA:
Implementation evidence (new executable behavior vs docs only):
Oracle and pinned tests / result:
CI at exact SHA (PASS / FAIL / PENDING / NOT RUN):
Blocked exits / new playable transitions:
Open owner design decisions (with explicit choices, not guesses):
Integrated to main? (NO / YES at SHA):
Player-visible result or screenshot/test session:
Next dependency and responsible agent:
```

**Board columns:** Ideas → Needs owner decision → Spec accepted → Implementing → Tests green at exact SHA → Integration review → Merged to `main` → Human-play verified. A proposal is not a mechanic, a green draft is not merged, and a merged mechanic is not automatically human-play validated. Establish GitHub milestones `Playable Multi-Position`, `Full Match From Standing`, `Ten-Position Graph`, `Roguelike Run` (titles are suggestions, not existing repo milestones).

**Progress measures, not vanity metrics:** number of usable graph families, count of real receivable exits, complete played matches without unsupported halts, reference replay mismatches, open unknown-owner decisions, number of pending unmerged PRs, number of user-input paths actually tested, unresolved UI/AI blockers. Maintain separate scores for structural correctness, game completeness and experience quality.

**Default checkpoint cadence:** update a one-screen project summary after each PR and compare against this baseline. At each milestone gate, run deterministic headless suite plus a **manual 2D interactive check** on the target laptop. No fabricated test times or green badges before evidence.

## Completed Claude assignment (B2a; archived task boundary)

B2a was executed by Claude as [draft PR #65](https://github.com/theaxlklo/BJJ-Game/pull/65), exact head `9942c5a53caf58d0d944bd7931ccc81bf86d0d07`, documentation only, GitHub exact-head workflow 4 PASS / 4 SKIP. The original scope below is retained as historical acceptance criteria, not as an instruction to rerun the task.

1. Verify `AGENTS.md`, all 30 mainline ancestor heads, independent #44, current CI on #63 and Godot code at exact SHA; do not change existing PR bases or merge anything.
2. Review `BjjPositionGraphMatch`, `PositionContract`, `HALF_GUARD_V0_RULES`, `POSITION_TOPOLOGY`, the B1e measurement and Side Control rules in Master Guide.
3. Draft `GODOT_V1/docs/SIDE_CONTROL_V0_PROPOSAL.md` with legal roles, separate axis, initiative, 3–5 meaningful actions per side, responses, setup/defense, fatigue policy, legal escape routes, a **real Half Guard Knee Slice→Side Control carryover**, validation of previous state's freeze, schema and independent Python test-only oracle plan. Label each as approved/demonstrated/proposed/open.
4. Include a boundary matrix for Half Guard entry, Side Control proposed exits, continuity of clock/stamina/latches/remainder, D3-B frozen controller, orientation and re-entry concerns. Do not create an automatic return into Mount.
5. Define negative tests for invalid label/id, stale window, wrong initiator, responder admission, terminal/halt, two independent replays, unsupported exits and receiver failure. Make the design testable in isolation, without extra action windows.
6. **Docs only, draft PR stacked on verified current #63**, with owner-review questions. No combat tuning, universal graph framework, new position code, scoring, stalling, Lion/REST/Momentum or UI in B2a. Stop for rule approval.

## Key owner decisions, deferred to the right gate

- **B2a.1:** investigate position-specific initiative and sequential versus simultaneous decisions; do **not** implement or preapprove Top-first Side Control, Bottom-first Closed Guard, or neutral simultaneous Open Guard. Show minimal safe extension without disturbing implemented windows.
- **B2a owner review (SC-D1–SC-D15):** Top/Bottom identities, first Side Control initiative, declared exits, action and defense set, local axis/grades/readiness, no-recovery economy, Half Guard snapshot edge, new opt-in graph constructor and oracle-vs-engine slicing. Draft #65 proposes values, none is frozen.
- **Return routes:** exact Mount Reversal landing and role swap; re-entry semantics for frozen Mount D3-B episode.
- **Ruleset:** how the game-specific third inactive *personal* turn earns repeat penalties and what meaningful activity means in each position. Keep official IBJJF 20-second rule separate.
- **Zero stamina:** REST recharge amount/timing and zero-stamina LOW technique grade/funding exception; the present LOW cost is 3, so both mechanics need code changes.
- **Lion:** integer rounding at 50%, deterministic personal-turn settlement including pass/D3-B/feints, precise ordering with end-of-match.
- **Momentum:** exact gain/consume/stack/grade impact. Feint secrecy and defender response must survive unchanged.
- **Match end:** pinned IBJJF edition, bout division/time and the game's deterministic adjudicator for tied scenarios.

## Non-negotiable engineering controls

1. Frozen Python oracle and historical evidence remain immutable unless an **explicitly authorized new ruleset** requires a separate oracle.
2. Typed Godot deterministic computation; no wall time, frame rate or hidden random rolls in game authority.
3. Match owner/position owner separation; positions determine rules and emit outcomes; graph validates/commits one destination; never let a UI invent transitions or windows.
4. Existing production config is opt-in; do not turn on experimental mechanics by accident.
5. One PR = one reviewable deliverable. Stop expanding the long stack without agreed integration cadence. Prefer reviewing/moving the ancestor chain bottom-up after owner authorization.
6. Exact-head CI plus meaningful scenario evidence; report what was **not** tested.
7. Respect F1's low-spec 2D-first requirement and the `AGENTS.md` project rule: human-play breadth over endless Mount tuning.

*This document is a planning baseline tracked in the repository documentation branch; publication does not merge, close or retarget any gameplay PR.*

## Living document workflow (established 2026-10-12)

The companion file [`OVERSIGHT_LEDGER.md`](OVERSIGHT_LEDGER.md) is the fast one-page overseer view. This longer roadmap is the architectural sequence, unchanged unless evidence changes dependencies or the owner approves a new rule. The first Claude assignment is archived as [`CLAUDE_B2A_HANDOFF.md`](CLAUDE_B2A_HANDOFF.md); Claude completed it in draft [#65](https://github.com/theaxlklo/BJJ-Game/pull/65). The next gate is **B2a.1 position-aware initiative review**, followed by owner review of SC-D1 through SC-D15, not permission to build Side Control. The #64 oversight documentation branch is kept independent of the gameplay stack.

**When the owner pastes Claude's next handoff:** cross-check its PR URL, exact SHA, changed files and CI claims against GitHub; add a timestamped immutable result entry to the ledger; update status/dependencies here, preserving old baseline evidence; identify proposal versus qualified code versus merged state; and produce one bounded next Claude prompt. Do not treat a claimed PASS as verified until independently checked. No background monitoring or automatic merge is implied.
