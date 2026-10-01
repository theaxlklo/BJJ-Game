# Mount v0 — Canonical BJJ Technique Naming Lock

## Status

This is an implementation addendum to **BJJ Game Concept v9 — Mount v0 CODE-READY FREEZE**.

It does **not** create v10.

It does **not** reopen the Mount v0 architecture.

It does **not** change:

```text
axis mechanics
hysteresis
drift
behavior modifiers
positional modifiers
resolution order
escape threshold
Bridge special rule
failure clamp
Exit Maps
cycle timing
initiative alternation
run-end conditions
```

This revision **does** correct the hand-authored lookup grades where static analysis exposed an unreachable Exit Map branch or where the assigned grade contradicted the BJJ meaning of the named technique/response. That is permitted by v9's freeze rule for concrete failures such as an unreachable branch, dominant lookup loop, or obviously wrong BJJ interaction.

Its purpose is to lock the BJJ terminology **and the corrected first-pass 18-grade matrix** before implementation so prototype shorthand or a mathematically broken table does not become permanent engine behavior.

The guiding rule is:

> Use recognized BJJ technique terminology when a recognized name exists. Use precise descriptive terminology for tactical reactions that do not have one universal technique name. Never invent a fake standardized BJJ name merely to make the UI sound more technical.

---

# 1. Naming Layers

Every action and response has four naming layers.

| Layer | Purpose | Example |
|---|---|---|
| Stable ID | Permanent machine identifier | `mount.bottom.elbow_knee_escape` |
| Canonical name | Full player-facing name | `Elbow-Knee Escape` |
| Short name | Compact CLI/UI display | `Elbow-Knee` |
| Aliases | Search/input/educational terminology | `Elbow Escape`, `Knee-Elbow Escape`, `Shrimp Escape` |

The old v9 terminology remains only as a `legacy_name` or design-reference field.

It should not be the primary player-facing terminology once implementation begins.

---

# 2. Final Mount v0 Technique Set

## Top-initiated actions

| Stable ID | Canonical name | Short name | v9 legacy name |
|---|---|---|---|
| `mount.top.high_mount_climb` | **High Mount Climb** | Climb High | Climb High |
| `mount.top.crossface_pressure` | **Crossface Pressure** | Crossface | Pressure Shift |
| `mount.top.americana_arm_isolation` | **Americana Arm Isolation** | Americana Isolation | Arm Isolation |

## Bottom-initiated actions

| Stable ID | Canonical name | Short name | v9 legacy name |
|---|---|---|---|
| `mount.bottom.bridge` | **Bridge** | Bridge | Bridge |
| `mount.bottom.elbow_knee_escape` | **Elbow-Knee Escape** | Elbow-Knee Escape | Elbow Escape |
| `mount.bottom.trap_and_roll_escape` | **Trap-and-Roll Escape** | Trap-and-Roll | Trap-and-Roll |

## Top responses

| Stable ID | Canonical name | Short name | v9 legacy name |
|---|---|---|---|
| `mount.top_response.post_and_base` | **Hand Post and Base** | Post | Post |
| `mount.top_response.wide_mount_base` | **Wide Mount Base** | Wide Base | Widen Base |
| `mount.top_response.hip_follow_repummel` | **Hip Follow and Knee Re-Pummel** | Hip Follow | Follow Hips |

## Bottom responses

| Stable ID | Canonical name | Short name | v9 legacy name |
|---|---|---|---|
| `mount.bottom_response.forearm_frame` | **Forearm Frame** | Frame | Frame |
| `mount.bottom_response.turn_in_recovery` | **Turn-In Recovery** | Turn In | Turn In |
| `mount.bottom_response.tight_elbow_arm_defense` | **Tight-Elbow Arm Defense** | Tight Elbows | Protect Arm |

These twelve names are the Mount v0 canonical vocabulary.

---

# 3. High Mount Climb

```text
Stable ID:
mount.top.high_mount_climb

Canonical:
High Mount Climb

Short:
Climb High

Legacy:
Climb High
```

### BJJ meaning

Top advances the knees and hips higher on Bottom's torso in an attempt to reduce Bottom's useful hip movement, separate Bottom's elbows from their lower-body defensive structure, and improve Mount control.

The action represents the mechanics of progressing toward a higher Mount.

### Important v0 limitation

Mount v0 does **not** create a separate `High Mount` positional state after success.

Therefore:

```text
High Mount Climb succeeds
≠ automatically enter a High Mount node
```

Instead:

```text
High Mount Climb succeeds
→ Mount control axis improves
```

Later versions may model:

```text
Low Mount
Standard Mount
High Mount
Technical Mount
S-Mount
```

as explicit subpositions.

Mount v0 does not.

### Do not call this S-Mount

S-Mount must remain a distinct future technique/position.

Never configure:

```text
S-Mount
```

as an alias of:

```text
High Mount Climb
```

### Accepted aliases

```text
Climb High
Climb to High Mount
High Mount Climb
Walk Knees High
Knees to Armpits
```

