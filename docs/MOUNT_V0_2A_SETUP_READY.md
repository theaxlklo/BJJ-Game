# Mount v0.2a — Minimal Setup / Ready

## Status

Implemented as the first v0.2 slice.

This slice exists to pay down the v0/v0.1 debts that depend directly on setup and Ready state without changing the frozen Mount-v0 matchup grades.

The frozen v0 enumerate digest remains authoritative.

## Design source

The authoritative design remains:

`docs/BJJ_Game_Concept_Current_Recap_v9_CODE_READY_FREEZE.md`

Relevant v9 rules:

- some techniques require preparation;
- setup is represented by broad tiers;
- setup can build through successful actions;
- Ready can create a decision window;
- techniques must be legal from the current state;
- in established positions the initiator locks the action before the responder chooses;
- setup may later decay, be disrupted, or be affected by commitment/stamina, but those details were intentionally left tunable.

## v0.2a setup tiers

The first implementation uses the smallest discrete model:

```text
None
  ↓ successful builder
Partial
  ↓ successful builder
Ready
```

A Ready target is consumed when that target action is used:

```text
Ready
  ↓ target action attempted
None
```

There is no continuous percentage in v0.2a.

There is no decay or hysteresis in v0.2a because the exact persistence rules remain unfrozen in v9.

## Two initial setup chains

### Bottom

```text
Bridge
  ↓ successful local result
Trap-and-Roll setup:
None → Partial → Ready
```

Before Ready, Trap-and-Roll is not a legal v0.2 action.

At Ready, the legal response set is narrowed to:

```text
Hip Follow and Knee Re-Pummel
```

The frozen raw Trap-and-Roll grades are unchanged.

This gives Bridge future value without buffing Bridge itself.

### Top

```text
High Mount Climb
  ↓ successful local result
Americana Arm Isolation setup:
None → Partial → Ready
```

Before Ready, Americana Arm Isolation is not a legal v0.2 action.

At Ready, the legal response set is:

```text
Forearm Frame
Turn-In Recovery
```

Tight-Elbow Arm Defense is no longer legal after the arm-isolation setup is Ready.

The frozen raw Americana grades are unchanged.

## Modern-path boundary

The setup layer lives around `MountMatch`.

`MountResolutionEngine` is unchanged.

Frozen `MountMatch.decide()` is unchanged and does not enforce setup legality or mutate setup progress.

Only modern `attempt()` can:

- reject an unready setup-dependent action;
- reject a response that is illegal against a Ready setup;
- advance setup after a successful builder;
- consume Ready after the target is used.

This preserves the legacy `mount_v0` path.

## Established-position ordering

The setup-enabled batch harness restores the v9 established-position ordering:

```text
initiator chooses / locks action
↓
legal responses are derived from current Ready state
↓
seeded responder chooses among those legal responses
↓
resolution
```

The historical v0.1 blind batch remains unchanged when v0.2 setup is disabled.

## Scripted batch policy

The setup-enabled batch policy is lexicographic:

```text
1. immediate escape if available
2. setup progress with positive advance probability
3. positive raw + realized positional gain
4. RESET
```

The setup step applies only while the target is not Ready.

This is why Bridge can now be selected for setup value without preferring setup over an immediately available escape.

## Reproducing v0.2a batch behavior

Use:

```bash
PYTHONPATH=src python -m bjj_game \
  --batch 100 \
  --seed 42 \
  --v02-setup \
  --top-behavior PRESSURE \
  --bottom-behavior ESCAPE
```

`--v02-setup` is batch-only in v0.2a.

Interactive Ready-aware action and response menus are deferred until the next interface slice.

## Definition-of-done movement

The measured checker currently reports:

```text
Gate 1  Perfect-response lock          PASS
Gate 2  RESET/stalling                 OPEN
Gate 3  Responder stamina              OPEN
Gate 4  Bridge setup role              PASS
Gate 5  Top post-opening activity      PASS
Gate 6  Exhausted Bottom escape        OPEN
Gate 7  Commitment meaning             OPEN
```

Current evidence:

```text
Gate 1:
Ready lock-free states
Top: 18
Bottom: 36

Gate 4:
Bridge selections: 40 / 100 standard matches
Bridge setup-priority selections: 40

Gate 5:
Top follow-up meaningful initiations / match: 2.550
  position: 0.000
  setup:    2.550
threshold: > 1.000
```

These statuses are calculated, not manually declared.

## Intentionally deferred from v0.2a

The following are not implemented in this slice:

- setup decay;
- setup hysteresis;
- correct-response setup disruption;
- simultaneous Ready events;
- Recognition;
- feints;
- commitment changing setup speed;
- exhaustion changing setup speed;
- responder stamina effects;
- RESET consuming or decaying setup;
- progress-based stalling;
- STABILIZE;
- submission finishes.

Those remain future v0.2/v0.3 work and must be added only when their corresponding gate/design question is addressed.

## Next slice

The most connected remaining debt is RESET / stalling.

Now that setup progress exists, the next design question can be measured directly:

> What setup/progress cost should repeated RESET impose without removing legitimate passing/resetting from BJJ?

Gate 2 remains OPEN until that rule is defined and the standardized RESET-lock probe no longer guarantees a Locked timeout.
