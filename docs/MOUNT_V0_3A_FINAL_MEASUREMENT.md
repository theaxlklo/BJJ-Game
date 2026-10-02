# v0.3a Final Measurement — Ready Response Projection

> **Superseded by PR-review Option A.** This file preserves the pre-stalemate measurement in which every non-success broke the submission track. The current amended result is in `docs/MOUNT_V0_3A_OPTION_A_MEASUREMENT.md`: Gate B reopened at 98/100 while Gates A/C/D/E pass. Do not treat the 39/100 result below as current.

## Final reviewed candidate

```text
276e0b649cd0d7fbd2eb82a637d55e3674eb8b67
```

GitHub Actions pull-request run:

```text
#404
```

Verification on both Python 3.11 and Python 3.13:

```text
205 tests PASS
modern semantic checker PASS
legacy checker PASS
```

Frozen enumerate digest:

```text
expected=3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
actual=3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

The frozen 18-entry Mount-v0 matrix remains unchanged.

## Final v0.3a gates

```text
Gate A PASS
Locked submission-progress probability=0.571
policy_selected=True

Gate B PASS
Tap=39/100 (39.0%)
Threat=99
Control=92
Finish=61
submission-stage attempts=858

Gate C PASS
Threat: 12 reachable / 12 best-defense-stops / 0 guaranteed
Control: 12 reachable / 12 best-defense-stops / 0 guaranteed
Finish: 12 reachable / 12 best-defense-stops / 0 guaranteed

Gate D PASS
attacker-only exhaustion changes=15
defender-only exhaustion changes=21
both-Exhausted cancellation mismatches=0/108
```

No v0.3a gate or threshold was moved after seeing results.

## Planned v0.2 transition

The v0.2 gate surface on the v0.3a branch is:

```text
Gate 1 PASS
Gate 2 OPEN
Gate 3 PASS
Gate 4 PASS
Gate 5 PASS
Gate 6 ACCEPTED
Gate 7 OPEN
```

Gate 2's DEFERRED -> OPEN change is intentional: a real `SUBMISSION_FINISH` surface now exists while the repeated-RESET Locked probe still times out. Stalling remains the separate v0.3b slice.

Gate 5 remains observational. Its unchanged threshold is 1.000; v0.3a raises measured meaningful Top follow-up work above that threshold without tuning submission rules to target Gate 5.

## Why Gate B changed from 55% to 39%

The final correction did not weaken the Americana grade table, change response weights, or tie the submission to Mount dominance.

Instead it fixed contextual response-policy projection.

Ordinary Bottom response mass remains:

```text
Forearm Frame = 4
Tight Elbows = 3
Turn-In Recovery = 0
```

Ready Americana makes Tight Elbows illegal and designates Turn-In Recovery as the legal fresh stalemate defense.

The previous filtering behavior discarded Tight Elbows' 3 weight points, producing:

```text
Frame = 4
Turn-In = 0

effective policy: 100% Frame
```

The corrected projection preserves the original total response mass:

```text
Frame = 4
Turn-In = 3
```

A fresh Ready-Americana entry therefore has exact submission-entry probability:

```text
4/7 = 0.571
```

instead of the accidental 1.000.

The same projection mechanism is generic to context-specific legality. It does not hardcode Americana or Mount.

## Behavior evidence after projection

Matched 100-seed Top-PRESSURE batches:

```text
Bottom ESCAPE:
  taps=39
  escapes=1
  timeouts=60
  setup-builds=1506
  submission-attempts=858

Bottom PROTECT:
  taps=31
  escapes=0
  timeouts=69
  setup-builds=1511
  submission-attempts=791

Bottom CONSERVE:
  taps=42
  escapes=34
  timeouts=24
  setup-builds=1045
  submission-attempts=780
```

PROTECT now has the expected direction relative to ESCAPE: fewer Tap outcomes.

## Exhaustion / recovery prediction

```text
fresh-fixed:
  taps=39
  escapes=1
  timeouts=60
  submission-attempts=858

exhausted-fixed:
  taps=45
  escapes=0
  timeouts=55
  submission-attempts=856

exhausted-recover:
  taps=43
  escapes=0
  timeouts=57
  submission-attempts=762
```

This matches the pre-implementation directional prediction:

- exhausted Bottom is more vulnerable;
- recovery reduces that vulnerability and reduces submission-attempt volume.

The probe remains observational and is not a gate.

## Reacquisition remains an observation, not a v0.3a tuning target

High Mount Climb setup-advance probability remains 1.000 through ordinary Stable/Strong/Locked states under the existing v0.2 setup rule.

That is intentionally **not** changed in v0.3a because the frozen v0.2 Gate-1 invariant requires Ready to remain reachable after two builder attempts against best-counter play. Tightening generic setup advancement here would reopen an already-reviewed v0.2 design decision.

The high reacquisition rate is therefore retained as evidence for later setup/submission-access refinement rather than tuned merely to lower Tap rate.

## v0.2 batch-count side effects

Ready-response projection is generic, so it also changes some setup-enabled v0.2 batch counts even when v0.3 submissions are not enabled.

Before projection, reviewed v0.2b evidence included:

```text
Gate 4:
  Bridge selections=853/100
  completed-chain Bridge builds=491
  completed Bottom chains=152

Gate 6 dynamic exhausted-Bottom escapes/100:
  PRESSURE=0
  HOLD=76
  CONSERVE=35
```

With contextual Ready projection:

```text
Gate 4:
  Bridge selections=845/100
  completed-chain Bridge builds=502
  completed Bottom chains=153

Gate 6 dynamic exhausted-Bottom escapes/100:
  PRESSURE=0
  HOLD=91
  CONSERVE=48
```

Statuses remain:

```text
Gate 4 PASS
Gate 6 ACCEPTED
```

The static Gate-6 route counts remain:

```text
PRESSURE=1
HOLD=0
CONSERVE=1
```

This side effect is explicit because the projection corrects the seeded responder's behavior in Ready states generally, not just when a submission finish is enabled.

## Multi-position design direction

Americana is not a Mount-owned technique.

v0.3a models:

```text
Mount context -> Americana access -> Threat -> Control -> Finish -> Tap
```

only because Mount is the currently implemented position.

The intended future separation is:

```text
Mount ----------\
Side Control ----\
Knee-on-Belly ----> Americana access/control graph -> Threat -> Control -> Finish
Guard -----------/
```

Position-specific entry contexts can define:

- how Americana access is earned;
- which defenses are legal at that context;
- which legal defense receives redirected response mass when another ordinary response becomes unavailable.

The Americana submission-control graph itself should remain reusable across positions.

## v0.3a closure

The v0.3a experiment now satisfies all four gates without:

- changing the frozen matchup table;
- moving Gate-B's range;
- moving Gate-5's threshold;
- tuning stamina;
- tuning commitment;
- adding another submission;
- declaring Americana Mount-exclusive.

The next planned mechanic slice remains v0.3b stalling / progress enforcement.

No merge is implied by this measurement; PR review remains required.
