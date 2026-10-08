# BJJ Game — Master Game Development Guide v10.3
## Merged Post-Mount Source of Truth — Decision Timers and Technique Memories Addendum

**Status:** Active master design + development roadmap  
**Supersedes:** `BJJ Game Concept — Current Design Recap v9 — Mount v0 CODE-READY FREEZE` as the project-wide planning document  
**Keeps:** durable v9 game rules, character/belt/roguelike concepts, submission philosophy, scoring/stalling concepts, deterministic design  
**Replaces:** obsolete Mount-v0-only implementation scaffolding and the AI-first development direction  
**Current development philosophy:** **Breadth first → human play → roguelike → frontend → depth/advanced AI**

**v10.2 design blueprint (2026-10-08):** v10.1 includes Dual-clock decision windows; memory-inspired technique presentation and roguelike rewards. These are design direction and provisional defaults, **not implemented gameplay**. The timing/session layer and memory presentation must not override the deterministic simulation core. The choice to port Python to Godot/GDScript is under evaluation, not approved or completed.

**v10.3 persistent-career adoption (2026-10-08):** One persistent fighter, belt-promotion runs, permanent belt/mastered-memory retention, discovered-impression retention, defeat-triggered Memory Fracture, and success-protected unfinished progress are accepted *design rules*. Exact balance, match counts, belt requirements, and Godot migration remain unimplemented/open. Section 58C controls where earlier memory-persistence language differs.

---

# 0. How to Use This Document

This is the single master guide for:

- what the game is;
- what already exists;
- what is incomplete;
- what has been intentionally deferred;
- what the first complete playable game requires;
- what order the backend should be built in;
- what systems must exist before frontend;
- what systems can wait.

When a system is completed, update its status here.

## Status Legend

- ✅ **Implemented / usable**
- 🟡 **Implemented partially / needs generalization**
- 🔵 **Designed direction / not yet implemented**
- ⚪ **Important but still needs design**
- ⏸ **Intentionally deferred**
- ❌ **Do not pursue right now**

---

# 1. Game Identity

The game is a:

> **Deterministic tactical Brazilian Jiu-Jitsu roguelike built around continuous simulated matches, slow-motion decision windows, broad positional struggles, style-driven physical identity, belt-driven knowledge, temporary run builds, staged submissions, and meaningful positional transitions.**

The game should reward:

- BJJ understanding;
- positional awareness;
- setup recognition;
- strategic timing;
- stamina management;
- risk management;
- chaining;
- adaptation;
- opponent scouting;
- build construction across a roguelike run.

The game should **not** primarily reward:

- twitch reactions;
- button mashing;
- fighting-game combo memorization;
- arbitrary hidden move priority;
- frame-perfect execution;
- hidden dice deciding whether correctly built techniques randomly work.

---

# 2. Current Project Reality

## 2.1 What is already strong

### Core match engine
✅ Five-minute simulated match clock foundation  
✅ Continuous simulated time rather than exchange-count turns  
✅ Event-driven decision windows  
✅ Initiative  
✅ Deterministic action resolution  
✅ Stamina and exhaustion  
✅ LOW / MEDIUM / HIGH commitment  
✅ Positional struggle axis and visible bands  
✅ Result grades  
✅ Exit-map concept  
✅ Stalling infrastructure  
✅ Submission-state infrastructure  
✅ Deterministic replay / regression checking  
✅ Batch/simulation infrastructure  

### Mount
✅ Mount is the first mature position.

Mount has already proven the engine can represent:

- positional authority;
- top/bottom asymmetry;
- deliberate actions;
- responses;
- positional drift;
- stamina;
- exhaustion/recovery;
- initiative;
- escapes;
- submission attacks;
- exit destinations;
- stalling;
- deterministic resolution.

**Mount is now the reference position, not the scope of the game.**

### AI
🟡 The AI/evaluator infrastructure is considerably more mature than the rest of the playable game.

Current direction:

- finish the currently selected fourth TE-2 authoritative surface;
- stop the campaign at 4 completed surfaces;
- preserve the partial evidence;
- close TE-2 as **OPEN / INCOMPLETE**;
- do not promote TACTICAL_V2;
- pause advanced tactical-AI research;
- use a simpler stable opponent policy while game breadth is built.

---

# 3. Development Correction

The project went too deep on one node—Mount—and on AI qualification before building enough of the actual grappling world.

That work is still valuable because the mechanics created for Mount are reusable.

## Previous pattern

```text
Mount
→ refine Mount
→ evaluate AI
→ refine evaluator
→ more simulation
→ more AI measurement
```

## New pattern

```text
Generalize Mount
→ build the 10-position graph
→ connect transitions
→ play a full human-controlled match
→ build fighter identity
→ build the roguelike run
→ start frontend
→ deepen content
→ improve AI later
```

## New development rule

> **Breadth before depth.**

For every new position:

1. define the tactical problem;
2. add 3–5 meaningful actions for each side;
3. add meaningful responses;
4. connect the position to neighboring nodes;
5. support stamina/commitment/setup/submission hooks;
6. test it;
7. move on.

Do **not** spend months perfecting one position before the complete graph exists.

---

# 4. Match Structure

The default match is:

```text
5:00 GAME TIME
```

This is **simulated grappling time**, not necessarily five real-world minutes.

There is no fixed number of turns.

A full match should be capable of flowing through:

- Standing;
- takedown entries;
- Guard;
- Half Guard;
- Side Control;
- Mount;
- Back Control;
- Turtle;
- Front Headlock;
- Leg Entanglement;
- sweeps;
- passes;
- reversals;
- scrambles;
- submission threats;
- escapes;
- transitions.

The player should lose because of BJJ decisions and match conditions—not because an arbitrary turn counter expired.

---

# 5. Presentation and Decision Model

## 5.1 Continuous presentation, event-driven decisions

At normal speed, fighters continue broad tactical behaviors.

Example behaviors:

```text
HOLD
PRESSURE
RETAIN
ESCAPE
DISENGAGE
HUNT SUBMISSION
CONSERVE
```

Those behaviors can create small predictable drift in:

- positional control;
- setup progress;
- stamina;
- submission danger;
- advancement/stalling state.

Meaningful events open decision windows.

## 5.2 Slow-motion decision windows

Conceptually:

```text
NORMAL SPEED
↓
Meaningful event
↓
SLOW-MOTION PRESENTATION
↓
MATCH CLOCK PAUSES
↓
Player reads situation
↓
Player chooses
↓
Choice locks
↓
MATCH CLOCK RESUMES
```

The player should not be punished for thinking slowly.

**Character Speed affects the fighter, not the amount of real-world time the human gets to decide.**

## 5.2a Two Clocks: Simulated Match Time vs Real-World Decision Time

**Status: 🔵 Design direction, not implemented.**

Two fundamentally different clocks must never be conflated:

1. **Match clock:** simulated BJJ time (normally 5:00), which advances during grappling simulation and remains **paused during player decision windows**.
2. **Decision deadline:** real-world wall-clock budget to lock a choice in a human decision window. It counts down while match simulation is paused, and it does **not** deduct simulated match seconds.

Provisional mode policy (subject to playtesting):

| Mode | Initial decision limit | Proposed expiry behavior |
|---|---|---|
| Solo / story | Unlimited by default | No automatic timeout |
| Casual PvP | 45 seconds per player/decision | Deterministic safe, legal fallback |
| Ranked PvP | 30 seconds per player/decision | Deterministic fallback; warn after 2 consecutive missed decisions, forfeit after 3 consecutive misses |
| Private match | Configurable | Agreed rules, validated by match host |

The **30-second figure is for competitive multiplayer**, not a universal timer for solo play. PvP itself remains deferred until single-player works. The game may later add an optional finite time bank, but must not add it without testing the simpler deadlines first.

**Decision-window rules:**

- The owner of the session clock (authoritative server in PvP) starts a deadline when a legal decision becomes actionable; it is not affected by rendering FPS, animation speed, deliberate lag, repeated invalid input, or reopening a menu.
- Time spent in an opponent's separate response window does not consume one's own deadline. Each human gets their applicable budget when they must act.
- In simultaneous hidden-choice windows (e.g. Standing), each player gets a deadline, locks secretly, and choices reveal only after both have locked or expired. The first player to lock is not penalized while waiting.
- An expired choice is resolved by a **published, deterministic, situation-aware legal fallback**. It is never an arbitrary technique, random attack, free escape, or automatic submission tap; emergency submission defense must have an explicit timeout policy that never fabricates player consent to `TAP` or `REFUSE`.
- A defaulted choice counts as a missed decision even if the fallback is tactically helpful. Counters for consecutive misses reset on a valid, on-time decision; the precise ranked forfeit policy must be validated for disconnect/reconnect cases.
- A player may inspect the position and all currently legal techniques during the countdown. Opening a technique detail or memory description never restarts the deadline.
- Offline pause / accessibility options and local solo settings can suspend or relax the deadline. PvP accommodations and reconnect policy need explicit fairness rules before shipping online.
- Automatic choice locking is session orchestration, **not** BJJ stalling. Match-rule penalties for lack of positional progress remain separate.

**Architecture:** define a proposed `DecisionTimerPolicy` / `DecisionDeadline` at the player-session boundary, **not** in `PositionContract`, `MountMatch`, or rendering code. The simulation consumes a resolved legal player command; it must not read wall-clock time to calculate positional outcomes. Deadline timing, server timestamps, and timeout commands are recorded in session/replay metadata when necessary. The deterministic core replays the final resolved commands, not wall-clock scheduling.

**Player-facing UX:** show an always-legible 5:00 simulated match clock and a separate contextual decision countdown; communicate locked/awaiting/timeout states clearly. Timeout does not spend simulated match time. Do not turn this into a reflex game; expose technique details efficiently and test whether 30 seconds is fair with real players.

## 5.3 Manual Read / Act

The player may proactively request a decision window when appropriate.

A manual window may:

- inspect tactical state;
- change broad behavior;
- initiate a legal technique when an opening/setup/initiative permits it.

Manual windows must have an in-game cost or constraint so the player cannot pause every simulated instant.

The exact current cost remains tunable.

## 5.4 Fast-forward

Stable uneventful stretches should accelerate toward the next meaningful event when:

- no meaningful setup is developing;
- no major threat is growing;
- no scoring/stalling threshold is near;
- no major stamina event is happening;
- no transition is developing.

The player should still understand what happened.

---

# 6. Strategic Timing

Being “late” means:

> You allowed the opponent to build too much positional or submission progress.

It should **not** mean:

> You failed a reflex test.

Earlier reactions should usually offer:

- more options;
- safer options;
- lower stamina cost.

Late reactions should usually offer:

- fewer options;
- more desperate techniques;
- higher stamina cost;
- worse positional consequences.

---

# 7. Universal Position Model

Mount should be generalized into a common **Position Contract**.

Each position must define:

```text
PositionContract

id
roles / perspectives
substate

control_axis
visible_band
behavior_drift

legal_actions(side, state)
legal_responses(action, state)

commitment_options
    LOW
    MEDIUM
    HIGH

setups
submission_routes

resolve(action, response, commitment)

result_grade
    STRONG_FAILURE
    FAILURE
    CONTESTED
    SUCCESS
    STRONG_SUCCESS

exit_map(action, result_grade)

stalling_rules
scoring_hooks
transition_rules
```

## Position Contract Definition of Done

- Mount runs through the contract without changing its intended behavior.
- A second position can use the contract without copying the Mount engine.
- Transitions are explicit.
- Submission hooks are position-independent.
- Human/frontend APIs do not access Mount-specific internals.

---

# 8. Position Graph v1 — 10 Core Positions

The first complete BJJ graph uses exactly ten top-level nodes.

| # | Position | Status | Main tactical problem |
|---|---|---|---|
| 1 | **Standing** | 🔵 | Entry, grips, takedown, guard pull, counter-wrestling |
| 2 | **Closed Guard** | 🔵 | Bottom offense/sweeps vs Top posture/open/pass |
| 3 | **Open Guard** | 🔵 | Retention/sweep/wrestle-up vs passing |
| 4 | **Half Guard** | 🔵 | Recover/sweep/wrestle-up vs flatten/pass |
| 5 | **Side Control** | 🔵 | Pin/advance/submission vs recovery |
| 6 | **Mount** | ✅ | Control/submission vs escape |
| 7 | **Back Control** | 🔵 | Choke/control vs hand-fighting/escape |
| 8 | **Turtle** | 🔵 | Breakdown/back take vs recovery/stand |
| 9 | **Front Headlock** | 🔵 | Choke/go-behind vs posture/recovery/reshoot |
| 10 | **Leg Entanglement** | 🔵 | Leg control/sweep/submission vs escape |

---

# 9. What Is Not a Position Node

These are actions, overlays, or transient resolution states:

