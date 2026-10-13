# Position-aware initiative contract (B2a.1) — proposal

**Status: documentation only. No engine, test, fixture or gameplay change; Mount and Half Guard behavior is untouched.**
Tags: **[OWNER-DIRECTION]** already agreed by the owner, formalized here, not reopened · **[OBSERVED]** verified in the code or documents at `main` · **[PROPOSAL]** a design or number awaiting owner approval · **[OPEN]** an owner decision · **[OWNER-APPROVED]** an explicit owner decision, recorded with its date.
Nothing tagged PROPOSAL or OPEN is a rule until the owner approves it. The name of this file is provisional.

**Revision 2 (2026-10-13):** the owner approved OD-2 Option B: General Technique (`G`) and position-role proficiency (`R`) are **separate**, and a new career fighter starts at `R = 0` (§8.0). Only that baseline is approved; every scale, weight, edge and XP-related number stays provisional, and §8.3–§9 were recomputed accordingly.

**Revision 3 (2026-10-13):** §11 and OD-9 were reconciled with `MATCH_INCENTIVES_HEART_OF_A_LION.md` (an earlier draft had invented a personal-turn definition and conflated two counters; §11.1 now separates the inactive-turn event from the Heart-of-a-Lion counted-turn event and §11.2 lists the open questions without answering them). The §9 calculator's percentage formatting is now pure-integer; every table and quoted percentage is unchanged.

## 1. What is already decided (and is not reopened)

**[OWNER-DIRECTION]** Initiative at the start of a position combines three things:

1. **General Technique proficiency**: a fighter characteristic. Belt influences its starting distribution, but distributions overlap and individuals vary.
2. **Position-and-role proficiency**: expertise in *this* position in *this* role (`side_control/bottom`, `closed_guard/bottom`, ...), earned (a new career fighter starts at `R = 0`, never derived from `G`) and accelerated by the player's selected training focuses.
3. **The tactical advantage of the current position**: the position's own opening priority.

A sufficiently skilled or specialized fighter may overcome the normal positional opening priority. Side Control ordinarily favors Top. Closed Guard may favor Bottom. Genuinely neutral positions keep simultaneous sealed choices. **Mount and Half Guard keep their implemented behavior until the owner explicitly authorizes a change.** Individual **Memory Mastery** stays separate from general initiative priority so nothing is counted twice.

Consequence for SC-D2 (`SIDE_CONTROL_V0_PROPOSAL.md` §6.4): "Top first or Bottom first" stops being a binary choice. Side Control becomes a *biased* position whose favored role is Top, and a large enough skill gap can reverse the opening. With no fighter skill data yet, the contract reduces to "the favored role opens" (§8.6), so B2b can proceed without waiting for the career system.

## 2. What exists today **[OBSERVED]**

| Fact | Where |
|---|---|
| Mount `initiator` defaults to `"top"`; it flips after every accepted non-exit exchange; an exit leaves it unchanged | `mount_exchange.gd`; `POSITION_GRAPH.md` §4 (D2) |
| Half Guard: the Top opens at entry; strict alternation; a pass flips; an exit does not | `HALF_GUARD_V0_RULES.md` §4, §5.4, §6 |
| A transition grants **no** window, time or initiative to either fighter (D2); the receiving position decides its own first window | `POSITION_GRAPH.md` §4 |
| Four separate fields: identity, physical role, control authority, initiative (`Roles.initiative_id`) | `POSITION_CONTRACT.md` |
| Guide §15: initiative is *triggered*, not permanently owned; the controlling Top ordinarily acts first in established top positions; a Guard Bottom with a valid opening can initiate; the non-initiator always gets a legal response phase; equal authority uses §17 sealed simultaneous choices | Master Guide §15, §17 |
| Mount has a free-initiative mechanism (`free_initiative_pending`, `free_initiative_beneficiary`, `consume_free_window`); nothing generates free windows yet | `mount_match.gd` |
| Half Guard counts initiations per **role** (`top_initiation_count`, `bottom_initiation_count`) | `HALF_GUARD_V0_RULES.md` |
| `BjjFighterDefinition` has only `definition_id` and `display_name`. **No proficiency, belt or focus data exists.** | `fighter_definition.gd`, `F0_FIGHTER_FOUNDATION.md` |
| Half Guard's sealed protocol is **asymmetric** (the attacker seals, the defender answers from a public view). **No symmetric simultaneous protocol exists.** | `TACTICAL_PREPARATION_AND_FEINTS.md` §7, `HALF_GUARD_V0_ENGINE.md` |
| Ten declared position ids: `back_control`, `closed_guard`, `front_headlock`, `half_guard`, `leg_entanglement`, `mount`, `open_guard`, `side_control`, `standing`, `turtle` | `position_registry.gd` |

## 3. Separate the concerns

**[PROPOSAL]** Seven things that must never be inferred from one another:

| Concept | Meaning | Owner of the value |
|---|---|---|
| Fighter identity | Stable id for the whole match | match owner |
| Physical role | Position-local role name | position |
| Control authority | Side of the position's signed axis | position |
| **Initiative** | Who holds the current window | position, per its policy |
| **Timing protocol** | Sequential with response, or simultaneous sealed | position policy |
| **Proficiency inputs** | General and position-role skill, frozen for the match | match owner (from fighter data) |
| Memory mastery | Proficiency with a named technique | fighter data; **never an initiative input** |

Why: physical elevation, axis sign and a temporary right to act answer different questions. Collapsing them is what makes "Bottom has initiative" or "Top lost control but still opens" impossible to express.

## 4. The contract **[PROPOSAL]**

### 4.1 Policy kinds (declared once per position, static)

| Kind | Opening rule | Skill inputs used? |
|---|---|---|
| `LEGACY_FIXED` | A declared role opens, then strict alternation: today's Mount and Half Guard | **No** |
| `BIASED_SEQUENTIAL` | A declared *favored role* opens unless the other fighter's skill advantage exceeds the position's edge; then strict alternation | Yes |
| `NEUTRAL_SIMULTANEOUS` | Nobody opens; both fighters seal a choice before reveal (§6) | **No**: skill never changes the protocol |

