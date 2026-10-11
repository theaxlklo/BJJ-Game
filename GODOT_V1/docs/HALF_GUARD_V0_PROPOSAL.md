# Half Guard v0 — rules and feasibility proposal (B1a)

**Status: PROPOSAL for owner review. Nothing in this document is approved or implemented.** It changes no GDScript, no
Python, no test, no workflow, no fixture and no earlier PR. Every rule, number, name and table below is a **[PROPOSAL]**
until the owner approves it by decision id (`HG-1` … `HG-25`, §2). The only code executed to prepare it is two throwaway
Python scripts outside the repository, reproduced verbatim in Appendices A and B, that check internal consistency and
reachability of the proposed tables. They are neither an oracle nor parity evidence.

Backend-first direction (owner): F1 stays available as an interactive Mount debugging interface and is not expanded.
The goal is deterministic position-to-position transitions, starting with Mount → Half Guard, so that complete matches
can later run from Standing without the interface.

Depends on: `POSITION_GRAPH.md` (§§1–12, questions Q1–Q8), `POSITION_TOPOLOGY.md` (§§6, 9, 11, 14, 15, 16, 19),
`POSITION_CONTRACT.md`, `CARRYOVER_EXPORT.md` (A3b), `F0_FIGHTER_FOUNDATION.md`, `F1_MOUNT_PRACTICE.md`,
Master Guide v10.4 §§7, 8, 11.4, 12–16, 19–22.

## 0. What this document delivers

1. Verified facts about what exists and what a second position can reuse (§1).
2. A decision register of every owner decision needed (§2).
3. A recommendation for each of Q1–Q8 with the exact deterministic rule, gameplay rationale, the simplest reusable
   component, alternatives and feasibility, the effect on Mount parity, the required tests and the unresolved owner
   decisions (§3).
4. A consolidated Half Guard v0 rules sheet that B1b can implement and an independent oracle can be written from (§4).
5. The entry specifications: a neutral entry request (B1b), the Mount edge adapter (B1c) and the opt-in graph integration (B1d) (§§5–6).
6. The independent test-only oracle plan (§7), architecture feasibility comparisons (§8), the slice plan with exact
   boundaries and the existing tests it does and does not touch (§9), measured prototype evidence (§10), risks (§11) and
   the prototype scripts (Appendices A and B).

Non-goals (unchanged): Standing, Closed/Open Guard, Side Control or any other position's mechanics, scoring, stalling,
Recognition, submissions, a Reversal landing, return to Mount, presentation work, Python engine changes, changes to F1.

## 1. Verified facts

### 1.1 What exists (checked in source at the F1 head `5886e49`)

| Fact | Where | Consequence for Half Guard |
| --- | --- | --- |
| The only position is Mount. Its exits come from Elbow-Knee Escape (SUCCESS → `Half Guard`; STRONG_SUCCESS → `Half Guard` at the Stable band, otherwise `Open Guard`) and Trap-and-Roll (≥ SUCCESS → unresolved `Reversal`). The A3d tests pin this inventory | `mount_catalog.gd`, `test_mount_slice.gd` | Half Guard is entered **only** by an Elbow-Knee Escape. Entry strength is not recorded in the exit label |
| The A3b carry-over record exports ids by role, stamina current/max/latch, behavior **remainders**, clock, last issued window id, the frozen D3-B fields, terminal flags and the exit. It omits Mount axis/band, held behaviors, setup tiers, submission stage, histories, initiative, authority, the window **interval** and the rules/RECOVER configuration | `mount_carryover.gd`, `CARRYOVER_EXPORT.md` | A receiver gets *state it must preserve* but no Mount-derived control values (D1). The cadence must come from somewhere else (§6.1) |
| `BjjStaminaPool.create(start, capacity)` derives the exhaustion latch from `start` alone. Thresholds: enter `floor(0.25 × max)` (inclusive `<=`), recover `ceil(0.35 × max)` (inclusive `>=`). `set_current` re-evaluates the latch. `BjjMountMatch._copy_pool` already restores a latch with `create(0, max)` + `set_current` | `stamina_pool.gd`, `mount_match.gd:128-131` | A latch can be restored with public API only, and production already does it (§5.4) |
| `BjjBehaviorStaminaPolicy.Meter(remainder)` accepts a remainder at construction | `behavior_stamina_policy.gd` | Meters restore without new API |
| Pure static, position-independent functions: `BjjGrade`, `BjjCommitment`, `BjjCommitmentSettlement`, `BjjExhaustionPolicy`. Position-independent objects: `BjjStaminaPool`, `BjjStaminaCostPolicy` (costs 3/7/12), `Meter` | `scripts/core/` | Half Guard needs **no new stamina or commitment math** |
| Mount-specific: catalog, resolver, rules (axis 0.10–4.00, bands, drift), setup tiers, the Americana submission, behaviors in production, RECOVER, D3-B. `BjjExchangeHistory` / `BjjExchangeResult` live in `core/` but are Mount-shaped | `scripts/positions/mount/`, `scripts/core/` | Not reused; Half Guard gets its own history and result shapes |
| `BjjMatchWindowGateway` owns window identity and admission, builds its own `BjjMountMatch`, and forces production policy (Rule 1 ON, Rule 2 OFF). `BjjPositionGraphMatch` wraps exactly one typed `_gateway`, logs events, classifies exits and halts on any exit. `classify_exit_from` returns `unknown_source_position` for any source other than Mount (pinned by tests and by POSITION_TOPOLOGY C-10). `submit()` hard-codes `POSITION_ID` | `mount_window_gateway.gd`, `graph_match.gd` | A second position needs a segment seam in the graph (§6) and a decision on how its exits are classified (HG-23) |
| The graph reads these views of its segment: `roles()`, `state_fields()`, `history_fields()`, `window_fields()`, `action_options()`, `response_options()`, `selected_commitment()`, `behavior_fields()`, `controller_fields()`, plus `carryover_segment()` (the graph is its only caller), and the `Report` schema (`closed`, `window_id`, `fighter_id`, `role`, `kind`, `transition.raw_destination`, `ended`) | `graph_match.gd` | A Half Guard segment must provide the same views **and** the same `Report` shape (§6.2). F0 reads only `roles()`, `state_fields()` and `behavior_fields()` |
| F1's controller reads `state.control_axis` and indexes `BjjMountRules.Band.keys()[state.band]` | `mount_practice_controller.gd:194-195` | A graph whose active segment is Half Guard would break F1's view; therefore default graphs must never contain Half Guard (HG-22) |
| The Python reference has **no** Half Guard and no non-Mount position. Existing oracles drive the unchanged `MountMatch.attempt` | `src/bjj_game/`, `GODOT_V1/tests/generate_*.py` | Half Guard needs a *new*, independent, test-only oracle (D6) |

### 1.2 Reuse map

| Component | Reuse in Half Guard | Change to existing code |
| --- | --- | --- |
| `BjjStaminaPool`, `BjjStaminaCostPolicy`, `BjjCommitment`, `BjjCommitmentSettlement`, `BjjExhaustionPolicy`, `BjjGrade` | Used as-is | None |
| `BjjBehaviorStaminaPolicy.Meter` | Carried (remainder preserved); not advanced in v0 | None |
| `BjjPositionContract` (`Roles`, `Command`, `Outcome`, `Transition`, `OptionList`) | `BjjHalfGuardContract extends BjjPositionContract` | None |
| `BjjMountCarryover.validate_segment` | The **Mount edge adapter** (B1c) validates the source record with the existing validator | None |
| `BjjPositionRegistry` | Destination ids (`side_control`, `open_guard`, `closed_guard`) are checked against it by a test | None |
| `BjjMountExchange.attempt` pipeline | **Re-implemented** as a smaller `BjjHalfGuardMatch.attempt` in the same order (§4.6); not shared | None (§8, row 5) |
| `BjjMatchWindowGateway` | A sibling `BjjHalfGuardWindowGateway` with the same views and the same nested `Report` class | None (Mount gateway untouched) |
| `BjjPositionGraphMatch` | A second, typed, nullable segment slot, an opt-in receiver constructor and a commit step | Deliberate, additive (B1d only) |

## 2. Decision register

Nothing below is approved. "Recommended" is this document's proposal; the owner may approve, amend or reject each id.

