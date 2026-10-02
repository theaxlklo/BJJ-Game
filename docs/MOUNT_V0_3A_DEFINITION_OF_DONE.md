# Mount v0.3a — Americana Submission Track Definition of Done

## Status

FROZEN BEFORE IMPLEMENTATION.

This slice starts from reviewed main:

```text
e33efff160aff5aab7ffed33dc14ae7231b4cc07
```

The frozen Mount-v0 enumerate digest remains authoritative:

```text
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

v0.3a exists to test one narrow question:

> Once Top has earned a Ready Americana from dominant Mount, can submission progress give Strong/Locked Mount a real terminal purpose without creating an automatic win or another cap treadmill?

This slice does **not** solve stalling. The stalling/progress rule is a separate v0.3b slice after a legitimate submission route exists.

## Expected v0.2 Gate-2 transition

The current v0.2 Gate 2 is DEFERRED only while no real `SUBMISSION_FINISH` action exists.

Therefore the first real v0.3a submission-finish surface is expected to change:

```text
Gate 2: DEFERRED -> OPEN
```

if the existing repeated-RESET Locked timeout still exists.

That transition is correct and planned. v0.3a must not weaken the Gate-2 checker merely to preserve DEFERRED.

v0.3b will address a competitor who chooses to stall after a legitimate progress route exists.

## v0.3a scope

Exactly one submission chain is added:

```text
Ready Americana
    -> Threat
    -> Control
    -> Finish
    -> Tap
