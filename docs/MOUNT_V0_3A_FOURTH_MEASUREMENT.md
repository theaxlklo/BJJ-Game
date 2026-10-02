# v0.3a Fourth Measurement — Re-entry and Ready Response Projection

## Evidence point

This measurement was taken after rejecting the Mount-only Americana continuity rule and keeping the submission track independent from Mount dominance.

Representative successful diagnostic run:

```text
GitHub Actions #390
head 1b461e499b258d32eb79dd972c532edb2c53acc3
```

Both Python versions passed the then-current mechanics suite, frozen digest, modern checker, and legacy checker.

Frozen digest remained:

```text
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

## Gate B remains open

Standard batch:

```text
Tap=55/100
Threat=99
Control=98
Finish=78
submission-stage attempts=902
```

The frozen target remains:

```text
0% < Tap match rate < 50%
```

No threshold change is authorized.

## Full rebuild after defense is already real

The current state flow does **not** leave stale Americana Ready state behind:

1. Ready Americana is consumed when used.
2. A successful entry starts Threat.
3. Any defended submission stage breaks the active submission track.
4. The Americana setup tier remains None after that defense.
5. Top must rebuild None -> Partial -> Ready before another entry.

Therefore the 55% Tap rate is not caused by Ready surviving a defended submission.

## Bottom behavior sweep

Matched 100-seed Top-PRESSURE batches:

```text
Bottom ESCAPE:
  taps=55
  escapes=2
  timeouts=43
  completed setup builds=1150
  submission attempts=902

Bottom PROTECT:
  taps=58
  escapes=0
  timeouts=42
  completed setup builds=1134
  submission attempts=853

Bottom CONSERVE:
  taps=58
  escapes=22
  timeouts=20
  completed setup builds=825
  submission attempts=832
```

This rejects the simple explanation that Gate B is high only because the standard batch uses ESCAPE instead of PROTECT.

PROTECT already applies the existing -1 modifier to Americana isolation and finish, yet match-level Tap rate does not fall below the frozen target.

## Reacquisition sweep

Exact High Mount Climb setup-advance probability under the current generic v0.2 setup rule:

```text
Loose / ESCAPE   1.000
Loose / PROTECT  0.000
Loose / CONSERVE 1.000

Stable / ESCAPE   1.000
Stable / PROTECT  1.000
Stable / CONSERVE 1.000

Strong / ESCAPE   1.000
Strong / PROTECT  1.000
Strong / CONSERVE 1.000

Locked / ESCAPE   1.000
Locked / PROTECT  1.000
Locked / CONSERVE 1.000
```

This confirms that once ordinary Mount control is established, High Mount Climb almost always advances Americana setup regardless of Bottom strategic behavior.

However, changing the generic setup rule so the best response can simply block progress would violate the frozen v0.2 Gate-1 invariant, which deliberately requires two builder attempts to reach Ready even against best-counter play.

So v0.3a should not reopen that generic rule casually.

## Ready-response projection bug

For ordinary Top attacks, the fixed positive-weight Bottom response mix is:

```text
Forearm Frame = 4
Tight Elbows = 3
Turn-In Recovery = 0
```

Ready Americana changes legality to:

```text
Forearm Frame
Turn-In Recovery
```

with Turn-In Recovery designated as the Ready stalemate / best defense.

The current blind responder filters the global mix to legal positive-weight responses. Therefore:

```text
Frame 4 -> retained
Tight Elbows 3 -> discarded because illegal
Turn-In 0 -> still zero
```

The effective Ready-Americana response policy becomes:

```text
Frame = 100%
Turn-In = 0%
```

So the standard batch never selects the Ready state's designated fresh stalemate defense.

That is a policy-projection inconsistency, not a claim about where Americana can exist.

## Pre-implementation projection rule

When a contextual legality rule removes a positive-weight response and identifies a legal designated stalemate/best-defense response, preserve the original total response mass:

```text
1. keep the weights of legal positive-weight responses;
2. collect positive weight from responses that became illegal;
3. redirect that removed weight to the context's designated stalemate response;
4. do not invent new total weight.
```

For Ready Americana this produces:

```text
Forearm Frame = 4
Turn-In Recovery = 3
```

The original 4:3 response mass is preserved.

For Ready Trap-and-Roll, the existing positive-weight legal responses are already Wide Base=2 and Hip Follow=1, so the projection changes nothing.

## Architecture implication

This rule belongs to **context-specific response legality**, not to Mount or Americana itself.

Long-term, the same submission-control graph can be entered from multiple positions:

```text
Mount ---------\
Side Control ---\
Knee-on-Belly ----> Americana access/control graph -> Threat -> Control -> Finish
Guard ----------/
```

Each positional entry context may expose different legal defenses and designate a different fallback/stalemate response while preserving the responder policy's probability mass.

That keeps submission identity separate from position identity.

## Change-control

This experiment does not change:

- the frozen 18-entry raw matchup table;
- global ordinary-response weights;
- stamina costs or exhaustion thresholds;
- commitment costs;
- Gate-B range;
- Gate-5 threshold;
- submission-stage grades;
- defended-stage -1.00 axis consequence.

If projected Ready response mass still leaves Gate B OPEN, record that result rather than tuning the 4:3 weights or the <50% threshold.
