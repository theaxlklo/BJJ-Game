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
  ↓ builder attempt / forced defensive reaction
Partial
  ↓ builder attempt / forced defensive reaction
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
  ↓ forces a base/posture reaction even if locally countered
Trap-and-Roll setup:
None → Partial → Ready
```

Before Ready, Trap-and-Roll is not a legal v0.2 action.

At Ready, the legal response set is:

```text
Wide Mount Base
Hip Follow and Knee Re-Pummel
```

Ready uses a separate v0.2 stalemate rule:

```text
Trap-and-Roll × Wide Mount Base
→ Contested
```

This is not written into the frozen 18-entry matchup matrix. It is a Ready-only, post-behavior/post-positional override. Exhaustion still applies afterward, so an Exhausted initiator can have the Ready stalemate degraded to Failure.

The frozen raw Trap-and-Roll grades are unchanged.

This gives Bridge future value without buffing Bridge itself.

### Top

```text
High Mount Climb
  ↓ forces defensive structure even if locally countered
Americana Arm Isolation setup:
None → Partial → Ready
```

Before Ready, Americana Arm Isolation is not a legal v0.2 action.

At Ready, the legal response set is:

```text
Forearm Frame
Turn-In Recovery
```

Turn-In Recovery is the designated Ready stalemate response and resolves to Contested after behavior/positional modifiers. Tight-Elbow Arm Defense is no longer legal after the arm-isolation setup is Ready.

The frozen raw Americana grades are unchanged.

## Ready-defense invariant

v0.2a now applies one general rule to every setup-dependent Ready action:

> **Ready turns the defender's perfect counter into a stalemate, not a loss.**

For every Ready setup rule:

- one legal response is designated as the stalemate response;
- that response resolves to post-positional `Contested`;
- at least one other legal response may still be worse for the defender;
- no fresh Ready state may have a best legal response below Contested;
- no fresh Ready state may make every legal response Success-or-better.

Current stalemate responses:

```text
Ready Trap-and-Roll   → Wide Mount Base
Ready Americana       → Turn-In Recovery
```

The override occurs before the external exhaustion modifier. Therefore an Exhausted initiator can still have a Ready stalemate shifted down to Failure.

## Modern-path boundary

The setup layer lives around `MountMatch`.

`MountResolutionEngine` is unchanged.

Frozen `MountMatch.decide()` is unchanged and does not enforce setup legality or mutate setup progress.

Only modern `attempt()` can:

- reject an unready setup-dependent action;
- reject a response that is illegal against a Ready setup;
- advance setup after a designated builder attempt;
- consume Ready after the target is used.

The builder's local grade and setup progress are separate signals. A defender may win the local exchange while still being forced into the reaction the setup chain is trying to provoke. This prevents a perfect responder from freezing setup at None forever.

Correct-response disruption/decay is still deferred; when that layer exists it may reduce or erase setup progress after specific answers instead of making all setup building impossible.

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
2. setup progress only when the Ready target would have positive tactical value
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
Ready states reached against best-counter play:
Top:    36 reachable / 36 best-counter Contested / 0 guaranteed-attacker
Bottom: 36 reachable / 36 best-counter Contested / 0 guaranteed-attacker

Gate 1 now passes because every reachable Ready state follows the Ready-defense invariant exactly.

Gate 4:
Bridge selections: 595 / 100 standard matches
Bridge setup-priority selections: 595
Bridge builds credited to completed chains: 590
Completed Bottom setup chains: 295

Gate 5:
Top follow-up meaningful initiations / match: 1.140
  position:               0.560
  completed setup builds: 0.580
threshold: > 1.000

Setup builders count only when their Ready target is later consumed in the same match.
```

These statuses are calculated, not manually declared.

## 25-stamina setup validation after Ready balancing

After the Ready stalemate invariant was implemented, the earlier v0.1 low-stamina comparisons were rerun with v0.2 setup enabled.

All runs used:

```text
1,000 matches
base seed 42
MEDIUM commitment
Top stamina 25
Bottom stamina 25
v0.2 setup/Ready enabled
```

Results:

| Condition | Half Guard | Reversal | Timeout | Mean Top stamina | Mean Bottom stamina |
|---|---:|---:|---:|---:|---:|
| HOLD vs ESCAPE — both fixed | 0.0% | 0.0% | 100.0% | 18.00 | 0.00 |
| HOLD vs ESCAPE — Bottom recovers only | 99.8% | 0.0% | 0.2% | 7.54 | 26.26 |
| HOLD vs ESCAPE — Top recovers only | 0.0% | 93.1% | 6.9% | 14.40 | 0.41 |
| PRESSURE vs ESCAPE — both fixed | 0.0% | 0.0% | 100.0% | 0.00 | 0.00 |
| PRESSURE vs ESCAPE — Top recovers only | 0.0% | 92.8% | 7.2% | 13.95 | 0.41 |
| PRESSURE vs PROTECT — Top recovers only | 0.0% | 0.6% | 99.4% | 30.99 | 23.19 |
| HOLD vs PROTECT — Bottom recovers only | 48.0% | 0.0% | 52.0% | 11.89 | 30.02 |
| PRESSURE vs PROTECT — Bottom recovers only | 0.0% | 0.0% | 100.0% | 0.00 | 29.26 |

Interpretation:

- Setup chains now create enough paid action volume that stamina is genuinely binding. Under fixed PRESSURE conditions, both competitors can end at zero stamina.
- An Exhausted Bottom still cannot escape in the fixed HOLD-vs-ESCAPE condition, but Bottom-only recovery changes that condition from 100% timeout to 99.8% Half Guard.
- Top-only recovery is strategically dangerous in ESCAPE conditions: switching to CONSERVE gives up the stronger Top defensive behavior and produces Reversal rates above 92%.
- Bottom recovery does not overcome PRESSURE-vs-PROTECT drift; recovering stamina is not itself an escape.
- Gate 3 remains OPEN because the responder-only fresh-vs-Exhausted exchange differential is still zero. These outcome changes come from initiator exhaustion and behavior switching, not from an Exhausted responder being mechanically weaker.
- Gate 6 remains OPEN because HOLD still has zero positive-weight Exhausted-Bottom escape routes without recovery.
- Gate 7 remains OPEN because commitment still changes cost only.

This confirms the v0.1 prediction that setup layers would create natural stamina pressure without retuning the 3/7/12 costs.

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

Gate 1 is now settled by the Ready-defense invariant.

The next experimental pass is the 25-stamina setup matrix, because setup chains now create enough action volume for exhaustion to become common. That evidence should be collected before changing responder stamina, exhausted escape reachability, or commitment.

The Locked/cap setup treadmill remains intentionally open and should be considered together with RESET/stalling, because both concern progress that can be accumulated cheaply while positional movement is absorbed.