The **bare alias `High Mount` is intentionally reserved** for the future High Mount subposition and must not resolve to this action. The last two aliases are descriptive search aliases, not preferred display names.

---

# 4. Crossface Pressure

```text
Stable ID:
mount.top.crossface_pressure

Canonical:
Crossface Pressure

Short:
Crossface

Legacy:
Pressure Shift
```

### BJJ meaning

Top uses upper-body pressure and head/shoulder control to compromise Bottom's alignment, flatten or turn Bottom, and make hip movement and effective framing more difficult.

This is a **control action**.

It is not a submission.

It does not automatically create another positional state.

### v0 mechanical meaning

```text
success
→ stronger Mount control

failure
→ Mount control deteriorates
```

### Accepted aliases

```text
Crossface
Crossface Pressure
Shoulder Pressure
Crossface Control
```

Do not use `Pressure Shift` as the main UI name.

That name remains only for compatibility with the design document.

---

# 5. Americana Arm Isolation

```text
Stable ID:
mount.top.americana_arm_isolation

Canonical:
Americana Arm Isolation

Short:
Americana Isolation

Legacy:
Arm Isolation
```

### BJJ meaning

Top attempts to separate and control one of Bottom's arms in the bent-arm configuration associated with an Americana attack.

The tactical objective in Mount v0 is **arm isolation**, not completion of the submission.

### Critical v0 rule

```text
Americana Arm Isolation
≠ Americana Finish
```

Mount v0.3 owns submission progression.

Therefore this action may improve control or create a conceptual attack opportunity, but Mount v0 must never produce:

```text
TAP
submission
injury
Americana Finish
```

from this action.

### Accepted aliases

```text
Americana Setup
Americana Isolation
Americana Arm Isolation
Bent-Arm Isolation
```

`Keylock` may later exist as a glossary/search synonym, but `Americana` should be the primary BJJ-facing term.

---

# 6. Bridge

```text
Stable ID:
mount.bottom.bridge

Canonical:
Bridge

Short:
Bridge

Legacy:
Bridge
```

### BJJ meaning

Bottom explosively elevates the hips to disrupt Top's balance, alter Top's weight distribution, create space, or force Top to react.

### Critical distinction

Bridge is **not** the same action as Trap-and-Roll Escape in the engine.

Therefore the canonical action should remain simply:

```text
Bridge
```

Do **not** use:

```text
Upa
```

as Bridge's primary alias.

Many BJJ curricula use `upa` for the complete bridge-and-roll/trap-and-roll escape. Using it for both actions would make the game's vocabulary ambiguous.

### v0 mechanical identity

Bridge is a **positional disruption action**.

It is explicitly not escape-capable.

Even if its result would mathematically reach or cross the Mount escape threshold:

```text
axis → +0.10
Mount remains
Exit Map does not fire
```

This is intentional.

Bridge creates the opportunity.

It does not complete the escape.

### Accepted aliases

```text
Bridge
Hip Bridge
Bridging
Bridge to Create Space
```

Do not alias it to:

```text
Trap-and-Roll
Bridge-and-Roll
Upa Escape
```

Those belong to the separate escape action.

---

# 7. Elbow-Knee Escape

```text
Stable ID:
mount.bottom.elbow_knee_escape

Canonical:
Elbow-Knee Escape

Short:
Elbow-Knee Escape

Legacy:
Elbow Escape
```

### BJJ meaning

Bottom uses framing, hip movement, and knee insertion to reclaim space between the bodies and recover guard.

This family is commonly known as the elbow-knee escape, elbow escape, knee-elbow escape, or mount shrimp escape.

### v0 Exit Map

If the final modified grade is:

```text
Success
```

and the escape threshold is reached:

```text
→ Half Guard
```

If the final modified grade is:

```text
Strong Success
```

and the escape threshold is reached:

```text
→ Open Guard
```

The destination is selected by **final grade**.

It is not selected by how far the numerical axis overshoots the threshold.

### Accepted aliases

```text
Elbow Escape
Elbow-Knee Escape
Knee-Elbow Escape
Knee-Elbow Mount Escape
Shrimp Escape
Mount Shrimp Escape
```

### Preferred educational text

```text
Use a frame and hip escape to create enough space to insert the knee and recover guard.
```

---

# 8. Trap-and-Roll Escape

```text
Stable ID:
mount.bottom.trap_and_roll_escape

Canonical:
Trap-and-Roll Escape

Short:
Trap-and-Roll

Legacy:
Trap-and-Roll
```

### BJJ meaning

Bottom removes Top's ability to base on one side by controlling/trapping the appropriate posting structures, then bridges and rolls Top toward the compromised side.

`Trap-and-Roll`, `Bridge-and-Roll`, and `Upa` are widely used for this mount-escape family.

### v0 Exit Map

If:

```text
final grade = Success
or
final grade = Strong Success
```

and the escape threshold is reached:

```text
→ Reversal
```

Mount v0 records only:

```text
Reversal
```