- takedown;
- sweep;
- pass;
- reversal;
- submission;
- scramble.

Example:

```text
Standing
  ↓ Single Leg
Half Guard
  ↓ Knee Slice
Side Control
  ↓ Advance
Mount
```

Positions are the **nodes**.

Techniques, defenses, and transitions are the **edges**.

---

# 10. Subpositions

Do not create a separate engine for every BJJ configuration.

Initially represent these as substates.

## Open Guard
- Butterfly
- De La Riva
- Reverse De La Riva
- Single-Leg X

## Side Control
- Standard Side Control
- North-South
- Knee-on-Belly

## Mount
- Low Mount
- High Mount
- Technical Mount

## Leg Entanglement
- Ashi
- 50/50
- later advanced entanglements

Promote a subposition to a full node only when human play demonstrates that it requires significantly different mechanics.

---

# 11. Position Content v0

The first implementation should prioritize **different tactical problems**, not encyclopedic move lists.

## 11.1 Standing

### Attacks / proactive choices
- Single Leg
- Double Leg
- Body Lock
- Snapdown
- Guard Pull
- Disengage / Reset

### Responses / counters
- Sprawl
- Whizzer
- Pummel
- Frame
- Counter-shot
- Guillotine threat
- Concede safer ground position

### Destinations
- Standing
- Closed Guard
- Open Guard
- Half Guard
- Turtle
- Front Headlock
- Side Control

### Missing design/implementation
- standing control/balance axis;
- grip/entry substates;
- takedown result grades;
- simultaneous neutral choices;
- guard-pull resolution;
- mat returns;
- counter-wrestling.

---

## 11.2 Closed Guard

### Bottom
- Hip Bump Sweep
- Scissor Sweep
- Arm Drag
- Triangle
- Armbar
- Stand / Wrestle Up

### Top
- Posture
- Stand to Open
- Pressure Open
- Stack
- Pass initiation
- disengagement where legal

### Destinations
- Open Guard
- Half Guard
- Side Control
- Mount after sweep/reversal
- Back Control
- submission track

---

## 11.3 Open Guard

### Bottom
- Guard Retention
- Butterfly Sweep
- Wrestle-Up
- Arm Drag
- Single-Leg X entry

### Top
- Toreando
- Knee Cut
- Over-Under
- Pressure Pass
- disengage / reset distance

### Destinations
- Standing
- Half Guard
- Side Control
- Back Control
- Leg Entanglement

---

## 11.4 Half Guard

### Bottom
- Underhook
- Recover Guard
- Sweep
- Wrestle-Up
- deeper half-guard entry later

### Top
- Crossface
- Flatten
- Knee Slice
- Backstep
- Advance to Side Control

### Destinations
- Guard
- Side Control
- Mount
- Turtle
- Back Control
- Front Headlock

---

## 11.5 Side Control

### Top
- Stabilize
- Transition to Mount
- Expose Back
- Kimura route
- Armbar route

### Bottom
- Shrimp
- Recover Guard
- Recover Half Guard
- Underhook Escape
- Bridge
- Turn to Knees
- Reversal

### Destinations
- Guard
- Half Guard
- Turtle
- Mount
- Back Control

---

## 11.6 Mount

✅ Mature reference node.

The exact current Mount action catalog is maintained by source code/tests rather than duplicated here.

Required future work:

- implement Mount through PositionContract;
- retain current deterministic semantics;
- expose generic transitions/submission hooks;
- preserve regression coverage.

---

## 11.7 Back Control

### Attacker
- Seatbelt / retain
- Hand Fight
- Arm Trap
- Rear Naked Choke
- Transition to Mount

### Defender
- Hand Fight
- Clear Hook
- Put Shoulders to Mat
- Turn Inward
- Emergency Submission Defense

### Destinations
- Mount
- Guard
- Turtle
- submission

---

## 11.8 Turtle

### Attacker
- Back Take
- Breakdown
- Mat Return
- Front Headlock
- Hold / Ride

### Defender
- Stand
- Sit-Out
- Granby
- Recover Guard
- Reversal

### Destinations
- Standing
- Guard
- Back Control
- Front Headlock
- Side Control

---

## 11.9 Front Headlock

### Attacker
- Guillotine
- D'Arce route
- Anaconda route
- Go-Behind
- Breakdown

### Defender
- Hand Fight
- Posture
- Reshoot
- Stand
- Recover Guard

### Destinations
- Turtle
- Back Control
- Side Control
- Standing
- submission

---

## 11.10 Leg Entanglement

### Attacker
- Straight Ankle Lock
- Sweep
- Off-Balance
- Positional Upgrade
- Control

### Defender
- Clear Knee Line
- Stand
- Turn Out
- Counter-position
- Disengage

### Destinations
- Open Guard
- Standing
- top position
- submission

Advanced heel-hook legality belongs to belt/ruleset design rather than the first universal move set.

---

# 12. Broad Two-Sided Struggle Axis

Every established position should use a broad control struggle instead of requiring the player to manage every grip and body part.

Conceptually:

```text
PLAYER 2 CONTROL              PLAYER 1 CONTROL

Locked Strong Stable Loose | Neutral | Loose Stable Strong Locked
```

Internal range:

```text
-4.0 ... 0.0 ... +4.0
```

The axis means:

> **Who has positional authority, and how secure is it?**

The context changes by position:

- Mount control vs escape;
- Guard pass vs retention/offense;
- takedown finish vs defense;
- Turtle breakdown vs recovery;
- Back retention vs escape;
- Leg-entanglement control vs disengagement.

## Core rules to preserve

- Drift can create opportunities.
- Drift should not automatically choose a new position.
- Deliberate action causes major transitions.
- Crossing Neutral means the current positional struggle breaks.
- The action/result determines the destination through an Exit Map.
- Local success does not necessarily equal escaping/winning the position.
- Visible bands use hysteresis to prevent flicker.
- Locked means strong control of the **current** position, not automatic progression.

Mount-specific numeric edge rules remain regression details in the Mount implementation/tests, not global game-design requirements.

---

# 13. Behavior Drift

Broad behavior should have mechanical purpose.

Examples:

```text
PRESSURE vs ESCAPE
→ control pressure rises
→ stamina cost

HUNT SUBMISSION vs ESCAPE
→ submission setup may grow
→ positional security may weaken

CONSERVE vs PRESSURE
→ stamina recovers
→ opponent may gain position

RETAIN vs PASS
→ guard axis changes based on attributes, setup, technique and style
```

Drift should be:

- slow;
- predictable;
- readable;
- strong enough to create events;
- weak enough that major transitions still require meaningful actions.

---

# 14. Exit Maps

Crossing Neutral does not itself select the next node.

The action that broke the position plus the result grade selects the destination.

Example:

```text
Mount — Elbow Escape

SUCCESS
→ Half Guard

STRONG SUCCESS
→ Open Guard
```

Another example:

```text
Standing — Single Leg

STRONG SUCCESS
→ Side Control

SUCCESS
→ Top Half Guard

CONTESTED
→ Turtle / Scramble resolution

FAILURE
→ Standing

STRONG FAILURE
→ Opponent Front Headlock
```

Every technique that can break a position must have explicit destinations.

---

# 15. Initiative Model

Initiative is **triggered**, not permanently owned by:

- top player;
- player ahead on the axis;
- player with better stats.

Examples:

```text
Mount:
Top builds an Arm Isolation opening
→ Top initiates
```

```text
Closed Guard:
Bottom Triangle reaches Ready
→ Bottom initiates
```

```text
Half Guard:
Bottom creates Wrestle-Up opening
→ Bottom initiates
```

The axis modifies the likelihood/quality of execution.

It does not monopolize the right to initiate.

---

# 16. Established Position: Initiator → Responder

Established positions generally use:

```text
INITIATOR
↓
Action locks
↓
RESPONDER reads current threat
↓
Responder chooses
↓
Resolution
```

The initiator cannot change the initial committed action after seeing the response.

Follow-ups depend on:

- setup;
- chain depth;
- position;
- stamina;
- technique knowledge;
- opponent response.

Design rule:

> **Every defense should close some routes while leaving others open.**

The current threat is readable; the exact chained follow-up should not always be known until committed.

---

# 17. Standing, Neutral States, and Scrambles: Simultaneous Choices

When neither fighter has established positional authority, both can act simultaneously.

Applies to:

- Standing Neutral;
- open scrambles;- loose transition states;
- some neutral guard situations;
- moments immediately after a position breaks.

Example:

```text
Standing

P1: Single Leg
P2: Snapdown
```

Both choices lock before resolution.

Near-simultaneous meaningful events may be grouped into the same decision window.

The approximate simultaneity threshold remains tunable.

---

# 18. Action Tags for Simultaneous Resolution

Avoid a giant move-vs-move priority table.

Techniques can carry broad interaction tags such as:

```text
ENTRY
PRESSURE
RETREAT
FRAME
ANGLE
SCRAMBLE
```

A compact tag interaction model supplies the broad relationship.

Then the exact outcome considers:

- current position;
- setup;
- control axis;
- technique;
- commitment;
- Power;
- Speed;
- Base;
- Mobility;
- Stamina;
- Belt knowledge;
- timing.

This should reduce hand-authored pairwise explosion while preserving BJJ specificity.

---

# 19. Result Grades

Universal result ladder:

```text
STRONG FAILURE
FAILURE
CONTESTED
SUCCESS
STRONG SUCCESS
```

A local success may:

- improve the axis;
- damage opponent setup;
- create an opening;
- build a setup;
- initiate a transition.

It does **not** necessarily win the position.

---

# 20. Deterministic Resolution

The preferred core philosophy remains:

> **No hidden dice roll decides whether a correctly built technique randomly succeeds.**

Uncertainty comes from:

- hidden simultaneous choices;
- incomplete Recognition;
- opponent tendencies;
- feints;
- style differences;
- stamina differences;
- setup state;
- technique choice;
- AI strategy.

The game may display labels like:

```text
Favorable
Contested
Dangerous
```

These summarize known state rather than hidden RNG.

---

# 21. Setup Progress

Some techniques require preparation.

Use broad setup states:

```text
None
Partial
Ready
```

Internally a continuous value may be used.

Setups may:

- build through behaviors;
- build through successful actions;
- decay;
- be disrupted;
- be consumed;
- create initiative when Ready.

Setup hysteresis should avoid flicker around thresholds.

---

# 22. Commitment

LOW / MEDIUM / HIGH remains a core system.

But commitment is a **modifier to a tactical technique**, not the primary action itself.

Good:

```text
Single Leg + LOW
Single Leg + MEDIUM
Single Leg + HIGH
```

Bad:

```text
Choose:
LOW
MEDIUM
HIGH
```

with no meaningful technique choice.

Commitment may affect:

- stamina cost;
- finishing force;
- positional risk;
- setup preservation;
- recovery exposure;
- outcome grade.

---

# 23. Physical Attributes

Physical identity uses:

- **Power**
- **Speed**
- **Stamina**
- **Base**
- **Mobility**

Technique knowledge is not a physical stat.

## Power
Ability to move the opponent.

Affects:

- takedown finishes;
- bridges;
- explosive reversals;
- posture breaking;
- forced movement;
- some finishing pressure.

## Base
Ability to resist being moved.

Affects:

- stability;
- balance;
- positional integrity;
- resisting displacement.

## Speed
Character execution speed—not human decision time.

May affect:

- action completion;
- setup progression;
- capitalization on openings;
- close simultaneous contests.

Speed does not automatically grant scramble initiative.

## Mobility
Affects:

- guard retention;
- recovery;
- inversion;
- scrambling;
- awkward-position movement.

## Stamina
Represents sustainable effort.

Typical commitment pattern:

```text
LOW       small cost
MEDIUM    moderate cost
HIGH      high cost
EXPLOSIVE very high cost where used
```

Recovery should come from choices such as:

- CONSERVE;
- RESET;
- slowing the pace.

Stabilizing a position should not give free stamina recovery.

---

# 24. Styles

Styles define physical/tactical identity.

All styles should use a controlled/equal stat budget.

## 24.1 Smasher

Identity:

- passing;
- pressure;
- pins;
- Mount;
- top submissions;
- grinding control.

Strengths:

- Power;
- Base;
- pressure.

Weaknesses:

- loose scrambles;
- inversion;
- mobility-heavy exchanges.

## 24.2 Lanky

Identity:

- Guard;
- triangles;
- armbars;
- range/leverage;
- unusual angles.

Strengths:

- Mobility;
- guard retention;
- submissions from distance.

Weaknesses:

- raw force contests;
- prolonged pressure battles;
- explosive wrestling exchanges.

## 24.3 Explosive

Identity:

- takedowns;
- scrambles;
- reversals;
- wrestling bursts;
- unstable-position attacks.

Strengths:

- Power;
- Speed;
- emergency attacks.

