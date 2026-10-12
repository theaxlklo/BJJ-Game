# BJJ Game — Project Oversight Ledger

**Revision:** 1.9 · **Snapshot date:** 2026-10-12 · **State:** Living manual ledger, updated from actual Claude handoffs and verified GitHub evidence.

**Repository:** https://github.com/theaxlklo/BJJ-Game  
**Engineering roadmap:** [`ENGINEERING_ROADMAP.md`](ENGINEERING_ROADMAP.md) (canonical repository document)  
**Completed Claude handoff:** [`CLAUDE_B2A_HANDOFF.md`](CLAUDE_B2A_HANDOFF.md) (archived B2a scope; completed in [PR #65](https://github.com/theaxlklo/BJJ-Game/pull/65)). **Next gate:** B2a.1 position-aware initiative design, then owner review of Side Control SC-D1–SC-D15; B2b not yet authorized.

## One-screen overseer pulse

| Indicator | Observed value | Meaning |
|---|---|---|
| Stable integrated baseline | `main` @ `27599f28fa0e815693aa9d36aedb7aa14d573ac8` | **#17 merged**; actual-main Python+Godot post-merge CI PASS |
| Current active stack tip | Draft PR [#65](https://github.com/theaxlklo/BJJ-Game/pull/65) @ `9942c5a53caf58d0d944bd7931ccc81bf86d0d07` | Side Control **proposal only**, no new executable position |
| Exact-head CI | #65 **4 PASS / 4 expected SKIP**; #63 **21/21 PASS**; #62 **21/21 PASS**; oversight #64 workflow PASS | Exact heads; doc-only CI proves no gameplay behavior |
| Open work | 30 remaining sequential Godot PRs (#18→#65), divergent #44, independent oversight #64 | #17 integrated; #18 still on old predecessor branch; #44 and #64 still independent |
| Tip relative to `main` | 75 commits ahead, 0 behind; 199 changed paths | GitHub compare for PR #65's exact SHA |
| Executable connected positions on tip | **Mount -> Half Guard**, opt-in | No Side Control receiver |
| Player interface | **F1 Mount practice** | Not a full multi-position player-vs-opponent match |
| Complete match from Standing | **NO** | Standing, scoring, decisions and wider routes missing |
| Future custom mechanics | **Specification only** | Stalling, Momentum, Heart of a Lion, REST, zero-stamina LOW memories |

## Visual project traffic flow

```mermaid
flowchart LR
  P0["P0 · Integration review"] --> P1["B2a · Side Control spec QUALIFIED"]
  P1 --> D["SC-D1–D15 · owner decision"]
  D --> P2["B2b/c · Oracle + engine"]
  P2 --> G["Open / Closed Guard"]
  G --> ST["Standing + loops"]
  ST --> R["Scoring + stalling"]
  R --> UI["Human UI + simple opponent"]
  UI --> MVP{{"First complete match"}}
  MVP --> MORE["Other positions + distinct mechanics + career"]
```

Status legend: **Observed** means source or GitHub evidence reviewed. **Proposed** means awaiting owner approval. **Qualified** means CI passed at the exact SHA. **Merged** means the changes actually entered `main`. **Playable** requires manual acceptance evidence.

## Current work queue

| Track | Slice | State | Next owner-visible result |
|---|---|---|---|
| Stack safety | P0 — integrate Godot safely | **#17 integrated and verified** | Next: owner-authorized **#18 retarget to main + premerge simulation only**; no #18 merge approval |
| Gameplay breadth | B2a — Side Control rules/entry spec | **Doc-qualified #65, not approved** | SC-D2 Top-first explicitly remains open; don't freeze numbers | 
| Initiative design | B2a.1 — Position-aware and skill-sensitive contract | **Next, design investigation only** | Include role-specific selectable training focuses, belt Technique variance and move mastery without implementing career, focus selection, or initiative changes |
| Implementation | B2b+ — rules sheet, independent oracle, Godot, receiver | **Blocked on SC-D1–SC-D15** | B2b separate Python oracle; B2c engine; B2d real Knee Slice → Side Control; B2e measurement |
| Wider positions | Open/Closed Guard, Standing, reversals | **Planned** | Full legal graph traversal and start |
| Match completion | Scoring, adjudication, activity enforcement, basic opponent | **Planned** | Human plays a complete fight from Standing |
| Distinctive mechanics | Heart of a Lion, REST, LOW-at-zero, Momentum | **Approved concept, not implemented** | Separate rule gates and tests after core match, or earlier if liveness blocks play |

## Owner decision register

| ID | Question | Current decision / state |
|---|---|---|
| D-SC-01 | Side Control SC-D1–SC-D15: roles, first initiative, axis, catalog, grades, economy, exits, entry, opt-in and slicing | **Proposal delivered #65; all owner decisions remain OPEN** |
| D-INIT-01 | Position-aware initiative, especially SC-D2 first Side Control window | **B2a.1 docs investigation approved; no specific priority policy approved** |
| D-INIT-02 | Neutral simultaneous commitments in Open Guard/Standing and potential Bottom initiative in Closed Guard | **Proposed future capability; not implemented; requires secrecy, clock, ordering, personal-turn rules** |
| D-INIT-03 | Belt-banded Technique stat with within-belt variance and position-specific proficiency affecting opening priority | **New owner design idea, NOT APPROVED**. Investigate in B2a.1, keep control/authority/response and clock independent; initial ranges/override thresholds OPEN. |
| D-FOCUS-01 | Player-selected positional training focuses keyed by position family **and physical role**; White Belt begins with proposed 2 focuses (e.g. Mount Top and Side Control Top); more slots as fighter improves | **Owner design direction/provisional 2-slot example; NOT CODE-AUTHORIZED.** Decide exact slot ladder, focus switching, XP/learning rules and persistent storage later. Preserve off-focus move legality, earned belts and earned proficiency. |
| D-MEM-01 | Three concurrent **blurry/unfinished memory slots**; learn one to free a slot, or choose to discard one when discovering a new move | **Owner mechanic direction; NOT IMPLEMENTED.** No automatic eviction; three is a concurrent learning limit, not total techniques, training focuses or Never Forget count. Explicit opt-in replacement required. |
| D-MEM-02 | Percentage retained on discarding blurry memory; later rediscovery restores residual clarity | **Owner-approved concept:** discard frees slot but preserves **some percentage of current earned progress** in a dormant trace; it is not an active fourth memory. **OPEN:** numeric rate, rounding, repeated replacements, persistence and learned/mastered thresholds. |
| D-STACK-01 | Batch A #17→#18→#22; subsequent remaining stack and independent #44/#64 | **#17 merged and all post-merge gates PASS**. Next recommended step: explicitly authorize #18 PR-base retarget and read-only qualification; **#18 merge not authorized**. |
| D-STALL-01 | Game-specific stalling trigger | **Approved direction: third consecutive inactive personal turn**, independent by fighter |
| D-STALL-02 | Penalty repeat/reset cadence and full activity classifier | **Open**; IBJJF-inspired scoring consequences are proposed |
| D-LION-01 | Heart of a Lion | **Approved concept**: both exactly 0; once per match; 50%; five completed personal turns each; then 100% if active |
| D-REST-01 | REST recovery amount and timing | **Open** |
| D-LOW-01 | Funding/grade rule for eligible LOW memories at stamina 0 | **Open**; existing LOW normally costs 3 |
| D-MOM-01 | Momentum strength, trigger, cap, consumption | **Open** |
| D-RETURN-01 | Mount Reversal destination and Mount re-entry D3-B reconciliation | **Open**; do not assume landing |

## Verified handoff history

### E-000 — Baseline audit, 2026-10-12

- Audited [PR #62](https://github.com/theaxlklo/BJJ-Game/pull/62) and [PR #63](https://github.com/theaxlklo/BJJ-Game/pull/63), active Godot stack and parallel [#44](https://github.com/theaxlklo/BJJ-Game/pull/44).
- PR #62 match-flow diagnostics: **2,534 games**, **74,490 windows**, **73,606 CI-gated structural assertions**. Unsupported exits are *incomplete-engine boundaries*, not losses; qualitative population measurements do not prove balance.
- Corrected report typo: Half Guard exchanging-cell maximum no-progress streak **53**, not 788 (which counted feint attempts in a different table).
- #63 exact head `650e7e1b9c6ba138a931c2805ce661e2268431b2`: **21/21 CI jobs passed**. Remains **open draft**; no merge.
- Next handoff expected: **B2a specification**. No Side Control mechanics authorized until owner approves the proposal.

### E-001 — Claude B2a Side Control proposal, 2026-10-12

- **User-supplied Claude handoff independently verified:** [draft PR #65](https://github.com/theaxlklo/BJJ-Game/pull/65), base draft #63 branch `docs/match-incentives-heart-of-lion-spec` at `650e7e1b9c6ba138a931c2805ce661e2268431b2`; exact head `9942c5a53caf58d0d944bd7931ccc81bf86d0d07`. GitHub comparison: **1 commit ahead, 0 behind**, **one new Markdown file** (`GODOT_V1/docs/SIDE_CONTROL_V0_PROPOSAL.md`, 346 lines). No code or engine behavior changed.
- **Exact-head GitHub workflow `38297697211`:** 8 total jobs, **4 success** (CI gate, classify changes, lightweight validation, qualification results), **4 skipped** (Godot and Python paths). This qualifies a **documentation proposal only**. Claude reports local whitespace/link checks; those local commands were not independently re-executed here.
- **Proposal contents:** Side Control identity and Top/Bottom role map; own signed axis, authority, first-window initiative question; six proposed action IDs (3 Top/3 Bottom), three responses per side and two raw-grade matrices; new readiness and economy rules; four exit labels (Mount, Back Control, Half Guard, Turtle) **all halt in v0**; Half Guard Knee Slice→Side Control adapter, snapshot validator and segment-continuity plan; B2b oracle, B2c Godot engine, B2d opt-in graph, B2e measurement.
- **Design decisions:** SC-D1–SC-D15 in §11 of the proposal are **unapproved**. Architectural recommendation to owner: D1 preserve roles; D2 Top-first is consistent with positional authority but causes consecutive personal decisions after Top's pass (no free window); D10 pure Half Guard snapshot adapter; D12 explicit new opt-in with unchanged defaults; D15 independent Python oracle checkpoint before GDScript. All numeric grades, entry axis/threshold, tier and stamina rules are provisional; owner must approve test baseline before oracle, not treat oracle as a substitute for owner decisions.
- **Critical risks to test at B2d:** destination-only receiver could wrongly rebuild Half Guard from retained Mount; at least 17 nullable routing sites and hard-coded Mount transition origin; stale Half Guard sealed protocol; missing Half Guard frozen fingerprint; stale carry-over-export and terminal handling; source scans/CI pins need explicit, justified updates; earlier B1e populations must remain unchanged. No return route or Mount Reversal landing may be invented.
- **Agent provenance:** Claude reports the named repo-specific reviewer agents were not registered in its session; it used general-purpose read-only agents with repository definitions inlined. Their findings are reported, not independently reproduced by the reviewers in this oversight turn.
- **Independent oversight docs:** [draft PR #64](https://github.com/theaxlklo/BJJ-Game/pull/64) holds this ledger and roadmap on a separate main-based branch; exact-head workflow at `e15b7ee4d623ee5a36edfe41b5947a12d3adb93b` succeeded. Docs #64 and gameplay #65 remain **unmerged**.
- **Next action:** present compact owner decision matrix; **do not authorize B2b or change #65's text** absent owner approval. Then draft B2b rules-sheet + test-only Python oracle prompt; keep P0 bottom-up integration as a parallel read-only track.

### E-002 — Owner initiates B2a.1 position-aware initiative review, 2026-10-12

- **Source:** owner's game-design concern accepted as a **new documentation-only design checkpoint**. Side Control may favor the pinning Top; Closed Guard may give offensive initiative to Bottom; neutral Open Guard and Standing may offer simultaneous committed choices. This is a design investigation, **not approval of Top-first SC-D2**, any per-position authority rule, or a new engine protocol.
- **Reason:** a universal alternating-turn rule or a universally Top-first rule would misrepresent some positions. Cross-position Knee Slice already creates a known consecutive-initiative ambiguity; existing Mount/Half Guard behavior is frozen and must not be changed by this exploratory slice.
- **New gate:** B2a.1 docs-only contract and position matrix, separate positional authority, initiative eligibility, and decision-timing mechanism. Require analysis of one clock advance per global bounded exchange, sealed information, preserved response options, and **per-fighter** personal completed-turn accounting for future custom stalling and Heart of a Lion. Simultaneous protocols are **not currently supported by simply adopting Half Guard's sealed feint flow**.
- **Development sequence:** B2a doc-qualified #65 → **B2a.1 (next)** → owner approval of SC-D1–SC-D15 → B2b standalone oracle/rules sheet → B2c typed engine → B2d graph seam → B2e measurement. P0 integration audit continues independently.
- **Git authority:** no merges, refactors or modifications to the #65 gameplay-stack branch authorized. Oversight updates committed to the independent main-based draft [PR #64](https://github.com/theaxlklo/BJJ-Game/pull/64); its new exact-head CI needs verification and must not be presumed green.

### E-003 — Owner proposes technique-sensitive initiative and belt variation, 2026-10-12

- **Owner's question, not a frozen rule:** can default initiative favor the naturally advantaged fighter in a position, but be overridden by a sufficiently large fighter Technique proficiency difference? White/Blue/Purple/Brown/Black would have different, overlapping typical skill distributions with variability within each belt.
- **Provisional paper model only:** 0–100 initial skill ranges White 10–35, Blue 25–50, Purple 40–65, Brown 55–80, Black 70–95. Distinguish *general Technique*, position-specific knowledge and named memory mastery. A Side Control Top bias such as +12 is **just an example**; neither ranges nor positional bonus nor threshold nor calculation is approved.
- **Key architecture constraints:** belt never decides automatically; skilled Bottom may earn opening priority without becoming the physical Top or nullifying the Top's response. No additional turn, premature window, clock advancement, feint information leak or RNG on every exchange. If skill varies at fighter generation, the variation must be seeded/stored and reproducible. Do not equate priority with already present action-result exhaustion modifiers.
- **Scope decision:** add the proficiency-vs-positional-bias alternatives and deterministic test cases to the **existing B2a.1 docs-only initiative investigation**, not to B2b oracle or current gameplay. The owner still needs to approve the eventual formula, belt distributions and SC-D2 interaction. No PR #65 or engine file was changed by this entry.

### E-004 — Owner proposes player-selected positional training focuses, 2026-10-12

- **Owner game-design direction:** positional expertise develops according to the positions a fighter **chooses to train**, with growing focus capacity through wins and belt/career development. Illustrative White Belt start: **2 chosen position-and-role focuses** (`mount/top` and `side_control/top`); later belts/achievements may unlock more. Exact level gating, number of later slots and XP rates remain open. This direction complements—not replaces—the proposed belt-banded general Technique and named memory mastery.
- **Role-specificity matters:** `mount/top` and `mount/bottom` are separate expertise areas, as are `side_control/top` and `side_control/bottom`. Standing/neutral families require their real role semantics, never fabricated top/bottom.
- **Proposed integration:** active focus enhances rate/direction of positional skill growth and may improve practice/clarity of matching move memories; earned role-specific proficiency persists when training assignments change. General Technique supplies broad competence, focus influences specialist skill, and named move memory controls learned-technique mastery. Avoid stacking all three independently into repeated priority and grade bonuses.
- **Constraints:** off-focus positions and legal defense remain playable; true observation-based technique learning remains possible outside focuses; no pass/REST spam for XP; no in-match free reallocations, new decision windows or clock changes. Career persistence respects retained earned belts and mastered knowledge. The current Godot fighter foundation is not assumed to implement these mechanics.
- **Action:** include a small, deterministic design matrix and data/role-contract proposal within B2a.1. **No PR #65, engine, oracle, roster, persistence format or default behavior was edited.** Defer numeric slot ladder, per-action XP, assignment/respec economy and initiative override formula to owner approval and later implementation. Full focus/memory development must not hold up the Side Control oracle once a safe provisional initiative baseline is approved.

### E-005 — Owner caps blurry memory queue at three slots, 2026-10-12

- **Owner mechanic direction:** a fighter may hold **three active blurry/unfinished technique memories simultaneously**. A new technique encountered while full offers a deliberate decision: **keep** the three existing learning projects, or **discard one** to admit the new blurry memory. Continued practice/observation can bring a chosen blurry memory to **learned** status and free its slot. This does **not** limit the fighter's accumulated learned/mastered repertoire.
- **Distinct player-controlled resources:** the White Belt example of two selected *positional training focuses* (D-FOCUS-01) is independent of **three active blurry memories** (D-MEM-01); both differ from the future limited **Never Forget** / clutch selections. Specializing in a position might speed clarification of related memories but cannot silently add blurry slots.
- **Safeguards:** explicit confirmation before replacement; no automatic loss of learned memories, no fourth hidden blurry slot, no duplicate technique IDs, deterministic encounter and selection history; observation and selection must not create a new combat decision window, advance the match clock, expose a sealed feint or remove mandatory defenses. Protect progression from trivial repeat-action XP farming.
- **Open design:** whether dropping a blurry memory destroys its incomplete progress, when it reaches learned (vs mastered), how to practice, whether repeated observations while queue is full can be tracked, the exact player-choice UI timing, technique-variant granularity, persistence across runs, and whether slot capacity can ever increase. None of these was implicitly approved by the capacity rule.
- **Scope:** added to [Roadmap v1.6](ENGINEERING_ROADMAP.md) for a later memory/career implementation slice; B2a.1 remains a **documentation-only initiative investigation**, and B2b remains blocked pending Side Control rules approval. No gameplay branch, PR #65 or existing oracle was modified.

### E-006 — Owner preserves partial clarity when discarding a blurry memory, 2026-10-12

- **Owner decision:** when a fighter deliberately discards one of the three unfinished/blurry memory projects, they retain **a percentage of the progress earned so far**. This prevents an abandoned learning project from feeling entirely wasted. The slot becomes free for the newly observed technique; the abandoned progress becomes a **dormant residual trace**, not a fourth active blurry memory.
- **Rediscovery:** upon a later genuine encounter and voluntary re-admission into one of the three slots, the technique should restore its residual clarity instead of starting completely from zero. The original three-slot cap, consent before replacing a memory, and permanent separation from learned/mastered and Never Forget memories remain unchanged.
- **Illustration, not an accepted rate:** 60% learned × a hypothetical 50% retention = 30% dormant clarity. **The actual retention percentage has NOT been selected**; also open are integer rounding, whether specializations influence retention, prevention of repeated-discard exploits, re-discovery recognition, and career/run persistence.
- **Implementation gate:** later Memory Constellation/learning slice only, with deterministic stable technique IDs and replay/save tests. No combat engine, SC-D2 initiative, B2a.1 or Side Control oracle work was authorized or changed by this decision.

### E-007 — P0 audit closing message and Batch A preflight decision, 2026-10-12

- **Supplied Claude excerpt:** the read-only P0 audit has finished and proposed first integration Batch A = PRs #17, #18 and #22. Claude reports **no merges, pushes, retargets or other mutations**. Its full audit report was not reproduced in the latest pasted excerpt, so conclusions outside Batch A cannot be independently accepted on that basis.
- **Independently checked on GitHub:** [#17](https://github.com/theaxlklo/BJJ-Game/pull/17) `1de58ef97c4a0a4342f6a80a36c352926620be6e` → [#18](https://github.com/theaxlklo/BJJ-Game/pull/18) `9c4166cef43d367786bbb24b76bccef6624779ba` → [#22](https://github.com/theaxlklo/BJJ-Game/pull/22) `83d2eb9d4d5f29249f1954ebf7b6b82661bac982`; each open, non-draft, mergeable, correctly stacked and historical exact-head workflows successful. GitHub submitted review list for each returned no reviews. PR #17 is directly based on main `7aaf576e5fc01af4a5592dc544d632e9a3bf4fb1`; subsequent bases match direct predecessor heads.
- **Merge-method recommendation:** repository reports merge commits, squash merges and rebase merges enabled. Prefer the **merge-commit** method to retain stacked ancestry, but confirm branch policies, bot rules and expected diff changes at each step. A green source PR does not demonstrate CI success on a new integration commit.
- **Decision:** approve Batch A as the **first integration candidate and read-only preflight scope**, not a blanket three-PR merge approval. Preflight should report exact current heads, branch protection, simulator/merge-tree or read-only diff, required CI and rollback; stop for the project owner's separate explicit merge authorization before changing `main`, PR bases or history. After a single authorized merge, check cumulative CI on the actual main SHA before permitting the next.
- **Scope frozen:** B2a.1, Side Control B2b+, #44 and oversight #64 must not be swept into this batch. Existing Python oracle, frozen fixtures, Godot parity and production opt-in must remain unchanged.
- **Next task:** Claude returns an actionable first-step premerge gate report, then owner selects go/no-go for #17. Keep `main` stable until approved.

### E-008 — PR #17 pre-merge qualified, engineering GO recommended, 2026-10-12

- **Claude report (local proof, not rerun by oversight):** clean isolated scratch merge of #17 `1de58ef97c4a0a4342f6a80a36c352926620be6e` into `main` `7aaf576e5fc01af4a5592dc544d632e9a3bf4fb1`; expected tree `3c91f43da03fd08af86a950351c26a023284af58`. Godot 4.7.2 headless import and Mount slice 40 assertions PASS; independent Python fixture 4,140 actions + 300 drifts; Godot-v-Python 92,939 comparisons; digest match; PYTHONHASHSEED 0/1/12345 reproducibility; 3D smoke, semantic checker, legacy entry point, PG8 history, and 516 Python 3.14.7 unit tests PASS. Claude reports no Git ref or remote mutations. These checks were **not independently executed** here.
- **Independently verified GitHub:** [PR #17](https://github.com/theaxlklo/BJJ-Game/pull/17) remains open non-draft, mergeable, with 1 commit/5 changed paths (only `.github/workflows/godot-v1.yml`, `GODOT_V1/.gitignore`, `GODOT_V1/docs/PORT_STATUS.md`, reference generator/test); base `main` at `7aaf576e5fc01af4a5592dc544d632e9a3bf4fb1`, exact head unchanged `1de58ef97c4a0a4342f6a80a36c352926620be6e`; both PR/push exact-head workflows completed successfully. GitHub reports merge-commit strategy enabled. Branch protection/review policy assessment is from Claude, not separately verified in this oversight action.
- **Known weaknesses:** the old Mount parity checker may incorrectly accept an empty fixture or an omitted expected field; local preflight deliberately inspected nonzero 4,140/300/92,939 counts and CI regenerates the fixture. The old aggregate CI gate does **not** include the independent Godot job. Track explicit count pins after the appropriate later PR, never retroactively alter frozen evidence.
- **Engineering verdict:** **GO for #17 using a merge commit once the project owner expressly authorizes the actual mainline operation**. The user supplied a GO report but has **not supplied an explicit merge instruction**. No merge, retarget, push or main mutation was executed by oversight. This is not approval for #18, #22, #44 or #64.
- **Post-merge strict gates:** verify current head/base again; resulting `main` tree exactly `3c91f43da03fd08af86a950351c26a023284af58`, #17 head ancestor, new `main` push workflow and separate Godot workflow on the *actual new main SHA* successful and not cancelled, Godot counts unchanged (40 assertions, 4,140 actions, 300 drifts, 92,939 checks). On changed SHAs/red/missing/cancelled/mismatched checks: stop, no retarget, no next merge, report discrepancy and recovery path. After complete PASS ask separately before changing #18's base.

### E-009 — PR #17 successfully integrated; post-merge CI verified, 2026-10-12

- **Claude's OVERSIGHT HANDOFF:** owner-authorized merge commit for [PR #17](https://github.com/theaxlklo/BJJ-Game/pull/17) using exact-head guard `1de58ef97c4a0a4342f6a80a36c352926620be6e`. New `main` `27599f28fa0e815693aa9d36aedb7aa14d573ac8`, with original predecessor `7aaf576e5fc01af4a5592dc544d632e9a3bf4fb1`. Claude reports correct expected tree `3c91f43da03fd08af86a950351c26a023284af58` and #17 head as ancestor; no other merge, retarget, push or deletion.
- **Independently verified GitHub:** #17 `merged=true`, `state=closed`, `merge_commit_sha=27599f28...`, with exact #17 head unchanged. `main` is exactly the reported merge SHA, based on commit comparison. Python workflow [38313261406](https://github.com/theaxlklo/BJJ-Game/actions/runs/38313261406) has 18 SUCCESS and one expected docs-only SKIPPED, including both Python versions' unit shards and `CI gate`. Godot workflow [38313261503](https://github.com/theaxlklo/BJJ-Game/actions/runs/38313261503) has a successful `godot-v1` job; its downloaded job log **independently confirms** 40 Mount assertions, 4,140 reference actions, 300 drifts and 92,939 cross-language parity checks. Claude reports both were non-cancelled `main` push runs with no deviations.
- **Verification limit:** the connector exposed the merged commit but not its complete tree object for an independent hash comparison; the exact tree equality and scratch clone cleanliness remain **Claude-reported**, not re-executed here. Godot's independent CI is still not part of old Python aggregate gate, and the old parity checker requires explicit count scrutiny.
- **Remaining stack:** 30 open sequential Godot PRs #18→#65; divergent #44 and independent docs/ledger #64 remain outside that stack. #18 unchanged head `9c4166cef43d367786bbb24b76bccef6624779ba`, based on `feat/godot-v1-reference-parity` (the original #17 head). Comparing #18 to actual `main` shows six commits ahead, one behind (the merge commit), 18 intended paths. #22 unchanged at `83d2eb9d4d5f29249f1954ebf7b6b82661bac982`. No reason to rebase or change head.
- **Next recommended owner authorization:** allow **retargeting PR #18 base to `main` only**, keeping its head unchanged, then have Claude qualify a simulated merge into actual `main` (CI/determinism/fixture counts, policy, no unexpected diff) and stop for a separate GO/NO-GO decision. **#18 merge, #22 retarget/merge and all further mainline writes are NOT approved by this entry.**

## Standard Claude-result ingestion form

For each result the owner pastes here, append a new `E-###` entry, checking at least:

```
Date / claimed slice:
PR URL / PR number / draft?
Base branch and SHA:
Head branch and exact SHA:
Changed files and implementation-vs-spec boundary:
Local checks and exact-head CI jobs:
Replay/parity/negative tests (actually observed):
New playable abilities (if any):
Unimplemented destinations or blocked behaviors:
Owner decisions needed:
Deviation from roadmap and why:
Merge state (not merely PR green):
Next narrow Claude prompt / acceptance gate:
```

**Operating agreement:** Updates are performed **during the conversation when new results are supplied**—not in the background. Each update should include revised downloads and the next bounded Claude prompt. Do not retroactively rewrite earlier evidence; add an entry and amend the current summary. Ask for owner approval before changing mechanics or merging the PR stack.
**Canonical upkeep:** Keep this file and [`ENGINEERING_ROADMAP.md`](ENGINEERING_ROADMAP.md) in version control. After each owner-supplied Claude handoff, verify PRs/CI, append a dated `E-###` evidence entry, and commit an update through the ordinary review process. No automatic or background updates are implied.