| Id | Decision | Recommended | Alternatives | Question |
| --- | --- | --- | --- | --- |
| HG-1 | Axis representation: signed integer **tenths**, range −40…+40, positive = Top passing advantage | Yes | Float like Mount; one-sided axis like Mount (positive-only) | Q1 |
| HG-2 | Five bands (BOTTOM_CONTROL, BOTTOM_EDGE, CONTESTED, TOP_EDGE, TOP_CONTROL) with the thresholds of §3 Q1 | Yes | Three bands; four bands without a neutral band | Q1 |
| HG-3 | Position-break lines at ±30, reached only by a deliberate, break-capable, successful technique; neutral (0) is an interior state, not a break. This **deliberately differs** from Guide §12/§14 "crossing neutral breaks the position", which the v10.4 clause "define the sign convention in each position's contract" permits for a guard-like contest | Yes | ±35; a break at neutral | Q1/Q8 |
| HG-4 | Entry axis fixed at **+5** (CONTESTED); authority = sign of the axis (none at exactly 0). Authority is **reported** (`Roles.control_authority_id`) and has no mechanical effect in v0 | Yes | Entry from the exit grade (needs a schema bump); entry at 0 or +10 | Q2 |
| HG-5 | First initiative after entry: **Top**; strict alternation after every accepted non-exit exchange or no-action pass; the exit exchange hands nothing over. Strict alternation (not Guide §15/§17 opening-triggered or sealed simultaneous choice) is a v0 simplification | Yes | Bottom first; opening-triggered initiative | Q3 |
| HG-6 | **No behaviors, no drift, no RECOVER, no D3-B in v0.** Time advances the clock only; carried meters stay frozen. Accepts the exhaustion consequences listed in Q4 | Yes | Reuse the flow policy with fixed behaviors (Q4 option B) | Q4/Q5/Q6 |
| HG-7 | Stamina and commitment: shared position-independent policies; v04 semantics always on; Rule 1 ON, Rule 2 OFF; baseline MEDIUM; **either fighter may choose any commitment** when initiating. **This departs from the AGENTS.md production invariant "LOW while Exhausted and baseline MEDIUM after clear"** because Half Guard has no RECOVER | Yes (as a flagged departure) | Mirror Mount's policy-selected commitment for an Exhausted fighter | Q5 |
| HG-8 | v0 catalog: Top Crossface, Flatten, Knee Slice; Bottom Underhook, Recover Guard (Guide §11.4 names). Deferred: Sweep, Wrestle-Up, Backstep, deeper half guard | Yes | Add Sweep/Wrestle-Up with explicitly unresolved destinations | Q8 |
| HG-9 | Response names and the 15 raw grades of §4.4 (new content) | Yes | Any table with the same structural properties | Q8 |
| HG-10 | Positional modifier: −1 for an initiator facing the opponent's CONTROL band | Yes | None; Mount-like asymmetric | Q8 |
| HG-11 | Exit map of §4.5 with labels `Side Control`, `Open Guard`, `Closed Guard`. The Recover Guard split (SUCCESS → Open Guard, STRONG → Closed Guard) is new landing content that needs T-2 provenance; Open Guard and Reversal stay honest halts; no return to Mount | Yes | Map STRONG Knee Slice to Mount; one guard for both grades | Q8 |
| HG-12 | Terminal rules: timeout only (no submissions, no tap, no scoring) | Yes | — | Q8 |
| HG-13 | One **neutral entry request** (ids by Half Guard role, per-fighter-id state) is the only way to build Half Guard, for both a Mount edge and tests/oracles. Scenario and normal-match starts are **not** registered (P-12) | Yes | A Mount-record-only receiver; register a scenario start now | Q2/Q7 |
| HG-14 | D3-B stays frozen inside the retained Mount segment, is never given to Half Guard, and `controller_fields()` is `{}` there | Yes | Per-position analogue (needs measurement) | Q6 |
| HG-15 | Latch restoration with public pool API only (the production `_copy_pool` pattern), proven by an exhaustive equivalence test; fall back to a validated pool factory only if the proof fails | Yes | New pool factory now | Q7 |
| HG-16 | Segment seam: keep the typed `_gateway` slot for Mount and add a **second typed, nullable Half Guard slot**; every graph pass-through branches on it. No `Variant`, no base class, no change to the Mount gateway. **This revises the "graph holds only one gateway" invariant that `test_position_graph_boundaries.gd` pins; approving HG-16 approves that revision** | Yes | `Variant` segment; abstract base class; one generic gateway | Q7 |
| HG-17 | Window ids continue from `last_issued_id + 1`; one new event `transition_committed`; the exit-producing window is consumed; no automatic window | Yes | — | Q3/Q7 |
| HG-18 | If building the receiver fails **after** an accepted exit exchange, the graph halts with `transition_entry_invalid` instead of rolling back. This **amends** `POSITION_GRAPH.md` §5 and §8 (whose letter says failed construction leaves state unchanged, which cannot hold once the exchange is settled). Needs explicit owner approval of the amendment | Yes | Roll back (needs a Mount seam) | Q7 |
| HG-19 | Independent oracle (§7): a new Python module under `tests/`, written from the approved rules, reusing only frozen position-independent stamina primitives, with a cross-check of its settlement helpers against Mount's private helpers and a mutation-sensitivity control (§7) | Yes | Translate the GDScript | §7 |
| HG-20 | Graph `carryover_export()` is **refused** (`carryover_unsupported_position`) while Half Guard is active; the v1 envelope validator is left unchanged; a v2 envelope is deliberately deferred, which **departs from POSITION_TOPOLOGY §9.3 step 5** ("a committing build must emit v2"). A graph halted with `transition_entry_invalid` is refused by the unchanged v1 validator (`inconsistent_graph_segment`) | Yes | Extend the envelope now | §6 |
| HG-21 | Slicing: **B1b** mechanics + neutral entry + latch proof + oracle + gateway conformance test; **B1c** Mount edge adapter; **B1d** opt-in graph integration. Each its own draft PR and exact-head CI. B1b and B1c must land (and compile) before B1d, because the graph's typed slot loads the Half Guard scripts for every graph | Yes | One combined slice | §9 |
| HG-22 | **Receivers are opt-in**: a separate constructor (`create_with_receivers`) builds a graph that may commit to Half Guard; `create` and every default graph keep today's behavior (all Mount exits halt). Flipping the default is a later, separately authorized step. The opt-in graph changes exactly **two** private-field pins (§9.3) | Yes | Commit by default (changes ~30 pinned assertions and breaks F1's view) | §6 |
| HG-23 | Classification adds **no new classification code**: the static `classify_exit_from` stays byte-identical (still `unknown_source_position` for a non-Mount source, pinned by C-10). The graph instance turns the static Mount answer `blocked / destination_not_implemented / <id>` into a `transition` iff `<id>` is in the receiver table, and classifies a Half Guard source's labels by calling the same unchanged function with Half Guard's own declarations (`{"half_guard": {"exits": EXIT_DESTINATIONS, "unresolved": []}}`) | Yes | A new instance-level classifier; change the static classifier | Q8/§6 |
| HG-24 | The Mount gateway object is **retained, frozen** after the commit (never advanced or submitted to again), so Mount's histories and D3-B record stay with the Mount segment as `POSITION_GRAPH.md` §6 says; Half Guard keeps its own histories | Yes | Keep only a detached record | §6 |
| HG-25 | The window cadence is captured by the opt-in graph from its own `configuration.interval` (default: that same Mount constant) and passed to the entry request; the Mount record is not extended. When the key is absent the default is the constant the Mount match itself uses (`BjjMountRules.DEFAULT_INTERVAL_SECONDS`), never a second literal | Yes | Add an interval to the record; fix 5 s and halt on mismatch | §5/§6 |

## 3. Answers to Q1–Q8

"Mount parity" means: the frozen Python Mount reference, its fixtures and digest, the Mount GDScript, and the Mount parity suites
(the 256,992-assertion slice and the exchange/lifecycle/D3-B/contract oracles). "Existing tests" means the pinned suites listed in §9.

### Q1 — Half Guard axis: sign convention, range, bands, hysteresis

**Exact rule [HG-1, HG-2, HG-3].** The axis is a signed integer in **tenths**, `a ∈ [−40, +40]`. **Positive = Top passing advantage;
negative = Bottom retention/recovery advantage** (D1). Display is `a / 10` with one decimal; that float is a view only and is never
stored or compared. All arithmetic is integer, so there is no rounding.

Bands are ordinals `−2…+2`: `BOTTOM_CONTROL (−2)`, `BOTTOM_EDGE (−1)`, `CONTESTED (0)`, `TOP_EDGE (+1)`, `TOP_CONTROL (+2)`.
Initial band for an axis `a`: `|a| < 10 → 0`; `10 ≤ |a| < 25 → ±1`; `|a| ≥ 25 → ±2` (sign of `a`). After every axis change the band is
updated by applying the first matching hysteresis rule until none applies. The rules are mutually exclusive per band, so order is immaterial:

| Direction | Band change | Applies when |
| --- | --- | --- |
| toward Top | 0 → +1 | `a ≥ 12` |
| toward Top | +1 → +2 | `a ≥ 27` |
| toward Top | −1 → 0 | `a ≥ −8` |
| toward Top | −2 → −1 | `a ≥ −23` |
| toward Bottom | +2 → +1 | `a ≤ 23` |
| toward Bottom | +1 → 0 | `a ≤ 8` |
| toward Bottom | 0 → −1 | `a ≤ −12` |
| toward Bottom | −1 → −2 | `a ≤ −27` |

Legal axis/band pairs (context validation): band 0: `−12 < a < 12`; +1: `8 < a < 27`; +2: `a > 23`; −1: `−27 < a < −8`; −2: `a < −23`.
Appendix A asserts that every axis in range has a legal band and that every rule lands on a legal pair.

The axis changes only through accepted exchanges in v0 (no drift, HG-6) and is clamped to `[−40, +40]`. Crossing a break line alone does nothing
(§4.5).

**Where the numbers come from.** The hysteresis width (±0.2 around nominal boundaries at 1.0 and 2.5) mirrors Mount's ±0.2 width; the break lines
at ±3.0 are chosen so that a break needs the CONTROL band plus a successful technique: the prototype finds exits in 2–4 windows with full
cooperation and none against perfect counters. They are proposals for owner edit, not derived values. **Parity note:** entry is +5 and every step is a multiple of 10, so an unclamped axis is always ≡ 5 (mod 10); a break line of 30 therefore behaves like 35 until a clamp occurs, and an axis of exactly 0 appears only after a clamp (for example 40 → 20 → 0). The owner may prefer a different entry value or line. The one-sided alternative and ±35 are listed below.

**Gameplay rationale.** Guide §12 defines the universal axis as `−4…+4` and requires each guard-like position to name its contesting sides and sign
(v10.4 clarification); D1 requires an axis oriented toward Top passing advantage versus Bottom retention/offense. Authority is simply "who is ahead".
Neutral is an interior contest state here (HG-3), unlike Mount's one-sided axis where crossing the floor is the escape.

**Simplest reusable component.** The *shape* of `BjjMountRules` (initial band, hysteresis list, legal-pair check) as a new `BjjHalfGuardRules` with its
own constants. D1 forbids reusing, converting or deriving from Mount's axis, so the constants are new even where the pattern is borrowed.

**Alternatives and feasibility.** (a) One-sided axis `0.1…4.0`: least new code, but it cannot express "Bottom is ahead", contradicts D1's orientation and
makes authority constant. (b) Floats: matches Mount's style, needs `round_ten`, and A3b already showed float round trips are rejected by design.
(c) Three bands (no EDGE bands) or four bands without a neutral band: fewer thresholds, but a two-sided contest then has no neutral state. (d) Break
lines at ±35 make exits slower. Recommended: HG-1/2/3 as written. Cost: ~110 lines, no change to existing code.