Weaknesses:

- burns stamina;
- weaker long control;
- costly failed high commitment.

## 24.4 Technician

Identity:

- efficiency;
- clean position;
- low wasted movement;
- strong Base;
- strong Stamina efficiency.

Weakness:

- lower Power;
- must build proper setup rather than brute force.

## 24.5 Wrestler

Identity:

- Standing;
- takedowns;
- mat returns;
- Turtle rides;
- wrestle-ups;
- scrambles.

Weaknesses:

- weaker bottom Guard;
- weaker submission defense from poor bottom positions.

**Wrestler and Smasher are separate identities.**

---

# 25. Belt System

Belts define **BJJ knowledge**.

A Belt controls:

- legal technique pool;
- counters;
- Recognition detail;
- Chain Depth;
- advanced options;
- submission complexity;
- unusual/specialized techniques.

Higher belts should not simply receive stronger physical attributes.

Their core advantage is:

> **They understand more BJJ.**

## Broad progression

### White
- basic takedowns;
- basic Guard;
- basic escapes;
- simple sweeps;
- common submissions;
- shallow chains;
- limited Recognition.

### Blue
- broader move pool;
- improved counters;
- deeper short chains;
- more Guard/pass options;
- stronger Recognition.

### Purple
- advanced systems;
- specialized Guards;
- deeper chaining;
- advanced counters;
- more submission families;
- stronger tactical information.

### Brown / Black
- broad and deep technique knowledge;
- sophisticated counters;
- deep chains;
- high Recognition;
- specialized/unusual techniques.

## Still missing

⚪ Exact technique-by-belt table  
⚪ Exact Chain Depth per belt  
⚪ Ruleset legality per belt  
⚪ Belt-specific starting packages  
⚪ Promotion requirements  
⚪ Belt-specific opponent pools  

---

# 26. Recognition

Recognition must add information—not hide basic tactical truth.

All belts should understand the fundamental danger.

Example:

```text
White:
"Your arm is being isolated."
Threat: Building
```

Higher knowledge may reveal:

```text
Blue:
"Armbar setup developing."
```

```text
Purple:
"Armbar setup developing.
Likely follow-up: Triangle or Back transition."
```

Higher Recognition may provide:

- technique names;
- likely follow-ups;
- counter-chain predictions;
- feint recognition;
- more precise defensive options;
- opponent tendency insight.

---

# 27. Feints

A feint should not make the UI lie.

Preferred model:

> **A feint is a real low-commitment threat.**

Everyone can see that a threat is building.

Higher knowledge may recognize:

- low commitment;
- low likelihood of follow-through;
- likely secondary attack.

Rules:

- a low-commitment feint cannot progress beyond the first submission threat stage;
- a cheap threat should be answerable with a similarly cheap defense;
- repeated feints must not become a nearly free stamina-drain exploit.

---

# 28. Technique Data System

Techniques should become data-driven wherever practical.

Conceptual schema:

```text
Technique

id
name

minimum_belt
legality_tags

start_positions
required_substate
requirements

interaction_tags
legal_responses

LOW_cost
MEDIUM_cost
HIGH_cost

attribute_scaling

setup_effects
submission_effects

STRONG_FAILURE_exit
FAILURE_exit
CONTESTED_exit
SUCCESS_exit
STRONG_SUCCESS_exit

chain_tags
recognition_tags
```

Goal:

> Adding a move usually means adding content + tests, not rewriting the engine.

---

# 29. Takedown System

Status: 🔵

Takedowns are **Standing transitions**, not separate minigames.

Each needs:

```text
entry_requirements
interaction_tags
commitment
responses
result-grade destinations
```

Example:

```text
Single Leg

STRONG SUCCESS
→ Side Control

SUCCESS
→ Top Half Guard

CONTESTED
→ Turtle / Scramble resolution

FAILURE
→ Standing

STRONG FAILURE
→ Opponent Front Headlock
```

First Standing set:

- Single Leg;
- Double Leg;
- Body Lock;
- Snapdown;
- Guard Pull.

Core defensive set:

- Sprawl;
- Whizzer;
- Pummel/Frame;
- Counter-shot;
- Guillotine threat.

---

# 30. Scramble Resolution

Status: 🔵

Scramble is initially a **transient state**, not an eleventh node.

It may use:

- Speed;
- Mobility;
- Base;
- current stamina;
- existing advantage;
- action tags;
- specific scramble choices.

It should resolve quickly into a real position.

If later human play demonstrates that scramble interaction needs more depth, it can become a larger subsystem.

---

# 31. Universal Submission System

The canonical submission stages are:

```text
OFF
↓
THREAT
↓
CONTROL
↓
FINISH
```

Defense pushes backward:

```text
FINISH → CONTROL → THREAT → OFF
```

The submission track sits **on top of the position**, rather than replacing the positional game.

Example:

```text
Position:
Mount — Top Strong

Submission:
Armbar CONTROL
```

Submission offense can sacrifice positional security.

Submission defense can change both:

- submission stage;
- positional axis.

---

# 32. Submission Finish

When FINISH is reached:

```text
FINISH secured
↓
Emergency Submission Window
↓
Defender:
TAP
or
REFUSE TAP
```

## TAP

```text
TAP
→ immediate loss
→ no major injury consequence
```

## REFUSE TAP

One final hidden simultaneous contest:

```text
Attacker finishing choice
vs
Defender emergency escape
```

Resolution stays deterministic once both choices are locked.

Possible outcomes:

- Escape;
- Referee Stoppage;
- Joint Injury;
- Unconsciousness.

There is no separate passive finish-hold plus extra later escape attempt.

---

# 33. Submission Switching and Chain Depth

Submission switching retains some progress, not all.

Preferred model:

```text
FINISH
→ switch
→ new submission begins at CONTROL
```

```text
CONTROL
→ switch
→ new submission begins at THREAT
```

Switching costs:

- stamina;
- progress;
- one Chain Depth use.

Chain Depth resets only when:

- submission returns to OFF;
- positional axis crosses Neutral;
- a new position becomes established.

Moving between visible bands does not refill Chain Depth.

---

# 34. Emergency Defense

A dangerous submission **always** creates an emergency response opportunity.

This applies to every belt.

White belts may have:

- simpler information;
- fewer technical counters.

They are never denied the chance to react.

---

# 35. Submission Consequences

## Joint Lock

Refuse + lose final contest:

```text
Joint Injury
→ Match Stoppage
```

Possible run consequences:

- limb-related technique penalty;
- technique temporarily unavailable;
- relevant Base/Power reduction;
- forced rest/medical node.

Potential severity:

- Minor Strain;
- Moderate Injury;
- Serious Injury.

Exact model remains open.

## Choke

Refuse + lose final contest:

```text
Unconsciousness
→ Match Stoppage
```

Possible consequences:

- forced recovery;
- temporary stamina ceiling reduction;
- rest node;
- recovery debuff.

Do not model permanent neurological damage.

## Final-match consequence

Refuse must still have cost even if there is no later match in the current run.

Potential meta consequences:

- promotion delay;
- recovery before next run;
- training restriction;
- next-run starting penalty.

---

# 36. Flash Submissions

Fast submissions may occur only under exceptional circumstances, such as:

- major defensive error;
- excellent setup;
- exhausted defender;
- strong positional advantage;
- specialist build;
- knowledge mismatch.

Even a flash submission still gets the mandatory emergency defense window.

---

# 37. Belt vs Run Rewards

Core rule:

```text
BELT
determines legal technique universe

RUN
selects/develops from that universe
```

A White Belt should not randomly obtain a fully mastered advanced Black-Belt-level technique.

## Technique variants

Run rewards may deepen known techniques.

Examples:

```text
Armbar
→ new starting position
```

```text
Triangle
→ stronger Closed Guard route
```

```text
Double Leg
→ improved Side Control follow-up
```

## Drilled techniques

Rare reward:

```text
DRILLED:
Granby Roll

higher stamina cost
weaker setup
fewer follow-ups
```

A drilled next-belt move may temporarily be usable in weaker form.

Successful use may help promotion progress.

Reward RNG should **not** be the only way to achieve promotion.

---

# 38. Promotion and Permanent Progression

Promotion should primarily come from milestones.

Possible milestones:

- win tournament at current belt;
- complete belt challenge;
- demonstrate required technique families;
- achieve a progression milestone set.

Opponents may be organized by belt division.

Because promotion also increases opponent difficulty, separate permanent progression should exist.

Possible permanent unlocks:

- styles;
- starting traits;
- gym upgrades;
- coaches;
- starting technique choices;
- cosmetics;
- training bonuses.

---

# 39. Traits / Abilities

Status: 🔵

Initial examples:

## Heavy Hips
- improved takedown defense;
- better top pressure.

## Fast Scrambler
- improved scramble outcomes.

## Gas Tank
- better stamina recovery.

## Grip Fighter
- stronger hand-fighting / grip situations.

## Submission Hunter
- submission-chain benefit.

## Escape Artist
- benefits escapes from losing positions.

## Pressure Cooker
- improved controlling pressure.

## Counter Wrestler
- improved defensive/counter takedown outcomes.

Target character complexity:

```text
5 physical attributes
+ 1 Style
+ Belt knowledge
+ 2–4 Traits
+ technique pool/loadout
```

Avoid hundreds of tiny stat modifiers.

---

# 40. Match Rulesets

The same grappling engine should eventually support:

- Points;- No-Points;
- Submission-Only.

## Points mode

Potential scoring events:

- takedown;
- sweep;
- pass;
- Mount;
- Back Control;
- advantages;
- penalties.

Preferred scoring concept:

```text
Reach scoring position at Stable
↓
Hold 3 simulated seconds
↓
Score
```

A positional entry scores once.

Leaving and later genuinely re-entering can score again.

Exact point values remain open.

## Submission-Only

No positional points.

Submission is the normal win condition.

Timeout result remains unresolved:

- Draw?
- Overtime?
- Judges?
- Dominance tiebreak?
- Tournament rule?

This must be resolved before a final production ruleset is frozen.

## First playable rule

Do **not** implement every ruleset before human play.

Choose one initial full-match ruleset first.

---

# 41. Stalling

Stalling measures **progress**, not button activity.

Meaningless action spam does not count as activity.

## Dominant positions

May use advancement timer:

```text
MOUNT ADVANCEMENT
20s
```

Timer can reset on:

- positional advance;
- genuine submission threat;
- meaningful defensive reaction forced;
- attacking transition.

## Guard / two-sided positions

The advancement obligation can follow whoever is favored on the positional axis, not merely whoever is physically on top.

## Standing

Neutral Standing uses shared activity expectations.

Exact attribution still requires tuning.

---

# 42. Stalling Penalties

## Points

Potential ladder:

```text
Warning
→ penalty/point consequence
→ position reset
→ escalation
```

Exact values remain open.

## Submission-Only

Prefer visible consequences benefiting the non-stalling player.

Examples:

```text
Top stalls in Mount
→ axis moves toward Bottom
```

```text
Bottom stalls defensively
→ axis moves toward Top
```

A stalling penalty should not break a position by passive drift alone.

If already at the boundary:

```text
non-stalling player
→ FREE INITIATIVE WINDOW
```

Repeated offense may cause Position Reset.

---

# 43. Time as a Strategic Resource

Clock state must affect risk.

Example:

```text
0:35 remaining
Down on points

SAFE:
Recover Guard

RISKY:
Wrestle Up

VERY RISKY:
Expose position to create submission attack
```

A fighter ahead may prioritize control.

A fighter behind may increase commitment/risk.

---

# 44. Gi vs No-Gi

Status: ⚪ **Important unresolved product decision.**

This changes:

- grips;
- chokes;
- Guard systems;
- passing;
- legal techniques;
- leg-lock environment;
- animation/visual requirements;
- style balance.

Options:

- No-Gi first;
- Gi first;
- both eventually;
- separate rulesets.

**This decision should be made before deep Guard technique tables are frozen.**

---

# 45. Character Model

The long-term model is:

```text
STYLE
- Power
- Speed
- Stamina
- Base
- Mobility

BELT
- Technique Pool
- Recognition
- Chain Depth
- Advanced Counters
- Submission Complexity

RUN
- Temporary Traits
- Technique Selection
- Upgrades
- Synergies
- Injuries
- Recovery State

META
- Belt Promotion
- Styles
- Coaches
- Gym Upgrades
- Starting Traits
- Starting Technique Choices
```

---

# 46. Roguelike Core Loop

Status: 🔵

Target:

```text
Training / Event
↓
Opponent / Scouting
↓
Match
↓
Reward / Injury / Recovery
↓
Training / Event
↓
Stronger Opponent
↓
...
↓
Run Finale
```

Possible rewards:

- technique variants;
- new legal techniques;
- upgrades;
- traits;
- stamina/conditioning changes;
- position-specific bonuses;
- synergies;
- Drilled techniques.

