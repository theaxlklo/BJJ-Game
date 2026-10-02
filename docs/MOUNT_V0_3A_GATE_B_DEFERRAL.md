# v0.3a Gate B Deferral — Automatic Expiry and Provisional Hold Cost

## Final v0.3a Gate-B decision

Gate B is **DEFERRED**, not PASS and not OPEN, while the current model lacks both:

1. response-side commitment state; and
2. a Recognition / information mechanic.

The checker does not rely on a manual reminder. It evaluates live capability signals:

```text
response_commitment_present
recognition_present
```

Current v0.3a state:

```text
response_commitment_present=False
recognition_present=False
-> Gate B DEFERRED
```

The deferral automatically expires when **either** signal becomes true.

Once expired, Gate B immediately resumes the unchanged measurement:

```text
0% < informed Tap rate < 50%
```

If the measured rate is inside that range, Gate B is PASS. Otherwise it is OPEN.

## Why the deferral exists

The current informed full-match experiment proves that isolated fatigue sensitivity exists but the normal match cannot maintain the required asymmetry.

Isolated Gate E:

```text
Top Fresh
Bottom Exhausted
best legal Turn-In every stage
-> Success / Success / Success
-> Tap
```

Full informed PRESSURE / ESCAPE with provisional hold cost:

```text
Tap=0/100
Threat=78
Control=0
Finish=0
final median stamina=0/0
```

The provisional responder cost solved one earlier problem:

```text
informed Threat reachability
0/100 -> 78/100
```

but did not solve conversion.

## Cancellation that closes the fatigue window

At standard MEDIUM commitment, Top pays 7 stamina per initiated action while the current submission-hold responder cost is LOW=3.

Sustained pressure therefore exhausts Top at least as fast as Bottom.

When both are Exhausted:

```text
Exhausted initiator modifier = -1
Exhausted responder modifier = +1 for initiator
net submission modifier = 0
```

Turn-In returns to Contested.

The future defender-effort / information slice must not restart from "try a larger number until Gate B passes." It must create a principled asymmetry through at least one of these designs:

### Cost asymmetry

The defender's cost for maintaining a submission stalemate becomes meaningfully different from the attacker's cost for forcing it, such as response commitment or another evidence-backed defender-effort model.

### Exhaustion-effect asymmetry

Mutual exhaustion stops canceling specifically for submission exchanges, through an explicit submission exhaustion rule rather than the generic -1/+1 cancellation.

Either path must be specified before tuning against Gate B.

## Provisional LOW=3 rule stays

The Ready/active Americana Contested hold cost of 3 remains in v0.3a.

It is explicitly **PROVISIONAL**.

Reason to retain it:

```text
without hold cost:
  informed Threat=0/100

with LOW=3 hold cost:
  informed Threat=78/100
```

That is a real measured improvement in submission access. Reverting it would restore a model where informed defense prevents the submission system from starting at all.

What LOW=3 does **not** prove:

- that 3 is the final defender cost;
- that defender effort should always be fixed-cost;
- that response commitment should equal LOW;
- that Gate B is solved.

The checker therefore prints the provisional status and the 0 -> 78 access evidence.

## Random and informed models remain visible

The random response prior and informed responder measure different questions.

Current contrast:

```text
random PRESSURE / ESCAPE:
  Tap=99/100

informed PRESSURE / ESCAPE:
  Tap=0/100
```

Neither extreme is silently substituted for the other.

While Gate B is deferred, both remain visible in `--check`.

## Setup-policy debt remains explicit

The informed PROTECT probe exposes the separate setup-policy problem:

```text
completed setup builds=1768
Threat entries=0
```

The batch policy ranks setup progress ahead of positional axis loss, so Top can repeatedly invest in setup despite failure to convert.

`--check` prints this as:

```text
V0.3a SETUP-POLICY DEBT: builder progress is ranked above axis loss; informed PROTECT builds=1768, Threat entries=0.
```

This remains debt for a later policy/setup slice and is not changed to close v0.3a.

## Final v0.3a target state

```text
A PASS
B DEFERRED
C PASS
D PASS
E PASS
```

v0.2 Gate 2 remains OPEN as planned for v0.3b stalling.

Gate 7 commitment meaning remains OPEN.

No Gate-B threshold, response weight, raw matchup grade, stamina threshold, or commitment cost is changed by this deferral.
