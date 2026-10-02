# v0.3a Second Measurement — One-Stage Regression Still Fails Gate B

## Evidence point

After the first failed 98% Tap measurement, defended submission stages were changed to unwind one layer while keeping the frozen -1.00 defenderward axis cost:

```text
Threat defended  -> track breaks
Control defended -> Threat
Finish defended  -> Control
```

Evidence head:

```text
8a39cf91da2baee5fe029847f6086a7328800cc9
```

GitHub Actions pull-request run:

```text
#370
```

The Python 3.13 job completed successfully with:

```text
202 tests PASS
frozen digest unchanged
modern checker PASS
legacy checker PASS
```

The same mechanics tests and frozen digest step also passed on Python 3.11 before its legacy-check tail completed.

## Measured gates

```text
v0.2 Gate 1 PASS
v0.2 Gate 2 OPEN
v0.2 Gate 3 PASS
v0.2 Gate 4 PASS
v0.2 Gate 5 PASS
v0.2 Gate 6 ACCEPTED
v0.2 Gate 7 OPEN

v0.3a Gate A PASS
v0.3a Gate B OPEN
v0.3a Gate C PASS
v0.3a Gate D PASS
```

## Gate B

The frozen target remains:

```text
0% < Tap match rate < 50%
```

Measured standard batch:

```text
Tap: 80/100 (80.0%)
Threat reached: 99
Control reached: 98
Finish reached: 87
submission-stage attempts: 898
```

The threshold is unchanged. Gate B still fails.

## Activity evidence

Gate 5 is observational only, but it exposes the mechanism:

```text
Top follow-up meaningful initiations/match: 15.420
  position: 0.000
  completed setup builds: 6.440
  submission attempts: 8.980
```

The one-stage regression makes an individual defense meaningful, but Top gets enough rebuild/re-entry cycles over five minutes to drive the match-level Tap rate back to 80%.

## Prediction probe

```text
fresh-fixed:
  taps=80
  escapes=3
  timeouts=17
  submission-attempts=898

exhausted-fixed:
  taps=80
  escapes=0
  timeouts=20
  submission-attempts=910

exhausted-recover:
  taps=83
  escapes=0
  timeouts=17
  submission-attempts=831
```

The expected exhaustion/recovery separation is not useful yet. Submission opportunity volume still dominates the aggregate outcome.

This probe remains non-gating.

## Next mechanics experiment

Keep every frozen threshold, response weight, raw matchup grade, stamina value, and commitment cost unchanged.

Treat a successful submission defense as recovery of the isolated arm rather than only a one-stage delay:

```text
Threat defended  -> track breaks
Control defended -> track breaks
Finish defended  -> track breaks
```

The frozen positional consequence remains:

```text
defended stage -> axis -1.00
```

This makes a completed Americana require uninterrupted Threat -> Control -> Finish progress once the track begins. A defender who wins any submission-stage exchange forces Top to rebuild the existing Americana setup before trying again.

This is a mechanics change against the unchanged Gate-B target, not a change to the target.
