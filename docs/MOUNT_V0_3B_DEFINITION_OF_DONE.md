# Mount v0.3b — Stalling / Progress Definition of Done

## Status

FROZEN BEFORE IMPLEMENTATION.

v0.3b starts from reviewed main:

```text
4e43a663c3741013c1ca9258437835724ca43807
```

The frozen Mount-v0 enumerate digest remains authoritative:

```text
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

v0.3a is the clean baseline:

```text
v0.2 Gate 2 OPEN
v0.3a Gate A PASS
v0.3a Gate B DEFERRED
v0.3a Gate C PASS
v0.3a Gate D PASS
v0.3a Gate E PASS
```

v0.3b answers one narrow question:

> Once a fighter has a legitimate legal route to work, how does the match distinguish active engagement from choosing to stall?

The rule must not punish a player merely because competent defense prevents successful advancement.

## Core definition — progress means a legal attempt, not successful advancement

A fighter is **engaged** when they take a legal attempt through a progress-capable route.

The result of that attempt does not need to advance the state.

A defender who successfully stops the attempt does not retroactively turn the initiator into a staller.

Examples:

```text
Threat + Top attacks Americana + informed Turn-In -> Contested hold
Top is ENGAGED.

Ready Americana + Top attacks isolation + Turn-In -> Contested
Top is ENGAGED.

Bottom attempts a legal escape and Top stops it
Bottom is ENGAGED.
```

This is the same principle that prevented Gate 2 from penalizing Locked Top before submissions existed: a player is not blamed for failure when the rules do not give them a viable route, and is not blamed for a competent opponent stopping a route they actually attempted.

## Progress-capable route

A legal non-RESET action is progress-capable when, from the state **before the responder chooses and before resolution**, it has at least one real channel to improve the initiator's state through the existing mechanics.

Recognized channels are:

```text
escape:
  terminal escape probability / escape-capable route

submission:
  enter or advance the submission-control track

setup:
  advance a legal setup target toward Ready

position:
  favorable realized positional movement that is not wholly absorbed by a cap
```

The categories follow the existing batch policy order:

```text
escape
-> submission progress
-> setup progress
-> positional progress
-> RESET
```

No axis conversion weight is invented.

### Attempt semantics

Once an action is progress-capable before response selection, **attempting it counts as engagement regardless of the actual response or final grade**.

Therefore:

- informed Turn-In holding Threat at Contested does not make Top a staller;
- a defended legal escape attempt does not make Bottom a staller;
- a legal setup attempt that the opponent stops still counts as engagement if the route was progress-capable when initiated.

### Non-progress actions

A legal action that has no current progress channel does not become engagement merely because it is non-RESET.

This prevents a fighter from avoiding the stalling rule by repeatedly selecting an action whose positional gain is completely absorbed by a cap and which has no escape, submission, or setup purpose.

## RESET semantics

RESET remains legal.

RESET is **not automatically stalling**.

On a fighter's initiation opportunity:

```text
no progress-capable route exists
-> RESET is legitimate
-> no stalling debt

at least one progress-capable route exists
+ fighter chooses RESET instead
-> stalling opportunity
-> contributes to that fighter's stalling clock/debt
```

This preserves legitimate recovery/yielding when the game offers no meaningful work.

## Defensive engagement

A fighter who is actively responding to the opponent's progress attempt is defending, not stalling.

A legal response to an opponent's progress-capable initiation counts as **defensive engagement** for the responder's stalling state.

In particular:

```text
Top attacks held Americana
Bottom chooses informed Turn-In
-> Top engaged by attacking
-> Bottom engaged by defending
-> neither receives a stalling penalty
```

A Bottom player who repeatedly RESETs their own initiation opportunities while not under an active opponent progress attempt is still subject to the same stalling rule as Top.

The system is symmetric.

## Frozen penalty direction

When a stalling penalty is triggered, Mount control moves **one nominal step toward the non-stalling player**.

Examples:

```text
Top stalls
-> axis moves one step toward Bottom

Bottom stalls
-> axis moves one step toward Top
```

The penalty may not itself cross Neutral or manufacture a positional escape/reversal.

The inherited boundary ladder is:

```text
Locked -> Strong -> Stable -> Loose -> STOP
```

For the v0.3b Locked case:

```text
Locked Top stalls
-> Top loses the Locked band
-> resulting Mount control is Strong
```

At the Neutral-side boundary, the penalty stops rather than crossing Neutral.

v0.3b must not create a new escape solely from a stalling penalty.

## Trigger cadence — deliberately not invented here

The **penalty effect** is frozen.

The exact time / consecutive-opportunity threshold that turns stalling opportunities into a penalty was not previously frozen.

Therefore this DoD does **not** invent:

- N consecutive RESETs;
- an arbitrary number of seconds;
- a post-hoc cadence chosen merely to make Gate 2 pass.

Before the penalty mechanic is implemented, its trigger cadence must be committed as a separate pre-implementation amendment.

The gates below define what that eventual trigger must accomplish without preselecting an unsupported threshold.

## Gate A — Gate 2 no longer locks at Locked

### Requirement

A one-sided Top-stalling probe must not end as:

```text
TIMEOUT — Mount retained at Locked
```

when Top repeatedly chooses RESET despite having a legal progress-capable route.

The probe must isolate Top's offense rather than let simultaneous Bottom stalling cancel the measurement.

### Probe shape

Top:

```text
PRESSURE
when initiation is available:
  if progress-capable route exists -> deliberately RESET
