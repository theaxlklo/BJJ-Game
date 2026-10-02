# v0.3a Design Amendment — Submission Stalemate and Informed Defense

## Why this amendment exists

PR #3 review found a contradiction between Ready Americana legality and active submission-stage legality.

Ready Americana establishes arm isolation and permits only:

```text
Forearm Frame
Turn-In Recovery
```

with Turn-In Recovery as the designated fresh stalemate defense.

The first v0.3a implementation then reopened **all** ordinary Bottom responses during Threat, Control, and Finish. That made Tight Elbows legal again immediately after isolation had made it illegal.

Because the frozen Americana row gives Tight Elbows a Strong Failure result, an informed responder could choose Tight Elbows at every stage and break the track indefinitely. Even responder exhaustion only shifts Strong Failure to Failure, so the perfect-response lock survived.

That means the 39% Tap result measured random-response mistakes rather than a submission route that can beat informed defense under the intended exhaustion condition.

This amendment is frozen before the corrective implementation.

## Submission-stage response legality

While the Americana isolation is active, Threat, Control, and Finish inherit the existing Ready-Americana legal response set:

```text
Forearm Frame
Turn-In Recovery
```

Tight Elbows remains illegal until the active Americana track is broken and the arm must be re-isolated.

This is an isolation-state rule, not a claim that Americana belongs only to Mount. Future positional entry contexts may provide their own legal defense sets for the same Americana control graph.

## Submission-stage result semantics

Stage resolution uses the frozen Americana matchup row plus the existing behavior, positional, and exhaustion modifiers.

The resulting final grade is interpreted as:

```text
Success / Strong Success
    -> advance one submission stage
    -> Finish success = Tap
    -> no free positional-axis gain

Contested
    -> HOLD the current submission stage
    -> no stage advance
    -> no track break
    -> no axis penalty

Failure / Strong Failure
    -> submission defense succeeds
    -> break the active Americana track
    -> persist axis -1.00 toward Bottom
```

Therefore `Contested` has the same conceptual role as the v0.2 Ready stalemate: competent fresh defense can stop progress without automatically winning the entire exchange.

The existing -1.00 anti-treadmill penalty applies only when the defender actually wins the submission exchange at Failure or worse.

## Gate C amendment — best fresh defense holds the stage

The prior wording, "best fresh defense stops advancement," was too weak because a guaranteed defender win also passed.

Gate C now requires, at every reachable Threat, Control, and Finish state with both competitors Fresh:

```text
best legal defense final grade == Contested
```

PASS requires:

- every reachable fresh stage state has at least one legal response;
- the defender's best legal response is exactly Contested;
- no reachable fresh stage has every legal response advance the attacker;
- no reachable fresh stage has best defense at Failure or Strong Failure.

This preserves the stalemate invariant rather than reintroducing perfect-response lock.

## Gate E — informed exhausted defender is not a perfect lock

A new gate explicitly checks the failure mode that Gate C previously missed.

### Requirement

With Top Fresh and Bottom Exhausted, an informed Bottom responder choosing the best legal response at every active Americana stage must not be able to stop the entire submission route forever.

The isolated v0.3a proof sequence starts at Threat with:

```text
Top Fresh
Bottom Exhausted
Top PRESSURE
Bottom ESCAPE
axis +3.50 / Locked
LOW commitment
no drift between stage attempts
```

At each Threat / Control / Finish attempt, the checker chooses the legal response producing the lowest final grade for Top.

PASS requires the informed best-response sequence to reach Tap.

This is intentionally an isolated mechanics proof, not a match-level Tap-rate target.

## Gate D remains unchanged

Gate D still checks:

- exhausted attacker changes at least one submission result;
- exhausted defender changes at least one submission result;
- both Exhausted cancel back to the fresh/fresh result.

Its stage signature must now distinguish:

```text
advance
hold
break
tap
```

rather than treating every non-success as the same defended result.

## Gate B remains unchanged

The frozen standard-batch target remains:

```text
0% < Tap match rate < 50%
```

No response weight, raw matchup grade, stamina value, commitment value, or Gate-B threshold changes in this amendment.

Gate B will be remeasured after the legality/stalemate correction.

## Stamina saturation observation

PR review also identified the opposite stamina extreme from early v0.1:

```text
PRESSURE vs ESCAPE
v0.3 submissions enabled
Top median final stamina = 0
Bottom median final stamina = 0
Top RESET count = 0
Bottom RESET count = 0
```

Late matches therefore frequently reach mutual exhaustion, whose v0.2b modifiers cancel and can make exchanges behave like fresh/fresh again.

This is recorded as **non-gating debt** for later pacing / stalling / recovery work. v0.3a must not tune stamina costs or recovery merely to change this observation.

The stalemate correction may alter these measurements and they must be reported again after implementation.

## Multi-position direction remains unchanged

Americana control remains separate from positional ownership:

```text
Mount ----------\
Side Control ----\
Knee-on-Belly ----> Americana access/isolation -> Threat -> Control -> Finish
Guard -----------/
```

Each future entry context may define how isolation is established and which defenses are legal while that isolation holds.

This amendment changes only the semantics of the currently modeled isolated-Americana stages.