**Effect on Mount parity.** None: no Mount file, fixture or Python source is touched.

**Required tests.** Literal band table over all 81 axis values; every hysteresis rule at and one tenth either side of its threshold, both directions, from
every legal starting band; multi-band jumps; legal-pair validation including rejection of impossible pairs; clamp at ±40; determinism; oracle replay of the
axis × band grid.

**Owner decisions.** HG-1, HG-2, HG-3.

### Q2 — Entry values and who holds control authority at entry

**Exact rule [HG-4, HG-13].** Every Half Guard built from an entry request starts at **axis +5, band CONTESTED (0)**. Control authority is a Half Guard
rule: the fighter on the positive side holds it (the `top` role when `a > 0`), the `bottom` role when `a < 0`, and **nobody** when `a == 0`
(`Roles.control_authority_id` is `""`). This is the contract's own definition ("the fighter on the positive/control side of the signed axis")
applied to a signed axis. Authority is reported only: in v0 it drives neither initiative nor grades.

For Mount → Half Guard the edge declares the identity role map (D1: the Mount Top stays `top`, the Mount Bottom stays `bottom` and has recovered
Half Guard). **The receiver itself accepts any validated role map and any source** (§5): the entry request names fighters by id, so a non-Mount source
(for example the Guide's Standing → Half Guard example, whose takedown assigns roles by outcome) can use it later without a Mount-shaped record.

**Gameplay rationale.** The escaping fighter has earned a *contested* guard, not a free one; Top keeps a slight edge. A fixed entry value keeps the A3b
schema unchanged and keeps D1's rule that no Mount number feeds Half Guard.

**Simplest reusable component.** Two constants and the sign rule; `Roles.control_authority_id` already exists.

**Alternatives and feasibility.** (a) Entry depends on the exit grade (SUCCESS vs STRONG at Stable): richer, but the record has no grade, so it needs a v2
schema and a Mount-side export change; deferred. (b) Entry at 0: authority becomes "none" at entry. (c) Entry at +10: an unearned head start.

**Effect on Mount parity.** None.

**Required tests.** Entry for a grid of valid requests; authority for literal axes (0, ±1, ±40); every invalid request refused; role-map variants including a
swapped bijection proving state follows the fighter id.

**Owner decisions.** HG-4, HG-13.

### Q3 — First initiative event and alternation

**Exact rule [HG-5, HG-17].** The exit-producing Mount window is consumed (D2): the transition grants no window, no extra action, no clock change and charges
nothing. The first window opens only when the caller calls `open_window()`, with id `last_issued_id + 1`; its owner is the **Top** (the fighter with
authority at entry). After every accepted non-exit exchange and every no-action pass the initiative flips; an exit exchange leaves it unchanged (the
position ends). Either initiator may take a no-action pass: it needs an open window, flips initiative, costs no stamina, appends the side to
`reset_window_history` and produces no grades. A window advances the clock by `min(interval, remaining)`; if that brings the clock to 0 the report is
`closed` and **no window opens** (timeout), so a submit can never meet a finished clock.

**Gameplay rationale.** Guide §15 and the v10.4 authority rule: the controlling top fighter ordinarily acts first; a bottom fighter acts when it has a
valid opening. D2 forbids a free follow-up for the escaper. Strict alternation is the turn structure the qualified Mount uses, so the window protocol,
F0 and F1 keep working. Opening-triggered initiative (Guide §15) and sealed simultaneous choice (§17) are the right long-term models but need setup and
trigger rules no approved decision defines.

**Simplest reusable component.** The window lifecycle of `BjjMatchWindowGateway` (§4.7), copied into a sibling gateway; alternation is one line.

**Alternatives and feasibility.** (a) Bottom first (momentum): invites an immediate second Bottom action. (b) Opening-triggered initiative: deferred (§11).

**Effect on Mount parity.** None. Mount's `initiator` after an exit is never read as a handoff.

**Required tests.** After commit no window is open and the counter equals the source's `last_issued_id`; the first window is the Top's with id `last_issued_id + 1`;
alternation over long sequences; no-action pass (open window required, initiator only, cost-free, recorded); exit leaves initiative unchanged;
timeout at the interval boundary with no window opened; zero clock change at the transition; replay determinism.

**Owner decisions.** HG-5, HG-17.

### Q4 — Does Half Guard use behaviors, and which stamina rates apply?

**Exact rule [HG-6].** **Half Guard v0 has no behaviors.** Time advances only the clock: no drift, no stamina flow, no behavior selection. The two `Meter`
remainders are carried into the receiver and **left unchanged** for the life of the segment, so they stay exact for a later position or a later behavior
rule. `behavior_fields()` returns `{"top": "", "bottom": ""}`.

**Gameplay rationale.** The behavior system is tied to Mount's measured production policy (PRESSURE/ESCAPE baseline, Bottom RECOVER, D3-B). Importing it
unmeasured would activate unapproved economics for both fighters; the repository's practice (D3-B and handoff-oscillation research) is to pre-register and
measure such rules. Dropping behaviors keeps the oracle small.

**Simplest reusable component.** None. `BjjBehaviorStaminaPolicy` stays untouched; only its `Meter` type is carried.

**Alternatives and feasibility.** (A) *Recommended:* no behaviors. (B) Reuse the flow policy with fixed behaviors (Top PRESSURE, Bottom ESCAPE, `CONSERVE`
when Exhausted) and no drift: free recovery, but RECOVER-like economics for both fighters without D3-B or measurement. (C) New Half Guard behaviors with
new rates: new stamina numbers, rejected for v0.

**Consequences the owner must accept (HG-6).**
* Stamina in Half Guard only falls. Appendix A: ~11 MEDIUM exchanges bring a fresh fighter to the Exhausted latch; random play leaves Half Guard in a median
  of 12–14 windows (a fresh entry therefore leaves 1–3 windows after the latch; an entry from a long Mount phase starts low and is exhausted for most of the
  segment).
* A fighter latched Exhausted at entry **stays** Exhausted for the whole segment (the recover threshold is unreachable without recovery).
* The no-action pass costs nothing, so passing dominates for an exhausted fighter and a rational stalemate to timeout exists; Mount has the same pass
  but also has recovery.
* Every Half Guard exit halts the graph (all destinations are unimplemented), so no continuing match exists past Half Guard.
* A human cannot reach Half Guard through F1 (F1 never selects Bottom actions), so v0 is a **mechanics-and-transition milestone**, not a player-facing position;
  a measured recovery rule is a separate slice (B1e, §9.4).

**Effect on Mount parity.** None.

**Required tests.** Time advance changes only the clock; pools and meters identical across any number of windows with no exchange; carried remainder equals the
entry's before and after windows and exchanges; `behavior_fields()` literal; no Half Guard code path references `BjjBehaviorStaminaPolicy` apart from the
`Meter` type (source scan).

**Owner decisions.** HG-6.

### Q5 — Stamina settlement inside Half Guard

**Exact rule [HG-7].** Position-independent policies, v04 commitment semantics always on (Half Guard has no legacy path):

1. Capture both historical bands before any cost; `exhaustion = BjjExhaustionPolicy.exchange(initiator_band, responder_band)`.
2. Initiator funding = `BjjStaminaCostPolicy.determine(requested, initiator.current)`; responder funding = `determine(response_commitment or MEDIUM, responder.current)`.
   `response_commitment` is supplied by the caller exactly as in Mount's `submit(...)`; empty means MEDIUM; anything else must be a valid commitment.
3. Grade: `g_pos = shift(raw, positional_modifier)`; `g_exh = shift(g_pos, exhaustion.modifier)`; `m = magnitude_modifier(initiator_effective, g_exh)`;
   `u = undercommitment_modifier(initiator_effective, responder_effective)`; `final = shift(shift(g_exh, m), u)`.
4. Apply axis, band, exit (§4.5) and initiative.
5. Spend the initiator's effective cost, then the responder's effective cost, each with `spend_up_to`. **Rule 1 ON** (an unfunded initiator waives the responder's
   cost; the Mount gateway already forces this) and **Rule 2 OFF** (no supplemental hold: no submissions). No RECOVER.
6. Baseline commitment `MEDIUM` (`selected_commitment()`); either fighter may request `LOW`, `MEDIUM` or `HIGH` when it initiates. The Mount rule
   `commitment_is_policy_selected` does not exist in Half Guard.

**Departure flagged (HG-7).** AGENTS.md preserves "LOW while Exhausted and baseline MEDIUM after clear" for Mount's production policy. That rule belongs to
Bottom RECOVER, which Half Guard does not have; allowing a free choice is a proposal, not a drift, and needs an explicit owner decision.

**Gameplay rationale.** The same settlement order the qualified Mount uses, so commitment, exhaustion and unfunded behavior mean the same thing in both
positions.

**Simplest reusable component.** `BjjStaminaCostPolicy`, `BjjCommitmentSettlement`, `BjjExhaustionPolicy`, `BjjGrade`, `BjjStaminaPool`, all unchanged. The
ordering is re-implemented once in `BjjHalfGuardMatch.attempt` (~60 lines) and checked against the oracle.

**Alternatives and feasibility.** (a) Refactor Mount's `attempt` into a shared settlement function: removes ~60 duplicated lines but touches the most heavily
qualified code (the exchange oracle: 14,631 scenarios / 8,851,698 comparisons, `EXCHANGE_SETTLEMENT.md`) for no behavior gain: rejected. (b) Mirror Mount's
policy-selected commitment for an Exhausted fighter: LOW for the Exhausted fighter on both sides; cheap to add later if the owner wants it.

**Effect on Mount parity.** None.

**Required tests.** Literal funding tables for every commitment × stamina; exhaustion modifier for all band pairs; magnitude and undercommitment cases; Rule 1
waiver; spend order; unfunded paths; oracle replay of the full grid; the oracle's helpers cross-checked against Mount's Python helpers.

**Owner decisions.** HG-7 (and HG-6 for the absence of RECOVER).

### Q6 — D3-B

**Exact rule [HG-14, HG-24].** Confirmed: D3-B is **frozen and never observed in Half Guard**. The retained Mount gateway keeps its D3-B controller exactly as the
exit left it; nothing ever calls it again. Half Guard has no controller, never calls `observe_advance` or `decide`, grants and consumes no token, and its
`controller_fields()` is `{}`. Entering Half Guard arms, re-arms and consumes nothing whatever the Bottom's band. Return to Mount stays unsupported, so no
reconciliation is designed.

**Gameplay rationale.** D3-B governs Mount's Bottom RECOVER; Half Guard has no RECOVER in v0, so nothing for it to govern. Freezing prevents a stale episode
from granting a second token on a later re-entry.

**Simplest reusable component.** None: absence plus the retained Mount gateway.

**Alternatives and feasibility.** A per-position analogue needs new rules and a measurement study; deferred with RECOVER.

**Effect on Mount parity.** None; D3-B evidence and digests are untouched.

**Required tests.** The retained Mount gateway's `controller_fields()` and every view are identical before the transition and after any amount of Half Guard play
(token counts unchanged); Half Guard exposes no controller; no Half Guard source references `BjjD3BController` (source scan).

**Owner decisions.** HG-14, HG-24, HG-6.

### Q7 — Gateway construction seam for carry-over

**Exact rule [HG-13, HG-15, HG-16, HG-17, HG-18, HG-22, HG-24, HG-25].**
1. **Neutral entry request** (B1b): one validated value, keyed by **fighter id**, builds a Half Guard match (§5.1). It is the only construction path.
2. **Mount edge adapter** (B1c): validates an A3b Mount record and *re-keys it by fighter id* into an entry request (§5.2). It reads no Mount object.
3. **Sibling gateway** `BjjHalfGuardWindowGateway`: the same views and the same nested `BjjMatchWindowGateway.Report` class, seeded with the entry's
   `last_issued_id`.
4. **Graph** (B1d): a second typed, nullable slot for the Half Guard gateway; an opt-in constructor with a receiver table; an atomic commit (§6).
5. Latch restoration uses public pool API (§5.4), proven before it is trusted.

**Gameplay rationale.** None directly: this is the seam that makes the transition atomic and keeps Mount untouched.

**Simplest reusable component.** `BjjMountCarryover.validate_segment`; `BjjStaminaPool.create` + `set_current` (the production `_copy_pool` pattern);
`Meter(remainder)`; `BjjPositionContract`.

**Alternatives and feasibility.** Detailed in §8. (1) *Sibling gateway + second typed slot* (recommended): ~240 new gateway lines and a dozen branched
pass-throughs, zero change to the Mount gateway; the dozen branches are reversible when a third position needs a real interface. (2) *`Variant` segment*:
every graph local needs an explicit type, and the `Report` schema is not enforced by the type system. (3) *Abstract base class on the Mount gateway*:
removes duplication but changes a class covered by the gateway, graph, contract, F0 and F1 suites. (4) *One generic gateway*: the largest refactor.

**Effect on Mount parity.** None for B1b/B1c. B1d changes the graph, not the Mount engine; with opt-in receivers (HG-22) the default graph's observable
behavior is byte-identical.

**Required tests.** Entry validity and invalidity per field; role re-keying (state follows the fighter id, not the role label); restore-then-advance
equivalence; no mutation of the source; window seeding; atomic commit; failure injection; conformance of the Half Guard gateway's views and `Report`
schema against the Mount gateway's (in B1b).

**Owner decisions.** HG-13, HG-15, HG-16, HG-17, HG-18, HG-20, HG-21, HG-22, HG-24, HG-25.

### Q8 — Catalog, responses and exit map (including Open Guard)

**Exact rule [HG-8 … HG-12, HG-23].** Full tables in §4.3–§4.5. In short:

* Top techniques: `Crossface`, `Flatten`, `Knee Slice` (break-capable). Bottom techniques: `Underhook`, `Recover Guard` (break-capable). Guide §11.4's
  `Sweep`, `Wrestle-Up`, `Backstep` and deeper half guard are **deferred**: Guide §11.4 lists no Standing destination for Half Guard, and a Sweep changes
  roles, so including them would need landings no decision defines — the situation of Mount's Reversal. They are candidates for later slices.
* Three responses per side; 15 matchups with deterministic raw grades (no hidden randomness, Guide §20).
* Exit map: Knee Slice with SUCCESS or better and the Top break line reached → `Side Control`; Recover Guard with the Bottom break line reached → `Open Guard`
  for SUCCESS, `Closed Guard` for STRONG_SUCCESS. All three receivers are unimplemented, so each is an **honest halt**: `transition_blocked` with reason
  `destination_not_implemented` and the declared destination id (HG-23: Half Guard's own declarations, evaluated by the graph instance; the static
  classifier still answers `unknown_source_position` for any non-Mount source, as C-10 pins).
* **The Mount STRONG_SUCCESS → `Open Guard` exit stays a halt** (the Open Guard receiver is a separate future slice; Mount's exit labels do not change;
  Reversal stays unresolved). Half Guard → Mount is not declared (return unsupported). Outgoing Half Guard edges declare no role maps because none can
  commit yet; a future receiver declares its own (AGENTS.md: exits need validated role mappings).
* Terminal: timeout only.

**Gameplay rationale.** The catalog uses the Guide's technique names and listed destinations (`Side Control`; `Guard`, which the exit map must resolve into
`Open Guard` or `Closed Guard`), keeps every defense closing some routes and leaving others open (Guide §16), and keeps each action's best counter available to
the responder, the property the qualified Mount has (§10). Response names are new content.