```

Bottom:

```text
ESCAPE
respond legally when attacked
on own initiation -> use the normal progress-aware policy rather than forced RESET
```

PASS requires:

- at least one Top stalling penalty is actually applied;
- Top cannot retain unchanged Locked control through the full clock solely by repeated RESET;
- the probe does not time out at Locked.

This is the executable closure condition for v0.2 Gate 2.

## Gate B — stalemated attacker is engaged, not punished

### Requirement

Create an active Americana stage under the fresh informed-defense stalemate:

```text
Top Fresh
Bottom Fresh
Top PRESSURE
Bottom ESCAPE
informed Turn-In
```

Top repeatedly attempts the legal Americana submission action.

Turn-In produces Contested and the stage holds.

PASS requires:

```text
Top stalling penalties = 0
```

even if:

```text
submission stage advances = 0
```

for the entire measured window.

This gate proves that "progress" means a legitimate attempt to advance, not successful advancement.

Bottom's informed Turn-In responses must also count as defensive engagement and must not create Bottom stalling penalties.

## Gate C — both sides can be penalized

### Requirement

The stalling system must not be Top-only.

Use two isolated one-sided probes.

Top-stall probe:

```text
Top has progress-capable route
Top repeatedly RESETs
Bottom remains engaged
-> Top penalty count > 0
```

Bottom-stall probe:

```text
Bottom has progress-capable route
Bottom repeatedly RESETs on its own initiation opportunities
Top remains engaged
-> Bottom penalty count > 0
```

PASS requires nonzero measured penalties for **both** sides.

The same trigger and penalty semantics must be used for both.

## Gate D — penalty cannot cross Neutral

### Requirement

A stalling penalty may improve the non-stalling player's control but may not itself create an escape/reversal by crossing Neutral.

Probe Top stalling from the lowest persisted Mount-control state where a penalty would otherwise overshoot.

PASS requires:

- persisted Mount axis remains on the Mount side of Neutral;
- no terminal exit is created by the penalty alone;
- no raw matchup grade or escape threshold is invoked to manufacture an exit.

This is a safety/invariant gate, not a pacing target.

## Gate E — Gate B deferral must remain deferred

v0.3b is a stalling/progress slice.

It must **not** add response commitment or Recognition/information as a side effect.

The existing automatic Gate-B expiry flags must remain:

```text
response_commitment_present=False
recognition_present=False
```

PASS requires v0.3a Gate B to remain:

```text
DEFERRED
```

throughout v0.3b.

If v0.3b accidentally makes either expiry flag true, this gate fails even if the stalling mechanics otherwise work.

## Observability requirements

The modern history/checker must expose enough information to audit stalling decisions.

At minimum record per side:

- progress-capable initiation opportunities;
- engaged progress attempts;
- defensive-engagement events;
- RESETs taken while a progress route existed;
- current stalling debt / clock state;
- stalling warnings if the frozen trigger uses them;
- stalling penalties applied;
- axis before / after each penalty;
- whether a Neutral-boundary clamp prevented further movement.

The checker must distinguish:

```text
no progress route + RESET
from
progress route exists + RESET
```

They are not the same event.

## Existing RESET probe

The historical probe:

```text
Top PRESSURE+RESET vs Bottom ESCAPE+RESET
```

remains useful as a legacy observation, but it is not sufficient by itself to assign stalling ownership because both competitors deliberately RESET.

v0.3b Gate A uses a one-sided Top-stall probe so the measured penalty cannot be canceled or obscured by simultaneous Bottom stalling.

A separate Bottom-stall probe supplies the symmetry evidence.

## Predictions recorded before implementation

These are observations to measure, not pass thresholds.

### Prediction 1 — Top RESET count falls

Once RESET while a progress route exists carries stalling debt, the progress-aware Top policy should choose RESET less often.

Record before/after RESET counts.

Do not tune the trigger merely to maximize this reduction.

### Prediction 2 — random-response Tap rate changes little

Against the random response mix, Top already attacks frequently.

The v0.3a random PRESSURE / ESCAPE Tap result should therefore move little compared with baseline.

This is directional only; no numeric "little" threshold is frozen.

### Prediction 3 — informed-defender Tap result remains zero

v0.3b does not solve the Gate-B fatigue cancellation:

```text
Exhausted initiator -1
+
Exhausted responder +1
=
0
```

The informed PRESSURE / ESCAPE full-match result is therefore predicted to remain:

```text
Tap=0/100
```

The stalling rule must not be tuned to manufacture submission finishes.

### Prediction 4 — Locked becomes harder to retain by resting

A Top player at Locked who has a legitimate submission/setup route but repeatedly chooses RESET should lose Locked control through the stalling penalty.

That is an intended consequence, not a regression.

## Non-goals

v0.3b does not:

- add response commitment;
- add Recognition/information;
- change the provisional LOW=3 submission-hold cost;
- change submission-stage grades;
- change response weights;
- change commitment costs;
- change exhaustion thresholds;
- change the generic -1/+1 mutual-exhaustion cancellation;
- tune Gate B;
- fix the setup-policy debt where setup progress can outrank axis loss;
- add new submissions;
- retune the frozen 18-entry matchup table.

## Verification discipline

Every v0.3b change must preserve:

```text
python -m unittest discover -s tests -v
python -m bjj_game --check
python -m mount_v0 --check
frozen --enumerate SHA-256
```

The frozen digest must remain:

```text
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

The v0.3a baseline gates must remain:

```text
A PASS
B DEFERRED
C PASS
D PASS
E PASS
```

except that v0.2 Gate 2 is expected to move:

```text
OPEN -> PASS
```

only when executable one-sided stalling evidence proves the Locked RESET lock is gone.

## Change-control rule

Before coding the actual stalling penalty trigger:

1. freeze its cadence/threshold in a separate design amendment;
2. do not pick the cadence by running batches until Gate 2 passes;
3. let the gates recompute from executable evidence;
4. preserve the informed submission and Gate-B deferral surfaces.

If a gate cannot pass, record the failed measurement before changing mechanics or criteria.