---

# 47. Training

Examples:

- Wrestling Session
- Guard Session
- Passing Session
- Submission Session
- Conditioning
- Recovery
- Open Mat

Training should often create choices, e.g.:

```text
Coach offers:

Single Leg Finish
Hip Bump Sweep
Armbar Chain

Choose one.
```

Still missing:

⚪ training-node frequency  
⚪ reward rarity  
⚪ technique capacity/loadout  
⚪ upgrade tiers  
⚪ permanent vs run-only learning  

---

# 48. Injuries and Recovery

Status: 🔵

Possible injuries:

- Shoulder
- Knee
- Rib
- Grip/Hand
- accumulated fatigue

Choices may include:

```text
REST
TRAIN THROUGH
ADAPT
```

Injury must create strategic consequences without becoming medical micromanagement.

---

# 49. Opponent Scouting

Status: 🔵

Example:

```text
Opponent:
Blue Belt Smasher

Strong:
Takedowns
Half Guard Top

Weak:
Bottom Guard

Power:
High

Stamina:
Average
```

How much information is visible depends on:

- scouting;
- Recognition;
- belt;
- prior opponent knowledge.

---

# 50. Roguelike Events

Potential events:

- Visiting Black Belt seminar;
- Hard Wrestling Room;
- Open Mat Challenge;
- Rival;
- Bad Weight Cut;
- Coach specialization;
- Training partner technique;
- Injury treatment;
- Recovery opportunity;
- unusual ruleset bout.

---

# 51. Run Finale

Status: ⚪

Choose one first-run structure.

Options:

- tournament bracket;
- gym challenge ladder;
- promotion test;
- rival finale.

Do not build multiple run structures initially.

---

# 52. Run Length and Pacing

Five simulated minutes can become long in wall-clock time.

Possible pacing tools:

- fast-forward stable stretches;
- shorter early matches;
- longer finals;
- event-driven acceleration;
- varied tournament format.

Possible example—not frozen:

```text
Early Rounds:
3:00 simulated

Semifinal / Final:
5:00 simulated
```

---

# 53. Human Player API

Status: 🔵 **Critical before frontend.**

Required conceptual objects:

```text
GameSnapshot
DecisionWindow
LegalAction
LegalResponse
CommitmentChoice
MatchResult
```

Required command:

```text
submit_player_choice(...)
```

The frontend must not directly mutate position internals.

---

# 54. GameSnapshot

Should expose:

- clock;
- current position;
- subposition;
- initiative;
- axis;
- visible band;
- player stamina;
- opponent stamina if information rules allow it;
- setup states;
- submission state;
- legal actions;
- legal responses;
- legal commitments;
- Recognition information;
- stalling;
- score;
- match result.

---

# 55. Headless Human-Play Milestone

Before frontend, a human must be able to play a complete match through the same API.

Example:

```text
5:00 — STANDING

Opponent:
Blue Belt Wrestler

Choose:
1. Single Leg
2. Double Leg
3. Body Lock
4. Guard Pull
5. Reset

> 1

Commitment:
LOW
MEDIUM
HIGH

> MEDIUM
```

## Definition of Done

The player can:

- begin Standing;
- manually choose all player actions;
- attack/defend takedowns;
- sweep;
- pass;
- escape;
- reverse;
- take the Back;
- move between the ten position nodes;
- enter submissions;
- defend submissions;
- manage stamina;
- reach Tap/Stoppage/time result;
- finish without touching engine internals.

---

# 56. AI Going Forward

Status: 🟡 **Paused as a primary research track.**

Near-term opponent AI should be:

- stable;
- deterministic enough for testing;
- style-aware;
- belt-aware;
- imperfect but believable.

AI personality should eventually understand:

- style;
- belt;
- score;
- clock;
- stamina;
- position;
- axis;
- initiative;
- simultaneous situations;
- setups;
- submission danger;
- risk;
- stalling;
- technique pool;
- Chain Depth.

Do not reopen major AI qualification until:

1. the 10-position graph exists;
2. a human can play full matches;
3. fighter identity exists;
4. the roguelike loop is playable.

---

# 57. Frontend Threshold

Frontend begins after:

- Position Contract exists;
- all ten position nodes have minimal playable content;
- Standing/takedowns work;
- universal submissions work across several positions;
- human Player API exists;
- a full terminal/headless match works.

The initial frontend needs:

- timer;
- position/subposition display;
- axis/band;
- stamina;
- setup/submission danger;
- action buttons;
- response buttons;
- commitment controls;
- Recognition information;
- score/stalling;
- match result.

---

# 58. Visual Representation

Status: ⏸

Later visual systems may include:

- mat visualization;
- 2D position diagrams;
- fighter models;
- authored Blender poses;
- authored pose transitions;
- procedural IK for contact;
- limited physics;
- replay;
- technique-chain visualization.

**Game state remains authoritative.**

Do not use full-body physics to decide whether BJJ techniques are legal.

---

# 58A. Technique Memories — Visual Action Language and Roguelike Identity

**Status: 🔵 Proposed product direction; not implemented or art-frozen.**

The player should not be limited to a fixed choice of four visible buttons/cards. Instead, present **available BJJ techniques as recognizable “memories” of learned movements**. These are *not necessarily literal playing cards*: distinct silhouettes, tiles, glyphs, folded notes, or other shaped artifacts can communicate knowledge, familiarity, purpose, and mastery. The final art direction remains open.

> **Fantasy:** The fighter recognizes a situation, recalls a move, commits to it, and learns new memories of BJJ through training and the roguelike run.

The metaphor describes **how techniques are learned, collected, surfaced, and visually understood**. It must not imply that the player randomly draws their legally known actions from a deck on every decision window. BJJ choices should remain grounded in position, setup, initiative, resources, knowledge, and ruleset legality.

## 58A.1 Four separate concepts — do not collapse them

| Layer | Meaning | Example | Persisted where? |
|---|---|---|---|
| **Fundamental movement** | Basic technique/defense every eligible fighter understands | Frame, Bridge, Posture, basic recovery | Baseline technique pool; available when legal |
| **Learned memory** | Technique knowledge available because of belt, training or a valid unlock | Specialized guard entry, an advanced counter | Belt/character knowledge, according to progression rules |
| **Run memory** | Temporary remembered refinement, specialization or synergy earned in this run | “Underhook Timing” improves Half Guard follow-ups | Run only unless explicitly defined otherwise |
| **Meta memory** | Permanent progression option such as a starting choice, coach lesson or unlock | Starting specialization unlocked after a milestone | Meta profile; not a free override of belt/legality |

**Belts represent knowledge, not extra raw strength.** Basics should never become arbitrary rare rewards that a player must draw before they can Bridge or Frame. Conversely, advanced memories must respect belt gates and ruleset legality; a `Drilled` next-belt memory is a limited, more expensive exception as described in the existing design, not unrestricted promotion.

## 58A.2 Memory is a visual wrapper over legal techniques, not the resolver

Proposed visual attributes (not fixed art requirements):

- **Shape / silhouette:** communicates family at a glance (escape, guard retention, pass, sweep, takedown, submission, counter, movement/utility).
- **Name and movement icon:** specific BJJ technique, with a readable description or optional short animation/diagram.
- **Familiarity/mastery treatment:** fundamental, learned, drilled, refined; shown without hiding mandatory safety information.
- **Readiness feedback:** legal now, needs setup, lacks stamina, not valid in this position, or locked by belt/ruleset — clearly differentiated.
- **Connection marks:** which positions, responses or techniques this memory can lead into.
- **Optional visual rarity:** for run rewards, not as a substitute for legality or mechanic explanation.

**Never infer mechanics purely from artwork.** Labels, tooltips, gamepad focus behavior, visual accessibility, and non-color-only distinctions are required. The technique library can contain many memories; the **decision window shows relevant/legal actions with filtering, grouping or scrollable navigation**, not an arbitrary fixed four-option hand.

## 58A.3 Memory categories for roguelike rewards (examples to validate)

These are **design examples, not approved numerical bonuses**:

| Memory type | Gameplay intention | Illustrative effect |
|---|---|---|
| **Technique Memory** | Add one eligible technique or variant to the run's usable repertoire | Gain a legal guard recovery variant |
| **Refinement Memory** | Improve execution in a particular tactical context | Lower cost of a correctly set-up escape |
| **Chain Memory** | Reinforce transitions between known actions | On an arm-drag success, improve access to an already-known follow-up |
| **Counter Memory** | Increase response specificity | Unlock an alternate response against a known entry |
| **Recognition Memory** | Read tactics earlier or with more precision | Show a likely next link in an opponent's submission chain |
| **Conditioning Memory** | Change stamina economy in a bounded, transparent way | Reduced fatigue from a narrow movement family |
| **Habit / Style Memory** | Create build identity with an explicit tradeoff | Pressure passing benefit at a mobility cost |
| **Scouting Memory** | Exploit information about a future opponent | Reveal a documented recurring preference before a match |
| **Recovery / Injury Memory** | Interact with the run's injury/recovery layer | Relearn a technique safely after an injury penalty |
| **Drilled Memory** | Temporarily access a valid next-belt technique, with drawbacks | Higher stamina cost, reduced setup/follow-ups |

Rewards may also be **composite memories** connecting two known techniques, but should not create impossible BJJ routes or violate the position graph. The phrase “memory rarity” concerns reward availability, not random success rolls during resolution.

## 58A.4 Decisions remain tactical, not a card-draw lottery

- A memory appears as an available **candidate** only when its underlying technique is legally available in the current position and state. A library browser may show unavailable memories with explicit reasons.
- A technique choice is separate from **LOW / MEDIUM / HIGH commitment**. Commitment changes cost/risk/intensity; it is not a memory type or an entire turn by itself.
- Defensive responses and basic safety routes must remain accessible even when the current run has few upgraded memories.
- The player may hold more than four techniques; UI density is solved with families, focus, search, contextual prioritization, and controller navigation rather than deleting choices.
- The game does not guarantee every learned move works in every state. Recognizing the correct opening and building setup remain essential.
- Roguelike growth should change how a fighter plays **across positions and matches**, while maintaining deterministic action resolution.
- Reward draws can be seeded/deterministically reproducible if the roguelike requires them; do not introduce hidden RNG into successful technique resolution.

## 58A.5 Example player experience (illustrative, not balanced)

```text
Standing -> attempt Single Leg [fundamental]
   |
   v
Half Guard -> recall Underhook [fundamental/learned by ruleset]
   |
   +-- Run memory: Underhook Timing [Refinement]
   |      improves a legal wrestle-up opportunity
   v
Sweep -> Top Half Guard -> Pass -> Side Control
   |
   +-- Run memory: Pressure Passing Chain [Chain]
          connects existing pass knowledge to next legal advance
```

At a post-match training event, the player might choose **one of several shaped memories** with different strategic consequences. That reward-selection UI may *look* card-like, but live BJJ decision windows are a navigable repertoire, **not** a fixed hand.

## 58A.6 Data boundaries and eventual Godot presentation

Keep technique IDs, eligibility, results, setup and Exit Maps authoritative in the simulation. A possible data relationship is:

```text
TechniqueDefinition (stable ID, position legality, action/responses, transitions)
        |
FighterKnowledge (belt, known techniques, valid drilled exceptions)
        |
RunMemoryModifiers (temporary, typed and bounded effects)
        |
LegalActionQuery (current fighter + position + state)
        |
MemoryViewModel (shape, text, icon, readiness, connection previews)
        |
Godot visual component / input navigation
```

This is deliberately a **data-flow concept**, not a commitment to a specific class hierarchy or an approved language migration. Presentation must not mutate rules directly; after a legal choice, the engine receives stable technique IDs plus commitment and any relevant validated modifiers. A future GDScript port must parity-test Python Mount behavior before expanding the position system.

## 58A.7 Scope, implementation order, and open decisions

1. **Now:** record the memory concept, separate the knowledge model from run modifiers, and ensure PositionContract/Human Player API can expose variable-length legal actions with stable IDs and availability reasons.
2. **After headless match works:** prototype a minimal memory selection/listing presentation and one bounded, seeded run-memory reward; validate usefulness in a small run.
3. **Roguelike phase:** expand reward types, synergies, coaches, injuries, and meta progression with tests and BJJ-domain review.
4. **Frontend phase:** finalize the visual shapes, animation, navigation, accessibility, and audio; do not require visual art to validate core gameplay.

Open decisions: literal vs abstract memory art; rarity and capacity; whether loadouts limit *advanced specializations* without removing fundamentals; memory acquisition and stacking limits; the detailed retention and fracture rules in §58C; balance of rewards vs belts; visual legibility with many eligible techniques; exact Gi/No-Gi technique legality.