**Simplest reusable component.** The Mount catalog *pattern* (entities with side/kind/name, raw grades keyed `action|response`, an exit function) as a new
`BjjHalfGuardCatalog`; exit labels follow Mount's convention (a `BjjHalfGuardContract.EXIT_DESTINATIONS` table whose ids a test checks against `BjjPositionRegistry`).

**Alternatives and feasibility.** (a) Add `Sweep` and `Wrestle-Up` with explicitly unresolved destinations (as Reversal): more content and two more unresolved
exits; the missing landing rule is the real blocker. (b) Map a STRONG Knee Slice to `Mount`: reaches a position whose re-entry is unsupported, so it would
always halt. (c) One guard for both Recover Guard grades: loses the grade distinction Mount's own exit map makes. Recommended: the v0 catalog.

**Effect on Mount parity.** None. The A3d inventory (candidates versus emitted exits) is unchanged because Mount's catalog and contract are unchanged.

**Required tests.** Exact catalog pins in the A3d style: entity set; break-capable set; every cell of technique × final grade × (axis line reached or not) → label
(labels do not depend on the band); no other producible label; literal exit map; undeclared labels rejected; destination ids ⊆ registry; no `mount`
destination; oracle replay.

**Owner decisions.** HG-8, HG-9, HG-10, HG-11, HG-12, HG-23.

## 4. Half Guard v0 rules sheet (implementation-ready, all [PROPOSAL])

### 4.1 State

`BjjHalfGuardMatch` holds: `axis_tenths: int`, `band: int` (−2…+2), `initiator: String` (`"top"` | `"bottom"`), `top`/`bottom` (`BjjStaminaPool`),
`top_meter`/`bottom_meter` (`Meter`, carried, never advanced), `initial_clock`/`clock_seconds`/`interval_seconds` (ints), `exit_destination`/`exit_reason` (strings),
and a history. `ended = clock_seconds <= 0 or exit_destination != ""`; `submission_tapped` is always `false`. After an exit the match is terminal: every
later exchange is refused with `terminal_exchange`. Roles are `top` and `bottom`; the role map binds stable fighter ids to them (identity, role, authority and
initiative stay separate).

