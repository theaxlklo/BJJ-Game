# Mount v0.4a — Independent Audit Amendment

## Status

RECORDED DURING INDEPENDENT REVIEW OF PR #5.

This amendment does **not** change the frozen v0.4a commitment semantics, costs, gates, thresholds, feature scope, or predictions in:

`docs/MOUNT_V0_4A_COMMITMENT_SEMANTICS_DEFINITION_OF_DONE.md`

It records two implementation/measurement corrections required to make the branch conform to that already-frozen contract.

## 1. Sequential modifier order must preserve intermediate grade clamps

The frozen order is:

```text
Ready / ordinary positional result
-> pre-cost exhaustion
-> initiator commitment magnitude
-> response under-commitment
-> final grade / positional resolution
```

Each grade step uses the existing bounded Grade domain:

```text
Strong Failure
Failure
Contested
Success
Strong Success
```

Therefore intermediate clamping is semantically meaningful.

The original v0.4a implementation calculated commitment modifiers from the sequential state but then summed:

```text
exhaustion modifier
+ commitment modifier
+ response mismatch modifier
```

and re-applied that total once to the pre-exhaustion grade.

That is not equivalent when an intermediate step clamps at an extreme and a later step moves back toward Contested.

Example:

```text
base Strong Failure
exhaustion -1
-> Strong Failure  (clamped)

MEDIUM magnitude
-> Strong Failure

under-committed response +1
-> Failure
```

A single summed modifier of:

```text
-1 + 0 + 1 = 0
```

incorrectly leaves the result at Strong Failure.

### Required correction

The implementation must compute the target grade **sequentially** in the frozen order.

When commitment adds no tactical grade change, the historical exhaustion `ResolutionResult` must be returned unchanged so feature-off and MEDIUM/MEDIUM compatibility preserve the complete current-exchange result, including diagnostic metadata such as `external_grade_modifier`.

When commitment changes the target grade, the positional resolver may be invoked with the delta required to reproduce that already-computed sequential target grade.

### Regression requirement

Add both:

1. a real exchange reproducing the intermediate-clamp case; and
2. exhaustive grade-level coverage across:
   - every Grade;
   - exhaustion shifts -1 / 0 / +1;
   - initiator effective commitment UNFUNDED / LOW / MEDIUM / HIGH;
   - responder effective commitment UNFUNDED / LOW / MEDIUM / HIGH.

The exhaustive test must pin:

```text
exhaustion
-> magnitude transform
-> response mismatch
```

in that order.

## 2. Gate C global dominance surface includes response commitment

Gate C was frozen as:

> no selectable commitment globally dominates another across the measured fully-funded state surface.

Once v0.4a adds response commitment, responder commitment is part of exchange state.

The original checker held responder commitment fixed at MEDIUM while comparing initiator LOW / MEDIUM / HIGH.

That is not a complete **global** surface.

### Required correction

For every otherwise-frozen ordinary exchange state, Gate C must evaluate initiator commitment comparisons separately under each fully funded responder commitment:

```text
response LOW
response MEDIUM
response HIGH
```

The existing dominance definition remains unchanged:

Commitment X dominates Y only when:

1. cost(X) <= cost(Y);
2. X is no worse than Y in every measured state for final grade, terminal exit attainment, and initiator-favorable realized axis movement;
3. X is strictly cheaper or strictly better in at least one measured state.

PASS still requires:

```text
no selectable commitment globally dominates another
```

No threshold or desired result is changed.

## 3. Gate-B explanatory text after expiry

The executable Gate-B rule is unchanged.

Before response commitment or Recognition exists:

```text
Gate B DEFERRED
```

Once response commitment exists:

```text
deferral expires automatically
unchanged 0% < informed Tap < 50% criterion resumes
```

The checker evidence text should describe the **current** surface when v0.4a is present:

- response commitment is now live;
- public MATCH commitment is actually used by the informed batch;
- an informed 0-tap result is OPEN evidence;
- Recognition/information remains later work;
- the range is not retuned.

Historical v0.3a deferral text remains appropriate only while the capability is absent.

## Change control

These corrections do not authorize changes to:

- LOW / MEDIUM / HIGH costs 3 / 7 / 12;
- commitment transforms;
- response mismatch +1;
- feint cap;
- responder funding semantics;
- hold cost;
- exhaustion thresholds;
- matchup matrix;
- response weights;
- Gate-B range;
- setup semantics;
- stalling mechanics;
- scoring.

After these corrections, all v0.4a gates and batches must be re-measured from the corrected implementation. The earlier first-measurement document remains historical evidence and must not be silently rewritten into the final result.