**Guardrail:** Do not implement a large deck-building framework or new memory-effect scripting language during Phase 1. Preserve the short path to a complete human-play BJJ match.

---

# 58B. Memory Constellation — Implementable Design Blueprint (v10.2)

**Status:** Design baseline proposed for owner approval. This section elaborates 58A; it does not claim shipped mechanics, numerical balance, Gi/No-Gi decisions, or a committed GDScript migration. Where 58A lists open questions, this section gives recommended provisional answers. Before code changes, freeze the selected defaults in an ADR and update the corresponding checklist. The baseline is intended to minimize future design churn without pretending untested numbers are final.

## 58B.1 Core player fantasy and nonnegotiable invariants

The fighter learns, recalls, combines, adapts, and sometimes loses confidence in techniques over a roguelike run. **Memory** is the organizing metaphor for the fighter's BJJ knowledge and build. It is not amnesia, random action draws, or a replacement for position legality.

1. **Universal fundamentals remain available** to eligible fighters in the relevant situation; never require drawing, equipping, or owning a rare reward to defend oneself.
2. **Legal actions derive from the rules engine**, not memory art, animations, frontend filtering, or reward randomization. A memory can grant knowledge only through explicit validated eligibility.
3. **Belts gate knowledge**; rulesets gate legality; current position/substate, setup and match state gate opportunity. These are independent filters. An advanced memorized technique is not legal merely because it is owned.
4. **Techniques are the actions; commitment modifies effort**. Technique + commitment is the player's command; memory modifiers are resolved deterministically.
5. **No four-choice ceiling and no random hands**. The current list of legal techniques can be as long as needed, with navigation and prioritization as UI concerns.
6. **Builds create specialization, not universal superiority**. Upgrades should be situational, legible, bounded, and, where strong, carry a tradeoff.
7. **Submission defense, Tap and Refuse remain intentional actions**. A time-expiry fallback never silently supplies either choice.
8. **Full match is the first milestone**. Build the data seams during engine architecture work; implement the reward economy after headless matches work.

## 58B.2 Vocabulary (frozen conceptual distinctions)

| Name | Definition | Persistence | Eligible during match? |
|---|---|---|---|
| TechniqueDefinition | Canonical mechanical movement, responses, requirements, position effects, exits | Game content | If legal and known |
| FundamentalKnowledge | Automatically available core knowledge for eligible fighters | Fighter baseline / belt rules | Yes, if legal |
| LearnedKnowledge | Techniques known through belt progression, starting selection or training | Character and/or run, as specified | Yes, if legal |
| DrilledKnowledge | Temporary, weaker, next-belt access with explicit penalties | Run | Yes, if ruleset permits exception |
| MemoryInstance | Owned modifier, technique grant, information insight, or chain specialization | Run or meta | Only if equipped/active where applicable |
| RecallView | Tactical presentation of currently relevant techniques and modifiers | Transient UI | Display only |
| Constellation | Navigable visualization of known techniques and owned memory connections | Generated view | Not itself a game state |
| SynergyLink | Typed conditional relationship between technique IDs, position transitions, or memory IDs | Content + owned activation | Only if preconditions hold |
| TechniqueMastery | Optional progression/familiarity state; not an extra belt | Character/meta if later authorized | Only through defined effects |

**Terminology:** “Recall” means presenting known options, not rolling to remember. “Memory equipped” means its specialization modifier is active, not that the underlying known movement becomes unavailable when unequipped. Do not conflate temporary run progress with permanent promotion.

## 58B.3 Memory presentation and shape grammar

Three player-facing views:

- **Repertoire**: searchable long-term library of known techniques, by position and family, with previews and explanations for unavailable moves.
- **Recall wheel/panel**: compact position-aware legal list in a paused decision window. Sort by legal response to current threat, prepared opportunities, baseline safe actions, then other legal actions; use grouping, scroll and controller navigation. The ordering is a recommendation layer; all legal options remain reachable.
- **Constellation**: post-match network of position nodes, technique memories and synergy connections, with separate preview of run rewards and build slots.

**Recommended shape language (art subject to usability testing):** shield = defensive/recovery; diamond = control; arrow = positional transition; triangle = submission; fork/branch = chain; eye = recognition/counter; ring/flame = conditioning/style. The same technique may have secondary tags; choose one primary silhouette per memory instance, plus explicit readable tags. Shape never controls rules. Colors may indicate temporary status or reward category, but color must never be the only signal. Mark readiness using text + icon: LEGAL, SETUP NEEDED, EXHAUSTED, BELT LOCKED, RULESET ILLEGAL, WRONG POSITION, INJURY BLOCKED. The real contract should use stable machine-readable reason codes.

**Scalability / input:** do not assume four visible techniques. Test 3, 8, 16 and 30 relevant items; keyboard/controller focus; screen readers or narrated text equivalents where practical; tooltip and expanded move panel remain inspectable without resetting PvP timer. Recognizable shorthand must be learnable without memorizing abstract shapes.

## 58B.4 Technique availability pipeline (normative ordering concept)

Input: fighter ID, current position ID/substate, context (initiator/responder/simultaneous), requested ruleset, fighter belt and knowledge, active injuries, stamina, setup and submission state.

1. Enumerate position-relevant canonical technique IDs.
2. Validate actual technique ruleset legality and required fighter knowledge; any Drilled exception must be explicit and narrower than normal belt knowledge.
3. Validate actor role, decision mode, substate, opponent action (for responses), setup and active threat.
4. Compute effort choices and funding/effective commitment, without pretending all actions require the same commitment set.
5. Apply eligible typed memory effects to the preview; never mutate TechniqueDefinition at runtime.
6. Return all legal options and a separately queryable list of temporarily unavailable/unknown techniques with stable reason codes.
7. Revalidate the selected technique ID + commitment + expected decision ID on submission; client-side display is not authority.

**Determinism:** stable sorting for logs and fixtures; modifier evaluation order fixed by declared priority and then stable ID; no dependence on scene order, render FPS, unordered map iteration or local locale. If an effect would produce illegal position traversal, reject it rather than silently creating a transition.

## 58B.5 Ten memory families and example effects (content templates, not verified balance)

| Family | Intended role | Concrete example | Constraints |
|---|---|---|---|
| Technique | Expand repertoire | Learn an eligible Half Guard counter | Knowledge and ruleset checks required |
| Refinement | Improve one known action under stated condition | Underhook Timing: reduce stamina burden on a legal Half Guard wrestle-up | Cannot alter illegal outcomes |
| Chain | Enhance an existing, valid follow-up | Pressure Pass Chain: follow-up setup retains some progress after a qualifying pass | Both endpoints must exist and be legal |
| Counter | Add a response route | Sprawl Reading: legal defensive response to a shot entry | Does not fabricate hidden intent |
| Recognition | Improve informational detail | Show the likely submission follow-up after observed setup | Must not reveal secret simultaneous choice early |
| Conditioning | Specific stamina economy | Short burst economy for takedown entries | Bounded; no infinite recovery loops |
| Habit / Style | Alter strategic tendency with tradeoff | Heavy pressure specialization with worse loose-scramble efficiency | Equal-budget identity, not blanket stat dominance |
| Scouting | Carry observed opponent tendencies | Reveal opponent's documented preference for a particular entry | Based on recorded behavior, not clairvoyance |
| Recovery / Injury | Navigate run setbacks | Rehab lesson reduces a named temporary injury restriction | No in-match injury erasure unless explicitly designed |
| Drilled | Temporary next-belt experiment | Weaker Granby with higher stamina and reduced follow-ups | Only narrow next-belt exception; never bypass ruleset |

## 58B.6 Constellation topology — graph without new position engines

Three different graph notions must remain separate:

- **Position graph**: actual game states (10 nodes) and legal positional transitions determined by action Exit Maps.
- **Technique chain graph**: possible tactical follow-ups between moves, conditioned by states, setup, responses and submission state.
- **Memory constellation**: the **player's personalized view** of known techniques and active modifier links; not a second source of rules.

Constellation edges can be: BUILDS_SETUP_FOR, COUNTERS, FOLLOWS_ON_SUCCESS, PRESERVES_SETUP, RECOGNIZES, REDUCES_COST_WHEN, and OPENS_KNOWN_ROUTE. Each edge has preconditions. A line drawn in the UI is not proof that a technique always follows; clicking it reveals the necessary state and response conditions. Never require manual dragging during the real-time decision countdown.

Example: Half Guard Underhook (known) → Wrestle Up (known). An acquired Underhook Timing memory may conditionally reduce the Wrestle Up cost when the underhook setup is READY. If guard control is lost or the opponent shuts down the route, the connection is inactive and visibly explained. This does **not** cause an automatic sweep.

## 58B.7 Memory acquisition and build economy: initial implementation defaults (PROVISIONAL)

**No random in-match draws.** Roguelike reward offers may be seeded for reproducibility. Favor post-match training events and specific gym/coaching encounters instead of showering each exchange with loot.

- **Reward timing:** one major memory-selection opportunity after each completed match in a short-run prototype; occasional other training/scouting/recovery event offers. This is a test cadence, not a promise of one reward on every production match.
- **Offer structure:** default to three candidate choices for reward screens, **not** a four-choice limit on combat. At least one option should be useful under the current fighter's legal ruleset and existing repertoire; validate eligibility before offering.
- **Ownership:** the player may collect multiple legal memories during a run. Basic/learned techniques are not loadout slots.
- **Activation capacity:** start without a cap for the first vertical slice (one or two owned modifiers); evaluate a cap on **advanced specialization effects only** if stacking proves degenerate. Suggested experimental cap: three active specialization slots, configurable, **not frozen**.
- **Duplicate offer:** no identical non-stackable owned memory offered again unless a named upgrade path exists; otherwise replace it deterministically with another candidate.
- **Rarity:** Common / Specialized / Exceptional may control offer frequency or complexity; rarity is never an outcome-success multiplier. Do not implement a rarity economy before a playable short run.
- **Upgrades:** favor tiered upgrades to the *same* memory (e.g., Practiced → Refined) over indefinite copies. No stacking unless the content definition explicitly permits it, with bounded ceilings.
- **Tradeoffs:** strong offensive bonuses should incur stamina, control security, defensive exposure, narrower applicability, or a limited opportunity cost rather than universal damage scaling.
- **Persistence:** see §58C for authoritative career and technique-memory retention. Mastered techniques, earned belts, discovery records, and qualified success-protected partial progress are distinct from temporary run modifiers. Drilled grants and run-only bonuses still expire. Promotion requires milestones, not lucky reward rolls.

**Anti-dead-run guarantee:** no reward may remove essential defensive fundamentals or make the fighter unable to answer common threats. There must be a transparent way to inspect the fighter's current known repertoire and active refinements.

## 58B.8 Numeric mechanics: what to defer and what to bound

**Do not freeze raw numerical stamina discounts, grade shifts, probability weights, slot counts, or rarity rates now.** The existing Mount math is historical authority and should not be retuned as part of language migration. Define effects declaratively with: target IDs/tags, valid states, trigger event, maximum activations, incompatibilities, explicit cost/risk/grade operations, and deterministic precedence. As an **initial safety constraint**, disallow any new memory from directly converting a STRONG_FAILURE into STRONG_SUCCESS, bypassing submission emergency defenses, changing legality, or bypassing an Exit Map. Exact constraints can later be refined through real gameplay testing.

For the first vertical slice implement only two or three narrow effect primitives: legal TECHNIQUE_GRANT, CONDITIONAL_STAMINA_COST adjustment, and CONDITIONAL_SETUP_PRESERVATION (the last only after the setup API exists). Treat recognition/scouting as separate read-only view effects. Avoid arbitrary scripting or Turing-complete user-authored effects.

## 58B.9 Concrete example: two runs, same belt and same ruleset

**Run A — Pressure learner**: Starts with common legal positional options. Receives Crossface Timing (refinement), then Pressure Passing Link (chain). From Half Guard top, a prepared Knee Slice can produce Side Control via existing Exit Maps. With the right state, the chain preserves a bounded amount of preparation toward a Mount advance. The player still chooses each technique and commitment; opponents can respond.

**Run B — Scramble learner**: Starts with exactly the same baseline options. Receives Underhook Timing (refinement), then Counter-Wrestle Recognition (information/counter). From Half Guard bottom, the fighter can more efficiently prepare a known Wrestle Up and read a documented counter route. A failed attempt still fails under deterministic rules. The fighter is not handed success by card rarity.

**Reward illustration:** Three offered post-match objects: Underhook Timing [Refinement], Escape Sequence [Chain], Conditioning: Short Bursts [Conditioning]. Their silhouettes, effects, eligibility, tradeoffs, and affected technique IDs are visible before selection. One is chosen. The offer screen is intentionally analogous to card drafting; combat is not.

## 58B.10 Timer and memory UX contract