**History schema** (field names reuse Mount's where the meaning is the same; all arrays of strings/ints, appended once per accepted exchange unless noted):
`initiated_action_history`, `response_history`, `raw_grade_history`, `modified_grade_history` (the five names `Strong Failure … Strong Success`),
`initiator_effective_commitment_history`, `responder_effective_commitment_history` (`""` for unfunded), `band_change_history` (`"<before>-><after>"` per band change,
in order), `reset_window_history` (side of each pass), `top_initiation_count`, `bottom_initiation_count`.

### 4.2 Axis and bands — see Q1.

### 4.3 Catalog (stable ids; names are the Guide §11.4 names for techniques, new content for responses)

| Id | Side | Kind | Name | Break-capable |
| --- | --- | --- | --- | --- |
| `half_guard.top.crossface` | top | action | Crossface | no |
| `half_guard.top.flatten` | top | action | Flatten | no |
| `half_guard.top.knee_slice` | top | action | Knee Slice | **yes (pass → Side Control)** |
| `half_guard.bottom.underhook` | bottom | action | Underhook | no |
| `half_guard.bottom.recover_guard` | bottom | action | Recover Guard | **yes (→ Open Guard / Closed Guard)** |
| `half_guard.bottom_response.hip_frame` | bottom | response | Hip Frame | — |
| `half_guard.bottom_response.underhook_fight` | bottom | response | Underhook Fight | — |
| `half_guard.bottom_response.knee_shield` | bottom | response | Knee Shield | — |
| `half_guard.top_response.head_control` | top | response | Head Control | — |
| `half_guard.top_response.hip_pressure` | top | response | Hip Pressure | — |
| `half_guard.top_response.knee_pin` | top | response | Knee Pin | — |

No technique descriptions are invented here.

### 4.4 Raw grades (15 matchups; grade from the initiator's point of view, −2…+2)

| Top initiator \ Bottom response | Hip Frame | Underhook Fight | Knee Shield |
| --- | --- | --- | --- |
| Crossface | +1 | −1 | 0 |
| Flatten | −1 | +1 | +1 |
| Knee Slice | 0 | +2 | −2 |

| Bottom initiator \ Top response | Head Control | Hip Pressure | Knee Pin |
| --- | --- | --- | --- |
| Underhook | −1 | 0 | +1 |
| Recover Guard | +2 | +1 | −2 |

Design properties (checked in Appendices A and B): every action has a counter (≤ −1) and a favorable response (≥ +1); no response is best against everything; each
exit label is reachable by plain play with cooperating opponents; and **the two break-capable actions can never succeed against their −2 counter, even
after exhaustion and commitment settlement** (Appendix B: the best reachable final grade from a raw −2 is CONTESTED), so a responder who always plays the
best counter can never be exited on. Plain counters (raw −1) *can* be lifted to SUCCESS by an Exhausted, under-committed responder; that is intended
to let stamina matter.

### 4.5 Resolution and exit map

For initiator `side`, action `A`, response `R`, band `b`, axis `a` (tenths):

1. `raw = RAW[A|R]`; `positional = −1` if (`side == top` and `b == −2`) or (`side == bottom` and `b == +2`), else `0`.
2. Grade pipeline of Q5 → `final`.
3. `delta = +10 × final` for the Top, `−10 × final` for the Bottom; `proposed = a + delta`.
4. **Break check**, only for a break-capable action and `final ≥ SUCCESS`:
   * `Knee Slice` and `proposed ≥ +30` → exit label `Side Control`;
   * `Recover Guard` and `proposed ≤ −30` → `Open Guard` if `final == SUCCESS`, `Closed Guard` if `final == STRONG_SUCCESS`.
5. No exit: `axis = clamp(proposed, −40, +40)`, band updated by the hysteresis rules, initiative flips.
   Exit: the **same clamp and band update are applied** (a deliberate divergence from Mount, which keeps the unclamped crossing axis out of the stored axis
   and does not update the band at an exit), `exit_destination` and `exit_reason` are set, initiative is unchanged, the match is `ended`. The oracle compares
   the post-exit axis and band.
6. `exit_reason` text: `"<Technique name> reached the pass line with final grade <Grade name>"` for a pass, `"<Technique name> reached the escape line with final grade <Grade name>"`
   for a Bottom break.
7. Costs are spent after the grade is settled (Q5 order). A rejected request changes nothing.

Declared exits: `EXIT_DESTINATIONS = {"Side Control": "side_control", "Open Guard": "open_guard", "Closed Guard": "closed_guard"}`; no unresolved labels.
`transition_destinations()` is those three ids (never `mount`).

### 4.6 Admission (all before any mutation)

*Match level* (`BjjHalfGuardMatch._validate`, mirroring `BjjMountExchange._validate`): `missing_request` → context
(`missing_configuration_or_state`, `missing_stamina_pool`, `aliased_fighter_pools`, `invalid_stamina_state`, `invalid_exhaustion_latch`, `invalid_initiator`,
`invalid_clock_context`, **then** `terminal_exchange`, `invalid_half_guard_context`) → `invalid_commitment` → `invalid_response_commitment` →
`unsupported_cost_policy` → `unknown_action` → `incorrect_action_side_or_kind` (also: an action not owned by the initiator) → `unknown_response` →
`incorrect_response_side_or_kind` → `unsupported_matchup`.

*Contract level* (`BjjHalfGuardContract`, mirroring `BjjMountContract._command_error`): `missing_command` → `missing_position` / `unknown_position` →
`missing_position_state` → the context errors above → `missing_fighter_id` → `unknown_fighter` → `not_initiator` → the match-level codes.

*Gateway level* (`BjjHalfGuardWindowGateway`, mirroring `BjjMatchWindowGateway._admission_error`): `no_open_window` → `stale_window` → context →
`window_initiator_changed` → `missing_fighter_id` → `unknown_fighter` → `not_initiator` → `response_without_action` → `commitment_without_action`;
open: `window_already_open`, `invalid_duration`. `commitment_is_policy_selected` is removed (HG-7).

### 4.7 Lifecycle and views

`open_window()` is `open_window_for(null)`. `open_window_for(duration)` (the session-owner test seam, as in Mount) checks in this order: `window_already_open` →
context errors → `invalid_duration` (`duration` is neither `null` nor an `int`) → `invalid_window_request` (`duration < 0`). `null` means the match interval and
**`0` is a legal zero-time window**. It then advances the clock by `min(duration or interval, remaining)` seconds; if the clock reached 0 the report is `closed` and
nothing opens, otherwise the window id increments and the window opens for the initiator. `submit(window_id, fighter_id, action_id, response_id, commitment, response_commitment)`
accepts an exchange or (empty action) a pass; an empty `commitment` on an exchange means `selected_commitment()` (`MEDIUM`).

**Report schema** (the graph reads these keys; both gateways return the same nested `BjjMatchWindowGateway.Report` class):

| Report | Keys (all present) | Half Guard values |
| --- | --- | --- |
| open, window opened | `closed` (false), `window_open` (true), `free` (false), `advance`, `window_id`, `fighter_id`, `role`, `commitment`, `state` | `advance` = `{"elapsed_seconds": int, "clock_seconds": int}` (no drift or stamina flow); `commitment` = `MEDIUM` |
| open, match ended by time | `closed` (true), `window_open` (false), `free` (false), `advance`, `window_id` (unchanged), `state` | — |
| submit | `window_id`, `fighter_id`, `role`, `kind`, `detail`, `transition`, `state`, `ended` | `kind` ∈ {`"exchange"`, `"reset"`}; `detail` = `{"settlement": <dictionary>}` (the exchange or pass record); `transition` = `Transition.fields()`; `state` = `state_fields()` |

The graph copies `kind` into its `decision_accepted` event (`decision`), so Half Guard events read `exchange` / `reset` where Mount's read `top_exchange` /
`bottom_decision` / `reset`: a deliberate, documented difference. **Conformance** (B1b test, run on both gateways) means: the Report key sets and types above; the
common `state_fields()` key superset below (key names and types, not values); identical results for the shared admission codes in equivalent situations
(`no_open_window`, `stale_window`, `unknown_fighter`, `not_initiator`, `window_already_open`, `invalid_duration`, `invalid_window_request`, `terminal_exchange`);
and a twin test that Half Guard and Mount windows advance by the same seconds under the same interval. `history_fields()`, `detail` and the technique vocabularies are
position-specific and are **not** required to be equal.

Public views are the Mount gateway's set: `window_fields`, `state_fields`, `history_fields`, `controller_fields` (= `{}`), `behavior_fields`, `roles`,
`action_options`, `response_options`, `selected_commitment`, `is_terminal`. `state_fields()` carries the keys F0 and the graph read (`top_stamina`,
`bottom_stamina`, `top_maximum`, `bottom_maximum`, `top_band`, `bottom_band`, `clock_seconds`, `initial_clock`, `initiator`, `exit_destination`, `exit_reason`,
`ended`, `submission_tapped`) plus Half Guard's own (`axis` = tenths ÷ 10 as a view, `axis_tenths`, `band`, `band_name`, `authority`). `carryover_segment()` is **not**
part of the Half Guard gateway (HG-20). F1's Mount-specific labels are not adapted: the opt-in constructor guarantees F1 never meets a Half Guard segment (HG-22).

**View details a developer would otherwise guess.** `top_band` / `bottom_band` are the stamina band strings (`Fresh`, `Working`, `Tired`, `Exhausted`) F0 reads; `authority` is a
fighter id (`""` at axis 0); `band_change_history` entries are `"<before>-><after>"` using the integer bands −2…+2; the commitment histories use `""` for unfunded
(Mount spells it `UNFUNDED`; deliberately different, documented). `action_options(fighter_id)` lists the fighter's own techniques with `available = true`
for the initiator and `available = false, reason = "not_initiator"` otherwise (every technique is always legal in v0: there are no setup or submission gates);
`response_options(action_id)` lists the responder side's three responses, all available, or an error (`illegal_action`, `missing_fighter_id`, context errors) exactly as the
Mount contract reports them.

## 5. Entry specifications

### 5.1 Neutral entry request (B1b) — the only way to build Half Guard (HG-13)

```
{ "role_map": {"top": <id>, "bottom": <id>},
  "fighters": { <id>: {"stamina_current": int, "stamina_maximum": int,
                       "exhaustion_latched": bool, "behavior_remainder_units": int}, ... },   # exactly the two ids, keyed by FIGHTER ID
  "clock": {"initial_seconds": int, "remaining_seconds": int},
  "window": {"last_issued_id": int},
  "interval_seconds": int }
```

`BjjHalfGuardEntry.validate(request)` is pure and fails closed, building nothing, in this order: exact keys and types (no floats; `int` is not `bool`); ids pass
`BjjPositionContract.fighter_ids_error`, are distinct and equal the key set of `fighters`; `role_map` has exactly `top` and `bottom` and is a bijection onto those
ids; stamina `maximum` in `1..MAXIMUM_EXACT`, `current` in `0..maximum`, the latch consistent with the pool's thresholds (`current <= enter` ⇒ latched,
`current >= recover` ⇒ not latched, between ⇒ either); remainders within ±`MAXIMUM_EXACT`; clock `initial` in `1..MAXIMUM_EXACT`, `remaining` in `1..initial`;
`last_issued_id >= 0`; `interval_seconds >= 1`.

`BjjHalfGuardMatch.from_entry(request)` builds: the pool and meter of the fighter assigned to each role (**looked up by fighter id**, so a swapped role map gives
each fighter its own stamina), the clock, `axis_tenths = +5`, `band = 0`, `initiator = "top"` and an empty history. Tests and oracles use the same path; scenario and
normal-match starts are not registered (P-12).

### 5.2 Mount edge adapter (B1c)

`BjjHalfGuardMountEdge.entry_from_record(record, interval_seconds)` is pure: (1) `BjjMountCarryover.validate_segment(record)`; (2) `source_position_id == "mount"`,
`exit == {kind: "exit", raw_destination: "Half Guard", destination_position_id: "half_guard", resolved: true}`, `terminal.ended == true`, `submission_tapped == false`,
`clock.remaining_seconds >= 1`; (3) the edge's role map is the **identity** (`top` ← `fighter_by_role.top`, `bottom` ← `fighter_by_role.bottom`, D1); (4) the record's
role-keyed `fighters.top` / `fighters.bottom` are **re-keyed by fighter id** into the request (POSITION_TOPOLOGY §6.2's hazard: stamina must follow the
fighter, not the role label); (5) `interval_seconds` comes from the caller (HG-25). It reads no Mount object, so it cannot mutate one.