```

The existing High Mount -> Americana Ready setup remains the only entry route.

A Ready Americana can enter the submission track only when:

- Top is the initiator;
- the current Mount band is Strong or Locked; and
- the Ready Americana resolves at Success or Strong Success after ordinary behavior, Ready, and exhaustion modifiers.

Entering the track consumes the existing Ready Americana setup.

Threat, Control, and Finish are explicit submission stages. A successful stage attempt advances exactly one stage. A successful attempt from Finish produces Tap and ends the match.

v0.3a deliberately excludes:

- refuse-tap;
- injury/damage modeling;
- multiple submissions;
- branching submission chains;
- submission-to-submission transitions;
- new submission-specific responses;
- commitment tuning;
- direct response stamina cost;
- stalling penalties.

Existing stamina costs and v0.2b exhaustion modifiers apply to submission attempts.

## Submission-defense rule

A submission stage advances only on final grade Success or Strong Success.

A defended stage is any legal submission-stage exchange whose final grade is Contested or worse.

Every defended stage moves Mount control **one nominal band step toward the defender**:

```text
Top submission defended -> axis -1.00
```

The result is clamped with the existing Mount axis bounds and the existing band-hysteresis update.

This is an explicit anti-treadmill rule. Submission progress is not allowed to repeatedly consume stamina at Locked while the +4.00 cap absorbs every downside.

A successful submission-stage exchange advances the submission track; it does not receive free positional-axis value merely for advancing the track.

## Batch-policy order

The scripted policy remains lexicographic and must not convert terminal progress into made-up axis points.

The v0.3a order is frozen as:

```text
1. escape probability
2. submission-progress probability
3. setup-progress probability
4. positive raw + realized positional movement
5. RESET
```

Submission progress is ranked separately for the same reason escape probability is ranked separately: it can lead to a terminal match outcome.

No conversion weight may translate a submission stage into axis value.

## Gate A — Locked has a submission purpose

### Requirement

From Locked Mount, with the v0.3a submission route legally available, Top must have at least one legal action whose probability of advancing the submission track is greater than zero against the positive-weight response mix.

### Measurement

The checker computes exact submission-stage advancement probability from the same weighted response policy used by batch play.

PASS requires:

```text
max Locked submission-progress probability > 0
```

This gate is probability-based. It does not use expected axis movement and does not assign an artificial axis value to submission progress.

The batch policy must select positive-probability submission progress before setup, positional work, or RESET.

## Gate B — Submissions finish sometimes, but a fresh competent defender survives most matches

### Design direction frozen before results

For the standardized fresh/fresh batch:

> A fresh, competent defender under dominant Top survives most matches rather than being submitted automatically.

The initial executable range derived from that statement is:

```text
0% < Tap match rate < 50%
```

The range is not to be moved after seeing the first v0.3a batch result.

### Measurement

Use the standardized deterministic v0.3a batch and report:

- Tap outcomes / matches;
- matches that reached Threat;
- matches that reached Control;
- matches that reached Finish;
- mean submission-stage attempts per match.

PASS requires a nonzero Tap rate below 50%.

## Gate C — Best fresh defense stops every submission stage

### Requirement

At every reachable Threat, Control, and Finish state with both competitors Fresh, the defender's best legal response must stop the submission track from advancing.

This is the submission equivalent of the v0.2 Ready Contested invariant.

It is not enough for one response to make the attack merely less successful. If every legal response still advances the submission track, the state is a guaranteed attacker win and the gate fails.

### Measurement

An exhaustive stage-aware checker enumerates every reachable fresh state and legal defense.

For each stage it reports:

- reachable states;
- states where best legal defense stops advancement;
- states where every legal response advances.

PASS requires:

```text
best-defense-stops == reachable
guaranteed-advance == 0
```

for Threat, Control, and Finish.

## Gate D — Exhaustion changes submission exchanges in both directions and cancels symmetrically

### Requirement

The v0.2b exhaustion rule remains authoritative:

```text
Exhausted initiator  -> -1 grade
Exhausted responder  -> +1 grade for initiator
both Exhausted       -> net 0
```

Submission-state evidence must show all three consequences explicitly.

### Measurement

For otherwise-identical isolated submission-stage exchanges:

1. hold defender Fresh and change only Top from Fresh to Exhausted;
2. hold Top Fresh and change only defender from Fresh to Exhausted;
3. compare both Exhausted with both Fresh.

PASS requires:

- at least one stage exchange changes when only the attacker becomes Exhausted;
- at least one stage exchange changes when only the defender becomes Exhausted; and
- both-Exhausted exchanges reproduce the corresponding both-Fresh submission outcome signature wherever the net exhaustion modifier is zero.

The signature includes at minimum:

- stage advancement / no advancement;
- Tap / no Tap;
- final submission stage;
- defended-stage axis penalty and resulting band.

## Defended-stage anti-treadmill invariant

Separate regression coverage must prove:

- a defended submission stage at Locked applies the -1.00 defenderward axis step;
- that penalty is persisted rather than absorbed by the +4.00 upper cap;
- the existing band hysteresis is used after the penalty;
- repeated best-defense submission attempts cannot remain indefinitely at unchanged Locked control while only draining Top stamina.

This is a mechanics invariant, not a new tuning gate.

## Predictions recorded before implementation results

These are predictions, not pass criteria:

1. v0.2 Gate 5 should rise because Top gains meaningful follow-up work from Strong/Locked.
2. Gate 5 remains an observation, not a submission-tuning target. The >1.000 threshold must not be moved and submission rules must not be tuned merely to cross it.
3. Exhausted Top should advance/finish the submission less effectively because initiated submission attempts inherit the existing -1 grade modifier.
4. Exhausted Bottom should become more vulnerable while defending because responder exhaustion gives the initiator +1 grade.
5. Bottom recovery should therefore become strategically more important under sustained PRESSURE.
6. Gate 2 should change from DEFERRED to OPEN as soon as the real `SUBMISSION_FINISH` action exists while the repeated-RESET Locked timeout remains.

Prediction 4/5 is the highest-priority early balance check because it can materially change the match outcome distribution.

## Standard v0.3a batch

Unless a pre-result design amendment is committed first, Gate B and observational comparisons use:

```text
100 matches
base seed 42
Top PRESSURE
Bottom ESCAPE
MEDIUM commitment
5:00 clock
starting axis +1.50
5-second interval
100 / 100 starting stamina
escape-first / submission-aware initiator policy
v0.2 setup/Ready enabled
v0.3a Americana submission track enabled
```

## Verification discipline

Every v0.3a implementation change must preserve:

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

The frozen 18-entry matchup table is not extended or retuned by v0.3a. Submission state and submission-specific policy belong in the modern match layer around the frozen resolution engine.

## Change-control rule

If a v0.3a gate cannot pass under this definition, record the failed measurement first.

Do not:

- move a threshold after seeing results;
- convert submission progress into arbitrary axis points;
- weaken best-defense requirements;
- hide the expected Gate-2 OPEN transition;
- retune the frozen matchup table.

Any criterion change must be committed as an explicit design amendment before the implementation is tuned against it.