A window-opening event captures an immutable decision ID, acting fighter(s), legal options snapshot/version, and authoritative wall-clock deadline (when applicable). The **simulated match clock is paused** throughout choosing; inspecting memory descriptions and scrolling cannot reset deadlines. Ranked 30-second and casual 45-second policies remain provisional; solo unlimited by default.

- **Initiator/responder:** only the active player's deadline runs for that window. Submission of a valid command locks the choice. After both required participants have locked, simulated time resumes.
- **Simultaneous/Standing:** each participant has an independent deadline beginning with the same actionable window. Choices are sealed until both lock or expire. No information from one player's secret choice leaks through legal-option previews or memory highlights.
- **Expiry:** choose an explicit deterministic, position-specific legal fallback command, without free stamina, bonus setup, surprise counter or automatic Tap/Refuse; emergency submission decisions need a distinct, reviewed policy before PvP.
- **Abuse:** invalid commands cannot restart countdown. Three consecutive ranked misses as a forfeit remains a *proposed* product policy pending disconnect/latency/accessibility testing, not a BJJ scoring rule. Distinguish network timeout from intentional AFK only to the degree authoritative evidence allows.
- **Replay:** deterministic simulation logs resolved commands and effect IDs; session logs deadline events and timeout reason separately. Replay of gameplay cannot depend on local wall-clock or render frames.

**Scalability / 30-second usability acceptance:** novice can locate a safe legal response, preview effect and commitment, and lock a choice within the limit with mouse and gamepad; typical advanced state with 12+ choices needs tested grouping/search shortcuts. Do not optimize through an artificial action cap.

## 58B.11 Data schema boundaries (conceptual, language-agnostic)

```text
TechniqueDefinition:
  id, family_tags, start_positions, legal_roles, belt_requirements,
  ruleset_tags, setup_requirements, interaction_tags, response_rules,
  commitment_options, canonical_resolution_and_exit_maps

FighterKnowledge:
  stable_fighter_id, belt, known_technique_ids,
  granted_drilled_ids, knowledge_source_ids

MemoryDefinition:
  id, family, display_key, silhouette_key, applicability,
  prerequisites, exclusions, rarity_label,
  effect_specs[], persistence_scope, stack_policy, preview_text

MemoryInstance:
  instance_id, definition_id, owner_fighter_id,
  acquired_at_event_id, level_or_variant, active_state

EffectSpec:
  stable_id, effect_type, trigger, target_ids_or_tags,
  conditions, bounded_parameters, precedence

LegalActionView:
  decision_id, technique_id, display_name,
  commitment_choices, current_relevance, readiness,
  unavailable_reasons, applicable_memory_ids,
  possible_followups_with_conditions

ResolvedCommand:
  decision_id, actor_id, technique_id,
  selected_commitment, validated_modifiers

TransitionResult:
  source_position, destination_position, resulting_roles,
  cause_technique_id, result_grade, state_carryover
```

The actual GDScript/Python/C# implementation should follow existing project conventions after code inspection. Data filenames/classes listed here are not frozen APIs. All content IDs must be stable and versioned; saves must retain definitions and compatible migration behavior.

## 58B.12 UI flow and input interactions

**Pre-match:** fighter profile → repertoire and current active memories → scouting → match. **Decision window:** current position/threat + match clock + relevant decision deadline + legal grouped technique memories → inspect (without deadline reset) → choose technique → choose LOW/MEDIUM/HIGH where legal → lock → reveal outcome. **Post-match:** result and injury → training/reward offer → choose or skip → constellation shows new connection and explanation → next encounter. **Run end:** summary distinguishes permanent unlocks from temporary memories removed at run closure.

A sample screen at 12+ actions should offer filters by tactical intent (Defend, Escape, Control, Advance, Submit, Counter), plus an All list. Filters must never change legal action enumeration. Show action preparation, stamina cost preview and why a connection is inactive. The visuals can use shaped tiles, glyphs or folds; do not freeze handcrafted art until navigation/accessibility are tested.

## 58B.13 Verification/acceptance tests

- Baseline Mount outcome parity before any Godot migration, including five-grade result, drift, clamp, band, stamina settlement, setup/submission and exact Exit Maps; old evidence never rewritten.
- Basic Frame/Bridge remain legal whenever their established underlying state allows, regardless of memory inventory/loadout/reward seed.
- A White Belt cannot acquire a Black-Belt-only technique from normal rewards; a defined Drilled exception is explicit and limited; ruleset-illegal moves remain unavailable even when owned.
- All legal actions appear with 3, 8, 16 and 30 candidates; ordering/filtering cannot hide or invalidate any.
- Same run seed + same player choices yields identical offers, acquisitions, modifiers, legal options, outcomes and saved constellation.
- Two memory effects that conflict are either rejected at acquisition/activation or resolved in documented stable precedence; duplicated non-stackable memory does not silently stack.
- A chain link never traverses an illegal transition; disabled links show the missing predicate rather than a fabricated route.
- Solo unlimited, PvP per-player clocks, simultaneous sealed decisions, timeout fallback and expiry metadata produce same gameplay when final resolved commands are replayed.
- No timeout fallback produces TAP/REFUSE without consent or bypasses emergency defense.
- Controller/keyboard usability: a new user can find a core escape and read a memory effect promptly. Time-limit fairness tested before ranked policy is frozen.
- Save/load round-trips preserve acquisition order, owned effects, stable IDs, active slots, drill expiry and meta/run boundaries.

## 58B.14 Phase sequencing, avoiding another architecture detour

**Design baseline now:** agree on vocabulary, invariant boundaries, reward prototypes and UI concepts. **Phase 1 engine foundation:** position contract and variable-length legal-action API; stable fighter identity and typed transitions; provide effect slots but **no** full memory reward economy. If Godot migration is adopted, perform Mount parity first. **Complete match milestone:** prove multiple positions and manually chosen moves/commitments without memory upgrades. **Roguelike prototype:** implement one short run with three representative memory types and deterministic reward offers; test differences across two builds. **Frontend phase:** refine silhouettes, inspect animations, accessibility, constellation interactions, and visual polish. **Later:** rarity economies, elaborate mastery layers, persistent gym/coach upgrades, multiplayer and speculative chain effects.

## 58B.15 Decision register — recommended baseline vs intentionally not frozen

| Design question | Recommendation | Status |
|---|---|---|
| Random card draw during BJJ exchange? | No; all known currently legal options accessible | Strong baseline |
| Are memories literal playing cards? | No; shaped technique artifacts/constellations | Strong baseline, art open |
| Are fundamentals equippable? | No; always available if legal | Strong baseline |
| Does belt influence knowledge, not raw Power? | Yes | Existing guide invariant |
| Are temporary memories able to bypass ruleset legality? | No | Strong baseline |
| Can advanced specialization slots be limited? | Possibly; never limit essential basics | Experiment, not frozen |
| Initial post-match offer count? | Three rewards | Prototype assumption |
| Exact memory numerical modifiers? | Freeze after simulation and playtest | Open |
| Rarity/drop rates? | Defer until short run works | Open |
| Concrete artwork/shape design? | Prototype then accessibility validation | Open |
| Persistent fighter and belt loss? | Same fighter across runs; earned belt never lost upon defeat | Accepted v10.3 design |
| Unfinished technique progress at defeat? | Reset to discovery baseline unless already mastered | Accepted v10.3 design |
| Unfinished technique progress after promotion? | Protected, but still vulnerable to a later fracture | Accepted v10.3 design |
| Training minigame required? | No; learning works through matches; training event optional | Accepted v10.3 direction |
| First ruleset Gi or No-Gi? | Decide before deep Guard/leg-lock catalogs | OPEN owner decision |
| Godot language? | Typed GDScript a candidate, parity spike required | OPEN owner decision |
| Solo time limit? | Unlimited by default | Proposed baseline |
| PvP deadlines? | Ranked 30s; casual 45s | Provisional, PvP deferred |
| Emergency submission timeout? | Never auto-consent; dedicated conservative policy required | OPEN design/safety gate |

**Boundary:** Design can be frozen conceptually before implementation, but no claim of gameplay balance, BJJ technique correctness, complete position catalogs, official ruleset legality, or art feasibility is made merely by writing this guide.

---


# 58C. Persistent Career, Technique Impressions, and Road to Black Belt — v10.3

**Status: Accepted structural design; not implemented.** This section supersedes earlier open-ended persistence assumptions in §§58A–58B and clarifies the established Belt/Run/Meta separation. Exact numerical progression, reward quantities, belt challenge thresholds, and UI art remain provisional. Do not alter historical Mount experiments or claims of existing implementation.

## 58C.1 Player fantasy and career invariants

> **One fighter, one career, many attempts at the next belt. What is discovered remains remembered; what is mastered becomes durable; what is still developing can fracture after defeat.**

1. A **single persistent fighter** continues across normal promotion runs. Restarting a run does not create a replacement fighter.
2. A **run is a road toward the next belt**: a short sequence of opponents, match rewards and a suitable promotion milestone/challenge.
3. **A lost run never demotes the fighter**. Reattempt progression from the current earned belt.
4. Earned belts, career record, eligible foundational techniques, permanent discovery records, and fully mastered technique knowledge survive run failure.
5. Unmastered, unprotected technique-development progress resets to its **discovered baseline** on defeat (Memory Fracture); the technique's existence is not forgotten.
6. Completing a promotion run **protects current unfinished technique progress**. This progress carries to the next run but remains susceptible to a subsequent Memory Fracture until mastered. Promotion protection is *not* equivalent to permanent mastery.
7. Temporary run refinements, trait buffs, scouting bonuses, and Drilled exceptions expire according to their explicit run scope, even after a successful promotion. Do not confuse these with retained technique-development progress.
8. All technique legality, belt access, position constraints, submission safety and deterministic resolution remain authoritative independently of memory ownership.9. Career history remains visible after both victory and defeat. An earned promotion is permanent.
10. No training minigame is required. Meaningful matches can supply exposure, recognition, execution experience and mastery evidence. Optional training events can be designed later.

### Persistence taxonomy

| Data | Scope | After defeat | After promotion |
|---|---|---|---|
| Fighter identity, career record, earned belt | Career | Keep | Keep, advance earned belt |
| Fundamental techniques and earned belt knowledge | Career | Keep | Keep |
| Encountered/discovered technique IDs, source/history | Career | Keep | Keep |
| Fully mastered technique knowledge/proficiency | Career | Keep | Keep |
| Unmastered understanding and execution progress | Run or protected carryover | Reset to discovered baseline | Carry as **protected but fragile** progress |
| Memory Resonance discovery familiarity | Career-level discovery fact; precise bonus not frozen | Eligible as discovered | Eligible as discovered |
| Temporary refinements, chain buffs, conditioning/scouting bonuses | Run | Expire | Expire |
| Drilled next-belt exception | Run | Expire | Expire unless normally learned independently |
| Run injuries and recovery conditions | Separate run/career injury policy, not yet finalized | Resolve per future injury design | Resolve per future injury design |
| Completed promotion milestone | Career | Cannot be undone | Persist |

**Important:** *Protected carryover* describes progress surviving a **successful** run boundary. It does **not** shield unfinished progress against the **next defeated run**. A later defeat fractures all then-unmastered progress unless a separately and explicitly approved mechanic changes this rule. This prevents an accidental permanent bank for unmastered techniques.

## 58C.2 Road to Black Belt structure

The principal progression is **White → Blue → Purple → Brown → Black**, using belt-appropriate opponents and challenges. Belt colors represent BJJ knowledge and option access, not a direct raw-stat multiplier. All belts remain earned permanently.

A prototype road might consist of **three matches plus a promotion challenge**, but that count is *illustrative*, not a frozen game rule. Each belt road should offer different tactical demands rather than the same sequence with larger statistics.

| Road | Design emphasis | Illustrative competency evidence (not fixed move checklist) |
|---|---|---|
| White → Blue | Survival, escapes, guard basics, simple attacks | Demonstrate core positional competence |
| Blue → Purple | Preferred game, connected actions, counters | Demonstrate meaningful chains and transitions |
| Purple → Brown | Adaptation, reactions, sophisticated defense | Succeed when preferred plan is disrupted |
| Brown → Black | Broad, efficient, high-level technical awareness | Demonstrate versatile choices against experienced opposition |
| Black Belt career | Endgame, rivals, optional specialist challenges | New challenges, not a mandatory character reset |

### Promotion outcomes