### 5.3 Role maps

The receiver accepts any validated bijection; an edge declares which one is legal. Mount → Half Guard declares the identity map. A future source (Standing after a
takedown) declares its own. No Half Guard rule reads a Mount role label.

### 5.4 Latch restoration (HG-15, T-7 option e)

If the latch is `false`: `BjjStaminaPool.create(current, maximum)`. If `true`: `create(0, maximum)` then `set_current(current)`. From the pool code: `create(0, max)`
latches for every capacity (`0 <= floor(0.25 × max)`), and `set_current` unlatches only at `current >= ceil(0.35 × max)`; a latched pool therefore stays
latched for every `current` the validator accepts as latched. This is the pattern `BjjMountMatch._copy_pool` already uses. The **proof obligation** is still tested (in B1b, because every oracle scenario depends on it):
for capacities `{1, 2, 3, 4, 7, 20, 37, 64, 100}` every (current, latched) pair the validator accepts, and for a large capacity (`9007199254740991`) the boundary grid
`current ∈ {0, 1, enter−1, enter, enter+1, recover−1, recover, recover+1, max−1, max}`: the restored pool equals the source pool field for field and, after fixed
spend/recover grids, stays equal. If any pair fails, fall back to a validated pool factory (option b) and re-propose.

### 5.5 Negative-first tests

Each refusal leaves its inputs untouched and builds nothing: every key missing/extra/wrong type/float/bool-for-int; ids duplicate/empty/padded; role map missing,
extra, duplicate, unknown, same fighter in both roles, not a bijection; stamina out of range, inconsistent latch; clock out of range or `remaining == 0`;
`interval_seconds` zero or negative. The Mount edge's own refusals (wrong source, wrong exit label/destination, unresolved exit, not ended, tapped, remaining 0, invalid
record) belong to B1c; the entry-request refusals and the latch proof belong to B1b. Positive: a grid of valid requests and records; state equality with the input; swapped role map follows the fighter id; determinism.

## 6. B1d — opt-in graph integration (atomic Mount → Half Guard)

### 6.1 Changes to the graph (additive; the only slice that touches qualified code)

* `BjjPositionGraphMatch.create(...)` is **unchanged** and builds a graph with **no receivers**, so every Mount exit halts exactly as today (HG-22).
* New `create_with_receivers(configuration, top_id, bottom_id, receivers)` builds the same graph with a receiver table. **Contract:** `receivers` is a `Dictionary`
  whose keys are a subset of `{"half_guard"}` (the only typed slot) and whose values are `Callable`s taking `(record: Dictionary, interval_seconds: int)` and returning a
  `BjjHalfGuardWindowGateway.Creation`; anything else is refused at construction with `invalid_receivers` and no graph is built. The table is the activation point, so an
  unknown key (for example `open_guard`) can never silently activate anything. At commit the returned object must be a `Creation` whose gateway's
  `roles().fighter_by_role` equals the graph's own fighter ids (POSITION_GRAPH §5 step 3, "identities unchanged"); otherwise the commit is the HG-18 halt.
  `BjjPositionGraphMatch.default_receivers()` returns the Half Guard edge for **future callers** (tests and the later owner flip; no production caller exists today,
  F1 uses `create`); a test may pass a faulty `Callable` to inject a failure. `create_with_receivers(..., {})` must be observably identical to `create`. The cadence is
  captured from the graph's own `configuration.interval` (HG-25).
* The typed `_gateway: BjjMatchWindowGateway` slot stays as the retained Mount segment; a second typed, nullable `_half_guard: BjjHalfGuardWindowGateway` slot holds the
  receiver; every pass-through (`state_fields`, `history_fields`, `controller_fields`, `window_fields`, `roles`, `action_options`, `response_options`,
  `selected_commitment`, `behavior_fields`, `open_window_for`, `submit`) branches on `_half_guard != null` (HG-16). `Report` locals are typed
  `BjjMatchWindowGateway.Report`, which the Half Guard gateway also returns.
* A read-only `active_position_id()` (`"mount"` or `"half_guard"`) is added; `submit()` uses it instead of the hard-coded `POSITION_ID` for the `blocked_transition`'s
  `from_position_id`, the exit classification and `_record_terminal`.
* **Classification (HG-23).** The static `classify_exit_from` is byte-identical and no classification code is added. For Mount, the instance takes the static answer
  (`blocked`, `destination_not_implemented`, `<id>`) and treats it as a `transition` only if `<id>` is a key of the receiver table; `Open Guard` (not in the table) and
  `Reversal` (`unresolved_destination`) stay blocked as today. For an active Half Guard segment the instance calls the same static function with Half Guard's declarations
  (`{"half_guard": {"exits": EXIT_DESTINATIONS, "unresolved": []}}`), so a Half Guard exit halts with `destination_not_implemented` and a correct `from_position_id`; a test pins
  that the static and instance answers differ only by this design.

### 6.2 Protocol (after an accepted decision whose outcome is a receiver exit)

1. Detect by the decision's transition and Mount's `exit_destination`, never by `ended`.
2. Classify (above).
3. Validate and build in isolation: `carryover_segment()` of the retained Mount gateway (the window is closed) → `BjjHalfGuardMountEdge.entry_from_record` →
   `BjjHalfGuardMatch.from_entry` → `BjjHalfGuardWindowGateway`. Nothing is mutated.
4. Commit: set `_half_guard`, append one `transition_committed {from_position_id, to_position_id, label}`. This step cannot fail. The Mount gateway object stays in
   `_gateway`, **frozen**: never advanced, submitted to or exported again (HG-24); its histories and D3-B record stay with it.
5. Open no window.

Event order (fixed, replay-checked): `decision_accepted` → `transition_committed` → later `window_opened`. Global indices stay monotonic; window ids continue
(`last_issued_id + 1`); the transition charges nothing and moves no clock.

**Failure semantics (HG-18).** The Mount exchange is already accepted and settled when step 3 runs, so a failure there cannot be a rollback. It is treated like an
unsupported destination: the exchange stands, the graph halts with `transition_blocked` reason `transition_entry_invalid`, and later commands are refused. This
**amends** the letter of `POSITION_GRAPH.md` §5 and §8 (both list failed construction under "leaves state unchanged"), which cannot be honored once the
exchange is settled; the owner approves the amendment explicitly. It is unreachable for a valid Mount export and is tested through the receiver-table
injection seam.

### 6.3 After the commit

`state_fields()`, `roles()`, `window_fields()`, `action_options()`, `response_options()`, `selected_commitment()`, `behavior_fields()`, `controller_fields()` (`{}`)
and `history_fields()` come from the Half Guard segment. **`carryover_export()` is refused** with `carryover_unsupported_position` while Half Guard is active (HG-20):
a Half Guard source schema is T-9 work. The v1 envelope validator is unchanged and accepts only `destination_not_implemented` / `unresolved_destination` halted reasons,
so a graph halted with `transition_entry_invalid` (Mount still the active segment) is refused by that validator with its existing `inconsistent_graph_segment`; both codes are pinned by B1d tests. A Half Guard exit (`Side Control`, `Open Guard`, `Closed Guard`) halts the graph exactly as
Mount's exits do today. Mount is not re-enterable.

## 7. Independent test-only oracle (D6, HG-19)

**Purpose.** There is no Python Half Guard. The oracle is a *new* Python implementation written from §4 after owner approval, so the GDScript engine is compared with
a second, independently written implementation, not with itself.

**Placement.** `tests/oracles/half_guard_v0.py` (importable module; no production engine; nothing under `src/` is edited), the generator
`GODOT_V1/tests/generate_half_guard_reference.py` (adds `tests/oracles` to `sys.path`; JSONL fixture in the ignored generated directory) and
`tests/test_half_guard_oracle.py` (Python unit tests with hand-computed literals; imports the oracle with the same `sys.path` insertion; whether CI discovery of
`tests/` resolves it is verified in B1b, since `tests/` is not a package). Names are provisional.

