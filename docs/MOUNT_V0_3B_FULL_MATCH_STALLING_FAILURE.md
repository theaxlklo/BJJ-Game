# Mount v0.3b — Full-Match Stalling Failure Measurement

## Status

RECORDED BEFORE ESCALATION MECHANICS CHANGE.

## Evidence head

```text
d3907985e98400e71b1f0f664f94cc8f2a6090ac
```

The corrected Gate-A probe now runs deliberate Top stalling through the full 5:00 match instead of stopping immediately after the first positional penalty.

The probe preserves Top's normal default-interval initiation cadence while suppressing Bottom's intervening initiation so defensive engagement cannot reset Top's advancement clock.

## Result

```text
v0.3b Gate A OPEN
v0.2 Gate 2 OPEN
```

Measured full-match result:

```text
Warning count: 1
one-band penalties: 13
final axis: +4.00
final band: Locked
locked_timeout: True
Locked decision windows: 59/59
```

The historical two-sided RESET probe also remains:

```text
TIMEOUT — Mount retained
+4.00 Locked
```

## Why the previous Gate A PASS was invalid

The previous Gate-A probe stopped after two 20-second offense periods:

```text
first offense -> Warning
second offense -> one-band penalty
```

and immediately read:

```text
+4.00 Locked -> +2.80 Strong
```

That proved only that the first penalty could temporarily dislodge Locked.

It did **not** prove the actual Gate-A requirement:

> deliberate stalling cannot retain Locked through timeout.

Because the match had not reached timeout, `locked_timeout=False` was trivially true.

The corrected probe removes that measurement error.

## Why one-band penalties are insufficient

Under the frozen PRESSURE / ESCAPE drift:

```text
Top drift = +0.10 axis / simulated second
```

A Locked-to-Strong stalling penalty sets the persisted axis to:

```text
+2.80
```

The Locked re-entry hysteresis threshold is:

```text
+3.20
```

So only:

```text
4 simulated seconds
```

of unchanged PRESSURE drift are needed to re-enter Locked.

The next qualifying stalling offense cannot occur until another:

```text
20 simulated seconds
```

without engagement.

Therefore a repeated one-band penalty is a temporary bump rather than a meaningful escalation.

The full-match evidence confirms the arithmetic: 13 positional penalties do not prevent a Locked timeout.

## Penalty-size note

"One visible band" is implemented by placing the axis on the existing hysteresis threshold for leaving the current band.

Therefore the numeric axis loss depends on where inside the band the offender currently sits.

For example:

```text
+4.00 Locked -> +2.80 Strong = -1.20
+3.21 Locked -> +2.80 Strong = -0.41
```

This is intentional for a **visible-band** penalty, but it means the rule is not a fixed numeric axis subtraction.

That property must remain documented if the first positional penalty stays in the final ladder.

## Other gates remain valid

The corrected full-match measurement does not invalidate the other v0.3b semantics:

```text
Gate B PASS
  active Americana attempts into informed Turn-In
  -> zero stalling penalties for both players

Gate C PASS
  either side can receive Warning + positional penalty

Gate D PASS
  positional penalty does not cross Neutral
  Loose boundary uses zero-time free initiative

Gate E PASS
  response_commitment_present=False
  recognition_present=False
  v0.3a Gate B remains DEFERRED
```

## Standard-play observation remains clean

The normal PRESSURE / ESCAPE policy continues to produce:

```text
Top warnings=0
Bottom warnings=0
Top penalties=0
Bottom penalties=0
```

Any stronger escalation must preserve this observation so engaged play is not accidentally punished.

## Design conclusion

The first two Section-33 rungs are not sufficient by themselves:

```text
Warning
-> one-band penalty
```

The v9 freeze already contains the next escalation concept:

```text
Second major offense:
Position Reset
```

and later states:

```text
Repeated offense may cause:
Position Reset
```

The next mechanics change must therefore complete that existing escalation rather than increase the 20-second cadence or numerically tune the one-band penalty until Gate A happens to pass.