- **Road success + required demonstrated competency:** award the next belt; retain mastered knowledge and the current incomplete development values as *protected carryover*; clear run-only modifiers; save career history; unlock the next road.
- **Road failure or promotion-challenge failure:** do not demote; record defeat and opponent/rival history; apply Memory Fracture to incomplete technique development; clear run-only modifiers; offer a new attempt from the current belt.
- **Competency missing despite match success:** do *not* automatically grant a belt. The eventual design must provide transparent ways to fulfill broadly defined competency criteria rather than forcing a single exact technique or random encounter. Whether an additional challenge is offered or the road counts as failed is **open**.
- **Player voluntarily abandons/restarts a run:** propose the same fracture treatment as defeat to prevent free rerolls, **but this is not yet frozen**. Suspend/save-and-resume must never count as abandonment.

Winning alone is not guaranteed promotion; the run should require competitive achievement **and** appropriate knowledge milestones, without demanding one arbitrary move.

## 58C.3 Technique acquisition: impression → reconstruction → mastery

The enemy-technique-learning inspiration is progressive acquisition, not an instant copy.

```text
Encounter opponent technique
        ↓
Fuzzy Impression (discovered, permanent record)
        ↓
Repeated observation / defense → understanding
        ↓
Reconstruction permitted when knowledge + rules allow
        ↓
Meaningful attempts → execution proficiency
        ↓
Refinement + evidence of valid application
        ↓
Mastered Technique (durable career knowledge)
        ↓
Optional chains / run-specific synergies
```

Technique discovery and technique eligibility are different. Seeing a next-belt or ruleset-restricted attack does not make it performable. A valid Drilled exception remains temporary and explicitly weaker.

**Two tracked learning dimensions are proposed:**
- **Understanding:** recognition of setup, purpose, defensive cues and tactical situation.
- **Execution proficiency:** ability to apply the known technique correctly with stamina/risk/response consequences.

The memory's apparent **clarity** may combine these for presentation, but a single UI clarity bar must not become an unchecked universal success percentage. At low clarity, a memory may only be recognizable; at a suitable knowledge threshold it may allow a simplified, legal reconstruction; refinement improves specific defined aspects. Mastery must never guarantee success.

### Proposed qualitative learning tiers (no numerical thresholds frozen)

1. **Fuzzy Impression:** recorded encounter, partially obscured silhouette; primarily recognition.
2. **Fragmented Recall:** developing understanding, perhaps an eligible limited reconstruction.
3. **Developing Technique:** usable where permitted with explicit setup, cost and counterplay drawbacks.
4. **Refined Technique:** normal competent application, with more sophisticated connections possible.
5. **Mastered Memory:** demonstrated durable competency; underlying technique knowledge persists across runs.

**Mastery evidence** should combine suitable understanding, meaningful attempts and at least one domain-appropriate demonstration against real resistance (e.g. a valid escape, stable transition, controlled submission threat). Exact evidence requirements are technique-family-specific and must be designed/tested later. Failed attempts may teach when they are mechanically meaningful; meaningless repeated spam must not create unlimited learning. Do not require winning by submission for every submission-family mastery.

## 58C.4 Memory Fracture and return to the next run

**Trigger:** normal promotion-road defeat. The game ends the run, not the fighter's career.

**Atomic resolution order (design target):**
1. Finalize match and run record, distinguishing loss from network/session disconnection.
2. Commit any legitimately earned mastery *before* processing the fracture.
3. Retain discoveries, permanent fundamentals, earned belt, mastered technique data, and career history.
4. Reset **all remaining unmastered** development to that technique's discovery baseline, including progress carried forward from a previous successful promotion.
5. Expire scoped run-only modifiers/grants.
6. Generate a post-run summary: retained, fractured, newly discovered, newly mastered, and belt unchanged.
7. Start a new road at the same belt only at the player's explicit next-run selection.

The proposed **Memory Fracture** animation shows incomplete artifact shapes splintering into faded silhouettes while fully mastered memories remain intact. This is a visual metaphor for interrupted consolidation, **not** a claim that the fighter suffers literal brain damage or amnesia.

**Previously discovered techniques** may receive *Memory Resonance*: a visibly explained recognition/relearning benefit when reencountered. Preserve this as a candidate reward rule; exact effect and size are not frozen. It must not instantly restore lost progress, enable forbidden techniques, or create a farmable infinite advantage.

## 58C.5 Run boundaries, success, and failure example

A Blue Belt begins **Road to Purple** with:
- Scissor Sweep: discovered, developing;
- Arm Drag: discovered, developing;
- Elbow-Knee Escape: mastered;
- one temporary Underhook Timing refinement.

**If defeated:** remain Blue; Scissor Sweep and Arm Drag revert to their discovered baselines; Elbow-Knee Escape remains mastered; Underhook Timing expires; record the attempt and allow another Road to Purple.

**If successfully promoted:** become Purple; retain unfinished Scissor Sweep and Arm Drag development as vulnerable carryover; retain mastered Elbow-Knee Escape; expire Underhook Timing; unlock the Purple-level repertoire subject to normal belt/ruleset conditions. Losing the next road would fracture still-unmastered Scissor Sweep and Arm Drag progress, too.

**No self-contradiction:** Success does *not* permanently save unmastered progress, and defeat does *not* erase discovery or undo a belt.

## 58C.6 Training is optional, not a mandatory separate gameplay mode

The game originally contained training as an event/reward concept, **not** a specified gym minigame. Do not silently introduce a mandatory training simulator.

- **Primary learning source:** live tactical exchanges (exposure, meaningful defense, real technique use).
- **Optional inter-match event:** choose a focus such as reconstructing an impression, refining a legal technique, recovery or scouting. Effects must be explicit and deterministic when implemented.
- **No forced training loop:** it must be possible to progress through reasonable match play without waiting for a rare gym reward.
- **No guaranteed effortless mastery:** rewards can assist but must respect knowledge gates and mastery evidence.

## 58C.7 Visual and interface integration

Memory Constellation remains a **view over the underlying rules**. It now displays persistence status as well as technique family and tactical connection:

- **Discovered / Fuzzy:** permanently archived silhouette;
- **Developing:** partially resolved icon and current understanding/execution;
- **Protected Carryover:** a visible *fragile* marker, not a mastered badge;
- **Mastered:** durable clarity/mark independent of run modifiers;
- **Run-only Upgrade:** distinct border/overlay with expiry at run closure;
- **Unavailable:** reason-coded BELT LOCKED, RULESET ILLEGAL, WRONG POSITION, SETUP NEEDED, etc.

The end-of-run interface shows a retained-versus-fractured comparison and current belt. The career screen shows completed roads, past opponents, rival encounters, belt promotions, losses and learned/mastered history. Combat still offers every **currently legal** action without a four-card cap; decision timers are independent from game time and are never reset by inspecting memories.

## 58C.8 Data boundaries and persistence schema (conceptual)

```text
CareerProfile:
  fighter_id, earned_belt, career_history,
  permanent_technique_knowledge, discovered_technique_ids,
  mastery_records, unlocked_career_options

TechniqueLearningRecord:
  technique_id, discovery_source,
  understanding_progress, execution_progress,
  learning_tier, mastered, protected_carryover,
  mastery_evidence

PromotionRun:
  run_id, starting_belt, target_belt,
  encounters, reward_seed, run_modifiers, drilled_grants,
  current_step, outcome

RunClosure:
  run_id, cause, belt_before, belt_after,
  newly_discovered, newly_mastered, fractured_progress,
  preserved_carryover, expired_run_effects
```

This is a **data model sketch**, not approval to implement all the fields before the playable match. Keep permanent identity/knowledge separate from volatile run state and deterministic match snapshots. A saved game must not confuse victory/promotion with a timeout/disconnect or award a belt twice when reloading a closure.

## 58C.9 Test obligations and safety against exploits

- Losing any promotion-road run leaves `earned_belt` unchanged.
- Successful authorized promotion advances exactly one valid belt step and persists through save/load.
- Discovered ID remains after fracture; its unfinished learning values reset, while mastery is unchanged.
- Success carries unfinished progress forward, but a later defeat fractures it if still unfinished.
- Processing run closure twice is idempotent: no double promotion, duplicate reward, or repeated reset anomalies.
- Core fundamentals remain available irrespective of memory inventory or fracture.
- No memory reward bypasses legal techniques, ruleset or belt restrictions except an explicit Drilled exception with limited duration and efficacy.
- Invalid/no-op exchanges cannot farm unlimited learning; deterministic identical event logs reproduce identical learning results.
- Unavailable technique reasons, retained/fractured summaries and career history are inspectable.
- A user-initiated normal pause/save is not a defeat.
- Timer expiry is a **decision policy event**, not necessarily a run failure; online forfeits and emergency submission windows need separate validated rules.

## 58C.10 Implementation priority and decision register

**Now (design only):** record the accepted career rules and expose the correct stable IDs / scope distinctions in future contracts.

**After playable headless full match:** implement a tiny single-fighter career with one prototype road and simple deterministic post-match reward choices, then test run defeat and promotion retention. Add a handful of known/fuzzy/mastered memories only after the legal-action API is stable.

**Later roguelike:** define belt-appropriate opponent pools and broadly demonstrated competency criteria, tune learning progression, build Memory Fracture, career journal, specialized constellation links and optional training events.

**Later polish:** visual icon blurring, shape connections, sound effects, and optional Black Belt endgame rival arcs. PvP and deep tactical AI remain deferred.

| Decision | State |
|---|---|
| Same fighter continues across runs | **Accepted** |
| Runs are roads to the next belt | **Accepted** |
| Defeat never removes earned belts | **Accepted** |
| Fundamentals, discoveries, mastered techniques and career history persist | **Accepted** |
| Incomplete learning fractures on failed run | **Accepted** |
| Successful promotion preserves incomplete progress, but it can fracture after a later loss | **Accepted** |
| Run-only buffs, rewards and Drilled access expire at run boundary | **Accepted** |
| Technical competency plus competitive achievement for promotion | **Accepted direction**, criteria open |
| Learning through matches; no mandatory training minigame | **Accepted direction** |
| Exact number of matches, mastery thresholds, learning rates, encounter rewards | **OPEN — balance/prototype** |
| Voluntary abandonment penalty, incomplete-competency road handling, long-term injury persistence | **OPEN — design** |
| Black Belt specialist/rival endgame | **Planned direction**, content deferred |
| Godot / typed GDScript migration | **Still open; require Mount parity spike** |

**Development guardrail:** Do not begin this career implementation before a complete headless human-play BJJ match. This is a concrete roadmap, not permission to restart an architecture-first or AI-first detour.

---

# 59. Save / Product Systems

Status: ⚪

Still required eventually:

- save/load;
- run persistence;
- career/meta persistence;
- settings;
- accessibility;
- key/controller support;
- audio;
- results/history screen;
- character screen;
- run map/event screen.

These do not block the first headless match.

---

# 60. Multiplayer

Status: ⏸

Deferred until single-player is proven.

Future issues:

- synchronized paused decision windows;
- simultaneous hidden commitments;
- initiator/responder secrecy;
- latency;
- disconnects;
- anti-stalling;
- dual-clock decision deadlines, server-authoritative wall-clock enforcement, timeout fallback and consecutive-miss policy;
- fairness.

---

# 61. Content Research Pipeline

Use previously collected references to populate techniques and transitions:

- GrappleMap;
- jiu-jitsu graph projects;
- BJJ Heroes;
- Submission Searcher;
- BJJ Mental Models;
- Dr. Jiu-Jitsu;
- trusted instructional/video references.

Each technique should eventually record:

```text
source/provenance
start position
substate
requirements
common responses
interaction tags
result destinations
belt requirement
ruleset legality
review status
```

Do not import hundreds of techniques before the first complete graph is playable.

---

# 62. Testing Philosophy

Keep the rigorous infrastructure that has already paid off:

✅ determinism  
✅ replay  
✅ invariants  
✅ regression tests  
✅ bug-seed tests  
✅ transition validation  
✅ exact state semantics  

Change the priority.

## New order

1. Does the mechanic work?
2. Does the interaction make BJJ sense?
3. Can a human understand it?
4. Does it create a real choice?
5. Does it connect to the rest of the graph?
6. Is it deterministic and testable?
7. Then balance it.
8. Then optimize AI.

Avoid:

- giant policy campaigns before breadth;
- tuning one node for months;
- treating simulations as the product.

---

# 63. Master Development Roadmap

## Phase 0 — Close TE-2
🟡 Current

- finish selected fourth surface;
- stop after four completed surfaces;
- preserve partial evidence;
- close as OPEN / INCOMPLETE;
- no rerun;
- no promotion;
- pause advanced AI.

**Exit:** AI no longer blocks game development.

---

## Phase 1 — Generalize Mount
🔵

- define PositionContract;
- refactor/integrate Mount through it;
- generalize transitions;
- generalize setup hooks;
- generalize submission hooks;
- preserve Mount regressions.

**Exit:** a second position can use the same architecture.

---

## Phase 2 — Position Graph v1
🔵

Recommended implementation order:

1. Standing
2. Closed Guard
3. Side Control
4. Half Guard
5. Back Control
6. Turtle
7. Open Guard
8. Front Headlock
9. Leg Entanglement
10. Mount integration/regression throughout

Each gets:

- 3–5 meaningful actions per side;
- core responses;
- commitments;
- setup hooks;
- basic stamina behavior;
- transition destinations;
- applicable submission routes.

**Exit:** all ten nodes are reachable through legitimate grappling transitions.

---

## Phase 3 — Standing / Takedowns
🔵

Initial set:

- Single Leg
- Double Leg
- Body Lock
- Snapdown
- Guard Pull

Defenses:

- Sprawl
- Whizzer
- Pummel
- Frame
- Counter-shot
- Front-headlock/guillotine counter routes

**Exit:** every normal match can begin Standing.

---

## Phase 4 — Universal Submission Coverage
🔵

Initial families:

- Americana
- Armbar
- Triangle
- Rear Naked Choke
- Guillotine
- D'Arce / Anaconda route
- Straight Ankle Lock

All use:

```text
THREAT → CONTROL → FINISH
```

**Exit:** submission machinery works from multiple position nodes.

---

## Phase 5 — Human Player API
🔵

Implement:

- GameSnapshot
- DecisionWindow
- LegalAction
- LegalResponse
- CommitmentChoice
- MatchResult
- submit_player_choice

**Exit:** a human can control the engine without internal access.

---

## Phase 6 — Complete Headless Match
🔵

### North-Star Milestone #1

> **Axel plays a complete BJJ match from Standing against the computer, manually choosing techniques and commitment, with the match moving naturally through multiple positions and possibly ending by submission.**

This milestone becomes the primary near-term development target.

---

## Phase 7 — Fighter Identity
🔵

Implement:

- attributes;
- five Styles;
- Belts;
- technique pools;
- Recognition;
- Chain Depth;
- traits/abilities;
- technique loadout.

**Exit:** fighters with different builds produce visibly different strategies.

---

## Phase 8 — Roguelike
🔵

Implement:

- run generation;
- opponents;
- scouting;
- training;
- technique drafts;
- Drilled techniques;
- traits;
- injuries;
- recovery;
- events;
- rewards;
- permanent progression;
- finale.

### North-Star Milestone #2

> **Axel completes a short roguelike run where his fighter changes meaningfully because of techniques, training, traits, injuries, scouting and opponents.**

---

## Phase 9 — Frontend
⚪

Build the first visual frontend around the already-playable Player API.

---

## Phase 10 — Depth / Content Expansion
⏸

Only after breadth:

- deeper Guard systems;
- more subpositions;
- larger technique catalog;
- more submissions;
- more traits;
- more events;
- additional rulesets;
- scoring polish;
- advanced AI;
- 3D/Blender visualization;
- animation;
- career depth.

---

# 64. Master Checklist

## Core Engine

- [x] Continuous simulated clock
- [x] Decision-window framework
- [x] Initiative
- [x] Stamina
- [x] LOW / MEDIUM / HIGH
- [x] Axis/bands
- [x] Deterministic resolution
- [x] Replay/testing
- [x] Stalling foundation
- [x] Submission foundation
- [ ] PositionContract
- [ ] Generic transition graph

## Positions

- [ ] Standing
- [ ] Closed Guard
- [ ] Open Guard
- [ ] Half Guard
- [ ] Side Control
- [x] Mount
- [ ] Back Control
- [ ] Turtle
- [ ] Front Headlock
- [ ] Leg Entanglement

## Transition Families

- [ ] Takedowns
- [ ] Guard Pull
- [ ] Passes
- [ ] Sweeps
- [ ] Escapes
- [ ] Reversals
- [ ] Back Takes
- [ ] Mat Returns
- [ ] Scramble resolution

## Submissions

- [x] Submission foundation / Mount implementation
- [ ] Position-independent submission overlay
- [ ] Americana
- [ ] Armbar
- [ ] Triangle
- [ ] Rear Naked Choke
- [ ] Guillotine
- [ ] D'Arce / Anaconda
- [ ] Straight Ankle Lock
- [ ] Submission switching
- [ ] Chain Depth generalized
- [ ] Tap / Refuse integrated across all positions
- [ ] Injury/unconsciousness run consequences

## Fighter Identity

- [ ] Power
- [ ] Speed
- [ ] Stamina as fighter attribute layer
- [ ] Base
- [ ] Mobility
- [ ] Smasher
- [ ] Lanky
- [ ] Explosive
- [ ] Technician
- [ ] Wrestler
- [ ] Belts
- [ ] Technique pools
- [ ] Recognition
- [ ] Chain Depth by belt
- [ ] Traits / abilities

## Human Play

- [ ] GameSnapshot
- [ ] DecisionWindow
- [ ] LegalAction
- [ ] LegalResponse
- [ ] CommitmentChoice
- [ ] MatchResult
- [ ] Human terminal controller
- [ ] Variable-length legal technique/memory presentation (no fixed four-choice cap)
- [ ] DecisionTimerPolicy/session API (simulated clock separate from wall time)
- [ ] Complete manual match from Standing

## Match Systems

- [ ] Choose first production ruleset
- [ ] Scoring table if Points
- [ ] Timeout outcome
- [ ] Standing stalling
- [ ] Guard stalling
- [ ] Universal advancement clocks
- [ ] Fast-forward pacing
- [ ] Manual Read / Act production behavior

## Roguelike

- [ ] Run structure
- [ ] Opponent generation
- [ ] Opponent scouting
- [ ] Training
- [ ] Technique draft
- [ ] Technique variants
- [ ] Memory reward types and bounded modifiers
- [ ] Fundamental / learned / run / meta memory separation
- [ ] Drilled techniques
- [ ] Traits
- [ ] Injuries
- [ ] Recovery
- [ ] Events
- [ ] Rewards
- [ ] Promotion
- [ ] Permanent progression
- [ ] Coaches
- [ ] Gym upgrades
- [ ] Run finale

## Product / Frontend

- [ ] Save/load
- [ ] Settings
- [ ] Accessibility
- [ ] Frontend
- [ ] Match HUD
- [ ] Memory-shaped technique UI prototype and accessibility
- [ ] Dual-clock decision countdown visualization
- [ ] Character screen
- [ ] Roguelike run screen
- [ ] Event/training screens
- [ ] Result screen
- [ ] Visual position representation
- [ ] Audio/presentation

---

# 65. Critical Open Decisions

These are real missing decisions—not reasons to restart architecture research.

## Before deep Guard implementation
- [ ] **Gi or No-Gi first?**

## Before first complete production match
- [ ] Which ruleset is first?
- [ ] Points values if Points
- [ ] Timeout/end rule
- [ ] exact Standing neutral/stalling behavior

## Before Belt system implementation
- [ ] exact technique-by-belt pool
- [ ] Chain Depth per belt
- [ ] belt-specific Recognition detail
- [ ] promotion milestones
- [ ] illegal/restricted submissions by belt/ruleset

## Before Roguelike implementation
- [ ] run finale structure
- [ ] technique loadout/capacity
- [ ] memory reward stacking, rarity and acquisition
- [ ] advanced-memory capacity without restricting fundamentals
- [ ] permanent vs temporary technique learning
- [ ] injury severity/recovery model
- [ ] event frequency
- [ ] promotion/meta reward balance

## Before Frontend art production
- [ ] 2D-first vs early 3D representation
- [ ] visual style
- [ ] animation scope
- [ ] memory silhouette/shape and technique-library navigation

---

# 66. Explicitly Deferred

The following are not required for the first complete playable game:

⏸ perfect AI  
⏸ completing TE-2  
⏸ every BJJ technique  
⏸ every Guard subtype  
⏸ every ruleset  
⏸ multiplayer  
⏸ perfect balance  
⏸ advanced career mode  
⏸ full 3D animation  
⏸ giant Blender pose library  
⏸ exhaustive technique database  
⏸ complex physics-driven grappling  

---

# 67. Project Guardrails

1. **Breadth before depth.**
2. **Human play before advanced AI.**
3. **Mount is the template, not the game.**
4. **Commitment modifies technique; it does not replace technique choice.**
5. **Belts represent knowledge rather than raw physical scaling.**
6. **Positions are nodes; techniques/responses are edges.**
7. **Submissions are a reusable overlay.**
8. **Major transitions come from deliberate actions, not passive drift.**
9. **Initiative is situational, not permanently owned by top.**
10. **Neutral/scramble states can use simultaneous decisions.**
11. **Recognition adds information without hiding basic truth.**
12. **Feints are real low-commitment threats, not fake UI information.**
13. **Stalling is measured by progress, not button presses.**
14. **The roguelike layer must create meaningful build decisions.**
15. **Frontend starts after a complete headless match.**
16. **Backend perfection must not delay the actual game again.**
17. **AI must support gameplay—not dictate the roadmap.**
18. **The game must feel like BJJ, not a generic UFC grappling game.**

---

# 68. Definition of “We Have the Game”

The project crosses from engine/research into an actual playable game when:

- [ ] Match starts Standing.
- [ ] Human chooses techniques.
- [ ] Opponent responds.
- [ ] Neutral situations can resolve simultaneous choices.
- [ ] LOW/MEDIUM/HIGH modifies technique commitment.
- [ ] Takedowns work.
- [ ] All ten core positions exist.
- [ ] Position transitions make BJJ sense.
- [ ] Sweeps work.
- [ ] Passes work.
- [ ] Escapes work.
- [ ] Reversals work.
- [ ] Back takes work.
- [ ] Scrambles resolve meaningfully.
- [ ] Multiple submission families work.
- [ ] Tap / Refuse works.
- [ ] Match can end by Tap/Stoppage/time.
- [ ] Styles make fighters feel different.
- [ ] Belts change knowledge and available options.
- [ ] Recognition changes information quality.
- [ ] Traits create different builds.
- [ ] A full human-controlled match works.
- [ ] A short roguelike run works.
- [ ] Frontend can consume the Player API without engine-specific hacks.

At that point the project is no longer:

> **a simulation laboratory centered on Mount.**

It is:

> **the tactical BJJ roguelike we intended to build.**

---

# Appendix A — What Was Removed From v9

The following v9 material is intentionally **not** carried forward as master project guidance because it was Mount-v0 scaffolding or has been superseded by implementation:

- Mount v0 fixed alternating initiator schedule;
- fixed 5-second prototype decision interval as a project-wide rule;
- placeholder Mount drift rates;
- the original Mount-only `HOLD/PRESSURE` vs `ESCAPE/PROTECT` mini-table;
- the 18-entry Mount-v0 lookup-table implementation plan;
- old Mount-v0 CLI override requirements;
- the old `--enumerate` checker specification;
- Mount-v0 logging-field specification;
- Mount-v0 run-end/report specification;
- staged `v0.1`–`v0.5` implementation roadmap;
- “do not add stamina/setup/submissions/AI” prototype restrictions;
- “next task is implement Mount v0” final freeze language;
- old architecture-freeze language that treated Mount as the immediate project boundary.

Those items served their purpose during the Mount prototype and are now historical implementation documentation.

They should remain available in git history/docs if needed for archaeology, but they should not govern new game development.

---

# Appendix B — Important v9 Concepts Preserved

The merged guide deliberately preserves these durable ideas:

- continuous simulated time;
- paused slow-motion decision windows;
- behavior drift;
- Manual Read / Act;
- fast-forward through stable stretches;
- broad two-sided positional axis;
- Exit Maps;
- triggered initiative;
- initiator/responder established-position exchanges;
- simultaneous Standing/scramble choices;
- action-tag interaction;
- setup progress;
- deterministic resolution;
- five physical attributes;
- Styles;
- Belt = knowledge;
- Recognition adds information;
- Feints as real low-commitment threats;
- Belt vs Run distinction;
- Drilled techniques;
- milestone-based promotion;
- THREAT → CONTROL → FINISH submissions;
- submission overlay on position;
- submission switching and Chain Depth;
- Emergency Submission Defense;
- Tap / Refuse;
- injury/unconsciousness run consequences;
- flash submissions;
- points/submission-only rulesets;
- advancement/stalling clocks;
- visible stalling penalties;
- time as strategic resource;
- roguelike run structure;
- permanent/meta progression;
- Gi vs No-Gi decision;
- authored animation with game state authoritative;
- single-player-first multiplayer deferral.

---

# Appendix C — Current North Stars

## North Star 1 — Actual BJJ Match

> **Start Standing and play a complete match manually, moving naturally through multiple positions and ending by submission or time.**

## North Star 2 — Actual Roguelike

> **Complete a short run where technique choices, traits, training, injuries, scouting, belt knowledge and opponent styles meaningfully change how later matches play.**

Everything else should support one of these two goals. The dual-clock deadline protects decision pacing without consuming BJJ match time; Technique Memories are a presentation and progression layer, not a fixed four-action card hand.