It does not yet need to determine whether the post-reversal position is specifically:

```text
Closed Guard
Open Guard
Half Guard
another stabilization state
```

That would add positional detail beyond Mount v0.

### Accepted aliases

```text
Trap-and-Roll
Trap-and-Roll Escape
Bridge-and-Roll
Bridge-and-Roll Escape
Upa
Upa Escape
```

---

# 9. Hand Post and Base

```text
Stable ID:
mount.top_response.post_and_base

Canonical:
Hand Post and Base

Short:
Post

Legacy:
Post
```

### BJJ meaning

Top responds to destabilization by establishing a posting point and restoring enough base to avoid being displaced or rolled.

Against Trap-and-Roll, this represents Top attempting to preserve or recover the post before Bottom fully removes it.

### Important abstraction

The engine does not currently track:

```text
left arm trapped
right arm free
left foot trapped
right foot free
head post available
```

Therefore this response represents the **post/base defensive concept** rather than a fully anatomical simulation.

### Accepted aliases

```text
Post
Hand Post
Post the Hand
Post and Base
Base Out
```

---

# 10. Wide Mount Base

```text
Stable ID:
mount.top_response.wide_mount_base

Canonical:
Wide Mount Base

Short:
Wide Base

Legacy:
Widen Base
```

### BJJ meaning

Top lowers or widens the support structure of Mount to make displacement more difficult.

It represents base management rather than a dedicated attack.

### Do not rename this Grapevine

A grapevine is a more specific leg-control configuration.

Mount v0 does not track enough leg anatomy to claim that every use of `Wide Base` is specifically a grapevine.

Therefore:

```text
Wide Mount Base
```

is the correct v0 name.

A future Grapevine Mount technique can be modeled separately.

### Accepted aliases

```text
Wide Base
Widen Base
Wide Mount Base
Base Wide
Lower the Base
```

---

# 11. Hip Follow and Knee Re-Pummel

```text
Stable ID:
mount.top_response.hip_follow_repummel

Canonical:
Hip Follow and Knee Re-Pummel

Short:
Hip Follow

Legacy:
Follow Hips
```

### BJJ meaning

Top tracks Bottom's hip movement instead of allowing Bottom to create separation, while re-establishing the knee/leg relationship needed to prevent Bottom's knee from entering cleanly.

Its clearest v0 purpose is defending the Elbow-Knee Escape.

### Why the name is descriptive

There is no need to pretend this entire reaction has one universally standardized BJJ technique name.

The movement being modeled is more precise than the old generic label `Follow Hips`, so the canonical display name is:

```text
Hip Follow and Knee Re-Pummel
```

Canonical player-facing names must use the word `and`; `+` is not used in canonical technique names.

### Accepted aliases

```text
Hip Follow
Follow the Hips
Knee Re-Pummel
Follow and Re-Pummel
Hip Tracking
```

---

# 12. Forearm Frame

```text
Stable ID:
mount.bottom_response.forearm_frame

Canonical:
Forearm Frame

Short:
Frame

Legacy:
Frame
```

### BJJ meaning

Bottom uses skeletal structure through the forearm/elbow region to manage distance, redirect pressure, and prevent Top from freely collapsing into the desired control.

### Accepted aliases

```text
Frame
Forearm Frame
```

`Hip Frame` and `Body Frame` are intentionally **not** aliases. They can describe different frame placements and would make this response less precise.

---

# 13. Turn-In Recovery

```text
Stable ID:
mount.bottom_response.turn_in_recovery

Canonical:
Turn-In Recovery

Short:
Turn In

Legacy:
Turn In
```

### BJJ meaning

Bottom turns toward the controlling player to restore useful alignment rather than remaining flattened or rotated in a direction that strengthens Top's control.

### Why this is not given a flashier technique name

`Turn In` is a tactical movement principle.

Different gyms and specific situations attach different techniques to it.

Mount v0 does not contain enough anatomical state to claim a more specific technique.

Therefore:

```text
Turn-In Recovery
```

is deliberately descriptive and technically honest.

### Accepted aliases

```text
Turn In
Turn-In
Turn-In Recovery
Turn Toward
Recover Alignment
```

---

# 14. Tight-Elbow Arm Defense

```text
Stable ID:
mount.bottom_response.tight_elbow_arm_defense

Canonical:
Tight-Elbow Arm Defense

Short:
Tight Elbows

Legacy:
Protect Arm
```

### BJJ meaning

Bottom retracts the vulnerable arm structure, keeping the elbow close to the torso instead of allowing Top to separate the elbow and isolate the arm.

Its specific Mount v0 purpose is to defend against:

```text
Americana Arm Isolation
```

### Why this is NOT called Elbow-Knee Connection

The elbow-knee connection is a broader and legitimate BJJ defensive concept involving maintaining structural connection between the upper and lower limbs.

However, replacing `Protect Arm` with `Elbow-Knee Connection` would change the semantic meaning of the v9 matchup table.

A genuine elbow-knee connection would also logically interfere strongly with Top's attempt to climb into High Mount.