A policy is `{position_id, kind, favored_role, legacy_role, edge}`; unused fields are empty.

### 4.2 Decision function (pure, integers only, no clock, no randomness)

```text
score(fighter, position, role) = general[fighter] + role_proficiency[fighter][position, role]     # separate integers, provisional scale 0..100 each; R is 0 for a new fighter and is never derived from G

decide_opening(policy, role_map, inputs, entry_adjust = 0):
    LEGACY_FIXED:          opener = role_map[policy.legacy_role]                  reason legacy_fixed
    NEUTRAL_SIMULTANEOUS:  opener = none                                           reason neutral_simultaneous
    BIASED_SEQUENTIAL:
        fav, oth   = role_map[policy.favored_role], the other fighter
        margin     = score(oth, ..., oth's role) - score(fav, ..., favored role)
        edge_now   = policy.edge - entry_adjust                                    # entry_adjust >= 0, default 0 (§8.7)
        opener     = oth if margin > edge_now else fav                             # strict ">": a tie keeps the favored role
        reason     = skill_override | favored_holds | favored_holds_tie
```

Why integers and a strict comparison: a float or an "either order" tie-break would let two platforms disagree on one opening, which breaks replay. Why no division: dividing a weighted average introduces rounding rules; comparing the raw sums needs none.

### 4.3 When it is evaluated