**Independence rules.**
1. Written from the approved rules sheet; table-driven, integer tenths; never reads the GDScript.
2. Imports only frozen, position-independent Python primitives (`StaminaCostPolicy`, `ExhaustionPolicy`, grade types) and **never constructs or runs a `MountMatch`**.
3. The three small commitment-settlement functions are re-implemented in the oracle, and a unit test asserts they equal Mount's Python helpers
   (`MountMatch._initiator_commitment_modifier`, `_response_undercommitment_modifier`, `_commitment_grade_transform`, `src/bjj_game/engine/match.py`) over the full
   grade × commitment grid (the one place Mount's private helpers are *called*, as an equality check, with `""` ↔ `None` and ints ↔ `Grade` mapped; the `engine.match` import lives inside that unit test, never in `half_guard_v0.py`).
4. **Latch expectations come from a literal two-state hysteresis model** in the oracle, not from building a pool with the same `create(low)` + `set_current` trick
   HG-15 proposes; the Godot side proves restore-versus-source equivalence separately.
5. **Mutation-sensitivity control:** a development-time check (evidence recorded in the B1b pull request, not a CI step) flips one raw grade and one threshold in a disposable copy of the fixture and confirms that the Godot replay fails.

**Scenario grids (counts measured, never asserted from this document).** Exchange: every axis (81) × every legal band × both initiators × every action × response ×
commitment × a boundary stamina grid (`current ∈ {0, 2, 3, 6, 7, 11, 12}` per fighter, latch enter/recover edges for capacities `1, 3, 4, 37, 100` and a large
one). Lifecycle: windows, passes, timeout, a window that brings the clock to 0. Entry: valid and invalid requests and role maps. Band update: every rule edge.
Non-mutation: every admission code against a full snapshot (pools, axis, band, initiator, history, clock, window state). Precedence: requests with several
simultaneous faults. Each scenario is replayed twice.

**CI mechanics.** The Godot reference test prints and asserts the measured scenario/operation/comparison counts inside the test and ends with the usual
`<name> PASS: N assertions` line, so the existing fail-closed validator (`--name`, `--exit-code`, `--expected-assertions`, exact pin) protects it; the generator step
fails on a missing or empty fixture. The older oracle-replay steps are error-scan-only; the new ones are stricter (a deliberate improvement, not a claim about
the old ones). A negative control proves the entry factory is not reachable from the registry or the graph's default constructor.

**Frozen evidence.** The Mount digest and every Mount fixture stay unchanged; the new fixture is generated, never edited to silence a mismatch.

## 8. Architecture feasibility (keep / adapter / refactor)

Counts quoted are CI-pinned values or are labelled estimates. No unpinned assertion counts are quoted.

| # | Change | Concrete need | Keep | Adapter | Refactor | Recommended | Measurable effect and regression risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | A second position's rules, state, contract | A real receiver | n/a | n/a | n/a | **New classes** (rules, catalog, resolver, match, contract, entry) | ~700–800 new lines (estimate); Mount files touched: 0 |
| 2 | Window lifecycle for Half Guard | Window id, admission order, reports | Copy Mount's gateway logic into a sibling gateway | A shared bookkeeping helper | Abstract base class on the Mount gateway | **Sibling gateway** (~240 lines, duplicated admission order) | A refactor would change a class covered by the gateway, graph, contract, F0 and F1 suites; the copy's risk is divergence, mitigated by a conformance test (views **and** the `Report` schema) run on both gateways, placed in B1b |
| 3 | Graph holds a second segment | Swap the active position | Single `_gateway` (impossible) | `Variant` segment | Segment base class | **Second typed nullable slot** (HG-16) | ~80 lines and a dozen branches in the graph; public API unchanged; `_gateway` and the tests that read it stay valid; two graph property-list pins change and the "one gateway" invariant is revised (§9.3, HG-16) |
| 4 | Default graph behavior | Do not disturb qualified suites or F1 | Commit by default | Opt-in constructor (HG-22) | Rewrite classification | **Opt-in constructor** | Default graphs byte-identical: the existing exit/classification/export/F1 tests are untouched; flipping the default later is one deliberate step |
| 5 | Settlement order | Same order as Mount | Re-implement once in Half Guard | Call a shared function | Extract Mount's settlement into a shared class | **Re-implement** (~60 lines) + oracle | Extraction would touch the exchange oracle's surface (14,631 scenarios / 8,851,698 comparisons) for no behavior gain |
| 6 | Carry-over entry | Preserve state without mutating the source | Hand over the same pools | Rebuild from a neutral request via public API (option e) | New pool factory | **Option e** with an exhaustive equivalence proof; fallback b | 0 new production API if the proof holds |
| 7 | F0/F1 read access | Work with a second position | Mount-specific adapter | Common `state_fields()` key set (§4.7) | A general snapshot interface | **Common key set**, no adapter change | F0 unchanged; F1 stays Mount-only because default graphs never hold Half Guard |
| 8 | Registry use | Validate destination ids | None | Test pins ids ⊆ registry | Derive constants from the registry | **Test pin** | No production edit |

## 9. Slice plan (HG-21)

### 9.1 B1b — Half Guard mechanics (after owner approval)

Files (new only): `scripts/positions/half_guard/{half_guard_rules,half_guard_catalog,half_guard_resolver,half_guard_match,half_guard_entry,half_guard_contract,half_guard_window_gateway}.gd`
(+ `.gd.uid`), `tests/test_half_guard_rules.gd`, `tests/test_half_guard_reference.gd`, `tests/test_half_guard_conformance.gd` (views and `Report` against the Mount gateway),
`tests/oracles/half_guard_v0.py`, `tests/test_half_guard_oracle.py`, `GODOT_V1/tests/generate_half_guard_reference.py`, `docs/HALF_GUARD_V0_RULES.md`, and one workflow
step per new Godot suite through the existing log validator (exact measured pins); no routing change. Negative-first order: refusals → catalog pins → rules/bands →
resolution → lifecycle → entry → oracle replay → determinism.

Definition of done: oracle reviewed and accepted first; Godot engine matches it with zero mismatches; the entry-request refusals (§5.5) and the latch equivalence proof (§5.4) pass; the conformance test passes; every Mount pin and suite unchanged
(256,992 / 431 / 750 / 1,036 and the Python parity steps); `git diff --check`, workflow validation; exact-head CI (Godot + Python 3.11/3.13). Python changes route as
shared, so full qualification runs on that PR (expected; not shortened).

### 9.2 B1c — Mount edge adapter and equivalence proofs

New: `half_guard_mount_edge.gd`, `tests/test_half_guard_mount_edge.gd`. Changes no existing file. DoD: the Mount edge refusals (§5.5), role re-keying (state follows the fighter id),
source-view equality before/after (the Mount gateway and graph views are identical after building an entry), zero Mount change.

### 9.3 B1d — opt-in graph integration

Changes: `graph_match.gd` only (second slot, receiver table, `create_with_receivers`, `active_position_id()`, commit, branched pass-throughs, export refusal), plus
documentation. Because `create` is unchanged:

* **Untouched by design:** `test_position_graph_classification.gd` (the static classifier is byte-identical), `test_position_registry.gd` (including its pinned
  `classify_exit_from("mount", "Half Guard")` answer and the 431 pin), `test_mount_practice.gd` and its 1,036 pin (F1 builds default graphs; its `_halted_controller("Half Guard")`
  and every `_gateway`/`graph._graph` use keep working; its "no public name contains gateway" check still passes with the three new public names), `test_position_graph_boundaries.gd` apart from the one pin below (exit search, lockstep tallies), `test_window_gateway_boundaries.gd`,
  `test_position_contract_boundaries.gd`, `test_mount_slice.gd` (A3d pins), `test_fighter_foundation.gd`, and the Mount/stamina/exchange/lifecycle/D3-B oracles.
* **Changes on purpose (two pins, verified by reading the tests):** (1) `test_carryover_export.gd` (~line 560) pins the graph's exact private property list
  `["_blocked", "_events", "_gateway", "_status", "_terminal_reason"]`; (2) `test_position_graph_boundaries.gd` (~lines 141–148) pins the same list under the name
  "graph holds only gateway, status, events, blocked, terminal reason" and asserts "one gateway, no second owner". Adding `_half_guard`, the receiver table and the
  cadence changes both, and HG-16 revises that invariant (the retained Mount gateway is still the only *Mount* owner; Half Guard has its own). The documentation text that says Half Guard is
  unimplemented stays true for default graphs and gains a note for opt-in graphs (`POSITION_GRAPH.md` §§5, 8 amendment per HG-18; `CARRYOVER_EXPORT.md` v1 note; `F1_MOUNT_PRACTICE.md` unchanged).
* **New tests:** whole-graph equality before/after for every refusal; transition tests (continuity of clock, pools, latches, remainders; the frozen Mount gateway's
  views and histories identical afterwards; zero charge; consumed window; no automatic window; event order and monotonic indices; window id continuity; token counts
  unchanged); Open Guard and Reversal still halt on an opt-in graph; every Half Guard exit halts with `destination_not_implemented` and `from_position_id = half_guard`; failure injection
  (HG-18); replay twice over the existing seed/axis/stamina grid; lockstep against a twin driven through the bare Mount gateway up to the exit; **a default graph with the
  same inputs halts at the same event index as before** and **`create_with_receivers(..., {})` is observably identical to `create`** (the opt-in proofs); a bad receiver table
  (`invalid_receivers`: non-dictionary, unknown key, non-`Callable` value) builds no graph; a wrong-identity or non-`Creation` receiver result is the HG-18 halt; after the commit a stale or duplicate
  window id, a Mount technique id, an unknown fighter and an identity mismatch are refused with whole-graph equality before and after; commands after a Half Guard halt are refused;
  a Half Guard timeout is a terminal outcome and never an exit; F1's controller is never given an opt-in graph.

Owner-flip of the default (making `create` commit) is a separate, later authorization that would carry the larger test update (classification ~20 assertions, exit-search
and export cases, the F1 blocked-state tests and the 431/1,036 pins).

### 9.4 Later slices (not proposed for approval now)

B1e: a measured stamina/recovery rule for Half Guard (pre-registered, like D3-B); B1f: Sweep/Wrestle-Up/Backstep with owner-approved landings; Open Guard, Closed Guard
and Side Control receivers; return routes and segment identity (P-11); a graph envelope v2 and carry-over export for non-Mount sources.

## 10. Prototype evidence (throwaway scripts, reproduced in the appendices)

Appendix A encodes §4.1–§4.5 **for raw grade + positional modifier only** (it omits the exhaustion, magnitude and undercommitment steps of Q5) in integer tenths and
checks, without any Godot or repository code:

* every axis in −40…+40 has a legal band and every band rule lands on a legal axis/band pair;
* every action has a counter (≤ −1) and a favorable response (≥ +1);
* breadth-first search over (axis, band, initiator) with free choices: 42 reachable states; the earliest exits are `Closed Guard` in 2 windows, `Side Control` in 3 and
  `Open Guard` in 4 (reachable only with cooperating or self-harming opponents);
* with a responder who always plays the best counter, no exit is reachable;
* 2,000 uniformly random 60-window games (seeds 0…1999) from the entry: `Side Control` 880, `Closed Guard` 671, `Open Guard` 413, timeout 36; median exit window 12–14.
  The random sampler ignores stamina, commitment and the real clock, and the 60-window horizon is arbitrary;
* stamina: with MEDIUM exchanges and no recovery a fresh fighter reaches the Exhausted latch at window 11.

Appendix B encodes the full grade pipeline of Q5 (shared position-independent functions transcribed from `BjjCommitmentSettlement` / `BjjExhaustionPolicy`) and finds that
the best final grade reachable from a raw −2 counter is `0` (CONTESTED) and from a raw −1 counter is `+1` (SUCCESS): the break-capable actions cannot beat their −2
counters, while ordinary counters can be lifted by exhaustion and under-commitment.

The first draft of the Recover Guard row had no `+1`, which made `Open Guard` unreachable; the prototype exposed it before the proposal was finalized. These numbers
describe the **proposed** tables only. They are not parity evidence, not a balance study and not an oracle; the appendices let anyone re-run them.

## 11. Risks and unresolved items

* **Stamina economy (highest risk, HG-6).** Without recovery, Half Guard is a mechanics-and-transition milestone, not a balanced position (Q4 lists the consequences).
* **New content.** Response names, the 15 grades, the break lines and the Recover Guard split are proposals that define gameplay; they need owner review, not only engineering review.
* **Duplicated settlement and admission order** (§8 rows 2 and 5) rely on the oracle and the conformance test, not on shared code.
* **Entry strength is flat** (fixed +5). Distinguishing SUCCESS from STRONG_SUCCESS needs a schema decision.
* **Deliberate v0 simplifications versus the Guide:** neutral is not a break (HG-3), initiative is strict alternation (HG-5), authority is reported only (HG-4).
* **Absent by design:** return to Mount, Sweep, Wrestle-Up, Backstep, opening-triggered initiative, behaviors/drift/RECOVER/D3-B, a graph envelope v2.
* **Opt-in receivers (HG-22)** keep every qualified suite and F1 unchanged but mean a "Half Guard commits" graph exists only through the new constructor until the owner flips the default.
* **Graph protocol amendment (HG-18)** edits the letter of `POSITION_GRAPH.md` §5/§8 when B1d lands.

## Appendix A — Reachability and consistency prototype (verbatim)

```python
"""Throwaway feasibility prototype of the PROPOSED Half Guard v0 numbers (not committed, not an oracle).
Integer tenths everywhere. Checks internal consistency and exit reachability."""
import itertools
from collections import deque

LO, HI = -40, 40
PASS_LINE, OUT_LINE = 30, -30
ENTRY = 5


def shift(g, s):
    return max(-2, min(2, g + s))


def initial_band(a):
    m = abs(a)
    sign = 1 if a > 0 else -1
    return 0 if m < 10 else sign * (1 if m < 25 else 2)


UP = {(0, 1): 12, (1, 2): 27, (-1, 0): -8, (-2, -1): -23}      # moving toward Top: a >= threshold
DOWN = {(2, 1): 23, (1, 0): 8, (0, -1): -12, (-1, -2): -27}     # moving toward Bottom: a <= threshold


def update_band(a, band):
    while True:
        nxt = None
        for (b0, b1), t in UP.items():
            if band == b0 and a >= t:
                nxt = b1
        for (b0, b1), t in DOWN.items():
            if band == b0 and a <= t:
                nxt = b1
        if nxt is None:
            return band
        band = nxt


def can_have(a, band):
    return {0: -12 < a < 12, 1: 8 < a < 27, 2: a > 23, -1: -27 < a < -8, -2: a < -23}[band]


# consistency: every axis has at least one legal band, and update_band lands on a legal band
for a in range(LO, HI + 1):
    assert any(can_have(a, b) for b in (-2, -1, 0, 1, 2)), a
    for b in (-2, -1, 0, 1, 2):
        if can_have(a, b):
            assert can_have(a, update_band(a, b)), (a, b)

TOP_RAW = {  # Top initiator, grade from Top's point of view; responses = Bottom's
    "crossface": {"hip_frame": 1, "underhook_fight": -1, "knee_shield": 0},
    "flatten": {"hip_frame": -1, "underhook_fight": 1, "knee_shield": 1},
    "knee_slice": {"hip_frame": 0, "underhook_fight": 2, "knee_shield": -2},
}
BOT_RAW = {  # Bottom initiator, grade from Bottom's point of view; responses = Top's
    "underhook": {"head_control": -1, "hip_pressure": 0, "knee_pin": 1},
    "recover_guard": {"head_control": 2, "hip_pressure": 1, "knee_pin": -2},
}


def pos_mod(initiator, band):
    if initiator == "top" and band == -2:
        return -1
    if initiator == "bottom" and band == 2:
        return -1
    return 0


def step(a, band, initiator, action, response):
    raw = (TOP_RAW if initiator == "top" else BOT_RAW)[action][response]
    g = shift(raw, pos_mod(initiator, band))
    delta = 10 * g if initiator == "top" else -10 * g
    proposed = a + delta
    exit_label = ""
    if initiator == "top" and action == "knee_slice" and g >= 1 and proposed >= PASS_LINE:
        exit_label = "Side Control"
    if initiator == "bottom" and action == "recover_guard" and g >= 1 and proposed <= OUT_LINE:
        exit_label = "Closed Guard" if g == 2 else "Open Guard"
    a2 = max(LO, min(HI, proposed))
    return a2, update_band(a2, band), g, exit_label


# BFS over (axis, band, initiator): cooperative play = both players choose freely (reachability).
start = (ENTRY, initial_band(ENTRY), "top")
dist = {start: 0}
queue = deque([start])
first_exit = {}
while queue:
    a, band, who = queue.popleft()
    nxt_who = "bottom" if who == "top" else "top"
    table = TOP_RAW if who == "top" else BOT_RAW
    for action in table:
        for response in table[action]:
            a2, b2, g, ex = step(a, band, who, action, response)
            if ex:
                first_exit.setdefault(ex, dist[(a, band, who)] + 1)
                continue
            state = (a2, b2, nxt_who)
            if state not in dist:
                dist[state] = dist[(a, band, who)] + 1
                queue.append(state)
print("entry", start, "band names -2..2 = BOTTOM_CONTROL..TOP_CONTROL")
print("states reachable under cooperative play:", len(dist))
print("earliest exit (windows, both players cooperating):", first_exit)

# Property mirrored from Mount: every action has a response giving the initiator <= -1.
for name, table in (("top", TOP_RAW), ("bottom", BOT_RAW)):
    for action, row in table.items():
        assert min(row.values()) <= -1, (name, action)
        assert max(row.values()) >= 1, (name, action)
print("every action has a counter (<= -1) and a favourable response (>= +1)")

# Perfect-counter responder: the initiator can never exit (same structural property as Mount).
def best_counter_exits():
    seen = {start}
    queue = deque([start])
    exits = set()
    while queue:
        a, band, who = queue.popleft()
        nxt_who = "bottom" if who == "top" else "top"
        table = TOP_RAW if who == "top" else BOT_RAW
        for action, row in table.items():
            response = min(row, key=lambda r: (row[r], r))
            a2, b2, g, ex = step(a, band, who, action, response)
            if ex:
                exits.add(ex)
                continue
            state = (a2, b2, nxt_who)
            if state not in seen:
                seen.add(state)
                queue.append(state)
    return exits, len(seen)
print("exits reachable if the responder always plays the best counter:", best_counter_exits())

# Uniformly random responders: Monte-Carlo-free exact expectation is overkill; sample deterministic grid of seeds.
import random
def run(seed, windows=60):
    rnd = random.Random(seed)
    a, band, who = start
    for w in range(1, windows + 1):
        table = TOP_RAW if who == "top" else BOT_RAW
        action = rnd.choice(sorted(table))
        response = rnd.choice(sorted(table[action]))
        a, band, g, ex = step(a, band, who, action, response)
        if ex:
            return ex, w
        who = "bottom" if who == "top" else "top"
    return "timeout", windows
results = {}
for seed in range(2000):
    ex, w = run(seed)
    results.setdefault(ex, []).append(w)
for ex, ws in sorted(results.items()):
    print("random play: %-12s %4d of 2000, median window %s" % (ex, len(ws), sorted(ws)[len(ws) // 2]))

# Stamina economy of one exchange under the position-independent policy (costs 3/7/12, v04, Rule 1 ON).
COST = {"LOW": 3, "MEDIUM": 7, "HIGH": 12}
cap, enter, recover = 100, 25, 35
cur_i = cur_r = 100
trace = []
for w in range(1, 40):
    cur_i, cur_r = cur_r, cur_i  # alternate roles
    cost_i = min(cur_i, COST["MEDIUM"]) if cur_i >= 7 else (3 if cur_i >= 3 else 0)
    cur_i -= cost_i
    cost_r = 0 if cost_i == 0 else min(cur_r, COST["MEDIUM"])
    cur_r -= cost_r
    trace.append((w, cur_i, cur_r))
    if min(cur_i, cur_r) <= enter:
        print("with MEDIUM exchanges and no recovery, the first fighter reaches the Exhausted latch at window", w, trace[-1])
        break
```

## Appendix B — Full-pipeline counter check (verbatim)

```python
"""Throwaway check: can an initiator reach SUCCESS against a counter once exhaustion and commitment settlement apply?
Mirrors the shared position-independent functions (BjjCommitmentSettlement / BjjExhaustionPolicy) from the rules text."""
import itertools

def shift(g, s): return max(-2, min(2, g + s))
ORDER = ["LOW", "MEDIUM", "HIGH"]
def rank(e): return ORDER.index(e) + 1 if e in ORDER else 0
def magnitude(e, g):
    if e == "HIGH":
        if g == 1: return 1
        if g == -1: return -1
    if e in ("LOW", ""):
        if g == 2: return -1
        if g == -2: return 1
    return 0
def under(i, r): return 1 if rank(r) < rank(i) else 0

best = {}
for raw in (-2, -1):
    top = -9
    for pos, exh, ie, re_ in itertools.product((-1, 0), (-1, 0, 1), ("", "LOW", "MEDIUM", "HIGH"), ("", "LOW", "MEDIUM", "HIGH")):
        g_pos = shift(raw, pos)
        g_exh = shift(g_pos, exh)
        final = shift(shift(g_exh, magnitude(ie, g_exh)), under(ie, re_))
        top = max(top, final)
    best[raw] = top
print("best final grade reachable from a raw -2 counter:", best[-2])
print("best final grade reachable from a raw -1 counter:", best[-1])
```