The existing matrix intentionally treats this response as **specifically prioritizing arm safety**, which can concede other positional progress.

Therefore Mount v0 uses:

```text
Tight-Elbow Arm Defense
```

not:

```text
Elbow-Knee Connection
```

A full `Elbow-Knee Connection` defensive action can be introduced later when the positional model is richer.

### Accepted aliases

```text
Tight Elbows
Arm Retraction
Elbow Retraction
Elbow-to-Ribs Defense
Protect the Arm
Tight-Elbow Defense
```

---

# 15. Final Raw Lookup Table — Top Initiates

Grades remain from the **initiator's perspective**.

| Top action | Bottom response | Raw grade | Tactical interpretation |
|---|---|---:|---|
| **High Mount Climb** | **Forearm Frame** | Success | A committed frame can separate Bottom's elbow structure from the ribs/armpit line and give Top room to climb; the frame is not the preferred answer to the positional climb. |
| **High Mount Climb** | **Turn-In Recovery** | Contested | Turning and adjusting alignment interferes with the climb but does not directly shut it down. |
| **High Mount Climb** | **Tight-Elbow Arm Defense** | Failure | Keeping the elbows compact to the ribs directly protects the space Top needs to occupy with the knees when climbing high. |
| **Crossface Pressure** | **Forearm Frame** | Failure | A correctly placed frame directly denies or redirects the upper-body connection needed for the crossface pressure. |
| **Crossface Pressure** | **Turn-In Recovery** | Success | The crossface controls head direction and therefore directly frustrates Bottom's attempt to turn in and recover alignment. |
| **Crossface Pressure** | **Tight-Elbow Arm Defense** | Strong Success | Bottom prioritizes compact arm safety while offering no dedicated answer to head/shoulder control, allowing Top to impose strong crossface pressure. |
| **Americana Arm Isolation** | **Forearm Frame** | Strong Success | An extended or committed framing structure gives Top a strong opportunity to separate and isolate the arm. |
| **Americana Arm Isolation** | **Turn-In Recovery** | Contested | Movement and alignment recovery complicate the isolation without being a dedicated arm defense. |
| **Americana Arm Isolation** | **Tight-Elbow Arm Defense** | Strong Failure | Bottom directly retracts and protects the structure Top is attempting to isolate. |

Machine representation:

```text
mount.top.high_mount_climb
    vs mount.bottom_response.forearm_frame
    = SUCCESS

mount.top.high_mount_climb
    vs mount.bottom_response.turn_in_recovery
    = CONTESTED

mount.top.high_mount_climb
    vs mount.bottom_response.tight_elbow_arm_defense
    = FAILURE

mount.top.crossface_pressure
    vs mount.bottom_response.forearm_frame
    = FAILURE

mount.top.crossface_pressure
    vs mount.bottom_response.turn_in_recovery
    = SUCCESS

mount.top.crossface_pressure
    vs mount.bottom_response.tight_elbow_arm_defense
    = STRONG_SUCCESS

mount.top.americana_arm_isolation
    vs mount.bottom_response.forearm_frame
    = STRONG_SUCCESS

mount.top.americana_arm_isolation
    vs mount.bottom_response.turn_in_recovery
    = CONTESTED

mount.top.americana_arm_isolation
    vs mount.bottom_response.tight_elbow_arm_defense
    = STRONG_FAILURE
```

---

# 16. Final Raw Lookup Table — Bottom Initiates

| Bottom action | Top response | Raw grade | Tactical interpretation |
|---|---|---:|---|
| **Bridge** | **Hand Post and Base** | Strong Failure | Top directly answers the destabilization by restoring a posting structure. |
| **Bridge** | **Wide Mount Base** | Failure | A wider base absorbs much of the bridge and limits displacement. |
| **Bridge** | **Hip Follow and Knee Re-Pummel** | Success | Top answers the wrong immediate problem; Bottom creates meaningful disruption/space. |
| **Elbow-Knee Escape** | **Hand Post and Base** | Strong Success | Top prepares for a roll/base problem rather than directly stopping hip movement and knee insertion. |
| **Elbow-Knee Escape** | **Wide Mount Base** | Success | A wide base is useful against displacement but does not directly stop shrimping, hip separation, and knee insertion; Bottom makes real guard-recovery progress. |
| **Elbow-Knee Escape** | **Hip Follow and Knee Re-Pummel** | Strong Failure | Top uses the purpose-built response to track the hip and deny/reverse the knee insertion. |
| **Trap-and-Roll Escape** | **Hand Post and Base** | Strong Failure | Posting/base restoration directly attacks the mechanism that makes the roll possible. |
| **Trap-and-Roll Escape** | **Wide Mount Base** | Failure | Broader base makes the reversal harder but is less direct than restoring the post. |
| **Trap-and-Roll Escape** | **Hip Follow and Knee Re-Pummel** | Strong Success | Top commits to tracking hip/knee movement instead of solving the missing-base problem and is highly vulnerable to the reversal. |