- **Exactly once per position entry** (including the match's first position). Never inside a window, never when a window closes, never at a timer.
- After the opener, **existing strict alternation continues** (a non-exit exchange flips the initiator; an exit does not). Skill therefore decides *who gets the first window*, not who owns the position. This cannot create a monopoly, a deadlock or extra turns.
- Inputs are a **frozen snapshot taken at match creation** and passed in immutably. A position never reads career data, and career changes (promotion, respec, new focus) take effect at the next match. Replays and saves reproduce the same opening because the recorded inputs, not live fighter data, drive it.
- A **missing input is a refusal with zero mutation** (`missing_proficiency`); no position silently invents a default. Until fighter data exists, the match owner supplies an explicit provisional profile (§8.6).
- The result is one detached event, `initiative_decided`: `position_id, kind, opener_id, favored_id, scores by fighter id, edge, effective_edge, margin, overridden, reason`. A replay verifier recomputes it from the recorded inputs and must match byte for byte.
- It grants **no window, no clock change and no charge**: it names who opens the next window the position would open anyway (D2 stays true).

### 4.4 Alternatives considered

| Variant | Description | Verdict |
|---|---|---|
| **V1 (this proposal)** | Skill contest at entry only | Simple, deterministic, cannot snowball |
| V2 | Re-contest at every window | Repeated initiative theft, passive runaway advantage, much harder to test. **Deferred**; revisit only with measured evidence |
| V3 | Skill changes the timing protocol (neutral becomes sequential) | Contradicts the owner direction that neutral positions keep simultaneous choices. **Rejected** |

## 5. Who may use which stat (no double counting) **[PROPOSAL]**

| Quantity | Opening priority | Execution / grade | Learning speed |
|---|---|---|---|
| General Technique | **Yes** | No (v0) | No |
| Position-role proficiency | **Yes** | No (v0) | Focus accelerates growth of this stat |
| Memory mastery (named technique) | **No** | Existing/future memory rules decide | Its own progress |
| Belt | Only as the starting distribution of General Technique; never a trump | No | No |

`R` is earned only: raising `G` or earning a belt never raises `R`, and a focus change never lowers it. Using General Technique or position proficiency to change grades, costs or legality needs its own owner approval and a balance test. A test must assert that `decide_opening` accepts no mastery input.

## 6. Timing protocols

### 6.1 Sequential with response **[OBSERVED, unchanged]**

The initiator chooses an action and commitment; the responder always has a legal response; one `window_id`; the simulated clock advances once per bounded exchange. Half Guard's asymmetric sealed variant stays Half Guard's.

### 6.2 Simultaneous sealed **[PROPOSAL, not implemented; its own future slice]**

Requirements, taken from Guide §17 and the existing information discipline:

- Both fighters commit before either choice is visible; the second commit reveals nothing about the first (public views stay redacted until reveal).
- **One** `window_id`, **one** clock advance and one history exchange per resolved pair.
- Resolution is a deterministic function of the pair (Guide §18 action tags), independent of which fighter sealed first or of fighter-id order.
- Each commit is admitted or refused atomically; a refusal leaves everything byte-identical.
- A missed real-world deadline uses a deterministic, published fallback per fighter; it never reveals the other commit.

```text
OPEN ──seal A──> A_SEALED ──seal B──> RESOLVING ──atomic reveal+resolve──> CLOSED
  └─seal B──> B_SEALED ──seal A──┘            (A and B are symmetric; order must not change the outcome)
CLOSED ──position rule──> stays NEUTRAL_SIMULTANEOUS
                      └─> triggered initiative: SEQUENTIAL with a named initiator (position-declared trigger, Guide §15/§17)
```

## 7. Position matrix **[PROPOSAL]**

Policy kinds are *placeholders until each position's own rules sheet is accepted*. Only the Mount and Half Guard rows describe current behavior.

| Position | Implemented | Proposed kind | Favored role | Playtest candidate edge (unapproved) | Notes |
|---|---|---|---|---|---|
| `mount` | Yes | `LEGACY_FIXED` | `top` opens | n/a | Preserved exactly; `initiator` default `top`, strict alternation |
| `half_guard` | Yes (opt-in) | `LEGACY_FIXED` | `top` opens at entry | n/a | Preserved exactly |
| `side_control` | Proposal only | `BIASED_SEQUENTIAL` | `top` (pin) | **25** (§8.5; bracket 20–30) | Resolves SC-D2 as a consequence, not a freeze; Bottom keeps real initiated escapes from the alternation |
| `closed_guard` | No | `BIASED_SEQUENTIAL` | `bottom` ("may favor Bottom") | 15 (bracket 10–20) | Triggered openings (Guide example: Bottom Triangle Ready) are position-local rules |
| `back_control` | No | `BIASED_SEQUENTIAL` | the back attacker | 40 (bracket 30–50) | Role vocabulary differs from top/bottom; per its sheet |
| `standing` | No | `NEUTRAL_SIMULTANEOUS` | none | n/a | Skill does not alter the protocol |
| `open_guard` | No | `NEUTRAL_SIMULTANEOUS` | none | n/a | Owner review at its rules sheet; a transient setup may trigger sequential initiative |
| `turtle`, `front_headlock`, `leg_entanglement` | No | **[OPEN]** | — | — | No proposal; decide at each rules sheet |

## 8. Numbers proposed for owner approval **[PROPOSAL; none is accepted unless marked OWNER-APPROVED]**

### 8.0 Approved baseline: General Technique and position-role proficiency are separate **[OWNER-APPROVED 2026-10-13, OD-2 Option B]**

- **`G` (General Technique)** is broad technical competence, influenced by belt with overlapping distributions and individual variation.
- **`R` (position-role proficiency)** is *earned* expertise for one position in one role (`side_control/bottom`, `closed_guard/bottom`, ...).
- **A new career fighter starts with `R = 0` for every position-role, whatever their `G`.** `R` is never set equal to `G`, and it does not rise automatically when `G` improves or a belt is earned.
- **Training focuses accelerate earning `R`.** Earned `R` persists when focus assignments change.
- **Unfocused fighters keep legal attacks, escapes and essential defenses** under the existing technique-knowledge rules: `R` influences only the opening-priority contest here, never legality.
- **Memory Mastery stays separate** and is not automatically an initiative modifier.

This approves the separate baseline only. It does **not** approve any scale, weight, edge, XP rate, fighter-schema change or career mechanic. Everything below that is a number stays **provisional**.

### 8.1 Scale and composition **[PROPOSAL]**

- `G` and `R` are integers; the provisional scale is `0..100` each. `score = G + R`, weights `1:1`, the simplest choice.
- The **edge** is in the same score units as `G` and `R`, so an untrained matchup (`R = 0` for both) is decided by the `G` gap against the edge, and a trained matchup adds the `R` gap.
- A different weight is the same as rescaling `R` and the edges together, so no edge is meaningful without `R`'s cap and growth pace (§8.8). The edges below are only as good as those two unknowns.
- `G` uses the owner's **illustrative** belt ranges (uniform integers; **not accepted**, not the real belt system): White 10–35, Blue 25–50, Purple 40–65, Brown 55–80, Black 70–95. The `R` levels used in the examples (20 light, 40 solid, 60 specialist, 80 elite) are labels for the calculation, **not** XP rates or a progression design.

### 8.2 How the position's opening advantage interacts with `G` and `R` **[PROPOSAL]**

The position hands its **favored role** a head start: the favored fighter opens unless the other fighter beats them by **more than the edge** (`(G + R)` of the other minus `(G + R)` of the favored, using each fighter's own role in this position). Read it as three layers:

1. **The position** supplies the edge. A favored fighter needs no skill to open, and two untrained equals always give the opening to the favored role.
2. **`G` is a shared currency.** It counts in every position, so a higher belt can reverse a position's priority by itself, but belt distributions overlap and the edge makes a small gap meaningless.
3. **`R` is the specific, earned currency.** It counts only in the position-role it was earned in, so training the *right* position can overcome a gap in belt, and a high-belt fighter who never trained this role has no head start in it.

`G` alone, `R` alone or both together can clear the edge; none is required. **Because `R` starts at 0 for everyone, early-career openings are decided by the position and the belt gap, and the earned `R` of a trained player is what later makes a position-aware opening.** The opening grants nothing else: no extra window, clock, charge or response right, and it is evaluated once per entry (§4.3).

### 8.3 Exact-enumeration evidence **[PROPOSAL; illustrative inputs]**

Each cell is the exact probability that the **non-favored** fighter opens (strict `>`; a tie keeps the favored role), over every integer `G` pair in the belt ranges. Where a single number is shown for a fighter, that is the stated `R` level.

**Table 1: both fighters untrained (`R = 0`).** Belt gap only.

| Other fighter vs favored-role fighter; edge → | 10 | 15 | 20 | 25 | 30 | 40 | 50 | 60 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| same belt | 0.178 | 0.081 | 0.022 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| other is 1 belt higher | 0.658 | 0.481 | 0.311 | 0.178 | 0.081 | 0.000 | 0.000 | 0.000 |
| other is 2 belts higher | 0.969 | 0.902 | 0.799 | 0.658 | 0.481 | 0.178 | 0.022 | 0.000 |
| other is 3 belts higher | 1.000 | 1.000 | 0.999 | 0.969 | 0.902 | 0.658 | 0.311 | 0.081 |
| other is 4 belts higher | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.969 | 0.799 | 0.481 |
| other is 1 belt **lower** | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

**Table 2: same belt (`G` random inside the range), different positional training.**

| Favored R / other R; edge → | 10 | 15 | 20 | 25 | 30 | 40 | 50 | 60 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| favored R=0 / other R=0 | 0.178 | 0.081 | 0.022 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| favored R=0 / other R=20 | 0.799 | 0.658 | 0.481 | 0.311 | 0.178 | 0.022 | 0.000 | 0.000 |
| favored R=0 / other R=40 | 1.000 | 0.999 | 0.969 | 0.902 | 0.799 | 0.481 | 0.178 | 0.022 |
| favored R=0 / other R=60 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.969 | 0.799 | 0.481 |
| favored R=0 / other R=80 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.969 |
| favored R=40 / other R=0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| favored R=40 / other R=20 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| favored R=40 / other R=40 | 0.178 | 0.081 | 0.022 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| favored R=40 / other R=60 | 0.799 | 0.658 | 0.481 | 0.311 | 0.178 | 0.022 | 0.000 | 0.000 |
| favored R=40 / other R=80 | 1.000 | 0.999 | 0.969 | 0.902 | 0.799 | 0.481 | 0.178 | 0.022 |

**Table 3: a specialized lower belt against an inexperienced higher belt.**

| Case; edge → | 10 | 15 | 20 | 25 | 30 | 40 | 50 | 60 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| White other R=40 vs Blue favored R=0 | 0.902 | 0.799 | 0.658 | 0.481 | 0.311 | 0.081 | 0.000 | 0.000 |
| White other R=60 vs Blue favored R=0 | 1.000 | 1.000 | 0.999 | 0.969 | 0.902 | 0.658 | 0.311 | 0.081 |
| White other R=80 vs Blue favored R=0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.999 | 0.902 | 0.658 |
| White other R=40 vs Purple favored R=0 | 0.481 | 0.311 | 0.178 | 0.081 | 0.022 | 0.000 | 0.000 | 0.000 |
| White other R=60 vs Purple favored R=0 | 0.969 | 0.902 | 0.799 | 0.658 | 0.481 | 0.178 | 0.022 | 0.000 |
| White other R=80 vs Purple favored R=0 | 1.000 | 1.000 | 1.000 | 0.999 | 0.969 | 0.799 | 0.481 | 0.178 |
| White **favored** R=40 vs Blue other R=0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| White **favored** R=60 vs Blue other R=0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| White **favored** R=80 vs Blue other R=0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

**Table 4: two Black Belts with equal General Technique (`G = 82`), different positional expertise.** Deterministic: the margin is exactly `R_other − R_favored`.

| Margin; edge → | 10 | 15 | 20 | 25 | 30 | 40 | 50 | 60 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| R_other − R_favored = 0 | favored | favored | favored | favored | favored | favored | favored | favored |
| R_other − R_favored = 10 | favored | favored | favored | favored | favored | favored | favored | favored |
| R_other − R_favored = 20 | **other** | **other** | favored | favored | favored | favored | favored | favored |
| R_other − R_favored = 25 | **other** | **other** | **other** | favored | favored | favored | favored | favored |
| R_other − R_favored = 26 | **other** | **other** | **other** | **other** | favored | favored | favored | favored |
| R_other − R_favored = 30 | **other** | **other** | **other** | **other** | favored | favored | favored | favored |
| R_other − R_favored = 40 | **other** | **other** | **other** | **other** | **other** | favored | favored | favored |
| R_other − R_favored = 41 | **other** | **other** | **other** | **other** | **other** | **other** | favored | favored |
| R_other − R_favored = 50 | **other** | **other** | **other** | **other** | **other** | **other** | favored | favored |
| R_other − R_favored = 60 | **other** | **other** | **other** | **other** | **other** | **other** | **other** | favored |
| R_other − R_favored = 80 | **other** | **other** | **other** | **other** | **other** | **other** | **other** | **other** |

### 8.4 Worked examples (read from the tables)

1. **White Belt vs Blue Belt, no positional experience** (Table 1). If the Blue Belt is the non-favored fighter, the White Belt's position priority is reversed 31.1% of the time at edge 20, 17.8% at 25, 8.1% at 30 and never at 40. If the *White* Belt is the non-favored one, the reversal is **0.000** at every edge: a lower belt with no experience never takes a higher belt's position.
2. **Two White Belts with different histories** (Table 2). With no training on either side, only `G` noise reverses the opening (2% at edge 20, 0% from 25). If the other White Belt has light training (`R = 20`) it reverses 31.1% of the time at edge 25 and 17.8% at 30; with solid training (`R = 40`) 90.2% and 79.9%. If the favored White Belt is *also* trained (`R = 40`), an `R = 40` challenger is back to noise level, and a challenger needs `R = 60` to reverse it 31.1% of the time at edge 25. Training on the favored side protects the pin.
3. **A specialized lower belt vs an inexperienced higher belt** (Table 3). A White Belt specialist (`R = 60`) takes the opening from an untrained Blue Belt 96.9% of the time at edge 25 and 65.8% at 40; an elite specialist (`R = 80`) 99.9% at edge 40. Against an untrained *Purple* Belt the specialist needs `R = 60` to win 65.8% at edge 25. The reverse (White favored specialist against an untrained Blue Belt) is never reversed. Specialization can beat belt, but only in the role it was earned in.
4. **Two Black Belts with equal `G`** (Table 4). Equal `G` cancels, so the winner is decided by the `R` gap alone: with edge 25 the other fighter needs a gap of **26** or more (25 is a tie and the favored role keeps it); with edge 40, **41**.
5. **A fighter changing focus without losing proficiency** (Table 5). Moving a focus slot away from `side_control/bottom` leaves the earned `R` untouched, and a belt promotion that raises `G` leaves `R` untouched too.

**Table 5: focus change and promotion (illustrative values; edge 25; opponent is an untrained Blue Belt, `G = 37`, `R = 0`, Top in Side Control).**

| Step | G | R[`side_control/bottom`] | Score | Opponent score | Margin | Opener (edge 25) |
|---|---:|---:|---:|---:|---:|---|
| Trained `side_control/bottom` (R=45); focus = `side_control/bottom` + `mount/top` | 22 | 45 | 67 | 37 | +30 | **fighter (override)** |
| Focus changed to `closed_guard/bottom` + `mount/top`; earned R unchanged | 22 | 45 | 67 | 37 | +30 | **fighter (override)** |
| Promoted: General Technique 22 → 37; R unchanged | 37 | 45 | 82 | 37 | +45 | **fighter (override)** |

### 8.5 Reassessing the candidate thresholds **[PROPOSAL; not approved]**

The earlier candidates (Side Control 40, Closed Guard 24, Back Control 60) assumed `R = G`, which doubled every skill gap. Halving them (20 / 12 / 30) reproduces the *untrained* behavior exactly, but the new baseline changes what a threshold means for **trained** fighters: the edge is now directly the `R` gap a specialist must earn. So the table below compares a **range of smaller thresholds** instead of one halving.

| Candidate edge → | 10 | 12 | 15 | 20 | 25 | 30 | 40 | 50 | 60 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| same belt, both untrained (G noise only) | 0.178 | 0.135 | 0.081 | 0.022 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| other 1 belt higher, both untrained | 0.658 | 0.592 | 0.481 | 0.311 | 0.178 | 0.081 | 0.000 | 0.000 | 0.000 |
| other 2 belts higher, both untrained | 0.969 | 0.947 | 0.902 | 0.799 | 0.658 | 0.481 | 0.178 | 0.022 | 0.000 |
| same belt, other R=20 (light training) | 0.799 | 0.747 | 0.658 | 0.481 | 0.311 | 0.178 | 0.022 | 0.000 | 0.000 |
| same belt, other R=40 (solid training) | 1.000 | 1.000 | 0.999 | 0.969 | 0.902 | 0.799 | 0.481 | 0.178 | 0.022 |
| White other R=60 vs Blue favored R=0 | 1.000 | 1.000 | 1.000 | 0.999 | 0.969 | 0.902 | 0.658 | 0.311 | 0.081 |
| R gap needed at equal G (edge + 1) | 11 | 13 | 16 | 21 | 26 | 31 | 41 | 51 | 61 |

What to read from it:

- **Same-belt untrained noise** should be small, or the position's priority means nothing between equals: ≤ 2% from edge 20, 0% from 25.
- **Adjacent-belt untrained reversal** is the cost of letting `G` alone override a position: 31% at 20, 18% at 25, 8% at 30, 0% at 40.
- **Training should clearly matter:** light training (`R = 20`) reverses 48% at edge 20, 31% at 25; solid training (`R = 40`) 97% at 20, 90% at 25, 80% at 30, 48% at 40.
- **The `R` gap needed at equal `G` is `edge + 1`**, so an edge is also a statement about how long a specialist must train: it is only meaningful against `R`'s cap and growth pace, which are not decided (§8.8).

| Position | Earlier candidate | Straight halving | **Recommended playtest value** | Bracket worth testing | Why |
|---|---|---|---|---|---|
| `side_control` (Top favored) | 40 | 20 | **25** | 20–30 | Equal fighters keep the pin (0% noise); adjacent-belt reversal 18% (not 31%); light training matters (31%); solid training clearly overcomes it (90%) |
| `closed_guard` (Bottom "may" be favored) | 24 | 12 | **15** | 10–20 | A deliberately mild bias: some noise (8%) and a real belt effect (48% adjacent), with light training already favoring the challenger (66%) |
| `back_control` (attacker favored) | 60 | 30 | **40** | 30–50 | A strong pin: no noise, no adjacent-belt reversal (0%), two belts needed (18%), solid training only 48% so real specialization is required |

These are starting points for the playtest/measurement plan in §12, **not** balance truth and **not** approved. If the owner changes `R`'s cap, the weights or the belt ranges, every edge must be recomputed with the script in §9.

### 8.6 Before fighter data exists, and existing experienced fighters **[PROPOSAL]**

- **Before any fighter proficiency data exists**, the match owner passes an explicit, recorded provisional profile. Any profile that is **identical for both fighters** (for example `G = 50`, `R = 0`) gives margin 0, so every `BIASED_SEQUENTIAL` position opens for its favored role. For Side Control that is the Top-opens behavior in `SIDE_CONTROL_V0_PROPOSAL.md`, recorded as a consequence of the placeholder profile, not a frozen rule. Tests for B2b use explicit stable inputs.
- **A new career fighter is `R = 0` everywhere.** A fighter who is *not* new (an experienced opponent, a boss, a saved fighter from before this system) would also read as `R = 0`, which wrongly makes a Black Belt look positionally untrained. Such fighters will eventually need an **explicitly defined starting proficiency or training history** (authored per fighter, or a documented history that earned it). It must **not** be derived silently from `G`, and this proposal does not design or implement a roster or opponent generator (OD-12).

### 8.7 Entry tempo adjustment **[OPEN, default 0]**

After a Knee Slice the passing fighter produced the exit and, if favored, also opens Side Control: consecutive personal opportunities across two positions, with no free window or clock. Rather than choose a side, the contract carries `entry_adjust` (default **0**) that lowers the favored role's edge when the favored fighter produced the entry transition. A value is decided only after the measurement plan in §12 shows whether it matters. OD-8.

### 8.8 Remaining numerical questions **[OPEN]**

1. **`R` cap and scale** (`0..100`?) and whether an elite specialist (`R = 80..100`) may outweigh several belts of `G`. At edge 25, a White Belt with `R = 100` takes the opening from an untrained Black Belt in 90.2% of the cases (average margin +40.0); whether specialization should be able to outrank belt that far is a design question.
2. **`R` growth pace** (XP per accepted exchange, focus acceleration, diminishing returns, anti-farming). Not decided; edges depend on it.
3. **Weights** between `G` and `R` (`1:1` is provisional).
4. **Edges** per position (§8.5) and whether they vary by belt or division.
5. **`G` belt distributions** and within-belt variance (illustrative here).
6. **Starting profile for existing experienced fighters** (§8.6, OD-12).
7. **`entry_adjust`** (§8.7).

## 9. Method and reproducibility

All tables above are produced by the script below with no randomness and no floating-point arithmetic: every integer `G` pair in the belt ranges is enumerated, the strict comparison `(G_other + R_other) − (G_favored + R_favored) > edge` is evaluated, and the count is rounded to three decimals and formatted with integer arithmetic only (no float is ever formed). Run it with `python3 -I`. It was run from this document to produce the tables, and a fresh run reproduces them exactly.

```python
"""B2a.1 sensitivity, exact and deterministic (integers only; no random numbers, no floats).
score = G + R. G is uniform over the owner's ILLUSTRATIVE belt range; R is an explicit illustrative
earned-expertise level (0 for a new career fighter). The non-favored fighter opens iff
score_other - score_favored > edge (strict), otherwise the favored role opens."""
BELTS = {'White': (10, 35), 'Blue': (25, 50), 'Purple': (40, 65), 'Brown': (55, 80), 'Black': (70, 95)}
EDGES = (10, 15, 20, 25, 30, 40, 50, 60)
CANDIDATES = (10, 12, 15, 20, 25, 30, 40, 50, 60)

def pct(hit, tot):                      # pure-integer rounding to 0.001 (half up); no float is ever formed
    thousandths = (2000 * hit + tot) // (2 * tot)
    return f"{thousandths // 1000}.{thousandths % 1000:03d}"

def p_override(fav, other, edge):
    """fav/other = (belt_or_fixed_G, R). Returns (hits, total) over all integer G pairs."""
    def gs(x):
        return range(BELTS[x][0], BELTS[x][1] + 1) if isinstance(x, str) else (x,)
    hit = tot = 0
    for gf in gs(fav[0]):
        for go in gs(other[0]):
            tot += 1
            hit += (go + other[1]) - (gf + fav[1]) > edge
    return hit, tot

def row(fav, other):
    return ' '.join(f'{pct(*p_override(fav, other, e)):>6}' for e in EDGES)

def header(first):
    return f'{first:<44}' + ' '.join(f'{e:>6}' for e in EDGES)

if __name__ == '__main__':
    print('TABLE 1  both untrained (R=0); P(non-favored fighter opens); edge in score units')
    print(header('other fighter vs favored-role fighter'))
    for label, fav, oth in [('same belt', 'White', 'White'), ('other is 1 belt higher', 'White', 'Blue'),
                            ('other is 2 belts higher', 'White', 'Purple'), ('other is 3 belts higher', 'White', 'Brown'),
                            ('other is 4 belts higher', 'White', 'Black'), ('other is 1 belt LOWER', 'Blue', 'White')]:
        print(f'{label:<44}' + row((fav, 0), (oth, 0)))
    print('\nTABLE 2  same belt (G random in range); R_fav / R_other illustrative earned expertise')
    print(header('favored R / other R'))
    for rf, ro in [(0, 0), (0, 20), (0, 40), (0, 60), (0, 80), (40, 0), (40, 20), (40, 40), (40, 60), (40, 80)]:
        print(f'{f"favored R={rf} / other R={ro}":<44}' + row(('White', rf), ('White', ro)))
    print('\nTABLE 3  specialist vs inexperienced higher belt (illustrative R)')
    print(header('case'))
    for r in (40, 60, 80):
        print(f'{f"White other R={r} vs Blue favored R=0":<44}' + row(('Blue', 0), ('White', r)))
    for r in (40, 60, 80):
        print(f'{f"White other R={r} vs Purple favored R=0":<44}' + row(('Purple', 0), ('White', r)))
    for r in (40, 60, 80):
        print(f'{f"White FAVORED R={r} vs Blue other R=0":<44}' + row(('White', r), ('Blue', 0)))
    print('\nTABLE 3b  threshold comparison (all untrained unless stated; P = non-favored fighter opens)')
    print(f'{"candidate edge (score units)":<44}' + ' '.join(f'{e:>6}' for e in CANDIDATES))
    for label, fav, oth in [('same belt, both untrained (G noise only)', ('White', 0), ('White', 0)),
                            ('other 1 belt higher, both untrained', ('White', 0), ('Blue', 0)),
                            ('other 2 belts higher, both untrained', ('White', 0), ('Purple', 0)),
                            ('same belt, other R=20 (light training)', ('White', 0), ('White', 20)),
                            ('same belt, other R=40 (solid training)', ('White', 0), ('White', 40)),
                            ('White R=60 other vs Blue favored R=0', ('Blue', 0), ('White', 60))]:
        print(f'{label:<44}' + ' '.join(f'{pct(*p_override(fav, oth, e)):>6}' for e in CANDIDATES))
    print(f'{"R gap needed at equal G (edge + 1)":<44}' + ' '.join(f'{e + 1:>6}' for e in CANDIDATES))
    print('\nTABLE 4  two Black Belts, equal G = 82 (fixed); margin = R_other - R_favored (deterministic)')
    print(header('R_other - R_favored'))
    for d in (0, 10, 20, 25, 26, 30, 40, 50, 60, 80):
        print(f'{d:<44}' + ' '.join(f'{"OTHER" if (82 + d) - 82 > e else "fav":>6}' for e in EDGES))

    print('\nTABLE 5  focus change keeps earned R; promotion changes G only (illustrative values, edge 25)')
    opponent_g, edge = 37, 25             # untrained Blue-ish Top (favored in Side Control), R = 0
    steps = [('trained sc/bottom; focus = sc/bottom + mount/top', 22, 45), ('focus changed to cg/bottom + mount/top', 22, 45),
             ('promoted: General Technique 22 -> 37', 37, 45)]
    for label, g, r in steps:
        margin = (g + r) - (opponent_g + 0)
        print(f'{label:<52} G={g:>2} R[sc/bottom]={r:>2} margin={margin:>3} -> {"fighter opens (override)" if margin > edge else "Top opens"}')
```

## 10. Edge cases

| # | Case | Proposed rule | Reason |
|---|---|---|---|
| 1 | Equal scores / margin exactly at the edge | Favored role opens (`favored_holds_tie`) | Deterministic; the position's priority is the default |
| 2 | Missing or out-of-range proficiency | Refuse entry, `missing_proficiency` / `invalid_proficiency`, zero mutation. `R = 0` is a valid explicit value; an absent value is not | Fail closed; no silent default, and no silent `R = G` |
| 3 | Mount / Half Guard | Policy `LEGACY_FIXED`; inputs ignored; replays byte-identical to today | Preserve existing behavior |
| 4 | Chains (Mount → Half Guard → Side Control) | One decision per entry, using the proficiency of the role the fighter **now** holds in the **new** position | Role proficiency is keyed `(position, role)`, not identity or axis |
| 5 | Roles swap on a reversal | Same: the roles at entry decide which `R` applies | Same |
| 6 | Neutral → sequential after a trigger | The position declares the trigger and the named initiator; no skill contest | Guide §15/§17 |
| 7 | Opener cannot act (exhausted) | Every window must offer at least one legal action (Side Control v0 has the free pass); skill can never choose an opener with no legal action | No deadlock |
| 8 | Free windows (a Mount mechanism exists; nothing generates them yet) | The opening decision neither creates nor consumes a free window; whether a free window counts toward either turn counter is open (§11.2) | Separate rule family; no invented accounting |
| 9 | Decision deadline expiry | Independent of initiative; existing published fallbacks apply; simultaneous needs its own | Three timeout systems stay separate |
| 10 | Frozen inputs vs mid-match career change | Impossible by construction; inputs are a match-creation snapshot | Replay determinism |
| 11 | Passive monopoly | Not possible: alternation after the opener; there is no repeated contest | V1 design |
| 12 | Information leak | Opening reveals only scores and the opener, never a sealed choice; neutral positions seal before reveal | Sealed decisions stay sealed |
| 13 | Memory mastery as an input | Not accepted; a test asserts it | No double counting |
| 14 | `G` rises or a belt is earned | `R` is unchanged; only `G` changes the next match's contest | OD-2: `R` is earned, never derived |
| 15 | Focus assignment changes | Earned `R` for every position-role persists; the focus only changes how fast future `R` is earned, and takes effect next match | OD-2; inputs are frozen per match |
| 16 | Unfocused fighter | Legal attacks, escapes and essential defenses unchanged (existing technique-knowledge rules); `R` affects only the opening contest | No move is locked for lack of focus |
| 17 | Experienced fighter with no recorded history | Reads as `R = 0`; needs an explicitly defined starting profile or history before it is used, never derived from `G` | OD-12; no roster generator is designed here |

## 11. Per-fighter turn accounting: reconciliation with the Match Incentives decisions

**Reconciled in revision 3 (2026-10-13).** An earlier draft of this section defined a "personal turn" as an accepted exchange in which the fighter was the initiator and said a response adds no turn. That answered a question the owner left open and merged two different counters, so it is **withdrawn**. The authority is [`MATCH_INCENTIVES_HEART_OF_A_LION.md`](MATCH_INCENTIVES_HEART_OF_A_LION.md) (owner-approved 2026-10-12; **specification only, nothing is implemented**) and Master Guide §§41–42. This section states only what the initiative contract must stay compatible with. It implements, approves and changes none of those rules.

### 11.1 Two separate events, never one counter

| | **Inactive-turn event** (custom stalling) | **Heart-of-a-Lion counted-turn event** |
|---|---|---|
| Owner decision | **[OWNER-APPROVED 2026-10-12]** | **[OWNER-APPROVED 2026-10-12]** |
| What it is | A consumed normal personal decision that the future activity classifier calls *inactive* | An accepted, resolved, normal personal decision turn counted during the once-per-match Heart of a Lion phase |
| Keyed by | Stable fighter ID; persists across position changes (never three global windows; initiative can be unequal) | Stable fighter ID; five counted turns remaining per fighter, kept at the match owner |
| Consequence | **The third consecutive inactive personal turn triggers the game's custom stalling penalty.** The first two are allowed (a warning after the second is a presentation proposal) | Once **both** fighters have completed five counted turns, each surviving fighter is restored to 100% of their own maximum at the next authoritative settlement boundary |
| Reset | Only meaningful activity under a future, explicit classifier clears the streak; meaningless action spam does not | Does not reset; the mechanic never re-arms |
| Rule status | A **custom game rule** ("custom game stalling with IBJJF-inspired scoring"). **It is not an official IBJJF rule:** the IBJJF reference (Rules Book v6.1, Arts. 7.2.1, 7.3.1) is a time-based threshold of 20 consecutive seconds, and a strict IBJJF mode would keep its own timing and exemptions | A **game-original modifier**, not an IBJJF rule; opt-in or a labeled custom ruleset |

**What the owner has decided about each**

- *Inactive-turn events:* an accepted normal **PASS** or **REST** decision counts as an inactive personal turn, subject to explicitly approved defensive exemptions (none are defined yet). **Legitimate failed attacks, escapes and defenses are not automatically inactive**, even when the fighter is exhausted. A fighter with no legal defense is not automatically punished for an opponent's unanswerable action. The streak is shared across all inactive and REST decisions by one fighter, so alternating REST with passes does not erase it. The penalty progression itself (1st recorded; 2nd one advantage to the opponent; 3rd two points; 4th disqualification) is an IBJJF-*inspired* match-scoring proposal in the Match Incentives document, not part of this contract.
- *Heart-of-a-Lion events:* it activates **only** when both fighters' current stamina is **exactly zero** at one authoritative boundary (the nonzero Exhausted latch is not enough); it immediately restores 50% of each fighter's own maximum; each fighter then has **five of their own counted normal personal decision turns**; it happens **once per match**, across position changes, and never re-arms; it opens no window, advances no clock, changes no position or role and bypasses no submission or penalty. A match owner stores `consumed`, the phase and the five-turn counters.
- *After Heart of a Lion is spent* (mutual exactly-zero, one-time phase fully completed): eligible **LOW memories** may be attempted (a failed legal attempt is not stalling) and **REST** may be chosen for up to **two** consecutive personal turns without a stalling penalty; the third consecutive inactive or REST turn triggers the custom stalling penalty. This keeps the existing LOW-memory and REST direction. It is **not** already legal in the engine (the current LOW funding cost is 3 stamina), and REST restores nothing until a separate deterministic rest-economy rule exists.
- *Rejected commands, unresolved seals, menu views and UI observations* consume **no** completed personal turn under either counter.

The classifications are independent. For example, an accepted normal PASS **is** an inactive-turn event (decided above), but whether it also advances the Heart-of-a-Lion counter is **open** (§11.2). Nothing here lets one classification stand in for the other.

### 11.2 Still open; this proposal answers none of them **[OPEN]**

| # | Open question | Source |
|---|---|---|
| 1 | Whether **passes** and other special decisions advance the Heart-of-a-Lion counter | Match Incentives §3 |
| 2 | Whether **D3-B holds** (and other specialized controller opportunities) count, for either counter | Match Incentives §3 |
| 3 | **Responder accounting**: whether a response is a personal turn, for either counter | Match Incentives §3 ("do not assume one window equals one fighter turn") |
| 4 | **Free windows** (Mount has a free-initiative mechanism; nothing generates one yet) | Match Incentives §3, §5 |
| 5 | **Simultaneous decisions** (and the effect of simultaneous initiative on the streak) | Match Incentives §1, §3 |
| 6 | **Integer rounding** of 50% restoration for fractional capacities | Match Incentives §3 |
| 7 | **Settlement order** relative to costs, score, terminal outcomes, transitions and exhaustion-latch recomputation | Match Incentives §3 |
| 8 | **Repeated stalling penalties**: cadence and reset after the third and later inactive turns, repeat-offense scoring, integration with other fouls | Match Incentives §1 |
| 9 | The activity classifier per position, the defensive and forced-hold exemptions, whether a successful defense immediately clears the streak, warning UX, referee tie handling, and whether REST restores any capacity | Match Incentives §1, §4 |

### 11.3 What the initiative contract must stay compatible with **[PROPOSAL]**

- **The opening decision is not a turn.** `initiative_decided` neither increments nor resets either counter, and an opening won by skill earns no turn credit.
- **Counting and classification live above the positions**, at the match owner, keyed by stable fighter ID, never by role. A position owns no inactivity or Heart-of-a-Lion state (consistent with `SIDE_CONTROL_V0_PROPOSAL.md` §7.4). Half Guard's existing role-keyed initiation counters stay as they are.
- **One window is not assumed to equal one fighter turn.** With a favored opening, alternation and (later) free windows or simultaneous decisions, per-fighter counting is what keeps "the third consecutive personal turn" and "five of their own turns" well defined.
- **The event log must keep the facts a future counter needs**: for each accepted decision the stable fighter ID(s), role(s), position ID, window ID, decision kind (action, response, pass, hold, REST, free-window use, simultaneous commit) and whether it was accepted and resolved. These are facts to record, **not** a classification.
- **Proficiency, belt, role and initiative priority never classify a turn.** `G` and `R` affect only the opening contest (§5).

## 12. Compatibility and test plan (design only; nothing is implemented)

**Compatibility invariants:** Mount and Half Guard suites, oracles and pinned counts are unchanged; replays of existing matches are byte-identical; no existing public API, test or fixture is edited; Python under `src/` is untouched; a graph built by any existing constructor behaves exactly as today. The contract creates no turn, inactivity or Heart-of-a-Lion state (§11).

**Negative-first tests (each leaves state byte-identical):** missing / extra / mistyped proficiency keys, `bool` or float where an int is required, out-of-range values, unknown position id or role, a policy with an unknown kind or a missing favored role, a mastery input, a second decision for the same entry, a decision while a window is open, a mismatched role map.

**Deterministic matrix:** equal ratings; adjacent belts; underdog Top and underdog Bottom; high-skill Bottom in Side Control and Closed Guard; low-technique Top in Open Guard (no override, protocol unchanged); two White Belts with different two-focus selections; identical belt and `G` with different focus histories; respec retaining earned proficiency (next match only); off-focus legal moves unaffected; promotion unlocking a focus; save/load and replay reproducing the same `initiative_decided` records; margin = edge and edge + 1; input permutations (fighter-id order must not matter); new career fighters at `R = 0` regardless of `G`; `G` increases and belt promotion leaving `R` unchanged; focus reassignment keeping earned `R`; Tables 1–5 and the §8.4 examples reproduced as fixtures; two Black Belts with equal `G` deciding by the `R` gap alone; an experienced fighter without an explicit starting profile refused.

**Measurement plan before any numeric acceptance:** after B2c exists, run the B1e-style harness with fixed provisional profiles across a belt-pair grid and report opener distribution, consecutive-opportunity frequency after Knee Slice, and any window starvation. These are evidence, not gates the doc pre-commits.

## 13. Staging after approval (nothing starts without the owner)

1. Owner reviews this document and SC-D1–SC-D15 together.
2. B2b: Side Control rules sheet and independent oracle, with the policy and provisional profile as explicit inputs (so it never waits for the career system).
3. B2c/B2d: typed engine and the Knee Slice receiver, using `decide_opening` for the first window.
4. Later, separate slices: fighter proficiency data, the symmetric simultaneous protocol (§6.2), the match-owner turn accounting of §11 (stalling and Heart of a Lion), memory mastery.

## 14. Owner decisions

| Id | Decision | Recommendation |
|---|---|---|
| OD-1 | Accept §3 (seven separate concerns) and the three policy kinds | Accept |
| OD-2 | **OWNER-APPROVED 2026-10-13 (Option B):** `G` and `R` are separate; a new career fighter starts at `R = 0`; `R` is never derived from `G` | Done |
| OD-2a | Scale (`0..100` provisional), weights (`1:1` provisional), `R` cap and growth pace | Decide with the progression design; every edge depends on it (§8.8) |
| OD-3 | Skill decides the opening only (V1); V2 deferred; V3 rejected | Accept |
| OD-4 | Edges: Side Control 25 (20–30), Closed Guard 15 (10–20), Back Control 40 (30–50); compare with the halved 20 / 12 / 30 (§8.5) | Accept as playtest starting values only |
| OD-5 | Strict `>`; a tie keeps the favored role | Accept |
| OD-6 | Inputs frozen at match creation; changes apply next match | Accept |
| OD-7 | Until fighter data exists, an explicit provisional profile identical for both fighters (for example `G = 50`, `R = 0`) (§8.6) | Accept |
| OD-8 | `entry_adjust` exists, default 0; decide a value after measurement | Accept |
| OD-9 | The nine open turn-accounting questions of §11.2 (passes and special decisions for the Heart-of-a-Lion counter, D3-B holds, responder accounting, free windows, simultaneous decisions, rounding, settlement order, repeated stalling penalties, classifier and exemptions). **Not answered here**; the stalling threshold, the inactive PASS/REST rule and Heart of a Lion are already owner-approved in the Match Incentives document | Decide with the stalling and Heart of a Lion slices; not needed for B2b or B2c |
| OD-10 | Policies for `turtle`, `front_headlock`, `leg_entanglement`, and confirming `open_guard`/`closed_guard` | Decide at each rules sheet |
| OD-11 | Mount / Half Guard stay `LEGACY_FIXED`; any conversion is a separate authorized slice | Accept |
| OD-12 | How an existing experienced fighter (opponent, boss, pre-system save) gets an explicit starting `R` or training history; never derived silently from `G` | Decide when fighter data is designed; no generator now |