Machine representation:

```text
mount.bottom.bridge
    vs mount.top_response.post_and_base
    = STRONG_FAILURE

mount.bottom.bridge
    vs mount.top_response.wide_mount_base
    = FAILURE

mount.bottom.bridge
    vs mount.top_response.hip_follow_repummel
    = SUCCESS

mount.bottom.elbow_knee_escape
    vs mount.top_response.post_and_base
    = STRONG_SUCCESS

mount.bottom.elbow_knee_escape
    vs mount.top_response.wide_mount_base
    = SUCCESS

mount.bottom.elbow_knee_escape
    vs mount.top_response.hip_follow_repummel
    = STRONG_FAILURE

mount.bottom.trap_and_roll_escape
    vs mount.top_response.post_and_base
    = STRONG_FAILURE

mount.bottom.trap_and_roll_escape
    vs mount.top_response.wide_mount_base
    = FAILURE

mount.bottom.trap_and_roll_escape
    vs mount.top_response.hip_follow_repummel
    = STRONG_SUCCESS
```

## Static Exit-Branch Reachability Check

The corrected Elbow-Knee row must preserve **both** v9 Exit Map branches.

### Half Guard

```text
Elbow-Knee Escape
vs Wide Mount Base
raw grade = Success
```

At Loose or Stable there is no downward positional modifier. A Bottom `Success` produces `axis_delta = -1.0`. Therefore any legal state at or below `+1.10` can reach the `+0.10` escape threshold and exit to:

```text
Half Guard
```

This makes Half Guard reachable.

### Open Guard

```text
Elbow-Knee Escape
vs Hand Post and Base
raw grade = Strong Success
```

At Loose or Stable there is no downward positional modifier. A Bottom `Strong Success` produces `axis_delta = -2.0`. Therefore sufficiently weak Loose/Stable Mount states can reach the escape threshold and exit to:

```text
Open Guard
```

At Strong or Locked, the positional modifier lowers `Strong Success → Success`; those visible bands are too far from the `+0.10` threshold for that one-point movement to break Mount. That is expected.

The checker must assert that **Half Guard and Open Guard are each reachable in at least one legal Mount v0 state**.

---

# 17. Grade Enum

The canonical machine enum remains:

```text
STRONG_FAILURE = -2
FAILURE        = -1
CONTESTED      =  0
SUCCESS        = +1
STRONG_SUCCESS = +2
```

Display strings:

```text
Strong Failure
Failure
Contested
Success
Strong Success
```

All lookup grades are always written from the initiator's perspective.

---

# 18. Behavior Names

These remain tactical behaviors rather than techniques.

## Top

```text
PRESSURE
HOLD
```

Player-facing names:

```text
PRESSURE → Apply Pressure
HOLD     → Hold Position
```

## Bottom

```text
ESCAPE
PROTECT
```

Player-facing names:

```text
ESCAPE  → Work to Escape
PROTECT → Protect / Survive
```

Do not rename these into techniques.
They describe what a grappler is broadly trying to do between decision windows.

---

# 19. Behavior Modifier Naming

The rules remain unchanged.

When Top uses:

```text
HOLD
```

and responds to:

```text
Bridge
Trap-and-Roll Escape
```

Bottom's resulting grade shifts down one grade.

When Bottom uses:

```text
PROTECT
```

and responds to:

```text
Americana Arm Isolation
```

Top's resulting grade shifts down one grade.

Logs should use canonical names and examples that actually exist in the raw table:

```text
Behavior Modifier:
Top HOLD defending Trap-and-Roll Escape
Raw grade: Strong Success
After HOLD: Success
```

and:

```text
Behavior Modifier:
Bottom PROTECT defending Americana Arm Isolation
Raw grade: Strong Success
After PROTECT: Success
```

---

# 20. Exit-Capability Metadata

Each bottom action must carry explicit metadata.

```text
Bridge
escape_capable = false
exit_map = none
special_rule = bridge_clamp
```

```text
Elbow-Knee Escape
escape_capable = true

SUCCESS
→ HALF_GUARD

STRONG_SUCCESS
→ OPEN_GUARD
```

```text
Trap-and-Roll Escape
escape_capable = true

SUCCESS
→ REVERSAL

STRONG_SUCCESS
→ REVERSAL
```

Do not infer exit capability by inspecting the action's name.

Store it explicitly.

---

# 21. Recommended Action Data Shape

Implementation should keep technique identity separate from resolution data.

Conceptually:

```text
ActionDefinition {
    id
    side
    canonical_name
    short_name
    legacy_name
    aliases
    category
    description
    escape_capable
    exit_map
    v0_notes
}
```

Example:

```text
id:
mount.bottom.elbow_knee_escape

side:
BOTTOM

canonical_name:
Elbow-Knee Escape

short_name:
Elbow-Knee Escape

legacy_name:
Elbow Escape

aliases:
Elbow Escape
Knee-Elbow Escape
Shrimp Escape
Mount Shrimp Escape

category:
ESCAPE

escape_capable:
true

exit_map:
SUCCESS        → HALF_GUARD
STRONG_SUCCESS → OPEN_GUARD
```

The 18-result matrix should reference only stable IDs.

Never use display strings as lookup keys.

Bad:

```text
lookup["Elbow-Knee Escape"]["Wide Mount Base"]
```

Correct:

```text
lookup[
    mount.bottom.elbow_knee_escape
][
    mount.top_response.wide_mount_base
]
```

This allows names to evolve later without changing engine behavior.

---

# 22. Alias Rules

Aliases exist for:

```text
CLI convenience
search
glossary
future educational UI
migration from v9 terminology
```

Aliases must never determine mechanics.

At startup/test time, validate that no alias resolves to two different Mount v0 entities.

Canonical names must not contain `+` or `&`; use the word `and` instead.

Input normalization should:

```text
1. Unicode-normalize the input.
2. Lowercase it.
3. Convert `+` and `&` tokens to the word `and` for backward/input convenience.
4. Treat hyphens and underscores as spaces.
5. Collapse repeated whitespace.
6. Trim leading/trailing whitespace.
```

Thus these can resolve identically:

```text
trap-and-roll
Trap And Roll
trap_and_roll
TRAP-AND-ROLL
```

But the engine should always convert the input immediately into the stable ID.

---

# 23. Special Alias Rule for Upa

`UPA` is potentially ambiguous in BJJ conversation because people may use it for bridging generally or for the complete bridge-and-roll escape.

Mount v0 resolves that ambiguity deliberately.

```text
upa
upa escape
bridge and roll
bridge-and-roll
```

resolve to:

```text
mount.bottom.trap_and_roll_escape
```

They do **not** resolve to:

```text
mount.bottom.bridge
```

The standalone Bridge action remains:

```text
bridge
hip bridge
bridging
```

This prevents one word from selecting two mechanically different actions.

---

# 24. CLI Presentation

Interactive hot-seat menus should display canonical names.

Example:

```text
BOTTOM INITIATES

1. Bridge
2. Elbow-Knee Escape
3. Trap-and-Roll Escape
```

Then:

```text
TOP RESPONSE

1. Hand Post and Base
2. Wide Mount Base
3. Hip Follow and Knee Re-Pummel
```

For compact output, short names may be used after the first full display.

Example:

```text
Bottom: Elbow-Knee Escape
Top: Hip Follow
```

Internally this must still resolve to:

```text
mount.bottom.elbow_knee_escape
mount.top_response.hip_follow_repummel
```

---

# 25. Decision Log Format

Every decision log should show both the human-readable term and the stable machine identity.

Example:

```text
DECISION

Clock:
4:35

Axis Before:
+1.50

Visible Band Before:
Stable

Initiator:
Bottom

Initiated Action:
Elbow-Knee Escape
[mount.bottom.elbow_knee_escape]

Response:
Hip Follow and Knee Re-Pummel
[mount.top_response.hip_follow_repummel]

Raw Grade:
Strong Failure (-2)

Behavior Modifier:
None

Positional Modifier:
None

Final Grade:
Strong Failure (-2)

Axis Delta:
+2.00

Proposed Axis:
+3.50

Escape Capable:
Yes

Escape Threshold Reached:
No

Axis After:
+3.50

Visible Band After:
Locked

Exit Destination:
None
```

This makes logs readable to both a BJJ practitioner and the programmer debugging the engine.

---

# 26. Bridge Log Example

```text
Initiated Action:
Bridge
[mount.bottom.bridge]

Response:
Hip Follow and Knee Re-Pummel
[mount.top_response.hip_follow_repummel]

Final Grade:
Success (+1)

Bottom-Initiated Axis Delta:
-1.00

Axis Before:
+0.50

Proposed Axis:
-0.50

Escape Capable:
No

Bridge Special Rule:
Triggered

Stored Axis:
+0.10

Position:
Mount

Exit Destination:
None
```

The log should explicitly say why a successful Bridge did not escape.

Never leave the tester to infer this from the number.

---

# 27. Elbow-Knee Escape Exit Log

Example Half Guard branch:

```text
Action:
Elbow-Knee Escape

Final Grade:
Success

Escape Threshold:
Reached

Exit:
Half Guard

Reason:
Elbow-Knee Escape reached escape threshold with final grade Success.
```

Example Open Guard branch:

```text
Action:
Elbow-Knee Escape

Final Grade:
Strong Success

Escape Threshold:
Reached

Exit:
Open Guard

Reason:
Elbow-Knee Escape reached escape threshold with final grade Strong Success.
```

Never write:

```text
Open Guard because axis overshot by 1.3
```

Overshoot does not choose the branch.

---

# 28. Trap-and-Roll Exit Log

```text
Action:
Trap-and-Roll Escape

Final Grade:
Strong Success

Escape Threshold:
Reached

Exit:
Reversal

Reason:
Trap-and-Roll Escape reached escape threshold with a successful final grade.
```

Do not automatically report:

```text
Closed Guard
```

unless a later positional model explicitly establishes that destination.

---

# 29. Exhaustive Checker Naming

`--enumerate` should use canonical names.

Example:

```text
TOP INITIATED

High Mount Climb
vs Forearm Frame
→ Success

High Mount Climb
vs Turn-In Recovery
→ Contested

High Mount Climb
vs Tight-Elbow Arm Defense
→ Failure
```

The stable IDs should optionally appear in verbose/debug mode.

The checker should understand aliases only as user input.

Its stored and reported matrix identity should use stable IDs plus canonical names.

---

# 30. Checker Semantic Tests

In addition to the existing v9 balance checks, implementation should assert the naming invariants in code.

```text
12 canonical Mount v0 entities exist.

6 are initiated actions.
6 are responses.

3 actions belong to Top.
3 actions belong to Bottom.

3 responses belong to Top.
3 responses belong to Bottom.

Exactly 18 raw lookup entries exist.

Every lookup entry references valid stable IDs.

No action/response pair is duplicated.

No required pair is missing.

Every stable ID is unique.

Every canonical name is unique within its relevant selection menu.

Every alias resolves unambiguously.

"upa" resolves only to Trap-and-Roll Escape.

"S-Mount" does not resolve to High Mount Climb.

"Elbow-Knee Connection" does not resolve to Tight-Elbow Arm Defense.

Bridge is not escape-capable.

Elbow-Knee Escape is escape-capable.

Trap-and-Roll Escape is escape-capable.

Americana Arm Isolation has no submission finish in v0.

Bare "High Mount" does not resolve to High Mount Climb.
"High Mount" is reserved for a future position ID.

No canonical name contains `+` or `&`.

"Hip Frame" does not resolve to Forearm Frame.
"Body Frame" does not resolve to Forearm Frame.

Elbow-Knee Escape can reach Half Guard in at least one legal state.
Elbow-Knee Escape can reach Open Guard in at least one legal state.
```

## Perfect-Response Diagnostic

Mount v0 deliberately keeps the v9 full-information established-position flow:

```text
Initiator commits action
→ responder sees the action
→ responder chooses response
→ deterministic resolution
```

The corrected table still has at least one `Failure` or `Strong Failure` counter to every initiated action. Therefore a responder who always chooses the best available counter can prevent every initiation from succeeding. This is a **known Mount v0 scaffolding limitation**, not something to hide.

Do **not** add `--blind` to the core Mount v0 flow. Blind commitment would test the simultaneous-choice model reserved for neutral/scramble states rather than the established-position initiator/responder system.

`--enumerate` must print a best-counter analysis for every initiated action:

```text
Action
Best responder choice
Raw grade against best response
Final grade by visible band
Can action succeed against unrestricted perfect response?
```

It must also print an aggregate diagnostic:

```text
PERFECT-RESPONSE LOCK: PRESENT

Meaning:
Every initiated action has at least one response that holds it to Failure or worse.

Classification:
KNOWN V0 SCAFFOLDING LIMITATION

Expected future resolution:
v0.2 setup/Ready/initiative legality can restrict which responses are available or tactically valid.
```

Do not distort otherwise believable BJJ matchup grades merely to force successful actions through a fully informed, unrestricted defender in v0.

---

# 31. Hysteresis and Naming

Visible bands continue to use:

```text
Loose
Stable
Strong
Locked
```

Recommended full player-facing forms:

```text
Loose Mount
Stable Mount
Strong Mount
Locked Mount
```

The machine enum may remain:

```text
LOOSE
STABLE
STRONG
LOCKED
```

Do not replace these with technique names.

They describe the **quality of Mount control**.

Example:

```text
Position:
Mount

Control:
Strong Mount

Top action:
Americana Arm Isolation

Bottom response:
Tight-Elbow Arm Defense
```

---

# 32. Multi-Band Hysteresis Implementation Clarification

A single action may cross multiple band thresholds.

Therefore visible-band updates must continue applying threshold transitions until no additional transition is legal.

Conceptually:

```text
repeat:
    evaluate transition from current visible band
    if transition occurs:
        set new visible band
        continue
    else:
        stop
```

Example:

```text
Visible Band:
Stable

Axis:
+1.50

Action moves axis to:
+3.50
```

The implementation must permit:

```text
Stable
→ Strong
→ Locked
```

in the same resolution.

Likewise a sufficiently large loss of control may produce:

```text
Locked
→ Strong
→ Stable
```

in the same resolution.

Each crossed boundary should be visible in debug logging.

---

# 33. Drift Clamp Clarification

Every drift tick uses the Mount v0 legal stored range:

```text
+0.10 through +4.00
```

Therefore after applying one drift tick:

```text
axis = clamp(axis + drift, +0.10, +4.00)
```

Drift can neither break Mount nor exceed Locked Mount.

---

# 34. Partial Final Decision Interval

If the remaining clock is shorter than `--interval`, simulate only the remaining time.

Example:

```text
Clock:
0:04

Interval:
7 seconds
```

Actual drift summary:

```text
Clock:
0:04 → 0:00

Duration:
4 simulated seconds
```

Never print:

```text
7-second interval
```

when only four simulated seconds occurred.

The summary must report actual start/end clock values.

---

# 35. Mount Duration and Elapsed Simulated Time

Keep both summary fields.

In Mount v0 they normally contain the same duration because the prototype begins in Mount and terminates when Mount breaks or the clock expires.

Keep both because later simulation versions can separate:

```text
Elapsed simulated match time
```

from:

```text
time spent specifically in Mount
```

No need to change the reporting schema later.

---

# 36. BJJ Vocabulary Boundary

Mount v0 distinguishes three different kinds of names.

| Type | Examples |
|---|---|
| Recognized technique/position terminology | High Mount, Americana, Elbow-Knee Escape, Trap-and-Roll |
| Recognized mechanics/concepts | Bridge, Crossface, Frame, Post, Base |
| Precise descriptive engine reactions | Hip Follow and Knee Re-Pummel, Turn-In Recovery, Tight-Elbow Arm Defense |

All three are acceptable.

What is not acceptable is inventing a named-looking technique where BJJ does not have one standardized name.

The game should teach useful grappling vocabulary without pretending the sport is more terminologically standardized than it actually is.

---

# 37. Future-Proofing Rules

The following distinctions are reserved now so later expansions do not require renaming Mount v0:

```text
High Mount
≠ S-Mount

Bridge
≠ Trap-and-Roll Escape

Arm Isolation
≠ Americana Finish

Wide Mount Base
≠ Grapevine Mount

Tight-Elbow Arm Defense
≠ full Elbow-Knee Connection system

Crossface Pressure
≠ Arm-Triangle attack

Reversal
≠ automatically Closed Guard
```

These distinctions should be tested wherever practical.

---

# 38. Final Canonical Matrix

The complete Mount v0 player vocabulary is now:

```text
TOP ACTIONS

High Mount Climb
Crossface Pressure
Americana Arm Isolation

BOTTOM ACTIONS

Bridge
Elbow-Knee Escape
Trap-and-Roll Escape

TOP RESPONSES

Hand Post and Base
Wide Mount Base
Hip Follow and Knee Re-Pummel

BOTTOM RESPONSES

Forearm Frame
Turn-In Recovery
Tight-Elbow Arm Defense
```

The raw 18 grades are:

```text
TOP INITIATES

High Mount Climb
  vs Forearm Frame
  → Success

High Mount Climb
  vs Turn-In Recovery
  → Contested

High Mount Climb
  vs Tight-Elbow Arm Defense
  → Failure

Crossface Pressure
  vs Forearm Frame
  → Failure

Crossface Pressure
  vs Turn-In Recovery
  → Success

Crossface Pressure
  vs Tight-Elbow Arm Defense
  → Strong Success

Americana Arm Isolation
  vs Forearm Frame
  → Strong Success

Americana Arm Isolation
  vs Turn-In Recovery
  → Contested

Americana Arm Isolation
  vs Tight-Elbow Arm Defense
  → Strong Failure
```

```text
BOTTOM INITIATES

Bridge
  vs Hand Post and Base
  → Strong Failure

Bridge
  vs Wide Mount Base
  → Failure

Bridge
  vs Hip Follow and Knee Re-Pummel
  → Success

Elbow-Knee Escape
  vs Hand Post and Base
  → Strong Success

Elbow-Knee Escape
  vs Wide Mount Base
  → Success

Elbow-Knee Escape
  vs Hip Follow and Knee Re-Pummel
  → Strong Failure

Trap-and-Roll Escape
  vs Hand Post and Base
  → Strong Failure

Trap-and-Roll Escape
  vs Wide Mount Base
  → Failure

Trap-and-Roll Escape
  vs Hip Follow and Knee Re-Pummel
  → Strong Success
```

---

# 39. Implementation Freeze

For the first running Mount v0 prototype:

```text
DO use these canonical names.

DO use stable IDs for every lookup.

DO retain old v9 names only as legacy metadata.

DO preserve all existing v9 mechanics.

DO log canonical name + stable ID.

DO run --enumerate after implementation.

DO inspect all four visible bands.

DO assert both Elbow-Knee Exit Map branches are reachable.

DO print best-counter analysis for every initiated action.

DO report PERFECT-RESPONSE LOCK: PRESENT as a known v0 limitation.

DO NOT add blind commitment to the core Mount v0 flow.

DO reserve bare "High Mount" for the future position.

DO keep `+` and `&` out of canonical names.

DO allow prototype evidence to reveal further bad matchup grades.
```

The naming itself should **not** be revisited merely because another phrase sounds nicer.
Rename something only if implementation or BJJ review demonstrates that the term is actually misleading.

The next task remains:

```text
IMPLEMENT MOUNT v0.
```

Not:

```text
REVIEW MOUNT v0 AGAIN.
```